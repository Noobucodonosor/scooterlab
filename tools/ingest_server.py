#!/usr/bin/env python3
"""ScooterLab Smart Garage Server & Telemetry Ingest (ADR-0003 / ADR-0005 / ADR-0008).

- `POST /upload`: ESP32-S3 telemetry ingest (strict `Authorization: Bearer <token>`,
  `.slab` v1 CRC32 verification, non-overwrite naming, `analyze.py` + optional MQTT UNS).
- `GET /`: Smart Garage Web App (`tools/webapp/`).
- `GET /api/*`, `POST /api/*`: Local-first garage dashboard, A/B telemetry, SYM
  maintenance schedule, factory tolerance checks, and guided 3D procedures.
"""

from __future__ import annotations

import hmac
import json
import os
import re
import shutil
import ssl
import tempfile
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from analyze import analyze_file, analyze_session_dict, compute_kpis
from garage_store import FACTORY_SPECS, GARAGE_PROCEDURES, GarageStore
from maintenance_tracker import compute_maintenance_schedule
from make_test_session import generate_synthetic_session
from mqtt_publisher import publish_uns_summary
from slab_codec import read_slab_full

SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9._-]{1,64}\.slab$")
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
MAX_JSON_BYTES = 64 * 1024
READ_CHUNK_BYTES = 64 * 1024
REQUEST_TIMEOUT_SEC = 15.0

WEBAPP_DIR = Path(__file__).resolve().parent / "webapp"
STATIC_FILES: Dict[str, tuple[str, str]] = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
    "/scooter3d.js": ("scooter3d.js", "application/javascript; charset=utf-8"),
}


def _unique_session_path(sessions_dir: Path, filename: str) -> Path:
    """Return a non-colliding destination path inside `sessions_dir`."""
    candidate = sessions_dir / filename
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    counter = 1
    while True:
        alt = sessions_dir / f"{stem}_{counter}{suffix}"
        if not alt.exists():
            return alt
        counter += 1


