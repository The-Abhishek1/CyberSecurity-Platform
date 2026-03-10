from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio


class RetentionPolicy:
    """Data retention policy definition"""
    
    def __init__(
        self,
        data_type: str,
        retention_days: int,
        archive_after_days: Optional[int] = None,
        delete_after_days: Optional[int] = None,
        compliance_tags: Optional[List[str]] = None
    ):
        self.data_type = data_type
        self.retention_days = retention_days
        self.archive_after_days = archive_after_days
        self.delete_after_days = delete_after_days
        self.compliance_tags = compliance_tags or []


class DataRetentionManager:
    """
    Data Retention Manager
    
    Features:
    - Policy-based retention
    - Automated archiving
    - Secure deletion
    - Compliance tracking
    """
    
    def __init__(self):
        self.policies: Dict[str, RetentionPolicy] = {}
        self.retention_log: List[Dict] = []
        
        # Load default policies
        self._load_default_policies()
        
        # Start retention worker
        asyncio.create_task(self._retention_worker())
        
        logger.info("Data Retention Manager initialized")
    
    def _load_default_policies(self):
        """Load default retention policies"""
        
        self.add_policy(RetentionPolicy(
            data_type="execution_logs",
            retention_days=90,
            archive_after_days=30,
            delete_after_days=365,
            compliance_tags=["soc2", "gdpr"]
        ))
        
        self.add_policy(RetentionPolicy(
            data_type="audit_logs",
            retention_days=365 * 7,  # 7 years
            archive_after_days=365,
            delete_after_days=None,  # Keep forever
            compliance_tags=["soc2", "hipaa", "pci_dss"]
        ))
        
        self.add_policy(RetentionPolicy(
            data_type="scan_results",
            retention_days=365,
            archive_after_days=90,
            delete_after_days=730,  # 2 years
            compliance_tags=["gdpr"]
        ))
        
        self.add_policy(RetentionPolicy(
            data_type="findings",
            retention_days=365 * 2,  # 2 years
            archive_after_days=365,
            delete_after_days=365 * 3,  # 3 years
            compliance_tags=["soc2", "pci_dss"]
        ))
        
        self.add_policy(RetentionPolicy(
            data_type="metrics",
            retention_days=30,
            archive_after_days=7,
            delete_after_days=90,
            compliance_tags=[]
        ))
    
    def add_policy(self, policy: RetentionPolicy):
        """Add retention policy"""
        self.policies[policy.data_type] = policy
        logger.info(f"Added retention policy for {policy.data_type}")
    
    async def check_retention(self, data_type: str, created_at: datetime) -> Dict:
        """Check retention requirements for data"""
        
        policy = self.policies.get(data_type)
        if not policy:
            return {"action": "keep", "reason": "No policy defined"}
        
        age_days = (datetime.utcnow() - created_at).days
        
        if policy.delete_after_days and age_days > policy.delete_after_days:
            return {
                "action": "delete",
                "reason": f"Exceeds retention period of {policy.delete_after_days} days"
            }
        elif policy.archive_after_days and age_days > policy.archive_after_days:
            return {
                "action": "archive",
                "reason": f"Exceeds archive threshold of {policy.archive_after_days} days"
            }
        
        return {"action": "keep", "reason": "Within retention period"}
    
    async def _retention_worker(self):
        """Background worker to enforce retention policies"""
        
        while True:
            try:
                await self._enforce_retention()
                await asyncio.sleep(86400)  # Run daily
            except Exception as e:
                logger.error(f"Retention worker error: {e}")
                await asyncio.sleep(3600)
    
    async def _enforce_retention(self):
        """Enforce retention policies"""
        
        logger.info("Running retention enforcement")
        
        # In production, this would query actual data stores
        # For demonstration, log the enforcement
        
        for data_type, policy in self.policies.items():
            logger.info(f"Checking retention for {data_type}")
            
            # Log retention action
            self.retention_log.append({
                "timestamp": datetime.utcnow().isoformat(),
                "data_type": data_type,
                "action": "checked",
                "policy": {
                    "retention_days": policy.retention_days,
                    "archive_after_days": policy.archive_after_days,
                    "delete_after_days": policy.delete_after_days
                }
            })
    
    async def get_retention_report(self, data_type: Optional[str] = None) -> Dict:
        """Get retention compliance report"""
        
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "policies": {},
            "compliance": {}
        }
        
        for dt, policy in self.policies.items():
            if data_type and dt != data_type:
                continue
            
            report["policies"][dt] = {
                "retention_days": policy.retention_days,
                "archive_after_days": policy.archive_after_days,
                "delete_after_days": policy.delete_after_days,
                "compliance_tags": policy.compliance_tags
            }
            
            # Check compliance
            report["compliance"][dt] = {
                "compliant": True,  # In production, check actual compliance
                "last_check": datetime.utcnow().isoformat(),
                "data_count": 0
            }
        
        return report