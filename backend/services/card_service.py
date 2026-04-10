from backend.models.card import CardORM, Card
from sqlalchemy.orm import Session
from typing import Dict, Iterator, List, Optional, Tuple
from sqlalchemy import and_, or_, func
import datetime
import hashlib


def compute_duplicate_group_id(name_zh: str, company_name_zh: str) -> str:
    """計算重複組 ID：md5(name_zh|company_name_zh)"""
    key = f"{name_zh or ''}|{company_name_zh or ''}"
    return hashlib.md5(key.encode('utf-8')).hexdigest()


def update_duplicate_group(db: Session, name_zh: str, company_name_zh: str):
    """更新指定 name_zh + company_name_zh 組合的重複標記"""
    if not name_zh:
        return

    group_id = compute_duplicate_group_id(name_zh, company_name_zh)

    query = db.query(CardORM).filter(CardORM.name_zh == name_zh)
    if company_name_zh:
        query = query.filter(CardORM.company_name_zh == company_name_zh)
    else:
        query = query.filter(or_(CardORM.company_name_zh.is_(None), CardORM.company_name_zh == ""))

    cards_in_group = query.all()

    if len(cards_in_group) > 1:
        for card in cards_in_group:
            card.duplicate_group_id = group_id
            card.reviewed_at = None
    else:
        for card in cards_in_group:
            card.duplicate_group_id = None
            card.reviewed_at = None

def get_cards(db: Session) -> List[dict]:
    """獲取所有名片（保留舊版本兼容性）"""
    # 優化：使用批量處理減少對象創建開銷
    cards = db.query(CardORM).order_by(CardORM.created_at.desc()).all()
    result = []
    
    for card in cards:
        # 直接使用 __dict__ 避免重複驗證
        card_dict = card.__dict__.copy()
        card_dict.pop('_sa_instance_state', None)
        
        # 處理日期時間
        if card_dict.get('created_at'):
            card_dict['created_at'] = card_dict['created_at'].isoformat()
        if card_dict.get('updated_at'):
            card_dict['updated_at'] = card_dict['updated_at'].isoformat()
        if card_dict.get('classified_at'):
            card_dict['classified_at'] = card_dict['classified_at'].isoformat()

        result.append(card_dict)
    return result

def iterate_cards_for_stats(db: Session, chunk_size: int = 500) -> Iterator[Dict[str, Optional[str]]]:
    """以最小欄位集批次迭代名片，用於統計計算"""
    query = (
        db.query(
            CardORM.name_zh,
            CardORM.name_en,
            CardORM.company_name_zh,
            CardORM.company_name_en,
            CardORM.position_zh,
            CardORM.position_en,
            CardORM.position1_zh,
            CardORM.position1_en,
            CardORM.department1_zh,
            CardORM.department1_en,
            CardORM.department2_zh,
            CardORM.department2_en,
            CardORM.department3_zh,
            CardORM.department3_en,
            CardORM.mobile_phone,
            CardORM.company_phone1,
            CardORM.company_phone2,
            CardORM.email,
            CardORM.line_id,
            CardORM.industry_category
        )
        .order_by(CardORM.created_at.desc())
    )

    for row in query.yield_per(chunk_size):
        yield {
            "name_zh": row.name_zh,
            "name_en": row.name_en,
            "company_name_zh": row.company_name_zh,
            "company_name_en": row.company_name_en,
            "position_zh": row.position_zh,
            "position_en": row.position_en,
            "position1_zh": row.position1_zh,
            "position1_en": row.position1_en,
            "department1_zh": row.department1_zh,
            "department1_en": row.department1_en,
            "department2_zh": row.department2_zh,
            "department2_en": row.department2_en,
            "department3_zh": row.department3_zh,
            "department3_en": row.department3_en,
            "mobile_phone": row.mobile_phone,
            "company_phone1": row.company_phone1,
            "company_phone2": row.company_phone2,
            "email": row.email,
            "line_id": row.line_id,
            "industry_category": row.industry_category
        }

