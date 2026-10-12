#!/usr/bin/env python3
"""Startet ein Kommando mit den Werten aus einer .env-Datei, unter Windows wie unter Linux.

Kontext: Die Shell zerlegt Werte mit Dollarzeichen, und ein scrypt-Hash enthält welche; hier
wird die Datei wörtlich gelesen. Aufruf: `python scripts/mitenv.py .env uvicorn app.main:app
--app-dir backend`. | Eingabe: Pfad zur .env-Datei, Kommando. | Ergebnis: Rückgabecode des
Kommandos, 2 bei falschem Aufruf.
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys


def laden(pfad: pathlib.Path) -> dict[str, str]:
    werte: dict[str, str] = {}
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        zeile = zeile.strip()
        if not zeile or zeile.startswith("#") or "=" not in zeile:
            continue
        name, _, wert = zeile.partition("=")
        wert = wert.strip()
        if len(wert) >= 2 and wert[0] == wert[-1] and wert[0] in "\"'":
            wert = wert[1:-1]
        werte[name.strip()] = wert
    return werte


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    pfad = pathlib.Path(sys.argv[1])
    if not pfad.exists():
        print(f"Datei nicht gefunden: {pfad}")
        return 2
    umgebung = {**os.environ, **laden(pfad)}
    return subprocess.call(sys.argv[2:], env=umgebung)


if __name__ == "__main__":
    sys.exit(main())
