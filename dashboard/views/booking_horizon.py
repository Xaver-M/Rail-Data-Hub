# dashboard/views/booking_horizon.py
import streamlit as st
import plotly.express as px
import pandas as pd
from dashboard.database import get_db
from dashboard.config import op_color, op_label

def render_booking_horizon(route, T):
    st.title(f"⏱️ {T['bh_head'].format(orig=route['origin_name'], dest=route['destination_name'])}")
    
    db = get_db()
    
    # Detektieren der Abfahrtszeit-Spalte
    sample_df = db.query("SELECT * FROM price_observations LIMIT 1")
    dep_col = next((c for c in ["departure_time", "departure_date", "departure", "departure_at"] if c in sample_df.columns), None)
    
    if not dep_col:
        st.warning(T["bh_no"])
        return

    # 1. SQL-Query: Daten nach Horizont und Anbieter aggregieren
    query = f"""
        SELECT 
            operator,
            EXTRACT(DAY FROM ({dep_col} - collected_at)) as horizon_days,
            AVG(price_eur) as avg_price,
            COUNT(id) as connection_count
        FROM price_observations
        WHERE origin_name = :origin AND destination_name = :destination
        GROUP BY operator, horizon_days
        HAVING EXTRACT(DAY FROM ({dep_col} - collected_at)) BETWEEN 0 AND 90
        ORDER BY horizon_days DESC
    """
    df_bh = db.query(query, params={"origin": route["origin_name"], "destination": route["destination_name"]})
    
    if df_bh.empty:
        st.warning(T["bh_no"])
        return

    # Datentypen korrigieren
    df_bh["horizon_days"] = pd.to_numeric(df_bh["horizon_days"]).astype(int)
    df_bh["avg_price"] = pd.to_numeric(df_bh["avg_price"])
    df_bh["connection_count"] = pd.to_numeric(df_bh["connection_count"])
    df_bh["Anbieter"] = df_bh["operator"].apply(op_label)
    
    color_map = {op_label(op): op_color(op) for op in df_bh["operator"].unique()}

    # 2. OPTIMALER BUCHUNGSZEITPUNKT (KPI-Karten berechnen)
    st.write(f"#### 💡 {T['bh_opt']}")
    
    # Berechnen, wann es pro Operator im Schnitt am günstigsten war
    opt_cols = st.columns(len(df_bh["operator"].unique()))
    for idx, op in enumerate(df_bh["operator"].unique()):
        df_op = df_bh[df_bh["operator"] == op]
        if not df_op.empty:
            # Günstigster Zeilenwert
            cheapest_row = df_op.loc[df_op["avg_price"].idxmin()]
            max_price = df_op["avg_price"].max()
            
            # Sparpotenzial berechnen vs. teuerstem Zeitpunkt
            savings_pct = 0
            if max_price > 0:
                savings_pct = ((max_price - cheapest_row["avg_price"]) / max_price) * 100
                
            with opt_cols[idx]:
                st.markdown(f"""
                <div class="kpi-card" style="border-top: 4px solid {op_color(op)};">
                    <div class="kpi-title">{op_label(op)}</div>
                    <div class="kpi-value">+{int(cheapest_row['horizon_days'])} {T['days_unit']}</div>
                    <div class="kpi-subtitle">{T['bh_cheap']} {cheapest_row['avg_price']:.2f} €</div>
                    <div class="kpi-subtitle" style="color:#a8e44a; font-weight:bold;">{T['bh_saves'].format(pct=savings_pct)}</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("---")

    # 3. CHARTS: Verlauf nach Horizont & Frequenz im Split-Layout
    c1, c2 = st.columns(2)
    
    with c1:
        st.write(f"#### 📊 {T['bh_c1']}")
        fig1 = px.line(
            df_bh, x="horizon_days", y="avg_price", color="Anbieter",
            color_discrete_map=color_map, markers=True,
            labels={"horizon_days": T["ov_days_adv"], "avg_price": T["bh_avg"]}
        )
        # Zeitachse umkehren (90 Tage im Voraus links, 0 Tage knapp vor Abfahrt rechts)
        fig1.update_xaxes(autorange="reversed")
        fig1.update_layout(hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig1, use_container_width=True)

    with c2:
        st.write(f"#### 📈 {T['bh_c2']}")
        fig2 = px.bar(
            df_bh, x="horizon_days", y="connection_count", color="Anbieter",
            color_discrete_map=color_map, barmode="stack",
            labels={"horizon_days": T["ov_days_adv"], "connection_count": T["bh_conn"]}
        )
        fig2.update_xaxes(autorange="reversed")
        fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")

    # 4. DETAIL-DATENTABELLE
    st.write(f"#### 📋 {T['bh_table']}")
    pivot_df = df_bh.pivot(index="horizon_days", columns="Anbieter", values="avg_price").sort_index(ascending=False)
    # Schönere Formatierung für Währungswerte
    st.dataframe(pivot_df.style.format("{:.2f} €", na_rep="—"), use_container_width=True)