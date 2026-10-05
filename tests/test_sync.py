"""Lagerabgleich: Formate, Pruefung, Fehlerzeilen, Vollabgleich."""
import io
import json

import pytest
from app.sync import Abgleich, datei_lesen, zeile_pruefen


@pytest.fixture(autouse=True)
def bestand_wiederherstellen(db, embedder, bestand):
    """Einige Tests hier machen einen Vollabgleich - der deaktiviert
    alles, was nicht in der Lieferung steht. Danach wird der Pruefbestand
    wiederhergestellt, damit die uebrigen Tests nicht davon abhaengen,
    in welcher Reihenfolge sie laufen."""
    yield
    from app.sync import Abgleich

    Abgleich(db, embedder).ausfuehren(bestand, vollabgleich=True)


GUT = {
    "sku": "X-1", "title": "Rückleuchte links", "brand": "Opel", "model": "Corsa D",
    "category": "Beleuchtung", "price_cents": 4500, "stock": 1,
}


def test_csv_mit_semikolon_und_deutschen_spalten():
    csv = ("Artikelnummer;Bezeichnung;Marke;Modell;Warengruppe;Preis;Bestand\n"
           "A-1;Rückleuchte links;Opel;Corsa D;Beleuchtung;45,00;2\n")
    zeilen = datei_lesen(csv.encode("utf-8"))
    assert len(zeilen) == 1
    teil = zeile_pruefen(zeilen[0], 1)
    assert teil["sku"] == "A-1"
    assert teil["price_cents"] == 4500, "45,00 Euro muessen 4500 Cent werden"
    assert teil["brand"] == "Opel"


def test_json_liste_und_objekt():
    assert len(datei_lesen(json.dumps([GUT]).encode())) == 1
    assert len(datei_lesen(json.dumps({"teile": [GUT]}).encode())) == 1


def test_byte_order_mark_stoert_nicht():
    csv = "﻿sku;title;brand;model;category;price_cents;stock\nB-1;Teil;VW;Golf V;Motor;100;1\n"
    zeilen = datei_lesen(csv.encode("utf-8"))
    assert zeile_pruefen(zeilen[0], 1)["sku"] == "B-1"


@pytest.mark.parametrize("aenderung,fehlertext", [
    ({"sku": ""}, "sku"),
    ({"price_cents": "keine Zahl"}, "Zahl"),
    ({"price_cents": -5}, "negativ"),
    ({"stock": -1}, "negativ"),
    ({"on_ebay": True, "ebay_url": ""}, "eBay"),
    ({"on_ebay": True, "ebay_url": "keine-adresse"}, "Adresse"),
    ({"year_from": 2010, "year_to": 2005}, "Baujahr"),
    ({"price_cents": 99_999_999}, "pruefen"),
])
def test_fehlerhafte_zeilen_werden_benannt(aenderung, fehlertext):
    with pytest.raises(ValueError) as exc:
        zeile_pruefen({**GUT, **aenderung}, 7)
    assert fehlertext.lower() in str(exc.value).lower().replace("ü", "ue").replace("ä", "ae").replace("ö", "oe")


@pytest.mark.parametrize("eingabe,erwartet", [
    ("VL", "links"), ("vorne links", "links"), ("R", "rechts"),
    ("right", "rechts"), ("hinten", "hinten"), ("quatsch", ""),
])
def test_lageangaben_werden_vereinheitlicht(eingabe, erwartet):
    assert zeile_pruefen({**GUT, "side": eingabe}, 1)["side"] == erwartet


def test_eine_kaputte_zeile_verwirft_nicht_die_ganze_lieferung(db, embedder):
    zeilen = [
        {**GUT, "sku": "OK-1"},
        {**GUT, "sku": "KAPUTT", "price_cents": "unsinn"},
        {**GUT, "sku": "OK-2"},
    ]
    e = Abgleich(db, embedder).ausfuehren(zeilen, vollabgleich=False)
    assert e.uebernommen == 2
    assert e.abgewiesen == 1
    assert e.fehler[0]["artikelnummer"] == "KAPUTT"
    assert e.fehler[0]["zeile"] == 2


def test_doppelte_nummer_wird_gemeldet(db, embedder):
    e = Abgleich(db, embedder).ausfuehren(
        [{**GUT, "sku": "DOPPEL"}, {**GUT, "sku": "DOPPEL"}], vollabgleich=False
    )
    assert e.uebernommen == 1 and e.abgewiesen == 1
    assert "mehrfach" in e.fehler[0]["problem"]


def test_unveraendertes_teil_wird_nicht_neu_eingebettet(db, embedder):
    ab = Abgleich(db, embedder)
    erst = ab.ausfuehren([{**GUT, "sku": "EINBETT-1"}], vollabgleich=False)
    assert erst.neu_eingebettet == 1
    zweit = ab.ausfuehren([{**GUT, "sku": "EINBETT-1"}], vollabgleich=False)
    assert zweit.neu_eingebettet == 0, "gleicher Text darf keine neue Einbettung kosten"
    dritt = ab.ausfuehren(
        [{**GUT, "sku": "EINBETT-1", "title": "Rückleuchte rechts"}], vollabgleich=False
    )
    assert dritt.neu_eingebettet == 1, "geaenderter Text braucht eine neue Einbettung"


def test_vollabgleich_deaktiviert_fehlende_teile(db, embedder):
    ab = Abgleich(db, embedder)
    ab.ausfuehren([{**GUT, "sku": "BLEIBT"}, {**GUT, "sku": "VERSCHWINDET"}], vollabgleich=True)
    e = ab.ausfuehren([{**GUT, "sku": "BLEIBT"}], vollabgleich=True)
    assert e.deaktiviert >= 1
    with db.conn() as c:
        row = c.execute("SELECT active, stock FROM parts WHERE sku='VERSCHWINDET'").fetchone()
    assert row["active"] is False and row["stock"] == 0
    # Nicht geloescht: Verkaufsdaten brauchen den Bezug.
    assert row is not None


def test_katalog_wird_nach_abgleich_neu_geladen(db, embedder, bestand):
    """Nach einem Abgleich muss der Fahrzeugkatalog veralten.

    Sonst bietet das Klick-Interview Marken an, zu denen seit dem
    naechtlichen Abgleich kein einziges Teil mehr im Lager liegt.
    """
    from app.search import TeileSuche

    suche = TeileSuche(db, embedder)
    suche.katalog.neu_laden()
    assert "Nio" not in suche.katalog._marken.values()

    Abgleich(db, embedder).ausfuehren(
        [{**GUT, "sku": "NEUMARKE-1", "brand": "Nio", "model": "ET5",
          "subcategory": "Rückleuchte"}],
        vollabgleich=False,
    )
    suche.katalog.verwerfen()
    erkennung = suche.katalog.erkennen("Rückleuchte Nio ET5")
    assert erkennung.marke == "Nio", "neue Marke muss sofort erkannt werden"
