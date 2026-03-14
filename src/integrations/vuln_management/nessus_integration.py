import logging
import aiohttp
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class NessusIntegration:
    """Nessus vulnerability scanner integration"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = config.get("url", "https://localhost:8834")
        self.access_key = config.get("access_key")
        self.secret_key = config.get("secret_key")
        self.session = None
        self.token = None
        logger.info("Nessus Integration initialized")
    
    async def initialize(self):
        """Initialize HTTP session and authenticate"""
        self.session = aiohttp.ClientSession()
        
        # Authenticate
        auth_url = f"{self.base_url}/session"
        auth_data = {
            "access_key": self.access_key,
            "secret_key": self.secret_key
        }
        
        try:
            async with self.session.post(auth_url, json=auth_data) as response:
                if response.status == 200:
                    result = await response.json()
                    self.token = result.get("token")
                    logger.info("Nessus authenticated successfully")
        except Exception as e:
            logger.error(f"Nessus authentication error: {e}")
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    def _get_headers(self):
        """Get headers with authentication token"""
        return {"X-Cookie": f"token={self.token}"} if self.token else {}
    
    async def create_scan(self, name: str, target: str, template: str = "basic") -> Optional[str]:
        """Create a new scan in Nessus"""
        url = f"{self.base_url}/scans"
        headers = self._get_headers()
        
        scan_data = {
            "uuid": "ad629e16-03b6-8c1d-cef6-ef8c9dd3c658",  # basic scan template
            "settings": {
                "name": name,
                "text_targets": target,
                "launch": "ON_DEMAND"
            }
        }
        
        try:
            async with self.session.post(url, json=scan_data, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("scan", {}).get("id")
        except Exception as e:
            logger.error(f"Nessus create scan error: {e}")
        
        return None
    
    async def launch_scan(self, scan_id: str) -> bool:
        """Launch a scan"""
        url = f"{self.base_url}/scans/{scan_id}/launch"
        headers = self._get_headers()
        
        try:
            async with self.session.post(url, headers=headers) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Nessus launch scan error: {e}")
            return False
    
    async def get_scan_status(self, scan_id: str) -> Optional[str]:
        """Get scan status"""
        url = f"{self.base_url}/scans/{scan_id}"
        headers = self._get_headers()
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("info", {}).get("status")
        except Exception as e:
            logger.error(f"Nessus get scan status error: {e}")
        
        return None
    
    async def get_scan_results(self, scan_id: str) -> List[Dict]:
        """Get scan results"""
        url = f"{self.base_url}/scans/{scan_id}"
        headers = self._get_headers()
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    vulnerabilities = []
                    
                    for vuln in result.get("vulnerabilities", []):
                        vulnerabilities.append({
                            "plugin_id": vuln.get("plugin_id"),
                            "plugin_name": vuln.get("plugin_name"),
                            "severity": vuln.get("severity"),
                            "count": vuln.get("count"),
                            "plugin_family": vuln.get("plugin_family")
                        })
                    
                    return vulnerabilities
        except Exception as e:
            logger.error(f"Nessus get scan results error: {e}")
        
        return []
    
    async def export_results(self, scan_id: str, format: str = "nessus") -> Optional[bytes]:
        """Export scan results"""
        # Create export request
        url = f"{self.base_url}/scans/{scan_id}/export"
        headers = self._get_headers()
        
        export_data = {"format": format}
        
        try:
            async with self.session.post(url, json=export_data, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    file_id = result.get("file")
                    
                    if not file_id:
                        return None
                    
                    # Check export status
                    import asyncio
                    status_url = f"{self.base_url}/scans/{scan_id}/export/{file_id}/status"
                    
                    for _ in range(10):  # Try for 10 seconds
                        async with self.session.get(status_url, headers=headers) as status_response:
                            if status_response.status == 200:
                                status_result = await status_response.json()
                                if status_result.get("status") == "ready":
                                    break
                        await asyncio.sleep(1)
                    
                    # Download file
                    download_url = f"{self.base_url}/scans/{scan_id}/export/{file_id}/download"
                    async with self.session.get(download_url, headers=headers) as download_response:
                        if download_response.status == 200:
                            return await download_response.read()
        except Exception as e:
            logger.error(f"Nessus export results error: {e}")
        
        return None