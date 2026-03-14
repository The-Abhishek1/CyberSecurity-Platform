
from typing import Dict, Any
from datetime import datetime, timedelta


class OperationalDashboard:
    """Operational dashboard for system health and performance"""
    
    async def generate(self,
                       tenant_id: str,
                       hours: int = 24) -> Dict[str, Any]:
        """Generate operational dashboard"""
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # Mock data - in production, would query actual metrics
        return {
            "tenant_id": tenant_id,
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "system_health": {
                "api_status": "healthy",
                "database_status": "healthy",
                "redis_status": "healthy",
                "rabbitmq_status": "healthy",
                "worker_pools": {
                    "nmap": {"active": 5, "total": 10, "utilization": 0.45},
                    "nuclei": {"active": 3, "total": 8, "utilization": 0.30},
                    "sqlmap": {"active": 2, "total": 5, "utilization": 0.25}
                }
            },
            "performance": {
                "api_latency_p95_ms": 245,
                "api_latency_p99_ms": 512,
                "error_rate": 0.02,
                "requests_per_second": 45,
                "active_executions": 12,
                "queue_depth": 8
            },
            "resource_usage": {
                "cpu_usage": 0.65,
                "memory_usage": 0.72,
                "disk_usage": 0.48,
                "network_io_mbps": 125
            },
            "recent_errors": [
                {
                    "timestamp": (end_time - timedelta(minutes=5)).isoformat(),
                    "type": "timeout",
                    "component": "worker",
                    "message": "Nmap scan timed out after 300s"
                },
                {
                    "timestamp": (end_time - timedelta(minutes=15)).isoformat(),
                    "type": "connection",
                    "component": "database",
                    "message": "Connection pool exhausted"
                }
            ],
            "sla_compliance": {
                "critical": 0.98,
                "high": 0.95,
                "medium": 0.92,
                "low": 0.88
            },
            "throughput_trend": [
                {"time": (end_time - timedelta(minutes=i*30)).strftime("%H:%M"),
                 "requests": 30 + i % 10 * 5} for i in range(48)
            ]
        }