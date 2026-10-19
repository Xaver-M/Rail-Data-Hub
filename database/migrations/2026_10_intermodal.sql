-- database/migrations/2026_10_intermodal.sql
-- Intermodal extension: operator -> mode mapping + comparison view.
--
-- Run on the VM (from repo root):
--   docker exec -i rail_data_hub_db psql -U rail_user -d rail_data < database/migrations/2026_10_intermodal.sql
--
-- Design: price_observations (hypertable) is NOT altered. The transport mode
-- lives in a small lookup table, so no hypertable rewrite / compression issues.


-- ─────────────────────────────────────────────────────────────
-- 0. PRE-CHECK (run manually before deciding on routes)
-- ─────────────────────────────────────────────────────────────
-- a) Exact operator spellings in the DB (compare with the INSERT below!)
--    SELECT DISTINCT operator FROM price_observations ORDER BY 1;
--
-- b) Data volume and recency per candidate route and operator
--    SELECT route_id,
--           operator,
--           COUNT(*)                              AS n_obs,
--           COUNT(DISTINCT collected_at::date)    AS crawl_days,
--           MIN(collected_at)::date               AS first_day,
--           MAX(collected_at)::date               AS last_day,
--           COUNT(*) FILTER (WHERE collected_at > NOW() - INTERVAL '14 days') AS n_last_14d
--    FROM price_observations
--    WHERE route_id IN ('milan-rome', 'madrid-barcelona', 'barcelona-madrid',
--                       'paris-nice', 'paris-marseille', 'berlin-munich',
--                       'milan-bari', 'rome-bari')
--    GROUP BY route_id, operator
--    ORDER BY route_id, operator;


BEGIN;

-- ─────────────────────────────────────────────────────────────
-- 1. OPERATOR METADATA
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS operator_meta (
    operator      TEXT PRIMARY KEY,
    mode          TEXT NOT NULL CHECK (mode IN ('rail', 'bus', 'air')),
    display_name  TEXT,
    is_low_cost   BOOLEAN
);

INSERT INTO operator_meta (operator, mode, display_name, is_low_cost) VALUES
    -- rail / bus (check spellings against query 0a!)
    ('db',           'rail', 'Deutsche Bahn',            FALSE),
    ('db_parsebot',  'rail', 'Deutsche Bahn (ParseBot)', FALSE),
    ('flixtrain',    'rail', 'Flixtrain',                TRUE),
    ('flixbus',      'bus',  'FlixBus',                  TRUE),
    ('trenitalia',   'rail', 'Trenitalia',               FALSE),
    ('italo',        'rail', 'Italo',                    FALSE),
    ('ouigo_es',     'rail', 'OUIGO España',             TRUE),
    ('ouigo_fr',     'rail', 'OUIGO France',             TRUE),
    ('regiojet',     'rail', 'RegioJet',                 TRUE),
    ('ceske-drahy',  'rail', 'České dráhy',              FALSE),
    -- air
    ('ita_airways',  'air',  'ITA Airways',              FALSE),
    ('aeroitalia',   'air',  'Aeroitalia',               FALSE),
    ('iberia',       'air',  'Iberia',                   FALSE),
    ('vueling',      'air',  'Vueling',                  TRUE),
    ('air_europa',   'air',  'Air Europa',               FALSE),
    ('air_france',   'air',  'Air France',               FALSE),
    ('transavia',    'air',  'Transavia',                TRUE),
    ('easyjet',      'air',  'easyJet',                  TRUE),
    ('ryanair',      'air',  'Ryanair',                  TRUE),
    ('volotea',      'air',  'Volotea',                  TRUE)
ON CONFLICT (operator) DO NOTHING;


-- ─────────────────────────────────────────────────────────────
-- 2. DAILY INTERMODAL VIEW
-- ─────────────────────────────────────────────────────────────
-- One row per route x operator x fare_class x horizon x collection day x travel day.
-- Unknown operators (e.g. a new airline slug) show up as mode 'unknown'
-- -> add them to operator_meta.

CREATE OR REPLACE VIEW v_intermodal_daily AS
SELECT
    po.route_id,
    COALESCE(om.mode, 'unknown')                              AS mode,
    po.operator,
    po.fare_class,
    po.booking_horizon_days,
    (po.collected_at AT TIME ZONE 'Europe/Berlin')::date      AS collection_day,  -- crawler's local day, see dashboard/database.py
    (po.departure_at AT TIME ZONE 'Europe/Berlin')::date      AS travel_day,
    MIN(po.price_eur)                                         AS min_price_eur,
    AVG(po.price_eur)                                         AS avg_price_eur,
    COUNT(*)                                                  AS n_offers
FROM price_observations po
LEFT JOIN operator_meta om ON om.operator = po.operator
WHERE po.route_id IN ('milan-rome', 'madrid-barcelona', 'barcelona-madrid', 'paris-nice')
GROUP BY 1, 2, 3, 4, 5, 6, 7;

COMMIT;


-- ─────────────────────────────────────────────────────────────
-- 3. EXAMPLE ANALYSIS QUERY
-- ─────────────────────────────────────────────────────────────
-- Cheapest price per mode, averaged over collection days, per horizon.
-- Air uses the no-bag headline fare; swap to 'economy_cabinbag' for the
-- luggage-adjusted comparison.
--
--    SELECT route_id,
--           booking_horizon_days,
--           mode,
--           ROUND(AVG(min_price)::numeric, 4)  AS mean_min_price_eur,
--           COUNT(*)                           AS n_days
--    FROM (
--        SELECT route_id, mode, booking_horizon_days, collection_day, travel_day,
--               MIN(min_price_eur) AS min_price
--        FROM v_intermodal_daily
--        WHERE mode <> 'air' OR fare_class = 'economy_nobag'
--        GROUP BY route_id, mode, booking_horizon_days, collection_day, travel_day
--    ) t
--    GROUP BY route_id, booking_horizon_days, mode
--    ORDER BY route_id, booking_horizon_days, mode;