def get_cards_paginated(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    industry: Optional[str] = None,
    filter_status: Optional[str] = None,
    # 高級篩選參數
    name_zh: Optional[str] = None,
    name_en: Optional[str] = None,
    company: Optional[str] = None,
    position: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    has_phone: Optional[bool] = None,
    has_email: Optional[bool] = None,
    has_address: Optional[bool] = None,
) -> Tuple[List[dict], int]:
    """分頁獲取名片，支持搜索和過濾"""
    query = db.query(CardORM)

    # 产业分类过滤
    if industry and industry != '全部':
        query = query.filter(CardORM.industry_category == industry)

    # 搜索過濾 - 支援姓名、公司、職稱的中英文搜索
    if search:
        search_filter = or_(
            # 姓名搜索 (中英文)
            CardORM.name_zh.contains(search),
            CardORM.name_en.contains(search),
            # 公司搜索 (中英文)
            CardORM.company_name_zh.contains(search),
            CardORM.company_name_en.contains(search),
            # 職稱搜索 (中英文，支援兩個職稱欄位)
            CardORM.position_zh.contains(search),
            CardORM.position_en.contains(search),
            CardORM.position1_zh.contains(search),
            CardORM.position1_en.contains(search),
            # 聯絡資訊搜索
            CardORM.mobile_phone.contains(search),
            CardORM.email.contains(search),
            # 🔍 產業標籤搜尋（primary_label + labels 都在這欄）
            CardORM.classification_reason.contains(search),
        )
        query = query.filter(search_filter)

    # === 高級篩選 ===
    if name_zh:
        query = query.filter(CardORM.name_zh.contains(name_zh))
    if name_en:
        query = query.filter(CardORM.name_en.contains(name_en))
    if company:
        query = query.filter(or_(
            CardORM.company_name_zh.contains(company),
            CardORM.company_name_en.contains(company),
        ))
    if position:
        query = query.filter(or_(
            CardORM.position_zh.contains(position),
            CardORM.position_en.contains(position),
            CardORM.position1_zh.contains(position),
            CardORM.position1_en.contains(position),
        ))

    # 日期區間篩選
    if date_from:
        try:
            dt_from = datetime.datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(CardORM.created_at >= dt_from)
        except ValueError:
            pass
    if date_to:
        try:
            dt_to = datetime.datetime.strptime(date_to, "%Y-%m-%d") + datetime.timedelta(days=1)
            query = query.filter(CardORM.created_at < dt_to)
        except ValueError:
            pass

    # 聯絡方式篩選
    def is_empty(col):
        return or_(col.is_(None), col == "")
    def is_not_empty(col):
        return and_(col.isnot(None), col != "")

    if has_phone is True:
        query = query.filter(or_(
            is_not_empty(CardORM.mobile_phone),
            is_not_empty(CardORM.company_phone1),
            is_not_empty(CardORM.company_phone2),
        ))
    elif has_phone is False:
        query = query.filter(and_(
            is_empty(CardORM.mobile_phone),
            is_empty(CardORM.company_phone1),
            is_empty(CardORM.company_phone2),
        ))

    if has_email is True:
        query = query.filter(is_not_empty(CardORM.email))
    elif has_email is False:
        query = query.filter(is_empty(CardORM.email))

    if has_address is True:
        query = query.filter(or_(
            is_not_empty(CardORM.company_address1_zh),
            is_not_empty(CardORM.company_address2_zh),
        ))
    elif has_address is False:
        query = query.filter(and_(
            is_empty(CardORM.company_address1_zh),
            is_empty(CardORM.company_address2_zh),
        ))

    # 狀態過濾（normal / problem）
    if filter_status in ("normal", "problem"):
        # 定義「欄位是空的」的判斷（NULL 或 空字串）
        def is_empty(col):
            return or_(col.is_(None), col == "")

        # 姓名缺失（中 + 英 都空）
        name_missing = and_(
            is_empty(CardORM.name_zh),
            is_empty(CardORM.name_en),
        )

        # 公司缺失（中 + 英 都空）
        company_missing = and_(
            is_empty(CardORM.company_name_zh),
            is_empty(CardORM.company_name_en),
        )

        # 職位全空
        position_missing = and_(
            is_empty(CardORM.position_zh),
            is_empty(CardORM.position_en),
            is_empty(CardORM.position1_zh),
            is_empty(CardORM.position1_en),
        )

        # 部門全空
        department_missing = and_(
            is_empty(CardORM.department1_zh),
            is_empty(CardORM.department1_en),
            is_empty(CardORM.department2_zh),
            is_empty(CardORM.department2_en),
            is_empty(CardORM.department3_zh),
            is_empty(CardORM.department3_en),
        )

        # 職位 & 部門都沒有 → 視為缺「職位或部門」
        position_or_dept_missing = and_(position_missing, department_missing)

        # 聯絡方式缺失（手機、電話1/2、Email、Line 全空）
        contact_missing = and_(
            is_empty(CardORM.mobile_phone),
            is_empty(CardORM.company_phone1),
            is_empty(CardORM.company_phone2),
            is_empty(CardORM.email),
            is_empty(CardORM.line_id),
        )

        # 「有問題」的判斷：有任一類缺失即可
        problem_condition = or_(
            name_missing,
            company_missing,
            position_or_dept_missing,
            contact_missing,
        )

        if filter_status == "problem":
            query = query.filter(problem_condition)
        elif filter_status == "normal":
            query = query.filter(~problem_condition)
    elif filter_status == "duplicate":
        query = query.filter(CardORM.duplicate_group_id.isnot(None), CardORM.reviewed_at.is_(None))

    # 獲取總數
    total = query.count()
    
    # 分頁查詢
    cards_page = query.order_by(CardORM.created_at.desc()).offset(skip).limit(limit).all()

    # 批次取得重複數量
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

    # 轉換為字典
    result = []
    for card_orm in cards_page:
        card_dict = card_orm.__dict__.copy()
        card_dict.pop('_sa_instance_state', None)

        if card_dict.get('created_at'):
            card_dict['created_at'] = card_dict['created_at'].isoformat()
        if card_dict.get('updated_at'):
            card_dict['updated_at'] = card_dict['updated_at'].isoformat()
        if card_dict.get('classified_at'):
            card_dict['classified_at'] = card_dict['classified_at'].isoformat()
        if card_dict.get('reviewed_at'):
            card_dict['reviewed_at'] = card_dict['reviewed_at'].isoformat()

        card_dict['duplicate_count'] = dup_counts.get(card_orm.duplicate_group_id, 0)

        result.append(card_dict)

    return result, total

