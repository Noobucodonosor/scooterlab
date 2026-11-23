# ADR-0002: Aggiornamento Hardware, MCU, Smart IMU e Sensoristica (Revisione 2026)

- **Stato:** Accettato (`Accepted`) — Evoluzione della baseline [`ADR-0001`](./0001-architettura-telemetria-iot-esp32.md)
- **Priorità:** P1 — Alta
- **Data:** 2026-11-20
- **Autori:** noobucodonosor (`@Noobucodonosor`)
- **Fonti:** Audit stack IoT/Embedded 2023–2026; [`ADR-0001`](./0001-architettura-telemetria-iot-esp32.md); [`docs/02-dati-tecnici-verificati.md`](../02-dati-tecnici-verificati.md)

---

## 1. Contesto e Problema

La baseline hardware definita in [`ADR-0001`](./0001-architettura-telemetria-iot-esp32.md) (ESP32 DevKit classico, IMU `MPU-6050` su I2C, programmazione via Arduino IDE) è funzionale per un primo prototipo da banco, ma alla fine del 2026 presenta quattro criticità strutturali rispetto allo stato dell'arte e ai vincoli reali del **SYM Symphony ST 200i ABS**:

1. **Obsolescenza e deriva termica della `MPU-6050`:** Il chip InvenSense MPU-6050 è fuori produzione da anni (il mercato è saturo di cloni con rumore elevato e forte drift termico). Il libretto ufficiale del Symphony (`[TUO]`) avverte esplicitamente che il **vano sottosella si scalda** per irraggiamento dal motore: una IMU consumer su I2C subisce deriva su roll/pitch e richiede calibrazioni manuali fragili (2 secondi sul cavalletto centrale).
2. **Saturazione del bus I2C ad alta frequenza:** Per l'analisi vibrazionale della trasmissione CVT (cinghia, rulli 18×14 mm, campana frizione) e del monocilindrico 169 cc fino a 8.000 rpm (~133 Hz fondamentale + armoniche oltre 1 kHz), il bus I2C classico si satura rapidamente (>70% di occupazione a pochi kHz), impedendo campionamenti puliti.
3. **Ciclo di vita SDK e compatibilità futura (Livello 1/2):** `ESP-IDF v5.2` ha raggiunto l'End-of-Life ad agosto 2026; inoltre il Symphony dispone di **bus CAN sul connettore OBD** (ECU motore + centralina ABS), quindi la MCU scelta deve esporre un controller **CAN/TWAI nativo** per abilitare il futuro Livello 1/2 senza cambiare scheda.
4. **Connettività cellulare futura (eventuale Livello 2 antifurto/live):** Le reti 2G/3G sono in dismissione tra 2025 e 2026; eventuali futuri moduli GSM/GPRS legacy sono da escludere a priori.

---

## 2. Decisione Architetturale

Si definisce lo **Stack Hardware Target 2026 (Rev. 2)** mantenendo invariato il principio di **non invasività** (positivo sottochiave, fusibile 1 A, buck 12 V → 5 V, scatola IP65, piastra in PETG/ASA):

1. **Microcontrollore (MCU) — Espressif generazione 2026 con TWAI nativo:**
   - **Scelta primaria consigliata:** **ESP32-S3** (dual-core 240 MHz, BLE 5.0, USB nativo, controller **CAN/TWAI**, maturo su ESP-IDF v6.x) oppure **ESP32-C5** (RISC-V 240 MHz, **Wi-Fi 6 dual-band 2,4/5 GHz** per scarico rapido delle sessioni in garage, BLE 5, TWAI, supporto PSRAM esterna).
   - **Esclusioni motivate:** Scartati `ESP32-P4` (privo di radio integrata, richiede co-processore e PCB doppio), schede SBC ad alto consumo come Raspberry Pi 5 / AI HAT+ 2 o Arduino VENTUNO Q (40 TOPS inutili su scooter, incompatibili con il budget termico del vano sottosella e con la batteria da 12 V / 6 Ah `[TUO]`).
2. **SDK & Build System:**
   - Adozione di **ESP-IDF v6.0 / v6.1.1** (via PlatformIO o toolchain nativa ESP-IDF) in C/C++ per garantire logging deterministico su microSD, supporto nativo a Secure Boot v2 / NVS encryption e manutenzione attiva post-EOL di v5.2.
3. **Sensoristica Inerziale — Smart IMU con In-Sensor AI su bus SPI:**
   - Sostituzione della `MPU-6050` con una **Smart IMU di grado industriale/automotive (-40 / +85 °C)**:
     - **Opzione A (Consigliata — Analisi vibrazionale & Edge AI):** **STMicroelectronics `ISM330IS`** (grado industriale, ideale per vano caldo) o **`LSM6DSO16IS`**, dotate di core RISC 32-bit **ISPU** (40 KB RAM) capace di eseguire sensor fusion, filtraggio FFT/SDFT e rilevamento anomalie/cadute direttamente nel sensore a consumi µW/sub-mA.
     - **Opzione B (Sensor fusion quaternionica plug-and-play):** **Bosch Sensortec `BHI360`** (core Fuser2 integrato per orientamento 3D/roll/pitch compensato senza deriva) oppure `TDK ICM-42688-P` (altissima precisione a basso rumore).
   - **Bus di collegamento:** Collegamento della IMU su **SPI** (con CS dedicato, separato dalla microSD o su secondo bus HSPI/VSPI) per sostenere campionamenti 1–4 kHz senza saturare I2C. *(Nota: MIPI I3C a 1,8 V è valutabile solo in caso di futura adozione di MCU STM32H5/U5/N6).*
