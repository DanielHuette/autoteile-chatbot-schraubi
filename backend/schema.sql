-- =====================================================================
--  Datenbankschema "Teile Thuns" - PostgreSQL 16 + pgvector >= 0.7
-- =====================================================================
--  Leitgedanke: Lagerbestand und Suchvektor liegen in DERSELBEN Zeile.
--  Eine Abfrage liefert Aehnlichkeit, Preis, Bestand und eBay-Status
--  gemeinsam. Es gibt keinen zweiten Datenspeicher, der veralten kann.
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- ---------------------------------------------------------------------
-- 1. Oeffentliche Teiledaten. Der Chatbot darf hier lesen.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS parts (
    id              BIGSERIAL PRIMARY KEY,
    sku             TEXT        NOT NULL UNIQUE,
    title           TEXT        NOT NULL,
    description     TEXT        NOT NULL DEFAULT '',
    brand           TEXT        NOT NULL,
    model           TEXT        NOT NULL,
    year_from       SMALLINT,
    year_to         SMALLINT,
    category        TEXT        NOT NULL,
    subcategory     TEXT        NOT NULL DEFAULT '',
    side            TEXT        NOT NULL DEFAULT '',          -- links/rechts/vorne/hinten
    condition       TEXT        NOT NULL DEFAULT 'gebraucht',
    price_cents     INTEGER     NOT NULL CHECK (price_cents >= 0),
    stock           INTEGER     NOT NULL DEFAULT 0 CHECK (stock >= 0),
    weight_grams    INTEGER     NOT NULL DEFAULT 1000 CHECK (weight_grams > 0),
    oem_numbers     TEXT[]      NOT NULL DEFAULT '{}',
    on_ebay         BOOLEAN     NOT NULL DEFAULT FALSE,
    ebay_url        TEXT        NOT NULL DEFAULT '',
    active          BOOLEAN     NOT NULL DEFAULT TRUE,
    search_text     TEXT        NOT NULL DEFAULT '',
    embedding       vector({EMBEDDING_DIM}),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Ein Teil, das nur auf eBay liegt, braucht einen Link dorthin.
    CONSTRAINT ebay_url_wenn_ebay CHECK (NOT on_ebay OR ebay_url <> '')
);

-- Bauteilname in einheitlicher Schreibweise. Lagerprogramme schreiben
-- mal "Rueckleuchte", mal "Rückleuchte", mal "RÜCKLEUCHTE" - gefiltert
-- wird deshalb nie auf dem Rohwert, sondern auf dieser Spalte. lower()
-- und replace() sind unveraenderlich und damit in einer generierten
-- Spalte erlaubt (unaccent waere es nicht).
ALTER TABLE parts
    ADD COLUMN IF NOT EXISTS subcategory_norm TEXT
    GENERATED ALWAYS AS (
        lower(replace(replace(replace(replace(replace(
            coalesce(subcategory,''),
            'ä','ae'),'ö','oe'),'ü','ue'),'Ä','ae'),'ß','ss'))
    ) STORED;

CREATE INDEX IF NOT EXISTS parts_subcategory_norm ON parts (subcategory_norm);

-- Volltext (deutsch) als generierte Spalte: keine Pflege, nie veraltet.
-- Die Vergleichsnummern bleiben hier bewusst aussen vor: array_to_string
-- ist in PostgreSQL nicht als unveraenderlich gekennzeichnet und damit in
-- einer generierten Spalte nicht erlaubt. Nummern werden ohnehin ueber
-- den eigenen Feldindex (parts_oem_gin) exakt gesucht - dort gehoeren
-- sie auch hin, denn eine Teilenummer will man exakt treffen, nicht
-- unscharf.
ALTER TABLE parts
    ADD COLUMN IF NOT EXISTS fts tsvector
    GENERATED ALWAYS AS (
        to_tsvector('german',
            coalesce(title,'') || ' ' || coalesce(description,'') || ' ' ||
            coalesce(brand,'') || ' ' || coalesce(model,'') || ' ' ||
            coalesce(category,'') || ' ' || coalesce(subcategory,'') || ' ' ||
            coalesce(side,''))
    ) STORED;

-- Vektorindex. HNSW, Kosinus-Abstand.
CREATE INDEX IF NOT EXISTS parts_embedding_hnsw
    ON parts USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS parts_fts_gin        ON parts USING gin (fts);
