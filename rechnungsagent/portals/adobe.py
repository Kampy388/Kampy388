from __future__ import annotations

import logging
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

from ..models import Rechnung
from ..storage import belegdateiname, eindeutiger_pfad
from .base import PortalQuelle

logger = logging.getLogger(__name__)


class AdobePortal(PortalQuelle):
    """Lädt Rechnungen aus der Adobe-Bestellhistorie (account.adobe.com).

    Hinweis: Adobe ändert die Struktur seiner Kontoseiten regelmäßig, und die
    Selektoren unten wurden nicht gegen ein Live-Konto getestet. Falls der
    automatische Download fehlschlägt, bitte die CSS-Selektoren an die
    aktuelle Seite anpassen oder die Rechnungen für den Monat übergangsweise
    manuell unter https://account.adobe.com/orders herunterladen.
    """

    name = "adobe"
    start_url = "https://account.adobe.com/orders"

    def rechnungen_herunterladen(self, jahr: int, monat: int, zielordner: Path) -> list[Rechnung]:
        gefunden: list[Rechnung] = []
        monatsschluessel = f"{jahr:04d}-{monat:02d}"

        with sync_playwright() as pw:
            browser, context = self._browser_kontext(pw)
            page = context.new_page()
            page.goto(self.start_url, wait_until="networkidle")

            bestellungen = page.locator("[data-testid='order-row'], .order-row, li.order")
            anzahl = bestellungen.count()
            logger.info("Adobe: %d Bestellung(en) auf der Seite gefunden.", anzahl)

            for i in range(anzahl):
                zeile = bestellungen.nth(i)
                text = zeile.inner_text()

                datums_match = re.search(r"(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})", text)
                if not datums_match:
                    continue
                tag, mon, jahr_text = datums_match.groups()
                jahr_text = jahr_text if len(jahr_text) == 4 else f"20{jahr_text}"
                belegdatum = f"{jahr_text}-{int(mon):02d}-{int(tag):02d}"
                if not belegdatum.startswith(monatsschluessel):
                    continue

                betrag_match = re.search(r"([\d.,]+)\s*(€|EUR|USD|\$)", text)
                betrag = betrag_match.group(1) if betrag_match else ""

                download_link = zeile.locator(
                    "a:has-text('Rechnung'), a:has-text('Invoice'), a:has-text('Beleg')"
                )
                if download_link.count() == 0:
                    logger.warning("Adobe: Kein Rechnungslink für Bestellung vom %s gefunden.", belegdatum)
                    continue

                with page.expect_download() as download_info:
                    download_link.first.click()
                download = download_info.value

                dateiname = belegdateiname(belegdatum, "adobe", "Adobe")
                ziel_pfad = eindeutiger_pfad(zielordner, dateiname)
                download.save_as(ziel_pfad)

                gefunden.append(
                    Rechnung(
                        dateiname=ziel_pfad.name,
                        quelle="adobe",
                        quelle_detail=self.konto.name,
                        belegdatum=belegdatum,
                        aussteller="Adobe",
                        betrag=betrag,
                        waehrung="EUR",
                    )
                )

            browser.close()

        logger.info("Adobe: %d Rechnung(en) für %s heruntergeladen.", len(gefunden), monatsschluessel)
        return gefunden
