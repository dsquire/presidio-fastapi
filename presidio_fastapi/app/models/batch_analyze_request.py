"""Model for analyzing multiple texts in a single request."""

from pydantic import BaseModel, Field


class BatchAnalyzeRequest(BaseModel):
    texts: list[str] = Field(..., description="List of texts to analyze for PII")
    language: str = Field(
        default="en",
        pattern="^[a-z]{2}$",
        description="Two-letter language code (ISO 639-1)",
    )
