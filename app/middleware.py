import logging
import time
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("app.request")


async def log_requests(request: Request, call_next):
    request_id = uuid.uuid4().hex
    request.state.request_id = request_id
    start = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.error(
            "request crashed",
            exc_info=True,
            extra=_fields(request, request_id, 500, latency_ms),
        )
        response = JSONResponse({"detail": "Internal server error"}, status_code=500)
    else:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        status_code = response.status_code
        level = (
            logging.ERROR if status_code >= 500
            else logging.WARNING if status_code >= 400
            else logging.INFO
        )
        logger.log(
            level,
            "request completed",
            extra=_fields(request, request_id, status_code, latency_ms),
        )

    response.headers["X-Request-ID"] = request_id
    return response


def _fields(request: Request, request_id: str, status_code: int, latency_ms: float) -> dict:
    return {
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status_code": status_code,
        "latency_ms": latency_ms,
        "user_id": getattr(request.state, "user_id", None),
        "user_role": getattr(request.state, "user_role", None),
    }