"""Analyzer service for PII detection."""

import logging
from functools import lru_cache
from pathlib import Path

from presidio_analyzer import AnalyzerEngine, AnalyzerEngineProvider

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
