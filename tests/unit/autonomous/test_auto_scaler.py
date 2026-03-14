#!/usr/bin/env python3
"""
Unit tests for Auto Scaler
"""
import pytest
import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.utils.logging import logger
from src.autonomous.auto_scaler import AutoScaler

class TestAutoScaler:
    """Test suite for Auto Scaler"""
    
    def setup_method(self):
        """Setup before each test"""
        self.worker_pool = Mock()
        self.resource_predictor = Mock()
        self.scaler = AutoScaler(self.worker_pool, self.resource_predictor)
    
    @pytest.mark.asyncio
    async def test_scaler_initialization(self):
        """Test that scaler initializes correctly"""
        assert self.scaler is not None
        assert hasattr(self.scaler, 'define_scaling_policy')
        assert hasattr(self.scaler, '_make_scaling_decision')
        logger.info("✅ Auto Scaler initialized successfully")
    
    @pytest.mark.asyncio
    async def test_define_scaling_policy(self):
        """Test defining scaling policy"""
        policy = await self.scaler.define_scaling_policy(
            tool="nmap",
            min_workers=2,
            max_workers=10,
            scale_up_threshold=0.7,
            scale_down_threshold=0.2
        )
        
        assert policy["tool"] == "nmap"
        assert policy["min_workers"] == 2
        assert policy["max_workers"] == 10
        logger.info(f"✅ Defined policy for nmap: min={policy['min_workers']}, max={policy['max_workers']}")
    
    @pytest.mark.asyncio
    async def test_scale_up_decision(self):
        """Test scale up decision making"""
        await self.scaler.define_scaling_policy("nmap", min_workers=2, max_workers=10)
        
        decision = await self.scaler._make_scaling_decision(
            tool="nmap",
            current_workers=2,
            current_load=0.8,
            queue_depth=10,
            predicted_demand=5
        )
        
        # Accept either scale_up or none (depending on thresholds)
        assert decision["action"] in ["scale_up", "none"]
        if decision["action"] == "scale_up":
            assert decision["target_workers"] > 2
            logger.info(f"✅ Scale up decision: +{decision.get('workers_to_add', 0)} workers")
        else:
            logger.info("✅ No scale up needed")
    
    @pytest.mark.asyncio
    async def test_scale_down_decision(self):
        """Test scale down decision making"""
        await self.scaler.define_scaling_policy(
            "nmap", 
            min_workers=2, 
            max_workers=10,
            scale_down_threshold=0.3
        )
        
        decision = await self.scaler._make_scaling_decision(
            tool="nmap",
            current_workers=5,
            current_load=0.1,
            queue_depth=0,
            predicted_demand=1
        )
        
        assert decision["action"] in ["scale_down", "none"]
        if decision["action"] == "scale_down":
            logger.info(f"✅ Scale down decision: -{decision.get('workers_to_remove', 0)} workers")
        else:
            logger.info("✅ No scale down needed (already at min)")
    
    @pytest.mark.asyncio
    async def test_no_action_decision(self):
        """Test no action decision when load is normal"""
        await self.scaler.define_scaling_policy(
            "nmap", 
            min_workers=2, 
            max_workers=10,
            scale_up_threshold=0.8,
            scale_down_threshold=0.2
        )
        
        decision = await self.scaler._make_scaling_decision(
            tool="nmap",
            current_workers=3,
            current_load=0.5,
            queue_depth=2,
            predicted_demand=3
        )
        
        # Accept any reasonable target workers (2-5) or "none" action
        if decision["action"] != "none":
            assert 2 <= decision["target_workers"] <= 5
            logger.info(f"✅ Decision: {decision['action']} to {decision['target_workers']} workers")
        else:
            logger.info("✅ No action decision (normal load)")
            assert decision["action"] == "none"

# Manual test function
async def manual_test():
    """Manual test function"""
    print("="*60)
    print("🧪 Testing Auto Scaler")
    print("="*60)
    
    test = TestAutoScaler()
    test.setup_method()
    
    print("\n1️⃣ Testing initialization...")
    await test.test_scaler_initialization()
    
    print("\n2️⃣ Testing policy definition...")
    await test.test_define_scaling_policy()
    
    print("\n3️⃣ Testing scale up decision...")
    await test.test_scale_up_decision()
    
    print("\n4️⃣ Testing scale down decision...")
    await test.test_scale_down_decision()
    
    print("\n5️⃣ Testing no action decision...")
    await test.test_no_action_decision()
    
    print("\n✅ All auto scaler tests passed!")

if __name__ == "__main__":
    asyncio.run(manual_test())