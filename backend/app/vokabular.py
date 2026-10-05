"""Umgangssprache -> Fachbegriff.

Der Kunde sagt "das rote Glas hinten", der Lagerbestand sagt
"Rueckleuchte". Diese Zuordnung ist der eigentliche Kern der
Teilesuche fuer Laien. Sie wird bewusst als Wortliste gepflegt und
nicht geraten: eine falsche Teileempfehlung kostet Rueckversand.
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

# Ortsangaben: der Kunde beschreibt die Lage, das Lager fuehrt eine Seite.
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
    """Grobe deutsche Grundform. Schneidet Flexionsendungen ab.

    "rotes"/"rote"/"roten" -> "rot", "vorderes"/"vorder" -> "vord".

    Es wird so lange gekuerzt, bis keine Endung mehr passt. Das ist
    wichtig: die Funktion muss auf ihr eigenes Ergebnis angewandt
    dasselbe liefern. Sonst passen Wortlisten und Kundentext nicht
    zusammen - "vorderes" wuerde zu "vorder", die Liste haette aber
    schon "vord" gespeichert, und der Treffer bliebe aus.

    Absichtlich einfach: es geht um robustes Wiedererkennen, nicht um
    Sprachwissenschaft. Nichts wird unter vier Zeichen gekuerzt, damit
    aus "rad" nicht "ra" wird.
    """
    while len(wort) >= 5:
        for endung in _ENDUNGEN:
            if wort.endswith(endung) and len(wort) - len(endung) >= 4:
                wort = wort[: -len(endung)]
                break
        else:
            break
    return wort


def staemme(text: str) -> list[str]:
    return [stamm(w) for w in normalisieren(text).split()]


def _passt(muster: str, text_staemme: set[str]) -> bool:
    """Alle Woerter des Musters muessen im Text vorkommen (Reihenfolge egal)."""
    return all(stamm(w) in text_staemme for w in muster.split())


def erweitern(text: str) -> str:
    """Fuegt dem Kundentext die passenden Fachbegriffe hinzu.

    Der Originaltext bleibt erhalten - es wird nichts ersetzt, nur
    ergaenzt. So geht keine Information verloren.
    """
    norm = normalisieren(text)
    vorhanden = {stamm(w) for w in norm.split()}
    zusatz: list[str] = []
    for umgangs, fach in UMGANGSSPRACHE:
        if _passt(umgangs, vorhanden):
            zusatz.extend(w for w in fach.split() if stamm(w) not in vorhanden)
    if not zusatz:
        return norm
    gesehen: set[str] = set()
    eindeutig = [w for w in zusatz if not (w in gesehen or gesehen.add(w))]
    return norm + " " + " ".join(eindeutig)


def seite_erkennen(text: str) -> str | None:
    """Erkennt links/rechts/vorne/hinten aus der Kundenbeschreibung.

    Fahrerseite bedeutet in Deutschland links. Eine ausdrueckliche
    Seitenangabe schlaegt die Lageangabe: "hinten links" -> links.
    """
    vorhanden = {stamm(w) for w in normalisieren(text).split()}
    for muster, seite in SEITEN:
        if _passt(muster, vorhanden):
            return seite
    return None


def jahr_erkennen(text: str) -> int | None:
    """Vierstellige Jahreszahl zwischen 1950 und 2049."""
    treffer = re.findall(r"\b(19[5-9]\d|20[0-4]\d)\b", text)
    return int(treffer[0]) if treffer else None


# Alle Woerter, die in der Umgangssprachliste vorkommen - Grundlage
# fuer die Tippfehlerkorrektur.
_BEKANNT: set[str] = set()
for _umgangs, _fach in UMGANGSSPRACHE:
    _BEKANNT.update(_umgangs.split())
    _BEKANNT.update(_fach.split())


def tippfehler_korrigieren(text: str, zusatzwoerter: set[str] | None = None) -> str:
    """Zieht verschriebene Woerter auf bekannte Begriffe.

    "Rueklicht" wird zu "ruecklicht", "Scheinwrfer" zu "scheinwerfer".
    Korrigiert wird nur, was deutlich aehnlich ist (Schwelle 0,84) und
    mindestens fuenf Zeichen hat - sonst wuerde aus "Rad" ein "Rat".
    Der Originaltext bleibt erhalten, das korrigierte Wort kommt dazu:
    so geht nichts verloren, falls die Korrektur danebenliegt.
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
