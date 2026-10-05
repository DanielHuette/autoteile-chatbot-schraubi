"""Die Schnittstellen von aussen: Chat, Interview, Versand, Abgleich."""
import pytest

from tests.conftest import TESTPASSWORT


def test_health(client):
    d = client.get("/api/health").json()
    assert d["status"] == "bereit"
    assert d["teile_verfuegbar"] > 0
    assert d["ohne_vektor"] == 0, "jedes aktive Teil braucht einen Suchvektor"


def test_begruessung_legt_ki_offen(client):
    # EU-KI-Verordnung Artikel 50: der Mensch muss wissen, dass er mit
    # einer Maschine spricht - und zwar unaufgefordert.
    d = client.post("/api/chat", json={"nachricht": "", "sitzung": "p1"}).json()
    text = " ".join(d["blasen"]).lower()
    assert "computerprogramm" in text and "kein mensch" in text
    assert d["art"] == "begruessung"


def test_ki_hinweis_vollstaendig(client):
    d = client.get("/api/ki-hinweis").json()
    assert d["ist_ki"] is True
    for feld in ("zweck", "funktionsweise", "daten", "grenzen",
                 "keine_automatisierte_entscheidung"):
        assert d[feld].strip()


def test_teilesuche_ueber_chat(client):
    d = client.post("/api/chat",
                    json={"nachricht": "Ruecklicht links Golf V", "sitzung": "p2"}).json()
    assert d["art"] == "treffer"
    assert d["teile"] and d["teile"][0]["subcategory"] == "Rückleuchte"
    assert "preis_euro" in d["teile"][0]


def test_ebay_teil_bekommt_link(client):
    d = client.post("/api/chat",
                    json={"nachricht": "Scheinwerfer rechts Astra H", "sitzung": "p3"}).json()
    ebay = [t for t in d["teile"] if t["on_ebay"]]
    assert ebay, "das Pruefteil liegt auf eBay"
    assert ebay[0]["ebay_url"].startswith("https://www.ebay.de/")
    assert "ebay" in " ".join(d["blasen"]).lower()


def test_versandauskunft_nennt_datum(client):
    d = client.post("/api/chat",
                    json={"nachricht": "Wie lange dauert der Versand nach Oesterreich?",
                          "sitzung": "p4"}).json()
    assert d["art"] == "versand"
    assert "Oesterreich" in d["blasen"][0]
    assert d["tabelle"][0]["frueheste_ankunft"]


def test_klick_interview_von_vorn(client):
    d = client.post("/api/interview", json={"stand": {}, "sitzung": "p5"}).json()
    assert d["art"] == "interview"
    assert d["interview"]["schritt"] == "marke"
    assert len(d["knoepfe"]) > 3
    assert d["hinweis"], "jeder Schritt braucht eine Hilfestellung"


def test_klick_interview_schreitet_voran(client):
    marke = client.post("/api/interview", json={"stand": {}}).json()
    erste = marke["knoepfe"][0]["aktion"].split(":", 2)[2]
    zweite = client.post("/api/interview", json={"stand": {"marke": erste}}).json()
    assert zweite["interview"]["schritt"] == "modell"
    assert zweite["interview"]["fortschritt"] == 2


def test_interview_nimmt_nur_bekannte_felder(client):
    # Ein erfundenes Feld darf nicht in die Abfrage geraten.
    d = client.post("/api/interview",
                    json={"stand": {"marke": "Opel", "boese": "'; DROP TABLE parts; --"}}).json()
    assert d["art"] == "interview"
    assert "boese" not in (d["interview"]["stand"] or {})


def test_kunde_bekommt_keine_umsatzzahlen(client):
    d = client.post("/api/chat",
                    json={"nachricht": "Wie hoch war der Umsatz?", "sitzung": "p6"}).json()
    assert d["art"] == "blockiert"
    assert not d["teile"] and not d["tabelle"]


