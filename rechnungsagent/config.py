from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv


@dataclass
class EmailKonto:
    name: str
    imap_server: str
    imap_port: int
    username: str
    password_env: str
    ordner: str = "INBOX"
    suchbegriffe: list[str] = field(default_factory=lambda: ["Rechnung", "Invoice"])
    absender_filter: list[str] = field(default_factory=list)

    @property
    def password(self) -> str:
        pw = os.environ.get(self.password_env, "")
        if not pw:
            raise RuntimeError(
                f"Umgebungsvariable '{self.password_env}' für Postfach '{self.name}' "
                "ist nicht gesetzt. Bitte in .env eintragen (siehe .env.example)."
            )
        return pw


@dataclass
class PortalKonto:
    name: str
    aktiv: bool = True
    storage_state: str = ""  # Pfad zur gespeicherten Playwright-Session (aus 'login'-Befehl)


@dataclass
class Ablage:
    basis_ordner: str = "Rechnungen"


@dataclass
class Konfiguration:
    email_konten: list[EmailKonto]
    portale: dict[str, PortalKonto]
    ablage: Ablage

    @classmethod
    def laden(cls, pfad: str = "config.yaml", env_pfad: str = ".env") -> "Konfiguration":
        if Path(env_pfad).exists():
            load_dotenv(env_pfad)

        rohdaten = yaml.safe_load(Path(pfad).read_text(encoding="utf-8")) or {}

        email_konten = [
            EmailKonto(
                name=k["name"],
                imap_server=k["imap_server"],
                imap_port=int(k.get("imap_port", 993)),
                username=k["username"],
                password_env=k["password_env"],
                ordner=k.get("ordner", "INBOX"),
                suchbegriffe=k.get("suchbegriffe", ["Rechnung", "Invoice"]),
                absender_filter=k.get("absender_filter", []),
            )
            for k in rohdaten.get("email_accounts", [])
        ]

        portale = {
            name: PortalKonto(
                name=name,
                aktiv=daten.get("aktiv", True),
                storage_state=daten.get("storage_state", f".auth/{name}_state.json"),
            )
            for name, daten in (rohdaten.get("portale", {}) or {}).items()
        }

        ablage = Ablage(basis_ordner=(rohdaten.get("ablage", {}) or {}).get("basis_ordner", "Rechnungen"))

        return cls(email_konten=email_konten, portale=portale, ablage=ablage)
