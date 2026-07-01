# dashboard/views/operator_comp.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from dashboard.database import get_db
from dashboard.config import op_color, op_label

def render_operator_comparison(route, T):
    st.title(f"⚖️ {T.get('tab_operator', 'Anbietervergleich & Streckenvergleich')}")
    st.markdown(f"### {T.get('route_label', 'Route')}: {route['label']}")
    
    db = get_db()

    # 1. Metriken im Direktvergleich (Oberer Bereich)
    query = """
        SELECT 
            operator,
            MIN(price_eur) as price_min,
            AVG(price_eur) as price_avg,
            COUNT(id) as observations
        FROM price_observations
        WHERE origin_name = :origin AND destination_name = :destination
        GROUP BY operator
    """
    df_op = db.query(query, params={"origin": route["origin_name"], "destination": route["destination_name"]})

    if df_op.empty:
        st.warning(T.get("no_data", "Keine Daten gefunden."))
        return

    st.write(f"#### 📊 {T.get('op_metrics_title', 'Effizienz-Kennzahlen im Direktvergleich')}")
    
    # Render der Metriken nebeneinander
    cols = st.columns(len(df_op))
    for idx, row in df_op.iterrows():
        with cols[idx]:
            op = row["operator"]
            st.markdown(f"##### <span style='color:{op_color(op)}'>●</span> {op_label(op)}", unsafe_allow_html=True)
            st.metric(T.get("op_low", "Günstigster Preis"), f"{float(row['price_min']):.2f} €")
            st.metric(f"Ø {T.get('bh_avg', 'Preis')}", f"{float(row['price_avg']):.2f} €")
            st.caption(f"{int(row['observations']):,} {T.get('ov_count', 'Messungen')}".replace(",", "."))

    st.markdown("---")

    # 2. Die originale Streckenvergleichs-Logik (Beide Strecken in einem Chart)
    st.write(f"#### 🔀 {T.get('op_comp_title', 'Streckenvergleich')}")
    
    # Alle Routen für das zweite Dropdown laden
    routes_query = """
        SELECT DISTINCT origin_name, destination_name 
        FROM price_observations 
        WHERE origin_name IS NOT NULL AND destination_name IS NOT NULL
    """
    all_routes = db.query(routes_query)
    all_routes["label"] = all_routes["origin_name"] + " → " + all_routes["destination_name"]
    
    comp_route_label = st.selectbox(
        T.get("comp_routes_label", "Strecken vergleichen"), 
        options=all_routes["label"].tolist(),
        index=0
    )
    
    if comp_route_label:
        comp_sel = all_routes[all_routes["label"] == comp_route_label].iloc[0]
        
        # Daten für Route 1 (Aktuelle Route)
        q1 = """
            SELECT EXTRACT(DAY FROM (departure_at - collected_at)) as horizon, AVG(price_eur) as price
            FROM price_observations
            WHERE origin_name = :origin AND destination_name = :destination AND departure_at IS NOT NULL
            GROUP BY horizon
        """
        df1 = db.query(q1, params={"origin": route["origin_name"], "destination": route["destination_name"]})
        
        # Daten für Route 2 (Vergleichsroute)
        df2 = db.query(q1, params={"origin": comp_sel["origin_name"], "destination": comp_sel["destination_name"]})
        
        # Plotly-Objekt für den kombinierten Linien-Vergleich aufbauen
        fig = go.Figure()
        
        if not df1.empty:
            df1["horizon"] = pd.to_numeric(df1["horizon"]).astype(int)
            df1 = df1[df1["horizon"].between(0, 90)].sort_values("horizon")
            fig.add_trace(go.Scatter(
                x=df1["horizon"], y=df1["price"],
                name=route["label"], line=dict(color="#4a9eff", width=3)
            ))
            
        if not df2.empty:
            df2["horizon"] = pd.to_numeric(df2["horizon"]).astype(int)
            df2 = df2[df2["horizon"].between(0, 90)].sort_values("horizon")
            fig.add_trace(go.Scatter(
                x=df2["horizon"], y=df2["price"],
                name=comp_route_label, line=dict(color="#ff7c5c", width=3, dash="dash")
            ))
            
        fig.update_xaxes(autorange="reversed", title_text=T.get("ov_days_adv", "Tage im Voraus"))
        fig.update_yaxes(title_text="Ø Ticketpreis (€)")
        fig.update_layout(
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )
        
        st.plotly_chart(fig, width="stretch")