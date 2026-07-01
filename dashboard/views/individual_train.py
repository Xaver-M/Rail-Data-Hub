# dashboard/views/individual_train.py
import streamlit as st
import plotly.express as px
import pandas as pd
from dashboard.database import get_db
from dashboard.config import op_color, op_label

def render_individual_train(route, T):
    st.title(f"🚆 {T['tab_train']}")
    st.markdown(f"### Route: {route['label']}")
    
    db = get_db()
    
    # Detektieren der Abfahrtszeit-Spalte
    sample_df = db.query("SELECT * FROM price_observations LIMIT 1")
    dep_col = next((c for c in ["departure_time", "departure_date", "departure", "departure_at"] if c in sample_df.columns), None)
    
    if not dep_col:
        st.warning(T["no_data"])
        return

    # 1. Alle verfügbaren Zugnummern für diese Strecke abfragen
    trains_query = """
        SELECT DISTINCT train_number 
        FROM price_observations
        WHERE origin_name = :origin AND destination_name = :destination AND train_number IS NOT NULL
        ORDER BY train_number ASC
    """
    trains_df = db.query(trains_query, params={"origin": route["origin_name"], "destination": route["destination_name"]})
    
    if trains_df.empty:
        st.info("Keine Zugnummern-Daten für diese Strecke vorhanden.")
        return
        
    train_list = trains_df["train_number"].tolist()
    selected_train = st.selectbox("🎯 Bitte eine Zugnummer wählen:", options=train_list)

    if not selected_train:
        return

    # 2. SQL-Abfrage für den spezifischen Zug
    query = f"""
        SELECT 
            operator,
            train_number,
            {dep_col} as departure_time,
            collected_at,
            price_eur,
            seats_available,
            EXTRACT(DAY FROM ({dep_col} - collected_at)) as horizon_days
        FROM price_observations
        WHERE origin_name = :origin AND destination_name = :destination AND train_number = :train
        ORDER BY collected_at DESC
    """
    df_single = db.query(query, params={
        "origin": route["origin_name"], 
        "destination": route["destination_name"], 
        "train": selected_train
    })

    if df_single.empty:
        st.warning(T["no_data"])
        return

    # Datentypen korrigieren
    df_single["price_eur"] = pd.to_numeric(df_single["price_eur"])
    df_single["horizon_days"] = pd.to_numeric(df_single["horizon_days"]).astype(int)
    if "seats_available" in df_single.columns:
        df_single["seats_available"] = pd.to_numeric(df_single["seats_available"], errors="coerce")

    # Statistiken für diesen spezifischen Zug anzeigen
    m1, m2, m3 = st.columns(3)
    m1.metric("Günstigster Preis", f"{df_single['price_eur'].min():.2f} €")
    m2.metric("Durchschnittspreis", f"{df_single['price_eur'].mean():.2f} €")
    m3.metric("Erfasste Beobachtungen", f"{len(df_single):,}".replace(",", "."))

    st.markdown("---")

    # 3. CHARTS IM SPLIT-LAYOUT
    c1, c2 = st.columns(2)
    
    with c1:
        st.write("#### 📉 Preiskurve nach Buchungshorizont")
        # Aggregieren nach Horizont für eine sauberere Kurve
        df_chart = df_single.groupby("horizon_days").agg({"price_eur": "mean"}).reset_index()
        
        fig1 = px.line(
            df_chart, x="horizon_days", y="price_eur", markers=True,
            labels={"horizon_days": T["ov_days_adv"], "price_eur": "Durchschnittspreis (€)"},
            color_discrete_sequence=[op_color(df_single["operator"].iloc[0])]
        )
        fig1.update_xaxes(autorange="reversed")
        fig1.update_layout(hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig1, use_container_width=True)

    with c2:
        st.write("#### 💺 Sitzplatzverfügbarkeit vs. Preis")
        if "seats_available" in df_single.columns and not df_single["seats_available"].dropna().empty:
            fig2 = px.scatter(
                df_single, x="seats_available", y="price_eur", 
                labels={"seats_available": "Verfügbare Sitze", "price_eur": "Preis (€)"},
                color_discrete_sequence=["#ffb547"]
            )
            fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Für diesen Betreiber/Zug werden keine Echtzeit-Sitzplatzdaten erhoben.")

    st.markdown("---")

    # 4. TABELLE DER LETZTEN MESSUNGEN
    st.write("#### 📋 Letzte Beobachtungen")
    st.dataframe(
        df_single[["collected_at", "departure_time", "horizon_days", "price_eur"]]
        .rename(columns={
            "collected_at": "Abfrage-Zeitpunkt", 
            "departure_time": "Geplante Abfahrt", 
            "horizon_days": "Tage im Voraus", 
            "price_eur": "Preis"
        }).head(100), 
        use_container_width=True
    )