"""Test middleware functionality."""

import time
from http import HTTPStatus

from fastapi.testclient import TestClient

RESPONSE_TIME_SLEEP = 0.1  # seconds


def test_security_headers(client: TestClient) -> None:
    """Ensure security headers are correctly added to all responses.

    Args:
        client: FastAPI test client for making requests.
    """
    response = client.get("/api/v1/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-XSS-Protection"] == "1; mode=block"
    assert (
        response.headers["Strict-Transport-Security"]
        == "max-age=31536000; includeSubDomains"
    )
    assert "Content-Security-Policy" in response.headers
    assert "script-src" in response.headers["Content-Security-Policy"]
    assert "Referrer-Policy" in response.headers
    assert "Permissions-Policy" in response.headers


def test_rate_limiter(client: TestClient) -> None:
    """Test rate limiting middleware functionality.

    Args:
        client: FastAPI test client for making requests.
    """
    # Send multiple requests to test rate limiting
    responses = []
    # Use a smaller number to avoid hitting the rate limit
    for _ in range(10):
        responses.append(client.get("/api/v1/health"))

    # All responses should be successful
    for response in responses:
        assert response.status_code == HTTPStatus.OK

    # Check rate limit headers
    assert "X-RateLimit-Limit" in responses[-1].headers
    assert "X-RateLimit-Remaining" in responses[-1].headers
    assert "X-RateLimit-Reset" in responses[-1].headers


def test_prometheus_metrics(client: TestClient) -> None:
    """Test Prometheus metrics endpoint functionality.

    Args:
        client: FastAPI test client for making requests.
    """
    # Make requests to several endpoints to generate metrics
    client.get("/api/v1/")
    client.get("/api/v1/health")
    # Use post method for the analyze endpoint
    client.post("/api/v1/analyze", json={"text": "My name is John Doe", "language": "en"})
    
    # Add a small delay to ensure metrics are updated
    time.sleep(RESPONSE_TIME_SLEEP)
    
    # Get the metrics in Prometheus format
    prometheus_response = client.get("/api/v1/metrics")
    assert prometheus_response.status_code == HTTPStatus.OK
    
    # Verify Prometheus format content
    content = prometheus_response.text
    assert "http_requests_total" in content
    assert "http_request_duration_seconds" in content
    assert "presidio_pii_entities_detected_total" in content
