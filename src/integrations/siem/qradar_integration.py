


import logging
import aiohttp
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class QRadarIntegration:
    """IBM QRadar SIEM integration"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = config.get("url", "https://localhost")
        self.api_key = config.get("api_key")
        self.session = None
        logger.info("QRadar Integration initialized")
    
    async def initialize(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession()
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    async def send_event(self, event: Dict[str, Any]) -> bool:
        """Send event to QRadar"""
        url = f"{self.base_url}/api/offenses"
        headers = {
            "SEC": self.api_key,
            "Content-Type": "application/json"
        }
        
        try:
            async with self.session.post(url, json=event, headers=headers) as response:
                return response.status in [200, 201]
        except Exception as e:
            logger.error(f"QRadar send event error: {e}")
            return False
    
    async def query_events(self, query: str) -> List[Dict]:
        """Query events from QRadar"""
        url = f"{self.base_url}/api/ariel/searches"
        headers = {"SEC": self.api_key}
        
        try:
            # Create search
            async with self.session.post(url, params={"query_expression": query}, headers=headers) as response:
                if response.status != 201:
                    return []
                
                search_data = await response.json()
                search_id = search_data.get("search_id")
                
                if not search_id:
                    return []
                
                # Get results
                import asyncio
                await asyncio.sleep(2)
                
                results_url = f"{self.base_url}/api/ariel/searches/{search_id}/results"
                async with self.session.get(results_url, headers=headers) as results_response:
                    if results_response.status == 200:
                        return await results_response.json()
        
        except Exception as e:
            logger.error(f"QRadar query error: {e}")
        
        return []
    
    async def health_check(self) -> bool:
        """Check QRadar connection health"""
        try:
            url = f"{self.base_url}/api/help/versions"
            headers = {"SEC": self.api_key}
            
            async with self.session.get(url, headers=headers) as response:
                return response.status == 200
        except:
            return False