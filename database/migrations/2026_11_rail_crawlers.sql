-- New rail crawlers 11/2026 (crawlers/eurostar, crawlers/european_sleeper): operator metadata.
-- Run once: psql -U <user> -d rail_data -f database/migrations/2026_11_rail_crawlers.sql

INSERT INTO operator_meta (operator, mode, display_name, is_low_cost) VALUES
    ('eurostar',         'rail', 'Eurostar',         FALSE),
    ('european_sleeper', 'rail', 'European Sleeper', FALSE),
    ('sj',               'rail', 'SJ',               FALSE)
ON CONFLICT (operator) DO NOTHING;
