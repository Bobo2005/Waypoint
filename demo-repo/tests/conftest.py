"""Shared pytest fixtures.

The demo clients are tested against a real (loopback) HTTP server instead of
library-specific mocks like `responses` or `requests_mock`. That's on
purpose: those mock libraries only intercept `requests`, so tests written
against them would break the moment a file gets migrated to `httpx` even if
the migration were perfect. Hitting a real socket makes the test suite
agnostic to which client library the source file happens to use.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # noqa: A002 - silence default access logging
        pass

    def _send_json(self, status: int, payload) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, status: int, text: str) -> None:
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler naming convention
        if self.path.startswith("/weather"):
            self._send_json(200, {"city": "Lagos", "temp_c": 29, "conditions": "sunny"})
        elif self.path.startswith("/users/") and self.path.endswith("/repos"):
            self._send_json(200, [{"name": "demo-repo", "stars": 3}])
        elif self.path == "/health":
            self._send_json(200, {"status": "ok"})
        elif self.path == "/broken/health":
            self._send_json(503, {"status": "down"})
        elif self.path == "/files/hello.txt":
            self._send_text(200, "hello from the fixture server")
        elif self.path == "/files/missing.txt":
            self._send_text(404, "not found")
        else:
            self._send_text(404, "not found")

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        payload = json.loads(raw) if raw else {}
        if self.path == "/webhooks/incoming":
            self._send_json(200, {"received": True, "event": payload.get("event")})
        else:
            self._send_json(404, {"error": "not found"})


@pytest.fixture(scope="session")
def live_server():
    """Start a real HTTP server on a random free port for the whole session."""
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        yield base_url
    finally:
        server.shutdown()
        thread.join(timeout=2)