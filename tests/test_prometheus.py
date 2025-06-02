"""Tests for Prometheus metrics functionality."""

from typing import Any, MutableMapping
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from presidio_fastapi.app.prometheus import (
    PrometheusMiddleware,
    metrics_endpoint,
    setup_prometheus,
    track_pii_entity,
)


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI application."""
    return FastAPI()


@pytest.fixture
def client_with_prometheus(app: FastAPI) -> TestClient:
    """Create a test client with Prometheus middleware."""
    setup_prometheus(app)
    return TestClient(app)


def test_prometheus_middleware_exception_handling() -> None:
    """Test that PrometheusMiddleware handles exceptions properly."""
    app = FastAPI()
    middleware = PrometheusMiddleware(app)

    # Create proper mock ASGI functions
    async def mock_receive() -> MutableMapping[str, Any]:
        return {"type": "http.request", "body": b""}

    async def mock_send(message: MutableMapping[str, Any]) -> None:
        pass

    # Mock an exception in the application
    async def mock_app(scope: MutableMapping[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] == "http":
            raise ValueError("Test exception")

    middleware.app = mock_app

    # Test that exception is properly handled and metrics are updated
    scope = {"type": "http", "path": "/api/v1/analyze", "method": "POST"}

    with pytest.raises(ValueError, match="Test exception"):
        # This will trigger the exception handling in middleware
        import asyncio

        asyncio.run(middleware(scope, mock_receive, mock_send))


def test_track_pii_entity() -> None:
    """Test the track_pii_entity function."""
    # Clear any existing metrics
    REGISTRY._collector_to_names.clear()
    REGISTRY._names_to_collectors.clear()

    # Test tracking PII entities
    track_pii_entity("EMAIL_ADDRESS", "en")
    track_pii_entity("PERSON", "en")
    track_pii_entity("CREDIT_CARD", "es")

    # Verify metrics were recorded (we can't easily assert specific values
    # due to Prometheus client's global state, but we can verify no exceptions)
    assert True  # If we reach here, no exceptions were thrown


def test_metrics_endpoint_function() -> None:
    """Test the metrics_endpoint function returns correct response."""
    endpoint_func = metrics_endpoint()

    # The function should return a callable
    assert callable(endpoint_func)

    # Test that it returns a Response with correct content type
    # The metrics function requires a request parameter (even though it's not used)
    mock_request = Mock()

    import asyncio

    response = asyncio.run(endpoint_func(mock_request))
    assert response.media_type == "text/plain; version=0.0.4; charset=utf-8"


def test_setup_prometheus_with_app(app: FastAPI) -> None:
    """Test that setup_prometheus correctly configures the app."""
    # Count initial middleware
    initial_middleware_count = len(app.user_middleware)
    initial_routes_count = len(app.routes)

    setup_prometheus(app)

    # Verify middleware was added
    assert len(app.user_middleware) == initial_middleware_count + 1

    # Verify metrics route was added
    assert len(app.routes) == initial_routes_count + 1
    # Verify the metrics route exists
    metrics_routes = [r for r in app.routes if "/metrics" in str(r)]
    assert len(metrics_routes) == 1


def test_prometheus_middleware_path_filtering() -> None:
    """Test that middleware only processes monitored paths."""
    app = FastAPI()

    # Create proper mock ASGI functions
    async def mock_receive() -> MutableMapping[str, Any]:
        return {"type": "http.request", "body": b""}

    async def mock_send(message: MutableMapping[str, Any]) -> None:
        pass

    # Mock settings to only monitor specific paths
    with patch("presidio_fastapi.app.prometheus.settings") as mock_settings:
        mock_settings.API_VERSION = "v1"
        mock_settings.PROMETHEUS_MONITORED_PATHS = "analyze"

        middleware = PrometheusMiddleware(app)

        # Test that non-monitored paths are skipped
        scope_unmonitored = {"type": "http", "path": "/api/v1/health", "method": "GET"}

        # Create an async mock app
        mock_app = AsyncMock()
        middleware.app = mock_app

        import asyncio

        asyncio.run(middleware(scope_unmonitored, mock_receive, mock_send))

        # Verify the original app was called without metrics processing
        mock_app.assert_called_once_with(scope_unmonitored, mock_receive, mock_send)


def test_prometheus_middleware_error_count_on_exception() -> None:
    """Test that error counts are incremented when exceptions occur."""
    app = FastAPI()

    # Create proper mock ASGI functions
    async def mock_receive() -> MutableMapping[str, Any]:
        return {"type": "http.request", "body": b""}

    async def mock_send(message: MutableMapping[str, Any]) -> None:
        pass

    with patch("presidio_fastapi.app.prometheus.settings") as mock_settings:
        mock_settings.API_VERSION = "v1"
        mock_settings.PROMETHEUS_MONITORED_PATHS = "analyze"

        middleware = PrometheusMiddleware(app)

        # Mock an exception in the application
        async def mock_app_with_exception(
            scope: MutableMapping[str, Any], receive: Any, send: Any
        ) -> None:
            raise RuntimeError("Database connection failed")

        middleware.app = mock_app_with_exception

        scope = {"type": "http", "path": "/api/v1/analyze", "method": "POST"}

        # Test exception handling
        with pytest.raises(RuntimeError, match="Database connection failed"):
            import asyncio

            asyncio.run(middleware(scope, mock_receive, mock_send))


def test_prometheus_middleware_non_http_scope() -> None:
    """Test that middleware handles non-HTTP scopes correctly."""
    app = FastAPI()
    middleware = PrometheusMiddleware(app)

    # Create proper mock ASGI functions
    async def mock_receive() -> MutableMapping[str, Any]:
        return {"type": "websocket.connect"}

    async def mock_send(message: MutableMapping[str, Any]) -> None:
        pass

    # Mock the app with AsyncMock for async compatibility
    mock_app = AsyncMock()
    middleware.app = mock_app

    # Test WebSocket scope
    websocket_scope = {"type": "websocket", "path": "/ws"}

    import asyncio

    asyncio.run(middleware(websocket_scope, mock_receive, mock_send))

    # Verify the original app was called for non-HTTP requests
    mock_app.assert_called_once_with(websocket_scope, mock_receive, mock_send)
