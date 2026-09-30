"""Small local server for manually demonstrating InfraWatch health checks."""

import argparse
import logging
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOGGER = logging.getLogger(__name__)


class DemoHealthHandler(BaseHTTPRequestHandler):
    """Serve deterministic healthy and unhealthy demo endpoints."""

    def do_GET(self) -> None:  # noqa: N802 - name required by BaseHTTPRequestHandler
        if self.path == "/health":
            self._send_response(HTTPStatus.OK, b'{"status":"healthy"}\n')
        elif self.path == "/unhealthy":
            self._send_response(HTTPStatus.SERVICE_UNAVAILABLE, b'{"status":"unhealthy"}\n')
        else:
            self._send_response(HTTPStatus.NOT_FOUND, b'{"status":"not_found"}\n')

    def _send_response(self, status: HTTPStatus, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        LOGGER.info("%s - %s", self.address_string(), format % args)


def main() -> None:
    """Run the demo server until interrupted."""
    parser = argparse.ArgumentParser(description="Run the InfraWatch demo service.")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), DemoHealthHandler)
    LOGGER.info("Demo server listening on http://127.0.0.1:%s", args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        LOGGER.info("Stopping demo server")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
