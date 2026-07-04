# dashboard/database.py
import os
import pandas as pd
import streamlit as st

# ─────────────────────────────────────────────────────────────
# Feste Schema-Konstanten (siehe price_observations Tabellenschema).
# Keine Laufzeit-Erkennung nötig — spart einen DB-Roundtrip pro Tab.
# ─────────────────────────────────────────────────────────────
DEP_COL = "departure_at"
ARR_COL = "arrival_at"


def get_db():
    """Nutzt das native Streamlit SQL-Verbindungsmanagement."""
    return st.connection("postgresql", type="sql")


# ─────────────────────────────────────────────────────────────
# Sidebar / Routenliste
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_route_list() -> pd.DataFrame:
    """Lädt NUR die Metadaten der Routen für die Sidebar. Blitzschnell dank TimescaleDB-Aggregation."""
    query = """
        SELECT
            origin_name,
            destination_name,
            route_id,
            COUNT(price_eur) as record_count,
            MAX(collected_at) as last_collected,
            ARRAY_AGG(DISTINCT operator) as operators
        FROM price_observations
        GROUP BY origin_name, destination_name, route_id
        ORDER BY record_count DESC;
    """
    db = get_db()
    df = db.query(query)
    df["record_count"] = pd.to_numeric(df["record_count"])
    df["label"] = df["origin_name"] + " → " + df["destination_name"]
    return df


@st.cache_data(ttl=3600)
def load_all_route_pairs() -> pd.DataFrame:
    """Alle distinct Origin/Destination-Paare, für Streckenvergleich-Dropdowns."""
    query = """
        SELECT DISTINCT origin_name, destination_name, route_id
        FROM price_observations
        WHERE origin_name IS NOT NULL AND destination_name IS NOT NULL
        ORDER BY origin_name, destination_name;
    """
    db = get_db()
    df = db.query(query)
    df["label"] = df["origin_name"] + " → " + df["destination_name"]
    return df


# ─────────────────────────────────────────────────────────────
# Overview
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=120)
def load_overview_kpis(origin, destination, days_back=30):
    """KPIs inkl. 7-Tage-Trend für die Overview-Kacheln."""
    query = """
        SELECT
            MIN(price_eur) as min_price,
            AVG(price_eur) as avg_price,
            COUNT(id) as total_obs,
            COUNT(DISTINCT operator) as n_operators,
            AVG(price_eur) FILTER (WHERE collected_at >= NOW() - INTERVAL '7 days') as recent_avg,
            AVG(price_eur) FILTER (WHERE collected_at <  NOW() - INTERVAL '7 days') as prior_avg
        FROM price_observations
        WHERE origin_name = :origin AND destination_name = :destination
          AND collected_at >= NOW() - INTERVAL '1 day' * :days_back
    """
    db = get_db()
    return db.query(query, params={"origin": origin, "destination": destination, "days_back": days_back})


@st.cache_data(ttl=120)
def load_timeline_data(origin, destination, days_back=30):
    """Preise pro Tag (MIN/AVG/MAX) und Operator für den Overview-Zeitverlauf."""
    query = """
        SELECT
            collected_at::date as col_date,
            operator,
            MIN(price_eur) as min_price,
            AVG(price_eur) as avg_price,
            MAX(price_eur) as max_price
        FROM price_observations
        WHERE origin_name = :origin AND destination_name = :destination
          AND collected_at >= NOW() - INTERVAL '1 day' * :days_back
        GROUP BY collected_at::date, operator
        ORDER BY col_date ASC;
    """
    db = get_db()
    df = db.query(query, params={"origin": origin, "destination": destination, "days_back": days_back})
    df["col_date"] = pd.to_datetime(df["col_date"])
    return df


@st.cache_data(ttl=300)
def load_price_range_by_operator(origin, destination):
    """Min/Avg/Max Preisspanne pro Operator (für Boxplot-artige Darstellung)."""
    query = """
        SELECT operator, MIN(price_eur) as price_min, AVG(price_eur) as price_avg, MAX(price_eur) as price_max,
               COUNT(id) as observations
        FROM price_observations
        WHERE origin_name = :origin AND destination_name = :destination
        GROUP BY operator;
    """
    db = get_db()
    return db.query(query, params={"origin": origin, "destination": destination})


