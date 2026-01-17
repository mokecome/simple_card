import os
import json
import re
import sqlite3
import datetime
from pathlib import Path
from urllib.parse import urlparse

from backend.core.config import settings  # 用來拿 DATABASE_URL

# === 基本設定 ===

DATABASE_URL = settings.DATABASE_URL          # 例：sqlite:///./cards.db
MAPPING_PATH = Path("company_industry_mapping_v3.json")
ONLY_UPDATE_EMPTY = False                     # True = 只更新 industry_category 為 NULL/空字串的
DRY_RUN = False                               # True = 只印結果不寫入 DB


# === 小工具 ===

def get_sqlite_path(db_url: str) -> str:
    """
    從 settings.DATABASE_URL 取得 SQLite 檔案路徑
    例如: sqlite:///./cards.db  -> ./cards.db
    """
    if not db_url.startswith("sqlite:///"):
        raise ValueError(f"目前腳本只支援 SQLite，收到的 DATABASE_URL = {db_url}")

    # 去掉前綴 sqlite:///
    path = db_url[len("sqlite:///"):]
    return path


def normalize_company_name(name: str) -> str:
    """
    和你前面 pipeline 一樣的正規化邏輯：
    - 去頭尾空白
    - 全部小寫
    - 移除空白/全形空白/tab
    - 去掉常見公司尾綴（co., ltd, inc...）
    """
    if not name:
        return ""
    name = name.strip().lower()
    # 移除空白/全形空白/tab
    name = re.sub(r"[ \u3000\t]+", "", name)
    # 去掉常見公司尾綴
    name = re.sub(r"(co\.?,?ltd\.?|corporation|corp\.?|inc\.?)$", "", name)
    return name.strip()


