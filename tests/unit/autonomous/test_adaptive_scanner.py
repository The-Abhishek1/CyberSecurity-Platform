#!/usr/bin/env python3
"""
Unit tests for Adaptive Scanner
"""
import pytest
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


# Import logger
from src.utils.logging import logger

from src.autonomous.adaptive_scanner import AdaptiveScanner
from src.memory.memory_service import MemoryService
from src.memory.vector_store import VectorStore
from src.memory.graph_store import GraphStore
from src.memory.time_series_store import TimeSeriesStore

class TestAdaptiveScanner:
    """Test suite for Adaptive Scanner"""
    
    def setup_method(self):
        """Setup before each test"""
        self.vector = VectorStore()
        self.graph = GraphStore()
        self.ts = TimeSeriesStore()
        self.memory = MemoryService(self.vector, self.graph, self.ts)
        self.scanner = AdaptiveScanner(self.memory)
    
    @pytest.mark.asyncio
    async def test_scanner_initialization(self):
        """Test that scanner initializes correctly"""
        assert self.scanner is not None
        assert hasattr(self.scanner, 'select_strategy')
        assert hasattr(self.scanner, 'learn_from_result')
        logger.info("✅ Scanner initialized successfully")
    
    @pytest.mark.asyncio
    async def test_strategy_selection_web(self):
        """Test strategy selection for web target"""
        strategy = await self.scanner.select_strategy(
            target_type="web",
            goal="Scan for vulnerabilities",
            context={"max_duration": 600}
        )
        
        assert strategy is not None
        assert "name" in strategy
        assert "tools" in strategy
        assert len(strategy["tools"]) > 0
        logger.info(f"✅ Selected web strategy: {strategy.get('name', 'unknown')}")
    
    @pytest.mark.asyncio
    async def test_strategy_selection_network(self):
        """Test strategy selection for network target"""
        strategy = await self.scanner.select_strategy(
            target_type="network",
            goal="Discover open ports",
            context={"max_duration": 300}
        )
        
        assert strategy is not None
        assert "name" in strategy
        assert "tools" in strategy
        logger.info(f"✅ Selected network strategy: {strategy.get('name', 'unknown')}")
    
    @pytest.mark.asyncio
    async def test_learning_from_results(self):
        """Test scanner learns from results"""
        # Learn from success
        await self.scanner.learn_from_result(
            strategy_name="quick_web_scan",
            target_type="web",
            result={
                "status": "success",
                "findings": ["XSS", "SQLi"],
                "duration": 120
            }
        )
        
        # Learn from failure
        await self.scanner.learn_from_result(
            strategy_name="deep_network_scan",
            target_type="network",
            result={
                "status": "failed",
                "error": "Timeout",
                "duration": 300
            }
        )
        
        assert "quick_web_scan" in self.scanner.strategy_weights
        assert "deep_network_scan" in self.scanner.strategy_weights
        assert self.scanner.strategy_weights["quick_web_scan"]["success_count"] == 1
        logger.info("✅ Scanner learned from results")

# Manual test function
async def manual_test():
    """Manual test function"""
    print("="*60)
    print("🧪 Testing Adaptive Scanner")
    print("="*60)
    
    test = TestAdaptiveScanner()
    test.setup_method()
    
    print("\n1️⃣ Testing initialization...")
    await test.test_scanner_initialization()
    
    print("\n2️⃣ Testing web strategy...")
    await test.test_strategy_selection_web()
    
    print("\n3️⃣ Testing network strategy...")
    await test.test_strategy_selection_network()
    
    print("\n4️⃣ Testing learning...")
    await test.test_learning_from_results()
    
    print("\n✅ All adaptive scanner tests passed!")

if __name__ == "__main__":
    asyncio.run(manual_test())