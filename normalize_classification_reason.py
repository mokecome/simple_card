import os
import sqlite3
import re
from pathlib import Path

from backend.core.config import settings  # 和 apply_industry_mapping_to_cards 一樣
# settings 會從 .env 讀 DATABASE_URL，例如 sqlite:///./cards.db


# === 設定區 ===
DATABASE_URL = settings.DATABASE_URL  # 例：sqlite:///./cards.db
DRY_RUN = False                       # 先用 True 看結果沒問題，再改成 False 實際更新
MAX_PREVIEW = 20                      # 預覽最多顯示幾筆轉換結果


# === 和 apply_industry_mapping_to_cards 一樣的取得 SQLite 路徑邏輯 ===

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


# === 專門把舊格式 reason 轉成新格式的函式 ===

def convert_reason(old: str) -> str | None:
    """
    支援以下格式轉換成：
        primary=xxx, labels=yyy,zzz

    可處理：
    - from_mapping_v3_browsing: primary: XXX | labels: A, B, C, key=xxx
    - from_mapping_v3_browsing: prrimary: XXX, key=xxx
    - from_mapping_v3_browsing:  primary: XXX, key=xxx
    - from_mapping_v3_browsing: primary: XXX
    - from_mapping_v3_browsing: primary: XXX | labels:
    """

    prefix = "from_mapping_v3_browsing:"
    if not old.startswith(prefix):
        return None

    body = old[len(prefix):].strip()

    # ---- 1️⃣  抓 primary (支援 typo：prrimary, pprimary...) ----
    m_primary = re.search(r"p+r*imary[:=]\s*(.*?)(\||,|$)", body, flags=re.IGNORECASE)
    if not m_primary:
        return None  # primary 都沒有 → 略過
    primary = m_primary.group(1).strip()

    # ---- 2️⃣  抓 labels (可選的) ----
    m_labels = re.search(
        r"labels[:=]\s*(.*?)(\||,?\s*key=|$)",
        body,
        flags=re.IGNORECASE,
    )

    if m_labels:
        labels_raw = m_labels.group(1).strip()
        # 處理空的 labels:
        if labels_raw == "" or labels_raw.lower() == "none":
            labels = ""
        else:
            parts = [p.strip() for p in labels_raw.split(",") if p.strip()]
            labels = ",".join(parts)
    else:
        # 無 labels 欄位 → 設成空
        labels = ""

    return f"primary={primary}, labels={labels}"


def main():
    print("=== classification_reason 清理工具 ===")
    print("使用 DATABASE_URL =", DATABASE_URL)

    # 1. 解析 SQLite 路徑
    db_path = get_sqlite_path(DATABASE_URL)
    print(f"🔗 連線到 SQLite 檔案：{db_path}")

    if not os.path.exists(db_path):
        print(f"❌ 找不到資料庫檔案：{db_path}")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 只抓舊格式的資料
    cur.execute(
        """
        SELECT id, classification_reason
        FROM cards
        WHERE classification_reason LIKE 'from_mapping_v3_browsing:%'
        """
    )
    rows = cur.fetchall()

    print(f"🔎 找到 {len(rows)} 筆舊格式 classification_reason 需要處理")

    updates = []
    preview_count = 0

    for card_id, old_reason in rows:
        new_reason = convert_reason(old_reason)
        if new_reason is None:
            print(f"⚠️ 無法解析 card_id={card_id}, reason={old_reason}")
            continue

        updates.append((new_reason, card_id))

        # 預覽前幾筆轉換結果
        if preview_count < MAX_PREVIEW:
            print("\n--- 預覽 ---")
            print(f"id={card_id}")
            print(f"  舊：{old_reason}")
            print(f"  新：{new_reason}")
            preview_count += 1

    print(f"\n✅ 可更新的筆數：{len(updates)}")

    if DRY_RUN:
        print("\n🧪 DRY_RUN 模式開啟：不會實際寫入資料庫。")
    else:
        print("\n💾 開始寫入資料庫...")
        cur.executemany(
            "UPDATE cards SET classification_reason = ? WHERE id = ?",
            updates,
        )
        conn.commit()
        print("✅ 更新完成，已寫入資料庫。")

    conn.close()


if __name__ == "__main__":
    main()
