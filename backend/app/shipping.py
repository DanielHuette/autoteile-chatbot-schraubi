"""Liefergebiete, Versandkosten und Lieferdatum ab dem tatsächlichen Bestellzeitpunkt.

Kontext: Gerechnet wird mit Bestellschluss, Wochenende und Feiertagen in Nordrhein-Westfalen,
damit Freitag 17 Uhr nicht "2 Tage" heißt. | Eingabe: Ländercode, Gewicht, Zeitpunkt.
| Ergebnis: Lieferauskunft mit Kosten, Versandtag und Ankunftsspanne.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any
from zoneinfo import ZoneInfo

from .db import Database

ZEITZONE = ZoneInfo("Europe/Berlin")
BESTELLSCHLUSS = dt.time(14, 0)
SPERRGUT_AB_GRAMM = 31_500

FESTE_FEIERTAGE: dict[str, tuple[int, int]] = {
    "Neujahr": (1, 1),
    "Tag der Arbeit": (5, 1),
    "Tag der Deutschen Einheit": (10, 3),
    "Allerheiligen": (11, 1),
    "1. Weihnachtstag": (12, 25),
    "2. Weihnachtstag": (12, 26),
}
TAGE_NACH_OSTERSONNTAG: dict[str, int] = {
    "Karfreitag": -2,
    "Ostermontag": 1,
    "Christi Himmelfahrt": 39,
    "Pfingstmontag": 50,
    "Fronleichnam": 60,
}


def _ostersonntag(jahr: int) -> dt.date:
    """Gauss'sche Osterformel."""
    a, b, c = jahr % 19, jahr % 4, jahr % 7
    k = jahr // 100
    p = (13 + 8 * k) // 25
    q = k // 4
    m = (15 - p + k - q) % 30
    n = (4 + k - q) % 7
    d = (19 * a + m) % 30
    e = (2 * b + 4 * c + 6 * d + n) % 7
    tag = 22 + d + e
    if tag > 31:
        return dt.date(jahr, 4, tag - 31)
    return dt.date(jahr, 3, tag)


def feiertage(jahr: int) -> set[dt.date]:
    """Gesetzliche Feiertage in Nordrhein-Westfalen."""
    ostern = _ostersonntag(jahr)
    feste = {dt.date(jahr, monat, tag) for monat, tag in FESTE_FEIERTAGE.values()}
    bewegliche = {ostern + dt.timedelta(days=d) for d in TAGE_NACH_OSTERSONNTAG.values()}
    return feste | bewegliche


def ist_werktag(tag: dt.date) -> bool:
    return tag.weekday() < 5 and tag not in feiertage(tag.year)


def werktage_addieren(start: dt.date, anzahl: int) -> dt.date:
    tag = start
    offen = anzahl
    while offen > 0:
        tag += dt.timedelta(days=1)
        if ist_werktag(tag):
            offen -= 1
    return tag


@dataclass
class Lieferauskunft:
    land: str
    land_code: str
    versandkosten_euro: float
    sperrgut: bool
    versand_am: dt.date
    frueheste_ankunft: dt.date
    spaeteste_ankunft: dt.date
    hinweis: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "land": self.land,
            "land_code": self.land_code,
            "versandkosten_euro": self.versandkosten_euro,
            "sperrgut": self.sperrgut,
            "versand_am": self.versand_am.isoformat(),
            "frueheste_ankunft": self.frueheste_ankunft.isoformat(),
            "spaeteste_ankunft": self.spaeteste_ankunft.isoformat(),
            "text": self.als_satz(),
            "hinweis": self.hinweis,
        }

    def als_satz(self) -> str:
        fmt = "%d.%m.%Y"
        teil = (
            f"Versand nach {self.land} kostet {self.versandkosten_euro:.2f} Euro. "
            f"Wir verschicken am {self.versand_am.strftime(fmt)}, "
        )
        if self.frueheste_ankunft == self.spaeteste_ankunft:
            teil += f"Ankunft voraussichtlich am {self.frueheste_ankunft.strftime(fmt)}."
        else:
            teil += (
                f"Ankunft voraussichtlich zwischen dem "
                f"{self.frueheste_ankunft.strftime(fmt)} und dem "
                f"{self.spaeteste_ankunft.strftime(fmt)}."
            )
        if self.sperrgut:
            teil += (
                " Dieses Teil ist zu groß für den Paketversand und geht per "
                "Spedition. Die Spedition meldet sich telefonisch zur Terminabsprache."
            )
        if self.hinweis:
            teil += " " + self.hinweis
        return teil


class Versand:
    def __init__(self, db: Database) -> None:
        self.db = db

    def zonen(self) -> list[dict[str, Any]]:
        with self.db.conn() as c:
            return [
                dict(r)
                for r in c.execute(
                    """SELECT country_code, country_name, zone, cost_cents,
                              days_min, days_max, bulky_surcharge_cents
                         FROM shipping_zones ORDER BY country_name"""
                ).fetchall()
            ]

    def zone(self, land_code: str) -> dict[str, Any] | None:
        with self.db.conn() as c:
            row = c.execute(
                """SELECT country_code, country_name, zone, cost_cents,
                          days_min, days_max, bulky_surcharge_cents
                     FROM shipping_zones WHERE country_code = upper(%s)""",
                (land_code,),
            ).fetchone()
        return dict(row) if row else None

    def auskunft(
        self,
        land_code: str,
        gewicht_gramm: int = 1000,
        jetzt: dt.datetime | None = None,
    ) -> Lieferauskunft | None:
        z = self.zone(land_code)
        if not z:
            return None
        jetzt = jetzt or dt.datetime.now(ZEITZONE)
        if jetzt.tzinfo is None:
            jetzt = jetzt.replace(tzinfo=ZEITZONE)
        heute = jetzt.date()
        if ist_werktag(heute) and jetzt.time() < BESTELLSCHLUSS:
            versand_am = heute
        else:
            versand_am = werktage_addieren(heute, 1)

        sperrgut = gewicht_gramm >= SPERRGUT_AB_GRAMM
        kosten = z["cost_cents"] + (z["bulky_surcharge_cents"] if sperrgut else 0)
        zuschlag_tage = 2 if sperrgut else 0

        return Lieferauskunft(
            land=z["country_name"],
            land_code=z["country_code"],
            versandkosten_euro=round(kosten / 100, 2),
            sperrgut=sperrgut,
            versand_am=versand_am,
            frueheste_ankunft=werktage_addieren(versand_am, z["days_min"] + zuschlag_tage),
            spaeteste_ankunft=werktage_addieren(versand_am, z["days_max"] + zuschlag_tage),
        )
