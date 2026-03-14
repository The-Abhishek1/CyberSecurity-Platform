import logging
import aiohttp
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
from datetime import datetime
import base64

logger = logging.getLogger(__name__)


class QualysIntegration:
    """Qualys vulnerability management integration"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = config.get("url", "https://qualysapi.qualys.com")
        self.username = config.get("username")
        self.password = config.get("password")
        self.session = None
        logger.info("Qualys Integration initialized")
    
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
        auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
        return {"Authorization": f"Basic {auth_b64}"}
    
    async def launch_scan(self, scan_title: str, target_ip: str, option_profile: str = "Initial Options") -> Optional[str]:
        """Launch a vulnerability scan"""
        url = f"{self.base_url}/api/2.0/fo/scan/"
        headers = {
            **self._get_auth_header(),
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "action": "launch",
            "scan_title": scan_title,
            "ip": target_ip,
            "option_title": option_profile
        }
        
        try:
            async with self.session.post(url, data=data, headers=headers) as response:
                if response.status == 200:
                    text = await response.text()
                    # Parse XML response
                    root = ET.fromstring(text)
                    return root.findtext(".//VALUE")
        except Exception as e:
            logger.error(f"Qualys launch scan error: {e}")
        
        return None
    
    async def get_scan_status(self, scan_ref: str) -> Optional[str]:
        """Get scan status"""
        url = f"{self.base_url}/api/2.0/fo/scan/"
        headers = self._get_auth_header()
        
        params = {
            "action": "list",
            "scan_ref": scan_ref
        }
        
        try:
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    text = await response.text()
                    root = ET.fromstring(text)
                    return root.findtext(".//STATUS")
        except Exception as e:
            logger.error(f"Qualys get scan status error: {e}")
        
        return None
    
    async def get_scan_results(self, scan_ref: str) -> List[Dict]:
        """Get scan results"""
        url = f"{self.base_url}/api/2.0/fo/scan/scan_result/"
        headers = self._get_auth_header()
        
        params = {
            "action": "fetch",
            "scan_ref": scan_ref,
            "output_format": "json"
        }
        
        try:
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    vulnerabilities = []
                    
                    # Parse JSON response
                    for vuln in result.get("VULNERABILITY_LIST", []):
                        vulnerabilities.append({
                            "qid": vuln.get("QID"),
                            "severity": vuln.get("SEVERITY"),
                            "title": vuln.get("TITLE"),
                            "category": vuln.get("CATEGORY")
                        })
                    
                    return vulnerabilities
        except Exception as e:
            logger.error(f"Qualys get scan results error: {e}")
        
        return []
    
    async def create_report(self, scan_ref: str, report_title: str, report_format: str = "pdf") -> Optional[str]:
        """Create a scan report"""
        url = f"{self.base_url}/api/2.0/fo/report/"
        headers = {
            **self._get_auth_header(),
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "action": "launch",
            "report_title": report_title,
            "template_id": "1",  # Default template
            "output_format": report_format,
            "scan_ref": scan_ref
        }
        
        try:
            async with self.session.post(url, data=data, headers=headers) as response:
                if response.status == 200:
                    text = await response.text()
                    root = ET.fromstring(text)
                    return root.findtext(".//VALUE")
        except Exception as e:
            logger.error(f"Qualys create report error: {e}")
        
        return None
    
    async def download_report(self, report_id: str) -> Optional[bytes]:
        """Download a report"""
        url = f"{self.base_url}/api/2.0/fo/report/"
        headers = self._get_auth_header()
        
        params = {
            "action": "fetch",
            "id": report_id
        }
        
        try:
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    return await response.read()
        except Exception as e:
            logger.error(f"Qualys download report error: {e}")
        
        return None