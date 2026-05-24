# 重複名片偵測功能設計

## 日期：2026-04-10

## 目標

當使用者不小心重複掃描同一張名片時，系統能自動偵測並標記，讓使用者在列表頁看到重複提示，並提供對比介面讓使用者決定保留或刪除。

## 設計決策摘要

| 項目 | 決策 |
|------|------|
| 偵測時機 | 儲存後標記，不阻擋掃描流程 |
| 判斷條件 | `name_zh` + `company_name_zh` 完全相同 |
| 列表呈現 | 標籤（重複 xN）+ 篩選器（duplicate） |
| 對比介面 | 上下堆疊卡片式，一頁一組，上下組切換 |
| 圖片顯示 | 正面 + 背面裁切圖 |
| 刪除方式 | 直接刪除（資料庫 + 圖片檔案） |
| 全部保留 | card 加 `reviewed_at` 欄位，標記已審查 |
| 重複標記儲存 | card 加 `duplicate_group_id` 欄位，用 name_zh + company_name_zh 的 hash 值 |

---

## 一、資料庫變更

### cards 表新增欄位

```python
duplicate_group_id = Column(String, nullable=True, index=True)  # md5(name_zh|company_name_zh)，非重複則為 NULL
reviewed_at = Column(DateTime, nullable=True)                    # 使用者審查「全部保留」時設定
```

### duplicate_group_id 規則

- 值 = `md5(f"{name_zh}|{company_name_zh}")`
- 只有當同一 hash 值的名片數量 > 1 時，才設定此欄位
- 只有 1 張時設為 NULL（不是重複）
- 新增名片時：計算 hash → 查有無同 hash 的既有名片 → 有的話，新卡和既有卡都設上 duplicate_group_id
- 刪除名片時：同組剩 1 張時，將最後一張的 duplicate_group_id 設為 NULL

### Migration 腳本

上線時需跑一次性腳本：
1. 掃全表，GROUP BY name_zh, company_name_zh
2. HAVING COUNT(*) > 1 的組別，計算 hash 並寫入 duplicate_group_id
3. 驗證結果（預期 259 組、562 張名片被標記）

---

## 二、後端 API

### 新增端點

#### `GET /api/v1/cards/duplicates`

取得所有待處理的重複組別（需登入）。

**查詢邏輯：**
- GROUP BY duplicate_group_id（不為 NULL）
- 過濾條件：組內至少有一張 reviewed_at 為 NULL
- 支援分頁：`skip`、`limit`（以組為單位）

**回傳格式：**
```json
{
  "groups": [
    {
      "group_id": "a1b2c3d4...",
      "name_zh": "林政憲",
      "company_name_zh": "國泰金融控股股份有限公司",
      "card_ids": [147, 5728, 6012, 6074, 6373],
      "count": 5
    }
  ],
  "total_groups": 259,
  "current_index": 0
}
```

#### `POST /api/v1/cards/duplicates/{group_id}/review`

標記該組全部保留（已審查）。

**行為：**
- 將該組所有名片的 reviewed_at 設為當前時間

### 修改現有端點

#### `GET /api/v1/cards/` — 擴充 status filter

- 新增 `status=duplicate` 選項
- 回傳的每張卡片附加 `duplicate_group_id` 和 `duplicate_count` 欄位

#### `DELETE /api/v1/cards/{id}` — 加上圖片刪除 + 重複組更新

- 刪除名片時同時刪除相關圖片檔案（原圖 + 裁切圖）
- 刪除後檢查同組剩餘數量，若只剩 1 張則清除其 duplicate_group_id

#### `POST /api/v1/cards/` — 新增時計算 duplicate_group_id

- 新增名片後，計算 hash
- 查詢是否有同 hash 的既有名片
- 有的話：新卡和所有同 hash 既有卡都設上 duplicate_group_id
- 同時清除同組名片的 reviewed_at（因為組成員變了，需要重新審查）

---

## 三、前端頁面

### CardManagerPage — 列表頁修改

**重複標籤：**
- 列表載入時，從卡片資料中讀取 `duplicate_group_id` 和 `duplicate_count`
- 有 duplicate_group_id 的卡片右上角顯示紅色標籤「重複 x3」
- 點擊標籤 → 跳轉到對比頁 `/cards/duplicates/:groupId`

**篩選器擴充：**
- status filter 新增「重複」選項（值 = `duplicate`）
- 選擇後只顯示 duplicate_group_id 不為空的名片

### DuplicateComparePage — 新增對比頁面

**路由：** `/cards/duplicates/:groupId`

**頁面結構：**
```
┌─ 頂部導航 ──────────────────┐
│ ← 返回    重複名片 (1/259)   │
└────────────────────────────┘

  林政憲 / 國泰金融控股 — 共 5 張
  ────────────────────────────

  ┌────────────────────────────┐
  │ #147  建立於 2025/10/15     │
  │ ┌──正面──┐  ┌──背面──┐    │
  │ │        │  │        │    │
  │ └────────┘  └────────┘    │
  │ 區塊鏈架構師                │
  │ 0983 803 251               │
  │ ericlin@cathayholdings...   │
  │                 ☐ 選擇刪除  │
  ├────────────────────────────┤
  │ #6012  建立於 2026/4/7      │
  │ ┌──正面──┐  ┌──背面──┐    │
  │ │        │  │        │    │
  │ └────────┘  └────────┘    │
  │ 區塊鏈架構師                │
  │ (無手機)                    │
  │ ericlin@cathayholdings...   │
  │                 ☐ 選擇刪除  │
  └────────────────────────────┘

  ┌──────────────────────────────┐
  │ [上一組] 全部保留 刪除已選(2) [下一組] │
  └──────────────────────────────┘
```

**互動邏輯：**
- 卡片按建立時間排序（最早的在上面）
- 每張顯示：裁切後正面+背面圖、職稱、手機、Email、建立時間
- 勾選要刪除的名片，底部按鈕顯示已選數量
- 「刪除已選」→ 二次確認彈窗 → 確認後逐張呼叫 DELETE API → 刷新頁面
- 刪除後該組剩 1 張 → 自動跳到下一組
- 刪除後該組仍 >1 張 → 留在當前組，繼續操作
- 「全部保留」→ 呼叫 POST /duplicates/{group_id}/review → 跳到下一組
- 最後一組處理完 → 顯示「所有重複組已處理完畢」→ 返回列表頁

---

## 四、檔案變更清單

### 後端
- `backend/models/card.py` — 新增 duplicate_group_id、reviewed_at 欄位
- `backend/schemas/card.py` — 新增對應 schema 欄位
- `backend/services/card_service.py` — 新增重複組查詢、review 邏輯、新增/刪除時的 duplicate_group_id 維護
- `backend/api/v1/card.py` — 新增 duplicates 端點、修改 create/delete 端點
- `backend/migrations/add_duplicate_fields.py` — Migration 腳本（新增欄位 + 初始化既有資料）

### 前端
- `frontend/src/App.js` — 新增 /cards/duplicates/:groupId 路由
- `frontend/src/pages/CardManagerPage.js` — 新增重複標籤、擴充 status filter
- `frontend/src/pages/DuplicateComparePage.js` — 新增對比頁面（新檔案）
- `frontend/src/pages/DuplicateComparePage.css` — 對比頁面樣式（新檔案）
