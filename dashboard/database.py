# dashboard/database.py
import os
from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd
import streamlit as st

# ─────────────────────────────────────────────────────────────
# Schema-Konstanten
# ─────────────────────────────────────────────────────────────
DEP_COL = "departure_at"
ARR_COL = "arrival_at"

# Collection day = calendar day in the crawlers' local time zone, not UTC.
# Crawlers compute the queried departure date as datetime.now() + horizon in
# local time, so a run at 23:30 UTC (= 01:30 CEST) belongs to the NEXT day.
# Grouping by UTC date splits/misassigns such runs.
COLLECTION_TZ = "Europe/Berlin"
COL_DATE_SQL = f"(collected_at AT TIME ZONE '{COLLECTION_TZ}')::date"


# Google Flights rows are collected but not shown yet (intermodal view is WIP).
# They are identified by their bag-variant fare_class (BAG_VARIANTS in
# config/flight_routes.py), which also catches airline slugs not known yet.
# All dashboard queries read FROM {OBS_TABLE} instead of price_observations.
SHOW_FLIGHTS = False
FLIGHT_FARE_CLASSES = ("economy_nobag", "economy_cabinbag")
_flight_list = ", ".join(f"'{fc}'" for fc in FLIGHT_FARE_CLASSES)
OBS_TABLE = "price_observations" if SHOW_FLIGHTS else (
    "(SELECT * FROM price_observations "
    f"WHERE fare_class IS NULL OR fare_class NOT IN ({_flight_list})) AS price_observations"
)


