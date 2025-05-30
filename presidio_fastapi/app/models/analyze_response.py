"""Response model for text analysis."""

from pydantic import BaseModel, Field

from .entity import Entity


class AnalyzeResponse(BaseModel):
    entities: list[Entity] = Field(..., description="List of detected entities")
    cached: bool = Field(default=False, description="Whether this result was from cache")
