# ScooterLab — Telemetria IoT & Hardware Design (SYM Symphony ST 200i)

[![Anteprima ScooterLab — Telemetria IoT ESP32](./docs/preview/social-preview.png)](https://noobucodonosor.github.io/scooterlab/)

**Scheda Interattiva & Schema Cablaggio Live (GitHub Pages):** [https://noobucodonosor.github.io/scooterlab/](https://noobucodonosor.github.io/scooterlab/)

Progetto di **ingegneria IoT / embedded e telemetria veicolare non invasiva (Livello 0)** per **SYM Symphony ST 200i ABS (XB20E2-EU)**, progettato per registrare cinematica, dinamica e percorsi su strada senza alterare l'impianto o la ECU di serie.

> **Stato del progetto:** **Specifica Hardware, BOM, Cablaggio, Scheda Officina Verificata e ADR completati** — Firmware ESP32 (C++/PlatformIO) e parser telemetria Python in roadmap.

## Architettura Hardware (Livello 0)
- **Microcontrollore:** ESP32 DevKit (Wi-Fi / BLE)
- **Inerziale (IMU):** MPU-6050 su bus I2C (accelerometro + giroscopio 6 assi)
- **Posizionamento:** Modulo GPS su UART (traccia, velocità reale, timestamp UTC)
- **Persistenza:** Modulo microSD 32 GB su SPI per logging offline continuo
- **Alimentazione Veicolare Sicura:** Positivo sottochiave 12 V → Fusibile 1 A → Convertitore Buck DC-DC 12 V → 5 V tarato a banco → Scatola stagna IP65

## Documentazione Tecnica
- **[Indice ADR, Architettura Target 2026 & Master Task Backlog](./docs/adr/README.md)**
  - [ADR-0001 — Architettura Telemetria IoT ESP32 (Baseline Livello 0)](./docs/adr/0001-architettura-telemetria-iot-esp32.md)
  - [ADR-0002 — Aggiornamento Hardware, MCU & Smart IMU (Revisione 2026)](./docs/adr/0002-aggiornamento-hardware-sensori-2026.md)
  - [ADR-0003 — Sicurezza, Hardening (RED/CRA-Ready) e Privacy](./docs/adr/0003-sicurezza-hardening-red-cra-privacy.md)
  - [ADR-0004 — Pipeline Dati, Unified Namespace (UNS) e Automazione](./docs/adr/0004-pipeline-dati-telemetria-uns-automazione.md)
- [Istruzioni di Montaggio (Livello 0 — Fasi A, B, C, C2, D)](./docs/01-istruzioni-montaggio-livello-0.md)
- [Scheda Dati Tecnici Verificati da Officina](./docs/02-dati-tecnici-verificati.md)
- [Manuali e Fonti Ufficiali](./docs/03-manuali-e-fonti.md)
- [AGENTS.md — Contesto & Regole per Sviluppatori e Agenti AI](./AGENTS.md)

## Stack & Competenze
- **Hardware & Embedded:** ESP32, MPU-6050 (I2C), GPS (UART), microSD (SPI), elettronica di alimentazione 12 V→5 V, protezioni IP65/fusibili
- **Metodologia:** Documentazione tracciabile per provenienza fonte (`[TUO]`, `[XB20]`, `[FAM]`, `[DERIV]`) + ADR-Driven
