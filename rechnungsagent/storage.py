from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path

from .models import Lauf, Rechnung

CSV_SPALTEN = [
    "belegdatum",
    "rechnungsnummer",
    "aussteller",
    "betrag",
    "waehrung",
    "dateiname",
    "quelle",
    "quelle_detail",
    "status",
]


def monatsordner(basis_ordner: str, jahr: int, monat: int) -> Path:
    ordner = Path(basis_ordner) / f"{jahr:04d}-{monat:02d}"
    ordner.mkdir(parents=True, exist_ok=True)
    return ordner


def sichere_dateinamen(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("_")
    return text or "beleg"


def eindeutiger_pfad(ordner: Path, dateiname: str) -> Path:
    ziel = ordner / dateiname
    if not ziel.exists():
        return ziel
    stamm, endung = ziel.stem, ziel.suffix
    zaehler = 2
    while True:
        kandidat = ordner / f"{stamm}_{zaehler}{endung}"
        if not kandidat.exists():
            return kandidat
        zaehler += 1


def belegdateiname(belegdatum: str, quelle: str, aussteller: str, endung: str = ".pdf") -> str:
    """Erzeugt einen DATEV-freundlichen Dateinamen: Datum_Aussteller_Quelle.pdf"""
    datum = belegdatum or "unbekannt"
    aussteller_sicher = sichere_dateinamen(aussteller or quelle)
    return sichere_dateinamen(f"{datum}_{aussteller_sicher}_{quelle}") + endung


def csv_exportieren(lauf: Lauf, basis_ordner: str) -> Path:
    """Schreibt/aktualisiert die Monats-CSV mit allen Belegmetadaten (Semikolon-getrennt,
    UTF-8 mit BOM für Excel) – als Vorbereitung für den DATEV-Import.
    """
    ordner = monatsordner(basis_ordner, lauf.jahr, lauf.monat)
    csv_pfad = ordner / f"rechnungen_{lauf.monatsschluessel}.csv"

    for rechnung in lauf.rechnungen:
        rechnung.nach_pruefung()

    with csv_pfad.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_SPALTEN, delimiter=";")
        writer.writeheader()
        for rechnung in sorted(lauf.rechnungen, key=lambda r: (r.belegdatum, r.aussteller)):
            writer.writerow(
                {
                    "belegdatum": rechnung.belegdatum,
                    "rechnungsnummer": rechnung.rechnungsnummer,
                    "aussteller": rechnung.aussteller,
                    "betrag": rechnung.betrag,
                    "waehrung": rechnung.waehrung,
                    "dateiname": rechnung.dateiname,
                    "quelle": rechnung.quelle,
                    "quelle_detail": rechnung.quelle_detail,
                    "status": rechnung.status,
                }
            )
    return csv_pfad
