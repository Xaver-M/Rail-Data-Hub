# dashboard/config.py
import pandas as pd
from datetime import datetime
import streamlit as st


OPERATOR_COLORS = {
    "db": "#4a9eff", "flixtrain": "#a8e44a", "regiojet": "#ff7c5c",
    "trenitalia": "#ffb547", "italo": "#ff4f4f", "ouigo_es": "#b47fff", "ouigo_fr": "#ff6eb4",
    "flixbus": "#18a04b", "ceske-drahy": "#003f87", "db_parsebot": "#f01414",
}

# Anbieter mit verlässlichen seats_available-Daten (geprüft im Snapshot: DB, DB-Parsebot,
# ČD liefern nie Sitzplatzdaten; Ouigo ES/FR nur für <5% der Zeilen, wirkt wie ein reines
# "fast ausverkauft"-Signal statt einer echten Sitzplatzzahl — daher hier bewusst ausgeschlossen).
SEATS_OPERATORS = {"italo", "flixtrain", "flixbus", "regiojet", "trenitalia"}

# Anbieter, für die DB-Bahncard-Preisvarianten (BC50/BC25) berechnet werden.
DB_BAHNCARD_OPERATORS = ("db", "db_parsebot")

OPERATOR_LABELS = {
    "db": "DB", "flixtrain": "Flixtrain", "regiojet": "RegioJet",
    "trenitalia": "Trenitalia", "italo": "Italo", "ouigo_es": "Ouigo ES", "ouigo_fr": "Ouigo FR",
    "flixbus": "Flixbus", "ceske-drahy": "České dráhy", "db_parsebot": "DB (ParseBot)",
}

# Zentrales Custom-CSS für den 1+ Premium Look (Schatten, Karten, abgerundete Ecken)
CUSTOM_CSS = """
<style>
    /* Premium KPI Karten */
    .kpi-card {
        background-color: var(--secondary-background-color);
        border: 1px solid rgba(128,128,128,0.18);
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.15);
        margin-bottom: 15px;
    }
    .kpi-title {
        font-size: 13px;
        color: var(--text-color);
        opacity: 0.55;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 5px;
    }
    .kpi-value {
        font-size: 28px;
        font-weight: 700;
        color: var(--text-color);
    }
    .kpi-subtitle {
        font-size: 12px;
        color: var(--text-color);
        opacity: 0.6;
        margin-top: 5px;
    }
    .kpi-badge {
        display: inline-block;
        font-size: 11px;
        font-weight: 600;
        margin-top: 6px;
        padding: 2px 8px;
        border-radius: 4px;
        border: 1px solid;
        background: transparent;
    }
</style>
"""

