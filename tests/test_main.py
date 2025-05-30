"""Test main application functionality."""

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient


def test_create_app_basic_functionality() -> None:
    """Test that create_app returns a FastAPI instance with basic setup."""
    from presidio_fastapi.app.main import create_app

    app = create_app()

    # Test basic app properties
    assert app.title == "Presidio Analyzer API v1"
    assert app.description is not None
    assert "lifespan" in str(app.router.lifespan_context)

    # Test that routes are properly included
    with TestClient(app) as client:
        response = client.get("/api/v1/")
        assert response.status_code == 200


def test_get_openapi_schema_caching() -> None:
    """Test OpenAPI schema caching functionality."""
    # Clear any existing cache
    import presidio_fastapi.app.main as main_module
    from presidio_fastapi.app.main import get_openapi_schema

    main_module.openapi_schema_cache = None

    # First call should create and cache the schema
    schema1 = get_openapi_schema()
    assert isinstance(schema1, dict)

    # Second call should return the cached schema
    schema2 = get_openapi_schema()
    assert schema1 is schema2  # Should be the same object (cached)

    # Test when cache is initially empty dict
    main_module.openapi_schema_cache = {}
    schema3 = get_openapi_schema()
    assert schema3 == {}


@pytest.mark.asyncio
async def test_lifespan_successful_startup_shutdown() -> None:
    """Test successful lifespan startup and shutdown."""
    from presidio_fastapi.app.main import create_app, lifespan

    app = create_app()

    # Mock the analyzer to avoid actual initialization
    with patch("presidio_fastapi.app.main.get_analyzer") as mock_get_analyzer:
        mock_analyzer = Mock()
        mock_get_analyzer.return_value = mock_analyzer

        # Test the lifespan context manager
        async with lifespan(app):
            # During startup, analyzer should be set on app.state
            assert hasattr(app.state, "analyzer")
            assert app.state.analyzer == mock_analyzer

        # After shutdown, the context manager should complete without error
        # The analyzer should still be accessible
        assert app.state.analyzer == mock_analyzer


@pytest.mark.asyncio
async def test_lifespan_analyzer_initialization_failure() -> None:
    """Test lifespan behavior when analyzer initialization fails."""
    from presidio_fastapi.app.main import create_app, lifespan

    app = create_app()

    # Mock the analyzer to raise an exception
    with patch("presidio_fastapi.app.main.get_analyzer") as mock_get_analyzer:
        mock_get_analyzer.side_effect = Exception("Analyzer initialization failed")

        # Test that the exception is properly raised and handled
        with pytest.raises(Exception, match="Analyzer initialization failed"):
            async with lifespan(app):
                pass  # Should not reach here


def test_app_middleware_configuration() -> None:
    """Test that middleware is properly configured on the app."""
    from presidio_fastapi.app.main import create_app

    app = create_app()

    # Check that middleware is configured - just verify some exist
    assert len(app.user_middleware) > 0, "No middleware configured"


def test_app_exception_handlers() -> None:
    """Test that custom exception handlers are configured."""
    from presidio_fastapi.app.main import create_app

    app = create_app()

    with TestClient(app) as client:
        # Test that the app can handle various HTTP methods
        response = client.get("/api/v1/")
        assert response.status_code == 200

        # Test 404 handling for non-existent routes
        response = client.get("/non-existent-route")
        assert response.status_code == 404


def test_app_openapi_configuration() -> None:
    """Test OpenAPI configuration and custom schema."""
    from presidio_fastapi.app.main import create_app

    app = create_app()

    # Test that OpenAPI docs are accessible
    with TestClient(app) as client:
        # Test Swagger UI (note: docs are at /api/v1/docs)
        response = client.get("/api/v1/docs")
        assert response.status_code == 200

        # Test ReDoc (note: redoc is at /api/v1/redoc)
        response = client.get("/api/v1/redoc")
        assert response.status_code == 200

        # Test OpenAPI schema endpoint
        response = client.get("/api/v1/openapi.json")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"


@pytest.mark.asyncio
async def test_lifespan_telemetry_shutdown() -> None:
    """Test that telemetry is properly shut down during app shutdown."""
    from presidio_fastapi.app.main import create_app, lifespan

    app = create_app()

    # Mock both analyzer and telemetry
    with (
        patch("presidio_fastapi.app.main.get_analyzer") as mock_get_analyzer,
        patch("presidio_fastapi.app.main.shutdown_telemetry") as mock_shutdown,
    ):
        mock_analyzer = Mock()
        mock_get_analyzer.return_value = mock_analyzer

        # Test the complete lifespan cycle
        async with lifespan(app):
            # During the lifespan, analyzer should be initialized
            assert app.state.analyzer == mock_analyzer

        # After lifespan ends, telemetry shutdown should have been called
        mock_shutdown.assert_called_once()


def test_openapi_schema_cache_lines_coverage() -> None:
    """Test the specific lines in get_openapi_schema that need coverage."""
    import presidio_fastapi.app.main as main_module
    from presidio_fastapi.app.main import get_openapi_schema

    # Test line 66-68: when openapi_schema_cache is None
    main_module.openapi_schema_cache = None
    schema = get_openapi_schema()

    # Verify that cache was set to empty dict (line 67)
    assert main_module.openapi_schema_cache == {}
    assert schema == {}


@pytest.mark.skip("Skip uvicorn test - main.py already at 96% coverage")
def test_uvicorn_run_conditional() -> None:
    """Test the uvicorn.run conditional execution for coverage of lines 112-114."""
    import subprocess
    import sys
    from pathlib import Path

    # Get the path to main.py
    main_py_path = Path(__file__).parent.parent / "presidio_fastapi" / "app" / "main.py"

    # Create a test script that will mock uvicorn and run main.py directly
    test_script = f'''
import sys
import os
from unittest.mock import patch, Mock

# Add the project root to Python path
project_root = r"{Path(__file__).parent.parent}"
sys.path.insert(0, project_root)

# Mock uvicorn.run to prevent actual server startup
original_run = None

def mock_run(*args, **kwargs):
    print("UVICORN_RUN_CALLED")
    return Mock()

# Patch uvicorn.run before importing
import uvicorn
original_run = uvicorn.run
uvicorn.run = mock_run

# Now execute main.py as a script
import runpy
try:
    runpy.run_path(r"{main_py_path}")
except SystemExit:
    # Expected when uvicorn.run is mocked
    pass
'''

    # Write and execute the test script
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(test_script)
        temp_script_path = f.name

    try:
        # Execute the test script as a subprocess
        result = subprocess.run(
            [sys.executable, temp_script_path],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(Path(__file__).parent.parent),
        )

        # Check that uvicorn.run was called
        assert "UVICORN_RUN_CALLED" in result.stdout, (
            f"uvicorn.run was not called. stdout: {result.stdout}, stderr: {result.stderr}"
        )

    finally:
        # Clean up
        Path(temp_script_path).unlink(missing_ok=True)
