from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Optional, Dict, Tuple
import time
import asyncio
from collections import defaultdict
import redis.asyncio as redis
from src.core.config import get_settings
from src.core.exceptions import RateLimitExceededError
from src.utils.logging import logger

settings = get_settings()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enterprise rate limiting middleware"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.enabled = settings.rate_limit.enabled
        self.strategy = settings.rate_limit.strategy
        self.redis_client = None
        
        # In-memory storage for development
        self.memory_storage = defaultdict(list)
        
        # Initialize Redis if configured
        if settings.rate_limit.redis_url:
            self.redis_client = redis.from_url(
                settings.rate_limit.redis_url,
                decode_responses=True
            )
    
    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)
        
        # Extract identifiers for rate limiting
        identifiers = await self._get_identifiers(request)
        
        # Check rate limits
        try:
            await self._check_rate_limits(request, identifiers)
        except RateLimitExceededError as e:
            return await self._handle_rate_limit_exceeded(request, e)
        
        # Process request
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time
        
        # Add rate limit headers
        await self._add_rate_limit_headers(response, identifiers)
        
        # Log rate limit info
        logger.debug(
            "Request processed",
            extra={
                "path": request.url.path,
                "duration_ms": int(duration * 1000),
                "identifiers": identifiers
            }
        )
        
        return response
    
    async def _get_identifiers(self, request: Request) -> Dict[str, str]:
        """Get identifiers for rate limiting"""
        identifiers = {}
        
        # User ID from auth (if authenticated)
        if hasattr(request.state, "user"):
            identifiers["user"] = request.state.user.get("sub", "anonymous")
        
        # Tenant ID
        if hasattr(request.state, "tenant"):
            identifiers["tenant"] = request.state.tenant
        
        # API key
        api_key = request.headers.get(settings.auth.api_key_header_name)
        if api_key:
            identifiers["api_key"] = api_key
        
        # IP address
        identifiers["ip"] = request.client.host
        
        # Endpoint
        identifiers["endpoint"] = request.url.path
        
        return identifiers
    
    async def _check_rate_limits(self, request: Request, identifiers: Dict[str, str]):
        """Check all applicable rate limits"""
        
        # Check endpoint-specific limits
        endpoint = identifiers.get("endpoint", "")
        if endpoint in settings.rate_limit.endpoint_limits:
            limit = settings.rate_limit.endpoint_limits[endpoint]
            await self._check_limit(
                key=f"endpoint:{endpoint}",
                limit=limit,
                identifiers=identifiers
            )
        
        # Check user limits
        user = identifiers.get("user")
        if user and user in settings.rate_limit.user_limits:
            limit = settings.rate_limit.user_limits[user]
            await self._check_limit(
                key=f"user:{user}",
                limit=limit,
                identifiers=identifiers
            )
        
        # Check tenant limits
        tenant = identifiers.get("tenant")
        if tenant and tenant in settings.rate_limit.tenant_limits:
            limit = settings.rate_limit.tenant_limits[tenant]
            await self._check_limit(
                key=f"tenant:{tenant}",
                limit=limit,
                identifiers=identifiers
            )
        
        # Apply default limit
        await self._check_limit(
            key=f"default:{identifiers.get('ip', 'unknown')}",
            limit=settings.rate_limit.default_limit,
            identifiers=identifiers
        )
    
    async def _check_limit(self, key: str, limit: str, identifiers: Dict[str, str]):
        """Check a specific rate limit"""
        
        # Parse limit string (e.g., "100/minute")
        max_requests, period = self._parse_limit(limit)
        period_seconds = self._parse_period(period)
        
        # Get current count
        if self.redis_client:
            # Distributed rate limiting with Redis
            current = await self._check_redis_limit(key, max_requests, period_seconds)
        else:
            # In-memory rate limiting (development only)
            current = self._check_memory_limit(key, max_requests, period_seconds)
        
        if current > max_requests:
            retry_after = period_seconds
            raise RateLimitExceededError(
                retry_after=retry_after,
                limit=limit
            )
    
    async def _check_redis_limit(self, key: str, max_requests: int, period: int) -> int:
        """Check rate limit using Redis"""
        redis_key = f"{settings.rate_limit.redis_prefix}{key}"
        
        if self.strategy == "fixed-window":
            # Fixed window counter
            current = await self.redis_client.incr(redis_key)
            if current == 1:
                await self.redis_client.expire(redis_key, period)
            return current
            
        elif self.strategy == "sliding-window":
            # Sliding window log
            now = time.time()
            pipeline = self.redis_client.pipeline()
            pipeline.zremrangebyscore(redis_key, 0, now - period)
            pipeline.zadd(redis_key, {str(now): now})
            pipeline.zcard(redis_key)
            pipeline.expire(redis_key, period)
            _, _, count, _ = await pipeline.execute()
            return count
            
        elif self.strategy == "token-bucket":
            # Token bucket algorithm
            redis_key = f"{redis_key}:tokens"
            last_refill_key = f"{redis_key}:last_refill"
            
            # Get current tokens and last refill
            tokens = await self.redis_client.get(redis_key)
            last_refill = await self.redis_client.get(last_refill_key)
            
            now = time.time()
            if tokens is None:
                # Initialize bucket
                tokens = max_requests
                await self.redis_client.setex(redis_key, period, tokens)
                await self.redis_client.setex(last_refill_key, period, now)
                return 0
            
            tokens = float(tokens)
            last_refill = float(last_refill) if last_refill else now
            
            # Calculate tokens to add
            time_passed = now - last_refill
            tokens_to_add = time_passed * (max_requests / period)
            tokens = min(max_requests, tokens + tokens_to_add)
            
            # Check if we can consume a token
            if tokens >= 1:
                tokens -= 1
                await self.redis_client.setex(redis_key, period, tokens)
                await self.redis_client.setex(last_refill_key, period, now)
                return 0
            
            return max_requests  # Rate limited
    
    def _check_memory_limit(self, key: str, max_requests: int, period: int) -> int:
        """Check rate limit using in-memory storage (development only)"""
        now = time.time()
        
        # Clean old entries
        self.memory_storage[key] = [
            timestamp for timestamp in self.memory_storage[key]
            if timestamp > now - period
        ]
        
        # Add current request
        self.memory_storage[key].append(now)
        
        return len(self.memory_storage[key])
    
    def _parse_limit(self, limit: str) -> Tuple[int, str]:
        """Parse limit string into (max_requests, period)"""
        try:
            count, period = limit.split("/")
            return int(count), period
        except (ValueError, AttributeError):
            return 100, "minute"
    
    def _parse_period(self, period: str) -> int:
        """Parse period string into seconds"""
        periods = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400,
            "week": 604800
        }
        return periods.get(period, 60)
    
    async def _add_rate_limit_headers(self, response, identifiers: Dict[str, str]):
        """Add rate limit headers to response"""
        # In production, calculate remaining limits
        response.headers["X-RateLimit-Limit"] = settings.rate_limit.default_limit
        response.headers["X-RateLimit-Remaining"] = "99"  # Example
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)
    
    async def _handle_rate_limit_exceeded(self, request: Request, error: RateLimitExceededError):
        """Handle rate limit exceeded"""
        from fastapi.responses import JSONResponse
        
        logger.warning(
            f"Rate limit exceeded: {error.message}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "ip": request.client.host
            }
        )
        
        return JSONResponse(
            status_code=error.status_code,
            content={
                "error": {
                    "code": error.code,
                    "message": error.message,
                    "retry_after": error.details.get("retry_after"),
                    "limit": error.details.get("limit")
                }
            },
            headers={
                "Retry-After": str(error.details.get("retry_after", 60))
            }
        )