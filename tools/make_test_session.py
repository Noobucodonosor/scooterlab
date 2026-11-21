#!/usr/bin/env python3
"""Generate a deterministic synthetic ScooterLab `.slab` v1 test session.

Usage:
    python3 tools/make_test_session.py --level0
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from slab_codec import CanRecord, GpsRecord, HealthRecord, ImuRecord, SlabHeader, write_slab


def generate_synthetic_session(
    out_path: Path,
    build_level: int = 0,
    duration_s: int = 60,
    imu_hz: int = 50,
    gps_hz: int = 5,
    sprint_scale: float = 1.0,
) -> Path:
    """Create a realistic synthetic ride (sprint 0-60 km/h, curves, road bumps)."""
    imu_records = []
    gps_records = []

    # Synthetic neutral coordinates (ocean/placeholder, never real user location)
    base_lat = 44.0000000
    base_lon = 9.0000000

    total_imu = duration_s * imu_hz
    for i in range(total_imu):
        t = i / imu_hz
        t_ms = int(round(t * 1000))

        # Speed profile (m/s):
        # 0-2s standstill -> 2-12s sprint to 65 km/h (18 m/s) -> 12-45s curves at ~45 km/h -> 45-60s brake
        if t < 2.0:
            speed_ms = 0.0
            ax_g = 0.0
        elif t < 12.0:
            frac = (t - 2.0) / (10.0 * sprint_scale)
            speed_ms = min(18.0, 18.0 * (1.0 - math.exp(-2.6 * frac)))
            ax_g = 0.28 * math.exp(-1.2 * frac)
        elif t < 48.0:
            speed_ms = 12.5 + 2.0 * math.sin(0.35 * (t - 12.0))
            ax_g = 0.05 * math.cos(0.35 * (t - 12.0))
        else:
            frac = (t - 48.0) / 12.0
            speed_ms = max(0.0, 12.5 * (1.0 - frac))
            ax_g = -0.25 if speed_ms > 0.2 else 0.0

        # Lean angle (roll) during curving section (12s-48s): up to +-26 deg
        if 12.0 <= t < 48.0:
            roll_deg = 24.0 * math.sin(0.45 * (t - 12.0)) + 3.0 * math.sin(1.1 * t)
        else:
            roll_deg = 0.4 * math.sin(0.8 * t)

        pitch_deg = -4.5 * ax_g
        # Vertical acceleration: 1g + road bumps + engine/CVT vibration (~14 Hz alias / 18 Hz)
        road_bump = 0.08 * math.sin(2 * math.pi * 6.0 * t) + 0.05 * math.sin(2 * math.pi * 14.0 * t)
        if 30.0 <= t <= 38.0:
            road_bump += 0.16 * math.sin(2 * math.pi * 9.5 * t)

        az_g = 1.0 + road_bump
        ay_g = math.sin(math.radians(roll_deg)) * 0.45

        imu_records.append(
            ImuRecord(
                t_ms=t_ms,
                ax_mg=int(round(ax_g * 1000)),
                ay_mg=int(round(ay_g * 1000)),
                az_mg=int(round(az_g * 1000)),
                gx_ddps=int(round(roll_deg * 2.0)),
                gy_ddps=int(round(pitch_deg * 2.0)),
                gz_ddps=int(round(roll_deg * 3.5)),
                roll_cdeg=int(round(roll_deg * 100)),
                pitch_cdeg=int(round(pitch_deg * 100)),
            )
        )

    dist_m = 0.0
    x_m = 0.0
    y_m = 0.0
    total_gps = duration_s * gps_hz
    health_records = []
    can_records = []
    for j in range(total_gps):
        t = j / gps_hz
        t_ms = int(round(t * 1000))
        if t < 2.0:
            speed_ms = 0.0
        elif t < 12.0:
            frac = (t - 2.0) / (10.0 * sprint_scale)
            speed_ms = min(18.0, 18.0 * (1.0 - math.exp(-2.6 * frac)))
        elif t < 48.0:
            speed_ms = 12.5 + 2.0 * math.sin(0.35 * (t - 12.0))
        else:
            frac = (t - 48.0) / 12.0
            speed_ms = max(0.0, 12.5 * (1.0 - frac))

        step_m = speed_ms / gps_hz
        dist_m += step_m
        heading = 0.045 * t + 0.65 * math.sin(0.14 * t)
        x_m += step_m * math.sin(heading)
        y_m += step_m * math.cos(heading)
        lat = base_lat + (y_m / 111_111.0)
        lon = base_lon + (x_m / (111_111.0 * math.cos(math.radians(base_lat))))

        gps_records.append(
            GpsRecord(
                t_ms=t_ms,
                lat_e7=int(round(lat * 1e7)),
                lon_e7=int(round(lon * 1e7)),
                speed_cms=int(round(speed_ms * 100)),
                alt_dm=10_150,  # 15.0 m slm (offset +1000m)
                sats=11,
                fix=3,
                hdop_x10=9,
            )
        )
        if j % gps_hz == 0:
            vbat = 14320 + int(round(90 * math.sin(0.2 * t)))
            temp_dc = 310 + int(round(t * 0.6))
            health_records.append(HealthRecord(t_ms=t_ms, vbat_mv=vbat, temp_dc=temp_dc))
            if build_level >= 1:
                rpm = int(3200 + speed_ms * 260)
                can_records.append(
                    CanRecord(
                        t_ms=t_ms,
                        can_id=0x18FEF100,
                        dlc=4,
                        data=rpm.to_bytes(2, "little") + b"\x32\x00",
                    )
                )

    header = SlabHeader(
        build_level=build_level,
        imu_hz=imu_hz,
        gps_hz=gps_hz,
        flags=2 if build_level >= 1 else 0,
        start_epoch_s=1_795_143_600,
    )
    return write_slab(
        out_path,
        header,
        imu_records,
        gps_records,
        can_records=can_records,
        health_records=health_records,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic ScooterLab .slab test session")
    parser.add_argument("--level0", action="store_true", help="Generate Livello 0 test session")
    parser.add_argument("--level", type=int, default=0, choices=[0, 1, 2], help="Build level")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent / "sessions" / "sess00002.slab",
        help="Output .slab file path",
    )
    parser.add_argument("--sprint-scale", type=float, default=1.0, help="Sprint time multiplier (for A/B tests)")
    args = parser.parse_args()

    level = 0 if args.level0 else args.level
    out = generate_synthetic_session(args.out, build_level=level, sprint_scale=args.sprint_scale)
    print(f"[make_test_session] Creata sessione sintetica Livello {level}: {out}")


if __name__ == "__main__":
    main()
