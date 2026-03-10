# tests/security/test_auth.py

import pytest
from fastapi.testclient import TestClient
from src.api.app import app
import jwt
import time

client = TestClient(app)

@pytest.mark.security
def test_jwt_authentication():
    """Test JWT authentication"""
    
    # Test without token
    response = client.get("/api/v1/execute")
    assert response.status_code == 401
    
    # Test with invalid token
    headers = {"Authorization": "Bearer invalid_token"}
    response = client.get("/api/v1/execute", headers=headers)
    assert response.status_code == 401

@pytest.mark.security
def test_api_key_authentication():
    """Test API key authentication"""
    
    # Test with invalid API key
    headers = {"X-API-Key": "invalid_key"}
    response = client.get("/api/v1/execute", headers=headers)
    assert response.status_code == 401

@pytest.mark.security
def test_rate_limiting():
    """Test rate limiting"""
    
    # Make many requests quickly
    for i in range(10):
        response = client.get("/health")
        assert response.status_code == 200
    
    # Should hit rate limit
    response = client.get("/health")
    assert response.status_code == 429  # Too Many Requests

@pytest.mark.security
def test_sql_injection_prevention():
    """Test SQL injection prevention"""
    
    # Attempt SQL injection in parameters
    malicious_input = "'; DROP TABLE users; --"
    response = client.get(f"/api/v1/status/{malicious_input}")
    assert response.status_code == 422  # Validation error, not 500

@pytest.mark.security
def test_xss_prevention():
    """Test XSS prevention"""
    
    # Attempt XSS in input
    xss_payload = "<script>alert('XSS')</script>"
    response = client.post(
        "/api/v1/execute",
        json={
            "goal": xss_payload,
            "target": "example.com"
        }
    )
    
    # Check that response doesn't contain unescaped script
    assert "<script>" not in response.text