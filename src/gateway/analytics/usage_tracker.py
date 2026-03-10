from typing import Dict, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict


class UsageTracker:
    """
    API Usage Tracker
    
    Features:
    - Real-time usage tracking
    - Per-tenant analytics
    - Per-API analytics
    - Rate limiting
    - Usage forecasting
    - Billing integration
    """
    
    def __init__(self):
        # Usage data: tenant_id -> api_id -> list of calls
        self.usage: Dict[str, Dict[str, List]] = defaultdict(lambda: defaultdict(list))
        
        # Aggregated stats
        self.stats: Dict[str, Dict] = defaultdict(lambda: {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_duration_ms": 0,
            "avg_duration_ms": 0,
            "calls_by_hour": defaultdict(int),
            "calls_by_api": defaultdict(int)
        })
        
        logger.info("Usage Tracker initialized")
    
    async def track_call(
        self,
        api_id: str,
        tenant_id: str,
        api_key: str,
        status_code: int,
        duration_ms: float,
        error: Optional[str] = None
    ):
        """Track API call"""
        
        call = {
            "timestamp": datetime.utcnow(),
            "api_id": api_id,
            "tenant_id": tenant_id,
            "api_key": api_key,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "error": error
        }
        
        # Store in tenant usage
        self.usage[tenant_id][api_id].append(call)
        
        # Update stats
        stats = self.stats[tenant_id]
        stats["total_calls"] += 1
        
        if 200 <= status_code < 300:
            stats["successful_calls"] += 1
        else:
            stats["failed_calls"] += 1
        
        stats["total_duration_ms"] += duration_ms
        stats["avg_duration_ms"] = stats["total_duration_ms"] / stats["total_calls"]
        
        hour_key = datetime.utcnow().strftime("%Y-%m-%d %H:00")
        stats["calls_by_hour"][hour_key] += 1
        stats["calls_by_api"][api_id] += 1
        
        # Limit history per tenant (keep last 10,000 calls)
        if len(self.usage[tenant_id][api_id]) > 10000:
            self.usage[tenant_id][api_id] = self.usage[tenant_id][api_id][-10000:]
    
    async def check_rate_limit(
        self,
        api_id: str,
        tenant_id: str,
        api_key: str,
        limit: str
    ) -> bool:
        """Check rate limit for API"""
        
        # Parse limit
        try:
            count, period = limit.split("/")
            max_requests = int(count)
            period_seconds = {
                "second": 1, "minute": 60, "hour": 3600, "day": 86400
            }.get(period, 60)
        except:
            max_requests = 100
            period_seconds = 60
        
        # Get recent calls
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=period_seconds)
        
        recent_calls = [
            call for call in self.usage[tenant_id][api_id]
            if call["timestamp"] > cutoff
        ]
        
        return len(recent_calls) < max_requests
    
    async def get_stats(
        self,
        api_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict:
        """Get usage statistics"""
        
        if not start_time:
            start_time = datetime.utcnow() - timedelta(days=30)
        if not end_time:
            end_time = datetime.utcnow()
        
        stats = {
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "tenants": {}
        }
        
        tenants = [tenant_id] if tenant_id else self.usage.keys()
        
        for tid in tenants:
            tenant_stats = self.stats.get(tid, {}).copy()
            
            # Filter by API if specified
            if api_id:
                tenant_stats["calls_by_api"] = {
                    api_id: tenant_stats["calls_by_api"].get(api_id, 0)
                }
                
                # Filter calls
                tenant_stats["total_calls"] = tenant_stats["calls_by_api"][api_id]
            
            # Filter by time
            tenant_stats["calls_by_hour"] = {
                hour: count for hour, count in tenant_stats.get("calls_by_hour", {}).items()
                if start_time <= datetime.strptime(hour, "%Y-%m-%d %H:00") <= end_time
            }
            
            stats["tenants"][tid] = tenant_stats
        
        return stats
    
    async def get_usage_forecast(self, tenant_id: str, days: int = 30) -> Dict:
        """Forecast future usage"""
        
        tenant_stats = self.stats.get(tenant_id, {})
        
        if not tenant_stats:
            return {}
        
        # Simple linear projection based on last 30 days
        daily_avg = tenant_stats["total_calls"] / 30
        
        forecast = {
            "tenant_id": tenant_id,
            "current_daily_avg": daily_avg,
            "projected_next_30_days": daily_avg * 30,
            "projected_next_90_days": daily_avg * 90,
            "confidence": 0.8  # Simple confidence score
        }
        
        return forecast
    
    async def get_top_apis(self, tenant_id: str, limit: int = 10) -> List[Dict]:
        """Get most used APIs for tenant"""
        
        tenant_stats = self.stats.get(tenant_id, {})
        calls_by_api = tenant_stats.get("calls_by_api", {})
        
        top_apis = sorted(
            [{"api_id": api, "calls": count} for api, count in calls_by_api.items()],
            key=lambda x: x["calls"],
            reverse=True
        )[:limit]
        
        return top_apis