"""LightloggerHandler: logging.Handler subclass for capture_logging."""

from __future__ import annotations

import logging

from lightlogger.buffer import LogBuffer, LogRecord

_LEVEL_NAMES = {
    logging.DEBUG: "debug",
    logging.INFO: "info",
    logging.WARNING: "warn",
    logging.ERROR: "error",
    logging.CRITICAL: "error",  # only 4 UI colors exist; CRITICAL folds into "error"
}


class LightloggerHandler(logging.Handler):
    """Mirrors stdlib `logging` records into a `LogBuffer` (and its SSE fan-out)."""

    def __init__(self, buffer: LogBuffer) -> None:
        super().__init__()
        self._buffer = buffer

    def emit(self, record: logging.LogRecord) -> None:
        try:
            log_record: LogRecord = {
                "time": record.created,
                "level": _LEVEL_NAMES.get(record.levelno, "info"),
                "message": record.getMessage(),
                "data": None,
                "file": record.pathname,
                "line": record.lineno,
                "logger_name": record.name,
            }
            self._buffer.add(log_record)
        except Exception:
            self.handleError(record)
