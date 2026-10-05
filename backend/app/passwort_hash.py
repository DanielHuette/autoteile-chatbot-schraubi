"""Erzeugt den Wert für ADMIN_PASSWORD_HASH.

Aufruf:   python -m app.passwort_hash
Das Passwort wird verdeckt eingegeben und nicht angezeigt.
"""
from __future__ import annotations

import getpass
import secrets
import sys

from .auth import hash_erzeugen


def main() -> int:
    print("Passwort für die Betriebsleitung festlegen.")
    print("Mindestens 12 Zeichen. Die Eingabe ist nicht sichtbar.\n")
    eins = getpass.getpass("Passwort: ")
    zwei = getpass.getpass("Wiederholen: ")
    if eins != zwei:
        print("\nDie beiden Eingaben sind nicht gleich. Nichts geändert.")
        return 1
    try:
        wert = hash_erzeugen(eins)
    except ValueError as exc:
        print(f"\n{exc}")
        return 1
    print("\nDiese zwei Zeilen in die Datei .env eintragen:\n")
    print(f"ADMIN_PASSWORD_HASH={wert}")
    print(f"SESSION_SECRET={secrets.token_urlsafe(48)}")
    print(f"SYNC_API_KEY={secrets.token_urlsafe(32)}")
    print("\nDas Passwort selbst steht nirgends in der Datei. Merken oder in einem")
    print("Passwortspeicher ablegen - es laesst sich nicht wiederherstellen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
