# tests/integration/test_api_integration.py

import pytest
import httpx
import asyncio
from fastapi.testclient import TestClient
from src.api.app import app

client = TestClient(app)

@pytest.mark.integration
def test_full_execution_flow():
    """Test complete execution flow through API"""
    
    # Step 1: Submit execution request
    response = client.post(
        "/api/v1/execute",
        json={
            "goal": "Scan example.com for vulnerabilities",
            "target": "example.com",
            "priority": "high",
            "mode": "sync"
        }
    )
    
    assert response.status_code == 202
    data = response.json()
    assert "process_id" in data
    process_id = data["process_id"]
    
    # Step 2: Check status
    status_response = client.get(f"/api/v1/status/{process_id}")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert "status" in status_data
    
    # Step 3: Wait for completion (in real test, would poll)
    # For now, just verify endpoint exists
    list_response = client.get("/api/v1/list")
    assert list_response.status_code == 200
    assert "executions" in list_response.json()

@pytest.mark.integration
@pytest.mark.asyncio
async def test_async_execution():
    """Test async execution with webhook"""
    
    async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/execute",
            json={
                "goal": "Async test scan",
                "mode": "async",
                "webhook_url": "http://localhost:9999/webhook"
            }
        )
        
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "pending"

@pytest.mark.integration
def test_batch_execution():
    """Test batch execution"""
    
    batch_request = {
        "executions": [
            {
                "goal": "Scan example.com",
                "target": "example.com"
            },
            {
                "goal": "Scan test.com",
                "target": "test.com"
            }
        ],
        "parallel": True
    }
    
    response = client.post("/api/v1/batch", json=batch_request)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all("process_id" in item for item in data)

@pytest.mark.integration
def test_health_endpoints():
    """Test health check endpoints"""
    
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    
    response = client.get("/metrics")
    assert response.status_code == 200