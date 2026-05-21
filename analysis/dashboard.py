import importlib
import os
import sys
import threading
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

# ── translations ──────────────────────────────────────────────────────────────
EN = {
    "csv_mode": "📁 CSV Mode", "db_mode": "🗄️ DB Mode",
    "sched_active": "⚙️ Scheduler active — daily at 03:00",
    "crawlers_running": "🔄 Crawlers running...", "no_data": "No data found.",
    "enter_route": "**Enter route**", "from_label": "From", "origin_ph": "Origin...",
    "to_label": "To", "dest_ph": "Destination...", "route_not_found": "Route not found:",
    "route_label": "Route", "data_points": "Data points", "last_label": "Last:",
    "reload_data": "🔄 Reload data", "operators_on_route": "**Operators on this route:**",
    "routes_found": lambda n: f"{n} route{'s' if n != 1 else ''} found",
    "region_de": "🇩🇪 Germany", "region_it": "🇮🇹 Italy", "region_es": "🇪🇸 Spain",
    "region_fr": "🇫🇷 France", "region_int": "🌍 International", "region_other": "🌐 Other",
    "just_now": "just now", "min_ago": "{m} min. ago", "h_ago": "{h} h ago",
    "days_ago": "{d} days ago", "days_unit": "days",
    "tab_overview": "📊 Overview", "tab_train": "🚆 Individual Train",
    "tab_horizon": "⏱ Booking Horizon", "tab_daytime": "🕐 Time of Day",
    "tab_operator": "⚖️ Operator Comparison", "tab_crawler": "🤖 Crawler Status",
    "dow": {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"},
    # overview
    "ov_time_range": "Time range (days back)", "ov_no_data": "No data in the selected time range.",
    "ov_lowest_price": "Overall lowest price", "ov_avg_price": "Avg. price overall",
    "ov_trend": "Trend (last 7d)", "ov_operators": "Operators",
    "ov_date": "Date", "ov_low_lbl": "Lowest price (€)", "ov_op": "Operator",
    "ov_price": "Price (€)", "ov_dep_hour": "Departure hour", "ov_count": "Count",
    "ov_days_adv": "Days in advance", "ov_fare_classes": "Fare classes",
    "ov_class": "Class", "ov_avg": "Avg. price (€)",
    "ov_c1": "Lowest price per day — last {days} days",
    "ov_c2": "Price range Min / Avg / Max per operator (diamond = average)",
    "ov_c3": "Number of connections per departure hour and operator",
    "ov_c4": "Number of recorded connections per booking horizon",
    "ov_c5": "Avg. price per fare class and operator",
    # individual train
    "tr_head": "Individual Train — {orig} → {dest}",
    "tr_no_data": "No data with train number for this route.",
    "tr_op": "Operator", "tr_sel": "Select train",
    "tr_cur": "Current price", "tr_fare": "Fare: {fare}",
    "tr_lohi": "Lowest / Highest", "tr_7d": "7-day change", "tr_seats": "Seats available",
    "tr_dev": "Price development — {train} ({dep})",
    "tr_no_hist": "No historical data for this train.",
    "tr_sur_title": "Price increase from lowest price — {train}\nBasis: Avg. {price:.2f} € at +{horizon} days",
    "tr_hz_lbl": "Booking horizon", "tr_sur_lbl": "Surcharge on lowest price (%)",
    "tr_abs": "Absolute price by booking horizon — {train}",
    "tr_low_line": "Lowest price {price:.2f} €",
    "tr_rec": (
        "💡 **Recommendation:** At +{days} days in advance this train was cheapest at avg. "
        "**{price:.2f} €** ({obs} observations). Latest booking (+{worst}d) costs **{pct:.1f}% more**."
    ),
    "tr_no_hz": "No horizon data for this train.",
    # booking horizon
    "bh_head": "Booking Horizon — {orig} → {dest}", "bh_no": "No horizon data.",
    "bh_c1": "Avg. price per operator by booking horizon",
    "bh_avg": "Avg. price (€)",
    "bh_c2": "Number of recorded connections per booking horizon",
    "bh_conn": "Number of connections",
    "bh_table": "Detail table — Avg. price per operator and horizon",
    "bh_opt": "Optimal booking time per operator",
    "bh_cheap": "Cheapest at", "bh_saves": "saves {pct:.0f}%",
    "bh_cap": "Avg. {price:.2f} € ({obs} obs.)",
    # time of day
    "dt_head": "Time of Day Analysis — {orig} → {dest}",
    "dt_op": "Operator", "dt_no": "No data for this operator.",
    "dt_c1": "Avg. price by departure hour — {op}",
    "dt_c2": "Heatmap — Avg. price per weekday and hour ({op})",
    "dt_wd": "Weekday", "dt_c3": "Avg. available seats by departure hour — {op}",
    "dt_seats": "Avg. seats",
    "dt_ch_h": "Cheapest hour", "dt_ex_h": "Most expensive hour",
    "dt_ch_d": "Cheapest day", "dt_ex_d": "Most expensive day",
    # operator comparison
    "op_head": "Operator Comparison & Route Comparison",
    "op_comp": "#### ⚖️ Operator Comparison — {orig} → {dest}",
    "op_hz": "Booking horizon",
    "op_no_hz": "No data for booking horizon +{days} days.",
    "op_cheap": "Cheapest", "op_exp": "Most expensive",
    "op_sav": "Max. savings", "op_sav_help": "By choosing the cheapest operator",
    "op_hz_m": "Horizon", "op_mam": "Min / Avg / Max at +{days}d",
    "op_extra": "Extra cost vs. {op}", "op_pct": "% more expensive",
    "op_prof": "**Operator Profile**",
    "op_radar_cats": ["Cheap Price", "Price Stability", "Availability", "Data Density"],
    "op_radar_t": "Operator profile at +{days}d",
    "op_radar_c": (
        "Cheap Price: lower min price = better · Price Stability: smaller spread = better · "
        "Availability: more seats = better · Data Density: more data points = better"
    ),
    "op_scatter": "Lowest price vs. avg. available seats",
    "op_seats_hz": "Avg. available seats by booking horizon",
    "op_low": "Lowest price (€)", "op_seats": "Avg. seats",
    "op_route_head": "#### 🔀 Route Comparison",
    "op_routes_lbl": "Routes to compare",
    "op_badge": " 🏆 Cheapest", "op_avg": "Avg.", "op_pts": "pts",
    "op_sel2": "Select at least 2 routes to compare.",
    "op_no_rt": "No route selected.",
    "op_hz_t": "Avg. price by booking horizon",
    "op_low_rt": "Lowest price per route",
    "op_conn": "Connections per horizon",
    # crawler
    "cr_head": "Crawler Status & Control",
    "cr_ctrl": "#### 🤖 Crawler Control",
    "cr_csv": (
        "Currently in **CSV mode**. Crawlers write to the database.\n\n"
        "To activate: set `DATA_SOURCE = 'db'` at the top and configure the DB."
    ),
    "cr_err": "⚠️ {n} import errors",
    "cr_sel": "Select crawlers", "cr_start": "▶ Start now",
    "cr_auto": (
        "**Automatic daily run:** every day at 03:00 — all crawlers. "
        "Active once `DATA_SOURCE = 'db'` is set."
    ),
    "cr_on": "✅ Active", "cr_off": "⚠️ Inactive",
    "cr_status": "#### 📋 Status per Crawler",
    "cr_stat_cap": "Crawler · Last collected · Records · Routes · Avg. price",
    "cr_refresh": "🔄 Refresh log",
    "cr_data": "#### 📊 Data Overview",
    "cr_total": "Total records", "cr_ops": "Operators",
    "cr_routes": "Routes", "cr_last": "Last collected",
    "cr_c1": "Total records per crawler",
    "cr_rec": "Records", "cr_cr": "Crawler",
    "cr_c2": "Records per day per crawler", "cr_date": "Date",
}

DE = {
    "csv_mode": "📁 CSV-Modus", "db_mode": "🗄️ DB-Modus",
    "sched_active": "⚙️ Scheduler aktiv — täglich um 03:00",
    "crawlers_running": "🔄 Crawler laufen...", "no_data": "Keine Daten gefunden.",
    "enter_route": "**Route eingeben**", "from_label": "Von", "origin_ph": "Herkunft...",
    "to_label": "Nach", "dest_ph": "Ziel...", "route_not_found": "Route nicht gefunden:",
    "route_label": "Route", "data_points": "Datenpunkte", "last_label": "Zuletzt:",
    "reload_data": "🔄 Daten neu laden", "operators_on_route": "**Anbieter auf dieser Strecke:**",
    "routes_found": lambda n: f"{n} Route{'n' if n != 1 else ''} gefunden",
    "region_de": "🇩🇪 Deutschland", "region_it": "🇮🇹 Italien", "region_es": "🇪🇸 Spanien",
    "region_fr": "🇫🇷 Frankreich", "region_int": "🌍 International", "region_other": "🌐 Sonstige",
    "just_now": "gerade eben", "min_ago": "vor {m} Min.", "h_ago": "vor {h} Std.",
    "days_ago": "vor {d} Tagen", "days_unit": "Tage",
    "tab_overview": "📊 Übersicht", "tab_train": "🚆 Einzelzug",
    "tab_horizon": "⏱ Buchungshorizont", "tab_daytime": "🕐 Tageszeit",
    "tab_operator": "⚖️ Anbietervergleich", "tab_crawler": "🤖 Crawler-Status",
    "dow": {0: "Mo", 1: "Di", 2: "Mi", 3: "Do", 4: "Fr", 5: "Sa", 6: "So"},
    "days_unit": "Tage",
    "ov_time_range": "Zeitraum (Tage zurück)", "ov_no_data": "Keine Daten im gewählten Zeitraum.",
    "ov_lowest_price": "Niedrigster Gesamtpreis", "ov_avg_price": "Durchschnittspreis gesamt",
    "ov_trend": "Trend (letzte 7T)", "ov_operators": "Anbieter",
    "ov_date": "Datum", "ov_low_lbl": "Niedrigster Preis (€)", "ov_op": "Anbieter",
    "ov_price": "Preis (€)", "ov_dep_hour": "Abfahrtsstunde", "ov_count": "Anzahl",
    "ov_days_adv": "Tage im Voraus", "ov_fare_classes": "Tarifklassen",
    "ov_class": "Klasse", "ov_avg": "Durchschnittspreis (€)",
    "ov_c1": "Niedrigster Preis pro Tag — letzte {days} Tage",
    "ov_c2": "Preisrange Min / Avg / Max pro Anbieter (Raute = Durchschnitt)",
    "ov_c3": "Anzahl Verbindungen pro Abfahrtsstunde und Anbieter",
    "ov_c4": "Anzahl aufgezeichneter Verbindungen pro Buchungshorizont",
    "ov_c5": "Durchschnittspreis pro Tarifklasse und Anbieter",
    "tr_head": "Einzelzug — {orig} → {dest}",
    "tr_no_data": "Keine Daten mit Zugnummer für diese Strecke.",
    "tr_op": "Anbieter", "tr_sel": "Zug auswählen",
    "tr_cur": "Aktueller Preis", "tr_fare": "Tarif: {fare}",
    "tr_lohi": "Min / Max", "tr_7d": "7-Tage-Änderung", "tr_seats": "Verfügbare Plätze",
    "tr_dev": "Preisentwicklung — {train} ({dep})",
    "tr_no_hist": "Keine historischen Daten für diesen Zug.",
    "tr_sur_title": "Preisaufschlag zum Tiefstwert — {train}\nBasis: Avg. {price:.2f} € bei +{horizon} Tagen",
    "tr_hz_lbl": "Buchungshorizont", "tr_sur_lbl": "Aufpreis auf Tiefstwert (%)",
    "tr_abs": "Absoluter Preis nach Buchungshorizont — {train}",
    "tr_low_line": "Tiefstwert {price:.2f} €",
    "tr_rec": (
        "💡 **Empfehlung:** Bei +{days} Tagen im Voraus war dieser Zug am günstigsten mit "
        "durchschn. **{price:.2f} €** ({obs} Beobachtungen). Späteste Buchung (+{worst}T) kostet **{pct:.1f}% mehr**."
    ),
    "tr_no_hz": "Keine Horizont-Daten für diesen Zug.",
    "bh_head": "Buchungshorizont — {orig} → {dest}", "bh_no": "Keine Horizont-Daten.",
    "bh_c1": "Durchschnittspreis pro Anbieter nach Buchungshorizont",
    "bh_avg": "Durchschnittspreis (€)",
    "bh_c2": "Anzahl aufgezeichneter Verbindungen pro Buchungshorizont",
    "bh_conn": "Anzahl Verbindungen",
    "bh_table": "Detailtabelle — Durchschnittspreis pro Anbieter und Horizont",
    "bh_opt": "Optimaler Buchungszeitpunkt pro Anbieter",
    "bh_cheap": "Günstigst bei", "bh_saves": "spart {pct:.0f}%",
    "bh_cap": "Avg. {price:.2f} € ({obs} Beob.)",
    "dt_head": "Tageszeit-Analyse — {orig} → {dest}",
    "dt_op": "Anbieter", "dt_no": "Keine Daten für diesen Anbieter.",
    "dt_c1": "Durchschnittspreis nach Abfahrtsstunde — {op}",
    "dt_c2": "Heatmap — Durchschnittspreis pro Wochentag und Stunde ({op})",
    "dt_wd": "Wochentag", "dt_c3": "Durchschn. verfügbare Plätze nach Abfahrtsstunde — {op}",
    "dt_seats": "Durchschn. Plätze",
    "dt_ch_h": "Günstigste Stunde", "dt_ex_h": "Teuerste Stunde",
    "dt_ch_d": "Günstigster Tag", "dt_ex_d": "Teuerster Tag",
    "op_head": "Anbietervergleich & Streckenvergleich",
    "op_comp": "#### ⚖️ Anbietervergleich — {orig} → {dest}",
    "op_hz": "Buchungshorizont",
    "op_no_hz": "Keine Daten für Buchungshorizont +{days} Tage.",
    "op_cheap": "Günstigster", "op_exp": "Teuerster",
    "op_sav": "Max. Ersparnis", "op_sav_help": "Durch Wahl des günstigsten Anbieters",
    "op_hz_m": "Horizont", "op_mam": "Min / Avg / Max bei +{days}T",
    "op_extra": "Mehrkosten vs. {op}", "op_pct": "% teurer",
    "op_prof": "**Anbieter-Profil**",
    "op_radar_cats": ["Günstiger Preis", "Preisstabilität", "Verfügbarkeit", "Datendichte"],
    "op_radar_t": "Anbieter-Profil bei +{days}T",
    "op_radar_c": (
        "Günstiger Preis: niedrigerer Mindestpreis = besser · Preisstabilität: kleinere Spanne = besser · "
        "Verfügbarkeit: mehr Plätze = besser · Datendichte: mehr Datenpunkte = besser"
    ),
    "op_scatter": "Niedrigster Preis vs. durchschn. verfügbare Plätze",
    "op_seats_hz": "Durchschn. verfügbare Plätze nach Buchungshorizont",
    "op_low": "Niedrigster Preis (€)", "op_seats": "Durchschn. Plätze",
    "op_route_head": "#### 🔀 Streckenvergleich",
    "op_routes_lbl": "Strecken vergleichen",
    "op_badge": " 🏆 Günstigste", "op_avg": "Avg.", "op_pts": "Pkt.",
    "op_sel2": "Mindestens 2 Strecken auswählen.",
    "op_no_rt": "Keine Strecke ausgewählt.",
    "op_hz_t": "Durchschnittspreis nach Buchungshorizont",
    "op_low_rt": "Niedrigster Preis pro Strecke",
    "op_conn": "Verbindungen pro Horizont",
    "cr_head": "Crawler-Status & Steuerung",
    "cr_ctrl": "#### 🤖 Crawler-Steuerung",
    "cr_csv": (
        "Aktuell im **CSV-Modus**. Crawler schreiben in die Datenbank.\n\n"
        "Zum Aktivieren: `DATA_SOURCE = 'db'` oben setzen und DB konfigurieren."
    ),
    "cr_err": "⚠️ {n} Importfehler",
    "cr_sel": "Crawler auswählen", "cr_start": "▶ Jetzt starten",
    "cr_auto": (
        "**Automatischer Tagesrun:** täglich um 03:00 — alle Crawler. "
        "Aktiv wenn `DATA_SOURCE = 'db'` gesetzt ist."
    ),
    "cr_on": "✅ Aktiv", "cr_off": "⚠️ Inaktiv",
    "cr_status": "#### 📋 Status pro Crawler",
    "cr_stat_cap": "Crawler · Zuletzt · Einträge · Strecken · Durchschnittspreis",
    "cr_refresh": "🔄 Log aktualisieren",
    "cr_data": "#### 📊 Datenübersicht",
    "cr_total": "Einträge gesamt", "cr_ops": "Anbieter",
    "cr_routes": "Strecken", "cr_last": "Zuletzt gesammelt",
    "cr_c1": "Einträge pro Crawler",
    "cr_rec": "Einträge", "cr_cr": "Crawler",
    "cr_c2": "Einträge pro Tag pro Crawler", "cr_date": "Datum",
}
TEXTS = {"en": EN, "de": DE}

# ── helpers ───────────────────────────────────────────────────────────────────
def op_label(op): return OPERATOR_LABELS.get(op, op)
def op_color(op): return OPERATOR_COLORS.get(op, "#888888")

def hex_to_rgba(hex_color: str, alpha: float = 0.533) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

def make_color_map(ops) -> dict:
    return {op_label(o): op_color(o) for o in ops}

def time_since(dt, T) -> str:
    try:
        diff = (datetime.now() - pd.to_datetime(dt)).total_seconds()
        if diff < 60:    return T["just_now"]
        if diff < 3600:  return T["min_ago"].format(m=int(diff/60))
        if diff < 86400: return T["h_ago"].format(h=int(diff/3600))
        return T["days_ago"].format(d=int(diff/86400))
    except Exception:
        return "—"

def agg_price_range(df, group_col):
    return (df.groupby(group_col)
            .agg(price_min=("price_eur","min"), price_avg=("price_eur","mean"), price_max=("price_eur","max"))
            .reset_index())

# ── data loading ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_all_data() -> pd.DataFrame:
    if DATA_SOURCE == "csv":
        df = pd.read_csv(CSV_PATH, low_memory=False,
                         parse_dates=["collected_at", "departure_at", "arrival_at"])
    else:
        import psycopg2
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST","localhost"), port=os.getenv("DB_PORT","5432"),
            dbname=os.getenv("DB_NAME","rail_data"), user=os.getenv("DB_USER","rail_user"),
            password=os.getenv("DB_PASSWORD"),
        )
        df = pd.read_sql("""
            SELECT id, collected_at, departure_at, arrival_at,
                   operator, origin_id, destination_id, origin_name, destination_name,
                   route_id, train_number, fare_class, price_eur,
                   seats_available, is_direct, booking_horizon_days
            FROM price_observations ORDER BY collected_at DESC
        """, conn); conn.close()
    for col in ["collected_at","departure_at","arrival_at"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True).dt.tz_convert(None)
    df["price_eur"]            = pd.to_numeric(df["price_eur"], errors="coerce")
    df["seats_available"]      = pd.to_numeric(df["seats_available"], errors="coerce")
    df["booking_horizon_days"] = pd.to_numeric(df["booking_horizon_days"], errors="coerce").astype("Int64")
    df["is_direct"]            = df["is_direct"].map({"t":True,"f":False,True:True,False:False})
    df["dep_hour"] = df["departure_at"].dt.hour
    df["dep_dow"]  = df["departure_at"].dt.dayofweek
    df["dep_date"] = df["departure_at"].dt.date
    df["col_date"] = df["collected_at"].dt.date
    return df

