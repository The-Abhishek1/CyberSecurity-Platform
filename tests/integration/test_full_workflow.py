#!/usr/bin/env python3
"""
Integration tests for complete enterprise workflow
"""
import pytest
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.logging import logger
from src.autonomous.adaptive_scanner import AdaptiveScanner
from src.memory.memory_service import MemoryService
from src.memory.vector_store import VectorStore
from src.memory.graph_store import GraphStore
from src.memory.time_series_store import TimeSeriesStore

from src.memory.memory_service import MemoryService
from src.memory.vector_store import VectorStore
from src.memory.graph_store import GraphStore
from src.memory.time_series_store import TimeSeriesStore
from src.tools.tool_registry import ToolRegistry
from src.tools.tool_router import ToolRouter
from src.workers.worker_pool import WorkerPool
from src.workers.container import ContainerManager
from src.workers.network_manager import NetworkManager
from src.workers.resource_monitor import ResourceMonitor
from src.autonomous.adaptive_scanner import AdaptiveScanner
from src.recommendation.tool_recommender import ToolRecommender
from src.recommendation.parameter_optimizer import ParameterOptimizer
from src.ai.model_manager import ModelManager
from src.tenant.tenant_manager import TenantManager
from src.tenant.isolation.data_isolation import DataIsolation
from src.tenant.billing.billing_calculator import BillingCalculator

class TestEnterpriseWorkflow:
    """Test complete enterprise workflow"""
    
    @pytest.fixture
    async def enterprise_components(self):
        """Initialize all enterprise components"""
        components = {}
        
        # Memory
        components['vector'] = VectorStore()
        components['graph'] = GraphStore()
        components['ts'] = TimeSeriesStore()
        components['memory'] = MemoryService(
            components['vector'], 
            components['graph'], 
            components['ts']
        )
        
        # Workers
        components['container'] = ContainerManager()
        components['network'] = NetworkManager()
        components['resource'] = ResourceMonitor()
        components['worker_pool'] = WorkerPool(
            components['container'],
            components['resource'],
            components['network']
        )
        
        # Tools
        components['tool_registry'] = ToolRegistry()
        components['worker_pool'].tool_registry = components['tool_registry']
        
        components['tool_router'] = ToolRouter(
            components['tool_registry'],
            components['worker_pool']
        )
        
        # AI Components
        components['model_manager'] = ModelManager()
        components['tool_recommender'] = ToolRecommender(
            components['memory'],
            components['model_manager']
        )
        components['param_optimizer'] = ParameterOptimizer(components['memory'])
        components['adaptive_scanner'] = AdaptiveScanner(components['memory'])
        
        # Tenant
        components['data_isolation'] = DataIsolation()
        components['billing'] = BillingCalculator()
        components['tenant_manager'] = TenantManager(
            components['data_isolation'],
            components['billing']
        )
        
        return components
    
    @pytest.mark.asyncio
    async def test_component_initialization(self, enterprise_components):
        """Test all components initialize correctly"""
        assert enterprise_components['memory'] is not None
        assert enterprise_components['worker_pool'] is not None
        assert enterprise_components['tool_router'] is not None
        assert enterprise_components['tool_recommender'] is not None
        assert enterprise_components['param_optimizer'] is not None
        assert enterprise_components['adaptive_scanner'] is not None
        assert enterprise_components['tenant_manager'] is not None
        print("✅ All components initialized successfully")
    
    @pytest.mark.asyncio
    async def test_tool_recommendation_flow(self, enterprise_components):
        """Test tool recommendation flow"""
        recommender = enterprise_components['tool_recommender']
        
        recommendations = await recommender.recommend_tools({
            "required_capabilities": ["port_scan", "vuln_scan"],
            "expected_duration": 600,
            "budget": 1.0
        })
        
        assert isinstance(recommendations, list)
        print(f"✅ Got {len(recommendations)} tool recommendations")
        for i, rec in enumerate(recommendations[:3]):
            print(f"   {i+1}. {rec['tool']['name']} (score: {rec['score']})")
    
    @pytest.mark.asyncio
    async def test_parameter_optimization_flow(self, enterprise_components):
        """Test parameter optimization flow"""
        optimizer = enterprise_components['param_optimizer']
        
        result = await optimizer.optimize_parameters(
            tool_name="nmap",
            task_context={
                "target": "example.com",
                "objective": "speed"
            }
        )
        
        assert "recommended_parameters" in result
        assert "confidence" in result
        print(f"✅ Optimized parameters for nmap")
        print(f"   Parameters: {result.get('recommended_parameters', {})}")
        print(f"   Confidence: {result.get('confidence')}")
    
    @pytest.mark.asyncio
    async def test_adaptive_scanner_flow(self, enterprise_components):
        """Test adaptive scanner flow"""
        scanner = enterprise_components['adaptive_scanner']
        
        strategy = await scanner.select_strategy(
            target_type="web",
            goal="Vulnerability scan",
            context={"max_duration": 600}
        )
        
        assert strategy is not None
        print(f"✅ Selected strategy: {strategy.get('name')}")
        
        # Test learning
        await scanner.learn_from_result(
            strategy_name=strategy['name'],
            target_type="web",
            result={"status": "success", "findings": ["XSS"]}
        )
        print("✅ Scanner learned from result")
    
    @pytest.mark.asyncio
    async def test_tenant_management_flow(self, enterprise_components):
        """Test tenant management flow"""
        tenant_mgr = enterprise_components['tenant_manager']
        
        # Create tenant
        tenant = await tenant_mgr.create_tenant(
            name="Test Enterprise",
            plan="enterprise",
            settings={"max_concurrent": 10}
        )
        
        assert "tenant_id" in tenant
        print(f"✅ Created tenant: {tenant['name']} (ID: {tenant['tenant_id']})")
        
        # Get tenant
        fetched = await tenant_mgr.get_tenant(tenant['tenant_id'])
        assert fetched['name'] == "Test Enterprise"
        print("✅ Retrieved tenant successfully")

if __name__ == "__main__":
    # Manual test execution
    async def manual_test():
        print("="*60)
        print("🧪 MANUAL INTEGRATION TEST")
        print("="*60)
        
        test = TestEnterpriseWorkflow()
        components = await test.enterprise_components()
        
        print("\n1️⃣ Testing component initialization...")
        await test.test_component_initialization(components)
        
        print("\n2️⃣ Testing tool recommendation...")
        await test.test_tool_recommendation_flow(components)
        
        print("\n3️⃣ Testing parameter optimization...")
        await test.test_parameter_optimization_flow(components)
        
        print("\n4️⃣ Testing adaptive scanner...")
        await test.test_adaptive_scanner_flow(components)
        
        print("\n5️⃣ Testing tenant management...")
        await test.test_tenant_management_flow(components)
        
        print("\n" + "="*60)
        print("✅ ALL INTEGRATION TESTS PASSED!")
        print("="*60)
    
    asyncio.run(manual_test())