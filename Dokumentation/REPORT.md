# Report: Cleaning up the Schraubi parts assistant

Deutsche Fassung: [BERICHT.md](BERICHT.md)

## Scope

**Context:** Pure clean-up of an existing project; names, customer-facing text and search vocabulary stay German and unchanged. | **Input:** Backend (backend/app), widget, benchmarks (bench), scripts, tests, CI. | **Output:** Less code, checked types, nine fixed defects with regression tests.

| Area | Change |
|---|---|
| Comments | Dividers, step narration and restatements removed; reasons (legal rule, measurement, pitfall) kept and shortened |
| Module docstrings | Every Python file starts with a summary and `Kontext: … \| Eingabe: … \| Ergebnis: …` |
| Types | Every function signature annotated; mypy in strict mode for backend/app |
| Lint | Rule set extended by S, SIM, RUF, PTH and ANN; `ruff format` applied to all files |
| Defects | Nine defects fixed, each with a test that fails on the old code |
| Environment | `requirements-dev.txt` with pinned versions; CI also checks formatting and types |
| Unchanged | File names, API function and field names, database, customer-facing text, `vokabular.py` word lists, README and operating manual |

## Removed

**Context:** Files and code with no function in the product. | **Input:** Search for unused functions, fields, imports and for references in README, operating manual and CI. | **Output:** 3 files and 11 unused code locations removed; no document refers to them.

| What | Reason |
|---|---|
| `scripts/upload_to_github.py` | Helper for publishing the repository, not part of the product |
| `scripts/tests_workflow.yml` | Copy of `.github/workflows/tests.yml`, only used by `upload_to_github.py` |
| `scripts/testserver.sh` | Hard-coded local path, not documented anywhere; the README shows the start command (`scripts/mitenv.py`) |
| `Sitzung.restsekunden` (auth.py) | Never read |
| `Pruefung.protokoll_art` (guardrails.py) | Set, never read |
| `Treffer.aehnlichkeit` and its collection in `_fusion` (search.py) | Set, never read |
| `TeileSuche.suchen` (search.py) | Never called |
| `staemme()` (vokabular.py) | Never called; word lists untouched |
| Parameters `begriff`, `stand`, `text` of the reply helpers (dialog.py) | Never used in the body |
| `erwartet_marke`, `erwartet_modell` (bench/anfragen.py) | Filled, never evaluated |
| `BLAU`, `BLAU_HELL`, `BLAU_TIEF`, `ROT` (bench/stil.py) | Never used |
| Duplicate part-number check (bench/testdaten.py) | Could never trigger with a running number |
| Parameter `suche` of `messen()` (bench/qualitaet.py) | Never used |
| `PYTHONPATH` assignment, `__import__("os")` (scripts/einrichten.py) | No effect at runtime, or needlessly indirect |
| Imports inside functions (main.py, auth.py, embeddings.py, lager_hochladen.py, conftest.py, test_sync.py) | Moved to the top or duplicated; `fastembed` stays a deliberate late import |
| Unused imports in four test files | Previously hidden by a rule exception |
| 350 comment lines (32 of them with `upload_to_github.py`) | Dividers, step narration, restatements of the code |

## Fixed defects

**Context:** Only defects that a test can demonstrate; every regression test fails on the old code, one extra test guards the unchanged part-number search. | **Input:** Review of input limits, key comparison, error responses, headers and file parsing. | **Output:** Nine defects fixed, 14 new tests.

