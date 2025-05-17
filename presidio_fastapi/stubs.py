"""Stubs for external dependencies."""

from pydantic import BaseModel
from pydantic_settings import BaseSettings
from starlette.middleware.base import BaseHTTPMiddleware

__all__ = ["BaseModel", "BaseSettings", "BaseHTTPMiddleware"]
