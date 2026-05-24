# Duplicate Card Detection Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Detect and mark duplicate business cards (same name_zh + company_name_zh), display duplicate tags in card list, and provide a comparison page for users to review and delete duplicates.

**Architecture:** Add `duplicate_group_id` (md5 hash) and `reviewed_at` fields to cards table. Backend computes hash on create/delete to maintain group state. New `/duplicates` endpoint returns grouped data. Frontend adds duplicate tags to list page and a new `DuplicateComparePage` for side-by-side review.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite, React, Antd Mobile

---

### Task 1: Database Migration Script

**Files:**
- Create: `backend/migrations/add_duplicate_fields.py`

**Step 1: Write the migration script**

```python
"""
新增重複名片偵測欄位 + 初始化既有資料

執行：
python -c "from backend.migrations.add_duplicate_fields import upgrade; upgrade()"
"""

from sqlalchemy import create_engine, text
import hashlib
import os
import sys


def compute_duplicate_group_id(name_zh, company_name_zh):
    """計算重複組 ID：md5(name_zh|company_name_zh)"""
    key = f"{name_zh or ''}|{company_name_zh or ''}"
    return hashlib.md5(key.encode('utf-8')).hexdigest()


def upgrade():
    database_url = os.getenv('DATABASE_URL', 'sqlite:///./cards.db')
    engine = create_engine(database_url)

    print("開始新增重複偵測欄位...")

    fields_to_add = [
        ("duplicate_group_id", "VARCHAR(32)", "重複組ID (md5 hash)"),
        ("reviewed_at", "DATETIME", "重複審查時間"),
    ]

    with engine.connect() as conn:
        # Step 1: 新增欄位
        for field_name, field_type, field_desc in fields_to_add:
            try:
                conn.execute(text(f"ALTER TABLE cards ADD COLUMN {field_name} {field_type}"))
                conn.commit()
                print(f"已新增欄位: {field_name} ({field_desc})")
            except Exception:
                print(f"略過欄位: {field_name}，可能已存在")

        # Step 2: 建立索引
        try:
            conn.execute(text("CREATE INDEX idx_duplicate_group_id ON cards(duplicate_group_id)"))
            conn.commit()
            print("已建立 duplicate_group_id 索引")
        except Exception:
            print("略過索引: idx_duplicate_group_id，可能已存在")

        # Step 3: 初始化既有資料的 duplicate_group_id
        print("開始初始化既有名片的重複標記...")

        # 找出所有重複組 (name_zh + company_name_zh 相同且 > 1 筆)
        result = conn.execute(text("""
            SELECT name_zh, company_name_zh, COUNT(*) as cnt
            FROM cards
            WHERE name_zh IS NOT NULL AND name_zh != ''
            GROUP BY name_zh, company_name_zh
            HAVING COUNT(*) > 1
        """))
        duplicate_groups = result.fetchall()

        updated_count = 0
        for row in duplicate_groups:
            name_zh_val = row[0]
            company_name_zh_val = row[1]
            group_id = compute_duplicate_group_id(name_zh_val, company_name_zh_val)

            conn.execute(
                text("""
                    UPDATE cards
                    SET duplicate_group_id = :group_id
                    WHERE name_zh = :name_zh
                    AND (company_name_zh = :company OR (company_name_zh IS NULL AND :company IS NULL) OR (company_name_zh = '' AND :company = ''))
                """),
                {"group_id": group_id, "name_zh": name_zh_val, "company": company_name_zh_val}
            )
            updated_count += row[2]

        conn.commit()
        print(f"初始化完成：{len(duplicate_groups)} 組重複，共 {updated_count} 張名片已標記")

    print("重複偵測欄位新增完成")


def downgrade():
    print("SQLite 不方便直接 DROP COLUMN。")
    print("如需回退，建議先還原資料庫備份。")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()
```

**Step 2: Run the migration**

```bash
cd /data1/165/ocr_v2/manage_card
python -c "from backend.migrations.add_duplicate_fields import upgrade; upgrade()"
```

Expected: 欄位新增成功，約 259 組重複被標記。

**Step 3: Verify migration result**

```bash
sqlite3 cards.db "SELECT COUNT(DISTINCT duplicate_group_id) FROM cards WHERE duplicate_group_id IS NOT NULL;"
sqlite3 cards.db "SELECT COUNT(*) FROM cards WHERE duplicate_group_id IS NOT NULL;"
```

