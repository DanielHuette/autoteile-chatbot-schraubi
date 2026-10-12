# Bericht: Aufräumen des Auskunftshelfers Schraubi

English version: [REPORT.md](REPORT.md)

## Umfang

**Kontext:** Reines Aufräumen eines bestehenden Projekts; Namen, Kundentexte und Suchwortschatz bleiben deutsch und unverändert. | **Eingabe:** Backend (backend/app), Widget, Messreihen (bench), Skripte, Tests, CI. | **Ergebnis:** Weniger Code, geprüfte Typen, neun behobene Fehler mit Regressionstests.

| Bereich | Änderung |
|---|---|
| Kommentare | Trennlinien, Nacherzählungen und Wiederholungen entfernt; Begründungen (Rechtsvorgabe, Messung, Fallstrick) gekürzt behalten |
| Modul-Docstrings | Jede Python-Datei beginnt mit Zusammenfassung und `Kontext: … \| Eingabe: … \| Ergebnis: …` |
| Typen | Alle Funktionssignaturen typisiert; mypy im strengen Modus für backend/app |
| Lint | Regelsatz um S, SIM, RUF, PTH und ANN erweitert; `ruff format` auf alle Dateien |
| Fehler | Neun Fehler behoben, jeder mit einem Test, der auf dem alten Stand fehlschlägt |
| Umgebung | `requirements-dev.txt` mit festen Versionen; CI prüft zusätzlich Format und Typen |
| Unverändert | Dateinamen, Funktions- und Feldnamen der Schnittstelle, Datenbank, Kundentexte, `vokabular.py`-Wortlisten, README und Betriebsanleitung |

## Entfernt

**Kontext:** Dateien und Code ohne Funktion im Produkt. | **Eingabe:** Suche nach ungenutzten Funktionen, Feldern, Importen und Verweisen in README, Betriebsanleitung und CI. | **Ergebnis:** 3 Dateien und 11 ungenutzte Code-Stellen entfernt; kein Verweis darauf in den Dokumenten.

| Was | Grund |
|---|---|
| `scripts/upload_to_github.py` | Hilfsskript zum Veröffentlichen des Repositorys, nicht Teil des Produkts |
| `scripts/tests_workflow.yml` | Kopie von `.github/workflows/tests.yml`, nur von `upload_to_github.py` benutzt |
| `scripts/testserver.sh` | Fester lokaler Pfad, nirgends dokumentiert; Start steht im README (`scripts/mitenv.py`) |
| `Sitzung.restsekunden` (auth.py) | Nie gelesen |
| `Pruefung.protokoll_art` (guardrails.py) | Gesetzt, nie gelesen |
| `Treffer.aehnlichkeit` samt Sammlung in `_fusion` (search.py) | Gesetzt, nie gelesen |
| `TeileSuche.suchen` (search.py) | Nie aufgerufen |
| `staemme()` (vokabular.py) | Nie aufgerufen; Wortlisten unberührt |
| Parameter `begriff`, `stand`, `text` der Antwort-Hilfsmethoden (dialog.py) | Im Rumpf nie benutzt |
| `erwartet_marke`, `erwartet_modell` (bench/anfragen.py) | Erzeugt, nie ausgewertet |
| `BLAU`, `BLAU_HELL`, `BLAU_TIEF`, `ROT` (bench/stil.py) | Nie benutzt |
| Doppelte Artikelnummer-Prüfung (bench/testdaten.py) | Konnte bei laufender Nummer nie greifen |
| Parameter `suche` von `messen()` (bench/qualitaet.py) | Nie benutzt |
| `PYTHONPATH`-Zuweisung, `__import__("os")` (scripts/einrichten.py) | Wirkungslos zur Laufzeit bzw. umständlich |
| Importe innerhalb von Funktionen (main.py, auth.py, embeddings.py, lager_hochladen.py, conftest.py, test_sync.py) | An den Dateianfang verlegt oder doppelt; `fastembed` bleibt bewusst spät importiert |
| Ungenutzte Importe in vier Testdateien | Bisher per Regelausnahme verdeckt |
| 350 Kommentarzeilen (32 davon mit `upload_to_github.py`) | Trennlinien, Nacherzählungen, Wiederholungen des Codes |

## Behobene Fehler

**Kontext:** Nur Fehler, die sich mit einem Test nachweisen lassen; jeder Regressionstest schlägt auf dem alten Stand fehl, ein Zusatztest sichert die unveränderte Nummernsuche. | **Eingabe:** Prüfung von Eingabegrenzen, Schlüsselvergleich, Fehlerantworten, Kopfzeilen und Dateieinlesen. | **Ergebnis:** Neun Fehler behoben, 14 neue Tests.

