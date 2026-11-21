"""End-to-end verification tests for ScooterLab Python pipeline & security controls."""

from __future__ import annotations

import http.client
import json
import math
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from analyze import analyze_file, compute_dominant_frequency, compute_kpis  # noqa: E402
from garage_store import GARAGE_PROCEDURES, GarageStore, evaluate_measurement  # noqa: E402
from ingest_server import create_server  # noqa: E402
from maintenance_tracker import build_uns_payload, compute_maintenance_schedule  # noqa: E402
from make_test_session import generate_synthetic_session  # noqa: E402
from slab_codec import (  # noqa: E402
    FOOTER_SIZE,
    GPS_SIZE,
    HEADER_SIZE,
    IMU_SIZE,
    REC_HDR_SIZE,
    CanRecord,
    GpsRecord,
    HealthRecord,
    ImuRecord,
    SlabHeader,
    read_slab,
    read_slab_full,
    write_slab,
)


def test_slab_binary_sizes_match_cpp_header() -> None:
    """Ensure Python struct sizes match `firmware/include/slab_format.h` static_asserts."""
    assert HEADER_SIZE == 32
    assert REC_HDR_SIZE == 4
    assert IMU_SIZE == 20
    assert GPS_SIZE == 20
    assert FOOTER_SIZE == 8

    cpp_header = (ROOT / "firmware" / "include" / "slab_format.h").read_text(encoding="utf-8")
    assert "sizeof(slab_header_t) == 32" in cpp_header
    assert "sizeof(slab_imu_rec_t) == 20" in cpp_header
    assert "sizeof(slab_gps_rec_t) == 20" in cpp_header
    assert "sizeof(slab_footer_t) == 8" in cpp_header


def test_generate_and_analyze_with_ab_baseline(tmp_path: Path) -> None:
    base_slab = generate_synthetic_session(tmp_path / "base.slab", build_level=0, sprint_scale=1.0)
    mod_slab = generate_synthetic_session(tmp_path / "mod.slab", build_level=0, sprint_scale=0.85)

    hdr, imu, gps = read_slab(base_slab)
    assert hdr.build_level == 0
    assert len(imu) == 60 * 50
    assert len(gps) == 60 * 5

    kpi, report = analyze_file(mod_slab, label="test A/B", baseline_path=base_slab, reports_dir=tmp_path)
    assert report.exists()
    html_out = report.read_text(encoding="utf-8")
    assert "ScooterLab — test A/B" in html_out
    assert kpi.zero_to_50_s is not None and 2.0 < kpi.zero_to_50_s < 12.0
    assert kpi.max_lean_left_deg > 15.0
    assert kpi.max_lean_right_deg > 15.0


def test_slab_crc32_detects_corruption(tmp_path: Path) -> None:
    slab = generate_synthetic_session(tmp_path / "corrupt.slab")
    data = bytearray(slab.read_bytes())
    data[50] ^= 0xFF
    slab.write_bytes(data)

    try:
        read_slab(slab)
        assert False, "Expected ValueError on corrupted payload CRC32"
    except ValueError as exc:
        assert "CRC32" in str(exc)


def test_ingest_server_enforces_bearer_auth(tmp_path: Path) -> None:
    token = "test-secret-token-xyz"
    slab = generate_synthetic_session(tmp_path / "upload_src.slab")
    raw = slab.read_bytes()

    srv = create_server("127.0.0.1", 0, token, tmp_path / "sessions", tmp_path / "reports")
    port = srv.server_address[1]
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        # 1. Missing token -> 401
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("POST", "/upload", body=raw, headers={"X-Session-Name": "sess00001.slab"})
        resp = conn.getresponse()
        assert resp.status == 401
        resp.read()
        conn.close()

        # 2. Valid token + valid .slab -> 200
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request(
            "POST",
            "/upload",
            body=raw,
            headers={
                "Authorization": f"Bearer {token}",
                "X-Session-Name": "sess00001.slab",
            },
        )
        resp = conn.getresponse()
        body = json.loads(resp.read().decode("utf-8"))
        assert resp.status == 200
        assert body["status"] == "ok"
        assert (tmp_path / "sessions" / "sess00001.slab").exists()
        assert (tmp_path / "reports" / "sess00001.html").exists()
        conn.close()

        # 3. Duplicate X-Session-Name does NOT overwrite existing session
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request(
            "POST",
            "/upload",
            body=raw,
            headers={
                "Authorization": f"Bearer {token}",
                "X-Session-Name": "sess00001.slab",
            },
        )
        resp = conn.getresponse()
        body2 = json.loads(resp.read().decode("utf-8"))
        assert resp.status == 200
        assert body2["session"] == "sess00001_1.slab"
        assert (tmp_path / "sessions" / "sess00001_1.slab").exists()
        conn.close()

        # 4. Malformed Content-Length -> 400 (no 500)
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request(
            "POST",
            "/upload",
            body=b"",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Session-Name": "bad.slab",
                "Content-Length": "not-an-int",
            },
        )
        resp = conn.getresponse()
        assert resp.status == 400
        resp.read()
        conn.close()

        # 5. GET /health -> 200
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/health")
        resp = conn.getresponse()
        assert resp.status == 200
        resp.read()
        conn.close()
    finally:
        srv.shutdown()
        srv.server_close()