Expected: ~259 groups, ~562 cards marked.

**Step 4: Commit**

```bash
git add backend/migrations/add_duplicate_fields.py
git commit -m "feat: add duplicate detection migration script"
```

---

### Task 2: Backend Model & Schema Updates

**Files:**
- Modify: `backend/models/card.py:66-71` (add columns before `__table_args__`)
- Modify: `backend/models/card.py:129` (add fields to Card pydantic model)
- Modify: `backend/schemas/card.py:128-130` (add fields to CardResponse)

**Step 1: Add ORM columns to CardORM**

In `backend/models/card.py`, after line 65 (`classified_at` field), before `__table_args__`:

```python
    # 重複偵測欄位
    duplicate_group_id = Column(String(32), index=True)  # md5(name_zh|company_name_zh)
    reviewed_at = Column(DateTime)                        # 重複審查時間
```

**Step 2: Add fields to Card pydantic model**

In `backend/models/card.py`, after line 129 (`classified_at` field), before `model_config`:

```python
    # 重複偵測欄位
    duplicate_group_id: Optional[str] = None
    reviewed_at: Optional[datetime.datetime] = None
```

**Step 3: Add fields to CardResponse schema**

In `backend/schemas/card.py`, after line 128 (`classified_at` field), before `class Config`:

```python
    duplicate_group_id: Optional[str] = None
    duplicate_count: Optional[int] = None
    reviewed_at: Optional[datetime] = None
```

**Step 4: Commit**

```bash
git add backend/models/card.py backend/schemas/card.py
git commit -m "feat: add duplicate_group_id and reviewed_at to card model/schema"
```

---

### Task 3: Backend Service — Duplicate Group Logic

**Files:**
- Modify: `backend/services/card_service.py`

**Step 1: Add hash utility and imports**

At the top of `card_service.py`, add `import hashlib` to existing imports. Add helper function after imports:

```python
import hashlib

def compute_duplicate_group_id(name_zh: str, company_name_zh: str) -> str:
    """計算重複組 ID：md5(name_zh|company_name_zh)"""
    key = f"{name_zh or ''}|{company_name_zh or ''}"
    return hashlib.md5(key.encode('utf-8')).hexdigest()
```

**Step 2: Add `update_duplicate_group` helper**

Add after `compute_duplicate_group_id`:

```python
def update_duplicate_group(db: Session, name_zh: str, company_name_zh: str):
    """更新指定 name_zh + company_name_zh 組合的重複標記"""
    if not name_zh:
        return

    group_id = compute_duplicate_group_id(name_zh, company_name_zh)

    # 找出同組的所有名片
    query = db.query(CardORM).filter(
        CardORM.name_zh == name_zh,
    )
    if company_name_zh:
        query = query.filter(CardORM.company_name_zh == company_name_zh)
    else:
        query = query.filter(or_(CardORM.company_name_zh.is_(None), CardORM.company_name_zh == ""))

    cards_in_group = query.all()

    if len(cards_in_group) > 1:
        # 多於一張 → 全部標記 duplicate_group_id，清除 reviewed_at
        for card in cards_in_group:
            card.duplicate_group_id = group_id
            card.reviewed_at = None
    else:
        # 只有一張或零張 → 清除標記
        for card in cards_in_group:
            card.duplicate_group_id = None
            card.reviewed_at = None
```

**Step 3: Modify `create_card()` (line 437)**

After `db.refresh(db_card)` (line 441), add duplicate group update:

```python
def create_card(db: Session, card: Card) -> dict:
    db_card = CardORM(**card.model_dump(exclude_unset=True))
    db.add(db_card)
    db.commit()
    db.refresh(db_card)

    # 更新重複組標記
    update_duplicate_group(db, db_card.name_zh, db_card.company_name_zh)
    db.commit()
    db.refresh(db_card)

    # 轉換為字典格式，處理datetime序列化
    card_dict = Card.model_validate(db_card).model_dump()
    for key in card_dict:
        if hasattr(card_dict[key], 'isoformat'):
            card_dict[key] = card_dict[key].isoformat()

    return card_dict
```

**Step 4: Modify `delete_card()` (line 480)**

Save name/company before deleting, then update the group:

