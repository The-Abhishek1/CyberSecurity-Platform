from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from src.utils.logging import logger

class UsageAggregator:
    """
    Tenant Usage Aggregator
    
    Features:
    - Real-time usage tracking
    - Multi-dimensional aggregation
    - Usage forecasting
    - Billing integration
    """
    
    def __init__(self):
        # Usage data: tenant_id -> resource -> list of usage events
        self.usage: Dict[str, Dict[str, List]] = defaultdict(lambda: defaultdict(list))
        
        # Aggregated usage
        self.aggregated: Dict[str, Dict] = defaultdict(lambda: defaultdict(float))
        
        logger.info("Usage Aggregator initialized")
    
    async def track_usage(
        self,
        tenant_id: str,
        resource: str,
        amount: float,
        metadata: Optional[Dict] = None
    ):
        """Track resource usage"""
        
        usage_event = {
            "timestamp": datetime.utcnow(),
            "tenant_id": tenant_id,
            "resource": resource,
            "amount": amount,
            "metadata": metadata or {}
        }
        
        self.usage[tenant_id][resource].append(usage_event)
        
        # Update aggregated usage
        date_key = datetime.utcnow().strftime("%Y-%m-%d")
        self.aggregated[tenant_id][f"{resource}:{date_key}"] += amount
        
        # Limit history
        if len(self.usage[tenant_id][resource]) > 10000:
            self.usage[tenant_id][resource] = self.usage[tenant_id][resource][-10000:]
    
    async def get_tenant_usage(
        self,
        tenant_id: str,
        resource: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict:
        """Get tenant usage"""
        
        if not start_time:
            start_time = datetime.utcnow() - timedelta(days=30)
        if not end_time:
            end_time = datetime.utcnow()
        
        usage_data = {}
        
        resources = [resource] if resource else self.usage[tenant_id].keys()
        
        for res in resources:
            events = [
                e for e in self.usage[tenant_id][res]
                if start_time <= e["timestamp"] <= end_time
            ]
            
            total = sum(e["amount"] for e in events)
            
            # Aggregate by day
            by_day = defaultdict(float)
            for e in events:
                day = e["timestamp"].strftime("%Y-%m-%d")
                by_day[day] += e["amount"]
            
            usage_data[res] = {
                "total": total,
                "by_day": dict(by_day),
                "count": len(events)
            }
        
        return usage_data
    
    async def get_all_tenants_usage(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict:
        """Get usage for all tenants"""
        
        usage = {}
        for tenant_id in self.usage:
            usage[tenant_id] = await self.get_tenant_usage(tenant_id, start_time, end_time)
        
        return usage
    
    async def get_usage_summary(
        self,
        tenant_id: str,
        period: str = "monthly"
    ) -> Dict:
        """Get usage summary for tenant"""
        
        now = datetime.utcnow()
        
        if period == "daily":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "weekly":
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "monthly":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            start = now - timedelta(days=30)
        
        usage = await self.get_tenant_usage(tenant_id, start_time=start)
        
        summary = {
            "tenant_id": tenant_id,
            "period": period,
            "start_date": start.isoformat(),
            "end_date": now.isoformat(),
            "total_cost": 0,
            "resources": {}
        }
        
        for resource, data in usage.items():
            # Calculate cost based on resource type
            cost = await self._calculate_cost(resource, data["total"])
            summary["resources"][resource] = {
                "usage": data["total"],
                "cost": cost
            }
            summary["total_cost"] += cost
        
        return summary
    
    async def _calculate_cost(self, resource: str, amount: float) -> float:
        """Calculate cost for resource usage"""
        
        # Pricing model (simplified)
        pricing = {
            "executions": 0.01,  # $0.01 per execution
            "storage_gb": 0.10,   # $0.10 per GB-month
            "api_calls": 0.001,   # $0.001 per 1000 calls
            "compute_hours": 0.05  # $0.05 per compute hour
        }
        
        return amount * pricing.get(resource, 0)