def test_maintenance_tracker_and_uns_privacy() -> None:
    schedule = {m.item: m for m in compute_maintenance_schedule(29_271, warn_threshold_km=800)}
    assert schedule["olio_motore"].next_due_km == 30_000
    assert schedule["olio_motore"].remaining_km == 729
    assert schedule["olio_motore"].status == "DUE_SOON"
    assert schedule["cinghia_rulli_candela"].next_due_km == 36_000

    uns = build_uns_payload(
        29_271,
        {"distance_km": 8.4, "lat": 44.35, "lon": 9.23, "vin": "REDACTED", "targa": "XX00000"},
    )
    assert "lat" not in uns["summary"]
    assert "lon" not in uns["summary"]
    assert "vin" not in uns["summary"]
    assert "targa" not in uns["summary"]
    assert uns["summary"]["distance_km"] == 8.4


def test_read_slab_recovery_from_truncated_file(tmp_path: Path) -> None:
    slab = generate_synthetic_session(tmp_path / "full.slab", duration_s=4)
    raw = slab.read_bytes()
    # Truncate footer + 10 bytes of the last record
    truncated = tmp_path / "truncated.slab"
    truncated.write_bytes(raw[: -(FOOTER_SIZE + 10)])

    try:
        read_slab(truncated)
        raise AssertionError("Strict read_slab should reject truncated file")
    except ValueError:
        pass

    hdr, imus, gpss = read_slab(truncated, recover=True)
    assert hdr.imu_hz == 50
    assert len(imus) > 150
    assert len(gpss) > 10


def test_gps_filter_ignores_nofix_and_high_hdop() -> None:
    hdr = SlabHeader(imu_hz=100, gps_hz=5)
    # 0->60 km/h with fix=0 (no fix) and high HDOP should be ignored
    gps = [
        GpsRecord(t_ms=0, lat_e7=0, lon_e7=0, speed_cms=0, alt_dm=0, sats=0, fix=0, hdop_x10=99),
        GpsRecord(t_ms=1000, lat_e7=0, lon_e7=0, speed_cms=1600, alt_dm=0, sats=4, fix=1, hdop_x10=80),
        GpsRecord(t_ms=2000, lat_e7=0, lon_e7=0, speed_cms=500, alt_dm=100, sats=9, fix=3, hdop_x10=12),
        GpsRecord(t_ms=4000, lat_e7=0, lon_e7=0, speed_cms=500, alt_dm=100, sats=9, fix=3, hdop_x10=12),
    ]
    kpi = compute_kpis(hdr, [], gps)
    assert kpi.max_speed_kmh == 18.0
    assert kpi.zero_to_50_s is None


def test_dominant_frequency_full_session_fft() -> None:
    # Place 28 Hz signal after sample 256 (0..300 quiet, 300..1024 at 28 Hz @ 100 Hz)
    sample_hz = 100
    az = [1.0] * 300 + [1.0 + 0.4 * math.sin(2.0 * math.pi * 28.0 * i / sample_hz) for i in range(724)]
    dom_hz = compute_dominant_frequency(az, sample_hz)
    assert abs(dom_hz - 28.0) <= 0.6