```python
def delete_card(db: Session, card_id: int) -> bool:
    db_card = db.query(CardORM).filter(CardORM.id == card_id).first()
    if not db_card:
        return False

    # 記住 name/company 以便刪除後更新重複組
    name_zh = db_card.name_zh
    company_name_zh = db_card.company_name_zh

    try:
        db.delete(db_card)
        db.commit()

        # 更新同組剩餘名片的重複標記
        update_duplicate_group(db, name_zh, company_name_zh)
        db.commit()

        return True
    except Exception as e:
        db.rollback()
        print(f"刪除名片錯誤: {e}")
        return False
```

**Step 5: Add `get_duplicate_groups()` function**

```python
def get_duplicate_groups(db: Session, skip: int = 0, limit: int = 1) -> Tuple[List[dict], int]:
    """取得待處理的重複組別（組內至少有一張 reviewed_at 為 NULL）"""

    # 找出所有有 duplicate_group_id 且組內有未審查名片的組
    subquery = db.query(
        CardORM.duplicate_group_id,
    ).filter(
        CardORM.duplicate_group_id.isnot(None),
        CardORM.reviewed_at.is_(None),
    ).group_by(
        CardORM.duplicate_group_id,
    ).subquery()

    # 取得總組數
    total_groups = db.query(func.count()).select_from(subquery).scalar()

    # 取得分頁的組 ID 列表
    group_ids_query = db.query(subquery.c.duplicate_group_id).offset(skip).limit(limit)
    group_ids = [row[0] for row in group_ids_query.all()]

    groups = []
    for group_id in group_ids:
        cards = db.query(CardORM).filter(
            CardORM.duplicate_group_id == group_id
        ).order_by(CardORM.created_at.asc()).all()

        if cards:
            card_dicts = []
            for card in cards:
                card_dict = Card.model_validate(card).model_dump()
                card_dict['id'] = card.id
                for key in card_dict:
                    if hasattr(card_dict[key], 'isoformat'):
                        card_dict[key] = card_dict[key].isoformat()
                card_dicts.append(card_dict)

            groups.append({
                "group_id": group_id,
                "name_zh": cards[0].name_zh,
                "company_name_zh": cards[0].company_name_zh or "",
                "cards": card_dicts,
                "count": len(cards),
            })

    return groups, total_groups
```

**Step 6: Add `review_duplicate_group()` function**

```python
def review_duplicate_group(db: Session, group_id: str) -> bool:
    """標記該重複組為已審查（全部保留）"""
    cards = db.query(CardORM).filter(
        CardORM.duplicate_group_id == group_id
    ).all()

    if not cards:
        return False

    now = datetime.datetime.utcnow()
    for card in cards:
        card.reviewed_at = now

    db.commit()
    return True
```

**Step 7: Modify `get_cards_paginated()` — add `duplicate` status filter**

After the existing `filter_status` block (around line 254), add:

```python
    elif filter_status == "duplicate":
        query = query.filter(CardORM.duplicate_group_id.isnot(None))
```

**Step 8: Modify `_card_to_dict()` helper or equivalent — add `duplicate_count`**

In the card-to-dict conversion used by `get_cards_paginated()`, after building `card_dict`, add duplicate_count lookup. Find where individual cards are serialized in the paginated results (around line 260-280) and add:

```python
# 在 card_dict 中加入 duplicate_count
if card_orm.duplicate_group_id:
    dup_count = db.query(func.count(CardORM.id)).filter(
        CardORM.duplicate_group_id == card_orm.duplicate_group_id
    ).scalar()
    card_dict['duplicate_count'] = dup_count
else:
    card_dict['duplicate_count'] = 0
```

Note: For performance, consider batch-loading duplicate counts for all cards in the page at once rather than N+1 queries. Pre-load with:

```python
# 在分頁查詢後，批次取得重複數量
group_ids = list(set(c.duplicate_group_id for c in cards_page if c.duplicate_group_id))
if group_ids:
    dup_counts = dict(
        db.query(CardORM.duplicate_group_id, func.count(CardORM.id))
        .filter(CardORM.duplicate_group_id.in_(group_ids))
        .group_by(CardORM.duplicate_group_id)
        .all()
    )
else:
    dup_counts = {}

# 在序列化每張卡片時
card_dict['duplicate_count'] = dup_counts.get(card_orm.duplicate_group_id, 0)
```

**Step 9: Commit**

```bash
git add backend/services/card_service.py
git commit -m "feat: add duplicate group detection logic in card service"
```

---

### Task 4: Backend API — Duplicate Endpoints

