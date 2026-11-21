# ScooterLab — BOM Rev. 2 (2026) & Pinout SPI / UART / TWAI

- **Riferimento ADR:** [`ADR-0002`](./adr/0002-aggiornamento-hardware-sensori-2026.md)
- **Veicolo Target:** SYM Symphony ST 200i ABS 2019 (`XB20E2-EU`)
- **Ambiente Operativo:** Vano sottosella anteriore (soggetto a calore motore `[TUO]`, vibrazioni monocilindrico 169 cc, umidità)

---

## 1. Distinta Base (BOM Rev. 2 — 2026)

| Componente | Modello Consigliato (2026) | Alternativa | Temp. Operativa | Bus / Interfaccia | Costo Stimato |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **MCU Edge** | **ESP32-S3 DevKitC-1** (N16R8, USB nativo, TWAI/CAN) | **ESP32-C5 DevKit** (Wi-Fi 6 dual-band 2,4/5 GHz + TWAI) | -40 / +85 °C | SPI, UART, TWAI, Wi-Fi/BLE | 8–14 € |
| **Smart IMU 6-Assi** | **ST `ISM330IS`** (grado industriale + core AI **ISPU**) | **ST `LSM6DSO16IS`** / **Bosch `BHI360`** | -40 / +85 °C (+105 °C ISM) | **SPI** (1–4 kHz) | 12–20 € |
| **Modulo GNSS** | **u-blox MAX-M10S / NEO-M10** (GPS+Galileo, 5–10 Hz) | NEO-M8N (5 Hz) | -40 / +85 °C | **UART1** (115200 bps) | 15–22 € |
| **Storage Offline** | Modulo microSD SPI + **SanDisk / Samsung High Endurance 32 GB** | Industrial SLC/pSLC microSD | -25 / +85 °C | **SPI** (CS dedicato) | 10–14 € |
| **Alimentazione 12V→5V** | Buck DC-DC automotive step-down 12 V → 5 V (≥2 A, es. LM2596/MP1584 schermato) | Modulo DC-DC isolato 9–36 V → 5 V | -40 / +85 °C | Positivo sottochiave | 5–10 € |
| **Protezione & Hold-Up** | Portafusibile stagno + fusibile **1 A** + **TVS `SMBJ18A`** (12 V) + Schottky `SS34` + **`4700 µF / 10 V` low-ESR** (inrush `2.2 Ω`) + partitore `IGN` | — | -40 / +85 °C | GPIO ADC / Interrupt | 5–8 € |
| **CAN Transceiver (Liv. 1/2)** | **TI `SN65HVD230`** (3,3 V, modalità *listen-only*) | MCP2562FD | -40 / +125 °C | **TWAI** (OBD CAN-H/L) | 3–5 € |
| **Meccanica & Cablaggio** | Scatola stagna **IP65**, piastra in **PETG/ASA** (mai PLA), connettori **JST-PH/SH** (mai Dupont), Posi-Tap | Pressacavi PG7 | ≥ 85 °C (PETG/ASA) | — | 12–18 € |

---

## 2. Tabella Pinout Verificata (ESP32-S3 — Zero Conflitti di Strapping)

> **Nota ESP32-S3:** Evitare i pin di strapping critici (`GPIO0`, `GPIO3`, `GPIO45`, `GPIO46`) e la coppia USB nativa (`GPIO19`, `GPIO20`) per mantenere attivo il debug USB-CDC.

| Funzione | Segnale | GPIO ESP32-S3 | Note Tecniche |
| :--- | :--- | :--- | :--- |
| **Bus SPI2 (Smart IMU dedicato)** | `SCK` | `GPIO12` | Bus dedicato ad alta frequenza (1–4 kHz), cavi < 10 cm |
| | `MOSI` | `GPIO11` | |
| | `MISO` | `GPIO13` | |
| **Smart IMU (`ISM330IS`)** | `CS_IMU` | `GPIO10` | Chip Select dedicato IMU (priorità campionamento) |
| | `INT1_IMU` | `GPIO9` | Interrupt data-ready / evento ISPU |
| **Bus SPI3 (microSD dedicato)** | `SD_SCK` | `GPIO36` | Bus separato per evitare stalli IMU su flush SD (su Octal PSRAM usare GPIO7/8/15) |
| | `SD_MOSI` | `GPIO35` | |
| | `SD_MISO` | `GPIO37` | |
| **microSD High Endurance** | `CS_SD` | `GPIO14` | Chip Select dedicato microSD (alimentazione 5 V / LDO locale) |
| **GNSS (UART1)** | `GPS_RX` (← TX modulo) | `GPIO18` | Incrociare TX modulo → RX MCU |
| | `GPS_TX` (→ RX modulo) | `GPIO17` | Incrociare RX modulo → TX MCU |
| **Monitor Alimentazione `IGN`** | `IGN_SENSE` (ADC/INT) | `GPIO4` | Partitore 12 V → 2,5 V max; trigger `fsync()` allo spegnimento |
| **CAN / TWAI (Livello 1/2)** | `CAN_TX` | `GPIO5` | Verso `SN65HVD230` (in modalità *listen-only* TX disabilitato via software) |
| | `CAN_RX` | `GPIO6` | Lettura passiva bus OBD Symphony ST 200i |
| **LED Stato** | `STATUS_LED` | `GPIO2` | Diagnostica rapida boot / fix GPS / upload TLS |
