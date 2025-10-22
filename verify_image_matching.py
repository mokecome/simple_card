#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
驗證圖片匹配關係 (增強版)
功能: 通過OCR識別圖片中的姓名,與Excel數據比對驗證匹配關係
特性: 圖片預覽、優雅錯誤處理、詳細報告
"""

import os
import sys
import json
import pandas as pd
import requests
from pathlib import Path
from collections import defaultdict
import base64

# 配置
CARD_DATA_DIR = "card_data"
EXCEL_FILE = "業務行銷客戶資料池.xlsx"
VERIFICATION_REPORT = "image_matching_report.json"
VERIFICATION_REPORT_HTML = "image_matching_report.html"  # HTML報告
OCR_API_URL = "http://localhost:8006/api/v1/ocr/scan"  # OCR API端點
SHOW_IMAGE_PREVIEW = True  # 是否在報告中顯示圖片預覽

def log(message):
    """輸出日誌"""
    print(f"[驗證] {message}")

def get_image_info(folder_id):
    """獲取指定文件夾的圖片信息"""
    folder_path = os.path.join(CARD_DATA_DIR, str(folder_id))

    if not os.path.exists(folder_path):
        return None

    images = []
    for file in os.listdir(folder_path):
        if file.lower().endswith(('.jpg', '.jpeg', '.png')):
            # 提取文件名中的數字
            file_number = os.path.splitext(file)[0]
            images.append({
                'filename': file,
                'number': file_number,
                'path': os.path.join(folder_path, file)
            })

    images.sort(key=lambda x: x['filename'])
    return images if images else None

def get_image_base64(image_path, max_size=200):
    """獲取圖片的Base64編碼 (用於HTML預覽)"""
    try:
        from PIL import Image
        import io

        # 打開圖片並調整大小
        img = Image.open(image_path)
        img.thumbnail((max_size, max_size))

        # 轉為Base64
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        img_str = base64.b64encode(buffer.getvalue()).decode()

        return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        return None

def ocr_extract_name(image_path):
    """使用OCR提取圖片中的姓名 (優雅錯誤處理)"""
    try:
        # 檢查文件是否存在
        if not os.path.exists(image_path):
            return {'success': False, 'error': '圖片文件不存在'}

        # 準備文件
        with open(image_path, 'rb') as f:
            files = {'front_image': (os.path.basename(image_path), f, 'image/jpeg')}

            # 調用OCR API (添加超時)
            response = requests.post(
                OCR_API_URL,
                files=files,
                data={'save_to_db': 'false'},  # 不保存到數據庫
                timeout=30  # 30秒超時
            )

        if response.status_code == 200:
            result = response.json()

            # 檢查API返回格式
            if 'data' not in result:
                return {'success': False, 'error': 'API返回格式錯誤'}

            parsed_fields = result.get('data', {}).get('parsed_fields', {})

            # 提取姓名(中文優先)
            name_zh = parsed_fields.get('name_zh', '').strip()
            name_en = parsed_fields.get('name_en', '').strip()

            return {
                'name_zh': name_zh,
                'name_en': name_en,
                'success': True
            }
        else:
            error_msg = f'HTTP {response.status_code}'
            try:
                error_data = response.json()
                if 'detail' in error_data:
                    error_msg += f': {error_data["detail"]}'
            except:
                pass
            return {'success': False, 'error': error_msg}

    except requests.Timeout:
        return {'success': False, 'error': 'OCR請求超時(30秒)'}
    except requests.ConnectionError:
        return {'success': False, 'error': '無法連接到OCR服務'}
    except Exception as e:
        return {'success': False, 'error': f'異常: {str(e)}'}

def compare_names(ocr_name_zh, ocr_name_en, excel_name_zh, excel_name_en):
    """比較姓名是否匹配"""
    # 去除空格並轉小寫比較
    def normalize(name):
        if pd.isna(name) or not name:
            return ""
        return str(name).replace(" ", "").lower()

    ocr_zh_norm = normalize(ocr_name_zh)
    ocr_en_norm = normalize(ocr_name_en)
    excel_zh_norm = normalize(excel_name_zh)
    excel_en_norm = normalize(excel_name_en)

    # 中文名匹配
    zh_match = ocr_zh_norm and excel_zh_norm and ocr_zh_norm == excel_zh_norm

    # 英文名匹配
    en_match = ocr_en_norm and excel_en_norm and ocr_en_norm == excel_en_norm

    # 中文名部分包含
    zh_partial = ocr_zh_norm and excel_zh_norm and (
        ocr_zh_norm in excel_zh_norm or excel_zh_norm in ocr_zh_norm
    )

    # 英文名部分包含
    en_partial = ocr_en_norm and excel_en_norm and (
        ocr_en_norm in excel_en_norm or excel_en_norm in ocr_en_norm
    )

    # 判斷匹配
    if zh_match or en_match:
        return True, "完全匹配"
    elif zh_partial or en_partial:
        return True, "部分匹配"
    else:
        return False, "不匹配"

def verify_matching_pattern():
    """驗證匹配模式 - 通過OCR姓名比對"""
    log("="*60)
    log("開始驗證圖片匹配關係 (OCR姓名比對)")
    log("="*60)

    # 讀取Excel文件
    log(f"\n讀取Excel文件: {EXCEL_FILE}")
    df = pd.read_excel(EXCEL_FILE)
    excel_total = len(df)
    log(f"Excel總行數: {excel_total}")

    # 樣本檢查點
    sample_points = [1, 10, 50, 100, 500, 1000, 2000, 3000, 3300, 3400, 3449]

    verification_results = {
        "excel_total_rows": excel_total,
        "samples": [],
        "pattern_analysis": {},
        "recommendations": [],
        "match_statistics": {
            "total_checked": 0,
            "matched": 0,
            "mismatched": 0,
            "ocr_failed": 0
        }
    }

    log("\n開始樣本檢查 (包含OCR驗證)...")
    log("⚠️  這可能需要幾分鐘時間...")
    log("="*60)

    for folder_id in sample_points:
        if folder_id > excel_total:
            log(f"\n跳過 folder_id={folder_id} (超出Excel範圍)")
            continue

        log(f"\n檢查點 {folder_id}:")
        log("-" * 40)

        # 獲取圖片信息
        images = get_image_info(folder_id)

        if images is None:
            log(f"  ❌ card_data/{folder_id} 文件夾不存在")
            verification_results["samples"].append({
                "folder_id": folder_id,
                "status": "folder_missing"
            })
            continue

        if len(images) == 0:
            log(f"  ❌ card_data/{folder_id} 文件夾為空")
            verification_results["samples"].append({
                "folder_id": folder_id,
                "status": "no_images"
            })
            continue

        # 獲取Excel對應行的數據
        excel_row = df.iloc[folder_id - 1]  # Excel索引從0開始,folder_id從1開始
        excel_name_zh = excel_row.get('姓名', '')
        excel_name_en = excel_row.get('name_en', '')

        log(f"  📁 文件夾: card_data/{folder_id}")
        log(f"  📊 Excel第{folder_id}行:")
        log(f"     - 姓名: {excel_name_zh}")
        log(f"     - 英文名: {excel_name_en}")
        log(f"     - 公司: {excel_row.get('公司名稱', 'N/A')}")

        # OCR識別第一張圖片的姓名
        log(f"  🔍 OCR識別中...")
        first_image_path = images[0]['path']
        ocr_result = ocr_extract_name(first_image_path)

        verification_results["match_statistics"]["total_checked"] += 1

        if not ocr_result['success']:
            log(f"  ❌ OCR識別失敗: {ocr_result.get('error', '未知錯誤')}")
            verification_results["samples"].append({
                "folder_id": folder_id,
                "status": "ocr_failed",
                "error": ocr_result.get('error'),
                "excel_data": {
                    "name_zh": str(excel_name_zh),
                    "name_en": str(excel_name_en)
                }
            })
            verification_results["match_statistics"]["ocr_failed"] += 1
            continue

        ocr_name_zh = ocr_result['name_zh']
        ocr_name_en = ocr_result['name_en']

        log(f"  🖼️  OCR識別結果:")
        log(f"     - 姓名: {ocr_name_zh}")
        log(f"     - 英文名: {ocr_name_en}")

        # 比較姓名
        is_match, match_type = compare_names(
            ocr_name_zh, ocr_name_en,
            excel_name_zh, excel_name_en
        )

        if is_match:
            log(f"  ✅ 姓名匹配! ({match_type})")
            verification_results["match_statistics"]["matched"] += 1
            sample_status = "matched"
        else:
            log(f"  ❌ 姓名不匹配!")
            verification_results["match_statistics"]["mismatched"] += 1
            sample_status = "mismatched"

        verification_results["samples"].append({
            "folder_id": folder_id,
            "status": sample_status,
            "match_type": match_type if is_match else "不匹配",
            "ocr_result": {
                "name_zh": ocr_name_zh,
                "name_en": ocr_name_en
            },
            "excel_data": {
                "name_zh": str(excel_name_zh),
                "name_en": str(excel_name_en),
                "company": str(excel_row.get('公司名稱', ''))
            },
            "images": [img['filename'] for img in images]
        })

    # 分析匹配模式
    log("\n" + "="*60)
    log("匹配統計:")
    log("="*60)

    stats = verification_results["match_statistics"]
    total_checked = stats["total_checked"]
    matched = stats["matched"]
    mismatched = stats["mismatched"]
    ocr_failed = stats["ocr_failed"]

    log(f"總檢查數: {total_checked}")
    log(f"姓名匹配: {matched} ({matched/total_checked*100 if total_checked > 0 else 0:.1f}%)")
    log(f"姓名不匹配: {mismatched} ({mismatched/total_checked*100 if total_checked > 0 else 0:.1f}%)")
    log(f"OCR失敗: {ocr_failed} ({ocr_failed/total_checked*100 if total_checked > 0 else 0:.1f}%)")

    # 計算匹配率
    match_rate = matched / total_checked if total_checked > 0 else 0

    log("\n" + "="*60)
    log("驗證結論:")
    log("="*60)

    if match_rate >= 0.9:  # 90%以上匹配
        log("✅ 匹配率優秀! (≥90%)")
        log("✅ 匹配規則確認: card_data/{folder_id} ↔ Excel第{folder_id}行")

        verification_results["pattern_analysis"] = {
            "pattern_confirmed": True,
            "match_rate": match_rate,
            "pattern_description": "card_data文件夾ID直接對應Excel行號,姓名匹配率高"
        }

        verification_results["recommendations"] = [
            "✅ 可以安全使用 link_card_images.py 進行關聯",
            "✅ Excel第N行 → card_data/N文件夾 → 數據庫card.id=N",
            "✅ 超過3449的文件夾需要單獨處理(執行OCR)"
        ]

    elif match_rate >= 0.7:  # 70-90%匹配
        log("⚠️  匹配率良好 (70-90%)")
        log("⚠️  部分樣本不匹配,可能是OCR識別誤差")

        verification_results["pattern_analysis"] = {
            "pattern_confirmed": True,
            "match_rate": match_rate,
            "pattern_description": "card_data文件夾ID基本對應Excel行號,存在少量OCR誤差"
        }

        verification_results["recommendations"] = [
            "✅ 可以使用 link_card_images.py 進行關聯",
            "⚠️  建議人工抽查不匹配的記錄",
            "⚠️  OCR識別可能存在誤差,需要後續校對"
        ]

    else:  # <70%匹配
        log("❌ 匹配率偏低 (<70%)")
        log("❌ 匹配關係存在問題,需要人工核實")

        verification_results["pattern_analysis"] = {
            "pattern_confirmed": False,
            "match_rate": match_rate,
            "pattern_description": "匹配關係不確定,需要人工核實"
        }

        verification_results["recommendations"] = [
            "❌ 請檢查不匹配的樣本",
            "❌ 可能需要調整匹配邏輯",
            "❌ 建議擴大樣本檢查範圍"
        ]

    # 保存報告
    with open(VERIFICATION_REPORT, 'w', encoding='utf-8') as f:
        json.dump(verification_results, f, ensure_ascii=False, indent=2)

    log(f"\n驗證報告已保存: {VERIFICATION_REPORT}")

    return verification_results

def generate_html_report(results):
    """生成HTML格式的驗證報告 (帶圖片預覽)"""
    try:
        html = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>名片圖片匹配驗證報告</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }
        h2 { color: #555; margin-top: 30px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
        .stat-card { background: #f9f9f9; padding: 15px; border-radius: 5px; border-left: 4px solid #4CAF50; }
        .stat-card.warning { border-left-color: #FF9800; }
        .stat-card.error { border-left-color: #f44336; }
        .stat-label { font-size: 12px; color: #777; }
        .stat-value { font-size: 24px; font-weight: bold; color: #333; }
        .sample { border: 1px solid #ddd; margin: 15px 0; padding: 15px; border-radius: 5px; background: #fafafa; }
        .sample.matched { border-left: 4px solid #4CAF50; }
        .sample.mismatched { border-left: 4px solid #f44336; }
        .sample.error { border-left: 4px solid #FF9800; }
        .sample-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
        .sample-id { font-size: 18px; font-weight: bold; }
        .sample-status { padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: bold; }
        .status-matched { background: #4CAF50; color: white; }
        .status-mismatched { background: #f44336; color: white; }
        .status-error { background: #FF9800; color: white; }
        .image-preview { display: flex; gap: 15px; margin: 15px 0; }
        .image-preview img { max-height: 150px; border: 1px solid #ddd; border-radius: 4px; }
        .data-row { display: grid; grid-template-columns: 120px 1fr; gap: 10px; margin: 5px 0; font-size: 14px; }
        .data-label { font-weight: bold; color: #666; }
        .data-value { color: #333; }
        .recommendations { background: #e8f5e9; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .recommendations li { margin: 5px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 名片圖片匹配驗證報告</h1>
        <p>生成時間: """ + pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>

        <h2>匹配統計</h2>
        <div class="stats">
            <div class="stat-card">
                <div class="stat-label">總檢查數</div>
                <div class="stat-value">""" + str(results['match_statistics']['total_checked']) + """</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">匹配成功</div>
                <div class="stat-value" style="color: #4CAF50;">""" + str(results['match_statistics']['matched']) + """</div>
            </div>
            <div class="stat-card warning">
                <div class="stat-label">匹配失敗</div>
                <div class="stat-value" style="color: #FF9800;">""" + str(results['match_statistics']['mismatched']) + """</div>
            </div>
            <div class="stat-card error">
                <div class="stat-label">OCR失敗</div>
                <div class="stat-value" style="color: #f44336;">""" + str(results['match_statistics']['ocr_failed']) + """</div>
            </div>
        </div>

        <h2>驗證結論</h2>
        <div class="recommendations">
            <p><strong>匹配率: """ + f"{results['pattern_analysis'].get('match_rate', 0)*100:.1f}%" + """</strong></p>
            <p>""" + results['pattern_analysis'].get('pattern_description', '') + """</p>
            <ul>
