from typing import Dict, Optional, List
from datetime import datetime, timedelta
from enum import Enum
from src.core.exceptions import QuotaExceededError
from src.utils.logging import logger


class QuotaType(str, Enum):
    DAILY_EXECUTIONS = "daily_executions"
    MONTHLY_EXECUTIONS = "monthly_executions"
    CONCURRENT_EXECUTIONS = "concurrent_executions"
    DAILY_COST = "daily_cost"
    MONTHLY_COST = "monthly_cost"
    TOOL_USAGE = "tool_usage"


class QuotaManager:
    """
    Enterprise quota management system
    
    Features:
    - Multi-level quotas (tenant, user, plan)
    - Time-based quotas (daily, monthly)
    - Resource-based quotas
    - Quota enforcement with grace periods
    - Quota usage tracking
    """
    
    def __init__(self):
        # Quota configurations
        self.tenant_quotas: Dict[str, Dict[QuotaType, Dict]] = {}
        self.user_quotas: Dict[str, Dict[QuotaType, Dict]] = {}
        self.plan_quotas: Dict[str, Dict[QuotaType, Dict]] = {}
        
        # Usage tracking
        self.usage: Dict[str, Dict[str, List]] = {}
        
        # Active executions count
        self.active_executions: Dict[str, int] = {}
    
    async def configure_tenant_quota(
        self,
        tenant_id: str,
        quota_type: QuotaType,
        limit: int,
        period: str = "monthly",
        grace_period: int = 0
    ):
        """Configure quota for a tenant"""
        
        if tenant_id not in self.tenant_quotas:
            self.tenant_quotas[tenant_id] = {}
        
        self.tenant_quotas[tenant_id][quota_type] = {
            "limit": limit,
            "period": period,
            "grace_period": grace_period,
            "created_at": datetime.utcnow()
        }
        
        logger.info(
            f"Configured quota for tenant {tenant_id}",
            extra={
                "tenant_id": tenant_id,
                "quota_type": quota_type.value,
                "limit": limit,
                "period": period
            }
        )
    
    async def configure_user_quota(
        self,
        user_id: str,
        quota_type: QuotaType,
        limit: int,
        period: str = "monthly",
        grace_period: int = 0
    ):
        """Configure quota for a user"""
        
        if user_id not in self.user_quotas:
            self.user_quotas[user_id] = {}
        
        self.user_quotas[user_id][quota_type] = {
            "limit": limit,
            "period": period,
            "grace_period": grace_period,
            "created_at": datetime.utcnow()
        }
    
    async def check_quota(
        self,
        tenant_id: str,
        user_id: str,
        quota_type: Optional[QuotaType] = None
    ):
        """Check if quota is available"""
        
        # Check concurrent executions first
        await self._check_concurrent_quota(tenant_id, user_id)
        
        # Check tenant quotas
        if tenant_id in self.tenant_quotas:
            for qtype, config in self.tenant_quotas[tenant_id].items():
                if quota_type and qtype != quota_type:
                    continue
                await self._check_quota_value(tenant_id, qtype, config)
        
        # Check user quotas
        if user_id in self.user_quotas:
            for qtype, config in self.user_quotas[user_id].items():
                if quota_type and qtype != quota_type:
                    continue
                await self._check_quota_value(user_id, qtype, config)
    
    async def _check_concurrent_quota(self, tenant_id: str, user_id: str):
        """Check concurrent execution quota"""
        
        tenant_concurrent = self.active_executions.get(f"tenant:{tenant_id}", 0)
        user_concurrent = self.active_executions.get(f"user:{user_id}", 0)
        
        # Check tenant concurrent limit
        if tenant_id in self.tenant_quotas:
            config = self.tenant_quotas[tenant_id].get(QuotaType.CONCURRENT_EXECUTIONS)
            if config and tenant_concurrent >= config["limit"]:
                raise QuotaExceededError(
                    f"Tenant {tenant_id} has reached concurrent execution limit",
                    quota_type=QuotaType.CONCURRENT_EXECUTIONS
                )
        
        # Check user concurrent limit
        if user_id in self.user_quotas:
            config = self.user_quotas[user_id].get(QuotaType.CONCURRENT_EXECUTIONS)
            if config and user_concurrent >= config["limit"]:
                raise QuotaExceededError(
                    f"User {user_id} has reached concurrent execution limit",
                    quota_type=QuotaType.CONCURRENT_EXECUTIONS
                )
    
    async def _check_quota_value(
        self,
        entity_id: str,
        quota_type: QuotaType,
        config: Dict
    ):
        """Check if a specific quota is exceeded"""
        
        usage = await self._get_usage(entity_id, quota_type, config["period"])
        
        if usage >= config["limit"]:
            # Check grace period
            if config["grace_period"] > 0:
                grace_used = await self._get_grace_usage(entity_id, quota_type)
                if grace_used < config["grace_period"]:
                    return  # Allow with grace period
            
            raise QuotaExceededError(
                f"Quota exceeded for {entity_id}: {quota_type.value}",
                quota_type=quota_type
            )
    
    async def _get_usage(self, entity_id: str, quota_type: QuotaType, period: str) -> int:
        """Get current usage for a quota"""
        
        key = f"{entity_id}:{quota_type.value}"
        
        if key not in self.usage:
            return 0
        
        now = datetime.utcnow()
        cutoff = self._get_period_cutoff(now, period)
        
        # Count usage within period
        usage = 0
        for record in self.usage[key]:
            if record["timestamp"] >= cutoff:
                usage += record["amount"]
        
        return usage
    
    async def _get_grace_usage(self, entity_id: str, quota_type: QuotaType) -> int:
        """Get grace period usage"""
        # Track grace usage separately
        return 0
    
    def _get_period_cutoff(self, now: datetime, period: str) -> datetime:
        """Get cutoff date for period"""
        if period == "daily":
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "weekly":
            return now - timedelta(days=now.weekday())
        elif period == "monthly":
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == "yearly":
            return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            return now - timedelta(days=30)  # Default monthly
    
    async def increment_usage(
        self,
        entity_id: str,
        quota_type: QuotaType,
        amount: int = 1
    ):
        """Increment usage counter"""
        
        key = f"{entity_id}:{quota_type.value}"
        
        if key not in self.usage:
            self.usage[key] = []
        
        self.usage[key].append({
            "timestamp": datetime.utcnow(),
            "amount": amount
        })
        
        # Cleanup old records
        cutoff = datetime.utcnow() - timedelta(days=31)
        self.usage[key] = [
            record for record in self.usage[key]
            if record["timestamp"] >= cutoff
        ]
    
    async def start_execution(self, tenant_id: str, user_id: str):
        """Track start of execution"""
        
        self.active_executions[f"tenant:{tenant_id}"] = \
            self.active_executions.get(f"tenant:{tenant_id}", 0) + 1
        self.active_executions[f"user:{user_id}"] = \
            self.active_executions.get(f"user:{user_id}", 0) + 1
        
        # Increment daily/monthly counters
        await self.increment_usage(f"tenant:{tenant_id}", QuotaType.DAILY_EXECUTIONS)
        await self.increment_usage(f"tenant:{tenant_id}", QuotaType.MONTHLY_EXECUTIONS)
        await self.increment_usage(f"user:{user_id}", QuotaType.DAILY_EXECUTIONS)
        await self.increment_usage(f"user:{user_id}", QuotaType.MONTHLY_EXECUTIONS)
    
    async def end_execution(self, tenant_id: str, user_id: str):
        """Track end of execution"""
        
        tenant_key = f"tenant:{tenant_id}"
        user_key = f"user:{user_id}"
        
        if tenant_key in self.active_executions:
            self.active_executions[tenant_key] = max(0, self.active_executions[tenant_key] - 1)
        
        if user_key in self.active_executions:
            self.active_executions[user_key] = max(0, self.active_executions[user_key] - 1)
    
    async def get_quota_status(
        self,
        tenant_id: str,
        user_id: str
    ) -> Dict[str, Dict]:
        """Get quota status for tenant and user"""
        
        status = {
            "tenant": {},
            "user": {}
        }
        
        # Get tenant quotas
        if tenant_id in self.tenant_quotas:
            for qtype, config in self.tenant_quotas[tenant_id].items():
                usage = await self._get_usage(f"tenant:{tenant_id}", qtype, config["period"])
                status["tenant"][qtype.value] = {
                    "limit": config["limit"],
                    "usage": usage,
                    "remaining": config["limit"] - usage,
                    "period": config["period"]
                }
        
        # Get user quotas
        if user_id in self.user_quotas:
            for qtype, config in self.user_quotas[user_id].items():
                usage = await self._get_usage(f"user:{user_id}", qtype, config["period"])
                status["user"][qtype.value] = {
                    "limit": config["limit"],
                    "usage": usage,
                    "remaining": config["limit"] - usage,
                    "period": config["period"]
                }
        
        # Add concurrent status
        status["concurrent"] = {
            "tenant": self.active_executions.get(f"tenant:{tenant_id}", 0),
            "user": self.active_executions.get(f"user:{user_id}", 0)
        }
        
        return status