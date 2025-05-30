"""Tests for the analyzer service module."""

from unittest.mock import Mock, patch

import pytest
from presidio_analyzer import AnalyzerEngine, RecognizerResult

from presidio_fastapi.app.services.analyzer import analyze_with_metrics, get_analyzer


def test_get_analyzer_success() -> None:
    """Test successful analyzer creation."""
    with patch(
        "presidio_fastapi.app.services.analyzer.AnalyzerEngineProvider"
    ) as mock_provider_class:
        # Mock the provider and engine
        mock_provider = Mock()
        mock_engine = Mock(spec=AnalyzerEngine)
        mock_provider.create_engine.return_value = mock_engine
        mock_provider_class.return_value = mock_provider

        # Clear the cache to ensure we test the actual function
        get_analyzer.cache_clear()

        analyzer = get_analyzer()

        # Verify the analyzer was created successfully
        assert analyzer == mock_engine
        mock_provider_class.assert_called_once()
        mock_provider.create_engine.assert_called_once()


def test_get_analyzer_configuration_file_path() -> None:
    """Test that the correct configuration file path is used."""
    with patch(
        "presidio_fastapi.app.services.analyzer.AnalyzerEngineProvider"
    ) as mock_provider_class:
        mock_provider = Mock()
        mock_engine = Mock(spec=AnalyzerEngine)
        mock_provider.create_engine.return_value = mock_engine
        mock_provider_class.return_value = mock_provider

        # Clear the cache
        get_analyzer.cache_clear()

        get_analyzer()

        # Verify the correct config path was used
        call_args = mock_provider_class.call_args
        config_path = call_args[1]["analyzer_engine_conf_file"]

        # Verify it points to the recognizers.yaml file
        assert config_path.endswith("recognizers.yaml")
        assert "config" in config_path


def test_get_analyzer_file_not_found_exception() -> None:
    """Test analyzer creation when configuration file is not found."""
    with patch(
        "presidio_fastapi.app.services.analyzer.AnalyzerEngineProvider"
    ) as mock_provider_class:
        # Mock FileNotFoundError
        mock_provider_class.side_effect = FileNotFoundError("Configuration file not found")

        # Clear the cache
        get_analyzer.cache_clear()

        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            get_analyzer()


def test_get_analyzer_invalid_configuration_exception() -> None:
    """Test analyzer creation with invalid YAML configuration."""
    with patch(
        "presidio_fastapi.app.services.analyzer.AnalyzerEngineProvider"
    ) as mock_provider_class:
        # Mock YAML parsing error
        mock_provider_class.side_effect = ValueError("Invalid YAML configuration")

        # Clear the cache
        get_analyzer.cache_clear()

        with pytest.raises(ValueError, match="Invalid YAML configuration"):
            get_analyzer()


def test_get_analyzer_engine_creation_failure() -> None:
    """Test analyzer creation when engine creation fails."""
    with patch(
        "presidio_fastapi.app.services.analyzer.AnalyzerEngineProvider"
    ) as mock_provider_class:
        mock_provider = Mock()
        # Mock engine creation failure
        mock_provider.create_engine.side_effect = RuntimeError("Failed to create engine")
        mock_provider_class.return_value = mock_provider

        # Clear the cache
        get_analyzer.cache_clear()

        with pytest.raises(RuntimeError, match="Failed to create engine"):
            get_analyzer()


def test_get_analyzer_caching() -> None:
    """Test that get_analyzer properly caches the result."""
    with patch(
        "presidio_fastapi.app.services.analyzer.AnalyzerEngineProvider"
    ) as mock_provider_class:
        mock_provider = Mock()
        mock_engine = Mock(spec=AnalyzerEngine)
        mock_provider.create_engine.return_value = mock_engine
        mock_provider_class.return_value = mock_provider

        # Clear the cache
        get_analyzer.cache_clear()

        # Call twice
        analyzer1 = get_analyzer()
        analyzer2 = get_analyzer()

        # Verify same instance is returned and provider is only called once
        assert analyzer1 == analyzer2
        mock_provider_class.assert_called_once()


def test_analyze_with_metrics() -> None:
    """Test analyze_with_metrics function."""
    # Mock analyzer
    mock_analyzer = Mock(spec=AnalyzerEngine)

    # Create mock results
    mock_result1 = RecognizerResult(entity_type="EMAIL_ADDRESS", start=10, end=25, score=0.85)
    mock_result2 = RecognizerResult(entity_type="PERSON", start=30, end=40, score=0.75)
    mock_results = [mock_result1, mock_result2]
    mock_analyzer.analyze.return_value = mock_results

    with patch("presidio_fastapi.app.services.analyzer.track_pii_entity") as mock_track:
        # Test the function
        results = analyze_with_metrics(
            analyzer=mock_analyzer,
            text="Test text with john@example.com and John Doe",
            language="en",
        )

        # Verify results are returned correctly
        assert results == mock_results

        # Verify analyzer.analyze was called with correct parameters
        mock_analyzer.analyze.assert_called_once_with(
            text="Test text with john@example.com and John Doe", language="en"
        )

        # Verify metrics were tracked for each entity
        assert mock_track.call_count == 2
        mock_track.assert_any_call("EMAIL_ADDRESS", "en")
        mock_track.assert_any_call("PERSON", "en")


def test_analyze_with_metrics_with_kwargs() -> None:
    """Test analyze_with_metrics with additional keyword arguments."""
    mock_analyzer = Mock(spec=AnalyzerEngine)
    mock_analyzer.analyze.return_value = []

    with patch("presidio_fastapi.app.services.analyzer.track_pii_entity"):
        # Test with additional kwargs
        analyze_with_metrics(
            analyzer=mock_analyzer,
            text="Test text",
            language="es",
            entities=["EMAIL_ADDRESS", "PERSON"],
            score_threshold=0.6,
        )

        # Verify all arguments were passed to analyzer
        mock_analyzer.analyze.assert_called_once_with(
            text="Test text",
            language="es",
            entities=["EMAIL_ADDRESS", "PERSON"],
            score_threshold=0.6,
        )


def test_analyze_with_metrics_empty_results() -> None:
    """Test analyze_with_metrics when no entities are found."""
    mock_analyzer = Mock(spec=AnalyzerEngine)
    mock_analyzer.analyze.return_value = []

    with patch("presidio_fastapi.app.services.analyzer.track_pii_entity") as mock_track:
        results = analyze_with_metrics(
            analyzer=mock_analyzer, text="Clean text with no PII", language="en"
        )

        # Verify empty results
        assert results == []

        # Verify no metrics were tracked
        mock_track.assert_not_called()
