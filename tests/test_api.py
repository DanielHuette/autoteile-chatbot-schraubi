"""Die HTTP-Schnittstellen von außen: Chat, Interview, Versand, Betriebsleitung, Abgleich.

Kontext: Tests gegen die FastAPI-Anwendung. | Eingabe: TestClient, Prüfbestand. | Ergebnis:
Pytest-Befunde.
"""

import pytest
from app.db import Database
from fastapi.testclient import TestClient

from tests.conftest import TESTPASSWORT


def test_health(client: TestClient) -> None:
    d = client.get("/api/health").json()
    assert d["status"] == "bereit"
    assert d["teile_verfuegbar"] > 0
    assert d["ohne_vektor"] == 0, "jedes aktive Teil braucht einen Suchvektor"


def test_begruessung_legt_ki_offen(client: TestClient) -> None:
    # EU-KI-Verordnung Artikel 50: unaufgefordert offenlegen, dass eine Maschine antwortet.
    d = client.post("/api/chat", json={"nachricht": "", "sitzung": "p1"}).json()
    text = " ".join(d["blasen"]).lower()
    assert "computerprogramm" in text and "kein mensch" in text
    assert d["art"] == "begruessung"


def test_ki_hinweis_vollstaendig(client: TestClient) -> None:
    d = client.get("/api/ki-hinweis").json()
    assert d["ist_ki"] is True
    for feld in (
        "zweck",
        "funktionsweise",
        "daten",
        "grenzen",
        "keine_automatisierte_entscheidung",
    ):
        assert d[feld].strip()


def test_teilesuche_ueber_chat(client: TestClient) -> None:
    d = client.post(
        "/api/chat", json={"nachricht": "Ruecklicht links Golf V", "sitzung": "p2"}
    ).json()
    assert d["art"] == "treffer"
    assert d["teile"] and d["teile"][0]["subcategory"] == "Rückleuchte"
    assert "preis_euro" in d["teile"][0]


def test_ebay_teil_bekommt_link(client: TestClient) -> None:
    d = client.post(
        "/api/chat", json={"nachricht": "Scheinwerfer rechts Astra H", "sitzung": "p3"}
    ).json()
    ebay = [t for t in d["teile"] if t["on_ebay"]]
    assert ebay, "das Pruefteil liegt auf eBay"
    assert ebay[0]["ebay_url"].startswith("https://www.ebay.de/")
    assert "ebay" in " ".join(d["blasen"]).lower()


def test_versandauskunft_nennt_datum(client: TestClient) -> None:
    d = client.post(
        "/api/chat",
        json={"nachricht": "Wie lange dauert der Versand nach Oesterreich?", "sitzung": "p4"},
    ).json()
    assert d["art"] == "versand"
    assert "Oesterreich" in d["blasen"][0]
    assert d["tabelle"][0]["frueheste_ankunft"]


def test_klick_interview_von_vorn(client: TestClient) -> None:
    d = client.post("/api/interview", json={"stand": {}, "sitzung": "p5"}).json()
    assert d["art"] == "interview"
    assert d["interview"]["schritt"] == "marke"
    assert len(d["knoepfe"]) > 3
    assert d["hinweis"], "jeder Schritt braucht eine Hilfestellung"


def test_klick_interview_schreitet_voran(client: TestClient) -> None:
    marke = client.post("/api/interview", json={"stand": {}}).json()
    erste = marke["knoepfe"][0]["aktion"].split(":", 2)[2]
    zweite = client.post("/api/interview", json={"stand": {"marke": erste}}).json()
    assert zweite["interview"]["schritt"] == "modell"
    assert zweite["interview"]["fortschritt"] == 2


def test_interview_nimmt_nur_bekannte_felder(client: TestClient) -> None:
    d = client.post(
        "/api/interview", json={"stand": {"marke": "Opel", "boese": "'; DROP TABLE parts; --"}}
    ).json()
    assert d["art"] == "interview"
    assert "boese" not in (d["interview"]["stand"] or {})


def test_kunde_bekommt_keine_umsatzzahlen(client: TestClient) -> None:
    d = client.post(
        "/api/chat", json={"nachricht": "Wie hoch war der Umsatz?", "sitzung": "p6"}
    ).json()
    assert d["art"] == "blockiert"
    assert not d["teile"] and not d["tabelle"]


def test_zu_lange_nachricht_wird_gekuerzt_nicht_abgelehnt(client: TestClient) -> None:
    antwort = client.post("/api/chat", json={"nachricht": "Rückleuchte " * 300, "sitzung": "p7"})
    assert antwort.status_code == 200


def test_ohne_anmeldung_keine_betriebsdaten(client: TestClient) -> None:
    assert client.post("/api/admin/frage", json={"frage": "Umsatz"}).status_code == 401
    assert client.get("/api/admin/betriebslage").status_code == 401


def test_falsches_token_wird_abgewiesen(client: TestClient) -> None:
    antwort = client.post(
        "/api/admin/frage", json={"frage": "Umsatz"}, headers={"X-Admin-Token": "erfunden.erfunden"}
    )
    assert antwort.status_code == 401


