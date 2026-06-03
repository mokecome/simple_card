# 批次名片上傳 OCR 辨識 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Scope:** 本期（V1）僅實作**單面批次上傳**（每張圖 = 一張名片正面）。正反面配對功能保留至 V2 實作；後端 API 設計保留向前相容（接受 `back_index`，但 V1 前端固定送 `null`）。

**Goal:** 讓使用者一次上傳最多 50 張名片圖片（單面），上傳完即可離開頁面，OCR 在背景處理並自動將每張名片存入資料庫（標記為「待確認」），使用者之後可在名片管理頁批次審核確認。

**Architecture:**
- **前端**：新增 `BatchUploadPage`，使用者上傳多張圖片後以縮圖列表顯示，可逐張刪除不要的，然後一鍵上傳。上傳完成立即得到 task_id，可離開頁面。（V2 將加入單面/雙面切換與分組調整 UI。）
- **後端**：`POST /api/v1/ocr/batch-upload` 接收檔案 → 寫入磁碟 → 用 `asyncio.create_task()` fire-and-forget 啟動背景 OCR（共用 `OCRService._llm_semaphore` 的 `Semaphore(2)` 並行限制）→ 立刻回傳 task_id。背景任務逐組 OCR 完成後**立刻寫入資料庫**，標記為「未確認」狀態。API 結構保留 `back_index` 欄位，V1 一律為 null。
- **審核流程**：名片管理頁新增「待確認」篩選按鈕，卡片顯示「未確認」標籤；同一批次的名片共享 `batch_id`，可進入批次審核頁（`/cards/batch/:batchId`）逐張編輯確認或一鍵全部確認。

**Tech Stack:** React + Antd Mobile（前端）、FastAPI + asyncio（後端）、既有 `OCRService` + `CardEnhancementService` + `TaskManager`、SQLAlchemy ORM

---

## 設計總覽

### 關鍵決策

| 項目 | V1 決策 |
|------|--------|
| 一次上傳上限 | **50 張圖片**（超過直接拒絕，要求重選） |
| 分組模式 | **固定單面**（每張圖 = 一張名片正面），雙面配對延至 V2 |
| 手動調整 | **僅支援刪除不要的圖片**（左滑或點 ✕） |
| 後端並行 | `asyncio.create_task()` fire-and-forget，共用 `Semaphore(2)` |
| 等待時間 | 使用者只需等「上傳」（30-60s），OCR 在背景跑不用守 |
| 結果落地 | C 方案：每張 OCR 完成立刻存入 DB（標記 `confirmed_at = NULL`） |
| 審核入口 | 名片管理頁新增「待確認 (N)」篩選按鈕 |
| 確認方式 | 逐張確認 + 全部確認雙軌 |
| 進度恢復 | localStorage 存 task_id，回來自動恢復 |
| 多任務限制 | 同一瀏覽器一次一個批次；不同瀏覽器各自獨立 |
| 入口位置 | 首頁卡片 + 名片管理頁 NavBar 右上角按鈕 |

### 使用者流程（V1 — 單面批次）

```
1. 進入 /batch-upload（從首頁卡片或名片管理頁右上角）
   ↓
2. 選圖（最多 50 張，每張 = 一張名片正面）
   ↓
3. 預覽縮圖列表，刪除不要的圖（可選）
   ↓
4. 點「開始辨識」→ 前端上傳所有圖（必須留在頁面）
   ↓
5. 後端寫入磁碟 → 啟動背景任務 → 回傳 task_id
   ↓
6. 前端彈出提示：「已收到 N 張，可離開頁面，OCR 將在背景處理」
   localStorage 存 task_id
   ↓
7. 使用者可離開頁面、切 APP、鎖螢幕（後端繼續跑）
   後端逐張 OCR → 每張完成立刻寫入 DB（batch_id=X, confirmed_at=NULL）
   ↓
8. 使用者回名片管理頁 → 看到「待確認 (N)」篩選
   → 點進去看到 N 張未確認名片，標籤顯示「未確認」
   → 點任一張可進入「批次審核頁」 /cards/batch/:batchId
   ↓
9. 批次審核頁：
   - 逐張檢查/編輯 → 點「✓ 確認」（confirmed_at 設為現在時間）
   - 不要的 → 點「✗ 刪除」
   - OCR 都準的話 → 底部「全部確認剩餘 N 張」一鍵搞定
   ↓
10. 已確認的名片從「待確認」消失，進入正常名片庫
```

### V2 規劃（下一期）

下期將加入正反面配對功能：
- 全域開關切換單面/雙面模式
- 雙面模式下自動兩兩配對
- 三種手動調整：組內 ⇄ 交換正反、跨組點選兩張互換、左滑刪除整組
- 後端 API 已預留 `back_index` 欄位，V2 只需前端改造

### API 設計

| Endpoint | 用途 |
|----------|------|
| `POST /api/v1/ocr/batch-upload` | 上傳圖片 + 分組資訊，建立背景任務後立即回傳 task_id |
| `GET /api/v1/ocr/batch-status/{task_id}` | 查詢任務進度（用於前端輪詢，主要在使用者還在頁面時用） |
| `GET /api/v1/cards/?confirmed=false` | 列出未確認名片（沿用既有 filter 參數） |
| `GET /api/v1/cards/batch/{batch_id}` | 取得特定批次的所有名片 |
| `PUT /api/v1/cards/{card_id}/confirm` | 確認單張名片（設定 confirmed_at） |
| `POST /api/v1/cards/batch/{batch_id}/confirm-all` | 一鍵確認批次內所有未確認名片 |

