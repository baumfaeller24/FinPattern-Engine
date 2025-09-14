# FinPattern-Engine

Ein modulares System für Mustererkennung in Finanzmarktdaten (Tick- und Bardaten) mit Fokus auf reproduzierbare Trading-Strategien.

## 🎯 Zielsetzung

FinPattern-Engine ist ein umfassendes Backtesting- und Forschungssystem für Trading-Strategien, das zwei komplementäre Ansätze zur Mustererkennung unterstützt:

- **Freie Mustererkennung**: Datengetriebene Entdeckung von Mustern mittels Machine Learning
- **Template-basierte Suche**: Mustererkennung basierend auf vordefiniertem Indikator-Katalog

Alle Ergebnisse sind vollständig reproduzierbar und können direkt als PineScript v5 für TradingView exportiert werden.

## 🏗️ Architektur

Das System basiert auf einer modularen Pipeline-Architektur mit 14 Kernmodulen:

```
DataIngest → Labeling → FeatureEngine → Splitter → [FreeSearch|DBSearch] 
    → RLParamTuner → Backtester → Validator → Exporter → Reporter
```

Gesteuert wird der gesamte Ablauf durch einen zentralen **Orchestrator** (State Machine), der die Koordination zwischen den Modulen übernimmt.

## 📋 Module

| Modul | Status | Beschreibung |
|-------|--------|-------------|
| **DataIngest** | ✅ **Vollständig** | Tickdaten einlesen, normalisieren, Bars erzeugen |
| **Labeling** | 📋 Geplant | Triple-Barrier Labels (TP/SL/Timeout) |
| **FeatureEngine** | 📋 Geplant | Technische Indikatoren berechnen |
| **Splitter** | 📋 Geplant | Walk-Forward, Purged/Embargo CV, Session-Splits |
| **FreeSearch** | 📋 Geplant | Datengetriebene Musterfindung (Trees, RuleFit) |
| **DBSearch** | 📋 Geplant | Musterkatalog + Parametertuning |
| **RLParamTuner** | 📋 Geplant | Reinforcement Learning für Parametrisierung |
| **Backtester** | 📋 Geplant | Kennzahlen pro Regel |
| **Validator** | 📋 Geplant | OOS-Kriterien prüfen |
| **Exporter** | 📋 Geplant | Pine v5, Markdown, CSV |
| **Reporter** | 📋 Geplant | Charts, Reports |
| **Orchestrator** | ⚠️ **Basis** | Ablaufsteuerung |
| **Persistence** | 📋 Geplant | Versionierung, Resume |
| **GUI** | ✅ **Vollständig** | Streamlit-Interface für alle Module |

## 🚀 Schnellstart

### Voraussetzungen

- Python 3.11+
- Linux-Umgebung
- Mindestens 16GB RAM (empfohlen: 32GB+)
- SSD-Speicher für optimale Performance

### Installation

```bash
git clone https://github.com/baumfaeller24/FinPattern-Engine.git
cd FinPattern-Engine
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Erste Schritte

```bash
# Demo mit Beispieldaten ausführen
python scripts/run_module.py --config configs/ingest_demo.yaml

# Oder mit eigenen Daten
python scripts/run_module.py --config configs/ingest.yaml

