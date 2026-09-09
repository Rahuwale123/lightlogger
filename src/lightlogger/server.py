"""ThreadingHTTPServer, daemon thread, and HTTP routes. SSE lands in Phase 4."""

from __future__ import annotations

import importlib.resources
import json
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from lightlogger.buffer import LogBuffer


class LightloggerServer(ThreadingHTTPServer):
    # SSE (Phase 4) holds connections open indefinitely; without daemon threads
    # per-request, one slow client would starve every other route.
    daemon_threads = True
    allow_reuse_address = True


def _make_handler(buffer: LogBuffer) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            pass  # stay quiet on the user's stdout; they didn't ask for access logs

        def do_GET(self) -> None:
            if self.path == "/":
                self._serve_index()
            elif self.path == "/api/logs":
                self._serve_logs()
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
