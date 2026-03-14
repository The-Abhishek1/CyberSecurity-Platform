#!/usr/bin/env python3
"""
Unit tests for Tool Recommender
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
from src.recommendation.tool_recommender import ToolRecommender
from src.ai.model_manager import ModelManager
from src.memory.memory_service import MemoryService
from src.memory.vector_store import VectorStore
from src.memory.graph_store import GraphStore
from src.memory.time_series_store import TimeSeriesStore

class TestToolRecommender:
    """Test suite for Tool Recommender"""
    
    def setup_method(self):
        """Setup before each test"""
        self.vector = VectorStore()
        self.graph = GraphStore()
        self.ts = TimeSeriesStore()
        self.memory = MemoryService(self.vector, self.graph, self.ts)
        self.model_manager = ModelManager()
        self.recommender = ToolRecommender(self.memory, self.model_manager)
    
    @pytest.mark.asyncio
    async def test_recommender_initialization(self):
        """Test recommender initialization"""
        assert self.recommender is not None
        assert hasattr(self.recommender, 'recommend_tools')
        assert hasattr(self.recommender, 'learn_from_execution')
        logger.info("✅ Tool Recommender initialized successfully")
    
    @pytest.mark.asyncio
    async def test_recommend_tools_port_scan(self):
        """Test tool recommendation for port scan"""
        recommendations = await self.recommender.recommend_tools(
            task_context={
                "required_capabilities": ["port_scan"],
                "expected_duration": 300,
                "budget": 0.5
            },
            top_k=3
        )
        
        assert isinstance(recommendations, list)
        if recommendations:
            assert "tool" in recommendations[0]
            assert "score" in recommendations[0]
        logger.info(f"✅ Got {len(recommendations)} recommendations for port scan")
    
    @pytest.mark.asyncio
    async def test_recommend_tools_vuln_scan(self):
        """Test tool recommendation for vulnerability scan"""
        recommendations = await self.recommender.recommend_tools(
            task_context={
                "required_capabilities": ["vulnerability_scan"],
                "expected_duration": 600,
                "budget": 1.0
            },
            top_k=3
        )
        
        assert isinstance(recommendations, list)
        logger.info(f"✅ Got {len(recommendations)} recommendations for vulnerability scan")
    
    @pytest.mark.asyncio
    async def test_learn_from_execution(self):
        """Test learning from execution"""
        await self.recommender.learn_from_execution(
            tool_name="nmap",
            context={"target": "example.com", "ports": "80"},
            result={
                "status": "success",
                "duration": 45,
                "findings": ["port 80 open"]
            }
        )
        
        assert "nmap" in self.recommender.tool_performance
        logger.info("✅ Learned from execution")

# Manual test function
async def manual_test():
    """Manual test function"""
    print("="*60)
    print("🧪 Testing Tool Recommender")
    print("="*60)
    
    test = TestToolRecommender()
    test.setup_method()
    
    print("\n1️⃣ Testing initialization...")
    await test.test_recommender_initialization()
    
    print("\n2️⃣ Testing port scan recommendations...")
    await test.test_recommend_tools_port_scan()
    
    print("\n3️⃣ Testing vuln scan recommendations...")
    await test.test_recommend_tools_vuln_scan()
    
    print("\n4️⃣ Testing learning...")
    await test.test_learn_from_execution()
    
    print("\n✅ All tool recommender tests passed!")

if __name__ == "__main__":
    asyncio.run(manual_test())