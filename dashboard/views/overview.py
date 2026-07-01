# dashboard/views/overview.py
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from dashboard.database import get_db
from dashboard.config import op_color, op_label

def render_overview(route, T):
    st.title(f"📊 {T['tab_overview']}")
    st.markdown(f"### Route: {route['label']}")
    
    db = get_db()
    
    # Abfragen, wie die Spalte für das Abfahrtsdatum heißt
    sample_df = db.query("SELECT * FROM price_observations LIMIT 1")
    dep_col = next((c for c in ["departure_time", "departure_date", "departure", "departure_at"] if c in sample_df.columns), None)
    
    if not dep_col:
        st.warning(T["no_data"])
        return

    # Zeitfilter (Tage zurück)
    days_back = st.slider(T["ov_time_range"], min_value=1, max_value=60, value=14)

    # 1. SQL für die KPIs
    kpi_query = f"""
        SELECT 
            MIN(price_eur) as min_price,
            AVG(price_eur) as avg_price,
            COUNT(id) as total_obs
        FROM price_observations
        WHERE origin_name = :origin AND destination_name = :destination
          AND collected_at >= NOW() - INTERVAL '{days_back} days'
    """
    kpi_df = db.query(kpi_query, params={"origin": route["origin_name"], "destination": route["destination_name"]})

    if kpi_df.empty or kpi_df.iloc[0]["total_obs"] == 0:
        st.warning(T["ov_no_data"])
        return

    row = kpi_df.iloc[0]
    
    # KPI Grid anzeigen
    m1, m2, m3 = st.columns(3)
    m1.metric(T["ov_lowest_price"], f"{float(row['min_price']):.2f} €")
    m2.metric(T["ov_avg_price"], f"{float(row['avg_price']):.2f} €")
    m3.metric(T["data_points"], f"{int(row['total_obs']):,}".replace(",", "."))

    st.markdown("---")

    # 2. CHART 1: Tiefstpreise pro Tag (Historischer Verlauf)
    st.write(f"#### 📉 {T['ov_c1'].format(days=days_back)}")
    
    timeline_query = f"""
        SELECT 
            collected_at::date as col_date,
            operator,
            MIN(price_eur) as min_price
        FROM price_observations
        WHERE origin_name = :origin AND destination_name = :destination
          AND collected_at >= NOW() - INTERVAL '{days_back} days'
        GROUP BY col_date, operator
        ORDER BY col_date ASC
    """
    timeline_df = db.query(timeline_query, params={"origin": route["origin_name"], "destination": route["destination_name"]})
    
    if not timeline_df.empty:
        timeline_df["Anbieter"] = timeline_df["operator"].apply(op_label)
        color_map = {op_label(op): op_color(op) for op in timeline_df["operator"].unique()}
        
        fig1 = px.line(
            timeline_df, x="col_date", y="min_price", color="Anbieter",
            color_discrete_map=color_map, markers=True,
            labels={"col_date": T["ov_date"], "min_price": T["ov_low_lbl"]}
        )
        fig1.update_layout(hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig1, use_container_width=True)

    st.markdown("---")

    # 3. CHARTS 2 & 3: Preisspanne & Abfahrtsstunden im Split-Layout
    c1, c2 = st.columns(2)
    
    with c1:
        st.write(f"#### ⚖️ {T['ov_c2']}")
        range_query = f"""
            SELECT 
                operator,
                MIN(price_eur) as min_p,
                AVG(price_eur) as avg_p,
                MAX(price_eur) as max_p
            FROM price_observations
            WHERE origin_name = :origin AND destination_name = :destination
            GROUP BY operator
        """
        range_df = db.query(range_query, params={"origin": route["origin_name"], "destination": route["destination_name"]})
        
        if not range_df.empty:
            fig2 = go.Figure()
            for _, r in range_df.iterrows():
                lbl = op_label(r["operator"])
                col = op_color(r["operator"])
                
                # Linie von Min bis Max
                fig2.add_trace(go.Scatter(
                    x=[lbl, lbl], y=[float(r["min_p"]), float(r["max_p"])],
                    mode="lines", line=dict(color=col, width=4), showlegend=False
                ))
                # Durchschnitt als Raute / Diamond
                fig2.add_trace(go.Scatter(
                    x=[lbl], y=[float(r["avg_p"])],
                    mode="markers", marker=dict(color="#fff", size=10, symbol="diamond", line=dict(color=col, width=2)),
                    name=lbl
                ))
            fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", yaxis_title="Preis (€)")
            st.plotly_chart(fig2, use_container_width=True)

    with c2:
        st.write(f"#### 🕐 {T['ov_c3']}")
        hour_query = f"""
            SELECT 
                EXTRACT(HOUR FROM {dep_col}) as dep_hour,
                operator,
                COUNT(id) as connection_count
            FROM price_observations
            WHERE origin_name = :origin AND destination_name = :destination
            GROUP BY dep_hour, operator
            ORDER BY dep_hour ASC
        """
        hour_df = db.query(hour_query, params={"origin": route["origin_name"], "destination": route["destination_name"]})
        
        if not hour_df.empty:
            hour_df["dep_hour"] = pd.to_numeric(hour_df["dep_hour"]).astype(int)
            hour_df["Anbieter"] = hour_df["operator"].apply(op_label)
            color_map = {op_label(op): op_color(op) for op in hour_df["operator"].unique()}
            
            fig3 = px.bar(
                hour_df, x="dep_hour", y="connection_count", color="Anbieter",
                color_discrete_map=color_map, barmode="stack",
                labels={"dep_hour": T["ov_dep_hour"], "connection_count": T["ov_count"]}
            )
            fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig3, use_container_width=True)