"""Lieferzeiten: Werktage, Feiertage, Bestellschluss."""
import datetime as dt

import pytest
from app.shipping import (
    BESTELLSCHLUSS,
    ZEITZONE,
    Versand,
    feiertage,
    ist_werktag,
    werktage_addieren,
)


def test_feiertage_nordrhein_westfalen_2026():
    f = feiertage(2026)
    assert dt.date(2026, 1, 1) in f       # Neujahr
    assert dt.date(2026, 4, 3) in f       # Karfreitag
    assert dt.date(2026, 4, 6) in f       # Ostermontag
    assert dt.date(2026, 5, 14) in f      # Christi Himmelfahrt
    assert dt.date(2026, 6, 4) in f       # Fronleichnam
    assert dt.date(2026, 10, 3) in f      # Tag der Deutschen Einheit
    assert dt.date(2026, 12, 25) in f
    assert dt.date(2026, 7, 15) not in f  # gewoehnlicher Mittwoch


def test_wochenende_und_feiertage_sind_keine_werktage():
    assert not ist_werktag(dt.date(2026, 10, 3))   # Samstag UND Feiertag
    assert not ist_werktag(dt.date(2026, 10, 4))   # Sonntag
    assert ist_werktag(dt.date(2026, 10, 5))       # Montag


def test_werktage_ueberspringen_wochenende():
    # Freitag + 1 Werktag = Montag
    assert werktage_addieren(dt.date(2026, 10, 9), 1) == dt.date(2026, 10, 12)
    # Freitag vor Ostern 2026: Karfreitag 3.4., Ostermontag 6.4.
    assert werktage_addieren(dt.date(2026, 4, 2), 1) == dt.date(2026, 4, 7)


def test_versandauskunft_vor_und_nach_bestellschluss(db, bestand):
    v = Versand(db)
    vormittag = dt.datetime(2026, 10, 5, 9, 0, tzinfo=ZEITZONE)   # Montag
    nachmittag = dt.datetime(2026, 10, 5, 16, 0, tzinfo=ZEITZONE)
    a = v.auskunft("DE", 1000, vormittag)
    b = v.auskunft("DE", 1000, nachmittag)
    assert a.versand_am == dt.date(2026, 10, 5)
    assert b.versand_am == dt.date(2026, 10, 6), "nach Bestellschluss erst am naechsten Werktag"
    assert BESTELLSCHLUSS.hour == 14


def test_sperrgut_kostet_mehr_und_dauert_laenger(db, bestand):
    v = Versand(db)
    jetzt = dt.datetime(2026, 10, 5, 9, 0, tzinfo=ZEITZONE)
    paket = v.auskunft("DE", 1000, jetzt)
    schwer = v.auskunft("DE", 45000, jetzt)     # Getriebe
    assert not paket.sperrgut and schwer.sperrgut
    assert schwer.versandkosten_euro > paket.versandkosten_euro
    assert schwer.spaeteste_ankunft > paket.spaeteste_ankunft
    assert "Spedition" in schwer.als_satz()


def test_unbekanntes_land(db, bestand):
    assert Versand(db).auskunft("XX") is None


def test_alle_zonen_plausibel(db, bestand):
    for z in Versand(db).zonen():
        assert z["cost_cents"] > 0
        assert 0 < z["days_min"] <= z["days_max"] <= 14
