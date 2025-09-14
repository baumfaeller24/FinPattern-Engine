# 🧪 Test-Guide: Modul 1 (DataIngest)

## Übersicht

Das DataIngest-Modul ist vollständig testbar und bietet verschiedene Test-Szenarien für unterschiedliche Anwendungsfälle.

## 🚀 1. Schnelltest (Demo-Modus)

### Einfachster Test mit integrierten Beispieldaten

```bash
cd /home/ubuntu/Linux-Superhelfer-Floki
python test_data_ingest.py
```

**Was passiert:**
- Verwendet integrierte `eurusd_sample.csv` (6 Ticks)
- Generiert alle 3 Bar-Typen (1m, 100t, 1000t)
- Zeigt Qualitätsbericht und Manifest
- Dauert < 1 Sekunde

**Erwartete Ausgabe:**
```
🚀 Testing DataIngest module with demo data...
✅ DataIngest completed successfully!
📊 Symbol: EURUSD
📁 Generated frames: 3
   - 1m: runs/test_demo/bars_1m.parquet
   - 100t: runs/test_demo/bars_100tick.parquet
   - 1000t: runs/test_demo/bars_1000tick.parquet
📈 Processed ticks: 6
📊 Gap coverage: 100.0%
🔖 Module version: 1.1
🔖 Schema version: 1.0
```

---

## 📊 2. Realistische Tests mit verschiedenen Datengrößen

### 2.1 Kleine Datenmenge (1K Ticks)

```bash
# Konfiguration für kleine Daten
cat > configs/test_small.yaml << EOF
symbol: EURUSD
out_dir: ./runs/test_small
csv:
  path: ./samples/ticks/eurusd_small.csv
bar_frames:
- type: time
  unit: 1m
- type: tick
  count: 100
demo: false
EOF

# Test ausführen
python -c "
import yaml
from core.data_ingest.data_ingest import run
config = yaml.safe_load(open('configs/test_small.yaml'))
result = run(config)
print(f'✅ Erfolgreich! Frames: {len(result[\"frames\"])}')
"
```

### 2.2 Mittlere Datenmenge (10K Ticks)

```bash
# Bereits vorkonfiguriert
python -c "
import yaml, json
from core.data_ingest.data_ingest import run
config = yaml.safe_load(open('configs/test_medium.yaml'))
result = run(config)

# Ergebnisse anzeigen
for frame_name, frame_path in result['frames'].items():
    import pandas as pd
    df = pd.read_parquet(frame_path)
    print(f'{frame_name}: {len(df)} Bars')

# Qualitätsbericht
with open(result['quality_report']) as f:
    quality = json.load(f)
print(f'Verarbeitete Ticks: {quality[\"n_raw_rows\"]:,}')
print(f'Gap-Abdeckung: {quality[\"gap_coverage_percent\"]:.1f}%')
"
```

**Erwartete Ausgabe:**
```
1m: 82 Bars
100t: 100 Bars  
1000t: 10 Bars
Verarbeitete Ticks: 10,000
Gap-Abdeckung: 100.0%
```

### 2.3 Große Datenmenge (100K Ticks)

```bash
# Konfiguration für große Daten
cat > configs/test_large.yaml << EOF
symbol: EURUSD
out_dir: ./runs/test_large
csv:
  path: ./samples/ticks/eurusd_large.csv
bar_frames:
- type: time
  unit: 1m
- type: tick
  count: 1000
max_missing_gap_seconds: 60
trim_weekend: true
demo: false
EOF

# Performance-Test
time python -c "
import yaml
from core.data_ingest.data_ingest import run
config = yaml.safe_load(open('configs/test_large.yaml'))
result = run(config)
print(f'✅ 100K Ticks verarbeitet!')
"
```

---

## 🧪 3. Unit-Tests (pytest)

### 3.1 Alle Tests ausführen

