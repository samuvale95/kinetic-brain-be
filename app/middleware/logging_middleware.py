import json
import time
import uuid
from typing import Any, Dict

from fastapi import Request
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


def _truncate(value: str, max_length: int = 500) -> str:
    if len(value) <= max_length:
        return value
    return f"{value[:max_length]}...<truncated>"


class RequestResponseLoggingMiddleware(BaseHTTPMiddleware):
    """Log every API request/response in a consistent way."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        start_time = time.perf_counter()

        # Read and cache request body, then rebuild Request with cached receive so downstream can read it
        body_bytes = await request.body()
        if body_bytes is not None:
            async def _receive():
                return {"type": "http.request", "body": body_bytes, "more_body": False}
            request = Request(request.scope, receive=_receive)
        body_text = ""
        if body_bytes:
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    parsed_body: Dict[str, Any] = json.loads(body_bytes)
                    body_text = json.dumps(parsed_body)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    body_text = body_bytes.decode("utf-8", errors="replace")
            else:
                body_text = body_bytes.decode("utf-8", errors="replace")

        log_context = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query": request.url.query or None,
            "client_ip": request.client.host if request.client else None,
            "content_type": request.headers.get("content-type"),
            "content_length": request.headers.get("content-length"),
        }
        if body_text:
            log_context["body"] = _truncate(body_text)

        logger.bind(**log_context).info("Incoming request")

        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            error_context = {
                **log_context,
                "duration_ms": round(duration_ms, 2),
                "user_id": getattr(request.state, "user_id", None),
                "user_email": getattr(request.state, "user_email", None),
            }
            logger.bind(**error_context).exception("Request raised unhandled exception")
            raise exc

        duration_ms = (time.perf_counter() - start_time) * 1000

        response_context = {
            **log_context,
            "duration_ms": round(duration_ms, 2),
            "status_code": response.status_code,
            "user_id": getattr(request.state, "user_id", None),
            "user_email": getattr(request.state, "user_email", None),
        }

        body_preview = getattr(response, "body", None)
        if isinstance(body_preview, (bytes, bytearray)):
            preview_text = body_preview.decode("utf-8", errors="replace")
            response_context["response_body"] = _truncate(preview_text)

        logger.bind(**response_context).info("Outgoing response")

        response.headers.setdefault("X-Request-ID", request_id)
        return response