@st.cache_data(ttl=300)
def load_routes(df) -> pd.DataFrame:
    grp = (df.groupby(["origin_name","destination_name","route_id"])
           .agg(operators=("operator", lambda x: sorted(x.unique().tolist())),
                record_count=("price_eur","count"), last_collected=("collected_at","max"))
           .reset_index())
    grp["label"] = grp["origin_name"] + " → " + grp["destination_name"]
    return grp.sort_values("record_count", ascending=False)

def filter_route(df, origin, destination):
    return df[(df["origin_name"]==origin) & (df["destination_name"]==destination)].copy()

# ── crawlers ──────────────────────────────────────────────────────────────────
@st.cache_resource
def _import_crawlers():
    defs = [
        ("db","crawlers.db.db_crawler","DBCrawler"),
        ("flixtrain","crawlers.flixtrain.flixtrain_crawler","FlixtrainCrawler"),
        ("trenitalia","crawlers.trenitalia.trenitalia_crawler","TrenitaliaCrawler"),
        ("italo","crawlers.italo.italo_crawler","ItaloCrawler"),
        ("ouigo_es","crawlers.ouigo_es.ougio_es_crawler","OuigoEsCrawler"),
        ("regiojet","crawlers.regiojet.regiojet_crawler","RegioJetCrawler"),
        ("ouigo_fr","crawlers.ouigo_fr.ouigo_fr_crawler","OuigoFrCrawler"),
    ]
    classes, errors = {}, {}
    for op, mod, cls in defs:
        try:
            classes[op] = getattr(importlib.import_module(mod), cls)
        except Exception as e:
            errors[op] = str(e); classes[op] = None
    return classes, errors

