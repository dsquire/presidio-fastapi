from functools import lru_cache
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from app.config import settings

@lru_cache()
def get_analyzer() -> AnalyzerEngine:
    """
    Create and cache the Presidio analyzer engine.
    
    Returns:
        AnalyzerEngine: Configured analyzer instance
    """
    nlp_config = {
        "nlp_engine_name": settings.NLP_ENGINE_NAME,
        "models": [{"lang_code": "en", "model_name": settings.SPACY_MODEL_EN}]
    }
    nlp_engine = NlpEngineProvider(nlp_configuration=nlp_config).create_engine()
    return AnalyzerEngine(nlp_engine=nlp_engine)
