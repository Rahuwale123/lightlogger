"""lightlogger: a live web dashboard for your Python logs. Zero dependencies."""

from __future__ import annotations

from typing import Any

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
    raise NotImplementedError  # implemented in Phase 1


def info(msg: str, data: Any | None = None) -> None:
    raise NotImplementedError  # implemented in Phase 1


def warn(msg: str, data: Any | None = None) -> None:
    raise NotImplementedError  # implemented in Phase 1


def error(msg: str, data: Any | None = None) -> None:
    raise NotImplementedError  # implemented in Phase 1


def var(name: str, value: Any) -> None:
    raise NotImplementedError  # implemented in Phase 1


def request(method: str, url: str, status: int, duration_ms: float) -> None:
    raise NotImplementedError  # implemented in Phase 1
