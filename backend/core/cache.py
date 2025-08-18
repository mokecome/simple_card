# -*- coding: utf-8 -*-
"""
簡單的內存緩存實現
"""
from datetime import datetime, timedelta
from typing import Any, Optional, Dict
import threading

class SimpleCache:
    """線程安全的簡單內存緩存"""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, datetime] = {}
        self._lock = threading.Lock()
    
    def get(self, key: str, default: Any = None) -> Any:
        """獲取緩存值"""
        with self._lock:
            if key in self._cache:
                # 檢查是否過期
                if datetime.now() - self._timestamps[key] < timedelta(minutes=5):
                    return self._cache[key]
                else:
                    # 過期則刪除
                    del self._cache[key]
                    del self._timestamps[key]
            return default
    
    def set(self, key: str, value: Any, ttl_minutes: int = 5) -> None:
        """設置緩存值"""
        with self._lock:
            self._cache[key] = value
            self._timestamps[key] = datetime.now()
    
    def delete(self, key: str) -> None:
        """刪除緩存值"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                del self._timestamps[key]
    
    def clear(self) -> None:
        """清空所有緩存"""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
    
    def invalidate_pattern(self, pattern: str) -> None:
        """使匹配模式的緩存失效"""
        with self._lock:
            keys_to_delete = [k for k in self._cache.keys() if pattern in k]
            for key in keys_to_delete:
                del self._cache[key]
                del self._timestamps[key]

# 全局緩存實例
cache = SimpleCache()

# 緩存裝飾器
def cached(key_prefix: str, ttl_minutes: int = 5):
    """緩存裝飾器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 生成緩存鍵
            cache_key = f"{key_prefix}:{args}:{kwargs}"
            
            # 嘗試從緩存獲取
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # 執行函數並緩存結果
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl_minutes)
            return result
        
        return wrapper
    return decorator