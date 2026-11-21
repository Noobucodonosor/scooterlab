#!/usr/bin/env python3
"""SYM Symphony ST 200i ABS maintenance schedule tracker & privacy-safe UNS payload builder.

Intervals sourced from `docs/02-dati-tecnici-verificati.md` (`[TUO]` official manual):
- Engine oil (SAE 10W-30, 0.70 L): every 3,000 km
- Transmission oil (SAE 85W-140, 170 cc) & Air filter: every 6,000 km
- Fuel pump filter: every 10,000 km
- Drive belt (1B01XMA02 / Bando S08-023), rollers (18x14mm 13g) & spark plug (NGK CR7HSA): every 12,000 km
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import Dict, List

MAINTENANCE_INTERVALS_KM: Dict[str, int] = {
    "olio_motore": 3_000,
    "olio_trasmissione": 6_000,
    "filtro_aria": 6_000,
    "filtro_pompa_benzina": 10_000,
    "cinghia_rulli_candela": 12_000,
}


@dataclass(frozen=True)
class MaintenanceItem:
    item: str
    interval_km: int
    next_due_km: int
    remaining_km: int
    status: str  # "OK" | "DUE_SOON" | "OVERDUE"


def compute_maintenance_schedule(
    odometer_km: float,
    warn_threshold_km: int = 500,
) -> List[MaintenanceItem]:
    """Compute remaining distance to each official SYM maintenance milestone."""
    if odometer_km < 0:
        raise ValueError("odometer_km deve essere >= 0")

    results: List[MaintenanceItem] = []
    for name, interval in MAINTENANCE_INTERVALS_KM.items():
        next_due = ((int(odometer_km) // interval) + 1) * interval
        remaining = int(round(next_due - odometer_km))
        if remaining <= 0:
            status = "OVERDUE"
        elif remaining <= warn_threshold_km:
            status = "DUE_SOON"
        else:
            status = "OK"
        results.append(
            MaintenanceItem(
                item=name,
                interval_km=interval,
                next_due_km=next_due,
                remaining_km=remaining,
                status=status,
            )
        )
    return results


def build_uns_payload(
    odometer_km: float,
    session_summary: Dict[str, object],
    topic_prefix: str = "scooterlab/symphony200",
) -> Dict[str, object]:
    """Build privacy-safe Unified Namespace (MQTT/UNS) JSON payload (never includes raw GPS)."""
    forbidden_keys = {"lat", "lon", "lat_e7", "lon_e7", "gps", "coordinates", "vin", "plate", "targa"}
    safe_summary = {k: v for k, v in session_summary.items() if k.lower() not in forbidden_keys}
    schedule = [asdict(item) for item in compute_maintenance_schedule(odometer_km)]
    return {
        "topic": f"{topic_prefix}/telemetry/session_summary",
        "vehicle": "SYM Symphony ST 200i ABS (XB20E2-EU)",
        "odometer_km": round(odometer_km, 1),
        "summary": safe_summary,
        "maintenance": schedule,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="SYM Symphony ST 200i maintenance schedule checker")
    parser.add_argument("--odometer-km", type=float, required=True, help="Current odometer reading in km")
    parser.add_argument("--warn-km", type=int, default=800, help="Warning threshold in km")
    args = parser.parse_args()

    items = compute_maintenance_schedule(args.odometer_km, warn_threshold_km=args.warn_km)
    print(json.dumps([asdict(i) for i in items], indent=2))


if __name__ == "__main__":
    main()
