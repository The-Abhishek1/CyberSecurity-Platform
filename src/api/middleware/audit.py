
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import json
from datetime import datetime

# Configure audit logger
audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)

# Add handler if not already configured
if not audit_logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - AUDIT - %(message)s')
    handler.setFormatter(formatter)
    audit_logger.addHandler(handler)


class AuditMiddleware(BaseHTTPMiddleware):
    """Audit logging middleware for tracking all requests"""
    
    async def dispatch(self, request: Request, call_next):
        # Capture request details
        request_id = getattr(request.state, "request_id", "unknown")
        user = getattr(request.state, "user", {"sub": "anonymous"})
        
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "user": user.get("sub", "anonymous"),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent")
        }
        
        # Log before processing
        audit_logger.info(f"REQUEST: {json.dumps(audit_entry)}")
        
        # Process request
        response = await call_next(request)
        
        # Add response details
        audit_entry["status_code"] = response.status_code
        audit_entry["duration"] = getattr(request.state, "duration", 0)
        
        # Log after processing
        audit_logger.info(f"RESPONSE: {json.dumps(audit_entry)}")
        
        return response