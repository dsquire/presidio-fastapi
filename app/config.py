import logging
from functools import lru_cache
from typing import Any, Dict, List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Manages application settings using Pydantic BaseSettings.

    Settings are loaded from environment variables and a .env file.

    Attributes:
        API_VERSION (str): The version of the API.
        OTLP_ENDPOINT (str): The OTLP endpoint for OpenTelemetry.
        OTLP_SECURE (bool): Whether to use a secure connection for OTLP.
        REQUESTS_PER_MINUTE (int): Allowed requests per minute for rate limiting.
        BURST_LIMIT (int): Burst limit for rate limiting.
        BLOCK_DURATION (int): Duration in seconds to block IPs exceeding limits.
        LOG_LEVEL (str): The logging level for the application.
        NLP_ENGINE_NAME (str): The name of the NLP engine (e.g., "spacy").
        SPACY_MODEL_EN (str): The Spacy model for English.
        SPACY_MODEL_ES (Optional[str]): The optional Spacy model for Spanish.
        MAX_TEXT_LENGTH (int): Maximum allowed text length for analysis.
        ALLOWED_ORIGINS (str): Comma-separated string of allowed CORS origins.
        MIN_CONFIDENCE_SCORE (float): Minimum confidence score for PII detection.
        ENTITY_MAPPING (Dict[str, List[str]]): Mapping of Presidio entities.
    """
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
        """Parses and validates CORS origins from ALLOWED_ORIGINS.

        Returns:
            A list of validated origin strings. Returns an empty list if
            ALLOWED_ORIGINS is empty or "*", which FastAPI interprets
            appropriately for CORS configuration.
        """
        if not self.ALLOWED_ORIGINS:
            return []
        if self.ALLOWED_ORIGINS == "*":
            return []  # FastAPI interprets empty list as no origins allowed
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def nlp_configuration(self) -> Dict[str, Any]:
        """Constructs the NLP configuration for Presidio Analyzer.

        This configuration includes the NLP engine name and a list of models
        with their language codes, model names, and entity mappings.
        The Spanish model is included only if SPACY_MODEL_ES is configured.

        Returns:
            A dictionary containing the NLP configuration suitable for
            NlpEngineProvider.
        """
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
        """Converts the string log level from settings to a logging constant.

        Defaults to logging.INFO if the configured LOG_LEVEL is invalid.

        Returns:
            The integer value of the logging level (e.g., logging.INFO,
            logging.DEBUG).
        """
        return getattr(logging, self.LOG_LEVEL.upper(), logging.INFO)

    class Config:
        """Pydantic configuration class for Settings.

        Attributes:
            env_file (str): The name of the environment file to load (e.g., ".env").
            case_sensitive (bool): Whether environment variable names are case-sensitive.
        """
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """Creates and caches a Settings instance.

    Uses lru_cache to ensure that the Settings object is created only once,
    improving performance by avoiding repeated file reads and environment
    variable lookups.

    Returns:
        A cached instance of the Settings class.
    """
    return Settings()

settings = get_settings()
