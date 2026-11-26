-- New rail crawlers 11/2026 (crawlers/renfe, crawlers/pkp_intercity): operator metadata.
-- Run once: psql -U <user> -d rail_data -f database/migrations/2026_11_renfe_pkp.sql

INSERT INTO operator_meta (operator, mode, display_name, is_low_cost) VALUES
    ('renfe',         'rail', 'Renfe',         FALSE),
    ('pkp_intercity', 'rail', 'PKP Intercity', FALSE)
ON CONFLICT (operator) DO NOTHING;
