"""Test configuration and fixtures."""

import asyncio
from typing import AsyncGenerator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from presidio_fastapi.app.main import create_app

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

    # Mock the telemetry setup and shutdown functions using monkeypatch
    from unittest.mock import MagicMock

    from presidio_fastapi.app import telemetry

    # Create a better mock that doesn't create real telemetry resources
    mock_setup = MagicMock()
    mock_shutdown = MagicMock()

    monkeypatch.setattr(telemetry, "setup_telemetry", mock_setup)
    monkeypatch.setattr(telemetry, "shutdown_telemetry", mock_shutdown)

    # Also mock the config settings to ensure OTEL_ENABLED is False
    from presidio_fastapi.app.config import settings

    monkeypatch.setattr(settings, "OTEL_ENABLED", False)

    # Reset telemetry global state to prevent cross-test contamination
    # Use direct assignment to ensure proper state reset
    telemetry._tracer_provider = None
    telemetry._span_processors.clear()
    telemetry._is_setup_complete = False


@pytest.fixture(scope="session")
def burst_limit() -> int:
    """Return the burst limit constant for rate limiting tests."""
    return BURST_LIMIT


@pytest.fixture
async def app_with_lifespan() -> AsyncGenerator[FastAPI, None]:
    """Provide a FastAPI app instance with lifespan events executed.

    Yields:
        FastAPI: The application instance.
    """
    app = create_app()

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
    # Mock the analyzer in app state with proper RecognizerResult objects
    from unittest.mock import Mock

    from presidio_analyzer import AnalyzerEngine, RecognizerResult

    mock_analyzer = Mock(spec=AnalyzerEngine)

    # Create mock results for a typical test
    mock_results = [
        RecognizerResult(entity_type="PERSON", start=11, end=19, score=0.85),
        RecognizerResult(entity_type="EMAIL_ADDRESS", start=33, end=49, score=0.95),
    ]
    mock_analyzer.analyze.return_value = mock_results

    # Set the mocked analyzer in app state
    app_with_lifespan.state.analyzer = mock_analyzer

    # Initialize test client with the app that has completed lifespan setup
    return TestClient(app_with_lifespan)
