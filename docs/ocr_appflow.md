# 名片OCR管理系統 應用流程指南 (2024 Q4)

## 架構總覽
- **前端 (`frontend/`)**：React 18 + Ant Design Mobile。`ScanUploadPage.js` 處理拍攝/上傳、OCR 進度顯示與欄位編輯；`CardManagerPage.js` 提供列表、搜尋、統計與匯出。
- **後端 (`backend/`)**：FastAPI 服務 (`main.py`) 掛載 `/api/v1/cards` 與 `/api/v1/ocr`。業務邏輯集中於 `services/`，資料模型定義於 `models/`，傳輸結構在 `schemas/`。
- **資料儲存**：預設使用 `cards.db` (SQLite)。圖片產物保存在 `output/card_images/`，批量匯入來源為 `ocr_card_background/uploads/`。
- **背景處理**：`task_manager` 管理產業分類與批量任務；`IndustryClassificationService` 透過 OpenAI API 執行分類。

## 核心流程

### 1. 啟動與初始化
1. 開發者執行 `python main.py` 或 `./start.sh` 啟動後端；`start.sh` 同步啟動 React 開發伺服器。
2. `main.py` 在 FastAPI lifespan 中初始化資料庫 (`backend/models/db.py`) 並創建上傳目錄。
3. 前端由 `index.js` 載入應用，路由指向掃描頁或管理頁。

### 2. 圖像擷取與上傳
1. `ScanUploadPage.js` 支援相機拍攝（透過 `utils/cameraManager.js`）與檔案選擇，限制格式為 JPG/PNG 並檢查大小。
2. 前端將檔案封裝成 `FormData`，以 `POST /api/v1/ocr/image` 上傳；同時更新預覽縮圖與解析狀態。

### 3. 圖像增強與 OCR
1. 後端 `OCRService.ocr_image` 先落地暫存檔，再透過 `CardEnhancementService.process_image` 嘗試智能裁切與 3 倍放大，必要時回退到 OpenCV 或 PIL 基礎處理。
2. `LLMApi` 以結構化 Prompt 呼叫本地（`OCR_API_URL`）或自訂 OpenAI 相容端點，確保回傳 25 個標準欄位。若結果不足，再以增強圖重試。

### 4. 欄位解析與表單填充
1. API 回傳原始 OCR 文字；前端向 `POST /api/v1/ocr/parse-fields` 送出請求。
2. `OCRService.parse_ocr_to_fields` 嘗試解析 JSON；若為純文字，會用關鍵字規則與 LLM 將內容映射至欄位，並處理中英文調換、電話/Email 抽取。
3. 前端依回傳欄位自動填入表單，並有 fallback 機制矯正錯置的中英文。

### 5. 名片保存與校驗
1. 使用者調整表單後提交至 `POST /api/v1/cards/`。資料驗證由 `CardCreate` Pydantic schema 完成。
2. `card_service.create_card` 寫入 `CardORM`，回傳 ISO 格式時間戳。
3. `CardManagerPage` 以 `checkCardStatus` 驗證必填欄位：姓名、公司、職位/部門、聯絡方式至少一個。後端 `get_cards_stats` 使用相同邏輯維繫前後端一致性。

### 6. 產業分類與統計
1. `/api/v1/cards/{id}/classify` 呼叫 `IndustryClassificationService`，依公司與職稱生成 Prompt，採 OpenAI Chat API 回傳「防詐/旅宿/工業應用/食品業/其他」。
2. `/api/v1/cards/classify/batch` 啟動背景執行緒，使用 `task_manager` 追蹤狀態；分類結果會更新 `industry_category`、信心度與時間戳。
3. `/api/v1/cards/stats` 彙整總數、缺失欄位及產業統計，提供前端儀表板資料。

### 7. 匯出與批量處理
1. `/api/v1/cards/export` 支援 CSV、Excel、vCard。程式以 `openpyxl` 或字串流產出檔案並透過 `StreamingResponse` 回傳。
2. `/api/v1/cards/batch-import` 掃描指定資料夾，利用 `BatchProcessingService` 管理記憶體與批次大小，先進行增強再交由 OCR。去重、欄位檢查與問題名片標記皆在匯入循環內完成。

## 主要 API 節點
| Endpoint | Method | Handler | 關鍵職責 |
| --- | --- | --- | --- |
| `/api/v1/ocr/image` | POST | `OCRService.ocr_image` | 上傳影像、進行增強與 OCR |
| `/api/v1/ocr/parse-fields` | POST | `OCRService.parse_ocr_to_fields` | 將 OCR 結果映射為 25 欄位 |
| `/api/v1/cards/` | GET/POST | `card.py` | 分頁查詢、建立名片資料 |
| `/api/v1/cards/export` | GET | `card.py` | 產出 CSV/Excel/vCard |
| `/api/v1/cards/stats` | GET | `card.py` | 名片完整度與產業統計 |
| `/api/v1/cards/{id}/classify` | POST | `card.py` + `IndustryClassificationService` | AI 產業分類 |

## 資料儲存與檔案管理
- SQLite 檔案位於 repo 根目錄，若切換資料庫請更新 `DATABASE_URL`。
- 圖片輸出於 `output/card_images/`，批量處理暫存檔使用 `tempfile` 自動清理。
- `.env` 管理 API 金鑰與 OCR 端點；`backend/core/config.py` 提供預設值與環境檢查。

## 錯誤處理與監控
- `ResponseHandler` 統一成功/失敗響應格式。
- 背景任務錯誤會記錄至 `task_manager` 並在 `/tasks/{id}` 查詢。
- 圖像處理、OCR 與分類均有多層回退機制（臨時檔清理、重試、使用原圖）。

## 開發擴充指引
- 新增欄位時需同步更新 `CardORM`、Pydantic schema、`ScanUploadPage` 的狀態物件、`OCRService.CARD_FIELDS`、統計邏輯。
- 若導入外部 OCR 供應商，擴充 `LLMApi.ocr_generate` 或為 `OCRService` 添加策略切換。
- 大型批次任務請遵循 `BatchProcessingService` 的監控邏輯，避免超過記憶體閾值。
