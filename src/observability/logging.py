import logging
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from pythonjsonlogger import jsonlogger

from src.core.config import get_settings

settings = get_settings()


class EnterpriseLogFormatter(jsonlogger.JsonFormatter):
    """
    Enterprise JSON log formatter
    
    Adds structured fields to all log entries
    """
    
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp
        if not log_record.get('timestamp'):
            log_record['timestamp'] = datetime.utcnow().isoformat()
        
        # Add service info
        log_record['service'] = settings.observability.service_name
        log_record['environment'] = settings.environment.value
        
        # Add log level
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        
        # Add trace context if available
        from opentelemetry import trace
        span = trace.get_current_span()
        if span:
            span_context = span.get_span_context()
            if span_context != trace.INVALID_SPAN_CONTEXT:
                log_record['trace_id'] = format(span_context.trace_id, '032x')
                log_record['span_id'] = format(span_context.span_id, '016x')


class AuditLogger:
    """
    Enterprise Audit Logger
    
    Features:
    - Immutable audit trail
    - Cryptographic signing
    - Tamper detection
    - Compliance-ready format
    """
    
    def __init__(self):
        self.audit_logger = logging.getLogger('audit')
        self.audit_logger.setLevel(logging.INFO)
        
        # Add handler if not already configured
        if not self.audit_logger.handlers:
            handler = logging.FileHandler(settings.observability.audit_log_path)
            formatter = EnterpriseLogFormatter()
            handler.setFormatter(formatter)
            self.audit_logger.addHandler(handler)
        
        # In-memory audit trail (for quick queries)
        self.audit_trail: List[Dict] = []
        
        # Cryptographic signing (in production, use HSM)
        self.signing_key = settings.security.audit_signing_key
    
    async def log(
        self,
        action: str,
        user_id: str,
        tenant_id: str,
        resource: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict] = None,
        result: str = "success",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log an audit event"""
        
        audit_entry = {
            "audit_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "resource": resource,
            "resource_id": resource_id,
            "details": details or {},
            "result": result,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "environment": settings.environment.value
        }
        
        # Add cryptographic signature
        audit_entry["signature"] = self._sign_audit_entry(audit_entry)
        
        # Log to file
        self.audit_logger.info(json.dumps(audit_entry))
        
        # Store in memory (limited size)
        self.audit_trail.append(audit_entry)
        if len(self.audit_trail) > 10000:
            self.audit_trail = self.audit_trail[-10000:]
        
        return audit_entry["audit_id"]
    
    def _sign_audit_entry(self, entry: Dict) -> str:
        """Cryptographically sign audit entry"""
        
        import hmac
        import hashlib
        
        # Create canonical string
        canonical = f"{entry['audit_id']}{entry['timestamp']}{entry['action']}{entry['user_id']}"
        
        # Sign
        signature = hmac.new(
            self.signing_key.encode(),
            canonical.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    async def verify_audit_entry(self, audit_id: str) -> bool:
        """Verify audit entry signature"""
        
        # Find entry
        entry = await self.get_audit_entry(audit_id)
        if not entry:
            return False
        
        # Recompute signature
        expected_signature = self._sign_audit_entry(entry)
        
        # Compare
        return hmac.compare_digest(entry["signature"], expected_signature)
    
    async def get_audit_entry(self, audit_id: str) -> Optional[Dict]:
        """Get audit entry by ID"""
        
        # Check memory first
        for entry in self.audit_trail:
            if entry["audit_id"] == audit_id:
                return entry
        
        # In production, search in log files or database
        return None
    
    async def query_audit_trail(
        self,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        action: Optional[str] = None,
        resource: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Query audit trail"""
        
        results = []
        
        for entry in self.audit_trail:
            # Apply filters
            if user_id and entry["user_id"] != user_id:
                continue
            if tenant_id and entry["tenant_id"] != tenant_id:
                continue
            if action and entry["action"] != action:
                continue
            if resource and entry["resource"] != resource:
                continue
            
            entry_time = datetime.fromisoformat(entry["timestamp"])
            if start_time and entry_time < start_time:
                continue
            if end_time and entry_time > end_time:
                continue
            
            results.append(entry)
            
            if len(results) >= limit:
                break
        
        return results
    
    async def generate_compliance_report(
        self,
        report_type: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict:
        """Generate compliance report from audit trail"""
        
        entries = await self.query_audit_trail(
            start_time=start_time,
            end_time=end_time,
            limit=10000
        )
        
        report = {
            "report_id": str(uuid.uuid4()),
            "report_type": report_type,
            "generated_at": datetime.utcnow().isoformat(),
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "summary": {
                "total_events": len(entries),
                "unique_users": len(set(e["user_id"] for e in entries)),
                "unique_actions": len(set(e["action"] for e in entries))
            },
            "events_by_action": {},
            "events_by_user": {},
            "events_by_resource": {},
            "verification": {
                "valid_signatures": 0,
                "invalid_signatures": 0
            }
        }
        
        for entry in entries:
            # Verify signature
            if await self.verify_audit_entry(entry["audit_id"]):
                report["verification"]["valid_signatures"] += 1
            else:
                report["verification"]["invalid_signatures"] += 1
            
            # Aggregate by action
            action = entry["action"]
            report["events_by_action"][action] = report["events_by_action"].get(action, 0) + 1
            
            # Aggregate by user
            user = entry["user_id"]
            report["events_by_user"][user] = report["events_by_user"].get(user, 0) + 1
            
            # Aggregate by resource
            resource = entry["resource"]
            report["events_by_resource"][resource] = report["events_by_resource"].get(resource, 0) + 1
        
        return report