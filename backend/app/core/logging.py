"""Structured logging configuration for OIL SIF Sentinel."""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """Format log records as structured JSON."""

    STRUCTURED_FIELDS = (
        "component",
        "request_id",
        "method",
        "route",
        "status",
        "duration_ms",
        "batch_id",
        "report_id",
        "case_id",
        "review_id",
        "exception_category",
    )

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }

        for field in self.STRUCTURED_FIELDS:
            val = getattr(record, field, None)
            if val is not None:
                log_entry[field] = val

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_logging(log_level: str = "INFO", log_format: str = "JSON") -> None:
    """Configure root logger with chosen formatting."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    if log_format.upper() == "JSON":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root_logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Get named logger instance."""
    return logging.getLogger(name)
