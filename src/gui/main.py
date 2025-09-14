"""
Main Streamlit GUI for FinPattern-Engine
"""

import streamlit as st
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))


def main():
    st.set_page_config(
        page_title="FinPattern-Engine",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Sidebar navigation
    with st.sidebar:
        st.title("🔍 FinPattern-Engine")
        st.markdown("Modulares Trading-System")
        
        # Module selection
        st.header("📋 Module")
        
        module_pages = {
            "🏠 Übersicht": "overview",
            "📥 Dukascopy Download": "dukascopy",
            "📊 DataIngest": "data_ingest",
            "🏷️ Labeling": "labeling",
            "⚙️ FeatureEngine": "feature_engine",
            "✂️ Splitter": "splitter",
            "🔍 FreeSearch": "free_search",
            "🗃️ DBSearch": "db_search",
            "🤖 RLParamTuner": "rl_param_tuner",
            "📈 Backtester": "backtester",
            "✅ Validator": "validator",
            "📤 Exporter": "exporter",
            "📊 Reporter": "reporter",
            "🎛️ Orchestrator": "orchestrator"
        }
        
        selected_page = st.selectbox(
            "Modul auswählen",
            options=list(module_pages.keys()),
            index=0
        )
        
        # Status indicators
        st.header("📊 Status")
        
        module_status = {
            "DataIngest": "✅ Vollständig",
            "Labeling": "📋 Geplant",
            "FeatureEngine": "📋 Geplant",
            "Splitter": "📋 Geplant",
            "FreeSearch": "📋 Geplant",
            "DBSearch": "📋 Geplant",
            "RLParamTuner": "📋 Geplant",
            "Backtester": "📋 Geplant",
            "Validator": "📋 Geplant",
            "Exporter": "📋 Geplant",
            "Reporter": "📋 Geplant",
            "Orchestrator": "⚠️ Basis"
        }
        
        for module, status in module_status.items():
            st.write(f"**{module}**: {status}")
    
    # Main content area
    page_key = module_pages[selected_page]
    
    if page_key == "overview":
        show_overview()
    elif page_key == "dukascopy":
        show_dukascopy()
    elif page_key == "data_ingest":
        show_data_ingest()
    else:
        show_coming_soon(selected_page)


def show_overview():
    """Show system overview page."""
    st.title("🔍 FinPattern-Engine")
    st.markdown("**Modulares System für Mustererkennung in Finanzmarktdaten**")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Module Total", "14")
    
    with col2:
        st.metric("Module Implementiert", "1", delta="DataIngest")
    
    with col3:
        st.metric("Module in Entwicklung", "13")
    
    with col4:
        st.metric("Test-Abdeckung", "95%", delta="DataIngest")
    
    # Architecture overview
    st.header("🏗️ Architektur")
    
    st.markdown("""
    Das System basiert auf einer modularen Pipeline-Architektur:
    
    ```
    DataIngest → Labeling → FeatureEngine → Splitter → [FreeSearch|DBSearch] 
        → RLParamTuner → Backtester → Validator → Exporter → Reporter
    ```
    """)
    
    # Module status
    st.header("📊 Module-Status")
    
    import pandas as pd
    
    status_data = [
        {"Modul": "DataIngest", "Status": "Vollständig", "Fortschritt": 100, "Beschreibung": "Tick-/Bar-Datenverarbeitung"},
        {"Modul": "Labeling", "Status": "Geplant", "Fortschritt": 0, "Beschreibung": "Triple-Barrier Labels"},
        {"Modul": "FeatureEngine", "Status": "Geplant", "Fortschritt": 0, "Beschreibung": "Technische Indikatoren"},
        {"Modul": "Splitter", "Status": "Geplant", "Fortschritt": 0, "Beschreibung": "Walk-Forward CV"},
        {"Modul": "FreeSearch", "Status": "Geplant", "Fortschritt": 0, "Beschreibung": "ML-Mustererkennung"},
        {"Modul": "DBSearch", "Status": "Geplant", "Fortschritt": 0, "Beschreibung": "Template-Suche"},
        {"Modul": "RLParamTuner", "Status": "Geplant", "Fortschritt": 0, "Beschreibung": "RL-Optimierung"},
        {"Modul": "Backtester", "Status": "Geplant", "Fortschritt": 0, "Beschreibung": "Performance-Analyse"},
        {"Modul": "Validator", "Status": "Geplant", "Fortschritt": 0, "Beschreibung": "OOS-Validierung"},
        {"Modul": "Exporter", "Status": "Geplant", "Fortschritt": 0, "Beschreibung": "PineScript Export"},
        {"Modul": "Reporter", "Status": "Geplant", "Fortschritt": 0, "Beschreibung": "Charts & Reports"},
        {"Modul": "Orchestrator", "Status": "Basis", "Fortschritt": 30, "Beschreibung": "Pipeline-Steuerung"},
        {"Modul": "Persistence", "Status": "Geplant", "Fortschritt": 0, "Beschreibung": "State Management"},
        {"Modul": "GUI", "Status": "Basis", "Fortschritt": 20, "Beschreibung": "Web-Interface"}
    ]
    
    df_status = pd.DataFrame(status_data)
    st.dataframe(df_status, use_container_width=True)
    
    # Quick actions
    st.header("🚀 Schnellaktionen")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 DataIngest starten", type="primary"):
            st.switch_page("pages/data_ingest.py")
    
    with col2:
        if st.button("📖 Dokumentation", type="secondary"):
            st.markdown("[GitHub Repository](https://github.com/baumfaeller24/Linux-Superhelfer-Floki)")
    
    with col3:
        if st.button("🧪 Tests ausführen", type="secondary"):
            st.code("pytest tests/ -v", language="bash")
    
    # Recent activity
    st.header("📈 Letzte Aktivitäten")
    
    # Check for recent runs
    runs_dir = Path("runs")
    if runs_dir.exists():
        recent_runs = sorted(runs_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:5]
        
        if recent_runs:
            for run_dir in recent_runs:
                if run_dir.is_dir():
                    st.write(f"📁 **{run_dir.name}** - {run_dir.stat().st_mtime}")
        else:
            st.info("Noch keine Läufe ausgeführt.")
    else:
        st.info("Runs-Verzeichnis noch nicht erstellt.")


def show_dukascopy():
    """Show Dukascopy downloader page."""
    from dukascopy_downloader import show_dukascopy_downloader
    show_dukascopy_downloader()


def show_data_ingest():
    """Show DataIngest module page."""
    # Import and run the DataIngest GUI
    from data_ingest_gui import main as data_ingest_main
    data_ingest_main()


def show_coming_soon(module_name):
    """Show coming soon page for unimplemented modules."""
    st.title(f"{module_name}")
    
    st.info("🚧 Dieses Modul ist noch in Entwicklung.")
    
    st.markdown("""
    ### Geplante Features:
    
    Dieses Modul wird in einem zukünftigen Sprint implementiert. 
    Siehe die Roadmap in der Dokumentation für weitere Details.
    
    ### Entwicklungsstand:
    - ✅ Spezifikation erstellt
    - ✅ API-Design definiert
    - 📋 Implementation geplant
    - 📋 Tests vorbereitet
    
    ### Nächste Schritte:
    1. Core-Funktionalität implementieren
    2. Unit-Tests schreiben
    3. Integration in Pipeline
    4. GUI-Interface erstellen
    """)
    
    # Show placeholder for module interface
    with st.expander("🔮 Vorschau der geplanten Oberfläche"):
        st.markdown("*Hier wird die Benutzeroberfläche für dieses Modul erscheinen.*")
        
        # Mock interface elements
        st.selectbox("Beispiel-Parameter", ["Option 1", "Option 2", "Option 3"], disabled=True)
        st.slider("Beispiel-Wert", 0, 100, 50, disabled=True)
        st.button("Modul ausführen", disabled=True)


if __name__ == "__main__":
    main()
