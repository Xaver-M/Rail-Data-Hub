# dashboard/views/normalized_prices.py
import streamlit as st
import plotly.express as px
import pandas as pd
from dashboard.database import get_db
from dashboard.config import op_color, op_label

def render_normalized_prices(route, T):
    st.title(f"📐 {T.get('tab_normalized', '€/km & €/h Analysen')}")
    st.markdown(f"### Route: {route['label']}")
    
    db = get_db()

    # 1. SQL-QUERY: Performante Aggregation direkt in der Datenbank
    query = """
        SELECT 
            operator,
            booking_horizon_days,
            MIN(price_eur) as price_min, 
            AVG(price_eur) as price_avg, 
            AVG(travel_hours) as travel_h_avg, 
            COUNT(id) as observations
        FROM (
            SELECT 
                id,
                operator,
                price_eur,
                EXTRACT(DAY FROM (departure_at - collected_at)) as booking_horizon_days,
                EXTRACT(EPOCH FROM (arrival_at - departure_at)) / 3600.0 as travel_hours
            FROM price_observations
            WHERE origin_name = :origin 
              AND destination_name = :destination
              AND departure_at IS NOT NULL 
              AND arrival_at IS NOT NULL
        ) as sub
        WHERE booking_horizon_days BETWEEN 0 AND 90
        GROUP BY operator, booking_horizon_days 
        ORDER BY booking_horizon_days ASC
    """
    
    with st.spinner("Berechne normalisierte Preis-Effizienz..."):
        df_norm = db.query(query, params={"origin": route["origin_name"], "destination": route["destination_name"]})
    
    if df_norm.empty:
        st.warning(T.get("no_data", "Keine ausreichenden Daten für diese Metrik vorhanden."))
        return

    # Datentypen korrigieren
    df_norm["booking_horizon_days"] = pd.to_numeric(df_norm["booking_horizon_days"]).astype(int)
    df_norm["price_avg"] = pd.to_numeric(df_norm["price_avg"])
    df_norm["price_min"] = pd.to_numeric(df_norm["price_min"])
    df_norm["travel_h_avg"] = pd.to_numeric(df_norm["travel_h_avg"])
    df_norm["Anbieter"] = df_norm["operator"].apply(op_label)
    
    color_map = {op_label(op): op_color(op) for op in df_norm["operator"].unique()}

    # 2. BERECHNUNG DER PREISEFFIZIENZ PRO STUNDE (€ / Reisedauer-Stunde)
    df_norm["euro_per_hour"] = df_norm["price_avg"] / df_norm["travel_h_avg"].replace(0, 1)

    st.markdown("---")

    # 3. CHARTS IM SPLIT-LAYOUT RENDERN
    c1, c2 = st.columns(2)
    
    with c1:
        st.write(f"#### ⏱️ {T.get('norm_c1_title', 'Preiseffizienz (€ pro Reise-Stunde)')}")
        fig1 = px.line(
            df_norm, x="booking_horizon_days", y="euro_per_hour", color="Anbieter",
            color_discrete_map=color_map, markers=True,
            labels={
                "booking_horizon_days": T.get("ov_days_adv", "Tage im Voraus"), 
                "euro_per_hour": "Effizienz (€ / h Reisedauer)"
            }
        )
        # Fix: Korrekte Achsen-Umkehrung für Plotly
        fig1.update_xaxes(autorange="reversed")
        fig1.update_layout(hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig1, width="stretch")

    with c2:
        st.write(f"#### 📐 {T.get('norm_c2_title', 'Durchschnittliche Reisedauer vs. Buchungshorizont')}")
        fig2 = px.bar(
            df_norm, x="booking_horizon_days", y="travel_h_avg", color="Anbieter",
            color_discrete_map=color_map, barmode="group",
            labels={
                "booking_horizon_days": T.get("ov_days_adv", "Tage im Voraus"), 
                "travel_h_avg": "Ø Reisedauer (Stunden)"
            }
        )
        fig2.update_xaxes(autorange="reversed")
        fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, width="stretch")

    st.markdown("---")

    # 4. SCATTER-MATRIX FÜR PREIS-KOMPENSATIONS-EFFIZIENZ
    st.write(f"#### 📊 {T.get('norm_scatter_title', 'Effizienz-Cluster: Ticketpreis vs. Reisezeit-Aufwand')}")
    
    fig3 = px.scatter(
        df_norm, x="travel_h_avg", y="price_avg", color="Anbieter",
        size="observations", color_discrete_map=color_map,
        hover_data=["booking_horizon_days"],
        labels={
            "travel_h_avg": "Ø Fahrzeit (Stunden)",
            "price_avg": "Ø Ticketpreis (€)",
            "observations": "Datenpunkte",
            "booking_horizon_days": "Tage im Voraus"
        }
    )
    fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig3, width="stretch")