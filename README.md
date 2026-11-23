# ScooterLab — Telemetria IoT, Smart Garage & Hardware Design (SYM Symphony ST 200i)

[![Anteprima ScooterLab — Telemetria IoT ESP32](./docs/preview/social-preview.png)](https://noobucodonosor.github.io/scooterlab/)

**Scheda Interattiva & Schema Cablaggio Live (GitHub Pages):** [https://noobucodonosor.github.io/scooterlab/](https://noobucodonosor.github.io/scooterlab/)

Progetto personale di **ingegneria IoT / embedded, telemetria veicolare non invasiva (Livello 0 → 2) e Smart Garage Officina** per **SYM Symphony ST 200i ABS (XB20E2-EU)** *(progetto indipendente, non affiliato a UTSA ScooterLab)*, progettato per registrare cinematica, dinamica e percorsi senza alterare l'impianto o la ECU di serie.

> **Stato del progetto:** **Specifica Hardware Rev. 2, 8 ADR accettati (`ADR-0001..0008`), scaffold firmware ESP-IDF v6.x (Dual-SPI + Hold-Up), pipeline dati Python (`.slab` v1 con `REC_CAN`/`REC_HEALTH`, `analyze.py`, `ingest_server.py`), Docker stack TLS/MQTT e Smart Garage Web App Officina attivi** — Driver sensori su banco in completamento.

## Architettura Hardware & Software Target (Rev. 2 — 2026)
- **Microcontrollore:** ESP32-S3 / ESP32-C5 (`ESP-IDF v6.x` / PlatformIO, TWAI/CAN integrato)
- **Inerziale (Smart IMU):** ST `ISM330IS` / Bosch `BHI360` su bus **Dual-SPI** (`SPI2`/`SPI3`, 1–4 kHz + In-Sensor AI)
- **Posizionamento:** Modulo GNSS `u-blox M10` su **UART** (5–10 Hz, traccia, velocità reale, timestamp UTC)
- **Persistenza & Protezione Automotive:** Ring-buffer microSD High Endurance 4 KB (formato binario `.slab` v1 con CRC32, `REC_CAN` e `REC_HEALTH`), positivo sottochiave 12 V → Fusibile 1 A → TVS + Buck 5 V + Hold-Up → IP65
- **Smart Garage & Officina (`ADR-0005`, `0008`):** upload Wi-Fi **HTTPS TLS 1.3 + Bearer Token** (NVS cifrata), Docker stack MQTT/UNS, report FFT/Welch (`analyze.py`) e **Smart Garage Web App** con procedure guidate officina, atlante esplosi SYM e Digital Twin 3D offline

## Documentazione Tecnica (`8 ADR`)
- **[Indice ADR, Architettura Target 2026 & Master Task Backlog](./docs/adr/README.md)**
  - [ADR-0001 — Architettura Telemetria IoT ESP32 (Baseline Livello 0)](./docs/adr/0001-architettura-telemetria-iot-esp32.md)
  - [ADR-0002 — Aggiornamento Hardware, MCU & Smart IMU (Revisione 2026)](./docs/adr/0002-aggiornamento-hardware-sensori-2026.md)
  - [ADR-0003 — Sicurezza, Hardening (RED/CRA-Ready) e Privacy](./docs/adr/0003-sicurezza-hardening-red-cra-privacy.md)
  - [ADR-0004 — Pipeline Dati, Unified Namespace (UNS) e Automazione](./docs/adr/0004-pipeline-dati-telemetria-uns-automazione.md)
  - [ADR-0005 — Smart Garage Container Stack, TLS End-to-End & Hardening Ingest](./docs/adr/0005-smart-garage-container-stack-tls.md)
  - [ADR-0006 — Dual-SPI (`SPI2`/`SPI3`), Ring-Buffer SD 4 KB, Hold-Up & Protezione TVS 12 V](./docs/adr/0006-dual-spi-buffer-holdup-automotive.md)
  - [ADR-0007 — Estensione `.slab` v1 (`REC_CAN` e `REC_HEALTH`) & Report Avanzato](./docs/adr/0007-estensione-slab-can-health.md)
  - [ADR-0008 — Smart Garage Web App, Procedure Guidate Officina & Digital Twin 3D Offline](./docs/adr/0008-smart-garage-webapp-officina.md)
- [BOM Rev. 2 (2026) & Pinout ESP32-S3/C5](./docs/bom-rev2-2026.md) · [Specifica `.slab` v1](./docs/04-formato-slab.md) · [Guida Officina & Smontaggio](./docs/05-guida-officina-manutenzione-smontaggio.md) · [AGENTS.md](./AGENTS.md)

## Stack & Test
- **Hardware & Embedded:** ESP32-S3/C5, `ESP-IDF v6.x`, Smart IMU `ISM330IS` (Dual-SPI), GNSS (UART), microSD (SPI), elettronica 12 V→5 V, TVS/Hold-Up, IP65
- **Backend, Web App & QA:** Python (`tools/slab_codec.py`, `tools/analyze.py`, `tools/ingest_server.py`, `tools/garage_store.py`, `tools/webapp/`), Docker Compose, TLS 1.3, NVS cifrata, MQTT/UNS, suite `pytest` in `tools/tests/` (configurata via `pyproject.toml`)
- **Licenza:** Rilasciato sotto licenza [MIT](./LICENSE).
