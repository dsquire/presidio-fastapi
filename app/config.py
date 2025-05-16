from pydantic_settings import BaseSettings
from typing import List, Dict, Any, Optional
from functools import lru_cache
import logging

class Settings(BaseSettings):
    # API Version
    API_VERSION: str = "v1"
    
    # OpenTelemetry Configuration
    OTLP_ENDPOINT: str = "http://localhost:4317"
    OTLP_SECURE: bool = False
    
    # Rate Limiting Settings
    REQUESTS_PER_MINUTE: int = 60
    BURST_LIMIT: int = 100
    BLOCK_DURATION: int = 300
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    
    # NLP Configuration
    NLP_ENGINE_NAME: str = "spacy"
    SPACY_MODEL_EN: str = "en_core_web_lg"
    SPACY_MODEL_ES: Optional[str] = None  # Optional Spanish language model
    MAX_TEXT_LENGTH: int = 102400
    ALLOWED_ORIGINS: str = ""
    MIN_CONFIDENCE_SCORE: float = 0.5

    # Entity Mapping Configuration
    ENTITY_MAPPING: Dict[str, List[str]] = {
        "PERSON": ["PERSON", "PER"],
        "EMAIL_ADDRESS": ["EMAIL"],
        "PHONE_NUMBER": ["PHONE", "PHONE_NUMBER"],
        "CREDIT_CARD": ["CREDIT_CARD", "CC"],
        "DATE_TIME": ["DATE", "TIME", "DATETIME"],
        "ADDRESS": ["LOC", "GPE", "LOCATION"],
        "US_SSN": ["SSN"],
        "IP_ADDRESS": ["IP"],
        "US_DRIVER_LICENSE": ["DRIVER_LICENSE", "DL"],
        "URL": ["URL", "URI"]
    }
    
    @property
    def cors_origins(self) -> List[str]:
        """Parse and validate CORS origins."""
        if not self.ALLOWED_ORIGINS:
            return []
        if self.ALLOWED_ORIGINS == "*":
            return []  # FastAPI interprets empty list as no origins allowed
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def nlp_configuration(self) -> Dict[str, Any]:
        """Get NLP configuration with entity mapping."""
        models = [
            {
                "lang_code": "en",
                "model_name": self.SPACY_MODEL_EN,
                "model_to_presidio_entity_mapping": self.ENTITY_MAPPING
            }
        ]
        
        # Add Spanish model if configured
        if self.SPACY_MODEL_ES:
            models.append({
                "lang_code": "es",
                "model_name": self.SPACY_MODEL_ES,
                "model_to_presidio_entity_mapping": self.ENTITY_MAPPING
            })
        
        return {
            "nlp_engine_name": self.NLP_ENGINE_NAME,
            "models": models
        }
    
    @property
    def log_level(self) -> int:
        """Convert string log level to logging constant."""
        return getattr(logging, self.LOG_LEVEL.upper(), logging.INFO)

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """Create cached settings instance."""
    return Settings()

settings = get_settings()
