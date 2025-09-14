#!/usr/bin/env python3
"""
Test der Dukascopy-Integration für FinPattern-Engine
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root / "src" / "gui"))

def test_dukascopy_import():
    """Test ob die Dukascopy-Bibliothek korrekt importiert werden kann"""
    try:
        import dukascopy_python
        from dukascopy_python.instruments import INSTRUMENT_FX_MAJORS_EUR_USD
        print("✅ Dukascopy-Python erfolgreich importiert")
        print(f"   Version: {dukascopy_python.__version__ if hasattr(dukascopy_python, '__version__') else 'Unknown'}")
        return True
    except ImportError as e:
        print(f"❌ Dukascopy-Python Import fehlgeschlagen: {e}")
        return False

def test_dukascopy_downloader_import():
    """Test ob unser Dukascopy-Downloader importiert werden kann"""
    try:
        from dukascopy_downloader import show_dukascopy_downloader, DUKASCOPY_AVAILABLE
        print("✅ Dukascopy-Downloader erfolgreich importiert")
        print(f"   Dukascopy verfügbar: {DUKASCOPY_AVAILABLE}")
        return True
    except ImportError as e:
        print(f"❌ Dukascopy-Downloader Import fehlgeschlagen: {e}")
        return False

def test_small_data_download():
    """Test eines kleinen Datendownloads"""
    try:
        import dukascopy_python
        from dukascopy_python.instruments import INSTRUMENT_FX_MAJORS_EUR_USD
        
        print("🔄 Teste kleinen Datendownload...")
        
        # Sehr kleiner Zeitraum (1 Stunde)
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)
        
        print(f"   Zeitraum: {start_time} bis {end_time}")
        
        # Download mit Timeout
        df = dukascopy_python.fetch(
            instrument=INSTRUMENT_FX_MAJORS_EUR_USD,
            interval=dukascopy_python.INTERVAL_TICK,
            offer_side=dukascopy_python.OFFER_SIDE_BID,
            start=start_time,
            end=end_time,
            max_retries=2,
            debug=False
        )
        
        if df is not None and not df.empty:
            print(f"✅ Download erfolgreich: {len(df)} Ticks erhalten")
            print(f"   Spalten: {list(df.columns)}")
            print(f"   Zeitraum: {df.index[0]} bis {df.index[-1]}")
            return True
        else:
            print("⚠️ Download erfolgreich, aber keine Daten erhalten (möglicherweise außerhalb der Handelszeiten)")
            return True
            
    except Exception as e:
        print(f"❌ Download-Test fehlgeschlagen: {e}")
        return False

def test_data_conversion():
    """Test der Datenkonvertierung"""
    try:
        from dukascopy_downloader import convert_dukascopy_to_finpattern
        import pandas as pd
        
        print("🔄 Teste Datenkonvertierung...")
        
        # Mock Dukascopy-Daten erstellen
        mock_data = pd.DataFrame({
            'bidPrice': [1.1000, 1.1001, 1.1002],
            'askPrice': [1.1002, 1.1003, 1.1004],
            'bidVolume': [100, 150, 200],
            'askVolume': [100, 150, 200]
        }, index=pd.to_datetime([
            '2025-01-01 09:00:00',
            '2025-01-01 09:00:01', 
            '2025-01-01 09:00:02'
        ]))
        
        # Konvertierung testen
        converted = convert_dukascopy_to_finpattern(mock_data, "EUR/USD", "Bid")
        
        if not converted.empty:
            print(f"✅ Konvertierung erfolgreich: {len(converted)} Zeilen")
            print(f"   Spalten: {list(converted.columns)}")
            print(f"   Beispiel-Zeile: {converted.iloc[0].to_dict()}")
            return True
        else:
            print("❌ Konvertierung fehlgeschlagen: Leeres DataFrame")
            return False
            
    except Exception as e:
        print(f"❌ Konvertierungs-Test fehlgeschlagen: {e}")
        return False

def main():
    """Führe alle Tests aus"""
    print("🧪 Teste Dukascopy-Integration für FinPattern-Engine")
    print("=" * 60)
    
    tests = [
        ("Dukascopy-Import", test_dukascopy_import),
        ("Downloader-Import", test_dukascopy_downloader_import),
        ("Datenkonvertierung", test_data_conversion),
        ("Kleiner Download", test_small_data_download),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 Test: {test_name}")
        print("-" * 40)
        
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test-Fehler: {e}")
            results.append((test_name, False))
    
    # Zusammenfassung
    print("\n" + "=" * 60)
    print("📊 Test-Zusammenfassung:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ BESTANDEN" if result else "❌ FEHLGESCHLAGEN"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Ergebnis: {passed}/{len(results)} Tests bestanden")
    
    if passed == len(results):
        print("🎉 Alle Tests erfolgreich! Dukascopy-Integration ist bereit.")
    else:
        print("⚠️ Einige Tests fehlgeschlagen. Überprüfen Sie die Installation.")
    
    return passed == len(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