def _col_date(series: pd.Series) -> pd.Series:
    """Collection day in COLLECTION_TZ for a tz-aware UTC timestamp series."""
    return series.dt.tz_convert(COLLECTION_TZ).dt.date

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
    if not SHOW_FLIGHTS and "fare_class" in df.columns:
        df = df[~df["fare_class"].isin(FLIGHT_FARE_CLASSES)]
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

    query = f"""
        SELECT
            origin_name, destination_name, route_id,
            COUNT(price_eur) as record_count,
            MAX(collected_at) as last_collected,
            ARRAY_AGG(DISTINCT operator) as operators
        FROM {OBS_TABLE}
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

    query = f"""
        SELECT DISTINCT origin_name, destination_name, route_id
        FROM {OBS_TABLE}
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

    query = f"""
        SELECT
            MIN(price_eur) as min_price, AVG(price_eur) as avg_price,
            COUNT(id) as total_obs, COUNT(DISTINCT operator) as n_operators,
            AVG(price_eur) FILTER (WHERE collected_at >= NOW() - INTERVAL '7 days') as recent_avg,
            AVG(price_eur) FILTER (WHERE collected_at <  NOW() - INTERVAL '7 days') as prior_avg
        FROM {OBS_TABLE}
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
        df["col_date"] = _col_date(df["collected_at"])
        result = (df.groupby(["col_date", "operator"])
                  .agg(min_price=("price_eur", "min"),
                       avg_price=("price_eur", "mean"),
                       max_price=("price_eur", "max"))
                  .reset_index()
                  .sort_values("col_date"))
        result["col_date"] = pd.to_datetime(result["col_date"])
        return result

    query = f"""
        SELECT {COL_DATE_SQL} as col_date, operator,
               MIN(price_eur) as min_price, AVG(price_eur) as avg_price, MAX(price_eur) as max_price
        FROM {OBS_TABLE}
        WHERE origin_name = :origin AND destination_name = :destination
          AND collected_at >= NOW() - INTERVAL '1 day' * :days_back
        GROUP BY 1, operator
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

    query = f"""
        SELECT operator, MIN(price_eur) as price_min, AVG(price_eur) as price_avg,
               MAX(price_eur) as price_max, COUNT(id) as observations
        FROM {OBS_TABLE}
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
        FROM {OBS_TABLE}
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

    query = f"""
        SELECT operator, fare_class, AVG(price_eur) as avg_price, COUNT(id) as observations
        FROM {OBS_TABLE}
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
        FROM {OBS_TABLE}
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
        FROM {OBS_TABLE}
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
                     price_max=("price_eur", "max"),
                     observations=("price_eur", "count"))
                .reset_index()
                .sort_values("booking_horizon_days", ascending=False))

    query = f"""
        SELECT operator, booking_horizon_days,
               AVG(price_eur) as price_avg, MIN(price_eur) as price_min, MAX(price_eur) as price_max,
               COUNT(id) as observations
        FROM {OBS_TABLE}
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

    query = f"""
        SELECT DISTINCT train_number FROM {OBS_TABLE}
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
        FROM {OBS_TABLE}
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
        FROM {OBS_TABLE}
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

    query = f"""
        SELECT operator,
               MIN(price_eur) as price_min, AVG(price_eur) as price_avg,
               MAX(price_eur) as price_max, AVG(seats_available) as seats_avg,
               COUNT(id) as observations
        FROM {OBS_TABLE}
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

    query = f"""
        SELECT operator, booking_horizon_days, AVG(seats_available) as seats_avg
        FROM {OBS_TABLE}
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

    query = f"""
        SELECT booking_horizon_days,
               AVG(price_eur) as price_avg, MIN(price_eur) as price_min,
               COUNT(id) as observations
        FROM {OBS_TABLE}
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
        cheapest_operator = (
            df.loc[df["price_eur"].idxmin(), "operator"] if not df.empty and df["price_eur"].notna().any() else None
        )
        return pd.DataFrame([{
            "price_min":    df["price_eur"].min(),
            "price_avg":    df["price_eur"].mean(),
            "n_operators":  df["operator"].nunique(),
            "observations": len(df),
            "cheapest_operator": cheapest_operator,
        }])

    query = f"""
        SELECT MIN(price_eur) as price_min, AVG(price_eur) as price_avg,
               COUNT(DISTINCT operator) as n_operators, COUNT(id) as observations,
               (ARRAY_AGG(operator ORDER BY price_eur ASC))[1] as cheapest_operator
        FROM {OBS_TABLE}
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
        FROM {OBS_TABLE}
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

    query = f"""
        SELECT COUNT(id) as total_records, COUNT(DISTINCT operator) as n_operators,
               COUNT(DISTINCT route_id) as n_routes, MAX(collected_at) as last_collected
        FROM {OBS_TABLE};
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

    query = f"""
        SELECT operator, COUNT(id) as records, MAX(collected_at) as last_collected,
               COUNT(DISTINCT route_id) as routes, AVG(price_eur) as avg_price
        FROM {OBS_TABLE}
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
    """days_back=None -> whole collection period."""
    if is_offline_mode():
        df = _snap().copy()
        if days_back is not None:
            cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days_back)
            df = df[df["collected_at"] >= cutoff]
        df["col_date"] = _col_date(df["collected_at"])
        result = (df.groupby(["col_date", "operator"])
                  .size().reset_index(name="records")
                  .sort_values("col_date"))
        result["col_date"] = pd.to_datetime(result["col_date"])
        result["records"]  = pd.to_numeric(result["records"])
        return result

    where = "" if days_back is None else "WHERE collected_at >= NOW() - INTERVAL '1 day' * :days_back"
    query = f"""
        SELECT {COL_DATE_SQL} as col_date, operator, COUNT(id) as records
        FROM {OBS_TABLE}
        {where}
        GROUP BY 1, operator ORDER BY col_date ASC;
    """
    db = get_db()
    df = db.query(query, params={} if days_back is None else {"days_back": days_back})
    df["col_date"] = pd.to_datetime(df["col_date"])
    df["records"]  = pd.to_numeric(df["records"])
    return df


@st.cache_data(ttl=120)
def load_crawler_health(days_back=7):
    if is_offline_mode():
        df = _snap()
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days_back)
        df = df[df["collected_at"] >= cutoff].copy()
        df["col_date"] = _col_date(df["collected_at"])
        result = (df.groupby(["operator", "col_date"])
                  .size().reset_index(name="records"))
        result["records"] = pd.to_numeric(result["records"])
        return result

    query = f"""
        SELECT operator, {COL_DATE_SQL} as col_date, COUNT(id) as records
        FROM {OBS_TABLE}
        WHERE collected_at >= NOW() - INTERVAL '1 day' * :days_back
        GROUP BY operator, 2;
    """
    db = get_db()
    df = db.query(query, params={"days_back": days_back})
    df["records"] = pd.to_numeric(df["records"])
    return df


