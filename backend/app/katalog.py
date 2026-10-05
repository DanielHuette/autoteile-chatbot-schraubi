"""Erkennt Bauteil und Fahrzeug im Kundentext - aus dem echten Bestand.

Der Katalog wird nicht gepflegt, sondern aus der Datenbank gelesen:
Marken, Modelle und Bauteilbezeichnungen, die tatsaechlich vorkommen.
Dadurch kann der Bot nichts erkennen, was es nicht gibt, und neue
Bauteilgruppen wirken sofort, ohne Codeaenderung.

Warum das wichtig ist: ohne Bauteilerkennung antwortet eine reine
Aehnlichkeitssuche auf "Rücklicht für den Golf" mit einer Bremsscheibe
für den Golf - die Marke stimmt, das Teil ist falsch. Beim Autoteil
entscheidet aber zuerst das Bauteil, dann das Fahrzeug.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from .embeddings import normalisieren
from .vokabular import erweitern, stamm, tippfehler_korrigieren

CACHE_SEKUNDEN = 300


@dataclass
class Erkennung:
    bauteil: str | None = None
    kategorie: str | None = None
    marke: str | None = None
    modell: str | None = None


class Katalog:
    def __init__(self, db) -> None:
        self.db = db
        self._lock = threading.Lock()
        self._geladen = 0.0
        self._bauteile: dict[str, str] = {}      # Stamm -> Bauteilname
        self._kategorien: dict[str, str] = {}
        self._marken: dict[str, str] = {}
        self._modelle: list[tuple[set[str], str, str]] = []  # Staemme, Modell, Marke
        self._wortschatz: set[str] = set()   # alle Bestandswoerter, für die Tippfehlerkorrektur

    # -- Laden -------------------------------------------------------
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
            schluessel = (r["model"], r["brand"])
            # Auch einzelne Buchstaben und Zahlen zaehlen: genau sie
            # unterscheiden "Astra G" von "Astra H" von "Astra J".
            modelle.setdefault(schluessel, set()).update(
                stamm(w) for w in normalisieren(r["model"]).split()
            )
            for wort in normalisieren(r["category"]).split():
                if len(wort) > 3:
                    kategorien[stamm(wort)] = r["category"]
            if r["subcategory"]:
                for wort in normalisieren(r["subcategory"]).split():
                    if len(wort) > 3:
                        # Ein Wort, das in zwei VERSCHIEDENEN Bauteilen
                        # vorkommt, taugt nicht zur Erkennung: aus
                        # "Steuergeraet" laesst sich nicht ableiten, ob
                        # ABS oder Motor gemeint ist.
                        #
                        # Zwei Schreibweisen desselben Bauteils sind aber
                        # kein Widerspruch - "Rückleuchte" und
                        # "Rückleuchte" meinen dasselbe. Verglichen wird
                        # daher die vereinheitlichte Form.
                        schluessel = stamm(wort)
                        neu_norm = normalisieren(r["subcategory"])
                        if schluessel in bauteile and bauteile[schluessel]:
                            if normalisieren(bauteile[schluessel]) != neu_norm:
                                bauteile[schluessel] = ""   # mehrdeutig
                        else:
                            bauteile.setdefault(schluessel, r["subcategory"])

        self._bauteile = {k: v for k, v in bauteile.items() if v}
        self._kategorien = kategorien
        self._marken = marken
        self._modelle = [(st, mo, ma) for (mo, ma), st in modelle.items()]
        # Wortschatz des Bestands: jedes Wort, das in Marke, Modell,
        # Kategorie oder Bauteil vorkommt. Damit wird auch "Schienwerfer"
        # noch gefunden, ohne eine gepflegte Tippfehlerliste.
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

    def neu_laden(self) -> None:
        with self._lock:
            self._laden()

    def verwerfen(self) -> None:
        """Markiert den Katalog als veraltet.

        Nach einem Lagerabgleich MUSS das passieren: sonst kennt der Bot
        bis zu fuenf Minuten lang die neuen Marken und Bauteile nicht -
        und bietet im Klick-Interview Marken an, zu denen seit dem
        Abgleich kein Teil mehr da ist.
        """
        with self._lock:
            self._geladen = 0.0

    # -- Erkennen ----------------------------------------------------
    def erkennen(self, text: str) -> Erkennung:
        self._sicherstellen()
        # Zwei Schritte: erst Tippfehler auf bekannte Woerter ziehen,
        # dann die Fachbegriffe ergänzen. "Rueklicht" wird so über
        # "ruecklicht" zur "rueckleuchte" - und damit zum Bestand.
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

        # Modell bestimmen. Ein vollstaendiger Treffer ("astra" UND "h")
        # schlaegt einen Teiltreffer. Bleibt es mehrdeutig - der Kunde
        # sagt nur "Astra", es gibt G, H und J - wird KEIN Modell
        # gesetzt. Lieber alle Generationen zeigen und das Baujahr
        # dabeischreiben, als die falsche raten.
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
