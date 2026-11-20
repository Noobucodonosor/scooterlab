# ADR-0001: Architettura Hardware & Telemetria IoT Livello 0 (ESP32 + IMU + GPS)

- **Stato:** Accepted (Specifica Hardware & Cablaggio pronta — Firmware in roadmap)
- **Data:** 2026-11-20
- **Autori:** Daniele Bertuccio
- **Target:** SYM Symphony ST 200i ABS 2019 (XB20E2-EU)

---

## 1. Contesto e Obiettivo

Progettare una centralina di telemetria IoT **non invasiva (Livello 0)** per scooter 4T, capace di registrare cinematica, traiettoria e dinamica di guida senza smontare carenature e senza interferire con la ECU di serie.

## 2. Decisione Architetturale (Hardware & Alimentazione)

- **MCU:** ESP32 DevKit (Wi-Fi/BLE per scarico dati e futura diagnostica).
- **Sensoristica:**
  - **IMU 6-assi `MPU-6050`** (I2C) per accelerazione longitudinale/laterale e angolo di piega/vibrazioni.
  - **Modulo GPS** (UART) per traccia, velocità reale e sincronizzazione temporale UTC.
- **Storage Locale:** Modulo **microSD** (32 GB) per logging deterministico offline ad alta frequenza.
- **Alimentazione & Protezione Veicolare:**
  - Prelievo su **positivo sottochiave** (evita scarica batteria a veicolo fermo).
  - **Fusibile 1 A** con portafusibile in linea.
  - **Convertitore Buck DC-DC 12 V → 5 V** tarato a banco con multimetro prima del collegamento.
  - Contenitore stagno **IP65** fissato nel vano sottosella/portaoggetti.

## 3. Fasi di Realizzazione

1. **Fase A — Banco:** assemblaggio e test alimentazione + bus I2C/UART/SPI.
2. **Fase B — Rilievo del vano:** quote, fissaggi e passaggio cablaggi sul mezzo reale.
3. **Fase C / C2 — Alimentazione & Montaggio:** taratura buck, positivo sottochiave, scatola IP65.
4. **Fase D — Primo giro & Firmware (Roadmap):** calibrazione IMU, registrazione sessione su microSD e generazione report di guida.
