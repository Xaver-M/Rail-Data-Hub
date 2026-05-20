import importlib
import os
import sys
import threading
from collections import defaultdict
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATA_SOURCE = "csv"
CSV_PATH    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "export.csv")

st.set_page_config(page_title="RailDataHub", page_icon="🚄", layout="wide", initial_sidebar_state="expanded")

OPERATOR_COLORS = {
    "db": "#4a9eff", "flixtrain": "#a8e44a", "regiojet": "#ff7c5c",
    "trenitalia": "#ffb547", "italo": "#ff4f4f", "ouigo_es": "#b47fff", "ouigo_fr": "#ff6eb4",
}
OPERATOR_LABELS = {
    "db": "DB", "flixtrain": "Flixtrain", "regiojet": "RegioJet",
    "trenitalia": "Trenitalia", "italo": "Italo", "ouigo_es": "Ouigo ES", "ouigo_fr": "Ouigo FR",
}

def op_label(op): return OPERATOR_LABELS.get(op, op)
def op_color(op): return OPERATOR_COLORS.get(op, "#888888")

def hex_to_rgba(hex_color: str, alpha: float = 0.533) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

def make_color_map(operators) -> dict:
    return {op_label(op): op_color(op) for op in operators}

def agg_price_range(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    return (
        df.groupby(group_col)
        .agg(price_min=("price_eur", "min"), price_avg=("price_eur", "mean"), price_max=("price_eur", "max"))
        .reset_index()
    )


# ──────────────────────────────────────────────
# DATA LOADING
# ──────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_all_data() -> pd.DataFrame:
    if DATA_SOURCE == "csv":
        df = pd.read_csv(CSV_PATH, low_memory=False,
                         parse_dates=["collected_at", "departure_at", "arrival_at"])
    else:
        import psycopg2
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"), port=os.getenv("DB_PORT", "5432"),
            dbname=os.getenv("DB_NAME", "rail_data"), user=os.getenv("DB_USER", "rail_user"),
            password=os.getenv("DB_PASSWORD"),
        )
        df = pd.read_sql("""
            SELECT id, collected_at, departure_at, arrival_at,
                   operator, origin_id, destination_id, origin_name, destination_name,
                   route_id, train_number, fare_class, price_eur,
                   seats_available, is_direct, booking_horizon_days
            FROM price_observations ORDER BY collected_at DESC
        """, conn)
        conn.close()

    for col in ["collected_at", "departure_at", "arrival_at"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True).dt.tz_convert(None)

    df["price_eur"]            = pd.to_numeric(df["price_eur"], errors="coerce")
    df["seats_available"]      = pd.to_numeric(df["seats_available"], errors="coerce")
    df["booking_horizon_days"] = pd.to_numeric(df["booking_horizon_days"], errors="coerce").astype("Int64")
    df["is_direct"]            = df["is_direct"].map({"t": True, "f": False, True: True, False: False})
    df["dep_hour"] = df["departure_at"].dt.hour
    df["dep_dow"]  = df["departure_at"].dt.dayofweek
    df["dep_date"] = df["departure_at"].dt.date
    df["col_date"] = df["collected_at"].dt.date
    return df


@st.cache_data(ttl=300)
def load_routes(df: pd.DataFrame) -> pd.DataFrame:
    grp = (
        df.groupby(["origin_name", "destination_name", "route_id"])
        .agg(operators=("operator", lambda x: sorted(x.unique().tolist())),
             record_count=("price_eur", "count"), last_collected=("collected_at", "max"))
        .reset_index()
    )
    grp["label"] = grp["origin_name"] + " → " + grp["destination_name"]
    return grp.sort_values("record_count", ascending=False)


def filter_route(df: pd.DataFrame, origin: str, destination: str) -> pd.DataFrame:
    return df[(df["origin_name"] == origin) & (df["destination_name"] == destination)].copy()


# ──────────────────────────────────────────────
# CRAWLER IMPORTS
# ──────────────────────────────────────────────

@st.cache_resource
def _import_crawlers() -> tuple[dict, dict]:
    definitions = [
        ("db",         "crawlers.db.db_crawler",                "DBCrawler"),
        ("flixtrain",  "crawlers.flixtrain.flixtrain_crawler",  "FlixtrainCrawler"),
        ("trenitalia", "crawlers.trenitalia.trenitalia_crawler", "TrenitaliaCrawler"),
        ("italo",      "crawlers.italo.italo_crawler",           "ItaloCrawler"),
        ("ouigo_es",   "crawlers.ouigo_es.ougio_es_crawler",     "OuigoEsCrawler"),
        ("regiojet",   "crawlers.regiojet.regiojet_crawler",     "RegioJetCrawler"),
        ("ouigo_fr",   "crawlers.ouigo_fr.ouigo_fr_crawler",     "OuigoFrCrawler"),
    ]
    classes, errors = {}, {}
    for op, module_path, class_name in definitions:
        try:
            module = importlib.import_module(module_path)
            classes[op] = getattr(module, class_name)
        except Exception as e:
            errors[op] = str(e)
            classes[op] = None
    return classes, errors


def _ts(): return datetime.now().strftime("%H:%M:%S")


