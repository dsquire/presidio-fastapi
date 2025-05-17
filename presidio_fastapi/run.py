#!/usr/bin/env python
"""Entry point for running the presidio-fastapi application."""

import uvicorn

from presidio_fastapi.app.config import settings


def main() -> None:
    """Run the application using uvicorn server."""
    uvicorn.run(
        "presidio_fastapi.app.main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        log_level=settings.LOG_LEVEL.lower(),
        reload=True,
    )


if __name__ == "__main__":
    main()
