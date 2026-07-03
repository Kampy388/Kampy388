import csv
from pathlib import Path

from rechnungsagent.models import Lauf, Rechnung
from rechnungsagent.storage import (
    belegdateiname,
    csv_exportieren,
    eindeutiger_pfad,
    monatsordner,
    sichere_dateinamen,
)


def test_sichere_dateinamen_entfernt_sonderzeichen():
    assert sichere_dateinamen("Müller & Söhne GmbH!") == "Muller_Sohne_GmbH"


def test_belegdateiname_format():
    name = belegdateiname("2026-07-03", "adobe", "Adobe Inc.")
    assert name == "2026-07-03_Adobe_Inc._adobe.pdf"


def test_eindeutiger_pfad_haengt_zaehler_an(tmp_path: Path):
    erster = eindeutiger_pfad(tmp_path, "beleg.pdf")
    erster.write_bytes(b"x")
    zweiter = eindeutiger_pfad(tmp_path, "beleg.pdf")
    assert zweiter.name == "beleg_2.pdf"


def test_monatsordner_erstellt_verzeichnis(tmp_path: Path):
    ordner = monatsordner(str(tmp_path / "Rechnungen"), 2026, 7)
    assert ordner.exists()
    assert ordner.name == "2026-07"


def test_csv_export_markiert_status_und_schreibt_zeilen(tmp_path: Path):
    lauf = Lauf(
        jahr=2026,
        monat=7,
        rechnungen=[
            Rechnung(
                dateiname="a.pdf",
                quelle="adobe",
                quelle_detail="adobe-konto",
                belegdatum="2026-07-03",
                rechnungsnummer="RE-1",
                aussteller="Adobe",
                betrag="12,99",
            ),
            Rechnung(
                dateiname="b.pdf",
                quelle="email",
                quelle_detail="privat (b.pdf)",
                belegdatum="2026-07-01",
                aussteller="Irgendwer GmbH",
            ),
        ],
    )

    csv_pfad = csv_exportieren(lauf, str(tmp_path / "Rechnungen"))
    assert csv_pfad.exists()

    with csv_pfad.open(encoding="utf-8-sig") as f:
        zeilen = list(csv.DictReader(f, delimiter=";"))

    assert len(zeilen) == 2
    vollstaendig = next(z for z in zeilen if z["dateiname"] == "a.pdf")
    unvollstaendig = next(z for z in zeilen if z["dateiname"] == "b.pdf")
    assert vollstaendig["status"] == "vollständig"
    assert unvollstaendig["status"] == "geprüft nötig"
