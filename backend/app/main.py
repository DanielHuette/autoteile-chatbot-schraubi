"""HTTP-Schnittstelle (FastAPI).

Aufbau der Zugaenge:

  /api/chat          Kundenchat. Oeffentlich, mengenbegrenzt.
  /api/interview     Klick-Interview. Oeffentlich.
  /api/versand       Liefergebiete. Oeffentlich.
  /api/admin/login   Anmeldung der Betriebsleitung. EIGENER Endpunkt -
                     das Passwort laeuft nie durch den Chat.
  /api/admin/frage   Betriebszahlen. Nur mit gueltiger Sitzung.
  /api/sync          Lagerabgleich. Nur mit Schnittstellenschluessel.
  /api/ki-hinweis    Transparenzangaben nach EU-KI-Verordnung.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
import pathlib
import time
from collections import deque
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from .auth import Fehlversuchsbremse, SitzungsVerwaltung, hash_pruefen
from .config import load_settings
from .db import Database
from .dialog import Gespraech, sitzungs_hash
from .embeddings import build_provider
from .guardrails import pruefen as regeln_pruefen
from .kpi import Kennzahlen
from .search import TeileSuche
from .shipping import Versand
from .sync import Abgleich, datei_lesen

log = logging.getLogger("teilethuns")

WIDGET_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "widget"


# ---------------------------------------------------------------------
# Mengenbegrenzung. Bewusst einfach (im Speicher, pro Prozess):
# ein Shop dieser Größe laeuft auf einem Prozess. Wird später
# skaliert, kommt hier Redis hinein – die Schnittstelle bleibt.
# ---------------------------------------------------------------------
class Mengenbremse:
    def __init__(self, pro_minute: int) -> None:
        self.pro_minute = pro_minute
        self._fenster: dict[str, deque[float]] = {}

    def erlaubt(self, key: str) -> bool:
        jetzt = time.monotonic()
        fenster = self._fenster.setdefault(key, deque())
        while fenster and jetzt - fenster[0] > 60:
            fenster.popleft()
        if len(fenster) >= self.pro_minute:
            return False
        fenster.append(jetzt)
        if len(self._fenster) > 10_000:  # Speicher deckeln
            for k in list(self._fenster)[:5_000]:
                if not self._fenster[k]:
                    del self._fenster[k]
        return True


class Zustand:
    settings: Any = None
    db: Database | None = None
    gespraech: Gespraech | None = None
    kennzahlen: Kennzahlen | None = None
    abgleich: Abgleich | None = None
    sitzungen: SitzungsVerwaltung | None = None
    bremse_login: Fehlversuchsbremse | None = None
    bremse_chat: Mengenbremse | None = None


Z = Zustand()


def vorfall_protokollieren(art: str, meldung: str, zusatz: dict | None = None) -> None:
    """Fehlerprotokoll als Datei – unabhaengig von der Datenbank, damit
    auch ein Datenbankausfall nachlesbar bleibt (EU-KI-Verordnung Art. 12)."""
    try:
        pfad = pathlib.Path(Z.settings.incident_log_path)
        pfad.parent.mkdir(parents=True, exist_ok=True)
        eintrag = {
            "zeit": dt.datetime.now(dt.UTC).isoformat(),
            "art": art,
            "meldung": meldung[:2000],
            **(zusatz or {}),
        }
        with pfad.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(eintrag, ensure_ascii=False) + "\n")
    except Exception:
        log.exception("Vorfallsprotokoll nicht schreibbar")


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = load_settings()
    logging.basicConfig(
        level=getattr(logging, s.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    Z.settings = s
    Z.db = Database(s.database_url, s.embedding_dim)
    if os.environ.get("APPLY_SCHEMA", "1") == "1":
        Z.db.apply_schema()
    embedder = build_provider(
        s.embedding_provider, s.embedding_model, s.embedding_dim,
        os.environ.get("OPENAI_API_KEY"),
    )
    suche = TeileSuche(Z.db, embedder)
    versand = Versand(Z.db)
    Z.gespraech = Gespraech(Z.db, suche, versand, s)
    Z.kennzahlen = Kennzahlen(Z.db)
    Z.abgleich = Abgleich(Z.db, embedder)
    Z.sitzungen = SitzungsVerwaltung(s.session_secret, s.admin_session_minutes)
    Z.bremse_login = Fehlversuchsbremse(Z.db, s.admin_max_attempts, s.admin_lockout_minutes)
    Z.bremse_chat = Mengenbremse(s.chat_rate_per_minute)
    log.info(
        "Bereit. Einbettungen: %s (%s Dimensionen)%s",
        s.embedding_provider, s.embedding_dim,
        "  ACHTUNG: Rueckfallverfahren ohne Bedeutungssuche!" if s.is_hashing_fallback else "",
    )
    try:
        yield
    finally:
        if Z.db:
            Z.db.close()


app = FastAPI(
    title="Teile Thuns – Auskunftshelfer",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,       # Keine oeffentliche Schnittstellen-Dokumentation.
    redoc_url=None,
    openapi_url=None,
)


@app.middleware("http")
async def schutz_kopfzeilen(request: Request, call_next):
    try:
        antwort: Response = await call_next(request)
    except HTTPException:
        raise
    except Exception as exc:
        vorfall_protokollieren("unbehandelter_fehler", repr(exc), {"pfad": request.url.path})
        log.exception("Unbehandelter Fehler auf %s", request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "blasen": [
                    "Entschuldigung, bei mir ist gerade etwas schiefgelaufen.",
                    "Bitte versuchen Sie es in einem Moment noch einmal – oder wenden Sie "
                    "sich direkt an den Shop.",
                ],
                "art": "fehler",
            },
        )
    antwort.headers["X-Content-Type-Options"] = "nosniff"
    antwort.headers["X-Frame-Options"] = "DENY"
    antwort.headers["Referrer-Policy"] = "no-referrer"
    antwort.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    antwort.headers["Cache-Control"] = "no-store"
    return antwort


def _cors_setup() -> None:
    # Muss nach dem Laden der Einstellungen passieren; FastAPI erlaubt
    # das Hinzufuegen nur vor dem Start, daher wird hier die Umgebung
    # direkt gelesen.
    erlaubt = [
        o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=erlaubt,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Admin-Token", "X-Sync-Key"],
        max_age=600,
    )


_cors_setup()


# ---------------------------------------------------------------------
# Datenmodelle
# ---------------------------------------------------------------------
class ChatAnfrage(BaseModel):
    # Keine harte Laengengrenze: wer versehentlich einen ganzen Absatz
    # einfuegt, soll keine Fehlermeldung bekommen, sondern eine Antwort.
    # Gekuerzt wird serverseitig auf MAX_MESSAGE_CHARS; gegen Missbrauch
    # wirken Mengenbremse und die Groessengrenze des Webservers.
    nachricht: str = Field(default="", max_length=20000)
    sitzung: str = Field(default="anonym", max_length=64)


class InterviewAnfrage(BaseModel):
    stand: dict[str, Any] = Field(default_factory=dict)
    sitzung: str = Field(default="anonym", max_length=64)


class LoginAnfrage(BaseModel):
    passwort: str = Field(min_length=1, max_length=256)


class AdminFrage(BaseModel):
    frage: str = Field(default="", max_length=500)


def _client_key(request: Request) -> str:
    # Nur ein gekuerzter Hash, keine gespeicherte IP-Adresse.
    roh = (request.client.host if request.client else "?") + "|" + request.headers.get(
        "user-agent", ""
    )[:120]
    return Fehlversuchsbremse.client_key(roh)


def betreiber_sitzung(x_admin_token: str | None = Header(default=None)) -> bool:
    if not x_admin_token or not Z.sitzungen:
        return False
    return Z.sitzungen.pruefen(x_admin_token) is not None


def nur_betreiber(x_admin_token: str | None = Header(default=None)) -> str:
    sitzung = Z.sitzungen.pruefen(x_admin_token) if Z.sitzungen else None
    if sitzung is None:
        raise HTTPException(status_code=401, detail="Nicht angemeldet oder Sitzung abgelaufen")
    return x_admin_token or ""


# ---------------------------------------------------------------------
# Oeffentliche Endpunkte
# ---------------------------------------------------------------------
@app.get("/api/health")
def health() -> dict[str, Any]:
    try:
        daten = Z.db.healthcheck() if Z.db else {}
        return {
            "status": "bereit",
            "zeit": dt.datetime.now(dt.UTC).isoformat(),
            "einbettung": Z.settings.embedding_provider,
            "dimensionen": Z.settings.embedding_dim,
            **{k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in daten.items()},
        }
    except Exception as exc:
        vorfall_protokollieren("health_fehler", repr(exc))
        raise HTTPException(status_code=503, detail="Datenbank nicht erreichbar") from exc


@app.get("/api/ki-hinweis")
def ki_hinweis() -> dict[str, Any]:
    """Transparenzangaben nach Artikel 50 der EU-KI-Verordnung."""
    s = Z.settings
    return {
        "ist_ki": True,
        "betreiber": s.shop_name,
        "zweck": "Auskunft zu gebrauchten Autoteilen, Versandkosten und Lieferzeiten.",
        "funktionsweise": (
            "Das System durchsucht den Lagerbestand mit zwei Verfahren: einer "
            "Bedeutungssuche (Vektorsuche in PostgreSQL mit pgvector) und einer "
            "Wortsuche. Antworten werden aus festen Textvorlagen gebildet, in die "
            "Werte aus der Datenbank eingesetzt werden. Es wird kein frei "
            "formulierender Text erzeugt."
        ),
        "keine_automatisierte_entscheidung": (
            "Es werden keine Entscheidungen über Personen getroffen. Es findet kein "
            "Profiling statt."
        ),
        "daten": (
            "Es werden keine Namen, E-Mail-Adressen oder IP-Adressen gespeichert. "
            "Zur Fehlersuche wird je Anfrage die Art des Vorgangs und ein "
            "nicht rueckrechenbarer Sitzungsschluessel für 90 Tage protokolliert."
        ),
        "mensch_erreichbar": {"telefon": s.operator_phone, "email": s.operator_email},
        "grenzen": (
            "Der Assistent gibt keine Einbauanleitungen, keine Rechtsberatung und "
            "keine Auskunft zu Betriebsdaten des Shops."
        ),
    }


@app.get("/api/versand/zonen")
def versand_zonen() -> dict[str, Any]:
    zonen = Versand(Z.db).zonen()
    return {
        "laender": [
            {
                "code": z["country_code"],
                "name": z["country_name"],
                "kosten_euro": round(z["cost_cents"] / 100, 2),
                "werktage_min": z["days_min"],
                "werktage_max": z["days_max"],
                "sperrgut_zuschlag_euro": round(z["bulky_surcharge_cents"] / 100, 2),
            }
            for z in zonen
        ]
    }


@app.post("/api/chat")
def chat(
    anfrage: ChatAnfrage,
    request: Request,
    ist_betreiber: bool = Depends(betreiber_sitzung),
) -> dict[str, Any]:
    beginn = time.perf_counter()
    if not Z.bremse_chat.erlaubt(_client_key(request)):
        raise HTTPException(
            status_code=429,
            detail="Zu viele Anfragen in kurzer Zeit. Bitte einen Moment warten.",
        )

    text = (anfrage.nachricht or "").strip()
    if len(text) > Z.settings.max_message_chars:
        text = text[: Z.settings.max_message_chars]
    sh = sitzungs_hash(anfrage.sitzung)

    # Schutzregeln vor allem anderen.
    pruefung = regeln_pruefen(text, ist_betreiber)
    if pruefung.blockiert:
        Z.db.log_event(sh, "blockiert", pruefung.grund)
        return {
            "blasen": [pruefung.antwort],
            "knoepfe": [{"text": "Teil suchen", "aktion": "interview_start"}],
            "art": "blockiert",
            "absicht": pruefung.grund,
            "teile": [], "interview": None, "hinweis": "", "tabelle": [],
        }

    # Angemeldete Betriebsleitung: Zahlenfragen gehen an die Kennzahlen.
    if ist_betreiber:
        from .kpi import absicht_erkennen

        if absicht_erkennen(text) != "uebersicht" or any(
            w in text.lower() for w in ("umsatz", "zahlen", "lager", "bericht", "uebersicht")
        ):
            auskunft = Z.kennzahlen.beantworten(text)
            Z.db.log_event(sh, "betreiber_auskunft", auskunft.absicht)
            return {
                "blasen": [auskunft.text],
                "knoepfe": [
                    {"text": "Umsatz heute", "aktion": "frage:Umsatz heute"},
                    {"text": "Bestseller 30 Tage", "aktion": "frage:Was sind die Topseller im Monat?"},
                    {"text": "Suchen ohne Treffer", "aktion": "frage:Welche Suchen hatten keine Treffer?"},
                    {"text": "Lagerbestand", "aktion": "frage:Wie ist der Lagerbestand?"},
                ],
                "art": "betreiber",
                "absicht": auskunft.absicht,
                "tabelle": auskunft.tabelle,
                "teile": [], "interview": None,
                "hinweis": f"Zeitraum: {auskunft.zeitraum}. Diese Angaben sind nur für Sie sichtbar.",
            }

    try:
        antwort = Z.gespraech.antworten(text)
    except Exception as exc:
        vorfall_protokollieren("chat_fehler", repr(exc), {"laenge": len(text)})
        Z.db.log_event(sh, "fehler", "chat", repr(exc)[:200])
        raise

    dauer = int((time.perf_counter() - beginn) * 1000)
    art = "treffer" if antwort.teile else ("kein_treffer" if antwort.art == "kein_treffer" else "frage")
    # Bei fehlenden Treffern wird der Suchtext protokolliert – daraus
    # entsteht die Nachfrageliste für den Einkauf.
    Z.db.log_event(sh, art, antwort.absicht, text if art == "kein_treffer" else "", dauer)
    return antwort.as_dict()


@app.post("/api/interview")
def interview(anfrage: InterviewAnfrage) -> dict[str, Any]:
    erlaubt = {"marke", "modell", "jahr", "kategorie", "bauteil"}
    stand = {
        k: (int(v) if k == "jahr" and str(v).strip().isdigit() else str(v)[:80])
        for k, v in (anfrage.stand or {}).items()
        if k in erlaubt and v not in (None, "")
    }
    antwort = Z.gespraech.interview(stand)
    Z.db.log_event(sitzungs_hash(anfrage.sitzung), "interview", antwort.absicht)
    return antwort.as_dict()


# ---------------------------------------------------------------------
# Betriebsleitung
# ---------------------------------------------------------------------
@app.post("/api/admin/login")
def admin_login(anfrage: LoginAnfrage, request: Request) -> dict[str, Any]:
    key = _client_key(request)
    rest = Z.bremse_login.gesperrt_bis(key)
    if rest > 0:
        raise HTTPException(
            status_code=429,
            detail=f"Zu viele Fehlversuche. Bitte {rest // 60 + 1} Minuten warten.",
        )
    if not hash_pruefen(anfrage.passwort, Z.settings.admin_password_hash):
        Z.bremse_login.vermerken(key, False)
        vorfall_protokollieren("login_fehlversuch", "falsches Passwort", {"client": key})
        # Absichtlich dieselbe, knappe Meldung – sie verraet nichts.
        raise HTTPException(status_code=401, detail="Passwort stimmt nicht.")
    Z.bremse_login.vermerken(key, True)
    token, dauer = Z.sitzungen.ausstellen("betreiber")
    return {
        "token": token,
        "gueltig_sekunden": dauer,
        "hinweis": (
            "Betriebsleitung angemeldet. Dieser Verlauf ist getrennt und wird beim "
            "Abmelden verworfen. Kunden sehen davon nichts."
        ),
    }


@app.post("/api/admin/logout")
def admin_logout(token: str = Depends(nur_betreiber)) -> dict[str, str]:
    Z.sitzungen.widerrufen(token)
    return {"status": "abgemeldet"}


@app.post("/api/admin/frage")
def admin_frage(anfrage: AdminFrage, token: str = Depends(nur_betreiber)) -> dict[str, Any]:
    auskunft = Z.kennzahlen.beantworten(anfrage.frage or "uebersicht")
    return auskunft.as_dict()


@app.get("/api/admin/betriebslage")
def admin_betriebslage(token: str = Depends(nur_betreiber)) -> dict[str, Any]:
    """Alles auf einen Blick: Bestand, letzter Abgleich, Fehler, Nachfragelücken."""
    with Z.db.conn() as c:
        letzte_syncs = [
            dict(r)
            for r in c.execute(
                """SELECT id, started_at, finished_at, rows_received, rows_upserted,
                          rows_rejected, rows_deactivated, status, message
                     FROM sync_runs ORDER BY started_at DESC LIMIT 5"""
            ).fetchall()
        ]
    return {
        "bestand": {
            k: (v.isoformat() if hasattr(v, "isoformat") else v)
            for k, v in Z.db.healthcheck().items()
        },
        "letzte_abgleiche": [
            {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in r.items()}
            for r in letzte_syncs
        ],
        "betrieb": Z.kennzahlen.betrieb(7, 0, "letzte 7 Tage").as_dict(),
        "nachfrageluecken": Z.kennzahlen.luecken(30, 0, "letzte 30 Tage").as_dict(),
    }


# ---------------------------------------------------------------------
# Lagerabgleich
# ---------------------------------------------------------------------
@app.post("/api/sync")
async def sync(
    request: Request,
    datei: UploadFile | None = None,
    x_sync_key: str | None = Header(default=None),
    vollabgleich: bool = False,
) -> dict[str, Any]:
    import hmac

    if not x_sync_key or not hmac.compare_digest(x_sync_key, Z.settings.sync_api_key):
        raise HTTPException(status_code=401, detail="Schnittstellenschluessel fehlt oder stimmt nicht")

    if datei is not None:
        rohdaten = await datei.read()
        name = datei.filename or ""
    else:
        rohdaten = await request.body()
        name = ""

    if not rohdaten:
        raise HTTPException(status_code=400, detail="Keine Daten empfangen")
    if len(rohdaten) > 64 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Datei größer als 64 MB")

    try:
        zeilen = datei_lesen(rohdaten, name)
    except Exception as exc:
        vorfall_protokollieren("sync_dateifehler", repr(exc), {"dateiname": name})
        raise HTTPException(status_code=400, detail=f"Datei nicht lesbar: {exc}") from exc

    try:
        ergebnis = Z.abgleich.ausfuehren(zeilen, vollabgleich=vollabgleich)
        # Der Fahrzeug- und Bauteilkatalog wird aus dem Bestand
        # abgeleitet. Nach einem Abgleich ist er veraltet.
        Z.gespraech.suche.katalog.verwerfen()
    except Exception as exc:
        vorfall_protokollieren("sync_fehler", repr(exc))
        raise HTTPException(
            status_code=500, detail="Abgleich fehlgeschlagen, Protokoll prüfen"
        ) from exc

    return ergebnis.as_dict()


@app.get("/api/sync/letzter")
def sync_letzter(x_sync_key: str | None = Header(default=None)) -> dict[str, Any]:
    import hmac

    if not x_sync_key or not hmac.compare_digest(x_sync_key, Z.settings.sync_api_key):
        raise HTTPException(status_code=401, detail="Schnittstellenschluessel fehlt oder stimmt nicht")
    with Z.db.conn() as c:
        row = c.execute(
            "SELECT * FROM sync_runs ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
    if not row:
        return {"status": "noch kein Abgleich gelaufen"}
    return {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in dict(row).items()}


# ---------------------------------------------------------------------
# Widget ausliefern
# ---------------------------------------------------------------------
@app.get("/widget.js")
def widget_js() -> FileResponse:
    pfad = WIDGET_DIR / "teilethuns-widget.js"
    if not pfad.exists():
        raise HTTPException(status_code=404, detail="Widget nicht gefunden")
    return FileResponse(
        pfad,
        media_type="application/javascript; charset=utf-8",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.get("/", response_class=PlainTextResponse)
def wurzel() -> str:
    return (
        "Teile Thuns – Auskunftshelfer laeuft.\n"
        "Einbindung in die Webseite:\n"
        '  <script src="DIESE-ADRESSE/widget.js" defer></script>\n'
    )
