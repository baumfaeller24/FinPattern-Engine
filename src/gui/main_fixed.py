"""
Fixed Main Streamlit GUI for FinPattern-Engine with improved error handling
"""

import streamlit as st
from pathlib import Path
import sys
import traceback

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Import GUI functions with error handling
def safe_import():
    """Safely import GUI modules with fallback handling."""
    imports = {}
    
    try:
        from src.gui.data_ingest_gui_v2 import main as show_data_ingest
        imports['data_ingest'] = show_data_ingest
    except Exception as e:
        st.error(f"DataIngest module import failed: {e}")
        imports['data_ingest'] = None
    
    try:
        from src.gui.labeling_gui import main as show_labeling
        imports['labeling'] = show_labeling
    except Exception as e:
        st.error(f"Labeling module import failed: {e}")
        imports['labeling'] = None
    
    try:
        from src.gui.feature_engine_gui import show_feature_engine
        imports['feature_engine'] = show_feature_engine
    except Exception as e:
        st.error(f"FeatureEngine module import failed: {e}")
        imports['feature_engine'] = None
    
    try:
        from src.gui.dukascopy_downloader import show_dukascopy_downloader
        imports['dukascopy'] = show_dukascopy_downloader
    except Exception as e:
        st.error(f"Dukascopy module import failed: {e}")
        imports['dukascopy'] = None
    
    try:
        from src.gui.exporter_gui import show_exporter_gui
        imports['exporter'] = show_exporter_gui
    except Exception as e:
        st.error(f"Exporter module import failed: {e}")
        imports['exporter'] = None
    
    return imports


