"""Erzeugt realistische Testbestaende.

Wird von der Testreihe und von der Messreihe genutzt. Die Teile sind
erfunden, aber die Struktur entspricht einem echten Gebrauchtteilelager:
Marke, Modell, Baujahrspanne, Kategorie, Bauteil, Lage, Zustand,
Vergleichsnummern, eBay-Markierung.
"""
from __future__ import annotations

import random

FAHRZEUGE: list[tuple[str, str, int, int]] = [
    ("Volkswagen", "Golf IV", 1997, 2003), ("Volkswagen", "Golf V", 2003, 2008),
    ("Volkswagen", "Golf VI", 2008, 2012), ("Volkswagen", "Golf VII", 2012, 2019),
    ("Volkswagen", "Passat B6", 2005, 2010), ("Volkswagen", "Passat B7", 2010, 2014),
    ("Volkswagen", "Polo 9N", 2001, 2009), ("Volkswagen", "Touran I", 2003, 2010),
    ("Volkswagen", "Caddy III", 2004, 2015),
    ("Opel", "Astra G", 1998, 2004), ("Opel", "Astra H", 2004, 2010),
    ("Opel", "Astra J", 2009, 2015), ("Opel", "Corsa C", 2000, 2006),
    ("Opel", "Corsa D", 2006, 2014), ("Opel", "Insignia A", 2008, 2017),
    ("Opel", "Zafira B", 2005, 2014), ("Opel", "Vectra C", 2002, 2008),
    ("BMW", "3er E46", 1998, 2005), ("BMW", "3er E90", 2005, 2012),
    ("BMW", "3er F30", 2011, 2019), ("BMW", "5er E60", 2003, 2010),
    ("BMW", "5er F10", 2010, 2017), ("BMW", "1er E87", 2004, 2011),
    ("BMW", "X3 E83", 2003, 2010),
    ("Mercedes-Benz", "C-Klasse W203", 2000, 2007),
    ("Mercedes-Benz", "C-Klasse W204", 2007, 2014),
    ("Mercedes-Benz", "E-Klasse W211", 2002, 2009),
    ("Mercedes-Benz", "A-Klasse W169", 2004, 2012),
    ("Mercedes-Benz", "Sprinter 906", 2006, 2018),
    ("Audi", "A3 8P", 2003, 2012), ("Audi", "A4 B7", 2004, 2008),
    ("Audi", "A4 B8", 2007, 2015), ("Audi", "A6 C6", 2004, 2011),
    ("Audi", "Q5 8R", 2008, 2017),
    ("Ford", "Focus II", 2004, 2011), ("Ford", "Focus III", 2010, 2018),
    ("Ford", "Fiesta VI", 2008, 2017), ("Ford", "Mondeo IV", 2007, 2014),
    ("Ford", "Transit VI", 2006, 2014),
    ("Renault", "Clio III", 2005, 2012), ("Renault", "Megane III", 2008, 2016),
    ("Renault", "Kangoo II", 2008, 2021),
    ("Toyota", "Corolla E12", 2001, 2007), ("Toyota", "Yaris XP9", 2005, 2011),
    ("Toyota", "Avensis T25", 2003, 2009),
    ("Skoda", "Octavia II", 2004, 2013), ("Skoda", "Fabia II", 2007, 2014),
    ("Skoda", "Superb II", 2008, 2015),
    ("Seat", "Leon 1P", 2005, 2012), ("Seat", "Ibiza 6L", 2002, 2008),
    ("Peugeot", "207", 2006, 2014), ("Peugeot", "308 I", 2007, 2014),
    ("Fiat", "Punto 199", 2005, 2018), ("Fiat", "Ducato 250", 2006, 2021),
    ("Nissan", "Qashqai J10", 2007, 2013), ("Nissan", "Micra K12", 2003, 2010),
    ("Hyundai", "i30 FD", 2007, 2012), ("Kia", "Ceed ED", 2006, 2012),
    ("Volvo", "V50", 2004, 2012), ("Mazda", "3 BK", 2003, 2009),
]