### 資料庫變更

```python
# Card 新增兩個欄位
batch_id      = Column(String(64), nullable=True, index=True)   # UUID，同批次共享
confirmed_at  = Column(DateTime, nullable=True, index=True)     # null = 未確認
```

---

## Task 1: 資料庫 — Card 模型加入 batch_id 和 confirmed_at

**Files:**
- Modify: `backend/models/card.py` (新增兩個欄位)
- Modify: `backend/schemas/card.py` (response schema 加入欄位)
- Create: `backend/migrations/add_batch_confirm_fields.py`

### Step 1: 修改 Card ORM

```python
# backend/models/card.py 在 CardORM 內新增
batch_id = Column(String(64), nullable=True, index=True)
confirmed_at = Column(DateTime, nullable=True, index=True)

# Pydantic Card 也對應加入
batch_id: Optional[str] = None
confirmed_at: Optional[datetime] = None
```

### Step 2: 撰寫 migration script

```python
# backend/migrations/add_batch_confirm_fields.py
"""新增 batch_id 與 confirmed_at 欄位到 cards 表"""
import sqlite3
from backend.core.config import DATABASE_URL

def migrate():
    db_path = DATABASE_URL.replace("sqlite:///", "")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE cards ADD COLUMN batch_id VARCHAR(64)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_batch_id ON cards(batch_id)")
        cursor.execute("ALTER TABLE cards ADD COLUMN confirmed_at DATETIME")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_confirmed_at ON cards(confirmed_at)")
        conn.commit()
        print("Migration successful")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print("Columns already exist, skipping")
        else:
            raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
```

### Step 3: 更新 CardResponse schema

```python
# backend/schemas/card.py 在 CardResponse 新增
batch_id: Optional[str] = None
confirmed_at: Optional[str] = None  # ISO datetime str
```

### Step 4: 執行 migration + 驗證

```bash
python backend/migrations/add_batch_confirm_fields.py
sqlite3 cards.db "PRAGMA table_info(cards);" | grep -E "batch_id|confirmed_at"
# 應該看到兩個新欄位
```

### Step 5: Commit

```bash
git add backend/models/card.py backend/schemas/card.py backend/migrations/add_batch_confirm_fields.py
git commit -m "feat: add batch_id and confirmed_at fields to Card model"
```

---

## Task 2: 後端 — 批次上傳 API（fire-and-forget + C 方案）

**Files:**
- Modify: `backend/api/v1/ocr.py` (新增 batch-upload 和 batch-status 端點)
- Modify: `backend/services/task_manager.py` (擴充支援儲存 batch_id)

### Step 1: 擴充 TaskManager 儲存 batch_id

```python
# task_manager.py - Task 類別新增
class Task:
    def __init__(self, task_id: str, total: int, batch_id: str = None):
        # ... 既有屬性 ...
        self.batch_id = batch_id  # 新增

    def to_dict(self) -> Dict:
        return {
            # ... 既有欄位 ...
            "batch_id": self.batch_id  # 新增
        }
```

### Step 2: 新增 batch-upload 端點（fire-and-forget）

