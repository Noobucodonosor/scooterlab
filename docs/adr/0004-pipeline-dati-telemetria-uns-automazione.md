# ADR-0004: Pipeline Dati Telemetria, Unified Namespace (UNS) e Automazione Manutenzione

- **Stato:** Proposto (`Proposed`)
- **Priorità:** P1 — Alta
- **Data:** 2026-11-20
- **Autori:** Daniele Bertuccio (`@Noobucodonosor`)
- **Fonti:** Audit stack IoT/Edge 2023–2026 (Node-RED 4.1, MQTT/UNS, n8n); [`docs/01-istruzioni-montaggio-livello-0.md`](../01-istruzioni-montaggio-livello-0.md); [`docs/02-dati-tecnici-verificati.md`](../02-dati-tecnici-verificati.md)

---

## 1. Contesto e Problema

Il flusso dati previsto nella guida Livello 0 (`ESP32 → HTTP upload → tools/ingest_server.py → analyze.py → HTML statico`) è eccellente per validare la catena in modo autonomo e leggero, ma mostra tre limiti non appena il progetto passa dalla prima prova all'uso continuativo sullo scooter:

1. **Accoppiamento rigido:** Il server di ingestione esegue direttamente l'analisi bloccando l'estendibilità verso dashboard storiche, confronti multi-sessione A/B o notifiche automatiche.
2. **Nessuna correlazione con la manutenzione reale del mezzo:** Il SYM Symphony ST 200i ha scadenze di manutenzione molto ravvicinate (`[TUO]`): olio motore ogni **3.000 km**, olio trasmissione e filtro aria ogni **6.000 km**, filtro pompa benzina a **10.000 km**, cinghia/rulli/candela ogni **12.000 km**. Integrare il chilometraggio cumulato dalle tracce GPS consente di automatizzare gli alert di officina e correlare il degrado delle prestazioni (es. 0–50 km/h o banda CVT 7.600–8.100 rpm) con l'usura di cinghia e rulli.
3. **Gestione dipendenze Python non isolata:** Le istruzioni citano un `pip install numpy pandas scipy matplotlib` globale, contrario alle best practice moderne di riproducibilità.

---

## 2. Decisione Architetturale

Si adotta una **pipeline modulare a due velocità (Offline-First + Bridge UNS/Automazione opzionale)**, applicando in scala domestica/maker il pattern 2026 di separazione tra acquisizione edge e orchestrazione IT:

1. **Livello Core (Offline-First — Obbligatorio):**
   - **Formato binario `.slab`** su microSD con header di versione, metadati sessione (`build_level`, sample rate IMU/GPS) e checksum CRC32 per rilevare corruzioni.
   - **Toolkit Python (`tools/`)** isolato tramite `pyproject.toml` / virtual environment (`uv` o `venv`), contenente:
     - `make_test_session.py`: generatore di sessioni sintetiche per validare la pipeline senza hardware.
     - `analyze.py`: parser `.slab` → calcolo KPI (velocità GPS, tempo 0–50 km/h, istogramma angoli di piega, indice comfort, spettro FFT vibrazioni) + generazione report HTML autocontenuto + confronto A/B rispetto alla mediana della baseline di 3 giri.
     - `ingest_server.py`: ricevitore HTTPS/autenticato (cfr. `ADR-0003`) che archivia la sessione in locale e invoca `analyze.py`.
2. **Livello Esteso (Opzionale — Pattern UNS + Automazione 2026):**
   - **Broker MQTT / Mini-UNS domestico** (es. Mosquitto o EMQX in container Docker/Podman) con topic gerarchici puliti:
     - `scooterlab/symphony200/telemetry/session_summary` (KPI aggregati post-giro, mai coordinate GPS raw su broker condivisi)
     - `scooterlab/symphony200/maintenance/odometer_km`
     - `scooterlab/symphony200/health/battery_v`
   - **Node-RED (v4.1.x):** Eventuale nodo di acquisizione/normalizzazione edge in garage (es. stato batteria, sensori ambiente officina, bridge verso Home Assistant).
   - **n8n (Orchestrazione IT & Alert):** Consumatore di eventi discreti a valle di webhook/MQTT per:
     - Inviare notifica Telegram/email con il riepilogo KPI del giro appena concluso;
     - Aggiornare il registro chilometrico e generare promemoria automatici prima dei tagliandi SYM (`3.000 / 6.000 / 10.000 / 12.000 km`).

---

## 3. Conseguenze

- **Positive:**
  - Chi vuole usare ScooterLab in modo semplice può limitarsi a microSD + `tools/analyze.py` senza alcun server o container.
  - Chi dispone di un home server / Raspberry Pi ottiene telemetria storica, tracciamento automatico dei tagliandi e notifiche zero-effort tramite il pattern standard 2026 (MQTT/UNS + Node-RED + n8n).
  - Ambiente Python riproducibile e testabile con sessioni sintetiche.
- **Trade-off / Vincoli:**
  - Definizione rigorosa dello schema binario `.slab` (versionato) per garantire retrocompatibilità tra firmware Livello 0, 1 e 2.
  - Evitare K3s/Kubernetes su singolo nodo domestico (complessità non giustificata; Docker/Podman Compose è sufficiente).

---

## 4. Task Operativi Collegati (con Definition of Done)

- [ ] **TASK-DATA-01**: **Specifica formato binario `.slab` v1 e generatore sintetico**
  - *File coinvolti*: `docs/04-formato-slab.md`, `tools/pyproject.toml`, `tools/make_test_session.py`
  - *Acceptance Criteria*: Specifica binaria documentata (header + record IMU/GPS + CRC32); `make_test_session.py --level0` genera un file `.slab` valido e deterministico in un virtualenv isolato.
  - *Verification Step*: `python3 tools/make_test_session.py --level0 && pytest tools/tests/`
- [ ] **TASK-DATA-02**: **Parser telemetria `analyze.py` con report HTML e confronto A/B**
  - *File coinvolti*: `tools/analyze.py`, `tools/templates/report.html`
  - *Acceptance Criteria*: Estrae velocità, 0–50 km/h, angolo di piega, comfort e spettro vibrazioni da `.slab`; supporta flag `--baseline` per confronto A/B.
  - *Verification Step*: `python3 tools/analyze.py sessions/sess00002.slab --label "prova"` genera un report HTML valido senza errori.
- [ ] **TASK-DATA-03**: **Integrazione opzionale MQTT/UNS & scadenziario manutenzione SYM**
  - *File coinvolti*: `tools/maintenance_tracker.py`, `tools/mqtt_publisher.py`
  - *Acceptance Criteria*: Pubblica riepilogo KPI (privo di coordinate GPS raw) su topic `scooterlab/symphony200/...` e calcola i km residui ai tagliandi SYM (`3k / 6k / 10k / 12k km`).
  - *Verification Step*: Unit test del calcolo scadenze manutenzione a partire da un chilometraggio iniziale configurabile.
