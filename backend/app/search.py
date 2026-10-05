"""Teilesuche: Bauteilerkennung, pgvector-Vektorsuche, deutscher Volltext.

Reihenfolge der Verfahren - jedes loest ein anderes Problem:

1. Teilenummer. Wer eine Nummer nennt, weiss was er will. Exakter
   Feldtreffer, kein Raten.
2. Bauteil und Fahrzeug aus dem Text erkennen (katalog.py). Beim
   Autoteil entscheidet zuerst das Bauteil: "Rücklicht für den Golf"
   darf nie eine Bremsscheibe für den Golf liefern.
3. Vektorsuche (pgvector, HNSW, Kosinus) für Bedeutung: "das rote
   Glas hinten" trifft die Rückleuchte, obwohl kein Wort uebereinstimmt.
4. Deutscher Volltext für Zeichen und Wortformen.
5. Trigramm als Rueckfall bei starken Tippfehlern.

Zusammengefuehrt wird mit Reciprocal Rank Fusion: gewichtet nach
Platzierung, nicht nach Punktzahl - so stoeren die unterschiedlichen
Skalen der Verfahren nicht.

Und: es gibt eine Mindestähnlichkeit. Eine Aehnlichkeitssuche liefert
immer etwas, auch bei Unsinn. Sechs falsche Teile sind für einen
Kunden schlechter als die ehrliche Auskunft "dazu habe ich nichts".
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from .embeddings import EmbeddingProvider, normalisieren
from .katalog import Erkennung, Katalog
from .vokabular import erweitern, jahr_erkennen, seite_erkennen, tippfehler_korrigieren

log = logging.getLogger("teilethuns.search")

RRF_K = 60
GEWICHT_VEKTOR = 1.0
GEWICHT_VOLLTEXT = 1.0
GEWICHT_TRIGRAMM = 0.5

# Mindestähnlichkeit der Vektorsuche (Kosinus, 0 bis 1). Unterhalb
# dieser Grenze gilt ein Teil als nicht gemeint. Der Wert ist in
# bench/qualitaet.py gemessen und nicht geschaetzt.
SCHWELLE_VEKTOR = 0.55

TEILENUMMER = re.compile(r"\b(?=[a-z0-9.\-/]*\d)[a-z0-9][a-z0-9.\-/]{4,}\b", re.I)


def sql_norm(text: str) -> str:
    """Genau dieselbe Vereinheitlichung wie die Spalte subcategory_norm.

    Muss mit schema.sql uebereinstimmen - sonst findet der Filter nichts.
    """
    t = text.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        t = t.replace(a, b)
    return t


@dataclass
class Filter:
    marke: str | None = None
    modell: str | None = None
    jahr: int | None = None
    kategorie: str | None = None
    bauteil: str | None = None
    seite: str | None = None
    nur_verfuegbar: bool = True

    def kopie(self, **aenderungen) -> Filter:
        neu = Filter(**self.__dict__)
        for k, v in aenderungen.items():
            setattr(neu, k, v)
        return neu

    def as_params(self) -> tuple:
        # Das Bauteil wird in derselben Schreibweise verglichen wie die
        # Spalte subcategory_norm sie speichert.
        bauteil = sql_norm(self.bauteil) if self.bauteil else None
        return (
            self.nur_verfuegbar,
            self.marke, self.marke,
            self.modell, self.modell,
            self.jahr, self.jahr, self.jahr,
            self.kategorie, self.kategorie,
            bauteil, bauteil,
            self.seite, self.seite,
        )


_WHERE = """
    p.active
    AND (NOT %s OR p.stock > 0)
    AND (%s::text IS NULL OR p.brand       = %s)
    AND (%s::text IS NULL OR p.model       = %s)
    AND (%s::int  IS NULL OR (p.year_from <= %s AND p.year_to >= %s))
    AND (%s::text IS NULL OR p.category    = %s)
    AND (%s::text IS NULL OR p.subcategory_norm = %s)
    AND (%s::text IS NULL OR p.side        = %s OR p.side = '')
"""

_SPALTEN = """
    p.id, p.sku, p.title, p.description, p.brand, p.model,
    p.year_from, p.year_to, p.category, p.subcategory, p.side,
    p.condition, p.price_cents, p.stock, p.weight_grams,
    p.on_ebay, p.ebay_url, p.oem_numbers
