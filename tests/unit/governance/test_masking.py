#!/usr/bin/env python3
"""
Unit tests for Data Masking
"""
import pytest
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from src.utils.logging import logger
from src.autonomous.adaptive_scanner import AdaptiveScanner
from src.memory.memory_service import MemoryService
from src.memory.vector_store import VectorStore
from src.memory.graph_store import GraphStore
from src.memory.time_series_store import TimeSeriesStore
from src.governance.masking import DataMaskingManager

class TestDataMasking:
    """Test suite for Data Masking"""
    
    def setup_method(self):
        """Setup before each test"""
        self.masker = DataMaskingManager()
    
    @pytest.mark.asyncio
    async def test_masking_initialization(self):
        """Test masking manager initialization"""
        assert self.masker is not None
        
        # Check for any of the possible method names
        has_method = (
            hasattr(self.masker, 'add_rule') or 
            hasattr(self.masker, 'add_masking_rule') or
            hasattr(self.masker, 'add_pattern')
        )
        
        has_mask = (
            hasattr(self.masker, 'mask_sensitive_data') or
            hasattr(self.masker, 'mask_data') or
            hasattr(self.masker, 'apply_masking')
        )
        
        assert has_method
        assert has_mask
        logger.info("✅ Data Masking initialized successfully")
    
    @pytest.mark.asyncio
    async def test_add_masking_rule(self):
        """Test adding masking rules"""
        await self.masker.add_rule(
            pattern=r"\b\d{3}-\d{2}-\d{4}\b",  # SSN pattern
            mask="XXX-XX-XXXX",
            name="ssn_mask"
        )
        
        assert "ssn_mask" in self.masker.rules
        logger.info("✅ Masking rule added successfully")
    
    @pytest.mark.asyncio
    async def test_mask_ssn(self):
        """Test masking SSN numbers"""
        await self.masker.add_rule(
            pattern=r"\b\d{3}-\d{2}-\d{4}\b",
            mask="XXX-XX-XXXX",
            name="ssn_mask"
        )
        
        text = "User SSN is 123-45-6789 and email is test@example.com"
        masked = await self.masker.mask_sensitive_data(text)
        
        assert "123-45-6789" not in masked
        assert "XXX-XX-XXXX" in masked
        assert "test@example.com" in masked  # Email should remain
        logger.info(f"✅ Masked text: {masked}")
    
    @pytest.mark.asyncio
    async def test_mask_credit_card(self):
        """Test masking credit card numbers"""
        await self.masker.add_rule(
            pattern=r"\b\d{4}-\d{4}-\d{4}-\d{4}\b",
            mask="XXXX-XXXX-XXXX-XXXX",
            name="cc_mask"
        )
        
        text = "Credit card: 4111-1111-1111-1111"
        masked = await self.masker.mask_sensitive_data(text)
        
        assert "4111-1111-1111-1111" not in masked
        assert "XXXX-XXXX-XXXX-XXXX" in masked
        logger.info(f"✅ Masked credit card: {masked}")
    
    @pytest.mark.asyncio
    async def test_multiple_rules(self):
        """Test multiple masking rules together"""
        # Add SSN rule
        await self.masker.add_rule(
            pattern=r"\b\d{3}-\d{2}-\d{4}\b",
            mask="XXX-XX-XXXX",
            name="ssn"
        )
        
        # Add credit card rule
        await self.masker.add_rule(
            pattern=r"\b\d{4}-\d{4}-\d{4}-\d{4}\b",
            mask="XXXX-XXXX-XXXX-XXXX",
            name="cc"
        )
        
        text = "SSN: 123-45-6789, CC: 4111-1111-1111-1111"
        masked = await self.masker.mask_sensitive_data(text)
        
        assert "123-45-6789" not in masked
        assert "4111-1111-1111-1111" not in masked
        assert "XXX-XX-XXXX" in masked
        assert "XXXX-XXXX-XXXX-XXXX" in masked
        logger.info(f"✅ Multiple rules applied: {masked}")

# Manual test function
async def manual_test():
    """Manual test function"""
    print("="*60)
    print("🧪 Testing Data Masking")
    print("="*60)
    
    test = TestDataMasking()
    test.setup_method()
    
    print("\n1️⃣ Testing initialization...")
    await test.test_masking_initialization()
    
    print("\n2️⃣ Testing add rule...")
    await test.test_add_masking_rule()
    
    print("\n3️⃣ Testing SSN masking...")
    await test.test_mask_ssn()
    
    print("\n4️⃣ Testing credit card masking...")
    await test.test_mask_credit_card()
    
    print("\n5️⃣ Testing multiple rules...")
    await test.test_multiple_rules()
    
    print("\n✅ All data masking tests passed!")

if __name__ == "__main__":
    asyncio.run(manual_test())