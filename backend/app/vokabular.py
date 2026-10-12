"""Laiensprache zu Fachbegriff: Umgangssprache, Lage, Baujahr, Wortstamm, Tippfehler.

Kontext: Bewusst als gepflegte Wortliste statt geraten, denn eine falsche Teileempfehlung
kostet Rückversand. | Eingabe: Kundentext. | Ergebnis: Um Fachbegriffe ergänzter Text,
erkannte Lage und erkanntes Baujahr.
"""

from __future__ import annotations

import difflib
import re

from .embeddings import normalisieren

# Mehrwortbegriffe zuerst, damit "rotes glas" nicht an "glas" haengen bleibt.
UMGANGSSPRACHE: list[tuple[str, str]] = [
    ("rotes glas", "rueckleuchte heckleuchte"),
    ("rotes licht", "rueckleuchte heckleuchte"),
    ("rote lampe", "rueckleuchte heckleuchte"),
    ("hinten licht", "rueckleuchte heckleuchte"),
    ("licht hinten", "rueckleuchte heckleuchte"),
    ("hinter lampe", "rueckleuchte heckleuchte"),
    ("ruecklicht", "rueckleuchte heckleuchte"),
    ("heckleuchte", "rueckleuchte heckleuchte"),
    ("bremslicht", "rueckleuchte bremsleuchte"),
    ("scheinwerfer", "scheinwerfer frontleuchte"),
    ("vorderlicht", "scheinwerfer frontleuchte"),
    ("vorder licht", "scheinwerfer frontleuchte"),
    ("vorne licht", "scheinwerfer frontleuchte"),
    ("licht vorne", "scheinwerfer frontleuchte"),
    ("frontlicht", "scheinwerfer frontleuchte"),
    ("blinker", "blinkleuchte fahrtrichtungsanzeiger"),
    ("winker", "blinkleuchte fahrtrichtungsanzeiger"),
    ("nebellampe", "nebelscheinwerfer"),
    ("nebellicht", "nebelscheinwerfer"),
    ("scheibenwischer", "wischerblatt wischarm"),
    ("wischer", "wischerblatt wischarm"),
    ("stossstange", "stossfaenger"),
    ("stosstange", "stossfaenger"),
    ("kotfluegel", "kotfluegel seitenteil"),
    ("motorhaube", "motorhaube fronthaube"),
    ("kofferraumdeckel", "heckklappe"),
    ("kofferraumklappe", "heckklappe"),
    ("hintere klappe", "heckklappe"),
    ("lichtmaschine", "generator lichtmaschine"),
    ("anlasser", "starter anlasser"),
    ("starter", "starter anlasser"),
    ("auspuff", "abgasanlage schalldaempfer"),
    ("auspufftopf", "schalldaempfer"),
    ("katalysator", "katalysator kat"),
    ("keilriemen", "keilrippenriemen"),
    ("zahnriemen", "zahnriemen steuerriemen"),
    ("wasserpumpe", "kuehlmittelpumpe wasserpumpe"),
    ("kuehler", "wasserkuehler kuehler"),
    ("luefter", "kuehlerluefter luefter"),
    ("bremsscheibe", "bremsscheibe"),
    ("bremsklotz", "bremsbelag bremsbacke"),
    ("bremsbelag", "bremsbelag"),
    ("handbremse", "handbremshebel feststellbremse"),
    ("stossdaempfer", "stossdaempfer federbein"),
    ("federbein", "federbein stossdaempfer"),
    ("querlenker", "querlenker lenker"),
    ("spurstange", "spurstange spurstangenkopf"),
    ("radlager", "radlager radnabe"),
    ("felge", "felge rad alufelge stahlfelge"),
    ("reifen", "reifen"),
    ("aussenspiegel", "aussenspiegel spiegel"),
    ("spiegel", "aussenspiegel spiegel"),
    ("seitenspiegel", "aussenspiegel spiegel"),
    ("ruecksitz", "rueckbank sitzbank"),
    ("fahrersitz", "sitz vordersitz"),
    ("lenkrad", "lenkrad"),
    ("armaturenbrett", "armaturenbrett instrumententafel"),
    ("tacho", "kombiinstrument tachometer"),
    ("tachometer", "kombiinstrument tachometer"),
    ("handschuhfach", "handschuhfach ablagefach"),
    ("tuergriff", "tuergriff griff"),
    ("fensterheber", "fensterheber fensterhebermotor"),
    ("tuerschloss", "tuerschloss schloss"),
    ("zuendschloss", "zuendschloss"),
    ("zuendkerze", "zuendkerze"),
    ("zuendspule", "zuendspule"),
    ("batterie", "starterbatterie batterie"),
    ("getriebe", "getriebe schaltgetriebe"),
    ("kupplung", "kupplung kupplungssatz"),
    ("antriebswelle", "antriebswelle gelenkwelle"),
    ("kardanwelle", "gelenkwelle kardanwelle"),
    ("tank", "kraftstoffbehaelter tank"),
    ("benzinpumpe", "kraftstoffpumpe"),
    ("dieselpumpe", "kraftstoffpumpe einspritzpumpe"),
    ("turbo", "turbolader"),
    ("turbolader", "turbolader"),
    ("luftfilter", "luftfilter"),
    ("innenraumfilter", "innenraumfilter pollenfilter"),
    ("pollenfilter", "innenraumfilter pollenfilter"),
    ("scheibe vorne", "windschutzscheibe frontscheibe"),
    ("windschutzscheibe", "windschutzscheibe frontscheibe"),
    ("heckscheibe", "heckscheibe"),
    ("seitenscheibe", "seitenscheibe tuerscheibe"),
    ("dachhimmel", "dachhimmel innenhimmel"),
    ("schiebedach", "schiebedach"),
    ("klimaanlage", "klimakompressor klimaanlage"),
    ("heizung", "heizungsgeblaese waermetauscher"),
    ("geblaese", "innenraumgeblaese geblaesemotor"),
    ("hupe", "signalhorn hupe"),
    ("radio", "autoradio radio"),
    ("navi", "navigationsgeraet navi"),
    ("steuergeraet", "steuergeraet motorsteuergeraet"),
    ("zentralverriegelung", "zentralverriegelung stellmotor"),
]

