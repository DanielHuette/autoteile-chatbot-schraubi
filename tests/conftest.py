"""Gemeinsame Fixtures: Testumgebung, Datenbank, Prüfbestand, HTTP-Client, Betreibersitzung.

Kontext: Getestet wird gegen eine echte PostgreSQL-Datenbank mit pgvector, weil sich
Vektorabstand, Volltext, Trigramm und Rechtetrennung nicht nachbilden lassen. | Eingabe:
TEST_DATABASE_URL, sonst DATABASE_URL. | Ergebnis: Fixtures für alle Testmodule.
"""

from __future__ import annotations

import os
import pathlib
import sys
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

import pytest
from fastapi.testclient import TestClient

WURZEL = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "backend"))
sys.path.insert(0, str(WURZEL / "bench"))

if TYPE_CHECKING:
    from app.db import Database
    from app.embeddings import EmbeddingProvider
    from app.search import TeileSuche

TESTPASSWORT = "PruefPasswort2026!"


def _umgebung_setzen() -> None:
    os.environ.setdefault(
        "DATABASE_URL",
        os.environ.get("TEST_DATABASE_URL", "postgresql://postgres@127.0.0.1:5433/teilethuns_test"),
    )
    os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", os.environ["DATABASE_URL"])
    # Tests prüfen die Mechanik; die Trefferqualität misst bench/qualitaet.py mit echtem Modell.
    os.environ["EMBEDDING_PROVIDER"] = "hashing"
    os.environ["EMBEDDING_DIM"] = "384"
    os.environ["ALLOWED_ORIGINS"] = "https://test.example"
    os.environ["SHOP_NAME"] = "Teile Thuns"
    os.environ["OPERATOR_EMAIL"] = "info@example.test"
    os.environ["OPERATOR_PHONE"] = "0251 000000"
    os.environ["SYNC_API_KEY"] = "pruefschluessel-fuer-die-tests-0001"
    os.environ["SESSION_SECRET"] = "pruefgeheimnis-mindestens-32-zeichen-lang-0001"
    os.environ["APPLY_SCHEMA"] = "0"
    from app.auth import hash_erzeugen

    os.environ["ADMIN_PASSWORD_HASH"] = hash_erzeugen(TESTPASSWORT)


_umgebung_setzen()


@pytest.fixture(scope="session")
def db() -> Iterator[Database]:
    from app.config import load_settings
    from app.db import Database

    s = load_settings()
    datenbank = Database(s.database_url, s.embedding_dim)
    datenbank.apply_schema()
    with datenbank.conn() as c:
        c.execute((WURZEL / "backend" / "grunddaten.sql").read_text(encoding="utf-8"))
        c.execute(
            "TRUNCATE parts, sales, chat_events, sync_runs, admin_login_attempts RESTART IDENTITY"
        )
        c.commit()
    yield datenbank
    datenbank.close()


@pytest.fixture(scope="session")
def embedder() -> EmbeddingProvider:
    from app.embeddings import build_provider

    return build_provider("hashing", "", 384)


@pytest.fixture(scope="session")
def bestand(db: Database, embedder: EmbeddingProvider) -> list[dict[str, Any]]:
    """Ein kleiner, fester Bestand - gleiche Daten bei jedem Lauf."""
    from app.sync import Abgleich
    from testdaten import erzeugen, verkaeufe_erzeugen

    teile = erzeugen(300, seed=99)
    teile.append(
        {
            "sku": "TT-PRUEF-01",
            "title": "Rückleuchte links Volkswagen Golf V",
            "description": "Prüfteil mit festen Werten.",
            "brand": "Volkswagen",
            "model": "Golf V",
            "year_from": 2003,
            "year_to": 2008,
            "category": "Beleuchtung",
            "subcategory": "Rückleuchte",
            "side": "links",
            "condition": "gebraucht, geprüft",
            "price_cents": 8900,
            "stock": 2,
            "weight_grams": 1200,
            "oem_numbers": ["1K6945095", "1K6-945-095"],
            "on_ebay": False,
            "ebay_url": "",
            "active": True,
        }
    )
    teile.append(
        {
            "sku": "TT-PRUEF-02",
            "title": "Scheinwerfer rechts Opel Astra H",
            "description": "Prüfteil, wird über eBay verkauft.",
            "brand": "Opel",
            "model": "Astra H",
            "year_from": 2004,
            "year_to": 2010,
            "category": "Beleuchtung",
            "subcategory": "Scheinwerfer",
            "side": "rechts",
            "condition": "gebraucht, sehr gut",
            "price_cents": 14900,
            "stock": 1,
            "weight_grams": 3500,
            "oem_numbers": ["93179289"],
            "on_ebay": True,
            "ebay_url": "https://www.ebay.de/itm/123456789012",
            "active": True,
        }
    )
    ergebnis = Abgleich(db, embedder).ausfuehren(teile, vollabgleich=True)
    assert ergebnis.abgewiesen == 0, ergebnis.fehler[:3]

    zeilen = verkaeufe_erzeugen(teile, 400, seed=5)
    with db.conn() as c:
        with c.cursor() as cur:
            cur.executemany(
                """INSERT INTO sales (order_ref, part_sku, sold_at, quantity,
                                      revenue_cents, channel)
                   VALUES (%(order_ref)s,%(part_sku)s,%(sold_at)s,%(quantity)s,
                           %(revenue_cents)s,%(channel)s)""",
                zeilen,
            )
        c.commit()
    return teile


@pytest.fixture
def suche(db: Database, embedder: EmbeddingProvider, bestand: list[dict[str, Any]]) -> TeileSuche:
    """Je Test frisch: andere Tests veraendern den Bestand, und der
    Katalog wird aus dem Bestand abgeleitet."""
    from app.search import TeileSuche

    s = TeileSuche(db, embedder)
    s.katalog.neu_laden()
    return s


@pytest.fixture(scope="session")
def client(db: Database, bestand: list[dict[str, Any]]) -> Iterator[TestClient]:
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin_token(client: TestClient) -> str:
    antwort = client.post("/api/admin/login", json={"passwort": TESTPASSWORT})
    assert antwort.status_code == 200, antwort.text
    return antwort.json()["token"]
