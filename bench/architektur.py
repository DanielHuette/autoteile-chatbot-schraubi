#!/usr/bin/env python3
"""Erzeugt das Architekturschaubild als SVG, PNG und als eigene Seite.

Gestaltung: heller Grund, drei benannte Gruppenflaechen fuer die drei
Ablaeufe, weisse Karten mit farbigem Rand, Farbe nur als Akzent.

Zwei Dinge, die im Bild nachgerechnet und nicht geschaetzt werden:

* Jede Beschriftung muss in ihren Kasten passen. Die Schriftbreite wird
  aus Zeichenzahl und Schriftgroesse berechnet; passt ein Titel nicht,
  bricht das Skript ab, statt ein Bild mit ueberlaufender Schrift zu
  schreiben.
* Jede Pfeilbeschriftung muss in die freie Gasse zwischen zwei Spalten
  passen. Sonst laege sie auf einem Kasten.

Die Kanten bewegen sich (laufende Strichlinie); das steckt im SVG und
laeuft daher auch in der Projektbeschreibung auf GitHub. Das Aufleuchten
bei Mauskontakt braucht eine Seite, die das SVG einbettet statt es als
Bild zu laden - deshalb entsteht zusaetzlich docs/architektur.html.

Aufruf:   python bench/architektur.py
"""
from __future__ import annotations

import base64
import html
import pathlib
import sys

WURZEL = pathlib.Path(__file__).resolve().parent.parent

# --- Raster ---------------------------------------------------------
BREITE = 1400
SP = [96, 418, 740, 1062]        # linke Kante der vier Spalten
BR, KH = 246, 74                 # Kastenbreite und -hoehe
GASSE = {1: (SP[0] + BR + SP[1]) / 2,
         2: (SP[1] + BR + SP[2]) / 2,
         3: (SP[2] + BR + SP[3]) / 2}
GASSENBREITE = SP[1] - (SP[0] + BR)

KOPF = 150
TAKT = 106
R = [KOPF + 58 + i * TAKT for i in range(4)]
MITTE = (R[1] + R[2]) / 2        # Kunde und Widget mittig zur Kette

F1 = (KOPF + 14, R[3] + KH + 30)
F2 = (F1[1] + 32, F1[1] + 32 + 134)
F3 = (F2[1] + 32, F2[1] + 32 + 134)
Y2, Y3 = F2[0] + 38, F3[0] + 38
HOEHE = F3[1] + 46

TITEL = "So arbeitet der Auskunftshelfer"
UNTER = "Vom vagen Satz des Kunden zum richtigen Teil – ohne Teilenummer"
SANS = "Inter,Segoe UI,system-ui,-apple-system,Roboto,Helvetica,Arial,sans-serif"

# --- Farben ---------------------------------------------------------
TINTE = "#0E2C4F"        # Ueberschrift und Kartentitel
GRAU = "#64809B"         # zweite Zeile in der Karte
ORANGE = "#E8872B"       # Signalfarbe der Marke

ART = {
    "akteur":  "#5A7A9B",
    "front":   "#2F6FB5",
    "dienst":  "#1C7FA8",
    "daten":   "#2E8F62",
    "sperre":  "#C8504A",
    "betrieb": "#C97B1E",
}

# Gruppe -> (Flaeche, Rand, Akzent)
GRUPPE = {
    "kunde":   ("#EEF4FC", "#CCDEF2", "#2F6FB5"),
    "sync":    ("#EDF7F1", "#C8E8D6", "#2E8F62"),
    "betrieb": ("#FDF4E9", "#F3DEC4", "#C97B1E"),
}

FLAECHEN = [(F1, "KUNDENANFRAGE", "kunde"),
            (F2, "TÄGLICHER LAGERABGLEICH", "sync"),
            (F3, "BETRIEBSDATEN", "betrieb")]

