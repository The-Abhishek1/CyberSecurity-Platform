
from fastapi import Request, HTTPException, Depends
from typing import Optional, Dict, Any
import uuid
from datetime import datetime

async def get_current_user(request: Request) -> Dict[str, Any]:
    """Get current authenticated user"""
    # In production, this would validate JWT token
    # For development, return mock user
    if hasattr(request.state, "user"):
        return request.state.user
    
    # Mock user for development
    return {
        "sub": "dev_user_123",
        "email": "dev@example.com",
        "tenant_id": "tenant_001",
        "permissions": ["read", "write", "execute"],
        "roles": ["admin"]
    }

async def get_tenant_id(request: Request) -> str:
    """Get tenant ID from request"""
    # Check header first
    tenant_id = request.headers.get("X-Tenant-ID")
    if tenant_id:
        return tenant_id
    
    # Check from user
    if hasattr(request.state, "user"):
        return request.state.user.get("tenant_id", "default")
    
    return "default"

async def get_request_id(request: Request) -> str:
    """Get or generate request ID for tracing"""
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        request.state.request_id = request_id
    return request_id

class RateLimiter:
    """Simple rate limiter for development"""
    
    def __init__(self):
        self.requests = {}
        
    async def check_rate_limit(self, key: str, limit: int = 100, window: int = 60):
        """Check if request is within rate limit"""
        now = datetime.utcnow().timestamp()
        
        if key not in self.requests:
            self.requests[key] = []
            
        # Clean old requests
        self.requests[key] = [ts for ts in self.requests[key] 
                              if ts > now - window]
        
        # Check limit
        if len(self.requests[key]) >= limit:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        # Add current request
        self.requests[key].append(now)
        return True

rate_limiter = RateLimiter()