| Defect | Effect before | Fix | Regression test |
|---|---|---|---|
| Sync key with a non-ASCII character | `hmac.compare_digest` on text raises `TypeError`: response 500 and an incident entry instead of 401 | Compare as bytes, one shared check for both sync endpoints | `test_sicherheit.py::test_sync_schluessel_mit_umlaut_ergibt_401_statt_500` |
| Invalid year in the click interview | `"abc"`, `"²"`, `"2005-2008"`, `2005.5` or `99999999999` caused a 500 response | A year counts only with 1 to 4 digits; otherwise it is treated as missing and the step is offered again | `test_api.py::test_interview_mit_ungueltigem_baujahr_fragt_erneut` (5 cases) |
| Interview state without a size limit | Public endpoint without rate limit accepted any number of fields | At most 10 fields, otherwise 422 | `test_sicherheit.py::test_interview_mit_zu_vielen_feldern_wird_abgewiesen` |
| Rate limiter never cleaned up | A visitor's window only empties on that visitor's next request; the clean-up deleted only empty windows, so almost never. Memory grew without bound, and above 10,000 visitors every request scanned 5,000 entries | Expired windows are removed | `test_sicherheit.py::test_mengenbremse_raeumt_abgelaufene_fenster` |
| Widget was never cached | The header middleware overwrote `Cache-Control: public, max-age=3600` of `/widget.js` with `no-store` | `no-store` only when the response sets no value of its own | `test_api.py::test_widget_wird_zwischengespeichert` |
| CSV parsing changed global state | When delimiter detection failed, `csv.excel.delimiter` was changed for the whole process | Delimiter applies to this reader only | `test_sync.py::test_csv_erkennung_veraendert_keinen_globalen_dialekt` |
| JSON delivery with a non-object | An element such as `42` raised a second error inside the error handling: whole sync aborted with 500 | Row is reported as rejected, part number `?` | `test_sync.py::test_zeile_ohne_objekt_wird_gemeldet_statt_abbruch` |
| Button "Ich habe eine Teilenummer" | Answered "Dazu finde ich im Moment kein passendes Teil" and was logged as unmet demand for purchasing; the existing reply `nummer_hinweis` was unreachable | A short message containing "Teilenummer" without digits gets the existing hint text (wording unchanged); with a number the search runs as before | `test_api.py::test_teilenummer_knopf_gibt_hinweis_statt_fehlanzeige`, `test_api.py::test_nummer_im_text_wird_weiter_gesucht` |
| `einrichten.py --verkaeufe` without `--beispiele` | Silently did nothing, although the docstring showed this call | Clear error message, exit code 2 | `test_skripte.py::test_einrichten_verkaeufe_ohne_beispiele_wird_abgelehnt` |

| Checked, no finding | Reason |
|---|---|
| SQL built from strings | `search.py` only interpolates module constants; all values are parameters |
| Session and cookies | No cookie; the session token travels in a header, HMAC check with `compare_digest` |
| Password | scrypt hash, `compare_digest`, failed-attempt lock stored in the database |
| CORS | Only `ALLOWED_ORIGINS`, without credentials |
| Error responses | 500 without internal details (existing test) |
| Timeouts on outbound calls | OpenAI 30 s, upload script 900 s, database pool 15 s |

## Refactoring without behaviour change

**Context:** Readability and checkability without changing replies or interfaces. | **Input:** All Python modules. | **Output:** Shorter, clearly typed functions; comparing all string literals old against new shows no change in customer-facing text.

| Location | Before | After |
|---|---|---|
| `main.py` state | `Optional` fields, 22 accesses without a check | Fixed types, set at start-up |
| `main.py` endpoints | `Depends`/`Header` as default values, key check duplicated | `Annotated`, one check `sync_schluessel`, admin check via `dependencies` |
| `main.py` date conversion | Same expression four times | `_json_tauglich()` |
| `main.py` interview state | Cleaning inside the endpoint | `stand_bereinigen()`, testable on its own |
| `dialog.py` reply selection | Eleven `if` branches | Mapping intent → method |
| `dialog.py` relaxation texts | Mutable class attribute | Module constant, wording identical |
| `search.py` | Access to private catalogue fields | Public method `Katalog.wortschatz()` |
| `search.py` `Filter.kopie` | Copy via `__dict__` and `setattr` | `dataclasses.replace` |
| `shipping.py` holidays | Date list with names as comments | Named tables `FESTE_FEIERTAGE`, `TAGE_NACH_OSTERSONNTAG` |
| `db.py` | Connection without row type | `Connection[DictRow]`, therefore checkable |
| `auth.py` | `except Exception` for hash and session | Only the error types that can actually occur |
| `sync.py` | `int(round(...))`, `md5` without marker | `round(...)`, `md5(..., usedforsecurity=False)` (change detection, no security purpose) |
| `vokabular.py` | Helper set built by a module-level loop, `set.add` trick | Set expression and `dict.fromkeys`; word lists untouched |
| Tests | Untyped fixtures, holiday names as comments | Typed fixtures, named data instead of comments |

## Figures before and after

**Context:** Measured on the state before and after the clean-up. | **Input:** ruff 0.16.10, mypy 2.4.0, pytest 9.1.1, PostgreSQL 16 with pgvector. | **Output:** All checks without findings, 14 more tests.

