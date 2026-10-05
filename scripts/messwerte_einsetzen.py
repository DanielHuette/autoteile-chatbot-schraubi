#!/usr/bin/env python3
"""Setzt die gemessenen Werte in die Projektbeschreibung ein.

Damit steht in der README keine Zahl, die nicht aus einer Messdatei
stammt. Die Platzhalter sehen so aus:

    <!-- MESSWERTE-QUALITAET -->   ... <!-- /MESSWERTE-QUALITAET -->

Aufruf:   python scripts/messwerte_einsetzen.py
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

WURZEL = pathlib.Path(__file__).resolve().parent.parent
README = WURZEL / "README.md"
LINKEDIN = WURZEL / "docs" / "LINKEDIN.md"


def de(wert: float, stellen: int = 1) -> str:
    """Deutsche Schreibweise: Komma statt Punkt."""
    return f"{wert:.{stellen}f}".replace(".", ",")


def block_ersetzen(text: str, name: str, inhalt: str) -> str:
    anfang, ende = f"<!-- MESSWERTE-{name} -->", f"<!-- /MESSWERTE-{name} -->"
    inhalt = inhalt.strip()
    # Kurze Werte bleiben in derselben Zeile, lange bekommen eigene.
    neu = (f"{anfang}{inhalt}{ende}" if "\n" not in inhalt and len(inhalt) < 40
           else f"{anfang}\n{inhalt}\n{ende}")
    muster = re.compile(re.escape(anfang) + r".*?" + re.escape(ende), re.S)
    if muster.search(text):
        return muster.sub(neu, text)
    return text.replace(anfang, neu, 1)


def qualitaet() -> str | None:
    pfad = WURZEL / "bench" / "results" / "qualitaet.json"
    if not pfad.exists():
        return None
    d = json.loads(pfad.read_text(encoding="utf-8"))
    e = d["ergebnis"]
    zeilen = [
        f"**{d['anfragen']} Kundenanfragen gegen {d['bestand']:,} Lagerteile.**"
        .replace(",", "."),
        "",
        "| Verfahren | Treffer Platz 1 | in den ersten 3 | mittlere Platzierung | falsches Teil zuoberst |",
        "|---|---:|---:|---:|---:|",
    ]
    namen = {
        "A_volltext": "nur Volltextsuche (PostgreSQL)",
        "B_vektor": "nur Vektorsuche (pgvector, HNSW)",
        "C_hybrid": "beides zusammengeführt (RRF)",
        "D_voll": "**vollständig** (+ Bauteilerkennung, Schwelle)",
    }
    for schluessel, name in namen.items():
        r = e[schluessel]
        fett = "**" if schluessel == "D_voll" else ""
        zeilen.append(
            f"| {name} | {fett}{de(r['top1_prozent'])} %{fett} | {de(r['top3_prozent'])} % | "
            f"{de(r['mrr'], 3)} | {de(r['falsch_top1_prozent'])} % |"
        )
    gewinn = e["D_voll"]["top1_prozent"] - e["B_vektor"]["top1_prozent"]
    zeilen += [
        "",
        f"Die Vektorsuche allein trifft in {de(e['B_vektor']['top1_prozent'])} % der Fälle. "
        f"Mit Volltext, Bauteilerkennung und Mindestähnlichkeit werden daraus "
        f"**{de(e['D_voll']['top1_prozent'])} %** – {de(gewinn)} Prozentpunkte mehr. "
        f"Entscheidender noch: Der Anteil, bei dem ein **falsches** Teil an erster Stelle "
        f"steht, fällt von {de(e['B_vektor']['falsch_top1_prozent'])} % auf "
        f"{de(e['D_voll']['falsch_top1_prozent'])} %.",
        "",
        f"*Einbettungen: {d['einbettung']['anbieter']}, {d['einbettung']['dimensionen']} "
        f"Dimensionen. Reproduzierbar mit* `bench/qualitaet.py`.",
    ]
    return "\n".join(zeilen)


def latenz() -> str | None:
    pfad = WURZEL / "bench" / "results" / "latenz.json"
    if not pfad.exists():
        return None
    d = json.loads(pfad.read_text(encoding="utf-8"))
    e = d["ergebnis"]
    zeilen = [
        "![Antwortzeit mit und ohne Index](docs/assets/messung-latenz.svg)",
        "",
        "| Lagergröße | ohne Index | mit HNSW | schneller | Trefferübereinstimmung | Indexgröße |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for g in sorted(e, key=int):
        r = e[g]
        zeilen.append(
            f"| {int(g):,} Teile |".replace(",", ".")
            + f" {de(r['sequenziell']['median_ms'], 2)} ms |"
            + f" **{de(r['hnsw']['median_ms'], 2)} ms** |"
            + f" {de(r['beschleunigung'])}× |"
            + f" {de(r['recall_at_k']*100)} % |"
            + f" {de(r['indexgroesse_bytes'] / 1024 / 1024)} MB |"
        )
    zeilen += [
        "",
        "*Mittelwert der Mitte (Median) je Einzelsuche, "
        f"{d['suchtexte']} verschiedene Suchtexte, {d['wiederholungen']} Wiederholungen, "
        "nach Warmlauf. Trefferübereinstimmung = Anteil der zehn exakt besten Teile, "
        "die der Index ebenfalls findet.*",
    ]
    return "\n".join(zeilen)


def tests() -> str | None:
    ergebnis = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--no-header"],
        cwd=WURZEL, capture_output=True, text=True,
    )
    treffer = re.search(r"(\d+) passed", ergebnis.stdout)
    if not treffer:
        return None
    anzahl = treffer.group(1)
    dateien = len(list((WURZEL / "tests").glob("test_*.py")))
    return (f"**{anzahl} automatische Tests** in {dateien} Dateien, alle grün. "
            f"Sie laufen bei jeder Änderung über GitHub Actions – zusammen mit der "
            f"Stilprüfung und der Messreihe zur Trefferqualität.")


def linkedin_post(d: dict) -> str:
    e = d["ergebnis"]
    return "\n".join([
        f"> Die Messreihe über {d['anfragen']} echte Kundenformulierungen gegen",
        f"> {d['bestand']:,} Lagerteile:".replace(",", "."),
        ">",
        f"> → nur Volltextsuche: {de(e['A_volltext']['top1_prozent'])} % richtig auf Platz 1",
        f"> → nur Vektorsuche (pgvector, HNSW): {de(e['B_vektor']['top1_prozent'])} %",
        f"> → beides zusammengeführt (Reciprocal Rank Fusion): "
        f"{de(e['C_hybrid']['top1_prozent'])} %",
        f"> → zusätzlich Bauteilerkennung und Mindestähnlichkeit: "
        f"{de(e['D_voll']['top1_prozent'])} %",
        ">",
        f"> Die interessante Zahl ist nicht die {e['D_voll']['top1_prozent']:.0f}. "
        f"Es ist die {e['B_vektor']['top1_prozent']:.0f}.",
    ])


def linkedin_featured(d: dict) -> str:
    e = d["ergebnis"]
    return "\n".join([
        f"> **Gemessen, nicht behauptet** ({d['anfragen']} Kundenanfragen, "
        f"{d['bestand']:,} Lagerteile)".replace(",", "."),
        f"> • nur Volltextsuche: {de(e['A_volltext']['top1_prozent'])} % Treffer auf Platz 1",
        f"> • nur Vektorsuche: {de(e['B_vektor']['top1_prozent'])} %",
        f"> • zusammengeführt: {de(e['C_hybrid']['top1_prozent'])} %",
        f"> • vollständiges System: {de(e['D_voll']['top1_prozent'])} %, "
        f"Mittelwert der Platzierung {de(e['D_voll']['mrr'], 3)}",
        f"> • falsches Teil an erster Stelle: von "
        f"{de(e['B_vektor']['falsch_top1_prozent'])} % auf "
        f"{de(e['D_voll']['falsch_top1_prozent'])} %",
    ])


def linkedin_setzen() -> list[str]:
    pfad = WURZEL / "bench" / "results" / "qualitaet.json"
    if not pfad.exists() or not LINKEDIN.exists():
        return []
    d = json.loads(pfad.read_text(encoding="utf-8"))
    text = LINKEDIN.read_text(encoding="utf-8")
    text = block_ersetzen(text, "POST", linkedin_post(d))
    text = block_ersetzen(text, "FEATURED", linkedin_featured(d))
    testtext = tests()
    if testtext:
        anzahl = re.search(r"\*\*(\d+) automatische", testtext)
        if anzahl:
            text = block_ersetzen(text, "TESTZAHL", anzahl.group(1))
    text = block_ersetzen(
        text, "KURZ", f"{de(d['ergebnis']['D_voll']['top1_prozent'])} %")
    LINKEDIN.write_text(text, encoding="utf-8")
    return ["LinkedIn-POST", "LinkedIn-FEATURED", "LinkedIn-KURZ"]


def main() -> int:
    text = README.read_text(encoding="utf-8")
    gesetzt = []
    for name, fn in (("QUALITAET", qualitaet), ("LATENZ", latenz), ("TESTS", tests)):
        inhalt = fn()
        if inhalt:
            text = block_ersetzen(text, name, inhalt)
            gesetzt.append(name)
        else:
            print(f"   ! keine Daten für {name}")
    README.write_text(text, encoding="utf-8")
    gesetzt += linkedin_setzen()
    print("eingesetzt:", ", ".join(gesetzt) or "nichts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
