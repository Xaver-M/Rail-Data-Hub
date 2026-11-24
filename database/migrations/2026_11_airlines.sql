-- Airlines from the IRG flight corridors 11/2026 (config/flight_routes.py): operator metadata.
-- Run once: psql -U <user> -d rail_data -f database/migrations/2026_11_airlines.sql

INSERT INTO operator_meta (operator, mode, display_name, is_low_cost) VALUES
    ('austrian',          'air', 'Austrian Airlines', FALSE),
    ('british_airways',   'air', 'British Airways',   FALSE),
    ('brussels_airlines', 'air', 'Brussels Airlines', FALSE),
    ('klm',               'air', 'KLM',               FALSE),
    ('lot',               'air', 'LOT',               FALSE),
    ('tarom',             'air', 'TAROM',             FALSE),
    ('wizz_air',          'air', 'Wizz Air',          TRUE)
ON CONFLICT (operator) DO NOTHING;
