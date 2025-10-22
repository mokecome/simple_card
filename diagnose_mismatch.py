#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
診斷圖片與數據不匹配問題
"""

import os
import json
import requests
import pandas as pd
from backend.models.db import get_db
from backend.models.card import CardORM

OCR_API_URL = "http://localhost:8006/api/v1/ocr/image"

def ocr_extract_fields(image_path):
    """使用OCR提取圖片中的所有字段"""
    try:
        with open(image_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(OCR_API_URL, files=files, timeout=30)

        if response.status_code == 200:
            text = response.json().get('text', '')
            # 解析JSON字符串
            if '```json' in text:
                json_str = text.split('```json')[1].split('```')[0].strip()
                fields = json.loads(json_str)
                return {'success': True, 'fields': fields}
            return {'success': False, 'error': '無法解析JSON'}
        else:
            return {'success': False, 'error': f'HTTP {response.status_code}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def main():
    print("="*80)
    print("圖片與數據匹配診斷工具")
    print("="*80)

    # 讀取Excel
    df = pd.read_excel("業務行銷客戶資料池.xlsx", sheet_name="工作表1")
    print(f"\nExcel記錄數: {len(df)}")

    # 連接數據庫
    db = next(get_db())
    db_count = db.query(CardORM).count()
    print(f"數據庫記錄數: {db_count}")

    # 檢查文件夾數量
    card_data_folders = [d for d in os.listdir("card_data") if os.path.isdir(os.path.join("card_data", d)) and d.isdigit()]
    print(f"card_data文件夾數: {len(card_data_folders)}")

    print("\n" + "="*80)
    print("開始抽樣檢查 (前10個文件夾)")
    print("="*80)

    mismatches = []

    for folder_id in range(1, 11):
        folder_path = f"card_data/{folder_id}"

        if not os.path.exists(folder_path):
            print(f"\n❌ 文件夾 {folder_id} 不存在")
            continue

        # 獲取圖片
        images = sorted([f for f in os.listdir(folder_path) if f.endswith('.jpg')])
        if not images:
            print(f"\n⚠️  文件夾 {folder_id} 無圖片")
            continue

        # OCR識別
        image_path = os.path.join(folder_path, images[0])
        print(f"\n📁 文件夾 {folder_id}: {images[0]}")
        print(f"   OCR識別中...")

        ocr_result = ocr_extract_fields(image_path)

        if not ocr_result['success']:
            print(f"   ❌ OCR失敗: {ocr_result['error']}")
            continue

        ocr_fields = ocr_result['fields']
        ocr_name = ocr_fields.get('name_zh', '') or ocr_fields.get('name_en', '')
        ocr_company = ocr_fields.get('company_name_zh', '') or ocr_fields.get('company_name_en', '')

        # 數據庫中的數據
        card = db.query(CardORM).filter(CardORM.id == folder_id).first()
        db_name = card.name_zh if card else ''
        db_company = card.company_name_zh if card else ''

        # Excel中的數據 (folder_id對應Excel第folder_id行，索引為folder_id-1)
        excel_row = df.iloc[folder_id - 1] if folder_id <= len(df) else None
        excel_name = excel_row['姓名'] if excel_row is not None else ''
        excel_company = excel_row['公司名稱'] if excel_row is not None and pd.notna(excel_row['公司名稱']) else ''

        # 比較
        name_match = (ocr_name == db_name) or (ocr_name == excel_name)
        company_match = (ocr_company == db_company) or (ocr_company == excel_company)

        status = "✅" if (name_match or company_match) else "❌"

        print(f"   {status} OCR: {ocr_name} | {ocr_company}")
        print(f"      DB:  {db_name} | {db_company}")
        print(f"      Excel: {excel_name} | {excel_company}")

        if not (name_match or company_match):
            mismatches.append({
                'folder_id': folder_id,
                'ocr_name': ocr_name,
                'ocr_company': ocr_company,
                'db_name': db_name,
                'db_company': db_company,
                'excel_name': excel_name,
                'excel_company': excel_company
            })

    print("\n" + "="*80)
    print("診斷結果")
    print("="*80)

    if mismatches:
        print(f"\n❌ 發現 {len(mismatches)} 個不匹配案例:")
        for m in mismatches:
            print(f"\n文件夾 {m['folder_id']}:")
            print(f"  圖片內容: {m['ocr_name']} - {m['ocr_company']}")
            print(f"  數據庫:   {m['db_name']} - {m['db_company']}")
            print(f"  Excel:   {m['excel_name']} - {m['excel_company']}")

        print("\n結論: 文件夾編號與Excel行號不對應!")
        print("建議: 需要通過OCR重新建立圖片與數據的映射關係")
    else:
        print("\n✅ 所有抽樣都匹配成功!")
        print("結論: 文件夾編號與Excel行號對應正確")

if __name__ == "__main__":
    main()
