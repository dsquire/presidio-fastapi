import logging
from functools import lru_cache
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from app.config import settings

logger = logging.getLogger(__name__)

@lru_cache()
def get_analyzer() -> AnalyzerEngine:
    """
    Create and cache the Presidio analyzer engine.
    
    Returns:
        AnalyzerEngine: Configured analyzer instance
    """
    try:
        logger.info("Creating NLP config...")
        nlp_config = {
            "nlp_engine_name": settings.NLP_ENGINE_NAME,
            "models": [{"lang_code": "en", "model_name": settings.SPACY_MODEL_EN}]
        }
        logger.info("NLP config created: %s", nlp_config)
        
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
