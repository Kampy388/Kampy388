from __future__ import annotations

import logging
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

from ..models import Rechnung
from ..storage import belegdateiname, eindeutiger_pfad
from .base import PortalQuelle

logger = logging.getLogger(__name__)


class AmazonPortal(PortalQuelle):
    """Lädt Rechnungen aus der Amazon-Bestellhistorie (amazon.de / Amazon Business).

    Hinweis: Amazon ändert seine Bestellhistorie-Seite häufig, und bei
    privaten Amazon.de-Konten ist eine echte Rechnungs-PDF nicht für jede
    Bestellung verfügbar (teils nur "Bestelldetails" ohne Rechnung). Bei
    Amazon Business gibt es i.d.R. für jede Bestellung einen direkten
    Rechnungs-Download. Die Selektoren unten sind ein Best-Effort-Ansatz und
    wurden nicht gegen ein Live-Konto getestet – bitte bei Bedarf anpassen.
    """

    name = "amazon"
    start_url = "https://www.amazon.de/gp/css/order-history"

    def rechnungen_herunterladen(self, jahr: int, monat: int, zielordner: Path) -> list[Rechnung]:
        gefunden: list[Rechnung] = []
        monatsschluessel = f"{jahr:04d}-{monat:02d}"

        with sync_playwright() as pw:
            browser, context = self._browser_kontext(pw)
            page = context.new_page()
            # Bestellhistorie direkt nach Jahr gefiltert öffnen, um Ladezeit zu sparen
            page.goto(f"{self.start_url}?orderFilter=year-{jahr}", wait_until="networkidle")

            bestellungen = page.locator(".order-card, .order")
            anzahl = bestellungen.count()
            logger.info("Amazon: %d Bestellung(en) für Jahr %d gefunden.", anzahl, jahr)

            for i in range(anzahl):
                zeile = bestellungen.nth(i)
                text = zeile.inner_text()

                datums_match = re.search(r"(\d{1,2})\.?\s*(\w+)\s*(\d{4})", text)
                if not datums_match:
                    continue
                belegdatum = self._parse_deutsches_datum(datums_match)
                if not belegdatum or not belegdatum.startswith(monatsschluessel):
                    continue

                betrag_match = re.search(r"([\d.,]+)\s*€", text)
                betrag = betrag_match.group(1) if betrag_match else ""

                rechnungs_link = zeile.locator(
                    "a:has-text('Rechnung'), a:has-text('Invoice')"
                )
                if rechnungs_link.count() == 0:
                    logger.warning("Amazon: Keine Rechnung für Bestellung vom %s verfügbar.", belegdatum)
                    continue

                with page.expect_download() as download_info:
                    rechnungs_link.first.click()
                download = download_info.value

                dateiname = belegdateiname(belegdatum, "amazon", "Amazon")
                ziel_pfad = eindeutiger_pfad(zielordner, dateiname)
                download.save_as(ziel_pfad)

                gefunden.append(
                    Rechnung(
                        dateiname=ziel_pfad.name,
                        quelle="amazon",
                        quelle_detail=self.konto.name,
                        belegdatum=belegdatum,
                        aussteller="Amazon",
                        betrag=betrag,
                        waehrung="EUR",
                    )
                )

            browser.close()

        logger.info("Amazon: %d Rechnung(en) für %s heruntergeladen.", len(gefunden), monatsschluessel)
        return gefunden

    @staticmethod
    def _parse_deutsches_datum(match: re.Match) -> str:
        monatsnamen = {
            "januar": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4, "mai": 5,
            "juni": 6, "juli": 7, "august": 8, "september": 9, "oktober": 10,
            "november": 11, "dezember": 12,
        }
        tag, monatsname, jahr = match.groups()
        monat = monatsnamen.get(monatsname.lower())
        if not monat:
            return ""
        return f"{int(jahr):04d}-{monat:02d}-{int(tag):02d}"
