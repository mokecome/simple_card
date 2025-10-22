#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
名片圖片關聯腳本
功能: 將card_data目錄中的圖片文件關聯到數據庫中的名片記錄
規則: card_data/{folder_id}/ 對應數據庫中的 card.id = folder_id
增強: 檢測未匹配的圖片文件夾,生成OCR處理清單
"""

import os
import sys
import json
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models.card import CardORM
from backend.models.db import Base

# 數據庫配置
DATABASE_URL = "sqlite:///./cards.db"
CARD_DATA_DIR = "card_data"
EXCEL_MAX_ID = 3449  # Excel文件最大ID
UNMAPPED_FOLDERS_FILE = "unmapped_card_folders.json"  # 未匹配文件夾清單

def log(message):
    """輸出日誌"""
    print(f"[圖片關聯] {message}")

def get_images_in_folder(folder_path):
    """獲取文件夾中的所有圖片文件"""
    images = []
    if not os.path.exists(folder_path):
        return images

    for file in os.listdir(folder_path):
        if file.lower().endswith(('.jpg', '.jpeg', '.png')):
            images.append(os.path.join(folder_path, file))

    # 按文件名排序
    images.sort()
    return images

def scan_unmapped_folders():
    """掃描未匹配的card_data文件夾(超出Excel範圍或缺失對應記錄)"""
    unmapped_folders = []

    log("\n開始掃描未匹配的圖片文件夾...")

    # 獲取所有card_data文件夾
    all_folders = []
    for item in os.listdir(CARD_DATA_DIR):
        item_path = os.path.join(CARD_DATA_DIR, item)
        if os.path.isdir(item_path) and item.isdigit():
            all_folders.append(int(item))

    all_folders.sort()
    log(f"發現 {len(all_folders)} 個數字文件夾 (範圍: {min(all_folders)}-{max(all_folders)})")

    # 找出超出Excel範圍的文件夾
    for folder_id in all_folders:
        if folder_id > EXCEL_MAX_ID:
            folder_path = os.path.join(CARD_DATA_DIR, str(folder_id))
            images = get_images_in_folder(folder_path)

            if images:
                unmapped_folders.append({
                    "folder_id": folder_id,
                    "folder_path": folder_path,
                    "images": images,
                    "image_count": len(images),
                    "reason": "超出Excel範圍"
                })

    # 保存到JSON文件
    if unmapped_folders:
        with open(UNMAPPED_FOLDERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(unmapped_folders, f, ensure_ascii=False, indent=2)

        log(f"\n⚠️  發現 {len(unmapped_folders)} 個未匹配的文件夾")
        log(f"範圍: {unmapped_folders[0]['folder_id']}-{unmapped_folders[-1]['folder_id']}")
        log(f"清單已保存到: {UNMAPPED_FOLDERS_FILE}")
        log("這些文件夾需要通過OCR掃描補充數據")
    else:
        log("✅ 所有文件夾都在Excel範圍內")

    return unmapped_folders

def link_images_to_cards():
    """關聯圖片到名片"""
    try:
        # 創建數據庫連接
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        log("開始關聯圖片...")
        log(f"card_data目錄: {os.path.abspath(CARD_DATA_DIR)}")
        log(f"Excel有效範圍: 1-{EXCEL_MAX_ID}")

        # 獲取所有名片
        cards = db.query(CardORM).order_by(CardORM.id).all()
        log(f"數據庫中共有 {len(cards)} 張名片")

        # 統計數據
        total_cards = len(cards)
        updated_count = 0
        no_folder_count = 0
        no_image_count = 0
        out_of_range_count = 0

        # 遍歷名片並關聯圖片
        for card in cards:
            card_id = card.id

            # 跳過超出Excel範圍的記錄
            if card_id > EXCEL_MAX_ID:
                out_of_range_count += 1
                continue

            folder_path = os.path.join(CARD_DATA_DIR, str(card_id))

            # 檢查文件夾是否存在
            if not os.path.exists(folder_path):
                no_folder_count += 1
                continue

            # 獲取文件夾中的圖片
            images = get_images_in_folder(folder_path)

            if not images:
                no_image_count += 1
                log(f"ID {card_id}: 文件夾存在但無圖片文件")
                continue

            # 更新名片記錄
            if len(images) >= 1:
                # 使用相對路徑存儲
                card.front_image_path = images[0]
                log(f"ID {card_id}: 設置正面圖片 -> {images[0]}")

            if len(images) >= 2:
                card.back_image_path = images[1]
                log(f"ID {card_id}: 設置反面圖片 -> {images[1]}")

            updated_count += 1

            # 每100張提交一次
            if updated_count % 100 == 0:
                db.commit()
                log(f"已處理 {updated_count}/{min(total_cards, EXCEL_MAX_ID)} 張名片...")

        # 最終提交
        db.commit()

        # 輸出統計信息
        log("\n" + "="*60)
        log("圖片關聯完成!")
        log(f"Excel範圍內名片: {min(total_cards, EXCEL_MAX_ID)}")
        log(f"成功關聯: {updated_count} 張 ({updated_count/min(total_cards, EXCEL_MAX_ID)*100:.1f}%)")
        log(f"文件夾缺失: {no_folder_count} 張")
        log(f"文件夾無圖片: {no_image_count} 張")
        if out_of_range_count > 0:
            log(f"超出範圍跳過: {out_of_range_count} 張")
        log("="*60)

        db.close()

        # 掃描未匹配的文件夾
        unmapped = scan_unmapped_folders()

        return True, unmapped

    except Exception as e:
        log(f"錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, []

if __name__ == "__main__":
    log("="*60)
    log("名片圖片關聯腳本 (增強版)")
    log("="*60)

    # 檢查card_data目錄是否存在
    if not os.path.exists(CARD_DATA_DIR):
        log(f"錯誤: card_data目錄不存在: {os.path.abspath(CARD_DATA_DIR)}")
        sys.exit(1)

    # 執行關聯
    success, unmapped = link_images_to_cards()

    if success:
        log("\n✅ 腳本執行成功!")

        # 提示未匹配文件夾的處理方式
        if unmapped:
            log("\n" + "="*60)
            log("📋 後續處理建議:")
            log(f"1. 檢查 {UNMAPPED_FOLDERS_FILE} 文件")
            log("2. 對這些圖片執行OCR掃描:")
            log("   - 使用前端「掃描上傳」功能逐個處理")
            log("   - 或使用批量OCR API處理")
            log("3. OCR完成後,新增的名片會自動獲得ID")
            log("="*60)

        sys.exit(0)
    else:
        log("\n❌ 腳本執行失敗!")
        sys.exit(1)
