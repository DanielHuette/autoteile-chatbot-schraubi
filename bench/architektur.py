#!/usr/bin/env python3
"""Erzeugt das Architekturschaubild als SVG.

Zwei Dinge, die ein Schaubild erst brauchbar machen:

* Die Kaesten stehen VERSETZT, nicht in Reih und Glied. Das Auge folgt
  dann dem Weg statt einer Tabelle.
* Jede Kante bewegt sich in Flussrichtung (laufende Strichlinie), und
  jeder Kasten leuchtet auf, wenn die Maus darueber faehrt.

Die Bewegung laeuft auch in der Projektbeschreibung auf GitHub, weil
sie im SVG selbst steckt. Das Leuchten bei Mauskontakt braucht dagegen
eine Seite, die das SVG einbettet statt es als Bild zu laden - deshalb
erzeugt dieses Skript zusaetzlich docs/architektur.html.

Aufruf:   python bench/architektur.py
"""
from __future__ import annotations

import html
import pathlib
import sys

WURZEL = pathlib.Path(__file__).resolve().parent.parent

# Markenfarben, aus der Logodatei gemessen.
BLAU = "#3575A8"
BLAU_HELL = "#5189B8"
BLAU_TIEF = "#2C5078"
GRUND = "#0E2135"
GRUND_2 = "#132B43"
RASTER = "#1D3C5A"
TEXT = "#EAF2F9"
TEXT_LEISE = "#9DBAD3"

# Kategorie -> (Randfarbe, Fuellung, Beschriftung)
ARTEN = {
    "aussen":   ("#7E9AB5", "rgba(126,154,181,.14)", "von aussen"),
    "widget":   (BLAU_HELL, "rgba(81,137,184,.16)", "im Browser"),
    "server":   ("#4FB3C9", "rgba(79,179,201,.14)", "Server"),
    "daten":    ("#3FAE7A", "rgba(63,174,122,.14)", "Datenbank"),
    "sperre":   ("#D2605A", "rgba(210,96,90,.15)", "gesperrt"),
    "betrieb":  ("#E8A33B", "rgba(232,163,59,.15)", "Betriebsleitung"),
}


class Kasten:
    def __init__(self, kennung, x, y, b, h, art, titel, zeilen, zeichen=""):
        self.kennung, self.x, self.y, self.b, self.h = kennung, x, y, b, h
        self.art, self.titel, self.zeilen, self.zeichen = art, titel, zeilen, zeichen

    @property
    def mitte_rechts(self): return (self.x + self.b, self.y + self.h / 2)
    @property
    def mitte_links(self): return (self.x, self.y + self.h / 2)
    @property
    def mitte_oben(self): return (self.x + self.b / 2, self.y)
    @property
    def mitte_unten(self): return (self.x + self.b / 2, self.y + self.h)


# --- Aufbau ---------------------------------------------------------
# Drei Zonen untereinander, damit sich die Wege nicht kreuzen:
#   oben   der Kundenweg,
#   Mitte  der taegliche Lagerabgleich,
#   unten  die Betriebsleitung.
# Zwischen den Spalten bleibt eine freie Bahn. Alle Kanten laufen
# rechtwinklig durch diese Bahnen - dadurch kann keine Linie ueber
# einen Kasten hinweglaufen.
S1, S2, S3, S4 = 36, 340, 644, 948
BR, BR4 = 212, 212
BAHN = {1: (S1 + BR + S2) / 2, 2: (S2 + BR + S3) / 2, 3: (S3 + BR + S4) / 2}
KOPF = 104

Z_KUNDE = KOPF + 8      # Zone 1: Kundenweg
Z_SYNC = KOPF + 456     # Zone 2: taeglicher Abgleich
Z_BETRIEB = KOPF + 580  # Zone 3: Betriebsleitung