def get_industry_breakdown(
    db: Session,
    search: Optional[str] = None,
    filter_status: Optional[str] = None,
    # 高級篩選參數
    name_zh: Optional[str] = None,
    name_en: Optional[str] = None,
    company: Optional[str] = None,
    position: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    has_phone: Optional[bool] = None,
    has_email: Optional[bool] = None,
    has_address: Optional[bool] = None,
) -> Dict[str, int]:
    """
    在目前條件（search + status + 高級篩選）下，各 industry_category 的數量
    """
    query = db.query(
        CardORM.industry_category,
        func.count(CardORM.id)
    )

    # 搜尋條件（跟 get_cards_paginated 一致）
    if search:
        search_filter = or_(
            CardORM.name_zh.contains(search),
            CardORM.name_en.contains(search),
            CardORM.company_name_zh.contains(search),
            CardORM.company_name_en.contains(search),
            CardORM.position_zh.contains(search),
            CardORM.position_en.contains(search),
            CardORM.position1_zh.contains(search),
            CardORM.position1_en.contains(search),
            CardORM.mobile_phone.contains(search),
            CardORM.email.contains(search),
            CardORM.classification_reason.contains(search),
        )
        query = query.filter(search_filter)

    # === 高級篩選（跟 get_cards_paginated 一致）===
    if name_zh:
        query = query.filter(CardORM.name_zh.contains(name_zh))
    if name_en:
        query = query.filter(CardORM.name_en.contains(name_en))
    if company:
        query = query.filter(or_(
            CardORM.company_name_zh.contains(company),
            CardORM.company_name_en.contains(company),
        ))
    if position:
        query = query.filter(or_(
            CardORM.position_zh.contains(position),
            CardORM.position_en.contains(position),
            CardORM.position1_zh.contains(position),
            CardORM.position1_en.contains(position),
        ))
    if date_from:
        try:
            dt_from = datetime.datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(CardORM.created_at >= dt_from)
        except ValueError:
            pass
    if date_to:
        try:
            dt_to = datetime.datetime.strptime(date_to, "%Y-%m-%d") + datetime.timedelta(days=1)
            query = query.filter(CardORM.created_at < dt_to)
        except ValueError:
            pass

    def is_empty(col):
        return or_(col.is_(None), col == "")
    def is_not_empty(col):
        return and_(col.isnot(None), col != "")

    if has_phone is True:
        query = query.filter(or_(
            is_not_empty(CardORM.mobile_phone),
            is_not_empty(CardORM.company_phone1),
            is_not_empty(CardORM.company_phone2),
        ))
    elif has_phone is False:
        query = query.filter(and_(
            is_empty(CardORM.mobile_phone),
            is_empty(CardORM.company_phone1),
            is_empty(CardORM.company_phone2),
        ))
    if has_email is True:
        query = query.filter(is_not_empty(CardORM.email))
    elif has_email is False:
        query = query.filter(is_empty(CardORM.email))
    if has_address is True:
        query = query.filter(or_(
            is_not_empty(CardORM.company_address1_zh),
            is_not_empty(CardORM.company_address2_zh),
        ))
    elif has_address is False:
        query = query.filter(and_(
            is_empty(CardORM.company_address1_zh),
            is_empty(CardORM.company_address2_zh),
        ))

    # 狀態條件（跟 get_cards_paginated 一致）
    if filter_status in ("normal", "problem"):
        name_missing = and_(is_empty(CardORM.name_zh), is_empty(CardORM.name_en))
        company_missing = and_(is_empty(CardORM.company_name_zh), is_empty(CardORM.company_name_en))

        position_missing = and_(
            is_empty(CardORM.position_zh), is_empty(CardORM.position_en),
            is_empty(CardORM.position1_zh), is_empty(CardORM.position1_en),
        )
        department_missing = and_(
            is_empty(CardORM.department1_zh), is_empty(CardORM.department1_en),
            is_empty(CardORM.department2_zh), is_empty(CardORM.department2_en),
            is_empty(CardORM.department3_zh), is_empty(CardORM.department3_en),
        )
        position_or_dept_missing = and_(position_missing, department_missing)

        contact_missing = and_(
            is_empty(CardORM.mobile_phone),
            is_empty(CardORM.company_phone1),
            is_empty(CardORM.company_phone2),
            is_empty(CardORM.email),
            is_empty(CardORM.line_id),
        )

        problem_condition = or_(name_missing, company_missing, position_or_dept_missing, contact_missing)

        if filter_status == "problem":
            query = query.filter(problem_condition)
        else:
            query = query.filter(~problem_condition)
    elif filter_status == "duplicate":
        query = query.filter(CardORM.duplicate_group_id.isnot(None), CardORM.reviewed_at.is_(None))

    query = query.group_by(CardORM.industry_category)
    rows = query.all()

    breakdown: Dict[str, int] = {}
    for cat, cnt in rows:
        key = (cat or "未分類")
        breakdown[key] = int(cnt)

    return breakdown

