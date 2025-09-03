from backend.models.card import CardORM, Card
from sqlalchemy.orm import Session
from typing import List, Tuple, Optional
from sqlalchemy import and_, or_, func
import datetime

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
        
        result.append(card_dict)
    return result

def get_cards_paginated(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    search: Optional[str] = None,
    filter_status: Optional[str] = None
) -> Tuple[List[dict], int]:
    """分頁獲取名片，支持搜索和過濾"""
    query = db.query(CardORM)
    
    # 搜索過濾 - 支援姓名、公司、職稱的中英文搜索
    if search:
        search_filter = or_(
            # 姓名搜索 (中英文)
            CardORM.name.contains(search),
            CardORM.name_en.contains(search),
            # 公司搜索 (中英文)
            CardORM.company_name.contains(search),
            CardORM.company_name_en.contains(search),
            # 職稱搜索 (中英文，支援兩個職稱欄位)
            CardORM.position.contains(search),
            CardORM.position_en.contains(search),
            CardORM.position1.contains(search),
            CardORM.position1_en.contains(search),
            # 聯絡資訊搜索
            CardORM.mobile_phone.contains(search),
            CardORM.email.contains(search)
        )
        query = query.filter(search_filter)
    
    # 獲取總數
    total = query.count()
    
    # 分頁查詢
    cards = query.order_by(CardORM.created_at.desc()).offset(skip).limit(limit).all()
    
    # 轉換為字典
    result = []
    for card in cards:
        card_dict = card.__dict__.copy()
        card_dict.pop('_sa_instance_state', None)
        
        if card_dict.get('created_at'):
            card_dict['created_at'] = card_dict['created_at'].isoformat()
        if card_dict.get('updated_at'):
            card_dict['updated_at'] = card_dict['updated_at'].isoformat()
        
        result.append(card_dict)
    
    return result, total

def get_card(db: Session, card_id: int) -> dict:
    card = db.query(CardORM).filter(CardORM.id == card_id).first()
    if not card:
        return None
    
    card_dict = Card.model_validate(card).model_dump()
    if card_dict.get('created_at'):
        card_dict['created_at'] = card_dict['created_at'].isoformat()
    if card_dict.get('updated_at'):
        card_dict['updated_at'] = card_dict['updated_at'].isoformat()
    
    return card_dict

def create_card(db: Session, card: Card) -> dict:
    db_card = CardORM(**card.model_dump(exclude_unset=True))
    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    
    # 轉換為字典格式，處理datetime序列化
    card_dict = Card.model_validate(db_card).model_dump()
    if card_dict.get('created_at'):
        card_dict['created_at'] = card_dict['created_at'].isoformat()
    if card_dict.get('updated_at'):
        card_dict['updated_at'] = card_dict['updated_at'].isoformat()
    
    return card_dict

def update_card(db: Session, card_id: int, card: Card) -> dict:
    db_card = db.query(CardORM).filter(CardORM.id == card_id).first()
    if not db_card:
        return None
    
    # 獲取要更新的數據，允許空字符串，只排除 None 值和 id 字段
    update_data = card.model_dump(exclude={'id'})
    
    for k, v in update_data.items():
        # 允許空字符串，但跳過 None 值和時間戳字段
        if hasattr(db_card, k) and v is not None and k not in ['created_at']:
            setattr(db_card, k, v)
    
    try:
        db.commit()
        db.refresh(db_card)
        
        # 轉換為字典格式，處理datetime序列化
        card_dict = Card.model_validate(db_card).model_dump()
        if card_dict.get('created_at'):
            card_dict['created_at'] = card_dict['created_at'].isoformat()
        if card_dict.get('updated_at'):
            card_dict['updated_at'] = card_dict['updated_at'].isoformat()
        
        return card_dict
    except Exception as e:
        db.rollback()
        print(f"更新名片錯誤: {e}")
        raise e

def delete_card(db: Session, card_id: int) -> bool:
    db_card = db.query(CardORM).filter(CardORM.id == card_id).first()
    if not db_card:
        return False
    try:
        db.delete(db_card)
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
            CardORM.name.contains(search),
            CardORM.name_en.contains(search),
            # 公司搜索 (中英文)
            CardORM.company_name.contains(search),
            CardORM.company_name_en.contains(search),
            # 職稱搜索 (中英文，支援兩個職稱欄位)
            CardORM.position.contains(search),
            CardORM.position_en.contains(search),
            CardORM.position1.contains(search),
            CardORM.position1_en.contains(search),
            # 聯絡資訊搜索
            CardORM.mobile_phone.contains(search),
            CardORM.email.contains(search)
        )
        query = query.filter(search_filter)
    
    return query.scalar()