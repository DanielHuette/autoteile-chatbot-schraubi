"""Sicherheit: Rechtetrennung, Mengenbremse, Fehlversuche, Protokolle."""
import os

import pytest

from tests.conftest import TESTPASSWORT


def test_chatrolle_darf_verkaufsdaten_nicht_lesen(db, bestand):
    """Zweite Schutzschicht: selbst bei einem Programmfehler kaeme der
    Chat nicht an die Tabelle 'sales' - die Datenbank verbietet es."""
    with db.conn() as c:
        rechte = c.execute(
            "SELECT has_table_privilege('teilethuns_chat','sales','SELECT') AS darf"
        ).fetchone()
    assert rechte["darf"] is False


def test_chatrolle_darf_teile_lesen(db, bestand):
    with db.conn() as c:
        rechte = c.execute(
            "SELECT has_table_privilege('teilethuns_chat','parts','SELECT') AS darf"
        ).fetchone()
    assert rechte["darf"] is True


def test_chatrolle_darf_teile_nicht_aendern(db, bestand):
    with db.conn() as c:
        for recht in ("INSERT", "UPDATE", "DELETE"):
            r = c.execute(
                "SELECT has_table_privilege('teilethuns_chat','parts',%s) AS darf", (recht,)
            ).fetchone()
            assert r["darf"] is False, f"Chat darf nicht {recht} auf parts"


def test_protokoll_enthaelt_keine_klartextkennung(client, db):
    client.post("/api/chat", json={"nachricht": "Rueckleuchte", "sitzung": "mein-klartext-name"})
    with db.conn() as c:
        zeilen = c.execute(
            "SELECT session_hash FROM chat_events ORDER BY id DESC LIMIT 5"
        ).fetchall()
    for z in zeilen:
        assert "mein-klartext-name" not in z["session_hash"]
        assert len(z["session_hash"]) == 16


def test_passwort_erscheint_nicht_im_protokoll(client, db):
    client.post("/api/admin/login", json={"passwort": TESTPASSWORT})
    with db.conn() as c:
        zeilen = c.execute("SELECT detail, intent FROM chat_events").fetchall()
    for z in zeilen:
        assert TESTPASSWORT not in (z["detail"] or "")
        assert TESTPASSWORT not in (z["intent"] or "")


def test_fehlversuche_sperren_den_zugang(client):
    from app.auth import Fehlversuchsbremse
    from app.main import Z

    bremse = Z.bremse_login
    key = Fehlversuchsbremse.client_key("pruef-sperre")
    with Z.db.conn() as c:
        c.execute("DELETE FROM admin_login_attempts WHERE client_key=%s", (key,))
        c.commit()
    assert bremse.gesperrt_bis(key) == 0
    for _ in range(bremse.max_versuche):
        bremse.vermerken(key, False)
    assert bremse.gesperrt_bis(key) > 0, "nach zu vielen Fehlversuchen muss gesperrt werden"
    bremse.vermerken(key, True)
    assert bremse.gesperrt_bis(key) == 0, "erfolgreiche Anmeldung raeumt die Sperre"


def test_mengenbremse_greift():
    from app.main import Mengenbremse

    b = Mengenbremse(3)
    assert all(b.erlaubt("x") for _ in range(3))
    assert not b.erlaubt("x")
    assert b.erlaubt("y"), "andere Besucher duerfen weiter"


def test_keine_oeffentliche_schnittstellenbeschreibung(client):
    # Eine offene Schnittstellenbeschreibung erleichtert Angriffe und
    # bringt dem Shopbetreiber nichts.
    for pfad in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(pfad).status_code == 404


def test_fehler_zeigt_keine_internen_angaben(client, monkeypatch):
    from app.main import Z

    def kaputt(*a, **k):
        raise RuntimeError("geheimer interner Pfad /var/secret/db.conf")

    monkeypatch.setattr(Z.gespraech, "antworten", kaputt)
    antwort = client.post("/api/chat", json={"nachricht": "Rueckleuchte", "sitzung": "f1"})
    assert antwort.status_code == 500
    assert "geheimer interner Pfad" not in antwort.text
    assert "schiefgelaufen" in antwort.text


def test_vorfall_wird_protokolliert(client, monkeypatch, tmp_path):
    # Settings sind unveraenderlich (eingefroren) - deshalb wird ein
    # Ersatzobjekt gesetzt statt ein Feld geaendert.
    import dataclasses
    import json

    from app.main import Z

    pfad = tmp_path / "vorfaelle.jsonl"
    monkeypatch.setattr(
        Z, "settings", dataclasses.replace(Z.settings, incident_log_path=str(pfad))
    )

    def kaputt(*a, **k):
        raise RuntimeError("Testfehler")

    monkeypatch.setattr(Z.gespraech, "antworten", kaputt)
    client.post("/api/chat", json={"nachricht": "Rueckleuchte", "sitzung": "f2"})
    assert pfad.exists(), "Fehler muss protokolliert werden (EU-KI-Verordnung Art. 12)"
    eintrag = json.loads(pfad.read_text(encoding="utf-8").splitlines()[0])
    assert eintrag["art"] in ("chat_fehler", "unbehandelter_fehler")
    assert "zeit" in eintrag