# kennung, x, y, Art, Titel, zweite Zeile, Sinnbild
KAESTEN = [
    ("kunde",     SP[0], MITTE, "akteur",  "Kunde",              "Beschreibt den Schaden",  "person"),
    ("widget",    SP[1], MITTE, "front",   "Chat-Widget",        "Ein Script-Tag im Shop",  "fenster"),
    ("regeln",    SP[2], R[0],  "sperre",  "Richtlinienfilter" , "Betriebsdaten gesperrt", "schild"),
    ("verstehen", SP[2], R[1],  "dienst",  "Anfrageanalyse",     "Bauteil und Fahrzeug",    "lupe"),
    ("suchen",    SP[2], R[2],  "dienst",  "Hybride Suche",      "Vektor, Volltext, RRF",   "netz"),
    ("antwort",   SP[2], R[3],  "dienst",  "Antwortaufbau",      "Feste Vorlagen",          "sprech"),
    ("parts",     SP[3], R[1],  "daten",   "Teilestamm",         "Tabelle parts",           "db"),
    ("hnsw",      SP[3], R[2],  "daten",   "Vektorindex",        "pgvector HNSW",           "index"),
    ("protokoll", SP[3], R[3],  "daten",   "Ereignisprotokoll",  "Ohne Personenbezug",      "liste"),
    ("lager",     SP[0], Y2,    "akteur",  "Warenwirtschaft",    "Bestand des Shops",       "datei"),
    ("sync",      SP[1], Y2,    "dienst",  "Lagerabgleich",      "Schnittstelle /api/sync", "pfeil"),
    ("betreiber", SP[0], Y3,    "akteur",  "Betreiber",          "Eigener Zugang",          "person"),
    ("passwort",  SP[1], Y3,    "betrieb", "Admin-Anmeldung",    "Nicht über den Chat", "schluessel"),
    ("anmeldung", SP[2], Y3,    "betrieb", "Anmeldedienst", "30 Minuten gültig",  "uhr"),
    ("sales",     SP[3], Y3,    "sperre",  "Verkaufsdaten",      "Tabelle sales",           "db"),
]
K = {k[0]: k for k in KAESTEN}

# von, nach, Beschriftung, Gasse ("spalte" / "rand" / Nummer), Art
KANTEN = [
    ("kunde", "widget", "", 1, "akteur"),
    ("widget", "regeln", "Anfrage", 2, "front"),
    ("regeln", "verstehen", "", "spalte", "dienst"),
    ("verstehen", "suchen", "", "spalte", "dienst"),
    ("suchen", "antwort", "", "spalte", "dienst"),
    ("verstehen", "parts", "Katalog", 3, "daten"),
    ("suchen", "hnsw", "Abstand", 3, "daten"),
    ("antwort", "protokoll", "Vorgang", 3, "daten"),
    ("lager", "sync", "CSV", 1, "akteur"),
    ("sync", "parts", "täglich", "rand", "daten"),
    ("betreiber", "passwort", "", 1, "betrieb"),
    ("passwort", "anmeldung", "separat", 2, "betrieb"),
    ("anmeldung", "sales", "intern", 3, "sperre"),
]


# --- Schriftbreite --------------------------------------------------
# Inter/Segoe/Arial: mittlere Zeichenbreite als Anteil der Schriftgroesse.
# Grosszuegig angesetzt, damit die Pruefung eher zu frueh als zu spaet
# anschlaegt.
# Nachgemessen an DejaVu Sans, der Schrift, mit der die PNG-Fassung
# gesetzt wird. Inter und Segoe UI sind schmaler, also ist der Wert die
# obere Schranke - was hier passt, passt ueberall.
BREIT_FETT = 0.63
BREIT_NORMAL = 0.56
T_GROSS, T_KLEIN = 15.5, 12.8


def textbreite(text: str, groesse: float, fett: bool = False) -> float:
    return len(text) * groesse * (BREIT_FETT if fett else BREIT_NORMAL)