CREATE INDEX IF NOT EXISTS parts_title_trgm     ON parts USING gin (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS parts_brand_model    ON parts (brand, model);
CREATE INDEX IF NOT EXISTS parts_category       ON parts (category, subcategory);
CREATE INDEX IF NOT EXISTS parts_active_stock   ON parts (active, stock);
CREATE INDEX IF NOT EXISTS parts_oem_gin        ON parts USING gin (oem_numbers);

-- ---------------------------------------------------------------------
-- 2. Versandzonen. Liefergebiete, Kosten, Laufzeit in Werktagen.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS shipping_zones (
    country_code  CHAR(2) PRIMARY KEY,
    country_name  TEXT    NOT NULL,
    zone          TEXT    NOT NULL,
    cost_cents    INTEGER NOT NULL CHECK (cost_cents >= 0),
    days_min      SMALLINT NOT NULL CHECK (days_min > 0),
    days_max      SMALLINT NOT NULL CHECK (days_max >= days_min),
    bulky_surcharge_cents INTEGER NOT NULL DEFAULT 0
);

-- ---------------------------------------------------------------------
-- 3. Geschuetzte Betriebsdaten. NUR mit Admin-Sitzung lesbar.
--    Technisch durchgesetzt: eigene Datenbankrolle ohne Leserecht
--    fuer den Chat-Zugang (siehe unten).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sales (
    id            BIGSERIAL PRIMARY KEY,
    order_ref     TEXT        NOT NULL,
    part_sku      TEXT        NOT NULL,
    sold_at       TIMESTAMPTZ NOT NULL,
    quantity      INTEGER     NOT NULL CHECK (quantity > 0),
    revenue_cents BIGINT      NOT NULL CHECK (revenue_cents >= 0),
    channel       TEXT        NOT NULL CHECK (channel IN ('shop','ebay'))
);
CREATE INDEX IF NOT EXISTS sales_sold_at ON sales (sold_at DESC);
CREATE INDEX IF NOT EXISTS sales_channel ON sales (channel, sold_at DESC);

-- ---------------------------------------------------------------------
-- 4. Protokolle. EU-KI-Verordnung Art. 12/13: Nachvollziehbarkeit.
--    Es werden KEINE Namen, Mailadressen oder IP-Adressen gespeichert.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chat_events (
    id          BIGSERIAL PRIMARY KEY,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    session_hash CHAR(16)   NOT NULL,      -- gekuerzter Hash, nicht rueckrechenbar
    kind        TEXT        NOT NULL,      -- frage, treffer, kein_treffer, fehler, blockiert
    intent      TEXT        NOT NULL DEFAULT '',
    detail      TEXT        NOT NULL DEFAULT '',
    latency_ms  INTEGER
);
CREATE INDEX IF NOT EXISTS chat_events_created ON chat_events (created_at DESC);
CREATE INDEX IF NOT EXISTS chat_events_kind    ON chat_events (kind, created_at DESC);

CREATE TABLE IF NOT EXISTS sync_runs (
    id            BIGSERIAL PRIMARY KEY,
    started_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at   TIMESTAMPTZ,
    rows_received INTEGER NOT NULL DEFAULT 0,
    rows_upserted INTEGER NOT NULL DEFAULT 0,
    rows_rejected INTEGER NOT NULL DEFAULT 0,
    rows_deactivated INTEGER NOT NULL DEFAULT 0,
    status        TEXT    NOT NULL DEFAULT 'laufend',
    message       TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS admin_login_attempts (
    id         BIGSERIAL PRIMARY KEY,
    at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    client_key CHAR(16)    NOT NULL,
    success    BOOLEAN     NOT NULL
);
CREATE INDEX IF NOT EXISTS admin_attempts_key ON admin_login_attempts (client_key, at DESC);

-- ---------------------------------------------------------------------
-- 5. Rechtetrennung auf Datenbankebene.
--    Der Chat-Zugang kann 'sales' nicht lesen - auch dann nicht, wenn
--    der Anwendungscode einen Fehler hat. Zweite Schutzschicht.
-- ---------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'teilethuns_chat') THEN
        CREATE ROLE teilethuns_chat NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'teilethuns_admin') THEN
        CREATE ROLE teilethuns_admin NOLOGIN;
    END IF;
END $$;

GRANT SELECT ON parts, shipping_zones TO teilethuns_chat;
GRANT INSERT ON chat_events TO teilethuns_chat;
GRANT USAGE, SELECT ON SEQUENCE chat_events_id_seq TO teilethuns_chat;
REVOKE ALL ON sales FROM teilethuns_chat;

GRANT SELECT ON ALL TABLES IN SCHEMA public TO teilethuns_admin;

-- ---------------------------------------------------------------------
-- 6. Aufbewahrungsfrist: Protokolle nach 90 Tagen loeschen (DSGVO).
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION protokolle_aufraeumen() RETURNS void AS $$
BEGIN
    DELETE FROM chat_events WHERE created_at < now() - INTERVAL '90 days';
    DELETE FROM admin_login_attempts WHERE at < now() - INTERVAL '30 days';
    DELETE FROM sync_runs WHERE started_at < now() - INTERVAL '365 days';
END $$ LANGUAGE plpgsql;
