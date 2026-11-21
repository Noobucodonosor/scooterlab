# ADR-0007: Estensione `.slab` v1 (`REC_CAN` e `REC_HEALTH`) & Report Avanzato

- **Stato:** Accettato (`Accepted`)
- **Priorità:** P2 — Media
- **Data:** 2026-11-21
- **Autori:** noobucodonosor / Audit Multifocale 2026
- **Issue collegate:** `#16` (`TASK-DATA-05`), `#8` (`TASK-DATA-02`), `#9` (`TASK-DATA-03`)

---

## 1. Contesto e Problema

Il formato binario `.slab` v1 (`ADR-0004`) definiva `SLAB_REC_CAN = 3` senza layout binario né supporto nel codec Python/C++, e non tracciava i dati di salute elettrica/termica (`IGN_SENSE` tensione regolatore SYM `14,0–14,8 V`, temperatura vano sottosella). Inoltre `tools/analyze.py` manteneva l'HTML inline invece del template `tools/templates/report.html` previsto da `TASK-DATA-02`.

---

## 2. Decisione Architetturale

1. **Estensione Retrocompatibile `.slab` v1 (TLV Record Types 3 e 4):**
   - **`SLAB_REC_CAN = 3` (20 byte):** `t_ms` (`uint32`), `can_id` (`uint32`), `dlc` (`uint8`), `reserved[3]` (`uint8[3]`), `data[8]` (`uint8[8]`).
   - **`SLAB_REC_HEALTH = 4` (8 byte):** `t_ms` (`uint32`), `vbat_mv` (`uint16`), `temp_dc` (`int16`, deci-°C).
   - `tools/slab_codec.py` mantiene `read_slab()` retrocompatibile (3-tuple) e introduce `read_slab_full()` (5-tuple con `CanRecord` e `HealthRecord`).
2. **Template `tools/templates/report.html` & Grafico Spettro Vibrazioni:**
   - Estrazione del template HTML in `tools/templates/report.html`, aggiunta del grafico SVG dello spettro vibrazioni (con indicazione banda Nyquist) e stato regolatore SYM (`14,0–14,8 V`).
3. **Chiusura Loop Livello 2 & Profilo `sdkconfig.prod.defaults`:**
   - Hook opzionale in `tools/ingest_server.py` (`SCOOTERLAB_MQTT_ENABLED=1`) verso `mqtt_publisher.py` (fail-safe: un broker offline non blocca l'upload HTTP 200).
   - File separato `firmware/sdkconfig.prod.defaults` con Secure Boot v2, Flash Encryption, NVS Encryption e OTA Rollback per la build di produzione su scooter.

---

## 3. Conseguenze

- **Positivi:** Retrocompatibilità totale con tutti i file `.slab` v1 esistenti, diagnosi immediata di regolatore/batteria SYM e spettro vibrazioni leggibile, loop Livello 2 completo end-to-end.
- **Trade-off:** Leggero incremento di complessità in `analyze.py` per gestire il template esterno e i record opzionali `HealthRecord`.

---

## 4. Task Operativi Collegati

- [x] **TASK-DATA-05** (`#16`): Estensione `.slab` (`REC_CAN`/`REC_HEALTH`), `tools/templates/report.html`, loop Livello 2 e `sdkconfig.prod.defaults`.
