"""Wortliste: versteht der Bot, wie Menschen über Autoteile reden?

Kontext: Tests zu vokabular.py ohne Datenbank. | Eingabe: Laienformulierungen. | Ergebnis:
Pytest-Befunde.
"""

import pytest
from app.vokabular import erweitern, jahr_erkennen, seite_erkennen, stamm, tippfehler_korrigieren


@pytest.mark.parametrize(
    "eingabe,erwartet",
    [
        ("Ruecklicht links", "rueckleuchte"),
        ("das rote Glas hinten", "rueckleuchte"),
        ("mein Auspufftopf ist durch", "schalldaempfer"),
        ("Blinker vorne", "blinkleuchte"),
        ("Lichtmaschine kaputt", "generator"),
        ("Anlasser dreht nicht", "starter"),
        ("Seitenspiegel abgefahren", "aussenspiegel"),
        ("Tacho ohne Funktion", "kombiinstrument"),
        ("Stossstange eingedrueckt", "stossfaenger"),
        ("Kofferraumdeckel verbeult", "heckklappe"),
        ("Wasserpumpe undicht", "kuehlmittelpumpe"),
        ("Scheibe vorne gerissen", "windschutzscheibe"),
    ],
)
def test_umgangssprache_wird_zu_fachbegriff(eingabe: str, erwartet: str) -> None:
    assert erwartet in erweitern(eingabe)


def test_originaltext_bleibt_erhalten() -> None:
    ergebnis = erweitern("Ruecklicht links Golf")
    assert "ruecklicht" in ergebnis
    assert "links" in ergebnis
    assert "golf" in ergebnis


@pytest.mark.parametrize(
    "eingabe,erwartet",
    [
        ("Rueckleuchte Fahrerseite", "links"),
        ("Spiegel Beifahrerseite", "rechts"),
        ("Stossdaempfer hinten", "hinten"),
        ("Scheinwerfer vorne", "vorne"),
        ("Scheinwerfer links", "links"),
        ("Lichtmaschine", None),
    ],
)
def test_seitenangabe(eingabe: str, erwartet: str | None) -> None:
    assert seite_erkennen(eingabe) == erwartet


@pytest.mark.parametrize(
    "eingabe,erwartet",
    [
        ("Golf Baujahr 2008", 2008),
        ("Astra von 1999", 1999),
        ("Rueckleuchte", None),
        ("Teilenummer 1K6945095", None),  # keine Jahreszahl, sondern eine Nummer
    ],
)
def test_baujahr(eingabe: str, erwartet: int | None) -> None:
    assert jahr_erkennen(eingabe) == erwartet


@pytest.mark.parametrize(
    "falsch,richtig",
    [
        ("Rueklicht links", "ruecklicht"),
        ("Scheinwrfer rechts", "scheinwerfer"),
        ("Bremsscheibn vorne", "bremsscheibe"),
    ],
)
def test_tippfehler_werden_gezogen(falsch: str, richtig: str) -> None:
    assert richtig in tippfehler_korrigieren(falsch)


def test_kurze_woerter_bleiben_unberuehrt() -> None:
    assert "rad" in tippfehler_korrigieren("Rad vorne")


def test_stammbildung() -> None:
    assert stamm("rotes") == stamm("rote") == stamm("roten")
    assert stamm("rad") == "rad"
