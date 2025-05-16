from typing import List, Optional
from pydantic import BaseModel, Field, conlist
from app.config import settings

class AnalyzeRequest(BaseModel):
    """Request model for text analysis."""
    text: str = Field(
        ...,
        description="The text to analyze for PII",
        min_length=1,
        max_length=settings.MAX_TEXT_LENGTH
    )
    language: str = Field(
        default="en",
        pattern="^[a-z]{2}$",
        description="Two-letter language code (ISO 639-1)"
    )

class BatchAnalyzeRequest(BaseModel):
    """Request model for batch text analysis."""
    texts: List[str] = Field(
        ...,
        description="List of texts to analyze for PII",
    )
    language: str = Field(
        default="en",
        pattern="^[a-z]{2}$",
        description="Two-letter language code (ISO 639-1)"
    )

class Entity(BaseModel):
    """Model representing a detected PII entity."""
    entity_type: str = Field(..., description="Type of the detected entity")
    start: int = Field(..., description="Starting position of the entity in the text")
    end: int = Field(..., description="Ending position of the entity in the text")
    score: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    text: str = Field(..., description="The actual text that was identified")

class AnalyzeResponse(BaseModel):
    """Response model for text analysis."""
    entities: List[Entity] = Field(..., description="List of detected entities")
    cached: bool = Field(default=False, description="Whether this result was from cache")

class BatchAnalyzeResponse(BaseModel):
    """Response model for batch text analysis."""
    results: List[AnalyzeResponse] = Field(..., description="Analysis results for each text")