# Übersetzungen (Eure originalen EN/DE Dictionaries gekürzt zur Übersicht)
EN = {
"csv_mode": "📁 CSV Mode", "db_mode": "🗄️ DB Mode",
    "crawlers_running": "🔄 Crawlers running...", "no_data": "No data found.",
    "enter_route": "**Enter route**", "from_label": "From", "origin_ph": "Origin...",
    "to_label": "To", "dest_ph": "Destination...", "route_not_found": "Route not found:",
    "swap_route": "Swap origin ↔ destination",
    "swap_unavailable": "⚠️ No data for the reversed route.",
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
    "tab_normalized": "📐 €/km & €/h",
    "dow": {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"},
    "ov_time_range": "Time range (days back)", "ov_no_data": "No data in the selected time range.",
    "ov_lowest_price": "Lowest price", "ov_avg_price": "Avg. price",
    "ov_max_price": "Highest price",
    "ov_trend": "Price trend", "ov_trend_sub": "Avg. last 7 crawl days vs. earlier",
    "ov_operators": "Operators",
    "ov_date": "Date", "ov_low_lbl": "Lowest price (€)", "ov_op": "Operator",
    "ov_price": "Price (€)", "ov_dep_hour": "Departure hour", "ov_count": "Count",
    "ov_days_adv": "Days in advance", "ov_fare_classes": "Fare classes",
    "ov_class": "Class", "ov_avg": "Avg. price (€)",
    "ov_c1": "Avg. price per crawl date — last {days} days",
    "ov_c1_note": "📌 Each point = avg. of all fares crawled on that date. Shows how the average price evolves over the observation window.",
    "ov_c2": "Price range Min / Avg / Max per operator (diamond = average)",
    "ov_c3": "Total recorded fare observations per departure hour and operator",
    "ov_c4": "Number of recorded connections per booking horizon",
    "ov_c5": "Avg. price per fare class and operator",
    "ov_mode": "View",
    "ov_mode_route": "📍 Whole route",
    "ov_mode_trip": "🚆 Single trip",
    "ov_show_reverse": "⇄ Also show return direction",
    "ov_dir_outbound": "Outbound",
    "ov_dir_return": "Return",
    "ov_no_reverse_data": "No data available for the return direction.",
    "ov_dep_date": "Departure date",
    "ov_train_filter": "Train",
    "ov_all_trains": "All trains (aggregated)",
    "ov_all_trains_note": "💡 Aggregated view across all trains. For individual train analysis see the Individual Train tab.",
    "ov_eur_km": "€ / km (avg.)", "ov_eur_h": "€ / h (avg.)",
    "ov_km_sub": "{km:.0f} km (Haversine)", "ov_h_sub": "Avg. travel: {h:.1f} h",
    "ov_no_dist": "No distance data", "ov_no_time": "No travel time data",
    "ov_no_trip_data": "No data for this departure date.",
    "ov_nearest": "Nearest dates with data:",
    "ov_trip_dev": "Price development by booking horizon — departure {date}",
    "ov_trend_trip": "Recent change (7d)",
    "ov_trend_trip_help": "Avg. of the last 7 crawl days vs. earlier crawls for this departure.",
    "ov_data_maturity": "📊 Recorded booking horizons: +{hmax} to +{hmin} · {covered}/90 horizons · {obs} observations",
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
    "bh_head": "Booking Horizon — {orig} → {dest}", "bh_no": "No horizon data.",
    "bh_c1": "Avg. price per operator by booking horizon",
    "bh_c1_dyn": "{basis} price per operator by booking horizon",
    "bh_avg": "Avg. price (€)",
    "bh_c2": "Number of recorded connections per booking horizon",
    "bh_conn": "Number of connections",
    "bh_table": "Detail table — Avg. price per operator and horizon",
    "bh_opt": "Optimal booking time per operator",
    "bh_cheap": "Cheapest at", "bh_saves": "saves {pct:.0f}%",
    "bh_cap": "Avg. {price:.2f} € ({obs} obs.)",
    "bh_bc_normal": "Standard fare",
    "bh_bc50": "🎫 BahnCard 50",
    "bh_bc25": "🎫 BahnCard 25",
    "bh_bc_note": "BahnCard 50 = 50% off, BahnCard 25 = 25% off — applied to DB and DB (ParseBot) standard fares.",
    "bh_bc_none": "Select at least one fare type to display.",
    "dt_head": "Time of Day Analysis — {orig} → {dest}",
    "dt_op": "Operator", "dt_no": "No data for this operator.",
    "dt_c1": "Avg. price by departure hour — {op}",
    "dt_c2": "Heatmap — Avg. price per weekday and hour ({op})",
    "dt_c1_dyn": "{basis} price by departure hour — {op}",
    "dt_c2_dyn": "{basis} price heatmap by weekday and hour ({op})",
    "dt_wd": "Weekday", "dt_c3": "Avg. available seats by departure hour — {op}",
    "dt_seats": "Avg. seats",
    "dt_ch_h": "Cheapest hour", "dt_ex_h": "Most expensive hour",
    "dt_ch_d": "Cheapest day", "dt_ex_d": "Most expensive day",
    "op_head": "Operator Comparison & Route Comparison",
    "op_comp": "#### ⚖️ Operator Comparison — {orig} → {dest}",
    "op_hz": "Booking horizon",
    "op_no_hz": "No data for booking horizon +{days} days.",
    "op_cheap": "Cheapest", "op_exp": "Most expensive",
    "op_sav": "Max. savings", "op_sav_help": "By choosing the cheapest operator",
    "op_hz_m": "Horizon", "op_mam": "Min / Avg / Max at +{days}d",
    "op_extra": "Extra cost vs. {op}", "op_pct": "% more expensive",
    "op_prof": "**Operator Profile**",
    "op_prof": "**Operator Profile**",
    "op_tbl_min": "Min Price", "op_tbl_avg": "Avg Price", "op_tbl_max": "Max Price",
    "op_tbl_spread": "Price Spread", "op_tbl_seats": "Avg. Seat Capacity", "op_tbl_obs": "Observations",
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
    "cr_head": "Crawler Status & Control",
    "cr_ctrl": "#### 🤖 Crawler Control",
    "cr_err": "⚠️ {n} import errors",
    "cr_sel": "Select crawlers", "cr_start": "▶ Start now",
    "cr_on": "✅ Active", "cr_off": "⚠️ Inactive",
    "cr_status": "#### 📋 Status per Crawler",
    "cr_stat_cap": "Crawler · Last collected · Records · Routes · Avg. price",
    "cr_refresh": "🔄 Refresh log",
    "cr_data": "#### 📊 Data Overview",
    "cr_total": "Total records", "cr_ops": "Crawlers",
    "cr_routes": "Routes", "cr_last": "Last collected",
    "cr_c1": "Total records per crawler",
    "cr_rec": "Records", "cr_cr": "Crawler",
    "cr_c2": "Records per day per crawler", "cr_date": "Date",
    "cr_tbl_op": "Operator", "cr_tbl_last": "Last run",
    "cr_tbl_rec": "Records", "cr_tbl_rt": "Routes", "cr_tbl_price": "Avg. price",
    "nm_head": "Normalized Prices — {orig} → {dest}",
    "nm_no_dist": "⚠️ No distance data available for this route.",
    "nm_no_time": "⚠️ No travel time data (arrival_at missing) for this route.",
    "nm_dist": "Route distance (Haversine)",
    "nm_km": "km",
    "nm_eur_km": "€ / km",
    "nm_eur_h": "€ / h",
    "nm_hz": "Booking horizon (days in advance)",
    "nm_c1": "Min. price per km by booking horizon",
    "nm_c2": "Min. price per hour of travel by booking horizon",
    "nm_c3": "€/km vs. €/h — Operator comparison at +{days} days",
    "nm_c4": "Distribution: price per km across all horizons",
    "nm_note": "ℹ️ Distances are Haversine (straight-line). Actual rail distances are typically 15–25% longer.",
    "nm_hz_sel": "Booking horizon for scatter",
    "nm_op": "Operator",
    "nm_travel_h": "Avg. travel time (h)",
    "nm_obs": "Observations",
    "nm_summary": "This route: **{eurkm:.3f} €/km** · **{eurh:.2f} €/h** (basis: {basis}, +{days}d)",
    "nm_basis_note": "Charts below use the selected price basis. €/h uses total journey time (incl. transfers).",
    "price_basis": "Price basis",
    "price_min": "Minimum",
    "price_avg": "Average",
    "price_basis_help": "Minimum = cheapest fare per group (robust yield-management basis). Average = mean of all fares (sensitive to which trains were captured).",
    "direct_filter": "Connection type",
    "direct_all": "All",
    "direct_only": "Direct only",
    "direct_transfer": "With transfer",
    "ov_dep_hour_note": "ℹ️ Note: some operators (esp. DB) only cover a limited daytime window — see Time of Day tab.",
    "ov_fare_note": "ℹ️ Fare classes are not directly comparable across operators; price_eur (cheapest available fare) is the reliable field.",
    "dt_coverage_warn": "⚠️ Limited daytime coverage: only {n} distinct hours recorded for {op}. Interpret with caution — this reflects the crawler's fixed query window, not the real timetable.",
    "dt_seats_none": "No seat-availability data for this operator.",
    "tr_heterogen": "⚠️ {n} distinct train identifiers for {op} — train numbers are heterogeneous (transfer combinations). Single-train analysis is most reliable for Trenitalia/Italo.",
    "cr_health": "#### 🚦 7-day health",
    "cr_health_cap": "Days with data in the last 7 · avg. records/day",
    "cr_health_ok": "✅", "cr_health_warn": "⚠️", "cr_health_bad": "❌",
    "cr_avg_day": "Ø/day",
        "lp_eyebrow":        "KIT · Institute of Economics · SS 2026",
    "lp_subtitle":       "Systematic collection and analysis of ticket prices from European rail operators — empirical foundation for studying yield management strategies in passenger rail.",
    "lp_kpi_obs":        "Observations",
    "lp_kpi_ops":        "Operators",
    "lp_kpi_routes":     "Routes",
    "lp_kpi_horizons":   "Horizons",
    "lp_sec_operators":  "Covered Operators",
    "lp_sec_collection": "Data Collection",
    "lp_sec_modules":    "Analysis Modules",
    "lp_sec_method":     "Methodology & Notes",
    "lp_observations":   "Observations",
    "lp_th_operator":    "Operator",
    "lp_obs_short":      "obs.",
    "lp_kit_full":       "Karlsruhe Institute of Technology",
    "lp_hz_label":       "Booking horizons in days before departure",
    "lp_steps_titles":   ["Scheduler", "14 Horizons", "TimescaleDB", "This Portal"],
    "lp_steps_descs":    [
        "Every day at 10:00 UTC the automated crawler process starts for all active operators simultaneously.",
        "Per route, prices are queried for 14 fixed booking points between 1 and 90 days before departure.",
        "All observations are deduplicated and stored in a time-series database on the project VM.",
        "The dashboard reads directly from the database and enables real-time analysis and comparison.",
    ],
    "lp_mod_names":      ["Overview", "Individual Train", "Booking Horizon", "Time of Day", "Operator Comparison", "€/km & €/h", "Crawler Status"],
    "lp_mod_questions":  [
        "How have prices on this route developed over time?",
        "How does the price of a specific train change over time?",
        "When is the optimal time to book?",
        "Are early or late departures systematically more expensive?",
        "Which operator offers the best price on this route?",
        "Which operator offers the best price per kilometre?",
        "How reliably are the data collectors running?",
    ],
    "lp_mod_details":    [
        "MIN · AVG · MAX per operator, selectable time range",
        "Price history from 90 days out to just before departure",
        "Price curves for all 14 booking horizons compared",
        "Price by departure hour and day of week",
        "Direct comparison of all operators at a selectable horizon",
        "Normalised prices for route-neutral comparison",
        "7-day availability, last runs, record counts",
    ],
    "lp_method_left":    (
        "<b>Price basis</b><br>"
        "All analyses use the cheapest available fare (<code>MIN(price_eur)</code>) per route, "
        "horizon and collection day. Standardised to: 1 adult, 2nd class / economy fare, "
        "single journey, no railcards or extras.<br><br>"
        "<b>Fare classes</b><br>"
        "The <code>fare_class</code> column is operator-specific and not directly comparable. "
        "For cross-operator comparisons only <code>price_eur</code> is used."
    ),
    "lp_method_right":   (
        "<b>Known limitations</b><br>"
        "The DB API has been blocking datacenter IPs since 18.05.2026 (HTTP 403/500); "
        "DB prices are additionally sourced via <code>db_parsebot</code>. "
        "The DB crawler only captures connections in the morning window "
        "(approx. 08:00–13:15 departure time).<br><br>"
        "<b>Time zones</b><br>"
        "All timestamps are stored in UTC. Exception: "
        "Trenitalia stores departure times in local time (<code>Europe/Rome</code>)."
    ),
    "lp_footer_sub":     "Institute of Economics · Team Project SS 2026",
    "lp_footer_last":    "Last crawl run",
     "lp_sec_findings":       "Key Results",
    "lp_finding_early":      "Early Booking Effect",
    "lp_finding_cheap":      "Biggest Price Range",
    "lp_finding_route":      "Most Observed Route",
    "lp_sec_growth":         "Data Growth & Coverage",
    "lp_growth_caption":     "Cumulative database build-up — last 120 days",
    "lp_density_caption":    "Data density per operator × booking horizon",
    "lp_density_good":       "good",
    "lp_density_partial":    "partial",
    "lp_density_sparse":     "sparse",
    "lp_kpi_period":         "Collection Period",
    "lp_finding_more_exp":   "more expensive",
    "lp_finding_cheaper":    "cheaper",
    "lp_finding_early_text": "Tickets with ≤7 days lead time cost on average <b>{pct:.1f}%</b> {dir} than with ≥60 days — aggregated across all operators and routes.",
    "lp_finding_cheap_text": "<b>{route}</b> shows the widest price swing: from {low:.2f}&nbsp;€ up to {high:.2f}&nbsp;€.",
    "lp_finding_route_text": "<b>{route}</b> is the route with the most price observations in the dataset.",
    "lp_footer_tech":        "Data: TimescaleDB · bwCloud VM · Ubuntu 24",
    "lp_footer_github":      "↗ GitHub · Xaver-M/Rail-Data-Hub",
    "lp_footer_kit":         "↗ KIT",
    "lp_footer_inst":        "↗ Institute of Economics",
    "price_max_label": "Maximum",
    "ov_max_price":    "Highest price",
    "sidebar_offline":       "⚠ Offline · local snapshot",
    "sidebar_eye":           "KIT · Institute of Economics",
    "sidebar_sub":           "Price monitoring in<br>passenger rail",
    "sidebar_nav":           "Navigation",
    "sidebar_obs":           "Observations",
    "sidebar_last":          "Last",
    "nav_start":             "Start",
    "nav_analyse":           "Analyse",
    "nav_compare":           "Operator Comparison",
    "nav_crawler":           "Crawler Status",
    "picker_route":          "Route",
    "picker_country":        "🌍 Country",
    "picker_all_countries":  "All countries",
    "picker_operators":      "🚄 Operator",
    "picker_all_operators":  "All operators",
    "picker_reset":          "✕ Reset",
    "picker_of":             "of",
    "picker_routes":         "routes",
    "picker_active_ops":     "Displayed Operators",
    "picker_all_active_ops": "All operators",
    "country_names": {
    "DE": "🇩🇪 Germany", "IT": "🇮🇹 Italy", "FR": "🇫🇷 France",
    "ES": "🇪🇸 Spain",   "CZ": "🇨🇿 Czechia", "AT": "🇦🇹 Austria",
    "SK": "🇸🇰 Slovakia", "HU": "🇭🇺 Hungary", "OTHER": "🌍 Other",
    }
}

DE = {
        "csv_mode": "📁 CSV-Modus", "db_mode": "🗄️ DB-Modus",
    "crawlers_running": "🔄 Crawler laufen...", "no_data": "Keine Daten gefunden.",
    "enter_route": "**Route eingeben**", "from_label": "Von", "origin_ph": "Herkunft...",
    "to_label": "Nach", "dest_ph": "Ziel...", "route_not_found": "Route nicht gefunden:",
    "swap_route": "Start ↔ Ziel tauschen",
    "swap_unavailable": "⚠️ Keine Daten für die umgekehrte Strecke.",
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
    "tab_normalized": "📐 €/km & €/h",
    "dow": {0: "Mo", 1: "Di", 2: "Mi", 3: "Do", 4: "Fr", 5: "Sa", 6: "So"},
    "days_unit": "Tage",
    "ov_time_range": "Zeitraum (Tage zurück)", "ov_no_data": "Keine Daten im gewählten Zeitraum.",
    "ov_lowest_price": "Niedrigster Preis", "ov_avg_price": "Durchschnittspreis",
    "ov_max_price": "Höchster Preis",
    "ov_trend": "Preisentwicklung", "ov_trend_sub": "Ø letzte 7 Crawl-Tage vs. früher",
    "ov_operators": "Anbieter",
    "ov_date": "Datum", "ov_low_lbl": "Niedrigster Preis (€)", "ov_op": "Anbieter",
    "ov_price": "Preis (€)", "ov_dep_hour": "Abfahrtsstunde", "ov_count": "Anzahl",
    "ov_days_adv": "Tage im Voraus", "ov_fare_classes": "Tarifklassen",
    "ov_class": "Klasse", "ov_avg": "Durchschnittspreis (€)",
    "ov_c1": "Ø Preis pro Crawl-Datum — letzte {days} Tage",
    "ov_c1_note": "📌 Jeder Punkt = Ø aller an diesem Datum gecrawlten Preise. Zeigt, wie sich der Durchschnittspreis im Beobachtungszeitraum entwickelt.",
    "ov_c2": "Preisrange Min / Avg / Max pro Anbieter (Raute = Durchschnitt)",
    "ov_c3": "Gesamte erfasste Preisbeobachtungen pro Abfahrtsstunde und Anbieter",
    "ov_c4": "Anzahl aufgezeichneter Verbindungen pro Buchungshorizont",
    "ov_c5": "Durchschnittspreis pro Tarifklasse und Anbieter",
    "ov_mode": "Ansicht",
    "ov_mode_route": "📍 Strecke gesamt",
    "ov_mode_trip": "🚆 Einzelne Reise",
    "ov_show_reverse": "⇄ Rückrichtung auch anzeigen",
    "ov_dir_outbound": "Hin",
    "ov_dir_return": "Rück",
    "ov_no_reverse_data": "Keine Daten für die Rückrichtung verfügbar.",
    "ov_dep_date": "Abfahrtsdatum",
    "ov_train_filter": "Zug",
    "ov_all_trains": "Alle Züge (aggregiert)",
    "ov_all_trains_note": "💡 Aggregierte Ansicht über alle Züge. Für die Analyse einzelner Züge siehe Tab Einzelzug.",
    "ov_eur_km": "€ / km (Ø)", "ov_eur_h": "€ / h (Ø)",
    "ov_km_sub": "{km:.0f} km (Luftlinie)", "ov_h_sub": "Ø Fahrzeit: {h:.1f} h",
    "ov_no_dist": "Keine Distanzdaten", "ov_no_time": "Keine Fahrzeitdaten",
    "ov_no_trip_data": "Keine Daten für dieses Abfahrtsdatum.",
    "ov_nearest": "Nächstgelegene Termine mit Daten:",
    "ov_trip_dev": "Preisentwicklung nach Buchungshorizont — Abfahrt {date}",
    "ov_trend_trip": "Preisänderung zuletzt (7T)",
    "ov_trend_trip_help": "Ø der letzten 7 Crawl-Tage vs. frühere Crawls für diese Abfahrt.",
    "ov_data_maturity": "📊 Erfasste Buchungshorizonte: +{hmax} bis +{hmin} · {covered}/90 Horizonte · {obs} Messungen",
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
    "bh_c1_dyn": "{basis} pro Anbieter nach Buchungshorizont",
    "bh_avg": "Durchschnittspreis (€)",
    "bh_c2": "Anzahl aufgezeichneter Verbindungen pro Buchungshorizont",
    "bh_conn": "Anzahl Verbindungen",
    "bh_table": "Detailtabelle — Durchschnittspreis pro Anbieter und Horizont",
    "bh_opt": "Optimaler Buchungszeitpunkt pro Anbieter",
    "bh_cheap": "Günstigst bei", "bh_saves": "spart {pct:.0f}%",
    "bh_cap": "Avg. {price:.2f} € ({obs} Beob.)",
    "bh_bc_normal": "Normalpreis",
    "bh_bc50": "🎫 Bahncard 50",
    "bh_bc25": "🎫 Bahncard 25",
    "bh_bc_note": "Bahncard 50 = 50% Rabatt, Bahncard 25 = 25% Rabatt — angewendet auf DB- und DB (ParseBot)-Normalpreise.",
    "bh_bc_none": "Bitte mindestens einen Preistyp auswählen.",
    "dt_head": "Tageszeit-Analyse — {orig} → {dest}",
    "dt_op": "Anbieter", "dt_no": "Keine Daten für diesen Anbieter.",
    "dt_c1": "Durchschnittspreis nach Abfahrtsstunde — {op}",
    "dt_c1_dyn": "{basis} nach Abfahrtsstunde — {op}",
    "dt_c2": "Heatmap — Durchschnittspreis pro Wochentag und Stunde ({op})",
    "dt_c2_dyn": "Heatmap — {basis} pro Wochentag und Stunde ({op})",
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
    "op_prof": "**Anbieter-Profil**",
    "op_tbl_min": "Mindestpreis", "op_tbl_avg": "Durchschn. Preis", "op_tbl_max": "Höchstpreis",
    "op_tbl_spread": "Preisspanne", "op_tbl_seats": "Durchschn. Sitzkapazität", "op_tbl_obs": "Beobachtungen",
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
    "cr_err": "⚠️ {n} Importfehler",
    "cr_sel": "Crawler auswählen", "cr_start": "▶ Jetzt starten",
    "cr_on": "✅ Aktiv", "cr_off": "⚠️ Inaktiv",
    "cr_status": "#### 📋 Status pro Crawler",
    "cr_stat_cap": "Crawler · Zuletzt · Einträge · Strecken · Durchschnittspreis",
    "cr_refresh": "🔄 Log aktualisieren",
    "cr_data": "#### 📊 Datenübersicht",
    "cr_total": "Einträge gesamt", "cr_ops": "Crawler",
    "cr_routes": "Strecken", "cr_last": "Zuletzt gesammelt",
    "cr_c1": "Einträge pro Crawler",
    "cr_rec": "Einträge", "cr_cr": "Crawler",
    "cr_c2": "Einträge pro Tag pro Crawler", "cr_date": "Datum",
    "cr_tbl_op": "Anbieter", "cr_tbl_last": "Letzter Lauf",
    "cr_tbl_rec": "Einträge", "cr_tbl_rt": "Strecken", "cr_tbl_price": "Ø Preis",
    "nm_head": "Normalisierte Preise — {orig} → {dest}",
    "nm_no_dist": "⚠️ Keine Distanzdaten für diese Strecke verfügbar.",
    "nm_no_time": "⚠️ Keine Fahrzeitdaten (arrival_at fehlt) für diese Strecke.",
    "nm_dist": "Streckendistanz (Luftlinie)",
    "nm_km": "km",
    "nm_eur_km": "€ / km",
    "nm_eur_h": "€ / h",
    "nm_hz": "Buchungshorizont (Tage im Voraus)",
    "nm_c1": "Mindestpreis pro km nach Buchungshorizont",
    "nm_c2": "Mindestpreis pro Fahrstunde nach Buchungshorizont",
    "nm_c3": "€/km vs. €/h — Anbietervergleich bei +{days} Tagen",
    "nm_c4": "Verteilung: Preis pro km über alle Horizonte",
    "nm_note": "ℹ️ Distanzen sind Luftlinien (Haversine). Tatsächliche Schienenwege sind typischerweise 15–25% länger.",
    "nm_hz_sel": "Buchungshorizont für Streudiagramm",
    "nm_op": "Anbieter",
    "nm_travel_h": "Ø Fahrzeit (h)",
    "nm_obs": "Beobachtungen",
    "nm_summary": "Diese Strecke: **{eurkm:.3f} €/km** · **{eurh:.2f} €/h** (Basis: {basis}, +{days}T)",
    "nm_basis_note": "Charts unten nutzen die gewählte Preisbasis. €/h nutzt die Gesamtreisezeit (inkl. Umstiege).",
    "price_basis": "Preisbasis",
    "price_min": "Minimum",
    "price_avg": "Durchschnitt",
    "price_basis_help": "Minimum = günstigster Tarif pro Gruppe (robuste Yield-Management-Basis). Durchschnitt = Mittel aller Tarife (abhängig davon, welche Züge erfasst wurden).",
    "direct_filter": "Verbindungstyp",
    "direct_all": "Alle",
    "direct_only": "Nur direkt",
    "direct_transfer": "Mit Umstieg",
    "ov_dep_hour_note": "ℹ️ Hinweis: Manche Anbieter (v.a. DB) decken nur ein begrenztes Tagesfenster ab — siehe Tab Tageszeit.",
    "ov_fare_note": "ℹ️ Tarifklassen sind zwischen Anbietern nicht direkt vergleichbar; price_eur (günstigster verfügbarer Tarif) ist das verlässliche Feld.",
    "dt_coverage_warn": "⚠️ Eingeschränkte Tagesabdeckung: nur {n} verschiedene Stunden für {op} erfasst. Vorsichtig interpretieren — dies spiegelt das feste Abfragefenster des Crawlers wider, nicht den echten Fahrplan.",
    "dt_seats_none": "Keine Sitzplatz-Verfügbarkeitsdaten für diesen Anbieter.",
    "tr_heterogen": "⚠️ {n} verschiedene Zug-IDs für {op} — Zugnummern sind heterogen (Umsteigekombinationen). Einzelzug-Analyse ist für Trenitalia/Italo am zuverlässigsten.",
    "cr_health": "#### 🚦 7-Tage-Gesundheit",
    "cr_health_cap": "Tage mit Daten in den letzten 7 · Ø Einträge/Tag",
    "cr_health_ok": "✅", "cr_health_warn": "⚠️", "cr_health_bad": "❌",
    "cr_avg_day": "Ø/Tag",
    "lp_eyebrow":       "KIT · Institut für Volkswirtschaftslehre · SS 2026",
    "lp_subtitle":      "Systematische Erhebung und Analyse von Fahrkartenpreisen europäischer Bahnbetreiber — Grundlage für die empirische Untersuchung von Yield-Management-Strategien im Schienenpersonenverkehr.",
    "lp_kpi_obs":       "Beobachtungen",
    "lp_kpi_ops":       "Betreiber",
    "lp_kpi_routes":    "Strecken",
    "lp_kpi_horizons":  "Horizonte",
    "lp_sec_operators": "Erfasste Betreiber",
    "lp_sec_collection":"Datenerhebung",
    "lp_sec_modules":   "Analyse-Module",
    "lp_sec_method":    "Methodik & Hinweise",
    "lp_observations":  "Beobachtungen",
    "lp_th_operator":   "Anbieter",
    "lp_obs_short":     "Beob.",
    "lp_kit_full":      "Karlsruher Institut für Technologie",
    "lp_hz_label":      "Buchungshorizonte in Tagen vor Abfahrt",
    "lp_steps_titles":  ["Scheduler", "14 Horizonte", "TimescaleDB", "Dieses Portal"],
    "lp_steps_descs":   [
        "Täglich 10:00 UTC startet der automatische Crawl-Prozess für alle aktiven Betreiber simultan.",
        "Pro Route werden Preise für 14 feste Buchungszeitpunkte zwischen 1 und 90 Tagen vor Abfahrt abgefragt.",
        "Alle Beobachtungen werden dedupliziert in einer Zeitreihendatenbank auf der Projekt-VM gespeichert.",
        "Das Dashboard liest direkt aus der Datenbank und ermöglicht Analyse und Vergleich in Echtzeit.",
    ],
    "lp_mod_names":     ["Übersicht", "Einzelzug", "Buchungshorizont", "Tageszeit", "Anbietervergleich", "€/km & €/h", "Crawler-Status"],
    "lp_mod_questions": [
        "Wie haben sich die Preise auf dieser Strecke entwickelt?",
        "Wie verändert sich der Preis eines konkreten Zuges über die Zeit?",
        "Wann ist der optimale Kaufzeitpunkt?",
        "Sind frühe oder späte Abfahrten systematisch teurer?",
        "Welcher Betreiber ist auf welcher Strecke am günstigsten?",
        "Welcher Betreiber bietet den besten Preis pro Kilometer?",
        "Wie zuverlässig laufen die Datensammler?",
    ],
    "lp_mod_details":   [
        "MIN · AVG · MAX pro Betreiber, wählbarer Zeitraum",
        "Preisverlauf ab 90 Tage bis kurz vor Abfahrt",
        "Preiskurven für alle 14 Buchungshorizonte im Vergleich",
        "Preis nach Abfahrtsstunde und Wochentag",
        "Direktvergleich aller Anbieter bei wählbarem Horizont",
        "Normalisierte Preise für streckenneutralen Vergleich",
        "7-Tage-Verfügbarkeit, letzte Läufe, Record-Counts",
    ],
    "lp_method_left":   (
        "<b>Preisbasis</b><br>"
        "Alle Analysen basieren auf dem günstigsten verfügbaren Tarif (<code>MIN(price_eur)</code>) "
        "pro Route, Horizont und Erhebungstag. Standardisierung: 1 Erwachsener, 2.&nbsp;Klasse "
        "bzw. Economy-Tarif, Einzelfahrt, ohne Rabattkarten oder Zusatzleistungen.<br><br>"
        "<b>Tarifklassen</b><br>"
        "Die <code>fare_class</code>-Spalte ist betreiberspezifisch und nicht direkt vergleichbar. "
        "Für Anbietervergleiche wird ausschließlich <code>price_eur</code> herangezogen."
    ),
    "lp_method_right":  (
        "<b>Bekannte Einschränkungen</b><br>"
        "Die DB-API blockiert Datacenter-IPs seit 18.05.2026 (HTTP&nbsp;403/500); "
        "DB-Preise werden ergänzend über <code>db_parsebot</code> bezogen. "
        "Der DB-Crawler erfasst ausschließlich Verbindungen im Morgenfenster "
        "(ca.&nbsp;08:00-13:15&nbsp;Uhr Abfahrtszeit).<br><br>"
        "<b>Zeitzonen</b><br>"
        "Alle Zeitstempel werden in UTC gespeichert. Ausnahme: "
        "Trenitalia speichert Abfahrtszeiten in Lokalzeit (<code>Europe/Rome</code>)."
    ),
    "lp_footer_sub":    "Institut für Volkswirtschaftslehre · Teamprojekt SS 2026",
    "lp_footer_last":   "Letzter Crawl-Lauf",
    "lp_sec_findings":       "Kernergebnisse",
    "lp_finding_early":      "Frühbuchereffekt",
    "lp_finding_cheap":      "Größter Preisunterschied",
    "lp_finding_route":      "Meist beobachtete Strecke",
    "lp_sec_growth":         "Datenwachstum & Abdeckung",
    "lp_growth_caption":     "Kumulativer Aufbau der Datenbank — letzte 120 Tage",
    "lp_density_caption":    "Datendichte pro Anbieter × Buchungshorizont",
    "lp_density_good":       "gut",
    "lp_density_partial":    "teilweise",
    "lp_density_sparse":     "lückenhaft",
    "lp_kpi_period":         "Erhebungszeitraum",
    "lp_finding_more_exp":   "teurer",
    "lp_finding_cheaper":    "günstiger",
    "lp_finding_early_text": "Tickets bei ≤7&nbsp;Tagen Vorlauf sind im Schnitt <b>{pct:.1f}%</b> {dir} als bei ≥60&nbsp;Tagen — aggregiert über alle Betreiber und Strecken.",
    "lp_finding_cheap_text": "<b>{route}</b> zeigt die größte Preisspanne: von {low:.2f}&nbsp;€ bis {high:.2f}&nbsp;€.",
    "lp_finding_route_text": "<b>{route}</b> ist die Strecke mit den meisten Preisbeobachtungen im Datensatz.",
    "lp_footer_tech":        "Daten: TimescaleDB · bwCloud VM · Ubuntu 24",
    "lp_footer_github":      "↗ GitHub · Xaver-M/Rail-Data-Hub",
    "lp_footer_kit":         "↗ KIT",
    "lp_footer_inst":        "↗ Institut für Volkswirtschaftslehre",
    "price_max_label": "Maximum",
    "ov_max_price":    "Höchster Preis",
    "sidebar_offline":       "⚠ Offline · lokaler Snapshot",
    "sidebar_eye":           "KIT · Institut für Volkswirtschaftslehre",
    "sidebar_sub":           "Preisbeobachtung im<br>Schienenpersonenverkehr",
    "sidebar_nav":           "Navigation",
    "sidebar_obs":           "Beobachtungen",
    "sidebar_last":          "Stand",
    "nav_start":             "Start",
    "nav_analyse":           "Analyse",
    "nav_compare":           "Anbietervergleich",
    "nav_crawler":           "Crawler-Status",
    "picker_route":          "Strecke",
    "picker_country":        "🌍 Land",
    "picker_all_countries":  "Alle Länder",
    "picker_operators":      "🚄 Anbieter",
    "picker_all_operators":  "Alle Anbieter",
    "picker_reset":          "✕ Reset",
    "picker_of":             "von",
    "picker_routes":         "Strecken",
    "picker_active_ops":     "Angezeigte Anbieter",
    "picker_all_active_ops": "Alle Anbieter",
    "country_names": {
    "DE": "🇩🇪 Deutschland", "IT": "🇮🇹 Italien", "FR": "🇫🇷 Frankreich",
    "ES": "🇪🇸 Spanien",    "CZ": "🇨🇿 Tschechien", "AT": "🇦🇹 Österreich",
    "SK": "🇸🇰 Slowakei",   "HU": "🇭🇺 Ungarn", "OTHER": "🌍 Andere",
},
 
}

TEXTS = {"en": EN, "de": DE}

def op_label(op): return OPERATOR_LABELS.get(op, op)
def op_color(op): return OPERATOR_COLORS.get(op, "#888888")

# Anzeige-Übersetzung für Bahnhofsnamen (nur fürs UI — origin_name/destination_name
# in der DB/den Queries bleiben unverändert, siehe config/routes.py).
STATION_DISPLAY_NAMES = {
    # ── Czech Republic ──
    "Brno hlavní nádraží":           {"en": "Brno Main Station",           "de": "Brünn Hbf"},
    "Ostrava hlavní nádraží":        {"en": "Ostrava Main Station",        "de": "Ostrau Hbf"},
    "Praha hlavní nádraží":          {"en": "Prague Main Station",         "de": "Prag Hbf"},
    # ── Slovakia ──
    "Bratislava hlavná stanica":     {"en": "Bratislava Main Station",     "de": "Bratislava Hbf"},
    # ── Poland ──
    "Kraków Główny":                 {"en": "Krakow Main Station",         "de": "Krakau Hbf"},
    "Gdańsk Główny":                 {"en": "Gdansk Main Station",         "de": "Danzig Hbf"},
    "Warszawa Centralna":            {"en": "Warsaw Central Station",      "de": "Warschau Hbf"},
    "Wrocław Główny":                {"en": "Wroclaw Main Station",        "de": "Breslau Hbf"},
    # ── France ──
    "Lyon toutes gares":             {"en": "Lyon - All Stations",        "de": "Lyon - Alle Bahnhöfe"},
    "Montpellier toutes gares":      {"en": "Montpellier - All Stations", "de": "Montpellier - Alle Bahnhöfe"},
    "Paris - Toutes les gares":      {"en": "Paris - All Stations",       "de": "Paris - Alle Bahnhöfe"},
    "Nice Ville":                    {"en": "Nice Main Station",          "de": "Nizza Hbf"},
    "Strasbourg Ville":              {"en": "Strasbourg Main Station",    "de": "Straßburg Hbf"},
    # ── Germany (formatting fix only, no translation) ──
    "Frankfurt(Main)Hbf":            {"en": "Frankfurt (Main) Hbf",       "de": "Frankfurt (Main) Hbf"},
    "München Hbf":                   {"en": "Munich Main Station",        "de": "München Hbf"},
    "Köln Hbf":                      {"en": "Cologne Main Station",       "de": "Köln Hbf"},
    # ── Austria / Switzerland ──
    "Wien Hbf":                      {"en": "Vienna Main Station",        "de": "Wien Hbf"},
    "Zürich HB":                     {"en": "Zurich Main Station",        "de": "Zürich HB"},
    # ── Italy ──
    "Bari Centrale":                 {"en": "Bari Main Station",          "de": "Bari Hbf"},
    "Bologna Centrale":              {"en": "Bologna Main Station",       "de": "Bologna Hbf"},
    "Bolzano":                       {"en": "Bolzano",                    "de": "Bozen"},
    "Firenze Santa Maria Novella":   {"en": "Florence Santa Maria Novella","de": "Florenz Santa Maria Novella"},
    "Genova Brignole":               {"en": "Genoa Brignole",             "de": "Genua Brignole"},
    "Genova Piazza Principe":        {"en": "Genoa Piazza Principe",      "de": "Genua Piazza Principe"},
    "Milano Centrale":               {"en": "Milan Main Station",         "de": "Mailand Hbf"},
    "Napoli Centrale":               {"en": "Naples Main Station",        "de": "Neapel Hbf"},
    "Padova":                        {"en": "Padua",                      "de": "Padua"},
    "Reggio di Calabria Centrale":   {"en": "Reggio Calabria Main Station","de": "Reggio Calabria Hbf"},
    "Roma Tiburtina":                {"en": "Rome Tiburtina",             "de": "Rom Tiburtina"},
    "Roma Termini":                  {"en": "Rome Termini",               "de": "Rom Termini"},
    "Trieste Centrale":              {"en": "Trieste Main Station",       "de": "Triest Hbf"},
    "Torino Porta Nuova":            {"en": "Turin Porta Nuova",          "de": "Turin Porta Nuova"},
    "Torino Porta Susa":             {"en": "Turin Porta Susa",           "de": "Turin Porta Susa"},
    "Venezia Mestre":                {"en": "Venice Mestre",              "de": "Venedig Mestre"},
    "Venezia Santa Lucia":           {"en": "Venice Santa Lucia",         "de": "Venedig Santa Lucia"},
    # ── Netherlands ──
    "Amsterdam Centraal":            {"en": "Amsterdam Central Station",  "de": "Amsterdam Hbf"},
    # ── Spain ──
    "Madrid - Todas las estaciones": {"en": "Madrid - All Stations",      "de": "Madrid - Alle Bahnhöfe"},
    "Sevilla - Santa Justa":         {"en": "Seville - Santa Justa",      "de": "Sevilla - Santa Justa"},
    "Zaragoza - Delicias":           {"en": "Zaragoza - Delicias",        "de": "Saragossa - Delicias"},
}

def station_name(raw_name, lang="en"):
    entry = STATION_DISPLAY_NAMES.get(raw_name)
    if entry:
        return entry[lang]
    if lang == "en" and raw_name.endswith(" Hbf"):
        return raw_name[:-len(" Hbf")] + " Main Station"
    return raw_name

def route_label(origin_name, destination_name, lang="en"):
    return f"{station_name(origin_name, lang)} → {station_name(destination_name, lang)}"

def time_since(dt, T) -> str:
    try:
        diff = (datetime.utcnow() - pd.to_datetime(dt).replace(tzinfo=None)).total_seconds()
        if diff < 60:    return T["just_now"]
        if diff < 3600:  return T["min_ago"].format(m=int(diff/60))
        if diff < 86400: return T["h_ago"].format(h=int(diff/3600))
        return T["days_ago"].format(d=int(diff/86400))
    except Exception:
        return "—"
    

def price_basis_toggle(key: str, T) -> str:
    """Gibt 'min', 'avg' oder 'max' zurück."""
    return st.radio(
        T["price_basis"], options=["min", "avg", "max"],
        format_func=lambda m: {"min": T["price_min"], "avg": T["price_avg"], "max": T["price_max_label"]}[m],
        horizontal=True, key=key
    )