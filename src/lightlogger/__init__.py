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

__version__ = "0.1.1"

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
    "help",
]

_HELP_TEXT = """\
lightlogger -- live web dashboard for your Python logs
========================================================

  pip install lightlogger

Quickstart
----------
  import lightlogger
  lightlogger.start()

That's it. Open the printed URL (default http://127.0.0.1:4356) and watch
your logs stream in live, in a dark, searchable dashboard.

Public API
----------

  start(port=4356, host="127.0.0.1", max_logs=5000,
        capture_logging=True, open_browser=False)
      Starts the dashboard server on a background thread. Calling it again
      while already running is a no-op, not an error.
          lightlogger.start(port=8080, open_browser=True)

  stop()
      Stops the server and detaches the logging handler. Mostly useful for
      tests and notebooks -- most scripts never need to call this.
          lightlogger.stop()

  debug(msg, data=None)
      Logs a debug-level message (grey in the UI).
          lightlogger.debug("cache miss", data={"key": "user:42"})

  info(msg, data=None)
      Logs an info-level message (blue in the UI).
          lightlogger.info("user logged in")

  warn(msg, data=None)
      Logs a warn-level message (yellow in the UI).
          lightlogger.warn("retrying after timeout")

  error(msg, data=None)
      Logs an error-level message (red in the UI).
          lightlogger.error("payment failed", data={"order_id": 123})

  var(name, value)
      Logs any variable as an expandable JSON blob under `name`.
          lightlogger.var("cart", cart_dict)

  request(method, url, status, duration_ms)
      Logs one HTTP request/response as a single formatted line. Level
      follows the status code: <400 info, 4xx warn, 5xx error.
          lightlogger.request("GET", "/api/users", 200, 12.4)
          lightlogger.request("POST", "/api/orders", 500, 812.0)  # -> error

  group(name)
      Context manager that groups related log lines into a collapsible
      tree in the UI. Nests, and is safe across threads and asyncio tasks
      (each gets its own independent group context).
          with lightlogger.group("process_order #4821"):
              lightlogger.info("validating cart")
              lightlogger.info("charging payment", data={"amount": 49.99})
              with lightlogger.group("send_notifications"):
                  lightlogger.info("email sent")

Capturing stdlib `logging`
---------------------------
start(capture_logging=True) is the default: it attaches a handler to the
root logger, so your existing `logging` calls -- and third-party
libraries' -- appear in the dashboard automatically, with zero code
changes.

Gotcha: Python's root logger defaults to level WARNING. A plain
`logging.info(...)` call will NOT appear unless your app has already
raised the level itself, e.g. `logging.basicConfig(level=logging.INFO)`.
lightlogger deliberately never forces the root logger's level open --
doing so would also unmute your app's OTHER existing handlers, which is
more disruptive than "zero code changes" is meant to be. `.warning()` and
above always show up out of the box; `.debug()`/`.info()` need that one
extra line if you want them too.

Not for production
-------------------
Binds to 127.0.0.1 only by default. This is a local development tool, not
a production observability system.

Docs & source
-------------
  https://github.com/Rahuwale123/lightlogger
"""

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
    if status >= 500:
        level = "error"
    elif status >= 400:
        level = "warn"
    else:
        level = "info"
    _emit(
        level,
        f"{method} {url} {status} {duration_ms:.1f}ms",
        {"method": method, "url": url, "status": status, "duration_ms": duration_ms},
    )


def help() -> None:
    """Print a quick-reference cheatsheet of the public API to stdout."""
    print(_HELP_TEXT)


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
