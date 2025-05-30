"""Test middleware functionality."""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from unittest.mock import Mock

import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient

from presidio_fastapi.app.middleware import (
    MetricsMiddleware,
    RateLimiterMiddleware,
)

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
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
    assert "Content-Security-Policy" in response.headers
    assert "script-src" in response.headers["Content-Security-Policy"]
    assert "Referrer-Policy" in response.headers
    assert "Permissions-Policy" in response.headers


def test_security_headers_multiple_endpoints(client: TestClient) -> None:
    """Test that security headers are added to all endpoint responses.

    Args:
        client: FastAPI test client for making requests.
    """
    endpoints = ["/api/v1/", "/api/v1/health", "/api/v1/metrics"]

    for endpoint in endpoints:
        response = client.get(endpoint)
        # Should have security headers regardless of status code
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "Strict-Transport-Security" in response.headers


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


def test_rate_limiter_burst_limit_violation() -> None:
    """Test rate limiter when burst limit is exceeded."""
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    # Create rate limiter with very low limits for testing
    app.add_middleware(
        RateLimiterMiddleware,
        requests_per_minute=5,
        burst_limit=3,  # Very low burst limit
        block_duration=60,
    )

    with TestClient(app) as test_client:
        # Make requests that exceed burst limit
        responses = []
        for i in range(5):
            response = test_client.get("/test")
            responses.append(response)
            if i < 3:
                assert response.status_code == HTTPStatus.OK

        # At least one should be rate limited
        status_codes = [r.status_code for r in responses]
        assert HTTPStatus.TOO_MANY_REQUESTS in status_codes


def test_rate_limiter_ip_blocking() -> None:
    """Test rate limiter IP blocking functionality."""
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    # Add rate limiter with very restrictive limits
    app.add_middleware(
        RateLimiterMiddleware,
        requests_per_minute=2,
        burst_limit=2,
        block_duration=10,
    )

    with TestClient(app) as test_client:
        # Make requests to trigger rate limiting
        responses = []
        for _ in range(4):
            response = test_client.get("/test")
            responses.append(response)

        # Should have some rate-limited responses
        status_codes = [r.status_code for r in responses]
        rate_limited_count = status_codes.count(HTTPStatus.TOO_MANY_REQUESTS)
        assert rate_limited_count > 0


def test_rate_limiter_blocked_ip_cleanup() -> None:
    """Test that blocked IPs are cleaned up after block duration."""
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    rate_limiter_middleware = RateLimiterMiddleware(
        app=app,
        requests_per_minute=1,
        burst_limit=1,
        block_duration=1,  # Very short block duration for testing
    )

    # Simulate blocked IP cleanup by manipulating the middleware directly
    # Add a blocked IP that should be expired
    past_time = datetime.now(timezone.utc) - timedelta(seconds=2)
    rate_limiter_middleware.blocked_ips["test_ip"] = past_time

    # Create a mock request
    mock_request = Mock()
    mock_request.client = Mock()
    mock_request.client.host = "test_ip"    # Create a mock call_next function
    async def mock_call_next(request: Request) -> Response:
        mock_response = Mock()
        mock_response.headers = {}
        return mock_response

    # Test that expired blocked IP is cleaned up
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(rate_limiter_middleware.dispatch(mock_request, mock_call_next))
        # The blocked IP should be removed from the dict
        assert "test_ip" not in rate_limiter_middleware.blocked_ips
    finally:
        loop.close()


def test_metrics_middleware_initialization() -> None:
    """Test MetricsMiddleware initialization."""
    app = FastAPI()

    # Test initialization without existing metrics
    middleware1 = MetricsMiddleware(app)
    assert middleware1.requests_count == 0
    assert len(middleware1.requests_by_path) == 0
    assert len(middleware1.response_times) == 0

    # Test initialization with existing metrics
    middleware1.requests_count = 5
    middleware1.requests_by_path["/test"] = 3
    middleware1.response_times = [0.1, 0.2]

    middleware2 = MetricsMiddleware(app, metrics=middleware1)
    assert middleware2.requests_count == 5
    assert middleware2.requests_by_path["/test"] == 3
    assert len(middleware2.response_times) == 2


