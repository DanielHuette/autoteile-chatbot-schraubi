#!/usr/bin/env python3
"""Startet ein Kommando mit den Werten aus einer .env-Datei.

Warum nicht einfach die Shell? Weil Werte mit Leerzeichen, Dollarzeichen
oder Umlauten in der Shell zerfallen - und ein scrypt-Hash enthaelt
beides. Dieser Weg liest die Datei wortgetreu und funktioniert unter
Windows genauso wie unter Linux.

    python scripts/mitenv.py .env uvicorn app.main:app --port 8000
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
