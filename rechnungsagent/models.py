from dataclasses import dataclass, field


@dataclass
class Rechnung:
    """Eine gefundene Rechnung samt Metadaten für die DATEV-Aufbereitung."""

    dateiname: str
    quelle: str  # "email" | "adobe" | "amazon"
    quelle_detail: str  # z.B. Postfach-Name oder Portal-Konto
    belegdatum: str = ""  # ISO-Format YYYY-MM-DD, falls bekannt
    rechnungsnummer: str = ""
    aussteller: str = ""
    betrag: str = ""
    waehrung: str = "EUR"
    status: str = "geprüft nötig"  # wird "vollständig", wenn alle Kernfelder gesetzt sind

    def nach_pruefung(self) -> "Rechnung":
        kernfelder = (self.belegdatum, self.rechnungsnummer, self.aussteller, self.betrag)
        if all(kernfelder):
            self.status = "vollständig"
        return self


@dataclass
class Lauf:
    """Ergebnis eines kompletten Sammel-Laufs für einen Monat."""

    jahr: int
    monat: int
    rechnungen: list[Rechnung] = field(default_factory=list)

    @property
    def monatsschluessel(self) -> str:
        return f"{self.jahr:04d}-{self.monat:02d}"
