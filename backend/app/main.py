import asyncio
import logging
import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.bootstrap import bootstrap_model_if_needed
from app.api.routes import router
from app.middleware import RequestLoggingMiddleware
from app.watcher import load_watch_config, run_watch_loop


def _configure_logging() -> None:
    """Configure structured JSON logging."""
    level = os.getenv("VISION_LOG_LEVEL", "INFO").upper()
    
    # Simple structured format
    fmt = "%(asctime)s %(levelname)s %(name)s %(message)s"
    if os.getenv("VISION_LOG_JSON", "0") in {"1", "true"}:
        fmt = '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}'
    
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format=fmt,
        stream=sys.stdout,
    )


def _try_register_heif() -> None:
    try:
        from pillow_heif import register_heif_opener

        register_heif_opener()
    except Exception:
        # Optional dependency; ignore if missing or not supported in runtime.
        return


def create_app() -> FastAPI:
    _configure_logging()
    
    app = FastAPI(
        title="Vision Runner API",
        version="0.1.0",
    )

    _try_register_heif()

    # Logging middleware (innermost, runs first)
    app.add_middleware(RequestLoggingMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    @app.on_event("startup")
    async def _startup() -> None:
        # Run in background so the API can come up quickly.
        asyncio.get_running_loop().run_in_executor(
            None,
            bootstrap_model_if_needed,
        )

        # Optional: Pi-style folder watching.
        if load_watch_config().enabled:
            asyncio.create_task(run_watch_loop())

    return app


app = create_app()
