## Rechnungsagent – Automatisierung der vorbereitenden Buchhaltung

Ein lokales Kommandozeilen-Tool, das für einen Monat automatisch alle
nötigen Eingangsrechnungen sammelt:

- **E-Mail-Postfächer** (beliebig viele, per IMAP) – findet Mails mit
  Rechnungs-Stichworten im Betreff und speichert die PDF-Anhänge.
- **Anbieter-Portale** – aktuell **Adobe** und **Amazon**, per Browser-Login
  (Playwright). Login-Zugangsdaten werden nicht gespeichert; du loggst dich
  einmalig manuell in einem sichtbaren Browserfenster ein (inkl. 2FA), danach
  wird die Session wiederverwendet.

Alle Rechnungen landen in `Rechnungen/JJJJ-MM/`, benannt nach dem Schema
`Datum_Aussteller_Quelle.pdf`, zusammen mit einer CSV
(`rechnungen_JJJJ-MM.csv`) mit Beleg-Metadaten (Datum, Rechnungsnummer,
Aussteller, Betrag, Dateiname, Quelle, Status) als Vorbereitung für den
Import in DATEV oder vergleichbare Buchhaltungssoftware. Belege, bei denen
nicht alle Angaben automatisch ermittelt werden konnten, werden mit dem
Status `geprüft nötig` markiert – diese CSV-Zeilen solltest du vor dem
Import manuell ergänzen/prüfen.

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

cp config.example.yaml config.yaml   # eigene Postfächer/Portale eintragen
cp .env.example .env                 # Passwörter eintragen (NICHT committen)
```

`config.yaml` und `.env` werden lokal gehalten und sind bereits in
`.gitignore` ausgeschlossen. Für E-Mail-Postfächer mit Zwei-Faktor-
Authentifizierung (z.B. GMail, Web.de) ein **App-Passwort** statt des
normalen Kontopassworts verwenden.

### Portal-Login einmalig einrichten

```bash
python -m rechnungsagent.cli login adobe
python -m rechnungsagent.cli login amazon
```

Es öffnet sich ein sichtbares Browserfenster. Dort ganz normal einloggen
(inkl. evtl. 2FA), danach im Terminal ENTER drücken – die Session wird unter
`.auth/` gespeichert und für spätere Läufe wiederverwendet.

### Monatliche Rechnungen abrufen

```bash
python -m rechnungsagent.cli run --monat 2026-07
# ohne --monat wird automatisch der aktuelle Monat verwendet
```

### Hinweise & Grenzen

- Die Portal-Selektoren (Adobe/Amazon) sind ein Best-Effort-Ansatz und
  können sich ändern, wenn die Anbieter ihre Webseiten aktualisieren.
  Schlägt ein Download fehl, gibt das Tool eine Warnung mit Klartext-Hinweis
  aus – die betroffene Rechnung dann übergangsweise manuell herunterladen.
- Es werden keine Passwörter für Adobe/Amazon gespeichert oder automatisiert
  eingegeben – nur die Browser-Session nach manuellem Login.
- Für Portale mit Bot-Erkennung/Captcha kann ein erneuter manueller Login
  nötig werden, falls die gespeicherte Session abläuft.

### Tests

```bash
pytest
```

Die Tests decken die reine Logik ab (Dateibenennung, CSV-Export,
Konfigurations-Parsing) – ohne echte Netzwerk-/IMAP-/Browser-Zugriffe.
