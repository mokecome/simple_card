# 名片系統圖片功能使用指南

## 📚 目錄
1. [前置準備](#前置準備)
2. [數據導入流程](#數據導入流程)
3. [圖片關聯流程](#圖片關聯流程)
4. [功能驗證](#功能驗證)
5. [常見問題](#常見問題)

---

## 前置準備

### 1. 備份數據庫 ✅ (已完成)
```bash
# 數據庫已備份到
cards_backup_20251015_131845.db
```

### 2. 確認文件結構
確保以下目錄存在且包含數據:
```
/data1/165/ocr_v2/manage_card/
├── cards.db                       # 數據庫文件
├── 業務行銷客戶資料池.xlsx         # Excel數據文件(3,449行)
├── card_data/                     # 名片圖片目錄(3,685個文件夾)
│   ├── 1/
│   │   ├── 435226.jpg            # 正面
│   │   └── 435227.jpg            # 反面
│   ├── 2/
│   ├── 3/
│   ...
│   ├── 3449/                     # Excel範圍內最後一個
│   ├── 3450/                     # 超出Excel範圍
│   ...
│   └── 3685/                     # 最後一個文件夾
├── link_card_images.py            # 圖片關聯腳本 ✅ (增強版)
├── verify_image_matching.py      # 匹配驗證腳本 ✅ (新增)
└── process_unmapped_cards.py     # 批量OCR處理腳本 ✅ (新增)
```

### 3. 驗證圖片匹配關係 🆕 (推薦執行)

**目的**: 通過OCR識別圖片中的姓名,驗證 `card_data/{folder_id}` 與 Excel第{folder_id}行的匹配關係

**執行命令**:
```bash
cd /data1/165/ocr_v2/manage_card
python3 verify_image_matching.py
```

**腳本功能**:
- 抽樣檢查11個關鍵點: 1, 10, 50, 100, 500, 1000, 2000, 3000, 3300, 3400, 3449
- 使用OCR識別每張名片圖片中的姓名
- 與Excel中對應行的姓名比對
- 計算匹配率並生成驗證報告

**預期輸出**:
```
============================================================
開始驗證圖片匹配關係 (OCR姓名比對)
============================================================
[驗證] 讀取Excel文件: 業務行銷客戶資料池.xlsx
[驗證] Excel總行數: 3449

[驗證] 開始樣本檢查 (包含OCR驗證)...
[驗證] ⚠️  這可能需要幾分鐘時間...

[驗證] 檢查點 1:
----------------------------------------
  📁 文件夾: card_data/1
  📊 Excel第1行:
     - 姓名: 高培勳
     - 英文名: Pei Hsun Kao
  🔍 OCR識別中...
  🖼️  OCR識別結果:
     - 姓名: 高培勳
     - 英文名: Pei Hsun Kao
  ✅ 姓名匹配! (完全匹配)

...

============================================================
匹配統計:
============================================================
總檢查數: 11
姓名匹配: 10 (90.9%)
姓名不匹配: 1 (9.1%)
OCR失敗: 0 (0.0%)

============================================================
驗證結論:
============================================================
✅ 匹配率優秀! (≥90%)
✅ 匹配規則確認: card_data/{folder_id} ↔ Excel第{folder_id}行
```

**驗證報告**: 保存在 `image_matching_report.json`

**結論判斷**:
- **≥90%匹配**: ✅ 可以安全執行圖片關聯
- **70-90%匹配**: ⚠️ 可以執行,但需要人工抽查
- **<70%匹配**: ❌ 需要人工核實匹配規則

---

## 數據導入流程

### 步驟1: 清空現有名片數據

**方式A: 通過前端界面(推薦)**
1. 訪問前端頁面: `http://localhost:1002`
2. 進入「名片管理」頁面
3. 找到底部「刪除所有名片」按鈕
4. 點擊並確認刪除

**方式B: 通過API(開發者)**
```bash
curl -X DELETE http://localhost:8006/api/v1/cards/all
```

**預期結果:**
```json
{
  "success": true,
  "message": "成功刪除 3449 張名片"
}
```

### 步驟2: 導入Excel數據

**通過前端界面:**
1. 在「名片管理」頁面
2. 點擊「文本導入」按鈕
3. 選擇文件: `業務行銷客戶資料池.xlsx`
4. 點擊「確認導入」
5. 等待導入完成(約2-3分鐘)

**預期結果:**
```
✅ 導入完成!成功 3449 張名片
  - 總行數: 3449
  - 成功導入: 3449 張
  - 重複: 0 張
  - 失敗: 0 張
```

**導入後數據狀態:**
- 所有名片的 `front_image_path` 和 `back_image_path` 都是 `NULL`
- 需要執行步驟3關聯圖片

---

## 圖片關聯流程

### 步驟3: 執行圖片關聯腳本

**執行命令:**
```bash
cd /data1/165/ocr_v2/manage_card
python3 link_card_images.py
```

**腳本功能 (增強版):**
- 掃描 `card_data/1` 到 `card_data/3449` 文件夾 (僅Excel範圍內)
- 將每個文件夾中的第一張圖片設置為 `front_image_path`
- 將第二張圖片(如果存在)設置為 `back_image_path`
- 匹配規則: `card_data/{folder_id}/` 對應數據庫 `card.id = folder_id`
- **新增**: 自動檢測超出範圍的文件夾 (3450-3685)
- **新增**: 生成未匹配文件夾清單 `unmapped_card_folders.json`

**預期輸出:**
```
============================================================
名片圖片關聯腳本 (增強版)
============================================================
[圖片關聯] 開始關聯圖片...
[圖片關聯] card_data目錄: /data1/165/ocr_v2/manage_card/card_data
[圖片關聯] Excel有效範圍: 1-3449
[圖片關聯] 數據庫中共有 3449 張名片
[圖片關聯] ID 1: 設置正面圖片 -> card_data/1/435226.jpg
[圖片關聯] ID 1: 設置反面圖片 -> card_data/1/435227.jpg
...
[圖片關聯] 已處理 100/3449 張名片...
[圖片關聯] 已處理 200/3449 張名片...
...
============================================================
圖片關聯完成!
Excel範圍內名片: 3449
成功關聯: 3400 張 (98.5%)
文件夾缺失: 45 張
文件夾無圖片: 4 張
============================================================

[圖片關聯] 開始掃描未匹配的圖片文件夾...
[圖片關聯] 發現 3685 個數字文件夾 (範圍: 1-3685)
[圖片關聯]
[圖片關聯] ⚠️  發現 236 個未匹配的文件夾
[圖片關聯] 範圍: 3450-3685
[圖片關聯] 清單已保存到: unmapped_card_folders.json
[圖片關聯] 這些文件夾需要通過OCR掃描補充數據

✅ 腳本執行成功!

============================================================
📋 後續處理建議:
1. 檢查 unmapped_card_folders.json 文件
2. 對這些圖片執行OCR掃描:
   - 使用前端「掃描上傳」功能逐個處理
   - 或使用批量OCR API處理
3. OCR完成後,新增的名片會自動獲得ID
============================================================
```

### 步驟4: 處理超出範圍的圖片 (可選)

**說明**: 如果需要處理 `card_data/3450` 到 `card_data/3685` 的圖片,執行批量OCR腳本

**執行命令:**
```bash
cd /data1/165/ocr_v2/manage_card
python3 process_unmapped_cards.py
```

**腳本功能:**
- 讀取 `unmapped_card_folders.json` 清單
- 批量調用OCR API處理這236個文件夾
- 每批處理10個,批次間延遲2秒
- 自動保存到數據庫並獲得新的ID

**預期輸出:**
```
============================================================
批量OCR處理未匹配名片
============================================================
[OCR處理] 加載了 236 個未匹配的文件夾
[OCR處理] 準備處理 236 個文件夾
[OCR處理] 範圍: 3450-3685

[OCR處理] 開始批量OCR處理...
[OCR處理] 總數: 236 個文件夾
[OCR處理] 批次大小: 10
============================================================

[OCR處理] 處理批次 1/24 (10 個文件夾)...
[OCR處理] ✅ 文件夾 3450 處理成功 → 新名片ID: 3450
[OCR處理] ✅ 文件夾 3451 處理成功 → 新名片ID: 3451
...
[OCR處理] 批次完成: 成功 10/10
[OCR處理] 總進度: 10/236 (4.2%)

...

============================================================
批量OCR處理完成!
總處理數: 236
成功: 220 (93.2%)
失敗: 16 (6.8%)
============================================================
```

---

## 功能驗證

### 步驟5: 重啟後端服務

```bash
# 停止現有服務
pkill -f "python main.py"

# 啟動新服務
cd /data1/165/ocr_v2/manage_card
python main.py
```

**或使用啟動腳本:**
```bash
./start.sh
```

### 步驟6: 驗證靜態文件服務

**測試card_data圖片訪問:**
```bash
# 測試第一張名片的圖片
curl -I http://localhost:8006/static/card_data/1/435226.jpg
```

**預期響應:**
```
HTTP/1.1 200 OK
content-type: image/jpeg
```

### 步驟7: 驗證前端顯示

**訪問前端頁面:**
```
http://localhost:1002/cards
```

**檢查項目:**

1. **名片管理頁面 (CardManagerPage)**
   - ✅ 每張名片卡片顯示縮略圖(正面/反面)
   - ✅ 圖片尺寸: 80px高度
   - ✅ 點擊圖片可以放大查看
   - ✅ 無圖片時顯示占位符圖標

2. **名片詳情頁面 (CardDetailPage)**
   - ✅ 頂部顯示「名片圖片」區域
   - ✅ 正面/反面圖片分別顯示
   - ✅ 圖片尺寸: 最大200px高度
   - ✅ 點擊圖片可以全屏查看
   - ✅ 圖片加載失敗時顯示錯誤提示

---

## 常見問題

### Q1: 部分名片沒有顯示圖片?

**原因:**
- card_data文件夾缺失(例如:card_data/123不存在)
- 文件夾存在但沒有圖片文件

**解決方法:**
```bash
# 檢查缺失的文件夾
python3 -c "
import os
for i in range(1, 3450):
    if not os.path.exists(f'card_data/{i}'):
        print(f'缺失: card_data/{i}')
"
```

### Q2: 圖片顯示404錯誤?

**檢查步驟:**
1. 確認後端服務已重啟
2. 確認main.py已添加StaticFiles配置
3. 測試靜態文件訪問

**調試命令:**
```bash
# 檢查圖片路徑
python3 -c "
from backend.models.db import get_db
from backend.models.card import CardORM

db = next(get_db())
card = db.query(CardORM).first()
print(f'ID: {card.id}')
print(f'Front: {card.front_image_path}')
print(f'Back: {card.back_image_path}')
"

# 測試文件訪問
curl -I http://localhost:8006/static/card_data/1/435226.jpg
```

### Q3: Excel導入失敗?

**檢查文件格式:**
- 確認是 `.xlsx` 格式
- 文件大小不超過50MB
- 欄位名稱與標準格式匹配

**查看日誌:**
```bash
tail -f backend/nohup_backend.log
```

### Q4: 如何回滾到原始數據?

**恢復備份:**
```bash
# 停止服務
pkill -f "python main.py"

# 恢復數據庫
cp cards_backup_20251015_131845.db cards.db

# 重啟服務
python main.py
```

---

## 技術細節

### 圖片URL轉換邏輯

**前端處理:**
```javascript
// card_data/1/435226.jpg → /static/card_data/1/435226.jpg
// output/card_images/front_xxx.jpg → /static/uploads/front_xxx.jpg

const getImageUrl = (imagePath) => {
  if (!imagePath) return null;
  if (imagePath.startsWith('card_data/')) {
    return `/static/${imagePath}`;
  }
  if (imagePath.startsWith('output/card_images/')) {
    return `/static/uploads/${imagePath.replace('output/card_images/', '')}`;
  }
  return imagePath;
};
```

### 後端靜態文件配置

**main.py:**
```python
from fastapi.staticfiles import StaticFiles

# 掛載靜態文件服務
app.mount("/static/card_data", StaticFiles(directory="card_data"), name="card_data")
app.mount("/static/uploads", StaticFiles(directory="output/card_images"), name="uploads")
```

### 數據庫字段

**CardORM模型:**
```python
class CardORM(Base):
    __tablename__ = "cards"
    id = Column(Integer, primary_key=True, index=True)

    # 圖片路徑字段
    front_image_path = Column(String(500))  # 正面圖片路徑
    back_image_path = Column(String(500))   # 反面圖片路徑

    # 其他25個名片字段...
```

---

## 維護建議

### 定期備份
```bash
# 每天備份數據庫
cp cards.db "cards_backup_$(date +%Y%m%d).db"

# 清理30天前的備份
find . -name "cards_backup_*.db" -mtime +30 -delete
```

### 監控圖片文件
```bash
# 檢查圖片文件總數
find card_data -name "*.jpg" | wc -l

# 檢查損壞的圖片
find card_data -name "*.jpg" -exec file {} \; | grep -v "JPEG image"
```

### 性能優化
- 前端圖片懶加載(已實現)
- 分頁載入名片(已實現:20張/頁)
- 瀏覽器緩存靜態文件(由FastAPI StaticFiles自動處理)

---

## 完成清單

### 已完成項目 ✅
- [x] 備份數據庫文件 (cards_backup_20251015_131845.db)
- [x] 創建圖片關聯腳本 (link_card_images.py - 增強版)
- [x] 創建匹配驗證腳本 (verify_image_matching.py - OCR姓名比對)
- [x] 創建批量OCR處理腳本 (process_unmapped_cards.py)
- [x] 配置後端靜態文件服務 (main.py)
- [x] 修改CardManagerPage添加圖片預覽
- [x] 修改CardDetailPage添加圖片顯示
- [x] 更新使用說明文檔 (USAGE_GUIDE.md)

### 操作步驟摘要 📋

**完整流程 (推薦順序):**
```bash
# 0. 驗證圖片匹配關係 (可選但推薦)
python3 verify_image_matching.py

# 1. 前端操作: 清空舊數據
訪問 http://localhost:1002 → 名片管理 → 刪除所有名片

# 2. 前端操作: 導入Excel
名片管理 → 文本導入 → 選擇業務行銷客戶資料池.xlsx → 確認導入

# 3. 關聯圖片到名片記錄
python3 link_card_images.py

# 4. 處理超出範圍的圖片 (可選)
python3 process_unmapped_cards.py

# 5. 重啟後端服務
pkill -f "python main.py"
python main.py

# 6. 驗證功能
訪問 http://localhost:1002/cards 查看名片圖片
```

**快速流程 (僅關聯現有數據):**
```bash
# 如果Excel數據已導入,只需執行:
python3 link_card_images.py
pkill -f "python main.py" && python main.py
```

---

## 聯繫支持

如有問題,請檢查:
- 後端日誌: `backend/nohup_backend.log`
- 瀏覽器控制台錯誤
- 網絡請求狀態

**祝使用愉快!** 🎉