"""

        for rec in results.get('recommendations', []):
            html += f"                <li>{rec}</li>\n"

        html += """
            </ul>
        </div>

        <h2>詳細樣本檢查結果</h2>
"""

        for sample in results.get('samples', []):
            folder_id = sample['folder_id']
            status = sample['status']

            # 狀態樣式
            if status == 'matched':
                sample_class = 'matched'
                status_class = 'status-matched'
                status_text = '✅ 匹配成功'
            elif status == 'mismatched':
                sample_class = 'mismatched'
                status_class = 'status-mismatched'
                status_text = '❌ 匹配失敗'
            else:
                sample_class = 'error'
                status_class = 'status-error'
                status_text = '⚠️ 處理失敗'

            html += f"""
        <div class="sample {sample_class}">
            <div class="sample-header">
                <div class="sample-id">檢查點 {folder_id}</div>
                <div class="sample-status {status_class}">{status_text}</div>
            </div>
"""

            # 圖片預覽
            if SHOW_IMAGE_PREVIEW and status in ['matched', 'mismatched']:
                images = get_image_info(folder_id)
                if images and len(images) > 0:
                    html += '            <div class="image-preview">\n'
                    for img in images[:2]:  # 最多顯示2張
                        img_base64 = get_image_base64(img['path'])
                        if img_base64:
                            html += f'                <img src="{img_base64}" alt="{img["filename"]}">\n'
                    html += '            </div>\n'

            # Excel數據
            if 'excel_data' in sample:
                excel = sample['excel_data']
                html += """
            <div class="data-row"><div class="data-label">📊 Excel數據:</div><div></div></div>
            <div class="data-row"><div class="data-label">姓名:</div><div class="data-value">""" + excel.get('name_zh', '') + """</div></div>
            <div class="data-row"><div class="data-label">英文名:</div><div class="data-value">""" + excel.get('name_en', '') + """</div></div>
            <div class="data-row"><div class="data-label">公司:</div><div class="data-value">""" + excel.get('company', '') + """</div></div>
