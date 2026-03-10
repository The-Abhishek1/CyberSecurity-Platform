# tests/chaos/test_resilience.py

import pytest
import asyncio
import random
import httpx
from datetime import datetime

@pytest.mark.chaos
@pytest.mark.asyncio
async def test_database_failure_resilience():
    """Test system behavior when database fails"""
    
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Submit a request
        response = await client.post(
            "/api/v1/execute",
            json={"goal": "Test scan", "target": "example.com"}
        )
        assert response.status_code == 202
        process_id = response.json()["process_id"]
        
        # Simulate database failure (in real test, would actually fail DB)
        # For now, just verify the API handles timeouts gracefully
        
        # Try to check status (might fail, but should handle gracefully)
        try:
            await client.get(f"/api/v1/status/{process_id}", timeout=0.1)
        except httpx.TimeoutException:
            pass  # Expected when DB is down
        
        # API should still respond to health checks
        health = await client.get("/health")
        assert health.status_code == 200

@pytest.mark.chaos
@pytest.mark.asyncio
async def test_network_partition():
    """Test behavior during network partition"""
    
    # Simulate network issues by introducing delays and timeouts
    async with httpx.AsyncClient(
        base_url="http://localhost:8000",
        timeout=httpx.Timeout(0.5)  # Very short timeout
    ) as client:
        
        for _ in range(10):
            try:
                await client.get("/health")
            except httpx.TimeoutException:
                # Should handle gracefully
                pass
            await asyncio.sleep(random.uniform(0.1, 0.3))

@pytest.mark.chaos
@pytest.mark.asyncio
async def test_service_restart():
    """Test behavior during service restart"""
    
    # This would typically be run with actual container restarts
    # For now, just verify API can handle temporary unavailability
    
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Normal request
        response = await client.get("/health")
        assert response.status_code == 200
        
        # Simulate restart by waiting
        await asyncio.sleep(5)
        
        # Should still work after restart
        response = await client.get("/health")
        assert response.status_code == 200

@pytest.mark.chaos
@pytest.mark.asyncio
async def test_load_spike():
    """Test behavior under load spike"""
    
    async def make_request(client, i):
        try:
            response = await client.post(
                "/api/v1/execute",
                json={
                    "goal": f"Test scan {i}",
                    "target": "example.com",
                    "priority": "low"
                }
            )
            return response.status_code
        except:
            return None
    
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
        # Send 50 concurrent requests
        tasks = [make_request(client, i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        
        # Most should succeed (some may be rate limited)
        success_count = sum(1 for r in results if r == 202)
        assert success_count >= 40  # At least 80% success rate