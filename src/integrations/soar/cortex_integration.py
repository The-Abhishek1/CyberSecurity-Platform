
import logging
import aiohttp
import json
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class CortexIntegration:
    """Cortex XSOAR integration"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = config.get("url", "https://localhost")
        self.api_key = config.get("api_key")
        self.session = None
        logger.info("Cortex Integration initialized")
    
    async def initialize(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession()
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    async def run_playbook(self, playbook_id: str, inputs: Dict[str, Any]) -> Optional[Dict]:
        """Run a Cortex playbook"""
        url = f"{self.base_url}/playbook/run"
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }
        
        data = {
            "playbook_id": playbook_id,
            "inputs": inputs
        }
        
        try:
            async with self.session.post(url, json=data, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.error(f"Cortex run playbook error: {e}")
        
        return None
    
    async def get_incident(self, incident_id: str) -> Optional[Dict]:
        """Get incident from Cortex"""
        url = f"{self.base_url}/incident/{incident_id}"
        headers = {"Authorization": self.api_key}
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.error(f"Cortex get incident error: {e}")
        
        return None
    
    async def update_incident(self, incident_id: str, update_data: Dict[str, Any]) -> bool:
        """Update incident in Cortex"""
        url = f"{self.base_url}/incident/{incident_id}"
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }
        
        try:
            async with self.session.put(url, json=update_data, headers=headers) as response:
                return response.status in [200, 204]
        except Exception as e:
            logger.error(f"Cortex update incident error: {e}")
            return False
