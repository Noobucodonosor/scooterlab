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
3. **Atlante Esplosi Ufficiali SYM, Ricambi OEM & Slot 3D Reale (`.glb`):**
   - Rimozione totale di geometrie placeholder a cubi a favore di un doppio visualizzatore (`tools/webapp/workshop_viewer.js`):
     1. **Atlante Esplosi Ufficiali SYM:** estrattore locale `tools/extract_atlas.py` (`pdftoppm` da `manuals/` verso `tools/local_atlas/`, sempre esclusa da `.gitignore` per copyright) con 10 tavole ad alta risoluzione sincronizzate automaticamente su ogni step operativo + catalogo `OEM_PARTS_CATALOG` cliccabile con link microfiche EasyParts.
     2. **Slot Modello 3D Reale (`.glb`):** caricamento locale in `tools/local_models/symphony.glb` (escluso da `.gitignore`) per scansioni 3D reali dello scooter (Polycam / Scaniverse) renderizzate offline in puro JS senza CDN.
4. **Mappa GPS Vettoriale Offline & Privacy Zone:**
   - Rendering SVG relativo locale (nessun tile server esterno) con toggle **Privacy Zone 300 m** che taglia partenza e arrivo intorno al garage.

---

## 3. Conseguenze

- **Positivi:** Esperienza unificata da casa e in garage, zero dipendenze runtime aggiuntive, piena operatività offline, zero rischi di leak GPS/odometro su GitHub.
- **Trade-off:** Il motore 3D parametrico privilegia chiarezza strutturale e zero-dipendenze rispetto a un modello CAD fotorealistico `.glb`.

---

## 4. Task Operativi Collegati

- [x] **TASK-APP-01** (`#21`): Creazione `tools/garage_store.py`, API `/api/*` in `ingest_server.py`, `analyze_session_dict` + `report.html` `stone-blueprint`, e Web App `tools/webapp/`.
- [x] **TASK-APP-02** (`#24`): Sostituzione placeholder cubi con Atlante Esplosi Ufficiali SYM (`tools/extract_atlas.py`), Catalogo Ricambi OEM e slot `.glb` reale (`tools/webapp/workshop_viewer.js`).
