#!/usr/bin/env python3
"""Optional MQTT / Mini-UNS publisher for ScooterLab (ADR-0004 / ADR-0005 / TASK-DATA-03).

Publishes ONLY privacy-safe aggregated KPIs and SYM maintenance alerts
(raw GPS coordinates, VIN, and license plate are stripped by `build_uns_payload`).
Uses `paho-mqtt` instead of shelling out to `mosquitto_pub -P` so credentials are
never exposed in the OS process table.
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Dict, Optional

from maintenance_tracker import build_uns_payload


def publish_uns_summary(
    odometer_km: float,
    session_summary: Dict[str, object],
    dry_run: bool = False,
) -> Dict[str, object]:
    prefix = os.environ.get("SCOOTERLAB_MQTT_TOPIC_PREFIX", "scooterlab/symphony200")
    payload = build_uns_payload(odometer_km, session_summary, topic_prefix=prefix)
    topic = str(payload["topic"])
    body = json.dumps(payload, ensure_ascii=False)

    if dry_run:
        return payload

    try:
        import paho.mqtt.publish as mqtt_publish
    except ImportError as exc:
        raise RuntimeError(
            "paho-mqtt non installato. Installa con `pip install 'scooterlab-tools[uns]'`."
        ) from exc

    host = os.environ.get("SCOOTERLAB_MQTT_HOST", "127.0.0.1")
    port = int(os.environ.get("SCOOTERLAB_MQTT_PORT", "1883"))
    user = os.environ.get("SCOOTERLAB_MQTT_USER", "")
    pw = os.environ.get("SCOOTERLAB_MQTT_PASS", "")
    ca_cert = os.environ.get("SCOOTERLAB_MQTT_CA_CERT", "")

    auth: Optional[Dict[str, str]] = {"username": user, "password": pw} if user else None
    tls: Optional[Dict[str, str]] = {"ca_certs": ca_cert} if ca_cert else None

    mqtt_publish.single(
        topic=topic,
        payload=body,
        hostname=host,
        port=port,
        auth=auth,
        tls=tls,
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish privacy-safe ScooterLab KPIs to MQTT/UNS")
    parser.add_argument("--odometer-km", type=float, required=True)
    parser.add_argument("--distance-km", type=float, default=0.0)
    parser.add_argument("--max-speed-kmh", type=float, default=0.0)
    parser.add_argument("--dry-run", action="store_true", help="Print JSON payload without connecting to broker")
    args = parser.parse_args()

    payload = publish_uns_summary(
        args.odometer_km,
        {"distance_km": args.distance_km, "max_speed_kmh": args.max_speed_kmh},
        dry_run=args.dry_run,
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
