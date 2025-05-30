"""Tests for configuration module targeting specific missing coverage lines."""

import logging

from presidio_fastapi.app.config import Settings, get_settings


def test_cors_origins_empty_filter():
    """Test cors_origins filters empty strings (line 118)."""
    settings = Settings(ALLOWED_ORIGINS=" , , ")
    # This tests line 118: if origin.strip() - filtering empty strings
    assert settings.cors_origins == []


def test_nlp_configuration_comment_stripping_en():
    """Test nlp_configuration strips comments from EN model (line 147)."""
    settings = Settings(SPACY_MODEL_EN="en_core_web_lg  # comment")
    config = settings.nlp_configuration
    # Tests line 147: self.SPACY_MODEL_EN.split("#")[0].strip()
    assert config["models"][0]["model_name"] == "en_core_web_lg"


def test_nlp_configuration_comment_stripping_es():
    """Test nlp_configuration strips comments from ES model (line 150)."""
    settings = Settings(
        SPACY_MODEL_EN="en_core_web_lg", SPACY_MODEL_ES="es_core_news_sm  # comment"
    )
    config = settings.nlp_configuration
    # Tests line 150: spanish_model_name = self.SPACY_MODEL_ES.split("#")[0].strip()
    assert config["models"][1]["model_name"] == "es_core_news_sm"


def test_nlp_configuration_empty_spanish_after_stripping():
    """Test Spanish model empty after comment stripping (line 151)."""
    settings = Settings(SPACY_MODEL_EN="en_core_web_lg", SPACY_MODEL_ES="  # Only comment")
    config = settings.nlp_configuration
    # Tests line 151: if spanish_model_name: (ensuring empty string filtered)
    assert len(config["models"]) == 1
    assert config["models"][0]["lang_code"] == "en"


def test_log_level_invalid_fallback():
    """Test log_level with invalid level defaults to INFO (line 170)."""
    settings = Settings(LOG_LEVEL="INVALID_LEVEL")
    # Tests line 170: getattr(logging, self.LOG_LEVEL.upper(), logging.INFO)
    assert settings.log_level == logging.INFO


def test_strip_inline_comments_validator():
    """Test _strip_inline_comments validator processing (lines 106-108)."""
    settings = Settings(
        SPACY_MODEL_EN="en_core_web_lg  # comment", LOG_LEVEL="DEBUG  # debug comment"
    )
    # Tests lines 106-108: validator processing string values
    assert settings.SPACY_MODEL_EN == "en_core_web_lg"
    assert settings.LOG_LEVEL == "DEBUG"


def test_get_settings_function():
    """Test get_settings function."""
    settings = get_settings()
    assert isinstance(settings, Settings)
    assert settings.API_VERSION == "v1"