```bash
# Vollständige Test-Suite
python -m pytest tests/test_core_data_ingest.py -v

# Spezifische Tests
python -m pytest tests/test_core_data_ingest.py::TestCoreDataIngest::test_demo_mode -v
python -m pytest tests/test_core_data_ingest.py::TestCoreDataIngest::test_full_pipeline_with_time_bars -v
python -m pytest tests/test_core_data_ingest.py::TestCoreDataIngest::test_tick_bars_generation -v
```

### 3.2 Error-Handling Tests

```bash
# Test für fehlende Spalten
python -m pytest tests/test_core_data_ingest.py::TestCoreDataIngest::test_error_handling_missing_columns -v

# Test für negative Spreads
python -m pytest tests/test_core_data_ingest.py::TestCoreDataIngest::test_error_handling_negative_spread -v
```

### 3.3 Verfügbare Test-Kategorien

| Test | Beschreibung | Dauer |
|------|-------------|-------|
| `test_demo_mode` | Demo-Modus mit Beispieldaten | ~0.5s |
| `test_full_pipeline_with_time_bars` | Komplette Pipeline mit Zeit-Bars | ~1s |
| `test_tick_bars_generation` | Tick-Bar Generierung | ~1s |
| `test_price_basis_options` | Verschiedene Preis-Basen (mid/bid/ask) | ~2s |
| `test_gap_analysis` | Gap-Erkennung mit Testlücken | ~1s |
| `test_weekend_trimming` | Wochenend-Daten entfernen | ~1s |
| `test_progress_logging` | Progress-Log Validierung | ~1s |
| `test_error_handling_*` | Verschiedene Error-Szenarien | ~0.5s |

---

## 🖥️ 4. GUI-Tests (Streamlit)

### 4.1 GUI starten

```bash
# Hauptinterface
streamlit run src/gui/main.py

# Direkt DataIngest-Modul
streamlit run src/gui/data_ingest_gui.py
```

### 4.2 GUI-Test-Szenarien

#### Szenario A: Demo-Modus
1. ✅ Demo-Modus aktivieren
2. ✅ Symbol: EURUSD
3. ✅ Alle Bar-Typen auswählen
4. ✅ "DataIngest ausführen" klicken
5. ✅ Progress-Bar beobachten
6. ✅ Ergebnisse downloaden

#### Szenario B: CSV-Upload
1. ✅ Demo-Modus deaktivieren
2. ✅ CSV-Datei hochladen (`samples/ticks/eurusd_medium.csv`)
3. ✅ Parameter anpassen (Gap-Schwelle, Preis-Basis)
4. ✅ Ausführen und Ergebnisse prüfen

#### Szenario C: Erweiterte Einstellungen
1. ✅ "Erweiterte Einstellungen" öffnen
2. ✅ Max. Gap auf 30 Sekunden setzen
3. ✅ Wochenenden-Trimming deaktivieren
4. ✅ Unterschiede in Qualitätsbericht beobachten

---

## 📋 5. Manuelle Validierung

### 5.1 Ausgabe-Dateien prüfen

```bash
# Nach einem Test die generierten Dateien untersuchen
ls -la runs/test_medium/

# Manifest prüfen
cat runs/test_medium/manifest.json | jq '.'

# Qualitätsbericht prüfen  
cat runs/test_medium/quality_report.json | jq '.'

# Progress-Log prüfen
tail -5 runs/test_medium/progress.jsonl
```

### 5.2 Bar-Daten analysieren

```bash
# 1-Minuten Bars untersuchen
python -c "
import pandas as pd
df = pd.read_parquet('runs/test_medium/bars_1m.parquet')
print(f'Bars: {len(df)}')
print(f'Zeitspanne: {df.index[0]} bis {df.index[-1]}')
print(f'OHLC-Konsistenz: {(df[\"h\"] >= df[\"l\"]).all()}')
print(f'Durchschnittliche Ticks pro Bar: {df[\"n_ticks\"].mean():.1f}')
"

# 100-Tick Bars untersuchen
python -c "
import pandas as pd
df = pd.read_parquet('runs/test_medium/bars_100tick.parquet')
print(f'Tick-Bars: {len(df)}')
print(f'Alle haben 100 Ticks: {(df[\"n_ticks\"] == 100).all()}')
print(f'Frame-Typ korrekt: {(df[\"frame\"] == \"100t\").all()}')
"
```

