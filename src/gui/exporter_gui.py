"""
GUI Component for Module 5: Exporter

This module provides the Streamlit interface for exporting strategies
to TradingView Pine Script and NautilusTrader formats.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import json
import tempfile
import zipfile
import io
from datetime import datetime

# Import the exporter module
import sys
sys.path.append('/home/ubuntu/FinPattern-Engine')
from core.exporter import exporter

def show_exporter_gui():
    """
    Display the Exporter GUI in Streamlit
    """
    
    st.header("📤 Module 5: Exporter")
    st.markdown("Export your labeled events to TradingView Pine Script or NautilusTrader strategies")
    
    # Configuration section
    st.subheader("⚙️ Export Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        strategy_name = st.text_input(
            "Strategy Name", 
            value="FinPattern Strategy",
            help="Name for your exported strategy"
        )
        
        export_formats = st.multiselect(
            "Export Formats",
            options=["pine_script", "nautilus_trader"],
            default=["pine_script"],
            help="Select which formats to export"
        )
    
    with col2:
        st.markdown("**Export Formats:**")
        st.markdown("- **Pine Script**: For TradingView visualization")
        st.markdown("- **NautilusTrader**: For backtesting and live trading")
    
    # File upload section
    st.subheader("📁 Input Data")
    
    # Option 1: Upload labeled events file
    uploaded_file = st.file_uploader(
        "Upload Labeled Events (Parquet)",
        type=['parquet'],
        help="Upload a parquet file containing labeled events from the Labeling module"
    )
    
    # Option 2: Use demo data
    use_demo = st.checkbox(
        "Use Demo Data", 
        help="Use sample labeled events for demonstration"
    )
    
    if use_demo:
        st.info("📊 Demo mode: Using sample labeled events with EUR/USD data")
    
    # Export button
    if st.button("🚀 Export Strategy", type="primary"):
        
        if not export_formats:
            st.error("❌ Please select at least one export format")
            return
        
        if not uploaded_file and not use_demo:
            st.error("❌ Please upload a labeled events file or enable demo mode")
            return
        
        try:
            # Prepare input data
            if use_demo:
                # Create demo labeled events
                labeled_events = _create_demo_labeled_events()
                
                # Save to temporary file
                with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp_file:
                    labeled_events.to_parquet(tmp_file.name, index=False)
                    events_path = tmp_file.name
            else:
                # Save uploaded file to temporary location
                with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp_file:
                    tmp_file.write(uploaded_file.read())
                    events_path = tmp_file.name
            
            # Create output directory
            with tempfile.TemporaryDirectory() as temp_dir:
                output_dir = Path(temp_dir) / "export_output"
                
                # Configure export
                config = {
                    "labeled_events_path": events_path,
                    "out_dir": str(output_dir),
                    "export_formats": export_formats,
                    "strategy_name": strategy_name
                }
                
                # Show progress
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                status_text.text("🔄 Starting export...")
                progress_bar.progress(10)
                
                # Run export
                result = exporter.run(config)
                
                progress_bar.progress(100)
                status_text.text("✅ Export completed successfully!")
                
                # Display results
                _display_export_results(result, output_dir)
                
        except Exception as e:
            st.error(f"❌ Export failed: {str(e)}")
            st.exception(e)

def _create_demo_labeled_events():
    """Create sample labeled events for demonstration"""
    import numpy as np
    
    np.random.seed(42)
    n_events = 50
    
    base_time = pd.Timestamp("2025-01-01 09:00:00", tz="UTC")
    
    events = []
    for i in range(n_events):
        entry_time = base_time + pd.Timedelta(minutes=i * 30)
        exit_time = entry_time + pd.Timedelta(minutes=np.random.randint(15, 120))
        
        label = np.random.choice([1, -1, 0], p=[0.3, 0.3, 0.4])
        hit_type = label if label != 0 else 0
        
        events.append({
            "event_index": i,
            "entry_time": entry_time,
            "exit_time": exit_time,
            "entry_price": 1.1000 + np.random.normal(0, 0.002),
            "label": label,
            "hit_type": hit_type,
            "return": np.random.normal(0, 0.001),
            "volatility_used": np.random.uniform(0.0001, 0.0005)
        })
    
    return pd.DataFrame(events)

def _display_export_results(result, output_dir):
    """Display the export results in the Streamlit interface"""
    
    st.success("🎉 Export completed successfully!")
    
    # Display summary
    summary = result["summary"]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Formats Exported", len(summary["exported_formats"]))
    
    with col2:
        st.metric("Events Processed", summary["total_events_exported"])
    
    with col3:
        st.metric("Strategy Name", summary["strategy_name"])
    
    # Display exported files
    st.subheader("📁 Exported Files")
    
    for format_name, file_path in result["output_files"].items():
        
        file_path_obj = Path(file_path)
        
        if format_name == "pine_script":
            st.markdown("### 📊 TradingView Pine Script")
            
            # Read and display the Pine Script
            with open(file_path_obj) as f:
                pine_content = f.read()
            
            st.code(pine_content, language="javascript")
            
            # Download button
            st.download_button(
                label="📥 Download Pine Script",
                data=pine_content,
                file_name=file_path_obj.name,
                mime="text/plain"
            )
            
        elif format_name == "nautilus_trader":
            st.markdown("### 🚢 NautilusTrader Strategy")
            
            # Read and display the strategy (first 50 lines)
            with open(file_path_obj) as f:
                nautilus_content = f.read()
            
            lines = nautilus_content.split('\n')
            preview_lines = lines[:50]
            
            st.code('\n'.join(preview_lines), language="python")
            
            if len(lines) > 50:
                st.info(f"📄 Showing first 50 lines of {len(lines)} total lines")
            
            # Download button
            st.download_button(
                label="📥 Download NautilusTrader Strategy",
                data=nautilus_content,
                file_name=file_path_obj.name,
                mime="text/plain"
            )

    # Create a zip file with all exported files
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for format_name, file_path in result["output_files"].items():
            file_path_obj = Path(file_path)
            zip_file.writestr(file_path_obj.name, file_path_obj.read_bytes())

    st.download_button(
        label="📥 Download All as ZIP",
        data=zip_buffer.getvalue(),
     file_name=f"{summary['strategy_name']}_export.zip",
        mime="application/zip"
    )

    
    # Usage instructions
    st.subheader("📖 Usage Instructions")
    
    if "pine_script" in result["output_files"]:
        with st.expander("🔧 How to use Pine Script in TradingView"):
            st.markdown("""
            **Steps to use your Pine Script in TradingView:**
            
            1. **Open TradingView** and go to the Pine Editor
            2. **Create a new script** and paste the downloaded Pine Script code
            3. **Save and add to chart** to see your signals
            4. **Customize colors and styles** as needed
            
            **What you'll see:**
            - 🟢 **Green triangles**: Long entry signals
            - 🔴 **Red triangles**: Short entry signals  
            - 🔵 **Blue circles**: Take profit exits
            - 🟠 **Orange crosses**: Stop loss exits
            """)
    
    if "nautilus_trader" in result["output_files"]:
        with st.expander("🚢 How to use NautilusTrader Strategy"):
            st.markdown("""
            **Steps to use your strategy in NautilusTrader:**
            
            1. **Install NautilusTrader**: `pip install nautilus_trader`
            2. **Save the strategy file** in your strategies directory
            3. **Configure your trading environment** (broker, data feeds)
            4. **Run backtests** or deploy for live trading
            
            **Features included:**
            - ✅ **Signal-based entries**: Based on your labeled events
            - ✅ **Position management**: Automatic entry/exit handling
            - ✅ **Risk management**: Built-in position sizing
            - ✅ **Logging**: Detailed trade logging for analysis
            """)

if __name__ == "__main__":
    show_exporter_gui()
