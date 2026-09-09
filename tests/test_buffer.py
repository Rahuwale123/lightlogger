"""Ring buffer, SSE fan-out, and the six public logging functions (Phase 1)."""

from __future__ import annotations

import sys
from queue import Empty

import pytest

import lightlogger
from lightlogger.buffer import LogBuffer, LogRecord, capture_caller


def make_record(message: str = "hello") -> LogRecord:
    return {
        "time": 0.0,
        "level": "info",
        "message": message,
        "data": None,
        "file": __file__,
        "line": 1,
        "logger_name": "test",
    }


class TestLogBuffer:
    def test_bounded_by_maxlen(self) -> None:
        buf = LogBuffer(maxlen=3)
        for i in range(5):
            buf.add(make_record(str(i)))
        assert len(buf) == 3
        assert [r["message"] for r in buf.snapshot()] == ["2", "3", "4"]

    def test_snapshot_is_a_copy(self) -> None:
        buf = LogBuffer(maxlen=10)
        buf.add(make_record())
        snap = buf.snapshot()
        snap.append(make_record("mutated"))
        assert len(buf) == 1

    def test_clear(self) -> None:
        buf = LogBuffer(maxlen=10)
        buf.add(make_record())
        buf.clear()
        assert len(buf) == 0
        assert buf.snapshot() == []

    def test_subscriber_receives_new_records(self) -> None:
        buf = LogBuffer(maxlen=10)
        sub = buf.subscribe()
        record = make_record("live")
        buf.add(record)
        assert sub.get_nowait() == record

    def test_multiple_subscribers_all_receive(self) -> None:
        buf = LogBuffer(maxlen=10)
        sub_a = buf.subscribe()
        sub_b = buf.subscribe()
        record = make_record("fanout")
        buf.add(record)
        assert sub_a.get_nowait() == record
        assert sub_b.get_nowait() == record

    def test_unsubscribe_stops_delivery(self) -> None:
        buf = LogBuffer(maxlen=10)
        sub = buf.subscribe()
        buf.unsubscribe(sub)
        buf.add(make_record())
        with pytest.raises(Empty):
            sub.get_nowait()

    def test_subscribing_does_not_replay_backlog(self) -> None:
        buf = LogBuffer(maxlen=10)
        buf.add(make_record("before"))
        sub = buf.subscribe()
        with pytest.raises(Empty):
            sub.get_nowait()

    def test_set_maxlen_truncates_to_the_most_recent_records(self) -> None:
        buf = LogBuffer(maxlen=10)
        for i in range(10):
            buf.add(make_record(str(i)))
        buf.set_maxlen(3)
        assert len(buf) == 3
        assert [r["message"] for r in buf.snapshot()] == ["7", "8", "9"]

    def test_set_maxlen_enforces_the_new_bound_on_future_appends(self) -> None:
        buf = LogBuffer(maxlen=10)
        buf.set_maxlen(2)
        for i in range(5):
            buf.add(make_record(str(i)))
        assert len(buf) == 2
        assert [r["message"] for r in buf.snapshot()] == ["3", "4"]

    def test_set_maxlen_growing_keeps_existing_records(self) -> None:
        buf = LogBuffer(maxlen=2)
        buf.add(make_record("a"))
        buf.add(make_record("b"))
        buf.set_maxlen(10)
        for i in range(5):
            buf.add(make_record(str(i)))
        assert [r["message"] for r in buf.snapshot()] == ["a", "b", "0", "1", "2", "3", "4"]


def test_capture_caller_returns_this_file_and_line() -> None:
    line_before = sys._getframe().f_lineno
    file, line = capture_caller(skip=1)
    assert file == __file__
    assert line == line_before + 1


class TestPublicLoggingFunctions:
    @pytest.fixture(autouse=True)
    def clear_global_buffer(self) -> None:
        lightlogger._buffer.clear()

    def test_debug_writes_a_debug_level_record(self) -> None:
        lightlogger.debug("checking cache")
        record = lightlogger._buffer.snapshot()[-1]
        assert record["level"] == "debug"
        assert record["message"] == "checking cache"
        assert record["data"] is None

    def test_info_captures_caller_file_and_line(self) -> None:
        line_before = sys._getframe().f_lineno
        lightlogger.info("user logged in")
        record = lightlogger._buffer.snapshot()[-1]
        assert record["level"] == "info"
        assert record["file"] == __file__
        assert record["line"] == line_before + 1

    def test_warn_writes_a_warn_level_record(self) -> None:
        lightlogger.warn("cache miss")
        record = lightlogger._buffer.snapshot()[-1]
        assert record["level"] == "warn"

    def test_error_carries_structured_data(self) -> None:
        lightlogger.error("payment failed", data={"order_id": 123})
        record = lightlogger._buffer.snapshot()[-1]
        assert record["level"] == "error"
        assert record["message"] == "payment failed"
        assert record["data"] == {"order_id": 123}

    def test_var_logs_name_as_message_and_value_as_data(self) -> None:
        cart = {"items": 3, "total": 49.99}
        lightlogger.var("cart", cart)
        record = lightlogger._buffer.snapshot()[-1]
        assert record["message"] == "cart"
        assert record["data"] == cart

    def test_request_builds_message_and_structured_data(self) -> None:
        lightlogger.request("GET", "/api/users", 200, 12.5)
        record = lightlogger._buffer.snapshot()[-1]
        assert record["message"] == "GET /api/users 200 12.5ms"
        assert record["data"] == {
            "method": "GET",
            "url": "/api/users",
            "status": 200,
            "duration_ms": 12.5,
        }

    def test_logging_is_append_only_across_calls(self) -> None:
        lightlogger.info("first")
        lightlogger.info("second")
        messages = [r["message"] for r in lightlogger._buffer.snapshot()]
        assert messages == ["first", "second"]
