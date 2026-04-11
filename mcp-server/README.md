<!-- Language: English | 繁體中文 -->

```
   ╔══════════════════════════════════════════════╗
   ║          CardOCR MCP Server                  ║
   ║                                              ║
   ║   AI Agent ──MCP──▶ 名片系統 + 商機爬蟲      ║
   ╚══════════════════════════════════════════════╝
```

<p align="center">
  <i>讓任何 MCP 相容的 AI Agent 安全存取名片 OCR 系統與商機爬蟲資料</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/MCP-1.27.0-green?logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xMiAyTDIgN2wxMCA1IDEwLTV6Ii8+PC9zdmc+" alt="MCP">
  <img src="https://img.shields.io/badge/transport-Streamable%20HTTP-orange" alt="Transport">
  <img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="License">
</p>

---

## 這個專案解決什麼問題？

```
傳統方式：
  用戶 → 打開網頁 → 登入 → 手動操作 → 看結果

MCP 方式：
  用戶 → 跟 AI 說話 → AI 自動呼叫 MCP Tool → 回答問題
```

名片 OCR 系統和商機爬蟲有豐富的資料，但只能透過網頁操作。
這個 MCP Server 把核心功能暴露為 7 個結構化 Tool，
讓 AI Agent（OpenClaw、Claude Desktop、Cursor 等）能直接存取。

◈ **不改動現有系統** — MCP Server 獨立運行，透過 HTTP 呼叫現有 FastAPI  
◈ **資料一次拿齊** — 回傳完整欄位，AI 自行決定顯示多少  
◈ **手機友好** — Tool description 指導 AI 預設只顯示 5 個關鍵欄位  

---

## 架構

```
                         ┌─────────────────────┐
  AI Agent (外網)        │   Cloudflare Tunnel  │
  OpenClaw / Claude      │   (HTTPS 加密通道)    │
        │                └──────────┬──────────┘
        │                           │
        ▼                           ▼
  ┌──────────┐    HTTP     ┌──────────────────┐    HTTP     ┌──────────────┐
  │ MCP 協議  │ ─────────▶ │  MCP Server      │ ─────────▶ │ FastAPI 後端  │
  │          │            │  port 8007        │            │ port 8006    │
  └──────────┘            │  (本專案)          │            │ (現有，不動)  │
                          └──────────────────┘            └──────────────┘
                                  │
                                  ├──▶ /api/v1/cards/*     (名片 CRUD)
                                  ├──▶ /api/v1/ocr/*       (OCR 辨識)
                                  └──▶ /spider/api/*       (商機爬蟲)
```

---

## Tools 一覽

### 名片 OCR

| Tool | 說明 | 類型 |
|------|------|------|
| `cardocr_scan_card` | 掃描名片圖片 → OCR 辨識 → 回傳 25 個結構化欄位 | 唯讀 |
| `cardocr_save_card` | 確認後將名片資料存入資料庫 | 寫入 |

### 客戶資料池

| Tool | 說明 | 類型 |
|------|------|------|
| `cardocr_search_contacts` | 依姓名/公司/電話/Email 模糊搜尋 | 唯讀 |
| `cardocr_get_contact_detail` | 查詢單一客戶完整 25 欄位 | 唯讀 |
| `cardocr_find_contacts_for_org` | 查某機關/公司我們認識誰 | 唯讀 |

### 商機標案

| Tool | 說明 | 類型 |
|------|------|------|
| `cardocr_get_opportunities` | 查看標案列表，可篩 BU/優先級/預算 | 唯讀 |
| `cardocr_get_opportunity_matches` | 查某標案匹配到的客戶人脈 | 唯讀 |

---

## 顯示策略

所有 Tool 回傳 **完整資料**，但透過 description 指導 AI 分層呈現：

| 場景 | 預設顯示 | 追問展開 |
|------|---------|---------|
| 搜尋/查看客戶 | 姓名、公司、職稱、手機、Email | 部門、地址、LINE、英文名… |
| 掃描名片 | 姓名、公司、職稱、手機、Email | 其餘 20 個欄位 |
| 商機標案 | 標案名、機關、預算、評分、截止日 | 技術標籤、類別、URL… |
| 標案匹配人脈 | 姓名、機關、關係程度、匹配分數 | 匹配原因、備註… |

> 資料一次拿齊，顯示分層呈現，追問不重複查詢。

---

## Quick Start

### 1. 安裝依賴

```bash
cd mcp-server
pip install -r requirements.txt
```

### 2. 設定環境變數

```bash
cp .env.example .env
# 編輯 .env 填入後端連線資訊
```

`.env` 設定項：

| 變數 | 說明 | 預設值 |
|------|------|--------|
| `MCP_PORT` | MCP Server 監聽端口 | `8007` |
| `BACKEND_URL` | FastAPI 後端位址 | `http://localhost:8006` |
| `BACKEND_USERNAME` | 登入帳號 | — |
| `BACKEND_PASSWORD` | 登入密碼 | — |
| `PROJECT_DIR` | 專案根目錄路徑 | — |

