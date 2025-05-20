"""Analyzer service for PII detection."""

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, List

from presidio_analyzer import AnalyzerEngine, AnalyzerEngineProvider, RecognizerResult

from presidio_fastapi.app.prometheus import track_pii_entity

logger = logging.getLogger(__name__)
# Set Presidio's logger to INFO level to suppress debug messages
logging.getLogger("presidio-analyzer").setLevel(logging.INFO)


@lru_cache()
def get_analyzer() -> AnalyzerEngine:
    """Creates and caches the Presidio analyzer engine using YAML configuration.

    Returns:
        AnalyzerEngine: An instance of presidio_analyzer.AnalyzerEngine
                        configured with settings from the YAML file.

    Raises:
        Exception: If the analyzer creation fails.
    """
    try:
        config_path = (
            Path(__file__).parent.parent.parent.parent / "config" / "recognizers.yaml"
        )
        logger.info("Loading analyzer configuration from %s", config_path)

        provider = AnalyzerEngineProvider(analyzer_engine_conf_file=str(config_path))
        analyzer = provider.create_engine()
        logger.info("Analyzer engine created successfully from configuration file")

        return analyzer
    except Exception as e:
        logger.error("Error creating analyzer: %s", str(e))
        logger.exception(e)
        raise


def analyze_with_metrics(
    analyzer: AnalyzerEngine,
    text: str,
    language: str,
    **kwargs: Any
) -> List[RecognizerResult]:
    """Analyzes text for PII and records metrics.
    
    Args:
        analyzer: The AnalyzerEngine instance
        text: The text to analyze
        language: The language code
        **kwargs: Additional arguments to pass to the analyzer
        
    Returns:
        List of RecognizerResult objects
    """
    results = analyzer.analyze(text=text, language=language, **kwargs)
    
    # Record metrics for each detected entity
    for result in results:
        track_pii_entity(result.entity_type, language)
        
    return results