def test_metrics_middleware_suspicious_request_detection() -> None:
    """Test that MetricsMiddleware detects suspicious requests."""
    app = FastAPI()
    middleware = MetricsMiddleware(app)

    # Create mock requests with suspicious patterns
    suspicious_patterns = [
        "/api/../../etc/passwd",  # Path traversal
        "/api/test?query=SELECT * FROM users",  # SQL injection
        "/api/test?data=<script>alert('xss')</script>",  # XSS
        "/api/../etc/passwd/test",  # Another path traversal
    ]

    for pattern in suspicious_patterns:
        mock_request = Mock()
        mock_request.url = Mock()
        mock_request.url.path = pattern
        mock_request.query_params = ""

        is_suspicious = middleware._is_suspicious_request(mock_request)
        assert is_suspicious, f"Pattern should be detected as suspicious: {pattern}"


def test_metrics_middleware_normal_request_processing() -> None:
    """Test normal request processing in MetricsMiddleware."""
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    @app.get("/metrics")
    async def metrics_endpoint():
        return {"metrics": "data"}

    app.add_middleware(MetricsMiddleware)

    with TestClient(app) as test_client:
        # Make several requests
        for _ in range(3):
            response = test_client.get("/test")
            assert response.status_code == HTTPStatus.OK

        # Get metrics - use the correct endpoint
        metrics_response = test_client.get("/metrics")
        assert metrics_response.status_code == HTTPStatus.OK


def test_metrics_middleware_error_handling() -> None:
    """Test MetricsMiddleware error handling and metrics collection."""
    app = FastAPI()

    @app.get("/test-error")
    async def error_endpoint():
        raise Exception("Test error")

    @app.get("/test-success")
    async def success_endpoint():
        return {"message": "success"}

    app.add_middleware(MetricsMiddleware)

    with TestClient(app) as test_client:
        # Make a successful request
        success_response = test_client.get("/test-success")
        assert success_response.status_code == HTTPStatus.OK

        # Make a request that causes an error (this should raise an exception)
        try:
            test_client.get("/test-error")
        except Exception:
            pass  # Expected to raise an exception


def test_metrics_middleware_calculations() -> None:
    """Test MetricsMiddleware metric calculation methods."""
    app = FastAPI()
    middleware = MetricsMiddleware(app)

    # Test average response time calculation
    middleware.response_times = [0.1, 0.2, 0.3]
    avg_time = middleware._calculate_average_response_time()
    assert abs(avg_time - 0.2) < 0.001  # Use tolerance for floating point comparison

    # Test with empty response times
    middleware.response_times = []
    avg_time = middleware._calculate_average_response_time()
    assert avg_time == 0.001

    # Test error rate calculation
    middleware.requests_count = 10
    middleware.error_counts[400] = 1
    middleware.error_counts[500] = 2
    error_rate = middleware._calculate_error_rate()
    assert error_rate == 0.3  # (1 + 2) / 10

    # Test with no requests
    middleware.requests_count = 0
    error_rate = middleware._calculate_error_rate()
    assert error_rate == 0.0


def test_metrics_middleware_get_metrics() -> None:
    """Test MetricsMiddleware get_metrics method."""
    app = FastAPI()
    middleware = MetricsMiddleware(app)

    # Set up some test data
    middleware.requests_by_path["/api/test"] = 5
    middleware.requests_by_path["/api/other"] = 3
    middleware.response_times = [0.1, 0.2, 0.3]
    middleware.error_counts[400] = 1
    middleware.error_counts[500] = 1
    middleware.suspicious_requests["192.168.1.1"] = 2
    # Set requests_count to match total path requests for consistency
    middleware.requests_count = 8

    metrics = middleware.get_metrics()

    assert metrics["total_requests"] == 8  # 5 + 3
    assert metrics["requests_by_path"]["/api/test"] == 5
    assert metrics["requests_by_path"]["/api/other"] == 3
    assert abs(metrics["average_response_time"] - 0.2) < 0.001
    assert metrics["error_rate"] == 0.25  # (1 + 1) / 8
    assert metrics["error_counts"][400] == 1
    assert metrics["error_counts"][500] == 1
    assert metrics["suspicious_requests"]["192.168.1.1"] == 2


def test_prometheus_metrics(client: TestClient) -> None:
    """Test Prometheus metrics endpoint functionality.

    Args:
        client: FastAPI test client for making requests.
    """
    # Make requests to several endpoints to generate metrics
    client.get("/api/v1/")
    client.get("/api/v1/health")
    # Use post method for the analyze endpoint
    client.post(
        "/api/v1/analyze",
        json={"text": "My name is John Doe", "language": "en"},
    )

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


