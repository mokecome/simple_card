# 建立時間日期篩選 - 搜尋與匯出 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 將現有的「導入日期範圍」篩選從純前端過濾改為後端 API 層級篩選，使其支援分頁查詢和匯出功能。

**Architecture:** 前端已有日期選擇 UI（`importDateFrom` / `importDateTo`），但目前只做 client-side 過濾，無法正確配合分頁。改為將日期參數傳給後端 API，在 `get_cards_paginated()` 中加入 `created_at` 的範圍查詢，同時在匯出 API 中也接收日期參數。

**Tech Stack:** FastAPI (backend), SQLAlchemy (ORM), React (frontend), SQLite (DB, `created_at` 已建索引)

---

## 現狀分析

| 層級 | 現狀 | 問題 |
|------|------|------|
| DB Model | `created_at` DateTime 欄位已存在且已建索引 | 無需修改 |
| Service | `get_cards_paginated()` 不接受日期參數 | 需新增 `date_from`, `date_to` |
| API `/cards/` | 無 `date_from`, `date_to` query params | 需新增 |
| API `/cards/export/download` | 無日期篩選參數 | 需新增 |
| Frontend `loadCards()` | 不傳日期參數給 API | 需傳入 |
| Frontend `handleExport()` | 不傳日期參數給 API | 需傳入 |
| Frontend 進階篩選 UI | 已有日期選擇器，但只做 client-side 過濾 | 改為 server-side |

---

### Task 1: 後端 Service — `get_cards_paginated()` 加入日期過濾

**Files:**
- Modify: `backend/services/card_service.py:81-88` (`get_cards_paginated` 函數簽名及過濾邏輯)

**Step 1: 修改函數簽名，加入 `date_from` 和 `date_to` 參數**

在 `get_cards_paginated()` 加入兩個 Optional[str] 參數：

```python
def get_cards_paginated(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    industry: Optional[str] = None,
    filter_status: Optional[str] = None,
    date_from: Optional[str] = None,   # 新增：格式 "YYYY-MM-DD"
    date_to: Optional[str] = None      # 新增：格式 "YYYY-MM-DD"
) -> Tuple[List[dict], int]:
```

**Step 2: 在搜索過濾之後、狀態過濾之前，加入日期過濾邏輯**

在 `if search:` 區塊之後（約 line 116 後）加入：

```python
    # 建立時間（日期）過濾
    if date_from:
        from datetime import datetime as dt
        try:
            start = dt.strptime(date_from, "%Y-%m-%d")
            query = query.filter(CardORM.created_at >= start)
        except ValueError:
            pass

    if date_to:
        from datetime import datetime as dt
        try:
            end = dt.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(CardORM.created_at <= end)
        except ValueError:
            pass
```

**Step 3: 驗證**

Run: `python -c "from backend.services.card_service import get_cards_paginated; print('import ok')"`

**Step 4: Commit**

```bash
git add backend/services/card_service.py
git commit -m "feat: add date_from/date_to filtering to get_cards_paginated"
```

---

### Task 2: 後端 API — 列表端點加入日期參數

**Files:**
- Modify: `backend/api/v1/card.py:107-120` (list_cards endpoint)

**Step 1: 在 `list_cards()` 加入 query parameters**

```python
@router.get("/")
def list_cards(
    skip: int = Query(0, ge=0, description="跳過記錄數"),
    limit: int = Query(100, ge=1, le=1000, description="每頁記錄數"),
    search: Optional[str] = Query(None, description="搜索關鍵詞"),
    industry: Optional[str] = Query(None, description="产业分类过滤"),
    status: Optional[str] = Query("all", description="狀態篩選: all / normal / problem"),
    date_from: Optional[str] = Query(None, description="建立日期起始 (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="建立日期結束 (YYYY-MM-DD)"),
    use_pagination: bool = Query(False, description="是否使用分頁"),
    db: Session = Depends(get_db)
):
```

**Step 2: 將日期參數傳入 `get_cards_paginated()` 呼叫**

```python
cards, total = get_cards_paginated(
    db, skip=skip, limit=limit, search=search,
    industry=industry, filter_status=status,
    date_from=date_from, date_to=date_to
)
```

**Step 3: Commit**

```bash
git add backend/api/v1/card.py
git commit -m "feat: add date_from/date_to query params to list_cards endpoint"
```

---

### Task 3: 後端 API — 匯出端點加入日期參數

**Files:**
- Modify: `backend/api/v1/card.py:801-821` (export_cards endpoint)

**Step 1: 在 `export_cards()` 加入日期 query parameters**

```python
@router.get("/export/download")
def export_cards(
    format: str = Query("csv", enum=["csv", "excel", "vcard"]),
    search: Optional[str] = Query(None, description="搜索關鍵詞"),
    industry: Optional[str] = Query(None, description="產業分類篩選"),
    status: Optional[str] = Query(None, description="狀態篩選: all / normal / problem"),
    date_from: Optional[str] = Query(None, description="建立日期起始 (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="建立日期結束 (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
```

