# Architecture Decision Records (ADR) & Master Task Backlog — ScooterLab

Questa cartella raccoglie gli **Architecture Decision Records (ADR)** e il **Master Task Backlog** del progetto **ScooterLab** (`Noobucodonosor/scooterlab`), documentando l'evoluzione dalla baseline Livello 0 (`ADR-0001`) allo stack IoT, Embedded, Sicurezza e Dati aggiornato al **novembre 2026**.

---

## Indice degli ADR

| ID | Titolo | Stato | Priorità | Autori / Fonti |
| :--- | :--- | :--- | :--- | :--- |
| **[ADR-0001](./0001-architettura-telemetria-iot-esp32.md)** | Architettura Hardware & Telemetria IoT Livello 0 (ESP32 + IMU + GPS) | Accettato (Baseline) | Core | Daniele Bertuccio |
| **[ADR-0002](./0002-aggiornamento-hardware-sensori-2026.md)** | Aggiornamento Hardware, MCU, Smart IMU e Sensoristica (Revisione 2026) | Proposto | **P1 — Alta** | Daniele Bertuccio / Audit 2026 |
| **[ADR-0003](./0003-sicurezza-hardening-red-cra-privacy.md)** | Sicurezza, Hardening (RED EN 18031 / CRA-Ready) e Privacy | Proposto | **P0 — Critica** | Daniele Bertuccio / Audit RED-CRA |
| **[ADR-0004](./0004-pipeline-dati-telemetria-uns-automazione.md)** | Pipeline Dati Telemetria, Unified Namespace (UNS) e Automazione Manutenzione | Proposto | **P1 — Alta** | Daniele Bertuccio / Audit 2026 |

---

## Diagramma Architetturale Target (2026)

```mermaid
flowchart LR
  subgraph Scooter["Scooter — SYM Symphony ST 200i (IP65)"]
    PWR["12V Sottochiave -> Fusibile 1A -> Buck 5V + Hold-Up"]
    IMU["Smart IMU Industriale (ISM330IS / BHI360)"]
    GPS["GNSS 5-10 Hz (UART)"]
    CAN["CAN/OBD Listen-Only (Livello 1/2)"]
    MCU["ESP32-S3 / C5 (ESP-IDF v6.x + Secure Boot + NVS)"]
    SD[("microSD High Endurance (.slab)")]

    PWR --> MCU
    IMU -->|"SPI 1-4 kHz + ISPU"| MCU
    GPS -->|"UART"| MCU
    CAN -.->|"TWAI"| MCU
    MCU -->|"SPI + CRC32"| SD
  end

  subgraph Garage["Garage / Home Lab (Zero Trust)"]
    ING["ingest_server.py (HTTPS TLS + Bearer Token)"]
    ANA["analyze.py (KPI + FFT + A/B Baseline)"]
    REP["Report HTML Locale"]
    MQTT["Broker MQTT / Mini-UNS (Opzionale)"]
    AUTO["Node-RED 4.1 / n8n (Alert & Tagliandi SYM)"]
    ZTNA["WireGuard ZTNA (Tailscale / NetBird)"]

    ING --> ANA --> REP
    ANA -.->|"KPI aggregati (no GPS raw)"| MQTT --> AUTO
    ZTNA -.-> REP
  end

  MCU -->|"Wi-Fi 6 / TLS 1.3 (al rientro)"| ING
```

---

## Master Task Backlog (Tutti i Task Censiti)

> **Nota:** Lo stato live (`Open` / `Closed`) di ciascun task può essere sincronizzato sulle **GitHub Issues** del repository. Usa `closes #<NumeroIssue>` nei commit per chiuderle automaticamente.

| Task ID | Issue | ADR | Titolo Task | File Coinvolti | Priorità | Assegnatari |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TASK-SEC-01** | `#1` | [ADR-0003](./0003-sicurezza-hardening-red-cra-privacy.md) | Configurazione `.gitignore`, `.env.example` e pre-release secret check | `.gitignore`, `.env.example`, `AGENTS.md` | **P0 — Critica** | `@Noobucodonosor` |
| **TASK-SEC-02** | `#2` | [ADR-0003](./0003-sicurezza-hardening-red-cra-privacy.md) | Provisioning sicuro Wi-Fi/Token con NVS cifrata nel firmware | `firmware/src/config_nvs.cpp`, `firmware/partitions.csv` | **P0 — Critica** | `@Noobucodonosor` |
| **TASK-SEC-03** | `#3` | [ADR-0003](./0003-sicurezza-hardening-red-cra-privacy.md) | Endpoint di ingestione HTTPS/TLS con autenticazione Bearer Token | `tools/ingest_server.py`, `firmware/src/uploader.cpp` | **P0 — Critica** | `@Noobucodonosor` |
| **TASK-HW-01** | `#4` | [ADR-0002](./0002-aggiornamento-hardware-sensori-2026.md) | Aggiornamento BOM Rev. 2 e pinout SPI/UART/TWAI | `docs/01-istruzioni-montaggio-livello-0.md`, `docs/bom-rev2-2026.md` | **P1 — Alta** | `@Noobucodonosor` |
| **TASK-HW-02** | `#5` | [ADR-0002](./0002-aggiornamento-hardware-sensori-2026.md) | Scaffold progetto firmware ESP-IDF v6.x / PlatformIO | `firmware/platformio.ini`, `firmware/src/main.cpp` | **P1 — Alta** | `@Noobucodonosor` |
| **TASK-HW-03** | `#6` | [ADR-0002](./0002-aggiornamento-hardware-sensori-2026.md) | Protezione chiusura file microSD su spegnimento quadro | `docs/01-istruzioni-montaggio-livello-0.md`, `firmware/src/power_monitor.cpp` | **P1 — Alta** | `@Noobucodonosor` |
| **TASK-DATA-01** | `#7` | [ADR-0004](./0004-pipeline-dati-telemetria-uns-automazione.md) | Specifica formato binario `.slab` v1 e generatore sintetico | `docs/04-formato-slab.md`, `tools/pyproject.toml`, `tools/make_test_session.py` | **P1 — Alta** | `@Noobucodonosor` |
| **TASK-DATA-02** | `#8` | [ADR-0004](./0004-pipeline-dati-telemetria-uns-automazione.md) | Parser telemetria `analyze.py` con report HTML e confronto A/B | `tools/analyze.py`, `tools/templates/report.html` | **P1 — Alta** | `@Noobucodonosor` |
| **TASK-DATA-03** | `#9` | [ADR-0004](./0004-pipeline-dati-telemetria-uns-automazione.md) | Integrazione opzionale MQTT/UNS & scadenziario manutenzione SYM | `tools/maintenance_tracker.py`, `tools/mqtt_publisher.py` | **P2 — Media** | `@Noobucodonosor` |