@st.cache_data(ttl=300)
def load_departure_hour_counts(origin, destination):
    """Anzahl Verbindungen pro Abfahrtsstunde und Operator."""
    query = f"""
        SELECT operator, EXTRACT(HOUR FROM {DEP_COL}) as dep_hour, COUNT(id) as connection_count
        FROM price_observations
        WHERE origin_name = :origin AND destination_name = :destination
        GROUP BY operator, dep_hour
        ORDER BY dep_hour ASC;
    """
    db = get_db()
    return db.query(query, params={"origin": origin, "destination": destination})


@st.cache_data(ttl=300)
def load_fare_class_avg(origin, destination):
    """Durchschnittspreis pro Tarifklasse und Operator."""
    query = """
        SELECT operator, fare_class, AVG(price_eur) as avg_price, COUNT(id) as observations
        FROM price_observations
        WHERE origin_name = :origin AND destination_name = :destination
          AND fare_class IS NOT NULL AND fare_class != ''
        GROUP BY operator, fare_class;
    """
    db = get_db()
    return db.query(query, params={"origin": origin, "destination": destination})


# ─────────────────────────────────────────────────────────────
# Single-Trip-Modus (Overview)
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_available_departure_dates(origin, destination):
    query = f"""
        SELECT DISTINCT {DEP_COL}::date as dep_date, COUNT(id) as n
        FROM price_observations
        WHERE origin_name = :origin AND destination_name = :destination AND {DEP_COL} IS NOT NULL
        GROUP BY dep_date
        ORDER BY dep_date ASC;
    """
    db = get_db()
    df = db.query(query, params={"origin": origin, "destination": destination})
    df["dep_date"] = pd.to_datetime(df["dep_date"]).dt.date
    return df


