from __future__ import annotations

import argparse
import logging
import sys
from datetime import date

from .config import Konfiguration
from .email_source import rechnungen_abrufen as email_rechnungen_abrufen
from .models import Lauf
from .portals.adobe import AdobePortal
from .portals.amazon import AmazonPortal
from .storage import csv_exportieren, monatsordner

PORTAL_KLASSEN = {
    "adobe": AdobePortal,
    "amazon": AmazonPortal,
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("rechnungsagent")


def _monat_parsen(wert: str) -> tuple[int, int]:
    try:
        jahr_str, monat_str = wert.split("-")
        return int(jahr_str), int(monat_str)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Format muss YYYY-MM sein, z.B. 2026-07") from exc


def befehl_login(args: argparse.Namespace, konfig: Konfiguration) -> None:
    portal_klasse = PORTAL_KLASSEN.get(args.portal)
    if not portal_klasse:
        print(f"Unbekanntes Portal '{args.portal}'. Verfügbar: {', '.join(PORTAL_KLASSEN)}")
        sys.exit(1)
    portal_konto = konfig.portale.get(args.portal)
    if not portal_konto:
        print(f"Portal '{args.portal}' ist nicht in config.yaml konfiguriert.")
        sys.exit(1)
    portal_klasse(portal_konto).login_einrichten()


def befehl_run(args: argparse.Namespace, konfig: Konfiguration) -> None:
    jahr, monat = args.monat if args.monat else (date.today().year, date.today().month)
    lauf = Lauf(jahr=jahr, monat=monat)
    zielordner = monatsordner(konfig.ablage.basis_ordner, jahr, monat)

    for konto in konfig.email_konten:
        try:
            lauf.rechnungen.extend(email_rechnungen_abrufen(konto, jahr, monat, zielordner))
        except Exception:
            logger.exception("Fehler beim Abrufen von Postfach '%s'", konto.name)

    for name, portal_konto in konfig.portale.items():
        if not portal_konto.aktiv:
            continue
        portal_klasse = PORTAL_KLASSEN.get(name)
        if not portal_klasse:
            logger.warning("Kein Handler für Portal '%s' implementiert, überspringe.", name)
            continue
        try:
            lauf.rechnungen.extend(portal_klasse(portal_konto).rechnungen_herunterladen(jahr, monat, zielordner))
        except Exception:
            logger.exception("Fehler beim Abrufen von Portal '%s'", name)

    csv_pfad = csv_exportieren(lauf, konfig.ablage.basis_ordner)
    print(f"\n{len(lauf.rechnungen)} Rechnung(en) für {lauf.monatsschluessel} gespeichert unter: {zielordner}")
    print(f"DATEV-Vorbereitungs-CSV: {csv_pfad}")

    unvollstaendig = [r for r in lauf.rechnungen if r.status != "vollständig"]
    if unvollstaendig:
        print(f"Hinweis: {len(unvollstaendig)} Beleg(e) benötigen manuelle Prüfung (fehlende Angaben in der CSV).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sammelt monatliche Eingangsrechnungen für die Buchhaltung.")
    parser.add_argument("--config", default="config.yaml", help="Pfad zur config.yaml (Standard: ./config.yaml)")
    parser.add_argument("--env", default=".env", help="Pfad zur .env-Datei mit Passwörtern (Standard: ./.env)")
    unterbefehle = parser.add_subparsers(dest="befehl", required=True)

    login_parser = unterbefehle.add_parser("login", help="Manuellen Portal-Login einrichten (Adobe, Amazon, ...)")
    login_parser.add_argument("portal", choices=list(PORTAL_KLASSEN))
    login_parser.set_defaults(func=befehl_login)

    run_parser = unterbefehle.add_parser("run", help="Rechnungen für einen Monat sammeln")
    run_parser.add_argument(
        "--monat", type=_monat_parsen, default=None, help="Zielmonat als YYYY-MM (Standard: aktueller Monat)"
    )
    run_parser.set_defaults(func=befehl_run)

    args = parser.parse_args()
    konfig = Konfiguration.laden(args.config, args.env)
    args.func(args, konfig)


if __name__ == "__main__":
    main()
