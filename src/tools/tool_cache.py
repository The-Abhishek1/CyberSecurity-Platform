from typing import Optional, Dict, Any, List
import json
import hashlib
from datetime import datetime, timedelta
from redis import asyncio as aioredis

from src.core.config import get_settings
from src.utils.logging import logger

settings = get_settings()


class ToolCache:
    """
    Enterprise Tool Cache
    
    Features:
    - Redis-backed caching
    - TTL per cache entry
    - Cache invalidation strategies
    - Compression for large results
    - Cache statistics
    """
    
    def __init__(self):
        self.redis = None
        self._connect_redis()
        
        # Local memory cache for hot items
        self.local_cache: Dict[str, Dict] = {}
        
        # Cache statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "invalidations": 0
        }
    
    def _connect_redis(self):
        """Connect to Redis"""
        try:
            self.redis = aioredis.from_url(
                settings.database.redis_dsn,
                decode_responses=True
            )
        except Exception as e:
            logger.warning(f"Failed to connect to Redis for cache: {e}")
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get value from cache"""
        
        # Check local cache first
        if key in self.local_cache:
            entry = self.local_cache[key]
            if datetime.utcnow() < entry["expires_at"]:
                self.stats["hits"] += 1
                return entry["value"]
            else:
                # Expired
                del self.local_cache[key]
        
        # Check Redis
        if self.redis:
            value = await self.redis.get(f"cache:{key}")
            if value:
                try:
                    parsed = json.loads(value)
                    self.stats["hits"] += 1
                    
                    # Update local cache
                    self.local_cache[key] = {
                        "value": parsed,
                        "expires_at": datetime.utcnow() + timedelta(seconds=60)
                    }
                    
                    return parsed
                except json.JSONDecodeError:
                    pass
        
        self.stats["misses"] += 1
        return None
    
    async def set(
        self,
        key: str,
        value: Dict[str, Any],
        ttl: int = 300,
        tags: Optional[List[str]] = None
    ):
        """Set value in cache"""
        
        # Store in Redis
        if self.redis:
            await self.redis.setex(
                f"cache:{key}",
                ttl,
                json.dumps(value)
            )
            
            # Store tags for invalidation
            if tags:
                for tag in tags:
                    await self.redis.sadd(f"tag:{tag}", key)
                    await self.redis.expire(f"tag:{tag}", ttl)
        
        # Store in local cache
        self.local_cache[key] = {
            "value": value,
            "expires_at": datetime.utcnow() + timedelta(seconds=min(ttl, 60))
        }
        
        self.stats["sets"] += 1
    
    async def invalidate(self, key: str):
        """Invalidate cache entry"""
        
        # Remove from Redis
        if self.redis:
            await self.redis.delete(f"cache:{key}")
        
        # Remove from local cache
        self.local_cache.pop(key, None)
        
        self.stats["invalidations"] += 1
    
    async def invalidate_by_tag(self, tag: str):
        """Invalidate all cache entries with tag"""
        
        if not self.redis:
            return
        
        # Get all keys with this tag
        keys = await self.redis.smembers(f"tag:{tag}")
        
        # Delete all keys
        if keys:
            pipeline = self.redis.pipeline()
            for key in keys:
                pipeline.delete(f"cache:{key}")
            await pipeline.execute()
            
            # Delete tag set
            await self.redis.delete(f"tag:{tag}")
            
            # Remove from local cache
            for key in keys:
                self.local_cache.pop(key, None)
            
            self.stats["invalidations"] += len(keys)
    
    async def get_or_compute(
        self,
        key: str,
        compute_func: callable,
        ttl: int = 300,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get from cache or compute and store"""
        
        # Try cache first
        cached = await self.get(key)
        if cached:
            return cached
        
        # Compute value
        value = await compute_func()
        
        # Store in cache
        await self.set(key, value, ttl, tags)
        
        return value
    
    async def clear(self):
        """Clear all cache entries"""
        
        if self.redis:
            await self.redis.flushdb()
        
        self.local_cache.clear()
        
        logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total * 100) if total > 0 else 0
        
        return {
            **self.stats,
            "hit_rate": hit_rate,
            "local_cache_size": len(self.local_cache)
        }