| Fehler | Auswirkung vorher | Behebung | Regressionstest |
|---|---|---|---|
| Schnittstellenschlüssel mit Umlaut | `hmac.compare_digest` auf Text wirft `TypeError`: Antwort 500 und Vorfallseintrag statt 401 | Vergleich als Bytes, eine gemeinsame Prüfung für beide Abgleich-Endpunkte | `test_sicherheit.py::test_sync_schluessel_mit_umlaut_ergibt_401_statt_500` |
| Ungültiges Baujahr im Klick-Interview | `"abc"`, `"²"`, `"2005-2008"`, `2005.5` oder `99999999999` führten zu Antwort 500 | Baujahr zählt nur mit 1 bis 4 Ziffern, sonst fehlt es und der Schritt wird erneut angeboten | `test_api.py::test_interview_mit_ungueltigem_baujahr_fragt_erneut` (5 Fälle) |
| Interviewstand ohne Größengrenze | Öffentlicher Endpunkt ohne Mengenbremse nahm beliebig viele Felder an | Höchstens 10 Felder, sonst 422 | `test_sicherheit.py::test_interview_mit_zu_vielen_feldern_wird_abgewiesen` |
| Mengenbremse räumte nie auf | Fenster eines Besuchers leeren sich nur bei seinem nächsten Besuch; die Bereinigung löschte nur leere Fenster, also fast nie. Speicher wuchs unbegrenzt, ab 10.000 Besuchern prüfte jede Anfrage 5.000 Einträge | Abgelaufene Fenster werden entfernt | `test_sicherheit.py::test_mengenbremse_raeumt_abgelaufene_fenster` |
| Widget wurde nie zwischengespeichert | Die Kopfzeilen-Middleware überschrieb `Cache-Control: public, max-age=3600` von `/widget.js` mit `no-store` | `no-store` nur, wenn die Antwort keine eigene Angabe hat | `test_api.py::test_widget_wird_zwischengespeichert` |
| CSV-Einlesen veränderte globalen Zustand | Scheiterte die Trennzeichenerkennung, wurde `csv.excel.delimiter` für den ganzen Prozess umgestellt | Trennzeichen nur für diesen Leser | `test_sync.py::test_csv_erkennung_veraendert_keinen_globalen_dialekt` |
| JSON-Lieferung mit Nicht-Objekt | Ein Element wie `42` löste in der Fehlerbehandlung einen zweiten Fehler aus: ganzer Abgleich mit 500 abgebrochen | Zeile wird als abgewiesen gemeldet, Artikelnummer `?` | `test_sync.py::test_zeile_ohne_objekt_wird_gemeldet_statt_abbruch` |
| Knopf „Ich habe eine Teilenummer“ | Antwort „Dazu finde ich im Moment kein passendes Teil“ und Eintrag als Nachfragelücke für den Einkauf; die vorhandene Antwort `nummer_hinweis` war nie erreichbar | Kurze Nachricht mit „Teilenummer“ ohne Ziffer erhält den vorhandenen Hinweistext (wörtlich unverändert); mit Nummer wird weiter gesucht | `test_api.py::test_teilenummer_knopf_gibt_hinweis_statt_fehlanzeige`, `test_api.py::test_nummer_im_text_wird_weiter_gesucht` |
| `einrichten.py --verkaeufe` ohne `--beispiele` | Tat stillschweigend nichts, obwohl der Docstring den Aufruf so zeigte | Klare Fehlermeldung, Rückgabecode 2 | `test_skripte.py::test_einrichten_verkaeufe_ohne_beispiele_wird_abgelehnt` |

| Geprüft, kein Befund | Begründung |
|---|---|
| SQL aus Zeichenketten | In `search.py` werden nur Modulkonstanten eingesetzt; alle Werte sind parametrisiert |
| Sitzung und Cookies | Kein Cookie; das Sitzungsmerkmal steht in einer Kopfzeile, HMAC-Prüfung mit `compare_digest` |
| Passwort | scrypt-Hash, Vergleich mit `compare_digest`, Fehlversuchsbremse in der Datenbank |
| CORS | Nur `ALLOWED_ORIGINS`, ohne Anmeldedaten |
| Fehlerantworten | 500 ohne interne Angaben (bestehender Test) |
| Zeitlimits ausgehender Aufrufe | OpenAI 30 s, Upload-Skript 900 s, Datenbankpool 15 s |

