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
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from slab_codec import GpsRecord, ImuRecord, SlabHeader, read_slab


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


def compute_dominant_frequency(az_g: List[float], sample_hz: int) -> float:
    """Estimate dominant vertical vibration frequency (2..Nyquist Hz) via DFT."""
    n = min(len(az_g), 256)
    if n < 16 or sample_hz <= 0:
        return 0.0
    segment = az_g[:n]
    mean_v = sum(segment) / n
    centered = [x - mean_v for x in segment]

    best_hz = 0.0
    best_mag = -1.0
    max_k = n // 2
    for k in range(1, max_k):
        freq = k * sample_hz / n
        if freq < 2.0:
            continue
        re = 0.0
        im = 0.0
        factor = -2.0 * math.pi * k / n
        for idx, val in enumerate(centered):
            ang = factor * idx
            re += val * math.cos(ang)
            im += val * math.sin(ang)
        mag = re * re + im * im
        if mag > best_mag:
            best_mag = mag
            best_hz = freq
    return round(best_hz, 1)


def compute_kpis(
    header: SlabHeader,
    imu_records: List[ImuRecord],
    gps_records: List[GpsRecord],
) -> SessionKPI:
    all_t_ms = [r.t_ms for r in imu_records] + [g.t_ms for g in gps_records]
    duration_s = (max(all_t_ms) - min(all_t_ms)) / 1000.0 if len(all_t_ms) >= 2 else 0.0

    speeds_kmh = [(g.speed_cms / 100.0) * 3.6 for g in gps_records]
    max_speed = max(speeds_kmh) if speeds_kmh else 0.0
    moving = [v for v in speeds_kmh if v > 2.0]
    avg_speed = (sum(moving) / len(moving)) if moving else 0.0

    distance_m = 0.0
    for a, b in zip(gps_records, gps_records[1:]):
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
        zero_to_50_s=compute_zero_to_50(gps_records),
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


def render_html_report(
    session_name: str,
    label: str,
    kpi: SessionKPI,
    gps_records: List[GpsRecord],
    baseline_kpi: Optional[SessionKPI] = None,
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

    rpm_box = "—" if kpi.build_level < 1 else "Attivo"
    susp_box = "—" if kpi.build_level < 2 else "Attivo"

    total_lean = sum(kpi.lean_histogram.values()) or 1
    hist_rows = "".join(
        f"<tr><td>{k}</td><td>{v}</td><td>{100.0 * v / total_lean:.1f}%</td></tr>"
        for k, v in kpi.lean_histogram.items()
    )

    return f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8" />
<title>ScooterLab Report — {html.escape(session_name)}</title>
<style>
  body {{ font-family: system-ui, -apple-system, sans-serif; background:#020617; color:#e2e8f0; margin:0; padding:24px; }}
  .wrap {{ max-width:900px; margin:0 auto; }}
  h1 {{ margin:0 0 4px; font-size:24px; }}
  .meta {{ color:#94a3b8; margin-bottom:20px; font-size:14px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:12px; margin-bottom:20px; }}
  .card {{ background:#0f172a; border:1px solid #1e293b; border-radius:10px; padding:14px; }}
  .card .k {{ color:#94a3b8; font-size:12px; text-transform:uppercase; }}
  .card .v {{ font-size:22px; font-weight:700; margin-top:4px; }}
  table {{ width:100%; border-collapse:collapse; background:#0f172a; border-radius:8px; overflow:hidden; margin-top:16px; }}
  th, td {{ padding:10px 12px; border-bottom:1px solid #1e293b; text-align:left; font-size:14px; }}
  th {{ color:#94a3b8; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>ScooterLab — {html.escape(label)}</h1>
  <div class="meta">Sessione: <code>{html.escape(session_name)}</code> · Livello {kpi.build_level} · Durata {kpi.duration_s} s · Distanza {kpi.distance_km} km</div>
  <div class="grid">
    <div class="card"><div class="k">0–50 km/h</div><div class="v">{z50_str}{z50_delta}</div></div>
    <div class="card"><div class="k">Velocità Max</div><div class="v">{kpi.max_speed_kmh} km/h{vmax_delta}</div></div>
    <div class="card"><div class="k">Piega Max SX / DX</div><div class="v">{kpi.max_lean_left_deg}° / {kpi.max_lean_right_deg}°</div></div>
    <div class="card"><div class="k">Indice Comfort (RMS)</div><div class="v">{kpi.comfort_rms_g} g{comf_delta}</div></div>
    <div class="card"><div class="k">Vibrazione Dominante</div><div class="v">{kpi.dominant_vib_hz} Hz</div></div>
    <div class="card"><div class="k">RPM / Sospensioni</div><div class="v">{rpm_box} / {susp_box}</div></div>
  </div>
  {_svg_speed_chart(gps_records)}
  <table>
    <thead><tr><th>Fascia Angolo di Piega</th><th>Campioni</th><th>Quota</th></tr></thead>
    <tbody>{hist_rows}</tbody>
  </table>
</div>
</body>
</html>
"""


def analyze_file(
    slab_path: Path,
    label: str = "sessione",
    baseline_path: Optional[Path] = None,
    reports_dir: Optional[Path] = None,
) -> Tuple[SessionKPI, Path]:
    header, imu, gps = read_slab(slab_path)
    kpi = compute_kpis(header, imu, gps)

    base_kpi: Optional[SessionKPI] = None
    if baseline_path is not None:
        bh, bi, bg = read_slab(baseline_path)
        base_kpi = compute_kpis(bh, bi, bg)

    out_dir = reports_dir or (Path(__file__).resolve().parent / "reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / f"{slab_path.stem}.html"
    report_path.write_text(
        render_html_report(slab_path.name, label, kpi, gps, base_kpi),
        encoding="utf-8",
    )
    return kpi, report_path


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