KAESTEN = [
    # ---- Zone 1: der Weg einer Kundenfrage ----
    Kasten("kunde", S1, Z_KUNDE + 36, BR, 82, "aussen", "Kunde, 72 Jahre",
           ["keine Teilenummer,", "beschreibt den Schaden"], "person"),
    Kasten("widget", S2, Z_KUNDE, BR, 98, "widget", "Widget \u00bbSchraubi\u00ab",
           ["ein <script>-Tag", "Klick-Interview", "17 px, Kn\u00f6pfe ab 48 px"], "fenster"),
    Kasten("regeln", S3, Z_KUNDE + 36, BR, 72, "sperre", "Schutzregeln",
           ["Umsatz? Marge?", "\u2192 blockiert"], "schild"),
    Kasten("verstehen", S3, Z_KUNDE + 136, BR, 88, "server", "Verstehen",
           ["Tippfehler \u2192 Fachbegriff", "Bauteil, Marke, Modell,",
            "Seite \u2013 aus dem Bestand"], "lupe"),
    Kasten("suchen", S3, Z_KUNDE + 256, BR, 94, "server", "Suchen, dreifach",
           ["Vektor, Volltext,", "Trigramm \u2013 per RRF", "Mindest\u00e4hnlichkeit 0,55"], "lupe"),
    Kasten("antwort", S3, Z_KUNDE + 382, BR, 72, "server", "Antworten",
           ["feste Vorlagen,", "Werte aus der Datenbank"], "sprech"),
    Kasten("parts", S4, Z_KUNDE + 128, BR4, 106, "daten", "Tabelle parts",
           ["Titel, Preis, Bestand,", "eBay-Kennzeichen,",
            "embedding vector(384),", "fts tsvector"], "db"),
    Kasten("hnsw", S4, Z_KUNDE + 268, BR4, 58, "daten", "HNSW-Index",
           ["pgvector, Kosinus"], "index"),
    Kasten("protokoll", S4, Z_KUNDE + 368, BR4, 84, "daten", "Protokolle",
           ["ohne Namen, ohne IP", "90 Tage, dann gel\u00f6scht", "Suchen ohne Treffer"], "liste"),

    # ---- Zone 2: der taegliche Lagerabgleich ----
    Kasten("lager", S1, Z_SYNC + 6, BR, 64, "aussen", "Lagerprogramm",
           ["t\u00e4glich, CSV oder JSON"], "datei"),
    Kasten("sync", S2, Z_SYNC, BR, 76, "server", "/api/sync",
           ["pr\u00fcft jede Zeile,", "bettet Ge\u00e4ndertes ein"], "pfeil"),

    # ---- Zone 3: die Betriebsleitung ----
    Kasten("betreiber", S1, Z_BETRIEB + 6, BR, 64, "betrieb", "Shop-Betreiber",
           ["meldet sich getrennt an"], "person"),
    Kasten("passwort", S2, Z_BETRIEB, BR, 76, "betrieb", "Eigenes Passwortfeld",
           ["nicht \u00fcber den Chat,", "nie im Verlauf"], "schluessel"),
    Kasten("anmeldung", S3, Z_BETRIEB, BR, 76, "betrieb", "Anmeldung",
           ["scrypt, HMAC, Sperre", "30 Minuten g\u00fcltig"], "schluessel"),
    Kasten("sales", S4, Z_BETRIEB, BR4, 76, "sperre", "Tabelle sales",
           ["Rolle teilethuns_chat", "hat KEIN Leserecht"], "db"),
]
NACH_KENNUNG = {k.kennung: k for k in KAESTEN}

# (von, nach, Beschriftung, Bahnnummer oder "spalte", Farbe)
# Die Bahnnummer sagt, durch welche freie Spalte die Kante laeuft.
# "spalte" heisst: senkrecht innerhalb derselben Spalte.
KANTEN = [
    ("kunde", "widget", "", 1, BLAU_HELL),
    ("widget", "regeln", "Frage", 2, BLAU_HELL),
    ("regeln", "verstehen", "", "spalte", "#4FB3C9"),
    ("verstehen", "suchen", "", "spalte", "#4FB3C9"),
    ("suchen", "antwort", "", "spalte", "#4FB3C9"),
    ("verstehen", "parts", "Katalog", 3, "#3FAE7A"),
    ("suchen", "hnsw", "Abstand", 3, "#3FAE7A"),
    ("antwort", "protokoll", "Vorgang", 3, "#3FAE7A"),
    ("lager", "sync", "", 1, "#7E9AB5"),
    ("sync", "parts", "t\u00e4glich", "rand", "#3FAE7A"),
    ("betreiber", "passwort", "", 1, "#E8A33B"),
    ("passwort", "anmeldung", "eigener Weg", 2, "#E8A33B"),
    ("anmeldung", "sales", "angemeldet", 3, "#E8A33B"),
]

