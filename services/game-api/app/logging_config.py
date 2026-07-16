from __future__ import annotations

import json
import logging
import sys
from typing import Any


class _JsonFormatter(logging.Formatter):
    """Structured JSON log formatter emitting time, level, logger, message, and exc_info."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "time": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            payload["exc_info"] = True
            payload["exception"] = self.formatException(record.exc_info)
        else:
            payload["exc_info"] = False
        return json.dumps(payload, default=str)


def configure_logging(*, level: int = logging.INFO) -> None:
    """Configure stdlib logging with a structured JSON formatter.

    Call once at application startup (e.g. top of ``lifespan``).
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)
