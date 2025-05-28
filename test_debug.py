"""Test to debug telemetry setup issues."""

import os
import pytest
from presidio_fastapi.app.config import settings


def test_environment_variables():
    """Test that environment variables are set correctly."""
    print(f"OTEL_ENABLED env var: {os.environ.get('OTEL_ENABLED')}")
    print(f"OTEL_ENABLED in settings: {settings.OTEL_ENABLED}")
    assert os.environ.get('OTEL_ENABLED') == 'false'
    assert settings.OTEL_ENABLED is False


def test_telemetry_import():
    """Test that telemetry can be imported without errors."""
    try:
        from presidio_fastapi.app.telemetry import setup_telemetry, shutdown_telemetry
        print("Telemetry imported successfully")
        assert True
    except Exception as e:
        print(f"Import error: {e}")
        pytest.fail(f"Failed to import telemetry: {e}")


def test_settings_attributes():
    """Test that required settings attributes exist."""
    print(f"OTEL_SERVICE_NAME: {getattr(settings, 'OTEL_SERVICE_NAME', 'NOT_FOUND')}")
    print(f"API_VERSION: {getattr(settings, 'API_VERSION', 'NOT_FOUND')}")
    
    assert hasattr(settings, 'OTEL_SERVICE_NAME')
    assert hasattr(settings, 'API_VERSION')
    assert not hasattr(settings, 'SERVICE_NAME')  # This should NOT exist