def get_card(db: Session, card_id: int) -> dict:
    card = db.query(CardORM).filter(CardORM.id == card_id).first()
    if not card:
        return None

    card_dict = Card.model_validate(card).model_dump()
    if card_dict.get('created_at'):
        card_dict['created_at'] = card_dict['created_at'].isoformat()
    if card_dict.get('updated_at'):
        card_dict['updated_at'] = card_dict['updated_at'].isoformat()
    if card_dict.get('classified_at'):
        card_dict['classified_at'] = card_dict['classified_at'].isoformat()

    return card_dict

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

def update_card(db: Session, card_id: int, card: Card) -> dict:
    db_card = db.query(CardORM).filter(CardORM.id == card_id).first()
    if not db_card:
        return None

    # 記住舊的 name/company 以便更新重複組
    old_name_zh = db_card.name_zh
    old_company_name_zh = db_card.company_name_zh

    # 獲取要更新的數據，允許空字符串，只排除 None 值和 id 字段
    update_data = card.model_dump(exclude={'id'})

    for k, v in update_data.items():
        # 允許空字符串，但跳過 None 值和時間戳字段
        if hasattr(db_card, k) and v is not None and k not in ['created_at']:
            setattr(db_card, k, v)

    try:
        db.commit()
        db.refresh(db_card)

        # 更新重複組標記（如果 name 或 company 變了）
        update_duplicate_group(db, old_name_zh, old_company_name_zh)
        if db_card.name_zh != old_name_zh or db_card.company_name_zh != old_company_name_zh:
            update_duplicate_group(db, db_card.name_zh, db_card.company_name_zh)
        db.commit()
        db.refresh(db_card)

        # 轉換為字典格式，處理datetime序列化
        card_dict = Card.model_validate(db_card).model_dump()
        for key in card_dict:
            if hasattr(card_dict[key], 'isoformat'):
                card_dict[key] = card_dict[key].isoformat()

        return card_dict
    except Exception as e:
        db.rollback()
        print(f"更新名片錯誤: {e}")
        raise e

def delete_card(db: Session, card_id: int) -> bool:
    db_card = db.query(CardORM).filter(CardORM.id == card_id).first()
    if not db_card:
        return False

    name_zh = db_card.name_zh
    company_name_zh = db_card.company_name_zh

    try:
        db.delete(db_card)
        db.commit()

        update_duplicate_group(db, name_zh, company_name_zh)
        db.commit()

        return True
    except Exception as e:
        db.rollback()
        print(f"刪除名片錯誤: {e}")
        return False

