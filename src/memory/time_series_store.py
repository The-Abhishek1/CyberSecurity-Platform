

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json


class TimeSeriesStore:
    """
    Time Series Store for metrics and time-based data
    
    In production, this would connect to InfluxDB, Prometheus, or similar.
    For development, we use an in-memory mock.
    """
    
    def __init__(self):
        self.data: Dict[str, List[Dict[str, Any]]] = {}
        
    async def write(
        self,
        measurement: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
        timestamp: Optional[datetime] = None
    ):
        """Write a data point to time series"""
        
        if measurement not in self.data:
            self.data[measurement] = []
        
        point = {
            "timestamp": (timestamp or datetime.utcnow()).isoformat(),
            "value": value,
            "tags": tags or {}
        }
        
        self.data[measurement].append(point)
        
        # Keep only last 1000 points per measurement
        if len(self.data[measurement]) > 1000:
            self.data[measurement] = self.data[measurement][-1000:]
    
    async def query(
        self,
        measurement: str,
        start_time: datetime,
        end_time: datetime,
        tags: Optional[Dict[str, str]] = None,
        aggregation: str = "mean"
    ) -> List[Dict[str, Any]]:
        """Query time series data"""
        
        if measurement not in self.data:
            return []
        
        results = []
        points = self.data[measurement]
        
        for point in points:
            point_time = datetime.fromisoformat(point["timestamp"])
            
            if start_time <= point_time <= end_time:
                # Check tags
                if tags:
                    match = True
                    for key, value in tags.items():
                        if point["tags"].get(key) != value:
                            match = False
                            break
                    if not match:
                        continue
                
                results.append(point)
        
        return results
    
    async def get_latest(
        self,
        measurement: str,
        tags: Optional[Dict[str, str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Get latest data point"""
        
        if measurement not in self.data or not self.data[measurement]:
            return None
        
        # Get latest by timestamp
        points = self.data[measurement]
        
        if tags:
            filtered = []
            for point in points:
                match = True
                for key, value in tags.items():
                    if point["tags"].get(key) != value:
                        match = False
                        break
                if match:
                    filtered.append(point)
            points = filtered
        
        if not points:
            return None
        
        # Sort by timestamp and return latest
        return sorted(points, key=lambda x: x["timestamp"], reverse=True)[0]
    
    async def get_stats(
        self,
        measurement: str,
        time_range: timedelta = timedelta(hours=1)
    ) -> Dict[str, float]:
        """Get statistics for a measurement"""
        
        if measurement not in self.data or not self.data[measurement]:
            return {}
        
        now = datetime.utcnow()
        start = now - time_range
        
        points = [
            p for p in self.data[measurement]
            if datetime.fromisoformat(p["timestamp"]) >= start
        ]
        
        if not points:
            return {}
        
        values = [p["value"] for p in points]
        
        return {
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "count": len(values)
        }
    
    async def list_measurements(self) -> List[str]:
        """List all measurements"""
        return list(self.data.keys())
    

    async def record_event(
        self,
        event_type: str,
        tags: Dict[str, str],
        value: float = 1.0
    ):
        """
        Record an event in time series
        """
        await self.write(
            measurement=event_type,
            value=value,
            tags=tags,
            timestamp=datetime.utcnow()
        )