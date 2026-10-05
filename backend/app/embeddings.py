"""Einbettungen (Embeddings): Text wird in einen Zahlenvektor uebersetzt,
damit pgvector ähnliche Teile finden kann.

Drei Anbieter:

* ``local``    - mehrsprachiges Modell, laeuft auf dem eigenen Server.
                 Keine laufenden Kosten, keine Daten an Dritte. Standard.
* ``openai``   - Fremddienst, falls kein eigenes Modell gewuenscht ist.
* ``hashing``  - Notfall-Rueckfall und Testbetrieb ohne Modell. Rein
                 lexikalisch (Zeichen-Dreiergruppen), also tippfehlertolerant,
                 aber NICHT bedeutungsaehnlich. Nur für Tests und Messreihen.
"""
from __future__ import annotations

import hashlib
import math
import re
import threading
from collections.abc import Sequence
from typing import Protocol

_WORD = re.compile(r"[a-zA-Z0-9À-ɏ]+")


def normalisieren(text: str) -> str:
    """Kleinschreibung, deutsche Umlaute vereinheitlichen, Rauschen weg."""
    t = text.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        t = t.replace(a, b)
    return " ".join(_WORD.findall(t))


class EmbeddingProvider(Protocol):
    dim: int

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


def _l2(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0.0:
        return vec
    return [v / norm for v in vec]


class HashingEmbedding:
    """Hashing-Trick auf Zeichen-Dreiergruppen und Wortstaemme.

    Deterministisch, ohne Modell, ohne Netz. Liefert lexikalische
    Ähnlichkeit: "ruecklicht" und "rueklicht" landen nah beieinander,
    "Rückleuchte" nicht. Deshalb nur Rueckfall und Testbetrieb.
    """

    def __init__(self, dim: int = 384) -> None:
        if dim < 64:
            raise ValueError("dim zu klein")
        self.dim = dim

    def _features(self, text: str) -> list[str]:
        norm = normalisieren(text)
        feats: list[str] = []
        for wort in norm.split():
            feats.append("w:" + wort)
            if len(wort) > 5:
                feats.append("p:" + wort[:5])
            padded = f"^{wort}$"
            for i in range(len(padded) - 2):
                feats.append("t:" + padded[i : i + 3])
        return feats

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            vec = [0.0] * self.dim
            for feat in self._features(text):
                digest = hashlib.blake2b(feat.encode("utf-8"), digest_size=8).digest()
                idx = int.from_bytes(digest[:4], "big") % self.dim
                sign = 1.0 if digest[4] & 1 else -1.0
                weight = 2.0 if feat.startswith("w:") else 1.0
                vec[idx] += sign * weight
            out.append(_l2(vec))
        return out


class LocalEmbedding:
    """Mehrsprachiges Satzmodell auf dem eigenen Server (fastembed)."""

    def __init__(self, model_name: str, dim: int) -> None:
        from fastembed import TextEmbedding  # lazy: nur wenn wirklich genutzt

        self._model = TextEmbedding(model_name)
        self.dim = dim
        self._lock = threading.Lock()

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        with self._lock:
            raw = list(self._model.embed(list(texts)))
        vecs = [_l2([float(x) for x in v]) for v in raw]
        for v in vecs:
            if len(v) != self.dim:
                raise ValueError(
                    f"Modell liefert {len(v)} Dimensionen, erwartet {self.dim}. "
                    "EMBEDDING_DIM anpassen und Datenbank neu aufbauen."
                )
        return vecs


class OpenAIEmbedding:
    """Fremddienst. Nur aktiv, wenn EMBEDDING_PROVIDER=openai gesetzt ist."""

    def __init__(self, model_name: str, dim: int, api_key: str) -> None:
        import httpx

        self.dim = dim
        self._model = model_name
        self._client = httpx.Client(
            base_url="https://api.openai.com/v1",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        resp = self._client.post(
            "/embeddings", json={"model": self._model, "input": list(texts)}
        )
        resp.raise_for_status()
        data = sorted(resp.json()["data"], key=lambda d: d["index"])
        return [_l2([float(x) for x in d["embedding"]]) for d in data]


def build_provider(
    provider: str, model_name: str, dim: int, api_key: str | None = None
) -> EmbeddingProvider:
    if provider == "hashing":
        return HashingEmbedding(dim)
    if provider == "local":
        return LocalEmbedding(model_name, dim)
    if provider == "openai":
        if not api_key:
            raise ValueError("OPENAI_API_KEY fehlt für EMBEDDING_PROVIDER=openai")
        return OpenAIEmbedding(model_name or "text-embedding-3-small", dim, api_key)
    raise ValueError(f"Unbekannter Anbieter: {provider!r}")
