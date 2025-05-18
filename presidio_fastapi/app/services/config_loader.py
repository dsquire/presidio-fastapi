"""Configuration loader for custom recognizers."""

import logging
import os
from pathlib import Path
from typing import Any, Dict

import yaml  # type: ignore[import-untyped]
from presidio_analyzer import Pattern, PatternRecognizer

logger = logging.getLogger(__name__)


def load_recognizer_config(
    config_path: str | Path | None = None,
) -> list[PatternRecognizer]:
    """Load recognizer configurations from YAML file.

    Args:
        config_path: Path to the YAML configuration file.
            If None, looks for 'config/recognizers.yaml' in the project root.

    Returns:
        List of configured PatternRecognizer instances.

    Raises:
        FileNotFoundError: If the configuration file cannot be found.
        ValueError: If the configuration is invalid.
    """
    if config_path is None:
        # Try to find config relative to the project root
        project_root = Path(__file__).parent.parent.parent.parent
        config_path = project_root / "config" / "recognizers.yaml"

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Recognizer configuration not found at {config_path}")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        recognizers = []
        defaults = config.get("defaults", {})

        for rec_config in config.get("recognizers", []):
            patterns = [
                Pattern(
                    name=p["name"],
                    regex=p["regex"],
                    score=p.get("score", defaults.get("min_score", 0.5)),
                )
                for p in rec_config.get("patterns", [])
            ]

            recognizer = PatternRecognizer(
                supported_entity=rec_config["supported_entity"],
                patterns=patterns,
                context=rec_config.get("context", []),
                supported_language=rec_config.get("supported_language", "en"),
            )

            recognizers.append(recognizer)
            logger.info(
                "Loaded recognizer %s for entity %s",
                rec_config["name"],
                rec_config["supported_entity"],
            )

        return recognizers

    except Exception as e:
        logger.error("Error loading recognizer configuration: %s", str(e))
        raise ValueError(f"Invalid recognizer configuration: {str(e)}") from e


def get_context_settings(config_path: str | Path | None = None) -> Dict[str, Any]:
    """Load global context settings from the configuration.

    Args:
        config_path: Path to the YAML configuration file.
            If None, looks for 'config/recognizers.yaml' in the project root.

    Returns:
        Dictionary containing context settings.
    """
    if config_path is None:
        project_root = Path(__file__).parent.parent.parent.parent
        config_path = project_root / "config" / "recognizers.yaml"

    if not os.path.exists(config_path):
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        return config.get("defaults", {}).get("context", {})
    except Exception as e:
        logger.error("Error loading context settings: %s", str(e))
        return {}
