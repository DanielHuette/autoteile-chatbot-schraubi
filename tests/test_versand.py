"""Lieferzeiten: Werktage, Feiertage in Nordrhein-Westfalen, Bestellschluss, Sperrgut.

Kontext: Tests zu shipping.py. | Eingabe: Feste Daten im Jahr 2026, Liefergebiete der
Testdatenbank. | Ergebnis: Pytest-Befunde.
"""

import datetime as dt
from typing import Any

from app.db import Database
from app.shipping import (
    BESTELLSCHLUSS,
    ZEITZONE,
    Versand,
    feiertage,
    ist_werktag,
    werktage_addieren,
)

FEIERTAGE_2026 = {
    "Neujahr": dt.date(2026, 1, 1),
    "Karfreitag": dt.date(2026, 4, 3),
    "Ostermontag": dt.date(2026, 4, 6),
    "Christi Himmelfahrt": dt.date(2026, 5, 14),
    "Fronleichnam": dt.date(2026, 6, 4),
    "Tag der Deutschen Einheit": dt.date(2026, 10, 3),
    "1. Weihnachtstag": dt.date(2026, 12, 25),
}
MONTAG = dt.date(2026, 10, 5)


def test_feiertage_nordrhein_westfalen_2026() -> None:
    f = feiertage(2026)
    for name, tag in FEIERTAGE_2026.items():
        assert tag in f, name
    gewoehnlicher_mittwoch = dt.date(2026, 7, 15)
    assert gewoehnlicher_mittwoch not in f


def test_wochenende_und_feiertage_sind_keine_werktage() -> None:
    samstag_und_feiertag = dt.date(2026, 10, 3)
    sonntag = dt.date(2026, 10, 4)
    assert not ist_werktag(samstag_und_feiertag)
    assert not ist_werktag(sonntag)
    assert ist_werktag(MONTAG)


def test_werktage_ueberspringen_wochenende() -> None:
    freitag, montag = dt.date(2026, 10, 9), dt.date(2026, 10, 12)
    assert werktage_addieren(freitag, 1) == montag
    gruendonnerstag, dienstag_nach_ostern = dt.date(2026, 4, 2), dt.date(2026, 4, 7)
    assert werktage_addieren(gruendonnerstag, 1) == dienstag_nach_ostern


def test_versandauskunft_vor_und_nach_bestellschluss(
    db: Database, bestand: list[dict[str, Any]]
) -> None:
    v = Versand(db)
    vormittag = dt.datetime(2026, 10, 5, 9, 0, tzinfo=ZEITZONE)
    nachmittag = dt.datetime(2026, 10, 5, 16, 0, tzinfo=ZEITZONE)
    a = v.auskunft("DE", 1000, vormittag)
    b = v.auskunft("DE", 1000, nachmittag)
    assert a.versand_am == MONTAG
    assert b.versand_am == dt.date(2026, 10, 6), "nach Bestellschluss erst am naechsten Werktag"
    assert BESTELLSCHLUSS.hour == 14


def test_sperrgut_kostet_mehr_und_dauert_laenger(
    db: Database, bestand: list[dict[str, Any]]
) -> None:
    v = Versand(db)
    jetzt = dt.datetime(2026, 10, 5, 9, 0, tzinfo=ZEITZONE)
    paket = v.auskunft("DE", 1000, jetzt)
    getriebe_gramm = 45_000
    schwer = v.auskunft("DE", getriebe_gramm, jetzt)
    assert not paket.sperrgut and schwer.sperrgut
    assert schwer.versandkosten_euro > paket.versandkosten_euro
    assert schwer.spaeteste_ankunft > paket.spaeteste_ankunft
    assert "Spedition" in schwer.als_satz()


def test_unbekanntes_land(db: Database, bestand: list[dict[str, Any]]) -> None:
    assert Versand(db).auskunft("XX") is None


def test_alle_zonen_plausibel(db: Database, bestand: list[dict[str, Any]]) -> None:
    for z in Versand(db).zonen():
        assert z["cost_cents"] > 0
        assert 0 < z["days_min"] <= z["days_max"] <= 14
