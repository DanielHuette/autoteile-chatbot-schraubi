"""Gemeinsame Gestaltung der Messdiagramme: Farben, Schriften, Rahmen, Textbausteine.

Kontext: Eine Stelle für das Aussehen, damit eine Änderung nicht in jedem Diagramm nachgezogen
werden muss. | Eingabe: Koordinaten, Texte, Farben. | Ergebnis: SVG-Fragmente als Text.
"""

from __future__ import annotations

GRUND = "#0E2135"
GRUND_2 = "#132B43"
RASTER = "#1D3C5A"
TEXT = "#EAF2F9"
TEXT_LEISE = "#9DBAD3"
TEXT_FEIN = "#6E8CA8"
TUERKIS = "#4FB3C9"
GRUEN = "#3FAE7A"
BERNSTEIN = "#E8A33B"
SCHIEFER = "#7E9AB5"

MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
SANS = "system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif"


def dez(wert: float, stellen: int = 1) -> str:
    """Deutsche Schreibweise mit Komma."""
    return f"{wert:.{stellen}f}".replace(".", ",")


def kopf(breite: int, hoehe: int, titel: str, unterzeile: str = "") -> list[str]:
    """Rahmen, Raster, Titel - der Anfang jedes Schaubilds."""
    t = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {breite} {hoehe}" '
        f'width="{breite}" height="{hoehe}" role="img" font-family="{SANS}">',
        "<defs>",
        f'<linearGradient id="grund" x1="0" y1="0" x2="0.6" y2="1">'
        f'<stop offset="0" stop-color="{GRUND_2}"/><stop offset="1" stop-color="{GRUND}"/></linearGradient>',
        '<pattern id="raster" width="34" height="34" patternUnits="userSpaceOnUse">'
        f'<path d="M34 0H0v34" fill="none" stroke="{RASTER}" stroke-width=".6" opacity=".45"/></pattern>',
        "</defs>",
        f'<rect width="{breite}" height="{hoehe}" rx="16" fill="url(#grund)"/>',
        f'<rect width="{breite}" height="{hoehe}" rx="16" fill="url(#raster)"/>',
        f'<text x="32" y="40" font-size="19" font-weight="800" fill="{TEXT}">{titel}</text>',
    ]
    if unterzeile:
        t.append(f'<text x="32" y="62" font-size="12.5" fill="{TEXT_LEISE}">{unterzeile}</text>')
    return t


def text(
    x: float,
    y: float,
    inhalt: object,
    groesse: float = 13,
    farbe: str = TEXT_LEISE,
    gewicht: str = "400",
    anker: str = "start",
    mono: bool = False,
) -> str:
    inhalt = str(inhalt).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    schrift = f' font-family="{MONO}"' if mono else ""
    return (
        f'<text x="{x}" y="{y}" font-size="{groesse}" fill="{farbe}" '
        f'font-weight="{gewicht}" text-anchor="{anker}"{schrift}>{inhalt}</text>'
    )