# ─────────────────────────────────────────────────────────────
# Export
# ─────────────────────────────────────────────────────────────
# Whitelist: export column name -> SQL expression (raw_response is never exported)
EXPORT_RAW_COLUMNS = {
    "collected_at":         "collected_at",
    "collection_day":       COL_DATE_SQL,
    "operator":             "operator",
    "route_id":             "route_id",
    "origin_name":          "origin_name",
    "destination_name":     "destination_name",
    "origin_id":            "origin_id",
    "destination_id":       "destination_id",
    "departure_at":         DEP_COL,
    "arrival_at":           ARR_COL,
    "booking_horizon_days": "booking_horizon_days",
    "train_number":         "train_number",
    "fare_class":           "fare_class",
    "price_eur":            "price_eur",
    "seats_available":      "seats_available",
    "is_direct":            "is_direct",
    "currency_raw":         "currency_raw",
    "source_url":           "source_url",
}
EXPORT_DAILY_GROUP = ["collection_day", "route_id", "origin_name", "destination_name",
                      "operator", "booking_horizon_days"]


@dataclass(frozen=True)
class ExportFilter:
    operators: tuple = ()          # empty = all
    route_ids: tuple = ()          # empty = all
    col_from: date | None = None   # collection day (COLLECTION_TZ), inclusive
    col_to: date | None = None
    horizons: tuple = ()           # empty = all
    direct_only: bool = False
    dep_from: date | None = None   # departure day, inclusive (optional)
    dep_to: date | None = None


def _day_start_utc(d: date) -> pd.Timestamp:
    return pd.Timestamp(d).tz_localize(COLLECTION_TZ).tz_convert("UTC")


def _export_where(f: ExportFilter) -> tuple[str, dict]:
    clauses, params = [], {}
    if f.operators:
        clauses.append("operator = ANY(:operators)")
        params["operators"] = list(f.operators)
    if f.route_ids:
        clauses.append("route_id = ANY(:route_ids)")
        params["route_ids"] = list(f.route_ids)
    # plain collected_at bounds (not the day expression) -> hypertable chunk exclusion
    if f.col_from:
        clauses.append("collected_at >= :ts_from")
        params["ts_from"] = _day_start_utc(f.col_from).to_pydatetime()
    if f.col_to:
        clauses.append("collected_at < :ts_to")
        params["ts_to"] = _day_start_utc(f.col_to + timedelta(days=1)).to_pydatetime()
    if f.horizons:
        clauses.append("booking_horizon_days = ANY(:horizons)")
        params["horizons"] = [int(h) for h in f.horizons]
    if f.direct_only:
        clauses.append("is_direct IS TRUE")
    if f.dep_from:
        clauses.append(f"{DEP_COL}::date >= :dep_from")
        params["dep_from"] = f.dep_from
    if f.dep_to:
        clauses.append(f"{DEP_COL}::date <= :dep_to")
        params["dep_to"] = f.dep_to
    return ("WHERE " + " AND ".join(clauses)) if clauses else "", params


def _export_filter_snapshot(f: ExportFilter) -> pd.DataFrame:
    df = _snap().copy()
    if df.empty:
        return df
    df["collection_day"] = _col_date(df["collected_at"])
    if f.operators:
        df = df[df["operator"].isin(f.operators)]
    if f.route_ids:
        df = df[df["route_id"].isin(f.route_ids)]
    if f.col_from:
        df = df[df["collection_day"] >= f.col_from]
    if f.col_to:
        df = df[df["collection_day"] <= f.col_to]
    if f.horizons:
        df = df[df["booking_horizon_days"].isin(f.horizons)]
    if f.direct_only:
        df = df[df["is_direct"].astype(str).str.lower().isin(["true", "t", "1"])]
    if f.dep_from or f.dep_to:
        dep_day = pd.to_datetime(df[DEP_COL], errors="coerce", utc=True).dt.date
        if f.dep_from:
            df = df[dep_day >= f.dep_from]
        if f.dep_to:
            df = df[dep_day <= f.dep_to]
    return df


