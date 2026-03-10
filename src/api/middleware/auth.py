from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Optional, Dict, Any, List
import time
import hashlib
import hmac
from src.core.security import security_service
from src.core.config import get_settings
from src.core.exceptions import AuthenticationError, AuthorizationError
from src.utils.logging import logger
import jwt

settings = get_settings()


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Enterprise authentication middleware"""
    
    def __init__(self, app: ASGIApp, exclude_paths: Optional[List[str]] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
        ]
        self.security = HTTPBearer(auto_error=False)
    
    async def dispatch(self, request: Request, call_next):
        # Skip authentication for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        try:
            # Extract and validate token
            token = await self._extract_token(request)
            if not token:
                raise AuthenticationError("No authentication token provided")
            
            # Validate token
            payload = await self._validate_token(token, request)
            
            # Add user info to request state
            request.state.user = payload
            request.state.token = token
            
            # Audit log
            await self._audit_log(request, payload)
            
        except AuthenticationError as e:
            return await self._handle_auth_error(request, e)
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return await self._handle_auth_error(
                request, 
                AuthenticationError("Authentication failed")
            )
        
        return await call_next(request)
    
    async def _extract_token(self, request: Request) -> Optional[str]:
        """Extract token from request"""
        # Try Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]
        
        # Try API key header
        api_key = request.headers.get(settings.auth.api_key_header_name)
        if api_key:
            return api_key
        
        # Try cookie
        token_cookie = request.cookies.get("access_token")
        if token_cookie:
            return token_cookie
        
        return None
    
    async def _validate_token(self, token: str, request: Request) -> Dict[str, Any]:
        """Validate token based on type"""
        try:
            # Try JWT validation first
            payload = security_service.decode_token(token)
            
            # Check token type
            token_type = payload.get("type")
            if token_type not in ["access", "refresh"]:
                raise AuthenticationError("Invalid token type")
            
            # Check if token is blacklisted
            if await self._is_token_blacklisted(token):
                raise AuthenticationError("Token has been revoked")
            
            # Check required permissions for endpoint
            await self._check_permissions(request, payload)
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError:
            # Try API key validation
            return await self._validate_api_key(token, request)
    
    async def _validate_api_key(self, api_key: str, request: Request) -> Dict[str, Any]:
        """Validate API key"""
        # In production, lookup API key in database
        # This is a simplified version
        if api_key.startswith("eso_"):
            # Hash the key for lookup
            hashed_key = security_service.hash_api_key(api_key)
            
            # Lookup in database (simplified)
            # api_key_record = await db.get_api_key(hashed_key)
            
            # Mock response
            return {
                "sub": "api_user",
                "type": "api_key",
                "permissions": ["read", "write"],
                "tenant_id": "default"
            }
        
        raise AuthenticationError("Invalid API key")
    
    async def _is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted"""
        # In production, check Redis
        # jti = payload.get("jti")
        # return await redis.exists(f"blacklist:{jti}")
        return False
    
    async def _check_permissions(self, request: Request, payload: Dict[str, Any]):
        """Check if user has required permissions for endpoint"""
        # Extract required permissions from route (if defined)
        required_perms = getattr(request.state, "required_permissions", [])
        if not required_perms:
            return
        
        user_perms = payload.get("permissions", [])
        
        # Check if user has all required permissions
        if not all(perm in user_perms for perm in required_perms):
            raise AuthorizationError("Insufficient permissions")
    
    async def _audit_log(self, request: Request, payload: Dict[str, Any]):
        """Log authentication event"""
        logger.info(
            "Authentication successful",
            extra={
                "user_id": payload.get("sub"),
                "token_type": payload.get("type"),
                "path": request.url.path,
                "method": request.method,
                "ip": request.client.host,
                "user_agent": request.headers.get("user-agent")
            }
        )
    
    async def _handle_auth_error(self, request: Request, error: AuthenticationError):
        """Handle authentication error"""
        from fastapi.responses import JSONResponse
        
        logger.warning(
            f"Authentication failed: {error.message}",
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
                    "timestamp": time.time()
                }
            },
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )