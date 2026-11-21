#!/usr/bin/env python3
"""ScooterLab telemetry analyzer (.slab v1 -> KPI, A/B diff & standalone HTML report).

Usage:
    python3 tools/analyze.py tools/sessions/sess00002.slab --label "prova"
    python3 tools/analyze.py ride_b.slab --baseline ride_a.slab --label "rulli 12g"
"""

from __future__ import annotations

import argparse
import html
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from string import Template
from typing import Any, Dict, List, Optional, Tuple

from slab_codec import CanRecord, GpsRecord, HealthRecord, ImuRecord, SlabHeader, read_slab_full


@dataclass(frozen=True)
class SessionKPI:
    build_level: int
    duration_s: float
    distance_km: float
    max_speed_kmh: float
    avg_speed_kmh: float
    zero_to_50_s: Optional[float]
    max_lean_left_deg: float
    max_lean_right_deg: float
    comfort_rms_g: float
    dominant_vib_hz: float
    lean_histogram: Dict[str, int]


def compute_zero_to_50(gps_records: List[GpsRecord]) -> Optional[float]:
    """Compute best 0 -> 50 km/h sprint duration (seconds) from GPS speed."""
    if not gps_records:
        return None
    best: Optional[float] = None
    start_t: Optional[float] = None
    for g in gps_records:
        v_kmh = (g.speed_cms / 100.0) * 3.6
        t_s = g.t_ms / 1000.0
        if v_kmh <= 2.0:
            start_t = t_s
        elif start_t is not None and v_kmh >= 50.0:
            dt = t_s - start_t
            if dt > 0.5 and (best is None or dt < best):
                best = dt
            start_t = None
    return round(best, 2) if best is not None else None