## Umbauten ohne Verhaltensänderung

**Kontext:** Lesbarkeit und Prüfbarkeit, ohne dass sich Antworten oder Schnittstellen ändern. | **Eingabe:** Alle Python-Module. | **Ergebnis:** Kürzere, eindeutig typisierte Funktionen; Vergleich aller Zeichenketten alt gegen neu ohne Abweichung bei Kundentexten.

| Stelle | Vorher | Nachher |
|---|---|---|
| `main.py` Zustand | Felder `Optional`, 22 Zugriffe ohne Prüfung | Feste Typen, gesetzt beim Start |
| `main.py` Endpunkte | `Depends`/`Header` als Vorgabewerte, Schlüsselprüfung doppelt | `Annotated`, eine Prüfung `sync_schluessel`, Admin-Prüfung über `dependencies` |
| `main.py` Datumsumwandlung | Viermal derselbe Ausdruck | `_json_tauglich()` |
| `main.py` Interviewstand | Bereinigung im Endpunkt | `stand_bereinigen()`, einzeln testbar |
| `dialog.py` Antwortwahl | Elf `if`-Zweige | Zuordnung Absicht → Methode |
| `dialog.py` Lockerungstexte | Veränderliches Klassenattribut | Modulkonstante, Texte wörtlich gleich |
| `search.py` | Zugriff auf private Felder des Katalogs | Öffentliche Methode `Katalog.wortschatz()` |
| `search.py` `Filter.kopie` | Kopie über `__dict__` und `setattr` | `dataclasses.replace` |
| `shipping.py` Feiertage | Datumsliste mit Namen als Kommentar | Benannte Tabellen `FESTE_FEIERTAGE`, `TAGE_NACH_OSTERSONNTAG` |
| `db.py` | Verbindung ohne Zeilentyp | `Connection[DictRow]`, dadurch prüfbar |
| `auth.py` | `except Exception` bei Hash und Sitzung | Nur die tatsächlich möglichen Fehlerarten |
| `sync.py` | `int(round(...))`, `md5` ohne Kennzeichnung | `round(...)`, `md5(..., usedforsecurity=False)` (Änderungserkennung, kein Schutzzweck) |
| `vokabular.py` | Hilfsmenge per Schleife auf Modulebene, Trick mit `set.add` | Mengen- und `dict.fromkeys`-Ausdruck; Wortlisten unberührt |
| Tests | Untypisierte Fixtures, Feiertagsnamen als Kommentare | Typisierte Fixtures, benannte Daten statt Kommentaren |

## Kennzahlen vorher und nachher

**Kontext:** Gemessen auf dem Stand vor und nach dem Aufräumen. | **Eingabe:** ruff 0.16.10, mypy 2.4.0, pytest 9.1.1, PostgreSQL 16 mit pgvector. | **Ergebnis:** Alle Prüfungen ohne Befund, 14 Tests mehr.

| Kennzahl | Vorher | Nachher |
|---|---|---|
| Tests | 140 bestanden | 154 bestanden |
| Lint-Regelsatz | E, F, W, I, UP, B, C4 | zusätzlich S, SIM, RUF, PTH, ANN |
| Befunde mit S, SIM, RUF, PTH | 246 | 0 |
| `ruff format --check` | 31 Dateien abweichend | 0 |
| mypy `backend/app` | 43 Fehler (nur `disallow_untyped_defs`) | 0 Fehler im strengen Modus |
| Kommentarzeilen gesamt | 433 von 7.078 (6,1 %) | 83 von 7.166 (1,2 %) |
| Dateien über 5 % Kommentaranteil | 16 | 0 |
| Module mit Kontext-Docstring | 0 von 37 | 37 von 37 |

### Kommentaranteil je Datei

Gezählt werden Kommentarzeilen geteilt durch nicht leere Zeilen; Docstrings zählen nicht, `noqa`-Marken nicht. Die Zeilenzahl steigt teils durch `ruff format`.

