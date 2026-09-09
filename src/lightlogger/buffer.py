"""Ring buffer and SSE client fan-out."""

from __future__ import annotations

import sys
import threading
from collections import deque
from queue import Queue
from typing import Any, TypedDict


class LogRecord(TypedDict):
    time: float
    level: str
    message: str
    data: Any
    file: str
    line: int
    logger_name: str


def capture_caller(skip: int) -> tuple[str, int]:
    # sys._getframe, not inspect.stack(): inspect.stack() reads source files
    # off disk on every call, which is too slow for a logging hot path.
    frame = sys._getframe(skip)
    return frame.f_code.co_filename, frame.f_lineno


class LogBuffer:
    """Bounded ring buffer of log records, with SSE client fan-out."""

    def __init__(self, maxlen: int = 5000) -> None:
        self._records: deque[LogRecord] = deque(maxlen=maxlen)
        # One lock for records and subscribers alike: append() is atomic under
        # the GIL on its own, but the subscriber set isn't, so a single lock
        # keeps this simple rather than mixing locked and lock-free paths.
        self._lock = threading.Lock()
        self._subscribers: set[Queue[LogRecord]] = set()

    def add(self, record: LogRecord) -> None:
        with self._lock:
            self._records.append(record)
            subscribers = list(self._subscribers)
        for subscriber in subscribers:
            subscriber.put(record)

    def snapshot(self) -> list[LogRecord]:
        with self._lock:
            return list(self._records)

    def clear(self) -> None:
        with self._lock:
            self._records.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._records)

    def subscribe(self) -> Queue[LogRecord]:
        subscriber: Queue[LogRecord] = Queue()
        with self._lock:
            self._subscribers.add(subscriber)
        return subscriber

    def unsubscribe(self, subscriber: Queue[LogRecord]) -> None:
        with self._lock:
            self._subscribers.discard(subscriber)