# (Kategorie, Bauteil, erlaubte Lagen, Preisspanne Euro, Gewicht Gramm)
# Die Lagen sind nicht beliebig: eine Rueckleuchte sitzt nie vorne, ein
# Scheinwerfer nie hinten. Testdaten, die das verletzen, erzeugen
# Scheinfehler in der Messreihe.
L_LR = ("links", "rechts")
L_VH = ("vorne", "hinten")
L_ALLE = ("links", "rechts", "vorne", "hinten")
L_KEINE: tuple[str, ...] = ()
BAUTEILE: list[tuple[str, str, tuple[str, ...], tuple[int, int], int]] = [
    ("Beleuchtung", "Rückleuchte", L_LR, (25, 180), 1200),
    ("Beleuchtung", "Scheinwerfer", L_LR, (45, 420), 3500),
    ("Beleuchtung", "Blinkleuchte", L_LR, (12, 60), 400),
    ("Beleuchtung", "Nebelscheinwerfer", L_LR, (20, 95), 700),
    ("Beleuchtung", "Kennzeichenleuchte", L_KEINE, (8, 30), 150),
    ("Beleuchtung", "Bremsleuchte", L_LR, (18, 90), 600),
    ("Karosserie", "Stoßfänger", L_VH, (80, 480), 7500),
    ("Karosserie", "Kotflügel", L_LR, (55, 260), 5200),
    ("Karosserie", "Motorhaube", L_KEINE, (110, 520), 14000),
    ("Karosserie", "Heckklappe", L_KEINE, (130, 650), 16000),
    ("Karosserie", "Tür", L_ALLE, (140, 700), 22000),
    ("Karosserie", "Außenspiegel", L_LR, (35, 240), 1400),
    ("Karosserie", "Schiebedach", L_KEINE, (180, 760), 18000),
    ("Motor", "Zylinderkopf", L_KEINE, (220, 1400), 24000),
    ("Motor", "Turbolader", L_KEINE, (190, 980), 6500),
    ("Motor", "Lichtmaschine", L_KEINE, (75, 390), 6000),
    ("Motor", "Anlasser", L_KEINE, (60, 280), 4200),
    ("Motor", "Kraftstoffpumpe", L_KEINE, (55, 300), 1800),
    ("Motor", "Zündspule", L_KEINE, (18, 85), 500),
    ("Motor", "Motorsteuergerät", L_KEINE, (140, 720), 900),
    ("Motor", "Ansaugbrücke", L_KEINE, (70, 340), 3200),
    ("Bremsen", "Bremsscheibe", L_VH, (18, 95), 6500),
    ("Bremsen", "Bremssattel", L_ALLE, (45, 260), 4000),
    ("Bremsen", "Bremskraftverstaerker", L_KEINE, (80, 320), 5500),
    ("Bremsen", "ABS-Steuergerät", L_KEINE, (110, 480), 2200),
    ("Fahrwerk", "Stoßdämpfer", L_ALLE, (35, 190), 4500),
    ("Fahrwerk", "Federbein", L_ALLE, (55, 280), 6200),
    ("Fahrwerk", "Querlenker", L_LR, (28, 150), 3600),
    ("Fahrwerk", "Spurstange", L_LR, (18, 85), 1200),
    ("Fahrwerk", "Radlager", L_ALLE, (25, 130), 2200),
    ("Fahrwerk", "Achsschenkel", L_LR, (60, 290), 7000),
    ("Innenraum", "Vordersitz", L_LR, (90, 460), 19000),
    ("Innenraum", "Rückbank", L_KEINE, (120, 580), 26000),
    ("Innenraum", "Lenkrad", L_KEINE, (45, 320), 2600),
    ("Innenraum", "Kombiinstrument", L_KEINE, (70, 390), 1400),
    ("Innenraum", "Handschuhfach", L_KEINE, (25, 120), 1900),
    ("Innenraum", "Innenraumgeblaese", L_KEINE, (35, 180), 2400),
    ("Innenraum", "Armaturenbrett", L_KEINE, (150, 690), 15000),
    ("Elektrik", "Fensterhebermotor", L_ALLE, (28, 140), 1600),
    ("Elektrik", "Zentralverriegelung Stellmotor", L_ALLE, (22, 110), 600),
    ("Elektrik", "Autoradio", L_KEINE, (30, 260), 1800),
    ("Elektrik", "Signalhorn", L_KEINE, (12, 55), 400),
    ("Elektrik", "Komfortsteuergeraet", L_KEINE, (80, 380), 800),
    ("Abgasanlage", "Schalldämpfer", L_KEINE, (55, 280), 9000),
    ("Abgasanlage", "Katalysator", L_KEINE, (120, 680), 7500),
    ("Abgasanlage", "Partikelfilter", L_KEINE, (180, 890), 11000),
    ("Abgasanlage", "Abgaskrümmer", L_KEINE, (70, 340), 5000),
    ("Kühlung", "Wasserkühler", L_KEINE, (55, 260), 5500),
    ("Kühlung", "Kühlerlüfter", L_KEINE, (45, 220), 3800),
    ("Kühlung", "Kühlmittelpumpe", L_KEINE, (30, 160), 1700),
    ("Kühlung", "Klimakompressor", L_KEINE, (95, 420), 6800),
    ("Kühlung", "Wärmetauscher", L_KEINE, (40, 190), 2900),
    ("Getriebe", "Schaltgetriebe", L_KEINE, (280, 1600), 42000),
    ("Getriebe", "Automatikgetriebe", L_KEINE, (420, 2400), 68000),
    ("Getriebe", "Kupplungssatz", L_KEINE, (70, 360), 8500),
    ("Getriebe", "Antriebswelle", L_LR, (55, 280), 7200),
    ("Getriebe", "Schaltbetätigung", L_KEINE, (40, 190), 2600),
    ("Räder", "Alufelge", L_KEINE, (35, 220), 9500),
    ("Räder", "Stahlfelge", L_KEINE, (18, 85), 8200),
    ("Räder", "Radnabe", L_ALLE, (30, 150), 3100),
    ("Glas", "Windschutzscheibe", L_KEINE, (80, 340), 13000),
    ("Glas", "Heckscheibe", L_KEINE, (60, 280), 9000),
    ("Glas", "Seitenscheibe", L_ALLE, (35, 160), 4200),
]

