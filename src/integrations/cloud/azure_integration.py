import logging
import aiohttp
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class AzureIntegration:
    """Microsoft Azure cloud platform integration"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tenant_id = config.get("tenant_id")
        self.client_id = config.get("client_id")
        self.client_secret = config.get("client_secret")
        self.subscription_id = config.get("subscription_id")
        self.session = None
        self.token = None
        self.token_expiry = None
        logger.info("Azure Integration initialized")
    
    async def initialize(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession()
        await self._authenticate()
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    async def _authenticate(self):
        """Authenticate with Azure AD"""
        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/token"
        
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "resource": "https://management.azure.com/"
        }
        
        try:
            async with self.session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    self.token = result.get("access_token")
                    expires_in = result.get("expires_in", 3600)
                    self.token_expiry = datetime.utcnow().timestamp() + expires_in
                    logger.info("Azure authentication successful")
        except Exception as e:
            logger.error(f"Azure authentication error: {e}")
    
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
    
    async def list_virtual_machines(self) -> List[Dict]:
        """List all virtual machines"""
        await self._ensure_token()
        
        url = f"https://management.azure.com/subscriptions/{self.subscription_id}/providers/Microsoft.Compute/virtualMachines?api-version=2023-03-01"
        headers = self._get_headers()
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    vms = []
                    
                    for vm in result.get("value", []):
                        vms.append({
                            "id": vm.get("id"),
                            "name": vm.get("name"),
                            "location": vm.get("location"),
                            "resource_group": vm.get("id", "").split("/")[4],
                            "vm_size": vm.get("properties", {}).get("hardwareProfile", {}).get("vmSize"),
                            "os_type": vm.get("properties", {}).get("storageProfile", {}).get("osDisk", {}).get("osType"),
                            "provisioning_state": vm.get("properties", {}).get("provisioningState")
                        })
                    
                    return vms
        except Exception as e:
            logger.error(f"Azure list VMs error: {e}")
        
        return []
    
    async def list_storage_accounts(self) -> List[Dict]:
        """List all storage accounts"""
        await self._ensure_token()
        
        url = f"https://management.azure.com/subscriptions/{self.subscription_id}/providers/Microsoft.Storage/storageAccounts?api-version=2022-09-01"
        headers = self._get_headers()
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    accounts = []
                    
                    for account in result.get("value", []):
                        accounts.append({
                            "id": account.get("id"),
                            "name": account.get("name"),
                            "location": account.get("location"),
                            "resource_group": account.get("id", "").split("/")[4],
                            "sku": account.get("sku", {}).get("name"),
                            "kind": account.get("kind"),
                            "https_only": account.get("properties", {}).get("supportsHttpsTrafficOnly", False),
                            "minimum_tls_version": account.get("properties", {}).get("minimumTlsVersion")
                        })
                    
                    return accounts
        except Exception as e:
            logger.error(f"Azure list storage accounts error: {e}")
        
        return []
    
    async def list_sql_servers(self) -> List[Dict]:
        """List all SQL servers"""
        await self._ensure_token()
        
        url = f"https://management.azure.com/subscriptions/{self.subscription_id}/providers/Microsoft.Sql/servers?api-version=2022-05-01-preview"
        headers = self._get_headers()
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    servers = []
                    
                    for server in result.get("value", []):
                        servers.append({
                            "id": server.get("id"),
                            "name": server.get("name"),
                            "location": server.get("location"),
                            "resource_group": server.get("id", "").split("/")[4],
                            "version": server.get("properties", {}).get("version"),
                            "administrator_login": server.get("properties", {}).get("administratorLogin")
                        })
                    
                    return servers
        except Exception as e:
            logger.error(f"Azure list SQL servers error: {e}")
        
        return []
    
    async def get_security_alerts(self) -> List[Dict]:
        """Get security alerts from Microsoft Defender"""
        await self._ensure_token()
        
        url = f"https://management.azure.com/subscriptions/{self.subscription_id}/providers/Microsoft.Security/alerts?api-version=2022-01-01"
        headers = self._get_headers()
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    alerts = []
                    
                    for alert in result.get("value", []):
                        alerts.append({
                            "id": alert.get("id"),
                            "name": alert.get("name"),
                            "severity": alert.get("properties", {}).get("severity"),
                            "status": alert.get("properties", {}).get("status"),
                            "description": alert.get("properties", {}).get("description"),
                            "time_generated": alert.get("properties", {}).get("timeGeneratedUtc")
                        })
                    
                    return alerts
        except Exception as e:
            logger.error(f"Azure security alerts error: {e}")
        
        return []