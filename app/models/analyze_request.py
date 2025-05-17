"""Model for analyzing a single text for PII entities."""

from pydantic import BaseModel, Field

from app.config import settings


class AnalyzeRequest(BaseModel):
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
