# dashboard/views/landing.py
import streamlit as st
import pandas as pd
from dashboard.config import op_color, op_label
from dashboard.database import load_crawler_overview, load_crawler_stats_by_operator


_OPERATOR_META = {
    "db":           {"flag": "🇩🇪", "country": "Deutschland",  "type": "Fernbahn"},
    "db_parsebot":  {"flag": "🇩🇪", "country": "Deutschland",  "type": "Fernbahn (2. Quelle)"},
    "flixtrain":    {"flag": "🇩🇪", "country": "Europa",       "type": "Low-Cost Bahn"},
    "flixbus":      {"flag": "🇪🇺", "country": "Europa",       "type": "Fernbus"},
    "trenitalia":   {"flag": "🇮🇹", "country": "Italien",      "type": "Fernbahn"},
    "italo":        {"flag": "🇮🇹", "country": "Italien",      "type": "High-Speed"},
    "ouigo_es":     {"flag": "🇪🇸", "country": "Spanien",      "type": "Low-Cost Bahn"},
    "ouigo_fr":     {"flag": "🇫🇷", "country": "Frankreich",   "type": "Low-Cost Bahn"},
    "regiojet":     {"flag": "🇨🇿", "country": "Tschechien",   "type": "Fernbahn"},
    "ceske-drahy":  {"flag": "🇨🇿", "country": "Tschechien",   "type": "Fernbahn"},
}

_HORIZONS = [90, 60, 45, 30, 21, 14, 10, 7, 6, 5, 4, 3, 2, 1]

# Leitfragen statt Beschreibungen – zieht den Blick an
_MODULES = [
    ("Übersicht",         "area",    "Wie haben sich die Preise auf dieser Strecke entwickelt?",
     "MIN · AVG · MAX pro Betreiber, wählbarer Zeitraum"),
    ("Einzelzug",         "line",    "Wie verändert sich der Preis eines konkreten Zuges über die Zeit?",
     "Preisverlauf ab 90 Tage bis kurz vor Abfahrt"),
    ("Buchungshorizont",  "curve",   "Wann ist der optimale Kaufzeitpunkt?",
     "Preiskurven für alle 14 Buchungshorizonte im Vergleich"),
    ("Tageszeit",         "heatmap", "Sind frühe oder späte Abfahrten systematisch teurer?",
     "Preis nach Abfahrtsstunde und Wochentag"),
    ("Anbietervergleich", "bar",     "Welcher Betreiber ist auf welcher Strecke am günstigsten?",
     "Direktvergleich aller Anbieter bei wählbarem Horizont"),
    ("€/km & €/h",        "scatter", "Welcher Betreiber bietet den besten Preis pro Kilometer?",
     "Normalisierte Preise für streckenneutralen Vergleich"),
    ("Crawler-Status",    "dots",    "Wie zuverlässig laufen die Datensammler?",
     "7-Tage-Verfügbarkeit, letzte Läufe, Record-Counts"),
]