```python
# backend/api/v1/ocr.py 新增

import os, json, uuid, asyncio
from typing import List
from datetime import datetime
from fastapi import Form
from sqlalchemy.orm import Session
from backend.services.task_manager import task_manager
from backend.services.card_enhancement_service import CardEnhancementService
from backend.core.config import UPLOAD_DIR
from backend.dependencies.db import get_db
from backend.models.card import Card as CardORM
from backend.services.card_service import create_card

MAX_BATCH_FILES = 50

@router.post("/batch-upload")
async def batch_upload(
    files: List[UploadFile] = File(...),
    groups: str = Form(...),  # JSON: [{"front_index": 0, "back_index": 1}, ...]
):
    """
    批次上傳名片圖片並啟動背景 OCR 處理。
    
    使用者只需等檔案上傳完成，回傳 task_id 後可立刻離開頁面。
    OCR 在背景進行，每張完成立刻存入 DB（標記 confirmed_at=NULL）。
    """
    # 驗證
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="請至少上傳一張圖片")
    if len(files) > MAX_BATCH_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"一次最多支援 {MAX_BATCH_FILES} 張圖片，目前上傳了 {len(files)} 張"
        )
    try:
        group_list = json.loads(groups)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="groups 格式錯誤，需為 JSON array")
    if not group_list:
        raise HTTPException(status_code=400, detail="請至少建立一組名片")

    # 產生批次 ID 和目錄
    batch_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_dir = os.path.join(UPLOAD_DIR, f"batch_{timestamp}_{batch_id[:8]}")
    os.makedirs(batch_dir, exist_ok=True)

    # 儲存所有檔案到磁碟
    saved_paths = []
    for i, f in enumerate(files):
        content = await f.read()
        ext = os.path.splitext(f.filename or "")[1].lower() or ".jpg"
        if ext not in [".jpg", ".jpeg", ".png"]:
            raise HTTPException(status_code=400, detail=f"不支援的檔案格式：{ext}")
        path = os.path.join(batch_dir, f"{i:03d}{ext}")
        with open(path, "wb") as fp:
            fp.write(content)
        saved_paths.append(path)

    # 建立背景任務
    task_id = task_manager.create_task(total=len(group_list), batch_id=batch_id)

    # Fire-and-forget：用 create_task 在同一個 event loop 啟動背景處理
    # 這樣 OCR 呼叫會自動共用 OCRService._llm_semaphore 的並行限制
    asyncio.create_task(
        _process_batch_ocr(task_id, batch_id, saved_paths, group_list)
    )

    # 立刻回傳，不等 OCR
    return {
        "success": True,
        "task_id": task_id,
        "batch_id": batch_id,
        "total_groups": len(group_list),
        "message": f"已收到 {len(files)} 張圖片，OCR 將在背景處理"
    }


async def _process_batch_ocr(task_id: str, batch_id: str, saved_paths: list, group_list: list):
    """背景處理：逐組 OCR + 立刻寫入 DB（C 方案）"""
    from backend.core.database import SessionLocal
    
    task_manager.start_task(task_id)
    ocr_svc = OCRService()

    for idx, group in enumerate(group_list):
        if task_manager.is_cancelled(task_id):
            break

        db = SessionLocal()
        try:
            front_path = saved_paths[group["front_index"]]
            back_index = group.get("back_index")
            back_path = saved_paths[back_index] if back_index is not None else None

            # 正面 OCR + 解析
            front_fields, front_ocr_text = await _ocr_and_parse(ocr_svc, front_path, "front")

            # 反面 OCR + 解析（合併到 front_fields，僅補空欄位）
            back_ocr_text = ""
            if back_path:
                back_fields, back_ocr_text = await _ocr_and_parse(ocr_svc, back_path, "back")
                for key, val in back_fields.items():
                    if val and not front_fields.get(key):
                        front_fields[key] = val

            # 立刻寫入 DB，標記為未確認
            name_zh = front_fields.get("name_zh", "").strip() or f"未命名_{idx+1}"
            card_data = CardORM(
                name_zh=name_zh,
                name_en=front_fields.get("name_en", ""),
                company_name_zh=front_fields.get("company_name_zh", ""),
                company_name_en=front_fields.get("company_name_en", ""),
                position_zh=front_fields.get("position_zh", ""),
                position_en=front_fields.get("position_en", ""),
                position1_zh=front_fields.get("position1_zh", ""),
                position1_en=front_fields.get("position1_en", ""),
                department1_zh=front_fields.get("department1_zh", ""),
                department1_en=front_fields.get("department1_en", ""),
                department2_zh=front_fields.get("department2_zh", ""),
                department2_en=front_fields.get("department2_en", ""),
                department3_zh=front_fields.get("department3_zh", ""),
                department3_en=front_fields.get("department3_en", ""),
                mobile_phone=front_fields.get("mobile_phone", ""),
                company_phone1=front_fields.get("company_phone1", ""),
                company_phone2=front_fields.get("company_phone2", ""),
                email=front_fields.get("email", ""),
                line_id=front_fields.get("line_id", ""),
                company_address1_zh=front_fields.get("company_address1_zh", ""),
                company_address1_en=front_fields.get("company_address1_en", ""),
                company_address2_zh=front_fields.get("company_address2_zh", ""),
                company_address2_en=front_fields.get("company_address2_en", ""),
                note1=front_fields.get("note1", ""),
                note2=front_fields.get("note2", ""),
                front_image_path=front_path,
                back_image_path=back_path,
                front_ocr_text=front_ocr_text,
                back_ocr_text=back_ocr_text,
                batch_id=batch_id,
                confirmed_at=None  # 標記為未確認
            )
            create_card(db, card_data)
            task_manager.update_progress(task_id, success=True)

        except Exception as e:
            logger.error(f"批次 OCR 處理第 {idx+1} 組失敗: {e}")
            task_manager.update_progress(task_id, success=False)
        finally:
            db.close()

    task_manager.complete_task(task_id)


async def _ocr_and_parse(ocr_svc, image_path: str, side: str):
    """單面 OCR + 欄位解析"""
    with open(image_path, "rb") as f:
        content = f.read()
    ocr_text = await ocr_svc.ocr_image(content)
    parsed = await ocr_svc.parse_ocr_to_fields(ocr_text, side)
    return parsed, ocr_text


@router.get("/batch-status/{task_id}")
async def batch_status(task_id: str):
    """查詢批次 OCR 任務進度"""
    status = task_manager.get_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="任務不存在")
    return {"success": True, "data": status}
```

### Step 3: 測試後端

```bash
python main.py
# 用 curl 測試 fire-and-forget 行為
time curl -X POST http://localhost:8006/api/v1/ocr/batch-upload \
  -F "files=@test1.jpg" -F "files=@test2.jpg" \
  -F 'groups=[{"front_index":0,"back_index":null},{"front_index":1,"back_index":null}]'
# 應該幾秒內就回傳，不會等 OCR
```

### Step 4: Commit

```bash
git add backend/api/v1/ocr.py backend/services/task_manager.py
git commit -m "feat: add batch upload API with fire-and-forget OCR and direct DB persistence"
```

---

## Task 3: 後端 — 待確認名片相關 API

**Files:**
- Modify: `backend/api/v1/card.py` (新增 batch 相關端點)
- Modify: `backend/services/card_service.py` (支援 confirmed_at 篩選)

### Step 1: 修改 get_cards_paginated 支援 confirmed 篩選

```python
# card_service.py - 在 get_cards_paginated 加入
def get_cards_paginated(db, ..., confirmed: Optional[bool] = None):
    query = db.query(CardORM)
    # ... 既有篩選 ...
    if confirmed is True:
        query = query.filter(CardORM.confirmed_at.isnot(None))
    elif confirmed is False:
        query = query.filter(CardORM.confirmed_at.is_(None))
    # ...
```

