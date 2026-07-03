from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

from playwright.sync_api import Browser, BrowserContext, sync_playwright

from ..config import PortalKonto
from ..models import Rechnung

logger = logging.getLogger(__name__)


class PortalQuelle(ABC):
    """Basisklasse für Rechnungs-Portale, die eine eingeloggte Browser-Session
    benötigen (Adobe, Amazon, ...).

    Zugangsdaten werden NICHT gespeichert oder automatisiert eingegeben – der
    Nutzer loggt sich einmalig manuell in einem sichtbaren Browserfenster ein
    (inkl. 2FA/Captcha), danach wird die Session als Playwright-'storage_state'
    wiederverwendet. So bleibt der Login-Flow robust gegenüber 2FA und
    Bot-Erkennung, ohne Passwörter im Klartext zu speichern.
    """

    name: str = "portal"
    start_url: str = ""

    def __init__(self, konto: PortalKonto):
        self.konto = konto
        self.storage_state_pfad = Path(konto.storage_state)

    def login_einrichten(self) -> None:
        """Öffnet ein sichtbares Browserfenster zum manuellen Login. Nach dem
        Schließen des Fensters wird die Session gespeichert."""
        self.storage_state_pfad.parent.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            page.goto(self.start_url)
            print(
                f"\nBitte im geöffneten Browserfenster bei '{self.name}' einloggen "
                "(inkl. evtl. Zwei-Faktor-Bestätigung). Anschließend hier im "
                "Terminal ENTER drücken, um die Session zu speichern..."
            )
            input()
            context.storage_state(path=str(self.storage_state_pfad))
            browser.close()
        logger.info("Session für '%s' gespeichert unter %s", self.name, self.storage_state_pfad)

    def _browser_kontext(self, pw, headless: bool = True) -> tuple[Browser, BrowserContext]:
        if not self.storage_state_pfad.exists():
            raise RuntimeError(
                f"Keine gespeicherte Session für '{self.name}' gefunden. "
                f"Bitte zuerst 'python -m rechnungsagent.cli login {self.name}' ausführen."
            )
        browser = pw.chromium.launch(headless=headless)
        context = browser.new_context(storage_state=str(self.storage_state_pfad), accept_downloads=True)
        return browser, context

    @abstractmethod
    def rechnungen_herunterladen(self, jahr: int, monat: int, zielordner: Path) -> list[Rechnung]:
        """Lädt alle Rechnungen des angegebenen Monats herunter und gibt sie als
        Rechnung-Objekte zurück."""
        raise NotImplementedError
