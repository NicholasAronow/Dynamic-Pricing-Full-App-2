"""
Redis client utility for shared state management across processes.
"""

import redis
import json
import os
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class RedisClient:
    """Singleton Redis client for consistent connection management."""
    
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize Redis connection."""
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self._client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self._client.ping()
            logger.info(f"Redis connected successfully to {redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._client = None
    
    @property
    def client(self) -> Optional[redis.Redis]:
        """Get Redis client instance."""
        if self._client is None:
            self._initialize()
        return self._client
    
    def set_sync_progress(self, user_id: int, progress_data: Dict[str, Any], ttl: int = 3600) -> bool:
        """
        Store sync progress in Redis with TTL.
        
        Args:
            user_id: User ID
            progress_data: Progress data dictionary
            ttl: Time to live in seconds (default 1 hour)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            logger.warning("Redis client not available, skipping progress update")
            return False
        
        try:
            key = f"square_sync:{user_id}:progress"
            value = json.dumps(progress_data)
            self.client.setex(key, ttl, value)
            logger.debug(f"Updated Redis sync progress for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to set sync progress in Redis: {e}")
            return False
    
    def get_sync_progress(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get sync progress from Redis.
        
        Args:
            user_id: User ID
        
        Returns:
            Progress data dictionary or None if not found
        """
        if not self.client:
            logger.warning("Redis client not available")
            return None
        
        try:
            key = f"square_sync:{user_id}:progress"
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Failed to get sync progress from Redis: {e}")
            return None
    
    def delete_sync_progress(self, user_id: int) -> bool:
        """
        Delete sync progress from Redis.
        
        Args:
            user_id: User ID
        
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False
        
        try:
            key = f"square_sync:{user_id}:progress"
            self.client.delete(key)
            logger.debug(f"Deleted Redis sync progress for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete sync progress from Redis: {e}")
            return False

# Global instance
redis_client = RedisClient()