**Files:**
- Modify: `backend/api/v1/card.py`

**Step 1: Add import**

At the top of `card.py`, add `get_duplicate_groups` and `review_duplicate_group` to the imports from card_service:

```python
from backend.services.card_service import (
    ...,
    get_duplicate_groups,
    review_duplicate_group,
)
```

**Step 2: Add `GET /duplicates` endpoint**

Add before the `GET /` endpoint (before line 174), because FastAPI matches routes top-down and `/duplicates` must match before `/{card_id}`:

```python
@router.get("/duplicates")
def list_duplicate_groups(
    skip: int = Query(0, ge=0, description="跳過組數"),
    limit: int = Query(1, ge=1, le=50, description="每次取幾組"),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """取得待處理的重複名片組別"""
    try:
        groups, total_groups = get_duplicate_groups(db, skip=skip, limit=limit)
        return ResponseHandler.success(
            data={
                "groups": groups,
                "total_groups": total_groups,
                "current_index": skip,
            },
            message="取得重複組別成功"
        )
    except Exception as e:
        logger.error(f"取得重複組別失敗: {str(e)}")
        return ResponseHandler.error(
            message="取得重複組別失敗",
            error=e,
            status_code=400
        )


@router.post("/duplicates/{group_id}/review")
def review_group(
    group_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """標記重複組為已審查（全部保留）"""
    try:
        success = review_duplicate_group(db, group_id)
        if not success:
            return ResponseHandler.error(
                message=f"找不到重複組 {group_id}",
                status_code=404
            )
        return ResponseHandler.success(message="已標記為全部保留")
    except Exception as e:
        logger.error(f"標記審查失敗: {str(e)}")
        return ResponseHandler.error(
            message="標記審查失敗",
            error=e,
            status_code=400
        )
```

**Step 3: Modify DELETE endpoint (line 878) — add image file deletion and duplicate group update**

In `remove_card()`, before calling `delete_card()`, get the card's image paths and delete files:

```python
@router.delete("/{card_id}")
def remove_card(card_id: int, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    try:
        card = get_card(db, card_id)
        if not card:
            return ResponseHandler.error(
                message=f"找不到ID為 {card_id} 的名片",
                status_code=404
            )

        # 刪除相關圖片檔案
        image_fields = ['front_image_path', 'back_image_path',
                        'front_cropped_image_path', 'back_cropped_image_path']
        for field in image_fields:
            path = card.get(field)
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    logger.info(f"已刪除圖片: {path}")
                except Exception as e:
                    logger.warning(f"刪除圖片失敗 {path}: {e}")

        if not delete_card(db, card_id):
            return ResponseHandler.error(
                message="刪除名片失敗",
                status_code=400
            )

        invalidate_card_stats_cache()
        return ResponseHandler.success(
            message="名片刪除成功"
        )
    except Exception as e:
        logger.error(f"刪除名片失敗: {str(e)}")
        return ResponseHandler.error(
            message="刪除名片失敗",
            error=e,
            status_code=400
        )
```

Note: `os` should already be imported in `card.py`. If not, add `import os`.

**Step 4: Modify POST /cards/ endpoint (line 509)**

After the card is created (around line 640-645 where `create_card()` is called), the duplicate group is already handled by the modified `create_card()` in card_service. No additional changes needed in the API endpoint.

**Step 5: Verify status filter passthrough**

Confirm that the `status` parameter value `"duplicate"` is correctly passed to `get_cards_paginated()` as `filter_status`. Check line 199 — it already passes `filter_status=status`, so the new `elif filter_status == "duplicate"` in the service will work automatically.

**Step 6: Commit**

```bash
git add backend/api/v1/card.py
git commit -m "feat: add duplicate group API endpoints"
```

---

### Task 5: Frontend — CardManagerPage Duplicate Tags & Filter

**Files:**
- Modify: `frontend/src/pages/CardManagerPage.js`

**Step 1: Add duplicate count to stats display**

The `globalStats` object likely has `total`, `normal`, `problem`. Add a `duplicate` count. Find where `globalStats` is set (from the stats API response) and check if we need to add a duplicate count endpoint, or compute it from the card list data.

Simple approach: use the existing card data. After loading cards, count those with `duplicate_group_id != null`.

**Step 2: Add duplicate filter button**

After the "有問題" button (line 1271), add:

```jsx
<Button
  color={filterStatus === 'duplicate' ? 'warning' : 'default'}
  fill={filterStatus === 'duplicate' ? 'solid' : 'outline'}
  size="small"
  onClick={() => setFilterStatus('duplicate')}
>
  重複
</Button>
```

**Step 3: Add duplicate tag to card rendering**

In `renderCardItem()`, after the industry category tag block (around line 1047), add:

```jsx
{card.duplicate_group_id && (
  <Tag
    color="danger"
    style={{ fontSize: '12px', marginTop: '4px', cursor: 'pointer' }}
    onClick={(e) => {
      e.stopPropagation();
      navigate(`/cards/duplicates/${card.duplicate_group_id}`);
    }}
  >
    重複 x{card.duplicate_count || '?'}
  </Tag>
)}
```

Make sure `useNavigate` is imported (it likely already is).

**Step 4: Commit**

```bash
git add frontend/src/pages/CardManagerPage.js
git commit -m "feat: add duplicate tags and filter to card manager page"
```

---

### Task 6: Frontend — DuplicateComparePage

**Files:**
- Create: `frontend/src/pages/DuplicateComparePage.js`
- Create: `frontend/src/pages/DuplicateComparePage.css`
- Modify: `frontend/src/App.js:88-95` (add route)

**Step 1: Add route in App.js**

After line 93 (CardDetailPage route), add:

```jsx
<Route path="/cards/duplicates/:groupId" element={<ProtectedRoute><DuplicateComparePage /></ProtectedRoute>} />
```

Add import at top:

```jsx
import DuplicateComparePage from './pages/DuplicateComparePage';
```

**Step 2: Create DuplicateComparePage.css**

```css
.duplicate-compare-page {
  min-height: 100vh;
  background: #f5f5f5;
  padding-bottom: 80px;
}

.duplicate-header {
  background: #fff;
  padding: 16px;
  border-bottom: 1px solid #eee;
  position: sticky;
  top: 0;
  z-index: 10;
}

.duplicate-header-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.duplicate-header-title {
  font-size: 16px;
  font-weight: bold;
  color: #333;
}

.duplicate-group-info {
  font-size: 14px;
  color: #666;
  padding: 0 16px;
  margin-top: 8px;
}

.duplicate-card-list {
  padding: 12px 16px;
}

.duplicate-card-item {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.duplicate-card-item.selected-for-delete {
  border: 2px solid #ff4d4f;
  background: #fff2f0;
}

.duplicate-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.duplicate-card-id {
  font-size: 13px;
  color: #999;
}

.duplicate-card-date {
  font-size: 12px;
  color: #bbb;
}

.duplicate-card-images {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.duplicate-card-images img {
  width: 48%;
  max-height: 150px;
  object-fit: contain;
  border-radius: 8px;
  border: 1px solid #eee;
  background: #fafafa;
}

.duplicate-card-info {
  font-size: 14px;
  color: #333;
  line-height: 1.6;
}

.duplicate-card-info .label {
  color: #999;
  margin-right: 4px;
}

.duplicate-bottom-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: #fff;
  border-top: 1px solid #eee;
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  z-index: 10;
}

.duplicate-nav-buttons {
  display: flex;
  gap: 8px;
}

.duplicate-action-buttons {
  display: flex;
  gap: 8px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #999;
}

.empty-state-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-state-text {
  font-size: 16px;
}
```

**Step 3: Create DuplicateComparePage.js**

