
import logging
import aiohttp
import json
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class TheHiveIntegration:
    """TheHive SOAR integration"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = config.get("url", "https://localhost")
        self.api_key = config.get("api_key")
        self.session = None
        logger.info("TheHive Integration initialized")
    
    async def initialize(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession()
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    async def create_case(self, case_data: Dict[str, Any]) -> Optional[str]:
        """Create case in TheHive"""
        url = f"{self.base_url}/api/case"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with self.session.post(url, json=case_data, headers=headers) as response:
                if response.status in [200, 201]:
                    result = await response.json()
                    return result.get("id")
        except Exception as e:
            logger.error(f"TheHive create case error: {e}")
        
        return None
    
    async def create_alert(self, alert_data: Dict[str, Any]) -> Optional[str]:
        """Create alert in TheHive"""
        url = f"{self.base_url}/api/alert"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with self.session.post(url, json=alert_data, headers=headers) as response:
                if response.status in [200, 201]:
                    result = await response.json()
                    return result.get("id")
        except Exception as e:
            logger.error(f"TheHive create alert error: {e}")
        
        return None
    
    async def add_observable(self, case_id: str, observable: Dict[str, Any]) -> bool:
        """Add observable to case"""
        url = f"{self.base_url}/api/case/{case_id}/observable"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with self.session.post(url, json=observable, headers=headers) as response:
                return response.status in [200, 204]
        except Exception as e:
            logger.error(f"TheHive add observable error: {e}")
            return False