def load_mapping(path: Path) -> dict:
    """
    載入 company_industry_mapping_v3.json
    預期格式：{ normalized_name: { primary_label, labels, confidence, ... }, ... }
    """
    if not path.exists():
        raise FileNotFoundError(f"找不到 mapping 檔案：{path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"mapping 檔案格式錯誤，預期為 dict，實際為: {type(data)}")

    print(f"✅ 載入公司產業 mapping，共 {len(data)} 筆公司")
    return data


def build_candidate_keys(row) -> list[str]:
    """
    給一筆 cards 資料，產生「可能對得上 mapping 的 key 候選列表」

    策略：
    - 同時考慮 company_name_zh / company_name_en
    - 每個名稱都經過 normalize_company_name
    - 去掉空字串 & 重複
    """
    names = []

    zh = (row["company_name_zh"] or "").strip()
    en = (row["company_name_en"] or "").strip()

    if zh:
        names.append(zh)
    if en:
        names.append(en)

    candidates = []

    for name in names:
        # 原始 normalize
        key1 = normalize_company_name(name)
        if key1:
            candidates.append(key1)

        # 額外：移除常見公司尾綴再 normalize 一次（避免我們之前少寫）
        # 例如「股份有限公司」「有限公司」「公司」等等
        tmp = re.sub(r"(股份有限公司|有限公司|股份有 限公司|公司)$", "", name)
        tmp = tmp.strip()
        if tmp and tmp != name:
            key2 = normalize_company_name(tmp)
            if key2:
                candidates.append(key2)

    # 去重
    seen = set()
    unique = []
    for k in candidates:
        if k not in seen:
            seen.add(k)
            unique.append(k)
    return unique


def normalize_confidence(raw_conf) -> float:
    """
    把 mapping 裡的 confidence 正規化成 0.0 ~ 1.0 之間的浮點數
    - 如果是 None / 空 → 給 0.9 當預設
    - 如果 >1，視為百分比，/100
    """
    if raw_conf is None:
        return 0.9
    try:
        c = float(raw_conf)
    except (TypeError, ValueError):
        return 0.9

    if c > 1.0:
        c = c / 100.0
    # 夾在 0~1 之間
    c = max(0.0, min(1.0, c))
    return c


# === 主流程 ===

def main():
    print("使用 DATABASE_URL =", DATABASE_URL)

    # 1. 載入 mapping
    mapping = load_mapping(MAPPING_PATH)

    # 2. 解析 SQLite 路徑並連線
    db_path = get_sqlite_path(DATABASE_URL)
    print(f"🔗 連線到 SQLite 檔案：{db_path}")

    if not os.path.exists(db_path):
        raise FileNotFoundError(f"找不到資料庫檔案：{db_path}")

    conn = sqlite3.connect(db_path)
    # row_factory 讓我們可以用 row["欄位名"] 方式取值
    conn.row_factory = sqlite3.Row

    try:
        cur = conn.cursor()

        # 3. 撈出 cards 表需要的欄位
        cur.execute("""
            SELECT
                id,
                company_name_zh,
                company_name_en,
                industry_category,
                classification_confidence,
                classification_reason,
                classified_at
            FROM cards
        """)
        rows = cur.fetchall()
        total = len(rows)
        print(f"🔍 從 cards 表讀到 {total} 筆名片")

        updated_rows = []
        updated_count = 0
        skipped_has_value = 0
        no_company_name = 0
        no_mapping_match = 0
        example_updates = []

        # 4. 逐筆處理
        for row in rows:
            card_id = row["id"]
            
            # 準備所有候選 key
            candidate_keys = build_candidate_keys(row)

            if not candidate_keys:
                no_company_name += 1
                continue

            if ONLY_UPDATE_EMPTY:
                existing = row["industry_category"]
                if existing is not None and str(existing).strip() != "":
                    skipped_has_value += 1
                    continue

            info = None
            used_key = None

            # 依序嘗試每個候選 key
            for key in candidate_keys:
                hit = mapping.get(key)
                if hit:
                    info = hit
                    used_key = key
                    break

            if not info:
                no_mapping_match += 1
                continue

            # === 從 mapping 取欄位 ===
            # 12 大類 → 寫入 cards.industry_category
            major = info.get("major_category_12")
            # 細標籤：primary_label + labels → 寫入 cards.classification_reason
            primary = info.get("primary_label")
            labels = info.get("labels") or []
            raw_conf = info.get("confidence")

            # 若 mapping 裡沒 major，就退回 primary，再不行就給「不明／其他」
            new_industry = (major or primary or "不明/其他")

            # 置信度照原本邏輯正規化（0~1）
            new_conf = normalize_confidence(raw_conf)

            # 組 classification_reason
            reason_parts = []
            if primary:
                reason_parts.append(f"primary: {primary}")
            if labels:
                reason_parts.append("labels: " + ", ".join(labels))

            base_reason = " | ".join(reason_parts) if reason_parts else None
            if base_reason:
                new_reason = f"from_mapping_v3: {base_reason}, key={used_key}"
            else:
                new_reason = f"from_mapping_v3: key={used_key}"

            now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

            updated_rows.append(
                (
                    new_industry,
                    new_conf,
                    new_reason,
                    now,
                    card_id,
                )
            )
            updated_count += 1

            if len(example_updates) < 5:
                example_updates.append({
                    "id": card_id,
                    "company_name_zh": row["company_name_zh"],
                    "company_name_en": row["company_name_en"],
                    "used_key": used_key,
                    "industry_category": new_industry,
                    "classification_confidence": new_conf,
                    "classification_reason": new_reason,
                })

        # 5. 寫入或 DRY_RUN
        print()
        print("📊 回填結果統計：")
        print(f"  總名片數：{total}")
        print(f"  ✅ 預計更新的名片數：{updated_count}")
        print(f"  ⚪ 已有產業分類而未更新（ONLY_UPDATE_EMPTY=True 才會累加）：{skipped_has_value}")
        print(f"  🚫 沒有公司名稱的名片：{no_company_name}")
        print(f"  ❓ 找不到對應 mapping 的名片數：{no_mapping_match}")
        print()

        if example_updates:
            print("👉 範例更新內容（前 5 筆）：")
            for ex in example_updates:
                print(
                    f"  - card_id={ex['id']}, "
                    f"company_zh={ex['company_name_zh']}, "
                    f"company_en={ex['company_name_en']}, "
                    f"industry={ex['industry_category']}, "
                    f"conf={ex['classification_confidence']:.3f}"
                )
        else:
            print("（沒有任何符合條件的更新）")

        if DRY_RUN:
            print("🔎 目前為 DRY_RUN 模式，不會實際寫入資料庫。")
        else:
            # 真正寫入
            print("💾 正在寫入資料庫...")
            cur.executemany(
                """
                UPDATE cards
                SET
                    industry_category = ?,
                    classification_confidence = ?,
                    classification_reason = ?,
                    classified_at = ?
                WHERE id = ?
                """,
                updated_rows,
            )
            conn.commit()
            print("✅ 寫入完成！")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
