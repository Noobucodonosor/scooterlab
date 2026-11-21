# ADR-0005: Smart Garage Container Stack, TLS End-to-End & Hardening Ingest

- **Stato:** Accettato
- **Data:** 2026-11-21
- **Autori:** noobucodonosor / Audit Multifocale 2026
- **Issue collegate:** `#11` (`TASK-INFRA-01`)

---

## 1. Contesto e Problema

L'audit multifocale del repository ha evidenziato criticità bloccanti nello stack Smart Garage (`docker/` + `tools/ingest_server.py` + `tools/mqtt_publisher.py`):
1. **Mismatch TLS Firmware ↔ Garage:** `firmware/src/config_nvs.cpp` rifiuta URL `http://`, ma `docker/docker-compose.yml` non montava la directory certificati e avviava `ingest_server.py` in chiaro.
2. **Hardening HTTP insufficiente:** `ingest_server.py` usava `HTTPServer` single-threaded senza timeout socket (rischio Slowloris), non gestiva `Content-Length` non numerico (`ValueError` → 500) e sovrascriveva silenziosamente sessioni esistenti su collisione di `X-Session-Name`.
3. **Mosquitto & Credenziali MQTT:** `docker/mosquitto.conf` impostava `allow_anonymous false` senza `password_file` (bloccando qualsiasi connessione), mentre `mqtt_publisher.py` passava `-P <password>` via CLI a `mosquitto_pub` (esposizione in process table).
4. **Container Privilegiato:** `docker/Dockerfile.ingest` eseguiva il processo come `root` senza `HEALTHCHECK`.

---

## 2. Decisione Architetturale

1. **Ingest Server Hardened (`tools/ingest_server.py`):**
   - Passaggio a `ThreadingHTTPServer` con timeout socket (`15s`) per request handler.
   - Endpoint `GET /health` per `HEALTHCHECK` container (senza esposizione dati).
   - Validazione rigorosa di `Content-Length` (gestione `ValueError` → `400 Bad Request`) e scrittura su file temporaneo a chunk (riduzione picco RAM).
   - Gestione non distruttiva delle collisioni su `X-Session-Name`: se `<name>.slab` esiste già, salvataggio incrementale `<name>_1.slab`, `<name>_2.slab`, ecc.
2. **TLS End-to-End & Docker Stack (`docker/`):**
   - `docker/docker-compose.yml` monta `../certs:/etc/scooterlab/certs:ro` su `scooterlab-ingest` e propaga `SCOOTERLAB_TLS_CERT` / `SCOOTERLAB_TLS_KEY`.
   - `docker/Dockerfile.ingest` esegue come utente non-root `scooterlab` e definisce un `HEALTHCHECK` TCP sulla porta di ascolto.
   - `docker/mosquitto.conf` espone il listener locale `1883` vincolato a `127.0.0.1` in `docker-compose.yml` per uso locale out-of-the-box, con sezione commentata pronta per `8883` TLS + `password_file`.
3. **MQTT Publisher Sicuro (`tools/mqtt_publisher.py`):**
   - Rimozione di `subprocess` + `mosquitto_pub -P` a favore della libreria `paho-mqtt` (`[project.optional-dependencies] uns` in `tools/pyproject.toml`), con supporto opzionale TLS CA (`SCOOTERLAB_MQTT_CA_CERT`).

---

## 3. Conseguenze

- **Positivi:** Eliminazione esposizione password in process table, nessuna sovrascrittura accidentale di sessioni `.slab`, container non-root con healthcheck, compatibilità TLS end-to-end con il firmware ESP32.
- **Trade-off:** `paho-mqtt` diventa una dipendenza runtime per chi usa `mqtt_publisher.py` (inclusa automaticamente nell'immagine Docker).

---

## 4. Task Operativi Collegati

- [x] **TASK-INFRA-01** (`#11`): Hardening `ingest_server.py`, migrazione `paho-mqtt`, fix `docker/` e formalizzazione `ADR-0005`.
