#!/usr/bin/env python3
"""Messreihe 2: Was bringt der HNSW-Index gegenüber dem sequenziellen Durchlauf?

Kontext: Gemessen wird die Zeit je Suchanfrage und die Übereinstimmung mit der exakten Suche
(Recall@k), denn schnell und falsch ist wertlos. Aufruf:
`python scripts/mitenv.py .env.bench bench/latenz.py --groessen 1000,10000`. | Eingabe:
Datenbank mit eingebettetem Bestand, Bestandsgrößen. | Ergebnis: bench/results/latenz.json.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import statistics
import sys
import time
from collections.abc import Callable
from typing import Any

WURZEL = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "backend"))
sys.path.insert(0, str(WURZEL / "bench"))

from app.config import load_settings
from app.db import Database
from app.embeddings import build_provider

# Bewusst minimal: gemessen wird der Vektorvergleich, nicht das Zusammensuchen von Spalten.
ABFRAGE = "SELECT id FROM messmenge ORDER BY embedding <=> %s::vector LIMIT %s"

SUCHTEXTE = [
    "Rueckleuchte links Volkswagen Golf",
    "Scheinwerfer rechts Opel Astra",
    "das rote Glas hinten rechts",
    "Lichtmaschine BMW 3er",
    "Schalldaempfer durchgerostet",
    "Stossdaempfer hinten Audi A4",
    "Aussenspiegel links Ford Focus",
    "Kombiinstrument Mercedes C-Klasse",
    "Turbolader Skoda Octavia",
    "Bremsscheibe vorne Seat Leon",
    "Kuehlmittelpumpe undicht",
    "Antriebswelle rechts Renault",
    "Heckklappe Toyota Corolla",
    "Fensterhebermotor vorne links",
    "Klimakompressor Peugeot",
    "Zylinderkopf Fiat Punto",
]


def zeitmessung(fn: Callable[[], object], wiederholungen: int) -> dict[str, float]:
    # Warmlaufen: sonst misst der erste Durchlauf Plan-Cache und Plattenzugriff mit.
    for _ in range(3):
        fn()
    zeiten = []
    for _ in range(wiederholungen):
        t0 = time.perf_counter()
        fn()
        zeiten.append((time.perf_counter() - t0) * 1000)
    zeiten.sort()
    return {
        "median_ms": round(statistics.median(zeiten), 2),
        "mittel_ms": round(statistics.fmean(zeiten), 2),
        "p95_ms": round(zeiten[int(len(zeiten) * 0.95)], 2),
        "min_ms": round(zeiten[0], 2),
        "max_ms": round(zeiten[-1], 2),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--groessen", default="1000,10000", help="Bestandsgroessen, durch Komma getrennt"
    )
    p.add_argument("--wiederholungen", type=int, default=40)
    p.add_argument("--k", type=int, default=10, help="Anzahl Treffer je Suche")
    p.add_argument("--ausgabe", default=str(WURZEL / "bench" / "results" / "latenz.json"))
    args = p.parse_args()

    groessen = [int(x) for x in args.groessen.split(",")]
    s = load_settings()
    db = Database(s.database_url, s.embedding_dim, max_size=2)
    embedder = build_provider(s.embedding_provider, s.embedding_model, s.embedding_dim)

    with db.conn() as c:
        vorhanden = c.execute(
            "SELECT count(*) AS n FROM parts WHERE embedding IS NOT NULL"
        ).fetchone()["n"]
    print(f"Bestand in der Datenbank: {vorhanden} Teile mit Vektor")
    if vorhanden < max(groessen):
        print(
            f"FEHLER: fuer {max(groessen)} Teile reicht der Bestand nicht. "
            f"Erst aufbauen (scripts/einrichten.py --beispiele {max(groessen)})."
        )
        return 1

    vektoren = embedder.embed(SUCHTEXTE)
    ergebnis: dict[str, dict[str, Any]] = {}

    for n in groessen:
        print(f"\n===== {n} Teile =====")
        with db.conn() as c:
            # Eigene Kopie der ersten n Teile: der Bestand bleibt unangetastet.
            c.execute("DROP TABLE IF EXISTS messmenge")
            c.execute(
                """CREATE TABLE messmenge AS
                     SELECT id, sku, title, subcategory, embedding
                       FROM parts WHERE embedding IS NOT NULL
                      ORDER BY id LIMIT %s""",
                (n,),
            )
            c.commit()

        def seq() -> None:
            with db.conn() as c:
                c.execute("SET LOCAL enable_indexscan = off")
                c.execute("SET LOCAL enable_bitmapscan = off")
                for v in vektoren:
                    c.execute(ABFRAGE, (v, args.k)).fetchall()

        print("  sequenzieller Durchlauf laeuft ...")
        seq_zeit = zeitmessung(seq, max(5, args.wiederholungen // 8))
        seq_je = {k: round(v / len(SUCHTEXTE), 2) for k, v in seq_zeit.items()}

        exakt: list[list[int]] = []
        with db.conn() as c:
            c.execute("SET LOCAL enable_indexscan = off")
            c.execute("SET LOCAL enable_bitmapscan = off")
            for v in vektoren:
                exakt.append([r["id"] for r in c.execute(ABFRAGE, (v, args.k)).fetchall()])

        print("  HNSW-Index bauen ...")
        t0 = time.perf_counter()
        with db.conn() as c:
            c.execute(
                "CREATE INDEX messmenge_hnsw ON messmenge "
                "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
            )
            c.commit()
        bauzeit = round(time.perf_counter() - t0, 2)

        with db.conn() as c:
            groesse = c.execute(
                "SELECT pg_size_pretty(pg_relation_size('messmenge_hnsw')) AS g,"
                "       pg_relation_size('messmenge_hnsw') AS bytes"
            ).fetchone()

        def hnsw() -> None:
            with db.conn() as c:
                for v in vektoren:
                    c.execute(ABFRAGE, (v, args.k)).fetchall()

        print("  HNSW-Suche laeuft ...")
        hnsw_zeit = zeitmessung(hnsw, args.wiederholungen)
        hnsw_je = {k: round(v / len(SUCHTEXTE), 2) for k, v in hnsw_zeit.items()}

        naeherung: list[list[int]] = []
        with db.conn() as c:
            for v in vektoren:
                naeherung.append([r["id"] for r in c.execute(ABFRAGE, (v, args.k)).fetchall()])

        recall = statistics.fmean(
            len(set(a) & set(b)) / len(a) for a, b in zip(exakt, naeherung, strict=True) if a
        )

        beschleunigung = (
            round(seq_je["median_ms"] / hnsw_je["median_ms"], 1) if hnsw_je["median_ms"] else 0
        )
        ergebnis[str(n)] = {
            "teile": n,
            "sequenziell": seq_je,
            "hnsw": hnsw_je,
            "beschleunigung": beschleunigung,
            "recall_at_k": round(recall, 4),
            "k": args.k,
            "indexbauzeit_s": bauzeit,
            "indexgroesse": groesse["g"],
            "indexgroesse_bytes": groesse["bytes"],
        }
        print(f"  sequenziell: {seq_je['median_ms']:8.2f} ms je Suche")
        print(
            f"  HNSW:        {hnsw_je['median_ms']:8.2f} ms je Suche   "
            f"({beschleunigung}x schneller)"
        )
        print(
            f"  Recall@{args.k}:   {recall * 100:7.1f} %   "
            f"Index: {groesse['g']} in {bauzeit}s gebaut"
        )

        with db.conn() as c:
            c.execute("DROP TABLE IF EXISTS messmenge")
            c.commit()

    aus = pathlib.Path(args.ausgabe)
    aus.parent.mkdir(parents=True, exist_ok=True)
    aus.write_text(
        json.dumps(
            {
                "suchtexte": len(SUCHTEXTE),
                "wiederholungen": args.wiederholungen,
                "einbettung": {"anbieter": s.embedding_provider, "dimensionen": s.embedding_dim},
                "ergebnis": ergebnis,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nGeschrieben: {aus}")
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
