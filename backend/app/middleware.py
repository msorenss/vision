"""Logging middleware for structured request/response logging."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("vision.api")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Add request-id and log request/response with latency."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Any],
    ) -> Response:
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        start = time.perf_counter()
        response: Response = await call_next(request)
        latency_ms = (time.perf_counter() - start) * 1000

        # Skip noisy paths
        path = request.url.path
        if path in {"/favicon.ico", "/health"}:
            response.headers["X-Request-ID"] = request_id
            return response

        logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": path,
                "status": response.status_code,
                "latency_ms": round(latency_ms, 2),
            },
        )

        response.headers["X-Request-ID"] = request_id
        return response