4. **Storage, GPS e Connessioni Meccaniche:**
   - **microSD:** Obbligatoria scheda **Industrial / High Endurance** (32 GB, formattata FAT32, scrittura bufferizzata a blocchi con chiusura sicura al taglio del sottochiave tramite supercondensatore o rilevamento tensione `IGN`).
   - **GPS:** Modulo GNSS multi-costellazione (GPS+Galileo+GLONASS, es. serie u-blox M10) a 5–10 Hz su UART per migliorare l'accuratezza delle accelerazioni 0–50 km/h e delle traiettorie in curva.
   - **Cablaggio interno:** Connettori bloccanti **JST-SH/PH** o **Qwiic / STEMMA QT** fissati meccanicamente (nessun cavo Dupont).
5. **Predisposizione Livello 1/2 (CAN & WAN):**
   - **CAN Bus:** Predisporre su PCB/millefori lo zoccolo per transceiver **CAN `SN65HVD230`** (3,3 V) in ascolto *listen-only* sul connettore OBD del Symphony.
   - **WAN futura (solo se richiesto antifurto/live tracking):** Vietati moduli 2G/3G; usare esclusivamente **LTE Cat-1bis** o **NB-IoT 3GPP Rel-17 NTN** (es. Nordic `nRF9151`). Evitare 5G RedCap finché la copertura 5G Standalone (SA) non è capillare.

---

## 3. Conseguenze

- **Positive:**
  - Eliminazione del drift termico della IMU nel vano sottosella caldo e miglioramento drastico della precisione dell'angolo di piega.
  - Abilitazione della **diagnostica predittiva CVT** (vibrazioni cinghia/rulli/frizione via FFT/ISPU) senza sovraccaricare la MCU.
  - Hardware già pronto per il Livello 1/2 (bus CAN OBD + Wi-Fi 6 / BLE 5) e allineato al ramo attivo ESP-IDF v6.x.
- **Trade-off / Vincoli:**
  - Costo BOM leggermente superiore rispetto al kit `ESP32 + MPU-6050` (~15–25 € in più per Smart IMU industriale + GNSS M10 + microSD High Endurance).
  - La programmazione del core ISPU (ST) richiede toolchain dedicata ST (`st-mems-ispu`): in Fase 1 la IMU può essere usata in modalità standard SPI ad alta frequenza, abilitando i modelli ISPU in Fase 2.

---

## 4. Task Operativi Collegati (con Definition of Done)

- [x] **TASK-HW-01**: **Aggiornamento BOM Rev. 2 e pinout SPI/UART/TWAI**
  - *File coinvolti*: `docs/01-istruzioni-montaggio-livello-0.md`, `docs/bom-rev2-2026.md`
  - *Acceptance Criteria*: BOM completa con codici esatti per MCU (ESP32-S3 o ESP32-C5), Smart IMU industriale (`ISM330IS` o `BHI360`), GNSS 10 Hz, microSD High Endurance, buck DC-DC e connettori JST; tabella pinout priva di conflitti SPI/UART/TWAI.
  - *Verification Step*: Revisione incrociata pinout su datasheet Espressif e verifica assenza di pin di strapping critici.
- [x] **TASK-HW-02**: **Scaffold progetto firmware ESP-IDF v6.x / PlatformIO**
  - *File coinvolti*: `firmware/platformio.ini` (o `firmware/CMakeLists.txt`), `firmware/src/main.cpp`
  - *Acceptance Criteria*: Progetto compilabile in locale per ESP32-S3/C5 con driver modulari per IMU SPI, GNSS UART e microSD FAT32 + flag `BUILD_LEVEL` (0/1/2).
  - *Verification Step*: Compilazione pulita (`pio run` o `idf.py build`) con 0 errori e 0 warning critici.
- [x] **TASK-HW-03**: **Protezione chiusura file microSD su spegnimento quadro**
  - *File coinvolti*: `docs/01-istruzioni-montaggio-livello-0.md`, `firmware/src/power_monitor.cpp`
  - *Acceptance Criteria*: Circuito di rilevamento caduta tensione 12 V sottochiave (partitore + diodo Schottky + condensatore di hold-up) che garantisce ≥200 ms di autonomia per `fsync()` e chiusura pulita del file `.slab`.
  - *Verification Step*: Test a banco con 10 spegnimenti bruschi consecutivi senza corruzione del filesystem FAT32.
