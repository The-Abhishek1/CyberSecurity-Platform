from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import base64
import secrets
import pyotp
import qrcode
import io
from src.core.config import get_settings

settings = get_settings()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SecurityService:
    """Enterprise security service handling all security operations"""
    
    def __init__(self):
        self.jwt_secret = settings.auth.jwt_secret_key.get_secret_value()
        self.jwt_algorithm = settings.auth.jwt_algorithm
        self.access_token_expire = settings.auth.jwt_access_token_expire_minutes
        self.refresh_token_expire = settings.auth.jwt_refresh_token_expire_days
        
        # Initialize encryption
        self._init_encryption()
    
    def _init_encryption(self):
        """Initialize field-level encryption"""
        key = settings.encryption.field_encryption_key.get_secret_value()
        # Derive a proper Fernet key
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"fixed_salt_please_change",  # In production, use a secure random salt per deployment
            iterations=100000,
        )
        key_bytes = kdf.derive(key.encode())
        self.fernet = Fernet(base64.urlsafe_b64encode(key_bytes))
    
    # ========== Password Management ==========
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against a hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)
    
    def validate_password_strength(self, password: str) -> Dict[str, bool]:
        """Validate password against enterprise strength requirements"""
        checks = {
            "length": len(password) >= 12,
            "uppercase": any(c.isupper() for c in password),
            "lowercase": any(c.islower() for c in password),
            "digits": any(c.isdigit() for c in password),
            "special": any(not c.isalnum() for c in password),
            "no_common": password.lower() not in self._get_common_passwords(),
        }
        return checks
    
    def _get_common_passwords(self) -> List[str]:
        """Return list of common passwords (in production, load from file)"""
        return ["password", "password123", "admin", "welcome", "login"]
    
    # ========== JWT Management ==========
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire)
        
        to_encode.update({
            "exp": expire,
            "type": "access",
            "jti": secrets.token_hex(16)  # Unique token ID
        })
        encoded_jwt = jwt.encode(to_encode, self.jwt_secret, algorithm=self.jwt_algorithm)
        return encoded_jwt
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create a JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire)
        
        to_encode.update({
            "exp": expire,
            "type": "refresh",
            "jti": secrets.token_hex(16)
        })
        encoded_jwt = jwt.encode(to_encode, self.jwt_secret, algorithm=self.jwt_algorithm)
        return encoded_jwt
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate a JWT token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            return payload
        except JWTError as e:
            raise ValueError(f"Invalid token: {str(e)}")
    
    def verify_token_type(self, token: str, expected_type: str) -> bool:
        """Verify that a token is of the expected type"""
        try:
            payload = self.decode_token(token)
            return payload.get("type") == expected_type
        except ValueError:
            return False
    
    # ========== API Key Management ==========
    def generate_api_key(self) -> str:
        """Generate a secure API key"""
        return f"eso_{secrets.token_urlsafe(32)}"
    
    def hash_api_key(self, api_key: str) -> str:
        """Hash an API key for storage"""
        return self.get_password_hash(api_key)
    
    def verify_api_key(self, plain_api_key: str, hashed_api_key: str) -> bool:
        """Verify an API key against its hash"""
        return self.verify_password(plain_api_key, hashed_api_key)
    
    # ========== Field-Level Encryption ==========
    def encrypt_field(self, data: str) -> str:
        """Encrypt a sensitive field"""
        encrypted = self.fernet.encrypt(data.encode())
        return encrypted.decode()
    
    def decrypt_field(self, encrypted_data: str) -> str:
        """Decrypt a sensitive field"""
        decrypted = self.fernet.decrypt(encrypted_data.encode())
        return decrypted.decode()
    
    def encrypt_dict_fields(self, data: Dict[str, Any], fields: List[str]) -> Dict[str, Any]:
        """Encrypt specified fields in a dictionary"""
        result = data.copy()
        for field in fields:
            if field in result and isinstance(result[field], str):
                result[field] = self.encrypt_field(result[field])
        return result
    
    def decrypt_dict_fields(self, data: Dict[str, Any], fields: List[str]) -> Dict[str, Any]:
        """Decrypt specified fields in a dictionary"""
        result = data.copy()
        for field in fields:
            if field in result and isinstance(result[field], str):
                try:
                    result[field] = self.decrypt_field(result[field])
                except:
                    # If decryption fails, leave as is
                    pass
        return result
    
    # ========== MFA/TOTP ==========
    def generate_totp_secret(self) -> str:
        """Generate a TOTP secret for MFA"""
        return pyotp.random_base32()
    
    def get_totp_uri(self, secret: str, email: str) -> str:
        """Get TOTP URI for QR code generation"""
        return pyotp.totp.TOTP(secret).provisioning_uri(
            name=email,
            issuer_name=settings.auth.mfa_issuer_name
        )
    
    def generate_qr_code(self, uri: str) -> bytes:
        """Generate QR code for TOTP setup"""
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        return img_bytes.getvalue()
    
    def verify_totp(self, secret: str, token: str) -> bool:
        """Verify a TOTP token"""
        totp = pyotp.TOTP(secret)
        return totp.verify(token)
    
    # ========== Data Masking ==========
    def mask_sensitive_data(self, data: str, visible_chars: int = 4) -> str:
        """Mask sensitive data (e.g., credit cards, API keys)"""
        if len(data) <= visible_chars:
            return "*" * len(data)
        return data[:visible_chars] + "*" * (len(data) - visible_chars)
    
    def mask_email(self, email: str) -> str:
        """Mask email address"""
        if "@" not in email:
            return self.mask_sensitive_data(email)
        
        local, domain = email.split("@", 1)
        masked_local = self.mask_sensitive_data(local, 2)
        return f"{masked_local}@{domain}"
    
    # ========== CSRF Protection ==========
    def generate_csrf_token(self) -> str:
        """Generate a CSRF token"""
        return secrets.token_urlsafe(32)
    
    def validate_csrf_token(self, token: str, stored_token: str) -> bool:
        """Validate a CSRF token (constant-time comparison)"""
        return secrets.compare_digital(token, stored_token)


# Singleton instance
security_service = SecurityService()