### Step 2: 新增 batch 相關端點

```python
# backend/api/v1/card.py 新增

from datetime import datetime

@router.get("/batch/{batch_id}")
async def get_batch_cards(
    batch_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """取得特定批次的所有名片（按建立時間排序）"""
    cards = db.query(CardORM).filter(
        CardORM.batch_id == batch_id
    ).order_by(CardORM.created_at).all()
    
    return ResponseHandler.success(data={
        "batch_id": batch_id,
        "total": len(cards),
        "confirmed_count": sum(1 for c in cards if c.confirmed_at),
        "items": [card_to_dict(c) for c in cards]
    })


@router.put("/{card_id}/confirm")
async def confirm_card(
    card_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """確認單張名片"""
    card = db.query(CardORM).filter(CardORM.id == card_id).first()
    if not card:
        return ResponseHandler.error(message="名片不存在", status_code=404)
    card.confirmed_at = datetime.now()
    db.commit()
    invalidate_card_stats_cache()
    return ResponseHandler.success(message="已確認")


@router.post("/batch/{batch_id}/confirm-all")
async def confirm_batch_all(
    batch_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """一鍵確認批次內所有未確認名片"""
    now = datetime.now()
    count = db.query(CardORM).filter(
        CardORM.batch_id == batch_id,
        CardORM.confirmed_at.is_(None)
    ).update({CardORM.confirmed_at: now})
    db.commit()
    invalidate_card_stats_cache()
    return ResponseHandler.success(
        data={"confirmed_count": count},
        message=f"已確認 {count} 張名片"
    )
```

### Step 3: 修改 GET /cards/ 支援 confirmed 篩選

```python
# card.py - get_cards 端點加入 query parameter
@router.get("/")
async def get_cards(
    # ... 既有參數 ...
    confirmed: Optional[bool] = Query(None, description="是否已確認"),
    ...
):
    # 傳給 get_cards_paginated
```

### Step 4: 測試

```bash
# 確認 API 工作
curl -H "Authorization: Bearer XXX" "http://localhost:8006/api/v1/cards/?confirmed=false"
curl -H "Authorization: Bearer XXX" "http://localhost:8006/api/v1/cards/batch/{batch_id}"
```

### Step 5: Commit

```bash
git add backend/api/v1/card.py backend/services/card_service.py
git commit -m "feat: add batch review API endpoints (get batch, confirm card, confirm all)"
```

---

## Task 4: 前端 — BatchUploadPage 單面批次上傳

**Files:**
- Create: `frontend/src/pages/BatchUploadPage.js`
- Modify: `frontend/src/App.js` (新增路由 + 首頁卡片)

### Step 1: 建立 BatchUploadPage 結構（含恢復進度）

```jsx
// frontend/src/pages/BatchUploadPage.js
import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Button, Space, Card, Toast, NavBar, Loading,
  Image, Dialog, ProgressBar
} from 'antd-mobile';
import { AddOutline, CloseOutline } from 'antd-mobile-icons';
import axios from 'axios';
import { API_BASE_URL } from '../config';

const MAX_FILES = 50;

const STAGE = {
  SELECT: 'select',      // 選圖 + 預覽
  UPLOADING: 'uploading', // 上傳中
  DONE: 'done'           // 上傳完成，可離開
};

const BatchUploadPage = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  const [stage, setStage] = useState(STAGE.SELECT);
  const [images, setImages] = useState([]); // [{file, preview, id}]
  const [uploadProgress, setUploadProgress] = useState(0);

  // 進入頁面時，檢查是否有未完成的任務
  useEffect(() => {
    const stored = localStorage.getItem('batch_upload_task');
    if (!stored) return;

    const { taskId } = JSON.parse(stored);
    axios.get(`${API_BASE_URL}/ocr/batch-status/${taskId}`)
      .then(res => {
        const status = res.data.data.status;
        if (status === 'processing' || status === 'pending') {
          Dialog.confirm({
            content: '你有一個批次任務正在背景處理中，前往名片管理頁查看？',
            onConfirm: () => navigate('/cards?confirmed=false')
          });
        } else {
          localStorage.removeItem('batch_upload_task');
        }
      })
      .catch(() => localStorage.removeItem('batch_upload_task'));
  }, [navigate]);

  // 元件卸載時釋放縮圖記憶體
  useEffect(() => {
    return () => {
      images.forEach(img => URL.revokeObjectURL(img.preview));
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
```

### Step 2: 選圖 + 50 張上限驗證

```jsx
  const handleSelectFiles = useCallback((e) => {
    const newFiles = Array.from(e.target.files);
    e.target.value = '';

    if (!newFiles.length) return;

    // 檔案格式驗證
    const invalidFiles = newFiles.filter(f => !['image/jpeg', 'image/png'].includes(f.type));
    if (invalidFiles.length) {
      Toast.show({
        content: `${invalidFiles.length} 張不是支援的格式（僅支援 JPG、PNG）`,
        position: 'center'
      });
      return;
    }

    // 50 張上限檢查
    if (images.length + newFiles.length > MAX_FILES) {
      Toast.show({
        content: `最多支援 ${MAX_FILES} 張，目前已選 ${images.length} 張，這次想新增 ${newFiles.length} 張，請重新選擇`,
        position: 'center',
        duration: 3000
      });
      return;
    }

    const newImages = newFiles.map((file, i) => ({
      file,
      preview: URL.createObjectURL(file),
      id: `img_${Date.now()}_${i}`
    }));

    setImages(prev => [...prev, ...newImages]);
  }, [images]);

  // 刪除單張圖
  const handleRemoveImage = useCallback((imageId) => {
    setImages(prev => {
      const target = prev.find(img => img.id === imageId);
      if (target) URL.revokeObjectURL(target.preview);
      return prev.filter(img => img.id !== imageId);
    });
  }, []);
```

