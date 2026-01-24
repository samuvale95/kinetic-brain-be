"""
Redis caching utility with decorator support
"""
from functools import wraps
from typing import Optional, Callable, Any
import json
import hashlib
from loguru import logger
import redis
from app.config import settings


class CacheManager:
    """Redis cache manager with fallback to in-memory"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.memory_cache: dict = {}
        self.use_redis = False
        
        # Initialize Redis if configured
        if settings.redis_url and settings.redis_url != "redis://localhost:6379":
            try:
                self.redis_client = redis.from_url(
                    settings.redis_url,
                    socket_connect_timeout=2,
                    decode_responses=True
                )
                # Test connection
                self.redis_client.ping()
                self.use_redis = True
                logger.info(f"Cache using Redis: {settings.redis_url}")
            except Exception as e:
                logger.warning(f"Redis not available, using in-memory cache: {e}")
                self.use_redis = False
        else:
            logger.info("Cache using in-memory storage (Redis not configured)")
    
    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from prefix, args, and kwargs"""
        # Serialize args and kwargs
        key_data = {
            "args": args,
            "kwargs": sorted(kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        key_hash = hashlib.md5(key_str.encode()).hexdigest()
        return f"{prefix}:{key_hash}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if self.use_redis and self.redis_client:
            try:
                value = self.redis_client.get(key)
                if value:
                    return json.loads(value)
            except Exception as e:
                logger.warning(f"Redis get error: {e}, falling back to memory")
                self.use_redis = False
        
        # Fallback to memory cache
        return self.memory_cache.get(key)
    
    def set(self, key: str, value: Any, ttl: int = 300):
        """Set value in cache with TTL (seconds)"""
        try:
            serialized = json.dumps(value, default=str)
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to serialize cache value: {e}")
            return False
        
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.setex(key, ttl, serialized)
                return True
            except Exception as e:
                logger.warning(f"Redis set error: {e}, falling back to memory")
                self.use_redis = False
        
        # Fallback to memory cache (simple dict, no TTL)
        self.memory_cache[key] = value
        return True
    
    def delete(self, key: str):
        """Delete key from cache"""
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.delete(key)
            except Exception as e:
                logger.warning(f"Redis delete error: {e}")
        
        # Also delete from memory cache
        self.memory_cache.pop(key, None)
    
    def delete_pattern(self, pattern: str):
        """Delete all keys matching pattern"""
        if self.use_redis and self.redis_client:
            try:
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
            except Exception as e:
                logger.warning(f"Redis delete_pattern error: {e}")
        
        # Also delete from memory cache
        keys_to_delete = [k for k in self.memory_cache.keys() if pattern.replace('*', '') in k]
        for key in keys_to_delete:
            del self.memory_cache[key]
    
    def clear(self):
        """Clear all cache"""
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.flushdb()
            except Exception as e:
                logger.warning(f"Redis clear error: {e}")
        
        self.memory_cache.clear()


# Global cache manager instance
cache_manager = CacheManager()


def cache_result(ttl: int = 300, prefix: str = "cache"):
    """
    Decorator to cache function results
    
    Args:
        ttl: Time to live in seconds (default: 300 = 5 minutes)
        prefix: Cache key prefix (default: "cache")
    
    Example:
        @cache_result(ttl=600, prefix="user_profile")
        def get_user_profile(user_id: int):
            # Expensive database query
            return db.query(User).filter(User.id == user_id).first()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = cache_manager._make_key(f"{prefix}:{func.__name__}", *args, **kwargs)
            
            # Try to get from cache
            cached_value = cache_manager.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value
            
            # Cache miss - execute function
            logger.debug(f"Cache miss: {cache_key}")
            result = func(*args, **kwargs)
            
            # Store in cache
            cache_manager.set(cache_key, result, ttl)
            
            return result
        
        # Add cache invalidation method
        def invalidate(*args, **kwargs):
            """Invalidate cache for specific arguments"""
            cache_key = cache_manager._make_key(f"{prefix}:{func.__name__}", *args, **kwargs)
            cache_manager.delete(cache_key)
        
        wrapper.invalidate = invalidate
        wrapper.cache_key = lambda *args, **kwargs: cache_manager._make_key(
            f"{prefix}:{func.__name__}", *args, **kwargs
        )
        
        return wrapper
    
    return decorator


def invalidate_cache_pattern(pattern: str):
    """Invalidate all cache keys matching pattern"""
    cache_manager.delete_pattern(pattern)


def clear_cache():
    """Clear all cache"""
    cache_manager.clear()
