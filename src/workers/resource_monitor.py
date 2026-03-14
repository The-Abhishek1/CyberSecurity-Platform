from typing import Dict


class ResourceMonitor:
    """Monitors resource usage of workers"""
    
    def __init__(self):
        self.resources = {}
    
    async def get_worker_stats(self, worker_id: str) -> Dict:
        """Get worker statistics"""
        return {
            "cpu_usage": 0.5,
            "memory_usage": 256 * 1024 * 1024,  # 256MB
            "disk_usage": 1024 * 1024 * 1024  # 1GB
        }