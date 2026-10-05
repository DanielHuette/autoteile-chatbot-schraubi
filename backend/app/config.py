"""Zentrale Konfiguration. Alle Werte kommen aus Umgebungsvariablen.

Es gibt bewusst keine Vorgabewerte für Geheimnisse: fehlt ein Geheimnis,
startet der Dienst nicht. Das verhindert, dass eine Installation
versehentlich mit einem Beispielpasswort im Netz steht.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


class ConfigError(RuntimeError):
    """Konfiguration ist unvollstaendig oder unplausibel."""


def _req(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        raise ConfigError(
            f"Umgebungsvariable {name} fehlt. Siehe .env.example."
        )
    return val


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} muss eine ganze Zahl sein, ist: {raw!r}") from exc


def _list(name: str, default: tuple[str, ...] = ()) -> list[str]:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return list(default)
    return [p.strip() for p in raw.split(",") if p.strip()]


@dataclass(frozen=True)
class Settings:
    database_url: str
    admin_password_hash: str
    session_secret: str
    sync_api_key: str

    embedding_provider: str = "local"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dim: int = 384

    allowed_origins: list[str] = field(default_factory=list)
    shop_name: str = "Teile Thuns"
    ebay_shop_url: str = ""
    operator_email: str = ""
    operator_phone: str = ""

    admin_session_minutes: int = 30
    admin_max_attempts: int = 5
    admin_lockout_minutes: int = 15
    chat_rate_per_minute: int = 30
    max_message_chars: int = 500

    log_level: str = "INFO"
    incident_log_path: str = "./logs/vorfaelle.jsonl"

    @property
    def is_hashing_fallback(self) -> bool:
        return self.embedding_provider == "hashing"


def load_settings() -> Settings:
    provider = os.environ.get("EMBEDDING_PROVIDER", "local").strip() or "local"
    if provider not in {"local", "openai", "hashing"}:
        raise ConfigError(
            "EMBEDDING_PROVIDER muss 'local', 'openai' oder 'hashing' sein, "
            f"ist: {provider!r}"
        )

    dim_default = {"local": 384, "openai": 1536, "hashing": 384}[provider]
    settings = Settings(
        database_url=_req("DATABASE_URL"),
        admin_password_hash=_req("ADMIN_PASSWORD_HASH"),
        session_secret=_req("SESSION_SECRET"),
        sync_api_key=_req("SYNC_API_KEY"),
        embedding_provider=provider,
        embedding_model=os.environ.get("EMBEDDING_MODEL", "").strip()
        or Settings.embedding_model,
        embedding_dim=_int("EMBEDDING_DIM", dim_default),
        allowed_origins=_list("ALLOWED_ORIGINS"),
        shop_name=os.environ.get("SHOP_NAME", "").strip() or "Teile Thuns",
        ebay_shop_url=os.environ.get("EBAY_SHOP_URL", "").strip(),
        operator_email=os.environ.get("OPERATOR_EMAIL", "").strip(),
        operator_phone=os.environ.get("OPERATOR_PHONE", "").strip(),
        admin_session_minutes=_int("ADMIN_SESSION_MINUTES", 30),
        admin_max_attempts=_int("ADMIN_MAX_ATTEMPTS", 5),
        admin_lockout_minutes=_int("ADMIN_LOCKOUT_MINUTES", 15),
        chat_rate_per_minute=_int("CHAT_RATE_PER_MINUTE", 30),
        max_message_chars=_int("MAX_MESSAGE_CHARS", 500),
        log_level=os.environ.get("LOG_LEVEL", "INFO").strip().upper() or "INFO",
        incident_log_path=os.environ.get("INCIDENT_LOG_PATH", "").strip()
        or "./logs/vorfaelle.jsonl",
    )

    if len(settings.session_secret) < 32:
        raise ConfigError(
            "SESSION_SECRET muss mindestens 32 Zeichen lang sein. "
            "Erzeugen mit: python -c \"import secrets;print(secrets.token_urlsafe(48))\""
        )
    if len(settings.sync_api_key) < 24:
        raise ConfigError("SYNC_API_KEY muss mindestens 24 Zeichen lang sein.")
    if not settings.admin_password_hash.startswith("$"):
        raise ConfigError(
            "ADMIN_PASSWORD_HASH sieht nicht wie ein Hash aus. Es darf NIE das "
            "Klartextpasswort hier stehen. Hash erzeugen mit: "
            "python -m app.passwort_hash"
        )
    if not settings.allowed_origins:
        raise ConfigError(
            "ALLOWED_ORIGINS fehlt. Eintragen ist Pflicht: nur diese Webseiten "
            "duerfen den Chatbot aufrufen, z.B. https://www.ihr-shop.de"
        )
    return settings
