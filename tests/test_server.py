"""Real server tests (Phase 2): start a real ThreadingHTTPServer, hit it over
HTTP with urllib, and confirm stop()/start() cycles cleanly.
"""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from collections.abc import Iterator

import pytest

import lightlogger


@pytest.fixture(autouse=True)
def _clean_slate() -> Iterator[None]:
    lightlogger._buffer.clear()
    yield
    lightlogger.stop()
    lightlogger._buffer.clear()


def _url(port: int, path: str) -> str:
    return f"http://127.0.0.1:{port}{path}"


def _get(port: int, path: str) -> tuple[int, bytes]:
    with urllib.request.urlopen(_url(port, path)) as resp:
        return resp.status, resp.read()


def _bound_port() -> int:
    httpd = lightlogger._httpd
    assert httpd is not None
    return int(httpd.server_address[1])


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
