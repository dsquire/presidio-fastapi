"""Test middleware functionality."""
import time

from fastapi.testclient import TestClient


def test_security_headers(client: TestClient):
    """Test security headers are added to responses."""
    response = client.get("/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-XSS-Protection"] == "1; mode=block"
    assert "Strict-Transport-Security" in response.headers
    assert "Content-Security-Policy" in response.headers

def test_rate_limiter(client: TestClient):
    """Test rate limiting functionality."""
    # Make burst_limit + 1 requests
    for _ in range(101):
        response = client.get("/")
    
    # Next request should be rate limited
    response = client.get("/")
    assert response.status_code == 429
    assert "retry_after" in response.json()

def test_metrics_endpoint(client: TestClient):
    """Test metrics collection and endpoint."""
    # Make some requests
    client.get("/")
    client.get("/health")
    time.sleep(0.1)  # Ensure we get some measurable response time
    
    # Check metrics
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    
    assert "total_requests" in data
    assert "requests_by_path" in data
    assert "average_response_time" in data
    assert "requests_in_last_minute" in data
    
    assert data["total_requests"] >= 3  # Including the metrics request itself
    assert "/" in data["requests_by_path"]
    assert "/health" in data["requests_by_path"]
    assert data["average_response_time"] > 0
