#!/usr/bin/env bash
# Generate a local self-signed TLS certificate for ScooterLab Garage Ingest Server (ADR-0003)
# Output files (`*.pem`, `*.key`, `*.crt`) are automatically ignored by `.gitignore`.
set -euo pipefail

OUT_DIR="${1:-./certs}"
HOST_SAN="${2:-IP:127.0.0.1,DNS:localhost,DNS:scooterlab.local}"

mkdir -p "$OUT_DIR"
openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 \
  -keyout "$OUT_DIR/ingest.key" \
  -out "$OUT_DIR/ingest.crt" \
  -days 825 -nodes \
  -subj "/CN=scooterlab-garage" \
  -addext "subjectAltName=$HOST_SAN" >/dev/null 2>&1

chmod 600 "$OUT_DIR/ingest.key"
echo "[gen_local_tls] Certificati TLS creati in $OUT_DIR (SAN: $HOST_SAN)"
echo "  Cert: $OUT_DIR/ingest.crt"
echo "  Key:  $OUT_DIR/ingest.key"
