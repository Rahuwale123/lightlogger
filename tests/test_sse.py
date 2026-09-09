"""SSE wire-format helpers, unit-tested directly (see sse.py's own docstring:
these are deliberately separable from a real HTTP server).
"""

from __future__ import annotations

import json

from lightlogger import sse
from lightlogger.buffer import LogRecord


def make_record(**overrides: object) -> LogRecord:
    record: LogRecord = {
        "time": 0.0,
        "level": "info",
        "message": "hello",
        "data": None,
        "file": __file__,
        "line": 1,
        "logger_name": "test",
        "group_id": None,
        "parent_group_id": None,
    }
    record.update(overrides)  # type: ignore[typeddict-item]
    return record


def test_format_retry_is_a_double_newline_frame() -> None:
    assert sse.format_retry() == b"retry: 3000\n\n"


def test_format_heartbeat_is_a_comment_line() -> None:
    assert sse.format_heartbeat() == b": ping\n\n"


def test_format_event_frames_the_record_as_a_data_line() -> None:
    record = make_record(message="streamed")
    payload = sse.format_event(record)
    assert payload.startswith(b"data: ")
    assert payload.endswith(b"\n\n")
    assert json.loads(payload[len(b"data: ") : -2]) == record


class NotJSONSerializable:
    """No __str__ of its own: object.__str__ falls back to __repr__, which
    is exactly what json.dumps(..., default=str) ends up calling."""

    def __repr__(self) -> str:
        return "<NotJSONSerializable sentinel>"


def test_format_event_serializes_arbitrary_objects_via_default_str() -> None:
    # `data` is caller-controlled and can be any Python object (see CLAUDE.md
    # section 5: serialization "works without crashing" for any object).
    # Sets and plain class instances are both realistic examples that are
    # NOT directly JSON-serializable, so this only passes if default=str's
    # fallback is actually exercised, not just present in the source line.
    record = make_record(data={"seen_ids": {1, 2, 3}, "obj": NotJSONSerializable()})
    payload = sse.format_event(record)  # must not raise
    decoded = json.loads(payload[len(b"data: ") : -2])
    assert "NotJSONSerializable sentinel" in decoded["data"]["obj"]
    assert isinstance(decoded["data"]["seen_ids"], str)  # a set has no JSON list form