def test_zu_lange_nachricht_wird_gekuerzt_nicht_abgelehnt(client):
    antwort = client.post("/api/chat", json={"nachricht": "Rückleuchte " * 300, "sitzung": "p7"})
    assert antwort.status_code == 200


# -- Betriebsleitung ---------------------------------------------------
def test_ohne_anmeldung_keine_betriebsdaten(client):
    assert client.post("/api/admin/frage", json={"frage": "Umsatz"}).status_code == 401
    assert client.get("/api/admin/betriebslage").status_code == 401


def test_falsches_token_wird_abgewiesen(client):
    antwort = client.post("/api/admin/frage", json={"frage": "Umsatz"},
                          headers={"X-Admin-Token": "erfunden.erfunden"})
    assert antwort.status_code == 401


def test_anmeldung_und_umsatzauskunft(client, admin_token):
    d = client.post("/api/admin/frage", json={"frage": "Wie hoch war der Umsatz letzten Monat?"},
                    headers={"X-Admin-Token": admin_token}).json()
    assert d["absicht"] == "umsatz"
    assert "Umsatz" in d["text"]
    assert d["tabelle"]


def test_betreiber_fragt_im_chat_nach_zahlen(client, admin_token):
    d = client.post("/api/chat", json={"nachricht": "Umsatz heute", "sitzung": "p8"},
                    headers={"X-Admin-Token": admin_token}).json()
    assert d["art"] == "betreiber"
    assert "nur für Sie sichtbar" in d["hinweis"]


def test_abmelden_macht_token_ungueltig(client):
    token = client.post("/api/admin/login", json={"passwort": TESTPASSWORT}).json()["token"]
    assert client.post("/api/admin/logout", headers={"X-Admin-Token": token}).status_code == 200
    assert client.post("/api/admin/frage", json={"frage": "Umsatz"},
                       headers={"X-Admin-Token": token}).status_code == 401


def test_betriebslage_zeigt_alles_wichtige(client, admin_token):
    d = client.get("/api/admin/betriebslage", headers={"X-Admin-Token": admin_token}).json()
    assert d["bestand"]["teile_verfuegbar"] > 0
    assert "nachfrageluecken" in d and "betrieb" in d


# -- Abgleich ----------------------------------------------------------
def test_abgleich_ohne_schluessel_abgewiesen(client):
    assert client.post("/api/sync", content=b"[]").status_code == 401


def test_abgleich_mit_falschem_schluessel(client):
    assert client.post("/api/sync", content=b"[]",
                       headers={"X-Sync-Key": "falsch"}).status_code == 401


def test_abgleich_nimmt_csv_an(client):
    import os
    csv = ("Artikelnummer;Bezeichnung;Marke;Modell;Warengruppe;Bauteil;Preis;Bestand\n"
           "API-1;Rückleuchte rechts;Ford;Focus II;Beleuchtung;Rueckleuchte;59,90;1\n")
    d = client.post("/api/sync", content=csv.encode("utf-8"),
                    headers={"X-Sync-Key": os.environ["SYNC_API_KEY"],
                             "Content-Type": "text/csv"}).json()
    assert d["uebernommen"] == 1 and d["abgewiesen"] == 0


def test_abgleich_meldet_kaputte_zeilen_zurueck(client):
    import os
    csv = ("sku;title;brand;model;category;price_cents;stock\n"
           "API-2;Teil;VW;Golf V;Motor;100;1\n"
           "API-3;Teil;VW;Golf V;Motor;keinepreis;1\n")
    d = client.post("/api/sync", content=csv.encode("utf-8"),
                    headers={"X-Sync-Key": os.environ["SYNC_API_KEY"]}).json()
    assert d["uebernommen"] == 1 and d["abgewiesen"] == 1
    assert d["fehler"][0]["zeile"] == 2


def test_schutzkopfzeilen_gesetzt(client):
    k = client.get("/api/health").headers
    assert k["x-content-type-options"] == "nosniff"
    assert k["x-frame-options"] == "DENY"
    assert k["cache-control"] == "no-store"
