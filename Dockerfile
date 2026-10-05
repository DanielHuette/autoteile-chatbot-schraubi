# Teile Thuns - Auskunftshelfer
# Ein Abbild, das ueberall laeuft: Render, Railway, Fly, Hetzner, eigener Server.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Abhaengigkeiten zuerst: so wird diese Schicht beim Codeaendern
# nicht neu gebaut.
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY widget/ ./widget/
COPY scripts/ ./scripts/

# Das Einbettungsmodell wird beim Bauen heruntergeladen, nicht beim
# ersten Kundenkontakt. Sonst wartet der erste Besucher 30 Sekunden.
RUN python -c "from fastembed import TextEmbedding; \
    TextEmbedding('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')" \
    || echo "Modell wird beim Start geladen"

# Kein Betrieb als Hauptbenutzer.
RUN useradd --create-home --uid 10001 schraubi && chown -R schraubi:schraubi /app
USER schraubi

ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
  CMD python -c "import urllib.request,os,sys; \
    sys.exit(0 if urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",8000)}/api/health', timeout=4).status==200 else 1)"

CMD ["sh", "-c", "uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port ${PORT:-8000}"]