### 3. 啟動

```bash
# 前景執行（開發除錯）
python server.py

# 背景執行
bash start_mcp.sh
```

### 4. 驗證

```bash
# 檢查是否監聽
lsof -i :8007

# 測試 MCP 握手
curl -s -X POST http://localhost:8007/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

### 5. 外網存取（Cloudflare Tunnel）

```bash
# 安裝 cloudflared
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb

# 啟動快速隧道
cloudflared tunnel --url http://localhost:8007
# → 會給你一個 https://xxx.trycloudflare.com URL
```

---

## 在 AI Agent 中使用

### OpenClaw

在 OpenClaw 設定中加入 MCP Server：

```
MCP Endpoint: https://your-tunnel-url.trycloudflare.com/mcp
Transport: Streamable HTTP
```

### Claude Desktop

`claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "cardocr": {
      "url": "https://your-tunnel-url.trycloudflare.com/mcp"
    }
  }
}
```

### 使用範例

```
用戶：幫我找國泰的聯絡人
AI  ：→ cardocr_search_contacts(query="國泰")
      找到 30 筆：
      1. 林政憲 — 國泰金控 區塊鏈架構師 📱0983-803-251
      2. 劉鍾仁 — 國泰創投 投資副總 📱886-938-182-383
      ...

用戶：有幾個高優先商機？
AI  ：→ cardocr_get_opportunities(priority="high")
      共 12 個高優先商機，總預算 NT$5.8億
      1. 🔴 智慧監控系統 — 故宮博物院 ⭐86分
      2. 🔴 資安防護平台 — 高雄港務 ⭐86分
      ...

用戶：第一個標案我們認識誰？
AI  ：→ cardocr_get_opportunity_matches(tender_id="...")
      匹配到 3 位人脈：
      🔥 劉建國 — 行政院（熟識）
      ...
```

---

## 目錄結構

```
mcp-server/
├── server.py                # MCP Server 進入點，註冊 7 個 tools
├── api_client.py            # FastAPI HTTP client（JWT 自動管理��
├── config.py                # 環境變數讀取
├── tools/
│   ├── ocr_tools.py         # scan_card, save_card
│   ├── contact_tools.py     # search_contacts, get_contact_detail, find_contacts_for_org
│   └── opportunity_tools.py # get_opportunities, get_opportunity_matches
├── requirements.txt
├── .env                     # 環境變數設定
└── start_mcp.sh             # 背景啟動腳本
```

---

## 技術細節

### 認證流程

```
MCP Server 啟動
    │
    ├── 第一次呼叫 Tool
    │       │
    │       ▼
    │   POST /api/v1/auth/login
    │       │
    │       ▼
    │   取得 JWT Token（快取 2.5 天）
    │       │
    │       ▼
    │   後續請求自動帶 Bearer Token
    │
    └── Token 過期 → 自動重新登入
```

### 現有端點對應

| MCP Tool | 內部呼叫 |
|----------|---------|
| `cardocr_scan_card` | `POST /api/v1/ocr/image` → `POST /api/v1/ocr/parse-fields` |
| `cardocr_save_card` | `POST /api/v1/cards` (multipart form-data) |
| `cardocr_search_contacts` | `GET /api/v1/cards?search=&use_pagination=true` |
| `cardocr_get_contact_detail` | `GET /api/v1/cards/{id}` |
| `cardocr_find_contacts_for_org` | `GET /api/v1/cards?company=` |
| `cardocr_get_opportunities` | `GET /spider/api/report` + MCP 層篩選 |
| `cardocr_get_opportunity_matches` | `GET /spider/api/tender/{id}` |

### Tool Annotations

| Tool | readOnly | destructive | idempotent |
|------|----------|-------------|------------|
| scan_card | ✓ | ✗ | ✓ |
| save_card | ✗ | ✗ | ✗ |
| search_contacts | ✓ | ✗ | ✓ |
| get_contact_detail | ✓ | ✗ | ✓ |
| find_contacts_for_org | ✓ | ✗ | ✓ |
| get_opportunities | ✓ | ✗ | ✓ |
| get_opportunity_matches | ✓ | ✗ | ✓ |

---

## 已知限制

| 限制 | 說明 | 解法 |
|------|------|------|
| 快速隧道 URL 不固定 | cloudflared 重啟後 URL 會變 | 改用命名隧道（需 Cloudflare 帳號） |
| 無 MCP 層認證 | 任何人知道 URL 就能呼叫 | 加 Bearer token 驗證或 Cloudflare Access |
| scan_card 需要 base64 | 大圖片 base64 很長 | 建議壓縮後再傳，或用 image_url |
| 依賴後端存活 | FastAPI 掛了 MCP Tool 全部失敗 | 加健康檢查 Tool 或 watchdog |

---

## License

MIT