@st.cache_data(ttl=120)
def load_trip_data(origin, destination, dep_date):
    """Alle Beobachtungen für eine konkrete Abfahrt (einzelnes Datum)."""
    query = f"""
        SELECT operator, train_number, {DEP_COL} as departure_at, collected_at,
               price_eur, booking_horizon_days, fare_class
        FROM price_observations
        WHERE origin_name = :origin AND destination_name = :destination
          AND {DEP_COL}::date = :dep_date
        ORDER BY collected_at ASC;
    """
    db = get_db()
    df = db.query(query, params={"origin": origin, "destination": destination, "dep_date": dep_date})
    for col in ["departure_at", "collected_at"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
    df["price_eur"] = pd.to_numeric(df["price_eur"], errors="coerce")
    df["booking_horizon_days"] = pd.to_numeric(df["booking_horizon_days"], errors="coerce")
    return df


# ─────────────────────────────────────────────────────────────
# Booking Horizon (nutzt die GESPEICHERTE Spalte, nicht EXTRACT!)
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_booking_horizon(origin, destination):
    query = """
        SELECT operator, booking_horizon_days,
               AVG(price_eur) as price_avg, MIN(price_eur) as price_min,
               COUNT(id) as observations
        FROM price_observations
        WHERE origin_name = :origin AND destination_name = :destination
          AND booking_horizon_days IS NOT NULL
          AND booking_horizon_days BETWEEN 0 AND 90
        GROUP BY operator, booking_horizon_days
        ORDER BY booking_horizon_days DESC;
    """
    db = get_db()
    return db.query(query, params={"origin": origin, "destination": destination})


# ─────────────────────────────────────────────────────────────
# Individual Train
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_train_numbers(origin, destination, operator):
    query = """
        SELECT DISTINCT train_number
        FROM price_observations
        WHERE origin_name = :origin AND destination_name = :destination
          AND operator = :operator AND train_number IS NOT NULL AND train_number != ''
        ORDER BY train_number ASC;
    """
    db = get_db()
    return db.query(query, params={"origin": origin, "destination": destination, "operator": operator})


@st.cache_data(ttl=180)
def load_single_train_data(origin, destination, operator, train_number):
    query = f"""
        SELECT operator, train_number, {DEP_COL} as departure_at, collected_at,
               price_eur, seats_available, booking_horizon_days, fare_class
        FROM price_observations
        WHERE origin_name = :origin AND destination_name = :destination
          AND operator = :operator AND train_number = :train_number
        ORDER BY collected_at DESC;
    """
    db = get_db()
    df = db.query(query, params={
        "origin": origin, "destination": destination,
        "operator": operator, "train_number": train_number,
    })
    for col in ["departure_at", "collected_at"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
    df["price_eur"] = pd.to_numeric(df["price_eur"], errors="coerce")
    df["seats_available"] = pd.to_numeric(df.get("seats_available"), errors="coerce")
    df["booking_horizon_days"] = pd.to_numeric(df["booking_horizon_days"], errors="coerce")
    return df


# ─────────────────────────────────────────────────────────────
# Time of Day
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_time_of_day(origin, destination, operator):
    query = f"""
        SELECT
            EXTRACT(HOUR   FROM {DEP_COL})       as dep_hour,
            (EXTRACT(ISODOW FROM {DEP_COL})::int - 1) as dep_dow,
            price_eur, seats_available
        FROM price_observations
        WHERE origin_name = :origin AND destination_name = :destination AND operator = :operator
          AND {DEP_COL} IS NOT NULL;
    """
    db = get_db()
    df = db.query(query, params={"origin": origin, "destination": destination, "operator": operator})
    df["dep_hour"] = pd.to_numeric(df["dep_hour"], errors="coerce").astype("Int64")
    df["dep_dow"]  = pd.to_numeric(df["dep_dow"], errors="coerce").astype("Int64")
    df["price_eur"] = pd.to_numeric(df["price_eur"], errors="coerce")
    df["seats_available"] = pd.to_numeric(df.get("seats_available"), errors="coerce")
    return df


# ─────────────────────────────────────────────────────────────
# Operator Comparison
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_operator_comparison_at_horizon(origin, destination, horizon_days):
    query = """
        SELECT operator,
               MIN(price_eur) as price_min, AVG(price_eur) as price_avg, MAX(price_eur) as price_max,
               AVG(seats_available) as seats_avg, COUNT(id) as observations
        FROM price_observations
        WHERE origin_name = :origin AND destination_name = :destination
          AND booking_horizon_days = :horizon_days
        GROUP BY operator;
    """
    db = get_db()
    return db.query(query, params={"origin": origin, "destination": destination, "horizon_days": horizon_days})


@st.cache_data(ttl=300)
def load_seats_by_horizon(origin, destination):
    query = """
        SELECT operator, booking_horizon_days, AVG(seats_available) as seats_avg
        FROM price_observations
        WHERE origin_name = :origin AND destination_name = :destination
          AND seats_available IS NOT NULL AND booking_horizon_days IS NOT NULL
        GROUP BY operator, booking_horizon_days;
    """
    db = get_db()
    return db.query(query, params={"origin": origin, "destination": destination})


@st.cache_data(ttl=300)
def load_route_horizon_curve(origin, destination):
    """Für Streckenvergleich: Preis je Horizont, basierend auf booking_horizon_days."""
    query = """
        SELECT booking_horizon_days,
               AVG(price_eur) as price_avg, MIN(price_eur) as price_min,
               COUNT(id) as observations
        FROM price_observations
        WHERE origin_name = :origin AND destination_name = :destination
          AND booking_horizon_days IS NOT NULL AND booking_horizon_days BETWEEN 0 AND 90
        GROUP BY booking_horizon_days
        ORDER BY booking_horizon_days ASC;
    """
    db = get_db()
    return db.query(query, params={"origin": origin, "destination": destination})


@st.cache_data(ttl=300)
def load_route_summary(origin, destination):
    query = """
        SELECT MIN(price_eur) as price_min, AVG(price_eur) as price_avg,
               COUNT(DISTINCT operator) as n_operators, COUNT(id) as observations
        FROM price_observations
        WHERE origin_name = :origin AND destination_name = :destination;
    """
    db = get_db()
    return db.query(query, params={"origin": origin, "destination": destination})


# ─────────────────────────────────────────────────────────────
# Normalized prices (€/km, €/h)
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=86400)
def load_distances() -> pd.DataFrame:
    """Lädt die Distanzdaten relativ aus dem config-Ordner im Hauptverzeichnis."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base_dir, "config", "route_distances.csv")
    try:
        dist = pd.read_csv(path)
        dist.columns = dist.columns.str.strip()
        dist = dist[dist["haversine_km"] != "NA"].copy()
        dist["haversine_km"] = pd.to_numeric(dist["haversine_km"], errors="coerce")
        return dist[["route_id", "haversine_km"]].dropna()
    except Exception:
        return pd.DataFrame(columns=["route_id", "haversine_km"])


@st.cache_data(ttl=300)
def load_normalized_price_data(origin, destination):
    """Preis + Fahrzeit je Beobachtung mit gespeichertem booking_horizon_days (nicht neu berechnet)."""
    query = f"""
        SELECT
            operator,
            booking_horizon_days,
            price_eur,
            is_direct,
            EXTRACT(EPOCH FROM ({ARR_COL} - {DEP_COL})) / 3600.0 as travel_h
        FROM price_observations
        WHERE origin_name = :origin AND destination_name = :destination
          AND {DEP_COL} IS NOT NULL AND {ARR_COL} IS NOT NULL
          AND booking_horizon_days IS NOT NULL AND booking_horizon_days BETWEEN 0 AND 90;
    """
    db = get_db()
    df = db.query(query, params={"origin": origin, "destination": destination})
    df["price_eur"] = pd.to_numeric(df["price_eur"], errors="coerce")
    df["travel_h"]  = pd.to_numeric(df["travel_h"], errors="coerce")
    df["booking_horizon_days"] = pd.to_numeric(df["booking_horizon_days"], errors="coerce").astype(int)
    df["is_direct"] = df["is_direct"].map({True: True, False: False, "t": True, "f": False})
    # Nur plausible Fahrzeiten (15 min – 24 h)
    df = df[(df["travel_h"] >= 0.25) & (df["travel_h"] <= 24)]
    return df


# ─────────────────────────────────────────────────────────────
# Crawler Status
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=120)
def load_crawler_overview():
    query = """
        SELECT
            COUNT(id) as total_records,
            COUNT(DISTINCT operator) as n_operators,
            COUNT(DISTINCT route_id) as n_routes,
            MAX(collected_at) as last_collected
        FROM price_observations;
    """
    db = get_db()
    return db.query(query)


@st.cache_data(ttl=120)
def load_crawler_stats_by_operator():
    query = """
        SELECT
            operator,
            COUNT(id) as records,
            MAX(collected_at) as last_collected,
            COUNT(DISTINCT route_id) as routes,
            AVG(price_eur) as avg_price
        FROM price_observations
        GROUP BY operator
        ORDER BY records DESC;
    """
    db = get_db()
    df = db.query(query)
    df["records"] = pd.to_numeric(df["records"])
    df["routes"]  = pd.to_numeric(df["routes"])
    df["avg_price"] = pd.to_numeric(df["avg_price"])
    return df


@st.cache_data(ttl=120)
def load_crawler_daily_counts(days_back=30):
    query = """
        SELECT collected_at::date as col_date, operator, COUNT(id) as records
        FROM price_observations
        WHERE collected_at >= NOW() - INTERVAL '1 day' * :days_back
        GROUP BY collected_at::date, operator
        ORDER BY col_date ASC;
    """
    db = get_db()
    df = db.query(query, params={"days_back": days_back})
    df["col_date"] = pd.to_datetime(df["col_date"])
    df["records"] = pd.to_numeric(df["records"])
    return df


@st.cache_data(ttl=120)
def load_crawler_health(days_back=7):
    """Für die 7-Tage-Ampel: an wie vielen der letzten N Tage hat jeder Operator Daten geliefert,
    und wie viele Records im Schnitt pro Tag."""
    query = """
        SELECT operator, collected_at::date as col_date, COUNT(id) as records
        FROM price_observations
        WHERE collected_at >= NOW() - INTERVAL '1 day' * :days_back
        GROUP BY operator, collected_at::date;
    """
    db = get_db()
    df = db.query(query, params={"days_back": days_back})
    df["records"] = pd.to_numeric(df["records"])
    return df