```jsx
import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button, Checkbox, Dialog, Toast, NavBar, SpinLoading } from 'antd-mobile';
import { LeftOutline, RightOutline } from 'antd-mobile-icons';
import apiClient from '../utils/apiClient';
import './DuplicateComparePage.css';

const API_BASE = process.env.REACT_APP_API_BASE || '';

function getImageUrl(path) {
  if (!path) return null;
  if (path.startsWith('card_data/')) return `${API_BASE}/static/${path}`;
  if (path.startsWith('output/card_images/')) {
    const filename = path.split('/').pop();
    return `${API_BASE}/static/uploads/${filename}`;
  }
  return `${API_BASE}/static/${path}`;
}

export default function DuplicateComparePage() {
  const { groupId } = useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [groups, setGroups] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [totalGroups, setTotalGroups] = useState(0);
  const [selectedForDelete, setSelectedForDelete] = useState(new Set());
  const [deleting, setDeleting] = useState(false);

  const loadGroup = useCallback(async (index) => {
    setLoading(true);
    setSelectedForDelete(new Set());
    try {
      const res = await apiClient.get(`/api/v1/cards/duplicates`, {
        params: { skip: index, limit: 1 }
      });
      if (res.data?.success && res.data.data) {
        setGroups(res.data.data.groups || []);
        setTotalGroups(res.data.data.total_groups || 0);
        setCurrentIndex(index);
      }
    } catch (err) {
      Toast.show({ content: '載入失敗', icon: 'fail' });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // If groupId is provided, we start at index 0
    // (could enhance later to find the specific group's index)
    loadGroup(0);
  }, [loadGroup]);

  const currentGroup = groups[0];

  const toggleSelect = (cardId) => {
    setSelectedForDelete(prev => {
      const next = new Set(prev);
      if (next.has(cardId)) next.delete(cardId);
      else next.add(cardId);
      return next;
    });
  };

  const handleDelete = async () => {
    if (selectedForDelete.size === 0) return;

    if (currentGroup && selectedForDelete.size >= currentGroup.cards.length) {
      Toast.show({ content: '不能刪除全部名片，至少保留一張', icon: 'fail' });
      return;
    }

    const confirmed = await Dialog.confirm({
      content: `確定要刪除已選的 ${selectedForDelete.size} 張名片嗎？此操作無法復原。`,
      confirmText: '確定刪除',
      cancelText: '取消',
    });

    if (!confirmed) return;

    setDeleting(true);
    try {
      for (const cardId of selectedForDelete) {
        await apiClient.delete(`/api/v1/cards/${cardId}`);
      }
      Toast.show({ content: `已刪除 ${selectedForDelete.size} 張名片`, icon: 'success' });

      // Reload current group
      await loadGroup(currentIndex);

      // If no more groups at this index, check if there are earlier ones
      // The group list shifts after deletion
    } catch (err) {
      Toast.show({ content: '刪除失敗', icon: 'fail' });
    } finally {
      setDeleting(false);
    }
  };

  const handleReview = async () => {
    if (!currentGroup) return;
    try {
      await apiClient.post(`/api/v1/cards/duplicates/${currentGroup.group_id}/review`);
      Toast.show({ content: '已標記全部保留', icon: 'success' });
      // Move to next group (same index since this one is now reviewed)
      await loadGroup(currentIndex);
    } catch (err) {
      Toast.show({ content: '操作失敗', icon: 'fail' });
    }
  };

  const goNext = () => {
    if (currentIndex < totalGroups - 1) {
      loadGroup(currentIndex + 1);
    }
  };

  const goPrev = () => {
    if (currentIndex > 0) {
      loadGroup(currentIndex - 1);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <SpinLoading color='primary' />
      </div>
    );
  }

  if (totalGroups === 0 || !currentGroup) {
    return (
      <div className="duplicate-compare-page">
        <NavBar onBack={() => navigate('/cards')}>重複名片</NavBar>
        <div className="empty-state">
          <div className="empty-state-icon">&#10003;</div>
          <div className="empty-state-text">所有重複組已處理完畢</div>
          <Button
            color="primary"
            style={{ marginTop: '20px' }}
            onClick={() => navigate('/cards')}
          >
            返回名片列表
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="duplicate-compare-page">
      {/* Header */}
      <NavBar onBack={() => navigate('/cards')}>
        重複名片 ({currentIndex + 1}/{totalGroups})
      </NavBar>

      <div className="duplicate-group-info">
        {currentGroup.name_zh} / {currentGroup.company_name_zh || '(無公司)'} — 共 {currentGroup.count} 張
      </div>

      {/* Card List */}
      <div className="duplicate-card-list">
        {currentGroup.cards.map((card) => (
          <div
            key={card.id}
            className={`duplicate-card-item ${selectedForDelete.has(card.id) ? 'selected-for-delete' : ''}`}
          >
            <div className="duplicate-card-header">
              <span className="duplicate-card-id">#{card.id}</span>
              <span className="duplicate-card-date">
                建立於 {card.created_at ? new Date(card.created_at).toLocaleDateString('zh-TW') : '未知'}
              </span>
            </div>

            {/* Images */}
            <div className="duplicate-card-images">
              {card.front_cropped_image_path || card.front_image_path ? (
                <img
                  src={getImageUrl(card.front_cropped_image_path || card.front_image_path)}
                  alt="正面"
                  onError={(e) => { e.target.style.display = 'none'; }}
                />
              ) : (
                <div style={{ width: '48%', height: '100px', background: '#f5f5f5', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#ccc' }}>
                  無正面圖
                </div>
              )}
              {card.back_cropped_image_path || card.back_image_path ? (
                <img
                  src={getImageUrl(card.back_cropped_image_path || card.back_image_path)}
                  alt="背面"
                  onError={(e) => { e.target.style.display = 'none'; }}
                />
              ) : (
                <div style={{ width: '48%', height: '100px', background: '#f5f5f5', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#ccc' }}>
                  無背面圖
                </div>
              )}
            </div>

            {/* Card Info */}
            <div className="duplicate-card-info">
              {card.position_zh && <div><span className="label">職稱:</span>{card.position_zh}</div>}
              {card.mobile_phone && <div><span className="label">手機:</span>{card.mobile_phone}</div>}
              {card.email && <div><span className="label">Email:</span>{card.email}</div>}
              {card.company_phone1 && <div><span className="label">電話:</span>{card.company_phone1}</div>}
            </div>

            {/* Delete Checkbox */}
            <div style={{ marginTop: '12px', textAlign: 'right' }}>
              <Checkbox
                checked={selectedForDelete.has(card.id)}
                onChange={() => toggleSelect(card.id)}
              >
                選擇刪除
              </Checkbox>
            </div>
          </div>
        ))}
      </div>

      {/* Bottom Bar */}
      <div className="duplicate-bottom-bar">
        <div className="duplicate-nav-buttons">
          <Button
            size="small"
            disabled={currentIndex === 0}
            onClick={goPrev}
          >
            <LeftOutline /> 上一組
          </Button>
        </div>
        <div className="duplicate-action-buttons">
          <Button
            size="small"
            color="primary"
            fill="outline"
            onClick={handleReview}
          >
            全部保留
          </Button>
          <Button
            size="small"
            color="danger"
            disabled={selectedForDelete.size === 0 || deleting}
            loading={deleting}
            onClick={handleDelete}
          >
            刪除已選({selectedForDelete.size})
          </Button>
        </div>
        <div className="duplicate-nav-buttons">
          <Button
            size="small"
            disabled={currentIndex >= totalGroups - 1}
            onClick={goNext}
          >
            下一組 <RightOutline />
          </Button>
        </div>
      </div>
    </div>
  );
}
```

