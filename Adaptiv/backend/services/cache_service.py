"""
Cache service for optimizing performance with large datasets
"""
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Any, Dict
import logging

logger = logging.getLogger(__name__)

class CacheService:
    """Simple in-memory cache for performance optimization"""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 300  # 5 minutes default TTL
    
    def _generate_key(self, prefix: str, **kwargs) -> str:
        """Generate a cache key from parameters"""
        # Sort kwargs to ensure consistent key generation
        sorted_params = sorted(kwargs.items())
        param_string = json.dumps(sorted_params, sort_keys=True)
        param_hash = hashlib.md5(param_string.encode()).hexdigest()
        return f"{prefix}:{param_hash}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in self._cache:
            cache_entry = self._cache[key]
            if datetime.now() < cache_entry['expires_at']:
                logger.debug(f"Cache hit for key: {key}")
                return cache_entry['data']
            else:
                # Expired, remove from cache
                del self._cache[key]
                logger.debug(f"Cache expired for key: {key}")
        
        logger.debug(f"Cache miss for key: {key}")
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        if ttl is None:
            ttl = self._cache_ttl
        
        expires_at = datetime.now() + timedelta(seconds=ttl)
        self._cache[key] = {
            'data': value,
            'expires_at': expires_at
        }
        logger.debug(f"Cache set for key: {key}, expires at: {expires_at}")
    
    def invalidate_pattern(self, pattern: str) -> None:
        """Invalidate all cache keys matching a pattern"""
        keys_to_remove = [key for key in self._cache.keys() if pattern in key]
        for key in keys_to_remove:
            del self._cache[key]
        logger.debug(f"Invalidated {len(keys_to_remove)} cache entries matching pattern: {pattern}")
    
    def clear(self) -> None:
        """Clear all cache entries"""
        self._cache.clear()
        logger.debug("Cache cleared")
    
    def get_product_performance_key(self, user_id: int, time_frame: str) -> str:
        """Generate cache key for product performance data"""
        return self._generate_key("product_performance", user_id=user_id, time_frame=time_frame)
    
    def get_price_history_key(self, item_ids: list) -> str:
        """Generate cache key for price history data"""
        # Sort item_ids to ensure consistent key generation
        sorted_ids = sorted(item_ids)
        return self._generate_key("price_history", item_ids=sorted_ids)

# Global cache instance
cache_service = CacheService()
