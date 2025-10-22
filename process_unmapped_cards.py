#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量OCR處理未匹配的名片圖片
功能: 讀取 unmapped_card_folders.json 並批量處理OCR掃描
"""

import os
import sys
import json
import asyncio
import aiohttp
from pathlib import Path

# 配置
UNMAPPED_FILE = "unmapped_card_folders.json"
OCR_API_URL = "http://localhost:8006/api/v1/ocr/scan"
BATCH_SIZE = 10  # 每批處理數量
DELAY_BETWEEN_BATCHES = 2  # 批次間延遲(秒)

def log(message):
    """輸出日誌"""
    print(f"[OCR處理] {message}")

def load_unmapped_folders():
    """加載未匹配的文件夾清單"""
    if not os.path.exists(UNMAPPED_FILE):
        log(f"錯誤: 找不到 {UNMAPPED_FILE} 文件")
        log("請先執行 link_card_images.py 生成清單")
        return None

    with open(UNMAPPED_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    log(f"加載了 {len(data)} 個未匹配的文件夾")
    return data

async def process_single_card(session, folder_info):
    """處理單張名片的OCR"""
    folder_id = folder_info['folder_id']
    images = folder_info['images']

    try:
        # 準備上傳文件
        data = aiohttp.FormData()

        # 添加正面圖片
        if len(images) >= 1:
            front_path = images[0]
            with open(front_path, 'rb') as f:
                data.add_field('front_image',
                             f.read(),
                             filename=os.path.basename(front_path),
                             content_type='image/jpeg')

        # 添加反面圖片(如果有)
        if len(images) >= 2:
            back_path = images[1]
            with open(back_path, 'rb') as f:
                data.add_field('back_image',
                             f.read(),
                             filename=os.path.basename(back_path),
                             content_type='image/jpeg')

        # 發送OCR請求
        async with session.post(OCR_API_URL, data=data) as response:
            if response.status == 200:
                result = await response.json()
                card_id = result.get('data', {}).get('card_id')
                log(f"✅ 文件夾 {folder_id} 處理成功 → 新名片ID: {card_id}")
                return True, card_id
            else:
                error_text = await response.text()
                log(f"❌ 文件夾 {folder_id} 處理失敗: {response.status} - {error_text}")
                return False, None

    except Exception as e:
        log(f"❌ 文件夾 {folder_id} 處理異常: {str(e)}")
        return False, None

async def process_batch(folders):
    """批量處理OCR"""
    total = len(folders)
    processed = 0
    success_count = 0
    failed_count = 0

    log("\n開始批量OCR處理...")
    log(f"總數: {total} 個文件夾")
    log(f"批次大小: {BATCH_SIZE}")
    log("="*60)

    # 創建HTTP會話
    async with aiohttp.ClientSession() as session:
        # 分批處理
        for i in range(0, total, BATCH_SIZE):
            batch = folders[i:i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE

            log(f"\n處理批次 {batch_num}/{total_batches} ({len(batch)} 個文件夾)...")

            # 並發處理當前批次
            tasks = [process_single_card(session, folder) for folder in batch]
            results = await asyncio.gather(*tasks)

            # 統計結果
            for success, card_id in results:
                processed += 1
                if success:
                    success_count += 1
                else:
                    failed_count += 1

            log(f"批次完成: 成功 {sum(1 for s, _ in results if s)}/{len(batch)}")
            log(f"總進度: {processed}/{total} ({processed/total*100:.1f}%)")

            # 批次間延遲
            if i + BATCH_SIZE < total:
                await asyncio.sleep(DELAY_BETWEEN_BATCHES)

    # 輸出最終統計
    log("\n" + "="*60)
    log("批量OCR處理完成!")
    log(f"總處理數: {processed}")
    log(f"成功: {success_count} ({success_count/total*100:.1f}%)")
    log(f"失敗: {failed_count} ({failed_count/total*100:.1f}%)")
    log("="*60)

    return success_count, failed_count

async def main():
    """主函數"""
    log("="*60)
    log("批量OCR處理未匹配名片")
    log("="*60)

    # 加載未匹配清單
    unmapped = load_unmapped_folders()
    if not unmapped:
        sys.exit(1)

    # 確認處理
    log(f"\n準備處理 {len(unmapped)} 個文件夾")
    log(f"範圍: {unmapped[0]['folder_id']}-{unmapped[-1]['folder_id']}")

    # 開始處理
    success, failed = await process_batch(unmapped)

    if failed == 0:
        log("\n✅ 所有文件夾處理成功!")
        sys.exit(0)
    else:
        log(f"\n⚠️  有 {failed} 個文件夾處理失敗,請檢查日誌")
        sys.exit(1)

if __name__ == "__main__":
    # 檢查Python版本
    if sys.version_info < (3, 7):
        log("錯誤: 需要 Python 3.7+")
        sys.exit(1)

    # 運行異步主函數
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("\n⚠️  用戶中斷處理")
        sys.exit(130)
