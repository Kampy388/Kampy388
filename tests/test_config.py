import os
from pathlib import Path

import pytest

from rechnungsagent.config import Konfiguration

BEISPIEL_CONFIG = """
email_accounts:
  - name: privat
    imap_server: imap.gmx.net
    username: test@gmx.de
    password_env: TEST_PASSWORD
    suchbegriffe: [Rechnung, Invoice]

portale:
  adobe:
    aktiv: true
    storage_state: .auth/adobe_state.json

ablage:
  basis_ordner: Rechnungen
"""


def test_konfiguration_laden(tmp_path: Path):
    config_pfad = tmp_path / "config.yaml"
    config_pfad.write_text(BEISPIEL_CONFIG, encoding="utf-8")

    konfig = Konfiguration.laden(str(config_pfad), env_pfad=str(tmp_path / "nicht_vorhanden.env"))

    assert len(konfig.email_konten) == 1
    konto = konfig.email_konten[0]
    assert konto.name == "privat"
    assert konto.imap_port == 993  # Default
    assert konto.suchbegriffe == ["Rechnung", "Invoice"]

    assert "adobe" in konfig.portale
    assert konfig.portale["adobe"].aktiv is True
    assert konfig.ablage.basis_ordner == "Rechnungen"


def test_email_konto_password_fehlt_wirft_fehler(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    config_pfad = tmp_path / "config.yaml"
    config_pfad.write_text(BEISPIEL_CONFIG, encoding="utf-8")
    monkeypatch.delenv("TEST_PASSWORD", raising=False)

    konfig = Konfiguration.laden(str(config_pfad), env_pfad=str(tmp_path / "nicht_vorhanden.env"))
    with pytest.raises(RuntimeError):
        _ = konfig.email_konten[0].password


def test_email_konto_password_aus_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    config_pfad = tmp_path / "config.yaml"
    config_pfad.write_text(BEISPIEL_CONFIG, encoding="utf-8")
    monkeypatch.setenv("TEST_PASSWORD", "geheim")

    konfig = Konfiguration.laden(str(config_pfad), env_pfad=str(tmp_path / "nicht_vorhanden.env"))
    assert konfig.email_konten[0].password == "geheim"