BREITE, HOEHE = 1244, 840


def zeichensatz(name: str, farbe: str) -> str:
    """Kleine Sinnbilder. Bewusst schlicht: sie sollen den Kasten
    einordnen, nicht mit ihm konkurrieren."""
    s = f'stroke="{farbe}" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"'
    formen = {
        "person": f'<circle cx="7" cy="5" r="3" {s}/><path d="M1.5 14c0-3 2.5-5 5.5-5s5.5 2 5.5 5" {s}/>',
        "fenster": f'<rect x="1" y="2.5" width="12" height="10" rx="2" {s}/><path d="M1 6h12M4 9h5" {s}/>',
        "schild": f'<path d="M7 1.5 12.5 4v4.5c0 2.6-2.2 4.6-5.5 5.5-3.3-.9-5.5-2.9-5.5-5.5V4z" {s}/><path d="M4.8 7.4 6.4 9l3-3.2" {s}/>',
        "lupe": f'<circle cx="6.2" cy="6.2" r="4.4" {s}/><path d="M9.6 9.6 13 13" {s}/>',
        "sprech": f'<path d="M1.5 3.5a2 2 0 0 1 2-2h7a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2H6l-3.2 2.6V10.5a2 2 0 0 1-1.3-2z" {s}/>',
        "db": f'<ellipse cx="7" cy="3.4" rx="5.2" ry="2" {s}/><path d="M1.8 3.4v7.2c0 1.1 2.3 2 5.2 2s5.2-.9 5.2-2V3.4" {s}/><path d="M1.8 7c0 1.1 2.3 2 5.2 2s5.2-.9 5.2-2" {s}/>',
        "index": f'<path d="M2 11.5 5 6.5l3 2.6 4-6.6" {s}/><circle cx="5" cy="6.5" r="1.1" {s}/><circle cx="8" cy="9.1" r="1.1" {s}/>',
        "schluessel": f'<circle cx="4.6" cy="7" r="3.1" {s}/><path d="M7.7 7H13M11 7v2.6M9.3 7v2" {s}/>',
        "datei": f'<path d="M3 1.5h5l3.2 3.2v8.3a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1v-10.5a1 1 0 0 1 1-1z" {s}/><path d="M8 1.5v3.4h3.2" {s}/>',
        "pfeil": f'<path d="M1.5 7h10" {s}/><path d="M8.2 3.8 11.5 7l-3.3 3.2" {s}/>',
        "liste": f'<path d="M2.5 3.5h9M2.5 7h9M2.5 10.5h6" {s}/>',
    }
    return formen.get(name, "")


def kasten_svg(k: Kasten) -> str:
    rand, fuell, _ = ARTEN[k.art]
    t = [f'<g class="tt-knoten tt-art-{k.art}" data-kennung="{k.kennung}" tabindex="0" '
         f'style="--rand:{rand};--fuell:{fuell}">']
    t.append(f'<rect class="tt-kasten" x="{k.x}" y="{k.y}" width="{k.b}" height="{k.h}" rx="13"/>')
    # Farbstreifen links: ordnet den Kasten seiner Art zu, auch ohne Farbsehen
    t.append(f'<rect class="tt-streifen-b" x="{k.x}" y="{k.y+9}" width="4" '
             f'height="{k.h-18}" rx="2"/>')
    if k.zeichen:
        t.append(f'<g transform="translate({k.x+15},{k.y+13})">{zeichensatz(k.zeichen, rand)}</g>')
    t.append(f'<text class="tt-titel" x="{k.x+36}" y="{k.y+24}">{html.escape(k.titel)}</text>')
    for i, z in enumerate(k.zeilen):
        t.append(f'<text class="tt-zeile" x="{k.x+16}" y="{k.y+45+i*15}">{html.escape(z)}</text>')
    t.append("</g>")
    return "\n".join(t)


