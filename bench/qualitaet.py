#!/usr/bin/env python3
"""Messreihe 1: Trifft die Suche das richtige Teil?

Verglichen werden vier Ausbaustufen auf demselben Bestand und
demselben Pruefkatalog. Das zeigt, was jede Schicht wirklich
beitraegt - und nicht nur, dass das Gesamtsystem irgendwie laeuft.

    A  Nur Volltextsuche      PostgreSQL, deutsches Woerterbuch
    B  Nur Vektorsuche        pgvector, HNSW, Kosinus
    C  A+B zusammengefuehrt   Reciprocal Rank Fusion, ohne Fachwissen
    D  Vollstaendig           C + Bauteilerkennung + Mindestaehnlichkeit

Gewertet wird das BAUTEIL. Wer ein Ruecklicht sucht, ist mit jedem
passenden Ruecklicht bedient - aber nie mit einer Bremsscheibe.

Aufruf:
    python scripts/mitenv.py .env bench/qualitaet.py --teile 2000
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

WURZEL = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "backend"))
sys.path.insert(0, str(WURZEL / "bench"))

from anfragen import Pruefanfrage, vollkatalog  # noqa: E402
from app.config import load_settings  # noqa: E402
from app.db import Database  # noqa: E402
from app.embeddings import build_provider  # noqa: E402
from app.search import Filter, TeileSuche  # noqa: E402
from app.sync import Abgleich  # noqa: E402
from testdaten import erzeugen  # noqa: E402


def vereinheitlichen(bezeichnung: str) -> str:
    """Schreibweise egal: "Rueckleuchte" und "Rückleuchte" sind dasselbe
    Bauteil. Gewertet wird der Begriff, nicht die Tippgewohnheit des
    Lagerprogramms."""
    t = (bezeichnung or "").lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"), ("-", " ")):
        t = t.replace(a, b)
    return " ".join(t.split())


def treffer_bauteile(zeilen: list[dict]) -> list[str]:
    return [vereinheitlichen(z["subcategory"]) for z in zeilen]


def bewerten(erwartet: str, gefunden: list[str], leer_erwartet: bool) -> dict:
    erwartet = vereinheitlichen(erwartet)
    if leer_erwartet:
        return {
            "top1": 1.0 if not gefunden else 0.0,
            "top3": 1.0 if not gefunden else 0.0,
            "rr": 1.0 if not gefunden else 0.0,
            "falsch_top1": 1.0 if gefunden else 0.0,
        }
    if not gefunden:
        return {"top1": 0.0, "top3": 0.0, "rr": 0.0, "falsch_top1": 0.0}
    top1 = 1.0 if gefunden[0] == erwartet else 0.0
    top3 = 1.0 if erwartet in gefunden[:3] else 0.0
    rr = 0.0
    for i, b in enumerate(gefunden, start=1):
        if b == erwartet:
            rr = 1.0 / i
            break
    return {"top1": top1, "top3": top3, "rr": rr, "falsch_top1": 1.0 - top1}


class Verfahren:
    def __init__(self, name: str, kurz: str, fn) -> None:
        self.name, self.kurz, self.fn = name, kurz, fn


def messen(suche: TeileSuche, katalog: list[Pruefanfrage], verfahren: list[Verfahren]) -> dict:
    ergebnis: dict[str, dict] = {}
    for v in verfahren:
        summe = {"top1": 0.0, "top3": 0.0, "rr": 0.0, "falsch_top1": 0.0}
        nach_gruppe: dict[str, dict] = {}
        dauer: list[float] = []
        for a in katalog:
            t0 = time.perf_counter()
            gefunden = v.fn(a.text)
            dauer.append((time.perf_counter() - t0) * 1000)
            punkte = bewerten(a.erwartet_bauteil, gefunden, a.erwartet_leer)
            for k in summe:
                summe[k] += punkte[k]
            g = nach_gruppe.setdefault(a.gruppe, {"n": 0, "top1": 0.0, "top3": 0.0})
            g["n"] += 1
            g["top1"] += punkte["top1"]
            g["top3"] += punkte["top3"]
        n = len(katalog)
        dauer.sort()
        ergebnis[v.kurz] = {
            "name": v.name,
            "top1_prozent": round(100 * summe["top1"] / n, 1),
            "top3_prozent": round(100 * summe["top3"] / n, 1),
            "mrr": round(summe["rr"] / n, 3),
            "falsch_top1_prozent": round(100 * summe["falsch_top1"] / n, 1),
            "median_ms": round(dauer[len(dauer) // 2], 1),
            "p95_ms": round(dauer[int(len(dauer) * 0.95)], 1),
            "gruppen": {
                k: {
                    "n": g["n"],
                    "top1_prozent": round(100 * g["top1"] / g["n"], 1),
                    "top3_prozent": round(100 * g["top3"] / g["n"], 1),
                }
                for k, g in sorted(nach_gruppe.items())
            },
        }
    return ergebnis


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--teile", type=int, default=2000, help="Groesse des Pruefbestands")
    p.add_argument("--anfragen-bestand", type=int, default=120)
    p.add_argument("--seed", type=int, default=20261005)
    p.add_argument("--neu-aufbauen", action="store_true",
                   help="Bestand neu erzeugen und einbetten (dauert)")
    p.add_argument("--ausgabe", default=str(WURZEL / "bench" / "results" / "qualitaet.json"))
    args = p.parse_args()

    s = load_settings()
    db = Database(s.database_url, s.embedding_dim)
    embedder = build_provider(s.embedding_provider, s.embedding_model, s.embedding_dim)

    teile = erzeugen(args.teile, seed=args.seed)
    if args.neu_aufbauen:
        print(f"Bestand mit {args.teile} Teilen aufbauen und einbetten ...")
        db.apply_schema()
        with db.conn() as c:
            c.execute("TRUNCATE parts RESTART IDENTITY")
            c.commit()
        t0 = time.perf_counter()
        e = Abgleich(db, embedder).ausfuehren(teile, vollabgleich=True)
        print(f"   {e.uebernommen} Teile in {time.perf_counter()-t0:.1f}s")

    suche = TeileSuche(db, embedder)
    suche.katalog.neu_laden()

    verfahren = [
        Verfahren("A  Nur Volltextsuche (PostgreSQL)", "A_volltext",
                  lambda t: treffer_bauteile(suche._volltext(t, Filter(), 6))),
        Verfahren("B  Nur Vektorsuche (pgvector HNSW)", "B_vektor",
                  lambda t: treffer_bauteile(suche._vektor(t, Filter(), 6))),
        Verfahren("C  Beides zusammengefuehrt (RRF)", "C_hybrid",
                  lambda t: treffer_bauteile([x.teil for x in suche._fusion(t, Filter(), 6, 30)])),
        Verfahren("D  Vollstaendig (RRF + Bauteilerkennung + Schwelle)", "D_voll",
                  lambda t: [vereinheitlichen(x.teil["subcategory"])
                             for x in suche.suchen_ausfuehrlich(t, limit=6).treffer]),
    ]

    katalog = vollkatalog(teile, args.anfragen_bestand, seed=args.seed % 10000)
    print(f"Pruefkatalog: {len(katalog)} Anfragen gegen {args.teile} Teile\n")

    ergebnis = messen(suche, katalog, verfahren)

    # -- Ausgabe ---------------------------------------------------
    kopf = f"{'Verfahren':52s} {'Top-1':>7s} {'Top-3':>7s} {'MRR':>6s} {'falsch':>7s} {'Median':>8s}"
    print(kopf)
    print("-" * len(kopf))
    for v in verfahren:
        r = ergebnis[v.kurz]
        print(f"{r['name']:52s} {r['top1_prozent']:6.1f}% {r['top3_prozent']:6.1f}% "
              f"{r['mrr']:6.3f} {r['falsch_top1_prozent']:6.1f}% {r['median_ms']:7.1f}ms")

    print("\nNach Art der Anfrage (Top-1, Verfahren D):")
    for g, w in ergebnis["D_voll"]["gruppen"].items():
        vergleich = ergebnis["B_vektor"]["gruppen"].get(g, {}).get("top1_prozent", 0)
        print(f"   {g:18s} n={w['n']:4d}   D: {w['top1_prozent']:5.1f}%   "
              f"(nur Vektorsuche: {vergleich:5.1f}%)")

    aus = pathlib.Path(args.ausgabe)
    aus.parent.mkdir(parents=True, exist_ok=True)
    aus.write_text(json.dumps({
        "bestand": args.teile,
        "anfragen": len(katalog),
        "einbettung": {"anbieter": s.embedding_provider, "modell": s.embedding_model,
                       "dimensionen": s.embedding_dim},
        "ergebnis": ergebnis,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nGeschrieben: {aus}")
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
