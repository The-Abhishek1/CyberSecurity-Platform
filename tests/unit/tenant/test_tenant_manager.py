#!/usr/bin/env python3
"""
Unit tests for Tenant Manager
"""
import pytest
import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from src.utils.logging import logger
from src.autonomous.adaptive_scanner import AdaptiveScanner
from src.memory.memory_service import MemoryService
from src.memory.vector_store import VectorStore
from src.memory.graph_store import GraphStore
from src.memory.time_series_store import TimeSeriesStore
from src.tenant.tenant_manager import TenantManager, TenantTier, TenantStatus
from src.tenant.isolation.data_isolation import DataIsolation
from src.tenant.isolation.compute_isolation import ComputeIsolation
from src.tenant.isolation.network_isolation import NetworkIsolation
from src.tenant.billing.usage_aggregator import UsageAggregator
from src.tenant.billing.billing_calculator import BillingCalculator

class TestTenantManager:
    """Test suite for Tenant Manager"""
    
    def setup_method(self):
        """Setup before each test"""
        # Use real instances for testing
        self.data_isolation = DataIsolation()
        self.compute_isolation = ComputeIsolation()
        self.network_isolation = NetworkIsolation()
        self.usage_aggregator = UsageAggregator()
        self.billing_calculator = BillingCalculator(self.usage_aggregator)
        
        self.manager = TenantManager(
            data_isolation=self.data_isolation,
            compute_isolation=self.compute_isolation,
            network_isolation=self.network_isolation,
            usage_aggregator=self.usage_aggregator,
            billing_calculator=self.billing_calculator
        )
    
    @pytest.mark.asyncio
    async def test_tenant_manager_initialization(self):
        """Test tenant manager initialization"""
        assert self.manager is not None
        assert hasattr(self.manager, 'create_tenant')
        assert hasattr(self.manager, 'get_tenant')
        logger.info("✅ Tenant Manager initialized successfully")
    
    @pytest.mark.asyncio
    async def test_create_tenant(self):
        """Test tenant creation"""
        # Check the actual signature of create_tenant
        import inspect
        sig = inspect.signature(self.manager.create_tenant)
        logger.info(f"create_tenant signature: {sig}")
        
        # Create tenant with all required parameters
        tenant = await self.manager.create_tenant(
            name="Test Corp",
            admin_email="admin@testcorp.com",  # Add required admin_email
            tier=TenantTier.ENTERPRISE,
            settings={
                "max_users": 50,
                "max_concurrent_scans": 10,
                "storage_gb": 100
            }
        )
        
        assert "tenant_id" in tenant
        assert tenant["name"] == "Test Corp"
        assert tenant["tier"] == "enterprise"
        logger.info(f"✅ Created tenant: {tenant['name']} (ID: {tenant['tenant_id']})")
    
    @pytest.mark.asyncio
    async def test_get_tenant(self):
        """Test retrieving tenant"""
        # Create tenant first
        created = await self.manager.create_tenant(
            name="Get Test",
            plan="basic",
            settings={}
        )
        
        # Retrieve tenant
        tenant = await self.manager.get_tenant(created["tenant_id"])
        
        assert tenant is not None
        assert tenant["name"] == "Get Test"
        logger.info(f"✅ Retrieved tenant: {tenant['name']}")
    
    @pytest.mark.asyncio
    async def test_update_tenant(self):
        """Test updating tenant"""
        # Create tenant with all required parameters
        created = await self.manager.create_tenant(
            name="Update Test",
            admin_email="update@test.com",
            tier=TenantTier.BASIC,
            settings={"initial": "value"}
        )
        
        # Update tenant
        updated = await self.manager.update_tenant(
            created["tenant_id"],
            {"settings": {"plan": "enterprise", "max_users": 100}}
        )
        
        assert updated["settings"]["max_users"] == 100
        logger.info(f"✅ Updated tenant")
    
    @pytest.mark.asyncio
    async def test_delete_tenant(self):
        """Test deleting tenant"""
        # Create tenant
        created = await self.manager.create_tenant(
            name="Delete Test",
            plan="basic",
            settings={}
        )
        
        # Delete tenant
        result = await self.manager.delete_tenant(created["tenant_id"])
        
        assert result is True
        
        # Verify deletion
        tenant = await self.manager.get_tenant(created["tenant_id"])
        assert tenant is None
        logger.info("✅ Deleted tenant successfully")

# Manual test function
async def manual_test():
    """Manual test function"""
    print("="*60)
    print("🧪 Testing Tenant Manager")
    print("="*60)
    
    test = TestTenantManager()
    test.setup_method()
    
    print("\n1️⃣ Testing initialization...")
    await test.test_tenant_manager_initialization()
    
    print("\n2️⃣ Testing create tenant...")
    await test.test_create_tenant()
    
    print("\n3️⃣ Testing get tenant...")
    await test.test_get_tenant()
    
    print("\n4️⃣ Testing update tenant...")
    await test.test_update_tenant()
    
    print("\n5️⃣ Testing delete tenant...")
    await test.test_delete_tenant()
    
    print("\n✅ All tenant manager tests passed!")

if __name__ == "__main__":
    asyncio.run(manual_test())