def _run_crawlers_thread(log_queue: list, ops_to_run: list | None = None):
    try:
        from config.routes import ROUTES, BOOKING_HORIZONS
    except Exception as e:
        log_queue.append(f"[{_ts()}] ✗ config/routes.py nicht gefunden: {e}")
        return

    crawler_classes, crawler_errors = _import_crawlers()
    active = ops_to_run or [op for op, cls in crawler_classes.items() if cls]
    log_queue.append(f"[{_ts()}] === Run gestartet — {len(active)} Crawler ===")

    for op in active:
        cls = crawler_classes.get(op)
        if cls is None:
            log_queue.append(f"[{_ts()}] ⚠  {op_label(op)} übersprungen — {crawler_errors.get(op, 'kein Modul')}")
            continue
        try:
            log_queue.append(f"[{_ts()}] ▶  {op_label(op)} startet...")
            cls().run(ROUTES, BOOKING_HORIZONS)
            log_queue.append(f"[{_ts()}] ✓  {op_label(op)} abgeschlossen")
        except Exception as e:
            log_queue.append(f"[{_ts()}] ✗  {op_label(op)} Fehler: {e}")

    log_queue.append(f"[{_ts()}] === Alle Crawler abgeschlossen ===")


@st.cache_resource
def _start_scheduler():
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except Exception as e:
        return None, str(e)
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=_run_crawlers_thread, args=[[], None],
        trigger="cron", hour=3, minute=0,
        id="daily_crawl", replace_existing=True, misfire_grace_time=3600,
    )
    scheduler.start()
    return scheduler, None


# ──────────────────────────────────────────────
# SESSION STATE
# ──────────────────────────────────────────────

if "log" not in st.session_state:
    st.session_state.log = []
if "running" not in st.session_state:
    st.session_state.running = False
if "initialized" not in st.session_state:
    scheduler, sched_err = _start_scheduler()
    st.session_state.sched_ok  = scheduler is not None
    st.session_state.sched_err = sched_err
    if DATA_SOURCE == "db" and scheduler is not None:
        st.session_state.log.append(f"[{_ts()}] Dashboard gestartet — initialer Crawler-Run beginnt...")
        threading.Thread(target=_run_crawlers_thread, args=(st.session_state.log, None), daemon=True).start()
        st.session_state.running = True
    st.session_state.initialized = True

df_all    = load_all_data()
routes_df = load_routes(df_all)
CRAWLER_CLASSES, CRAWLER_IMPORT_ERRORS = _import_crawlers()

DOW_LABELS = {0: "Mo", 1: "Di", 2: "Mi", 3: "Do", 4: "Fr", 5: "Sa", 6: "So"}

def time_since(dt) -> str:
    try:
        diff = (datetime.now() - pd.to_datetime(dt)).total_seconds()
        if diff < 60:    return "gerade eben"
        if diff < 3600:  return f"vor {int(diff/60)} Min."
        if diff < 86400: return f"vor {int(diff/3600)} Std."
        return f"vor {int(diff/86400)} Tagen"
    except Exception:
        return "—"


# ══════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 🚄 RailDataHub")
    st.caption("📁 CSV-Modus" if DATA_SOURCE == "csv" else "🗄️ DB-Modus")

    if DATA_SOURCE == "db":
        if st.session_state.sched_ok:
            st.success("⚙️ Scheduler aktiv — täglich 03:00 Uhr")
        else:
            st.warning(f"⚠️ Scheduler: {st.session_state.sched_err}")
        if st.session_state.running:
            st.info("🔄 Crawler laufen...")

    st.divider()

    if routes_df.empty:
        st.error("Keine Daten gefunden.")
        st.stop()

    st.markdown("**Strecke wählen**")
    search_term = st.text_input("Suche", placeholder="z.B. Berlin, Madrid, Roma...",
                                label_visibility="collapsed", key="route_search")

    all_route_labels = routes_df["label"].tolist()
    filtered_labels  = ([l for l in all_route_labels if search_term.lower() in l.lower()]
                        if search_term else all_route_labels)
    if not filtered_labels:
        st.warning("Keine Strecke gefunden.")
        filtered_labels = all_route_labels

    def route_region(label: str) -> str:
        DE  = ["Berlin","Hamburg","München","Frankfurt","Köln","Stuttgart","Leipzig","Hannover",
               "Karlsruhe","Basel","Bremen","Dortmund","Dresden","Kiel","Düsseldorf","Aachen",
               "Koblenz","Saarbrücken","Zürich","Graz","Passau","Wiesbaden"]
        IT  = ["Milano","Roma","Napoli","Torino","Venezia","Lecce","Salerno",
               "Taranto","Bolzano","Brescia","Genova","Trieste","Udine","Ravenna","Reggio"]
        ES  = ["Madrid","Barcelona","Valencia","Sevilla","Zaragoza","Albacete"]
        FR  = ["Paris","Lyon","Marseille","Nantes","Bordeaux","Montpellier","Nice","Toulouse","Rennes","Strasbourg","Brest"]
        INT = ["Wien","Praha","Budapest","Bratislava","Amsterdam","Brussels"]
        for city in DE:
            if city in label: return "🇩🇪 Deutschland"
        for city in IT:
            if city in label: return "🇮🇹 Italien"
        for city in ES:
            if city in label: return "🇪🇸 Spanien"
        for city in FR:
            if city in label: return "🇫🇷 Frankreich"
        for city in INT:
            if city in label: return "🌍 International"
        return "🌐 Sonstige"

    grouped: dict = defaultdict(list)
    for lbl in filtered_labels:
        grouped[route_region(lbl)].append(lbl)

    group_order    = ["🇩🇪 Deutschland","🇮🇹 Italien","🇪🇸 Spanien","🇫🇷 Frankreich","🌍 International","🌐 Sonstige"]
    display_labels = [lbl for g in group_order for lbl in grouped.get(g, [])]

    if "selected_label" not in st.session_state:
        st.session_state.selected_label = display_labels[0]
    if st.session_state.selected_label not in display_labels:
        st.session_state.selected_label = display_labels[0]

    selected_label = st.selectbox(
        "Strecke", display_labels,
        index=display_labels.index(st.session_state.selected_label)
              if st.session_state.selected_label in display_labels else 0,
        label_visibility="collapsed", key="route_selector",
    )
    st.session_state.selected_label = selected_label
    st.caption(f"{route_region(selected_label)} · {len(filtered_labels)} Strecken verfügbar")

    sel         = routes_df[routes_df["label"] == selected_label].iloc[0]
    origin      = sel["origin_name"]
    destination = sel["destination_name"]
    operators   = sel["operators"]

    st.divider()
    st.markdown("**Operator auf dieser Strecke:**")
    for op in operators:
        st.markdown(f'<span style="color:{op_color(op)}">●</span> {op_label(op)}', unsafe_allow_html=True)

    st.divider()
    st.metric("Datenpunkte", f'{int(sel["record_count"]):,}'.replace(",", "."))
    st.caption(f"Zuletzt: {time_since(sel['last_collected'])}")

    if st.button("🔄 Daten neu laden"):
        st.cache_data.clear()
        st.rerun()