### Step 3: 上傳（fire-and-forget 對接）

```jsx
  const handleStartUpload = useCallback(async () => {
    if (!images.length) {
      Toast.show({ content: '請先選取圖片', position: 'center' });
      return;
    }

    setStage(STAGE.UPLOADING);
    setUploadProgress(0);

    try {
      const formData = new FormData();
      images.forEach(img => formData.append('files', img.file));

      // V1：每張圖一組正面（back_index 一律 null，預留 V2 配對）
      const groupPayload = images.map((_, i) => ({
        front_index: i,
        back_index: null
      }));
      formData.append('groups', JSON.stringify(groupPayload));

      const res = await axios.post(`${API_BASE_URL}/ocr/batch-upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 300000, // 5 分鐘
        onUploadProgress: (e) => {
          setUploadProgress(Math.round((e.loaded * 100) / e.total));
        }
      });

      if (res.data.success) {
        localStorage.setItem('batch_upload_task', JSON.stringify({
          taskId: res.data.task_id,
          batchId: res.data.batch_id,
          totalGroups: res.data.total_groups,
          startedAt: new Date().toISOString()
        }));
        setStage(STAGE.DONE);
      }
    } catch (error) {
      Toast.show({
        content: `上傳失敗: ${error.response?.data?.detail || error.message}`,
        position: 'center'
      });
      setStage(STAGE.SELECT);
    }
  }, [images]);
```

### Step 4: JSX 渲染（三個階段）

```jsx
  return (
    <div style={{ minHeight: '100vh', background: '#f5f5f5' }}>
      <NavBar onBack={() => navigate(-1)}>批次上傳辨識</NavBar>

      {/* ===== 階段一：選圖 + 預覽 ===== */}
      {stage === STAGE.SELECT && (
        <div style={{ padding: 16 }}>
          <Card style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 14, color: '#666', lineHeight: 1.6 }}>
              📦 每張圖會被視為一張名片正面，最多可選 {MAX_FILES} 張<br/>
              💡 雙面名片功能將在下一期推出
            </div>
          </Card>

          <div style={{ marginBottom: 8, color: '#666', fontSize: 13 }}>
            已選取 <strong>{images.length}</strong> / {MAX_FILES} 張
          </div>

          <Button
            block
            color="primary"
            size="large"
            onClick={() => fileInputRef.current?.click()}
            disabled={images.length >= MAX_FILES}
            style={{ marginBottom: 16 }}
          >
            <AddOutline /> 選取名片圖片
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png"
            multiple
            onChange={handleSelectFiles}
            style={{ display: 'none' }}
          />

          {/* 縮圖網格（3 欄 grid） */}
          {images.length > 0 && (
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: 8,
              marginBottom: 16
            }}>
              {images.map((img, i) => (
                <div
                  key={img.id}
                  style={{
                    position: 'relative',
                    aspectRatio: '1',
                    borderRadius: 8,
                    overflow: 'hidden',
                    background: '#fff'
                  }}
                >
                  <Image src={img.preview} width="100%" height="100%" fit="cover" />
                  <div style={{
                    position: 'absolute', top: 4, left: 4,
                    background: 'rgba(0,0,0,0.5)', color: '#fff',
                    borderRadius: 4, padding: '2px 6px', fontSize: 11
                  }}>
                    #{i + 1}
                  </div>
                  <div
                    onClick={() => handleRemoveImage(img.id)}
                    style={{
                      position: 'absolute', top: 4, right: 4,
                      background: 'rgba(255,77,79,0.9)', color: '#fff',
                      width: 24, height: 24, borderRadius: '50%',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      cursor: 'pointer'
                    }}
                  >
                    <CloseOutline fontSize={14} />
                  </div>
                </div>
              ))}
            </div>
          )}

          {images.length > 0 && (
            <Button
              block
              color="success"
              size="large"
              onClick={handleStartUpload}
            >
              開始辨識（共 {images.length} 張名片）
            </Button>
          )}
        </div>
      )}

      {/* ===== 階段二：上傳中 ===== */}
      {stage === STAGE.UPLOADING && (
        <div style={{ padding: 16, textAlign: 'center' }}>
          <Loading color="primary" />
          <div style={{ margin: '16px 0', fontSize: 16 }}>正在上傳圖片...</div>
          <ProgressBar percent={uploadProgress} />
          <div style={{ marginTop: 8, color: '#999' }}>{uploadProgress}%</div>
          <div style={{ marginTop: 16, color: '#ff9500', fontSize: 13 }}>
            ⚠️ 上傳中請勿離開頁面
          </div>
        </div>
      )}

      {/* ===== 階段三：上傳完成（可離開） ===== */}
      {stage === STAGE.DONE && (
        <div style={{ padding: 16 }}>
          <Card>
            <div style={{ textAlign: 'center', padding: '24px 0' }}>
              <div style={{ fontSize: 48, color: '#52c41a' }}>✓</div>
              <div style={{ fontSize: 18, fontWeight: 'bold', marginTop: 8 }}>
                已收到 {images.length} 張名片！
              </div>
              <div style={{ color: '#666', marginTop: 16, lineHeight: 1.6 }}>
                OCR 將在背景處理（約 {Math.ceil(images.length * 0.3)} - {Math.ceil(images.length * 0.6)} 分鐘）<br/>
                你可以離開這個頁面、關掉瀏覽器或鎖螢幕走人<br/>
                完成後可在「名片管理」→「待確認」查看結果
              </div>
            </div>
          </Card>
          <Space direction="vertical" block style={{ marginTop: 16 }}>
            <Button
              block
              color="primary"
              size="large"
              onClick={() => navigate('/cards?confirmed=false')}
            >
              前往名片管理查看
            </Button>
            <Button
              block
              size="large"
              onClick={() => {
                images.forEach(img => URL.revokeObjectURL(img.preview));
                setImages([]);
                setStage(STAGE.SELECT);
                localStorage.removeItem('batch_upload_task');
              }}
            >
              再上傳一批
            </Button>
          </Space>
        </div>
      )}
    </div>
  );
};

