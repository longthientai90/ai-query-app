from __future__ import annotations

import hashlib
import logging

import structlog

_configured = False


def setup_logging(level: str = "INFO") -> None:
    global _configured
    if _configured:
        return

    # Emit one JSON log line per event for easier ingestion by log collectors.
    logging.basicConfig(level=level.upper(), format="%(message)s")
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    _configured = True


def get_logger(name: str):
    return structlog.get_logger(name)


def sql_hash(sql: str) -> str:
    # Use short hash for correlation without exposing raw SQL text.
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()[:12]
