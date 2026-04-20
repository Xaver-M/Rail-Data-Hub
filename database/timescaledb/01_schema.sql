CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS price_observations (
    id                  BIGSERIAL,
    collected_at        TIMESTAMPTZ         NOT NULL,
    departure_at        TIMESTAMPTZ         NOT NULL,
     arrival_at           TIMESTAMPTZ        NOT NULL,
    operator             TEXT               NOT NULL,
    origin_id            TEXT               NOT NULL,
    destination_id       TEXT               NOT NULL,
    origin_name          TEXT,
    destination_name     TEXT,
    train_number         TEXT,
    fare_class           TEXT,
    price_eur            NUMERIC(8,2)       NOT NULL,
    seats_available      INTEGER,
    currency_raw         TEXT,
    booking_horizon_days INTEGER,
    source_url           TEXT,
    raw_response         JSONB
);

SELECT create_hypertable('price_observations', 'collected_at',
    if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_operator
    ON price_observations (operator, collected_at DESC);

CREATE INDEX IF NOT EXISTS idx_route
    ON price_observations (origin_id, destination_id, collected_at DESC);

CREATE TABLE IF NOT EXISTS crawler_logs (
    id           BIGSERIAL,
    run_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    operator     TEXT         NOT NULL,
    status       TEXT         NOT NULL,
    records_written INTEGER,
    error_msg    TEXT
);
