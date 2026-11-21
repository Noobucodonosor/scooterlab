# AGENTS.md — Contesto & Linee Guida per Agenti AI e Sviluppatori

> **REGOLA AUREA (MANDATORY):**
> Prima di modificare l'architettura hardware/software, aggiornare la BOM, scrivere firmware o toccare la pipeline dati, **DEVI leggere [`docs/adr/README.md`](./docs/adr/README.md)** e gli ADR specifici nella cartella [`docs/adr/`](./docs/adr/).

---

## 1. Panoramica del Progetto

- **Nome Progetto:** `ScooterLab`
- **Repository:** `Noobucodonosor/scooterlab` (pubblico)
- **Veicolo Target:** SYM Symphony ST 200i ABS 2019 (`XB20E2-EU`, motore 169 cc 4T raffreddato ad aria)
- **Obiettivo:** Telemetria IoT e hardware design **non invasivo** (Livello 0 → Livello 2) per registrare cinematica, dinamica, vibrazioni e percorsi su strada senza alterare l'impianto elettrico o la ECU di serie.
- **Stack Tecnologico (Baseline → Target 2026):**
  - **Edge MCU & SDK:** ESP32-S3 / ESP32-C5 (controller CAN/TWAI integrato) con **ESP-IDF v6.x** / PlatformIO (evoluzione rispetto alla baseline Arduino IDE su ESP32 classico).
  - **Sensoristica:** Smart IMU industriale (`ST ISM330IS` / `LSM6DSO16IS` con core ISPU, oppure `Bosch BHI360`) su bus **SPI** + modulo GPS su **UART** + microSD High Endurance su **SPI** (evoluzione rispetto a MPU-6050 su I2C).
  - **Sicurezza (RED EN 18031 / CRA-ready):** Secure Boot v2, OTA firmati con Downgrade Protection, partizione NVS cifrata, upload HTTPS/MQTTS TLS autenticato, accesso remoto Zero Trust via WireGuard (Tailscale / NetBird).
  - **Pipeline Dati & Analisi:** Formato offline binario `.slab` + parser/reportistica Python (`tools/analyze.py`), estendibile via broker MQTT / Unified Namespace (Node-RED 4.1.x) e automazione IT/manutenzione (n8n).

---

## 2. Mappa dei File Principali

| File / Cartella | Ruolo |
| :--- | :--- |
| [`docs/adr/README.md`](./docs/adr/README.md) | **Indice degli ADR**, diagramma architetturale Mermaid e **Master Task Backlog**. |
| [`docs/adr/0001-architettura-telemetria-iot-esp32.md`](./docs/adr/0001-architettura-telemetria-iot-esp32.md) | Baseline Livello 0 (ESP32 DevKit, MPU-6050, GPS, microSD, buck 12V→5V). |
| [`docs/adr/0002-aggiornamento-hardware-sensori-2026.md`](./docs/adr/0002-aggiornamento-hardware-sensori-2026.md) | Evoluzione 2026 hardware, MCU, Smart IMU (In-Sensor AI), bus SPI e connettività WAN futura. |
| [`docs/adr/0003-sicurezza-hardening-red-cra-privacy.md`](./docs/adr/0003-sicurezza-hardening-red-cra-privacy.md) | Hardening sicurezza (RED/CRA-ready), cifratura, OTA firmati, ZTNA e policy privacy. |
| [`docs/adr/0004-pipeline-dati-telemetria-uns-automazione.md`](./docs/adr/0004-pipeline-dati-telemetria-uns-automazione.md) | Pipeline dati offline-first (`.slab`), parser Python, broker MQTT/UNS e automazione manutenzione. |
| [`docs/01-istruzioni-montaggio-livello-0.md`](./docs/01-istruzioni-montaggio-livello-0.md) | Guida operativa di montaggio Livello 0 (Fasi A, B, C, C2, D). |
| [`docs/02-dati-tecnici-verificati.md`](./docs/02-dati-tecnici-verificati.md) | Scheda tecnica da officina con tracciabilità fonte (`[TUO]`, `[XB20]`, `[FAM]`, `[DERIV]`). |
| [`docs/03-manuali-e-fonti.md`](./docs/03-manuali-e-fonti.md) | Indice dei 13 manuali ufficiali e schemi elettrici SYM. |

---

## 3. Metodologia di Lavoro (ADR + Tracciabilità Fonti)

1. **Tracciabilità dei dati meccanici/elettrici:** Ogni dato aggiunto a `docs/02-dati-tecnici-verificati.md` deve indicare l'etichetta di provenienza: `[TUO]`, `[XB20]`, `[FAM]`, `[DERIV]`.
2. **ADR-Driven:** Ogni decisione architetturale è documentata in `docs/adr/NNNN-slug.md` e collegata a task operativi `TASK-<MODULO>-XX` tracciati nel Master Task Backlog e su GitHub Issues.
3. **Commit Atomici:**
   ```bash
   git commit -m "feat(TASK-HW-01): descrizione sintetica (closes #N)"
   ```

---

## 4. Sicurezza & Privacy (Regole Critiche — Repository Pubblico)

- **Mai committare dati identificativi del veicolo o del proprietario:** Nessuna targa, nessun numero di telaio (VIN), nessun indirizzo di casa o foto di documenti d'officina non oscurati.
- **Mai committare tracce GPS reali:** Le cartelle `sessions/`, `reports/` e i file `*.slab`, `*.gps.csv`, `*.gpx` devono restare sempre in `.gitignore`.
- **Mai committare segreti o credenziali Wi-Fi:** Nessun `HOME_SSID`, `HOME_PASS`, token API o certificato privato nel codice sorgente o nei file `.ino`/`.c`/`.h`. Usare `.env` locale o provisioning NVS cifrato.
- **Verifica Pre-Release:** Prima di ogni push di milestone, eseguire:
  ```bash
  python3 ~/.gemini/config/skills/adr-github-methodology/scripts/pre_release_check.py
  ```
