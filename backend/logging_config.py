"""
Centralized Loguru configuration for AtmosMind.

- Development: colorized stderr
- Production (ENV=production): JSON lines on stdout for cloud log parsers

Standard-library ``logging`` calls are intercepted and routed through Loguru.
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Any

from loguru import logger

_CONFIGURED = False


class _InterceptHandler(logging.Handler):
    """Route stdlib logging records into Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame = logging.currentframe()
        depth = 2
        while frame is not None and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def is_production_env() -> bool:
    return os.getenv("ENV", "").strip().casefold() == "production"


def setup_logging() -> None:
    """Idempotent Loguru + stdlib logging bootstrap."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    logger.remove()

    if is_production_env():
        logger.add(
            sys.stdout,
            level=os.getenv("LOG_LEVEL", "INFO").upper(),
            serialize=True,
            backtrace=False,
            diagnose=False,
        )
    else:
        logger.add(
            sys.stderr,
            level=os.getenv("LOG_LEVEL", "DEBUG").upper(),
            colorize=True,
            backtrace=True,
            diagnose=False,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            ),
        )

    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)

    for noisy in ("uvicorn", "uvicorn.error", "uvicorn.access", "httpx", "httpcore"):
        logging.getLogger(noisy).handlers = [_InterceptHandler()]
        logging.getLogger(noisy).propagate = False

    _CONFIGURED = True
    logger.bind(
        event="logging_bootstrap",
        env="production" if is_production_env() else "development",
        json_logs=is_production_env(),
    ).info("Logging configured")


def _extract_status_code(exc: BaseException) -> int | None:
    response = getattr(exc, "response", None)
    if response is not None:
        code = getattr(response, "status_code", None)
        if isinstance(code, int):
            return code
    for attr in ("status_code", "code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    text = str(exc)
    if "429" in text:
        return 429
    if "503" in text:
        return 503
    return None


def log_outbound_api(
    service: str,
    *,
    success: bool,
    latency_ms: float | None = None,
    lat: float | None = None,
    lon: float | None = None,
    status_code: int | None = None,
    locations: int | None = None,
    error: str | None = None,
    **extra: Any,
) -> None:
    """Structured log for Open-Meteo / Air Quality outbound HTTP calls."""
    payload: dict[str, Any] = {
        "event": "outbound_api",
        "service": service,
        "success": success,
        "latency_ms": round(latency_ms, 2) if latency_ms is not None else None,
        "lat": lat,
        "lon": lon,
        "status_code": status_code,
        "locations": locations,
        **extra,
    }
    message = f"{service} {'ok' if success else 'failed'}"
    if error:
        message = f"{message}: {error}"

    bound = logger.bind(**{k: v for k, v in payload.items() if v is not None})
    if success:
        bound.info(message)
    else:
        bound.warning(message)


def log_gemini_error(operation: str, exc: BaseException, **extra: Any) -> None:
    """Structured log for Gemini / Google GenAI failures (incl. HTTP 429)."""
    status_code = _extract_status_code(exc)
    message = str(exc).casefold()
    rate_limited = status_code == 429 or "429" in message or "resource exhausted" in message
    connection_dropped = any(
        marker in message
        for marker in (
            "connection",
            "timeout",
            "unavailable",
            "deadline exceeded",
            "failed to connect",
        )
    )

    logger.bind(
        event="gemini_api",
        operation=operation,
        status_code=status_code,
        rate_limited=rate_limited,
        connection_dropped=connection_dropped,
        error_type=type(exc).__name__,
        **extra,
    ).error("Gemini API error: {}", exc)


def log_redis_event(
    event: str,
    *,
    component: str,
    fallback: str | None = None,
    error: str | None = None,
    level: str = "warning",
) -> None:
    """Structured log for Redis connectivity issues and degradation paths."""
    bound = logger.bind(
        event="redis",
        redis_event=event,
        component=component,
        fallback=fallback,
        error=error,
    )
    text = f"Redis {event} in {component}"
    if fallback:
        text = f"{text}; fallback={fallback}"
    if error:
        text = f"{text}: {error}"

    if level == "info":
        bound.info(text)
    elif level == "error":
        bound.error(text)
    else:
        bound.warning(text)
