"""Model representing a detected PII entity."""

from pydantic import BaseModel, Field


class Entity(BaseModel):
    entity_type: str = Field(..., description="Type of the detected entity")
    start: int = Field(..., description="Starting position of the entity in the text")
    end: int = Field(..., description="Ending position of the entity in the text")
    score: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    text: str = Field(..., description="The actual text that was identified")
