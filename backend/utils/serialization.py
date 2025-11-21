"""
DateTime serialization utilities for consistent API responses
"""
from typing import Dict, Any, Optional, List


def serialize_datetime_fields(card_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    統一處理datetime字段序列化為ISO格式字符串

    Args:
        card_dict: 包含datetime字段的字典

    Returns:
        處理後的字典（原地修改）

    Example:
        >>> from datetime import datetime
        >>> card = {'name': 'Test', 'created_at': datetime.now()}
        >>> serialize_datetime_fields(card)
        {'name': 'Test', 'created_at': '2024-01-01T12:00:00'}
    """
    datetime_fields = ['created_at', 'updated_at', 'classified_at']

    for field in datetime_fields:
        if card_dict.get(field):
            # 如果字段存在且不為None，轉換為ISO格式字符串
            card_dict[field] = card_dict[field].isoformat()

    return card_dict


def serialize_datetime_list(cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    批量處理多個名片的datetime字段

    Args:
        cards: 名片字典列表

    Returns:
        處理後的名片列表
    """
    return [serialize_datetime_fields(card) for card in cards]
