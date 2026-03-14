import logging
import aiohttp
import json
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class Auth0Integration:
    """Auth0 identity provider integration"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.domain = config.get("domain", "your-tenant.auth0.com")
        self.client_id = config.get("client_id")
        self.client_secret = config.get("client_secret")
        self.audience = config.get("audience", f"https://{self.domain}/api/v2/")
        self.session = None
        self.token = None
        logger.info("Auth0 Integration initialized")
    
    async def initialize(self):
        """Initialize HTTP session and get token"""
        self.session = aiohttp.ClientSession()
        await self._get_token()
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    async def _get_token(self):
        """Get management API token"""
        url = f"https://{self.domain}/oauth/token"
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "audience": self.audience,
            "grant_type": "client_credentials"
        }
        
        try:
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    self.token = result.get("access_token")
                    logger.info("Auth0 token obtained successfully")
        except Exception as e:
            logger.error(f"Auth0 get token error: {e}")
    
    def _get_headers(self):
        """Get headers with auth token"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    async def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        await self._ensure_token()
        
        url = f"https://{self.domain}/api/v2/users/{user_id}"
        headers = self._get_headers()
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.error(f"Auth0 get user error: {e}")
        
        return None
    
    async def _ensure_token(self):
        """Ensure token is valid"""
        if not self.token:
            await self._get_token()
    
    async def list_users(self, page: int = 0, per_page: int = 50) -> List[Dict]:
        """List all users"""
        await self._ensure_token()
        
        url = f"https://{self.domain}/api/v2/users"
        headers = self._get_headers()
        
        params = {
            "page": page,
            "per_page": per_page,
            "include_totals": "true"
        }
        
        try:
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("users", [])
        except Exception as e:
            logger.error(f"Auth0 list users error: {e}")
        
        return []
    
    async def create_user(self, email: str, password: str, connection: str = "Username-Password-Authentication") -> Optional[Dict]:
        """Create a new user"""
        await self._ensure_token()
        
        url = f"https://{self.domain}/api/v2/users"
        headers = self._get_headers()
        
        data = {
            "email": email,
            "password": password,
            "connection": connection
        }
        
        try:
            async with self.session.post(url, json=data, headers=headers) as response:
                if response.status in [200, 201]:
                    return await response.json()
        except Exception as e:
            logger.error(f"Auth0 create user error: {e}")
        
        return None
    
    async def delete_user(self, user_id: str) -> bool:
        """Delete a user"""
        await self._ensure_token()
        
        url = f"https://{self.domain}/api/v2/users/{user_id}"
        headers = self._get_headers()
        
        try:
            async with self.session.delete(url, headers=headers) as response:
                return response.status in [200, 204]
        except Exception as e:
            logger.error(f"Auth0 delete user error: {e}")
            return False
    
    async def get_roles(self) -> List[Dict]:
        """Get all roles"""
        await self._ensure_token()
        
        url = f"https://{self.domain}/api/v2/roles"
        headers = self._get_headers()
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.error(f"Auth0 get roles error: {e}")
        
        return []
    
    async def assign_user_role(self, user_id: str, role_id: str) -> bool:
        """Assign role to user"""
        await self._ensure_token()
        
        url = f"https://{self.domain}/api/v2/users/{user_id}/roles"
        headers = self._get_headers()
        
        data = {"roles": [role_id]}
        
        try:
            async with self.session.post(url, json=data, headers=headers) as response:
                return response.status in [200, 204]
        except Exception as e:
            logger.error(f"Auth0 assign role error: {e}")
            return False