import logging
from functools import lru_cache

from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider

from app.config import settings

logger = logging.getLogger(__name__)

@lru_cache()
def get_analyzer() -> AnalyzerEngine:
    """
    Create and cache the Presidio analyzer engine with entity mapping configuration.
    
    Returns:
        AnalyzerEngine: Configured analyzer instance with entity mapping
        
    Raises:
        Exception: If analyzer creation fails
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
