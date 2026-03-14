
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
import uuid

# Configure audit logger
audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)

# Add console handler if not already configured
if not audit_logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    audit_logger.addHandler(console_handler)

class AuditLogger:
    """Enterprise audit logger for tracking all security-relevant events"""
    
    def __init__(self):
        self.audit_trail = []
        
    async def log(self, action: str, user_id: str, tenant_id: str, 
                  resource: str, details: Optional[Dict] = None):
        """Log an audit event"""
        audit_entry = {
            "audit_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "resource": resource,
            "details": details or {}
        }
        
        # Log to file/console
        audit_logger.info(json.dumps(audit_entry))
        
        # Store in memory (for testing/quick access)
        self.audit_trail.append(audit_entry)
        if len(self.audit_trail) > 1000:
            self.audit_trail = self.audit_trail[-1000:]
            
        return audit_entry["audit_id"]
    
    async def query(self, user_id: Optional[str] = None, 
                    action: Optional[str] = None,
                    start_time: Optional[datetime] = None,
                    limit: int = 100) -> list:
        """Query audit trail"""
        results = self.audit_trail.copy()
        
        if user_id:
            results = [r for r in results if r["user_id"] == user_id]
        if action:
            results = [r for r in results if r["action"] == action]
        if start_time:
            results = [r for r in results 
                      if datetime.fromisoformat(r["timestamp"]) >= start_time]
            
        return results[:limit]

# Singleton instance
audit_logger_instance = AuditLogger()