**Step 4: Commit**

```bash
git add frontend/src/pages/DuplicateComparePage.js frontend/src/pages/DuplicateComparePage.css frontend/src/App.js
git commit -m "feat: add duplicate comparison page"
```

---

### Task 7: Integration Testing & Verification

**Step 1: Run migration on backup first**

```bash
cp cards.db cards_backup_$(date +%Y%m%d_%H%M%S).db
python -c "from backend.migrations.add_duplicate_fields import upgrade; upgrade()"
```

**Step 2: Verify database state**

```bash
sqlite3 cards.db "SELECT COUNT(DISTINCT duplicate_group_id) as groups, COUNT(*) as cards FROM cards WHERE duplicate_group_id IS NOT NULL;"
sqlite3 cards.db "SELECT duplicate_group_id, name_zh, company_name_zh, COUNT(*) FROM cards WHERE duplicate_group_id IS NOT NULL GROUP BY duplicate_group_id ORDER BY COUNT(*) DESC LIMIT 5;"
```

**Step 3: Start backend and test API**

```bash
python main.py &
# Test duplicates endpoint
curl -s http://localhost:8006/api/v1/cards/duplicates?skip=0&limit=1 -H "Authorization: Bearer <token>" | python -m json.tool
```

**Step 4: Start frontend and verify UI**

```bash
cd frontend && npm start
```

Manual checks:
- [ ] Card list page shows "重複 xN" tags on duplicate cards
- [ ] "重複" filter button works in status filter
- [ ] Clicking duplicate tag navigates to comparison page
- [ ] Comparison page shows cards in the group with images
- [ ] "全部保留" marks group as reviewed, moves to next
- [ ] Selecting and deleting cards works with confirmation dialog
- [ ] After deleting down to 1 card, group disappears and moves to next
- [ ] "所有重複組已處理完畢" shown when all groups are done
- [ ] Navigation between groups works (上一組/下一組)

**Step 5: Final commit**

```bash
git add -A
git commit -m "feat: complete duplicate card detection feature"
```