# --- Sinnbilder -----------------------------------------------------
def sinnbild(name: str, farbe: str) -> str:
    """Flache Strichzeichnungen, 20x20, in der Farbe der Art."""
    s = (f'stroke="{farbe}" stroke-width="1.8" fill="none" '
         f'stroke-linecap="round" stroke-linejoin="round"')
    return {
        "person": f'<circle cx="10" cy="7" r="3.6" {s}/>'
                  f'<path d="M3 18c0-3.6 3.1-6.2 7-6.2s7 2.6 7 6.2" {s}/>',
        "fenster": f'<rect x="2" y="3.5" width="16" height="13" rx="2.6" {s}/>'
                   f'<path d="M2 8h16M5.5 11.6h6" {s}/>',
        "schild": f'<path d="M10 2.2 16.6 5.2v5.6c0 3.4-2.7 5.8-6.6 7-3.9-1.2-6.6-3.6-6.6-7V5.2z" {s}/>'
                  f'<path d="M7.3 10.3 9.3 12.3l3.6-4" {s}/>',
        "lupe": f'<circle cx="8.6" cy="8.6" r="5.6" {s}/><path d="M12.8 12.8 17.4 17.4" {s}/>',
        "netz": f'<circle cx="5" cy="5.4" r="2.2" {s}/><circle cx="15" cy="5.4" r="2.2" {s}/>'
                f'<circle cx="10" cy="15" r="2.2" {s}/>'
                f'<path d="M6.6 7.1 9 12.9M13.4 7.1 11 12.9M7.2 5.4h5.6" {s}/>',
        "sprech": f'<path d="M2.4 5.2a2.6 2.6 0 0 1 2.6-2.6h10a2.6 2.6 0 0 1 2.6 2.6v6.2'
                  f'a2.6 2.6 0 0 1-2.6 2.6H8.4L4 17.6v-3.6a2.6 2.6 0 0 1-1.6-2.6z" {s}/>',
        "db": f'<ellipse cx="10" cy="5" rx="7" ry="2.7" {s}/>'
              f'<path d="M3 5v10c0 1.5 3.1 2.7 7 2.7s7-1.2 7-2.7V5" {s}/>'
              f'<path d="M3 10c0 1.5 3.1 2.7 7 2.7s7-1.2 7-2.7" {s}/>',
        "index": f'<path d="M2.6 16 7 9.4l4.2 3.6L17.4 4" {s}/>'
                 f'<circle cx="7" cy="9.4" r="1.5" {s}/><circle cx="11.2" cy="13" r="1.5" {s}/>',
        "liste": f'<path d="M3.4 5h13.2M3.4 10h13.2M3.4 15h8.6" {s}/>',
        "datei": f'<path d="M4.4 2.2h7L16.6 7.4v10.4a1.4 1.4 0 0 1-1.4 1.4H4.4'
                 f'A1.4 1.4 0 0 1 3 17.8V3.6a1.4 1.4 0 0 1 1.4-1.4z" {s}/>'
                 f'<path d="M11.4 2.2v5.2h5.2" {s}/>',
        "pfeil": f'<path d="M2.6 10h13.4" {s}/><path d="M11.6 5.6 16 10l-4.4 4.4" {s}/>',
        "schluessel": f'<circle cx="6.6" cy="10" r="4.2" {s}/>'
                      f'<path d="M10.8 10h7M15.4 10v3.4M12.9 10v2.6" {s}/>',
        "uhr": f'<circle cx="10" cy="10" r="7.4" {s}/><path d="M10 5.6V10l3 2" {s}/>',
    }.get(name, "")


# --- Wege -----------------------------------------------------------
RAD = 14


def _weg(x1, y1, gasse_x, y2, x2) -> str:
    """Rechtwinklig: waagerecht heraus, senkrecht durch die freie Gasse,
    waagerecht hinein. In der Gasse steht per Aufbau kein Kasten, also
    kann keine Linie ueber einen Kasten laufen."""
    if abs(y1 - y2) < 2:
        return f"M{x1} {y1} L{x2} {y2}"
    runter = 1 if y2 > y1 else -1
    hin = 1 if gasse_x > x1 else -1
    raus = 1 if x2 > gasse_x else -1
    r = min(RAD, abs(y2 - y1) / 2, abs(gasse_x - x1), abs(x2 - gasse_x))
    return (f"M{x1} {y1} L{gasse_x - hin*r} {y1} "
            f"Q{gasse_x} {y1}, {gasse_x} {y1 + runter*r} "
            f"L{gasse_x} {y2 - runter*r} "
            f"Q{gasse_x} {y2}, {gasse_x + raus*r} {y2} L{x2} {y2}")


