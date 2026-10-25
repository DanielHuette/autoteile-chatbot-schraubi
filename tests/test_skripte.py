"""Kommandozeilenskripte: Aufrufe, die ohne Datenbank geprüft werden können.

Kontext: Tests zu scripts/. | Eingabe: Skriptaufrufe mit festen Argumenten. | Ergebnis:
Pytest-Befunde.
"""

import pathlib
import subprocess
import sys

WURZEL = pathlib.Path(__file__).resolve().parent.parent


def test_einrichten_verkaeufe_ohne_beispiele_wird_abgelehnt() -> None:
    lauf = subprocess.run(
        [sys.executable, str(WURZEL / "scripts" / "einrichten.py"), "--verkaeufe", "5"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert lauf.returncode == 2
    assert "--beispiele" in lauf.stderr
