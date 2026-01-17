import os
import json
import re
import sqlite3
import datetime
import unicodedata
from pathlib import Path

from backend.core.config import settings  # 和 backfill_industry_prod_v2 一樣拿 DATABASE_URL

# === 基本設定 ===

DATABASE_URL = settings.DATABASE_URL          # 例：sqlite:///./cards.db
MAPPING_PATH = Path("company_industry_mapping_v3.json")

ONLY_UPDATE_EMPTY = False                      # True = 只更新目前 industry_category 為 NULL/空字串的
DRY_RUN = False                                # True = 只印結果不寫入 DB


# === 小工具：和之前 backfill 一樣的取 SQLite 路徑 ===

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


# === 本次 pipeline 用到的 normalization（跟 mapping 一致） ===

def normalize_width(text: str) -> str:
    """全形/半形 NFKC 正規化"""
    return unicodedata.normalize("NFKC", text)


def remove_parentheses(text: str) -> str:
    """移除中英文括號內的內容"""
    return re.sub(r"[（(].*?[）)]", "", text).strip()


def clean_company_name_strong(name: str) -> str:
    """
    強化版公司名稱清理（無繁簡轉換）：
    - NFKC 正規化（全形/半形）
    - 去掉前後空白
    - 移除括號內文字
    - 中文尾綴 aggressive 清理（股份有限公司、有限公司、企業、集團、控股...）
    - 英文尾綴清理（Co., Ltd, Inc, Corp...）
    - 壓縮多個空白
    """
    if not name:
        return ""

    # 全形/半形正規化
    name = normalize_width(name).strip()
    if not name:
        return ""

    # 去括號
    name = remove_parentheses(name)

    # 中文 aggressive 尾綴
    zh_suffixes = [
        "股份有限公司臺灣分公司",
        "股份有限公司台灣分公司",
        "股份有限公司台北分公司",
        "股份有限公司分公司",
        "有限公司臺灣分公司",
        "有限公司台灣分公司",
        "有限公司台北分公司",
        "有限公司分公司",
        "企業股份有限公司",
        "企業有限公司",
        "有限股份公司",
        "股份有限公司",
        "有限公司",
        "股份公司",
        "企業",
        "控股公司",
        "控股",
        "集團",
        "事業部",
        "事業群",
        "事業處",
        "事業單位",
        "分公司",
        "總公司",
        "分行",
        "分部",
        "部門",
        "部",
        "課",
        "組",
        "處",
        "公司",  # 放後面，避免過度清洗
    ]

    for suf in zh_suffixes:
        if name.endswith(suf):
            name = name[: -len(suf)].strip()
            break

    # 英文尾綴清理
    lowered = name.lower().rstrip(" .,")

    en_suffixes = [
        "co., ltd",
        "co, ltd",
        "co ltd",
        "co.,ltd",
        "company ltd",
        "company limited",
        "inc.",
        "inc",
        "corp.",
        "corp",
        "corporation",
        "limited",
        "ltd.",
        "ltd",
    ]

    for suf in en_suffixes:
        if lowered.endswith(suf):
            cut_len = len(suf)
            name = name[: -cut_len].rstrip(" .,")
            break

    # 壓縮空白
    name = re.sub(r"\s+", " ", name)

    return name.strip()


def make_company_key(company_name_zh: str, company_name_en: str) -> str | None:
    """
    用跟 mapping 一樣的規則算出 company_key：
    - 優先 cleaned_zh，其次 cleaned_en，再來 raw_zh / raw_en
    """
    raw_zh = (company_name_zh or "").strip()
    raw_en = (company_name_en or "").strip()

    cleaned_zh = clean_company_name_strong(raw_zh) if raw_zh else ""
    cleaned_en = clean_company_name_strong(raw_en) if raw_en else ""

    if cleaned_zh:
        return cleaned_zh
    elif cleaned_en:
        return cleaned_en
    elif raw_zh:
        return raw_zh
    elif raw_en:
        return raw_en
    else:
        return None


def normalize_confidence(raw_conf) -> float:
    """
    把 mapping 裡的 confidence 正規化成 0.0 ~ 1.0 的 float
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
    c = max(0.0, min(1.0, c))
    return c


def load_mapping(path: Path) -> dict:
    """
    載入 company_industry_mapping_v3.json
    預期格式：list[ { company_key, major_category_12, primary_label, labels, confidence, ... }, ... ]
    轉成 dict: { company_key: entry }
    """
    if not path.exists():
        raise FileNotFoundError(f"找不到 mapping 檔案：{path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"mapping 檔案格式錯誤，預期為 list，實際為: {type(data)}")

    mapping: dict[str, dict] = {}
    for entry in data:
        key = entry.get("company_key")
        if not key:
            continue
        mapping[key] = entry

    print(f"✅ 載入公司產業 mapping，共 {len(mapping)} 筆公司（以 company_key 計）")
    return mapping


# === 主流程 ===

def main():
    print("使用 DATABASE_URL =", DATABASE_URL)
    print(f"⚙️  DRY_RUN = {DRY_RUN}, ONLY_UPDATE_EMPTY = {ONLY_UPDATE_EMPTY}")

    # 1. 載入 mapping
    mapping = load_mapping(MAPPING_PATH)

    # 2. 解析 SQLite 路徑並連線（和 backfill_industry_prod_v2 型式相同）
    db_path = get_sqlite_path(DATABASE_URL)
    print(f"🔗 連線到 SQLite 檔案：{db_path}")

    if not os.path.exists(db_path):
        raise FileNotFoundError(f"找不到資料庫檔案：{db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # 可以用 row["欄位名"] 方式取值

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

        now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        # 4. 逐筆處理
        for row in rows:
            card_id = row["id"]
            company_name_zh = row["company_name_zh"]
            company_name_en = row["company_name_en"]
            existing_industry = row["industry_category"]

            # 只更新空白產業的情況
            if ONLY_UPDATE_EMPTY:
                if existing_industry is not None and str(existing_industry).strip() != "":
                    skipped_has_value += 1
                    continue

            key = make_company_key(company_name_zh, company_name_en)
            if not key:
                no_company_name += 1
                continue

            info = mapping.get(key)
            if not info:
                no_mapping_match += 1
                continue

            # === 從 mapping 取欄位 ===
            major = info.get("major_category_12")
            primary = info.get("primary_label")
            labels = info.get("labels") or []
            raw_conf = info.get("confidence")

            new_industry = (major or primary or "不明/其他")
            new_conf = normalize_confidence(raw_conf)

            labels_str = ", ".join(labels)
            if primary or labels:
                base_reason = []
                if primary:
                    base_reason.append(f"primary: {primary}")
                if labels:
                    base_reason.append(f"labels: {labels_str}")
                base_reason_str = " | ".join(base_reason)
                new_reason = f"from_mapping_v3_browsing: {base_reason_str}, key={key}"
            else:
                new_reason = f"from_mapping_v3_browsing: key={key}"

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
                    "company_name_zh": company_name_zh,
                    "company_name_en": company_name_en,
                    "used_key": key,
                    "industry_category": new_industry,
                    "classification_confidence": new_conf,
                    "classification_reason": new_reason,
                })

        # 5. 統計與寫入 / DRY_RUN
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
            if updated_rows:
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
            else:
                print("ℹ️ 沒有任何需要更新的資料，略過寫入。")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
