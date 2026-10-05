"""Taeglicher Lagerabgleich.

Der Shop schickt eine Datei (CSV oder JSON) an /api/sync. Jede Zeile
wird einzeln geprüft: eine fehlerhafte Zeile verwirft nicht die
ganze Lieferung, sondern wird gemeldet und uebersprungen. Das ist für
den Betreiber entscheidend - sonst steht der Bot wegen eines Tippfehlers
in Zeile 4000 einen Tag lang auf altem Bestand.

Einbettungen werden nur neu berechnet, wenn sich der Suchtext
tatsaechlich geändert hat. Ein unveraendertes Teil kostet also nichts.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from .embeddings import EmbeddingProvider

log = logging.getLogger("teilethuns.sync")

PFLICHTFELDER = ("sku", "title", "brand", "model", "category", "price_cents")

# Spaltennamen, wie sie in Lagerprogrammen üblich vorkommen.
SPALTEN_ALIAS: dict[str, str] = {
    "artikelnummer": "sku", "artikelnr": "sku", "art_nr": "sku", "nummer": "sku",
    "bezeichnung": "title", "titel": "title", "name": "title",
    "beschreibung": "description", "text": "description",
    "marke": "brand", "hersteller": "brand", "fabrikat": "brand",
    "modell": "model", "typ": "model", "baureihe": "model",
    "baujahr_von": "year_from", "bj_von": "year_from", "jahr_von": "year_from",
    "baujahr_bis": "year_to", "bj_bis": "year_to", "jahr_bis": "year_to",
    "kategorie": "category", "gruppe": "category", "warengruppe": "category",
    "unterkategorie": "subcategory", "bauteil": "subcategory",
    "seite": "side", "lage": "side", "position": "side",
    "zustand": "condition",
    "preis": "price_euro", "preis_euro": "price_euro", "vk": "price_euro",
    "preis_cent": "price_cents",
    "bestand": "stock", "menge": "stock", "lagerbestand": "stock", "anzahl": "stock",
    "gewicht": "weight_grams", "gewicht_gramm": "weight_grams",
    "gewicht_kg": "weight_kg",
    "oem": "oem_numbers", "oem_nummern": "oem_numbers", "vergleichsnummern": "oem_numbers",
    "ebay": "on_ebay", "auf_ebay": "on_ebay", "ebay_flag": "on_ebay",
    "ebay_link": "ebay_url", "ebay_url": "ebay_url",
    "aktiv": "active",
}

WAHR = {"1", "true", "ja", "j", "y", "yes", "wahr", "x"}
FALSCH = {"0", "false", "nein", "n", "no", "falsch", ""}


@dataclass
class SyncErgebnis:
    empfangen: int = 0
    uebernommen: int = 0
    abgewiesen: int = 0
    deaktiviert: int = 0
    neu_eingebettet: int = 0
    fehler: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "empfangen": self.empfangen,
            "uebernommen": self.uebernommen,
            "abgewiesen": self.abgewiesen,
            "deaktiviert": self.deaktiviert,
            "neu_eingebettet": self.neu_eingebettet,
            # Nur die ersten 50 Fehler: eine kaputte Datei soll keine
            # Antwort mit 10.000 Zeilen erzeugen.
            "fehler": self.fehler[:50],
            "fehler_gesamt": len(self.fehler),
        }


def _bool(wert: Any, feld: str) -> bool:
    if isinstance(wert, bool):
        return wert
    s = str(wert or "").strip().lower()
    if s in WAHR:
        return True
    if s in FALSCH:
        return False
    raise ValueError(f"{feld}: '{wert}' ist kein Ja/Nein-Wert")


def _int(wert: Any, feld: str, standard: int | None = None) -> int | None:
    s = str(wert if wert is not None else "").strip().replace(" ", "")
    if s == "":
        return standard
    s = s.replace(",", ".")
    try:
        return int(round(float(s)))
    except ValueError as exc:
        raise ValueError(f"{feld}: '{wert}' ist keine Zahl") from exc


def spalten_normieren(zeile: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in zeile.items():
        if k is None:
            continue
        key = str(k).strip().lower().replace(" ", "_").replace("-", "_")
        key = key.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
        out[SPALTEN_ALIAS.get(key, key)] = v
    return out


def suchtext_bauen(t: dict[str, Any]) -> str:
    """Ein lesbarer Satz, aus dem die Einbettung gebildet wird.

    Ganze Sätze schlagen Stichwortlisten: das Satzmodell ist auf
    Sprache trainiert, nicht auf Tabellenzellen.
    """
    teile = [t["title"]]
    lage = t.get("side") or ""
    if lage:
        teile.append(lage)
    teile.append(f"für {t['brand']} {t['model']}")
    if t.get("year_from") and t.get("year_to"):
        teile.append(f"Baujahr {t['year_from']} bis {t['year_to']}")
    teile.append(f"Kategorie {t['category']}")
    if t.get("subcategory"):
        teile.append(t["subcategory"])
    if t.get("description"):
        teile.append(str(t["description"])[:400])
    if t.get("oem_numbers"):
        teile.append("Vergleichsnummern " + " ".join(t["oem_numbers"][:6]))
    return ", ".join(str(x) for x in teile if x)


def zeile_pruefen(roh: dict[str, Any], nummer: int) -> dict[str, Any]:
    z = spalten_normieren(roh)

    # Preis darf in Euro oder Cent kommen.
    if "price_cents" not in z or str(z.get("price_cents", "")).strip() == "":
        euro = z.get("price_euro")
        if euro is None or str(euro).strip() == "":
            raise ValueError("Preis fehlt (price_cents oder preis)")
        z["price_cents"] = int(round(float(str(euro).replace(",", ".")) * 100))

    if "weight_kg" in z and str(z.get("weight_kg", "")).strip() != "":
        z["weight_grams"] = int(round(float(str(z["weight_kg"]).replace(",", ".")) * 1000))

    for feld in PFLICHTFELDER:
        if str(z.get(feld, "")).strip() == "":
            raise ValueError(f"Pflichtfeld '{feld}' fehlt oder ist leer")

    oem = z.get("oem_numbers") or []
    if isinstance(oem, str):
        oem = [x.strip() for x in oem.replace(";", ",").replace("|", ",").split(",") if x.strip()]
    oem = [str(x).upper()[:40] for x in oem][:20]

    # Lage vereinheitlichen. Lagerprogramme schreiben "VL", "vorne links",
    # "left front" - gespeichert wird genau einer von vier Werten, weil
    # die Suche darauf filtert. Bei Kombinationen gewinnt links/rechts:
    # danach fragt der Kunde, "vorne" ergibt sich meist aus dem Teil.
    seite = str(z.get("side", "") or "").strip().lower()
    seite = seite.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
    kurz = {
        "l": "links", "li": "links", "left": "links", "ls": "links",
        "r": "rechts", "re": "rechts", "right": "rechts", "rs": "rechts",
        "v": "vorne", "vo": "vorne", "front": "vorne", "vorn": "vorne",
        "h": "hinten", "hi": "hinten", "rear": "hinten", "back": "hinten",
        "vl": "links", "vr": "rechts", "hl": "links", "hr": "rechts",
    }
    if seite in kurz:
        seite = kurz[seite]
    elif "links" in seite or "left" in seite:
        seite = "links"
    elif "rechts" in seite or "right" in seite:
        seite = "rechts"
    elif "vorn" in seite or "front" in seite:
        seite = "vorne"
    elif "hinten" in seite or "rear" in seite:
        seite = "hinten"
    elif seite not in {"links", "rechts", "vorne", "hinten", ""}:
        seite = ""

    on_ebay = _bool(z.get("on_ebay", False), "on_ebay")
    ebay_url = str(z.get("ebay_url", "") or "").strip()
    if on_ebay and not ebay_url:
        raise ValueError("Teil ist als eBay-Artikel markiert, aber ohne eBay-Link")
    if ebay_url and not ebay_url.startswith(("https://", "http://")):
        raise ValueError(f"eBay-Link sieht nicht wie eine Adresse aus: {ebay_url[:60]}")

    preis = _int(z["price_cents"], "price_cents") or 0
    if preis < 0:
        raise ValueError("Preis ist negativ")
    if preis > 5_000_000:
        raise ValueError("Preis über 50.000 Euro - bitte prüfen")

    bestand = _int(z.get("stock"), "stock", 0) or 0
    if bestand < 0:
        raise ValueError("Bestand ist negativ")

    jahr_von = _int(z.get("year_from"), "year_from", None)
    jahr_bis = _int(z.get("year_to"), "year_to", None)
    if jahr_von and jahr_bis and jahr_von > jahr_bis:
        raise ValueError(f"Baujahr von ({jahr_von}) liegt hinter bis ({jahr_bis})")

    teil = {
        "zeile": nummer,
        "sku": str(z["sku"]).strip()[:64],
        "title": str(z["title"]).strip()[:300],
        "description": str(z.get("description", "") or "").strip()[:2000],
        "brand": str(z["brand"]).strip()[:60],
        "model": str(z["model"]).strip()[:60],
        "year_from": jahr_von,
        "year_to": jahr_bis,
        "category": str(z["category"]).strip()[:60],
        "subcategory": str(z.get("subcategory", "") or "").strip()[:60],
        "side": seite,
        "condition": str(z.get("condition", "gebraucht") or "gebraucht").strip()[:40],
        "price_cents": preis,
        "stock": bestand,
        "weight_grams": max(1, _int(z.get("weight_grams"), "weight_grams", 1000) or 1000),
        "oem_numbers": oem,
        "on_ebay": on_ebay,
        "ebay_url": ebay_url[:500],
        "active": _bool(z.get("active", True), "active"),
    }
    teil["search_text"] = suchtext_bauen(teil)
    return teil


def datei_lesen(inhalt: bytes, dateiname: str = "") -> list[dict[str, Any]]:
    """Erkennt CSV oder JSON selbst - der Betreiber soll nicht erst
    ein Format auswaehlen müssen."""
    text = inhalt.decode("utf-8-sig", errors="replace")
    gestrippt = text.lstrip()
    if gestrippt.startswith(("{", "[")) or dateiname.endswith(".json"):
        daten = json.loads(gestrippt)
        if isinstance(daten, dict):
            for key in ("parts", "teile", "items", "data", "rows"):
                if isinstance(daten.get(key), list):
                    return daten[key]
            raise ValueError(
                "JSON-Objekt ohne Liste. Erwartet wird eine Liste von Teilen "
                "oder ein Objekt mit dem Feld 'teile'."
            )
        if not isinstance(daten, list):
            raise ValueError("JSON muss eine Liste von Teilen sein")
        return daten

    # CSV: Trennzeichen selbst erkennen (Semikolon ist in Deutschland üblich).
    probe = text[:4096]
    try:
        dialekt = csv.Sniffer().sniff(probe, delimiters=";,\t|")
    except csv.Error:
        dialekt = csv.excel
        dialekt.delimiter = ";" if probe.count(";") > probe.count(",") else ","
    return list(csv.DictReader(io.StringIO(text), dialect=dialekt))


class Abgleich:
    def __init__(self, db, embedder: EmbeddingProvider) -> None:
        self.db = db
        self.embedder = embedder

    def _lauf_starten(self) -> int:
        with self.db.conn() as c:
            row = c.execute(
                "INSERT INTO sync_runs (status) VALUES ('laufend') RETURNING id"
            ).fetchone()
            c.commit()
        return int(row["id"])

    def _lauf_beenden(self, lauf_id: int, e: SyncErgebnis, status: str, meldung: str) -> None:
        with self.db.conn() as c:
            c.execute(
                """UPDATE sync_runs SET finished_at = now(), rows_received=%s,
                       rows_upserted=%s, rows_rejected=%s, rows_deactivated=%s,
                       status=%s, message=%s
                     WHERE id=%s""",
                (e.empfangen, e.uebernommen, e.abgewiesen, e.deaktiviert,
                 status, meldung[:1000], lauf_id),
            )
            c.commit()

    def ausfuehren(
        self, zeilen: Iterable[dict[str, Any]], vollabgleich: bool = False
    ) -> SyncErgebnis:
        e = SyncErgebnis()
        lauf_id = self._lauf_starten()
        try:
            geprueft: list[dict[str, Any]] = []
            gesehene_skus: set[str] = set()
            for nr, roh in enumerate(zeilen, start=1):
                e.empfangen += 1
                try:
                    teil = zeile_pruefen(roh, nr)
                except Exception as exc:
                    e.abgewiesen += 1
                    e.fehler.append({
                        "zeile": nr,
                        "artikelnummer": str(roh.get("sku") or roh.get("artikelnummer") or "?")[:64],
                        "problem": str(exc),
                    })
                    continue
                if teil["sku"] in gesehene_skus:
                    e.abgewiesen += 1
                    e.fehler.append({
                        "zeile": nr, "artikelnummer": teil["sku"],
                        "problem": "Artikelnummer kommt in der Datei mehrfach vor",
                    })
                    continue
                gesehene_skus.add(teil["sku"])
                geprueft.append(teil)

            if not geprueft:
                self._lauf_beenden(lauf_id, e, "fehlgeschlagen", "Keine gueltige Zeile in der Datei")
                return e

            # Welche Suchtexte haben sich geändert? Nur die brauchen
            # eine neue Einbettung.
            with self.db.conn() as c:
                bekannt = {
                    r["sku"]: r["hash"]
                    for r in c.execute(
                        """SELECT sku, md5(search_text) AS hash FROM parts
                            WHERE sku = ANY(%s) AND embedding IS NOT NULL""",
                        ([t["sku"] for t in geprueft],),
                    ).fetchall()
                }

            zu_einbetten = [
                t for t in geprueft
                if bekannt.get(t["sku"])
                != hashlib.md5(t["search_text"].encode("utf-8")).hexdigest()
            ]
            vektoren: dict[str, list[float]] = {}
            for i in range(0, len(zu_einbetten), 64):
                block = zu_einbetten[i : i + 64]
                vektorblock = self.embedder.embed([x["search_text"] for x in block])
                for t, v in zip(block, vektorblock, strict=True):
                    vektoren[t["sku"]] = v
            e.neu_eingebettet = len(vektoren)

            with self.db.conn() as c:
                with c.cursor() as cur:
                    for t in geprueft:
                        vec = vektoren.get(t["sku"])
                        cur.execute(
                            """
                            INSERT INTO parts (sku,title,description,brand,model,year_from,
                                year_to,category,subcategory,side,condition,price_cents,stock,
                                weight_grams,oem_numbers,on_ebay,ebay_url,active,search_text,
                                embedding,updated_at)
                            VALUES (%(sku)s,%(title)s,%(description)s,%(brand)s,%(model)s,
                                %(year_from)s,%(year_to)s,%(category)s,%(subcategory)s,%(side)s,
                                %(condition)s,%(price_cents)s,%(stock)s,%(weight_grams)s,
                                %(oem_numbers)s,%(on_ebay)s,%(ebay_url)s,%(active)s,
                                %(search_text)s,%(embedding)s, now())
                            ON CONFLICT (sku) DO UPDATE SET
                                title=EXCLUDED.title, description=EXCLUDED.description,
                                brand=EXCLUDED.brand, model=EXCLUDED.model,
                                year_from=EXCLUDED.year_from, year_to=EXCLUDED.year_to,
                                category=EXCLUDED.category, subcategory=EXCLUDED.subcategory,
                                side=EXCLUDED.side, condition=EXCLUDED.condition,
                                price_cents=EXCLUDED.price_cents, stock=EXCLUDED.stock,
                                weight_grams=EXCLUDED.weight_grams,
                                oem_numbers=EXCLUDED.oem_numbers, on_ebay=EXCLUDED.on_ebay,
                                ebay_url=EXCLUDED.ebay_url, active=EXCLUDED.active,
                                search_text=EXCLUDED.search_text,
                                embedding=COALESCE(EXCLUDED.embedding, parts.embedding),
                                updated_at=now()
                            """,
                            {**{k: v for k, v in t.items() if k != "zeile"}, "embedding": vec},
                        )
                        e.uebernommen += 1

                    if vollabgleich:
                        # Was nicht geliefert wurde, ist nicht mehr im Bestand.
                        # Nicht löschen: der Kunde soll noch eine Auskunft
                        # bekommen, und Verkaufsdaten brauchen den Bezug.
                        cur.execute(
                            """UPDATE parts SET active = FALSE, stock = 0, updated_at = now()
                                WHERE active AND NOT (sku = ANY(%s))""",
                            (list(gesehene_skus),),
                        )
                        e.deaktiviert = cur.rowcount
                c.commit()

            status = "erfolgreich" if e.abgewiesen == 0 else "mit_warnungen"
            self._lauf_beenden(
                lauf_id, e, status,
                f"{e.uebernommen} übernommen, {e.abgewiesen} abgewiesen, "
                f"{e.neu_eingebettet} neu eingebettet",
            )
            return e
        except Exception as exc:
            log.exception("Abgleich abgebrochen")
            self._lauf_beenden(lauf_id, e, "fehlgeschlagen", str(exc))
            raise