# GUI starten
streamlit run src/gui/main.py
```

## 🧪 Live-Demo

**Testen Sie Modul 1 sofort online:**

### 🔗 [Live-Demo Interface](https://8501-iwfvnrtzwyj1n5cnmdx3c-ca619beb.manusvm.computer)

**30-Sekunden Test:**
1. ✅ Link öffnen → "📊 DataIngest" klicken
2. ✅ "Demo-Modus" aktiviert lassen
3. ✅ "🔄 DataIngest ausführen" klicken
4. ✅ Ergebnisse downloaden

## 📊 Datenformat

### Eingabe
- **Tickdaten**: CSV mit Spalten `timestamp`, `bid`, `ask`, `[volume]`
- **Format**: ISO8601 UTC Timestamps
- **Konfiguration**: YAML für Run-Parameter

### Ausgabe (DataIngest)
- **Normalisierte Ticks**: `raw_norm.parquet`
- **Zeit-Bars**: `bars_1m.parquet` (OHLC + Spread-Info)
- **Tick-Bars**: `bars_100tick.parquet`, `bars_1000tick.parquet`
- **Qualitätsbericht**: `quality_report.json`
- **Manifest**: `manifest.json` mit Metadaten und Versionierung

### Erweiterte Bar-Schema

```python
BAR_COLUMNS = [
    "symbol",           # z.B. "EURUSD"
    "frame",            # z.B. "1m", "100t"
    "t_open_ns",        # Öffnungszeit (Nanosekunden seit Epoch)
    "t_close_ns",       # Schließzeit (Nanosekunden seit Epoch)
    "o", "h", "l", "c", # OHLC Preise (Mid/Bid/Ask je nach Basis)
    "o_bid", "o_ask",   # Eröffnungs-Bid/Ask
    "c_bid", "c_ask",   # Schluss-Bid/Ask
    "spread_mean",      # Durchschnittlicher Spread
    "n_ticks",          # Anzahl Ticks in diesem Bar
    "v_sum",            # Volumen (falls verfügbar)
    "tick_first_id",    # ID des ersten Ticks
    "tick_last_id",     # ID des letzten Ticks
    "gap_flag"          # 1 wenn Datenlücke erkannt
]
```

## 🎯 Performance-Ziele

- **Datenvolumen**: Monatsdaten EUR/USD (ca. 1-2 Mio. Ticks) in <4h
- **RAM-Nutzung**: ≤100 GB bei Bar-Bildung
- **Reproduzierbarkeit**: Identische Ergebnisse bei gleichem Seed
- **Modularität**: Jedes Modul einzeln testbar und austauschbar

## 📁 Projektstruktur

```
finpattern-engine/
├── core/                 # Neue modulare Struktur
│   ├── data_ingest/      # ✅ Vollständig implementiert
│   ├── orchestrator/     # ⚠️ Basis-Implementation
│   └── [weitere Module]  # 📋 Geplant
├── src/                  # Legacy-Struktur (wird migriert)
├── samples/              # ✅ Beispiel-Tickdaten
├── scripts/              # ✅ Ausführungs-Scripts
├── tests/                # Unit- und Integrationstests
├── configs/              # YAML-Konfigurationen
├── docs/                 # Dokumentation
└── runs/                 # Output-Verzeichnis für Läufe
```

## 🔧 Entwicklung

### Entwicklungsumgebung

```bash
# Development Dependencies installieren
pip install -r requirements-dev.txt

# Tests ausführen
pytest tests/

# Code-Qualität prüfen
black src/ core/
flake8 src/ core/
mypy src/ core/
```

### Governance & Standards

- **Determinismus**: Alle Module verwenden kontrollierte Seeds
- **Versionierung**: Semantische Versionen für Module und Schemas
- **Logging**: Strukturierte Logs in `progress.jsonl`
- **Fehlercodes**: Standardisierte Error-Codes für alle Module
- **Performance**: Parquet mit Snappy-Kompression, Chunked I/O

### Error-Codes

```python
MISSING_COLUMN = "MISSING_COLUMN"      # Erforderliche Spalte fehlt
NEGATIVE_SPREAD = "NEGATIVE_SPREAD"    # Ask < Bid erkannt
UNSORTED_INPUT = "UNSORTED_INPUT"      # Daten nicht zeitlich sortiert
TIMEZONE_ERROR = "TIMEZONE_ERROR"      # Zeitzone-Parsing fehlgeschlagen
IO_ERROR = "IO_ERROR"                  # Datei-I/O Fehler
GAP_EXCESS = "GAP_EXCESS"              # Zu große Datenlücken
CONFIG_ERROR = "CONFIG_ERROR"          # Konfigurationsfehler
```

## 🧪 Testing

Das DataIngest-Modul ist vollständig getestet:

```bash
# Spezifische Tests für DataIngest
pytest tests/test_data_ingest.py -v

# Mit Demo-Daten testen
python scripts/run_module.py --config configs/ingest_demo.yaml
```

## 🤝 Beitragen

1. Fork des Repositories
2. Feature-Branch erstellen (`git checkout -b feature/amazing-feature`)
3. Änderungen committen (`git commit -m 'Add amazing feature'`)
4. Branch pushen (`git push origin feature/amazing-feature`)
5. Pull Request erstellen

## 📄 Lizenz

Dieses Projekt steht unter der MIT-Lizenz. Siehe [LICENSE](LICENSE) für Details.

## 🤝 Support

Bei Fragen oder Problemen:
- GitHub Issues für Bug-Reports und Feature-Requests
- Dokumentation unter `docs/`
- Beispiel-Konfigurationen unter `configs/`

---

**Entwickelt für professionelle Trading-Strategieentwicklung mit Fokus auf Reproduzierbarkeit und wissenschaftliche Rigorosität.**