export default BatchUploadPage;
```

### Step 5: 新增路由與首頁入口

```jsx
// frontend/src/App.js
import BatchUploadPage from './pages/BatchUploadPage';

// Routes 內新增
<Route path="/batch-upload" element={<BatchUploadPage />} />

// Home component 內，在「開始掃描」後新增卡片
<div className="feature-card feature-card--batch" onClick={() => navigate('/batch-upload')}>
  <div className="feature-icon">📦</div>
  <div className="feature-text">
    <div className="feature-name">批次上傳辨識</div>
    <div className="feature-desc">一次上傳最多 50 張名片，OCR 背景處理</div>
  </div>
  <span className="feature-arrow">›</span>
</div>
```

### Step 6: 手動測試

```
1. 訪問 /batch-upload
2. 選 5 張圖 → 確認縮圖網格顯示 5 張，每張有 # 序號
3. 點某張的 ✕ → 刪除該張
4. 一次嘗試選 51 張 → 應該被擋下，提示重選
5. 選擇 .pdf 或 .gif → 應該擋下，提示格式錯誤
6. 點「開始辨識」→ 看上傳進度條 → 完成後看到綠色完成畫面
7. 上傳完成後重新整理 → 應提示「有任務正在處理」
```

### Step 8: Commit

```bash
git add frontend/src/pages/BatchUploadPage.js frontend/src/App.js
git commit -m "feat: add batch upload page with grouping, manual adjustment, and fire-and-forget upload"
```

---

## Task 5: 前端 — 名片管理頁的「待確認」篩選 + NavBar 入口

**Files:**
- Modify: `frontend/src/pages/CardManagerPage.js` (新增待確認篩選、NavBar 按鈕、未確認標籤)

### Step 1: NavBar 加入批次上傳入口

在 `CardManagerPage.js:1176` 的 NavBar 修改：

```jsx
<NavBar
  onBack={() => navigate('/')}
  right={
    <Button
      size="mini"
      color="primary"
      fill="none"
      onClick={() => navigate('/batch-upload')}
    >
      <AddOutline /> 批次上傳
    </Button>
  }
>
  名片管理
</NavBar>
```

### Step 2: 新增「待確認」篩選按鈕

在現有的篩選按鈕區域（line 1262 附近）增加：

```jsx
<Button
  size="small"
  color={filterStatus === 'pending' ? 'primary' : 'default'}
  fill={filterStatus === 'pending' ? 'solid' : 'outline'}
  onClick={() => setFilterStatus('pending')}
>
  待確認
  {pendingCount > 0 && (
    <Badge content={pendingCount} style={{ marginLeft: 4 }} />
  )}
</Button>
```

對應在 `loadCards` 中傳入 `confirmed=false` 參數當 filterStatus === 'pending'。

### Step 3: 卡片上顯示「未確認」標籤

在每張名片的渲染區塊（line 837 附近）加：

```jsx
{!card.confirmed_at && (
  <Tag color="warning" style={{ marginLeft: 4 }}>未確認</Tag>
)}
```

### Step 4: 點擊未確認名片 → 跳到批次審核頁

```jsx
onClick={() => {
  if (!card.confirmed_at && card.batch_id) {
    navigate(`/cards/batch/${card.batch_id}`);
  } else {
    navigate(`/cards/${card.id}`);
  }
}}
```

### Step 5: 支援 URL query string 預設篩選

```jsx
// 進入頁面時讀 query string
useEffect(() => {
  const params = new URLSearchParams(location.search);
  if (params.get('confirmed') === 'false') {
    setFilterStatus('pending');
  }
}, [location.search]);
```

### Step 6: Commit

```bash
git add frontend/src/pages/CardManagerPage.js
git commit -m "feat: add pending filter, unconfirmed tag, and batch upload entry in card manager"
```

---

## Task 6: 前端 — 批次審核頁

**Files:**
- Create: `frontend/src/pages/BatchReviewPage.js`
- Modify: `frontend/src/App.js` (新增路由)

### Step 1: 建立 BatchReviewPage

```jsx
// frontend/src/pages/BatchReviewPage.js
import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Card, Button, NavBar, Toast, Tag, Image, Collapse,
  Input, Dialog, FloatingBubble, Loading
} from 'antd-mobile';
import { CheckOutline, DeleteOutline, EditSOutline } from 'antd-mobile-icons';
import axios from 'axios';
import { API_BASE_URL } from '../config';