| Datei | Vorher | Nachher |
|---|---|---|
| `backend/app/auth.py` | 4 / 146 (2,7 %) | 1 / 148 (0,7 %) |
| `backend/app/config.py` | 0 / 104 (0,0 %) | 0 / 100 (0,0 %) |
| `backend/app/db.py` | 12 / 171 (7,0 %) | 3 / 166 (1,8 %) |
| `backend/app/dialog.py` | 26 / 535 (4,9 %) | 3 / 638 (0,5 %) |
| `backend/app/embeddings.py` | 1 / 117 (0,9 %) | 1 / 111 (0,9 %) |
| `backend/app/guardrails.py` | 6 / 90 (6,7 %) | 2 / 123 (1,6 %) |
| `backend/app/katalog.py` | 34 / 168 (20,2 %) | 7 / 139 (5,0 %) |
| `backend/app/kpi.py` | 5 / 241 (2,1 %) | 1 / 292 (0,3 %) |
| `backend/app/main.py` | 37 / 465 (8,0 %) | 6 / 455 (1,3 %) |
| `backend/app/passwort_hash.py` | 0 / 31 (0,0 %) | 0 / 31 (0,0 %) |
| `backend/app/search.py` | 33 / 316 (10,4 %) | 9 / 284 (3,2 %) |
| `backend/app/shipping.py` | 12 / 151 (7,9 %) | 0 / 154 (0,0 %) |
| `backend/app/sync.py` | 14 / 353 (4,0 %) | 5 / 403 (1,2 %) |
| `backend/app/vokabular.py` | 5 / 203 (2,5 %) | 2 / 178 (1,1 %) |
| `bench/anfragen.py` | 8 / 140 (5,7 %) | 0 / 119 (0,0 %) |
| `bench/architektur.py` | 22 / 346 (6,4 %) | 12 / 358 (3,4 %) |
| `bench/diagramme.py` | 1 / 194 (0,5 %) | 1 / 312 (0,3 %) |
| `bench/latenz.py` | 11 / 184 (6,0 %) | 3 / 187 (1,6 %) |
| `bench/qualitaet.py` | 1 / 164 (0,6 %) | 0 / 190 (0,0 %) |
| `bench/stil.py` | 3 / 50 (6,0 %) | 0 / 54 (0,0 %) |
| `bench/testdaten.py` | 6 / 208 (2,9 %) | 3 / 234 (1,3 %) |
| `scripts/einrichten.py` | 0 / 66 (0,0 %) | 0 / 77 (0,0 %) |
| `scripts/lager_hochladen.py` | 0 / 80 (0,0 %) | 0 / 76 (0,0 %) |
| `scripts/messwerte_einsetzen.py` | 1 / 175 (0,6 %) | 0 / 184 (0,0 %) |
| `scripts/mitenv.py` | 0 / 37 (0,0 %) | 0 / 36 (0,0 %) |
| `scripts/upload_to_github.py` | 32 / 419 (7,6 %) | entfernt |
| `tests/conftest.py` | 4 / 115 (3,5 %) | 1 / 141 (0,7 %) |
| `tests/oberflaeche.py` | 13 / 237 (5,5 %) | 2 / 266 (0,8 %) |
| `tests/test_api.py` | 5 / 123 (4,1 %) | 1 / 181 (0,6 %) |
| `tests/test_auth.py` | 3 / 48 (6,2 %) | 0 / 48 (0,0 %) |
| `tests/test_guardrails.py` | 1 / 44 (2,3 %) | 0 / 55 (0,0 %) |
| `tests/test_sicherheit.py` | 4 / 93 (4,3 %) | 1 / 120 (0,8 %) |
| `tests/test_skripte.py` | – | 0 / 18 (0,0 %) |
| `tests/test_suche.py` | 4 / 97 (4,1 %) | 0 / 118 (0,0 %) |
| `tests/test_sync.py` | 5 / 146 (3,4 %) | 1 / 200 (0,5 %) |
| `tests/test_versand.py` | 14 / 54 (25,9 %) | 0 / 71 (0,0 %) |
| `tests/test_vokabular.py` | 4 / 56 (7,1 %) | 1 / 69 (1,4 %) |
| `widget/teilethuns-widget.js` | 102 / 911 (11,2 %) | 17 / 827 (2,1 %) |
| **Gesamt** | **433 / 7078 (6,1 %)** | **83 / 7166 (1,2 %)** |

## Ausnahmen im Regelsatz

**Kontext:** Jede Ausnahme steht mit Begründung in `pyproject.toml`. | **Eingabe:** Befunde des erweiterten Regelsatzes. | **Ergebnis:** Neun begründete Ausnahmen, alle eng auf Datei oder Regel begrenzt.

