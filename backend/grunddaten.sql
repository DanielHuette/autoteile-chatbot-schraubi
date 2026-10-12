-- Grunddaten: Liefergebiete, Versandkosten, Laufzeiten.
-- Diese Werte darf der Betreiber anpassen. Sie sind die einzige Quelle
-- fuer die Versandauskunft des Chatbots - was hier steht, sagt der Bot.
-- Laufzeit in WERKTAGEN ab Versandtag.

INSERT INTO shipping_zones
    (country_code, country_name, zone, cost_cents, days_min, days_max, bulky_surcharge_cents)
VALUES
    ('DE', 'Deutschland',  'Inland',   695,  1, 2,  4900),
    ('AT', 'Oesterreich',  'EU-nah',  1290,  2, 4,  7900),
    ('NL', 'Niederlande',  'EU-nah',  1190,  2, 4,  7900),
    ('BE', 'Belgien',      'EU-nah',  1190,  2, 4,  7900),
    ('LU', 'Luxemburg',    'EU-nah',  1190,  2, 4,  7900),
    ('DK', 'Daenemark',    'EU-nah',  1390,  3, 5,  8900),
    ('FR', 'Frankreich',   'EU-West', 1490,  3, 5,  8900),
    ('CZ', 'Tschechien',   'EU-Ost',  1390,  3, 5,  8900),
    ('PL', 'Polen',        'EU-Ost',  1390,  3, 5,  8900),
    ('IT', 'Italien',      'EU-Sued', 1690,  4, 7, 10900),
    ('ES', 'Spanien',      'EU-Sued', 1890,  5, 8, 12900),
    ('SE', 'Schweden',     'EU-Nord', 1790,  4, 7, 10900),
    ('CH', 'Schweiz',      'Drittland', 2490, 4, 8, 14900)
ON CONFLICT (country_code) DO UPDATE SET
    country_name = EXCLUDED.country_name,
    zone         = EXCLUDED.zone,
    cost_cents   = EXCLUDED.cost_cents,
    days_min     = EXCLUDED.days_min,
    days_max     = EXCLUDED.days_max,
    bulky_surcharge_cents = EXCLUDED.bulky_surcharge_cents;