"""

            # OCR結果
            if 'ocr_result' in sample:
                ocr = sample['ocr_result']
                html += """
            <div class="data-row" style="margin-top: 10px;"><div class="data-label">🖼️ OCR識別:</div><div></div></div>
            <div class="data-row"><div class="data-label">姓名:</div><div class="data-value">""" + ocr.get('name_zh', '') + """</div></div>
            <div class="data-row"><div class="data-label">英文名:</div><div class="data-value">""" + ocr.get('name_en', '') + """</div></div>
"""

            # 匹配類型
            if 'match_type' in sample:
                html += """
            <div class="data-row" style="margin-top: 10px;"><div class="data-label">匹配結果:</div><div class="data-value">""" + sample['match_type'] + """</div></div>
"""

            # 錯誤信息
            if 'error' in sample:
                html += """
            <div class="data-row" style="margin-top: 10px; color: #f44336;"><div class="data-label">錯誤:</div><div class="data-value">""" + sample['error'] + """</div></div>
"""

            html += """
        </div>
"""

        html += """
    </div>
</body>
</html>
"""

        # 保存HTML文件
        with open(VERIFICATION_REPORT_HTML, 'w', encoding='utf-8') as f:
            f.write(html)

        log(f"HTML報告已保存: {VERIFICATION_REPORT_HTML}")
        return True

    except Exception as e:
        log(f"生成HTML報告失敗: {str(e)}")
        return False

def main():
    """主函數"""
    log("="*60)
    log("圖片匹配關係驗證工具 (增強版)")
    log("="*60)

    # 檢查文件是否存在
    if not os.path.exists(CARD_DATA_DIR):
        log(f"錯誤: {CARD_DATA_DIR} 目錄不存在")
        sys.exit(1)

    if not os.path.exists(EXCEL_FILE):
        log(f"錯誤: {EXCEL_FILE} 文件不存在")
        sys.exit(1)

    # 執行驗證
    results = verify_matching_pattern()

    # 生成HTML報告
    generate_html_report(results)

    # 總結
    log("\n" + "="*60)
    log("驗證完成!")
    log("="*60)

    if results["pattern_analysis"].get("pattern_confirmed"):
        log("\n✅ 匹配關係已確認,可以繼續執行:")
        log("   1. python3 link_card_images.py")
        log("   2. python3 process_unmapped_cards.py (處理超出範圍的)")
        log(f"\n📄 查看詳細報告: {VERIFICATION_REPORT_HTML}")
        sys.exit(0)
    else:
        log("\n⚠️  匹配關係存在疑問,請檢查報告文件")
        log(f"📄 查看詳細報告: {VERIFICATION_REPORT_HTML}")
        sys.exit(1)

if __name__ == "__main__":
    main()
