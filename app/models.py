"""Data models for the Presidio FastAPI service.

This module contains all the Pydantic models used for request/response
validation and serialization.
"""
from pydantic import BaseModel, Field

from app.config import settings


class AnalyzeRequest(BaseModel):
    """Request model for text analysis.
    
    Attributes:
        text: The input text to analyze for PII entities.
        language: The language of the input text (ISO 639-1 code).
    """
    text: str = Field(
        ...,
        description="The text to analyze for PII",
        min_length=1,
        max_length=settings.MAX_TEXT_LENGTH,
    )
    language: str = Field(
        default="en",
        pattern="^[a-z]{2}$",
        description="Two-letter language code (ISO 639-1)",
    )


class BatchAnalyzeRequest(BaseModel):
    """Request model for batch text analysis.
    
    Allows analyzing multiple texts in a single request.
    
    Attributes:
        texts: A list of texts to analyze for PII entities.
        language: The language of the input texts (ISO 639-1 code).
    """
    texts: list[str] = Field(
        ...,
        description="List of texts to analyze for PII",
    )
    language: str = Field(
        default="en",
        pattern="^[a-z]{2}$",
        description="Two-letter language code (ISO 639-1)",
    )


class Entity(BaseModel):
    """Model representing a detected PII entity.
    
    Attributes:
        entity_type: The type of PII entity detected (e.g., PERSON, EMAIL).
        start: Starting character position of the entity in the text.
        end: Ending character position of the entity in the text.
        score: Confidence score of the detection (0.0 to 1.0).
        text: The actual text that was identified as a PII entity.
    """
    entity_type: str = Field(
        ...,
        description="Type of the detected entity",
    )
    start: int = Field(
        ...,
        description="Starting position of the entity in the text",
    )
    end: int = Field(
        ...,
        description="Ending position of the entity in the text",
    )
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score",
    )
    text: str = Field(
        ...,
        description="The actual text that was identified",
    )


class AnalyzeResponse(BaseModel):
    """Response model for text analysis.
    
    Attributes:
        entities: List of detected PII entities in the text.
        cached: Whether the result was retrieved from cache.
    """
    entities: list[Entity] = Field(
        ...,
        description="List of detected entities",
    )
    cached: bool = Field(
        default=False,
        description="Whether this result was from cache",
    )


class BatchAnalyzeResponse(BaseModel):
    """Response model for batch text analysis.
    
    Attributes:
        results: Analysis results for each text in the batch request.
    """
    results: list[AnalyzeResponse] = Field(
        ...,
        description="Analysis results for each text",
    )
