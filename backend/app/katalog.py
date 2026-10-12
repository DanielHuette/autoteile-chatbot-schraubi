"""Erkennt Bauteil, Kategorie, Marke und Modell im Kundentext anhand des echten Bestands.

Kontext: Der Katalog wird aus der Datenbank gelesen, nicht gepflegt; so erkennt der Bot nur,
was es gibt, und das Bauteil entscheidet vor dem Fahrzeug. | Eingabe: Kundentext.
| Ergebnis: Erkennung; der Katalog wird fünf Minuten zwischengespeichert.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from .db import Database
from .embeddings import normalisieren
from .vokabular import erweitern, stamm, tippfehler_korrigieren

CACHE_SEKUNDEN = 300

# -inf statt 0.0: time.monotonic() ist kurz nach dem Rechnerstart selbst klein, ein
# verworfener Katalog galt sonst in den ersten fünf Minuten als frisch.
VERALTET = float("-inf")


@dataclass
class Erkennung:
    bauteil: str | None = None
    kategorie: str | None = None
    marke: str | None = None
    modell: str | None = None


class Katalog:
    def __init__(self, db: Database) -> None:
        self.db = db
        self._lock = threading.Lock()
        self._geladen = VERALTET
        self._bauteile: dict[str, str] = {}
        self._kategorien: dict[str, str] = {}
        self._marken: dict[str, str] = {}
        self._modelle: list[tuple[set[str], str, str]] = []
        self._wortschatz: set[str] = set()

    def _laden(self) -> None:
        with self.db.conn() as c:
            zeilen = c.execute(
                """SELECT DISTINCT brand, model, category, subcategory
                     FROM parts WHERE active"""
            ).fetchall()

        bauteile: dict[str, str] = {}
        kategorien: dict[str, str] = {}
        marken: dict[str, str] = {}
        modelle: dict[tuple[str, str], set[str]] = {}

        for r in zeilen:
            for wort in normalisieren(r["brand"]).split():
                if len(wort) > 2:
                    marken[stamm(wort)] = r["brand"]
            # Ohne Längengrenze: einzelne Buchstaben unterscheiden "Astra G" von "Astra H".
            modelle.setdefault((r["model"], r["brand"]), set()).update(
                stamm(w) for w in normalisieren(r["model"]).split()
            )
            for wort in normalisieren(r["category"]).split():
                if len(wort) > 3:
                    kategorien[stamm(wort)] = r["category"]
            if r["subcategory"]:
                for wort in normalisieren(r["subcategory"]).split():
                    if len(wort) > 3:
                        # Ein Wort aus zwei verschiedenen Bauteilen ist mehrdeutig; zwei
                        # Schreibweisen desselben Bauteils sind es nicht.
                        schluessel = stamm(wort)
                        neu_norm = normalisieren(r["subcategory"])
                        if bauteile.get(schluessel):
                            if normalisieren(bauteile[schluessel]) != neu_norm:
                                bauteile[schluessel] = ""
                        else:
                            bauteile.setdefault(schluessel, r["subcategory"])

        self._bauteile = {k: v for k, v in bauteile.items() if v}
        self._kategorien = kategorien
        self._marken = marken
        self._modelle = [(st, mo, ma) for (mo, ma), st in modelle.items()]
        wortschatz: set[str] = set()
        for r in zeilen:
            for feld in ("brand", "model", "category", "subcategory"):
                wortschatz.update(w for w in normalisieren(r[feld] or "").split() if len(w) > 3)
        self._wortschatz = wortschatz
        self._geladen = time.monotonic()

    def _sicherstellen(self) -> None:
        if time.monotonic() - self._geladen < CACHE_SEKUNDEN and self._bauteile:
            return
        with self._lock:
            if time.monotonic() - self._geladen < CACHE_SEKUNDEN and self._bauteile:
                return
            self._laden()

    def wortschatz(self) -> set[str]:
        """Alle Wörter aus Marke, Modell, Kategorie und Bauteil, für die Tippfehlerkorrektur."""
        self._sicherstellen()
        return self._wortschatz

    def neu_laden(self) -> None:
        with self._lock:
            self._laden()

    def verwerfen(self) -> None:
        """Pflicht nach jedem Lagerabgleich, sonst gilt bis zu fünf Minuten der alte Bestand."""
        with self._lock:
            self._geladen = VERALTET

    def erkennen(self, text: str) -> Erkennung:
        self._sicherstellen()
        korrigiert = tippfehler_korrigieren(text, self._wortschatz)
        worte = erweitern(korrigiert).split()
        staemme = [stamm(w) for w in worte]
        menge = set(staemme)

        bauteil = None
        for st in staemme:
            if st in self._bauteile:
                bauteil = self._bauteile[st]
                break

        kategorie = None
        for st in staemme:
            if st in self._kategorien:
                kategorie = self._kategorien[st]
                break

        marke = None
        for st in staemme:
            if st in self._marken:
                marke = self._marken[st]
                break

        # Vollständiger Treffer schlägt Teiltreffer; bleibt es mehrdeutig ("Astra" bei G, H, J),
        # wird kein Modell geraten.
        bewertet: list[tuple[int, bool, str, str]] = []
        for modell_staemme, modell_name, modell_marke in self._modelle:
            if marke and modell_marke != marke:
                continue
            treffer = len(modell_staemme & menge)
            if treffer:
                bewertet.append(
                    (treffer, treffer == len(modell_staemme), modell_name, modell_marke)
                )

        modell = None
        if bewertet:
            bestwert = max((t, v) for t, v, _, _ in bewertet)
            beste = [b for b in bewertet if (b[0], b[1]) == bestwert]
            namen = {b[2] for b in beste}
            if len(namen) == 1:
                modell = beste[0][2]
                if not marke:
                    marke = beste[0][3]
            elif not marke:
                marken = {b[3] for b in beste}
                if len(marken) == 1:
                    marke = beste[0][3]

        return Erkennung(bauteil=bauteil, kategorie=kategorie, marke=marke, modell=modell)