# In Deutschland sitzt der Fahrer links.
SEITEN: list[tuple[str, str]] = [
    ("fahrerseite", "links"),
    ("fahrerseitig", "links"),
    ("beifahrerseite", "rechts"),
    ("beifahrerseitig", "rechts"),
    ("linke seite", "links"),
    ("rechte seite", "rechts"),
    ("links", "links"),
    ("rechts", "rechts"),
    ("vorne", "vorne"),
    ("vorn", "vorne"),
    ("hinten", "hinten"),
    ("hinterer", "hinten"),
    ("hintere", "hinten"),
]

_ENDUNGEN = ("ern", "esten", "este", "eren", "ere", "en", "em", "er", "es", "e", "s", "n")


def stamm(wort: str) -> str:
    """Grobe deutsche Grundform: "rotes"/"rote"/"roten" -> "rot".

    Gekürzt wird, bis keine Endung mehr passt, damit stamm(stamm(w)) == stamm(w) gilt und
    Wortlisten und Kundentext zusammenpassen. Nie unter vier Zeichen, damit "rad" bleibt.
    """
    while len(wort) >= 5:
        for endung in _ENDUNGEN:
            if wort.endswith(endung) and len(wort) - len(endung) >= 4:
                wort = wort[: -len(endung)]
                break
        else:
            break
    return wort


def _passt(muster: str, text_staemme: set[str]) -> bool:
    """Alle Woerter des Musters muessen im Text vorkommen (Reihenfolge egal)."""
    return all(stamm(w) in text_staemme for w in muster.split())


def erweitern(text: str) -> str:
    """Ergänzt Fachbegriffe; der Originaltext bleibt erhalten, damit nichts verloren geht."""
    norm = normalisieren(text)
    vorhanden = {stamm(w) for w in norm.split()}
    zusatz: list[str] = []
    for umgangs, fach in UMGANGSSPRACHE:
        if _passt(umgangs, vorhanden):
            zusatz.extend(w for w in fach.split() if stamm(w) not in vorhanden)
    if not zusatz:
        return norm
    return norm + " " + " ".join(dict.fromkeys(zusatz))


def seite_erkennen(text: str) -> str | None:
    """Erkennt links/rechts/vorne/hinten; "hinten links" ergibt links."""
    vorhanden = {stamm(w) for w in normalisieren(text).split()}
    for muster, seite in SEITEN:
        if _passt(muster, vorhanden):
            return seite
    return None


def jahr_erkennen(text: str) -> int | None:
    """Vierstellige Jahreszahl zwischen 1950 und 2049."""
    treffer = re.findall(r"\b(19[5-9]\d|20[0-4]\d)\b", text)
    return int(treffer[0]) if treffer else None


_BEKANNT: set[str] = {
    wort for umgangs, fach in UMGANGSSPRACHE for wort in (*umgangs.split(), *fach.split())
}


def tippfehler_korrigieren(text: str, zusatzwoerter: set[str] | None = None) -> str:
    """Ergänzt verschriebene Wörter um den bekannten Begriff: "Rueklicht" -> "ruecklicht".

    Nur ab fünf Zeichen und Ähnlichkeit 0,84, sonst würde aus "Rad" ein "Rat". Das Original
    bleibt stehen, falls die Korrektur danebenliegt.
    """
    bekannt = _BEKANNT | (zusatzwoerter or set())
    norm = normalisieren(text)
    ergaenzt: list[str] = []
    for wort in norm.split():
        if len(wort) < 5 or wort in bekannt:
            continue
        treffer = difflib.get_close_matches(wort, bekannt, n=1, cutoff=0.84)
        if treffer and treffer[0] != wort:
            ergaenzt.append(treffer[0])
    return (norm + " " + " ".join(ergaenzt)).strip() if ergaenzt else norm
