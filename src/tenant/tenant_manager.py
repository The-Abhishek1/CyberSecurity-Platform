from typing import Dict, Optional, List
from datetime import datetime
import uuid
import json

from src.tenant.isolation.data_isolation import DataIsolation
from src.tenant.isolation.compute_isolation import ComputeIsolation
from src.tenant.isolation.network_isolation import NetworkIsolation
from src.tenant.billing.usage_aggregator import UsageAggregator
from src.tenant.billing.billing_calculator import BillingCalculator
from src.utils.logging import logger


class TenantStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"
    PENDING = "pending"


class TenantTier(str, Enum):
    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class TenantManager:
    """
    Enterprise Tenant Manager
    
    Features:
    - Tenant lifecycle management
    - Tenant isolation (data, compute, network)
    - Tenant configuration
    - Quota management
    - Cross-tenant collaboration
    - Billing integration
    """
    
    def __init__(
        self,
        data_isolation: DataIsolation,
        compute_isolation: ComputeIsolation,
        network_isolation: NetworkIsolation,
        usage_aggregator: UsageAggregator,
        billing_calculator: BillingCalculator
    ):
        self.data_isolation = data_isolation
        self.compute_isolation = compute_isolation
        self.network_isolation = network_isolation
        self.usage_aggregator = usage_aggregator
        self.billing_calculator = billing_calculator
        
        # Tenant storage
        self.tenants: Dict[str, Dict] = {}
        
        # Tenant quotas
        self.quotas: Dict[str, Dict] = {}
        
        # Tenant configurations
        self.configs: Dict[str, Dict] = {}
        
        # Cross-tenant relationships
        self.relationships: Dict[str, List[str]] = {}
        
        logger.info("Tenant Manager initialized")
    
    async def create_tenant(
        self,
        name: str,
        tier: TenantTier = TenantTier.BASIC,
        admin_email: str,
        settings: Optional[Dict] = None
    ) -> Dict:
        """Create new tenant"""
        
        tenant_id = f"tenant_{uuid.uuid4().hex[:12]}"
        
        tenant = {
            "tenant_id": tenant_id,
            "name": name,
            "tier": tier.value,
            "status": TenantStatus.PENDING.value,
            "admin_email": admin_email,
            "created_at": datetime.utcnow().isoformat(),
            "settings": settings or {},
            "features": self._get_tier_features(tier)
        }
        
        self.tenants[tenant_id] = tenant
        
        # Initialize isolation layers
        await self.data_isolation.initialize_tenant(tenant_id)
        await self.compute_isolation.initialize_tenant(tenant_id, tier)
        await self.network_isolation.initialize_tenant(tenant_id)
        
        # Set default quotas
        await self.set_tenant_quotas(tenant_id, self._get_default_quotas(tier))
        
        # Set default config
        self.configs[tenant_id] = self._get_default_config(tier)
        
        logger.info(f"Created tenant {tenant_id}: {name} ({tier.value})")
        
        return tenant
    
    async def activate_tenant(self, tenant_id: str):
        """Activate tenant"""
        
        if tenant_id in self.tenants:
            self.tenants[tenant_id]["status"] = TenantStatus.ACTIVE.value
            self.tenants[tenant_id]["activated_at"] = datetime.utcnow().isoformat()
            logger.info(f"Activated tenant {tenant_id}")
    
    async def suspend_tenant(self, tenant_id: str, reason: str):
        """Suspend tenant"""
        
        if tenant_id in self.tenants:
            self.tenants[tenant_id]["status"] = TenantStatus.SUSPENDED.value
            self.tenants[tenant_id]["suspended_at"] = datetime.utcnow().isoformat()
            self.tenants[tenant_id]["suspension_reason"] = reason
            logger.info(f"Suspended tenant {tenant_id}: {reason}")
    
    async def delete_tenant(self, tenant_id: str):
        """Delete tenant (soft delete)"""
        
        if tenant_id in self.tenants:
            self.tenants[tenant_id]["status"] = TenantStatus.DELETED.value
            self.tenants[tenant_id]["deleted_at"] = datetime.utcnow().isoformat()
            
            # Clean up isolation layers
            await self.data_isolation.cleanup_tenant(tenant_id)
            await self.compute_isolation.cleanup_tenant(tenant_id)
            await self.network_isolation.cleanup_tenant(tenant_id)
            
            logger.info(f"Deleted tenant {tenant_id}")
    
    async def get_tenant(self, tenant_id: str) -> Optional[Dict]:
        """Get tenant information"""
        return self.tenants.get(tenant_id)
    
    async def list_tenants(self, status: Optional[str] = None) -> List[Dict]:
        """List all tenants"""
        
        if status:
            return [t for t in self.tenants.values() if t["status"] == status]
        return list(self.tenants.values())
    
    async def set_tenant_quotas(self, tenant_id: str, quotas: Dict):
        """Set tenant quotas"""
        
        self.quotas[tenant_id] = {
            **quotas,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Set quotas for tenant {tenant_id}: {quotas}")
    
    async def get_tenant_quotas(self, tenant_id: str) -> Dict:
        """Get tenant quotas"""
        
        quotas = self.quotas.get(tenant_id, {})
        
        # Add current usage
        usage = await self.usage_aggregator.get_tenant_usage(tenant_id)
        
        return {
            "quotas": quotas,
            "usage": usage,
            "remaining": {
                key: quotas.get(key, 0) - usage.get(key, 0)
                for key in quotas.keys()
            }
        }
    
    async def check_tenant_quota(
        self,
        tenant_id: str,
        resource: str,
        amount: int = 1
    ) -> bool:
        """Check if tenant has quota available"""
        
        quotas = self.quotas.get(tenant_id, {})
        usage = await self.usage_aggregator.get_tenant_usage(tenant_id)
        
        current_usage = usage.get(resource, 0)
        quota_limit = quotas.get(resource, float('inf'))
        
        return (current_usage + amount) <= quota_limit
    
    async def create_relationship(
        self,
        tenant_id: str,
        related_tenant_id: str,
        relationship_type: str
    ):
        """Create cross-tenant relationship"""
        
        if tenant_id not in self.relationships:
            self.relationships[tenant_id] = []
        
        self.relationships[tenant_id].append({
            "tenant_id": related_tenant_id,
            "type": relationship_type,
            "created_at": datetime.utcnow().isoformat()
        })
        
        logger.info(f"Created {relationship_type} relationship between {tenant_id} and {related_tenant_id}")
    
    async def get_related_tenants(
        self,
        tenant_id: str,
        relationship_type: Optional[str] = None
    ) -> List[Dict]:
        """Get related tenants"""
        
        related = self.relationships.get(tenant_id, [])
        
        if relationship_type:
            related = [r for r in related if r["type"] == relationship_type]
        
        return related
    
    def _get_tier_features(self, tier: TenantTier) -> List[str]:
        """Get features for tier"""
        
        features = {
            TenantTier.FREE: ["basic_scanning", "email_reports", "7_day_retention"],
            TenantTier.BASIC: ["basic_scanning", "api_access", "email_reports", "30_day_retention"],
            TenantTier.PROFESSIONAL: ["advanced_scanning", "api_access", "slack_integration", "90_day_retention", "custom_reports"],
            TenantTier.ENTERPRISE: ["all_features", "sso", "audit_logs", "365_day_retention", "dedicated_support", "custom_integrations"]
        }
        
        return features.get(tier, [])
    
    def _get_default_quotas(self, tier: TenantTier) -> Dict:
        """Get default quotas for tier"""
        
        quotas = {
            TenantTier.FREE: {
                "executions_per_month": 100,
                "concurrent_executions": 2,
                "storage_gb": 1,
                "api_calls_per_day": 1000,
                "team_members": 1
            },
            TenantTier.BASIC: {
                "executions_per_month": 1000,
                "concurrent_executions": 5,
                "storage_gb": 10,
                "api_calls_per_day": 10000,
                "team_members": 5
            },
            TenantTier.PROFESSIONAL: {
                "executions_per_month": 10000,
                "concurrent_executions": 20,
                "storage_gb": 100,
                "api_calls_per_day": 100000,
                "team_members": 20
            },
            TenantTier.ENTERPRISE: {
                "executions_per_month": 100000,
                "concurrent_executions": 100,
                "storage_gb": 1000,
                "api_calls_per_day": 1000000,
                "team_members": 100
            }
        }
        
        return quotas.get(tier, {})
    
    def _get_default_config(self, tier: TenantTier) -> Dict:
        """Get default configuration for tier"""
        
        return {
            "retention_days": {
                TenantTier.FREE: 7,
                TenantTier.BASIC: 30,
                TenantTier.PROFESSIONAL: 90,
                TenantTier.ENTERPRISE: 365
            }.get(tier, 30),
            "audit_logging": tier in [TenantTier.PROFESSIONAL, TenantTier.ENTERPRISE],
            "sso_enabled": tier == TenantTier.ENTERPRISE,
            "custom_domains": tier == TenantTier.ENTERPRISE,
            "notification_channels": self._get_notification_channels(tier)
        }
    
    def _get_notification_channels(self, tier: TenantTier) -> List[str]:
        """Get available notification channels for tier"""
        
        channels = {
            TenantTier.FREE: ["email"],
            TenantTier.BASIC: ["email", "webhook"],
            TenantTier.PROFESSIONAL: ["email", "webhook", "slack"],
            TenantTier.ENTERPRISE: ["email", "webhook", "slack", "pagerduty", "teams"]
        }
        
        return channels.get(tier, ["email"])