const KEY_FIELDS = [
  { key: 'name_zh', label: '姓名' },
  { key: 'company_name_zh', label: '公司' },
  { key: 'position_zh', label: '職位' },
  { key: 'mobile_phone', label: '手機' },
  { key: 'email', label: 'Email' },
  { key: 'name_en', label: 'English Name' },
  { key: 'company_name_en', label: 'Company' },
  { key: 'position_en', label: 'Position' },
];

const BatchReviewPage = () => {
  const navigate = useNavigate();
  const { batchId } = useParams();
  const [loading, setLoading] = useState(true);
  const [batchData, setBatchData] = useState({ total: 0, confirmed_count: 0, items: [] });
  const [confirming, setConfirming] = useState(null); // card id being confirmed

  useEffect(() => {
    loadBatchCards();
  }, [batchId]);

  const loadBatchCards = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_BASE_URL}/cards/batch/${batchId}`);
      if (res.data.success) {
        setBatchData(res.data.data);
      }
    } catch (error) {
      Toast.show({ content: '載入失敗', position: 'center' });
    } finally {
      setLoading(false);
    }
  };

  // 編輯欄位（本地狀態，未即時送 API）
  const handleEditField = useCallback((cardId, field, value) => {
    setBatchData(prev => ({
      ...prev,
      items: prev.items.map(c => c.id === cardId ? { ...c, [field]: value, _dirty: true } : c)
    }));
  }, []);

  // 確認單張（先儲存編輯，再確認）
  // **重要**：`PUT /cards/{id}` 是 full-replace 端點。送出時必須包含全部欄位
  // （不只 KEY_FIELDS），否則未送出的欄位會被清空。實作請參考 BatchReviewPage.js
  // 的 SKIP_KEYS：以 card 物件展開後排除非欄位 key（如 id、batch_id、_dirty、image_url 等）。
  const handleConfirmCard = useCallback(async (card) => {
    setConfirming(card.id);
    try {
      // 如有編輯，先儲存
      if (card._dirty) {
        const formData = new FormData();
        KEY_FIELDS.forEach(({ key }) => {
          formData.append(key, card[key] || '');
        });
        await axios.put(`${API_BASE_URL}/cards/${card.id}`, formData);
      }
      // 確認
      await axios.put(`${API_BASE_URL}/cards/${card.id}/confirm`);
      await loadBatchCards();
      Toast.show({ content: '已確認', position: 'center' });
    } catch (error) {
      Toast.show({ content: '確認失敗', position: 'center' });
    } finally {
      setConfirming(null);
    }
  }, []);

  // 全部確認
  const handleConfirmAll = useCallback(() => {
    const unconfirmedCount = batchData.items.filter(c => !c.confirmed_at).length;
    Dialog.confirm({
      content: `確認剩餘 ${unconfirmedCount} 張名片？確認後將進入正式名片庫。`,
      onConfirm: async () => {
        try {
          await axios.post(`${API_BASE_URL}/cards/batch/${batchId}/confirm-all`);
          await loadBatchCards();
          Toast.show({ content: `已確認 ${unconfirmedCount} 張`, position: 'center' });
        } catch (error) {
          Toast.show({ content: '操作失敗', position: 'center' });
        }
      }
    });
  }, [batchData, batchId]);

  // 刪除名片
  const handleDelete = useCallback((card) => {
    Dialog.confirm({
      content: `確定刪除「${card.name_zh}」？`,
      onConfirm: async () => {
        try {
          await axios.delete(`${API_BASE_URL}/cards/${card.id}`);
          await loadBatchCards();
        } catch (error) {
          Toast.show({ content: '刪除失敗', position: 'center' });
        }
      }
    });
  }, []);

  if (loading) {
    return <div style={{ textAlign: 'center', padding: 40 }}><Loading /></div>;
  }

  const unconfirmedCount = batchData.items.filter(c => !c.confirmed_at).length;

  return (
    <div style={{ minHeight: '100vh', background: '#f5f5f5', paddingBottom: 80 }}>
      <NavBar onBack={() => navigate('/cards')}>批次審核</NavBar>

      <div style={{ padding: 16 }}>
        <Card style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 14 }}>
            已確認 <strong style={{ color: '#52c41a' }}>{batchData.confirmed_count}</strong>
            {' / '}
            共 <strong>{batchData.total}</strong> 張
          </div>
        </Card>

        {batchData.items.map(card => (
          <Card key={card.id} style={{ marginBottom: 8, opacity: card.confirmed_at ? 0.6 : 1 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                  <strong style={{ fontSize: 15 }}>{card.name_zh || '(未命名)'}</strong>
                  {card.confirmed_at ? (
                    <Tag color="success">✓ 已確認</Tag>
                  ) : (
                    <Tag color="warning">未確認</Tag>
                  )}
                </div>
                <div style={{ color: '#666', fontSize: 13 }}>
                  <div>{card.company_name_zh}</div>
                  <div>{card.position_zh}</div>
                  <div>{card.mobile_phone} {card.email}</div>
                </div>
              </div>
              {card.front_image_path && (
                <Image src={card.front_image_url} width={60} height={60} fit="cover" style={{ borderRadius: 4 }} />
              )}
            </div>

            {!card.confirmed_at && (
              <>
                <Collapse style={{ marginTop: 8 }}>
                  <Collapse.Panel key="edit" title={<><EditSOutline /> 編輯欄位</>}>
                    {KEY_FIELDS.map(({ key, label }) => (
                      <div key={key} style={{ marginBottom: 8 }}>
                        <div style={{ fontSize: 12, color: '#999' }}>{label}</div>
                        <Input
                          value={card[key] || ''}
                          onChange={val => handleEditField(card.id, key, val)}
                        />
                      </div>
                    ))}
                  </Collapse.Panel>
                </Collapse>

                <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                  <Button
                    block
                    size="small"
                    color="primary"
                    loading={confirming === card.id}
                    onClick={() => handleConfirmCard(card)}
                  >
                    <CheckOutline /> 確認
                  </Button>
                  <Button
                    size="small"
                    color="danger"
                    fill="outline"
                    onClick={() => handleDelete(card)}
                  >
                    <DeleteOutline />
                  </Button>
                </div>
              </>
            )}
          </Card>
        ))}
      </div>

      {/* 底部固定的「全部確認」按鈕 */}
      {unconfirmedCount > 0 && (
        <div style={{
          position: 'fixed', bottom: 0, left: 0, right: 0,
          padding: 12, background: '#fff', borderTop: '1px solid #eee',
          boxShadow: '0 -2px 8px rgba(0,0,0,0.04)'
        }}>
          <Button block color="primary" size="large" onClick={handleConfirmAll}>
            ✓ 全部確認剩餘 {unconfirmedCount} 張
          </Button>
        </div>
      )}
    </div>
  );
};

export default BatchReviewPage;
```