R = 12   # Eckenradius der Kantenfuehrung


def _weg(x1, y1, bahn_x, y2, x2) -> str:
    """Waagerecht heraus, senkrecht durch die Bahn, waagerecht hinein.

    Die beiden Ecken sind gerundet. Entscheidend ist, dass die gerade
    Strecke VOR der Rundung endet und NACH ihr weiterlaeuft - sonst
    entsteht ein Knick statt einer Kurve.
    """
    if abs(y1 - y2) < 2:
        return f"M{x1} {y1} L{x2} {y2}"
    runter = 1 if y2 > y1 else -1
    hin = 1 if bahn_x > x1 else -1
    raus = 1 if x2 > bahn_x else -1
    r = min(R, abs(y2 - y1) / 2, abs(bahn_x - x1), abs(x2 - bahn_x))
    return (
        f"M{x1} {y1} "
        f"L{bahn_x - hin*r} {y1} "
        f"Q{bahn_x} {y1}, {bahn_x} {y1 + runter*r} "
        f"L{bahn_x} {y2 - runter*r} "
        f"Q{bahn_x} {y2}, {bahn_x + raus*r} {y2} "
        f"L{x2} {y2}"
    )


def kante_svg(von: str, nach: str, beschriftung: str, bahn, farbe: str, nr: int) -> str:
    """Zeichnet eine Kante ausschliesslich rechtwinklig.

    Waagerecht aus dem Kasten heraus, senkrecht durch die freie Bahn
    zwischen zwei Spalten, waagerecht in den Zielkasten. Weil in dieser
    Bahn per Aufbau kein Kasten steht, kann keine Linie ueber einen
    Kasten hinweglaufen - mit Kurven war das nicht sicherzustellen.
    """
    a, b = NACH_KENNUNG[von], NACH_KENNUNG[nach]

    if bahn == "spalte":                       # senkrecht, gleiche Spalte
        x1, y1 = a.mitte_unten
        x2, y2 = b.mitte_oben
        d = f"M{x1} {y1} L{x2} {y2-8}"
        bx, by = x1 + 64, (y1 + y2) / 2 + 4

    elif bahn == "rand":                       # aussen herum, am rechten Rand hinauf
        x1, y1 = a.mitte_rechts
        x2, y2 = b.mitte_rechts
        d = _weg(x1, y1, BREITE - 30, y2, x2 + 8)
        bx, by = (x1 + BREITE - 30) / 2, y1 - 11

    else:                                      # durch die freie Bahn zwischen zwei Spalten
        x1, y1 = a.mitte_rechts
        x2, y2 = b.mitte_links
        d = _weg(x1, y1, BAHN[bahn], y2, x2 - 8)
        bx, by = BAHN[bahn], (y1 + y2) / 2

    t = [f'<g class="tt-kante" style="--kante:{farbe}">',
         f'<path class="tt-linie" d="{d}"/>',
         f'<path class="tt-fluss" d="{d}" style="animation-delay:{nr*0.24:.2f}s"/>',
         f'<path class="tt-spitze" d="{d}" marker-end="url(#spitze-{farbe.lstrip("#")})"/>']
    if beschriftung:
        breite = len(beschriftung) * 6.2 + 16
        t.append(f'<rect class="tt-kantenfeld" x="{bx-breite/2:.1f}" y="{by-9:.1f}" '
                 f'width="{breite:.1f}" height="18" rx="9"/>')
        t.append(f'<text class="tt-kantentext" x="{bx:.1f}" y="{by+3.5:.1f}">'
                 f'{html.escape(beschriftung)}</text>')
    t.append("</g>")
    return "\n".join(t)


