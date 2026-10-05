#!/usr/bin/env python3
"""Erzeugt die Diagramme der Messreihen als SVG.

Die Bilder werden aus den Messdateien gebaut, nicht von Hand
gezeichnet. Dadurch kann in der Projektbeschreibung keine Zahl stehen,
die so nie gemessen wurde.

Gestaltung und Farben kommen aus bench/stil.py - dieselben wie beim
Architekturschaubild, damit alles als ein Satz erkennbar ist.

Aufruf:   python bench/diagramme.py
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from stil import (  # noqa: E402
    BERNSTEIN,
    GRUEN,
    RASTER,
    SCHIEFER,
    TEXT,
    TEXT_FEIN,
    TEXT_LEISE,
    TUERKIS,
    dez,
    kopf,
    text,
)

WURZEL = pathlib.Path(__file__).resolve().parent.parent
ZIEL = WURZEL / "docs" / "assets"


def balken(x, y, breite, hoehe, anteil, farbe, rund=5):
    """Ein Balken mit Spur dahinter - die Spur zeigt das Maximum."""
    return (f'<rect x="{x}" y="{y}" width="{breite}" height="{hoehe}" rx="{rund}" '
            f'fill="{RASTER}" opacity=".45"/>'
            f'<rect x="{x}" y="{y}" width="{breite*anteil:.1f}" height="{hoehe}" rx="{rund}" '
            f'fill="{farbe}"/>')


def qualitaetsdiagramm(daten: dict) -> str:
    e = daten["ergebnis"]
    reihen = [
        ("A", "nur Volltextsuche", e["A_volltext"], SCHIEFER),
        ("B", "nur Vektorsuche (pgvector)", e["B_vektor"], SCHIEFER),
        ("C", "beides zusammengeführt", e["C_hybrid"], TUERKIS),
        ("D", "vollständig", e["D_voll"], GRUEN),
    ]
    b, h = 820, 376
    links, oben, breite, zeile = 286, 100, 408, 58
    t = kopf(b, h, "Wie oft steht das richtige Bauteil an erster Stelle?",
             f"{daten['anfragen']} Kundenanfragen gegen "
             f"{daten['bestand']:,} Lagerteile. Höher ist besser.".replace(",", "."))

    for p in (0, 25, 50, 75, 100):
        x = links + breite * p / 100
        t.append(text(x, oben - 14, f"{p}%", 11, TEXT_FEIN, "600", "middle", mono=True))
        for i in range(len(reihen)):
            y = oben + i * zeile
            t.append(f'<line x1="{x}" y1="{y-4}" x2="{x}" y2="{y+26}" stroke="{RASTER}" '
                     f'stroke-width="1" stroke-dasharray="3 4"/>')

    for i, (buchstabe, name, r, farbe) in enumerate(reihen):
        y = oben + i * zeile
        hervor = buchstabe == "D"
        t.append(f'<rect x="32" y="{y-2}" width="22" height="22" rx="6" fill="{farbe}" '
                 f'opacity="{0.95 if hervor else 0.3}"/>')
        t.append(text(43, y + 14, buchstabe, 13, "#0E2135" if hervor else TEXT, "800", "middle"))
        t.append(text(64, y + 14, name, 14, TEXT if hervor else TEXT_LEISE,
                      "700" if hervor else "500"))
        t.append(balken(links, y, breite, 22, r["top1_prozent"] / 100, farbe))
        t.append(text(links + breite * r["top1_prozent"] / 100 + 10, y + 16,
                      f"{dez(r['top1_prozent'])} %", 14, TEXT, "800"))
        t.append(text(64, y + 32, f"mittlere Platzierung {dez(r['mrr'], 3)}   ·   "
                                  f"falsches Teil zuoberst {dez(r['falsch_top1_prozent'])} %",
                      11, TEXT_FEIN, "400", mono=True))

    gewinn = e["D_voll"]["top1_prozent"] - e["B_vektor"]["top1_prozent"]
    t.append(f'<line x1="32" y1="{h-62}" x2="{b-32}" y2="{h-62}" stroke="{RASTER}" stroke-width="1"/>')
    t.append(text(32, h - 38,
                  f"Die Vektorsuche allein trifft in {e['B_vektor']['top1_prozent']:.0f} % der Fälle. "
                  f"Mit Volltext, Bauteilerkennung", 13, TEXT, "600"))
    t.append(text(32, h - 19,
                  f"und Mindestähnlichkeit werden daraus {e['D_voll']['top1_prozent']:.0f} % – "
                  f"{dez(gewinn)} Prozentpunkte mehr.", 13, TEXT, "600"))
    t.append("</svg>")
    return "\n".join(t)


def gruppendiagramm(daten: dict) -> str:
    d = daten["ergebnis"]["D_voll"]["gruppen"]
    v = daten["ergebnis"]["B_vektor"]["gruppen"]
    namen = {
        "umgangssprache": "Umgangssprache", "umschreibung": "Umschreibung",
        "synonym": "anderes Wort", "tippfehler": "Tippfehler",
        "schadensbild": "Schadensbild", "normal": "Fachbegriff",
        "aus_bestand": "aus dem Bestand", "unsinn": "fremde Themen",
    }
    reihen = sorted(d.items(), key=lambda kv: kv[1]["top1_prozent"])
    b = 820
    h = 128 + len(reihen) * 42
    links, oben, breite = 212, 112, 470

    t = kopf(b, h, "Wo die Bedeutungssuche allein nicht reicht",
             "Treffer an erster Stelle, nach Art der Kundenanfrage.")
    t.append(f'<rect x="{links}" y="78" width="13" height="13" rx="3.5" fill="{GRUEN}"/>')
    t.append(text(links + 20, 89, "vollständiges System", 11.5, TEXT_LEISE))
    t.append(f'<rect x="{links+182}" y="78" width="13" height="13" rx="3.5" fill="{SCHIEFER}" opacity=".55"/>')
    t.append(text(links + 202, 89, "nur Vektorsuche", 11.5, TEXT_LEISE))

    for i, (schluessel, w) in enumerate(reihen):
        y = oben + i * 42
        t.append(text(32, y + 12, namen.get(schluessel, schluessel), 13.5, TEXT, "600"))
        t.append(text(32, y + 28, f"n = {w['n']}", 10.5, TEXT_FEIN, "400", mono=True))
        vw = v.get(schluessel, {}).get("top1_prozent", 0)
        t.append(f'<rect x="{links}" y="{y}" width="{breite*vw/100:.1f}" height="12" rx="3" '
                 f'fill="{SCHIEFER}" opacity=".55"/>')
        t.append(f'<rect x="{links}" y="{y+16}" width="{breite*w["top1_prozent"]/100:.1f}" '
                 f'height="12" rx="3" fill="{GRUEN}"/>')
        t.append(text(links + breite * max(vw, w["top1_prozent"]) / 100 + 10, y + 21,
                      f"{w['top1_prozent']:.0f} %", 13, TEXT, "800"))
    t.append("</svg>")
    return "\n".join(t)


def latenzdiagramm(daten: dict) -> str:
    e = daten["ergebnis"]
    groessen = sorted((int(k) for k in e), key=int)
    b, h = 820, 440
    links, unten, breite, hoehe = 92, 296, 630, 190
    hoechst = max(e[str(g)]["sequenziell"]["median_ms"] for g in groessen) * 1.2

    t = kopf(b, h, "Antwortzeit je Suche: mit und ohne Index",
             "Dieselbe Abfrage, dieselben Daten. Weniger ist besser.")

    for anteil in (0, 0.25, 0.5, 0.75, 1.0):
        y = unten - hoehe * anteil
        t.append(f'<line x1="{links}" y1="{y}" x2="{links+breite}" y2="{y}" stroke="{RASTER}" '
                 f'stroke-width="1" stroke-dasharray="3 4"/>')
        t.append(text(links - 12, y + 4, dez(hoechst * anteil, 1), 11, TEXT_FEIN, "500", "end", mono=True))
    t.append(text(links - 12, 96, "ms", 11, TEXT_FEIN, "700", "end"))

    gruppe = breite / len(groessen)
    for i, g in enumerate(groessen):
        r = e[str(g)]
        x0 = links + i * gruppe + gruppe * 0.17
        bb = gruppe * 0.25
        for j, (schluessel, farbe, beschriftung) in enumerate(
            [("sequenziell", SCHIEFER, "ohne Index"), ("hnsw", BERNSTEIN, "HNSW")]
        ):
            wert = r[schluessel]["median_ms"]
            bh = max(3, hoehe * wert / hoechst)
            x = x0 + j * (bb + 14)
            t.append(f'<rect x="{x:.1f}" y="{unten-bh:.1f}" width="{bb:.1f}" height="{bh:.1f}" '
                     f'rx="5" fill="{farbe}" opacity="{0.55 if j==0 else 1}"/>')
            t.append(text(x + bb / 2, unten - bh - 9, dez(wert, 2), 12.5, TEXT, "800", "middle", mono=True))
            t.append(text(x + bb / 2, unten + 18, beschriftung, 11, TEXT_LEISE, "500", "middle"))
        mitte = x0 + bb + 7
        t.append(text(mitte, unten + 42, f"{g:,} Teile".replace(",", "."), 13.5, TEXT, "700", "middle"))
        t.append(text(mitte, unten + 62, f"{dez(r['beschleunigung'])}× schneller",
                      12.5, BERNSTEIN, "800", "middle"))
        t.append(text(mitte, unten + 82, f"Treffer {dez(r['recall_at_k']*100)} %",
                      11.5, GRUEN, "700", "middle"))

    t.append(f'<line x1="32" y1="{h-40}" x2="{b-32}" y2="{h-40}" stroke="{RASTER}" stroke-width="1"/>')
    t.append(text(32, h - 18, "Treffer = Anteil der zehn exakt besten Teile, die der Index "
                              "ebenfalls findet. Schnell allein genügt nicht.", 11.5, TEXT_LEISE))
    t.append("</svg>")
    return "\n".join(t)


def als_png(svg_pfad: pathlib.Path, breite: int = 1600) -> bool:
    """Legt eine Bildfassung daneben.

    LinkedIn und die meisten anderen Netzwerke zeigen kein SVG an.
    Ohne Bildfassung bliebe die Messreihe dort unsichtbar - und genau
    sie ist das Argument.
    """
    try:
        import cairosvg
    except ImportError:
        return False
    ziel = svg_pfad.with_suffix(".png")
    cairosvg.svg2png(url=str(svg_pfad), write_to=str(ziel), output_width=breite)
    return True


def main() -> int:
    ZIEL.mkdir(parents=True, exist_ok=True)
    erzeugt = []
    qpfad = WURZEL / "bench" / "results" / "qualitaet.json"
    if qpfad.exists():
        daten = json.loads(qpfad.read_text(encoding="utf-8"))
        (ZIEL / "messung-qualitaet.svg").write_text(qualitaetsdiagramm(daten), encoding="utf-8")
        (ZIEL / "messung-gruppen.svg").write_text(gruppendiagramm(daten), encoding="utf-8")
        erzeugt += ["messung-qualitaet.svg", "messung-gruppen.svg"]
    lpfad = WURZEL / "bench" / "results" / "latenz.json"
    if lpfad.exists():
        daten = json.loads(lpfad.read_text(encoding="utf-8"))
        (ZIEL / "messung-latenz.svg").write_text(latenzdiagramm(daten), encoding="utf-8")
        erzeugt.append("messung-latenz.svg")
    if not erzeugt:
        print("Keine Messdateien gefunden. Erst bench/qualitaet.py und bench/latenz.py laufen lassen.")
        return 1
    for name in erzeugt:
        print("geschrieben:", ZIEL / name)

    # Bildfassungen fuer Netzwerke, die kein SVG anzeigen
    bilder = [n for n in erzeugt if als_png(ZIEL / n)]
    if bilder:
        print("Bildfassungen (fuer LinkedIn):",
              ", ".join(n.replace(".svg", ".png") for n in bilder))
    else:
        print("Hinweis: cairosvg fehlt - ohne es gibt es keine Bildfassungen "
              "(pip install cairosvg)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