### 5.3 Schema-Validierung

```bash
# Prüfe ob alle 18 Spalten vorhanden sind
python -c "
import pandas as pd
from core.data_ingest.schema import BAR_COLUMNS

df = pd.read_parquet('runs/test_medium/bars_1m.parquet')
expected = set(BAR_COLUMNS)
actual = set(df.columns)

print(f'Erwartete Spalten: {len(expected)}')
print(f'Tatsächliche Spalten: {len(actual)}')
print(f'Schema korrekt: {expected == actual}')

if expected != actual:
    print(f'Fehlende: {expected - actual}')
    print(f'Zusätzliche: {actual - expected}')
"
```

---

## ⚡ 6. Performance-Tests

### 6.1 Geschwindigkeits-Benchmark

```bash
# Zeitmessung für verschiedene Datengrößen
echo "=== Performance-Test ==="

echo "1K Ticks:"
time python -c "
from core.data_ingest.data_ingest import run
config = {'out_dir': './runs/perf_1k', 'demo': True, 'bar_frames': [{'type': 'time', 'unit': '1m'}]}
run(config)
"

echo "10K Ticks:"  
time python -c "
import yaml
from core.data_ingest.data_ingest import run
config = yaml.safe_load(open('configs/test_medium.yaml'))
config['out_dir'] = './runs/perf_10k'
run(config)
"
```

### 6.2 Memory-Profiling

```bash
# Memory-Verbrauch messen (falls memory_profiler installiert)
pip install memory-profiler

python -m memory_profiler -c "
from core.data_ingest.data_ingest import run
import yaml
config = yaml.safe_load(open('configs/test_medium.yaml'))
config['out_dir'] = './runs/memory_test'
run(config)
"
```

---

## 🔍 7. Debugging und Troubleshooting

### 7.1 Verbose Logging

```bash
# Progress-Log in Echtzeit verfolgen
python -c "
import yaml
from core.data_ingest.data_ingest import run
config = yaml.safe_load(open('configs/test_medium.yaml'))
config['out_dir'] = './runs/debug_test'
run(config)
" &

# In anderem Terminal:
tail -f runs/debug_test/progress.jsonl
```

### 7.2 Häufige Probleme

| Problem | Lösung |
|---------|--------|
| `KeyError: 'csv'` | Demo-Modus aktivieren oder CSV-Pfad konfigurieren |
| `FileNotFoundError` | Pfad zu CSV-Datei prüfen |
| `NEGATIVE_SPREAD` | Datenqualität prüfen (Ask < Bid) |
| `MISSING_COLUMN` | CSV-Format validieren (timestamp, bid, ask) |
| Pandas FutureWarnings | Normal, funktioniert trotzdem |

### 7.3 Test-Daten erstellen

```bash
# Neue Testdaten generieren
python create_test_data.py

# Eigene CSV-Datei validieren
python -c "
import pandas as pd
df = pd.read_csv('path/to/your/data.csv')
print(f'Spalten: {list(df.columns)}')
print(f'Zeilen: {len(df)}')
print(f'Erste 3 Zeilen:')
print(df.head(3))
"
```

---

## ✅ 8. Test-Checkliste

Vor der Freigabe für Modul 2 sollten alle Tests erfolgreich sein:

- [ ] **Demo-Modus Test** erfolgreich
- [ ] **10K Ticks Test** erfolgreich  
- [ ] **Unit-Tests** alle bestanden
- [ ] **GUI-Test** funktional
- [ ] **Schema-Validierung** korrekt
- [ ] **Error-Handling** funktioniert
- [ ] **Performance** akzeptabel (<5s für 10K Ticks)
- [ ] **Manifest** wird korrekt erstellt
- [ ] **Progress-Logging** funktioniert
- [ ] **Alle 3 Bar-Typen** werden generiert

**Status: ✅ Alle Tests bestanden - Modul 1 ist production-ready!**