def _ts(): return datetime.now().strftime("%H:%M:%S")

def _run_crawlers_thread(log_queue, ops_to_run=None):
    try:
        from config.routes import ROUTES, BOOKING_HORIZONS
    except Exception as e:
        log_queue.append(f"[{_ts()}] ✗ config/routes.py not found: {e}"); return
    crawler_classes, crawler_errors = _import_crawlers()
    active = ops_to_run or [op for op, cls in crawler_classes.items() if cls]
    log_queue.append(f"[{_ts()}] === Run started — {len(active)} crawlers ===")
    for op in active:
        cls = crawler_classes.get(op)
        if cls is None:
            log_queue.append(f"[{_ts()}] ⚠  {op_label(op)} skipped — {crawler_errors.get(op,'no module')}"); continue
        try:
            log_queue.append(f"[{_ts()}] ▶  {op_label(op)} starting...")
            cls().run(ROUTES, BOOKING_HORIZONS)
            log_queue.append(f"[{_ts()}] ✓  {op_label(op)} completed")
        except Exception as e:
            log_queue.append(f"[{_ts()}] ✗  {op_label(op)} error: {e}")
    log_queue.append(f"[{_ts()}] === All crawlers completed ===")

@st.cache_resource
def _start_scheduler():
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except Exception as e:
        return None, str(e)
    s = BackgroundScheduler()
    s.add_job(_run_crawlers_thread, args=[[], None], trigger="cron", hour=3, minute=0,
              id="daily_crawl", replace_existing=True, misfire_grace_time=3600)
    s.start(); return s, None

