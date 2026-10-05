"""Datenbankzugriff. Verbindungspool, Schemaaufbau, Hilfsabfragen.

Alle Abfragen sind parametrisiert. Es wird nie Text in SQL eingesetzt,
damit keine SQL-Einschleusung möglich ist.
"""
from __future__ import annotations

import logging
import pathlib
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

log = logging.getLogger("teilethuns.db")

SCHEMA_PATH = pathlib.Path(__file__).resolve().parent.parent / "schema.sql"


class Database:
    def __init__(self, dsn: str, embedding_dim: int, min_size: int = 1, max_size: int = 8) -> None:
        self.embedding_dim = embedding_dim
        self._pool = ConnectionPool(
            dsn,
            min_size=min_size,
            max_size=max_size,
            kwargs={"row_factory": dict_row},
            open=True,
            timeout=15.0,
        )

    def close(self) -> None:
        self._pool.close()

    @contextmanager
    def conn(self) -> Iterator[psycopg.Connection]:
        with self._pool.connection() as c:
            from pgvector.psycopg import register_vector

            # Beim allerersten Start existiert der Datentyp noch nicht -
            # er wird ja gerade erst vom Schema angelegt. Dann wird ohne
            # Typanmeldung weitergearbeitet; ab dem nächsten Aufruf
            # greift sie.
            try:
                register_vector(c)
            except psycopg.ProgrammingError:
                log.debug("vector-Typ noch nicht vorhanden - Schema wird gleich angelegt")
            yield c

    # -- Schema -------------------------------------------------------
    def apply_schema(self) -> None:
        sql = SCHEMA_PATH.read_text(encoding="utf-8").replace(
            "{EMBEDDING_DIM}", str(self.embedding_dim)
        )
        with self.conn() as c:
            # Erweiterungen zuerst, in eigener Transaktion: erst danach
            # kennt die Verbindung den Datentyp vector.
            c.execute("CREATE EXTENSION IF NOT EXISTS vector")
            c.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
            c.commit()
        with self.conn() as c:
            c.execute(sql)
            c.commit()
        log.info("Schema angewendet (Dimension %s)", self.embedding_dim)

    def healthcheck(self) -> dict[str, Any]:
        with self.conn() as c:
            row = c.execute(
                """
                SELECT
                  (SELECT count(*) FROM parts WHERE active AND stock > 0) AS teile_verfuegbar,
                  (SELECT count(*) FROM parts WHERE active AND on_ebay)   AS teile_auf_ebay,
                  (SELECT max(updated_at) FROM parts)                     AS letzte_aenderung,
                  (SELECT extversion FROM pg_extension WHERE extname='vector') AS pgvector,
                  (SELECT count(*) FROM parts WHERE embedding IS NULL AND active) AS ohne_vektor
                """
            ).fetchone()
        return dict(row or {})

    # -- Fahrzeugkatalog für das Klick-Interview ---------------------
    # Wird direkt aus dem Lagerbestand abgeleitet. Dadurch gibt es im
    # Interview nie eine Auswahl, zu der es kein Teil gibt.
    def marken(self) -> list[dict[str, Any]]:
        with self.conn() as c:
            return [
                dict(r)
                for r in c.execute(
                    """
                    SELECT brand AS wert, count(*) AS anzahl
                      FROM parts WHERE active AND stock > 0
                     GROUP BY brand ORDER BY brand
                    """
                ).fetchall()
            ]

    def modelle(self, marke: str) -> list[dict[str, Any]]:
        with self.conn() as c:
            return [
                dict(r)
                for r in c.execute(
                    """
                    SELECT model AS wert, count(*) AS anzahl
                      FROM parts WHERE active AND stock > 0 AND brand = %s
                     GROUP BY model ORDER BY model
                    """,
                    (marke,),
                ).fetchall()
            ]

    def baujahre(self, marke: str, modell: str) -> list[dict[str, Any]]:
        """Baujahre in Fuenferschritten, damit die Auswahl kurz bleibt."""
        with self.conn() as c:
            rows = c.execute(
                """
                SELECT min(year_from) AS von, max(year_to) AS bis
                  FROM parts
                 WHERE active AND stock > 0 AND brand = %s AND model = %s
                   AND year_from IS NOT NULL AND year_to IS NOT NULL
                """,
                (marke, modell),
            ).fetchone()
        if not rows or rows["von"] is None:
            return []
        von, bis = int(rows["von"]), int(rows["bis"])
        spannen: list[dict[str, Any]] = []
        start = von - (von % 5)
        while start <= bis:
            ende = min(start + 4, bis)
            spannen.append({"wert": f"{max(start, von)}-{ende}", "von": max(start, von), "bis": ende})
            start += 5
        return spannen

    def kategorien(self, marke: str, modell: str, jahr: int | None = None) -> list[dict[str, Any]]:
        with self.conn() as c:
            return [
                dict(r)
                for r in c.execute(
                    """
                    SELECT category AS wert, count(*) AS anzahl
                      FROM parts
                     WHERE active AND stock > 0 AND brand = %s AND model = %s
                       AND (%s::int IS NULL OR (year_from <= %s AND year_to >= %s))
                     GROUP BY category ORDER BY category
                    """,
                    (marke, modell, jahr, jahr, jahr),
                ).fetchall()
            ]

    def bauteile(
        self, marke: str, modell: str, kategorie: str, jahr: int | None = None
    ) -> list[dict[str, Any]]:
        with self.conn() as c:
            return [
                dict(r)
                for r in c.execute(
                    """
                    SELECT subcategory AS wert, count(*) AS anzahl
                      FROM parts
                     WHERE active AND stock > 0 AND brand = %s AND model = %s
                       AND category = %s
                       AND (%s::int IS NULL OR (year_from <= %s AND year_to >= %s))
                     GROUP BY subcategory ORDER BY subcategory
                    """,
                    (marke, modell, kategorie, jahr, jahr, jahr),
                ).fetchall()
            ]

    # -- Protokollierung ---------------------------------------------
    def log_event(
        self,
        session_hash: str,
        kind: str,
        intent: str = "",
        detail: str = "",
        latency_ms: int | None = None,
    ) -> None:
        try:
            with self.conn() as c:
                c.execute(
                    """INSERT INTO chat_events (session_hash, kind, intent, detail, latency_ms)
                       VALUES (%s,%s,%s,%s,%s)""",
                    (session_hash[:16], kind, intent[:60], detail[:500], latency_ms),
                )
                c.commit()
        except Exception:  # Protokollieren darf den Chat niemals abbrechen
            log.exception("Protokolleintrag fehlgeschlagen")
