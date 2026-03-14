from typing import Dict, Any, Optional
import re
from src.utils.logging import logger  


class DataMaskingManager:
    """
    Data Masking Manager
    
    Features:
    - Dynamic data masking
    - Pattern-based masking
    - Role-based unmasking
    - Consistent masking
    """
    
    def __init__(self):
        # Masking patterns
        self.masking_patterns = {
            "email": (r'([^@]+)@', lambda m: '*' * len(m.group(1)) + '@'),
            "phone": (r'(\d{3})[-.]?(\d{3})[-.]?(\d{4})', 'XXX-XXX-\\3'),
            "ssn": (r'\d{3}-\d{2}-\d{4}', 'XXX-XX-\\3'),
            "credit_card": (r'\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}', 'XXXX-XXXX-XXXX-\\4'),
            "ip_address": (r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', 'XXX.XXX.XXX.\\4'),
            "api_key": (r'[a-zA-Z0-9]{20,40}', lambda m: m.group()[:4] + '*' * (len(m.group()) - 8) + m.group()[-4:])
        }
        
        logger.info("Data Masking Manager initialized")
    
    async def mask_data(
        self,
        data: Any,
        pattern_type: Optional[str] = None,
        role: Optional[str] = None
    ) -> Any:
        """Mask sensitive data"""
        
        if isinstance(data, str):
            return await self._mask_string(data, pattern_type, role)
        elif isinstance(data, dict):
            return await self._mask_dict(data, pattern_type, role)
        elif isinstance(data, list):
            return [await self.mask_data(item, pattern_type, role) for item in data]
        
        return data
    
    async def _mask_string(
        self,
        data: str,
        pattern_type: Optional[str],
        role: Optional[str]
    ) -> str:
        """Mask sensitive data in string"""
        
        # Check if role allows unmasking
        if role and await self._can_unmask(role, pattern_type):
            return data
        
        masked = data
        
        if pattern_type and pattern_type in self.masking_patterns:
            # Apply specific pattern
            pattern, replacement = self.masking_patterns[pattern_type]
            if callable(replacement):
                masked = re.sub(pattern, replacement, masked)
            else:
                masked = re.sub(pattern, replacement, masked)
        else:
            # Apply all patterns
            for ptype, (pattern, replacement) in self.masking_patterns.items():
                if callable(replacement):
                    masked = re.sub(pattern, replacement, masked)
                else:
                    masked = re.sub(pattern, replacement, masked)
        
        return masked
    
    async def _mask_dict(
        self,
        data: Dict,
        pattern_type: Optional[str],
        role: Optional[str]
    ) -> Dict:
        """Mask sensitive data in dictionary"""
        
        masked = {}
        
        for key, value in data.items():
            # Check if key indicates sensitive data
            sensitive_keywords = ['password', 'token', 'secret', 'key', 'credential']
            if any(kw in key.lower() for kw in sensitive_keywords):
                masked[key] = "[MASKED]"
            else:
                masked[key] = await self.mask_data(value, pattern_type, role)
        
        return masked
    
    async def _can_unmask(self, role: str, pattern_type: Optional[str]) -> bool:
        """Check if role can unmask data"""
        
        # Define unmasking permissions
        unmask_permissions = {
            "admin": ["*"],
            "security_engineer": ["email", "ip_address"],
            "auditor": ["email"],
            "viewer": []
        }
        
        allowed = unmask_permissions.get(role, [])
        
        if "*" in allowed:
            return True
        
        if pattern_type and pattern_type in allowed:
            return True
        
        return False
    
    async def consistent_mask(
        self,
        data: str,
        salt: Optional[str] = None
    ) -> str:
        """Apply consistent masking (same input -> same masked output)"""
        
        import hashlib
        
        # Create hash for consistent masking
        hash_input = f"{data}{salt or ''}".encode()
        hash_value = hashlib.sha256(hash_input).hexdigest()
        
        # Use hash to generate consistent masked value
        if '@' in data:  # Email
            local, domain = data.split('@')
            masked_local = hash_value[:len(local)]
            return f"{masked_local}@{domain}"
        elif data.replace('.', '').isdigit():  # IP or number
            return hash_value[:len(data)]
        else:
            return hash_value[:len(data)]