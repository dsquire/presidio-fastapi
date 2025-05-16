import logging
from functools import lru_cache

from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider

from app.config import settings

logger = logging.getLogger(__name__)


@lru_cache()
def get_analyzer() -> AnalyzerEngine:
    """Creates and caches the Presidio analyzer engine.

    The engine is configured with entity mapping from the application settings.
    Uses lru_cache to ensure the engine is created only once.

    Returns:
        AnalyzerEngine: An instance of presidio_analyzer.AnalyzerEngine 
                        configured with NLP engine and entity mappings.

    Raises:
        Exception: If the analyzer or NLP engine creation fails.
    """
    try:
        logger.info("Creating NLP config with entity mapping...")
        nlp_config = settings.nlp_configuration
        logger.debug("NLP config: %s", nlp_config)

        logger.info("Creating NLP engine...")
        nlp_engine = NlpEngineProvider(nlp_configuration=nlp_config).create_engine()
        logger.info("NLP engine created successfully")

        logger.info("Creating Analyzer engine...")
        analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
        logger.info("Analyzer engine created successfully")

        return analyzer
    except Exception as e:
        logger.error("Error creating analyzer: %s", str(e))
        logger.exception(e)
        raise
