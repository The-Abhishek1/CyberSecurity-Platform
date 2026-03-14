#!/usr/bin/env python3
"""
Unit tests for Usage Aggregator and Billing Calculator
"""
import pytest
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from src.utils.logging import logger
from src.autonomous.adaptive_scanner import AdaptiveScanner
from src.memory.memory_service import MemoryService
from src.memory.vector_store import VectorStore
from src.memory.graph_store import GraphStore
from src.memory.time_series_store import TimeSeriesStore
from src.tenant.billing.usage_aggregator import UsageAggregator
from src.tenant.billing.billing_calculator import BillingCalculator

class TestBilling:
    """Test suite for Billing components"""
    
    def setup_method(self):
        """Setup before each test"""
        self.usage_aggregator = UsageAggregator()
        self.billing_calculator = BillingCalculator(self.usage_aggregator)
    
    @pytest.mark.asyncio
    async def test_usage_aggregator_initialization(self):
        """Test usage aggregator initialization"""
        assert self.usage_aggregator is not None
        logger.info("✅ Usage Aggregator initialized successfully")
    
    @pytest.mark.asyncio
    async def test_track_usage(self):
        """Test tracking usage"""
        await self.usage_aggregator.track_usage(
            tenant_id="test-tenant",
            resource="executions",
            amount=5,
            metadata={"scan_type": "nmap"}
        )
        
        usage = await self.usage_aggregator.get_tenant_usage("test-tenant")
        assert "executions" in usage
        assert usage["executions"]["total"] == 5
        logger.info("✅ Usage tracked successfully")
    
    @pytest.mark.asyncio
    async def test_usage_summary(self):
        """Test usage summary"""
        # Track some usage
        for i in range(10):
            await self.usage_aggregator.track_usage(
                tenant_id="test-tenant",
                resource="executions",
                amount=1
            )
        
        summary = await self.usage_aggregator.get_usage_summary(
            tenant_id="test-tenant",
            period="daily"
        )
        
        assert "resources" in summary
        assert "executions" in summary["resources"]
        logger.info("✅ Usage summary generated successfully")
    
    @pytest.mark.asyncio
    async def test_billing_calculator_initialization(self):
        """Test billing calculator initialization"""
        assert self.billing_calculator is not None
        logger.info("✅ Billing Calculator initialized successfully")
    
    @pytest.mark.asyncio
    async def test_calculate_invoice(self):
        """Test invoice calculation"""
        # Track some usage
        for i in range(150):  # 150 executions
            await self.usage_aggregator.track_usage(
                tenant_id="test-tenant",
                resource="executions",
                amount=1
            )
        
        invoice = await self.billing_calculator.calculate_invoice(
            tenant_id="test-tenant",
            tier="basic"
        )
        
        assert "invoice_id" in invoice
        assert "charges" in invoice
        assert invoice["tenant_id"] == "test-tenant"
        logger.info(f"✅ Invoice calculated: total ${invoice['total']:.2f}")

# Manual test function
async def manual_test():
    """Manual test function"""
    print("="*60)
    print("🧪 Testing Billing Components")
    print("="*60)
    
    test = TestBilling()
    test.setup_method()
    
    print("\n1️⃣ Testing Usage Aggregator initialization...")
    await test.test_usage_aggregator_initialization()
    
    print("\n2️⃣ Testing track usage...")
    await test.test_track_usage()
    
    print("\n3️⃣ Testing usage summary...")
    await test.test_usage_summary()
    
    print("\n4️⃣ Testing Billing Calculator initialization...")
    await test.test_billing_calculator_initialization()
    
    print("\n5️⃣ Testing calculate invoice...")
    await test.test_calculate_invoice()
    
    print("\n✅ All billing tests passed!")

if __name__ == "__main__":
    asyncio.run(manual_test())