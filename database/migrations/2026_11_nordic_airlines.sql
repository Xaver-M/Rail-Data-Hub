-- Airlines on the Stockholm-Oslo flight corridor (config/flight_routes.py): operator metadata.
-- Run once: psql -U <user> -d rail_data -f database/migrations/2026_11_nordic_airlines.sql

INSERT INTO operator_meta (operator, mode, display_name, is_low_cost) VALUES
    ('sas',       'air', 'SAS',                 FALSE),
    ('norwegian', 'air', 'Norwegian',           TRUE),
    ('ethiopian', 'air', 'Ethiopian Airlines',  FALSE)
ON CONFLICT (operator) DO NOTHING;
