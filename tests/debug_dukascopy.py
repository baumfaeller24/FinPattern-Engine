
import pandas as pd
from datetime import datetime, timedelta
import dukascopy_python
from dukascopy_python.instruments import INSTRUMENT_FX_MAJORS_EUR_USD
import pytz

def debug_dukascopy_fetch_timezone_aware():
    """
    Isolierter Test für die dukascopy_python.fetch Funktion mit zeitzonen-bewussten Timestamps.
    """
    print("🐛 Starte Dukascopy Debug-Skript (Timezone-Aware)...")

    # Definiere einen klaren, festen Zeitraum (letzte 3 Tage) mit expliziter UTC-Zeitzone
    utc_tz = pytz.utc
    end_date = datetime.now(utc_tz)
    start_date = end_date - timedelta(days=3)

    print(f"🗓️ Test-Zeitraum (UTC): {start_date.strftime('%Y-%m-%d %H:%M:%S %Z')} bis {end_date.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"PAIR: EUR/USD")

    try:
        # Führe den Fetch-Aufruf mit zeitzonen-bewussten Objekten aus
        df = dukascopy_python.fetch(
            instrument=INSTRUMENT_FX_MAJORS_EUR_USD,
            interval=dukascopy_python.INTERVAL_TICK,
            offer_side=dukascopy_python.OFFER_SIDE_BID,
            start=start_date,
            end=end_date,
            max_retries=3,
            debug=True
        )

        # Überprüfe das Ergebnis
        if df is None:
            print("❌ FEHLER: DataFrame ist None. Kein Ergebnis von der API.")
        elif df.empty:
            print("❌ FEHLER: DataFrame ist leer. Keine Daten für den Zeitraum gefunden.")
        else:
            print(f"✅ ERFOLG: {len(df)} Ticks heruntergeladen.")
            print("--- Erste 5 Zeilen ---")
            print(df.head())
            print("--- Letzte 5 Zeilen ---")
            print(df.tail())

    except Exception as e:
        print(f"💥 KRITISCHER FEHLER: Eine Ausnahme ist aufgetreten.")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_dukascopy_fetch_timezone_aware()