**Step 2: 更新 `has_filter` 判斷，加入日期條件**

```python
has_filter = search or (industry and industry != '全部') or (status and status != 'all') or date_from or date_to
```

**Step 3: 傳入日期參數到 `get_cards_paginated()`**

```python
if has_filter:
    cards, total = get_cards_paginated(
        db, skip=0, limit=999999,
        search=search,
        industry=industry if industry and industry != '全部' else None,
        filter_status=status if status and status != 'all' else None,
        date_from=date_from,
        date_to=date_to
    )
```

**Step 4: Commit**

```bash
git add backend/api/v1/card.py
git commit -m "feat: add date_from/date_to to export endpoint"
```

---

### Task 4: 前端 — `loadCards()` 傳入日期參數給 API

**Files:**
- Modify: `frontend/src/pages/CardManagerPage.js:381-389` (loadCards API call)

**Step 1: 在 `loadCards()` 的 API params 中加入日期參數**

```javascript
const response = await axios.get('/api/v1/cards/', {
  params: {
    use_pagination: true,
    skip: currentPageToLoad * pageSize,
    limit: pageSize,
    search: searchText || undefined,
    industry: industryFilter && industryFilter !== '全部' ? industryFilter : undefined,
    status: filterStatus !== 'all' ? filterStatus : undefined,
    date_from: advancedFilters.importDateFrom || undefined,
    date_to: advancedFilters.importDateTo || undefined,
  }
});
```

**Step 2: 確保 `advancedFilters` 變更時觸發重新載入**

檢查 `useEffect` 依賴陣列（約 line 511），確認 `advancedFilters` 已包含在內。如未包含，需加入 `advancedFilters.importDateFrom` 和 `advancedFilters.importDateTo`。

**Step 3: 移除 client-side 日期過濾（lines 467-475）**

刪除以下程式碼（因為已改為 server-side 過濾）：

```javascript
// 移除這段 — 日期過濾已改為 server-side
// if (advancedFilters.importDateFrom || advancedFilters.importDateTo) {
//   const cardDate = new Date(card.created_at);
//   if (advancedFilters.importDateFrom && cardDate < new Date(advancedFilters.importDateFrom)) {
//     return false;
//   }
//   if (advancedFilters.importDateTo && cardDate > new Date(advancedFilters.importDateTo + ' 23:59:59')) {
//     return false;
//   }
// }
```

**Step 4: Commit**

```bash
git add frontend/src/pages/CardManagerPage.js
git commit -m "feat: pass date params to API, remove client-side date filtering"
```

---

### Task 5: 前端 — `handleExport()` 傳入日期參數

**Files:**
- Modify: `frontend/src/pages/CardManagerPage.js:570-577` (handleExport)

**Step 1: 在 `handleExport()` 的 params 中加入日期參數**

在 `if (filterStatus && filterStatus !== 'all')` 之後加入：

```javascript
if (advancedFilters.importDateFrom) params.append('date_from', advancedFilters.importDateFrom);
if (advancedFilters.importDateTo) params.append('date_to', advancedFilters.importDateTo);
```

**Step 2: Commit**

```bash
git add frontend/src/pages/CardManagerPage.js
git commit -m "feat: pass date params to export API"
```

---

### Task 6: 前端 — 日期選擇觸發重新查詢

**Files:**
- Modify: `frontend/src/pages/CardManagerPage.js` (useEffect dependencies, ~line 511)

**Step 1: 確保日期篩選變更時自動重新載入**

找到控制 `loadCards()` 的 `useEffect`，確認日期值在依賴中。如果進階篩選目前只在「套用」按鈕時生效，則需在套用按鈕的 handler 中呼叫 `loadCards()`。

觀察現有 flow：進階篩選面板有「套用篩選」按鈕 → 點擊後更新 `advancedFilters` state → 如果 `useEffect` 監聽到變化就自動 reload。

需確認套用按鈕的邏輯能觸發 `loadCards()`。

**Step 2: 驗證完整流程**

1. 選擇日期範圍 → 套用 → 確認 API 請求帶有 `date_from` / `date_to`
2. 匯出 → 確認匯出的資料只包含該日期範圍

**Step 3: Commit**

```bash
git add frontend/src/pages/CardManagerPage.js
git commit -m "feat: ensure date filter triggers reload"
```

---

## 影響範圍總結

| 檔案 | 修改類型 | 說明 |
|------|----------|------|
| `backend/services/card_service.py` | 函數簽名 + 查詢邏輯 | 加 `date_from`, `date_to` 過濾 |
| `backend/api/v1/card.py` | 兩個端點加參數 | list + export 加 date params |
| `frontend/src/pages/CardManagerPage.js` | API 呼叫 + 移除 client-side 過濾 | 3 處修改 |

**無需修改：**
- DB Model（`created_at` 已存在且有索引）
- 前端 UI（日期選擇器已存在於進階篩選面板中）
- Schema / Migration
