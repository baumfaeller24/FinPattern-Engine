"""
Streamlit GUI for DataIngest Module - FinPattern-Engine
"""

import streamlit as st
import pandas as pd
import json
import yaml
from pathlib import Path
import tempfile
import shutil
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# Import the core module
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from core.data_ingest.data_ingest import run as run_data_ingest


def main():
    st.set_page_config(
        page_title="FinPattern-Engine: DataIngest",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 FinPattern-Engine: DataIngest Module")
    st.markdown("Tick-Daten einlesen, normalisieren und Bars generieren")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Konfiguration")
        
        # Demo mode toggle
        demo_mode = st.checkbox("Demo-Modus (Beispieldaten)", value=True)
        
        if not demo_mode:
            # File upload
            uploaded_file = st.file_uploader(
                "CSV-Datei hochladen",
                type=['csv'],
                help="CSV mit Spalten: timestamp, bid, ask"
            )
        
        # Symbol configuration
        symbol = st.text_input("Symbol", value="EURUSD", help="Währungspaar oder Instrument")
        
        # Price basis
        price_basis = st.selectbox(
            "Preis-Basis",
            options=["mid", "bid", "ask"],
            index=0,
            help="Basis für OHLC-Berechnung"
        )
        
        # Bar frames
        st.subheader("Bar-Typen")
        
        time_bars = st.checkbox("Zeit-Bars (1 Minute)", value=True)
        tick_bars_100 = st.checkbox("Tick-Bars (100 Ticks)", value=True)
        tick_bars_1000 = st.checkbox("Tick-Bars (1000 Ticks)", value=False)
        
        # Advanced settings
        with st.expander("Erweiterte Einstellungen"):
            max_gap_seconds = st.number_input(
                "Max. Gap (Sekunden)",
                min_value=1,
                max_value=3600,
                value=60,
                help="Maximale Lücke zwischen Ticks"
            )
            
            trim_weekend = st.checkbox(
                "Wochenenden entfernen",
                value=True,
                help="Samstag/Sonntag-Daten entfernen"
            )
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("🚀 Ausführung")
        
        # Build configuration
        bar_frames = []
        if time_bars:
            bar_frames.append({"type": "time", "unit": "1m"})
        if tick_bars_100:
            bar_frames.append({"type": "tick", "count": 100})
        if tick_bars_1000:
            bar_frames.append({"type": "tick", "count": 1000})
        
        config = {
            "symbol": symbol,
            "price_basis": price_basis,
            "max_missing_gap_seconds": max_gap_seconds,
            "trim_weekend": trim_weekend,
            "bar_frames": bar_frames
        }
        
        if demo_mode:
            config["demo"] = True
        
        # Show configuration
        with st.expander("Aktuelle Konfiguration anzeigen"):
            st.json(config)
        
        # Run button
        if st.button("🔄 DataIngest ausführen", type="primary"):
            if not demo_mode and not uploaded_file:
                st.error("Bitte laden Sie eine CSV-Datei hoch oder aktivieren Sie den Demo-Modus.")
                return
            
            # Create temporary directory for output
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                config["out_dir"] = str(temp_path / "output")
                
                if not demo_mode:
                    # Save uploaded file
                    csv_path = temp_path / "uploaded_data.csv"
                    with open(csv_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    config["csv"] = {"path": str(csv_path)}
                
                # Progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    # Run the module
                    status_text.text("Starte DataIngest...")
                    result = run_data_ingest(config)
                    progress_bar.progress(100)
                    status_text.text("✅ Erfolgreich abgeschlossen!")
                    
                    # Store results in session state
                    st.session_state['last_result'] = result
                    st.session_state['output_dir'] = config["out_dir"]
                    
                    st.success("DataIngest erfolgreich ausgeführt!")
                    
                    # Show summary
                    st.subheader("📋 Zusammenfassung")
                    
                    col_a, col_b, col_c = st.columns(3)
                    
                    with col_a:
                        st.metric("Symbol", result['symbol'])
                    
                    with col_b:
                        st.metric("Generierte Frames", len(result['frames']))
                    
                    with col_c:
                        if Path(result['quality_report']).exists():
                            with open(result['quality_report']) as f:
                                quality = json.load(f)
                            st.metric("Verarbeitete Ticks", f"{quality['n_raw_rows']:,}")
                    
                    # Copy results to a persistent location for download
                    persistent_dir = Path("runs") / f"gui_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    persistent_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Copy all output files
                    import shutil
                    for item in Path(config["out_dir"]).iterdir():
                        if item.is_file():
                            shutil.copy2(item, persistent_dir / item.name)
                    
                    st.session_state['persistent_dir'] = str(persistent_dir)
                    
                except Exception as e:
                    progress_bar.progress(0)
                    status_text.text("❌ Fehler aufgetreten")
                    st.error(f"Fehler beim Ausführen: {str(e)}")
    
    with col2:
        st.header("📊 Ergebnisse")
        
        if 'last_result' in st.session_state:
            result = st.session_state['last_result']
            persistent_dir = Path(st.session_state.get('persistent_dir', ''))
            
            # Quality Report
            if 'quality_report' in result and Path(result['quality_report']).exists():
                with open(result['quality_report']) as f:
                    quality = json.load(f)
                
                st.subheader("🔍 Qualitätsbericht")
                
                # Basic stats
                st.write(f"**Verarbeitete Ticks:** {quality['n_raw_rows']:,}")
                st.write(f"**Gap-Abdeckung:** {quality['gap_coverage_percent']:.1f}%")
                
                # Spread statistics
                if 'spread_stats' in quality:
                    spread_stats = quality['spread_stats']
                    st.write(f"**Durchschnittlicher Spread:** {spread_stats['mean']:.5f}")
                    st.write(f"**95%-Perzentil Spread:** {spread_stats['p95']:.5f}")
                
                # Gap analysis
                if quality['gap_items']:
                    st.write(f"**Erkannte Gaps:** {len(quality['gap_items'])}")
                    
                    # Show gap details
                    with st.expander("Gap-Details"):
                        for i, (start, end, duration) in enumerate(quality['gap_items'][:5]):
                            st.write(f"Gap {i+1}: {duration:.1f}s ({start} - {end})")
                        if len(quality['gap_items']) > 5:
                            st.write(f"... und {len(quality['gap_items']) - 5} weitere")
            
            # Download section
            st.subheader("💾 Downloads")
            
            if persistent_dir.exists():
                for file_path in persistent_dir.iterdir():
                    if file_path.is_file():
                        with open(file_path, 'rb') as f:
                            st.download_button(
                                label=f"📁 {file_path.name}",
                                data=f.read(),
                                file_name=file_path.name,
                                mime="application/octet-stream"
                            )
            
            # Manifest info
            if 'manifest' in result and Path(result['manifest']).exists():
                with st.expander("📄 Manifest anzeigen"):
                    with open(result['manifest']) as f:
                        manifest = json.load(f)
                    st.json(manifest)
        
        else:
            st.info("Führen Sie DataIngest aus, um Ergebnisse zu sehen.")
    
    # Progress monitoring (if available)
    if 'output_dir' in st.session_state:
        progress_file = Path(st.session_state['output_dir']) / "progress.jsonl"
        if progress_file.exists():
            st.header("📈 Fortschritt")
            
            # Read progress log
            progress_data = []
            try:
                with open(progress_file) as f:
                    for line in f:
                        progress_data.append(json.loads(line))
                
                if progress_data:
                    # Create progress chart
                    df_progress = pd.DataFrame(progress_data)
                    df_progress['timestamp'] = pd.to_datetime(df_progress['timestamp'])
                    
                    fig = px.line(
                        df_progress,
                        x='timestamp',
                        y='percent',
                        title='Fortschritt über Zeit',
                        labels={'percent': 'Fortschritt (%)', 'timestamp': 'Zeit'}
                    )
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Show step details
                    with st.expander("Schritt-Details"):
                        for step in progress_data:
                            st.write(f"**{step['step']}** ({step['percent']}%): {step['message']}")
            
            except Exception as e:
                st.warning(f"Konnte Fortschritt nicht laden: {e}")


if __name__ == "__main__":
    main()
