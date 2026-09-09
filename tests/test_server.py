"""Real server tests (Phase 2/4): start a real ThreadingHTTPServer, hit it
over HTTP with urllib (including the raw SSE wire protocol on /api/stream),
and confirm stop()/start() cycles cleanly.
"""

from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from http.client import HTTPResponse

import pytest

import lightlogger
from lightlogger.buffer import LogBuffer
from lightlogger.server import create_server, serve_in_background


@pytest.fixture(autouse=True)
def _clean_slate() -> Iterator[None]:
    lightlogger._buffer.clear()
    yield
    lightlogger.stop()
    lightlogger._buffer.clear()
    # A test that opens /api/stream and closes the client side without
    # waiting leaves its server-side thread blocked in subscriber.get() until
    # its own heartbeat timeout notices the broken pipe -- previously masked
    # by the old heartbeat test's real 15s sleep giving those stragglers time
    # to time out on their own. Force the subscriber set empty between tests
    # so a still-lingering entry from one test can never pollute the next
    # test's subscriber-count assertions (the lock matches how buffer.py
    # guards this same set elsewhere).
    with lightlogger._buffer._lock:
        lightlogger._buffer._subscribers.clear()


def _url(port: int, path: str) -> str:
    return f"http://127.0.0.1:{port}{path}"


def _get(port: int, path: str) -> tuple[int, bytes]:
    with urllib.request.urlopen(_url(port, path)) as resp:
        return resp.status, resp.read()


def _bound_port() -> int:
    httpd = lightlogger._httpd
    assert httpd is not None
    return int(httpd.server_address[1])


def _open_stream(port: int, timeout: float = 5.0) -> HTTPResponse:
    # A bounded socket timeout on every SSE connection a test opens: /api/stream
    # is a genuinely long-lived response, and without this a bug that stops
    # the server writing would hang the read (and the whole test run) forever
    # instead of failing loudly.
    resp = urllib.request.urlopen(_url(port, "/api/stream"), timeout=timeout)
    assert isinstance(resp, HTTPResponse)
    return resp


def test_start_prints_url_and_binds_default_port() -> None:
    lightlogger.start()
    assert _bound_port() == 4356


def test_api_logs_returns_json_backlog() -> None:
    lightlogger.start()
    lightlogger.info("hello from a test", data={"n": 1})
    status, body = _get(_bound_port(), "/api/logs")
    assert status == 200
    records = json.loads(body)
    assert any(r["message"] == "hello from a test" and r["data"] == {"n": 1} for r in records)


def test_index_route_serves_html() -> None:
    lightlogger.start()
    status, body = _get(_bound_port(), "/")
    assert status == 200
    assert b"lightlogger" in body


def test_unknown_route_is_404() -> None:
    lightlogger.start()
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(_url(_bound_port(), "/nope"))
    assert exc_info.value.code == 404


def test_stop_frees_the_port_and_start_works_again() -> None:
    lightlogger.start()
    port = _bound_port()
    lightlogger.stop()

    # If shutdown() + server_close() didn't actually release the socket, this
    # bind would fail with "address already in use".
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    probe.bind(("127.0.0.1", port))
    probe.close()

    lightlogger.start(port=port)
    assert _bound_port() == port
    status, _ = _get(port, "/api/logs")
    assert status == 200


def test_port_auto_increments_when_default_port_is_busy() -> None:
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blocker.bind(("127.0.0.1", 0))
    busy_port = blocker.getsockname()[1]
    blocker.listen(1)
    try:
        lightlogger.start(port=busy_port)
        assert _bound_port() == busy_port + 1
        status, _ = _get(_bound_port(), "/api/logs")
        assert status == 200
    finally:
        blocker.close()


def test_start_is_idempotent_while_already_running() -> None:
    lightlogger.start()
    first_port = _bound_port()
    lightlogger.start(port=first_port + 50)  # should be a no-op, not rebind
    assert _bound_port() == first_port