| Regel | Geltungsbereich | Grund |
|---|---|---|
| E501 | überall | Lange Kundentexte werden nicht umbrochen; Codezeilen setzt `ruff format` |
| RUF001–RUF003 | überall | Gedankenstrich und typografische Zeichen sind gewollter Kundentext |
| ANN401 | überall | Rohzeilen aus Lagerdateien und JSON sind bis zur Prüfung untypisiert |
| S101, S105, S603 | `tests/` | `assert` in pytest, feste Prüfgeheimnisse der Testdatenbank, fester Skriptaufruf |
| S608 | `backend/app/search.py`, `bench/` | Eingesetzt werden nur Modulkonstanten und Zahlen |
| S311 | `bench/` | Zufall für reproduzierbare Testdaten |
| E402 | `bench/`, `scripts/` | Eigenständige Skripte setzen erst `sys.path` |
| S310 | `scripts/` | Ziel-URL legt der Betreiber selbst fest |
| S603 | `scripts/mitenv.py` | Startet absichtlich das übergebene Kommando |

## Umgebung und CI

**Kontext:** Gleiche Werkzeugversionen lokal und in GitHub Actions. | **Eingabe:** `backend/requirements.txt` (unverändert, fest), `.github/workflows/tests.yml`. | **Ergebnis:** Eine Installationsdatei für Entwicklung und CI, zwei zusätzliche Prüfschritte.

| Datei | Änderung |
|---|---|
| `requirements-dev.txt` | Neu: bindet `backend/requirements.txt` ein, dazu `mypy==2.4.0`, `pytest==9.1.1`, `ruff==0.16.10` |
| `.github/workflows/tests.yml` | Installiert `requirements-dev.txt`; prüft `ruff check .`, `ruff format --check .`, `mypy`; Kommentar zum gelöschten Upload-Skript entfernt |
| `pyproject.toml` | `[tool.mypy]` (Python 3.11, strenger Modus, `disallow_untyped_defs`, nur `backend/app`), erweiterte ruff-Regeln mit begründeten Ausnahmen |

## Abschlussprüfung

**Kontext:** Prüfung des fertigen Stands vor dem Commit. | **Eingabe:** Arbeitsstand dieses Commits. | **Ergebnis:** Alle Prüfungen bestanden; das Basisabbild kam wegen der Abrufgrenze von Docker Hub über einen Spiegel.

| Prüfung | Ergebnis |
|---|---|
| `ruff check .` | Bestanden |
| `ruff format --check .` | Bestanden, 42 Dateien (37 Python, 5 Markdown) |
| `mypy` (streng, `backend/app`) | 0 Fehler in 15 Dateien |
| `pytest` gegen PostgreSQL 16 mit pgvector | 154 bestanden |
| Frische Umgebung mit Python 3.12 aus `requirements-dev.txt` | Installation und alle Prüfungen bestanden |
| Regressionstests gegen den alten Stand | 13 von 13 schlagen dort fehl |
| `node --check widget/teilethuns-widget.js` | Bestanden; Änderungen am Widget betreffen nur Kommentare |
| `docker build --network=host .` | Docker Hub antwortete mit 429 (Abrufgrenze). Gleicher Bau mit `python:3.12-slim` aus `mirror.gcr.io` erfolgreich; Container startet, `/api/health` meldet „bereit“, `/widget.js` liefert `public, max-age=3600` |
| Vergleich aller Zeichenketten alt gegen neu | Kundentexte und Wortlisten unverändert |
| Suche nach Geheimnissen, lokalen Pfaden, Debug-Ausgaben, TODO | Kein Befund; nur Platzhalter in `.env.example` und der Testzugang der CI-Datenbank |

## Nachgezogen

**Kontext:** Kleine Befunde am Rand des Aufräumens | **Eingabe:** Beobachtungen während der Arbeit | **Ergebnis:** behoben

| Punkt | Stand |
|---|---|
| README-Block „automatische Tests“ nennt noch 140 Tests | Erledigt |
| README „Selbst ausprobieren“: `python -m app.passwort_hash` findet das Paket nur im Ordner `backend/` | Erledigt |
| `EBAY_SHOP_URL` wird eingelesen, aber nirgends verwendet | Erledigt |
| Hinter einem Proxy (z. B. Render) sieht der Dienst nur die Proxy-Adresse; Mengen- und Fehlversuchsbremse gelten dann für alle Besucher mit gleichem Browser gemeinsam | Erledigt |
| `passwort_hash.py` sagt „Diese zwei Zeilen“, gibt aber drei aus | Erledigt |
| `docs/LINKEDIN.md` enthält Werbetexte im Produkt-Repository | Bleibt lokal, kommt nicht ins Repository |