ZUSTAENDE = [
    "gebraucht, geprüft", "gebraucht, guter Zustand", "gebraucht, leichte Gebrauchsspuren",
    "gebraucht, sehr gut", "generalüberholt",
]
BESCHREIBUNGEN = [
    "Ausgebaut aus einem Unfallfahrzeug mit {km} km Laufleistung. Funktion geprüft.",
    "Originalteil, {km} km gelaufen. Sichtprüfung ohne Befund.",
    "Gebrauchtteil mit {km} km. Leichte Gebrauchsspuren, voll funktionsfähig.",
    "Demontiert von einem Fahrzeug mit {km} km. Dichtungen in Ordnung.",
    "Sofort einbaufertig, {km} km Laufleistung, keine Risse oder Bruchstellen.",
]


def erzeugen(anzahl: int, seed: int = 20261005, ebay_anteil: float = 0.22) -> list[dict]:
    """Erzeugt `anzahl` Teile. Gleicher seed = gleiche Daten."""
    rnd = random.Random(seed)
    teile: list[dict] = []
    gesehen: set[str] = set()
    nr = 0
    while len(teile) < anzahl:
        nr += 1
        marke, modell, bj_von, bj_bis = rnd.choice(FAHRZEUGE)
        kategorie, bauteil, lagen, (p_min, p_max), gewicht = rnd.choice(BAUTEILE)
        # Bei Teilen mit Lage wird in einem von fuenf Faellen keine
        # angegeben - so fuehrt das Lager es in der Praxis auch.
        lage = rnd.choice(lagen) if lagen and rnd.random() > 0.2 else ""
        sku = f"TT-{nr:06d}"
        if sku in gesehen:
            continue
        gesehen.add(sku)

        titel_teile = [bauteil]
        if lage:
            titel_teile.append(lage)
        titel_teile.append(f"{marke} {modell}")
        titel = " ".join(titel_teile)

        auf_ebay = rnd.random() < ebay_anteil
        km = rnd.randrange(45, 290) * 1000
        teile.append({
            "sku": sku,
            "title": titel,
            "description": rnd.choice(BESCHREIBUNGEN).format(km=f"{km:,}".replace(",", ".")),
            "brand": marke,
            "model": modell,
            "year_from": bj_von,
            "year_to": bj_bis,
            "category": kategorie,
            "subcategory": bauteil,
            "side": lage,
            "condition": rnd.choice(ZUSTAENDE),
            "price_cents": rnd.randrange(p_min * 100, p_max * 100, 50),
            "stock": rnd.choices([0, 1, 1, 1, 2, 3], weights=[1, 5, 5, 5, 2, 1])[0],
            "weight_grams": int(gewicht * rnd.uniform(0.85, 1.15)),
            "oem_numbers": [
                f"{rnd.choice('1234568ABK')}{rnd.randrange(10,99)}"
                f"{rnd.randrange(100000,999999)}{rnd.choice('ABCDEFGHJK')}"
                for _ in range(rnd.randrange(1, 4))
            ],
            "on_ebay": auf_ebay,
            "ebay_url": (
                f"https://www.ebay.de/itm/{rnd.randrange(100000000000, 999999999999)}"
                if auf_ebay else ""
            ),
            "active": True,
        })
    return teile


def verkaeufe_erzeugen(teile: list[dict], anzahl: int, seed: int = 7) -> list[dict]:
    """Verkaufshistorie der letzten 120 Tage fuer die Betreiberzahlen."""
    import datetime as dt

    rnd = random.Random(seed)
    heute = dt.datetime.now(dt.UTC)
    verkauft = [t for t in teile if t["price_cents"] > 0]
    zeilen = []
    for i in range(anzahl):
        t = rnd.choice(verkauft)
        tage_zurueck = int(abs(rnd.gauss(0, 40))) % 120
        menge = rnd.choices([1, 1, 1, 2], weights=[8, 4, 2, 1])[0]
        zeilen.append({
            "order_ref": f"A-2026-{10000 + i}",
            "part_sku": t["sku"],
            "sold_at": (heute - dt.timedelta(days=tage_zurueck,
                                             hours=rnd.randrange(0, 24))),
            "quantity": menge,
            "revenue_cents": t["price_cents"] * menge,
            "channel": "ebay" if t["on_ebay"] and rnd.random() < 0.7 else "shop",
        })
    return zeilen


if __name__ == "__main__":
    import json
    import sys

    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    print(json.dumps(erzeugen(n), ensure_ascii=False, indent=2)[:3000])