def test_rate_limiter_cleanup_expired_blocked_ips() -> None:
    """Test cleanup of expired blocked IPs in the rate limiter."""
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    app.add_middleware(
        RateLimiterMiddleware,
        requests_per_minute=10,
        burst_limit=5,
        block_duration=1,
    )

    # Simulate the cleanup by directly testing the logic
    # This tests lines 85-95 in middleware.py
    now = datetime.now(timezone.utc)
    past_time = now - timedelta(seconds=2)

    # Create a new rate limiter instance to test the logic
    test_rate_limiter = RateLimiterMiddleware(
        app=FastAPI(),
        requests_per_minute=10,
        burst_limit=5,
        block_duration=1,
    )    # Add an expired blocked IP
    test_rate_limiter.blocked_ips["expired_ip"] = past_time
    test_rate_limiter.blocked_ips["valid_ip"] = now + timedelta(seconds=10)
    # Make a request from the expired IP - this should trigger cleanup
    mock_request = Mock()
    mock_request.client = Mock()
    mock_request.client.host = "expired_ip"

    async def mock_call_next(request: Request) -> Response:
        mock_response = Mock()
        mock_response.headers = {}
        return mock_response

    # Run the dispatch method which should clean up the expired IP
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(test_rate_limiter.dispatch(mock_request, mock_call_next))
        # The expired IP should be removed, but the valid one should remain
        assert "expired_ip" not in test_rate_limiter.blocked_ips
        assert "valid_ip" in test_rate_limiter.blocked_ips
    finally:
        loop.close()


def test_rate_limiter_blocked_ip_response() -> None:
    """Test that blocked IPs receive proper 429 response."""
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    # Create rate limiter with very low limits
    test_rate_limiter = RateLimiterMiddleware(
        app=app,
        requests_per_minute=1,
        burst_limit=1,
        block_duration=5,
    )

    # Manually block an IP
    now = datetime.now(timezone.utc)
    test_rate_limiter.blocked_ips["blocked_ip"] = now + timedelta(seconds=5)

    # Create a mock request from the blocked IP
    mock_request = Mock()
    mock_request.client = Mock()
    mock_request.client.host = "blocked_ip"

    async def mock_call_next(request: Request) -> Response:
        mock_response = Mock()
        mock_response.headers = {}
        return mock_response    # Test that the blocked IP gets a 429 response
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        response = loop.run_until_complete(
            test_rate_limiter.dispatch(mock_request, mock_call_next)
        )
        assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
        # Test that retry_after is included in response (lines 85-95)
        import json

        response_body = (
            response.body.decode() if isinstance(response.body, bytes) else response.body
        )
        response_content = json.loads(response_body)
        assert "retry_after" in response_content
    finally:
        loop.close()


def test_rate_limiter_burst_limit_blocking() -> None:
    """Test that burst limit violations result in IP blocking."""
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    # Create rate limiter with very low burst limit
    test_rate_limiter = RateLimiterMiddleware(
        app=app,
        requests_per_minute=10,
        burst_limit=2,  # Very low burst limit
        block_duration=5,
    )

    # Create mock request
    mock_request = Mock()
    mock_request.client = Mock()
    mock_request.client.host = "test_ip"

    async def mock_call_next(request: Request) -> Response:
        mock_response = Mock()
        mock_response.headers = {}
        return mock_response

    # Simulate burst limit exceeded scenario
    import time

    now_ts = time.time()
    # 3 requests in last minute
    test_rate_limiter.requests["test_ip"] = [now_ts - 10, now_ts - 5, now_ts - 1]

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        response = loop.run_until_complete(test_rate_limiter.dispatch(mock_request, mock_call_next))
        # Should return 429 due to burst limit violation (lines 105-115)
        assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
        # IP should be blocked
        assert "test_ip" in test_rate_limiter.blocked_ips
    finally:
        loop.close()