def bulk_create_cards(db: Session, cards: List[Card]) -> Tuple[List[dict], List[str]]:
    """批量創建名片 - 優化版
    Returns:
        Tuple[List[dict], List[str]]: (成功創建的名片列表, 錯誤信息列表)
    """
    success_cards = []
    error_messages = []
    
    try:
        # 批量創建 ORM 對象
        db_cards = []
        for i, card in enumerate(cards):
            try:
                db_card = CardORM(**card.model_dump(exclude_unset=True))
                db_cards.append(db_card)
            except Exception as e:
                error_messages.append(f"記錄 {i+1}: {str(e)}")
        
        if db_cards:
            # 使用 bulk_insert_mappings 更高效
            mappings = [card.model_dump(exclude_unset=True) for card in cards[:len(db_cards)]]
            db.bulk_insert_mappings(CardORM, mappings)
            db.commit()
            
            # 返回插入的數據（不需要刷新，提高性能）
            for mapping in mappings:
                # 添加時間戳
                mapping['created_at'] = mapping.get('created_at', datetime.datetime.utcnow()).isoformat()
                mapping['updated_at'] = mapping.get('updated_at', datetime.datetime.utcnow()).isoformat()
                success_cards.append(mapping)
        
        return success_cards, error_messages
        
    except Exception as e:
        db.rollback()
        print(f"批量創建名片錯誤: {e}")
        return [], [f"批量插入失敗: {str(e)}"]

def get_cards_count(db: Session, search: Optional[str] = None) -> int:
    """獲取名片總數"""
    query = db.query(func.count(CardORM.id))
    
    if search:
        search_filter = or_(
            # 姓名搜索 (中英文)
            CardORM.name_zh.contains(search),
            CardORM.name_en.contains(search),
            # 公司搜索 (中英文)
            CardORM.company_name_zh.contains(search),
            CardORM.company_name_en.contains(search),
            # 職稱搜索 (中英文，支援兩個職稱欄位)
            CardORM.position_zh.contains(search),
            CardORM.position_en.contains(search),
            CardORM.position1_zh.contains(search),
            CardORM.position1_en.contains(search),
            # 聯絡資訊搜索
            CardORM.mobile_phone.contains(search),
            CardORM.email.contains(search),
            # 產業標籤搜尋
            CardORM.classification_reason.contains(search),
        )
        query = query.filter(search_filter)
    
    return query.scalar()


def get_duplicate_groups(db: Session, skip: int = 0, limit: int = 1) -> Tuple[List[dict], int]:
    """取得待處理的重複組別（組內至少有一張 reviewed_at 為 NULL）"""

    subquery = db.query(
        CardORM.duplicate_group_id,
    ).filter(
        CardORM.duplicate_group_id.isnot(None),
        CardORM.reviewed_at.is_(None),
    ).group_by(
        CardORM.duplicate_group_id,
    ).subquery()

    total_groups = db.query(func.count()).select_from(subquery).scalar()

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


def get_duplicate_group_by_id(db: Session, group_id: str) -> Tuple[dict, int, int]:
    """根據 group_id 取得指定重複組，並回傳該組在所有待處理組中的索引位置"""

    # 取得所有待處理組的 ID 列表（有序）
    subquery = db.query(
        CardORM.duplicate_group_id,
    ).filter(
        CardORM.duplicate_group_id.isnot(None),
        CardORM.reviewed_at.is_(None),
    ).group_by(
        CardORM.duplicate_group_id,
    ).subquery()

    all_group_ids = [row[0] for row in db.query(subquery.c.duplicate_group_id).all()]
    total_groups = len(all_group_ids)

    # 找出目標組的索引
    group_index = 0
    if group_id in all_group_ids:
        group_index = all_group_ids.index(group_id)

    # 取得該組的名片
    cards = db.query(CardORM).filter(
        CardORM.duplicate_group_id == group_id
    ).order_by(CardORM.created_at.asc()).all()

    if not cards:
        return None, total_groups, 0

    card_dicts = []
    for card in cards:
        card_dict = Card.model_validate(card).model_dump()
        card_dict['id'] = card.id
        for key in card_dict:
            if hasattr(card_dict[key], 'isoformat'):
                card_dict[key] = card_dict[key].isoformat()
        card_dicts.append(card_dict)

    group = {
        "group_id": group_id,
        "name_zh": cards[0].name_zh,
        "company_name_zh": cards[0].company_name_zh or "",
        "cards": card_dicts,
        "count": len(cards),
    }

    return group, total_groups, group_index


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