def test_max_logs_is_applied_to_the_buffer_end_to_end() -> None:
    lightlogger.start(max_logs=100)
    for i in range(500):
        lightlogger.info(f"log {i}")
    status, body = _get(_bound_port(), "/api/logs")
    assert status == 200
    records = json.loads(body)
    assert len(records) == 100
    assert records[0]["message"] == "log 400"
    assert records[-1]["message"] == "log 499"


class TestApiStream:
    def test_sets_sse_headers(self) -> None:
        lightlogger.start()
        resp = _open_stream(_bound_port())
        try:
            assert resp.headers["Content-Type"] == "text/event-stream"
            assert resp.headers["Cache-Control"] == "no-cache"
        finally:
            resp.close()

    def test_sends_retry_directive_first_as_a_double_newline_frame(self) -> None:
        lightlogger.start()
        resp = _open_stream(_bound_port())
        try:
            assert resp.readline() == b"retry: 3000\n"
            assert resp.readline() == b"\n"
        finally:
            resp.close()

    def test_emits_a_new_log_record_as_a_data_frame(self) -> None:
        lightlogger.start()
        resp = _open_stream(_bound_port())
        try:
            resp.readline()  # retry: 3000
            resp.readline()  # blank line closing the retry frame
            # Reading those two lines guarantees the server already reached
            # buffer.subscribe() (it writes the retry line only after
            # subscribing), so this record can't be missed by a race.
            lightlogger.info("streamed live", data={"ok": True})

            data_line = b""
            for _ in range(5):  # bounded: never read indefinitely
                line = resp.readline()
                if line.startswith(b"data: "):
                    data_line = line
                    break
            assert data_line.startswith(b"data: ")
            record = json.loads(data_line[len(b"data: ") :])
            assert record["message"] == "streamed live"
            assert record["data"] == {"ok": True}
            # Mandatory double-newline framing: a blank line must follow.
            assert resp.readline() == b"\n"
        finally:
            resp.close()

    def test_sends_a_heartbeat_comment_within_the_heartbeat_interval(self) -> None:
        # A throwaway server with a fast heartbeat_interval, built directly via
        # create_server()/serve_in_background() rather than lightlogger.start():
        # start() intentionally has no heartbeat_interval param (frozen public
        # API), so this is the one place that bypasses it. Keeps this test
        # from genuinely waiting the real 15s production interval.
        fast_interval = 0.2
        buffer = LogBuffer()
        httpd = create_server(buffer, "127.0.0.1", 0, heartbeat_interval=fast_interval)
        serve_in_background(httpd)
        port = int(httpd.server_address[1])
        try:
            resp = _open_stream(port, timeout=fast_interval + 5.0)
            try:
                resp.readline()  # retry: 3000
                resp.readline()  # blank line

                heartbeat_line = b""
                for _ in range(5):  # bounded: never read indefinitely
                    line = resp.readline()
                    if line.startswith(b":"):
                        heartbeat_line = line
                        break
                assert heartbeat_line == b": ping\n"
                assert resp.readline() == b"\n"
            finally:
                resp.close()
        finally:
            httpd.shutdown()
            httpd.server_close()

    def test_disconnecting_unsubscribes_the_client_and_does_not_leak(self) -> None:
        lightlogger.start()
        before = len(lightlogger._buffer._subscribers)

        resp = _open_stream(_bound_port())
        resp.readline()  # retry: 3000
        resp.readline()  # blank line
        assert len(lightlogger._buffer._subscribers) == before + 1

        resp.close()  # simulate the browser tab closing

        # The server thread only discovers the closed socket on its next
        # write attempt (a heartbeat up to HEARTBEAT_INTERVAL_SECONDS away, or
        # sooner if something is logged), so nudge it with new records and
        # poll briefly rather than asserting instantly.
        deadline = time.time() + 5.0
        while time.time() < deadline:
            lightlogger.info("nudge for disconnect detection")
            if len(lightlogger._buffer._subscribers) == before:
                break
            time.sleep(0.05)

        assert len(lightlogger._buffer._subscribers) == before