def _export_daily_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    return (df.groupby(EXPORT_DAILY_GROUP, dropna=False)["price_eur"]
              .agg(price_min="min", price_avg="mean", price_max="max", n_offers="count")
              .reset_index()
              .sort_values(["collection_day", "route_id", "operator", "booking_horizon_days"]))


@st.cache_data(ttl=600)
def load_export_date_range():
    """First/last collection day (COLLECTION_TZ) in the visible data."""
    if is_offline_mode():
        df = _snap()
        if df.empty:
            return None, None
        days = _col_date(df["collected_at"])
        return days.min(), days.max()

    db = get_db()
    r = db.query(f"SELECT MIN({COL_DATE_SQL}) AS first_day, MAX({COL_DATE_SQL}) AS last_day FROM {OBS_TABLE}").iloc[0]
    return pd.Timestamp(r["first_day"]).date(), pd.Timestamp(r["last_day"]).date()


@st.cache_data(ttl=120)
def count_export(f: ExportFilter, level: str) -> int:
    """Rows the export would contain. level: 'raw' or 'daily'."""
    if is_offline_mode():
        df = _export_filter_snapshot(f)
        return len(df) if level == "raw" or df.empty else len(_export_daily_snapshot(df))

    where, params = _export_where(f)
    if level == "raw":
        query = f"SELECT COUNT(*) AS n FROM {OBS_TABLE} {where}"
    else:
        query = f"""
            SELECT COUNT(*) AS n FROM (
                SELECT 1 FROM {OBS_TABLE} {where}
                GROUP BY {COL_DATE_SQL}, route_id, origin_name, destination_name,
                         operator, booking_horizon_days
            ) t
        """
    return int(get_db().query(query, params=params).iloc[0]["n"])


