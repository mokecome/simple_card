# 名片圖片匹配功能說明

## 📝 概述

本系統已增強圖片匹配功能,支持:
1. **智能驗證**: 通過OCR識別圖片姓名驗證匹配關係
2. **增強關聯**: 只處理Excel範圍內的圖片,避免數據混亂
3. **批量處理**: 自動處理超出範圍的圖片(可選)

## 🗂️ 文件結構

```
/data1/165/ocr_v2/manage_card/
├── 業務行銷客戶資料池.xlsx         (3,449行)
├── card_data/                     (3,685個文件夾)
│   ├── 1-3449/                   (Excel範圍內)
│   └── 3450-3685/                (超出Excel範圍)
├── link_card_images.py            (圖片關聯腳本 - 增強版)
├── verify_image_matching.py       (匹配驗證腳本 - OCR驗證)
├── process_unmapped_cards.py      (批量OCR處理腳本)
└── USAGE_GUIDE.md                (詳細使用指南)
```

## 🔄 匹配邏輯

### 驗證規則
```
card_data/{folder_id}/ ↔ Excel第{folder_id}行 ↔ 數據庫card.id={folder_id}
```

### 驗證方式
- **OCR識別**: 讀取圖片中的姓名
- **姓名比對**: 與Excel中的姓名比較
- **匹配率**: ≥90%為優秀,70-90%為良好,<70%需核實

## 🛠️ 腳本功能

### 1. verify_image_matching.py (驗證腳本)

**功能**:
- 抽樣檢查11個關鍵點
- OCR識別圖片中的姓名
- 與Excel數據比對
- 生成驗證報告

**使用**:
```bash
python3 verify_image_matching.py
```

**輸出**:
- 控制台顯示匹配結果
- 生成 `image_matching_report.json`

### 2. link_card_images.py (關聯腳本 - 增強版)

**功能**:
- 關聯Excel範圍內的圖片 (1-3449)
- 檢測超出範圍的文件夾 (3450-3685)
- 生成未匹配文件夾清單

**使用**:
```bash
python3 link_card_images.py
```

**輸出**:
- 更新數據庫圖片路徑
- 生成 `unmapped_card_folders.json`

### 3. process_unmapped_cards.py (批量OCR處理)

**功能**:
- 讀取未匹配文件夾清單
- 批量調用OCR API
- 自動保存到數據庫

**使用**:
```bash
python3 process_unmapped_cards.py
```

**配置**:
- 批次大小: 10個/批
- 批次延遲: 2秒
- API端點: http://localhost:8006/api/v1/ocr/scan

## 📊 數據流程

```
┌─────────────────────────────────────────────────┐
│ 1. 驗證匹配關係 (可選)                              │
│    verify_image_matching.py                     │
│    ↓ 生成驗證報告                                  │
├─────────────────────────────────────────────────┤
│ 2. 前端導入Excel                                   │
│    業務行銷客戶資料池.xlsx → 數據庫                 │
│    ↓ 3449條記錄                                    │
├─────────────────────────────────────────────────┤
│ 3. 關聯圖片                                        │
│    link_card_images.py                          │
│    ↓ 更新圖片路徑 (1-3449)                         │
│    ↓ 生成未匹配清單 (3450-3685)                    │
├─────────────────────────────────────────────────┤
│ 4. 處理超出範圍圖片 (可選)                          │
│    process_unmapped_cards.py                    │
│    ↓ 批量OCR處理                                   │
│    ↓ 新增236條記錄                                 │
├─────────────────────────────────────────────────┤
│ 5. 重啟服務                                        │
│    pkill -f "python main.py" && python main.py  │
└─────────────────────────────────────────────────┘
```

## ⚙️ 配置參數

### link_card_images.py
```python
EXCEL_MAX_ID = 3449              # Excel最大ID
UNMAPPED_FOLDERS_FILE = "unmapped_card_folders.json"
```

### verify_image_matching.py
```python
sample_points = [1, 10, 50, 100, 500, 1000, 2000, 3000, 3300, 3400, 3449]
OCR_API_URL = "http://localhost:8006/api/v1/ocr/scan"
```

### process_unmapped_cards.py
```python
BATCH_SIZE = 10                  # 每批處理數量
DELAY_BETWEEN_BATCHES = 2        # 批次間延遲(秒)
OCR_API_URL = "http://localhost:8006/api/v1/ocr/scan"
```

## 🚨 注意事項

1. **執行順序**: 建議先驗證後關聯
2. **備份數據**: 執行前已備份數據庫 (`cards_backup_20251015_131845.db`)
3. **網絡連接**: OCR處理需要API服務運行
4. **處理時間**: 批量OCR可能需要較長時間(236個約20-30分鐘)

## 📈 預期結果

### Excel範圍內 (1-3449)
- 成功關聯: ~98.5% (3400+張)
- 文件夾缺失: ~1.3% (45張)
- 文件夾無圖片: ~0.1% (4張)

### 超出範圍 (3450-3685)
- 未匹配文件夾: 236個
- 需要OCR處理: 全部
- 預期成功率: >90%

## 🔗 相關文檔

- **詳細使用指南**: [USAGE_GUIDE.md](./USAGE_GUIDE.md)
- **項目說明**: [CLAUDE.md](./CLAUDE.md)

## 📞 技術支持

遇到問題請檢查:
1. 後端日誌: `backend/nohup_backend.log`
2. 驗證報告: `image_matching_report.json`
3. 未匹配清單: `unmapped_card_folders.json`

---

**最後更新**: 2025-10-15
**版本**: v2.0 (增強版)
