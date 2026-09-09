"""lightlogger: a live web dashboard for your Python logs. Zero dependencies."""

from __future__ import annotations

import logging
import threading
import time
import uuid
import webbrowser
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from lightlogger.buffer import LogBuffer, LogRecord, _current_group_id, capture_caller
from lightlogger.handler import LightloggerHandler
from lightlogger.server import LightloggerServer, create_server, serve_in_background

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
    "group",
]

_buffer = LogBuffer(maxlen=5000)
_httpd: LightloggerServer | None = None
_thread: threading.Thread | None = None
_logging_handler: LightloggerHandler | None = None


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
        "group_id": None,
        "parent_group_id": _current_group_id.get(),
    }
    _buffer.add(record)


def start(
    port: int = 4356,
    host: str = "127.0.0.1",
    max_logs: int = 5000,
    capture_logging: bool = True,
    open_browser: bool = False,
) -> None:
    global _httpd, _thread, _logging_handler
    if _httpd is not None:
        return  # already running; start() is idempotent, not an error

    _buffer.set_maxlen(max_logs)

    if host == "0.0.0.0":  # noqa: S104
        print(
            "lightlogger WARNING: binding to 0.0.0.0 exposes your logs to your "
            "whole network. Only do this if you mean it."
        )

    _httpd = create_server(_buffer, host, port)
    _thread = serve_in_background(_httpd)
    bound_port = _httpd.server_address[1]
    print(f"lightlogger UI → http://{host}:{bound_port}")

    if open_browser:
        webbrowser.open(f"http://{host}:{bound_port}")

    if capture_logging:
        _logging_handler = LightloggerHandler(_buffer)
        logging.getLogger().addHandler(_logging_handler)


def stop() -> None:
    global _httpd, _thread, _logging_handler
    if _logging_handler is not None:
        logging.getLogger().removeHandler(_logging_handler)
        _logging_handler = None
    if _httpd is None:
        return
    _httpd.shutdown()
    _httpd.server_close()
    _httpd = None
    _thread = None


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


@contextmanager
def group(name: str) -> Iterator[None]:
    group_id = uuid.uuid4().hex
    parent_group_id = _current_group_id.get()
    # skip=3: capture_caller's own frame, this generator's frame (resumed by
    # @contextmanager's __enter__ via next()), and contextlib's
    # _GeneratorContextManager.__enter__ itself -> lands on the user's
    # `with lightlogger.group(...):` call site. Verified empirically in
    # tests/test_buffer.py (test_group_captures_caller_file_and_line).
    file, line = capture_caller(skip=3)
    record: LogRecord = {
        "time": time.time(),
        "level": "group",
        "message": name,
        "data": None,
        "file": file,
        "line": line,
        "logger_name": "lightlogger",
        "group_id": group_id,
        "parent_group_id": parent_group_id,
    }
    _buffer.add(record)
    token = _current_group_id.set(group_id)
    try:
        yield
    finally:
        _current_group_id.reset(token)
