#!/usr/bin/env python3
"""ScooterLab Smart Garage store, factory specs & guided procedures (ADR-0008).

Pure-stdlib module managing:
- `FACTORY_SPECS`: official SYM Symphony ST 200i ABS (`XB20E2-EU`) tolerances (`[TUO]`, `[XB20]`, `[FAM]`).
- `GARAGE_PROCEDURES`: complete step-by-step guides (30k service, factory checkup,
  body disassembly Levels A-D, ScooterLab Rev. 2 installation, quick diagnostics),
  each step linked to a 3D Digital Twin subsystem (`focus_part`).
- `GarageStore`: atomic local JSON persistence (`tools/garage_state.json`, gitignored).
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


FACTORY_SPECS: List[Dict[str, Any]] = [
    {
        "id": "battery_rest_v",
        "label": "Batteria a riposo (quadro OFF)",
        "unit": "V",
        "nominal": "12.6–12.8",
        "ok_min": 12.5,
        "ok_max": 13.0,
        "warn_min": 12.3,
        "warn_max": 13.2,
        "source": "[TUO]",
        "part": "battery_fuses",
        "hint": "Sotto 12,3 V ricaricare o valutare sostituzione YTX7A-BS (12V 6Ah).",
    },
    {
        "id": "parasitic_ma",
        "label": "Dispersione parassita (quadro OFF)",
        "unit": "mA",
        "nominal": "< 1.0",
        "ok_min": 0.0,
        "ok_max": 1.0,
        "warn_min": 0.0,
        "warn_max": 2.0,
        "source": "[XB20]",
        "part": "battery_fuses",
        "hint": "Amperometro in serie al negativo batteria con quadro OFF.",
    },
    {
        "id": "regulator_v",
        "label": "Ricarica regolatore (~2.000 rpm, fari ON)",
        "unit": "V",
        "nominal": "14.0–14.8",
        "ok_min": 13.8,
        "ok_max": 14.9,
        "warn_min": 13.2,
        "warn_max": 15.0,
        "source": "[XB20]",
        "part": "battery_fuses",
        "hint": "> 15,0 V = regolatore guasto; < 13,2 V = verificare statore (0,2–1,2 Ω Y–Y).",
    },
    {
        "id": "valve_in_mm",
        "label": "Gioco valvola Aspirazione IN (< 35 °C)",
        "unit": "mm",
        "nominal": "0.12 ± 0.02",
        "ok_min": 0.10,
        "ok_max": 0.14,
        "warn_min": 0.08,
        "warn_max": 0.16,
        "source": "[TUO]",
        "part": "engine_valves",
        "hint": "Misurare al PMS in compressione (tacca T + foro camme in alto).",
    },
    {
        "id": "valve_ex_mm",
        "label": "Gioco valvola Scarico EX (< 35 °C)",
        "unit": "mm",
        "nominal": "0.12 ± 0.02",
        "ok_min": 0.10,
        "ok_max": 0.14,
        "warn_min": 0.08,
        "warn_max": 0.16,
        "source": "[TUO]",
        "part": "engine_valves",
        "hint": "Regolare con spessimetro a lamelle; ruotare albero SOLO in senso orario.",
    },
    {
        "id": "spark_gap_mm",
        "label": "Gap elettrodo candela (NGK CR7HSA)",
        "unit": "mm",
        "nominal": "0.60–0.70",
        "ok_min": 0.60,
        "ok_max": 0.70,
        "warn_min": 0.50,
        "warn_max": 0.80,
        "source": "[TUO]",
        "part": "engine_valves",
        "hint": "Serrare a 10–12 Nm (prima avvitare a mano).",
    },
    {
        "id": "cvt_belt_mm",
        "label": "Larghezza cinghia CVT (1B01XMA02 / Bando S08-023)",
        "unit": "mm",
        "nominal": "19.7 (lim. 17.5)",
        "ok_min": 18.2,
        "ok_max": 20.2,
        "warn_min": 17.5,
        "warn_max": 20.5,
        "source": "[XB20]",
        "part": "cvt_case",
        "hint": "Sostituire sotto 17,5 mm o ogni 12.000 km o in presenza di crepe.",
    },
    {
        "id": "cvt_roller_mm",
        "label": "Diametro minimo rulli variatore (18×14 mm)",
        "unit": "mm",
        "nominal": "18.0 (lim. 17.5)",
        "ok_min": 17.7,
        "ok_max": 18.2,
        "warn_min": 17.5,
        "warn_max": 18.3,
        "source": "[TUO]",
        "part": "cvt_case",
        "hint": "Misurare su 2 assi a 90°: sostituire se < 17,5 mm o ovalizzati > 0,25 mm.",
    },
    {
        "id": "tire_front_bar",
        "label": "Pressione gomma anteriore a freddo (110/70-16)",
        "unit": "bar",
        "nominal": "2.00",
        "ok_min": 1.90,
        "ok_max": 2.10,
        "warn_min": 1.75,
        "warn_max": 2.25,
        "source": "[TUO]",
        "part": "wheels_abs",
        "hint": "Controllare a freddo con manometro affidabile.",
    },
    {
        "id": "tire_rear_bar",
        "label": "Pressione gomma posteriore a freddo (110/70-16)",
        "unit": "bar",
        "nominal": "2.00–2.25",
        "ok_min": 1.95,
        "ok_max": 2.30,
        "warn_min": 1.80,
        "warn_max": 2.50,
        "source": "[TUO]",
        "part": "wheels_abs",
        "hint": "2,00 bar da solo, 2,25 bar con passeggero.",
    },
    {
        "id": "brake_pad_mm",
        "label": "Spessore ferodo pastiglie freno",
        "unit": "mm",
        "nominal": ">= 2.0",
        "ok_min": 2.0,
        "ok_max": 8.0,
        "warn_min": 1.5,
        "warn_max": 9.0,
        "source": "[FAM]",
        "part": "wheels_abs",
        "hint": "Sostituire prima di scendere sotto 1,5 mm o al raggiungimento tacca usura.",
    },
]

SPEC_BY_ID: Dict[str, Dict[str, Any]] = {s["id"]: s for s in FACTORY_SPECS}


def evaluate_measurement(spec_id: str, value: float) -> Dict[str, Any]:
    """Evaluate a garage measurement against SYM Symphony ST 200i tolerances."""
    spec = SPEC_BY_ID.get(spec_id)
    if spec is None:
        raise ValueError(f"Specifica sconosciuta: {spec_id}")

    if spec["ok_min"] <= value <= spec["ok_max"]:
        status = "OK"
        message = f"In tolleranza ({value} {spec['unit']} vs {spec['nominal']} {spec['unit']})"
    elif spec["warn_min"] <= value <= spec["warn_max"]:
        status = "WARNING"
        message = f"Al limite ({value} {spec['unit']} — {spec['hint']})"
    else:
        status = "OUT_OF_SPEC"
        message = f"Fuori specifica! ({value} {spec['unit']} vs {spec['nominal']} {spec['unit']} — {spec['hint']})"

    return {
        "spec_id": spec_id,
        "value": value,
        "status": status,
        "message": message,
        "nominal": spec["nominal"],
        "unit": spec["unit"],
        "source": spec["source"],
    }


GARAGE_PROCEDURES: List[Dict[str, Any]] = [
    {
        "id": "service_30k",
        "title": "Tagliando Completo 30.000 km",
        "category": "Manutenzione",
        "duration": "~2–3 ore",
        "summary": "Procedura completa oli, filtri, candela, gioco valvole e revisione CVT con coppie ufficiali.",
        "steps": [
            {
                "title": "1. Sicurezza, moto fredda e accesso sottosella",
                "focus_part": "underseat_tub",
                "tools": "Bussola 10 mm, cricchetto",
                "torque_spec": "Motore < 35 °C · Prima polo (-) poi (+)",
                "warning": "MAI scollegare il connettore centralina ABS con chiave su ON (Maxsym pag. 14-15).",
                "detail": "Metti lo scooter sul cavalletto centrale in piano. Apri la sella, svita i bulloni flangiati da 10 mm del cestello e sollevalo verticalmente scollegando eventuale presa USB.",
            },
            {
                "title": "2. Scarico e ricarica olio motore (0,70 L)",
                "focus_part": "engine_valves",
                "tools": "Bussola 17 mm, dinamometrica, vaschetta, imbuto",
                "torque_spec": "0,70 L SAE 10W-30 API SH/CD · Tappo 34–44 Nm",
                "warning": "Pulisci retina filtro olio e controlla O-ring del tappo prima di serrare.",
                "detail": "Scarica l'olio a motore tiepido, lascia scolare 5 minuti, serra il tappo a 34–44 Nm, riempi con 0,70 L esatti e verifica il livello sull'astina senza avvitarla.",
            },
            {
                "title": "3. Cambio olio trasmissione finale (170 cc)",
                "focus_part": "cvt_case",
                "tools": "Bussola 12 mm, siringa graduata",
                "torque_spec": "170 cc SAE 85W-140 GL-5 hypoid",
                "warning": "Non contaminare disco freno o pneumatico posteriore durante il rabbocco.",
                "detail": "Rimuovi vite carico e vite scarico dietro al carter CVT sinistro, fai defluire l'olio vecchio, chiudi lo scarico e inietta 170 cc dal foro superiore.",
            },
            {
                "title": "4. Sostituzione filtro aria in carta",
                "focus_part": "cvt_case",
                "tools": "Cacciavite PH2, panno pulito",
                "torque_spec": "Ricambio 17211-ADB-000 (HFA5101)",
                "warning": "Non soffiare aria compressa dall'esterno verso l'interno su filtri in carta.",
                "detail": "Svita le viti perimetrali del coperchio airbox sopra il carter sinistro, pulisci l'interno scatola da olio/polvere e monta il nuovo filtro.",
            },
            {
                "title": "5. Candela NGK CR7HSA (gap & serraggio)",
                "focus_part": "engine_valves",
                "tools": "Chiave candela 16 mm snodata, spessimetro, dinamometrica",
                "torque_spec": "Gap 0,6–0,7 mm · Serraggio 10–12 Nm",
                "warning": "Avvita sempre i primi filetti a mano per non spanare la testata in alluminio.",
                "detail": "Sfila la pipetta, soffia eventuale sporco attorno alla sede, controlla colore e gap (0,6–0,7 mm) e serra a 10–12 Nm.",
            },
            {
                "title": "6. Controllo e regolazione gioco valvole",
                "focus_part": "engine_valves",
                "tools": "Spessimetro 0,10/0,12/0,15 mm, chiave 8/9/10 mm",
                "torque_spec": "IN 0,12 ± 0,02 mm · EX 0,12 ± 0,02 mm (< 35 °C)",
                "warning": "Ruota l'albero motore SOLO IN SENSO ORARIO fino a tacca T e foro camme in alto.",
                "detail": "Togli tappo ispezione volano e coperchio punterie. Verifica al PMS in compressione che entrambi i bilancieri siano liberi, misura con lamella 0,12 mm e registra nella scheda Check-Up.",
            },
            {
                "title": "7. Ispezione CVT: cinghia, rulli 18×14 mm e frizione",
                "focus_part": "cvt_case",
                "tools": "Bussola 8/10/17/19 mm, blocca-variatore, calibro, dinamometrica",
                "torque_spec": "Variatore 49–59 Nm · Frizione 54–59 Nm · Carter 25–29 Nm",
                "warning": "MAI bloccare la ruota posteriore col freno per svitare il variatore (danni al riduttore).",
                "detail": "Rimuovi i 7 bulloni M8 del carter sinistro. Usa il blocca-variatore, misura larghezza cinghia (lim. 17,5 mm) e rulli su 2 assi (lim. 17,5 mm, ovalizzazione < 0,25 mm), soffia la polvere e serra a coppia.",
            },
        ],
    },
    {
        "id": "factory_checkup",
        "title": "Verifica Conformità di Fabbrica (5 Step)",
        "category": "Collaudo",
        "duration": "~45 min",
        "summary": "Certifica stato elettrico, EFI/ABS, motore, CVT e ciclistica prima dei giri di baseline.",
        "steps": [
            {
                "title": "1. Impianto elettrico & ricarica regolatore",
                "focus_part": "battery_fuses",
                "tools": "Multimetro digitale (DC V + mA)",
                "torque_spec": "Riposo 12,6–12,8 V · Ricarica 14,0–14,8 V · Dispersione < 1 mA",
                "warning": "Se supera 15,0 V a 2.000 rpm spegni subito: rischio bruciatura centraline.",
                "detail": "Misura tensione a quadro OFF, poi dispersione in serie al negativo, poi ricarica a 2.000 rpm fari accesi. Inserisci i valori nel tab Check-Up Fabbrica.",
            },
            {
                "title": "2. Autodiagnosi spie EFI & anelli fonici ABS",
                "focus_part": "wheels_abs",
                "tools": "Torcia, panno pulito",
                "torque_spec": "Spia ABS spenta > 10 km/h · Anelli 50 fori integri",
                "warning": "Non avvicinare magneti o utensili ferrosi ai sensori Hall ruota.",
                "detail": "Accendi il quadro: verifica spia EFI (niente lampeggi errore) e controlla visivamente pulizia e traferro dei due anelli fonici a 50 fori su ruota ant/post.",
            },
            {
                "title": "3. Verifica candela & fasatura/valvole",
                "focus_part": "engine_valves",
                "tools": "Spessimetro, chiave candela 16 mm",
                "torque_spec": "Valvole 0,12 ± 0,02 mm · Compressione 10,2 ± 0,2 kg/cm²",
                "warning": "Eseguire sempre a motore freddo (< 35 °C).",
                "detail": "Controlla che il gioco valvole rientri in 0,10–0,14 mm e che l'elettrodo candela sia nocciola chiaro.",
            },
            {
                "title": "4. Controllo calibro trasmissione CVT",
                "focus_part": "cvt_case",
                "tools": "Calibro digitale, blocca-variatore",
                "torque_spec": "Cinghia ≥ 17,5 mm · Rulli ≥ 17,5 mm · Ferodo ≥ 2,0 mm",
                "warning": "Pulegge e cinghia devono restare 100% prive di grasso.",
                "detail": "Verifica spessore cinghia, sfericità rulli 18×14 mm e assenza di solchi nella campana frizione.",
            },
            {
                "title": "5. Freni, pressioni gomme & circonferenza ruota reale",
                "focus_part": "wheels_abs",
                "tools": "Manometro, calibro, metro a nastro, gessetto",
                "torque_spec": "2,00 bar ant · 2,00–2,25 bar post · Rotolamento ~1,716 m",
                "warning": "Controlla gioco leve freno (10–20 mm) e spessore pastiglie prima della prova su strada.",
                "detail": "Fai un segno a terra e sulla gomma anteriore 110/70-16, spingi lo scooter per 1 giro esatto e misura i mm reali per calibrare la velocità ruota Livello 1.",
            },
        ],
    },
    {
        "id": "disassembly_panels",
        "title": "Smontaggio Scocche & Accessi (Liv. A–D)",
        "category": "Carrozzeria",
        "duration": "15–60 min",
        "summary": "Ordine esatto di smontaggio per ogni zona senza rompere clip e ganci in plastica.",
        "steps": [
            {
                "title": "Livello A — Cestello sottosella (Batteria, Fusibili, ScooterLab L0)",
                "focus_part": "underseat_tub",
                "tools": "Bussola 10 mm, vaschetta magnetica viti",
                "torque_spec": "Zero carenature esterne smontate",
                "warning": "Scollega l'eventuale cavo luce vano o USB prima di estrarre il cestello.",
                "detail": "Svuota il vano, svita i bulloni flangiati da 10 mm sul fondo e solleva verticalmente. Accedi subito a batteria 12V 6Ah, fusibili (10A×2, 15A, 20A), parte alta motore e zona anteriore vano.",
            },
            {
                "title": "Livello B — Airbox & Carter Trasmissione CVT",
                "focus_part": "cvt_case",
                "tools": "PH2, bussola 8/10 mm",
                "torque_spec": "7×M8 carter alluminio 25–29 Nm (a croce)",
                "warning": "Tieni il carter dritto sfilandolo per non perdere le 2 boccole di centraggio.",
                "detail": "Smonta il convogliatore aria anteriore del carter, poi allenta a croce i 7 bulloni M8 perimetrali.",
            },
            {
                "title": "Livello C — Coprimanubrio & Scudo Anteriore (OBD / CAN / ABS)",
                "focus_part": "front_obd",
                "tools": "Leva in plastica per clip, PH1/PH2, chiave specchietti",
                "torque_spec": "Viti autofilettanti 4×12 / 4,8×16 mm",
                "warning": "Mai tirare di forza: guarda il verso del gancio e scollega frecce/faro prima di appoggiare lo scudo.",
                "detail": "Svita specchietti (attenzione a filetto sx lato dx), viti interne retroscudo manubrio e viti inferiori sotto faro; scorri lo scudo in avanti/basso per accedere a cruscotto, connettore OBD e centralina ABS.",
            },
            {
                "title": "Livello D — Fianchetti Posteriori & Codone",
                "focus_part": "underseat_tub",
                "tools": "Bussola 10/12 mm, PH2, leva plastica",
                "torque_spec": "Portapacchi + copertura tunnel + viti laterali",
                "warning": "Sfila i fianchetti scorrendo all'indietro per liberare i ganci anteriori.",
                "detail": "Rimuovi cestello (Liv. A), portapacchi posteriore, copertura centrale tunnel e viti perimetrali dei fianchetti dx/sx.",
            },
        ],
    },
    {
        "id": "install_scooterlab",
        "title": "Installazione Centralina ScooterLab Rev. 2",
        "category": "IoT & Cablaggio",
        "duration": "~2 ore",
        "summary": "Montaggio non invasivo Livello 0/1 con ESP32-S3, Dual-SPI, TVS SMBJ18A e Hold-Up 4700 µF.",
        "steps": [
            {
                "title": "1. Taratura banco: Buck 5V, TVS SMBJ18A & Hold-Up 4700 µF",
                "focus_part": "scooterlab_box",
                "tools": "Multimetro, alimentatore 12V banco, saldatore, guaina termorestringente",
                "torque_spec": "Uscita Buck 5,00 ± 0,05 V · Fusibile 1 A · Hold-Up ≥ 200 ms",
                "warning": "Collega il modulo ESP32 SOLO dopo aver verificato 5,00 V stabili a vuoto e sotto carico.",
                "detail": "Salda TVS SMBJ18A in ingresso 12V, diodo Schottky SS34 + 2,2 Ω inrush + condensatore 4700 µF/10V post-buck, e verifica il partitore 47k/10k su IGN_SENSE (GPIO4).",
            },
            {
                "title": "2. Verifica positivo sottochiave nel vano (senza tagli)",
                "focus_part": "battery_fuses",
                "tools": "Multimetro DC, Posi-Tap (no rubacorrente a lama)",
                "torque_spec": "0 V quadro OFF · ~12,5 V ON · ~14,2 V motore acceso",
                "warning": "Muovi il manubrio a fine corsa dx/sx durante la misura per verificare assenza falsi contatti.",
                "detail": "Individua la linea sottochiave nel vano fusibili/sottosella dopo aver aperto il cestello (Liv. A) e deriva con Posi-Tap protetto da fusibile 1 A.",
            },
            {
                "title": "3. Fissaggio scatola IP65 & orientamento IMU ISM330IS",
                "focus_part": "scooterlab_box",
                "tools": "Piastra PETG/ASA, velcro 3M Dual Lock / viti M3, livella",
                "torque_spec": "Assi IMU: +X avanti, +Y sinistra, +Z alto · Zona anteriore fredda",
                "warning": "Usa PETG/ASA (mai PLA che si deforma col calore sottosella) e connettori JST-PH/SH (mai Dupont).",
                "detail": "Posiziona la scatola IP65 nella parete anteriore del vano lontana dalla testata. Fissa l'antenna GNSS u-blox M10 con vista cielo sotto plastica non metallizzata.",
            },
            {
                "title": "4. Primo giro di calibrazione & upload TLS in garage",
                "focus_part": "scooterlab_box",
                "tools": "Smartphone con Smart Garage App, Wi-Fi garage",
                "torque_spec": "NVS cifrata + HTTPS TLS 1.3 + Bearer Token",
                "warning": "Non spegnere di colpo prima di verificare il led di chiusura sicura al rientro.",
                "detail": "Esegui un giro di 10–15 min, rientra in garage con quadro acceso 30 s e verifica la comparsa della sessione `.slab` nel tab Telemetria.",
            },
        ],
    },
    {
        "id": "diagnostics_quick",
        "title": "Diagnostica Rapida Guasti (Elettrico, EFI, ABS, CVT)",
        "category": "Diagnostica",
        "duration": "10–30 min",
        "summary": "Checklist rapida se noti batterie scariche, spie accese, strappi o calo prestazioni.",
        "steps": [
            {
                "title": "1. Batteria che si scarica o tensione anomala",
                "focus_part": "battery_fuses",
                "tools": "Multimetro",
                "torque_spec": "Statore 0,2–1,2 Ω (Y–Y) · Regolatore 14,0–14,8 V",
                "warning": "Scollega il regolatore prima di misurare la resistenza degli avvolgimenti statore.",
                "detail": "Se a 2.000 rpm la carica è < 13,2 V testa i 3 fili gialli statore (continuità 0,2–1,2 Ω e isolamento infinito verso massa); se > 15,0 V sostituisci il regolatore.",
            },
            {
                "title": "2. Spia EFI lampeggiante",
                "focus_part": "front_obd",
                "tools": "Cronometro / occhi",
                "torque_spec": "Lampeggio lungo 1 s = decine · corto 0,5 s = unità",
                "warning": "Annota tutta la sequenza prima di spegnere il quadro.",
                "detail": "Conta i codici lampeggio EFI con quadro su ON e confronta con sezione 8 di docs/02-dati-tecnici-verificati.md (sensore TPS, O2, temperatura motore, bobina).",
            },
            {
                "title": "3. Spia ABS accesa sopra i 10 km/h",
                "focus_part": "wheels_abs",
                "tools": "Panno, spessimetro amagnetico",
                "torque_spec": "Anelli 50 fori (3,43 cm/impulso) · Codici Bosch C1042–C1055",
                "warning": "Mai staccare connettore ABS con chiave su ON.",
                "detail": "Pulisci fango/limatura ferrosa dalle finestre degli anelli fonici anteriore e posteriore e verifica l'integrità del cavo sensore lungo forcella e forcellone.",
            },
            {
                "title": "4. Strappi in partenza o calo velocità max CVT",
                "focus_part": "cvt_case",
                "tools": "Calibro, carta vetrata fine 400 (solo leggera opacizzazione ferodo)",
                "torque_spec": "Banda lavoro target: 7.600–8.100 rpm",
                "warning": "Non usare mai olio o grasso vicino a ganasce frizione o pulegge.",
                "detail": "Controlla vetrificazione ferodo ganasce, spiattellamento rulli 18×14 mm e verifica con il grafico FFT/0–50 km/h di Telemetria.",
            },
        ],
    },
]


DEFAULT_STATE: Dict[str, Any] = {
    "odometer_km": 29271.0,
    "baseline_session": None,
    "maintenance_log": [],
    "factory_checks": {},
    "procedure_progress": {},
}


class GarageStore:
    """Thread-safe JSON persistence for local vehicle state (never committed to Git)."""

    def __init__(self, state_path: Optional[Path] = None) -> None:
        env_path = os.environ.get("SCOOTERLAB_GARAGE_STATE")
        self.state_path = Path(state_path or env_path or (Path(__file__).resolve().parent / "garage_state.json"))
        self._lock = threading.Lock()

    def load(self) -> Dict[str, Any]:
        with self._lock:
            return self._read_unlocked()

    def _read_unlocked(self) -> Dict[str, Any]:
        if not self.state_path.exists():
            return json.loads(json.dumps(DEFAULT_STATE))
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return json.loads(json.dumps(DEFAULT_STATE))
        merged = json.loads(json.dumps(DEFAULT_STATE))
        if isinstance(data, dict):
            merged.update(data)
        return merged

    def _write_unlocked(self, state: Dict[str, Any]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.state_path)

    def set_odometer(self, odometer_km: float) -> Dict[str, Any]:
        if odometer_km < 0 or odometer_km > 999999:
            raise ValueError("Chilometraggio non valido")
        with self._lock:
            state = self._read_unlocked()
            state["odometer_km"] = round(float(odometer_km), 2)
            self._write_unlocked(state)
            return state

    def add_distance(self, delta_km: float) -> Dict[str, Any]:
        if delta_km <= 0:
            return self.load()
        with self._lock:
            state = self._read_unlocked()
            state["odometer_km"] = round(float(state.get("odometer_km", 0.0)) + float(delta_km), 2)
            self._write_unlocked(state)
            return state

    def set_baseline(self, session_name: Optional[str]) -> Dict[str, Any]:
        with self._lock:
            state = self._read_unlocked()
            state["baseline_session"] = session_name
            self._write_unlocked(state)
            return state

    def log_maintenance(self, item: str, km: float, notes: str = "") -> Dict[str, Any]:
        if not item.strip():
            raise ValueError("Nome intervento obbligatorio")
        with self._lock:
            state = self._read_unlocked()
            entry = {
                "item": item.strip(),
                "km": round(float(km), 1),
                "notes": notes.strip()[:240],
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            log: List[Dict[str, Any]] = list(state.get("maintenance_log", []))
            log.insert(0, entry)
            state["maintenance_log"] = log[:100]
            if km > float(state.get("odometer_km", 0.0)):
                state["odometer_km"] = round(float(km), 2)
            self._write_unlocked(state)
            return state

    def record_check(self, spec_id: str, value: float, notes: str = "") -> Dict[str, Any]:
        eval_res = evaluate_measurement(spec_id, float(value))
        eval_res["notes"] = notes.strip()[:240]
        eval_res["timestamp"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._lock:
            state = self._read_unlocked()
            checks = dict(state.get("factory_checks", {}))
            checks[spec_id] = eval_res
            state["factory_checks"] = checks
            self._write_unlocked(state)
            return eval_res

    def toggle_procedure_step(self, proc_id: str, step_idx: int, done: bool) -> Dict[str, Any]:
        proc = next((p for p in GARAGE_PROCEDURES if p["id"] == proc_id), None)
        if proc is None:
            raise ValueError(f"Procedura sconosciuta: {proc_id}")
        if step_idx < 0 or step_idx >= len(proc["steps"]):
            raise ValueError(f"Step fuori range: {step_idx}")
        with self._lock:
            state = self._read_unlocked()
            progress = dict(state.get("procedure_progress", {}))
            completed = set(progress.get(proc_id, []))
            if done:
                completed.add(int(step_idx))
            else:
                completed.discard(int(step_idx))
            progress[proc_id] = sorted(completed)
            state["procedure_progress"] = progress
            self._write_unlocked(state)
            return state