"""


@dataclass
class Treffer:
    teil: dict[str, Any]
    punkte: float
    quellen: list[str] = field(default_factory=list)
    aehnlichkeit: float | None = None

    def as_dict(self) -> dict[str, Any]:
        d = {k: v for k, v in self.teil.items() if k not in ("aehnlichkeit", "rang")}
        d["relevanz"] = round(self.punkte, 4)
        d["gefunden_durch"] = self.quellen
        d["preis_euro"] = round(d.pop("price_cents") / 100, 2)
        d["oem_numbers"] = list(d.get("oem_numbers") or [])
        d.pop("id", None)
        return d


@dataclass
class Suchergebnis:
    treffer: list[Treffer] = field(default_factory=list)
    erkennung: Erkennung = field(default_factory=Erkennung)
    # Was gelockert werden musste, damit überhaupt etwas kam.
    # Daraus macht der Dialog einen ehrlichen Satz.
    gelockert: list[str] = field(default_factory=list)
    verwendeter_filter: Filter | None = None


class TeileSuche:
    def __init__(self, db, embedder: EmbeddingProvider) -> None:
        self.db = db
        self.embedder = embedder
        self.katalog = Katalog(db)

    # -- Einzelverfahren ---------------------------------------------
    def _teilenummer_treffer(self, text: str, f: Filter, limit: int) -> list[dict]:
        kandidaten = [m.group(0).upper() for m in TEILENUMMER.finditer(text)]
        if not kandidaten:
            return []
        varianten: list[str] = []
        for k in kandidaten:
            varianten.append(k)
            blank = re.sub(r"[.\-/\s]", "", k)
            if blank != k:
                varianten.append(blank)
        # Bei der Nummernsuche greift nur der Verfuegbarkeitsfilter:
        # eine Nummer ist eindeutig, Marke und Modell stecken schon drin.
        nf = Filter(nur_verfuegbar=f.nur_verfuegbar)
        with self.db.conn() as c:
            rows = c.execute(
                f"""
                SELECT {_SPALTEN}
                  FROM parts p
                 WHERE {_WHERE}
                   AND (
                        upper(p.sku) = ANY(%s)
                     OR upper(replace(replace(replace(p.sku,'-',''),'.',''),'/','')) = ANY(%s)
                     OR EXISTS (
                          SELECT 1 FROM unnest(p.oem_numbers) o
                           WHERE upper(o) = ANY(%s)
                              OR upper(replace(replace(replace(o,'-',''),'.',''),'/','')) = ANY(%s)
                        )
                   )
                 ORDER BY p.stock DESC
                 LIMIT %s
                """,
                (*nf.as_params(), varianten, [re.sub(r"[.\-/]", "", v) for v in varianten],
                 varianten, [re.sub(r"[.\-/]", "", v) for v in varianten], limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def _vektor(self, anfrage: str, f: Filter, limit: int) -> list[dict]:
        vec = self.embedder.embed([anfrage])[0]
        with self.db.conn() as c:
            rows = c.execute(
                f"""
                SELECT {_SPALTEN}, 1 - (p.embedding <=> %s::vector) AS aehnlichkeit
                  FROM parts p
                 WHERE {_WHERE} AND p.embedding IS NOT NULL
                 ORDER BY p.embedding <=> %s::vector
                 LIMIT %s
                """,
                (vec, *f.as_params(), vec, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def _volltext(self, anfrage: str, f: Filter, limit: int) -> list[dict]:
        worte = [w for w in normalisieren(anfrage).split() if len(w) > 2]
        if not worte:
            return []
        # Erst alle Woerter verlangen (UND). Das ist genau. Nur wenn
        # das leer bleibt, wird auf ODER gelockert - sonst ueberschwemmt
        # ein Allerweltswort wie "links" die Liste.
        for verknuepfung in (" & ", " | "):
            tsquery = verknuepfung.join(f"{w}:*" for w in worte)
            with self.db.conn() as c:
                rows = c.execute(
                    f"""
                    SELECT {_SPALTEN}, ts_rank_cd(p.fts, q) AS rang
                      FROM parts p, to_tsquery('german', %s) q
                     WHERE {_WHERE} AND p.fts @@ q
                     ORDER BY rang DESC
                     LIMIT %s
                    """,
                    (tsquery, *f.as_params(), limit),
                ).fetchall()
            if rows:
                return [dict(r) for r in rows]
        return []

    def _trigramm(self, anfrage: str, f: Filter, limit: int) -> list[dict]:
        norm = normalisieren(anfrage)
        if len(norm) < 4:
            return []
        with self.db.conn() as c:
            rows = c.execute(
                f"""
                SELECT {_SPALTEN}, similarity(lower(p.title), %s) AS aehnlichkeit
                  FROM parts p
                 WHERE {_WHERE} AND lower(p.title) %% %s
                 ORDER BY aehnlichkeit DESC
                 LIMIT %s
                """,
                (norm, *f.as_params(), norm, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    # -- Zusammenfuehrung --------------------------------------------
    def _fusion(self, text: str, f: Filter, limit: int, kandidaten: int) -> list[Treffer]:
        # Gleiche Aufbereitung wie bei der Erkennung: Tippfehler ziehen,
        # dann Fachbegriffe ergänzen.
        self.katalog._sicherstellen()
        angereichert = erweitern(tippfehler_korrigieren(text, self.katalog._wortschatz))
        listen: list[tuple[str, float, list[dict]]] = []
        try:
            vektor = self._vektor(angereichert, f, kandidaten)
            # Mindestähnlichkeit anwenden. Ohne Bauteilfilter ist die
            # Grenze wichtiger, denn dann kann alles im Lager antworten.
            schwelle = SCHWELLE_VEKTOR if not f.bauteil else SCHWELLE_VEKTOR - 0.15
            vektor = [r for r in vektor if (r.get("aehnlichkeit") or 0) >= schwelle]
            listen.append(("vektor", GEWICHT_VEKTOR, vektor))
        except Exception:
            log.exception("Vektorsuche fehlgeschlagen - weiter mit Volltext")
        try:
            listen.append(("volltext", GEWICHT_VOLLTEXT, self._volltext(angereichert, f, kandidaten)))
        except Exception:
            log.exception("Volltextsuche fehlgeschlagen")
        try:
            listen.append(("trigramm", GEWICHT_TRIGRAMM, self._trigramm(text, f, kandidaten)))
        except Exception:
            log.exception("Trigrammsuche fehlgeschlagen")

        punkte: dict[int, float] = {}
        quellen: dict[int, list[str]] = {}
        teile: dict[int, dict] = {}
        aehnlich: dict[int, float] = {}
        for name, gewicht, liste in listen:
            for platz, row in enumerate(liste, start=1):
                pid = row["id"]
                punkte[pid] = punkte.get(pid, 0.0) + gewicht / (RRF_K + platz)
                quellen.setdefault(pid, []).append(name)
                teile.setdefault(pid, row)
                if name == "vektor":
                    aehnlich[pid] = float(row.get("aehnlichkeit") or 0)

        # Vorrat vor Ausverkauft, dann Relevanz.
        sortiert = sorted(
            punkte.items(),
            key=lambda kv: (teile[kv[0]]["stock"] > 0, kv[1]),
            reverse=True,
        )
        return [
            Treffer(teile[pid], score, quellen[pid], aehnlich.get(pid))
            for pid, score in sortiert
        ][:limit]

    def suchen_ausfuehrlich(
        self,
        text: str,
        f: Filter | None = None,
        limit: int = 6,
        kandidaten: int = 30,
    ) -> Suchergebnis:
        f = f or Filter()

        # 1) Teilenummer schlaegt alles.
        direkt = self._teilenummer_treffer(text, f, limit)
        if direkt:
            return Suchergebnis(
                treffer=[Treffer(t, 1.0, ["teilenummer"], 1.0) for t in direkt],
                verwendeter_filter=f,
            )

        # 2) Was steckt im Text? Nur ergänzen, nie überschreiben -
        #    eine Vorgabe aus dem Klick-Interview ist verbindlicher als
        #    eine Vermutung aus dem Satz.
        erkennung = self.katalog.erkennen(text)
        if f.seite is None:
            f.seite = seite_erkennen(text)
        if f.jahr is None:
            f.jahr = jahr_erkennen(text)
        if f.bauteil is None and erkennung.bauteil:
            f.bauteil = erkennung.bauteil
        if f.kategorie is None and erkennung.kategorie and not f.bauteil:
            f.kategorie = erkennung.kategorie
        if f.marke is None and erkennung.marke:
            f.marke = erkennung.marke
        if f.modell is None and erkennung.modell:
            f.modell = erkennung.modell

        # 3) Suchen und, wenn noetig, stufenweise lockern. Das Bauteil
        #    wird NIE gelockert: ein falsches Bauteil hilft niemandem.
        #    Gelockert werden nur Angaben, die die Auswahl einengen.
        stufen: list[tuple[Filter, str]] = [(f, "")]
        if f.seite:
            stufen.append((f.kopie(seite=None), "seite"))
        if f.jahr:
            stufen.append((f.kopie(seite=None, jahr=None), "baujahr"))
        if f.modell:
            stufen.append((f.kopie(seite=None, jahr=None, modell=None), "modell"))
        # Letzte Stufe: auch ausverkaufte Teile zeigen, damit der Kunde
        # weiss, dass es das Teil gibt, und nachfragen kann.
        stufen.append((f.kopie(seite=None, jahr=None, nur_verfuegbar=False), "vorrat"))

        # Welche Angaben eine Stufe aufgegeben hat, steht in ihrem Namen.
        # Bei Erfolg werden ALLE bis dahin aufgegebenen Angaben gemeldet -
        # sonst zeigt der Bot ein Teil vom falschen Modell, ohne das zu
        # sagen. Das ist der teuerste Fehler, den er machen kann.
        for nr, (stufe, _name) in enumerate(stufen):
            treffer = self._fusion(text, stufe, limit, kandidaten)
            if treffer:
                return Suchergebnis(
                    treffer=treffer,
                    erkennung=erkennung,
                    gelockert=[n for _, n in stufen[1 : nr + 1] if n],
                    verwendeter_filter=stufe,
                )

        return Suchergebnis(
            erkennung=erkennung,
            gelockert=[n for _, n in stufen[1:] if n],
            verwendeter_filter=f,
        )

    # Kurzform für Aufrufer, die nur die Liste brauchen.
    def suchen(
        self, text: str, f: Filter | None = None, limit: int = 6, kandidaten: int = 30
    ) -> list[Treffer]:
        return self.suchen_ausfuehrlich(text, f, limit, kandidaten).treffer
