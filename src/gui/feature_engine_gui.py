"""
Streamlit GUI for Module 3: FeatureEngine

This module provides a user-friendly interface for generating technical analysis features.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from pathlib import Path
import tempfile
import os

# Import from our project
from core.feature_engine.feature_engine import run as run_feature_engine
from core.orchestrator.run_manager import run_manager


def show_feature_engine():
    """Main function to display the FeatureEngine GUI."""
    
    st.title("🔧 FeatureEngine - Technische Indikatoren")
    st.markdown("**Generiere professionelle technische Indikatoren für Machine Learning Modelle**")
    
    # --- Configuration Section ---
    st.header("⚙️ Konfiguration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Eingabedaten")
        
        # Demo mode toggle
        demo_mode = st.checkbox("Demo-Modus (EUR/USD Beispieldaten)", value=True)
        
        if not demo_mode:
            uploaded_file = st.file_uploader(
                "Gelabelte Parquet-Datei hochladen",
                type=['parquet'],
                help="Laden Sie eine Parquet-Datei mit gelabelten Bar-Daten hoch (Output von Modul 2)"
            )
        else:
            st.info("📈 Demo-Modus: Verwendet integrierte EUR/USD Beispieldaten mit Labels")
    
    with col2:
        st.subheader("🎛️ Feature-Kategorien")
        
        # Feature categories selection
        momentum = st.checkbox("📈 Momentum Indikatoren", value=True, 
                              help="RSI, MACD, Stochastic, CCI")
        trend = st.checkbox("📊 Trend Indikatoren", value=True,
                           help="SMA, EMA, ADX, Trend-Verhältnisse")
        volatility = st.checkbox("📉 Volatilitäts Indikatoren", value=True,
                                help="Bollinger Bands, ATR, Volatilität")
        volume = st.checkbox("📦 Volume Indikatoren", value=False,
                            help="OBV, Volume-Verhältnisse (nur wenn Volume-Daten verfügbar)")
    
    # Advanced parameters
    with st.expander("🔧 Erweiterte Parameter"):
        col3, col4 = st.columns(2)
        
        with col3:
            rsi_period = st.number_input("RSI Periode", min_value=5, max_value=50, value=14)
            macd_fast = st.number_input("MACD Fast", min_value=5, max_value=30, value=12)
            macd_slow = st.number_input("MACD Slow", min_value=15, max_value=50, value=26)
        
        with col4:
            bb_period = st.number_input("Bollinger Bands Periode", min_value=10, max_value=50, value=20)
            bb_std = st.number_input("Bollinger Bands Std Dev", min_value=1.0, max_value=3.0, value=2.0, step=0.1)
            atr_period = st.number_input("ATR Periode", min_value=5, max_value=30, value=14)
    
    # --- Execution Section ---
    st.header("🚀 Ausführung")
    
    # Build feature categories list
    feature_categories = []
    if momentum:
        feature_categories.append("momentum")
    if trend:
        feature_categories.append("trend")
    if volatility:
        feature_categories.append("volatility")
    if volume:
        feature_categories.append("volume")
    
    if not feature_categories:
        st.warning("⚠️ Bitte wählen Sie mindestens eine Feature-Kategorie aus.")
        return
    
    # Run button
    if st.button("🔧 FeatureEngine starten", type="primary"):
        
        # Prepare input data
        if demo_mode:
            # Create demo labeled data
            demo_data = create_demo_labeled_data()
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.parquet') as tmp_file:
                demo_data.to_parquet(tmp_file.name)
                input_file_path = tmp_file.name
        else:
            if uploaded_file is None:
                st.error("❌ Bitte laden Sie eine Parquet-Datei hoch oder aktivieren Sie den Demo-Modus.")
                return
            
            # Save uploaded file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.parquet') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                input_file_path = tmp_file.name
        
        # Prepare configuration
        config = {
            "input_file": input_file_path,
            "feature_categories": feature_categories,
            "rsi_period": rsi_period,
            "macd_fast": macd_fast,
            "macd_slow": macd_slow,
            "bb_period": bb_period,
            "bb_std": bb_std,
            "atr_period": atr_period,
            "out_dir": tempfile.mkdtemp()
        }
        
        # Execute FeatureEngine
        with st.spinner("🔧 Generiere technische Indikatoren..."):
            result = run_feature_engine(config)
        
        # Clean up temporary input file
        try:
            os.unlink(input_file_path)
        except:
            pass
        
        # Display results
        if result and result.get("success"):
            st.success("✅ FeatureEngine erfolgreich abgeschlossen!")
            
            # Load and display results
            feature_data_path = result["feature_data_path"]
            df_features = pd.read_parquet(feature_data_path)
            
            # Display summary
            report = result["report"]
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📊 Anzahl Bars", f"{report['n_bars']:,}")
            with col2:
                st.metric("🔧 Original Features", report['n_original_features'])
            with col3:
                st.metric("✨ Neue Features", report['n_new_features'])
            with col4:
                st.metric("📈 Total Features", len(df_features.columns))
            
            # Feature overview
            st.subheader("📋 Generierte Features")
            
            new_features = report['new_feature_names']
            if new_features:
                # Group features by category
                momentum_features = [f for f in new_features if any(x in f.lower() for x in ['rsi', 'macd', 'stoch', 'cci'])]
                trend_features = [f for f in new_features if any(x in f.lower() for x in ['sma', 'ema', 'price_vs'])]
                volatility_features = [f for f in new_features if any(x in f.lower() for x in ['bb_', 'atr', 'volatility'])]
                volume_features = [f for f in new_features if any(x in f.lower() for x in ['obv', 'volume'])]
                other_features = [f for f in new_features if f not in momentum_features + trend_features + volatility_features + volume_features]
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if momentum_features:
                        st.write("**📈 Momentum:**")
                        for feature in momentum_features:
                            st.write(f"• {feature}")
                    
                    if volatility_features:
                        st.write("**📉 Volatilität:**")
                        for feature in volatility_features:
                            st.write(f"• {feature}")
                
                with col2:
                    if trend_features:
                        st.write("**📊 Trend:**")
                        for feature in trend_features:
                            st.write(f"• {feature}")
                    
                    if volume_features:
                        st.write("**📦 Volume:**")
                        for feature in volume_features:
                            st.write(f"• {feature}")
                
                if other_features:
                    st.write("**🔧 Weitere Features:**")
                    for feature in other_features:
                        st.write(f"• {feature}")
            
            # Visualizations
            st.subheader("📊 Feature Visualisierungen")
            
            # Sample recent data for visualization
            recent_data = df_features.tail(100)
            
            # Price and moving averages
            if 'sma_20' in df_features.columns:
                fig_price = go.Figure()
                fig_price.add_trace(go.Scatter(x=recent_data.index, y=recent_data['close'], 
                                             name='Close Price', line=dict(color='blue')))
                if 'sma_20' in recent_data.columns:
                    fig_price.add_trace(go.Scatter(x=recent_data.index, y=recent_data['sma_20'], 
                                                 name='SMA 20', line=dict(color='orange')))
                if 'ema_20' in recent_data.columns:
                    fig_price.add_trace(go.Scatter(x=recent_data.index, y=recent_data['ema_20'], 
                                                 name='EMA 20', line=dict(color='green')))
                
                fig_price.update_layout(title="💹 Preis und Moving Averages", 
                                      xaxis_title="Zeit", yaxis_title="Preis")
                st.plotly_chart(fig_price, use_container_width=True)
            
            # RSI
            if 'rsi_14' in df_features.columns:
                fig_rsi = go.Figure()
                fig_rsi.add_trace(go.Scatter(x=recent_data.index, y=recent_data['rsi_14'], 
                                           name='RSI 14', line=dict(color='purple')))
                fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Überkauft")
                fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Überverkauft")
                fig_rsi.update_layout(title="📈 RSI (Relative Strength Index)", 
                                    xaxis_title="Zeit", yaxis_title="RSI")
                st.plotly_chart(fig_rsi, use_container_width=True)
            
            # MACD
            if 'macd' in df_features.columns:
                fig_macd = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                       subplot_titles=('MACD Line & Signal', 'MACD Histogram'))
                
                fig_macd.add_trace(go.Scatter(x=recent_data.index, y=recent_data['macd'], 
                                            name='MACD', line=dict(color='blue')), row=1, col=1)
                if 'macd_signal' in recent_data.columns:
                    fig_macd.add_trace(go.Scatter(x=recent_data.index, y=recent_data['macd_signal'], 
                                                name='Signal', line=dict(color='red')), row=1, col=1)
                if 'macd_histogram' in recent_data.columns:
                    fig_macd.add_trace(go.Bar(x=recent_data.index, y=recent_data['macd_histogram'], 
                                            name='Histogram', marker_color='green'), row=2, col=1)
                
                fig_macd.update_layout(title="📊 MACD Indicator", height=500)
                st.plotly_chart(fig_macd, use_container_width=True)
            
            # Download section
            st.subheader("💾 Downloads")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Feature data download
                csv_data = df_features.to_csv(index=True)
                st.download_button(
                    label="📊 Feature-Daten (CSV)",
                    data=csv_data,
                    file_name=f"features_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            
            with col2:
                # Report download
                report_json = json.dumps(report, indent=2)
                st.download_button(
                    label="📋 Feature-Report (JSON)",
                    data=report_json,
                    file_name=f"feature_report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
            
            with col3:
                # Parquet download
                parquet_data = open(feature_data_path, 'rb').read()
                st.download_button(
                    label="💾 Feature-Daten (Parquet)",
                    data=parquet_data,
                    file_name=f"features_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.parquet",
                    mime="application/octet-stream"
                )
            
            # Clean up temporary files
            try:
                os.unlink(feature_data_path)
                os.rmdir(result["output_dir"])
            except:
                pass
        
        else:
            st.error(f"❌ FeatureEngine fehlgeschlagen: {result.get('error', 'Unbekannter Fehler')}")


def create_demo_labeled_data():
    """Create demo labeled data for testing."""
    import numpy as np
    
    # Generate realistic EUR/USD data with labels
    np.random.seed(42)
    n_bars = 500
    
    # Base price around 1.10
    base_price = 1.10
    price_changes = np.random.normal(0, 0.0005, n_bars)
    prices = [base_price]
    
    for change in price_changes:
        new_price = prices[-1] + change
        prices.append(max(1.05, min(1.15, new_price)))  # Keep within realistic range
    
    prices = np.array(prices[1:])
    
    # Generate OHLC data
    data = {
        'open': prices,
        'high': prices + np.random.uniform(0, 0.0010, n_bars),
        'low': prices - np.random.uniform(0, 0.0010, n_bars),
        'close': prices + np.random.normal(0, 0.0003, n_bars),
        'volume': np.random.randint(1000, 10000, n_bars),
        'label': np.random.choice([-1, 0, 1], n_bars, p=[0.3, 0.4, 0.3]),  # From labeling module
        'ret': np.random.normal(0, 0.001, n_bars),  # Returns from labeling
        't_final': np.random.randint(1, 25, n_bars)  # Time to barrier hit
    }
    
    # Ensure high >= low and realistic OHLC relationships
    data['high'] = np.maximum(data['high'], np.maximum(data['open'], data['close']))
    data['low'] = np.minimum(data['low'], np.minimum(data['open'], data['close']))
    
    df = pd.DataFrame(data)
    df.index = pd.date_range('2025-01-01', periods=n_bars, freq='1min')
    
    return df


if __name__ == "__main__":
    show_feature_engine()