# ── session state ─────────────────────────────────────────────────────────────
for k, v in [("log",[]),("running",False),("lang_code","en"),("page","main")]:
    if k not in st.session_state: st.session_state[k] = v
if "initialized" not in st.session_state:
    scheduler, sched_err = _start_scheduler()
    st.session_state.sched_ok  = scheduler is not None
    st.session_state.sched_err = sched_err
    if DATA_SOURCE == "db" and scheduler is not None:
        st.session_state.log.append(f"[{_ts()}] Dashboard started — initial crawler run beginning...")
        threading.Thread(target=_run_crawlers_thread, args=(st.session_state.log, None), daemon=True).start()
        st.session_state.running = True
    st.session_state.initialized = True

with st.spinner("Loading data..."):
    df_all    = load_all_data()
    routes_df = load_routes(df_all)
CRAWLER_CLASSES, CRAWLER_IMPORT_ERRORS = _import_crawlers()

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🚄 RailDataHub")

    c1, c2 = st.columns(2)
    if c1.button("🇬🇧 English", use_container_width=True,
                 type="primary" if st.session_state.lang_code=="en" else "secondary"):
        st.session_state.lang_code = "en"; st.rerun()
    if c2.button("🇩🇪 Deutsch", use_container_width=True,
                 type="primary" if st.session_state.lang_code=="de" else "secondary"):
        st.session_state.lang_code = "de"; st.rerun()

    T = TEXTS[st.session_state.lang_code]
    st.caption(T["csv_mode"] if DATA_SOURCE=="csv" else T["db_mode"])

    if DATA_SOURCE == "db":
        if st.session_state.sched_ok: st.success(T["sched_active"])
        else: st.warning(f"⚠️ Scheduler: {st.session_state.sched_err}")
        if st.session_state.running: st.info(T["crawlers_running"])

    st.divider()
    if routes_df.empty: st.error(T["no_data"]); st.stop()

    st.markdown(T["enter_route"])
    all_origins = sorted(df_all["origin_name"].dropna().unique())
    all_dests   = sorted(df_all["destination_name"].dropna().unique())

    ca, cb = st.columns(2)
    orig_in = ca.text_input(T["from_label"], placeholder=T["origin_ph"], key="origin_input")
    dest_in = cb.text_input(T["to_label"],   placeholder=T["dest_ph"],   key="dest_input")

    orig_hits = [o for o in all_origins if orig_in.strip().lower() in o.lower()] if orig_in.strip() else list(all_origins)
    dest_hits = [d for d in all_dests   if dest_in.strip().lower() in d.lower()] if dest_in.strip() else list(all_dests)
    filtered  = routes_df[routes_df["origin_name"].isin(orig_hits) & routes_df["destination_name"].isin(dest_hits)]

    if orig_in.strip() and dest_in.strip() and filtered.empty:
        st.warning(f"{T['route_not_found']} **{orig_in.strip()} → {dest_in.strip()}**")
        filtered = routes_df

    labels = filtered["label"].tolist()

    def route_region(label):
        for city in ["Berlin","Hamburg","München","Frankfurt","Köln","Stuttgart","Leipzig","Hannover",
                     "Karlsruhe","Basel","Bremen","Dortmund","Dresden","Kiel","Düsseldorf","Aachen",
                     "Koblenz","Saarbrücken","Zürich","Graz","Passau","Wiesbaden"]:
            if city in label: return T["region_de"]
        for city in ["Milano","Roma","Napoli","Torino","Venezia","Lecce","Salerno","Taranto",
                     "Bolzano","Brescia","Genova","Trieste","Udine","Ravenna","Reggio"]:
            if city in label: return T["region_it"]
        for city in ["Madrid","Barcelona","Valencia","Sevilla","Zaragoza","Albacete"]:
            if city in label: return T["region_es"]
        for city in ["Paris","Lyon","Marseille","Nantes","Bordeaux","Montpellier","Nice",
                     "Toulouse","Rennes","Strasbourg","Brest"]:
            if city in label: return T["region_fr"]
        for city in ["Wien","Praha","Budapest","Bratislava","Amsterdam","Brussels"]:
            if city in label: return T["region_int"]
        return T["region_other"]

    if "selected_label" not in st.session_state or st.session_state.selected_label not in labels:
        st.session_state.selected_label = labels[0]

    selected_label = st.selectbox(
        T["route_label"], labels,
        index=labels.index(st.session_state.selected_label) if st.session_state.selected_label in labels else 0,
        label_visibility="collapsed", key="route_selector",
    )
    st.session_state.selected_label = selected_label
    st.caption(f"{route_region(selected_label)} · {T['routes_found'](len(labels))}")

    sel         = routes_df[routes_df["label"]==selected_label].iloc[0]
    origin      = sel["origin_name"]
    destination = sel["destination_name"]
    operators   = sel["operators"]

    st.divider()
    st.markdown(T["operators_on_route"])
    for op in operators:
        st.markdown(f'<span style="color:{op_color(op)}">●</span> {op_label(op)}', unsafe_allow_html=True)

    st.divider()
    _nb1, _nb2 = st.columns(2)
    if _nb1.button(T["tab_operator"], use_container_width=True,
                   type="primary" if st.session_state.page == "operator" else "secondary"):
        st.session_state.page = "operator" if st.session_state.page != "operator" else "main"
        st.rerun()
    if _nb2.button(T["tab_crawler"], use_container_width=True,
                   type="primary" if st.session_state.page == "crawler" else "secondary"):
        st.session_state.page = "crawler" if st.session_state.page != "crawler" else "main"
        st.rerun()

    st.divider()
    st.metric(T["data_points"], f'{int(sel["record_count"]):,}'.replace(",","."))
    st.caption(f"{T['last_label']} {time_since(sel['last_collected'], T)}")
    if st.button(T["reload_data"]): st.cache_data.clear(); st.rerun()

df        = filter_route(df_all, origin, destination)
color_map = make_color_map(operators)
_page     = st.session_state.page

