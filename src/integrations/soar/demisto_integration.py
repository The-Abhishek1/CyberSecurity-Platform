import logging
import aiohttp
import json
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class DemistoIntegration:
    """Demisto/Cortex XSOAR SOAR integration"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = config.get("url", "https://localhost")
        self.api_key = config.get("api_key")
        self.session = None
        logger.info("Demisto Integration initialized")
    
    async def initialize(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession()
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    async def create_incident(self, incident_data: Dict[str, Any]) -> Optional[str]:
        """Create incident in Demisto"""
        url = f"{self.base_url}/incident"
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }
        
        try:
            async with self.session.post(url, json=incident_data, headers=headers) as response:
                if response.status in [200, 201]:
                    result = await response.json()
                    return result.get("id")
        except Exception as e:
            logger.error(f"Demisto create incident error: {e}")
        
        return None
    
    async def update_incident(self, incident_id: str, update_data: Dict[str, Any]) -> bool:
        """Update incident in Demisto"""
        url = f"{self.base_url}/incident/{incident_id}"
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }
        
        try:
            async with self.session.put(url, json=update_data, headers=headers) as response:
                return response.status in [200, 204]
        except Exception as e:
            logger.error(f"Demisto update incident error: {e}")
            return False
    
    async def get_incident(self, incident_id: str) -> Optional[Dict]:
        """Get incident from Demisto"""
        url = f"{self.base_url}/incident/{incident_id}"
        headers = {"Authorization": self.api_key}
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.error(f"Demisto get incident error: {e}")
        
        return None
    
    async def add_note(self, incident_id: str, note: str) -> bool:
        """Add note to incident"""
        url = f"{self.base_url}/incident/{incident_id}/note"
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }
        
        try:
            async with self.session.post(url, json={"note": note}, headers=headers) as response:
                return response.status in [200, 204]
        except Exception as e:
            logger.error(f"Demisto add note error: {e}")
            return False