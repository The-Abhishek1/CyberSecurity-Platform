

import logging
import aiohttp
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class AzureADIntegration:
    """Azure Active Directory integration"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tenant_id = config.get("tenant_id")
        self.client_id = config.get("client_id")
        self.client_secret = config.get("client_secret")
        self.session = None
        self.token = None
        self.token_expiry = None
        logger.info("Azure AD Integration initialized")
    
    async def initialize(self):
        """Initialize HTTP session and get token"""
        self.session = aiohttp.ClientSession()
        await self._authenticate()
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    async def _authenticate(self):
        """Authenticate with Azure AD"""
        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default"
        }
        
        try:
            async with self.session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    self.token = result.get("access_token")
                    expires_in = result.get("expires_in", 3600)
                    self.token_expiry = datetime.utcnow().timestamp() + expires_in
                    logger.info("Azure AD authentication successful")
        except Exception as e:
            logger.error(f"Azure AD authentication error: {e}")
    
    async def _ensure_token(self):
        """Ensure token is valid"""
        if not self.token or (self.token_expiry and datetime.utcnow().timestamp() > self.token_expiry - 300):
            await self._authenticate()
    
    def _get_headers(self):
        """Get headers with auth token"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    async def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        await self._ensure_token()
        
        url = f"https://graph.microsoft.com/v1.0/users/{user_id}"
        headers = self._get_headers()
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.error(f"Azure AD get user error: {e}")
        
        return None
    
    async def list_users(self, filter: Optional[str] = None, top: int = 100) -> List[Dict]:
        """List all users"""
        await self._ensure_token()
        
        url = "https://graph.microsoft.com/v1.0/users"
        headers = self._get_headers()
        
        params = {"$top": top}
        if filter:
            params["$filter"] = filter
        
        try:
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("value", [])
        except Exception as e:
            logger.error(f"Azure AD list users error: {e}")
        
        return []
    
    async def list_groups(self) -> List[Dict]:
        """List all groups"""
        await self._ensure_token()
        
        url = "https://graph.microsoft.com/v1.0/groups"
        headers = self._get_headers()
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("value", [])
        except Exception as e:
            logger.error(f"Azure AD list groups error: {e}")
        
        return []
    
    async def get_user_groups(self, user_id: str) -> List[Dict]:
        """Get groups for a user"""
        await self._ensure_token()
        
        url = f"https://graph.microsoft.com/v1.0/users/{user_id}/memberOf"
        headers = self._get_headers()
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("value", [])
        except Exception as e:
            logger.error(f"Azure AD get user groups error: {e}")
        
        return []
    
    async def create_user(self, user_data: Dict) -> Optional[Dict]:
        """Create a new user"""
        await self._ensure_token()
        
        url = "https://graph.microsoft.com/v1.0/users"
        headers = self._get_headers()
        
        try:
            async with self.session.post(url, json=user_data, headers=headers) as response:
                if response.status in [200, 201]:
                    return await response.json()
        except Exception as e:
            logger.error(f"Azure AD create user error: {e}")
        
        return None
    
    async def delete_user(self, user_id: str) -> bool:
        """Delete a user"""
        await self._ensure_token()
        
        url = f"https://graph.microsoft.com/v1.0/users/{user_id}"
        headers = self._get_headers()
        
        try:
            async with self.session.delete(url, headers=headers) as response:
                return response.status in [200, 204]
        except Exception as e:
            logger.error(f"Azure AD delete user error: {e}")
            return False
    
    async def get_roles(self) -> List[Dict]:
        """Get directory roles"""
        await self._ensure_token()
        
        url = "https://graph.microsoft.com/v1.0/directoryRoles"
        headers = self._get_headers()
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("value", [])
        except Exception as e:
            logger.error(f"Azure AD get roles error: {e}")
        
        return []