from __future__ import annotations

import email
import imaplib
import logging
from calendar import monthrange
from datetime import date
from email.header import decode_header
from email.message import Message
from pathlib import Path

from .config import EmailKonto
from .models import Rechnung
from .storage import belegdateiname, eindeutiger_pfad

logger = logging.getLogger(__name__)

PDF_ENDUNGEN = (".pdf",)


def _dekodiere(wert: str | None) -> str:
    if not wert:
        return ""
    teile = decode_header(wert)
    ergebnis = []
    for text, kodierung in teile:
        if isinstance(text, bytes):
            ergebnis.append(text.decode(kodierung or "utf-8", errors="replace"))
        else:
            ergebnis.append(text)
    return "".join(ergebnis)


def _imap_datum(d: date) -> str:
    # IMAP SEARCH erwartet das Format "01-Jan-2026"
    return d.strftime("%d-%b-%Y")


def _finde_pdf_anhaenge(nachricht: Message) -> list[tuple[str, bytes]]:
    anhaenge = []
    for teil in nachricht.walk():
        dateiname = teil.get_filename()
        if not dateiname:
            continue
        dateiname = _dekodiere(dateiname)
        if not dateiname.lower().endswith(PDF_ENDUNGEN):
            continue
        payload = teil.get_payload(decode=True)
        if payload:
            anhaenge.append((dateiname, payload))
    return anhaenge


def rechnungen_abrufen(konto: EmailKonto, jahr: int, monat: int, zielordner: Path) -> list[Rechnung]:
    """Durchsucht ein IMAP-Postfach nach Rechnungsmails im angegebenen Monat und
    speichert alle PDF-Anhänge im Zielordner. Gibt die gefundenen Rechnungen zurück.
    """
    start = date(jahr, monat, 1)
    ende = date(jahr, monat, monthrange(jahr, monat)[1])

    gefunden: list[Rechnung] = []

    with imaplib.IMAP4_SSL(konto.imap_server, konto.imap_port) as verbindung:
        verbindung.login(konto.username, konto.password)
        verbindung.select(konto.ordner, readonly=True)

        suchkriterien = [f'SINCE "{_imap_datum(start)}"', f'BEFORE "{_imap_datum(ende)}"']
        # BEFORE ist exklusiv – daher einen Tag auf "ende" addieren
        ende_exklusiv = date.fromordinal(ende.toordinal() + 1)
        suchkriterien[1] = f'BEFORE "{_imap_datum(ende_exklusiv)}"'

        status, daten = verbindung.search(None, *suchkriterien)
        if status != "OK":
            logger.warning("IMAP-Suche für Postfach '%s' fehlgeschlagen: %s", konto.name, status)
            return gefunden

        nachricht_ids = daten[0].split()
        for msg_id in nachricht_ids:
            status, msg_daten = verbindung.fetch(msg_id, "(RFC822)")
            if status != "OK" or not msg_daten or not msg_daten[0]:
                continue
            rohnachricht = msg_daten[0][1]
            nachricht = email.message_from_bytes(rohnachricht)

            betreff = _dekodiere(nachricht.get("Subject"))
            absender = _dekodiere(nachricht.get("From"))

            if konto.absender_filter and not any(f.lower() in absender.lower() for f in konto.absender_filter):
                continue
            if konto.suchbegriffe and not any(s.lower() in betreff.lower() for s in konto.suchbegriffe):
                continue

            anhaenge = _finde_pdf_anhaenge(nachricht)
            if not anhaenge:
                continue

            try:
                empfangsdatum = email.utils.parsedate_to_datetime(nachricht.get("Date")).date().isoformat()
            except (TypeError, ValueError):
                empfangsdatum = ""

            aussteller = absender.split("<")[0].strip().strip('"') or absender

            for original_dateiname, inhalt in anhaenge:
                neuer_dateiname = belegdateiname(empfangsdatum, "email", aussteller)
                ziel_pfad = eindeutiger_pfad(zielordner, neuer_dateiname)
                ziel_pfad.write_bytes(inhalt)

                gefunden.append(
                    Rechnung(
                        dateiname=ziel_pfad.name,
                        quelle="email",
                        quelle_detail=f"{konto.name} ({original_dateiname})",
                        belegdatum=empfangsdatum,
                        aussteller=aussteller,
                        betrag="",
                    )
                )

    logger.info("Postfach '%s': %d Rechnung(en) gefunden.", konto.name, len(gefunden))
    return gefunden
