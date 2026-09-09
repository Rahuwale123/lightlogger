"""LightloggerHandler + capture_logging wiring (Phase 5)."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator

import pytest

import lightlogger
from lightlogger.handler import LightloggerHandler


@pytest.fixture(autouse=True)
def _clean_slate() -> Iterator[None]:
    root = logging.getLogger()
    original_level = root.level
    original_handlers = list(root.handlers)
    lightlogger._buffer.clear()
    yield
    lightlogger.stop()
    lightlogger._buffer.clear()
    # Belt-and-suspenders: remove anything a test attached directly to the
    # root logger (not through lightlogger.start()/stop()) and restore the
    # level exactly, so nothing leaks into test_buffer.py/test_server.py --
    # root logger state is global and shared across the whole pytest run.
    for handler in list(root.handlers):
        if handler not in original_handlers:
            root.removeHandler(handler)
    root.setLevel(original_level)


def test_plain_stdlib_logging_call_appears_in_the_buffer() -> None:
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)  # simulate an app that already lowered its level

    lightlogger.start()

    logging.getLogger().info("plain stdlib info")
    time.sleep(0.1)

    records = lightlogger._buffer.snapshot()
    matches = [r for r in records if r["message"] == "plain stdlib info"]
    assert len(matches) == 1
    record = matches[0]
    assert record["level"] == "info"
    assert record["logger_name"] == "root"
    assert record["file"] == __file__
    assert record["data"] is None


def test_third_party_style_logger_warning_appears_without_level_fiddling() -> None:
    lightlogger.start()

    logging.getLogger("some.third.party.lib").warning("disk almost full")
    time.sleep(0.1)

    records = lightlogger._buffer.snapshot()
    matches = [r for r in records if r["message"] == "disk almost full"]
    assert len(matches) == 1
    record = matches[0]
    assert record["level"] == "warn"
    assert record["logger_name"] == "some.third.party.lib"
    assert record["file"] == __file__


def test_start_stop_start_does_not_double_attach() -> None:
    root = logging.getLogger()

    def _lightlogger_handlers() -> list[logging.Handler]:
        return [h for h in root.handlers if isinstance(h, LightloggerHandler)]

    lightlogger.start()
    assert len(_lightlogger_handlers()) == 1

    lightlogger.stop()
    assert len(_lightlogger_handlers()) == 0

    lightlogger.start()
    assert len(_lightlogger_handlers()) == 1

    logging.getLogger("double.attach.check").warning("should appear exactly once")
    time.sleep(0.1)
    records = lightlogger._buffer.snapshot()
    matches = [r for r in records if r["message"] == "should appear exactly once"]
    assert len(matches) == 1
