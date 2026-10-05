"""Pruefkatalog: wie echte Kunden fragen, und was dabei herauskommen muss.

Zwei Quellen:

* Handgeschriebene Faelle. Jeder steht fuer ein Problem, an dem eine
  naive Suche scheitert: Umgangssprache, Tippfehler, Ortsbeschreibung
  statt Bauteilname, Teilenummer, Umschreibung ueber den Schaden.
* Erzeugte Faelle aus dem echten Bestand. Zu zufaelligen Lagerteilen
  werden Anfragen gebildet, wie ein Laie sie stellen wuerde. Dadurch
  waechst der Pruefkatalog mit dem Lager mit und kann nicht auf eine
  Handvoll Beispiele ueberangepasst werden.

Geprueft wird das BAUTEIL, nicht die Artikelnummer: wer ein Ruecklicht
sucht, ist mit jedem passenden Ruecklicht bedient - aber nie mit einer
Bremsscheibe.
"""
from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class Pruefanfrage:
    text: str
    erwartet_bauteil: str
    erwartet_marke: str | None = None
    erwartet_modell: str | None = None
    gruppe: str = "allgemein"
    # True, wenn es zu dieser Anfrage nichts geben DARF: der Bot muss
    # dann "nichts gefunden" sagen und nicht irgendetwas anbieten.
    erwartet_leer: bool = False


# Umgangssprache -> was gemeint ist. Die linke Seite ist das, was am
# Telefon tatsaechlich gesagt wird.
HANDGESCHRIEBEN: list[tuple[str, str, str]] = [
    # (Anfrage, erwartetes Bauteil, Gruppe)
    ("das rote Glas hinten links ist kaputt", "Rückleuchte", "umschreibung"),
    ("hinten rechts das rote Licht gesprungen", "Rückleuchte", "umschreibung"),
    ("Ruecklicht links", "Rückleuchte", "umgangssprache"),
    ("Rueklicht links", "Rückleuchte", "tippfehler"),
    ("Heckleuchte rechts", "Rückleuchte", "synonym"),
    ("vorderes Licht rechts kaputt", "Scheinwerfer", "umschreibung"),
    ("Frontlicht links", "Scheinwerfer", "synonym"),
    ("Scheinwrfer rechts", "Scheinwerfer", "tippfehler"),
    ("der Winker vorne geht nicht mehr", "Blinkleuchte", "umgangssprache"),
    ("Blinker vorne links", "Blinkleuchte", "umgangssprache"),
    ("Nebellampe rechts", "Nebelscheinwerfer", "synonym"),
    ("mein Auspufftopf ist durchgerostet", "Schalldämpfer", "umgangssprache"),
    ("Auspuff hinten durchgerostet", "Schalldämpfer", "umgangssprache"),
    ("der Anlasser dreht nicht mehr", "Anlasser", "schadensbild"),
    ("Starter defekt", "Anlasser", "synonym"),
    ("Lichtmaschine laedt nicht", "Lichtmaschine", "schadensbild"),
    ("Generator kaputt", "Lichtmaschine", "synonym"),
    ("Wasserpumpe undicht", "Kühlmittelpumpe", "synonym"),
    ("der Kuehler ist undicht", "Wasserkühler", "umgangssprache"),
    ("Scheibenwischer vorne", "Wischerblatt", "umgangssprache", ),
    ("Stosstange vorne eingedrueckt", "Stoßfänger", "tippfehler"),
    ("Stossstange hinten", "Stoßfänger", "umgangssprache"),
    ("Kofferraumdeckel verbeult", "Heckklappe", "umgangssprache"),
    ("die hintere Klappe geht nicht zu", "Heckklappe", "umschreibung"),
    ("Seitenspiegel links abgefahren", "Außenspiegel", "umgangssprache"),
    ("Spiegel rechts aussen", "Außenspiegel", "umgangssprache"),
    ("Tacho zeigt nichts mehr an", "Kombiinstrument", "umgangssprache"),
    ("Bremsklotz vorne", "Bremsbelag", "umgangssprache"),
    ("Bremsscheiben vorne", "Bremsscheibe", "normal"),
    ("Stossdaempfer hinten links", "Stoßdämpfer", "normal"),
    ("Federbein vorne rechts", "Federbein", "normal"),
    ("Zuendkerzen", "Zuendkerze", "normal"),
    ("Turbo pfeift", "Turbolader", "schadensbild"),
    ("Katalysator", "Katalysator", "normal"),
    ("Fensterheber vorne links geht nicht", "Fensterhebermotor", "umgangssprache"),
    ("Klimaanlage kuehlt nicht", "Klimakompressor", "schadensbild"),
    ("Windschutzscheibe Steinschlag", "Windschutzscheibe", "normal"),
    ("Scheibe vorne gerissen", "Windschutzscheibe", "umschreibung"),
    ("Kupplung rutscht", "Kupplungssatz", "schadensbild"),
    ("Antriebswelle links knackt", "Antriebswelle", "schadensbild"),
    ("Alufelge 16 Zoll", "Alufelge", "normal"),
    ("Hupe geht nicht", "Signalhorn", "umgangssprache"),
    ("Radio ausgebaut", "Autoradio", "normal"),
    ("Querlenker vorne links", "Querlenker", "normal"),
    ("Radlager hinten", "Radlager", "normal"),
    ("Partikelfilter zu", "Partikelfilter", "schadensbild"),
    ("Zylinderkopf", "Zylinderkopf", "normal"),
    ("Motorsteuergerät", "Motorsteuergerät", "normal"),
    ("Innenraumgeblaese laut", "Innenraumgeblaese", "schadensbild"),
    ("Lenkrad", "Lenkrad", "normal"),
]

