#!/usr/bin/env python3
"""Extract official SYM exploded diagrams & service plates from local `manuals/` PDFs.

Outputs crisp high-resolution PNG plates into `tools/local_atlas/` (excluded from Git
via `.gitignore`) so the Smart Garage Web App displays real SYM technical drawings
synchronized with every guided disassembly/maintenance step.

Requires `pdftoppm` (Poppler) installed locally (`brew install poppler`).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parents[1]
MANUALS_DIR = ROOT / "manuals"
OUT_DIR = Path(__file__).resolve().parent / "local_atlas"

# (out_filename, source_pdf, page_number, description)
PLATES_SPEC: List[Tuple[str, str, int, str]] = [
    ("symphony_overview.png", "symphony_st_200_abs_e4_owners_tr.pdf", 3, "Posizione componenti Symphony ST 200i ABS [TUO]"),
    ("battery_fuses.png", "symphony_st_200_abs_e4_owners_tr.pdf", 17, "Vano batteria 12V 6Ah & accesso sottosella [TUO]"),
    ("fuses_box.png", "symphony_st_200_abs_e4_owners_tr.pdf", 19, "Scatola fusibili 10A/15A/20A [TUO]"),
    ("engine_valves.png", "fiddle3_200i_service_manual.pdf", 24, "Gioco valvole 0,12 mm & fasatura PMS [XB20]"),
    ("lubrication.png", "fiddle3_200i_service_manual.pdf", 33, "Esploso lubrificazione & olio motore 0,70 L [XB20]"),
    ("cvt_exploded.png", "fiddle3_200i_service_manual.pdf", 102, "Esploso trasmissione CVT (variatore, cinghia, rulli, frizione) [XB20]"),
    ("final_drive.png", "fiddle3_200i_service_manual.pdf", 115, "Esploso riduttore finale & olio 170 cc [XB20]"),
    ("body_covers.png", "jet14_service_manual.pdf", 135, "Smontaggio carenature, viti & scudo anteriore [FAM]"),
    ("abs_wheels.png", "maxsym_abs_service_manual.pdf", 215, "Posizione centralina ABS Bosch & sensori ruota 50 fori [FAM]"),
    ("wiring_xb20.png", "fiddle3_200i_electrical_diagram.pdf", 1, "Schema elettrico completo motore XB20 [XB20]"),
]


def extract_all(dpi: int = 180) -> List[Path]:
    if shutil.which("pdftoppm") is None:
        raise SystemExit("ERRORE: `pdftoppm` (poppler) non trovato nel PATH. Installa con `brew install poppler`.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generated: List[Path] = []
    for out_name, pdf_name, page, desc in PLATES_SPEC:
        pdf_path = MANUALS_DIR / pdf_name
        if not pdf_path.exists():
            print(f"[skip] Manuale mancante: {pdf_path}")
            continue
        prefix = OUT_DIR / Path(out_name).stem
        cmd = [
            "pdftoppm",
            "-png",
            "-r",
            str(dpi),
            "-singlefile",
            "-f",
            str(page),
            "-l",
            str(page),
            str(pdf_path),
            str(prefix),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        out_file = OUT_DIR / out_name
        generated.append(out_file)
        print(f"[ok] {out_file.name:22s} ({out_file.stat().st_size // 1024:4d} KB) <- {pdf_name} p.{page} | {desc}")
    return generated


if __name__ == "__main__":
    files = extract_all()
    print(f"\n[extract_atlas] Estratte {len(files)}/{len(PLATES_SPEC)} tavole in {OUT_DIR}")
