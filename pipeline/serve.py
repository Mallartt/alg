"""Start the FastAPI server: `python serve.py` (or via uvicorn directly)."""

from __future__ import annotations

import argparse

import uvicorn

from src.api import build_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the recognition HTTP service.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    app = build_app()
    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
