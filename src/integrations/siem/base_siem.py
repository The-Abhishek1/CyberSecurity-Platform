from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
import aiohttp
import json


class BaseSIEMIntegration(ABC):
    """Base class for SIEM integrations"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.session = None
        self.base_url = config.get("url")
        self.api_key = config.get("api_key")
    
    async def initialize(self):
        """Initialize SIEM connection"""
        self.session = aiohttp.ClientSession()
    
    async def close(self):
        """Close SIEM connection"""
        if self.session:
            await self.session.close()
    
    @abstractmethod
    async def send_event(self, event: Dict) -> bool:
        """Send event to SIEM"""
        pass
    
    @abstractmethod
    async def query_events(self, query: str) -> List[Dict]:
        """Query events from SIEM"""
        pass
    
    async def send_alert(self, alert: Dict) -> bool:
        """Send alert to SIEM"""
        return await self.send_event({
            "type": "alert",
            "timestamp": datetime.utcnow().isoformat(),
            **alert
        })


class SplunkIntegration(BaseSIEMIntegration):
    """Splunk SIEM integration"""
    
    async def send_event(self, event: Dict) -> bool:
        url = f"{self.base_url}/services/collector"
        headers = {
            "Authorization": f"Splunk {self.config.get('hec_token')}",
            "Content-Type": "application/json"
        }
        
        try:
            async with self.session.post(url, json=event, headers=headers) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Splunk send event failed: {e}")
            return False
    
    async def query_events(self, query: str) -> List[Dict]:
        url = f"{self.base_url}/services/search/jobs"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        # Create search job
        search_data = {
            "search": f"search {query}",
            "output_mode": "json"
        }
        
        try:
            async with self.session.post(url, data=search_data, headers=headers) as response:
                job_data = await response.json()
                job_id = job_data.get("sid")
                
                # Get results
                results_url = f"{url}/{job_id}/results"
                async with self.session.get(results_url, headers=headers) as results_response:
                    results = await results_response.json()
                    return results.get("results", [])
        except Exception as e:
            logger.error(f"Splunk query failed: {e}")
            return []


class QRadarIntegration(BaseSIEMIntegration):
    """IBM QRadar integration"""
    
    async def send_event(self, event: Dict) -> bool:
        url = f"{self.base_url}/api/offenses"
        headers = {
            "SEC": self.api_key,
            "Content-Type": "application/json"
        }
        
        try:
            async with self.session.post(url, json=event, headers=headers) as response:
                return response.status == 201
        except Exception as e:
            logger.error(f"QRadar send event failed: {e}")
            return False
    
    async def query_events(self, query: str) -> List[Dict]:
        url = f"{self.base_url}/api/ariel/searches"
        headers = {"SEC": self.api_key}
        
        try:
            # Create search
            async with self.session.post(url, params={"query_expression": query}, headers=headers) as response:
                search_data = await response.json()
                search_id = search_data.get("search_id")
                
                # Get results
                results_url = f"{url}/{search_id}/results"
                async with self.session.get(results_url, headers=headers) as results_response:
                    return await results_response.json()
        except Exception as e:
            logger.error(f"QRadar query failed: {e}")
            return []