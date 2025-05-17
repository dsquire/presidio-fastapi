"""Test middleware functionality."""

import time
from http import HTTPStatus

from fastapi.testclient import TestClient

# Constants for rate limiting tests
from .conftest import BURST_LIMIT

RESPONSE_TIME_SLEEP = 0.1  # seconds


def test_security_headers(client: TestClient) -> None:
    """Ensure security headers are correctly added to all responses.

    Args:
        client: FastAPI test client for making requests.
    """
    response = client.get("/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-XSS-Protection"] == "1; mode=block"
    assert "Strict-Transport-Security" in response.headers
    assert "Content-Security-Policy" in response.headers


def test_rate_limiter(client: TestClient) -> None:
    """Verify that the rate limiter enforces request limits per IP.

    Args:
        client: FastAPI test client for making requests.
    """
    # Make burst_limit + 1 requests
    for _ in range(BURST_LIMIT + 1):
        response = client.get("/")

    # Next request should be rate limited
    response = client.get("/")
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
    response_data = response.json()
    assert "retry_after" in response_data


def test_metrics_endpoint(client: TestClient) -> None:
    """Check that metrics are collected and exposed via the metrics endpoint.

    Args:
        client: FastAPI test client for making requests.
    """
    # Make some requests
    client.get("/")
    client.get("/health")
    time.sleep(RESPONSE_TIME_SLEEP)  # Ensure we get some measurable response time

    # Check metrics
    response = client.get("/metrics")
    assert response.status_code == HTTPStatus.OK
    data = response.json()

    assert "total_requests" in data
    assert "requests_by_path" in data
    assert "average_response_time" in data
    assert "requests_in_last_minute" in data

    assert data["total_requests"] >= 3  # Including the metrics request itself
    assert "/" in data["requests_by_path"]
    assert "/health" in data["requests_by_path"]
    assert data["average_response_time"] > 0
