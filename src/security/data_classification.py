from typing import Dict, Any, List, Optional
import re
import hashlib
from enum import Enum

class DataClassificationLevel(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    CRITICAL = "critical"


class DataClassificationManager:
    """
    Data Classification Manager
    
    Features:
    - Automatic data classification
    - PII detection
    - Sensitive data tagging
    - Classification policies
    """
    
    def __init__(self):
        # PII patterns
        self.pii_patterns = {
            "email": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
            "credit_card": r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
            "ip_address": r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
            "api_key": r'[a-zA-Z0-9]{20,40}'
        }
        
        # Classification rules
        self.classification_rules = {
            DataClassificationLevel.PUBLIC: {
                "patterns": [],
                "max_pii_count": 0,
                "requires_encryption": False
            },
            DataClassificationLevel.INTERNAL: {
                "patterns": ["email", "ip_address"],
                "max_pii_count": 10,
                "requires_encryption": False
            },
            DataClassificationLevel.CONFIDENTIAL: {
                "patterns": ["ssn", "credit_card"],
                "max_pii_count": 100,
                "requires_encryption": True
            },
            DataClassificationLevel.RESTRICTED: {
                "patterns": ["all"],
                "max_pii_count": None,
                "requires_encryption": True
            },
            DataClassificationLevel.CRITICAL: {
                "patterns": ["all"],
                "max_pii_count": None,
                "requires_encryption": True
            }
        }
        
        # Classification cache
        self.classification_cache: Dict[str, Dict] = {}
    
    async def classify_data(
        self,
        data: Any,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Classify data based on content and context"""
        
        # Convert to string for pattern matching
        if not isinstance(data, str):
            data_str = json.dumps(data)
        else:
            data_str = data
        
        # Generate cache key
        cache_key = hashlib.md5(data_str.encode()).hexdigest()
        
        # Check cache
        if cache_key in self.classification_cache:
            cached = self.classification_cache[cache_key]
            if (datetime.utcnow() - cached["timestamp"]).seconds < 3600:
                return cached["result"]
        
        # Detect PII
        pii_found = await self._detect_pii(data_str)
        
        # Determine classification level
        level = await self._determine_level(pii_found, context)
        
        # Check encryption requirement
        requires_encryption = self.classification_rules[level]["requires_encryption"]
        
        result = {
            "level": level.value,
            "pii_detected": pii_found,
            "requires_encryption": requires_encryption,
            "classification_timestamp": datetime.utcnow().isoformat(),
            "data_hash": cache_key
        }
        
        # Cache result
        self.classification_cache[cache_key] = {
            "result": result,
            "timestamp": datetime.utcnow()
        }
        
        return result
    
    async def _detect_pii(self, data: str) -> List[Dict]:
        """Detect PII in data"""
        
        pii_found = []
        
        for pii_type, pattern in self.pii_patterns.items():
            matches = re.finditer(pattern, data)
            for match in matches:
                pii_found.append({
                    "type": pii_type,
                    "value": match.group(),
                    "position": match.span()
                })
        
        return pii_found
    
    async def _determine_level(
        self,
        pii_found: List[Dict],
        context: Optional[Dict]
    ) -> DataClassificationLevel:
        """Determine classification level"""
        
        # Check for critical data
        if context and context.get("data_type") in ["credentials", "encryption_keys"]:
            return DataClassificationLevel.CRITICAL
        
        # Check for restricted data
        restricted_patterns = ["ssn", "credit_card"]
        for pii in pii_found:
            if pii["type"] in restricted_patterns:
                return DataClassificationLevel.RESTRICTED
        
        # Check for confidential data
        if len(pii_found) > 10:
            return DataClassificationLevel.CONFIDENTIAL
        elif len(pii_found) > 0:
            return DataClassificationLevel.CONFIDENTIAL
        
        # Check context
        if context and context.get("source") == "internal":
            return DataClassificationLevel.INTERNAL
        
        # Default
        return DataClassificationLevel.PUBLIC
    
    async def redact_sensitive_data(
        self,
        data: Any,
        level: DataClassificationLevel
    ) -> Any:
        """Redact sensitive data based on classification"""
        
        if isinstance(data, str):
            return await self._redact_string(data, level)
        elif isinstance(data, dict):
            return await self._redact_dict(data, level)
        elif isinstance(data, list):
            return [await self.redact_sensitive_data(item, level) for item in data]
        
        return data
    
    async def _redact_string(self, data: str, level: DataClassificationLevel) -> str:
        """Redact sensitive data in string"""
        
        redacted = data
        
        for pii_type, pattern in self.pii_patterns.items():
            # Redact all PII for restricted and critical
            if level in [DataClassificationLevel.RESTRICTED, DataClassificationLevel.CRITICAL]:
                redacted = re.sub(pattern, "[REDACTED]", redacted)
            # Redact only sensitive PII for confidential
            elif level == DataClassificationLevel.CONFIDENTIAL:
                if pii_type in ["ssn", "credit_card"]:
                    redacted = re.sub(pattern, "[REDACTED]", redacted)
                else:
                    # Mask but show last 4
                    def mask_match(match):
                        value = match.group()
                        if len(value) > 4:
                            return "*" * (len(value) - 4) + value[-4:]
                        return "[REDACTED]"
                    
                    redacted = re.sub(pattern, mask_match, redacted)
        
        return redacted
    
    async def _redact_dict(self, data: Dict, level: DataClassificationLevel) -> Dict:
        """Redact sensitive data in dictionary"""
        
        redacted = {}
        
        for key, value in data.items():
            # Check if key indicates sensitive data
            sensitive_keywords = ['password', 'token', 'secret', 'key', 'credential']
            if any(kw in key.lower() for kw in sensitive_keywords):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = await self.redact_sensitive_data(value, level)
        
        return redacted
    
    async def get_classification_policy(self, level: DataClassificationLevel) -> Dict:
        """Get policy for classification level"""
        return self.classification_rules.get(level, {})