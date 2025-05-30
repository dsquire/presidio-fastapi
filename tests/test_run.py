"""Tests for the run.py entry point module."""

from unittest.mock import patch

from presidio_fastapi.run import main


def test_main_calls_uvicorn_with_correct_parameters() -> None:
    """Test that main() calls uvicorn.run with the correct parameters.

    This test verifies that the main function properly configures and starts
    the uvicorn server with settings from the configuration.
    """
    with patch("presidio_fastapi.run.uvicorn.run") as mock_uvicorn_run:
        with patch("presidio_fastapi.run.settings") as mock_settings:
            # Configure mock settings
            mock_settings.SERVER_HOST = "127.0.0.1"
            mock_settings.SERVER_PORT = 8080
            mock_settings.LOG_LEVEL = "DEBUG"

            # Call the main function
            main()

            # Verify uvicorn.run was called with correct parameters
            mock_uvicorn_run.assert_called_once_with(
                "presidio_fastapi.app.main:app",
                host="127.0.0.1",
                port=8080,
                log_level="debug",
                reload=True,
            )


def test_main_uses_default_settings() -> None:
    """Test that main() uses default settings when no custom config is provided."""
    with patch("presidio_fastapi.run.uvicorn.run") as mock_uvicorn_run:
        # Call main with default settings
        main()

        # Verify uvicorn.run was called (settings will be loaded from actual config)
        mock_uvicorn_run.assert_called_once()

        # Verify the app module string is correct
        call_args = mock_uvicorn_run.call_args
        assert call_args[1]["reload"] is True
        assert "presidio_fastapi.app.main:app" in call_args[0]


def test_main_handles_settings_properly() -> None:
    """Test that main() properly loads and uses settings configuration."""
    with patch("presidio_fastapi.run.uvicorn.run") as mock_uvicorn_run:
        with patch("presidio_fastapi.run.settings") as mock_settings:
            # Test with different settings values
            mock_settings.SERVER_HOST = "0.0.0.0"
            mock_settings.SERVER_PORT = 9000
            mock_settings.LOG_LEVEL = "WARNING"

            main()

            # Verify settings were used correctly
            mock_uvicorn_run.assert_called_once_with(
                "presidio_fastapi.app.main:app",
                host="0.0.0.0",
                port=9000,
                log_level="warning",
                reload=True,
            )


def test_main_converts_log_level_to_lowercase() -> None:
    """Test that the LOG_LEVEL setting is converted to lowercase for uvicorn."""
    with patch("presidio_fastapi.run.uvicorn.run") as mock_uvicorn_run:
        with patch("presidio_fastapi.run.settings") as mock_settings:
            mock_settings.SERVER_HOST = "localhost"
            mock_settings.SERVER_PORT = 8000
            mock_settings.LOG_LEVEL = "INFO"

            main()

            # Verify log level is lowercased
            call_args = mock_uvicorn_run.call_args[1]
            assert call_args["log_level"] == "info"


if __name__ == "__main__":
    # Allow running this test file directly
    main()
