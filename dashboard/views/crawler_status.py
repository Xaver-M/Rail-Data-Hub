# dashboard/views/crawler_status.py
import streamlit as st
import threading
import sys
import os
import importlib
from datetime import datetime

# Ein globales Dictionary, um den Status der laufenden Threads zu tracken, falls gewünscht
if "running_crawlers" not in st.session_state:
    st.session_state.running_crawlers = {}

def run_crawler_thread(bot_module_name):
    """Hilfsfunktion, um einen Crawler-Bot dynamisch in einem Thread auszuführen."""
    try:
        # Versucht das Bot-Modul aus dem crawler-Verzeichnis zu laden
        bot_module = importlib.import_module(f"crawler.bots.{bot_module_name}")
        if hasattr(bot_module, "main"):
            bot_module.main()
        elif hasattr(bot_module, "run"):
            bot_module.run()
    except Exception as e:
        print(f"Fehler beim Ausführen des Crawlers {bot_module_name}: {e}", file=sys.stderr)

def render_crawler_status(T):
    st.title(f"🤖 {T['tab_crawler']}")
    st.markdown("### 🔄 Crawler-Steuerung & Bot-Protokolle")
    
    # 1. Übersicht der verfügbaren Bots
    # Hier listen wir die Bots auf, die in deinem Projekt existieren (erweiterbar)
    available_bots = {
        "db_crawler": "Deutsche Bahn Bot",
        "flix_crawler": "Flixtrain / Flixbus Bot",
        "trenitalia_crawler": "Trenitalia Bot",
        "italo_crawler": "Italo Bot",
        "ouigo_crawler": "Ouigo Bot"
    }
    
    st.write("#### ⚡ Live-Aktionen")
    
    # Spalten-Layout für die Bots
    cols = st.columns(len(available_bots))
    
    for idx, (bot_id, bot_name) in enumerate(available_bots.items()):
        with cols[idx]:
            is_running = st.session_state.running_crawlers.get(bot_id, False)
            
            # Status-Badge
            if is_running:
                st.success(f"🟢 {bot_name}\n(Läuft)")
                if st.button(f"Stoppen", key=f"stop_{bot_id}", disabled=True):
                    # Thread-Stoppen ist in Python nativ komplex, daher hier ausgegraut
                    pass
            else:
                st.error(f"🔴 {bot_name}\n(Inaktiv)")
                if st.button(f"Starten", key=f"start_{bot_id}"):
                    # Thread starten
                    t = threading.Thread(target=run_crawler_thread, args=(bot_id,), daemon=True)
                    t.start()
                    st.session_state.running_crawlers[bot_id] = True
                    st.rerun()

    st.markdown("---")

    # 2. Live-Logs (Simuliert oder aus einer Logdatei gelesen)
    st.write("#### 📋 Letzte System-Protokolle")
    
    # Pfad zu einer eventuellen Log-Datei definieren
    log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "crawler.log")
    
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                # Die letzten 50 Zeilen der Log-Datei lesen
                log_lines = f.readlines()[-50:]
                log_text = "".join(log_lines)
                st.code(log_text, language="text")
        except Exception as e:
            st.error(f"Fehler beim Lesen der Log-Datei: {e}")
    else:
        # Standard-Fallbacks falls (noch) keine Datei existiert
        st.info("Keine externe Log-Datei gefunden. Zeige aktuelle Dashboard-Sitzungsprotokolle:")
        st.code(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: RailDataHub Dashboard erfolgreich initialisiert.\n"
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Warte auf Crawler-Aktivierung...", 
            language="text"
        )