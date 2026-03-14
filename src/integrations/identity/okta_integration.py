import logging
import aiohttp
import json
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class OktaIntegration:
    """Okta identity provider integration"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = config.get("url", "https://your-org.okta.com")
        self.api_token = config.get("api_token")
        self.session = None
        logger.info("Okta Integration initialized")
    
    async def initialize(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession()
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    def _get_headers(self):
        """Get headers with API token"""
        return {
            "Authorization": f"SSWS {self.api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    async def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        url = f"{self.base_url}/api/v1/users/{user_id}"
        headers = self._get_headers()
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.error(f"Okta get user error: {e}")
        
        return None
    
    async def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        url = f"{self.base_url}/api/v1/users/{email}"
        headers = self._get_headers()
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.error(f"Okta get user by email error: {e}")
        
        return None
    
    async def list_users(self, limit: int = 200) -> List[Dict]:
        """List all users"""
        url = f"{self.base_url}/api/v1/users"
        headers = self._get_headers()
        
        params = {"limit": limit}
        
        try:
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.error(f"Okta list users error: {e}")
        
        return []
    
    async def get_user_groups(self, user_id: str) -> List[Dict]:
        """Get groups for a user"""
        url = f"{self.base_url}/api/v1/users/{user_id}/groups"
        headers = self._get_headers()
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.error(f"Okta get user groups error: {e}")
        
        return []
    
    async def create_user(self, profile: Dict, credentials: Optional[Dict] = None) -> Optional[Dict]:
        """Create a new user"""
        url = f"{self.base_url}/api/v1/users"
        headers = self._get_headers()
        
        data = {
            "profile": profile,
            "credentials": credentials or {}
        }
        
        try:
            async with self.session.post(url, json=data, headers=headers) as response:
                if response.status in [200, 201]:
                    return await response.json()
        except Exception as e:
            logger.error(f"Okta create user error: {e}")
        
        return None
    
    async def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user"""
        url = f"{self.base_url}/api/v1/users/{user_id}/lifecycle/deactivate"
        headers = self._get_headers()
        
        try:
            async with self.session.post(url, headers=headers) as response:
                return response.status in [200, 204]
        except Exception as e:
            logger.error(f"Okta deactivate user error: {e}")
            return False
    
    async def get_applications(self) -> List[Dict]:
        """Get all applications"""
        url = f"{self.base_url}/api/v1/apps"
        headers = self._get_headers()
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.error(f"Okta get applications error: {e}")
        
        return []
    
    async def assign_user_to_app(self, app_id: str, user_id: str) -> bool:
        """Assign user to application"""
        url = f"{self.base_url}/api/v1/apps/{app_id}/users"
        headers = self._get_headers()
        
        data = {"id": user_id}
        
        try:
            async with self.session.post(url, json=data, headers=headers) as response:
                return response.status in [200, 201]
        except Exception as e:
            logger.error(f"Okta assign user to app error: {e}")
            return False
