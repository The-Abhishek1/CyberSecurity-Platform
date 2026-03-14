
import logging
import aiohttp
import json
from typing import Dict, Any, List, Optional
from base64 import b64encode

logger = logging.getLogger(__name__)


class ServiceNowIntegration:
    """ServiceNow ticketing system integration"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = config.get("url", "https://localhost")
        self.username = config.get("username")
        self.password = config.get("password")
        self.session = None
        logger.info("ServiceNow Integration initialized")
    
    async def initialize(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession()
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    def _get_auth_header(self):
        """Get basic auth header"""
        auth_str = f"{self.username}:{self.password}"
        auth_bytes = auth_str.encode('utf-8')
        auth_b64 = b64encode(auth_bytes).decode('utf-8')
        return {"Authorization": f"Basic {auth_b64}"}
    
    async def create_incident(self, short_description: str, description: str, 
                               urgency: int = 2, impact: int = 2,
                               category: str = "security") -> Optional[Dict]:
        """Create incident in ServiceNow"""
        url = f"{self.base_url}/api/now/table/incident"
        headers = {
            **self._get_auth_header(),
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        incident_data = {
            "short_description": short_description,
            "description": description,
            "urgency": urgency,
            "impact": impact,
            "category": category,
            "caller_id": "system"
        }
        
        try:
            async with self.session.post(url, json=incident_data, headers=headers) as response:
                if response.status in [200, 201]:
                    result = await response.json()
                    return {
                        "sys_id": result.get("result", {}).get("sys_id"),
                        "number": result.get("result", {}).get("number"),
                        "url": f"{self.base_url}/nav_to.do?uri={result.get('result', {}).get('sys_id')}"
                    }
        except Exception as e:
            logger.error(f"ServiceNow create incident error: {e}")
        
        return None
    
    async def update_incident(self, sys_id: str, update_data: Dict[str, Any]) -> bool:
        """Update incident in ServiceNow"""
        url = f"{self.base_url}/api/now/table/incident/{sys_id}"
        headers = {
            **self._get_auth_header(),
            "Content-Type": "application/json"
        }
        
        try:
            async with self.session.put(url, json=update_data, headers=headers) as response:
                return response.status in [200, 204]
        except Exception as e:
            logger.error(f"ServiceNow update incident error: {e}")
            return False
    
    async def add_work_note(self, sys_id: str, note: str) -> bool:
        """Add work note to incident"""
        url = f"{self.base_url}/api/now/table/incident/{sys_id}"
        headers = {
            **self._get_auth_header(),
            "Content-Type": "application/json"
        }
        
        data = {"work_notes": note}
        
        try:
            async with self.session.put(url, json=data, headers=headers) as response:
                return response.status in [200, 204]
        except Exception as e:
            logger.error(f"ServiceNow add work note error: {e}")
            return False
    
    async def get_incident(self, sys_id: str) -> Optional[Dict]:
        """Get incident details"""
        url = f"{self.base_url}/api/now/table/incident/{sys_id}"
        headers = self._get_auth_header()
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("result")
        except Exception as e:
            logger.error(f"ServiceNow get incident error: {e}")
        
        return None
