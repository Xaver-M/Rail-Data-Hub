# dashboard/database.py
import os
import pandas as pd
import streamlit as st

# ─────────────────────────────────────────────────────────────
# Schema-Konstanten
# ─────────────────────────────────────────────────────────────
DEP_COL = "departure_at"
ARR_COL = "arrival_at"

_SNAPSHOT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "snapshot.csv"
)

# ─────────────────────────────────────────────────────────────
# Offline-Modus: DB-Check + Snapshot
# ─────────────────────────────────────────────────────────────
@st.cache_resource
def _check_db_available() -> bool:
    """Prüft einmalig beim Start ob die DB erreichbar ist."""
    try:
        db = st.connection("postgresql", type="sql")
        db.query("SELECT 1", ttl=0)
        return True
    except Exception:
        return False


def is_offline_mode() -> bool:
    return not _check_db_available()


@st.cache_data(ttl=3600)
def _load_snapshot() -> pd.DataFrame:
    """Lädt den lokalen CSV-Snapshot als Fallback."""
    if not os.path.exists(_SNAPSHOT_PATH):
        st.error(
            f"Offline-Modus aktiv, aber kein Snapshot gefunden unter:\n`{_SNAPSHOT_PATH}`\n\n"
            "Bitte `data/snapshot.csv` im Projektordner ablegen."
        )
        return pd.DataFrame()
    df = pd.read_csv(_SNAPSHOT_PATH, low_memory=False)
    for col in ["collected_at", "departure_at", "arrival_at"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")
    df["price_eur"] = pd.to_numeric(df["price_eur"], errors="coerce")
    df["booking_horizon_days"] = pd.to_numeric(df["booking_horizon_days"], errors="coerce")
    return df


def _snap() -> pd.DataFrame:
    """Kurzform für _load_snapshot()."""
    return _load_snapshot()


def _route(df: pd.DataFrame, origin: str, destination: str) -> pd.DataFrame:
    """Filtert Snapshot auf eine Route."""
    return df[
        (df["origin_name"] == origin) &
        (df["destination_name"] == destination)
    ]


# ─────────────────────────────────────────────────────────────
# DB-Verbindung
# ─────────────────────────────────────────────────────────────
def get_db():
    try:
        return st.connection("postgresql", type="sql")
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────
# Sidebar / Routenliste
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_route_list() -> pd.DataFrame:
    if is_offline_mode():
        df = _snap()
        if df.empty:
            return pd.DataFrame()
        agg = (df.groupby(["origin_name", "destination_name", "route_id"])
               .agg(
                   record_count=("price_eur", "count"),
                   last_collected=("collected_at", "max"),
               )
               .reset_index())
        agg["operators"] = (
            df.groupby(["origin_name", "destination_name", "route_id"])["operator"]
            .apply(lambda x: list(x.unique()))
            .values
        )
        agg = agg.sort_values("record_count", ascending=False)
        agg["label"] = agg["origin_name"] + " → " + agg["destination_name"]
        return agg

    query = """
        SELECT
            origin_name, destination_name, route_id,
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
    if is_offline_mode():
        df = _snap()
        if df.empty:
            return pd.DataFrame()
        result = (df[["origin_name", "destination_name", "route_id"]]
                  .dropna()
                  .drop_duplicates()
                  .sort_values(["origin_name", "destination_name"]))
        result["label"] = result["origin_name"] + " → " + result["destination_name"]
        return result

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
    if is_offline_mode():
        df = _route(_snap(), origin, destination)
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days_back)
        df = df[df["collected_at"] >= cutoff]
        if df.empty:
            return pd.DataFrame()
        recent = df[df["collected_at"] >= pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=7)]["price_eur"].mean()
        prior  = df[df["collected_at"] <  pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=7)]["price_eur"].mean()
        return pd.DataFrame([{
            "min_price":    df["price_eur"].min(),
            "avg_price":    df["price_eur"].mean(),
            "total_obs":    len(df),
            "n_operators":  df["operator"].nunique(),
            "recent_avg":   recent,
            "prior_avg":    prior,
        }])

    query = """
        SELECT
            MIN(price_eur) as min_price, AVG(price_eur) as avg_price,
            COUNT(id) as total_obs, COUNT(DISTINCT operator) as n_operators,
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
    if is_offline_mode():
        df = _route(_snap(), origin, destination)
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days_back)
        df = df[df["collected_at"] >= cutoff].copy()
        df["col_date"] = df["collected_at"].dt.date
        result = (df.groupby(["col_date", "operator"])
                  .agg(min_price=("price_eur", "min"),
                       avg_price=("price_eur", "mean"),
                       max_price=("price_eur", "max"))
                  .reset_index()
                  .sort_values("col_date"))
        result["col_date"] = pd.to_datetime(result["col_date"])
        return result

    query = """
        SELECT collected_at::date as col_date, operator,
               MIN(price_eur) as min_price, AVG(price_eur) as avg_price, MAX(price_eur) as max_price
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
    if is_offline_mode():
        df = _route(_snap(), origin, destination)
        return (df.groupby("operator")
                .agg(price_min=("price_eur", "min"),
                     price_avg=("price_eur", "mean"),
                     price_max=("price_eur", "max"),
                     observations=("price_eur", "count"))
                .reset_index())

    query = """
        SELECT operator, MIN(price_eur) as price_min, AVG(price_eur) as price_avg,
               MAX(price_eur) as price_max, COUNT(id) as observations
        FROM price_observations
        WHERE origin_name = :origin AND destination_name = :destination
        GROUP BY operator;
    """
    db = get_db()
    return db.query(query, params={"origin": origin, "destination": destination})


@st.cache_data(ttl=300)
def load_departure_hour_counts(origin, destination):
    if is_offline_mode():
        df = _route(_snap(), origin, destination).copy()
        df["dep_hour"] = pd.to_datetime(df[DEP_COL], errors="coerce").dt.hour
        return (df.groupby(["operator", "dep_hour"])
                .size().reset_index(name="connection_count")
                .sort_values("dep_hour"))

    query = f"""
        SELECT operator, EXTRACT(HOUR FROM {DEP_COL}) as dep_hour, COUNT(id) as connection_count
        FROM price_observations
        WHERE origin_name = :origin AND destination_name = :destination
        GROUP BY operator, dep_hour ORDER BY dep_hour ASC;
    """
    db = get_db()
    return db.query(query, params={"origin": origin, "destination": destination})


@st.cache_data(ttl=300)
def load_fare_class_avg(origin, destination):
    if is_offline_mode():
        df = _route(_snap(), origin, destination)
        df = df[df["fare_class"].notna() & (df["fare_class"] != "")]
        return (df.groupby(["operator", "fare_class"])
                .agg(avg_price=("price_eur", "mean"),
                     observations=("price_eur", "count"))
                .reset_index())

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
# Single-Trip-Modus
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_available_departure_dates(origin, destination):
    if is_offline_mode():
        df = _route(_snap(), origin, destination).copy()
        df["dep_date"] = pd.to_datetime(df[DEP_COL], errors="coerce").dt.date
        result = (df.groupby("dep_date").size().reset_index(name="n")
                  .sort_values("dep_date"))
        result["dep_date"] = pd.to_datetime(result["dep_date"]).dt.date
        return result

    query = f"""
        SELECT DISTINCT {DEP_COL}::date as dep_date, COUNT(id) as n
        FROM price_observations
        WHERE origin_name = :origin AND destination_name = :destination AND {DEP_COL} IS NOT NULL
        GROUP BY dep_date ORDER BY dep_date ASC;
    """
    db = get_db()
    df = db.query(query, params={"origin": origin, "destination": destination})
    df["dep_date"] = pd.to_datetime(df["dep_date"]).dt.date
    return df


@st.cache_data(ttl=120)
def load_trip_data(origin, destination, dep_date):
    if is_offline_mode():
        df = _route(_snap(), origin, destination).copy()
        df["_dep_date"] = pd.to_datetime(df[DEP_COL], errors="coerce").dt.date
        df = df[df["_dep_date"] == dep_date].drop(columns=["_dep_date"])
        df = df.rename(columns={DEP_COL: "departure_at"})
        for col in ["departure_at", "collected_at"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        df["price_eur"] = pd.to_numeric(df["price_eur"], errors="coerce")
        df["booking_horizon_days"] = pd.to_numeric(df["booking_horizon_days"], errors="coerce")
        return df.sort_values("collected_at")

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
# Booking Horizon
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_booking_horizon(origin, destination):
    if is_offline_mode():
        df = _route(_snap(), origin, destination)
        df = df[df["booking_horizon_days"].notna() &
                df["booking_horizon_days"].between(0, 90)]
        return (df.groupby(["operator", "booking_horizon_days"])
                .agg(price_avg=("price_eur", "mean"),
                     price_min=("price_eur", "min"),
                     observations=("price_eur", "count"))
                .reset_index()
                .sort_values("booking_horizon_days", ascending=False))

    query = """
        SELECT operator, booking_horizon_days,
               AVG(price_eur) as price_avg, MIN(price_eur) as price_min, MAX(price_eur) as price_max,
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
    if is_offline_mode():
        df = _route(_snap(), origin, destination)
        df = df[(df["operator"] == operator) &
                df["train_number"].notna() & (df["train_number"] != "")]
        return pd.DataFrame({"train_number": sorted(df["train_number"].unique())})

    query = """
        SELECT DISTINCT train_number FROM price_observations
        WHERE origin_name = :origin AND destination_name = :destination
          AND operator = :operator AND train_number IS NOT NULL AND train_number != ''
        ORDER BY train_number ASC;
    """
    db = get_db()
    return db.query(query, params={"origin": origin, "destination": destination, "operator": operator})


