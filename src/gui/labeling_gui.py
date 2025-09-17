"""
Streamlit GUI for Module 2: Triple-Barrier Labeling
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
from pathlib import Path
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from core.labeling.labeling import run as run_labeling
from core.orchestrator.run_manager import run_manager


def main():
    """Main function for the Labeling GUI."""
    
    st.title("🏷️ Modul 2: Triple-Barrier Labeling")
    st.markdown("**Generiert Trading-Labels basierend auf Take-Profit, Stop-Loss und Timeout-Barrieren**")
    
    # --- Sidebar: Configuration ---
    with st.sidebar:
        st.header("⚙️ Konfiguration")
        
        # Input file selection
        st.subheader("📊 Input-Daten")
        
        # Check for available bar files from Module 1
        runs_dir = Path("runs")
        available_files = []
        
        if runs_dir.exists():
            for run_dir in runs_dir.iterdir():
                if run_dir.is_dir():
                    data_ingest_dir = run_dir / "data_ingest"
                    if data_ingest_dir.exists():
                        for file in data_ingest_dir.glob("bars_*.parquet"):
                            available_files.append(str(file))
        
        # Add demo files
        demo_files = [
            "samples/bars/bars_1m_demo.parquet",
            "samples/bars/bars_100tick_demo.parquet", 
            "samples/bars/bars_1000tick_demo.parquet"
        ]
        
        all_files = ["Demo-Modus (integrierte Daten)"] + available_files + demo_files
        
        selected_input = st.selectbox(
            "Bar-Daten auswählen",
            options=all_files,
            help="Wählen Sie die Bar-Daten von Modul 1 aus"
        )
        
        # Upload option
        uploaded_file = st.file_uploader(
            "Oder Parquet-Datei hochladen",
            type=["parquet"],
            help="Bar-Daten im Parquet-Format"
        )
        
        st.divider()
        
        # Triple-Barrier Parameters
        st.subheader("🎯 Triple-Barrier Parameter")
        
        tp_mult = st.number_input(
            "Take-Profit Multiplikator",
            min_value=0.1,
            max_value=10.0,
            value=2.0,
            step=0.1,
            help="Multiplikator für Take-Profit Schwelle basierend auf Volatilität"
        )
        
        sl_mult = st.number_input(
            "Stop-Loss Multiplikator", 
            min_value=0.1,
            max_value=10.0,
            value=1.0,
            step=0.1,
            help="Multiplikator für Stop-Loss Schwelle basierend auf Volatilität"
        )
        
        timeout_bars = st.number_input(
            "Timeout (Bars)",
            min_value=1,
            max_value=1000,
            value=24,
            step=1,
            help="Anzahl Bars bis zum Timeout (Vertikale Barriere)"
        )
        
        st.divider()
        
        # Advanced Parameters
        st.subheader("🔧 Erweiterte Parameter")
        
        volatility_span = st.number_input(
            "Volatilitäts-Span",
            min_value=10,
            max_value=500,
            value=100,
            step=10,
            help="EWMA Span für Volatilitätsberechnung"
        )
        
        price_basis = st.selectbox(
            "Preis-Basis für Entry",
            options=["close", "open", "high", "low"],
            index=0,
            help="Welcher Preis für Entry-Punkt verwendet wird"
        )
        
        st.divider()
        
        # Output Configuration
        st.subheader("📤 Output")
        
        output_suffix = st.text_input(
            "Output-Suffix",
            value="_labeled",
            help="Suffix für Output-Datei (z.B. bars_1m_labeled.parquet)"
        )
    
    # --- Main Area ---
    
    # Demo mode or file selection
    use_demo = selected_input == "Demo-Modus (integrierte Daten)"
    
    if use_demo:
        st.info("📊 **Demo-Modus aktiv** - Verwendet integrierte EUR/USD 1-Minuten Bars")
        
        # Create demo data
        demo_data = create_demo_bar_data()
        input_file_path = None
        df_input = demo_data
        
    elif uploaded_file:
        st.success(f"📁 **Datei hochgeladen:** {uploaded_file.name}")
        df_input = pd.read_parquet(uploaded_file)
        input_file_path = None
        
    elif selected_input in available_files:
        st.success(f"📁 **Datei ausgewählt:** {Path(selected_input).name}")
        input_file_path = selected_input
        df_input = pd.read_parquet(input_file_path)
        
    else:
        st.warning("⚠️ Bitte wählen Sie Input-Daten aus oder laden Sie eine Datei hoch.")
        return
    
    # --- Data Preview ---
    with st.expander("👁️ Daten-Vorschau", expanded=False):
        st.subheader("Input Bar-Daten")
        st.dataframe(df_input.head(10))
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Anzahl Bars", len(df_input))
        with col2:
            st.metric("Zeitraum", f"{len(df_input)} Bars")
        with col3:
            if "close" in df_input.columns:
                price_range = df_input["close"].max() - df_input["close"].min()
                st.metric("Preis-Range", f"{price_range:.5f}")
    
    # --- Configuration Summary ---
    st.subheader("⚙️ Konfiguration")
    
    config_col1, config_col2 = st.columns(2)
    
    with config_col1:
        st.write("**Triple-Barrier Parameter:**")
        st.write(f"• Take-Profit: {tp_mult}x Volatilität")
        st.write(f"• Stop-Loss: {sl_mult}x Volatilität") 
        st.write(f"• Timeout: {timeout_bars} Bars")
        
    with config_col2:
        st.write("**Erweiterte Parameter:**")
        st.write(f"• Volatilitäts-Span: {volatility_span}")
        st.write(f"• Preis-Basis: {price_basis}")
        st.write(f"• Output-Suffix: {output_suffix}")
    
    # --- Run Labeling ---
    st.subheader("🚀 Labeling ausführen")
    
    if st.button("🏷️ Triple-Barrier Labeling starten", type="primary"):
        
        # Create temporary file if using demo or uploaded data
        if use_demo or uploaded_file:
            temp_dir = Path("temp_labeling")
            temp_dir.mkdir(exist_ok=True)
            temp_input_file = temp_dir / "input_bars.parquet"
            df_input.to_parquet(temp_input_file)
            input_file_path = str(temp_input_file)
        
        # Create configuration
        config = {
            "input_file": input_file_path,
            "tp_mult": tp_mult,
            "sl_mult": sl_mult,
            "timeout_bars": timeout_bars,
            "volatility_span": volatility_span,
            "price_basis": price_basis,
            "output_suffix": output_suffix,
            "out_dir": f"runs/labeling_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Run labeling
            status_text.text("🏷️ Starte Triple-Barrier Labeling...")
            progress_bar.progress(10)
            
            result = run_labeling(config)
            
            if result and result["success"]:
                progress_bar.progress(100)
                status_text.text("✅ Labeling erfolgreich abgeschlossen!")
                
                # Display results
                st.success("🎉 **Triple-Barrier Labeling erfolgreich!**")
                
                # Load and display labeled data
                labeled_data = pd.read_parquet(result["labeled_data_path"])
                
                # Results summary
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Gelabelte Bars", len(labeled_data))
                
                with col2:
                    tp_count = (labeled_data["label"] == 1).sum()
                    st.metric("Take-Profit", tp_count)
                
                with col3:
                    sl_count = (labeled_data["label"] == -1).sum()
                    st.metric("Stop-Loss", sl_count)
                
                with col4:
                    timeout_count = (labeled_data["label"] == 0).sum()
                    st.metric("Timeout", timeout_count)
                
                # Label distribution chart
                st.subheader("📊 Label-Verteilung")
                
                label_counts = labeled_data["label"].value_counts()
                label_names = {1: "Take-Profit", -1: "Stop-Loss", 0: "Timeout"}
                
                fig = px.pie(
                    values=label_counts.values,
                    names=[label_names[label] for label in label_counts.index],
                    title="Verteilung der Trading-Labels"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Return distribution
                st.subheader("📈 Return-Verteilung")
                
                fig_hist = px.histogram(
                    labeled_data,
                    x="ret",
                    color="label",
                    nbins=50,
                    title="Verteilung der Returns nach Label",
                    labels={"ret": "Return", "count": "Anzahl"}
                )
                st.plotly_chart(fig_hist, use_container_width=True)
                
                # Sample of labeled data
                st.subheader("🔍 Gelabelte Daten (Sample)")
                st.dataframe(labeled_data.head(20))
                
                # Download options
                st.subheader("📥 Download")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Download labeled data
                    labeled_csv = labeled_data.to_csv(index=False)
                    st.download_button(
                        label="📊 Gelabelte Daten (CSV)",
                        data=labeled_csv,
                        file_name=f"labeled_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                
                with col2:
                    # Download report
                    report_json = json.dumps(result["report"], indent=2)
                    st.download_button(
                        label="📋 Labeling-Report (JSON)",
                        data=report_json,
                        file_name=f"labeling_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
                
            else:
                progress_bar.progress(0)
                error_msg = result.get("error", "Unbekannter Fehler") if result else "Unbekannter Fehler"
                status_text.text(f"❌ Fehler: {error_msg}")
                st.error(f"**Fehler beim Labeling:** {error_msg}")
                
        except Exception as e:
            progress_bar.progress(0)
            status_text.text(f"❌ Fehler: {str(e)}")
            st.error(f"**Unerwarteter Fehler:** {str(e)}")
    
    # --- Information Section ---
    with st.expander("ℹ️ Über Triple-Barrier Labeling", expanded=False):
        st.markdown("""
        ### Was ist Triple-Barrier Labeling?
        
        Triple-Barrier Labeling ist eine Methode zur Erstellung von Trading-Labels, die drei "Barrieren" verwendet:
        
        1. **Take-Profit Barriere (Oben)**: Wenn der Preis um X% steigt → Label = +1
        2. **Stop-Loss Barriere (Unten)**: Wenn der Preis um Y% fällt → Label = -1  
        3. **Timeout Barriere (Zeit)**: Nach Z Bars ohne TP/SL → Label = 0
        
        ### Parameter-Erklärung:
        
        - **Take-Profit Multiplikator**: Wie weit der Preis steigen muss (relativ zur Volatilität)
        - **Stop-Loss Multiplikator**: Wie weit der Preis fallen muss (relativ zur Volatilität)
        - **Timeout Bars**: Nach wie vielen Bars ein Trade als "Timeout" gilt
        - **Volatilitäts-Span**: Zeitfenster für Volatilitätsberechnung (EWMA)
        
        ### Verwendung:
        
        Die gelabelten Daten können für Machine Learning Modelle verwendet werden, um Trading-Signale zu generieren.
        """)


def create_demo_bar_data() -> pd.DataFrame:
    """Create demo bar data for testing."""
    
    np.random.seed(42)
    n_bars = 500
    
    # Generate realistic EUR/USD price movement
    base_price = 1.10000
    returns = np.random.normal(0, 0.0001, n_bars)  # Small returns
    prices = base_price * np.exp(np.cumsum(returns))
    
    # Create OHLC data
    data = []
    for i in range(n_bars):
        price = prices[i]
        noise = np.random.normal(0, 0.00005, 4)  # Small noise for OHLC
        
        open_price = price + noise[0]
        high_price = price + abs(noise[1])
        low_price = price - abs(noise[2])
        close_price = price + noise[3]
        
        # Ensure OHLC consistency
        high_price = max(open_price, high_price, low_price, close_price)
        low_price = min(open_price, high_price, low_price, close_price)
        
        data.append({
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "volume": np.random.randint(1000, 5000),
            "n_ticks": np.random.randint(50, 200)
        })
    
    df = pd.DataFrame(data)
    df.index = pd.date_range("2025-09-01 09:00", periods=n_bars, freq="1min")
    
    return df


if __name__ == "__main__":
    main()