def kantenweg(von: str, nach: str, gasse):
    a, b = K[von], K[nach]
    if gasse == "spalte":
        x1, y1 = a[1] + BR / 2, a[2] + KH
        x2, y2 = b[1] + BR / 2, b[2]
        return f"M{x1} {y1} L{x2} {y2-10}", x1, (y1 + y2) / 2
    if gasse == "rand":
        x1, y1 = a[1] + BR, a[2] + KH / 2
        x2, y2 = b[1] + BR, b[2] + KH / 2
        return _weg(x1, y1, BREITE - 42, y2, x2 + 10), (x1 + BREITE - 42) / 2, y1 - 15
    x1, y1 = a[1] + BR, a[2] + KH / 2
    x2, y2 = b[1], b[2] + KH / 2
    return _weg(x1, y1, GASSE[gasse], y2, x2 - 10), GASSE[gasse], (y1 + y2) / 2


def tint(hexfarbe: str, anteil: float) -> str:
    """Farbe auf Weiss aufhellen - ergibt die zarten Felder."""
    r, g, b = (int(hexfarbe[i:i + 2], 16) for i in (1, 3, 5))
    r, g, b = (round(c + (255 - c) * (1 - anteil)) for c in (r, g, b))
    return f"#{r:02X}{g:02X}{b:02X}"


def karte_svg(k) -> str:
    kennung, x, y, art, titel, zweite, bild = k
    farbe = ART[art]
    t = [f'<g class="tt-karte" data-kennung="{kennung}" tabindex="0" '
         f'style="--rand:{farbe}">']
    t.append(f'<rect class="tt-rahmen" x="{x}" y="{y}" width="{BR}" height="{KH}" '
             f'rx="12" fill="#FFFFFF" stroke="{farbe}" stroke-width="1.7"/>')
    bx, by = x + 18, y + KH / 2 - 18
    t.append(f'<rect x="{bx}" y="{by}" width="36" height="36" rx="10" '
             f'fill="{tint(farbe, .14)}"/>')
    t.append(f'<g transform="translate({bx+8},{by+8})">{sinnbild(bild, farbe)}</g>')
    tx = bx + 46
    t.append(f'<text x="{tx}" y="{y+30}" font-family="{SANS}" font-size="{T_GROSS}" '
             f'font-weight="700" fill="{TINTE}">{html.escape(titel)}</text>')
    t.append(f'<text x="{tx}" y="{y+50}" font-family="{SANS}" font-size="{T_KLEIN}" '
             f'fill="{GRAU}">{html.escape(zweite)}</text>')
    t.append("</g>")
    return "\n".join(t)


def flaeche_svg(bereich, beschriftung: str, schluessel: str) -> str:
    oben, unten = bereich
    fuell, _rand, akzent = GRUPPE[schluessel]
    x, b = 56, BREITE - 112
    t = [f'<rect x="{x}" y="{oben}" width="{b}" height="{unten-oben}" rx="16" '
         f'fill="{fuell}"/>']
    breite = len(beschriftung) * (12.5 * BREIT_FETT + 1.1) + 34
    t.append(f'<rect x="{x+20}" y="{oben-13}" width="{breite:.0f}" height="26" rx="13" '
             f'fill="{akzent}"/>')
    t.append(f'<text x="{x+20+breite/2:.0f}" y="{oben}" font-family="{SANS}" '
             f'font-size="12.5" font-weight="700" fill="#FFFFFF" letter-spacing="1.1" '
             f'text-anchor="middle" dominant-baseline="central">{beschriftung}</text>')
    return "\n".join(t)


