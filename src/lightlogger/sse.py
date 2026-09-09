"""SSE framing helpers: exact wire format for text/event-stream responses.

Kept separate from server.py so the wire format (double-newline framing,
retry directive, heartbeat comment) is defined in exactly one place and can
be unit-tested without spinning up a real HTTP server.
"""

from __future__ import annotations

import json

from lightlogger.buffer import LogRecord

RETRY_MS = 3000


def format_retry() -> bytes:
    return f"retry: {RETRY_MS}\n\n".encode()


def format_event(record: LogRecord) -> bytes:
    # default=str: log `data` can be any Python object the caller passed in.
    payload = json.dumps(record, default=str)
    return f"data: {payload}\n\n".encode()


def format_heartbeat() -> bytes:
    # A comment line (leading colon) per the SSE spec: browsers/proxies ignore
    # its content but the bytes on the wire keep the connection looking alive.
    return b": ping\n\n"