def test_slab_can_health_roundtrip_and_report_template(tmp_path: Path) -> None:
    hdr = SlabHeader(build_level=1, imu_hz=100, gps_hz=5)
    imus = [
        ImuRecord(t_ms=i * 10, ax_mg=0, ay_mg=0, az_mg=1000, gx_ddps=0, gy_ddps=0, gz_ddps=0, roll_cdeg=0, pitch_cdeg=0)
        for i in range(40)
    ]
    gpss = [GpsRecord(t_ms=0, lat_e7=0, lon_e7=0, speed_cms=0, alt_dm=0, sats=8, fix=3, hdop_x10=12)]
    cans = [CanRecord(t_ms=100, can_id=0x18FEF100, dlc=4, data=b"\x1A\x2B\x00\x00")]
    healths = [HealthRecord(t_ms=100, vbat_mv=14350, temp_dc=315)]

    path = write_slab(tmp_path / "ext.slab", hdr, imus, gpss, can_records=cans, health_records=healths)
    h2, i2, g2, c2, hl2 = read_slab_full(path)
    assert h2.record_count == len(imus) + len(gpss) + len(cans) + len(healths)
    assert len(c2) == 1 and c2[0].can_id == 0x18FEF100
    assert len(hl2) == 1 and hl2[0].vbat_mv == 14350

    _, report = analyze_file(path, label="ext_test", reports_dir=tmp_path / "reports")
    html_text = report.read_text(encoding="utf-8")
    assert "14.35–14.35 V (OK)" in html_text
    assert "Spettro Vibrazioni Asse Z" in html_text


def test_garage_store_specs_procedures_and_persistence(tmp_path: Path) -> None:
    assert evaluate_measurement("regulator_v", 14.35)["status"] == "OK"
    assert evaluate_measurement("regulator_v", 15.6)["status"] == "OUT_OF_SPEC"
    assert evaluate_measurement("valve_in_mm", 0.12)["status"] == "OK"
    assert evaluate_measurement("cvt_roller_mm", 17.2)["status"] == "OUT_OF_SPEC"
    assert len(GARAGE_PROCEDURES) >= 5

    store = GarageStore(tmp_path / "garage_state.json")
    store.set_odometer(29500.5)
    store.record_check("regulator_v", 14.4, "misura a 2000 rpm")
    store.toggle_procedure_step("service_30k", 0, True)
    store.log_maintenance("olio_motore", 29500.5, "0.70L 10W-30")

    reloaded = GarageStore(tmp_path / "garage_state.json").load()
    assert reloaded["odometer_km"] == 29500.5
    assert reloaded["factory_checks"]["regulator_v"]["status"] == "OK"
    assert reloaded["procedure_progress"]["service_30k"] == [0]
    assert reloaded["maintenance_log"][0]["item"] == "olio_motore"


def test_webapp_api_and_demo_flow(tmp_path: Path) -> None:
    token = "test-webapp-token"
    srv = create_server(
        "127.0.0.1",
        0,
        token,
        tmp_path / "sessions",
        tmp_path / "reports",
        state_path=tmp_path / "garage_state.json",
    )
    port = srv.server_address[1]
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        # 1. Static Web App & JS assets
        for path in ("/", "/styles.css", "/app.js", "/scooter3d.js"):
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            conn.request("GET", path)
            r = conn.getresponse()
            assert r.status == 200
            r.read()
            conn.close()

        # 2. Generate demo A/B sessions
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("POST", "/api/sessions/demo")
        r = conn.getresponse()
        demo = json.loads(r.read().decode("utf-8"))
        assert r.status == 200
        assert "demo_post_rulli.slab" in demo["created"]
        conn.close()

        # 3. Inspect A/B session detail with privacy trim
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/api/sessions/demo_post_rulli.slab?baseline=demo_pre_30k.slab&privacy=1")
        r = conn.getresponse()
        detail = json.loads(r.read().decode("utf-8"))
        assert r.status == 200
        assert detail["baseline_session"] == "demo_pre_30k.slab"
        assert detail["deltas"]["zero_to_50_s"] < 0
        assert detail["health_summary"]["regulator_ok"] is True
        assert detail["can_count"] > 0
        assert len(detail["gps_track"]) >= 2
        conn.close()

        # 4. Save factory check via API
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        payload = json.dumps({"spec_id": "valve_in_mm", "value": 0.12}).encode("utf-8")
        conn.request("POST", "/api/garage/check", body=payload, headers={"Content-Type": "application/json"})
        r = conn.getresponse()
        chk = json.loads(r.read().decode("utf-8"))
        assert r.status == 200
        assert chk["result"]["status"] == "OK"
        conn.close()
    finally:
        srv.shutdown()
        srv.server_close()
