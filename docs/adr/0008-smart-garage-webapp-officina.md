# ADR-0008: Smart Garage Web App, Procedure Guidate Officina & Digital Twin 3D Offline

- **Stato:** Accettato (`Accepted`)
- **Priorità:** P1 — Alta
- **Data:** 2026-11-21
- **Autori:** Daniele Bertuccio / Archeologia & Redesign 2026
- **Issue collegate:** `#21` (`TASK-APP-01`)

---

## 1. Contesto e Problema

Dopo il completamento della pipeline binaria `.slab` v1 (`ADR-0004`/`0007`) e del server `ingest_server.py` (`ADR-0005`), le capacità reali del progetto restavano frammentate tra script CLI isolati (`analyze.py`, `maintenance_tracker.py`) e documentazione statica Markdown (`docs/05-guida-officina-manutenzione-smontaggio.md`). L'utente aveva bisogno di un compagno operativo unico per:
1. Usare l'app anche da casa (generazione demo A/B, simulazione controlli) oltre che in garage su smartphone.
2. Essere guidato passo-passo in **qualsiasi** intervento sul SYM Symphony ST 200i (tagliando 30.000 km, check-up fabbrica, smontaggio scocche Liv. A–D, installazione ScooterLab Rev. 2, diagnostica guasti).
3. Disporre di un **modello 3D interattivo offline** derivato dalle quote reali verificate del veicolo e sincronizzato automaticamente con ogni step operativo.
4. Validare le proprie misure reali (`[XB20]`/`[TUO]`) e ispezionare telemetria + mappa con privacy zone senza servizi cloud esterni.

---

## 2. Decisione Architetturale

1. **Web App Local-First Zero-Dependency (`tools/webapp/`):**
   - Servita direttamente da `tools/ingest_server.py` sulla stessa porta (`:8500`, HTTPS TLS + Bearer opzionale / accesso diretto loopback & LAN ZTNA), senza build Node/React né CDN esterni.
   - Design system coerente **`stone-blueprint`** (`#dfdedb` / `#26251e` / `#2456d6`), ergonomia mobile con tap target ≥ 44 px.
2. **Motore Officina & Stato Locale (`tools/garage_store.py` → `tools/garage_state.json`):**
   - File JSON locale **sempre escluso da Git** (`.gitignore`) per salvare odometro cumulato, registro tagliandi eseguiti, misure verificate contro `FACTORY_SPECS` (`[TUO]`/`[XB20]`/`[FAM]`), avanzamento step delle procedure guidate e baseline A/B selezionata.
3. **Digital Twin 3D Parametrico Offline (`tools/webapp/scooter3d.js`):**
   - Motore 3D prospettico Canvas 2D in puro JavaScript costruito sulle dimensioni reali verificate del SYM Symphony ST 200i (passo 1350 mm, lunghezza 2000 mm, ruote 16", altezza sella 792 mm), con orbita 360° mouse/touch, zoom, modalità **Raggi-X** e focus automatico (`focusPart`) dal passo attivo della guida al relativo sottosistema (cestello sottosella, batteria/fusibili, centralina ScooterLab IP65, testa/valvole/candela, carter CVT, scudo/OBD, ruote/anelli ABS 50 fori).
   - Trasparenza ingegneristica: dichiarato esplicitamente come modello parametrico tecnico e non mesh CAD millimetrica delle plastiche OEM.
4. **Mappa GPS Vettoriale Offline & Privacy Zone:**
   - Rendering SVG relativo locale (nessun tile server esterno) con toggle **Privacy Zone 300 m** che taglia partenza e arrivo intorno al garage.

---

## 3. Conseguenze

- **Positivi:** Esperienza unificata da casa e in garage, zero dipendenze runtime aggiuntive, piena operatività offline, zero rischi di leak GPS/odometro su GitHub.
- **Trade-off:** Il motore 3D parametrico privilegia chiarezza strutturale e zero-dipendenze rispetto a un modello CAD fotorealistico `.glb`.

---

## 4. Task Operativi Collegati

- [x] **TASK-APP-01** (`#21`): Creazione `tools/garage_store.py`, API `/api/*` in `ingest_server.py`, `analyze_session_dict` + `report.html` `stone-blueprint`, e Web App `tools/webapp/` con Digital Twin 3D offline.
