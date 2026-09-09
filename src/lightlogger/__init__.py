"""lightlogger: a live web dashboard for your Python logs. Zero dependencies."""

from __future__ import annotations

import time
from typing import Any

from lightlogger.buffer import LogBuffer, LogRecord, capture_caller

__version__ = "0.1.0"

__all__ = [
    "start",
    "stop",
    "debug",
    "info",
    "warn",
    "error",
    "var",
    "request",
]

_buffer = LogBuffer(maxlen=5000)


def _emit(level: str, message: str, data: Any = None, *, logger_name: str = "lightlogger") -> None:
    # skip=3: capture_caller's own frame, this frame, and the public
    # debug/info/warn/error/var/request wrapper -> lands on the user's call site.
    file, line = capture_caller(skip=3)
    record: LogRecord = {
        "time": time.time(),
        "level": level,
        "message": message,
        "data": data,
        "file": file,
        "line": line,
        "logger_name": logger_name,
    }
    _buffer.add(record)


def start(
    port: int = 4356,
    host: str = "127.0.0.1",
    max_logs: int = 5000,
    capture_logging: bool = True,
    open_browser: bool = False,
) -> None:
    raise NotImplementedError  # implemented in Phase 2


def stop() -> None:
    raise NotImplementedError  # implemented in Phase 2


def debug(msg: str, data: Any | None = None) -> None:
    _emit("debug", msg, data)


def info(msg: str, data: Any | None = None) -> None:
    _emit("info", msg, data)


def warn(msg: str, data: Any | None = None) -> None:
    _emit("warn", msg, data)


def error(msg: str, data: Any | None = None) -> None:
    _emit("error", msg, data)


def var(name: str, value: Any) -> None:
    _emit("info", name, value)


def request(method: str, url: str, status: int, duration_ms: float) -> None:
    _emit(
        "info",
        f"{method} {url} {status} {duration_ms:.1f}ms",
        {"method": method, "url": url, "status": status, "duration_ms": duration_ms},
    )
