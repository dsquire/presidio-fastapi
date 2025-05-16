from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache

class Settings(BaseSettings):
    NLP_ENGINE_NAME: str = "spacy"
    SPACY_MODEL_EN: str = "en_core_web_lg"
    MAX_TEXT_LENGTH: int = 102400
    ALLOWED_ORIGINS: str = ""
    MIN_CONFIDENCE_SCORE: float = 0.5
    
    @property
    def cors_origins(self) -> List[str]:
        """Parse and validate CORS origins."""
        if not self.ALLOWED_ORIGINS:
            return []
        if self.ALLOWED_ORIGINS == "*":
            return []  # FastAPI interprets empty list as no origins allowed
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """Create cached settings instance."""
    return Settings()

settings = get_settings()