def logo_daten() -> str:
    """Logo als Datenadresse einbetten, damit das SVG fuer sich steht."""
    pfad = WURZEL / "docs" / "assets" / "logo-teilethuns.png"
    roh = base64.b64encode(pfad.read_bytes()).decode()
    return f"data:image/png;base64,{roh}"


STIL = """
  .tt-rahmen{transition:stroke-width .18s ease, filter .18s ease}
  .tt-karte:hover .tt-rahmen, .tt-karte:focus-visible .tt-rahmen{
    stroke-width:2.6;filter:drop-shadow(0 2px 8px var(--rand))}
  .tt-karte{cursor:default}
  /* Laufende Strichlinie: zeigt die Richtung, auch ohne Pfeilspitze */
  .tt-fluss{stroke-dasharray:10 160;stroke-dashoffset:170;
    animation:tt-fliessen 3.6s linear infinite}
  @keyframes tt-fliessen{to{stroke-dashoffset:0}}
  @media (prefers-reduced-motion:reduce){
    .tt-fluss{animation:none;stroke-dasharray:none;opacity:0}
  }
"""


def diagramm() -> str:
    t = [f'<svg xmlns="http://www.w3.org/2000/svg" '
         f'xmlns:xlink="http://www.w3.org/1999/xlink" '
         f'viewBox="0 0 {BREITE} {HOEHE}" width="{BREITE}" height="{HOEHE}" '
         f'role="img" aria-label="Aufbau des Auskunftshelfers von Teile Thuns">']
    t.append("<defs>")
    for farbe in set(ART.values()):
        t.append(f'<marker id="spitze-{farbe.lstrip("#")}" viewBox="0 0 10 10" '
                 f'refX="9" refY="5" markerWidth="6.5" markerHeight="6.5" '
                 f'orient="auto"><path d="M0 .6 10 5 0 9.4z" fill="{farbe}"/></marker>')
    t.append(f"<style>{STIL}</style>")
    t.append("</defs>")

    t.append(f'<rect width="{BREITE}" height="{HOEHE}" fill="#FFFFFF"/>')

    # Kopf: Logo links, Ueberschrift mittig, darunter eine Zeile in Signalfarbe
    t.append(f'<image x="56" y="30" width="211" height="56" '
             f'xlink:href="{logo_daten()}" href="{logo_daten()}"/>')
    t.append(f'<text x="{BREITE/2}" y="62" font-family="{SANS}" font-size="38" '
             f'font-weight="800" fill="{TINTE}" text-anchor="middle">{TITEL}</text>')
    t.append(f'<text x="{BREITE/2}" y="98" font-family="{SANS}" font-size="20" '
             f'font-weight="600" fill="{ORANGE}" text-anchor="middle">{UNTER}</text>')

    for bereich, beschriftung, schluessel in FLAECHEN:
        t.append(flaeche_svg(bereich, beschriftung, schluessel))

    for nr, (von, nach, text, gasse, art) in enumerate(KANTEN):
        d, bx, by = kantenweg(von, nach, gasse)
        farbe = ART[art]
        t.append(f'<path d="{d}" fill="none" stroke="{farbe}" stroke-width="1.7" '
                 f'opacity=".75" marker-end="url(#spitze-{farbe.lstrip("#")})"/>')
        t.append(f'<path class="tt-fluss" d="{d}" fill="none" stroke="{farbe}" '
                 f'stroke-width="2.6" stroke-linecap="round" '
                 f'style="animation-delay:{nr*0.26:.2f}s"/>')
        if text:
            b = textbreite(text, 12.5) + 20
            t.append(f'<rect x="{bx-b/2:.1f}" y="{by-11:.1f}" width="{b:.1f}" '
                     f'height="22" rx="11" fill="#FFFFFF" stroke="{farbe}" '
                     f'stroke-width="1.1"/>')
            t.append(f'<text x="{bx:.1f}" y="{by:.1f}" font-family="{SANS}" '
                     f'font-size="12.5" font-weight="600" fill="{farbe}" '
                     f'text-anchor="middle" dominant-baseline="central">'
                     f'{html.escape(text)}</text>')

    for k in KAESTEN:
        t.append(karte_svg(k))
    t.append("</svg>")
    return "\n".join(t)