### Step 2: 新增路由

```jsx
// App.js
import BatchReviewPage from './pages/BatchReviewPage';

<Route path="/cards/batch/:batchId" element={<ProtectedRoute><BatchReviewPage /></ProtectedRoute>} />
```

### Step 3: 整合 E2E 測試

```
完整流程驗證：
1. /batch-upload 選 5 張圖
2. 點某張的 ✕ 刪除 → 剩 4 張
3. 點「開始辨識」→ 看上傳進度條
4. 上傳完成提示「可離開」
5. 不要關頁面，直接點「前往名片管理」
6. 看到「待確認 (4)」篩選按鈕（先等 OCR 跑完，可能要等一下）
7. 點進去看到 4 張名片，標籤都是「未確認」
8. 點任一張 → 進入批次審核頁
9. 編輯第 1 張的姓名 → 點「確認」 → 變成已確認
10. 點「全部確認剩餘 3 張」 → 全部變綠
11. 回名片管理頁 → 「待確認」變 0
12. 切到「全部」→ 看到 4 張已確認名片
```

### Step 4: Commit

```bash
git add frontend/src/pages/BatchReviewPage.js frontend/src/App.js
git commit -m "feat: add batch review page with per-card and bulk confirmation"
```

---

## Task 7: 邊界處理 + 體驗打磨

**Files:**
- Modify: 所有相關檔案

### Step 1: OCR 失敗的處理

如果某張 OCR 完全失敗（API 錯誤等），仍寫入 DB 但 `note1 = "OCR失敗: <error>"`，使用者可在「待確認」看到並手動修正/刪除。

### Step 2: 重複上傳偵測

進入 `/batch-upload` 時若 localStorage 有未完成任務，提示「有一批正在處理，是否前往查看？」。

### Step 3: 上傳失敗的重試

上傳中斷 → 圖片仍在 state，使用者可直接重試而不用重選。

### Step 4: 名片管理頁未確認的徽章

NavBar 或篩選按鈕旁顯示未確認總數，幫助使用者注意到還有待處理的批次。

### Step 5: 最終 commit

```bash
git add -A
git commit -m "feat: polish batch upload UX with error handling and pending badge"
```

---

## 風險與緩解

| 風險 | 緩解措施 |
|------|---------|
| 50 張圖上傳超時 | axios timeout 設 5 分鐘；4G 網路約 60-120s 應夠用 |
| 大量圖同時 OCR 撞 OpenAI rate limit | 沿用既有 Semaphore(2)，背景任務也共用此限制 |
| 後端重啟導致進行中任務遺失 | C 方案每張立刻存 DB，已處理的不會丟；未處理的圖片仍在磁碟，可加 admin 工具重跑 |
| 使用者刪除批次內所有名片後 batch_id 變孤兒 | 不影響功能，可定期清理 |
| 手機端 50 張縮圖記憶體 | URL.createObjectURL 在元件卸載時 revoke；測試低階機表現 |
| 並發兩批次共用 Semaphore 拖慢單張掃描 | 既有限制就是 2，三人同時用最多排 1 個，可接受 |
| 部分欄位編輯導致其他欄位被覆寫 | `PUT /cards/{id}` 是 full-replace，前端必須送出全部欄位（見 `BatchReviewPage.js` SKIP_KEYS 排除清單） |

## 未來可擴展

### V2（下一期，已預留向前相容）
- **正反面配對模式**：全域開關切換單面/雙面、自動兩兩配對
- **手動分組調整**：組內 ⇄ 交換正反、跨組點選兩張互換、左滑刪除整組
- 後端 API 的 `back_index` 欄位已預留，V2 只需前端改造

### V3+
- SSE 取代 localStorage 輪詢，即時推送 OCR 進度
- 自動正反面偵測（CV 模型判斷圖片朝向）
- 拖拽排序分組（react-dnd）
- 同批次批次刪除（一鍵清空整批）
- 匯出待確認名片為 Excel 給離線確認
- Admin 介面：查看所有進行中/失敗任務、手動重跑