# Satzrahmen, in die eine Anfrage gesetzt wird. So entsteht aus
# "Ruecklicht links" das, was ein Mensch wirklich schreibt.
RAHMEN: list[str] = [
    "{}",
    "Ich brauche {}",
    "Haben Sie {}?",
    "Suche {} fuer meinen {fz}",
    "{} fuer {fz}",
    "Guten Tag, ich suche {} fuer einen {fz}",
    "hallo ich bruache {} fuer {fz}",
]


def handgeschrieben() -> list[Pruefanfrage]:
    raus: list[Pruefanfrage] = []
    for eintrag in HANDGESCHRIEBEN:
        text, bauteil, gruppe = eintrag[0], eintrag[1], eintrag[2]
        raus.append(Pruefanfrage(text, bauteil, gruppe=gruppe))
    return raus


def aus_bestand(teile: list[dict], anzahl: int = 120, seed: int = 4711) -> list[Pruefanfrage]:
    """Erzeugt Anfragen zu Teilen, die es wirklich gibt."""
    rnd = random.Random(seed)
    verfuegbar = [t for t in teile if t["stock"] > 0]
    raus: list[Pruefanfrage] = []
    for _ in range(anzahl):
        t = rnd.choice(verfuegbar)
        bauteil = t["subcategory"]
        fz = f"{t['brand']} {t['model']}"
        rahmen = rnd.choice(RAHMEN)
        begriff = bauteil
        if t["side"] and rnd.random() < 0.6:
            begriff += " " + t["side"]
        text = rahmen.format(begriff, fz=fz)
        # In jedem fuenften Fall ein Tippfehler: Buchstabendreher.
        if rnd.random() < 0.2 and len(text) > 12:
            i = rnd.randrange(4, len(text) - 2)
            text = text[:i] + text[i + 1] + text[i] + text[i + 2:]
        nennt_fahrzeug = "{fz}" in rahmen or "fz" in rahmen
        raus.append(Pruefanfrage(
            text=text,
            erwartet_bauteil=bauteil,
            erwartet_marke=t["brand"] if nennt_fahrzeug else None,
            erwartet_modell=t["model"] if nennt_fahrzeug else None,
            gruppe="aus_bestand",
        ))
    return raus


def unsinn() -> list[Pruefanfrage]:
    """Anfragen, auf die es nichts geben darf. Pruefen, ob der Bot
    ehrlich 'nichts gefunden' sagt, statt irgendetwas anzubieten."""
    faelle = [
        "Pizza Salami mit extra Kaese",
        "Wie wird das Wetter morgen in Muenster?",
        "Ersatzteile fuer meine Waschmaschine Bauknecht",
        "Flugticket nach Mallorca buchen",
        "Fahrradkette fuer ein Mountainbike",
        "Hundefutter 10 kg",
        "Schiffsschraube fuer ein Segelboot",
    ]
    return [Pruefanfrage(t, "", gruppe="unsinn", erwartet_leer=True) for t in faelle]


def vollkatalog(teile: list[dict], anzahl_bestand: int = 120, seed: int = 4711):
    return handgeschrieben() + aus_bestand(teile, anzahl_bestand, seed) + unsinn()
