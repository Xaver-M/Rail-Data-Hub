# dashboard/views/time_of_day.py
import streamlit as st
import plotly.express as px
import pandas as pd
from dashboard.database import get_db
from dashboard.config import op_color, op_label

def render_time_of_day(route, T):
    # Sicherer Fallback mit .get(), falls 'td_head' in deiner config.py fehlt
    title_template = T.get('td_head', 'Tageszeit-Analyse: {orig} ➔ {dest}')
    st.title(f"🕐 {title_template.format(orig=route['origin_name'], dest=route['destination_name'])}")
    
    db = get_db()
    
    # Detektieren der Abfahrtszeit-Spalte
    sample_df = db.query("SELECT * FROM price_observations LIMIT 1")
    dep_col = next((c for c in ["departure_time", "departure_date", "departure", "departure_at"] if c in sample_df.columns), None)
    
    if not dep_col:
        st.warning(T.get("no_data", "Keine Daten gefunden."))
        return

    # 1. SQL-Query: Preise nach Abfahrtsstunde (0-23) und Anbieter aggregieren
    query = f"""
        SELECT 
            operator,
            EXTRACT(HOUR FROM {dep_col}) as dep_hour,
            MIN(price_eur) as min_price,
            AVG(price_eur) as avg_price,
            COUNT(id) as connection_count
        FROM price_observations
        WHERE origin_name = :origin AND destination_name = :destination
        GROUP BY operator, dep_hour
        ORDER BY dep_hour ASC
    """
    df_td = db.query(query, params={"origin": route["origin_name"], "destination": route["destination_name"]})
    
    if df_td.empty:
        st.warning(T.get("no_data", "Keine Daten gefunden."))
        return

    # Typkonvertierungen & Labeling
    df_td["dep_hour"] = pd.to_numeric(df_td["dep_hour"]).astype(int)
    df_td["min_price"] = pd.to_numeric(df_td["min_price"])
    df_td["avg_price"] = pd.to_numeric(df_td["avg_price"])
    df_td["connection_count"] = pd.to_numeric(df_td["connection_count"])
    df_td["Anbieter"] = df_td["operator"].apply(op_label)
    
    color_map = {op_label(op): op_color(op) for op in df_td["operator"].unique()}

    # 2. CHARTS IM SPLIT-LAYOUT
    c1, c2 = st.columns(2)
    
    with c1:
        st.write(f"#### 🏷️ {T.get('td_c1_title', 'Durchschnittspreis nach Tageszeit')}")
        fig1 = px.line(
            df_td, x="dep_hour", y="avg_price", color="Anbieter",
            color_discrete_map=color_map, markers=True,
            labels={"dep_hour": T.get("ov_dep_hour", "Abfahrtsstunde"), "avg_price": T.get("bh_avg", "Durchschnittspreis (€)")}
        )
        fig1.update_xaxes(tickmode="linear", tick0=0, dtick=2, showgrid=True, gridcolor="#222")
        fig1.update_yaxes(showgrid=True, gridcolor="#222")
        fig1.update_layout(hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig1, width="stretch")

    with c2:
        st.write(f"#### 📉 {T.get('td_c2_title', 'Günstigster Preis nach Tageszeit')}")
        fig2 = px.line(
            df_td, x="dep_hour", y="min_price", color="Anbieter",
            color_discrete_map=color_map, markers=True,
            labels={"dep_hour": T.get("ov_dep_hour", "Abfahrtsstunde"), "min_price": T.get("op_low", "Niedrigster Preis (€)")}
        )
        fig2.update_xaxes(tickmode="linear", tick0=0, dtick=2, showgrid=True, gridcolor="#222")
        fig2.update_yaxes(showgrid=True, gridcolor="#222")
        fig2.update_layout(hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, width="stretch")

    st.markdown("---")

    # 3. VERTEILUNG / TAKTUNG
    st.write(f"#### 📊 {T.get('td_density_title', 'Abfahrtsdichte nach Stunden')}")
    fig3 = px.bar(
        df_td, x="dep_hour", y="connection_count", color="Anbieter",
        color_discrete_map=color_map, barmode="group",
        labels={"dep_hour": T.get("ov_dep_hour", "Abfahrtsstunde"), "connection_count": T.get("ov_count", "Anzahl")}
    )
    fig3.update_xaxes(tickmode="linear", tick0=0, dtick=1)
    fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig3, width="stretch")