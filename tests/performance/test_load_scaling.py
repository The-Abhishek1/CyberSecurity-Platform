#!/usr/bin/env python3
"""
Performance and load tests
"""
import pytest
import asyncio
import time
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.logging import logger
from src.autonomous.adaptive_scanner import AdaptiveScanner
from src.memory.memory_service import MemoryService
from src.memory.vector_store import VectorStore
from src.memory.graph_store import GraphStore
from src.memory.time_series_store import TimeSeriesStore

from src.workers.worker_pool import WorkerPool
from src.workers.container import ContainerManager
from src.workers.network_manager import NetworkManager
from src.workers.resource_monitor import ResourceMonitor
from src.tools.tool_registry import ToolRegistry
from src.tools.tool_router import ToolRouter

class TestPerformance:
    """Performance test suite"""
    
    @pytest.fixture
    async def performance_components(self):
        """Initialize components for performance testing"""
        container = ContainerManager()
        network = NetworkManager()
        resource = ResourceMonitor()
        worker_pool = WorkerPool(container, resource, network)
        
        registry = ToolRegistry()
        worker_pool.tool_registry = registry
        
        router = ToolRouter(registry, worker_pool)
        
        return {
            'worker_pool': worker_pool,
            'registry': registry,
            'router': router
        }
    
    @pytest.mark.asyncio
    async def test_concurrent_executions(self, performance_components):
        """Test concurrent execution performance"""
        worker_pool = performance_components['worker_pool']
        
        # Initialize pools
        await worker_pool.initialize_pool("nmap", {"name": "nmap"})
        
        async def execute_scan(scan_id):
            start = time.time()
            result = await worker_pool._execute_direct_docker({
                "tool_name": "nmap",
                "args": ["-p", "80", "scanme.nmap.org"],
                "timeout": 30
            })
            duration = time.time() - start
            return {
                "id": scan_id,
                "success": result.get("success", False),
                "duration": duration
            }
        
        # Run 5 concurrent scans
        print("\n📊 Running 5 concurrent scans...")
        tasks = [execute_scan(i) for i in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successes = sum(1 for r in results if isinstance(r, dict) and r["success"])
        durations = [r["duration"] for r in results if isinstance(r, dict)]
        
        print(f"   Success rate: {successes}/5")
        if durations:
            print(f"   Avg duration: {sum(durations)/len(durations):.2f}s")
            print(f"   Min duration: {min(durations):.2f}s")
            print(f"   Max duration: {max(durations):.2f}s")
        
        assert successes >= 3  # At least 60% success
    
    @pytest.mark.asyncio
    async def test_response_time(self, performance_components):
        """Test API response time"""
        router = performance_components['router']
        
        from src.models.dag import TaskNode, TaskType, AgentCapability
        
        task = TaskNode(
            name="Performance Test",
            description="Test response time",
            task_type=TaskType.SCAN,
            required_capabilities=[AgentCapability.PORT_SCAN],
            parameters={"target": "scanme.nmap.org", "ports": "80"}
        )
        
        # Measure response time
        start = time.time()
        
        result = await router.route_and_execute(
            task=task,
            params=task.parameters,
            user_id="perf_test",
            tenant_id="perf_tenant",
            execution_id="perf_exec"
        )
        
        duration = time.time() - start
        
        print(f"\n📊 Response time: {duration:.2f}s")
        assert duration < 30  # Should complete within 30 seconds
    
    @pytest.mark.asyncio
    async def test_memory_usage(self, performance_components):
        """Test memory usage during operations"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform some operations
        worker_pool = performance_components['worker_pool']
        for i in range(10):
            await worker_pool.get_pool_stats("nmap")
        
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory
        
        print(f"\n📊 Memory usage:")
        print(f"   Initial: {initial_memory:.2f} MB")
        print(f"   Final: {final_memory:.2f} MB")
        print(f"   Increase: {memory_increase:.2f} MB")
        
        assert memory_increase < 100  # Should not increase by more than 100MB

if __name__ == "__main__":
    # Manual performance test
    async def manual_test():
        print("="*60)
        print("⚡ PERFORMANCE TEST SUITE")
        print("="*60)
        
        test = TestPerformance()
        components = await test.performance_components()
        
        print("\n1️⃣ Testing concurrent executions...")
        await test.test_concurrent_executions(components)
        
        print("\n2️⃣ Testing response time...")
        await test.test_response_time(components)
        
        print("\n3️⃣ Testing memory usage...")
        await test.test_memory_usage(components)
        
        print("\n" + "="*60)
        print("✅ ALL PERFORMANCE TESTS PASSED!")
        print("="*60)
    
    asyncio.run(manual_test())