"""Small same-origin HTTP adapter for the browser demo."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .engine import run_workflow
from .models import InputError

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
EXAMPLES = ROOT / "examples"
MAX_BODY_BYTES = 64 * 1024


class Handler(BaseHTTPRequestHandler):
    server_version = "SignalDesk/1.0"

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, value: object) -> None:
        self._send(status, json.dumps(value, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        path = urlsplit(self.path).path
        if path == "/api/health":
            self._json(200, {"status": "ok", "engine": "deterministic-policy-v1"})
            return
        if path == "/api/examples":
            names = ("checkout-outage", "payment-degradation", "staging-warning")
            examples = []
            for name in names:
                data = json.loads((EXAMPLES / f"{name}.json").read_text(encoding="utf-8"))
                examples.append({"id": name, "label": data["title"], "incident": data})
            self._json(200, examples)
            return

        files = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/app.css": ("app.css", "text/css; charset=utf-8"),
            "/app.js": ("app.js", "text/javascript; charset=utf-8"),
            "/favicon.svg": ("favicon.svg", "image/svg+xml"),
        }
        if path in files:
            name, mime = files[path]
            self._send(200, (STATIC / name).read_bytes(), mime)
        else:
            self._json(404, {"error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if urlsplit(self.path).path != "/api/run":
            self._json(404, {"error": "Not found"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= MAX_BODY_BYTES:
                self._json(413, {"error": "Request body must be 1–65536 bytes"})
                return
            raw = json.loads(self.rfile.read(size).decode("utf-8"))
            result = run_workflow(raw)
        except (ValueError, UnicodeDecodeError, InputError) as exc:
            self._json(400, {"error": str(exc)})
            return
        self._json(200, result)


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"SignalDesk is ready at http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping SignalDesk")
    finally:
        server.server_close()