STIL = """
  .tt-grund{fill:url(#verlauf)}
  .tt-kasten{fill:var(--fuell);stroke:var(--rand);stroke-width:1.5;
    transition:fill-opacity .18s ease, stroke-width .18s ease, filter .18s ease}
  .tt-streifen-b{fill:var(--rand);opacity:.85}
  .tt-titel{fill:#EAF2F9;font:700 14.5px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
  .tt-zeile{fill:#9DBAD3;font:400 12px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
  .tt-knoten{cursor:default}
  /* Leuchten bei Mauskontakt. Wirkt nur dort, wo das Schaubild in die
     Seite eingebettet ist - als Bild geladen bekommt es keine Mausereignisse. */
  .tt-knoten:hover .tt-kasten, .tt-knoten:focus-visible .tt-kasten{
    stroke-width:2.6;filter:drop-shadow(0 0 7px var(--rand));fill-opacity:1.6}
  .tt-knoten:hover .tt-titel{fill:#fff}
  .tt-knoten:hover .tt-zeile{fill:#CDE1F1}

  .tt-linie{stroke:var(--kante);stroke-width:1.5;fill:none;opacity:.32}
  .tt-spitze{stroke:none;fill:none}
  /* Laufende Strichlinie: zeigt die Richtung, auch ohne Pfeilspitze */
  .tt-fluss{stroke:var(--kante);stroke-width:2.1;fill:none;stroke-linecap:round;
    stroke-dasharray:9 150;stroke-dashoffset:159;opacity:.95;
    animation:tt-fliessen 3.4s linear infinite}
  @keyframes tt-fliessen{to{stroke-dashoffset:0}}
  .tt-kantenfeld{fill:#0E2135;stroke:var(--kante);stroke-width:.8;opacity:.94}
  .tt-kantentext{fill:#BBD3E6;font:600 10.5px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
    text-anchor:middle}
  .tt-kopfzeile{fill:#F4F9FD;font:800 20px system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif}
  .tt-unterzeile{fill:#9DBAD3;font:400 13px system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif}
  .tt-legende{fill:#9DBAD3;font:600 11.5px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
  @media (prefers-reduced-motion:reduce){
    .tt-fluss{animation:none;stroke-dasharray:none;stroke-dashoffset:0;opacity:.6}
  }
"""


