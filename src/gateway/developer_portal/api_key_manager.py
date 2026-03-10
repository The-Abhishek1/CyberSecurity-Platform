from typing import Dict, Optional, List
from datetime import datetime, timedelta
import secrets
import hashlib
import hmac

from src.core.config import get_settings
from src.utils.logging import logger

settings = get_settings()


class APIKeyManager:
    """
    Enterprise API Key Manager
    
    Features:
    - API key generation
    - Key rotation
    - Key revocation
    - Usage tracking per key
    - Expiration management
    - Permission scoping
    """
    
    def __init__(self):
        # API keys storage: key_hash -> key_info
        self.api_keys: Dict[str, Dict] = {}
        
        # Key usage tracking
        self.usage: Dict[str, List] = {}
        
        # Rate limit tracking
        self.rate_limits: Dict[str, List] = {}
        
        logger.info("API Key Manager initialized")
    
    async def generate_key(
        self,
        tenant_id: str,
        name: str,
        permissions: Optional[List[str]] = None,
        expires_in_days: int = 365,
        rate_limit: str = "100/minute"
    ) -> Dict[str, str]:
        """Generate new API key"""
        
        # Generate key
        key = f"eso_{secrets.token_urlsafe(32)}"
        key_hash = self._hash_key(key)
        key_id = secrets.token_hex(8)
        
        # Store key info
        self.api_keys[key_hash] = {
            "key_id": key_id,
            "tenant_id": tenant_id,
            "name": name,
            "permissions": permissions or ["*"],
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=expires_in_days),
            "last_used": None,
            "rate_limit": rate_limit,
            "active": True
        }
        
        logger.info(f"Generated API key {key_id} for tenant {tenant_id}")
        
        return {
            "key_id": key_id,
            "key": key,  # Only returned once!
            "tenant_id": tenant_id,
            "name": name,
            "expires_at": self.api_keys[key_hash]["expires_at"].isoformat()
        }
    
    async def validate_key(self, key: str, tenant_id: str) -> bool:
        """Validate API key"""
        
        key_hash = self._hash_key(key)
        
        if key_hash not in self.api_keys:
            return False
        
        key_info = self.api_keys[key_hash]
        
        # Check tenant
        if key_info["tenant_id"] != tenant_id:
            return False
        
        # Check active
        if not key_info["active"]:
            return False
        
        # Check expiration
        if key_info["expires_at"] < datetime.utcnow():
            return False
        
        # Update last used
        key_info["last_used"] = datetime.utcnow()
        
        return True
    
    async def revoke_key(self, key_id: str, tenant_id: str) -> bool:
        """Revoke API key"""
        
        for key_hash, key_info in self.api_keys.items():
            if key_info["key_id"] == key_id and key_info["tenant_id"] == tenant_id:
                key_info["active"] = False
                key_info["revoked_at"] = datetime.utcnow()
                logger.info(f"Revoked API key {key_id}")
                return True
        
        return False
    
    async def rotate_key(self, key_id: str, tenant_id: str) -> Optional[Dict]:
        """Rotate API key"""
        
        # Find existing key
        old_key_info = None
        old_key_hash = None
        
        for kh, ki in self.api_keys.items():
            if ki["key_id"] == key_id and ki["tenant_id"] == tenant_id:
                old_key_info = ki
                old_key_hash = kh
                break
        
        if not old_key_info:
            return None
        
        # Generate new key
        new_key = await self.generate_key(
            tenant_id=tenant_id,
            name=f"{old_key_info['name']} (rotated)",
            permissions=old_key_info["permissions"],
            rate_limit=old_key_info["rate_limit"]
        )
        
        # Revoke old key
        old_key_info["active"] = False
        old_key_info["rotated_at"] = datetime.utcnow()
        old_key_info["new_key_id"] = new_key["key_id"]
        
        logger.info(f"Rotated API key {key_id} -> {new_key['key_id']}")
        
        return new_key
    
    async def check_rate_limit(self, key: str, tenant_id: str) -> bool:
        """Check rate limit for key"""
        
        key_hash = self._hash_key(key)
        
        if key_hash not in self.api_keys:
            return False
        
        key_info = self.api_keys[key_hash]
        
        # Parse rate limit
        limit_str = key_info["rate_limit"]
        try:
            count, period = limit_str.split("/")
            max_requests = int(count)
            period_seconds = {
                "second": 1, "minute": 60, "hour": 3600, "day": 86400
            }.get(period, 60)
        except:
            max_requests = 100
            period_seconds = 60
        
        # Track requests
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=period_seconds)
        
        if key_hash not in self.rate_limits:
            self.rate_limits[key_hash] = []
        
        # Clean old requests
        self.rate_limits[key_hash] = [
            ts for ts in self.rate_limits[key_hash]
            if ts > cutoff
        ]
        
        # Check limit
        if len(self.rate_limits[key_hash]) >= max_requests:
            return False
        
        # Add current request
        self.rate_limits[key_hash].append(now)
        
        return True
    
    async def track_usage(self, key: str, endpoint: str, status_code: int):
        """Track API key usage"""
        
        key_hash = self._hash_key(key)
        
        if key_hash not in self.usage:
            self.usage[key_hash] = []
        
        self.usage[key_hash].append({
            "timestamp": datetime.utcnow(),
            "endpoint": endpoint,
            "status_code": status_code
        })
        
        # Limit history
        if len(self.usage[key_hash]) > 10000:
            self.usage[key_hash] = self.usage[key_hash][-10000:]
    
    def _hash_key(self, key: str) -> str:
        """Hash API key for storage"""
        return hashlib.sha256(key.encode()).hexdigest()
    
    async def get_key_info(self, key_id: str, tenant_id: str) -> Optional[Dict]:
        """Get API key information"""
        
        for key_hash, key_info in self.api_keys.items():
            if key_info["key_id"] == key_id and key_info["tenant_id"] == tenant_id:
                return {
                    "key_id": key_info["key_id"],
                    "tenant_id": key_info["tenant_id"],
                    "name": key_info["name"],
                    "permissions": key_info["permissions"],
                    "created_at": key_info["created_at"].isoformat(),
                    "expires_at": key_info["expires_at"].isoformat(),
                    "last_used": key_info["last_used"].isoformat() if key_info["last_used"] else None,
                    "rate_limit": key_info["rate_limit"],
                    "active": key_info["active"]
                }
        
        return None
    
    async def list_keys(self, tenant_id: str) -> List[Dict]:
        """List all keys for tenant"""
        
        keys = []
        for key_hash, key_info in self.api_keys.items():
            if key_info["tenant_id"] == tenant_id:
                keys.append({
                    "key_id": key_info["key_id"],
                    "name": key_info["name"],
                    "created_at": key_info["created_at"].isoformat(),
                    "expires_at": key_info["expires_at"].isoformat(),
                    "last_used": key_info["last_used"].isoformat() if key_info["last_used"] else None,
                    "active": key_info["active"]
                })
        
        return keys