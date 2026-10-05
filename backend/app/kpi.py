"""Auskünfte für die Betriebsleitung.

Es gibt keinen Weg von freiem Text zu freiem SQL. Stattdessen werden
aus der Frage eine Absicht und ein Zeitraum erkannt; dazu gehoert eine
feste, gepruefte Abfrage. Dadurch kann der Bot
hier weder etwas erfinden noch versehentlich fremde Tabellen lesen.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .embeddings import normalisieren
from .vokabular import stamm

ZEITRAEUME: list[tuple[tuple[str, ...], str, int]] = [
    (("heute",), "heute", 1),
    (("gestern",), "gestern", 1),
    (("woche", "wochen"), "letzte 7 Tage", 7),
    (("monat", "monats", "monate"), "letzte 30 Tage", 30),
    (("quartal",), "letzte 90 Tage", 90),
    (("jahr", "jahres"), "letzte 365 Tage", 365),
]

# Absichten mit ihren Signalwoertern. Erkannt wird nicht der erste
# Treffer, sondern die Absicht mit den meisten Treffern – sonst
# entscheidet die Reihenfolge der Liste statt der Frage.
ABSICHTEN: list[tuple[str, tuple[str, ...]]] = [
    ("umsatz", ("umsatz", "umsaetze", "erloes", "erloese", "einnahme",
                "einnahmen", "verdient", "eingenommen")),
    ("stueckzahl", ("verkaufszahlen", "stueck", "stueckzahl", "stueckzahlen",
                    "verkauft", "absatz", "tagesverlauf")),
    ("topseller", ("topseller", "bestseller", "beliebteste", "meistverkauft",
                   "laeuft", "gaengig", "rennt")),
    ("kanal", ("ebay", "kanal", "kanaele", "marktplatz", "plattform",
               "verkaufsweg", "vergleich")),
    ("lager", ("lager", "lagerbestand", "bestand", "vorrat", "lagerwert",
               "ladenhueter", "vorraetig")),
    ("luecken", ("luecke", "luecken", "nachfrage", "ohne", "treffer",
                 "vergeblich", "erfolglos", "nachgefragt")),
    ("betrieb", ("fehler", "stoerung", "stoerungen", "panne", "protokoll",
                 "anfragen", "gespraech", "gespraeche", "betriebslage",
                 "ausfall", "funktioniert")),
]

@dataclass
class Auskunft:
    absicht: str
    zeitraum: str
    text: str
    tabelle: list[dict[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "absicht": self.absicht,
            "zeitraum": self.zeitraum,
            "text": self.text,
            "tabelle": self.tabelle,
        }


def _euro(cents: int | None) -> str:
    return f"{(cents or 0) / 100:,.2f} Euro".replace(",", "X").replace(".", ",").replace("X", ".")


def absicht_erkennen(frage: str) -> str:
    staemme = {stamm(w) for w in normalisieren(frage).split()}
    beste, punkte = "uebersicht", 0
    for name, worte in ABSICHTEN:
        treffer = len(staemme & {stamm(w) for w in worte})
        if treffer > punkte:
            beste, punkte = name, treffer
    return beste


def zeitraum_erkennen(frage: str) -> tuple[str, int, int]:
    """Gibt (Bezeichnung, Tage zurück, Versatz in Tagen) zurück."""
    staemme = {stamm(w) for w in normalisieren(frage).split()}
    for worte, label, tage in ZEITRAEUME:
        if staemme & {stamm(w) for w in worte}:
            versatz = 1 if label == "gestern" else 0
            return label, tage, versatz
    return "letzte 30 Tage", 30, 0


class Kennzahlen:
    def __init__(self, db) -> None:
        self.db = db

    def _rows(self, sql: str, params: tuple = ()) -> list[dict]:
        with self.db.conn() as c:
            return [dict(r) for r in c.execute(sql, params).fetchall()]

    # -- Einzelauskuenfte --------------------------------------------
    def umsatz(self, tage: int, versatz: int, label: str) -> Auskunft:
        rows = self._rows(
            """
            SELECT coalesce(sum(revenue_cents),0) AS umsatz_cents,
                   coalesce(sum(quantity),0)      AS stueck,
                   count(DISTINCT order_ref)      AS auftraege
              FROM sales
             WHERE sold_at >= (current_date - make_interval(days => %s + %s))
               AND sold_at <  (current_date - make_interval(days => %s) + INTERVAL '1 day')
            """,
            (tage, versatz, versatz),
        )
        r = rows[0]
        schnitt = (r["umsatz_cents"] / r["auftraege"]) if r["auftraege"] else 0
        return Auskunft(
            "umsatz", label,
            f"Umsatz {label}: {_euro(r['umsatz_cents'])} aus {r['auftraege']} "
            f"Aufträgen ({r['stueck']} Teile). Durchschnittlicher Auftragswert "
            f"{_euro(int(schnitt))}.",
            rows,
        )

    def stueckzahl(self, tage: int, versatz: int, label: str) -> Auskunft:
        rows = self._rows(
            """
            SELECT date_trunc('day', sold_at)::date AS tag,
                   sum(quantity)      AS stueck,
                   sum(revenue_cents) AS umsatz_cents
              FROM sales
             WHERE sold_at >= current_date - make_interval(days => %s)
             GROUP BY 1 ORDER BY 1 DESC
            """,
            (tage + versatz,),
        )
        gesamt = sum(r["stueck"] for r in rows)
        return Auskunft(
            "stueckzahl", label,
            f"{gesamt} verkaufte Teile {label}, aufgeschluesselt nach Tag.",
            rows,
        )

    def topseller(self, tage: int, versatz: int, label: str) -> Auskunft:
        rows = self._rows(
            """
            SELECT s.part_sku, coalesce(p.title,'(nicht mehr im Bestand)') AS titel,
                   sum(s.quantity) AS stueck, sum(s.revenue_cents) AS umsatz_cents
              FROM sales s LEFT JOIN parts p ON p.sku = s.part_sku
             WHERE s.sold_at >= current_date - make_interval(days => %s)
             GROUP BY 1,2 ORDER BY stueck DESC, umsatz_cents DESC LIMIT 10
            """,
            (tage + versatz,),
        )
        if not rows:
            return Auskunft("topseller", label, f"Keine Verkäufe {label}.", [])
        erst = rows[0]
        return Auskunft(
            "topseller", label,
            f"Bestseller {label}: {erst['titel']} ({erst['stueck']} Stück, "
            f"{_euro(erst['umsatz_cents'])}). Die vollständige Liste steht in der Tabelle.",
            rows,
        )

    def kanal(self, tage: int, versatz: int, label: str) -> Auskunft:
        rows = self._rows(
            """
            SELECT channel AS kanal, sum(quantity) AS stueck,
                   sum(revenue_cents) AS umsatz_cents,
                   count(DISTINCT order_ref) AS auftraege
              FROM sales
             WHERE sold_at >= current_date - make_interval(days => %s)
             GROUP BY 1 ORDER BY umsatz_cents DESC
            """,
            (tage + versatz,),
        )
        gesamt = sum(r["umsatz_cents"] for r in rows) or 1
        teile = ", ".join(
            f"{r['kanal']}: {_euro(r['umsatz_cents'])} ({r['umsatz_cents'] * 100 // gesamt} Prozent)"
            for r in rows
        )
        return Auskunft("kanal", label, f"Umsatz je Verkaufsweg {label} - {teile or 'keine Daten'}.", rows)

    def lager(self, *_: Any) -> Auskunft:
        rows = self._rows(
            """
            SELECT category AS kategorie, count(*) AS teile,
                   sum(stock) AS stueck,
                   sum(price_cents::bigint * stock) AS lagerwert_cents,
                   count(*) FILTER (WHERE on_ebay) AS davon_ebay
              FROM parts WHERE active
             GROUP BY 1 ORDER BY lagerwert_cents DESC
            """
        )
        wert = sum(r["lagerwert_cents"] or 0 for r in rows)
        stueck = sum(r["stueck"] or 0 for r in rows)
        return Auskunft(
            "lager", "aktueller Bestand",
            f"{stueck} Teile auf Lager, Verkaufswert {_euro(wert)}, "
            f"verteilt auf {len(rows)} Kategorien.",
            rows,
        )

    def luecken(self, tage: int, versatz: int, label: str) -> Auskunft:
        """Wonach Kunden gefragt haben, ohne etwas zu finden.

        Das ist die nuetzlichste Auskunft für den Einkauf: sie zeigt
        Nachfrage, die der Bestand gerade nicht deckt.
        """
        rows = self._rows(
            """
            SELECT detail AS suchbegriff, count(*) AS anfragen,
                   max(created_at)::date AS zuletzt
              FROM chat_events
             WHERE kind = 'kein_treffer'
               AND created_at >= current_date - make_interval(days => %s)
               AND detail <> ''
             GROUP BY 1 ORDER BY anfragen DESC LIMIT 20
            """,
            (tage + versatz,),
        )
        return Auskunft(
            "luecken", label,
            f"{len(rows)} verschiedene Suchen {label} ohne Treffer. "
            "Das ist Nachfrage, die der Bestand nicht deckt."
            if rows else f"Alle Suchanfragen {label} hatten Treffer.",
            rows,
        )

    def betrieb(self, tage: int, versatz: int, label: str) -> Auskunft:
        rows = self._rows(
            """
            SELECT kind AS art, count(*) AS anzahl,
                   round(avg(latency_ms)) AS schnitt_ms,
                   max(latency_ms) AS langsamste_ms
              FROM chat_events
             WHERE created_at >= current_date - make_interval(days => %s)
             GROUP BY 1 ORDER BY anzahl DESC
            """,
            (tage + versatz,),
        )
        fehler = sum(r["anzahl"] for r in rows if r["art"] == "fehler")
        gesamt = sum(r["anzahl"] for r in rows)
        return Auskunft(
            "betrieb", label,
            f"{gesamt} Chatvorgaenge {label}, davon {fehler} mit Fehler.",
            rows,
        )

    def uebersicht(self, tage: int, versatz: int, label: str) -> Auskunft:
        umsatz = self.umsatz(tage, versatz, label)
        lager = self.lager()
        luecken = self.luecken(tage, versatz, label)
        return Auskunft(
            "uebersicht", label,
            umsatz.text + " " + lager.text + " " + luecken.text,
            umsatz.tabelle + lager.tabelle,
        )

    # -- Einstieg ----------------------------------------------------
    def beantworten(self, frage: str) -> Auskunft:
        absicht = absicht_erkennen(frage)
        label, tage, versatz = zeitraum_erkennen(frage)
        tabelle: dict[str, Callable[..., Auskunft]] = {
            "umsatz": self.umsatz,
            "stueckzahl": self.stueckzahl,
            "topseller": self.topseller,
            "kanal": self.kanal,
            "lager": self.lager,
            "luecken": self.luecken,
            "betrieb": self.betrieb,
            "uebersicht": self.uebersicht,
        }
        return tabelle[absicht](tage, versatz, label)
