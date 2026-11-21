# ADR-0003: Sicurezza, Hardening (RED EN 18031 / CRA-Ready) e Privacy

- **Stato:** Accettato (`Accepted`)
- **Priorità:** P0 — Critica
- **Data:** 2026-11-20
- **Autori:** Daniele Bertuccio (`@Noobucodonosor`)
- **Fonti:** Audit normativo UE 2025–2026 (Direttiva RED Reg. 2022/30 & EN 18031, Cyber Resilience Act); [`docs/01-istruzioni-montaggio-livello-0.md`](../01-istruzioni-montaggio-livello-0.md)

---

## 1. Contesto e Problema

Le istruzioni originali di Livello 0 ([`docs/01-istruzioni-montaggio-livello-0.md`](../01-istruzioni-montaggio-livello-0.md)) adottano pratiche tipiche dei prototipi IoT del 2023 che nel 2026 risultano insicure e non conformi ai principi di *security-by-design*:

1. **Credenziali Wi-Fi hardcoded nel firmware:** `HOME_SSID` e `HOME_PASS` inseriti in chiaro in testa al file `.ino`. Un eventuale furto dello scooter o della centralina esporrebbe le credenziali della rete domestica, oltre al rischio di commit accidentale nel repository pubblico.
2. **Upload telemetria in chiaro senza autenticazione:** Invio delle sessioni via `http://192.168.1.50:8500/upload` senza TLS e senza token di autenticazione. Le tracce GPS contengono dati altamente sensibili (posizione di casa, abitudini, orari di parcheggio).
3. **Assenza di verifica integrità firmware:** Nessun Secure Boot, nessun OTA firmato e nessuna protezione da downgrade.
4. **Esposizione in repository pubblico:** Il repository `Noobucodonosor/scooterlab` è pubblico; eventuali dati reali di officina (targa, telaio/VIN) o sessioni GPS committate per errore costituirebbero un data leak irreversibile.

*Nota normativa:* Essendo ScooterLab un prototipo personale non immesso sul mercato UE, non ricade negli obblighi formali di marcatura CE della **Direttiva RED (EN 18031-1/2/3, applicabile dal 1° agosto 2025)** o del **Cyber Resilience Act (notifiche ENISA/CSIRT attive dall'11 settembre 2026, piena applicazione 11 dicembre 2027)**. Adottare comunque questi requisiti fin dal giorno zero protegge i dati personali del proprietario e rende l'architettura riutilizzabile in contesti professionali o commerciali.

---

## 2. Decisione Architetturale

1. **Zero Segreti nel Codice & NVS Encryption:**
   - Rimozione totale di SSID, password Wi-Fi, IP fissi e token dal codice sorgente.
   - Salvataggio delle configurazioni sensibili nella partizione **NVS cifrata** di ESP-IDF (oppure in file `.env` / `secrets.h` rigorosamente esclusi da `.gitignore` durante lo sviluppo a banco).
   - Provisioning iniziale tramite BLE/SoftAP protetto da PIN univoco (nessuna password di default condivisa, in linea con EN 18031).
2. **Trasporto Cifrato e Autenticato (Garage Upload):**
   - Sostituzione di `http://...:8500/upload` con **HTTPS (TLS 1.3)** o **MQTTS (TLS)** verso il server domestico, con certificato CA pinnato nel firmware e autenticazione tramite **Bearer Token** (o certificato client mTLS).
3. **Catena di Avvio e Aggiornamenti Sicuri (SUM — Secure Update Mechanism):**
   - Abilitazione di **Secure Boot v2**, **Signed OTA Verification** e **OTA Downgrade Protection** (nativi in ESP-IDF v6.x).
   - In caso di adozione futura di ESPHome (serie `2026.11+`), mantenere attivi i medesimi flag nativi.
4. **Accesso Remoto Zero Trust (ZTNA) & Rete Domestica:**
   - Nessun port-forwarding sul router di casa per esporre il server di ingestione o la dashboard report.
   - Per consultare i report o gestire il server da remoto/officina, utilizzare esclusivamente una mesh **WireGuard Zero Trust** (**Tailscale** o **NetBird** self-hosted).
   - Se la rete domestica/lab impiega stack Nethesis, utilizzare **NethSecurity 8** (gateway/firewall perimetrale) separato da **NethServer 8** (servizi container), escludendo qualsiasi istanza NethServer 7 (EOL giugno 2024).
5. **Policy Privacy & Igienizzazione Repository Pubblico:**
   - `.gitignore` rigoroso su `sessions/`, `reports/`, `*.slab`, `*.gps.csv`, `*.gpx`, `.env`, `secrets.h`, `private/`.
   - I dati di officina del mezzo (es. chilometri percorsi per scadenziario manutenzione) possono essere registrati nei documenti pubblici **solo in forma anonimizzata** (mai targa, mai numero di telaio VIN, mai nominativi o protocolli identificativi).

---

## 3. Conseguenze

- **Positive:**
  - Protezione completa della rete Wi-Fi domestica e delle tracce GPS personali anche in caso di furto fisico della centralina dallo scooter.
  - Progetto nativamente pronto per eventuale evoluzione a prodotto commerciale conforme a RED (EN 18031) e CRA (inclusa tracciabilità dipendenze/SBOM).
- **Trade-off / Vincoli:**
  - Prima attivazione leggermente più articolata rispetto a uno sketch Arduino hardcoded (generazione certificato TLS locale e configurazione `.env` / NVS).
  - L'abilitazione irreversibile degli eFuse di Secure Boot v2 va eseguita **solo a firmware stabile** (durante la Fase A a banco si opera in modalità debug/sviluppo con chiavi di test).

---

## 4. Task Operativi Collegati (con Definition of Done)

- [ ] **TASK-SEC-01**: **Configurazione `.gitignore`, `.env.example` e pre-release secret check**
  - *File coinvolti*: `.gitignore`, `.env.example`, `AGENTS.md`
  - *Acceptance Criteria*: Tutti i pattern sensibili (`*.slab`, `*.gps.csv`, `secrets.h`, `.env`, `*.key`) sono esclusi da Git; lo script `pre_release_check.py` passa senza errori.
  - *Verification Step*: `python3 ~/.gemini/config/skills/adr-github-methodology/scripts/pre_release_check.py`
- [ ] **TASK-SEC-02**: **Provisioning sicuro Wi-Fi/Token con NVS cifrata nel firmware**
  - *File coinvolti*: `firmware/src/config_nvs.cpp`, `firmware/partitions.csv`
  - *Acceptance Criteria*: Nessuna credenziale hardcoded nel repository; il firmware carica SSID/PASS e Bearer Token da partizione NVS cifrata.
  - *Verification Step*: Scansione grep sul codice sorgente (`git grep -i "HOME_PASS"`) con 0 corrispondenze reali e test di connessione Wi-Fi a banco.
- [ ] **TASK-SEC-03**: **Endpoint di ingestione HTTPS/TLS con autenticazione Bearer Token**
  - *File coinvolti*: `tools/ingest_server.py`, `firmware/src/uploader.cpp`
  - *Acceptance Criteria*: Il server rifiuta connessioni prive di token valido (`401 Unauthorized`) e accetta upload solo su TLS (o dietro reverse proxy TLS / mesh Tailscale-NetBird).
  - *Verification Step*: Test `curl` senza token → `401`; test `curl` con token valido e file `.slab` sintetico → `200 OK`.