@st.cache_data(ttl=120, max_entries=4)
def load_export(f: ExportFilter, level: str, columns: tuple = (), limit: int | None = None) -> pd.DataFrame:
    """Export data. level='raw' uses `columns` (keys of EXPORT_RAW_COLUMNS), 'daily' is fixed."""
    if level == "raw":
        columns = [c for c in columns if c in EXPORT_RAW_COLUMNS] or list(EXPORT_RAW_COLUMNS)

    if is_offline_mode():
        df = _export_filter_snapshot(f)
        if df.empty:
            return df
        if level == "daily":
            out = _export_daily_snapshot(df)
        else:
            out = df.sort_values(["collected_at", "route_id"])[[c for c in columns if c in df.columns]]
        return out.head(limit) if limit else out

    where, params = _export_where(f)
    if level == "daily":
        query = f"""
            SELECT {COL_DATE_SQL} AS collection_day, route_id, origin_name, destination_name,
                   operator, booking_horizon_days,
                   MIN(price_eur) AS price_min, AVG(price_eur) AS price_avg,
                   MAX(price_eur) AS price_max, COUNT(*) AS n_offers
            FROM {OBS_TABLE} {where}
            GROUP BY 1, 2, 3, 4, 5, 6
            ORDER BY 1, 2, 5, 6
        """
    else:
        select = ", ".join(f"{EXPORT_RAW_COLUMNS[c]} AS {c}" for c in columns)
        query = f"SELECT {select} FROM {OBS_TABLE} {where} ORDER BY collected_at, route_id"
    if limit:
        query += " LIMIT :limit"
        params["limit"] = int(limit)

    df = get_db().query(query, params=params, ttl=0)
    for col in ("price_min", "price_avg", "price_max", "price_eur"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# ─────────────────────────────────────────────────────────────
# Intermodal (rail/bus vs. air) – preview
# ─────────────────────────────────────────────────────────────
# These queries read price_observations directly (not OBS_TABLE): they are the
# only place where flight rows are shown. Air rows = FLIGHT_FARE_CLASSES; one
# bag variant is compared at a time. The CSV snapshot contains no flights ->
# offline mode returns empty frames.
BUS_OPERATORS = ("flixbus",)

_MODE_SQL = (f"CASE WHEN fare_class IN ({_flight_list}) THEN 'air' "
             f"WHEN operator = ANY(:bus_ops) THEN 'bus' ELSE 'rail' END")
# ground rows + only the selected bag variant of the air rows
_ONE_AIR_VARIANT_SQL = f"(fare_class IS NULL OR fare_class NOT IN ({_flight_list}) OR fare_class = :air_fc)"


@st.cache_data(ttl=600)
def load_intermodal_corridors() -> pd.DataFrame:
    """route_ids with flight data: label from the ground rows + air collection days."""
    if is_offline_mode():
        return pd.DataFrame()
    query = f"""
        WITH air AS (
            SELECT route_id, MIN({COL_DATE_SQL}) AS first_air_day,
                   COUNT(DISTINCT {COL_DATE_SQL}) AS air_days,
                   COUNT(*) AS air_records,
                   ARRAY_AGG(DISTINCT operator) AS airlines,
                   ARRAY_AGG(DISTINCT origin_id || '-' || destination_id) AS airport_pairs
            FROM price_observations
            WHERE fare_class IN ({_flight_list})
            GROUP BY route_id
        ), ground AS (
            SELECT DISTINCT ON (route_id) route_id, origin_name, destination_name
            FROM {OBS_TABLE}
            WHERE route_id IN (SELECT route_id FROM air)
            ORDER BY route_id, collected_at DESC
        )
        SELECT a.route_id, g.origin_name, g.destination_name,
               a.first_air_day, a.air_days, a.air_records, a.airlines, a.airport_pairs
        FROM air a LEFT JOIN ground g USING (route_id)
        ORDER BY a.route_id;
    """
    df = get_db().query(query)
    df["first_air_day"] = pd.to_datetime(df["first_air_day"]).dt.date
    df["air_records"] = pd.to_numeric(df["air_records"])
    return df


@st.cache_data(ttl=300)
def load_intermodal_horizon(route_id: str, air_fare_class: str) -> pd.DataFrame:
    """Min/avg price + travel time per mode × operator × horizon, on days with air data only."""
    if is_offline_mode():
        return pd.DataFrame()
    query = f"""
        WITH air_days AS (
            SELECT DISTINCT {COL_DATE_SQL} AS d FROM price_observations
            WHERE route_id = :route_id AND fare_class = :air_fc
        )
        SELECT {_MODE_SQL} AS mode, operator, booking_horizon_days,
               MIN(price_eur) AS price_min, AVG(price_eur) AS price_avg, COUNT(*) AS n_offers,
               AVG(EXTRACT(EPOCH FROM ({ARR_COL} - {DEP_COL})) / 3600.0) AS travel_h
        FROM price_observations
        WHERE route_id = :route_id AND {_ONE_AIR_VARIANT_SQL}
          AND booking_horizon_days IS NOT NULL
          AND {COL_DATE_SQL} IN (SELECT d FROM air_days)
        GROUP BY 1, 2, 3
        ORDER BY 3, 1, 2;
    """
    df = get_db().query(query, params={"route_id": route_id, "air_fc": air_fare_class,
                                       "bus_ops": list(BUS_OPERATORS)})
    for col in ("price_min", "price_avg", "travel_h"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["booking_horizon_days"] = pd.to_numeric(df["booking_horizon_days"]).astype(int)
    return df


@st.cache_data(ttl=300)
def load_intermodal_daily(route_id: str, air_fare_class: str, horizon: int, days_back: int = 60) -> pd.DataFrame:
    """Cheapest price per collection day × mode at one booking horizon."""
    if is_offline_mode():
        return pd.DataFrame()
    query = f"""
        SELECT {COL_DATE_SQL} AS col_date, {_MODE_SQL} AS mode,
               MIN(price_eur) AS price_min,
               (ARRAY_AGG(operator ORDER BY price_eur ASC))[1] AS cheapest_operator
        FROM price_observations
        WHERE route_id = :route_id AND {_ONE_AIR_VARIANT_SQL}
          AND booking_horizon_days = :horizon
          AND collected_at >= NOW() - INTERVAL '1 day' * :days_back
        GROUP BY 1, 2
        ORDER BY 1, 2;
    """
    df = get_db().query(query, params={"route_id": route_id, "air_fc": air_fare_class,
                                       "bus_ops": list(BUS_OPERATORS), "horizon": int(horizon),
                                       "days_back": int(days_back)})
    df["col_date"] = pd.to_datetime(df["col_date"])
    df["price_min"] = pd.to_numeric(df["price_min"], errors="coerce")
    return df