def _list_sessions_summary(sessions_dir: Path) -> List[Dict[str, Any]]:
    if not sessions_dir.exists():
        return []
    out: List[Dict[str, Any]] = []
    for p in sorted(sessions_dir.glob("*.slab"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            hdr, imu, gps, can_recs, health_recs = read_slab_full(p, recover=True)
            kpi = compute_kpis(hdr, imu, gps)
            out.append(
                {
                    "name": p.name,
                    "size_bytes": p.stat().st_size,
                    "build_level": kpi.build_level,
                    "duration_s": kpi.duration_s,
                    "distance_km": kpi.distance_km,
                    "max_speed_kmh": kpi.max_speed_kmh,
                    "zero_to_50_s": kpi.zero_to_50_s,
                    "comfort_rms_g": kpi.comfort_rms_g,
                    "can_count": len(can_recs),
                    "health_count": len(health_recs),
                }
            )
        except Exception:
            out.append({"name": p.name, "size_bytes": p.stat().st_size, "corrupt": True})
    return out


def make_handler(
    bearer_token: str,
    sessions_dir: Path,
    reports_dir: Path,
    store: Optional[GarageStore] = None,
    tls_enabled: bool = False,
):
    garage = store or GarageStore(sessions_dir.parent / "garage_state.json")

    class IngestHandler(BaseHTTPRequestHandler):
        def setup(self) -> None:
            super().setup()
            self.request.settimeout(REQUEST_TIMEOUT_SEC)

        def _send_json(self, status: HTTPStatus, payload: dict) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_bytes(self, status: HTTPStatus, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _has_bearer_auth(self) -> bool:
            auth = self.headers.get("Authorization", "")
            expected = f"Bearer {bearer_token}"
            return bool(bearer_token) and hmac.compare_digest(auth, expected)

        def _is_api_allowed(self) -> bool:
            if self._has_bearer_auth():
                return True
            client_ip = self.client_address[0] if self.client_address else ""
            return client_ip in ("127.0.0.1", "::1", "::ffff:127.0.0.1")

        def _read_json_body(self) -> Optional[Dict[str, Any]]:
            raw_len = self.headers.get("Content-Length", "0")
            try:
                length = int(raw_len)
            except ValueError:
                return None
            if length <= 0 or length > MAX_JSON_BYTES:
                return None
            raw = self.rfile.read(length)
            try:
                data = json.loads(raw.decode("utf-8"))
                return data if isinstance(data, dict) else None
            except (UnicodeDecodeError, json.JSONDecodeError):
                return None

        def _build_overview(self) -> Dict[str, Any]:
            state = garage.load()
            odom = float(state.get("odometer_km", 29271.0))
            schedule = [asdict(m) for m in compute_maintenance_schedule(odom)]
            return {
                "odometer_km": odom,
                "baseline_session": state.get("baseline_session"),
                "maintenance_schedule": schedule,
                "maintenance_log": state.get("maintenance_log", []),
                "factory_specs": FACTORY_SPECS,
                "factory_checks": state.get("factory_checks", {}),
                "procedures": GARAGE_PROCEDURES,
                "procedure_progress": state.get("procedure_progress", {}),
                "sessions": _list_sessions_summary(sessions_dir),
                "server_info": {
                    "tls_enabled": tls_enabled,
                    "mqtt_enabled": os.environ.get("SCOOTERLAB_MQTT_ENABLED", "0") == "1",
                },
            }

        def _ingest_slab_stream(self, filename: str, recover: bool = False) -> Optional[Dict[str, Any]]:
            if not SAFE_NAME_RE.match(filename):
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_filename"})
                return None

            raw_len = self.headers.get("Content-Length", "0")
            try:
                length = int(raw_len)
            except ValueError:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_content_length"})
                return None

            if length <= 0 or length > MAX_UPLOAD_BYTES:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_content_length"})
                return None

            with tempfile.NamedTemporaryFile(suffix=".slab", delete=False) as tmp:
                tmp_path = Path(tmp.name)
                remaining = length
                while remaining > 0:
                    chunk = self.rfile.read(min(READ_CHUNK_BYTES, remaining))
                    if not chunk:
                        break
                    tmp.write(chunk)
                    remaining -= len(chunk)

            if remaining != 0:
                tmp_path.unlink(missing_ok=True)
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "truncated_body"})
                return None

            try:
                read_slab_full(tmp_path, recover=recover)
            except ValueError as exc:
                tmp_path.unlink(missing_ok=True)
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": f"invalid_slab: {exc}"})
                return None

            sessions_dir.mkdir(parents=True, exist_ok=True)
            dest = _unique_session_path(sessions_dir, filename)
            shutil.move(str(tmp_path), str(dest))

            if recover:
                analysis = analyze_session_dict(dest, recover=True)
                kpi_dist = analysis["kpi"]["distance_km"]
                kpi_vmax = analysis["kpi"]["max_speed_kmh"]
                report_name = ""
            else:
                kpi, report_path = analyze_file(dest, label=dest.stem, reports_dir=reports_dir)
                kpi_dist = kpi.distance_km
                kpi_vmax = kpi.max_speed_kmh
                report_name = report_path.name

            if kpi_dist > 0:
                garage.add_distance(kpi_dist)

            if os.environ.get("SCOOTERLAB_MQTT_ENABLED", "0") == "1":
                try:
                    odom = float(garage.load().get("odometer_km", 0.0))
                    publish_uns_summary(
                        odom,
                        {"distance_km": kpi_dist, "max_speed_kmh": kpi_vmax},
                    )
                except Exception as exc:
                    print(f"[ingest] Avviso UNS/MQTT: {exc}")

            return {
                "status": "ok",
                "session": dest.name,
                "report": report_name,
                "distance_km": kpi_dist,
                "max_speed_kmh": kpi_vmax,
            }

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path

            if path == "/health":
                self._send_json(HTTPStatus.OK, {"status": "ok"})
                return

            if path in STATIC_FILES:
                fname, ctype = STATIC_FILES[path]
                target = WEBAPP_DIR / fname
                if target.exists():
                    self._send_bytes(HTTPStatus.OK, ctype, target.read_bytes())
                    return
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "webapp_missing"})
                return

            if path.startswith("/api/"):
                if not self._is_api_allowed():
                    self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                    return

                if path == "/api/overview":
                    self._send_json(HTTPStatus.OK, self._build_overview())
                    return

                if path.startswith("/api/sessions/"):
                    name = path[len("/api/sessions/") :]
                    if not SAFE_NAME_RE.match(name):
                        self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_filename"})
                        return
                    slab_path = sessions_dir / name
                    if not slab_path.exists():
                        self._send_json(HTTPStatus.NOT_FOUND, {"error": "session_not_found"})
                        return

                    qs = parse_qs(parsed.query)
                    recover = qs.get("recover", ["0"])[0] == "1"
                    privacy = qs.get("privacy", ["0"])[0] == "1"
                    base_name = qs.get("baseline", [""])[0]
                    base_path: Optional[Path] = None
                    if base_name and SAFE_NAME_RE.match(base_name) and base_name != name:
                        cand = sessions_dir / base_name
                        if cand.exists():
                            base_path = cand

                    try:
                        data = analyze_session_dict(
                            slab_path,
                            baseline_path=base_path,
                            recover=recover,
                            privacy_trim_m=300.0 if privacy else 0.0,
                        )
                    except ValueError as exc:
                        self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                        return
                    self._send_json(HTTPStatus.OK, data)
                    return

            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path

            if path == "/upload":
                if not self._has_bearer_auth():
                    self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                    return
                filename = self.headers.get("X-Session-Name", "session.slab")
                result = self._ingest_slab_stream(filename, recover=False)
                if result is not None:
                    self._send_json(HTTPStatus.OK, result)
                return

            if path.startswith("/api/"):
                if not self._is_api_allowed():
                    self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                    return

                if path == "/api/sessions/upload":
                    filename = self.headers.get("X-Session-Name", "browser_upload.slab")
                    recover = self.headers.get("X-Recover", "0") == "1"
                    result = self._ingest_slab_stream(filename, recover=recover)
                    if result is not None:
                        self._send_json(HTTPStatus.OK, result)
                    return

                if path == "/api/sessions/demo":
                    sessions_dir.mkdir(parents=True, exist_ok=True)
                    pre = sessions_dir / "demo_pre_30k.slab"
                    post = sessions_dir / "demo_post_rulli.slab"
                    generate_synthetic_session(pre, build_level=0, duration_s=60, sprint_scale=1.18)
                    generate_synthetic_session(post, build_level=1, duration_s=60, sprint_scale=0.86)
                    analyze_file(pre, label="Pre-Tagliando 30k", reports_dir=reports_dir)
                    analyze_file(post, label="Post-Tagliando Rulli Nuovi", baseline_path=pre, reports_dir=reports_dir)
                    garage.set_baseline(pre.name)
                    self._send_json(
                        HTTPStatus.OK,
                        {"status": "ok", "created": [pre.name, post.name], "overview": self._build_overview()},
                    )
                    return

                body = self._read_json_body()
                if body is None:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
                    return

                try:
                    if path == "/api/garage/odometer":
                        state = garage.set_odometer(float(body["odometer_km"]))
                        self._send_json(HTTPStatus.OK, {"status": "ok", "odometer_km": state["odometer_km"]})
                        return
                    if path == "/api/garage/maintenance":
                        state = garage.log_maintenance(
                            str(body["item"]),
                            float(body["km"]),
                            str(body.get("notes", "")),
                        )
                        self._send_json(HTTPStatus.OK, {"status": "ok", "overview": self._build_overview()})
                        return
                    if path == "/api/garage/check":
                        res = garage.record_check(
                            str(body["spec_id"]),
                            float(body["value"]),
                            str(body.get("notes", "")),
                        )
                        self._send_json(HTTPStatus.OK, {"status": "ok", "result": res})
                        return
                    if path == "/api/garage/procedure":
                        state = garage.toggle_procedure_step(
                            str(body["proc_id"]),
                            int(body["step_idx"]),
                            bool(body["done"]),
                        )
                        self._send_json(
                            HTTPStatus.OK,
                            {"status": "ok", "procedure_progress": state["procedure_progress"]},
                        )
                        return
                    if path == "/api/garage/baseline":
                        sess = body.get("session")
                        if sess is not None and not SAFE_NAME_RE.match(str(sess)):
                            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_filename"})
                            return
                        garage.set_baseline(str(sess) if sess else None)
                        self._send_json(HTTPStatus.OK, {"status": "ok", "baseline_session": sess})
                        return
                except (KeyError, TypeError, ValueError) as exc:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                    return

            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

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
    state_path: Optional[Path] = None,
) -> ThreadingHTTPServer:
    store = GarageStore(state_path or (sessions_dir.parent / "garage_state.json"))
    tls_enabled = bool(tls_cert and tls_key)
    server = ThreadingHTTPServer(
        (host, port),
        make_handler(bearer_token, sessions_dir, reports_dir, store=store, tls_enabled=tls_enabled),
    )
    if tls_enabled and tls_cert and tls_key:
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
    print(f"[ingest] Smart Garage Web App & Upload: {scheme}://{host}:{port}/ (Bearer auth attiva)")
    srv.serve_forever()


if __name__ == "__main__":
    main()
