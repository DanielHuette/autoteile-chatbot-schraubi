#!/usr/bin/env python3
"""Schickt die Lagerdatei an den Chatbot. Fuer den taeglichen Abgleich.

Dieses Skript laeuft beim Shop-Betreiber, meist nachts als geplante
Aufgabe. Es braucht nur zwei Angaben, die aus der Umgebung kommen:

    BOT_URL=https://ihre-adresse
    SYNC_API_KEY=...

Aufruf:

    python scripts/lager_hochladen.py lager.csv
    python scripts/lager_hochladen.py lager.csv --vollabgleich

--vollabgleich bedeutet: Was nicht in der Datei steht, ist nicht mehr
im Bestand und wird auf "nicht verfuegbar" gesetzt. Ohne diesen Schalter
werden nur die gelieferten Teile angelegt oder aktualisiert.

Als geplante Aufgabe unter Windows (Aufgabenplanung), taeglich 3 Uhr:
    python C:\\Pfad\\scripts\\lager_hochladen.py C:\\Export\\lager.csv --vollabgleich

Unter Linux (crontab -e):
    0 3 * * *  cd /pfad && python scripts/lager_hochladen.py export/lager.csv --vollabgleich
"""
from __future__ import annotations

import argparse
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("datei", help="CSV- oder JSON-Datei mit dem Lagerbestand")
    p.add_argument("--vollabgleich", action="store_true",
                   help="Nicht gelieferte Teile als nicht mehr verfuegbar markieren")
    p.add_argument("--url", default=os.environ.get("BOT_URL", ""))
    p.add_argument("--schluessel", default=os.environ.get("SYNC_API_KEY", ""))
    args = p.parse_args()

    if not args.url or not args.schluessel:
        print("FEHLER: BOT_URL und SYNC_API_KEY muessen gesetzt sein.")
        print("Beispiel:  set BOT_URL=https://ihre-adresse   (Windows)")
        print("           export BOT_URL=https://ihre-adresse  (Linux, macOS)")
        return 2

    pfad = pathlib.Path(args.datei)
    if not pfad.exists():
        print(f"FEHLER: Datei nicht gefunden: {pfad}")
        return 2

    daten = pfad.read_bytes()
    print(f"Sende {pfad.name} ({len(daten)/1024:.0f} kB) an {args.url} ...")

    ziel = args.url.rstrip("/") + "/api/sync"
    if args.vollabgleich:
        ziel += "?" + urllib.parse.urlencode({"vollabgleich": "true"})

    anfrage = urllib.request.Request(
        ziel, data=daten, method="POST",
        headers={
            "X-Sync-Key": args.schluessel,
            "Content-Type": "text/csv" if pfad.suffix.lower() == ".csv" else "application/json",
        },
    )
    try:
        with urllib.request.urlopen(anfrage, timeout=900) as antwort:
            import json

            ergebnis = json.loads(antwort.read())
    except urllib.error.HTTPError as fehler:
        print(f"FEHLER {fehler.code}: {fehler.read().decode(errors='replace')[:500]}")
        return 1
    except urllib.error.URLError as fehler:
        print(f"FEHLER: Server nicht erreichbar ({fehler.reason})")
        return 1

    print(f"  empfangen:    {ergebnis['empfangen']}")
    print(f"  uebernommen:  {ergebnis['uebernommen']}")
    print(f"  abgewiesen:   {ergebnis['abgewiesen']}")
    if ergebnis.get("deaktiviert"):
        print(f"  nicht mehr im Bestand: {ergebnis['deaktiviert']}")
    print(f"  neu eingebettet: {ergebnis['neu_eingebettet']}")

    if ergebnis["abgewiesen"]:
        print(f"\n{ergebnis['fehler_gesamt']} fehlerhafte Zeilen, die ersten davon:")
        for f in ergebnis["fehler"][:15]:
            print(f"  Zeile {f['zeile']:>6}  {f['artikelnummer']:<20} {f['problem']}")
        print("\nDiese Teile fehlen im Chatbot. Bitte in der Lagerdatei korrigieren.")
        return 1

    print("\nAlles uebernommen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