@st.cache_data(ttl=180)
def load_single_train_data(origin, destination, operator, train_number):
    if is_offline_mode():
        df = _route(_snap(), origin, destination)
        df = df[(df["operator"] == operator) & (df["train_number"] == train_number)].copy()
        df = df.rename(columns={DEP_COL: "departure_at"})
        for col in ["departure_at", "collected_at"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        df["price_eur"] = pd.to_numeric(df["price_eur"], errors="coerce")
        df["seats_available"] = pd.to_numeric(df.get("seats_available"), errors="coerce")
        df["booking_horizon_days"] = pd.to_numeric(df["booking_horizon_days"], errors="coerce")
        return df.sort_values("collected_at", ascending=False)

    query = f"""
        SELECT operator, train_number, {DEP_COL} as departure_at, collected_at,
               price_eur, seats_available, booking_horizon_days, fare_class, is_direct
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
    if is_offline_mode():
        df = _route(_snap(), origin, destination)
        df = df[(df["operator"] == operator) & df[DEP_COL].notna()].copy()
        dep = pd.to_datetime(df[DEP_COL], errors="coerce")
        df["dep_hour"] = dep.dt.hour
        df["dep_dow"]  = dep.dt.dayofweek
        df["price_eur"] = pd.to_numeric(df["price_eur"], errors="coerce")
        df["seats_available"] = pd.to_numeric(df.get("seats_available"), errors="coerce")
        return df[["dep_hour", "dep_dow", "price_eur", "seats_available"]]

    query = f"""
        SELECT
            EXTRACT(HOUR   FROM {DEP_COL}) as dep_hour,
            (EXTRACT(ISODOW FROM {DEP_COL})::int - 1) as dep_dow,
            price_eur, seats_available
        FROM price_observations
        WHERE origin_name = :origin AND destination_name = :destination
          AND operator = :operator AND {DEP_COL} IS NOT NULL;
    """
    db = get_db()
    df = db.query(query, params={"origin": origin, "destination": destination, "operator": operator})
    df["dep_hour"] = pd.to_numeric(df["dep_hour"], errors="coerce").astype("Int64")
    df["dep_dow"]  = pd.to_numeric(df["dep_dow"],  errors="coerce").astype("Int64")
    df["price_eur"] = pd.to_numeric(df["price_eur"], errors="coerce")
    df["seats_available"] = pd.to_numeric(df.get("seats_available"), errors="coerce")
    return df


# ─────────────────────────────────────────────────────────────
# Operator Comparison
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_operator_comparison_at_horizon(origin, destination, horizon_days):
    if is_offline_mode():
        df = _route(_snap(), origin, destination)
        df = df[df["booking_horizon_days"] == horizon_days]
        return (df.groupby("operator")
                .agg(price_min=("price_eur", "min"),
                     price_avg=("price_eur", "mean"),
                     price_max=("price_eur", "max"),
                     seats_avg=("seats_available", "mean"),
                     observations=("price_eur", "count"))
                .reset_index())

    query = """
        SELECT operator,
               MIN(price_eur) as price_min, AVG(price_eur) as price_avg,
               MAX(price_eur) as price_max, AVG(seats_available) as seats_avg,
               COUNT(id) as observations
        FROM price_observations
        WHERE origin_name = :origin AND destination_name = :destination
          AND booking_horizon_days = :horizon_days
        GROUP BY operator;
    """
    db = get_db()
    return db.query(query, params={"origin": origin, "destination": destination, "horizon_days": horizon_days})


@st.cache_data(ttl=300)
def load_seats_by_horizon(origin, destination):
    if is_offline_mode():
        df = _route(_snap(), origin, destination)
        df = df[df["seats_available"].notna() & df["booking_horizon_days"].notna()]
        return (df.groupby(["operator", "booking_horizon_days"])
                .agg(seats_avg=("seats_available", "mean"))
                .reset_index())

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
    if is_offline_mode():
        df = _route(_snap(), origin, destination)
        df = df[df["booking_horizon_days"].notna() &
                df["booking_horizon_days"].between(0, 90)]
        return (df.groupby("booking_horizon_days")
                .agg(price_avg=("price_eur", "mean"),
                     price_min=("price_eur", "min"),
                     observations=("price_eur", "count"))
                .reset_index()
                .sort_values("booking_horizon_days"))

    query = """""
        SELECT booking_horizon_days,
               AVG(price_eur) as price_avg, MIN(price_eur) as price_min,
               COUNT(id) as observations
        FROM price_observations
        WHERE origin_name = :origin AND destination_name = :destination
          AND booking_horizon_days IS NOT NULL AND booking_horizon_days BETWEEN 0 AND 90
        GROUP BY booking_horizon_days ORDER BY booking_horizon_days ASC;
    """
    db = get_db()
    return db.query(query, params={"origin": origin, "destination": destination})


@st.cache_data(ttl=300)
def load_route_summary(origin, destination):
    if is_offline_mode():
        df = _route(_snap(), origin, destination)
        return pd.DataFrame([{
            "price_min":    df["price_eur"].min(),
            "price_avg":    df["price_eur"].mean(),
            "n_operators":  df["operator"].nunique(),
            "observations": len(df),
        }])

    query = """
        SELECT MIN(price_eur) as price_min, AVG(price_eur) as price_avg,
               COUNT(DISTINCT operator) as n_operators, COUNT(id) as observations
        FROM price_observations
        WHERE origin_name = :origin AND destination_name = :destination;
    """
    db = get_db()
    return db.query(query, params={"origin": origin, "destination": destination})


# ─────────────────────────────────────────────────────────────
# Normalized prices
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=86400)
def load_distances() -> pd.DataFrame:
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
    if is_offline_mode():
        df = _route(_snap(), origin, destination).copy()
        df = df[df[DEP_COL].notna() & df[ARR_COL].notna() &
                df["booking_horizon_days"].notna() &
                df["booking_horizon_days"].between(0, 90)]
        dep = pd.to_datetime(df[DEP_COL], errors="coerce", utc=True)
        arr = pd.to_datetime(df[ARR_COL], errors="coerce", utc=True)
        df["travel_h"] = (arr - dep).dt.total_seconds() / 3600.0
        df["price_eur"] = pd.to_numeric(df["price_eur"], errors="coerce")
        df["booking_horizon_days"] = pd.to_numeric(df["booking_horizon_days"], errors="coerce").astype(int)
        df["is_direct"] = df["is_direct"].map({True: True, False: False, "t": True, "f": False})
        df = df[(df["travel_h"] >= 0.25) & (df["travel_h"] <= 24)]
        return df[["operator", "booking_horizon_days", "price_eur", "is_direct", "travel_h"]]

    query = f"""
        SELECT operator, booking_horizon_days, price_eur, is_direct,
               EXTRACT(EPOCH FROM ({ARR_COL} - {DEP_COL})) / 3600.0 as travel_h
        FROM price_observations
        WHERE origin_name = :origin AND destination_name = :destination
          AND {DEP_COL} IS NOT NULL AND {ARR_COL} IS NOT NULL
          AND booking_horizon_days IS NOT NULL AND booking_horizon_days BETWEEN 0 AND 90;
    """
    db = get_db()
    df = db.query(query, params={"origin": origin, "destination": destination})
    df["price_eur"] = pd.to_numeric(df["price_eur"], errors="coerce")
    df["travel_h"]  = pd.to_numeric(df["travel_h"],  errors="coerce")
    df["booking_horizon_days"] = pd.to_numeric(df["booking_horizon_days"], errors="coerce").astype(int)
    df["is_direct"] = df["is_direct"].map({True: True, False: False, "t": True, "f": False})
    df = df[(df["travel_h"] >= 0.25) & (df["travel_h"] <= 24)]
    return df


# ─────────────────────────────────────────────────────────────
# Crawler Status
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=120)
def load_crawler_overview():
    if is_offline_mode():
        df = _snap()
        if df.empty:
            return pd.DataFrame()
        return pd.DataFrame([{
            "total_records":  len(df),
            "n_operators":    df["operator"].nunique(),
            "n_routes":       df["route_id"].nunique() if "route_id" in df.columns else 0,
            "last_collected": df["collected_at"].max(),
        }])

    query = """
        SELECT COUNT(id) as total_records, COUNT(DISTINCT operator) as n_operators,
               COUNT(DISTINCT route_id) as n_routes, MAX(collected_at) as last_collected
        FROM price_observations;
    """
    db = get_db()
    return db.query(query)


@st.cache_data(ttl=120)
def load_crawler_stats_by_operator():
    if is_offline_mode():
        df = _snap()
        if df.empty:
            return pd.DataFrame()
        result = (df.groupby("operator")
                  .agg(records=("price_eur", "count"),
                       last_collected=("collected_at", "max"),
                       avg_price=("price_eur", "mean"))
                  .reset_index())
        if "route_id" in df.columns:
            routes = df.groupby("operator")["route_id"].nunique().reset_index(name="routes")
            result = result.merge(routes, on="operator")
        else:
            result["routes"] = 0
        result["records"]   = pd.to_numeric(result["records"])
        result["routes"]    = pd.to_numeric(result["routes"])
        result["avg_price"] = pd.to_numeric(result["avg_price"])
        return result.sort_values("records", ascending=False)

    query = """
        SELECT operator, COUNT(id) as records, MAX(collected_at) as last_collected,
               COUNT(DISTINCT route_id) as routes, AVG(price_eur) as avg_price
        FROM price_observations
        GROUP BY operator ORDER BY records DESC;
    """
    db = get_db()
    df = db.query(query)
    df["records"]   = pd.to_numeric(df["records"])
    df["routes"]    = pd.to_numeric(df["routes"])
    df["avg_price"] = pd.to_numeric(df["avg_price"])
    return df


@st.cache_data(ttl=120)
def load_crawler_daily_counts(days_back=30):
    if is_offline_mode():
        df = _snap()
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days_back)
        df = df[df["collected_at"] >= cutoff].copy()
        df["col_date"] = df["collected_at"].dt.date
        result = (df.groupby(["col_date", "operator"])
                  .size().reset_index(name="records")
                  .sort_values("col_date"))
        result["col_date"] = pd.to_datetime(result["col_date"])
        result["records"]  = pd.to_numeric(result["records"])
        return result

    query = """
        SELECT collected_at::date as col_date, operator, COUNT(id) as records
        FROM price_observations
        WHERE collected_at >= NOW() - INTERVAL '1 day' * :days_back
        GROUP BY collected_at::date, operator ORDER BY col_date ASC;
    """
    db = get_db()
    df = db.query(query, params={"days_back": days_back})
    df["col_date"] = pd.to_datetime(df["col_date"])
    df["records"]  = pd.to_numeric(df["records"])
    return df


@st.cache_data(ttl=120)
def load_crawler_health(days_back=7):
    if is_offline_mode():
        df = _snap()
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days_back)
        df = df[df["collected_at"] >= cutoff].copy()
        df["col_date"] = df["collected_at"].dt.date
        result = (df.groupby(["operator", "col_date"])
                  .size().reset_index(name="records"))
        result["records"] = pd.to_numeric(result["records"])
        return result

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