def test_rate_limiter_rate_limit_exceeded() -> None:
    """Test rate limit exceeded scenario."""
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    # Create rate limiter
    test_rate_limiter = RateLimiterMiddleware(
        app=app,
        requests_per_minute=3,
        burst_limit=10,  # High burst limit, low rate limit
        block_duration=5,
    )

    # Create mock request
    mock_request = Mock()
    mock_request.client = Mock()
    mock_request.client.host = "test_ip"

    async def mock_call_next(request: Request) -> Response:
        mock_response = Mock()
        mock_response.headers = {}
        return mock_response    # Simulate rate limit exceeded (but not burst limit)
    import time
    now_ts = time.time()
    # Add exactly requests_per_minute requests in the last minute
    test_rate_limiter.requests["test_ip"] = [
        now_ts - 50, now_ts - 30, now_ts - 10
    ]
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        response = loop.run_until_complete(
            test_rate_limiter.dispatch(mock_request, mock_call_next)
        )
        # Should return 429 due to rate limit (lines 117-125)
        assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
        import json

        response_body = (
            response.body.decode() if isinstance(response.body, bytes) else response.body
        )
        response_content = json.loads(response_body)
        assert "retry_after" in response_content
    finally:
        loop.close()


def test_metrics_middleware_exception_handling() -> None:
    """Test MetricsMiddleware exception handling and error counting."""
    app = FastAPI()

    @app.get("/test-500")
    async def error_endpoint():
        raise ValueError("Internal server error")

    @app.get("/test-success")
    async def success_endpoint():
        return {"message": "success"}

    # Create metrics middleware directly
    metrics_middleware = MetricsMiddleware(app)

    # Create mock request
    mock_request = Mock()
    mock_request.url = Mock()
    mock_request.url.path = "/test-500"
    mock_request.client = Mock()
    mock_request.client.host = "test_ip"

    async def mock_call_next_error(request: Request) -> Response:
        raise ValueError("Test error")

    # Test exception handling in dispatch method
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        # This should raise an exception but still update metrics (lines 205-220)
        with pytest.raises(ValueError):
            loop.run_until_complete(metrics_middleware.dispatch(mock_request, mock_call_next_error))

        # Check that error metrics were recorded
        assert metrics_middleware.error_counts[500] > 0
        assert metrics_middleware.requests_count > 0
        assert metrics_middleware.requests_by_path["/test-500"] > 0
    finally:
        loop.close()


def test_metrics_middleware_response_time_tracking() -> None:
    """Test that MetricsMiddleware tracks response times correctly."""
    app = FastAPI()
    metrics_middleware = MetricsMiddleware(app)

    # Create mock request
    mock_request = Mock()
    mock_request.url = Mock()
    mock_request.url.path = "/test"
    mock_request.client = Mock()
    mock_request.client.host = "test_ip"

    async def mock_call_next_slow(request: Request) -> Response:
        # Simulate slow response
        await asyncio.sleep(0.1)
        mock_response = Mock()
        mock_response.headers = {}
        mock_response.status_code = 200
        return mock_response

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(metrics_middleware.dispatch(mock_request, mock_call_next_slow))
        # Check that response time was recorded
        assert len(metrics_middleware.response_times) > 0
        assert metrics_middleware.response_times[-1] >= 0.05  # Should be at least 0.05 seconds
        assert metrics_middleware.requests_count > 0
        assert metrics_middleware.requests_by_path["/test"] > 0
    finally:
        loop.close()


def test_metrics_middleware_suspicious_request_various_patterns() -> None:
    """Test MetricsMiddleware detection of various suspicious patterns."""
    app = FastAPI()
    middleware = MetricsMiddleware(app)

    # Test various suspicious patterns that should be detected
    test_cases = [
        ("/api/../../etc/passwd", "Path traversal with ../../"),
        ("/api/test?q=SELECT * FROM users", "SQL injection with SELECT"),
        ("/api/test?data=<script>alert('xss')</script>", "XSS with script tags"),
        ("/api/../etc/passwd/config", "Path traversal with ../etc/passwd"),
        ("/api/normal", "Normal request - should not be suspicious"),
    ]

    for path, description in test_cases:
        mock_request = Mock()
        mock_request.url = Mock()
        mock_request.url.path = path
        mock_request.query_params = ""

        is_suspicious = middleware._is_suspicious_request(mock_request)

        if "normal" in description.lower():
            assert not is_suspicious, f"Normal request incorrectly flagged: {description}"
        else:
            assert is_suspicious, f"Suspicious pattern not detected: {description}"


