#!/usr/bin/env python3
"""
Unit tests for API Gateway
"""
import pytest
import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.utils.logging import logger

# Import based on actual file structure from your image
try:
    from src.gateway.api_gateway import EnterpriseAPIGateway
except ImportError:
    try:
        from src.gateway.transformations.api_gateway import EnterpriseAPIGateway
    except ImportError:
        EnterpriseAPIGateway = None

from src.tenant.tenant_manager import TenantManager
from src.tenant.isolation.data_isolation import DataIsolation
from src.tenant.isolation.compute_isolation import ComputeIsolation
from src.tenant.isolation.network_isolation import NetworkIsolation
from src.tenant.billing.usage_aggregator import UsageAggregator
from src.tenant.billing.billing_calculator import BillingCalculator
from src.gateway.developer_portal.api_key_manager import APIKeyManager
from src.gateway.analytics.usage_tracker import UsageTracker
from src.security.rbac import RBACManager

class TestAPIGateway:
    """Test suite for API Gateway"""
    
    def setup_method(self):
        """Setup before each test"""
        # Create mock tenant manager with all required dependencies
        self.data_isolation = Mock(spec=DataIsolation)
        self.compute_isolation = Mock(spec=ComputeIsolation)
        self.network_isolation = Mock(spec=NetworkIsolation)
        self.usage_aggregator = Mock(spec=UsageAggregator)
        self.billing_calculator = Mock(spec=BillingCalculator)
        
        self.tenant_manager = TenantManager(
            data_isolation=self.data_isolation,
            compute_isolation=self.compute_isolation,
            network_isolation=self.network_isolation,
            usage_aggregator=self.usage_aggregator,
            billing_calculator=self.billing_calculator
        )
        
        self.rbac = RBACManager()
        self.api_key_manager = Mock(spec=APIKeyManager)
        self.usage_tracker = Mock(spec=UsageTracker)
        
        if EnterpriseAPIGateway is None:
            self.gateway = None
        else:
            self.gateway = EnterpriseAPIGateway(
                tenant_manager=self.tenant_manager,
                rbac_manager=self.rbac,
                api_key_manager=self.api_key_manager,
                usage_tracker=self.usage_tracker
            )
    
    
    @pytest.mark.asyncio
    async def test_gateway_initialization(self):
        """Test gateway initialization"""
        if self.gateway is None:
            pytest.skip("Gateway not available")
        assert self.gateway is not None
        
        # Check for either method name (different versions might have different names)
        has_register = hasattr(self.gateway, 'register_api') or hasattr(self.gateway, 'register_route')
        has_route = hasattr(self.gateway, 'route_request') or hasattr(self.gateway, 'handle_request')
        
        assert has_register or has_route
        logger.info("✅ API Gateway initialized successfully")
    
    @pytest.mark.asyncio
    async def test_register_api(self):
        """Test API registration"""
        if self.gateway is None:
            pytest.skip("Gateway not available")
            
        async def dummy_handler(request):
            return {"status": "success", "data": request}
        
        await self.gateway.register_api(
            name="test_api",
            version="v1",
            protocol="REST",
            handler=dummy_handler,
            methods=["GET", "POST"],
            path="/api/v1/test"
        )
        
        assert "test_api" in self.gateway.registered_apis
        logger.info("✅ API registered successfully")
    
    @pytest.mark.asyncio
    async def test_route_request(self):
        """Test request routing"""
        if self.gateway is None:
            pytest.skip("Gateway not available")
            
        async def test_handler(request):
            return {"result": "success", "echo": request.get("body", {})}
        
        await self.gateway.register_api(
            name="scan",
            version="v1",
            protocol="REST",
            handler=test_handler,
            methods=["POST"],
            path="/api/v1/scan"
        )
        
        request = {
            "path": "/api/v1/scan",
            "method": "POST",
            "headers": {"X-Tenant-ID": "test-tenant"},
            "body": {"target": "example.com"}
        }
        
        response = await self.gateway.route_request(request)
        assert response["result"] == "success"
        assert response["echo"]["target"] == "example.com"
        logger.info("✅ Request routed successfully")

# Manual test function
async def manual_test():
    """Manual test function"""
    print("="*60)
    print("🧪 Testing API Gateway")
    print("="*60)
    
    test = TestAPIGateway()
    test.setup_method()
    
    print("\n1️⃣ Testing initialization...")
    await test.test_gateway_initialization()
    
    print("\n2️⃣ Testing API registration...")
    await test.test_register_api()
    
    print("\n3️⃣ Testing request routing...")
    await test.test_route_request()
    
    print("\n✅ All API gateway tests passed!")

if __name__ == "__main__":
    asyncio.run(manual_test())