def _fft_radix2(x: List[complex]) -> List[complex]:
    """Cooley-Tukey radix-2 FFT (requires len(x) to be a power of 2)."""
    n = len(x)
    if n <= 1:
        return x
    even = _fft_radix2(x[0::2])
    odd = _fft_radix2(x[1::2])
    twiddles = [
        complex(math.cos(-2.0 * math.pi * k / n), math.sin(-2.0 * math.pi * k / n)) * odd[k]
        for k in range(n // 2)
    ]
    return [even[k] + twiddles[k] for k in range(n // 2)] + [
        even[k] - twiddles[k] for k in range(n // 2)
    ]


def compute_spectrum(az_g: List[float], sample_hz: int) -> Tuple[List[Tuple[float, float]], float]:
    """Compute Welch-averaged Hann-windowed spectrum [(freq_hz, power), ...] and dominant Hz."""
    if len(az_g) < 32 or sample_hz <= 0:
        return [], 0.0

    win_n = 512 if len(az_g) >= 512 else 256
    while win_n > len(az_g) and win_n > 32:
        win_n //= 2
    step = max(1, win_n // 2)

    hann = [0.5 * (1.0 - math.cos(2.0 * math.pi * i / (win_n - 1))) for i in range(win_n)]
    psd = [0.0] * (win_n // 2)
    segments = 0

    for start in range(0, len(az_g) - win_n + 1, step):
        seg = az_g[start : start + win_n]
        mean_v = sum(seg) / win_n
        windowed = [complex((seg[i] - mean_v) * hann[i], 0.0) for i in range(win_n)]
        spec = _fft_radix2(windowed)
        for k in range(1, win_n // 2):
            c = spec[k]
            psd[k] += c.real * c.real + c.imag * c.imag
        segments += 1

    if segments == 0:
        return [], 0.0

    bins: List[Tuple[float, float]] = []
    best_hz = 0.0
    best_mag = -1.0
    for k in range(1, win_n // 2):
        freq = k * sample_hz / win_n
        mag = psd[k] / segments
        bins.append((freq, mag))
        if freq >= 2.0 and mag > best_mag:
            best_mag = mag
            best_hz = freq
    return bins, round(best_hz, 1)


def compute_dominant_frequency(az_g: List[float], sample_hz: int) -> float:
    """Estimate dominant vertical vibration frequency (2..Nyquist Hz) via
    Welch-averaged Hann-windowed periodogram across the full session."""
    _, dom_hz = compute_spectrum(az_g, sample_hz)
    return dom_hz


def filter_valid_gps(gps_records: List[GpsRecord], max_hdop_x10: int = 50) -> List[GpsRecord]:
    """Filter out GNSS records without 2D/3D fix or with poor HDOP (> 5.0)."""
    return [g for g in gps_records if g.fix >= 2 and 0 < g.hdop_x10 <= max_hdop_x10]


def compute_kpis(
    header: SlabHeader,
    imu_records: List[ImuRecord],
    gps_records: List[GpsRecord],
) -> SessionKPI:
    all_t_ms = [r.t_ms for r in imu_records] + [g.t_ms for g in gps_records]
    duration_s = (max(all_t_ms) - min(all_t_ms)) / 1000.0 if len(all_t_ms) >= 2 else 0.0

    valid_gps = filter_valid_gps(gps_records)
    speeds_kmh = [(g.speed_cms / 100.0) * 3.6 for g in valid_gps]
    max_speed = max(speeds_kmh) if speeds_kmh else 0.0
    moving = [v for v in speeds_kmh if v > 2.0]
    avg_speed = (sum(moving) / len(moving)) if moving else 0.0

    distance_m = 0.0
    for a, b in zip(valid_gps, valid_gps[1:]):
        dt_s = max(0.0, (b.t_ms - a.t_ms) / 1000.0)
        v_ms = ((a.speed_cms + b.speed_cms) / 2.0) / 100.0
        distance_m += v_ms * dt_s

    rolls = [r.roll_cdeg / 100.0 for r in imu_records]
    max_left = abs(min([0.0] + [x for x in rolls if x < 0]))
    max_right = max([0.0] + [x for x in rolls if x > 0])

    az_vals = [r.az_mg / 1000.0 for r in imu_records]
    comfort_rms = (
        math.sqrt(sum((v - 1.0) ** 2 for v in az_vals) / len(az_vals))
        if az_vals
        else 0.0
    )

    bins = {"0-5°": 0, "5-15°": 0, "15-25°": 0, "25°+": 0}
    for r in rolls:
        ar = abs(r)
        if ar < 5:
            bins["0-5°"] += 1
        elif ar < 15:
            bins["5-15°"] += 1
        elif ar < 25:
            bins["15-25°"] += 1
        else:
            bins["25°+"] += 1

    return SessionKPI(
        build_level=header.build_level,
        duration_s=round(duration_s, 1),
        distance_km=round(distance_m / 1000.0, 2),
        max_speed_kmh=round(max_speed, 1),
        avg_speed_kmh=round(avg_speed, 1),
        zero_to_50_s=compute_zero_to_50(valid_gps),
        max_lean_left_deg=round(max_left, 1),
        max_lean_right_deg=round(max_right, 1),
        comfort_rms_g=round(comfort_rms, 3),
        dominant_vib_hz=compute_dominant_frequency(az_vals, header.imu_hz),
        lean_histogram=bins,
    )


def _svg_speed_chart(gps_records: List[GpsRecord]) -> str:
    w, h = 640, 180
    if len(gps_records) < 2:
        return "<p>Dati GPS insufficienti per il grafico velocità.</p>"
    t_max = max(g.t_ms for g in gps_records) / 1000.0 or 1.0
    v_max = max(((g.speed_cms / 100.0) * 3.6 for g in gps_records), default=60.0)
    v_max = max(v_max, 60.0)

    pts = []
    for g in gps_records:
        x = 30 + (g.t_ms / 1000.0 / t_max) * (w - 50)
        v = (g.speed_cms / 100.0) * 3.6
        y = (h - 25) - (v / v_max) * (h - 45)
        pts.append(f"{x:.1f},{y:.1f}")
    poly = " ".join(pts)
    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="background:#0f172a;border-radius:8px">'
        f'<line x1="30" y1="{h-25}" x2="{w-20}" y2="{h-25}" stroke="#334155" />'
        f'<polyline fill="none" stroke="#38bdf8" stroke-width="2.2" points="{poly}" />'
        f'<text x="34" y="18" fill="#94a3b8" font-size="11">Velocità GPS (km/h) — Max {v_max:.0f}</text>'
        f"</svg>"
    )


def _svg_spectrum_chart(spectrum: List[Tuple[float, float]], nyquist_hz: float) -> str:
    w, h = 640, 160
    if len(spectrum) < 2:
        return "<p>Dati IMU insufficienti per lo spettro vibrazioni.</p>"
    max_p = max((p for _, p in spectrum), default=1.0) or 1.0
    f_max = nyquist_hz or spectrum[-1][0] or 1.0
    pts = []
    for freq, power in spectrum:
        x = 30 + (freq / f_max) * (w - 50)
        y = (h - 25) - (power / max_p) * (h - 45)
        pts.append(f"{x:.1f},{y:.1f}")
    poly = " ".join(pts)
    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="background:#0f172a;border-radius:8px">'
        f'<line x1="30" y1="{h-25}" x2="{w-20}" y2="{h-25}" stroke="#334155" />'
        f'<polyline fill="none" stroke="#a855f7" stroke-width="2" points="{poly}" />'
        f'<text x="34" y="18" fill="#94a3b8" font-size="11">Spettro Vibrazioni Asse Z (2–{f_max:.0f} Hz Nyquist)</text>'
        f"</svg>"
    )


def render_html_report(
    session_name: str,
    label: str,
    kpi: SessionKPI,
    gps_records: List[GpsRecord],
    baseline_kpi: Optional[SessionKPI] = None,
    spectrum: Optional[List[Tuple[float, float]]] = None,
    nyquist_hz: float = 50.0,
    can_records: Optional[List[CanRecord]] = None,
    health_records: Optional[List[HealthRecord]] = None,
) -> str:
    def _delta(curr: Optional[float], base: Optional[float], unit: str = "", invert: bool = False) -> str:
        if curr is None or base is None:
            return ""
        diff = curr - base
        sign = "+" if diff > 0 else ""
        color = "#22c55e" if (diff < 0 if invert else diff > 0) else "#f97316"
        return f' <span style="font-size:12px;color:{color}">({sign}{diff:.2f}{unit})</span>'

    z50_str = f"{kpi.zero_to_50_s:.2f} s" if kpi.zero_to_50_s is not None else "—"
    z50_delta = _delta(kpi.zero_to_50_s, baseline_kpi.zero_to_50_s if baseline_kpi else None, "s", invert=True)
    vmax_delta = _delta(kpi.max_speed_kmh, baseline_kpi.max_speed_kmh if baseline_kpi else None, " km/h")
    comf_delta = _delta(kpi.comfort_rms_g, baseline_kpi.comfort_rms_g if baseline_kpi else None, " g", invert=True)

    can_box = f"{len(can_records)} frame" if can_records else ("—" if kpi.build_level < 1 else "Attivo")
    if health_records:
        v_min = min(r.vbat_mv for r in health_records) / 1000.0
        v_max = max(r.vbat_mv for r in health_records) / 1000.0
        reg_ok = 13.8 <= v_max <= 14.9 and v_min >= 12.0
        regulator_box = f"{v_min:.2f}–{v_max:.2f} V ({'OK' if reg_ok else 'CHECK'})"
    else:
        regulator_box = "—"

    total_lean = sum(kpi.lean_histogram.values()) or 1
    hist_rows = "".join(
        f"<tr><td>{k}</td><td>{v}</td><td>{100.0 * v / total_lean:.1f}%</td></tr>"
        for k, v in kpi.lean_histogram.items()
    )

    tpl_path = Path(__file__).resolve().parent / "templates" / "report.html"
    tpl = Template(tpl_path.read_text(encoding="utf-8"))
    return tpl.safe_substitute(
        session_name=html.escape(session_name),
        label=html.escape(label),
        build_level=kpi.build_level,
        duration_s=kpi.duration_s,
        distance_km=kpi.distance_km,
        z50_str=z50_str,
        z50_delta=z50_delta,
        max_speed_kmh=kpi.max_speed_kmh,
        vmax_delta=vmax_delta,
        max_lean_left_deg=kpi.max_lean_left_deg,
        max_lean_right_deg=kpi.max_lean_right_deg,
        comfort_rms_g=kpi.comfort_rms_g,
        comf_delta=comf_delta,
        dominant_vib_hz=kpi.dominant_vib_hz,
        regulator_box=regulator_box,
        can_box=can_box,
        speed_svg=_svg_speed_chart(gps_records),
        spectrum_svg=_svg_spectrum_chart(spectrum or [], nyquist_hz),
        hist_rows=hist_rows,
    )


def analyze_file(
    slab_path: Path,
    label: str = "sessione",
    baseline_path: Optional[Path] = None,
    reports_dir: Optional[Path] = None,
) -> Tuple[SessionKPI, Path]:
    header, imu, gps, can_recs, health_recs = read_slab_full(slab_path)
    kpi = compute_kpis(header, imu, gps)
    az_vals = [r.az_mg / 1000.0 for r in imu]
    spectrum, _ = compute_spectrum(az_vals, header.imu_hz)

    base_kpi: Optional[SessionKPI] = None
    if baseline_path is not None:
        bh, bi, bg, _, _ = read_slab_full(baseline_path)
        base_kpi = compute_kpis(bh, bi, bg)

    out_dir = reports_dir or (Path(__file__).resolve().parent / "reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / f"{slab_path.stem}.html"
    report_path.write_text(
        render_html_report(
            slab_path.name,
            label,
            kpi,
            gps,
            base_kpi,
            spectrum=spectrum,
            nyquist_hz=header.imu_hz / 2.0,
            can_records=can_recs,
            health_records=health_recs,
        ),
        encoding="utf-8",
    )
    return kpi, report_path


def _downsample(items: List[Any], max_len: int) -> List[Any]:
    if len(items) <= max_len or max_len <= 1:
        return items
    step = (len(items) - 1) / (max_len - 1)
    return [items[int(round(i * step))] for i in range(max_len)]


def _build_local_track(
    gps_records: List[GpsRecord],
    privacy_trim_m: float = 0.0,
) -> List[Dict[str, float]]:
    valid = filter_valid_gps(gps_records)
    if len(valid) < 2:
        return []

    lat0 = valid[0].lat_e7 / 1e7
    lon0 = valid[0].lon_e7 / 1e7
    cos_lat = math.cos(math.radians(lat0)) or 1.0

    raw_pts: List[Tuple[float, float, float, float]] = []
    cum_dist = 0.0
    prev_x = 0.0
    prev_y = 0.0
    for idx, g in enumerate(valid):
        x = ((g.lon_e7 / 1e7) - lon0) * 111_111.0 * cos_lat
        y = ((g.lat_e7 / 1e7) - lat0) * 111_111.0
        if idx > 0:
            cum_dist += math.hypot(x - prev_x, y - prev_y)
        prev_x, prev_y = x, y
        v_kmh = round((g.speed_cms / 100.0) * 3.6, 1)
        raw_pts.append((x, y, v_kmh, cum_dist))

    total_dist = raw_pts[-1][3]
    if privacy_trim_m > 0 and total_dist > (2.2 * privacy_trim_m):
        trimmed = [
            p for p in raw_pts
            if privacy_trim_m <= p[3] <= (total_dist - privacy_trim_m)
        ]
    else:
        trimmed = raw_pts

    if not trimmed:
        trimmed = raw_pts

    pts = [
        {"x": round(p[0], 1), "y": round(p[1], 1), "kmh": p[2], "dist_m": round(p[3], 1)}
        for p in trimmed
    ]
    return _downsample(pts, 260)


def analyze_session_dict(
    slab_path: Path,
    baseline_path: Optional[Path] = None,
    recover: bool = False,
    privacy_trim_m: float = 0.0,
) -> Dict[str, Any]:
    """Return full telemetry analysis + downsampled series as a JSON-serializable dict."""
    header, imu, gps, can_recs, health_recs = read_slab_full(slab_path, recover=recover)
    kpi = compute_kpis(header, imu, gps)
    az_vals = [r.az_mg / 1000.0 for r in imu]
    spectrum, _ = compute_spectrum(az_vals, header.imu_hz)

    valid_gps = filter_valid_gps(gps)
    speed_series = _downsample(
        [{"t_s": round(g.t_ms / 1000.0, 2), "kmh": round((g.speed_cms / 100.0) * 3.6, 1)} for g in valid_gps],
        240,
    )
    spectrum_series = [
        {"hz": round(hz, 2), "power": round(pwr, 4)}
        for hz, pwr in _downsample(spectrum, 160)
    ]

    base_kpi_dict: Optional[Dict[str, Any]] = None
    deltas: Dict[str, Optional[float]] = {}
    if baseline_path is not None and baseline_path.exists():
        bh, bi, bg, _, _ = read_slab_full(baseline_path, recover=True)
        base_kpi = compute_kpis(bh, bi, bg)
        base_kpi_dict = asdict(base_kpi)
        deltas = {
            "zero_to_50_s": (
                round(kpi.zero_to_50_s - base_kpi.zero_to_50_s, 2)
                if kpi.zero_to_50_s is not None and base_kpi.zero_to_50_s is not None
                else None
            ),
            "max_speed_kmh": round(kpi.max_speed_kmh - base_kpi.max_speed_kmh, 1),
            "avg_speed_kmh": round(kpi.avg_speed_kmh - base_kpi.avg_speed_kmh, 1),
            "comfort_rms_g": round(kpi.comfort_rms_g - base_kpi.comfort_rms_g, 3),
        }

    health_summary: Dict[str, Any] = {}
    if health_recs:
        v_min = min(r.vbat_mv for r in health_recs) / 1000.0
        v_max = max(r.vbat_mv for r in health_recs) / 1000.0
        t_max = max(r.temp_dc for r in health_recs) / 10.0
        health_summary = {
            "vbat_min_v": round(v_min, 2),
            "vbat_max_v": round(v_max, 2),
            "temp_max_c": round(t_max, 1),
            "regulator_ok": 13.8 <= v_max <= 14.9 and v_min >= 12.0,
        }

    return {
        "session": slab_path.name,
        "recovered": recover,
        "kpi": asdict(kpi),
        "baseline_session": baseline_path.name if baseline_path else None,
        "baseline_kpi": base_kpi_dict,
        "deltas": deltas,
        "nyquist_hz": round(header.imu_hz / 2.0, 1),
        "speed_series": speed_series,
        "spectrum_series": spectrum_series,
        "gps_track": _build_local_track(gps, privacy_trim_m=privacy_trim_m),
        "privacy_trim_m": privacy_trim_m,
        "health_summary": health_summary,
        "can_count": len(can_recs),
        "record_counts": {
            "imu": len(imu),
            "gps": len(gps),
            "gps_valid": len(valid_gps),
            "can": len(can_recs),
            "health": len(health_recs),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a ScooterLab .slab telemetry file")
    parser.add_argument("slab_file", type=Path, help="Path to .slab file")
    parser.add_argument("--label", default="baseline", help="Human-readable label for the report")
    parser.add_argument("--baseline", type=Path, default=None, help="Optional baseline .slab for A/B comparison")
    parser.add_argument("--out-dir", type=Path, default=None, help="Output directory for HTML report")
    args = parser.parse_args()

    kpi, report_path = analyze_file(args.slab_file, args.label, args.baseline, args.out_dir)
    print(f"[analyze] Report generato: {report_path}")
    print(
        f"  Durata={kpi.duration_s}s | Dist={kpi.distance_km}km | "
        f"Vmax={kpi.max_speed_kmh}km/h | 0-50={kpi.zero_to_50_s}s | "
        f"Piega={kpi.max_lean_left_deg}/{kpi.max_lean_right_deg}deg | Comfort={kpi.comfort_rms_g}g"
    )


if __name__ == "__main__":
    main()