def test_metrics_middleware_comprehensive_metrics_calculation() -> None:
    """Test comprehensive metrics calculation with edge cases."""
    app = FastAPI()
    middleware = MetricsMiddleware(app)

    # Test metrics calculation with various data
    middleware.requests_by_path["/api/test1"] = 5
    middleware.requests_by_path["/api/test2"] = 3
    middleware.requests_by_path["/api/test3"] = 2
    middleware.response_times = [0.1, 0.2, 0.15, 0.25, 0.3]
    middleware.error_counts[400] = 1
    middleware.error_counts[404] = 2
    middleware.error_counts[500] = 1
    middleware.suspicious_requests["192.168.1.1"] = 3
    middleware.suspicious_requests["10.0.0.1"] = 1
    # Set requests_count to match the total for proper error rate calculation
    middleware.requests_count = 10

    metrics = middleware.get_metrics()

    # Verify all metrics are correctly calculated
    assert metrics["total_requests"] == 10  # 5 + 3 + 2
    assert metrics["requests_by_path"]["/api/test1"] == 5
    assert metrics["requests_by_path"]["/api/test2"] == 3
    assert metrics["requests_by_path"]["/api/test3"] == 2
    assert abs(metrics["average_response_time"] - 0.2) < 0.001  # (0.1+0.2+0.15+0.25+0.3)/5
    assert metrics["error_rate"] == 0.4  # (1+2+1)/10
    assert metrics["error_counts"][400] == 1
    assert metrics["error_counts"][404] == 2
    assert metrics["error_counts"][500] == 1
    assert metrics["suspicious_requests"]["192.168.1.1"] == 3
    assert metrics["suspicious_requests"]["10.0.0.1"] == 1


def test_metrics_middleware_edge_case_calculations() -> None:
    """Test edge cases in metrics calculations."""
    app = FastAPI()
    middleware = MetricsMiddleware(app)

    # Test empty response times - should return 0.001
    assert middleware._calculate_average_response_time() == 0.001

    # Test empty error counts - should return 0.0
    assert middleware._calculate_error_rate() == 0.0

    # Test with some response times but very small values
    middleware.response_times = [0.0001, 0.0002]
    avg_time = middleware._calculate_average_response_time()
    assert avg_time == max(0.00015, 0.001)  # Should be at least 0.001

    # Test error rate with zero requests
    middleware.requests_count = 0
    middleware.error_counts[500] = 1
    assert middleware._calculate_error_rate() == 0.0


def test_metrics_middleware_suspicious_request_logging() -> None:
    """Test that suspicious requests are properly logged and counted."""
    app = FastAPI()
    metrics_middleware = MetricsMiddleware(app)

    # Create mock request with suspicious pattern
    mock_request = Mock()
    mock_request.url = Mock()
    mock_request.url.path = "/api/../../etc/passwd"  # Suspicious pattern
    mock_request.client = Mock()
    mock_request.client.host = "suspicious_ip"

    async def mock_call_next(request: Request) -> Response:
        mock_response = Mock()
        mock_response.headers = {}
        mock_response.status_code = 200
        return mock_response

    # Test that suspicious request is detected and counted
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(metrics_middleware.dispatch(mock_request, mock_call_next))

        # Check that suspicious request was logged (lines 191-192)
        assert metrics_middleware.suspicious_requests["suspicious_ip"] == 1
        assert metrics_middleware.requests_count > 0
        assert metrics_middleware.requests_by_path["/api/../../etc/passwd"] > 0
    finally:
        loop.close()


def test_metrics_middleware_error_status_code_tracking() -> None:
    """Test that different error status codes are properly tracked."""
    app = FastAPI()
    metrics_middleware = MetricsMiddleware(app)

    # Create mock request
    mock_request = Mock()
    mock_request.url = Mock()
    mock_request.url.path = "/api/test"
    mock_request.client = Mock()
    mock_request.client.host = "test_ip"

    # Test different error status codes
    error_codes = [400, 404, 500, 503]

    for status_code in error_codes:

        async def mock_call_next_error(request: Request, code=status_code) -> Response:
            mock_response = Mock()
            mock_response.headers = {}
            mock_response.status_code = code
            return mock_response

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(metrics_middleware.dispatch(mock_request, mock_call_next_error))
        finally:
            loop.close()

    # Check that all error codes were tracked (line 205)
    for status_code in error_codes:
        assert metrics_middleware.error_counts[status_code] == 1
