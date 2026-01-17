"""
用公司產業 mapping 檔，回填 DB cards 表的產業欄位。

- 會連到 backend.core.config.settings.DATABASE_URL 指定的 DB
- 讀取 company_industry_mapping_v3.json (可以改成你實際檔名)
- 依照公司名稱 (中文 / 英文) 正規化後去 mapping 找產業
- 找到的話更新：
    - industry_category
    - classification_confidence
    - classification_reason
    - classified_at

⚠️ 預設為 DRY_RUN = True，不會真的寫入 DB，確認沒問題後再改成 False。
"""

import os
import json
import re
import datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# 這兩個是你專案裡已經有的
from backend.core.config import settings
from backend.models.card import Card  # SQLAlchemy 的 Card 模型
from backend.models.db import SessionLocal


# ======== 可調整參數 ========

# 使用專案設定的 DATABASE_URL（正式機上會從 .env 讀）
DATABASE_URL = settings.DATABASE_URL

# 產業 mapping 檔路徑（放在專案根目錄）
MAPPING_PATH = Path("company_industry_mapping_v3.json")

# 是否只更新「目前 industry_category 為空」的名片
ONLY_UPDATE_EMPTY = False  # 如果想全面覆蓋舊分類 → False

# 是否為試跑模式（不寫入 DB）
DRY_RUN = True  # ✅ 先用 True 看結果，確認沒問題再改 False


# ======== 工具函式 ========

def normalize_company_name(name: str) -> str:
    """
    公司名正規化函式（請依你之前 backfill 用的邏輯微調）
    - 去頭尾空白
    - 全轉小寫
    - 移除空白 / 全形空白
    - 移除常見公司結尾（股份有限公司、co., ltd 等）
    """
    if not name:
        return ""

    # 去空白 & 小寫
    name = name.strip().lower()

    # 移除一般與全形空白
    name = re.sub(r"[ \u3000\t]+", "", name)

    # 移除常見英文字尾
    name = re.sub(r"(co\.?,?ltd\.?|corporation|corp\.?|inc\.?)$", "", name)

    # 這裡如果你之前有處理「股份有限公司」之類，也可以照搬進來
    # name = re.sub(r"(股份有限公司|有限公司)$", "", name)

    return name.strip()


def load_mapping(path: Path) -> dict:
    """
    載入 mapping JSON，格式預期：
    {
        "normalized_company_name": {
            "primary_label": "...",
            "labels": ["...", "..."],
            "description": "...",
            "confidence": 92.5,
            ...
        },
        ...
    }
    """
    if not path.exists():
        raise FileNotFoundError(f"找不到 mapping 檔案：{path}")

    data = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError(f"mapping 檔案格式錯誤，預期為 dict，實際為: {type(data)}")

    print(f"✅ 載入公司產業 mapping，共 {len(data)} 筆公司")
    return data


def choose_company_name(card: Card) -> str:
    """
    從一筆 card 紀錄中，挑一個公司名稱用來做 mapping 查詢：
    - 優先 company_name_zh，若沒有再用 company_name_en
    """
    return (card.company_name_zh or card.company_name_en or "").strip()


# ======== 主流程 ========

def main():
    print("使用 DATABASE_URL =", DATABASE_URL)

    # 1. 載入 mapping
    mapping = load_mapping(MAPPING_PATH)

    # 2. 建立 DB 連線
    #engine = create_engine(DATABASE_URL, future=True)

    updated_count = 0
    skipped_has_value = 0
    no_company_name = 0
    no_mapping_match = 0

    example_updates = []

    session = SessionLocal()
    try:
        # 3. 讀出所有 cards
        cards = session.query(Card).all()
        total = len(cards)
        print(f"🔍 從 cards 表讀到 {total} 筆名片")

        for card in cards:
            company_raw = choose_company_name(card)
            if not company_raw:
                no_company_name += 1
                continue

            # 如果只更新空的，而這筆已有分類 → 跳過
            if ONLY_UPDATE_EMPTY and card.industry_category:
                skipped_has_value += 1
                continue

            key = normalize_company_name(company_raw)
            info = mapping.get(key)

            if not info:
                no_mapping_match += 1
                continue

            # 從 mapping 取出欄位
            primary = info.get("primary_label") or "不明/其他"
            labels = info.get("labels") or []
            conf = float(info.get("confidence") or 90.0)

            # 準備要寫入的內容
            new_industry = primary
            new_conf = conf
            new_reason = f"from_mapping_v3: primary={primary}, labels={','.join(labels)}"
            now = datetime.datetime.utcnow()

            # 如果不是 DRY_RUN，就真的更新物件
            card.industry_category = new_industry
            card.classification_confidence = new_conf
            card.classification_reason = new_reason
            card.classified_at = now

            updated_count += 1

            # 收集幾筆範例，之後印出來給你看
            if len(example_updates) < 5:
                example_updates.append({
                    "id": card.id,
                    "company_name_zh": card.company_name_zh,
                    "company_name_en": card.company_name_en,
                    "industry_category": new_industry,
                    "classification_confidence": new_conf,
                    "classification_reason": new_reason,
                })

        # 4. 決定是否要 commit
        if DRY_RUN:
            session.rollback()
            print("🔎 目前為 DRY_RUN 模式，不會寫入資料庫。")
        else:
            session.commit()
            print("💾 已將變更寫入資料庫。")
    
    finally:
        session.close()

    # ======= 統計輸出 =======
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
                f"conf={ex['classification_confidence']:.1f}"
            )
    else:
        print("（沒有任何符合條件的更新）")


if __name__ == "__main__":
    main()
