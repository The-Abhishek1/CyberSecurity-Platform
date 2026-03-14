


import logging
import aiohttp
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class Rapid7Integration:
    """Rapid7 InsightVM vulnerability management integration"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = config.get("url", "https://localhost:3780")
        self.api_key = config.get("api_key")
        self.session = None
        logger.info("Rapid7 Integration initialized")
    
    async def initialize(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession()
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    def _get_headers(self):
        """Get headers with API key"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def create_scan(self, name: str, targets: List[str], engine_id: int = 1) -> Optional[int]:
        """Create a new scan"""
        url = f"{self.base_url}/api/3/scans"
        headers = self._get_headers()
        
        scan_data = {
            "name": name,
            "targets": targets,
            "engineId": engine_id
        }
        
        try:
            async with self.session.post(url, json=scan_data, headers=headers) as response:
                if response.status in [200, 201]:
                    result = await response.json()
                    return result.get("id")
        except Exception as e:
            logger.error(f"Rapid7 create scan error: {e}")
        
        return None
    
    async def launch_scan(self, scan_id: int) -> bool:
        """Launch a scan"""
        url = f"{self.base_url}/api/3/scans/{scan_id}/launch"
        headers = self._get_headers()
        
        try:
            async with self.session.post(url, headers=headers) as response:
                return response.status in [200, 202]
        except Exception as e:
            logger.error(f"Rapid7 launch scan error: {e}")
            return False
    
    async def get_scan_status(self, scan_id: int) -> Optional[str]:
        """Get scan status"""
        url = f"{self.base_url}/api/3/scans/{scan_id}"
        headers = self._get_headers()
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("status")
        except Exception as e:
            logger.error(f"Rapid7 get scan status error: {e}")
        
        return None
    
    async def get_vulnerabilities(self, scan_id: int, severity: str = "all") -> List[Dict]:
        """Get vulnerabilities from scan"""
        url = f"{self.base_url}/api/3/scans/{scan_id}/vulnerabilities"
        headers = self._get_headers()
        
        params = {}
        if severity != "all":
            params["severity"] = severity
        
        try:
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    vulnerabilities = []
                    
                    for vuln in result.get("resources", []):
                        vulnerabilities.append({
                            "id": vuln.get("id"),
                            "title": vuln.get("title"),
                            "severity": vuln.get("severity"),
                            "cvss_score": vuln.get("cvssScore"),
                            "description": vuln.get("description"),
                            "solution": vuln.get("solution")
                        })
                    
                    return vulnerabilities
        except Exception as e:
            logger.error(f"Rapid7 get vulnerabilities error: {e}")
        
        return []
    
    async def get_assets(self, scan_id: int) -> List[Dict]:
        """Get assets from scan"""
        url = f"{self.base_url}/api/3/scans/{scan_id}/assets"
        headers = self._get_headers()
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    assets = []
                    
                    for asset in result.get("resources", []):
                        assets.append({
                            "id": asset.get("id"),
                            "ip": asset.get("ip"),
                            "hostname": asset.get("hostname"),
                            "os": asset.get("os"),
                            "vulnerability_count": asset.get("vulnerabilityCount")
                        })
                    
                    return assets
        except Exception as e:
            logger.error(f"Rapid7 get assets error: {e}")
        
        return []
    
    async def generate_report(self, scan_id: int, report_format: str = "pdf") -> Optional[bytes]:
        """Generate scan report"""
        url = f"{self.base_url}/api/3/scans/{scan_id}/report"
        headers = self._get_headers()
        
        params = {"format": report_format}
        
        try:
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    return await response.read()
        except Exception as e:
            logger.error(f"Rapid7 generate report error: {e}")
        
        return None
