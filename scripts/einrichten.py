#!/usr/bin/env python3
"""Richtet die Datenbank ein: Schema, Grunddaten, auf Wunsch Beispielteile.

Aufruf:
    python scripts/einrichten.py                  # Schema + Grunddaten
    python scripts/einrichten.py --beispiele 400  # zusaetzlich Beispielteile
    python scripts/einrichten.py --verkaeufe 900  # zusaetzlich Verkaufshistorie
"""
from __future__ import annotations

import argparse
import pathlib
import sys

WURZEL = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "backend"))
sys.path.insert(0, str(WURZEL))

from app.config import load_settings  # noqa: E402
from app.db import Database  # noqa: E402
from app.embeddings import build_provider  # noqa: E402
from app.sync import Abgleich  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--beispiele", type=int, default=0,
                   help="Anzahl erfundener Beispielteile (nur zum Ausprobieren)")
    p.add_argument("--verkaeufe", type=int, default=0,
                   help="Anzahl erfundener Verkaufszeilen (nur zum Ausprobieren)")
    p.add_argument("--seed", type=int, default=20261005)
    args = p.parse_args()

    s = load_settings()
    db = Database(s.database_url, s.embedding_dim)
    print("Schema anlegen ...")
    db.apply_schema()

    print("Grunddaten (Liefergebiete) einspielen ...")
    with db.conn() as c:
        c.execute((WURZEL / "backend" / "grunddaten.sql").read_text(encoding="utf-8"))
        c.commit()

    if args.beispiele:
        import os
        os.environ.setdefault("PYTHONPATH", str(WURZEL))
        sys.path.insert(0, str(WURZEL / "bench"))
        from testdaten import erzeugen, verkaeufe_erzeugen

        print(f"{args.beispiele} Beispielteile erzeugen und einbetten ...")
        teile = erzeugen(args.beispiele, seed=args.seed)
        embedder = build_provider(
            s.embedding_provider, s.embedding_model, s.embedding_dim,
            __import__("os").environ.get("OPENAI_API_KEY"),
        )
        ergebnis = Abgleich(db, embedder).ausfuehren(teile, vollabgleich=False)
        print("  ", ergebnis.as_dict())

        if args.verkaeufe:
            print(f"{args.verkaeufe} Verkaufszeilen erzeugen ...")
            zeilen = verkaeufe_erzeugen(teile, args.verkaeufe, seed=args.seed % 1000)
            with db.conn() as c:
                with c.cursor() as cur:
                    cur.executemany(
                        """INSERT INTO sales
                             (order_ref, part_sku, sold_at, quantity, revenue_cents, channel)
                           VALUES (%(order_ref)s,%(part_sku)s,%(sold_at)s,%(quantity)s,
                                   %(revenue_cents)s,%(channel)s)""",
                        zeilen,
                    )
                c.commit()
            print("  fertig")

    print("\nStand:", db.healthcheck())
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
