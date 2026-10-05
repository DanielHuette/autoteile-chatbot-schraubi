"""Anmeldung der Betriebsleitung.

Wichtig und bewusst so gebaut:

* Das Passwort wird NIE als Chatnachricht verschickt. Es geht über
  einen eigenen Endpunkt (/api/admin/login) und taucht daher nicht im
  Gespräschsverlauf, in der Chat-Protokolltabelle oder auf dem
  Bildschirm auf.
* Gespeichert wird nur ein scrypt-Hash. Aus ihm laesst sich das
  Passwort nicht zurückrechnen.
* Die Sitzung ist ein signiertes Kurzzeit-Merkmal (HMAC-SHA256) mit
  Ablaufzeit. Es wird serverseitig geprüft, nicht geglaubt.
* Nach mehreren Fehlversuchen wird der Zugang zeitweise gesperrt.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass

SCRYPT_N = 2**15
SCRYPT_R = 8
SCRYPT_P = 1
# OpenSSL begrenzt den Speicher für scrypt auf 32 MB. n=2**15, r=8
# braucht genau 32 MB, daher wird die Grenze ausdruecklich hochgesetzt.
SCRYPT_MAXMEM = 96 * 1024 * 1024


def hash_erzeugen(passwort: str) -> str:
    """Erzeugt den Wert für ADMIN_PASSWORD_HASH."""
    if len(passwort) < 12:
        raise ValueError("Das Passwort muss mindestens 12 Zeichen haben.")
    salt = os.urandom(16)
    key = hashlib.scrypt(
        passwort.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P,
        dklen=32, maxmem=SCRYPT_MAXMEM,
    )
    return f"$scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${base64.b64encode(salt).decode()}${base64.b64encode(key).decode()}"


def hash_pruefen(passwort: str, gespeichert: str) -> bool:
    try:
        _, verfahren, n, r, p, salt_b64, key_b64 = gespeichert.split("$")
        if verfahren != "scrypt":
            return False
        key = hashlib.scrypt(
            passwort.encode("utf-8"),
            salt=base64.b64decode(salt_b64),
            n=int(n), r=int(r), p=int(p), dklen=32, maxmem=SCRYPT_MAXMEM,
        )
        return hmac.compare_digest(key, base64.b64decode(key_b64))
    except Exception:
        return False


@dataclass
class Sitzung:
    rolle: str
    ablauf: int

    @property
    def restsekunden(self) -> int:
        return max(0, self.ablauf - int(time.time()))


class SitzungsVerwaltung:
    def __init__(self, secret: str, dauer_minuten: int = 30) -> None:
        self._secret = secret.encode("utf-8")
        self._dauer = dauer_minuten * 60
        # Zurueckgezogene Sitzungen (Abmeldung). Kurzlebig, daher im Speicher.
        self._widerrufen: set[str] = set()

    def ausstellen(self, rolle: str = "betreiber") -> tuple[str, int]:
        nutzlast = {
            "rolle": rolle,
            "exp": int(time.time()) + self._dauer,
            "jti": secrets.token_urlsafe(8),
        }
        roh = json.dumps(nutzlast, separators=(",", ":"), sort_keys=True).encode()
        teil1 = base64.urlsafe_b64encode(roh).rstrip(b"=")
        sig = hmac.new(self._secret, teil1, hashlib.sha256).digest()
        teil2 = base64.urlsafe_b64encode(sig).rstrip(b"=")
        return f"{teil1.decode()}.{teil2.decode()}", self._dauer

    def pruefen(self, token: str | None) -> Sitzung | None:
        if not token or "." not in token or len(token) > 512:
            return None
        teil1, _, teil2 = token.partition(".")
        try:
            sig_erwartet = hmac.new(self._secret, teil1.encode(), hashlib.sha256).digest()
            sig_gegeben = base64.urlsafe_b64decode(teil2 + "=" * (-len(teil2) % 4))
            if not hmac.compare_digest(sig_erwartet, sig_gegeben):
                return None
            roh = base64.urlsafe_b64decode(teil1 + "=" * (-len(teil1) % 4))
            daten = json.loads(roh)
        except Exception:
            return None
        if daten.get("jti") in self._widerrufen:
            return None
        if int(daten.get("exp", 0)) <= int(time.time()):
            return None
        return Sitzung(rolle=str(daten.get("rolle", "")), ablauf=int(daten["exp"]))

    def widerrufen(self, token: str | None) -> None:
        if not token or "." not in token:
            return
        try:
            teil1 = token.split(".", 1)[0]
            roh = base64.urlsafe_b64decode(teil1 + "=" * (-len(teil1) % 4))
            jti = json.loads(roh).get("jti")
            if jti:
                self._widerrufen.add(str(jti))
        except Exception:
            return


class Fehlversuchsbremse:
    """Sperrt einen Zugang nach zu vielen Fehlversuchen - in der Datenbank,
    damit die Sperre auch nach einem Neustart greift."""

    def __init__(self, db, max_versuche: int = 5, sperre_minuten: int = 15) -> None:
        self.db = db
        self.max_versuche = max_versuche
        self.sperre_minuten = sperre_minuten

    @staticmethod
    def client_key(roh: str) -> str:
        return hashlib.blake2b(roh.encode("utf-8"), digest_size=8).hexdigest()

    def gesperrt_bis(self, client_key: str) -> int:
        """Restsekunden der Sperre, 0 wenn offen."""
        with self.db.conn() as c:
            row = c.execute(
                """
                SELECT count(*) AS fehler,
                       max(at)  AS letzter
                  FROM admin_login_attempts
                 WHERE client_key = %s
                   AND NOT success
                   AND at > now() - make_interval(mins => %s)
                """,
                (client_key, self.sperre_minuten),
            ).fetchone()
        if not row or (row["fehler"] or 0) < self.max_versuche:
            return 0
        import datetime as dt

        bis = row["letzter"] + dt.timedelta(minutes=self.sperre_minuten)
        rest = (bis - dt.datetime.now(dt.UTC)).total_seconds()
        return max(0, int(rest))

    def vermerken(self, client_key: str, erfolg: bool) -> None:
        with self.db.conn() as c:
            c.execute(
                "INSERT INTO admin_login_attempts (client_key, success) VALUES (%s,%s)",
                (client_key, erfolg),
            )
            if erfolg:
                # Erfolgreiche Anmeldung raeumt die Fehlversuche weg.
                c.execute(
                    "DELETE FROM admin_login_attempts WHERE client_key = %s AND NOT success",
                    (client_key,),
                )
            c.commit()
