"""Findet die Suche das richtige Teil - und schweigt sie, wenn nicht?"""
import pytest
from app.search import Filter


def bauteile(ergebnis):
    return [t.teil["subcategory"] for t in ergebnis.treffer]


def test_teilenummer_trifft_genau(suche):
    e = suche.suchen_ausfuehrlich("1K6945095")
    assert e.treffer, "Teilenummer muss treffen"
    assert e.treffer[0].teil["sku"] == "TT-PRUEF-01"
    assert e.treffer[0].quellen == ["teilenummer"]


def test_teilenummer_mit_und_ohne_bindestriche(suche):
    mit = suche.suchen_ausfuehrlich("1K6-945-095")
    ohne = suche.suchen_ausfuehrlich("1K6945095")
    assert mit.treffer[0].teil["sku"] == ohne.treffer[0].teil["sku"] == "TT-PRUEF-01"


def test_artikelnummer_des_shops_trifft(suche):
    e = suche.suchen_ausfuehrlich("TT-PRUEF-02")
    assert e.treffer and e.treffer[0].teil["sku"] == "TT-PRUEF-02"


@pytest.mark.parametrize("frage,bauteil", [
    ("Rückleuchte links Golf V", "Rückleuchte"),
    ("Ruecklicht links Golf V", "Rückleuchte"),
    ("das rote Glas hinten links Golf V", "Rückleuchte"),
    ("Scheinwerfer rechts Astra H", "Scheinwerfer"),
    ("Scheinwrfer rechts Astra H", "Scheinwerfer"),
])
def test_laiensprache_findet_das_richtige_bauteil(suche, frage, bauteil):
    e = suche.suchen_ausfuehrlich(frage)
    assert e.treffer, f"kein Treffer fuer {frage!r}"
    assert e.treffer[0].teil["subcategory"] == bauteil


def test_fahrzeug_und_bauteil_werden_erkannt(suche):
    e = suche.suchen_ausfuehrlich("Rückleuchte links fuer einen Volkswagen Golf V")
    assert e.erkennung.bauteil == "Rückleuchte"
    assert e.erkennung.marke == "Volkswagen"
    assert e.erkennung.modell == "Golf V"


def test_mehrdeutiges_modell_wird_nicht_geraten(suche):
    # "Astra" gibt es als G, H und J - da darf nicht geraten werden.
    e = suche.suchen_ausfuehrlich("Rückleuchte Opel Astra")
    assert e.erkennung.marke == "Opel"
    assert e.erkennung.modell is None


@pytest.mark.parametrize("unsinn", [
    "Pizza Salami mit extra Kaese",
    "Hundefutter 10 kg",
    "Flugticket nach Mallorca",
])
def test_unsinn_ergibt_lieber_nichts(suche, unsinn):
    assert not suche.suchen_ausfuehrlich(unsinn).treffer


def test_falsches_bauteil_wird_nie_geliefert(suche):
    # Der teuerste Fehler: Kunde sucht Licht, bekommt Bremse.
    e = suche.suchen_ausfuehrlich("Ruecklicht links Golf V")
    for t in e.treffer:
        assert t.teil["subcategory"] == "Rückleuchte"


def test_lockerung_wird_gemeldet(suche):
    # Fuer ein Modell ohne dieses Teil muss der Bot sagen, dass er
    # das Modell aufgegeben hat - sonst kauft jemand ein falsches Teil.
    e = suche.suchen_ausfuehrlich("Rückleuchte Volkswagen Golf V rechts")
    if e.treffer and e.verwendeter_filter.modell is None:
        assert "modell" in e.gelockert


def test_filter_aus_dem_interview_hat_vorrang(suche):
    f = Filter(marke="Opel", modell="Astra H", kategorie="Beleuchtung")
    e = suche.suchen_ausfuehrlich("Scheinwerfer", f)
    for t in e.treffer:
        assert t.teil["brand"] == "Opel"


def test_nur_verfuegbare_teile_zuerst(suche):
    e = suche.suchen_ausfuehrlich("Rückleuchte")
    bestaende = [t.teil["stock"] > 0 for t in e.treffer]
    assert bestaende == sorted(bestaende, reverse=True), "Lagerware muss oben stehen"


def test_sql_einschleusung_hat_keine_wirkung(suche, db):
    boese = [
        "Rückleuchte'; DROP TABLE parts; --",
        "' OR 1=1 --",
        "Golf\\'; DELETE FROM parts WHERE '1'='1",
        "'; UPDATE parts SET price_cents=0; --",
    ]
    for b in boese:
        suche.suchen_ausfuehrlich(b)
    with db.conn() as c:
        n = c.execute("SELECT count(*) AS n FROM parts").fetchone()["n"]
    assert n > 100, "Tabelle muss unveraendert sein"


def test_zwei_schreibweisen_desselben_bauteils(db, embedder, suche):
    """Lagerprogramme schreiben mal "Rueckleuchte", mal "Rückleuchte".

    Beide muessen gefunden werden - und die Schreibweise darf die
    Bauteilerkennung nicht aushebeln.
    """
    from app.sync import Abgleich

    Abgleich(db, embedder).ausfuehren([{
        "sku": "SCHREIB-1", "title": "Rueckleuchte rechts Ford Mondeo IV",
        "brand": "Ford", "model": "Mondeo IV", "category": "Beleuchtung",
        "subcategory": "Rueckleuchte", "side": "rechts",
        "price_cents": 7900, "stock": 1,
    }], vollabgleich=False)
    suche.katalog.neu_laden()

    e = suche.suchen_ausfuehrlich("Rückleuchte Ford Mondeo")
    assert e.erkennung.bauteil, "Bauteil muss trotz zweier Schreibweisen erkannt werden"
    assert e.treffer, "das anders geschriebene Teil muss gefunden werden"
    assert any(t.teil["sku"] == "SCHREIB-1" for t in e.treffer)

    with db.conn() as c:
        c.execute("DELETE FROM parts WHERE sku = 'SCHREIB-1'")
        c.commit()