| Figure | Before | After |
|---|---|---|
| Tests | 140 passed | 154 passed |
| Lint rule set | E, F, W, I, UP, B, C4 | plus S, SIM, RUF, PTH, ANN |
| Findings with S, SIM, RUF, PTH | 246 | 0 |
| `ruff format --check` | 31 files differ | 0 |
| mypy `backend/app` | 43 errors (`disallow_untyped_defs` only) | 0 errors in strict mode |
| Comment lines overall | 433 of 7,078 (6.1 %) | 83 of 7,166 (1.2 %) |
| Files above 5 % comments | 16 | 0 |
| Modules with a context docstring | 0 of 37 | 37 of 37 |

### Comment ratio per file

Comment lines divided by non-blank lines; docstrings and `noqa` markers are not counted. Line counts partly grow because of `ruff format`.

| File | Before | After |
|---|---|---|
| `backend/app/auth.py` | 4 / 146 (2.7 %) | 1 / 148 (0.7 %) |
| `backend/app/config.py` | 0 / 104 (0.0 %) | 0 / 100 (0.0 %) |
| `backend/app/db.py` | 12 / 171 (7.0 %) | 3 / 166 (1.8 %) |
| `backend/app/dialog.py` | 26 / 535 (4.9 %) | 3 / 638 (0.5 %) |
| `backend/app/embeddings.py` | 1 / 117 (0.9 %) | 1 / 111 (0.9 %) |
| `backend/app/guardrails.py` | 6 / 90 (6.7 %) | 2 / 123 (1.6 %) |
| `backend/app/katalog.py` | 34 / 168 (20.2 %) | 7 / 139 (5.0 %) |
| `backend/app/kpi.py` | 5 / 241 (2.1 %) | 1 / 292 (0.3 %) |
| `backend/app/main.py` | 37 / 465 (8.0 %) | 6 / 455 (1.3 %) |
| `backend/app/passwort_hash.py` | 0 / 31 (0.0 %) | 0 / 31 (0.0 %) |
| `backend/app/search.py` | 33 / 316 (10.4 %) | 9 / 284 (3.2 %) |
| `backend/app/shipping.py` | 12 / 151 (7.9 %) | 0 / 154 (0.0 %) |
| `backend/app/sync.py` | 14 / 353 (4.0 %) | 5 / 403 (1.2 %) |
| `backend/app/vokabular.py` | 5 / 203 (2.5 %) | 2 / 178 (1.1 %) |
| `bench/anfragen.py` | 8 / 140 (5.7 %) | 0 / 119 (0.0 %) |
| `bench/architektur.py` | 22 / 346 (6.4 %) | 12 / 358 (3.4 %) |
| `bench/diagramme.py` | 1 / 194 (0.5 %) | 1 / 312 (0.3 %) |
| `bench/latenz.py` | 11 / 184 (6.0 %) | 3 / 187 (1.6 %) |
| `bench/qualitaet.py` | 1 / 164 (0.6 %) | 0 / 190 (0.0 %) |
| `bench/stil.py` | 3 / 50 (6.0 %) | 0 / 54 (0.0 %) |
| `bench/testdaten.py` | 6 / 208 (2.9 %) | 3 / 234 (1.3 %) |
| `scripts/einrichten.py` | 0 / 66 (0.0 %) | 0 / 77 (0.0 %) |
| `scripts/lager_hochladen.py` | 0 / 80 (0.0 %) | 0 / 76 (0.0 %) |
| `scripts/messwerte_einsetzen.py` | 1 / 175 (0.6 %) | 0 / 184 (0.0 %) |
| `scripts/mitenv.py` | 0 / 37 (0.0 %) | 0 / 36 (0.0 %) |
| `scripts/upload_to_github.py` | 32 / 419 (7.6 %) | removed |
| `tests/conftest.py` | 4 / 115 (3.5 %) | 1 / 141 (0.7 %) |
| `tests/oberflaeche.py` | 13 / 237 (5.5 %) | 2 / 266 (0.8 %) |
| `tests/test_api.py` | 5 / 123 (4.1 %) | 1 / 181 (0.6 %) |
| `tests/test_auth.py` | 3 / 48 (6.2 %) | 0 / 48 (0.0 %) |
| `tests/test_guardrails.py` | 1 / 44 (2.3 %) | 0 / 55 (0.0 %) |
| `tests/test_sicherheit.py` | 4 / 93 (4.3 %) | 1 / 120 (0.8 %) |
| `tests/test_skripte.py` | – | 0 / 18 (0.0 %) |
| `tests/test_suche.py` | 4 / 97 (4.1 %) | 0 / 118 (0.0 %) |
| `tests/test_sync.py` | 5 / 146 (3.4 %) | 1 / 200 (0.5 %) |
| `tests/test_versand.py` | 14 / 54 (25.9 %) | 0 / 71 (0.0 %) |
| `tests/test_vokabular.py` | 4 / 56 (7.1 %) | 1 / 69 (1.4 %) |
| `widget/teilethuns-widget.js` | 102 / 911 (11.2 %) | 17 / 827 (2.1 %) |
| **Total** | **433 / 7078 (6.1 %)** | **83 / 7166 (1.2 %)** |

