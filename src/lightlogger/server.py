"""ThreadingHTTPServer, daemon thread, and HTTP routes."""

from __future__ import annotations

import importlib.resources
import json
import sys
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from queue import Empty
from typing import Any

from lightlogger import sse
from lightlogger.buffer import LogBuffer

# How long an /api/stream client blocks on its queue before it gets a
# heartbeat comment instead. Also doubles as the heartbeat period.
HEARTBEAT_INTERVAL_SECONDS = 15.0


class LightloggerServer(ThreadingHTTPServer):
    # SSE holds connections open indefinitely; without daemon threads per
    # request, one slow client would starve every other route.
    daemon_threads = True
    allow_reuse_address = True

    def handle_error(self, request: Any, client_address: Any) -> None:
        # An /api/stream client that goes away (tab closed, reconnect churn)
        # can reset the connection at any point, including while a *later*,
        # unrelated request is being read on a freshly accepted socket. The
        # default handle_error() dumps a full traceback to stderr for that,
        # which looks like a server bug when it's just a disconnected client
        # -- same spirit as log_message() already staying quiet above.
        exc_type = sys.exc_info()[0]
        if exc_type is not None and issubclass(exc_type, (BrokenPipeError, ConnectionResetError)):
            return
        super().handle_error(request, client_address)


def _make_handler(buffer: LogBuffer) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            pass  # stay quiet on the user's stdout; they didn't ask for access logs

        def do_GET(self) -> None:
            if self.path == "/":
                self._serve_index()
            elif self.path == "/api/logs":
                self._serve_logs()
            elif self.path == "/api/stream":
                self._serve_stream()
            else:
                self.send_error(HTTPStatus.NOT_FOUND)

        def _serve_index(self) -> None:
            html = (importlib.resources.files("lightlogger") / "static" / "index.html").read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)

        def _serve_logs(self) -> None:
            # default=str: log `data` can be any Python object the caller passed in.
            body = json.dumps(buffer.snapshot(), default=str).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _serve_stream(self) -> None:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

            # BaseHTTPRequestHandler gives no clean "client closed the tab"
            # signal for a response this long-lived, so disconnect is detected
            # the standard way: attempt the write, and treat any failure
            # (BrokenPipeError, ConnectionResetError, or a generic OSError) as
            # the client having gone away. finally: unsubscribe() always runs,
            # so a leaked subscriber queue can't accumulate per disconnect.
            subscriber = buffer.subscribe()
            try:
                self.wfile.write(sse.format_retry())
                self.wfile.flush()
                while True:
                    try:
                        record = subscriber.get(timeout=HEARTBEAT_INTERVAL_SECONDS)
                    except Empty:
                        payload = sse.format_heartbeat()
                    else:
                        payload = sse.format_event(record)
                    self.wfile.write(payload)
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                buffer.unsubscribe(subscriber)

    return Handler


def create_server(buffer: LogBuffer, host: str, port: int) -> LightloggerServer:
    """Bind a server, auto-incrementing past `port` on OSError (port busy)."""
    handler_cls = _make_handler(buffer)
    while True:
        try:
            return LightloggerServer((host, port), handler_cls)
        except OSError:
            port += 1


def serve_in_background(httpd: LightloggerServer) -> threading.Thread:
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return thread
