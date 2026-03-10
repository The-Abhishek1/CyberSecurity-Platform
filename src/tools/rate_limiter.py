from typing import Dict, List, Optional
from datetime import datetime, timedelta
import asyncio
from redis import asyncio as aioredis

from src.core.config import get_settings
from src.core.exceptions import RateLimitExceededError
from src.utils.logging import logger

settings = get_settings()


class TokenBucket:
    """Token bucket algorithm for rate limiting"""
    
    def __init__(self, rate: float, capacity: int):
        self.rate = rate  # tokens per second
        self.capacity = capacity
        self.tokens = capacity
        self.last_refill = datetime.utcnow()
        self.lock = asyncio.Lock()
    
    async def consume(self, tokens: int = 1) -> bool:
        """Consume tokens from bucket"""
        
        async with self.lock:
            # Refill tokens
            now = datetime.utcnow()
            time_passed = (now - self.last_refill).total_seconds()
            self.tokens = min(
                self.capacity,
                self.tokens + time_passed * self.rate
            )
            self.last_refill = now
            
            # Check if we can consume
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False


class ToolRateLimiter:
    """
    Enterprise Rate Limiter for Tools
    
    Features:
    - Multiple rate limiting algorithms
    - Per-user, per-tenant, per-tool limits
    - Distributed rate limiting with Redis
    - Burst handling
    - Rate limit headers
    """
    
    def __init__(self):
        self.redis = None
        self._connect_redis()
        
        # Local rate limiters (for development)
        self.local_limiters: Dict[str, TokenBucket] = {}
        
        # Rate limit configurations
        self.limits: Dict[str, Dict] = {}
        
        logger.info("Tool Rate Limiter initialized")
    
    def _connect_redis(self):
        """Connect to Redis for distributed rate limiting"""
        try:
            self.redis = aioredis.from_url(
                settings.database.redis_dsn,
                decode_responses=True
            )
        except Exception as e:
            logger.warning(f"Failed to connect to Redis for rate limiting: {e}")
    
    async def configure_limit(
        self,
        key: str,
        rate: float,
        capacity: int,
        scope: str = "global"
    ):
        """Configure rate limit"""
        
        self.limits[key] = {
            "rate": rate,
            "capacity": capacity,
            "scope": scope
        }
    
    async def check_limits(
        self,
        user_id: str,
        tenant_id: str,
        tools: List[Dict]
    ):
        """Check all applicable rate limits"""
        
        for tool in tools:
            tool_name = tool["name"]
            
            # Check global tool limit
            await self._check_limit(
                key=f"tool:global:{tool_name}",
                user_id=user_id,
                tenant_id=tenant_id,
                tool=tool
            )
            
            # Check tenant tool limit
            await self._check_limit(
                key=f"tool:tenant:{tenant_id}:{tool_name}",
                user_id=user_id,
                tenant_id=tenant_id,
                tool=tool
            )
            
            # Check user tool limit
            await self._check_limit(
                key=f"tool:user:{user_id}:{tool_name}",
                user_id=user_id,
                tenant_id=tenant_id,
                tool=tool
            )
    
    async def _check_limit(
        self,
        key: str,
        user_id: str,
        tenant_id: str,
        tool: Dict
    ):
        """Check a specific rate limit"""
        
        # Get limit configuration
        limit_config = await self._get_limit_config(key, tool)
        if not limit_config:
            return
        
        # Check limit
        if self.redis:
            # Distributed rate limiting with Redis
            allowed = await self._check_redis_limit(
                key=key,
                rate=limit_config["rate"],
                capacity=limit_config["capacity"]
            )
        else:
            # Local rate limiting
            allowed = await self._check_local_limit(
                key=key,
                rate=limit_config["rate"],
                capacity=limit_config["capacity"]
            )
        
        if not allowed:
            raise RateLimitExceededError(
                message=f"Rate limit exceeded for {key}",
                retry_after=60,
                limit=f"{limit_config['capacity']}/{limit_config['rate']}s"
            )
    
    async def _get_limit_config(self, key: str, tool: Dict) -> Optional[Dict]:
        """Get rate limit configuration"""
        
        # Check if configured
        if key in self.limits:
            return self.limits[key]
        
        # Use tool defaults
        tool_limits = tool.get("rate_limits", {})
        
        # Determine limit based on key pattern
        if "global" in key:
            limit_str = tool_limits.get("global", tool_limits.get("default", "100/minute"))
        elif "tenant" in key:
            limit_str = tool_limits.get("tenant", tool_limits.get("default", "50/minute"))
        elif "user" in key:
            limit_str = tool_limits.get("user", tool_limits.get("default", "10/minute"))
        else:
            limit_str = tool_limits.get("default", "100/minute")
        
        # Parse limit string
        return self._parse_limit(limit_str)
    
    def _parse_limit(self, limit_str: str) -> Dict:
        """Parse limit string like '100/minute'"""
        
        try:
            count, period = limit_str.split("/")
            count = int(count)
            
            # Convert period to seconds
            period_seconds = {
                "second": 1,
                "minute": 60,
                "hour": 3600,
                "day": 86400
            }.get(period, 60)
            
            # Calculate rate (tokens per second) and capacity
            rate = count / period_seconds
            capacity = count  # Allow full burst
            
            return {
                "rate": rate,
                "capacity": capacity
            }
        except:
            # Default
            return {
                "rate": 100 / 60,  # 100 per minute
                "capacity": 100
            }
    
    async def _check_redis_limit(
        self,
        key: str,
        rate: float,
        capacity: int
    ) -> bool:
        """Check rate limit using Redis with token bucket"""
        
        redis_key = f"ratelimit:{key}"
        now = datetime.utcnow().timestamp()
        
        # Use Lua script for atomic operation
        lua_script = """
        local key = KEYS[1]
        local now = tonumber(ARGV[1])
        local rate = tonumber(ARGV[2])
        local capacity = tonumber(ARGV[3])
        
        local bucket = redis.call('hgetall', key)
        local tokens = capacity
        local last_refill = now
        
        if #bucket > 0 then
            tokens = tonumber(bucket[2])
            last_refill = tonumber(bucket[4])
            
            -- Refill tokens
            local time_passed = now - last_refill
            tokens = math.min(capacity, tokens + time_passed * rate)
        end
        
        -- Check if we can consume
        if tokens >= 1 then
            tokens = tokens - 1
            redis.call('hmset', key, 'tokens', tokens, 'last_refill', now)
            redis.call('expire', key, 3600)
            return 1
        end
        
        return 0
        """
        
        script = self.redis.register_script(lua_script)
        result = await script(
            keys=[redis_key],
            args=[now, rate, capacity]
        )
        
        return result == 1
    
    async def _check_local_limit(
        self,
        key: str,
        rate: float,
        capacity: int
    ) -> bool:
        """Check rate limit using local token bucket"""
        
        if key not in self.local_limiters:
            self.local_limiters[key] = TokenBucket(rate, capacity)
        
        return await self.local_limiters[key].consume()
    
    async def get_remaining(self, key: str) -> int:
        """Get remaining tokens for key"""
        
        if self.redis:
            bucket = await self.redis.hgetall(f"ratelimit:{key}")
            if bucket:
                return int(bucket.get("tokens", 0))
        
        return 0
    
    async def reset_limit(self, key: str):
        """Reset rate limit for key"""
        
        if self.redis:
            await self.redis.delete(f"ratelimit:{key}")
        else:
            self.local_limiters.pop(key, None)