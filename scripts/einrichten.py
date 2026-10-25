#!/usr/bin/env python3
"""Richtet die Datenbank ein: Schema, Liefergebiete und auf Wunsch erfundene Beispieldaten.

Kontext: Einmalige Einrichtung oder Demo. Aufruf: `python scripts/einrichten.py` für Schema und
Grunddaten, `--beispiele 400` für Beispielteile, zusätzlich `--verkaeufe 900` für eine
Verkaufshistorie. | Eingabe: Umgebungsvariablen laut .env.example. | Ergebnis: Befüllte
Datenbank, Bestandsübersicht auf der Konsole, Rückgabecode 0.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import sys

WURZEL = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "backend"))
sys.path.insert(0, str(WURZEL))

from app.config import load_settings
from app.db import Database
from app.embeddings import build_provider
from app.sync import Abgleich


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--beispiele",
        type=int,
        default=0,
        help="Anzahl erfundener Beispielteile (nur zum Ausprobieren)",
    )
    p.add_argument(
        "--verkaeufe",
        type=int,
        default=0,
        help="Anzahl erfundener Verkaufszeilen (nur zum Ausprobieren)",
    )
    p.add_argument("--seed", type=int, default=20261005)
    args = p.parse_args()
    if args.verkaeufe and not args.beispiele:
        p.error("--verkaeufe braucht --beispiele: Verkaeufe beziehen sich auf die Beispielteile.")

    s = load_settings()
    db = Database(s.database_url, s.embedding_dim)
    print("Schema anlegen ...")
    db.apply_schema()

    print("Grunddaten (Liefergebiete) einspielen ...")
    with db.conn() as c:
        c.execute((WURZEL / "backend" / "grunddaten.sql").read_text(encoding="utf-8"))
        c.commit()

    if args.beispiele:
        sys.path.insert(0, str(WURZEL / "bench"))
        from testdaten import erzeugen, verkaeufe_erzeugen

        print(f"{args.beispiele} Beispielteile erzeugen und einbetten ...")
        teile = erzeugen(args.beispiele, seed=args.seed)
        embedder = build_provider(
            s.embedding_provider,
            s.embedding_model,
            s.embedding_dim,
            os.environ.get("OPENAI_API_KEY"),
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