# Mini-SVG-Icons pro Modul-Typ
_CHART_ICONS = {
    "area": """<svg viewBox="0 0 40 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M0 20 L8 14 L16 16 L24 8 L32 10 L40 4 L40 24 L0 24Z" fill="currentColor" opacity="0.15"/>
        <path d="M0 20 L8 14 L16 16 L24 8 L32 10 L40 4" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>""",
    "line": """<svg viewBox="0 0 40 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M0 18 L10 14 L18 16 L26 6 L34 8 L40 2" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
        <circle cx="26" cy="6" r="2" fill="currentColor"/>
        <circle cx="40" cy="2" r="2" fill="currentColor"/>
    </svg>""",
    "curve": """<svg viewBox="0 0 40 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M2 20 C10 20 14 18 20 12 C26 6 30 4 38 4" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round"/>
        <path d="M2 20 C10 20 16 19 22 17 C28 15 32 12 38 10" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" opacity="0.45"/>
    </svg>""",
    "heatmap": """<svg viewBox="0 0 40 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="2" y="2" width="8" height="8" rx="1" fill="currentColor" opacity="0.2"/>
        <rect x="12" y="2" width="8" height="8" rx="1" fill="currentColor" opacity="0.7"/>
        <rect x="22" y="2" width="8" height="8" rx="1" fill="currentColor" opacity="0.4"/>
        <rect x="32" y="2" width="6" height="8" rx="1" fill="currentColor" opacity="0.9"/>
        <rect x="2" y="13" width="8" height="8" rx="1" fill="currentColor" opacity="0.6"/>
        <rect x="12" y="13" width="8" height="8" rx="1" fill="currentColor" opacity="0.3"/>
        <rect x="22" y="13" width="8" height="8" rx="1" fill="currentColor" opacity="0.8"/>
        <rect x="32" y="13" width="6" height="8" rx="1" fill="currentColor" opacity="0.15"/>
    </svg>""",
    "bar": """<svg viewBox="0 0 40 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="2" y="8" width="6" height="14" rx="1" fill="currentColor" opacity="0.9"/>
        <rect x="11" y="13" width="6" height="9" rx="1" fill="currentColor" opacity="0.6"/>
        <rect x="20" y="4" width="6" height="18" rx="1" fill="currentColor" opacity="0.9"/>
        <rect x="29" y="10" width="6" height="12" rx="1" fill="currentColor" opacity="0.5"/>
        <rect x="2" y="22" width="33" height="1" rx="0.5" fill="currentColor" opacity="0.2"/>
    </svg>""",
    "scatter": """<svg viewBox="0 0 40 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="8" cy="18" r="2.5" fill="currentColor" opacity="0.6"/>
        <circle cx="16" cy="12" r="3.5" fill="currentColor" opacity="0.8"/>
        <circle cx="24" cy="8" r="2" fill="currentColor" opacity="0.5"/>
        <circle cx="32" cy="14" r="4" fill="currentColor" opacity="0.7"/>
        <circle cx="38" cy="6" r="1.5" fill="currentColor" opacity="0.4"/>
        <path d="M4 20 L38 4" stroke="currentColor" stroke-width="0.75" stroke-dasharray="2 2" opacity="0.25"/>
    </svg>""",
    "dots": """<svg viewBox="0 0 40 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="6" cy="6" r="3" fill="currentColor" opacity="0.9"/>
        <circle cx="6" cy="14" r="3" fill="currentColor" opacity="0.9"/>
        <circle cx="20" cy="6" r="3" fill="currentColor" opacity="0.5"/>
        <circle cx="20" cy="14" r="3" fill="currentColor" opacity="0.9"/>
        <circle cx="34" cy="6" r="3" fill="currentColor" opacity="0.2"/>
        <circle cx="34" cy="14" r="3" fill="currentColor" opacity="0.9"/>
        <rect x="12" y="5" width="5" height="2" rx="1" fill="currentColor" opacity="0.15"/>
        <rect x="12" y="13" width="5" height="2" rx="1" fill="currentColor" opacity="0.15"/>
        <rect x="26" y="5" width="5" height="2" rx="1" fill="currentColor" opacity="0.15"/>
        <rect x="26" y="13" width="5" height="2" rx="1" fill="currentColor" opacity="0.15"/>
    </svg>""",
}


