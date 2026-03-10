from typing import Optional, Dict, Any
import hvac
from cryptography.fernet import Fernet
import base64
import json

from src.core.config import get_settings
from src.utils.logging import logger

settings = get_settings()


class SecretsManager:
    """
    Enterprise Secrets Manager
    
    Integrates with HashiCorp Vault
    Features:
    - Dynamic secrets
    - Secret rotation
    - Encryption as a service
    - Audit logging
    """
    
    def __init__(self):
        self.vault_client = None
        self.fernet = None
        self._init_vault()
        self._init_encryption()
        
        logger.info("Secrets Manager initialized")
    
    def _init_vault(self):
        """Initialize Vault client"""
        try:
            self.vault_client = hvac.Client(
                url=settings.vault_url,
                token=settings.vault_token
            )
            
            if self.vault_client.is_authenticated():
                logger.info("Connected to Vault")
            else:
                logger.warning("Failed to authenticate with Vault")
                self.vault_client = None
                
        except Exception as e:
            logger.error(f"Failed to initialize Vault: {e}")
            self.vault_client = None
    
    def _init_encryption(self):
        """Initialize local encryption (fallback)"""
        key = settings.encryption.field_encryption_key.get_secret_value()
        # Derive proper Fernet key
        key_bytes = base64.urlsafe_b64encode(key.encode().ljust(32)[:32])
        self.fernet = Fernet(key_bytes)
    
    async def get_secret(
        self,
        path: str,
        key: Optional[str] = None
    ) -> Optional[Any]:
        """Get secret from Vault"""
        
        if self.vault_client:
            try:
                response = self.vault_client.secrets.kv.v2.read_secret_version(
                    path=path,
                    mount_point='secret'
                )
                
                data = response['data']['data']
                
                if key:
                    return data.get(key)
                return data
                
            except Exception as e:
                logger.error(f"Failed to read secret from Vault: {e}")
                return None
        
        # Fallback to environment or local encryption
        return await self._get_local_secret(path, key)
    
    async def write_secret(
        self,
        path: str,
        data: Dict[str, Any]
    ):
        """Write secret to Vault"""
        
        if self.vault_client:
            try:
                self.vault_client.secrets.kv.v2.create_or_update_secret(
                    path=path,
                    secret=data,
                    mount_point='secret'
                )
                logger.info(f"Secret written to {path}")
                
            except Exception as e:
                logger.error(f"Failed to write secret to Vault: {e}")
    
    async def rotate_secret(self, path: str) -> bool:
        """Rotate a secret"""
        
        if not self.vault_client:
            return False
        
        try:
            # Read current secret
            response = self.vault_client.secrets.kv.v2.read_secret_version(
                path=path,
                mount_point='secret'
            )
            
            current_data = response['data']['data']
            
            # Generate new version (customize per secret type)
            new_data = await self._generate_new_version(current_data)
            
            # Write new version
            await self.write_secret(path, new_data)
            
            logger.info(f"Secret rotated for {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rotate secret: {e}")
            return False
    
    async def _generate_new_version(self, current_data: Dict) -> Dict:
        """Generate new version of secret"""
        
        new_data = current_data.copy()
        
        for key, value in current_data.items():
            if 'password' in key.lower() or 'token' in key.lower() or 'key' in key.lower():
                # Generate new random value
                if 'token' in key.lower():
                    import secrets
                    new_data[key] = secrets.token_urlsafe(32)
                else:
                    import string
                    import random
                    chars = string.ascii_letters + string.digits + "!@#$%^&*"
                    new_data[key] = ''.join(random.choice(chars) for _ in range(16))
        
        return new_data
    
    async def _get_local_secret(self, path: str, key: Optional[str]) -> Optional[Any]:
        """Get secret from environment or encrypted storage"""
        
        # Convert path to environment variable
        env_key = path.replace('/', '_').upper()
        env_value = getattr(settings, env_key, None)
        
        if env_value:
            if key:
                # Parse JSON if needed
                try:
                    data = json.loads(env_value)
                    return data.get(key)
                except:
                    pass
            return env_value
        
        # Try encrypted local storage
        try:
            encrypted = await self._read_encrypted_file(path)
            if encrypted:
                decrypted = self.fernet.decrypt(encrypted.encode()).decode()
                data = json.loads(decrypted)
                return data.get(key) if key else data
        except Exception as e:
            logger.error(f"Failed to decrypt local secret: {e}")
        
        return None
    
    async def _read_encrypted_file(self, path: str) -> Optional[str]:
        """Read encrypted file from local storage"""
        import os
        
        file_path = f"/etc/secrets/{path}.enc"
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return f.read().strip()
        
        return None
    
    async def encrypt(self, data: str) -> str:
        """Encrypt data using local encryption"""
        encrypted = self.fernet.encrypt(data.encode())
        return encrypted.decode()
    
    async def decrypt(self, encrypted_data: str) -> str:
        """Decrypt data using local encryption"""
        decrypted = self.fernet.decrypt(encrypted_data.encode())
        return decrypted.decode()
    
    async def generate_database_credentials(
        self,
        database: str,
        ttl: str = "1h"
    ) -> Dict[str, str]:
        """Generate dynamic database credentials"""
        
        if not self.vault_client:
            return {}
        
        try:
            response = self.vault_client.secrets.database.generate_credentials(
                name=database,
                mount_point='database'
            )
            
            return {
                "username": response['data']['username'],
                "password": response['data']['password'],
                "lease_id": response['lease_id'],
                "lease_duration": response['lease_duration']
            }
            
        except Exception as e:
            logger.error(f"Failed to generate database credentials: {e}")
            return {}