## Rule exceptions

**Context:** Every exception is justified in `pyproject.toml`. | **Input:** Findings of the extended rule set. | **Output:** Nine justified exceptions, each limited to a file or rule.

| Rule | Scope | Reason |
|---|---|---|
| E501 | everywhere | Long customer texts are not wrapped; `ruff format` sets the code lines |
| RUF001–RUF003 | everywhere | Dashes and typographic characters are intended customer text |
| ANN401 | everywhere | Raw rows from stock files and JSON are untyped until validated |
| S101, S105, S603 | `tests/` | `assert` in pytest, fixed test-database secrets, fixed script call |
| S608 | `backend/app/search.py`, `bench/` | Only module constants and numbers are interpolated |
| S311 | `bench/` | Randomness for reproducible test data |
| E402 | `bench/`, `scripts/` | Stand-alone scripts set `sys.path` first |
| S310 | `scripts/` | The operator sets the target URL |
| S603 | `scripts/mitenv.py` | Deliberately starts the given command |

## Environment and CI

**Context:** Same tool versions locally and in GitHub Actions. | **Input:** `backend/requirements.txt` (unchanged, pinned), `.github/workflows/tests.yml`. | **Output:** One install file for development and CI, two additional check steps.

| File | Change |
|---|---|
| `requirements-dev.txt` | New: includes `backend/requirements.txt`, plus `mypy==2.4.0`, `pytest==9.1.1`, `ruff==0.16.10` |
| `.github/workflows/tests.yml` | Installs `requirements-dev.txt`; runs `ruff check .`, `ruff format --check .`, `mypy`; comment about the deleted upload script removed |
| `pyproject.toml` | `[tool.mypy]` (Python 3.11, strict mode, `disallow_untyped_defs`, `backend/app` only), extended ruff rules with justified exceptions |

## Final check

**Context:** Check of the finished state before the commit. | **Input:** Working tree of this commit. | **Output:** All checks passed; the base image came from a mirror because of the Docker Hub pull limit.

| Check | Result |
|---|---|
| `ruff check .` | Passed |
| `ruff format --check .` | Passed, 42 files (37 Python, 5 Markdown) |
| `mypy` (strict, `backend/app`) | 0 errors in 15 files |
| `pytest` against PostgreSQL 16 with pgvector | 154 passed |
| Fresh Python 3.12 environment from `requirements-dev.txt` | Install and all checks passed |
| Regression tests against the old code | 13 of 13 fail there |
| `node --check widget/teilethuns-widget.js` | Passed; widget changes are comments only |
| `docker build --network=host .` | Docker Hub answered 429 (pull limit). The same build with `python:3.12-slim` from `mirror.gcr.io` succeeded; the container starts, `/api/health` reports "bereit", `/widget.js` sends `public, max-age=3600` |
| Comparing all string literals old against new | Customer texts and word lists unchanged |
| Search for secrets, local paths, debug output, TODO | No finding; only placeholders in `.env.example` and the CI test-database login |

## Followed up

**Context:** Small findings at the edge of the clean-up | **Input:** Observations made during the work | **Output:** fixed

| Point | Status |
|---|---|
| The README block "automatische Tests" still says 140 tests | Done |
| README "Selbst ausprobieren": `python -m app.passwort_hash` only finds the package inside `backend/` | Done |
| `EBAY_SHOP_URL` is read but never used | Done |
| Behind a proxy (e.g. Render) the service only sees the proxy address; rate limit and failed-login lock are then shared by all visitors with the same browser | Done |
| `passwort_hash.py` says "Diese zwei Zeilen" but prints three | Done |
| `docs/LINKEDIN.md` holds marketing text in the product repository | Kept locally, not in the repository |
