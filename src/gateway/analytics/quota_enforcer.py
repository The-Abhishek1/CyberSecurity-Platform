from typing import Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict


class QuotaEnforcer:
    """Enforces API quotas and limits"""
    
    def __init__(self):
        self.quotas = {}
        self.usage = defaultdict(list)
    
    async def set_quota(self, tenant_id: str, quota_type: str, limit: int, period: str = "day"):
        """Set quota for tenant"""
        
        if tenant_id not in self.quotas:
            self.quotas[tenant_id] = {}
        
        self.quotas[tenant_id][quota_type] = {
            "limit": limit,
            "period": period,
            "reset_at": datetime.utcnow()
        }
    
    async def check_quota(self, tenant_id: str, quota_type: str, amount: int = 1) -> bool:
        """Check if quota is available"""
        
        if tenant_id not in self.quotas or quota_type not in self.quotas[tenant_id]:
            return True
        
        quota = self.quotas[tenant_id][quota_type]
        
        # Reset if period has passed
        now = datetime.utcnow()
        if self._should_reset(quota["reset_at"], quota["period"]):
            self.usage[f"{tenant_id}:{quota_type}"] = []
            quota["reset_at"] = now
        
        current_usage = len(self.usage[f"{tenant_id}:{quota_type}"])
        
        if current_usage + amount > quota["limit"]:
            return False
        
        # Record usage
        for _ in range(amount):
            self.usage[f"{tenant_id}:{quota_type}"].append(now)
        
        return True
    
    def _should_reset(self, reset_at: datetime, period: str) -> bool:
        """Check if quota should reset"""
        now = datetime.utcnow()
        
        if period == "day":
            return reset_at.date() < now.date()
        elif period == "hour":
            return reset_at.hour != now.hour or reset_at.date() < now.date()
        elif period == "month":
            return reset_at.month != now.month or reset_at.year < now.year
        
        return False
    
    async def get_quota_status(self, tenant_id: str) -> Dict:
        """Get quota status for tenant"""
        
        status = {}
        
        if tenant_id in self.quotas:
            for quota_type, quota in self.quotas[tenant_id].items():
                current_usage = len(self.usage[f"{tenant_id}:{quota_type}"])
                status[quota_type] = {
                    "limit": quota["limit"],
                    "used": current_usage,
                    "remaining": quota["limit"] - current_usage,
                    "period": quota["period"]
                }
        
        return status
