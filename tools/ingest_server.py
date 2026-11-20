#!/usr/bin/env python3
"""ScooterLab secure telemetry ingest server (ADR-0003 / TASK-SEC-03).

Requires `Authorization: Bearer <SCOOTERLAB_BEARER_TOKEN>`, validates the uploaded
`.slab` v1 binary (magic + CRC32) before persisting, and triggers `analyze.py`.
Supports native TLS via `SCOOTERLAB_TLS_CERT` / `SCOOTERLAB_TLS_KEY` or running
behind a local TLS reverse proxy / WireGuard ZTNA mesh (Tailscale / NetBird).
"""

from __future__ import annotations

import hmac
import json
import os
import re
import ssl
import tempfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional

from analyze import analyze_file
from slab_codec import read_slab

SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9._-]{1,64}\.slab$")


def make_handler(bearer_token: str, sessions_dir: Path, reports_dir: Path):
    class IngestHandler(BaseHTTPRequestHandler):
        def _send_json(self, status: HTTPStatus, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/upload":
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return

            auth = self.headers.get("Authorization", "")
            expected = f"Bearer {bearer_token}"
            if not bearer_token or not hmac.compare_digest(auth, expected):
                self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return

            filename = self.headers.get("X-Session-Name", "session.slab")
            if not SAFE_NAME_RE.match(filename):
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_filename"})
                return

            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 50 * 1024 * 1024:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_content_length"})
                return

            raw = self.rfile.read(length)
            with tempfile.NamedTemporaryFile(suffix=".slab", delete=False) as tmp:
                tmp.write(raw)
                tmp_path = Path(tmp.name)

            try:
                read_slab(tmp_path)
            except ValueError as exc:
                tmp_path.unlink(missing_ok=True)
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": f"invalid_slab: {exc}"})
                return

            sessions_dir.mkdir(parents=True, exist_ok=True)
            dest = sessions_dir / filename
            dest.write_bytes(raw)
            tmp_path.unlink(missing_ok=True)

            kpi, report_path = analyze_file(dest, label=dest.stem, reports_dir=reports_dir)
            self._send_json(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "session": dest.name,
                    "report": report_path.name,
                    "distance_km": kpi.distance_km,
                    "max_speed_kmh": kpi.max_speed_kmh,
                },
            )

        def log_message(self, fmt: str, *args) -> None:
            print(f"[ingest] {self.address_string()} - {fmt % args}")

    return IngestHandler


def create_server(
    host: str,
    port: int,
    bearer_token: str,
    sessions_dir: Path,
    reports_dir: Path,
    tls_cert: Optional[str] = None,
    tls_key: Optional[str] = None,
) -> HTTPServer:
    server = HTTPServer((host, port), make_handler(bearer_token, sessions_dir, reports_dir))
    if tls_cert and tls_key:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(certfile=tls_cert, keyfile=tls_key)
        server.socket = ctx.wrap_socket(server.socket, server_side=True)
    return server


def main() -> None:
    token = os.environ.get("SCOOTERLAB_BEARER_TOKEN", "")
    if not token:
        raise SystemExit("ERRORE: imposta SCOOTERLAB_BEARER_TOKEN prima di avviare ingest_server.py")

    host = os.environ.get("SCOOTERLAB_INGEST_HOST", "127.0.0.1")
    port = int(os.environ.get("SCOOTERLAB_INGEST_PORT", "8500"))
    sessions_dir = Path(os.environ.get("SCOOTERLAB_SESSIONS_DIR", "tools/sessions"))
    reports_dir = Path(os.environ.get("SCOOTERLAB_REPORTS_DIR", "tools/reports"))
    tls_cert = os.environ.get("SCOOTERLAB_TLS_CERT") or None
    tls_key = os.environ.get("SCOOTERLAB_TLS_KEY") or None

    srv = create_server(host, port, token, sessions_dir, reports_dir, tls_cert, tls_key)
    scheme = "https" if (tls_cert and tls_key) else "http"
    print(f"[ingest] In ascolto su {scheme}://{host}:{port}/upload (Bearer auth attiva)")
    srv.serve_forever()


if __name__ == "__main__":
    main()
