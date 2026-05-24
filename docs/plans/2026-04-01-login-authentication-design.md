# 登入認證功能設計

**日期：** 2026-04-01
**狀態：** 設計完成，待實作

## 目標

為名片 OCR 管理系統新增登入認證功能，保護敏感資料頁面，同時保留掃描上傳功能的開放使用。

## 設計決策

| 決策項目 | 選擇 | 原因 |
|---------|------|------|
| 登入觸發時機 | 點擊受保護功能時彈出 | 掃描上傳保持開放，降低業務人員使用門檻 |
| 登入介面 | Modal 彈窗 | 體驗流暢，不離開當前頁面 |
| 帳密儲存 | 後端 `.env` 環境變數 | 目前只有一組帳密，簡單即可；未來可擴充為資料庫 |
| Session 維持 | localStorage + JWT，7 天有效期 | 避免公司同事每天重新登入 |

## 受保護範圍

| 路由 | 頁面 | 需要登入 |
|------|------|---------|
| `/` | 首頁（功能選擇） | 否 |
| `/scan` | 掃描/上傳 | 否 |
| `/cards` | 名片管理列表 | **是** |
| `/cards/:id` | 單張名片詳情 | **是** |
| `/add-card` | 手動新增名片 | **是** |
| `/spider` | 商機爬蟲 | **是** |

## 後端設計

### 新增端點

- `POST /api/v1/auth/login` — 接收 `{ username, password }`，驗證後回傳 JWT token
- 驗證失敗回傳 401

### JWT Token

- 使用 `python-jose` 套件產生
- Payload 包含 `sub`（username）和 `exp`（過期時間 7 天）
- Secret key 存在 `.env`（`AUTH_SECRET_KEY`）

### API 保護

- 新增 `get_current_user` dependency，解析並驗證 token
- 套用到需要保護的路由（`/cards`、`/spider` 相關端點）

### 不需要保護的後端端點

- `/health`、`/config`
- `/api/v1/ocr/*`（掃描上傳用）
- `/api/v1/cards/crop-preview`（裁切預覽，掃描流程用）

### `.env` 新增變數

```
AUTH_USERNAME=admin
AUTH_PASSWORD=（公司設定的密碼）
AUTH_SECRET_KEY=（隨機產生的密鑰）
```

## 前端設計

### LoginModal 元件

- 使用 antd-mobile 的 `Modal` + `Form` 元件（與現有風格一致）
- 帳號、密碼兩個輸入框 + 登入按鈕
- 登入失敗顯示錯誤提示
- 登入成功後關閉 Modal，頁面自動顯示內容

### ProtectedRoute 元件

- 包裹受保護的路由，檢查 localStorage 中的 token
- 有 token 且未過期 → 正常渲染頁面
- 無 token 或已過期 → 渲染頁面但彈出 LoginModal（不跳轉，保持在當前 URL）
- 登入成功後 Modal 關閉，內容自動顯示

### 首頁按鈕行為

- 點「名片管理」或「商機爬蟲」→ 未登入時先彈出 LoginModal，登入成功後再 navigate 到目標頁面
- 點「掃描上傳」→ 直接進入，不檢查

### Token 管理

- 登入成功 → `localStorage.setItem('auth_token', token)`
- `apiClient.js` 的 request interceptor 自動帶上 `Authorization: Bearer <token>`
- 收到 401 回應 → 清除 token，彈出 LoginModal

## 實作檔案清單

### 後端新增

- `backend/api/v1/auth.py` — 登入端點
- `backend/services/auth_service.py` — JWT 產生與驗證邏輯
- `backend/dependencies/auth.py` — `get_current_user` dependency

### 後端修改

- `backend/api/v1/__init__.py` 或 router 設定 — 註冊 auth router
- `backend/api/v1/card.py` — 受保護端點加上 auth dependency
- `.env` — 新增 AUTH 相關變數
- `requirements.txt` — 新增 `python-jose`、`passlib`

### 前端新增

- `frontend/src/components/LoginModal.js` — 登入彈窗元件
- `frontend/src/components/ProtectedRoute.js` — 路由保護元件
- `frontend/src/api/auth.js` — 登入 API 呼叫
- `frontend/src/utils/auth.js` — token 存取、過期檢查工具函式

### 前端修改

- `frontend/src/App.js` — 受保護路由包裹 ProtectedRoute
- `frontend/src/utils/apiClient.js` — 啟用已註解的 token interceptor，加上 401 處理
