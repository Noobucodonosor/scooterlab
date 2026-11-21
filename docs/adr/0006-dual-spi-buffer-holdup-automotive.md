# ADR-0006: Dual-SPI (`SPI2`/`SPI3`), Ring-Buffer SD 4 KB, Hold-Up & Protezione TVS 12 V

- **Stato:** Accettato (`Accepted`)
- **Priorità:** P1 — Alta
- **Data:** 2026-11-21
- **Autori:** noobucodonosor / Audit Multifocale 2026
- **Issue collegate:** `#13` (`TASK-HW-05`)

---

## 1. Contesto e Problema

La Rev. 2 iniziale (`ADR-0002`) presentava tre rischi di affidabilità su strada:
1. **Contesa su bus SPI2 condiviso:** Smart IMU (`1–4 kHz`) e microSD condividevano `SPI2` (`GPIO11/12/13`), esponendo il campionamento IMU a blocchi durante le latenze di scrittura SD (10–50 ms).
2. **Write amplification su FATFS:** `SlabWriter::write_record` eseguiva due `fwrite()` da 4 e 20 byte per ogni record senza buffer applicativo da 4 KB.
3. **Circuito Hold-Up e Transienti 12 V non dimensionati:** Mancavano capacità, ESR, limitazione inrush per garantire ≥ 200 ms di autonomia allo spegnimento quadro, e un diodo TVS automotive sulla linea 12 V sottochiave.

---

## 2. Decisione Architetturale

1. **Separazione Bus Dual-SPI (ESP32-S3):**
   - **`SPI2` (dedicato Smart IMU `ISM330IS`):** `SCK=GPIO12`, `MOSI=GPIO11`, `MISO=GPIO13`, `CS_IMU=GPIO10`, `INT1_IMU=GPIO9`.
   - **`SPI3` (dedicato microSD High Endurance):** `SD_SCK=GPIO36`, `SD_MOSI=GPIO35`, `SD_MISO=GPIO37`, `CS_SD=GPIO14` (nessun conflitto con USB-CDC `GPIO19/20` né strapping `GPIO0/3/45/46`; su moduli Octal PSRAM verificare disponibilità `GPIO35–37` o rimappare su `GPIO7/8/15`).
2. **Block-Buffer 4 KB in `SlabWriter`:**
   - Buffer RAM da `4096` byte (`buf_`) con flush automatico al raggiungimento di 4 KB e flush esplicito in `close_safe()` prima di `END!` + `fsync()`.
3. **Protezione Transienti 12 V & Dimensionamento Hold-Up (≥ 200 ms):**
   - Ingresso 12 V sottochiave: Fusibile 1 A → **TVS unidirezionale/bidirezionale `SMBJ18A`** (clamp transienti load-dump/bobina) → Buck DC-DC 12 V → 5 V.
   - Rail 5 V post-buck: Diodo Schottky (`SS34` / `MBR140`) → resistore limitazione inrush `2.2 Ω / 1 W` → **Condensatore bulk `4700 µF / 10 V` low-ESR** (a 250 mA medi senza Wi-Fi attivo durante `fsync()`, $\Delta V \approx 1.0\text{ V}$ in ~200 ms, mantenendo l'LDO 3,3 V sopra dropout).

---

## 3. Conseguenze

- **Positivi:** Zero stalli IMU durante flush SD, ~170× meno chiamate `fwrite()` su FATFS, protezione elettrica reale su impianto 12 V del monocilindrico 169 cc.
- **Trade-off:** 3 GPIO aggiuntivi dedicati a `SPI3` e ingombro leggermente maggiore del condensatore `4700 µF` nella scatola IP65.

---

## 4. Task Operativi Collegati

- [x] **TASK-HW-05** (`#13`): Formalizzazione `ADR-0006`, aggiornamento `docs/bom-rev2-2026.md` / `platformio.ini` e block-buffer 4 KB in `SlabWriter`.
- [ ] **Driver hardware su banco:** Implementare driver SPI `ISM330IS`, UART `u-blox M10` e ADC `IGN_SENSE` su ESP32-S3 reale.
