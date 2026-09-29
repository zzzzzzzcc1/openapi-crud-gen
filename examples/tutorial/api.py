"""Tutorial backend for examples/tutorial/openapi.yaml (standard library only).

    python examples/tutorial/api.py       # serves http://127.0.0.1:8000

Unlike examples/mock_api.py, this one validates input and looks users up by id,
so the TODOs in the generated tests decide whether they pass or fail. Every
request starts from the same seed data, so you can re-run the tutorial freely.
"""

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

SEED = {"1": {"id": "1", "name": "Ada"}}


class Handler(BaseHTTPRequestHandler):
    # In-memory store shared by every request. The seed users are restored at the
    # start of each request so the tutorial can be re-run as often as you like.
    users: dict[str, dict[str, str]] = {key: dict(value) for key, value in SEED.items()}

    def handle_one_request(self) -> None:
        for key, value in SEED.items():
            self.users.setdefault(key, dict(value))
        super().handle_one_request()

    def do_GET(self) -> None:
        user_id = self._user_id()
        if user_id is None:
            self._send(200, {"users": list(self.users.values())})
            return
        user = self.users.get(user_id)
        if user is None:
            self._send(404, {"error": f"user {user_id} not found"})
            return
        self._send(200, user)

    def do_POST(self) -> None:
        payload = self._json_body()
        name = payload.get("name")
        if not name:
            self._send(400, {"error": "name is required"})
            return
        new_id = str(max(int(key) for key in self.users) + 1)
        self.users[new_id] = {"id": new_id, "name": name}
        self._send(201, self.users[new_id])

    def do_PUT(self) -> None:
        user = self.users.get(self._user_id())
        if user is None:
            self._send(404, {"error": "user not found"})
            return
        name = self._json_body().get("name")
        if not name:
            self._send(400, {"error": "name is required"})
            return
        user["name"] = name
        self._send(200, user)

    def do_DELETE(self) -> None:
        if self.users.pop(self._user_id(), None) is None:
            self._send(404, {"error": "user not found"})
            return
        self._send(204)

    def _user_id(self) -> str | None:
        parts = self.path.split("?")[0].strip("/").split("/")
        return parts[1] if len(parts) > 1 else None

    def _json_body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return {}

    def _send(self, status: int, payload: dict | None = None) -> None:
        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def log_request(self, code: int | str = "-", size: int | str = "-") -> None:
        print(f"{self.command} {self.path} -> {code}")


def main(port: int = 8000) -> None:
    print(f"tutorial API listening on http://127.0.0.1:{port} (Ctrl+C to stop)")
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8000)
