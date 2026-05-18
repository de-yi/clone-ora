"""Tiny HTTP health server so platforms like Fly don't auto-stop the machine.

ora is a Socket Mode Slack bot — the meaningful traffic is an outbound
WebSocket, with no inbound HTTP. Fly's autoscaler interprets the lack of
inbound HTTP as "idle" and stops the machine. So we serve a minimal /health
endpoint on 0.0.0.0:8080 in a background thread; that gives the platform
something to probe and keeps the machine alive.

Uses stdlib only (no new deps).
"""

import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

logger = logging.getLogger(__name__)


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"ok\n")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    # Silence the default per-request access logs — they're noise in our logs.
    def log_message(self, format, *args):  # noqa: A002
        pass


def start(port: int = 8080) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("0.0.0.0", port), _HealthHandler)
    thread = threading.Thread(
        target=server.serve_forever, name="health-server", daemon=True
    )
    thread.start()
    logger.info("health server listening on 0.0.0.0:%d", port)
    return server
