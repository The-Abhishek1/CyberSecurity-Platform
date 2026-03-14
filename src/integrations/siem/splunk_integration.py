import logging
import aiohttp
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SplunkIntegration:
    """Splunk SIEM integration for sending and querying security events"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = config.get("url", "https://localhost:8089")
        self.hec_token = config.get("hec_token")
        self.session = None
        logger.info("Splunk Integration initialized")
    
    async def initialize(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession()
        logger.debug("Splunk HTTP session created")
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    async def send_event(self, event: Dict[str, Any]) -> bool:
        """Send event to Splunk HEC"""
        url = f"{self.base_url}/services/collector"
        headers = {
            "Authorization": f"Splunk {self.hec_token}",
            "Content-Type": "application/json"
        }
        
        # Format event for Splunk
        splunk_event = {
            "event": event,
            "sourcetype": "_json",
            "time": datetime.utcnow().timestamp()
        }
        
        try:
            async with self.session.post(url, json=splunk_event, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("text") == "Success"
                else:
                    logger.error(f"Splunk send event failed: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Splunk send event error: {e}")
            return False
    
    async def send_alert(self, alert: Dict[str, Any]) -> bool:
        """Send alert to Splunk"""
        return await self.send_event({
            "type": "alert",
            **alert
        })
    
    async def query_events(self, query: str, earliest: str = "-24h", latest: str = "now", limit: int = 100) -> List[Dict]:
        """Query events from Splunk"""
        url = f"{self.base_url}/services/search/jobs"
        headers = {
            "Authorization": f"Bearer {self.hec_token}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        search_data = {
            "search": f"search {query} | head {limit}",
            "earliest_time": earliest,
            "latest_time": latest,
            "output_mode": "json"
        }
        
        try:
            # Create search job
            async with self.session.post(url, data=search_data, headers=headers) as response:
                if response.status != 201:
                    logger.error(f"Splunk search job creation failed: {response.status}")
                    return []
                
                job_data = await response.json()
                job_id = job_data.get("sid")
                
                if not job_id:
                    return []
                
                # Wait for job to complete
                import asyncio
                await asyncio.sleep(2)
                
                # Get results
                results_url = f"{self.base_url}/services/search/jobs/{job_id}/results"
                async with self.session.get(results_url, headers=headers) as results_response:
                    if results_response.status == 200:
                        results = await results_response.json()
                        return results.get("results", [])
        
        except Exception as e:
            logger.error(f"Splunk query error: {e}")
        
        return []
    
    async def create_alert(self, name: str, query: str, severity: str = "medium") -> bool:
        """Create alert in Splunk"""
        # Mock implementation - in production, would create saved search with alert
        logger.info(f"Created Splunk alert: {name} ({severity})")
        return True
    
    async def health_check(self) -> bool:
        """Check Splunk connection health"""
        try:
            url = f"{self.base_url}/services/server/info"
            headers = {"Authorization": f"Bearer {self.hec_token}"}
            
            async with self.session.get(url, headers=headers) as response:
                return response.status == 200
        except:
            return False