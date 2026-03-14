
import logging
import aiohttp
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class GCPIntegration:
    """Google Cloud Platform integration"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.project_id = config.get("project_id")
        self.credentials = config.get("credentials")  # Service account JSON
        self.session = None
        self.token = None
        self.token_expiry = None
        logger.info("GCP Integration initialized")
    
    async def initialize(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession()
        await self._authenticate()
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    async def _authenticate(self):
        """Authenticate with GCP"""
        # In production, use google-auth library
        # This is a simplified mock
        self.token = "mock-gcp-token"
        self.token_expiry = datetime.utcnow().timestamp() + 3600
        logger.info("GCP authentication successful (mock)")
    
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
    
    async def list_compute_instances(self) -> List[Dict]:
        """List all compute instances"""
        await self._ensure_token()
        
        url = f"https://compute.googleapis.com/compute/v1/projects/{self.project_id}/zones/us-central1-a/instances"
        headers = self._get_headers()
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    instances = []
                    
                    for item in result.get("items", []):
                        instances.append({
                            "id": item.get("id"),
                            "name": item.get("name"),
                            "zone": item.get("zone"),
                            "machine_type": item.get("machineType"),
                            "status": item.get("status"),
                            "creation_timestamp": item.get("creationTimestamp")
                        })
                    
                    return instances
        except Exception as e:
            logger.error(f"GCP list instances error: {e}")
        
        return []
    
    async def list_storage_buckets(self) -> List[Dict]:
        """List all storage buckets"""
        await self._ensure_token()
        
        url = f"https://storage.googleapis.com/storage/v1/b?project={self.project_id}"
        headers = self._get_headers()
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    buckets = []
                    
                    for item in result.get("items", []):
                        buckets.append({
                            "id": item.get("id"),
                            "name": item.get("name"),
                            "location": item.get("location"),
                            "storage_class": item.get("storageClass"),
                            "time_created": item.get("timeCreated"),
                            "iam_configuration": item.get("iamConfiguration", {})
                        })
                    
                    return buckets
        except Exception as e:
            logger.error(f"GCP list buckets error: {e}")
        
        return []
    
    async def list_sql_instances(self) -> List[Dict]:
        """List all Cloud SQL instances"""
        await self._ensure_token()
        
        url = f"https://sqladmin.googleapis.com/v1/projects/{self.project_id}/instances"
        headers = self._get_headers()
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    instances = []
                    
                    for item in result.get("items", []):
                        instances.append({
                            "name": item.get("name"),
                            "database_version": item.get("databaseVersion"),
                            "region": item.get("region"),
                            "state": item.get("state"),
                            "settings": item.get("settings", {})
                        })
                    
                    return instances
        except Exception as e:
            logger.error(f"GCP list SQL instances error: {e}")
        
        return []
    
    async def get_iam_policy(self) -> Dict:
        """Get IAM policy"""
        await self._ensure_token()
        
        url = f"https://cloudresourcemanager.googleapis.com/v1/projects/{self.project_id}:getIamPolicy"
        headers = self._get_headers()
        
        try:
            async with self.session.post(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.error(f"GCP get IAM policy error: {e}")
        
        return {}
    
    async def get_security_findings(self) -> List[Dict]:
        """Get security findings from Security Command Center"""
        await self._ensure_token()
        
        url = f"https://securitycenter.googleapis.com/v1/organizations/{self.project_id}/sources/-/findings"
        headers = self._get_headers()
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    findings = []
                    
                    for finding in result.get("findings", []):
                        findings.append({
                            "name": finding.get("name"),
                            "category": finding.get("category"),
                            "severity": finding.get("severity"),
                            "description": finding.get("description"),
                            "event_time": finding.get("eventTime")
                        })
                    
                    return findings
        except Exception as e:
            logger.error(f"GCP security findings error: {e}")
        
        return []
