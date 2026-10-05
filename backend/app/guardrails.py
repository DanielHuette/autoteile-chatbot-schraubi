"""Schutzregeln: welche Frage darf wer gestellt bekommen.

Grundsatz: Der Bot erzeugt KEINE freien Texte über Geschaeftszahlen.
Er kann Umsatzfragen also nicht versehentlich beantworten – es gibt
keinen Pfad vom Kundenchat zur Tabelle 'sales'. Diese Regeln hier sind
die erste Schicht: sie erkennen die Absicht und antworten freundlich
ablehnend, statt den Kunden ins Leere laufen zu lassen.

Zweite Schicht ist die Rechtetrennung in der Datenbank (schema.sql),
dritte Schicht die getrennte Betriebsleitung (/api/admin/*).
"""
from __future__ import annotations

from dataclasses import dataclass

from .vokabular import stamm

# Begriffe, die auf eine Frage nach Betriebsinterna hindeuten.
GESCHAEFTSBEGRIFFE: set[str] = {
    stamm(w)
    for w in (
        "umsatz", "umsaetze", "gewinn", "gewinnmarge", "marge", "rendite",
        "verkaufszahlen", "verkaufszahl", "absatz", "absatzzahlen",
        "einkaufspreis", "einkaufspreise", "beschaffungspreis", "deckungsbeitrag",
        "einkauf", "wareneinsatz", "selbstkosten", "stundensatz",
        "bilanz", "jahresabschluss", "buchhaltung", "steuer", "steuern",
        "betriebsgeheimnis", "betriebsgeheimnisse", "geschaeftsgeheimnis",
        "lieferant", "lieferanten", "einkaufsquelle", "bezugsquelle",
        "kundenliste", "kundendaten", "kundenadressen", "adressliste",
        "mitarbeiter", "gehalt", "gehaelter", "lohn", "personalkosten",
        "kalkulation", "aufschlag", "handelsspanne", "lagerwert",
        "bestellungen", "bestellhistorie", "auftragsbuch", "retourenquote",
    )
}

# Stichwoerter, die allein zu häufig harmlos vorkommen. Sie loesen nur
# aus, wenn ein zweiter Hinweis dazukommt.
MEHRDEUTIG: set[str] = {stamm(w) for w in ("preis", "kosten", "wert", "zahlen")}
MEHRDEUTIG_PARTNER: set[str] = {
    stamm(w) for w in ("intern", "gesamt", "firma", "betrieb", "laden", "monat", "jahr")
}

# Versuche, die Rolle zu wechseln oder Anweisungen zu überschreiben.
# Der Bot hat kein Sprachmodell, das sich umstimmen liesse – der
# Hinweis wird trotzdem protokolliert, damit Angriffe sichtbar werden.
UMSTIMMVERSUCHE: tuple[str, ...] = (
    "ignoriere", "vergiss deine", "vergiss alle", "system prompt", "systemprompt",
    "du bist jetzt", "ab jetzt bist du", "entwicklermodus", "developer mode",
    "jailbreak", "dan modus", "gib mir dein passwort", "zeige dein passwort",
    "ignore previous", "ignore all previous", "disregard your",
)


@dataclass
class Pruefung:
    blockiert: bool
    grund: str = ""
    antwort: str = ""
    protokoll_art: str = ""


ABLEHNUNG_GESCHAEFT = (
    "Dazu kann ich leider keine Auskunft geben. Ich helfe Ihnen gern bei "
    "Ersatzteilen, Preisen einzelner Teile, Versandkosten und Lieferzeiten."
)

ABLEHNUNG_UMSTIMMEN = (
    "Ich bin nur für die Teilesuche und den Versand zuständig und kann "
    "daran nichts ändern. Wonach suchen Sie denn?"
)


def pruefen(text: str, ist_betreiber: bool) -> Pruefung:
    """Prueft eine eingehende Nachricht.

    ist_betreiber=True nur bei gueltiger, serverseitig geprueften
    Betriebsleitungs-Sitzung. Dann sind Geschaeftsfragen erlaubt.
    """
    klein = text.lower()
    for muster in UMSTIMMVERSUCHE:
        if muster in klein:
            return Pruefung(
                blockiert=True,
                grund="umstimmversuch",
                antwort=ABLEHNUNG_UMSTIMMEN,
                protokoll_art="blockiert",
            )

    if ist_betreiber:
        return Pruefung(blockiert=False)

    staemme = {stamm(w) for w in klein.replace("?", " ").replace(",", " ").split()}
    if staemme & GESCHAEFTSBEGRIFFE:
        return Pruefung(
            blockiert=True,
            grund="geschaeftsdaten",
            antwort=ABLEHNUNG_GESCHAEFT,
            protokoll_art="blockiert",
        )
    if (staemme & MEHRDEUTIG) and (staemme & MEHRDEUTIG_PARTNER):
        return Pruefung(
            blockiert=True,
            grund="geschaeftsdaten_mehrdeutig",
            antwort=ABLEHNUNG_GESCHAEFT,
            protokoll_art="blockiert",
        )
    return Pruefung(blockiert=False)
