"""Re-export the FastAPI app for `uvicorn pipeline.src.api:app`."""

from .server import build_app

app = build_app()

__all__ = ["app", "build_app"]