df = filter_route(df_all, origin, destination)


# ══════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Übersicht", "🚆 Einzelner Zug", "⏱ Buchungshorizont",
    "🕐 Tageszeit", "⚖️ Operator-Vergleich", "🤖 Crawler-Status",
])


# ════════════════════════════════════════════
# TAB 1 — ÜBERSICHT
# ════════════════════════════════════════════

with tab1:
    st.subheader(f"{origin} → {destination}")
    days      = st.slider("Zeitraum (Tage zurück)", 7, 90, 30, key="ov_days")
    cutoff_dt = df["collected_at"].max() - pd.Timedelta(days=days)
    df_ts = (
        df[df["collected_at"] >= cutoff_dt]
        .groupby(["col_date", "operator"])
        .agg(price_min=("price_eur","min"), price_avg=("price_eur","mean"), price_max=("price_eur","max"))
        .reset_index().rename(columns={"col_date": "date"})
    )

    if df_ts.empty:
        st.info("Keine Daten im gewählten Zeitraum.")
    else:
        min_price   = float(df["price_eur"].min())
        min_op      = df.loc[df["price_eur"].idxmin(), "operator"]
        avg_price   = float(df["price_eur"].mean())
        recent_mask = df["collected_at"] >= (df["collected_at"].max() - pd.Timedelta(days=7))
        trend = ((df[recent_mask]["price_eur"].mean() - df[~recent_mask]["price_eur"].mean())
                 / df[~recent_mask]["price_eur"].mean() * 100) if not df[~recent_mask].empty else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tiefstpreis gesamt", f"{min_price:.2f} €", op_label(min_op))
        c2.metric("Ø Preis gesamt", f"{avg_price:.2f} €")
        c3.metric("Trend (letzte 7T)", f"{trend:+.1f}%", delta=f"{trend:+.1f}%", delta_color="inverse")
        c4.metric("Operator", len(operators))

        color_map        = make_color_map(operators)
        df_ts["op_label"] = df_ts["operator"].map(op_label)
        fig = px.line(df_ts, x="date", y="price_min", color="op_label", color_discrete_map=color_map,
                      title=f"Tiefstpreis je Tag — letzte {days} Tage",
                      labels={"date":"Datum","price_min":"Tiefstpreis (€)","op_label":"Operator"})
        fig.update_traces(line_width=2)
        fig.update_layout(hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

        df_range = agg_price_range(df, "operator")
        fig2 = go.Figure()
        for _, row in df_range.iterrows():
            c = op_color(row["operator"])
            fig2.add_trace(go.Bar(
                name=op_label(row["operator"]), x=[op_label(row["operator"])],
                y=[float(row["price_max"]) - float(row["price_min"])], base=[float(row["price_min"])],
                marker_color=hex_to_rgba(c), marker_line_color=c, marker_line_width=1.5))
            fig2.add_trace(go.Scatter(
                x=[op_label(row["operator"])], y=[float(row["price_avg"])], mode="markers",
                marker=dict(color=c, size=10, symbol="diamond"), showlegend=False,
                hovertemplate=f"Ø {float(row['price_avg']):.2f} €"))
        fig2.update_layout(barmode="overlay", showlegend=False, yaxis_title="Preis (€)",
                           title="Preisspanne Min / Ø / Max je Operator (Raute = Durchschnitt)")
        st.plotly_chart(fig2, use_container_width=True)

        df_freq = df.groupby(["dep_hour","operator"]).agg(anzahl=("price_eur","count")).reset_index()
        df_freq["op_label"]   = df_freq["operator"].map(op_label)
        df_freq["hour_label"] = df_freq["dep_hour"].astype(str).str.zfill(2) + ":00"
        fig_freq = px.bar(df_freq, x="hour_label", y="anzahl", color="op_label",
                          color_discrete_map=color_map, barmode="group",
                          title="Anzahl Verbindungen je Abfahrtsstunde und Operator",
                          labels={"hour_label":"Abfahrtsstunde","anzahl":"Anzahl","op_label":"Operator"})
        fig_freq.update_layout(hovermode="x unified")
        st.plotly_chart(fig_freq, use_container_width=True)

        df_freq_hz = (df.dropna(subset=["booking_horizon_days"])
                      .groupby(["booking_horizon_days","operator"]).agg(anzahl=("price_eur","count")).reset_index())
        df_freq_hz["op_label"]            = df_freq_hz["operator"].map(op_label)
        df_freq_hz["booking_horizon_days"] = df_freq_hz["booking_horizon_days"].astype(int)
        fig_freq2 = px.bar(df_freq_hz, x="booking_horizon_days", y="anzahl", color="op_label",
                           color_discrete_map=color_map, barmode="group",
                           title="Anzahl erfasste Verbindungen je Buchungshorizont",
                           labels={"booking_horizon_days":"Tage im Voraus","anzahl":"Anzahl","op_label":"Operator"})
        st.plotly_chart(fig_freq2, use_container_width=True)

        df_fare = df[df["fare_class"].notna() & (df["fare_class"] != "")]
        if not df_fare.empty:
            st.subheader("Preisklassen (fare_class)")
            df_fare_grp = (df_fare.groupby(["operator","fare_class"])
                           .agg(avg_price=("price_eur","mean"), count=("price_eur","count")).reset_index())
            df_fare_grp["op_label"] = df_fare_grp["operator"].map(op_label)
            fig3 = px.bar(df_fare_grp, x="fare_class", y="avg_price", color="op_label",
                          color_discrete_map=color_map, barmode="group",
                          title="Ø Preis je Preisklasse und Operator",
                          labels={"fare_class":"Klasse","avg_price":"Ø Preis (€)","op_label":"Operator"})
            st.plotly_chart(fig3, use_container_width=True)


# ════════════════════════════════════════════
# TAB 2 — EINZELNER ZUG
# ════════════════════════════════════════════

with tab2:
    st.subheader(f"Einzelner Zug — {origin} → {destination}")
    df_with_train = df[df["train_number"].notna() & (df["train_number"] != "")].copy()

    if df_with_train.empty:
        st.info("Keine Daten mit Zugnummer für diese Strecke.")
    else:
        sel_op_t = st.selectbox("Operator", operators, format_func=op_label, key="train_op")
        df_op    = df_with_train[df_with_train["operator"] == sel_op_t]

        df_trains = (
            df_op.sort_values("collected_at", ascending=False)
            .groupby("train_number")
            .agg(price_now   =("price_eur",       "first"),
                 price_min   =("price_eur",       "min"),
                 price_max   =("price_eur",       "max"),
                 dep_time    =("departure_at",    "first"),
                 fare_class  =("fare_class",      "first"),
                 seats_now   =("seats_available", "first"),
                 collected_at=("collected_at",    "first"))
            .reset_index().sort_values("dep_time")
        )
        cutoff_7d = df_op["collected_at"].max() - pd.Timedelta(days=8)
        df_week   = (df_op[df_op["collected_at"] <= cutoff_7d]
                     .sort_values("collected_at", ascending=False)
                     .groupby("train_number")["price_eur"].first().rename("price_7d_ago"))
        df_trains = df_trains.merge(df_week, on="train_number", how="left")
        df_trains["change_7d"] = (
            (df_trains["price_now"] - df_trains["price_7d_ago"]) / df_trains["price_7d_ago"] * 100
        ).round(1)

        def train_fmt(t):
            r    = df_trains[df_trains["train_number"] == t].iloc[0]
            dep  = pd.to_datetime(r["dep_time"]).strftime("%H:%M")
            chg  = f"  {r['change_7d']:+.1f}%" if not pd.isna(r.get("change_7d", float("nan"))) else ""
            fare = f"  [{r['fare_class']}]" if pd.notna(r["fare_class"]) and r["fare_class"] else ""
            return f"{t}{fare}  —  {dep} Uhr  |  {float(r['price_now']):.2f} €{chg}"

        sel_train = st.selectbox("Zug wählen", df_trains["train_number"].tolist(),
                                 format_func=train_fmt, key="train_name")

        row     = df_trains[df_trains["train_number"] == sel_train].iloc[0]
        dep_str = pd.to_datetime(row["dep_time"]).strftime("%H:%M")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Aktueller Preis", f"{float(row['price_now']):.2f} €", help=f"Fare: {row['fare_class'] or '—'}")
        m2.metric("Tiefst / Höchst", f"{float(row['price_min']):.2f} € / {float(row['price_max']):.2f} €")
        chg = row.get("change_7d", float("nan"))
        m3.metric("Änderung 7T",
                  f"{float(chg):+.1f}%" if not pd.isna(chg) else "—",
                  delta=f"{float(chg):+.1f}%" if not pd.isna(chg) else None, delta_color="inverse")
        seats = row.get("seats_now")
        m4.metric("Sitze verfügbar", str(int(seats)) if not pd.isna(seats) else "—")

        st.divider()

        df_hist = (df_op[df_op["train_number"] == sel_train]
                   .groupby("col_date").agg(price_min=("price_eur","min"), price_avg=("price_eur","mean"))
                   .reset_index().sort_values("col_date"))
        if not df_hist.empty:
            avg_l = float(df_hist["price_avg"].mean())
            fig   = px.line(df_hist, x="col_date", y="price_min",
                            title=f"Preisentwicklung — {sel_train} ({dep_str} Uhr)",
                            labels={"col_date":"Datum","price_min":"Tiefstpreis (€)"},
                            color_discrete_sequence=[op_color(sel_op_t)])
            fig.add_hline(y=avg_l, line_dash="dot", line_color="#888", annotation_text=f"Ø {avg_l:.2f} €")
            fig.update_traces(line_width=2, fill="tozeroy", fillcolor=hex_to_rgba(op_color(sel_op_t), 0.125))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Keine Verlaufsdaten für diesen Zug.")

        df_hz = (df_op[df_op["train_number"] == sel_train]
                 .dropna(subset=["booking_horizon_days"])
                 .groupby("booking_horizon_days")
                 .agg(price_avg=("price_eur","mean"), price_min=("price_eur","min"), observations=("price_eur","count"))
                 .reset_index().sort_values("booking_horizon_days"))
        if not df_hz.empty:
            tiefst_p = float(df_hz["price_avg"].min())
            tiefst_h = int(df_hz.loc[df_hz["price_avg"].idxmin(), "booking_horizon_days"])
            df_hz["aufschlag_pct"] = ((df_hz["price_avg"].astype(float) - tiefst_p) / tiefst_p * 100).round(1)
            df_hz["label"] = "+" + df_hz["booking_horizon_days"].astype(str) + "T"

            fig2 = px.bar(df_hz, x="label", y="aufschlag_pct", color="aufschlag_pct",
                          color_continuous_scale=["#a8e44a","#ffb547","#ff5f5f"],
                          range_color=[0, df_hz["aufschlag_pct"].max()],
                          title=f"Preisanstieg vom Tiefstpreis — {sel_train}\nBasis: Ø {tiefst_p:.2f} € bei +{tiefst_h} Tagen",
                          labels={"label":"Buchungshorizont","aufschlag_pct":"Aufschlag auf Tiefstpreis (%)"},
                          custom_data=["price_avg","observations","price_min"])
            fig2.update_traces(hovertemplate=(
                "<b>%{x}</b><br>+%{y:.1f}% teurer als Tiefstpreis<br>"
                "Ø %{customdata[0]:.2f} €<br>Min %{customdata[2]:.2f} €<br>%{customdata[1]} Beobachtungen"))
            fig2.update_coloraxes(showscale=False)
            st.plotly_chart(fig2, use_container_width=True)

            fig3 = px.line(df_hz, x="label", y="price_avg", markers=True,
                           title=f"Absoluter Preis nach Buchungshorizont — {sel_train}",
                           labels={"label":"Buchungshorizont","price_avg":"Ø Preis (€)"},
                           color_discrete_sequence=[op_color(sel_op_t)],
                           custom_data=["aufschlag_pct","observations"])
            fig3.update_traces(
                line_width=2, marker_size=7,
                fill="tozeroy", fillcolor=hex_to_rgba(op_color(sel_op_t), 0.083),
                hovertemplate="<b>%{x}</b><br>Ø %{y:.2f} €<br>+%{customdata[0]:.1f}% vs. Tiefstpreis<br>%{customdata[1]} Beobachtungen")
            fig3.add_hline(y=tiefst_p, line_dash="dot", line_color="#3B6D11",
                           annotation_text=f"Tiefstpreis {tiefst_p:.2f} €")
            st.plotly_chart(fig3, use_container_width=True)

            best  = df_hz.loc[df_hz["price_avg"].idxmin()]
            worst = df_hz.loc[df_hz["price_avg"].idxmax()]
            st.success(
                f"💡 **Empfehlung:** Bei +{int(best['booking_horizon_days'])} Tagen Vorlauf "
                f"war dieser Zug mit Ø **{float(best['price_avg']):.2f} €** am günstigsten "
                f"({int(best['observations'])} Beobachtungen). "
                f"Späteste Buchung (+{int(worst['booking_horizon_days'])}T) kostet "
                f"**{float(worst['aufschlag_pct']):.1f}% mehr**."
            )
        else:
            st.info("Keine Horizont-Daten für diesen Zug.")


# ════════════════════════════════════════════
# TAB 3 — BUCHUNGSHORIZONT
# ════════════════════════════════════════════

with tab3:
    st.subheader(f"Buchungshorizont — {origin} → {destination}")
    df_h = (df.dropna(subset=["booking_horizon_days"])
            .groupby(["operator","booking_horizon_days"])
            .agg(price_avg=("price_eur","mean"), price_min=("price_eur","min"), observations=("price_eur","count"))
            .reset_index().sort_values(["operator","booking_horizon_days"]))

    if df_h.empty:
        st.info("Keine Horizont-Daten.")
    else:
        df_h["op_label"]            = df_h["operator"].map(op_label)
        df_h["booking_horizon_days"] = df_h["booking_horizon_days"].astype(int)
        color_map = make_color_map(operators)

        fig = px.line(df_h, x="booking_horizon_days", y="price_avg", color="op_label",
                      color_discrete_map=color_map, markers=True,
                      title="Ø Preis je Operator nach Buchungshorizont",
                      labels={"booking_horizon_days":"Tage im Voraus","price_avg":"Ø Preis (€)","op_label":"Operator"},
                      custom_data=["observations","price_min"])
        fig.update_traces(line_width=2, marker_size=7,
                          hovertemplate="<b>%{fullData.name}</b><br>+%{x} Tage<br>Ø %{y:.2f} €<br>"
                                        "Min %{customdata[1]:.2f} €<br>%{customdata[0]} Beobachtungen")
        fig.update_layout(hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

        fig_freq = px.bar(df_h, x="booking_horizon_days", y="observations", color="op_label",
                          color_discrete_map=color_map, barmode="group",
                          title="Anzahl erfasste Verbindungen je Buchungshorizont",
                          labels={"booking_horizon_days":"Tage im Voraus","observations":"Anzahl Verbindungen","op_label":"Operator"})
        fig_freq.update_layout(hovermode="x unified")
        st.plotly_chart(fig_freq, use_container_width=True)

        st.subheader("Detailtabelle — Ø Preis je Operator und Horizont")
        pivot = df_h.pivot_table(index="operator", columns="booking_horizon_days", values="price_avg").round(2)
        pivot.index   = pivot.index.map(op_label)
        pivot.columns = ["+" + str(int(c)) + "T" for c in pivot.columns]
        st.dataframe(pivot, use_container_width=True)

        st.subheader("Optimaler Buchungszeitpunkt je Operator")
        cols = st.columns(max(1, len(df_h["operator"].unique())))
        for i, op in enumerate(sorted(df_h["operator"].unique())):
            df_op_h = df_h[df_h["operator"] == op]
            best  = df_op_h.loc[df_op_h["price_avg"].idxmin()]
            worst = df_op_h.loc[df_op_h["price_avg"].idxmax()]
            saving = (float(worst["price_avg"]) - float(best["price_avg"])) / float(worst["price_avg"]) * 100
            with cols[i]:
                st.markdown(f"**{op_label(op)}**")
                st.metric("Günstigst bei", f"+{int(best['booking_horizon_days'])} Tage",
                          f"spart {saving:.0f}%", delta_color="off")
                st.caption(f"Ø {float(best['price_avg']):.2f} € ({int(best['observations'])} Beob.)")


# ════════════════════════════════════════════
# TAB 4 — TAGESZEIT
# ════════════════════════════════════════════

with tab4:
    st.subheader(f"Tageszeit-Analyse — {origin} → {destination}")
    sel_dt_op = st.selectbox("Operator", operators, format_func=op_label, key="dt_op")
    df_dt = df[df["operator"] == sel_dt_op].copy()

    if df_dt.empty:
        st.info("Keine Daten für diesen Operator.")
    else:
        df_hour = (df_dt.groupby("dep_hour")["price_eur"].mean().reset_index()
                   .rename(columns={"price_eur":"price_avg","dep_hour":"hour"}))
        df_hour["hour_label"] = df_hour["hour"].astype(str).str.zfill(2) + ":00"
        fig = px.bar(df_hour, x="hour_label", y="price_avg", color="price_avg",
                     color_continuous_scale=["#a8e44a","#ffb547","#ff5f5f"],
                     title=f"Ø Preis nach Abfahrtsstunde — {op_label(sel_dt_op)}",
                     labels={"hour_label":"Abfahrtsstunde","price_avg":"Ø Preis (€)"})
        fig.update_coloraxes(showscale=False)
        st.plotly_chart(fig, use_container_width=True)

        df_dt["dow_label"]  = df_dt["dep_dow"].map(DOW_LABELS)
        df_dt["hour_label"] = df_dt["dep_hour"].astype(str).str.zfill(2) + ":00"
        pivot_heat = df_dt.pivot_table(index="dow_label", columns="hour_label",
                                       values="price_eur", aggfunc="mean").round(2)
        pivot_heat = pivot_heat.reindex([d for d in ["Mo","Di","Mi","Do","Fr","Sa","So"] if d in pivot_heat.index])
        if not pivot_heat.empty:
            fig2 = px.imshow(pivot_heat, color_continuous_scale=["#1a3a1a","#a8e44a","#ffb547","#ff5f5f"],
                             labels={"x":"Abfahrtsstunde","y":"Wochentag","color":"Ø Preis (€)"},
                             title=f"Heatmap — Ø Preis je Wochentag und Stunde ({op_label(sel_dt_op)})",
                             aspect="auto")
            fig2.update_xaxes(tickangle=45)
            st.plotly_chart(fig2, use_container_width=True)

        df_seats_h = (df_dt.dropna(subset=["seats_available"])
                      .groupby("dep_hour")["seats_available"].mean().reset_index()
                      .rename(columns={"seats_available":"seats_avg","dep_hour":"hour"}))
        if not df_seats_h.empty:
            df_seats_h["hour_label"] = df_seats_h["hour"].astype(str).str.zfill(2) + ":00"
            fig3 = px.line(df_seats_h, x="hour_label", y="seats_avg", markers=True,
                           title=f"Ø verfügbare Sitze nach Abfahrtsstunde — {op_label(sel_dt_op)}",
                           labels={"hour_label":"Abfahrtsstunde","seats_avg":"Ø Sitze"},
                           color_discrete_sequence=[op_color(sel_dt_op)])
            fig3.update_traces(line_width=2)
            st.plotly_chart(fig3, use_container_width=True)

        if not df_hour.empty:
            min_h  = df_hour.loc[df_hour["price_avg"].idxmin()]
            max_h  = df_hour.loc[df_hour["price_avg"].idxmax()]
            df_dow = df_dt.groupby("dow_label")["price_eur"].mean()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Günstigste Stunde", min_h["hour_label"], f"Ø {float(min_h['price_avg']):.2f} €")
            c2.metric("Teuerste Stunde",   max_h["hour_label"], f"Ø {float(max_h['price_avg']):.2f} €")
            if not df_dow.empty:
                c3.metric("Günstigster Tag", df_dow.idxmin(), f"Ø {float(df_dow.min()):.2f} €")
                c4.metric("Teuerster Tag",   df_dow.idxmax(), f"Ø {float(df_dow.max()):.2f} €")


# ════════════════════════════════════════════
# TAB 5 — OPERATOR-VERGLEICH
# ════════════════════════════════════════════

with tab5:
    st.subheader("Operator-Vergleich & Streckenvergleich")
    st.markdown("#### Strecken vergleichen")
    all_routes         = routes_df["label"].tolist()
    sel_routes_compare = st.multiselect(
        "Strecken für Vergleich", options=all_routes,
        default=[st.session_state.get("selected_label", all_routes[0])],
        key="route_compare",
    )

    if len(sel_routes_compare) >= 2:
        frames, frames_freq = [], []
        for rl in sel_routes_compare:
            r_row   = routes_df[routes_df["label"] == rl].iloc[0]
            df_r    = filter_route(df_all, r_row["origin_name"], r_row["destination_name"])
            df_hz_r = (df_r.dropna(subset=["booking_horizon_days"])
                       .groupby("booking_horizon_days")
                       .agg(price_avg=("price_eur","mean"), price_min=("price_eur","min")).reset_index())
            df_hz_r["route"]              = rl
            df_hz_r["booking_horizon_days"] = df_hz_r["booking_horizon_days"].astype(int)
            frames.append(df_hz_r)

            df_fq = (df_r.dropna(subset=["booking_horizon_days"])
                     .groupby("booking_horizon_days").agg(anzahl=("price_eur","count")).reset_index())
            df_fq["route"]              = rl
            df_fq["booking_horizon_days"] = df_fq["booking_horizon_days"].astype(int)
            frames_freq.append(df_fq)

        df_routes_hz = pd.concat(frames, ignore_index=True)
        fig_rc = px.line(df_routes_hz, x="booking_horizon_days", y="price_avg", color="route", markers=True,
                         title="Ø Preis nach Buchungshorizont — Streckenvergleich",
                         labels={"booking_horizon_days":"Tage im Voraus","price_avg":"Ø Preis (€)"})
        fig_rc.update_traces(line_width=2, marker_size=6)
        fig_rc.update_layout(hovermode="x unified")
        st.plotly_chart(fig_rc, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            df_routes_min = (df_routes_hz.groupby("route")
                             .agg(tiefstpreis=("price_min","min")).reset_index().sort_values("tiefstpreis"))
            fig_rm = px.bar(df_routes_min, x="route", y="tiefstpreis", color="route",
                            title="Tiefstpreis je Strecke", labels={"tiefstpreis":"Tiefstpreis (€)"},
                            text="tiefstpreis")
            fig_rm.update_traces(texttemplate="%{text:.2f} €", textposition="outside")
            fig_rm.update_layout(showlegend=False)
            st.plotly_chart(fig_rm, use_container_width=True)
        with col2:
            df_freq_rc = pd.concat(frames_freq, ignore_index=True)
            fig_fq = px.bar(df_freq_rc, x="booking_horizon_days", y="anzahl", color="route",
                            barmode="group", title="Anzahl Verbindungen je Horizont",
                            labels={"booking_horizon_days":"Tage im Voraus","anzahl":"Anzahl"})
            fig_fq.update_layout(hovermode="x unified")
            st.plotly_chart(fig_fq, use_container_width=True)
    else:
        st.info("Wähle mindestens 2 Strecken für den Vergleich." if sel_routes_compare else "Keine Strecke ausgewählt.")

    st.divider()
    st.markdown(f"#### Operator-Vergleich — {origin} → {destination}")
    horizon_val = st.select_slider("Buchungshorizont",
                                   options=[1,2,3,4,5,6,7,10,14,21,30,45,60,90], value=14, key="cp_h")
    df_cp = (df[df["booking_horizon_days"] == horizon_val].groupby("operator")
             .agg(price_min=("price_eur","min"), price_avg=("price_eur","mean"),
                  price_max=("price_eur","max"), seats_avg=("seats_available","mean"),
                  observations=("price_eur","count")).reset_index().sort_values("price_min"))

    if df_cp.empty:
        st.info(f"Keine Daten für Buchungshorizont +{horizon_val} Tage.")
    else:
        df_cp["op_label"] = df_cp["operator"].map(op_label)
        min_p, max_p      = float(df_cp["price_min"].min()), float(df_cp["price_min"].max())
        savings    = (max_p - min_p) / max_p * 100 if max_p > 0 else 0
        cheapest   = df_cp.iloc[0]
        most_exp   = df_cp.iloc[-1]
        color_map  = make_color_map(operators)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Günstigster Operator", op_label(cheapest["operator"]), f"{float(cheapest['price_min']):.2f} €")
        c2.metric("Teuerster Operator",   op_label(most_exp["operator"]), f"{float(most_exp['price_min']):.2f} €")
        c3.metric("Max. Ersparnis", f"{savings:.0f}%", help="Durch Wahl des günstigsten Operators")
        c4.metric("Buchungshorizont", f"+{horizon_val} Tage")

        col_l, col_r = st.columns(2)
        with col_l:
            fig = go.Figure()
            for _, row in df_cp.iterrows():
                c = op_color(row["operator"])
                fig.add_trace(go.Bar(
                    name=row["op_label"], x=["Min","Ø","Max"],
                    y=[float(row["price_min"]), float(row["price_avg"]), float(row["price_max"])],
                    marker_color=[hex_to_rgba(c, 0.8), hex_to_rgba(c, 0.533), hex_to_rgba(c, 0.267)],
                    marker_line_color=c, marker_line_width=1))
            fig.update_layout(barmode="group", yaxis_title="Preis (€)",
                              title=f"Preisvergleich bei +{horizon_val} Tagen — Min / Ø / Max")
            st.plotly_chart(fig, use_container_width=True)
        with col_r:
            df_cp["diff_pct"] = ((df_cp["price_min"].astype(float) - min_p) / min_p * 100).round(1)
            fig2 = px.bar(df_cp, x="op_label", y="diff_pct", color="diff_pct",
                          color_continuous_scale=["#a8e44a","#ffb547","#ff5f5f"],
                          title=f"Mehrkosten vs. {op_label(cheapest['operator'])}",
                          labels={"op_label":"Operator","diff_pct":"% teurer"}, text="diff_pct")
            fig2.update_traces(texttemplate="+%{text:.1f}%", textposition="outside")
            fig2.update_coloraxes(showscale=False)
            st.plotly_chart(fig2, use_container_width=True)

        df_seats = df_cp[df_cp["seats_avg"].notna()].copy()
        if not df_seats.empty:
            fig3 = px.scatter(df_seats, x="price_min", y="seats_avg", color="op_label",
                              color_discrete_map=color_map, size=[20]*len(df_seats), text="op_label",
                              title="Tiefstpreis vs. Ø verfügbare Sitze",
                              labels={"price_min":"Tiefstpreis (€)","seats_avg":"Ø Sitze","op_label":"Operator"},
                              custom_data=["observations"])
            fig3.update_traces(textposition="top center",
                               hovertemplate="<b>%{text}</b><br>%{x:.2f} €<br>%{y:.0f} Sitze Ø<br>%{customdata[0]} Beob.")
            st.plotly_chart(fig3, use_container_width=True)

        df_seats_h = (df.dropna(subset=["seats_available","booking_horizon_days"])
                      .groupby(["operator","booking_horizon_days"])
                      .agg(seats_avg=("seats_available","mean")).reset_index())
        if not df_seats_h.empty:
            df_seats_h["op_label"] = df_seats_h["operator"].map(op_label)
            fig4 = px.line(df_seats_h, x="booking_horizon_days", y="seats_avg", color="op_label",
                           color_discrete_map=color_map, markers=True,
                           title="Ø verfügbare Sitze nach Buchungshorizont",
                           labels={"booking_horizon_days":"Tage im Voraus","seats_avg":"Ø Sitze","op_label":"Operator"})
            st.plotly_chart(fig4, use_container_width=True)


# ════════════════════════════════════════════
# TAB 6 — CRAWLER STATUS & STEUERUNG
# ════════════════════════════════════════════

with tab6:
    st.subheader("Crawler-Status & Steuerung")

    with st.expander("▶ Crawler manuell starten", expanded=True):
        if DATA_SOURCE == "csv":
            st.info(
                "Aktuell im **CSV-Modus**. Crawler schreiben in die Datenbank.\n\n"
                "Zum Aktivieren: `DATA_SOURCE = 'db'` am Anfang setzen und DB konfigurieren."
            )

        available = [op for op, cls in CRAWLER_CLASSES.items() if cls]
        if CRAWLER_IMPORT_ERRORS:
            with st.expander(f"⚠️ {len(CRAWLER_IMPORT_ERRORS)} Import-Fehler"):
                for op, err in CRAWLER_IMPORT_ERRORS.items():
                    st.code(f"{op_label(op)}: {err}", language=None)

        col_sel, col_btn = st.columns([3, 1])
        with col_sel:
            to_run = st.multiselect("Crawler auswählen", options=available, default=available,
                                    format_func=op_label, key="manual_ops")
        with col_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            clicked = st.button("▶ Jetzt starten",
                                disabled=st.session_state.running or not to_run,
                                use_container_width=True)

        if clicked and to_run:
            st.session_state.log     = []
            st.session_state.running = True
            threading.Thread(target=_run_crawlers_thread, args=(st.session_state.log, to_run), daemon=True).start()
            st.rerun()

        if st.session_state.log:
            st.code("\n".join(st.session_state.log), language=None)
            if "abgeschlossen" in (st.session_state.log[-1] if st.session_state.log else ""):
                if st.session_state.running:
                    st.session_state.running = False
                    st.cache_data.clear()
            if st.session_state.running:
                st.button("🔄 Log aktualisieren", on_click=st.rerun)

    st.divider()
    st.subheader("Datenstatus")
    df_by_op = (df_all.groupby("operator")
                .agg(records=("price_eur","count"), last_collected=("collected_at","max"),
                     first_collected=("collected_at","min"), routes=("route_id","nunique"),
                     avg_price=("price_eur","mean"))
                .reset_index().sort_values("records", ascending=False))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Records gesamt",    f'{len(df_all):,}'.replace(",", "."))
    c2.metric("Operator",          df_all["operator"].nunique())
    c3.metric("Strecken",          df_all["route_id"].nunique())
    c4.metric("Zuletzt gesammelt", time_since(df_all["collected_at"].max()))

    st.subheader("Status je Crawler / Operator")
    for _, row in df_by_op.iterrows():
        col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 1, 2])
        with col1:
            st.markdown(f'<span style="color:{op_color(row["operator"])}">●</span> **{op_label(row["operator"])}**',
                        unsafe_allow_html=True)
        col2.metric("", time_since(row["last_collected"]),             label_visibility="collapsed")
        col3.metric("", f'{int(row["records"]):,}'.replace(",", "."), label_visibility="collapsed")
        col4.metric("", int(row["routes"]),                            label_visibility="collapsed")
        col5.metric("", f"{float(row['avg_price']):.2f} €",           label_visibility="collapsed")

    color_map = make_color_map(OPERATOR_COLORS.keys())
    df_by_op["op_label"] = df_by_op["operator"].map(op_label)
    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(df_by_op.sort_values("records"), x="records", y="op_label", orientation="h",
                     color="op_label", color_discrete_map=color_map,
                     title="Records gesamt je Crawler", labels={"records":"Records","op_label":"Crawler"})
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        df_daily = df_all.groupby(["col_date","operator"]).agg(records=("price_eur","count")).reset_index()
        df_daily["op_label"] = df_daily["operator"].map(op_label)
        fig2 = px.bar(df_daily, x="col_date", y="records", color="op_label",
                      color_discrete_map=color_map, title="Records pro Tag je Crawler",
                      labels={"col_date":"Datum","records":"Records","op_label":"Crawler"})
        fig2.update_layout(barmode="stack")
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    col_i, col_s = st.columns([3, 1])
    with col_i:
        st.info("**Automatischer Tagesrun:** täglich 03:00 Uhr — alle Crawler\n"
                "Aktiv sobald `DATA_SOURCE = 'db'` gesetzt ist.\n"
                "Uhrzeit ändern: `hour=3, minute=0` in `_start_scheduler()` anpassen.")
    with col_s:
        st.success("✅ Scheduler\nläuft" if st.session_state.sched_ok else "⚠️ Scheduler\ninaktiv\n(CSV-Modus)")