def pruefen() -> list[str]:
    """Rechnet nach, bevor geschrieben wird."""
    maengel: list[str] = []
    platz = BR - 18 - 36 - 10 - 12          # Rand, Sinnbildfeld, Abstand, Rand
    for _kennung, x, y, _art, titel, zweite, _bild in KAESTEN:
        if textbreite(titel, T_GROSS, True) > platz:
            maengel.append(f"Titel {titel!r} passt nicht in den Kasten")
        if textbreite(zweite, T_KLEIN) > platz:
            maengel.append(f"Zweite Zeile {zweite!r} passt nicht in den Kasten")
        if x < 20 or x + BR > BREITE - 20 or y + KH > HOEHE - 20:
            maengel.append(f"{titel!r} ragt aus dem Bild")

    for i, a in enumerate(KAESTEN):
        for b in KAESTEN[i + 1:]:
            if (a[1] < b[1] + BR and b[1] < a[1] + BR
                    and a[2] < b[2] + KH and b[2] < a[2] + KH):
                maengel.append(f"{a[0]} und {b[0]} ueberdecken sich")

    for _von, _nach, text, gasse, _art in KANTEN:
        if text and gasse in GASSE:
            b = textbreite(text, 12.5) + 20
            if b > GASSENBREITE:
                maengel.append(
                    f"Beschriftung {text!r} ist {b:.0f} px breit, "
                    f"die freie Gasse nur {GASSENBREITE} px")
    return maengel


SEITE = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Teile Thuns – Aufbau des Auskunftshelfers</title>
<style>
  body{margin:0;padding:40px 20px;background:#F4F7FA;
    font-family:Inter,Segoe UI,system-ui,-apple-system,Roboto,Arial,sans-serif;color:#0E2C4F}
  main{max-width:1440px;margin:0 auto}
  p.unter{color:#64809B;margin:0 0 22px;font-size:15px}
  .bild{background:#fff;border:1px solid #DCE6F0;border-radius:18px;padding:14px;
    box-shadow:0 10px 30px rgba(14,44,79,.08)}
  svg{width:100%;height:auto;display:block}
  p.hinweis{color:#8AA3BA;font-size:13px;margin-top:20px}
  code{background:#EAF1F8;padding:2px 6px;border-radius:5px}
</style>
</head>
<body>
<main>
  <p class="unter">Mit der Maus über eine Karte fahren, um sie hervorzuheben.
  Die Pfeile laufen in Flussrichtung.</p>
  <div class="bild">__SVG__</div>
  <p class="hinweis">Dieses Schaubild wird aus <code>bench/architektur.py</code> erzeugt.</p>
</main>
</body>
</html>
"""


def main() -> int:
    maengel = pruefen()
    if maengel:
        print("Das Schaubild wurde NICHT geschrieben:")
        for m in maengel:
            print("  -", m)
        return 1

    ziel = WURZEL / "docs" / "assets"
    ziel.mkdir(parents=True, exist_ok=True)
    svg = diagramm()
    (ziel / "architektur.svg").write_text(svg, encoding="utf-8")
    (WURZEL / "docs" / "architektur.html").write_text(
        SEITE.replace("__SVG__", svg), encoding="utf-8")
    print("geschrieben:", ziel / "architektur.svg")
    print("geschrieben:", WURZEL / "docs" / "architektur.html")

    try:
        import cairosvg

        cairosvg.svg2png(url=str(ziel / "architektur.svg"),
                         write_to=str(ziel / "architektur.png"), output_width=1800)
        print("geschrieben:", ziel / "architektur.png")
    except ImportError:
        print("Hinweis: cairosvg fehlt - ohne es gibt es keine Bildfassung")
    return 0


if __name__ == "__main__":
    sys.exit(main())