def _css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* ── Hero ── */
    .lp-eyebrow {
        font-size: 0.65rem;
        font-weight: 600;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: var(--text-color);
        opacity: 0.35;
        margin-bottom: 0.6rem;
        font-family: 'Inter', sans-serif;
    }
    .lp-title {
        font-family: 'Inter', sans-serif;
        font-size: 2.6rem;
        font-weight: 700;
        letter-spacing: -0.03em;
        color: var(--text-color);
        line-height: 1.05;
        margin: 0 0 0.8rem 0;
    }
    .lp-subtitle {
        font-family: 'Inter', sans-serif;
        font-size: 0.92rem;
        font-weight: 400;
        color: var(--text-color);
        opacity: 0.5;
        line-height: 1.7;
        max-width: 480px;
        margin: 0;
    }

    /* ── KPI Grid ── */
    .lp-kpi-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.8rem 2rem;
    }
    .lp-kpi {
        border-top: 2px solid #2563EB;
        padding-top: 0.7rem;
    }
    .lp-kpi-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 2rem;
        font-weight: 600;
        color: var(--text-color);
        line-height: 1;
        margin-bottom: 0.25rem;
        letter-spacing: -0.02em;
    }
    .lp-kpi-label {
        font-size: 0.65rem;
        font-weight: 600;
        color: var(--text-color);
        opacity: 0.35;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        font-family: 'Inter', sans-serif;
    }

    /* ── Divider ── */
    .lp-rule {
        height: 1px;
        background: rgba(128,128,128,0.12);
        margin: 2.2rem 0;
    }

    /* ── Section Label ── */
    .lp-section-label {
        font-size: 0.62rem;
        font-weight: 600;
        letter-spacing: 0.22em;
        text-transform: uppercase;
        color: var(--text-color);
        opacity: 0.3;
        margin-bottom: 1.2rem;
        font-family: 'Inter', sans-serif;
    }

    /* ── Operator Grid ── */
    .lp-op-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .lp-op-card {
        border: 1px solid rgba(128,128,128,0.13);
        border-radius: 7px;
        padding: 0.85rem 0.9rem 0.7rem 0.9rem;
        background: var(--secondary-background-color);
        position: relative;
        overflow: hidden;
    }
    /* Farbiger Akzentstreifen oben */
    .lp-op-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        border-radius: 7px 7px 0 0;
    }
    .lp-op-flag {
        font-size: 1.1rem;
        margin-bottom: 0.35rem;
        line-height: 1;
    }
    .lp-op-name {
        font-size: 0.8rem;
        font-weight: 700;
        color: var(--text-color);
        font-family: 'Inter', sans-serif;
        margin-bottom: 0.15rem;
        line-height: 1.2;
    }
    .lp-op-type {
        font-size: 0.65rem;
        color: var(--text-color);
        opacity: 0.38;
        margin-bottom: 0.6rem;
        font-family: 'Inter', sans-serif;
    }
    .lp-op-count {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.82rem;
        font-weight: 600;
        color: var(--text-color);
        opacity: 0.75;
    }
    .lp-op-count-label {
        font-size: 0.6rem;
        color: var(--text-color);
        opacity: 0.28;
        font-family: 'Inter', sans-serif;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    /* ── Prozess-Flow ── */
    .lp-flow {
        display: grid;
        grid-template-columns: 1fr 24px 1fr 24px 1fr 24px 1fr;
        align-items: center;
        gap: 0;
        margin-bottom: 1.5rem;
    }
    .lp-flow-step {
        border: 1px solid rgba(128,128,128,0.13);
        border-radius: 7px;
        padding: 1rem 1rem 0.9rem 1rem;
        background: var(--secondary-background-color);
    }
    .lp-flow-num {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.62rem;
        font-weight: 600;
        color: #2563EB;
        margin-bottom: 0.55rem;
        letter-spacing: 0.05em;
    }
    .lp-flow-title {
        font-size: 0.85rem;
        font-weight: 700;
        color: var(--text-color);
        margin-bottom: 0.35rem;
        font-family: 'Inter', sans-serif;
        line-height: 1.2;
    }
    .lp-flow-desc {
        font-size: 0.7rem;
        color: var(--text-color);
        opacity: 0.42;
        line-height: 1.55;
        font-family: 'Inter', sans-serif;
    }
    .lp-flow-arrow {
        text-align: center;
        font-size: 0.9rem;
        color: var(--text-color);
        opacity: 0.2;
        font-family: 'Inter', sans-serif;
    }

    /* ── Horizont-Badges ── */
    .lp-hz-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.3rem;
        margin: 0.5rem 0 0 0;
    }
    .lp-hz {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.68rem;
        font-weight: 500;
        padding: 0.18rem 0.5rem;
        border: 1px solid rgba(128,128,128,0.18);
        border-radius: 3px;
        color: var(--text-color);
        opacity: 0.5;
        background: var(--secondary-background-color);
    }

    /* ── Modul-Grid ── */
    .lp-mod-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .lp-mod-grid-bottom {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 0.5rem;
        margin-bottom: 1rem;
    }
    .lp-mod-card {
        border: 1px solid rgba(128,128,128,0.13);
        border-radius: 7px;
        padding: 0.9rem 1rem;
        background: var(--secondary-background-color);
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }
    .lp-mod-icon {
        width: 40px;
        height: 24px;
        color: #2563EB;
        flex-shrink: 0;
    }
    .lp-mod-question {
        font-size: 0.8rem;
        font-weight: 600;
        color: var(--text-color);
        font-family: 'Inter', sans-serif;
        line-height: 1.35;
    }
    .lp-mod-name {
        font-size: 0.65rem;
        font-weight: 600;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--text-color);
        opacity: 0.35;
        font-family: 'Inter', sans-serif;
    }
    .lp-mod-desc {
        font-size: 0.68rem;
        color: var(--text-color);
        opacity: 0.38;
        line-height: 1.5;
        font-family: 'Inter', sans-serif;
        margin-top: auto;
    }

    /* ── Methodik ── */
    .lp-method {
        font-size: 0.82rem;
        color: var(--text-color);
        opacity: 0.55;
        line-height: 1.75;
        font-family: 'Inter', sans-serif;
    }
    .lp-method b {
        color: var(--text-color);
        opacity: 1;
        font-weight: 600;
    }
    .lp-method code {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.74rem;
        background: rgba(128,128,128,0.1);
        padding: 0.05rem 0.3rem;
        border-radius: 3px;
    }

    /* ── Footer ── */
    .lp-footer {
        border-top: 1px solid rgba(128,128,128,0.12);
        padding: 1.2rem 0 2rem 0;
        margin-top: 2.5rem;
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        flex-wrap: wrap;
        gap: 0.5rem;
    }
    .lp-footer-l {
        font-size: 0.73rem;
        color: var(--text-color);
        opacity: 0.3;
        line-height: 1.7;
        font-family: 'Inter', sans-serif;
    }
    .lp-footer-r {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.65rem;
        color: var(--text-color);
        opacity: 0.2;
    }
    </style>
    """, unsafe_allow_html=True)


def render_landing(T):
    _css()

    overview = load_crawler_overview()
    df_ops   = load_crawler_stats_by_operator()

    total_records  = int(overview.iloc[0]["total_records"]) if not overview.empty else 0
    n_operators    = int(overview.iloc[0]["n_operators"])   if not overview.empty else 0
    n_routes       = int(overview.iloc[0]["n_routes"])      if not overview.empty else 0
    last_collected = overview.iloc[0]["last_collected"]     if not overview.empty else None

    # ══════════════════════════════════════════════════════════
    # HERO
    # ══════════════════════════════════════════════════════════
    col_hero, col_kpis = st.columns([3, 2], gap="large")

    with col_hero:
        st.markdown("""
        <div class="lp-eyebrow">KIT · Institut für Wirtschaftswissenschaften · SS 2026</div>
        <h1 class="lp-title">Rail Data Hub</h1>
        <p class="lp-subtitle">
            Systematische Erhebung und Analyse von Fahrkartenpreisen
            europäischer Bahnbetreiber — Grundlage für die empirische
            Untersuchung von Yield-Management-Strategien im
            Schienenpersonenverkehr.
        </p>
        """, unsafe_allow_html=True)

    with col_kpis:
        st.markdown("<br>", unsafe_allow_html=True)
        rec_fmt = f"{total_records:,}".replace(",", ".")
        st.markdown(f"""
        <div class="lp-kpi-grid">
            <div class="lp-kpi">
                <div class="lp-kpi-value">{rec_fmt}</div>
                <div class="lp-kpi-label">Beobachtungen</div>
            </div>
            <div class="lp-kpi">
                <div class="lp-kpi-value">{n_operators}</div>
                <div class="lp-kpi-label">Betreiber</div>
            </div>
            <div class="lp-kpi">
                <div class="lp-kpi-value">{n_routes}</div>
                <div class="lp-kpi-label">Strecken</div>
            </div>
            <div class="lp-kpi">
                <div class="lp-kpi-value">14</div>
                <div class="lp-kpi-label">Horizonte</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="lp-rule"></div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # BETREIBER — 5-Spalten-Grid mit Farbstreifen oben
    # ══════════════════════════════════════════════════════════
    st.markdown('<div class="lp-section-label">Erfasste Betreiber</div>', unsafe_allow_html=True)

    if not df_ops.empty:
        # Sortiere nach Record-Count absteigend – wichtigste Betreiber zuerst
        df_sorted = df_ops.sort_values("records", ascending=False)

        # Erste 5 in Reihe 1, Rest in Reihe 2
        rows = [df_sorted.iloc[:5], df_sorted.iloc[5:]]
        for row_df in rows:
            if row_df.empty:
                continue
            cols = st.columns(5)
            for col, (_, r) in zip(cols, row_df.iterrows()):
                op    = r["operator"]
                meta  = _OPERATOR_META.get(op, {"flag": "🚆", "country": "–", "type": "–"})
                color = op_color(op)
                name  = op_label(op)
                count = f"{int(r['records']):,}".replace(",", ".")
                with col:
                    st.markdown(f"""
                    <div class="lp-op-card" style="border-top-color:{color}">
                        <div class="lp-op-card" style="position:absolute;top:0;left:0;right:0;height:3px;background:{color};border-radius:7px 7px 0 0;"></div>
                        <div class="lp-op-flag">{meta['flag']}</div>
                        <div class="lp-op-name">{name}</div>
                        <div class="lp-op-type">{meta['country']} · {meta['type']}</div>
                        <div class="lp-op-count">{count}</div>
                        <div class="lp-op-count-label">Beobachtungen</div>
                    </div>
                    """, unsafe_allow_html=True)

    st.markdown('<div class="lp-rule"></div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # DATENERHEBUNG — Flow mit Pfeilen
    # ══════════════════════════════════════════════════════════
    st.markdown('<div class="lp-section-label">Datenerhebung</div>', unsafe_allow_html=True)

    steps = [
        ("01", "Scheduler",     "Täglich 10:00 UTC startet der automatische Crawl-Prozess für alle aktiven Betreiber simultan."),
        ("02", "14 Horizonte",  "Pro Route werden Preise für 14 feste Buchungszeitpunkte zwischen 1 und 90 Tagen vor Abfahrt abgefragt."),
        ("03", "TimescaleDB",   "Alle Beobachtungen werden dedupliziert in einer Zeitreihendatenbank auf der Projekt-VM gespeichert."),
        ("04", "Dieses Portal", "Das Dashboard liest direkt aus der Datenbank und ermöglicht Analyse und Vergleich in Echtzeit."),
    ]

    flow_html = '<div class="lp-flow">'
    for i, (num, title, desc) in enumerate(steps):
        flow_html += f"""
        <div class="lp-flow-step">
            <div class="lp-flow-num">{num}</div>
            <div class="lp-flow-title">{title}</div>
            <div class="lp-flow-desc">{desc}</div>
        </div>"""
        if i < len(steps) - 1:
            flow_html += '<div class="lp-flow-arrow">→</div>'
    flow_html += '</div>'
    st.markdown(flow_html, unsafe_allow_html=True)

    # Horizont-Badges
    st.markdown(
        '<div style="font-size:0.65rem;color:var(--text-color);opacity:0.3;margin-bottom:0.3rem;font-family:Inter,sans-serif;letter-spacing:0.1em;text-transform:uppercase;">Buchungshorizonte in Tagen vor Abfahrt</div>'
        '<div class="lp-hz-row">' +
        "".join(f'<span class="lp-hz">{h}</span>' for h in _HORIZONS) +
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown('<div class="lp-rule"></div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # ANALYSE-MODULE — Leitfragen + Mini-Chart-Icons
    # ══════════════════════════════════════════════════════════
    st.markdown('<div class="lp-section-label">Analyse-Module</div>', unsafe_allow_html=True)

    # Erste 4 Module
    top_mods = _MODULES[:4]
    bot_mods = _MODULES[4:]

    def _mod_card(name, chart_type, question, detail):
        icon_svg = _CHART_ICONS.get(chart_type, "")
        return f"""
        <div class="lp-mod-card">
            <div class="lp-mod-icon">{icon_svg}</div>
            <div>
                <div class="lp-mod-name">{name}</div>
                <div class="lp-mod-question">{question}</div>
            </div>
            <div class="lp-mod-desc">{detail}</div>
        </div>"""

    top_html = '<div class="lp-mod-grid">' + "".join(_mod_card(*m) for m in top_mods) + '</div>'
    bot_html = '<div class="lp-mod-grid-bottom">' + "".join(_mod_card(*m) for m in bot_mods) + '</div>'
    st.markdown(top_html + bot_html, unsafe_allow_html=True)

    st.markdown('<div class="lp-rule"></div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # METHODIK
    # ══════════════════════════════════════════════════════════
    st.markdown('<div class="lp-section-label">Methodik & Hinweise</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("""
        <div class="lp-method">
            <b>Preisbasis</b><br>
            Alle Analysen basieren auf dem günstigsten verfügbaren Tarif
            (<code>MIN(price_eur)</code>) pro Route, Horizont und Erhebungstag.
            Standardisierung: 1 Erwachsener, 2.&nbsp;Klasse bzw. Economy-Tarif,
            Einzelfahrt, ohne Rabattkarten oder Zusatzleistungen.<br><br>
            <b>Tarifklassen</b><br>
            Die <code>fare_class</code>-Spalte ist betreiberspezifisch und nicht direkt
            vergleichbar. Für Anbietervergleiche wird ausschließlich
            <code>price_eur</code> herangezogen.
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="lp-method">
            <b>Bekannte Einschränkungen</b><br>
            Die DB-API blockiert Datacenter-IPs seit 18.05.2026 (HTTP&nbsp;403/500);
            DB-Preise werden ergänzend über <code>db_parsebot</code> bezogen.
            Der DB-Crawler erfasst ausschließlich Verbindungen im Morgenfenster
            (ca.&nbsp;08:00–13:15&nbsp;Uhr Abfahrtszeit).<br><br>
            <b>Zeitzonen</b><br>
            Alle Zeitstempel werden in UTC gespeichert. Ausnahme:
            Trenitalia speichert Abfahrtszeiten in Lokalzeit
            (<code>Europe/Rome</code>).
        </div>
        """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # FOOTER
    # ══════════════════════════════════════════════════════════
    last_str = (
        pd.Timestamp(last_collected).strftime("%d.%m.%Y, %H:%M UTC")
        if last_collected is not None else "–"
    )
    st.markdown(f"""
    <div class="lp-footer">
        <div class="lp-footer-l">
            Rail Data Hub · Karlsruher Institut für Technologie<br>
            Institut für Wirtschaftswissenschaften · Teamprojekt SS 2026
        </div>
        <div class="lp-footer-r">Letzter Crawl-Lauf: {last_str}</div>
    </div>
    """, unsafe_allow_html=True)