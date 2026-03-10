from fastapi import Request, HTTPException, Depends
from typing import Optional
import uuid

async def get_current_user(request: Request):
    """Get current user from request state"""
    if hasattr(request.state, "user"):
        return request.state.user
    
    # For development, return a mock user
    return {
        "sub": "dev_user",
        "email": "dev@example.com",
        "permissions": ["*"]
    }

async def get_tenant_id(request: Request) -> str:
    """Get tenant ID from request"""
    # Try header first
    tenant_id = request.headers.get("X-Tenant-ID")
    if tenant_id:
        return tenant_id
    
    # Try from user
    if hasattr(request.state, "user"):
        return request.state.user.get("tenant_id", "default")
    
    # Default tenant
    return "default"

async def get_request_id(request: Request) -> str:
    """Get or generate request ID"""
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
    return request_id
