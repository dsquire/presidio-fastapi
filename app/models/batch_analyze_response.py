"""Response model for batch text analysis."""

from pydantic import BaseModel, Field

from .analyze_response import AnalyzeResponse


class BatchAnalyzeResponse(BaseModel):
    results: list[AnalyzeResponse] = Field(
        ..., description="Analysis results for each text"
    )
