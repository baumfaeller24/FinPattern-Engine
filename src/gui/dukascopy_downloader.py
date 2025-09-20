"""
Dukascopy Data Downloader für FinPattern-Engine GUI
Ermöglicht direkten Download von historischen Tickdaten über die Dukascopy API
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import tempfile
import os
from pathlib import Path
import logging
import pytz

# Dukascopy Python Library
try:
    import dukascopy_python
    from dukascopy_python.instruments import (
        INSTRUMENT_FX_MAJORS_EUR_USD,
        INSTRUMENT_FX_MAJORS_GBP_USD,
        INSTRUMENT_FX_MAJORS_USD_JPY,
        INSTRUMENT_FX_MAJORS_USD_CHF,
        INSTRUMENT_FX_MAJORS_AUD_USD,
        INSTRUMENT_FX_MAJORS_USD_CAD,
        INSTRUMENT_FX_MAJORS_NZD_USD,
    )
    DUKASCOPY_AVAILABLE = True
except ImportError:
    DUKASCOPY_AVAILABLE = False

# Instrument Mapping
INSTRUMENTS = {
    "EUR/USD": INSTRUMENT_FX_MAJORS_EUR_USD if DUKASCOPY_AVAILABLE else None,
    "GBP/USD": INSTRUMENT_FX_MAJORS_GBP_USD if DUKASCOPY_AVAILABLE else None,
    "USD/JPY": INSTRUMENT_FX_MAJORS_USD_JPY if DUKASCOPY_AVAILABLE else None,
    "USD/CHF": INSTRUMENT_FX_MAJORS_USD_CHF if DUKASCOPY_AVAILABLE else None,
    "AUD/USD": INSTRUMENT_FX_MAJORS_AUD_USD if DUKASCOPY_AVAILABLE else None,
    "USD/CAD": INSTRUMENT_FX_MAJORS_USD_CAD if DUKASCOPY_AVAILABLE else None,
    "NZD/USD": INSTRUMENT_FX_MAJORS_NZD_USD if DUKASCOPY_AVAILABLE else None,
}

def show_dukascopy_downloader():
    """
    Zeigt die Dukascopy Downloader-Oberfläche in der Streamlit GUI
    """
    st.header("📈 Dukascopy Daten-Download")
    
    if not DUKASCOPY_AVAILABLE:
        st.error("""
        ❌ **Dukascopy Python Library nicht installiert**
        
        Bitte installieren Sie die Bibliothek:
        ```bash
        pip install dukascopy-python
        ```
        """)
        return None
    
    st.info("""
    🏦 **Dukascopy Bank SA** bietet kostenlose historische Tickdaten für Forex-Paare.
    Laden Sie direkt die benötigten Daten für Ihre Analyse herunter.
    """)
    
    # Konfiguration
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Instrument")
        symbol = st.selectbox(
            "Forex-Paar auswählen:",
            options=list(INSTRUMENTS.keys()),
            index=0,
            help="Wählen Sie das gewünschte Währungspaar"
        )
        
        offer_side = st.selectbox(
            "Preis-Seite:",
            options=["Bid", "Ask"],
            index=0,
            help="Bid = Verkaufspreis, Ask = Kaufpreis"
        )
    
    with col2:
        st.subheader("📅 Zeitraum")
        
        # Vordefinierte Zeiträume
        preset = st.selectbox(
            "Schnellauswahl:",
            options=[
                "Benutzerdefiniert",
                "Letzte 24 Stunden",
                "Letzte 7 Tage", 
                "Letzter Monat",
                "Letzte 3 Monate"
            ],
            index=1
        )
        
        # Zeitraum berechnen (UTC-korrigiert)
        now_utc = datetime.now(pytz.utc)
        if preset == "Letzte 24 Stunden":
            start_date = now_utc - timedelta(days=1)
            end_date = now_utc
        elif preset == "Letzte 7 Tage":
            start_date = now_utc - timedelta(days=7)
            end_date = now_utc
        elif preset == "Letzter Monat":
            start_date = now_utc - timedelta(days=30)
            end_date = now_utc
        elif preset == "Letzte 3 Monate":
            start_date = now_utc - timedelta(days=90)
            end_date = now_utc
        else:
            # Benutzerdefiniert
            start_date_input = st.date_input(
                "Start-Datum:",
                value=now_utc.date() - timedelta(days=7),
                max_value=now_utc.date()
            )
            end_date_input = st.date_input(
                "End-Datum:",
                value=now_utc.date(),
                max_value=now_utc.date()
            )
            # Kombiniere Datum mit Zeit und mache es UTC-aware
            start_date = pytz.utc.localize(datetime.combine(start_date_input, datetime.min.time()))
            end_date = pytz.utc.localize(datetime.combine(end_date_input, datetime.max.time()))
    
    # Erweiterte Optionen
    with st.expander("🔧 Erweiterte Einstellungen"):
        max_retries = st.number_input(
            "Max. Wiederholungen bei Fehlern:",
            min_value=1,
            max_value=10,
            value=3,
            help="Anzahl der Wiederholungsversuche bei Netzwerkfehlern"
        )
        
        debug_mode = st.checkbox(
            "Debug-Modus aktivieren",
            value=False,
            help="Zeigt detaillierte Logs während des Downloads"
        )
    
    # Download-Button
    st.subheader("⬇️ Download")
    
    # Geschätzte Datenmenge
    days_diff = (end_date - start_date).days
    estimated_ticks = days_diff * 50000  # Grobe Schätzung: 50K Ticks/Tag
    estimated_size_mb = estimated_ticks * 50 / 1024 / 1024  # ~50 Bytes/Tick
    
    st.info(f"""
    📊 **Geschätzte Datenmenge:**
    - Zeitraum: {days_diff} Tage
    - Geschätzte Ticks: ~{estimated_ticks:,}
    - Geschätzte Größe: ~{estimated_size_mb:.1f} MB
    """)
    
    if st.button("🚀 Daten herunterladen", type="primary"):
        return download_dukascopy_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            offer_side=offer_side,
            max_retries=max_retries,
            debug_mode=debug_mode
        )
    
    return None

def download_dukascopy_data(symbol, start_date, end_date, offer_side, max_retries, debug_mode):
    """
    Lädt Daten von Dukascopy herunter und konvertiert sie ins FinPattern-Format
    """
    if not DUKASCOPY_AVAILABLE:
        st.error("Dukascopy Library nicht verfügbar")
        return None
    
    # Progress-Anzeige
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("🔄 Verbindung zu Dukascopy...")
        progress_bar.progress(10)
        
        # Instrument und Offer-Side mapping
        instrument = INSTRUMENTS[symbol]
        offer_side_param = (
            dukascopy_python.OFFER_SIDE_BID if offer_side == "Bid" 
            else dukascopy_python.OFFER_SIDE_ASK
        )
        
        status_text.text(f"📥 Lade {symbol} Tickdaten...")
        progress_bar.progress(30)
        
        

        # FINAL FIX: Convert to naive datetime objects representing UTC
        start_ts = pd.Timestamp(start_date).to_pydatetime().replace(tzinfo=None)
        end_ts = pd.Timestamp(end_date).to_pydatetime().replace(tzinfo=None)


        # Daten herunterladen (Tick-Level)
        df = dukascopy_python.fetch(
            instrument=instrument,
            interval=dukascopy_python.INTERVAL_TICK,
            offer_side=offer_side_param,
            start=start_ts,
            end=end_ts,
            max_retries=max_retries,
            debug=debug_mode
        )
        
        progress_bar.progress(70)
        status_text.text("🔄 Konvertiere Datenformat...")
        
        if df is None or df.empty:
            st.error("❌ Keine Daten für den gewählten Zeitraum verfügbar")
            return None
        
        # Konvertierung ins FinPattern-Format
        converted_df = convert_dukascopy_to_finpattern(df, symbol, offer_side)
        
        progress_bar.progress(90)
        status_text.text("💾 Erstelle CSV-Datei...")
        
        # Temporäre CSV-Datei erstellen
        temp_file = create_temp_csv(converted_df, symbol, start_date, end_date)
        
        progress_bar.progress(100)
        status_text.text("✅ Download abgeschlossen!")
        
        # Erfolgs-Meldung
        st.success(f"""
        ✅ **Download erfolgreich!**
        
        📊 **Statistiken:**
        - Symbol: {symbol}
        - Zeitraum: {start_date.strftime('%Y-%m-%d')} bis {end_date.strftime('%Y-%m-%d')}
        - Anzahl Ticks: {len(converted_df):,}
        - Preis-Seite: {offer_side}
        
        📁 **Datei bereit für DataIngest-Modul**
        """)
        
        # Download-Button für CSV
        with open(temp_file, 'rb') as f:
            csv_data = f.read()
        
        filename = f"{symbol.replace('/', '').lower()}_dukascopy_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
        
        st.download_button(
            label="📥 CSV-Datei herunterladen",
            data=csv_data,
            file_name=filename,
            mime="text/csv",
            help="Laden Sie die konvertierte CSV-Datei für das DataIngest-Modul herunter"
        )
        
        return temp_file
        
    except Exception as e:
        st.error(f"❌ **Fehler beim Download:** {str(e)}")
        if debug_mode:
            st.exception(e)
        return None
    
    finally:
        progress_bar.empty()
        status_text.empty()

def convert_dukascopy_to_finpattern(df, symbol, offer_side):
    """
    Konvertiert Dukascopy DataFrame ins FinPattern-Engine Format
    """
    # Dukascopy Tick-Format:
    # - timestamp (Index)
    # - bidPrice, askPrice
    # - bidVolume, askVolume
    
    converted_data = []
    
    for timestamp, row in df.iterrows():
        # Timestamp in ISO8601 UTC Format
        timestamp_str = timestamp.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        
        # Bid/Ask Preise
        bid_price = row.get('bidPrice', 0.0)
        ask_price = row.get('askPrice', 0.0)
        
        # Validierung: Ask muss > Bid sein
        if ask_price <= bid_price:
            continue
        
        converted_data.append({
            'timestamp': timestamp_str,
            'bid': bid_price,
            'ask': ask_price
        })
    
    return pd.DataFrame(converted_data)

def create_temp_csv(df, symbol, start_date, end_date):
    """
    Erstellt eine temporäre CSV-Datei
    """
    # Temporäres Verzeichnis
    temp_dir = tempfile.gettempdir()
    filename = f"{symbol.replace('/', '').lower()}_dukascopy_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
    temp_file = os.path.join(temp_dir, filename)
    
    # CSV speichern
    df.to_csv(temp_file, index=False)
    
    return temp_file

def install_dukascopy_library():
    """
    Hilfsfunktion zur Installation der Dukascopy Library
    """
    st.info("""
    ### 📦 Dukascopy Library Installation
    
    Um die Dukascopy-Integration zu nutzen, installieren Sie bitte:
    
    ```bash
    pip install dukascopy-python
    ```
    
    **Features:**
    - ✅ Kostenlose historische Tickdaten
    - ✅ Forex Majors (EUR/USD, GBP/USD, etc.)
    - ✅ Hohe Datenqualität von Dukascopy Bank SA
    - ✅ Direkte Integration in FinPattern-Engine
    """)

if __name__ == "__main__":
    # Test der Funktionalität
    show_dukascopy_downloader()