def test_anmeldung_und_umsatzauskunft(client: TestClient, admin_token: str) -> None:
    d = client.post(
        "/api/admin/frage",
        json={"frage": "Wie hoch war der Umsatz letzten Monat?"},
        headers={"X-Admin-Token": admin_token},
    ).json()
    assert d["absicht"] == "umsatz"
    assert "Umsatz" in d["text"]
    assert d["tabelle"]


def test_betreiber_fragt_im_chat_nach_zahlen(client: TestClient, admin_token: str) -> None:
    d = client.post(
        "/api/chat",
        json={"nachricht": "Umsatz heute", "sitzung": "p8"},
        headers={"X-Admin-Token": admin_token},
    ).json()
    assert d["art"] == "betreiber"
    assert "nur für Sie sichtbar" in d["hinweis"]


def test_abmelden_macht_token_ungueltig(client: TestClient) -> None:
    token = client.post("/api/admin/login", json={"passwort": TESTPASSWORT}).json()["token"]
    assert client.post("/api/admin/logout", headers={"X-Admin-Token": token}).status_code == 200
    assert (
        client.post(
            "/api/admin/frage", json={"frage": "Umsatz"}, headers={"X-Admin-Token": token}
        ).status_code
        == 401
    )


def test_betriebslage_zeigt_alles_wichtige(client: TestClient, admin_token: str) -> None:
    d = client.get("/api/admin/betriebslage", headers={"X-Admin-Token": admin_token}).json()
    assert d["bestand"]["teile_verfuegbar"] > 0
    assert "nachfrageluecken" in d and "betrieb" in d


def test_abgleich_ohne_schluessel_abgewiesen(client: TestClient) -> None:
    assert client.post("/api/sync", content=b"[]").status_code == 401


def test_abgleich_mit_falschem_schluessel(client: TestClient) -> None:
    assert (
        client.post("/api/sync", content=b"[]", headers={"X-Sync-Key": "falsch"}).status_code == 401
    )


def test_abgleich_nimmt_csv_an(client: TestClient) -> None:
    import os

    csv = (
        "Artikelnummer;Bezeichnung;Marke;Modell;Warengruppe;Bauteil;Preis;Bestand\n"
        "API-1;Rückleuchte rechts;Ford;Focus II;Beleuchtung;Rueckleuchte;59,90;1\n"
    )
    d = client.post(
        "/api/sync",
        content=csv.encode("utf-8"),
        headers={"X-Sync-Key": os.environ["SYNC_API_KEY"], "Content-Type": "text/csv"},
    ).json()
    assert d["uebernommen"] == 1 and d["abgewiesen"] == 0


def test_abgleich_meldet_kaputte_zeilen_zurueck(client: TestClient) -> None:
    import os

    csv = (
        "sku;title;brand;model;category;price_cents;stock\n"
        "API-2;Teil;VW;Golf V;Motor;100;1\n"
        "API-3;Teil;VW;Golf V;Motor;keinepreis;1\n"
    )
    d = client.post(
        "/api/sync", content=csv.encode("utf-8"), headers={"X-Sync-Key": os.environ["SYNC_API_KEY"]}
    ).json()
    assert d["uebernommen"] == 1 and d["abgewiesen"] == 1
    assert d["fehler"][0]["zeile"] == 2


def test_schutzkopfzeilen_gesetzt(client: TestClient) -> None:
    k = client.get("/api/health").headers
    assert k["x-content-type-options"] == "nosniff"
    assert k["x-frame-options"] == "DENY"
    assert k["cache-control"] == "no-store"


@pytest.mark.parametrize("jahr", ["abc", "²", "99999999999", "2005-2008", 2005.5])
def test_interview_mit_ungueltigem_baujahr_fragt_erneut(client: TestClient, jahr: object) -> None:
    stand = {"marke": "Volkswagen", "modell": "Golf V", "jahr": jahr}
    antwort = client.post("/api/interview", json={"stand": stand})
    assert antwort.status_code == 200
    assert antwort.json()["interview"]["schritt"] == "baujahr"


def test_widget_wird_zwischengespeichert(client: TestClient) -> None:
    antwort = client.get("/widget.js")
    assert antwort.status_code == 200
    assert antwort.headers["cache-control"] == "public, max-age=3600"
    assert antwort.headers["x-content-type-options"] == "nosniff"


def test_teilenummer_knopf_gibt_hinweis_statt_fehlanzeige(client: TestClient, db: Database) -> None:
    d = client.post(
        "/api/chat", json={"nachricht": "Ich habe eine Teilenummer", "sitzung": "p9"}
    ).json()
    assert d["absicht"] == "nummer_hinweis"
    assert "mit einer Nummer finde ich das Teil sofort" in d["blasen"][0]
    with db.conn() as c:
        luecken = c.execute(
            "SELECT count(*) AS n FROM chat_events WHERE detail = 'Ich habe eine Teilenummer'"
        ).fetchone()
    assert luecken["n"] == 0, "der Knopftext ist keine Nachfrage fuer den Einkauf"


def test_nummer_im_text_wird_weiter_gesucht(client: TestClient) -> None:
    d = client.post(
        "/api/chat", json={"nachricht": "Teilenummer 1K6945095", "sitzung": "p10"}
    ).json()
    assert d["art"] == "treffer"
    assert d["teile"][0]["sku"] == "TT-PRUEF-01"