def diagramm() -> str:
    t = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {BREITE} {HOEHE}" '
         f'width="{BREITE}" height="{HOEHE}" role="img" '
         f'aria-label="Aufbau des Auskunftshelfers von Teile Thuns">']
    t.append("<defs>")
    t.append(f'<linearGradient id="verlauf" x1="0" y1="0" x2="0.6" y2="1">'
             f'<stop offset="0" stop-color="{GRUND_2}"/><stop offset="1" stop-color="{GRUND}"/></linearGradient>')
    t.append('<pattern id="raster" width="34" height="34" patternUnits="userSpaceOnUse">'
             f'<path d="M34 0H0v34" fill="none" stroke="{RASTER}" stroke-width=".6" opacity=".5"/></pattern>')
    for farbe in {f for *_, f in KANTEN}:
        t.append(f'<marker id="spitze-{farbe.lstrip("#")}" viewBox="0 0 9 9" refX="8" refY="4.5" '
                 f'markerWidth="6" markerHeight="6" orient="auto">'
                 f'<path d="M0 0 9 4.5 0 9z" fill="{farbe}" opacity=".85"/></marker>')
    t.append(f"<style>{STIL}</style>")
    t.append("</defs>")

    t.append(f'<rect class="tt-grund" width="{BREITE}" height="{HOEHE}" rx="16"/>')
    t.append(f'<rect width="{BREITE}" height="{HOEHE}" rx="16" fill="url(#raster)"/>')

    t.append('<text class="tt-kopfzeile" x="34" y="40">Teile Thuns – so arbeitet der Auskunftshelfer</text>')
    t.append('<text class="tt-unterzeile" x="34" y="63">Zwei getrennte Wege durch dasselbe System. '
             'Der Kundenweg erreicht die Verkaufsdaten nicht – das verhindert die Datenbank, nicht nur der Code.</text>')

    # Zonen benennen, damit klar ist, dass es drei getrennte Ablaeufe sind
    for y, beschriftung in ((Z_KUNDE - 16, "WENN EIN KUNDE FRAGT"),
                            (Z_SYNC - 16, "JEDE NACHT: LAGERABGLEICH"),
                            (Z_BETRIEB - 16, "WENN DER BETREIBER ZAHLEN BRAUCHT")):
        t.append(f'<line x1="34" y1="{y}" x2="{BREITE-34}" y2="{y}" stroke="{RASTER}" '
                 f'stroke-width="1"/>')
        breite = len(beschriftung) * 6.4 + 20
        t.append(f'<rect x="34" y="{y-10}" width="{breite:.0f}" height="20" rx="10" '
                 f'fill="{GRUND}" stroke="{RASTER}" stroke-width="1"/>')
        t.append(f'<text x="{34+breite/2:.0f}" y="{y+4}" font-size="10.5" fill="{TEXT_LEISE}" '
                 f'font-weight="700" text-anchor="middle" letter-spacing="1" '
                 f'font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace">'
                 f'{beschriftung}</text>')

    for nr, (von, nach, b, r, f) in enumerate(KANTEN):
        t.append(kante_svg(von, nach, b, r, f, nr))
    for k in KAESTEN:
        t.append(kasten_svg(k))

    # Legende in einem eigenen Streifen, damit sie nichts ueberdeckt
    y = HOEHE - 24
    t.append(f'<line x1="34" y1="{HOEHE-52}" x2="{BREITE-34}" y2="{HOEHE-52}" '
             f'stroke="{RASTER}" stroke-width="1"/>')
    x = 34
    for _art, (rand, fuell, label) in ARTEN.items():
        t.append(f'<rect x="{x}" y="{y-9}" width="12" height="12" rx="3.5" fill="{fuell}" '
                 f'stroke="{rand}" stroke-width="1.4"/>')
        t.append(f'<text class="tt-legende" x="{x+18}" y="{y+1}">{html.escape(label)}</text>')
        x += 24 + len(label) * 7.1
    t.append("</svg>")
    return "\n".join(t)


SEITE = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Teile Thuns &ndash; Aufbau des Auskunftshelfers</title>
<style>
  body{margin:0;background:#0A1A2B;color:#EAF2F9;
       font:400 16px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;
       padding:26px 18px 60px}
  main{max-width:1060px;margin:0 auto}
  h1{font-size:24px;margin:0 0 6px}
  p.unter{color:#9DBAD3;margin:0 0 22px;font-size:15px}
  .rahmen{background:#0E2135;border:1px solid #1D3C5A;border-radius:18px;padding:10px;
          box-shadow:0 18px 50px rgba(0,0,0,.45)}
  .rahmen svg{width:100%;height:auto;display:block}
  .hinweis{margin-top:20px;color:#9DBAD3;font-size:14px;border-left:3px solid #3575A8;
           padding-left:14px}
  a{color:#7FB6DE}
</style>
</head>
<body>
<main>
  <h1>So arbeitet der Auskunftshelfer</h1>
  <p class="unter">Mit der Maus &uuml;ber einen Kasten fahren, um ihn hervorzuheben.
     Die Pfeile laufen in Flussrichtung.</p>
  <div class="rahmen">
__SVG__
  </div>
  <p class="hinweis">Dieses Schaubild wird aus <code>bench/architektur.py</code> erzeugt.
     &Auml;ndert sich der Aufbau, &auml;ndert sich das Bild &ndash; nicht umgekehrt.</p>
</main>
</body>
</html>
"""


def main() -> int:
    ziel = WURZEL / "docs" / "assets"
    ziel.mkdir(parents=True, exist_ok=True)
    svg = diagramm()
    (ziel / "architektur.svg").write_text(svg, encoding="utf-8")
    (WURZEL / "docs" / "architektur.html").write_text(
        SEITE.replace("__SVG__", svg), encoding="utf-8")
    print("geschrieben:", ziel / "architektur.svg")
    print("geschrieben:", WURZEL / "docs" / "architektur.html")

    # Bildfassung fuer Netzwerke ohne SVG-Anzeige (LinkedIn)
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
