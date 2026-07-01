# dashboard/database.py
import os
import pandas as pd
import streamlit as st

def get_db():
    """Nutzt das native Streamlit SQL-Verbindungsmanagement."""
    return st.connection("postgresql", type="sql")

@st.cache_data(ttl=300)
def load_route_list():
    """
    Lädt NUR die Metadaten der Routen für die Sidebar.
    Blitzschnell, da TimescaleDB die Aggregation übernimmt.
    """
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
    # Explizite Typkonvertierung für saubere Weiterverarbeitung
    df["record_count"] = pd.to_numeric(df["record_count"])
    df["label"] = df["origin_name"] + " → " + df["destination_name"]
    return df

@st.cache_data(ttl=60)
def load_overview_stats(origin, destination, days_back=30):
    """Holt voraggregierte Metriken für die High-End KPI-Karten."""
    query = """
        SELECT 
            MIN(price_eur) as min_price,
            AVG(price_eur) as avg_price,
            COUNT(id) as total_observations,
            COUNT(DISTINCT train_number) as unique_trains
        FROM price_observations
        WHERE origin_name = :origin 
          AND destination_name = :destination
          AND collected_at >= NOW() - INTERVAL '1 day' * :days_back
    """
    db = get_db()
    return db.query(query, params={"origin": origin, "destination": destination, "days_back": days_back})

@st.cache_data(ttl=120)
def load_timeline_data(origin, destination, days_back=30):
    """Aggregiert Preise pro Tag via TimescaleDB für das Haupt-Chart."""
    query = """
        SELECT 
            collected_at::date as col_date,
            operator,
            MIN(price_eur) as min_price,
            AVG(price_eur) as avg_price
        FROM price_observations
        WHERE origin_name = :origin 
          AND destination_name = :destination
          AND collected_at >= NOW() - INTERVAL '1 day' * :days_back
        GROUP BY collected_at::date, operator
        ORDER BY col_date ASC;
    """
    db = get_db()
    df = db.query(query, params={"origin": origin, "destination": destination, "days_back": days_back})
    df["col_date"] = pd.to_datetime(df["col_date"])
    return df

@st.cache_data(ttl=86400)
def load_distances():
    """Lädt die Distanzdaten relativ aus dem config-Ordner im Hauptverzeichnis."""
    # Pfad navigiert vom dashboard-Ordner hoch ins Hauptverzeichnis und dann in config/
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base_dir, "config", "route_distances.csv")
    try:
        dist = pd.read_csv(path)
        # Sicherstellen, dass Spaltennamen sauber sind
        dist.columns = dist.columns.str.strip()
        dist = dist[dist["haversine_km"] != "NA"].copy()
        dist["haversine_km"] = pd.to_numeric(dist["haversine_km"], errors="coerce")
        return dist[["route_id", "haversine_km"]].dropna()
    except Exception as e:
        # Falls es schiefgeht, loggen wir ein leeres DF, damit die App nicht abstürzt
        return pd.DataFrame(columns=["route_id", "haversine_km"])