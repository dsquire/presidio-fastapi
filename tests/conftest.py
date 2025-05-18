"""Test configuration and fixtures."""

import asyncio
from typing import AsyncGenerator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from presidio_fastapi.app.main import create_app
from presidio_fastapi.app.middleware import MetricsMiddleware

# Test constants
REQUESTS_PER_MINUTE = 60
BURST_LIMIT = 100
BLOCK_DURATION = 1


@pytest.fixture(autouse=True)
def disable_telemetry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable OpenTelemetry for all tests.

    This prevents test runs from generating telemetry data and
    attempting to connect to external services.

    Args:
        monkeypatch: pytest's monkeypatch fixture for modifying values.
    """
    # Completely disable OpenTelemetry
    monkeypatch.setenv("OTEL_ENABLED", "false")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    # Disable all OpenTelemetry features
    monkeypatch.setenv("OTEL_PYTHON_DISABLED_INSTRUMENTATIONS", "*")
    monkeypatch.setenv("OTEL_TRACES_SAMPLER", "always_off")
    monkeypatch.setenv("OTEL_TRACES_EXPORTER", "none")

    # Prevent any exporters from being created
    monkeypatch.setenv("OTEL_METRIC_EXPORT_INTERVAL", "0")
    monkeypatch.setenv("OTEL_METRIC_EXPORT", "none")

    # Mock the telemetry setup function using monkeypatch
    from unittest.mock import MagicMock

    from presidio_fastapi.app import telemetry

    monkeypatch.setattr(telemetry, "setup_telemetry", MagicMock())


@pytest.fixture(scope="session")
def metrics_middleware() -> MetricsMiddleware:
    """Create a metrics middleware instance shared across all tests.

    This uses session scope to ensure the same instance is used across all tests,
    preserving request counts and other metrics.

    Returns:
        MetricsMiddleware: The shared metrics middleware instance.
    """
    # Initialize with None as app since it will be set later in create_app
    return MetricsMiddleware(None)


@pytest.fixture
async def app_with_lifespan(
    metrics_middleware: MetricsMiddleware,
) -> AsyncGenerator[FastAPI, None]:
    """Provide a FastAPI app instance with lifespan events executed.

    Args:
        metrics_middleware: The shared metrics middleware instance.

    Yields:
        FastAPI: The application instance.
    """
    app = create_app(metrics_instance=metrics_middleware)

    async with app.router.lifespan_context(app):
        # Wait for any background tasks
        await asyncio.sleep(0.1)
        yield app


@pytest.fixture
def client(app_with_lifespan: FastAPI) -> TestClient:
    """Create a test client for the FastAPI app with lifespan setup.

    Args:
        app_with_lifespan: The FastAPI app instance with lifespan events.

    Returns:
        TestClient: A configured test client for making requests.
    """
    # Initialize test client with the app that has completed lifespan setup
    return TestClient(app_with_lifespan)
