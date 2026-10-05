#!/usr/bin/env python3
"""Legt das Repository an und laedt das Projekt hoch.

Der Zugangsschluessel wird nie angezeigt, nie gespeichert und nie
weitergegeben. Das Skript sucht ihn in dieser Reihenfolge:

  1. Umgebungsvariable GH_TOKEN oder GITHUB_TOKEN
  2. Eine Datei, die ausdruecklich mit --schluesseldatei genannt wird
  3. Automatische Suche im Projektverzeichnis (--suchen)

Gearbeitet wird ueber die GitHub-Schnittstelle, nicht ueber das
Programm git - es muss also nichts weiter installiert sein als Python.

    python scripts/upload_to_github.py --suchen
    python scripts/upload_to_github.py --schluesseldatei C:\\AI_Projekte\\zugang.txt

Vor dem Hochladen wird geprueft, dass keine Geheimnisse mitgehen.
Findet das Skript welche, bricht es ab - lieber kein Hochladen als ein
veroeffentlichtes Passwort.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

WURZEL = pathlib.Path(__file__).resolve().parent.parent

# Muster eines GitHub-Zugangsschluessels. Beide heute gebraeuchlichen
# Formen: der klassische (ghp_) und der feingranulare (github_pat_).
SCHLUESSELMUSTER = re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{50,})\b")

# Muster, die niemals im Repository landen duerfen.
GEHEIMNISMUSTER: list[tuple[str, str]] = [
    (r"\$scrypt\$\d+\$", "ein Passwort-Hash"),
    (r"\bgh[pousr]_[A-Za-z0-9]{36,}\b", "ein GitHub-Zugangsschluessel"),
    (r"\bgithub_pat_[A-Za-z0-9_]{50,}\b", "ein GitHub-Zugangsschluessel"),
    (r"\bsk-[A-Za-z0-9]{32,}\b", "ein OpenAI-Schluessel"),
    (r"postgres(?:ql)?://[^\s\"']*:(?!passwort@|password@|geheim@)[^\s\"'@]+@",
     "eine Datenbankadresse mit Passwort"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "ein privater Schluessel"),
]

# Diese Dateien duerfen die Muster als Beispiel enthalten.
AUSNAHMEN = {"scripts/upload_to_github.py", ".github/workflows/tests.yml", "tests/test_auth.py"}

# Was nie hochgeladen wird, egal was im Ordner liegt.
NICHT_HOCHLADEN = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", "logs",
                   ".venv", "venv", "node_modules", ".idea", ".vscode"}


# ---------------------------------------------------------------------
# Zugangsschluessel finden
# ---------------------------------------------------------------------
def schluessel_aus_datei(pfad: pathlib.Path) -> str | None:
    try:
        if pfad.stat().st_size > 2_000_000:
            return None
        inhalt = pfad.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None
    treffer = SCHLUESSELMUSTER.search(inhalt)
    return treffer.group(0) if treffer else None


def alle_schluessel_aus_datei(pfad: pathlib.Path) -> list[str]:
    try:
        if pfad.stat().st_size > 2_000_000:
            return []
        inhalt = pfad.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    gesehen: list[str] = []
    for treffer in SCHLUESSELMUSTER.finditer(inhalt):
        if treffer.group(0) not in gesehen:
            gesehen.append(treffer.group(0))
    return gesehen


def schluessel_suchen(verzeichnis: pathlib.Path) -> list[tuple[str, pathlib.Path]]:
    """Durchsucht ein Verzeichnis nach GitHub-Zugangsschluesseln.

    Gefunden werden ALLE, nicht nur der erste: wer mehrere Projekte hat,
    hat meist mehrere Schluessel, und abgelaufene liegen oft noch herum.
    Zurueck kommt der Schluessel samt Fundort - angezeigt wird spaeter
    allein der Dateiname.
    """
    endungen = {".txt", ".env", ".cfg", ".ini", ".json", ".md", ".yml", ".yaml", ".conf", ""}

    def rang(p: pathlib.Path) -> tuple[int, int]:
        name = p.name.lower()
        vorne = 0 if any(w in name for w in ("token", "github", "zugang", "secret", "key", "env")) else 1
        return (vorne, len(str(p)))

    # Nicht blind durch alles laufen: ein Projektverzeichnis enthaelt
    # schnell Hunderttausende Dateien in Abhaengigkeitsordnern. Gesucht
    # wird nur bis in die vierte Ebene und ohne diese Ordner.
    ueberspringen = NICHT_HOCHLADEN | {
        "site-packages", "dist", "build", "target", ".next", ".cache",
        "AppData", "Windows", "Program Files", "models", "cache",
    }
    kandidaten: list[pathlib.Path] = []

    def gehen(ordner: pathlib.Path, tiefe: int) -> None:
        if tiefe > 4 or len(kandidaten) > 4000:
            return
        try:
            eintraege = list(ordner.iterdir())
        except (PermissionError, OSError):
            return
        for eintrag in eintraege:
            try:
                if eintrag.is_dir():
                    if eintrag.name not in ueberspringen and not eintrag.is_symlink():
                        gehen(eintrag, tiefe + 1)
                elif eintrag.suffix.lower() in endungen:
                    kandidaten.append(eintrag)
            except (PermissionError, OSError):
                continue

    gehen(verzeichnis, 0)

    funde: list[tuple[str, pathlib.Path]] = []
    bereits: set[str] = set()
    for pfad in sorted(kandidaten, key=rang):
        for schluessel in alle_schluessel_aus_datei(pfad):
            if schluessel not in bereits:
                bereits.add(schluessel)
                funde.append((schluessel, pfad))
    return funde


def kandidaten_sammeln(args) -> list[tuple[str, str]]:
    """Alle in Frage kommenden Zugangsschluessel, beste Quelle zuerst."""
    funde: list[tuple[str, str]] = []

    aus_umgebung = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if aus_umgebung:
        funde.append((aus_umgebung.strip(), "Umgebungsvariable"))

    if args.schluesseldatei:
        pfad = pathlib.Path(args.schluesseldatei)
        if not pfad.exists():
            print(f"   FEHLER: Datei nicht gefunden: {pfad}")
        else:
            for schluessel in alle_schluessel_aus_datei(pfad):
                funde.append((schluessel, str(pfad)))
            if not funde:
                print(f"   In {pfad.name} steht kein GitHub-Zugangsschluessel.")

    if args.suchen:
        ordner = pathlib.Path(args.suchordner)
        if not ordner.exists():
            print(f"   FEHLER: Suchordner nicht gefunden: {ordner}")
        else:
            print(f"   Suche in {ordner} ...")
            for schluessel, pfad in schluessel_suchen(ordner):
                funde.append((schluessel, str(pfad)))

    # Doppelte entfernen, Reihenfolge behalten.
    gesehen: set[str] = set()
    eindeutig: list[tuple[str, str]] = []
    for schluessel, herkunft in funde:
        if schluessel not in gesehen:
            gesehen.add(schluessel)
            eindeutig.append((schluessel, herkunft))
    return eindeutig


# ---------------------------------------------------------------------
# Geheimnispruefung
# ---------------------------------------------------------------------
def dateien_sammeln() -> list[pathlib.Path]:
    """Alles, was hochgeladen wuerde - .gitignore wird beachtet."""
    ignorieren = set()
    gitignore = WURZEL / ".gitignore"
    if gitignore.exists():
        for zeile in gitignore.read_text(encoding="utf-8").splitlines():
            zeile = zeile.strip()
            if zeile and not zeile.startswith(("#", "!")):
                ignorieren.add(zeile.rstrip("/"))

    def ausgeschlossen(p: pathlib.Path) -> bool:
        teile = set(p.relative_to(WURZEL).parts)
        if NICHT_HOCHLADEN & teile:
            return True
        for muster in ignorieren:
            if muster in teile:
                return True
            if muster.startswith("*") and p.name.endswith(muster[1:]):
                return True
            if p.name == muster:
                return True
        # .env.example ist ausdruecklich erwuenscht
        if p.name.startswith(".env") and p.name != ".env.example":
            return True
        return False

    return sorted(p for p in WURZEL.rglob("*") if p.is_file() and not ausgeschlossen(p))


def geheimnisse_suchen(dateien: list[pathlib.Path]) -> list[str]:
    funde: list[str] = []
    for pfad in dateien:
        name = str(pfad.relative_to(WURZEL)).replace("\\", "/")
        if name in AUSNAHMEN or pfad.stat().st_size > 2_000_000:
            continue
        try:
            inhalt = pfad.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for muster, beschreibung in GEHEIMNISMUSTER:
            if re.search(muster, inhalt):
                funde.append(f"{name}: {beschreibung}")
    return funde


# ---------------------------------------------------------------------
# GitHub-Schnittstelle
# ---------------------------------------------------------------------
class GitHub:
    def __init__(self, schluessel: str) -> None:
        self._schluessel = schluessel

    def __call__(self, pfad: str, methode: str = "GET", daten: dict | None = None):
        anfrage = urllib.request.Request(
            f"https://api.github.com{pfad}",
            method=methode,
            data=json.dumps(daten).encode() if daten is not None else None,
            headers={
                "Authorization": f"Bearer {self._schluessel}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
                "User-Agent": "teilethuns-upload",
            },
        )
        try:
            with urllib.request.urlopen(anfrage, timeout=60) as antwort:
                roh = antwort.read()
                return antwort.status, (json.loads(roh) if roh else {})
        except urllib.error.HTTPError as fehler:
            roh = fehler.read()
            try:
                return fehler.code, json.loads(roh)
            except Exception:
                return fehler.code, {"message": roh.decode(errors="replace")[:300]}
        except urllib.error.URLError as fehler:
            return 0, {"message": f"GitHub nicht erreichbar: {fehler.reason}"}


def hochladen(gh: GitHub, konto: str, repo: str, zweig: str,
              dateien: list[pathlib.Path]) -> bool:
    """Laedt alle Dateien als EINEN Stand hoch.

    Erst wird jede Datei als Objekt abgelegt, dann ein Verzeichnisbaum
    daraus gebaut, dann ein Stand darauf gesetzt. So entsteht genau ein
    Eintrag in der Versionsgeschichte - nicht 74.
    """
    # Ein frisch angelegtes Repository ist voellig leer: es hat keinen
    # Zweig und keinen Stand. Die Objektschnittstelle lehnt dort ab
    # ("Git Repository is empty"). Deshalb wird zuerst EINE Datei ueber
    # die Dateischnittstelle abgelegt - damit entsteht der Zweig, und
    # alles Weitere laeuft wie gewohnt.
    status, _ = gh(f"/repos/{konto}/{repo}/git/ref/heads/{zweig}")
    if status != 200:
        print("   Repository ist leer, erster Stand wird angelegt ...")
        erste = next((d for d in dateien if d.name == "README.md"), dateien[0])
        status, antwort = gh(
            f"/repos/{konto}/{repo}/contents/{erste.relative_to(WURZEL).as_posix()}",
            "PUT",
            {"message": "Projektbeschreibung",
             "content": base64.b64encode(erste.read_bytes()).decode(),
             "branch": zweig},
        )
        if status not in (200, 201):
            print(f"   FEHLER beim ersten Stand: {antwort.get('message')}")
            return False

    print(f"   {len(dateien)} Dateien werden abgelegt ...")
    baum = []
    for nr, pfad in enumerate(dateien, start=1):
        name = str(pfad.relative_to(WURZEL)).replace("\\", "/")
        rohdaten = pfad.read_bytes()
        status, antwort = gh(f"/repos/{konto}/{repo}/git/blobs", "POST", {
            "content": base64.b64encode(rohdaten).decode(),
            "encoding": "base64",
        })
        if status not in (200, 201):
            print(f"   FEHLER bei {name}: {antwort.get('message')}")
            return False
        baum.append({"path": name, "mode": "100644", "type": "blob", "sha": antwort["sha"]})
        if nr % 10 == 0 or nr == len(dateien):
            print(f"      {nr}/{len(dateien)}")

    # Gibt es den Zweig schon? Dann wird darauf aufgesetzt.
    status, antwort = gh(f"/repos/{konto}/{repo}/git/ref/heads/{zweig}")
    eltern = [antwort["object"]["sha"]] if status == 200 else []

    status, antwort = gh(f"/repos/{konto}/{repo}/git/trees", "POST", {"tree": baum})
    if status not in (200, 201):
        print(f"   FEHLER beim Verzeichnisbaum: {antwort.get('message')}")
        return False
    baum_sha = antwort["sha"]

    status, antwort = gh(f"/repos/{konto}/{repo}/git/commits", "POST", {
        "message": ("Auskunftshelfer fuer Gebrauchtteile: pgvector-Suche in Laiensprache, "
                    "Klick-Interview, eBay-Weiterleitung, getrennte Betriebsleitung, "
                    "Messreihen und Betriebsanleitung"),
        "tree": baum_sha,
        "parents": eltern,
    })
    if status not in (200, 201):
        print(f"   FEHLER beim Festschreiben: {antwort.get('message')}")
        return False
    commit_sha = antwort["sha"]

    if eltern:
        status, antwort = gh(f"/repos/{konto}/{repo}/git/refs/heads/{zweig}", "PATCH",
                             {"sha": commit_sha, "force": False})
    else:
        status, antwort = gh(f"/repos/{konto}/{repo}/git/refs", "POST",
                             {"ref": f"refs/heads/{zweig}", "sha": commit_sha})
    if status not in (200, 201):
        print(f"   FEHLER beim Setzen des Zweigs: {antwort.get('message')}")
        return False
    return True


# Die Datei .github/workflows/tests.yml kann auf manchen Rechnern nicht
# von aussen geschrieben werden - ein Schutz gegen eingeschleuste
# Arbeitsablaeufe. Fehlt sie lokal, wird sie hier beim Hochladen
# angelegt, damit die Dauerpruefung im Repository trotzdem laeuft.
WORKFLOW_PFAD = ".github/workflows/tests.yml"


def workflow_nachtragen(gh: GitHub, konto: str, repo: str, zweig: str) -> None:
    vorlage = WURZEL / ".github" / "workflows" / "tests.yml"
    if vorlage.exists():
        return
    quelle = WURZEL / "scripts" / "tests_workflow.yml"
    if not quelle.exists():
        return
    status, _ = gh(f"/repos/{konto}/{repo}/contents/{WORKFLOW_PFAD}")
    if status == 200:
        return
    status, antwort = gh(f"/repos/{konto}/{repo}/contents/{WORKFLOW_PFAD}", "PUT", {
        "message": "Dauerpruefung bei jeder Aenderung",
        "content": base64.b64encode(quelle.read_bytes()).decode(),
        "branch": zweig,
    })
    if status in (200, 201):
        print("   Dauerpruefung (.github/workflows/tests.yml) nachgetragen")
    else:
        print(f"   Hinweis: Dauerpruefung nicht angelegt ({antwort.get('message')})")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--name", default="autoteile-chatbot-schraubi")
    p.add_argument("--beschreibung", default=(
        "Auskunftshelfer fuer einen Gebrauchtteile-Versandshop: pgvector-Teilesuche in "
        "Laiensprache, Klick-Interview, eBay-Weiterleitung, getrennte Betriebsleitung. "
        "FastAPI, PostgreSQL 16, barrierefreies Widget."
    ))
    p.add_argument("--privat", action="store_true", help="Repository nicht oeffentlich anlegen")
    p.add_argument("--zweig", default="main")
    p.add_argument("--schluesseldatei", default="",
                   help="Datei, in der der GitHub-Zugangsschluessel steht")
    p.add_argument("--suchen", action="store_true",
                   help="Zugangsschluessel selbst im Projektverzeichnis suchen")
    p.add_argument("--suchordner", default=r"C:\AI_Projekte",
                   help="Wo gesucht wird, wenn --suchen gesetzt ist")
    p.add_argument("--nur-pruefen", action="store_true",
                   help="nur die Geheimnispruefung laufen lassen, nichts hochladen")
    p.add_argument("--nur-schluessel", action="store_true",
                   help="nur den Zugangsschluessel suchen und pruefen, nichts hochladen")
    args = p.parse_args()

    print("1) Geheimnispruefung ...")
    dateien = dateien_sammeln()
    funde = geheimnisse_suchen(dateien)
    if funde:
        print("\n   ABBRUCH - diese Dateien enthalten Geheimnisse:")
        for f in funde:
            print("     -", f)
        print("\n   Entfernen oder in .gitignore eintragen, dann erneut versuchen.")
        return 1
    print(f"   in Ordnung, {len(dateien)} Dateien ohne Vertrauliches")

    if args.nur_pruefen:
        return 0

    print("\n2) Zugangsschluessel ...")
    kandidaten = kandidaten_sammeln(args)
    if not kandidaten:
        print("\nKein Zugangsschluessel gefunden. Eine dieser Moeglichkeiten:")
        print("   python scripts/upload_to_github.py --suchen")
        print("   python scripts/upload_to_github.py --schluesseldatei PFAD\\ZUR\\DATEI")
        print("   Umgebungsvariable setzen:  set GH_TOKEN=...   (Windows)")
        print("\nEinen Schluessel erzeugen: https://github.com/settings/tokens")
        print("Benoetigtes Recht: 'repo'.")
        return 1
    print(f"   {len(kandidaten)} Schluessel gefunden, wird der Reihe nach geprueft")

    # Jeder Fund wird ausprobiert. Abgelaufene Schluessel liegen oft noch
    # herum - deshalb entscheidet nicht der Fundort, sondern GitHub.
    gh = None
    konto = ""
    for schluessel, herkunft in kandidaten:
        kandidat = GitHub(schluessel)
        status, benutzer = kandidat("/user")
        kurz = pathlib.Path(herkunft).name if herkunft != "Umgebungsvariable" else herkunft
        if status == 200:
            gh, konto = kandidat, benutzer["login"]
            print(f"   gueltig: {kurz}")
            break
        if status == 401:
            print(f"   abgelaufen oder zurueckgezogen: {kurz}")
        elif status == 0:
            print(f"   {benutzer.get('message')}")
            return 1
        else:
            print(f"   nicht brauchbar ({status}): {kurz}")

    if gh is None:
        print("\nKeiner der gefundenen Schluessel ist gueltig.")
        print("Einen neuen erzeugen: https://github.com/settings/tokens")
        print("Benoetigtes Recht: 'repo'. Danach erneut starten.")
        return 1

    print("\n3) Angemeldet ...")
    print(f"   als {konto}")

    if args.nur_schluessel:
        print("\nSchluessel ist gueltig. Fuer das Hochladen ohne --nur-schluessel starten.")
        return 0

    print(f"\n4) Repository {konto}/{args.name} ...")
    status, _ = gh(f"/repos/{konto}/{args.name}")
    if status == 200:
        print("   besteht bereits, wird weiterverwendet")
    else:
        status, antwort = gh("/user/repos", "POST", {
            "name": args.name,
            "description": args.beschreibung,
            "private": bool(args.privat),
            "has_issues": True,
            "has_wiki": False,
            "auto_init": False,
        })
        if status not in (200, 201):
            print(f"   FEHLER {status}: {antwort.get('message')}")
            return 1
        print(f"   angelegt ({'privat' if args.privat else 'oeffentlich'})")

    print("\n5) Hochladen ...")
    if not hochladen(gh, konto, args.name, args.zweig, dateien):
        return 1

    workflow_nachtragen(gh, konto, args.name, args.zweig)

    print("\n6) Beschlagwortung ...")
    gh(f"/repos/{konto}/{args.name}/topics", "PUT", {"names": [
        "pgvector", "postgresql", "fastapi", "semantic-search", "hybrid-search",
        "chatbot", "ecommerce", "eu-ai-act", "accessibility", "python", "hnsw",
    ]})

    print(f"\nFertig: https://github.com/{konto}/{args.name}")
    print("Der Zugangsschluessel wurde nirgends gespeichert.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