if _page == "operator":
    st.subheader(T["op_head"])

    # Route Comparison
    with st.container(border=True):
        st.markdown(T["op_route_head"])
        all_routes = routes_df["label"].tolist()
        sel_rts = st.multiselect(T["op_routes_lbl"], options=all_routes,
                                 default=[st.session_state.get("selected_label", all_routes[0])],
                                 key="route_compare")
        if len(sel_rts) >= 2:
            frames, ffreq, summary = [], [], []
            for rl in sel_rts:
                rr    = routes_df[routes_df["label"]==rl].iloc[0]
                df_r  = filter_route(df_all, rr["origin_name"], rr["destination_name"])
                dfhzr = (df_r.dropna(subset=["booking_horizon_days"])
                         .groupby("booking_horizon_days")
                         .agg(price_avg=("price_eur","mean"), price_min=("price_eur","min")).reset_index())
                dfhzr["route"] = rl
                dfhzr["booking_horizon_days"] = dfhzr["booking_horizon_days"].astype(int)
                frames.append(dfhzr)
                dffq = (df_r.dropna(subset=["booking_horizon_days"])
                        .groupby("booking_horizon_days").agg(count=("price_eur","count")).reset_index())
                dffq["route"] = rl
                dffq["booking_horizon_days"] = dffq["booking_horizon_days"].astype(int)
                ffreq.append(dffq)
                summary.append({"route":rl, "low":float(df_r["price_eur"].min()),
                                 "avg":float(df_r["price_eur"].mean()),
                                 "ops":int(df_r["operator"].nunique()), "pts":len(df_r)})
            cheapest_rt = min(summary, key=lambda x: x["low"])
            for s in summary:
                best = s["route"]==cheapest_rt["route"]
                border = "2px solid #a8e44a" if best else "1px solid #333"
                badge  = T["op_badge"] if best else ""
                st.markdown(
                    f'<div style="border:{border};border-radius:8px;padding:10px 12px;background:#111;margin-bottom:8px;">'
                    f'<div style="font-size:11px;color:#888;margin-bottom:2px;">{s["route"]}{badge}</div>'
                    f'<div style="font-size:20px;font-weight:700;color:#fff;">{s["low"]:.2f} €</div>'
                    f'<div style="font-size:11px;color:#aaa;">{T["op_avg"]} {s["avg"]:.2f} € · {s["ops"]} op. · {s["pts"]:,} {T["op_pts"]}</div>'
                    f'</div>', unsafe_allow_html=True)
            df_rhz = pd.concat(frames, ignore_index=True)
            fig = px.line(df_rhz, x="booking_horizon_days", y="price_avg", color="route", markers=True,
                          title=T["op_hz_t"],
                          labels={"booking_horizon_days":T["ov_days_adv"],"price_avg":T["bh_avg"]})
            fig.update_traces(line_width=2, marker_size=5); fig.update_layout(hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
            df_rmin = (df_rhz.groupby("route").agg(low=("price_min","min")).reset_index().sort_values("low"))
            fig2 = px.bar(df_rmin, x="route", y="low", color="route", title=T["op_low_rt"],
                          labels={"low":T["op_low"]}, text="low")
            fig2.update_traces(texttemplate="%{text:.2f} €", textposition="outside")
            fig2.update_layout(showlegend=False); st.plotly_chart(fig2, use_container_width=True)
            df_frc = pd.concat(ffreq, ignore_index=True)
            fig3 = px.bar(df_frc, x="booking_horizon_days", y="count", color="route", barmode="group",
                          title=T["op_conn"], labels={"booking_horizon_days":T["ov_days_adv"],"count":T["ov_count"]})
            fig3.update_layout(hovermode="x unified"); st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info(T["op_sel2"] if sel_rts else T["op_no_rt"])

    st.divider()

    # Operator Comparison
    with st.container(border=True):
        st.markdown(T["op_comp"].format(orig=origin, dest=destination))
        hz_val = st.select_slider(T["op_hz"], options=[1,2,3,4,5,6,7,10,14,21,30,45,60,90], value=14, key="cp_h")
        df_cp  = (df[df["booking_horizon_days"]==hz_val].groupby("operator")
                  .agg(price_min=("price_eur","min"), price_avg=("price_eur","mean"),
                       price_max=("price_eur","max"), seats_avg=("seats_available","mean"),
                       observations=("price_eur","count")).reset_index().sort_values("price_min"))
        if df_cp.empty:
            st.info(T["op_no_hz"].format(days=hz_val))
        else:
            df_cp["op_label"] = df_cp["operator"].map(op_label)
            min_p  = float(df_cp["price_min"].min())
            max_p  = float(df_cp["price_min"].max())
            savings = (max_p-min_p)/max_p*100 if max_p > 0 else 0
            cheap  = df_cp.iloc[0]; most_e = df_cp.iloc[-1]

            c1,c2,c3,c4 = st.columns(4)
            c1.metric(T["op_cheap"], op_label(cheap["operator"]), f"{float(cheap['price_min']):.2f} €")
            c2.metric(T["op_exp"],   op_label(most_e["operator"]), f"{float(most_e['price_min']):.2f} €")
            c3.metric(T["op_sav"],   f"{savings:.0f}%", help=T["op_sav_help"])
            c4.metric(T["op_hz_m"],  f"+{hz_val}d")

            cl, cr = st.columns(2)
            with cl:
                fig = go.Figure()
                for _, row in df_cp.iterrows():
                    c = op_color(row["operator"])
                    fig.add_trace(go.Bar(name=row["op_label"], x=["Min","Avg","Max"],
                                         y=[float(row["price_min"]),float(row["price_avg"]),float(row["price_max"])],
                                         marker_color=[hex_to_rgba(c,0.8),hex_to_rgba(c,0.533),hex_to_rgba(c,0.267)],
                                         marker_line_color=c, marker_line_width=1))
                fig.update_layout(barmode="group", yaxis_title=T["ov_price"],
                                  title=T["op_mam"].format(days=hz_val), margin=dict(t=40,b=20))
                st.plotly_chart(fig, use_container_width=True)
            with cr:
                df_cp["diff_pct"] = ((df_cp["price_min"].astype(float)-min_p)/min_p*100).round(1)
                fig2 = px.bar(df_cp, x="op_label", y="diff_pct", color="diff_pct",
                              color_continuous_scale=["#a8e44a","#ffb547","#ff5f5f"],
                              title=T["op_extra"].format(op=op_label(cheap["operator"])),
                              labels={"op_label":T["ov_op"],"diff_pct":T["op_pct"]}, text="diff_pct")
                fig2.update_traces(texttemplate="+%{text:.1f}%", textposition="outside")
                fig2.update_coloraxes(showscale=False); fig2.update_layout(margin=dict(t=40,b=20))
                st.plotly_chart(fig2, use_container_width=True)

            if len(df_cp) >= 2:
                st.markdown(T["op_prof"])
                spread  = df_cp["price_max"].astype(float) - df_cp["price_min"].astype(float)
                max_pm  = df_cp["price_min"].astype(float).max()
                min_pm  = df_cp["price_min"].astype(float).min()
                mx_sp   = spread.max(); mx_obs = float(df_cp["observations"].max())
                mx_seats = float(df_cp["seats_avg"].fillna(0).max())
                cats    = T["op_radar_cats"]; fig_r = go.Figure()
                for _, row in df_cp.iterrows():
                    denom = (max_pm-min_pm) if (max_pm-min_pm) > 0 else 1
                    vals  = [1-(float(row["price_min"])-min_pm)/denom,
                             1-(float(row["price_max"])-float(row["price_min"]))/(mx_sp if mx_sp>0 else 1),
                             float(row["seats_avg"] or 0)/(mx_seats if mx_seats>0 else 1),
                             float(row["observations"])/(mx_obs if mx_obs>0 else 1)]
                    fig_r.add_trace(go.Scatterpolar(
                        r=vals+[vals[0]], theta=cats+[cats[0]], fill="toself", name=row["op_label"],
                        line_color=op_color(row["operator"]), fillcolor=hex_to_rgba(op_color(row["operator"]),0.18)))
                fig_r.update_layout(
                    polar=dict(radialaxis=dict(visible=True,range=[0,1],
                               tickvals=[0.25,0.5,0.75,1.0],ticktext=["25%","50%","75%","100%"])),
                    title=T["op_radar_t"].format(days=hz_val),
                    legend=dict(orientation="h",yanchor="bottom",y=-0.25), margin=dict(t=50,b=60))
                st.plotly_chart(fig_r, use_container_width=True)
                st.caption(T["op_radar_c"])

            df_sc = df_cp[df_cp["seats_avg"].notna()].copy()
            if not df_sc.empty:
                fig3 = px.scatter(df_sc, x="price_min", y="seats_avg", color="op_label",
                                  color_discrete_map=color_map, size=[20]*len(df_sc), text="op_label",
                                  title=T["op_scatter"],
                                  labels={"price_min":T["op_low"],"seats_avg":T["op_seats"],"op_label":T["ov_op"]},
                                  custom_data=["observations"])
                fig3.update_traces(textposition="top center",
                                   hovertemplate="<b>%{text}</b><br>%{x:.2f} €<br>%{y:.0f} seats<br>%{customdata[0]} obs.")
                st.plotly_chart(fig3, use_container_width=True)

            df_sh2 = (df.dropna(subset=["seats_available","booking_horizon_days"])
                      .groupby(["operator","booking_horizon_days"]).agg(seats_avg=("seats_available","mean")).reset_index())
            if not df_sh2.empty:
                df_sh2["op_label"] = df_sh2["operator"].map(op_label)
                fig4 = px.line(df_sh2, x="booking_horizon_days", y="seats_avg", color="op_label",
                               color_discrete_map=color_map, markers=True, title=T["op_seats_hz"],
                               labels={"booking_horizon_days":T["ov_days_adv"],"seats_avg":T["op_seats"],"op_label":T["ov_op"]})
                st.plotly_chart(fig4, use_container_width=True)

    st.stop()

if _page == "crawler":
    st.subheader(T["cr_head"])

    df_by_op = (df_all.groupby("operator")
                .agg(records=("price_eur","count"), last_collected=("collected_at","max"),
                     first_collected=("collected_at","min"), routes=("route_id","nunique"),
                     avg_price=("price_eur","mean"))
                .reset_index().sort_values("records", ascending=False))

    # Data Overview
    with st.container(border=True):
        st.markdown(T["cr_data"])
        c1,c2,c3,c4 = st.columns(4)
        c1.metric(T["cr_total"], f'{len(df_all):,}'.replace(",","."))
        c2.metric(T["cr_ops"],   df_all["operator"].nunique())
        c3.metric(T["cr_routes"],df_all["route_id"].nunique())
        c4.metric(T["cr_last"],  time_since(df_all["collected_at"].max(), T))

        cm_all = make_color_map(OPERATOR_COLORS.keys())
        df_by_op["op_label"] = df_by_op["operator"].map(op_label)
        fig = px.bar(df_by_op.sort_values("records"), x="records", y="op_label", orientation="h",
                     color="op_label", color_discrete_map=cm_all, title=T["cr_c1"],
                     labels={"records":T["cr_rec"],"op_label":T["cr_cr"]})
        fig.update_layout(showlegend=False); st.plotly_chart(fig, use_container_width=True)

        df_daily = df_all.groupby(["col_date","operator"]).agg(records=("price_eur","count")).reset_index()
        df_daily["op_label"] = df_daily["operator"].map(op_label)
        fig2 = px.bar(df_daily, x="col_date", y="records", color="op_label",
                      color_discrete_map=cm_all, title=T["cr_c2"],
                      labels={"col_date":T["cr_date"],"records":T["cr_rec"],"op_label":T["cr_cr"]})
        fig2.update_layout(barmode="stack"); st.plotly_chart(fig2, use_container_width=True)

    # Crawler Control
    with st.container(border=True):
        st.markdown(T["cr_ctrl"])
        if DATA_SOURCE == "csv": st.info(T["cr_csv"])
        available = [op for op, cls in CRAWLER_CLASSES.items() if cls]
        if CRAWLER_IMPORT_ERRORS:
            with st.expander(T["cr_err"].format(n=len(CRAWLER_IMPORT_ERRORS))):
                for op, err in CRAWLER_IMPORT_ERRORS.items():
                    st.code(f"{op_label(op)}: {err}", language=None)
        cs, cb = st.columns([3,1])
        with cs:
            to_run = st.multiselect(T["cr_sel"], options=available, default=available,
                                    format_func=op_label, key="manual_ops")
        with cb:
            st.markdown("<br>", unsafe_allow_html=True)
            clicked = st.button(T["cr_start"], disabled=st.session_state.running or not to_run,
                                use_container_width=True)
        if clicked and to_run:
            st.session_state.log = []; st.session_state.running = True
            threading.Thread(target=_run_crawlers_thread, args=(st.session_state.log, to_run), daemon=True).start()
            st.rerun()
        if st.session_state.log:
            st.code("\n".join(st.session_state.log), language=None)
            if "completed" in (st.session_state.log[-1] if st.session_state.log else ""):
                if st.session_state.running:
                    st.session_state.running = False; st.cache_data.clear()
            if st.session_state.running:
                st.button(T["cr_refresh"], on_click=st.rerun)
        ci, cs2 = st.columns([3,1])
        with ci: st.caption(T["cr_auto"])
        with cs2: st.success(T["cr_on"] if st.session_state.sched_ok else T["cr_off"])

    # Status per Crawler
    with st.container(border=True):
        st.markdown(T["cr_status"])
        st.caption(T["cr_stat_cap"])
        for _, row in df_by_op.iterrows():
            c1,c2,c3,c4,c5 = st.columns([2,2,1,1,2])
            with c1:
                st.markdown(f'<span style="color:{op_color(row["operator"])}">●</span> **{op_label(row["operator"])}**',
                            unsafe_allow_html=True)
            c2.metric("", time_since(row["last_collected"], T),          label_visibility="collapsed")
            c3.metric("", f'{int(row["records"]):,}'.replace(",","."),   label_visibility="collapsed")
            c4.metric("", int(row["routes"]),                            label_visibility="collapsed")
            c5.metric("", f"{float(row['avg_price']):.2f} €",           label_visibility="collapsed")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
.stTabs [data-baseweb="tab-list"] { width: 100%; gap: 0; }
.stTabs [data-baseweb="tab"]      { flex: 1; justify-content: center; }
</style>
""", unsafe_allow_html=True)
tab1, tab2, tab3, tab4 = st.tabs([
    T["tab_overview"], T["tab_train"], T["tab_horizon"], T["tab_daytime"],
])

# ── TAB 1: OVERVIEW ───────────────────────────────────────────────────────────
with tab1:
    st.subheader(f"{origin} → {destination}")
    days      = st.slider(T["ov_time_range"], 7, 90, 30, key="ov_days")
    cutoff    = df["collected_at"].max() - pd.Timedelta(days=days)
    df_ts = (df[df["collected_at"]>=cutoff]
             .groupby(["col_date","operator"])
             .agg(price_min=("price_eur","min"), price_avg=("price_eur","mean"), price_max=("price_eur","max"))
             .reset_index().rename(columns={"col_date":"date"}))

    if df_ts.empty:
        st.info(T["ov_no_data"])
    else:
        min_price = float(df["price_eur"].min())
        min_op    = df.loc[df["price_eur"].idxmin(),"operator"]
        avg_price = float(df["price_eur"].mean())
        recent    = df["collected_at"] >= (df["collected_at"].max() - pd.Timedelta(days=7))
        trend     = ((df[recent]["price_eur"].mean()-df[~recent]["price_eur"].mean())
                     / df[~recent]["price_eur"].mean()*100) if not df[~recent].empty else 0

        c1,c2,c3,c4 = st.columns(4)
        c1.metric(T["ov_lowest_price"], f"{min_price:.2f} €", op_label(min_op))
        c2.metric(T["ov_avg_price"], f"{avg_price:.2f} €")
        c3.metric(T["ov_trend"], f"{trend:+.1f}%", delta=f"{trend:+.1f}%", delta_color="inverse")
        c4.metric(T["ov_operators"], len(operators))

        df_ts["op_label"] = df_ts["operator"].map(op_label)
        fig = px.line(df_ts, x="date", y="price_min", color="op_label", color_discrete_map=color_map,
                      title=T["ov_c1"].format(days=days),
                      labels={"date":T["ov_date"],"price_min":T["ov_low_lbl"],"op_label":T["ov_op"]})
        fig.update_traces(line_width=2); fig.update_layout(hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

        df_bp = df[df["price_eur"].notna()].copy()
        df_bp["op_label"] = df_bp["operator"].map(op_label)
        fig2 = px.box(df_bp, x="op_label", y="price_eur", color="op_label",
                      color_discrete_map=color_map, points="outliers",
                      title=T["ov_c2"],
                      labels={"op_label": T["ov_op"], "price_eur": T["ov_price"]})
        fig2.update_layout(showlegend=False, yaxis_title=T["ov_price"])
        st.plotly_chart(fig2, use_container_width=True)

        df_freq = df.groupby(["dep_hour","operator"]).agg(count=("price_eur","count")).reset_index()
        df_freq["op_label"]   = df_freq["operator"].map(op_label)
        df_freq["hour_label"] = df_freq["dep_hour"].astype(str).str.zfill(2) + ":00"
        fig3 = px.bar(df_freq, x="hour_label", y="count", color="op_label", color_discrete_map=color_map,
                      barmode="group", title=T["ov_c3"],
                      labels={"hour_label":T["ov_dep_hour"],"count":T["ov_count"],"op_label":T["ov_op"]})
        fig3.update_layout(hovermode="x unified"); st.plotly_chart(fig3, use_container_width=True)

        df_fhz = (df.dropna(subset=["booking_horizon_days"])
                  .groupby(["booking_horizon_days","operator"]).agg(count=("price_eur","count")).reset_index())
        df_fhz["op_label"]             = df_fhz["operator"].map(op_label)
        df_fhz["booking_horizon_days"] = df_fhz["booking_horizon_days"].astype(int)
        fig4 = px.bar(df_fhz, x="booking_horizon_days", y="count", color="op_label",
                      color_discrete_map=color_map, barmode="group", title=T["ov_c4"],
                      labels={"booking_horizon_days":T["ov_days_adv"],"count":T["ov_count"],"op_label":T["ov_op"]})
        st.plotly_chart(fig4, use_container_width=True)

        df_fare = df[df["fare_class"].notna() & (df["fare_class"]!="")]
        if not df_fare.empty:
            st.subheader(T["ov_fare_classes"])
            df_fg = (df_fare.groupby(["operator","fare_class"])
                     .agg(avg_price=("price_eur","mean"), count=("price_eur","count")).reset_index())
            df_fg["op_label"] = df_fg["operator"].map(op_label)
            fig5 = px.bar(df_fg, x="fare_class", y="avg_price", color="op_label",
                          color_discrete_map=color_map, barmode="group", title=T["ov_c5"],
                          labels={"fare_class":T["ov_class"],"avg_price":T["ov_avg"],"op_label":T["ov_op"]})
            st.plotly_chart(fig5, use_container_width=True)

# ── TAB 2: INDIVIDUAL TRAIN ───────────────────────────────────────────────────
with tab2:
    st.subheader(T["tr_head"].format(orig=origin, dest=destination))
    df_wt = df[df["train_number"].notna() & (df["train_number"]!="")].copy()
    if df_wt.empty:
        st.info(T["tr_no_data"])
    else:
        sel_op = st.selectbox(T["tr_op"], operators, format_func=op_label, key="train_op")
        df_op  = df_wt[df_wt["operator"]==sel_op]
        df_trains = (df_op.sort_values("collected_at", ascending=False)
                     .groupby("train_number")
                     .agg(price_now=("price_eur","first"), price_min=("price_eur","min"),
                          price_max=("price_eur","max"), dep_time=("departure_at","first"),
                          fare_class=("fare_class","first"), seats_now=("seats_available","first"),
                          collected_at=("collected_at","first"))
                     .reset_index().sort_values("dep_time"))
        cut7 = df_op["collected_at"].max() - pd.Timedelta(days=8)
        df_w  = (df_op[df_op["collected_at"]<=cut7].sort_values("collected_at",ascending=False)
                 .groupby("train_number")["price_eur"].first().rename("price_7d_ago"))
        df_trains = df_trains.merge(df_w, on="train_number", how="left")
        df_trains["change_7d"] = ((df_trains["price_now"]-df_trains["price_7d_ago"])
                                  / df_trains["price_7d_ago"]*100).round(1)

        def train_fmt(t):
            r   = df_trains[df_trains["train_number"]==t].iloc[0]
            dep = pd.to_datetime(r["dep_time"]).strftime("%H:%M")
            chg = f"  {r['change_7d']:+.1f}%" if not pd.isna(r.get("change_7d",float("nan"))) else ""
            fare = f"  [{r['fare_class']}]" if pd.notna(r["fare_class"]) and r["fare_class"] else ""
            return f"{t}{fare}  —  {dep}  |  {float(r['price_now']):.2f} €{chg}"

        sel_tr  = st.selectbox(T["tr_sel"], df_trains["train_number"].tolist(), format_func=train_fmt, key="train_name")
        row     = df_trains[df_trains["train_number"]==sel_tr].iloc[0]
        dep_str = pd.to_datetime(row["dep_time"]).strftime("%H:%M")

        m1,m2,m3,m4 = st.columns(4)
        m1.metric(T["tr_cur"], f"{float(row['price_now']):.2f} €", help=T["tr_fare"].format(fare=row["fare_class"] or "—"))
        m2.metric(T["tr_lohi"], f"{float(row['price_min']):.2f} € / {float(row['price_max']):.2f} €")
        chg = row.get("change_7d", float("nan"))
        m3.metric(T["tr_7d"], f"{float(chg):+.1f}%" if not pd.isna(chg) else "—",
                  delta=f"{float(chg):+.1f}%" if not pd.isna(chg) else None, delta_color="inverse")
        seats = row.get("seats_now")
        m4.metric(T["tr_seats"], str(int(seats)) if not pd.isna(seats) else "—")
        st.divider()

        df_hist = (df_op[df_op["train_number"]==sel_tr]
                   .groupby("col_date").agg(price_min=("price_eur","min"), price_avg=("price_eur","mean"))
                   .reset_index().sort_values("col_date"))
        if not df_hist.empty:
            avg_l = float(df_hist["price_avg"].mean())
            fig   = px.line(df_hist, x="col_date", y="price_min",
                            title=T["tr_dev"].format(train=sel_tr, dep=dep_str),
                            labels={"col_date":T["ov_date"],"price_min":T["ov_low_lbl"]},
                            color_discrete_sequence=[op_color(sel_op)])
            fig.add_hline(y=avg_l, line_dash="dot", line_color="#888", annotation_text=f"Avg. {avg_l:.2f} €")
            fig.update_traces(line_width=2, fill="tozeroy", fillcolor=hex_to_rgba(op_color(sel_op),0.125))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(T["tr_no_hist"])

        df_hz = (df_op[df_op["train_number"]==sel_tr].dropna(subset=["booking_horizon_days"])
                 .groupby("booking_horizon_days")
                 .agg(price_avg=("price_eur","mean"), price_min=("price_eur","min"), observations=("price_eur","count"))
                 .reset_index().sort_values("booking_horizon_days"))
        if not df_hz.empty:
            tp = float(df_hz["price_avg"].min())
            th = int(df_hz.loc[df_hz["price_avg"].idxmin(),"booking_horizon_days"])
            df_hz["surcharge_pct"] = ((df_hz["price_avg"].astype(float)-tp)/tp*100).round(1)
            df_hz["label"] = "+"+df_hz["booking_horizon_days"].astype(str)+"d"

            fig2 = px.bar(df_hz, x="label", y="surcharge_pct", color="surcharge_pct",
                          color_continuous_scale=["#a8e44a","#ffb547","#ff5f5f"],
                          range_color=[0, df_hz["surcharge_pct"].max()],
                          title=T["tr_sur_title"].format(train=sel_tr, price=tp, horizon=th),
                          labels={"label":T["tr_hz_lbl"],"surcharge_pct":T["tr_sur_lbl"]},
                          custom_data=["price_avg","observations","price_min"])
            fig2.update_traces(hovertemplate="<b>%{x}</b><br>+%{y:.1f}%<br>Avg. %{customdata[0]:.2f} €"
                                             "<br>Min %{customdata[2]:.2f} €<br>%{customdata[1]} obs.")
            fig2.update_coloraxes(showscale=False); st.plotly_chart(fig2, use_container_width=True)

            fig3 = px.line(df_hz, x="label", y="price_avg", markers=True,
                           title=T["tr_abs"].format(train=sel_tr),
                           labels={"label":T["tr_hz_lbl"],"price_avg":T["ov_avg"]},
                           color_discrete_sequence=[op_color(sel_op)],
                           custom_data=["surcharge_pct","observations"])
            fig3.update_traces(line_width=2, marker_size=7,
                               fill="tozeroy", fillcolor=hex_to_rgba(op_color(sel_op),0.083),
                               hovertemplate="<b>%{x}</b><br>Avg. %{y:.2f} €<br>+%{customdata[0]:.1f}%<br>%{customdata[1]} obs.")
            fig3.add_hline(y=tp, line_dash="dot", line_color="#3B6D11",
                           annotation_text=T["tr_low_line"].format(price=tp))
            st.plotly_chart(fig3, use_container_width=True)

            best  = df_hz.loc[df_hz["price_avg"].idxmin()]
            worst = df_hz.loc[df_hz["price_avg"].idxmax()]
            st.success(T["tr_rec"].format(days=int(best["booking_horizon_days"]), price=float(best["price_avg"]),
                                          obs=int(best["observations"]), worst=int(worst["booking_horizon_days"]),
                                          pct=float(worst["surcharge_pct"])))
        else:
            st.info(T["tr_no_hz"])

# ── TAB 3: BOOKING HORIZON ────────────────────────────────────────────────────
with tab3:
    st.subheader(T["bh_head"].format(orig=origin, dest=destination))
    df_h = (df.dropna(subset=["booking_horizon_days"])
            .groupby(["operator","booking_horizon_days"])
            .agg(price_avg=("price_eur","mean"), price_min=("price_eur","min"), observations=("price_eur","count"))
            .reset_index().sort_values(["operator","booking_horizon_days"]))
    if df_h.empty:
        st.info(T["bh_no"])
    else:
        df_h["op_label"]             = df_h["operator"].map(op_label)
        df_h["booking_horizon_days"] = df_h["booking_horizon_days"].astype(int)

        fig = px.line(df_h, x="booking_horizon_days", y="price_avg", color="op_label",
                      color_discrete_map=color_map, markers=True, title=T["bh_c1"],
                      labels={"booking_horizon_days":T["ov_days_adv"],"price_avg":T["bh_avg"],"op_label":T["ov_op"]},
                      custom_data=["observations","price_min"])
        fig.update_traces(line_width=2, marker_size=7,
                          hovertemplate="<b>%{fullData.name}</b><br>+%{x} days<br>Avg. %{y:.2f} €"
                                        "<br>Min %{customdata[1]:.2f} €<br>%{customdata[0]} obs.")
        fig.update_layout(hovermode="x unified"); st.plotly_chart(fig, use_container_width=True)

        fig2 = px.bar(df_h, x="booking_horizon_days", y="observations", color="op_label",
                      color_discrete_map=color_map, barmode="group", title=T["bh_c2"],
                      labels={"booking_horizon_days":T["ov_days_adv"],"observations":T["bh_conn"],"op_label":T["ov_op"]})
        fig2.update_layout(hovermode="x unified"); st.plotly_chart(fig2, use_container_width=True)

        st.subheader(T["bh_table"])
        pivot = df_h.pivot_table(index="operator", columns="booking_horizon_days", values="price_avg").round(2)
        pivot.index   = pivot.index.map(op_label)
        pivot.columns = [f"+{int(c)}d" for c in pivot.columns]
        st.dataframe(pivot, use_container_width=True)

        st.subheader(T["bh_opt"])
        cols = st.columns(max(1, len(df_h["operator"].unique())))
        for i, op in enumerate(sorted(df_h["operator"].unique())):
            dfo   = df_h[df_h["operator"]==op]
            best  = dfo.loc[dfo["price_avg"].idxmin()]
            worst = dfo.loc[dfo["price_avg"].idxmax()]
            saving = (float(worst["price_avg"])-float(best["price_avg"]))/float(worst["price_avg"])*100
            with cols[i]:
                st.markdown(f"**{op_label(op)}**")
                st.metric(T["bh_cheap"], f"+{int(best['booking_horizon_days'])} {T['days_unit']}",
                          T["bh_saves"].format(pct=saving), delta_color="off")
                st.caption(T["bh_cap"].format(price=float(best["price_avg"]), obs=int(best["observations"])))

# ── TAB 4: TIME OF DAY ────────────────────────────────────────────────────────
with tab4:
    st.subheader(T["dt_head"].format(orig=origin, dest=destination))
    sel_op = st.selectbox(T["dt_op"], operators, format_func=op_label, key="dt_op")
    df_dt  = df[df["operator"]==sel_op].copy()
    if df_dt.empty:
        st.info(T["dt_no"])
    else:
        DOW = T["dow"]
        df_hour = (df_dt.groupby("dep_hour")["price_eur"].mean().reset_index()
                   .rename(columns={"price_eur":"price_avg","dep_hour":"hour"}))
        df_hour["hour_label"] = df_hour["hour"].astype(str).str.zfill(2)+":00"
        fig = px.bar(df_hour, x="hour_label", y="price_avg", color="price_avg",
                     color_continuous_scale=["#a8e44a","#ffb547","#ff5f5f"],
                     title=T["dt_c1"].format(op=op_label(sel_op)),
                     labels={"hour_label":T["ov_dep_hour"],"price_avg":T["ov_avg"]})
        fig.update_coloraxes(showscale=False); st.plotly_chart(fig, use_container_width=True)

        df_dt["dow_label"]  = df_dt["dep_dow"].map(DOW)
        df_dt["hour_label"] = df_dt["dep_hour"].astype(str).str.zfill(2)+":00"
        ph = df_dt.pivot_table(index="dow_label", columns="hour_label", values="price_eur", aggfunc="mean").round(2)
        ph = ph.reindex([d for d in DOW.values() if d in ph.index])
        if not ph.empty:
            fig2 = px.imshow(ph, color_continuous_scale=["#1a3a1a","#a8e44a","#ffb547","#ff5f5f"],
                             labels={"x":T["ov_dep_hour"],"y":T["dt_wd"],"color":T["ov_avg"]},
                             title=T["dt_c2"].format(op=op_label(sel_op)), aspect="auto")
            fig2.update_xaxes(tickangle=45); st.plotly_chart(fig2, use_container_width=True)

        df_sh = (df_dt.dropna(subset=["seats_available"]).groupby("dep_hour")["seats_available"]
                 .mean().reset_index().rename(columns={"seats_available":"seats_avg","dep_hour":"hour"}))
        if not df_sh.empty:
            df_sh["hour_label"] = df_sh["hour"].astype(str).str.zfill(2)+":00"
            fig3 = px.line(df_sh, x="hour_label", y="seats_avg", markers=True,
                           title=T["dt_c3"].format(op=op_label(sel_op)),
                           labels={"hour_label":T["ov_dep_hour"],"seats_avg":T["dt_seats"]},
                           color_discrete_sequence=[op_color(sel_op)])
            fig3.update_traces(line_width=2); st.plotly_chart(fig3, use_container_width=True)

        if not df_hour.empty:
            minh = df_hour.loc[df_hour["price_avg"].idxmin()]
            maxh = df_hour.loc[df_hour["price_avg"].idxmax()]
            df_dow = df_dt.groupby("dow_label")["price_eur"].mean()
            c1,c2,c3,c4 = st.columns(4)
            c1.metric(T["dt_ch_h"], minh["hour_label"], f"Avg. {float(minh['price_avg']):.2f} €")
            c2.metric(T["dt_ex_h"], maxh["hour_label"], f"Avg. {float(maxh['price_avg']):.2f} €")
            if not df_dow.empty:
                c3.metric(T["dt_ch_d"], df_dow.idxmin(), f"Avg. {float(df_dow.min()):.2f} €")
                c4.metric(T["dt_ex_d"], df_dow.idxmax(), f"Avg. {float(df_dow.max()):.2f} €")
