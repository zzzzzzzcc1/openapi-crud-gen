"""Tiny stand-in backend so generated tests can run without a real API.

    python examples/mock_api.py          # listens on http://127.0.0.1:8000
    python examples/mock_api.py 9000     # or pick another port

Every request gets a plausible status code (200 / 201 / 204) and an empty JSON
body. Demo only: no routing, no validation, no state, no persistence.
"""

import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

STATUS = {"GET": 200, "POST": 201, "PUT": 200, "PATCH": 200, "DELETE": 204}


class Handler(BaseHTTPRequestHandler):
    def _respond(self) -> None:
        status = STATUS.get(self.command, 200)
        body = b"" if status == 204 else b"{}"
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = _respond

    def log_message(self, *args: object) -> None:
        pass


def main(port: int = 8000) -> None:
    print(f"stub API listening on http://127.0.0.1:{port} (Ctrl+C to stop)")
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8000)