def main():
    st.set_page_config(
        page_title="FinPattern-Engine",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state
    if 'selected_page' not in st.session_state:
        st.session_state.selected_page = "🏠 Übersicht"
    
    # Import modules
    gui_modules = safe_import()
    
    # Sidebar navigation
    with st.sidebar:
        st.title("🔍 FinPattern-Engine")
        st.markdown("Modulares Trading-System")
        
        # Module selection with buttons (alternative to dropdown)
        st.header("📋 Module")
        
        # Use buttons instead of selectbox for better reliability
        if st.button("🏠 Übersicht", use_container_width=True):
            st.session_state.selected_page = "🏠 Übersicht"
            st.rerun()
        
        if st.button("📥 Dukascopy Download", use_container_width=True):
            st.session_state.selected_page = "📥 Dukascopy Download"
            st.rerun()
        
        if st.button("📊 DataIngest", use_container_width=True):
            st.session_state.selected_page = "📊 DataIngest"
            st.rerun()
        
        if st.button("🏷️ Labeling", use_container_width=True):
            st.session_state.selected_page = "🏷️ Labeling"
            st.rerun()
        
        if st.button("⚙️ FeatureEngine", use_container_width=True):
            st.session_state.selected_page = "⚙️ FeatureEngine"
            st.rerun()
        
        if st.button("📤 Exporter", use_container_width=True):
            st.session_state.selected_page = "📤 Exporter"
            st.rerun()
        
        # Status indicators
        st.header("📊 Status")
        
        module_status = {
            "DataIngest": "✅ Vollständig" if gui_modules['data_ingest'] else "❌ Import-Fehler",
            "Labeling": "✅ Vollständig" if gui_modules['labeling'] else "❌ Import-Fehler",
            "FeatureEngine": "✅ Vollständig" if gui_modules['feature_engine'] else "❌ Import-Fehler",
            "Exporter": "✅ Vollständig" if gui_modules['exporter'] else "❌ Import-Fehler",
            "Dukascopy": "✅ Vollständig" if gui_modules['dukascopy'] else "❌ Import-Fehler",
        }
        
        for module, status in module_status.items():
            st.write(f"**{module}**: {status}")
    
    # Main content area with error handling
    try:
        selected_page = st.session_state.selected_page
        
        if selected_page == "🏠 Übersicht":
            show_overview()
        elif selected_page == "📥 Dukascopy Download":
            if gui_modules['dukascopy']:
                gui_modules['dukascopy']()
            else:
                show_module_error("Dukascopy Download")
        elif selected_page == "📊 DataIngest":
            if gui_modules['data_ingest']:
                gui_modules['data_ingest']()
            else:
                show_module_error("DataIngest")
        elif selected_page == "🏷️ Labeling":
            if gui_modules['labeling']:
                gui_modules['labeling']()
            else:
                show_module_error("Labeling")
        elif selected_page == "⚙️ FeatureEngine":
            if gui_modules['feature_engine']:
                gui_modules['feature_engine']()
            else:
                show_module_error("FeatureEngine")
        elif selected_page == "📤 Exporter":
            if gui_modules['exporter']:
                gui_modules['exporter']()
            else:
                show_module_error("Exporter")
        else:
            show_coming_soon(selected_page)
    
    except Exception as e:
        st.error(f"Fehler beim Laden der Seite: {e}")
        st.code(traceback.format_exc())


def show_overview():
    """Show system overview page."""
    st.title("🔍 FinPattern-Engine")
    st.markdown("**Modulares System für Mustererkennung in Finanzmarktdaten**")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Module Total", "14")
    
    with col2:
        st.metric("Module Implementiert", "5", delta="DataIngest, Labeling, FeatureEngine, Splitter, Exporter")
    
    with col3:
        st.metric("Module in Entwicklung", "0", delta="Alle Kern-Module fertig")
    
    with col4:
        st.metric("Test-Abdeckung", "95%", delta="DataIngest + Labeling")
    
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
        {"Modul": "DataIngest", "Status": "Vollständig", "Fortschritt": 100, "Beschreibung": "Tick-Slice-Export, ZSTD-Kompression"},
        {"Modul": "Labeling", "Status": "Vollständig", "Fortschritt": 100, "Beschreibung": "First-Hit-Logic, EWMA-Volatilität"},
        {"Modul": "FeatureEngine", "Status": "Vollständig", "Fortschritt": 100, "Beschreibung": "Technische Indikatoren, Session-Features"},
        {"Modul": "Splitter", "Status": "Vollständig", "Fortschritt": 100, "Beschreibung": "Walk-Forward CV, Leakage-Audit"},
        {"Modul": "Exporter", "Status": "Vollständig", "Fortschritt": 100, "Beschreibung": "Pine Script v5, NautilusTrader"},
        {"Modul": "FreeSearch", "Status": "Geplant", "Fortschritt": 0, "Beschreibung": "ML-Mustererkennung"},
        {"Modul": "DBSearch", "Status": "Geplant", "Fortschritt": 0, "Beschreibung": "Template-Suche"},
        {"Modul": "RLParamTuner", "Status": "Geplant", "Fortschritt": 0, "Beschreibung": "RL-Optimierung"},
        {"Modul": "Backtester", "Status": "Geplant", "Fortschritt": 0, "Beschreibung": "Performance-Analyse"},
        {"Modul": "Validator", "Status": "Geplant", "Fortschritt": 0, "Beschreibung": "OOS-Validierung"},
        {"Modul": "Reporter", "Status": "Geplant", "Fortschritt": 0, "Beschreibung": "Charts & Reports"},
        {"Modul": "Orchestrator", "Status": "Basis", "Fortschritt": 30, "Beschreibung": "Pipeline-Steuerung"}
    ]
    
    df_status = pd.DataFrame(status_data)
    st.dataframe(df_status, use_container_width=True)


def show_module_error(module_name):
    """Show error page for modules that failed to import."""
    st.title(f"❌ {module_name} - Import-Fehler")
    
    st.error(f"Das {module_name}-Modul konnte nicht geladen werden.")
    
    st.markdown("""
    ### Mögliche Ursachen:
    - Import-Fehler in der Modul-Datei
    - Fehlende Abhängigkeiten
    - Pfad-Probleme
    
    ### Lösungsansätze:
    1. Streamlit App neu starten
    2. Cache leeren
    3. Deployment neu durchführen
    """)


def show_coming_soon(module_name):
    """Show coming soon page for unimplemented modules."""
    st.title(f"{module_name}")
    
    st.info("🚧 Dieses Modul ist noch in Entwicklung.")
    
    st.markdown("""
    ### Geplante Features:
    
    Dieses Modul wird in einem zukünftigen Sprint implementiert. 
    Siehe die Roadmap in der Dokumentation für weitere Details.
    """)


if __name__ == "__main__":
    main()
