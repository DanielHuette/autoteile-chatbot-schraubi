"""Anmeldung der Betriebsleitung: Passwort, Sitzung, Manipulation."""
import time

import pytest
from app.auth import SitzungsVerwaltung, hash_erzeugen, hash_pruefen

GEHEIM = "g" * 48


def test_passwort_wird_nicht_im_klartext_gespeichert():
    h = hash_erzeugen("MeinPasswort2026!")
    assert "MeinPasswort2026!" not in h
    assert h.startswith("$scrypt$")


def test_richtiges_und_falsches_passwort():
    h = hash_erzeugen("MeinPasswort2026!")
    assert hash_pruefen("MeinPasswort2026!", h)
    assert not hash_pruefen("MeinPasswort2025!", h)
    assert not hash_pruefen("", h)


def test_gleiches_passwort_ergibt_unterschiedliche_hashes():
    # Zufallssalz: zwei Betriebe mit demselben Passwort sind nicht
    # an gleichen Hashes erkennbar.
    assert hash_erzeugen("Gleiches2026!") != hash_erzeugen("Gleiches2026!")


def test_zu_kurzes_passwort_wird_abgelehnt():
    with pytest.raises(ValueError):
        hash_erzeugen("kurz")


def test_kaputter_hash_ergibt_keine_anmeldung():
    assert not hash_pruefen("egal", "unsinn")
    assert not hash_pruefen("egal", "$md5$1$2$3$4$5")


def test_sitzung_ist_gueltig_und_manipulationssicher():
    sv = SitzungsVerwaltung(GEHEIM, 30)
    token, dauer = sv.ausstellen()
    assert dauer == 1800
    assert sv.pruefen(token).rolle == "betreiber"
    # Ein veraendertes Zeichen macht die Sitzung ungueltig.
    assert sv.pruefen(token[:-2] + "xy") is None
    assert sv.pruefen(token.split(".")[0] + ".falsch") is None
    assert sv.pruefen(None) is None
    assert sv.pruefen("") is None


def test_fremdes_geheimnis_wird_nicht_akzeptiert():
    token, _ = SitzungsVerwaltung("a" * 48, 30).ausstellen()
    assert SitzungsVerwaltung("b" * 48, 30).pruefen(token) is None


def test_abgelaufene_sitzung():
    sv = SitzungsVerwaltung(GEHEIM, 0)
    token, _ = sv.ausstellen()
    time.sleep(1.1)
    assert sv.pruefen(token) is None


def test_abmeldung_macht_sitzung_sofort_ungueltig():
    sv = SitzungsVerwaltung(GEHEIM, 30)
    token, _ = sv.ausstellen()
    assert sv.pruefen(token) is not None
    sv.widerrufen(token)
    assert sv.pruefen(token) is None
