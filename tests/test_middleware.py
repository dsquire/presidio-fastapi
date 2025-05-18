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
    response = client.get("/api/v1/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-XSS-Protection"] == "1; mode=block"
    assert "Strict-Transport-Security" in response.headers
    assert "Content-Security-Policy" in response.headers


def test_rate_limiter(client: TestClient) -> None:
    """Verify that the rate limiter enforces request limits per IP.

    Args:
        client: FastAPI test client for making requests.
    """  # Make burst_limit + 1 requests
    for _ in range(BURST_LIMIT + 1):
        response = client.get("/api/v1/")

    # Next request should be rate limited
    response = client.get("/api/v1/")
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
    response_data = response.json()
    assert "retry_after" in response_data


def test_metrics_endpoint(client: TestClient) -> None:
    """Check that metrics are collected and exposed via the metrics endpoint.

    Args:
        client: FastAPI test client for making requests.
    """
    # Get initial metrics
    response = client.get("/api/v1/metrics")
    assert response.status_code == HTTPStatus.OK
    initial_data = response.json()
    # Get initial metrics data to verify existence
    _ = initial_data["requests_by_path"]

    # Make a series of test requests to generate metrics
    assert client.get("/api/v1/").status_code == HTTPStatus.OK
    assert client.get("/api/v1/health").status_code == HTTPStatus.OK
    assert (
        client.post("/api/v1/analyze", json={"text": "test"}).status_code
        == HTTPStatus.OK
    )
    time.sleep(RESPONSE_TIME_SLEEP)  # Wait for metrics to update

    # Get updated metrics and verify
    response = client.get("/api/v1/metrics")
    assert response.status_code == HTTPStatus.OK
    data = response.json()

    # Verify metrics structure
    assert "total_requests" in data
    assert "requests_by_path" in data
    assert "average_response_time" in data
    assert "requests_in_last_minute" in data
    assert "error_counts" in data
    assert "suspicious_requests" in data
    # Check that path counts have been incremented
    assert (
        "/api/v1/metrics" in data["requests_by_path"]
    ), "Metrics endpoint path should be tracked"
    assert (
        "/api/v1/" in data["requests_by_path"]
    ), "Root endpoint path should be tracked"
    assert (
        "/api/v1/health" in data["requests_by_path"]
    ), "Health endpoint path should be tracked"
    assert (
        "/api/v1/analyze" in data["requests_by_path"]
    ), "Analyze endpoint path should be tracked"

    # Check that path metrics are non-zero (middleware properly counting requests)
    assert data["requests_by_path"]["/api/v1/metrics"] >= 1, "Metrics endpoint count"
    assert data["requests_by_path"]["/api/v1/"] >= 1, "Root endpoint count"
    assert data["requests_by_path"]["/api/v1/health"] >= 1, "Health endpoint count"
    assert data["requests_by_path"]["/api/v1/analyze"] >= 1, "Analyze endpoint count"

    # General metrics assertions
    assert data["average_response_time"] > 0
    assert data["requests_in_last_minute"] >= 4
