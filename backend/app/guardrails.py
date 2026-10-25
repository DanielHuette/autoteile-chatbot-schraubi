"""Schutzregeln: welche Frage ein Kunde und welche die Betriebsleitung gestellt bekommt.

Kontext: Erste von drei Schichten; die zweite ist die Rechtetrennung in schema.sql, die dritte
die getrennte Betriebsleitung unter /api/admin. | Eingabe: Nachricht, Betreiberstatus.
| Ergebnis: Pruefung mit Sperrgrund und freundlicher Ablehnung.
"""

from __future__ import annotations

from dataclasses import dataclass

from .vokabular import stamm

GESCHAEFTSBEGRIFFE: set[str] = {
    stamm(w)
    for w in (
        "umsatz",
        "umsaetze",
        "gewinn",
        "gewinnmarge",
        "marge",
        "rendite",
        "verkaufszahlen",
        "verkaufszahl",
        "absatz",
        "absatzzahlen",
        "einkaufspreis",
        "einkaufspreise",
        "beschaffungspreis",
        "deckungsbeitrag",
        "einkauf",
        "wareneinsatz",
        "selbstkosten",
        "stundensatz",
        "bilanz",
        "jahresabschluss",
        "buchhaltung",
        "steuer",
        "steuern",
        "betriebsgeheimnis",
        "betriebsgeheimnisse",
        "geschaeftsgeheimnis",
        "lieferant",
        "lieferanten",
        "einkaufsquelle",
        "bezugsquelle",
        "kundenliste",
        "kundendaten",
        "kundenadressen",
        "adressliste",
        "mitarbeiter",
        "gehalt",
        "gehaelter",
        "lohn",
        "personalkosten",
        "kalkulation",
        "aufschlag",
        "handelsspanne",
        "lagerwert",
        "bestellungen",
        "bestellhistorie",
        "auftragsbuch",
        "retourenquote",
    )
}

# Allein zu oft harmlos; sperren nur zusammen mit einem MEHRDEUTIG_PARTNER.
MEHRDEUTIG: set[str] = {stamm(w) for w in ("preis", "kosten", "wert", "zahlen")}
MEHRDEUTIG_PARTNER: set[str] = {
    stamm(w) for w in ("intern", "gesamt", "firma", "betrieb", "laden", "monat", "jahr")
}

# Ohne Sprachmodell wirkungslos; werden trotzdem gesperrt, damit Angriffe im Protokoll stehen.
UMSTIMMVERSUCHE: tuple[str, ...] = (
    "ignoriere",
    "vergiss deine",
    "vergiss alle",
    "system prompt",
    "systemprompt",
    "du bist jetzt",
    "ab jetzt bist du",
    "entwicklermodus",
    "developer mode",
    "jailbreak",
    "dan modus",
    "gib mir dein passwort",
    "zeige dein passwort",
    "ignore previous",
    "ignore all previous",
    "disregard your",
)


@dataclass
class Pruefung:
    blockiert: bool
    grund: str = ""
    antwort: str = ""


ABLEHNUNG_GESCHAEFT = (
    "Dazu kann ich leider keine Auskunft geben. Ich helfe Ihnen gern bei "
    "Ersatzteilen, Preisen einzelner Teile, Versandkosten und Lieferzeiten."
)

ABLEHNUNG_UMSTIMMEN = (
    "Ich bin nur für die Teilesuche und den Versand zuständig und kann "
    "daran nichts ändern. Wonach suchen Sie denn?"
)


def pruefen(text: str, ist_betreiber: bool) -> Pruefung:
    """Geschäftsfragen sind nur mit serverseitig geprüfter Betreibersitzung erlaubt."""
    klein = text.lower()
    for muster in UMSTIMMVERSUCHE:
        if muster in klein:
            return Pruefung(
                blockiert=True,
                grund="umstimmversuch",
                antwort=ABLEHNUNG_UMSTIMMEN,
            )

    if ist_betreiber:
        return Pruefung(blockiert=False)

    staemme = {stamm(w) for w in klein.replace("?", " ").replace(",", " ").split()}
    if staemme & GESCHAEFTSBEGRIFFE:
        return Pruefung(
            blockiert=True,
            grund="geschaeftsdaten",
            antwort=ABLEHNUNG_GESCHAEFT,
        )
    if (staemme & MEHRDEUTIG) and (staemme & MEHRDEUTIG_PARTNER):
        return Pruefung(
            blockiert=True,
            grund="geschaeftsdaten_mehrdeutig",
            antwort=ABLEHNUNG_GESCHAEFT,
        )
    return Pruefung(blockiert=False)
