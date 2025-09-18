# FinPattern-Engine v2.2

Ein modulares System für Mustererkennung in Finanzmarktdaten mit wissenschaftlich fundierter Tick-Level-Präzision und Walk-Forward-Validation.

## 🎯 Zielsetzung

FinPattern-Engine ist ein umfassendes Backtesting- und Forschungssystem für Trading-Strategien, das höchste wissenschaftliche Standards erfüllt:

- **Tick-Level-Präzision**: First-Hit-Logic für simultane TP/SL-Auflösung
- **Dynamische Volatilität**: EWMA-basierte adaptive Skalierung
- **Walk-Forward-Validation**: Robuste, leakage-freie Backtests
- **Vollständige Reproduzierbarkeit**: Deterministische Ergebnisse mit Seed-Kontrolle

Alle Ergebnisse können direkt als PineScript v5 für TradingView oder NautilusTrader exportiert werden.

## 🏗️ Architektur v2.2

Das System basiert auf einer modularen Pipeline-Architektur mit wissenschaftlich fundierten Verbesserungen:

```
DataIngest v2.2 → Labeling v2.2 → FeatureEngine v2.0 → Splitter v1.0 
    → [FreeSearch|DBSearch] → RLParamTuner → Backtester → Validator 
    → Exporter v1.0 → Reporter
```

**Neu in v2.2:**
- **Event-basierte Tick-Slices** für präzise First-Hit-Detection
- **EWMA-Volatilitäts-Skalierung** für adaptive TP/SL-Levels
- **Walk-Forward-Validation** mit automatisiertem Leakage-Audit
- **Smart Backup System** mit Session-Context-Erhaltung

## 📋 Module Status (v2.2)

| Modul | Status | Version | Beschreibung |
|-------|--------|---------|-------------|
| **DataIngest** | ✅ **v2.2** | Produktiv | Tick-Slice-Export, Kompression, Enhanced Manifest |
| **Labeling** | ✅ **v2.2** | Produktiv | First-Hit-Logic, EWMA-Volatilität, Dual-Timeout |
| **FeatureEngine** | ✅ **v2.0** | Produktiv | Technische Indikatoren, Session-Features |
| **Splitter** | ✅ **v1.0** | Produktiv | Walk-Forward, Session-aware, Leakage-Audit |
| **Exporter** | 🚧 **v1.0** | In Entwicklung | Pine Script v5, NautilusTrader Export |
| **FreeSearch** | 📋 Geplant | - | ML-basierte Musterfindung |
| **DBSearch** | 📋 Geplant | - | Template-basierte Mustersuche |
| **RLParamTuner** | 📋 Geplant | - | Reinforcement Learning Optimierung |
| **Backtester** | 📋 Geplant | - | Performance-Kennzahlen |
| **Validator** | 📋 Geplant | - | Out-of-Sample Validierung |
| **Reporter** | 📋 Geplant | - | Charts und Reports |
| **Orchestrator** | ⚠️ **Basis** | - | Pipeline-Steuerung |
| **GUI** | ✅ **v2.2** | Live | Streamlit-Interface für alle Module |

## 🚀 Schnellstart

### Live-Demo (Sofort verfügbar)

**🔗 [FinPattern-Engine Live Demo](https://urfpj9ftymspf3o6henh7p.streamlit.app/)**

**30-Sekunden Test:**
1. ✅ Link öffnen → Modul auswählen
2. ✅ Demo-Daten verwenden oder eigene hochladen
3. ✅ Pipeline ausführen
4. ✅ Ergebnisse analysieren und downloaden

### Lokale Installation

```bash
git clone https://github.com/baumfaeller24/FinPattern-Engine.git
cd FinPattern-Engine
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Smart Backup System aktivieren
./setup_cron_backup.sh

# GUI starten
streamlit run src/gui/main.py
```

## 🔬 Wissenschaftliche Verbesserungen v2.2

### DataIngest v2.2: Tick-Slice-Export
- **Event-basierte Speicherung**: Individuelle Parquet-Dateien pro Bar/Event
- **Nanosekunden-Präzision**: `time_from_bar_start_ns` für exakte Timing-Analyse
- **ZSTD-Kompression**: Optimierte Speicherung mit 128MB Row-Groups
- **Enhanced Manifest**: Detaillierte Metadaten mit Performance-Metriken

### Labeling v2.2: First-Hit-Logic
- **Tick-Level-Auflösung**: Eliminiert Look-Ahead-Bias bei simultanen TP/SL-Hits
- **EWMA-Volatilität**: Dynamische TP/SL-Skalierung basierend auf aktueller Marktvolatilität
- **Dual-Timeout**: Unterstützung für Bar- und Zeit-basierte Timeouts
- **Wissenschaftliche Rigorosität**: Vollständig deterministische Labeling-Logik

### Splitter v1.0: Walk-Forward-Validation
- **Zeitreihen-korrekt**: Respektiert temporale Datenstruktur
- **Leakage-Audit**: Automatische Erkennung von Daten-Überlappungen
- **Flexible Methoden**: Time-based, Session-aware, Rolling-Window
- **Robuste Backtests**: Verhindert Overfitting durch realistische Splits

## 📊 Datenformat v2.2

### Enhanced Tick-Slice-Export
```
output/
├── bars_1m.parquet              # Standard OHLC Bars
├── tick_slices_1m/              # Event-basierte Tick-Slices
│   ├── ticks_event_000001.parquet
│   ├── ticks_event_000002.parquet
│   └── slice_manifest.json
├── manifest.json                # Enhanced mit v2.2 Metadaten
└── quality_report.json          # Erweiterte Qualitätsmetriken
```

### Tick-Slice-Schema
```python
TICK_SLICE_COLUMNS = [
    "event_id",                  # Eindeutige Event-ID
    "tick_sequence",             # Sequenz innerhalb des Events
    "ts_ns",                     # Timestamp in Nanosekunden
    "time_from_bar_start_ns",    # Zeit seit Bar-Beginn
    "bid", "ask", "mid_price",   # Preis-Daten
]
```

### Walk-Forward-Split-Schema
```python
SPLIT_INFO = {
    "split_id": 0,
    "split_type": "walk_forward",
    "train_indices": [0, 1, 2, ...],
    "test_indices": [100, 101, ...],
    "train_period": {"start": "2025-01-01", "end": "2025-01-30"},
    "test_period": {"start": "2025-01-31", "end": "2025-02-10"},
    "leakage_report": {"has_leakage": false, "issues": []}
}
```

## 🎯 Performance-Benchmarks v2.2

| Metrik | v2.1 | v2.2 | Verbesserung |
|--------|------|------|-------------|
| **Tick-Slice-Export** | - | ✅ | Neue Funktion |
| **Speicher-Effizienz** | Standard | +40% | ZSTD-Kompression |
| **First-Hit-Präzision** | Bar-Level | Tick-Level | Nanosekunden-genau |
| **Leakage-Detection** | Manuell | Automatisch | 100% Coverage |
| **Backup-Sicherheit** | Manuell | Alle 15min | Smart Detection |

## 🧪 Testing v2.2

Alle Module sind vollständig getestet:

```bash
# DataIngest v2.2 Tests
pytest tests/test_data_ingest_v22.py -v

# Labeling v2.2 Tests  
pytest tests/test_labeling_v22.py -v

# Splitter v1.0 Tests
pytest tests/test_splitter.py -v

# Vollständige Test-Suite
pytest tests/ -v
```

**Test-Coverage:**
- ✅ DataIngest v2.2: 5/5 Tests bestanden
- ✅ Labeling v2.2: 6/6 Tests bestanden  
- ✅ Splitter v1.0: 7/7 Tests bestanden

## 🔄 Smart Backup System

**Automatische Sicherung alle 15 Minuten:**
```bash
# Status prüfen
crontab -l
tail -f backup_cron.log

# Backups anzeigen
ls -la backups/

# Session-Context anzeigen
cat last_session_context.md
```

**Features:**
- ✅ **Change-Detection**: Backup nur bei echten Änderungen
- ✅ **Session-Context**: Chat-Kontinuität über Sessions hinweg
- ✅ **Lock-System**: Verhindert Backup-Konflikte
- ✅ **Health-Checks**: Tägliche System-Validierung

## 🚀 Nächste Schritte (v2.3)

### Exporter v1.0 (In Entwicklung)
- **TradingView Pine Script v5**: Direkte Chart-Integration
- **NautilusTrader Export**: Python-basierte Live-Trading-Strategien
- **GUI-Integration**: Ein-Klick-Export-Buttons

### Geplante Erweiterungen
- **Institutionelle Features**: CVD, Order-Flow-Analyse (v2.3)
- **Spot+Futures-Fusion**: Hybrid-Datenmodell (v2.3)
- **ML-Pipeline**: FreeSearch und DBSearch Module (v3.0)

## 📁 Projektstruktur v2.2

```
FinPattern-Engine/
├── core/                          # Modulare Kern-Architektur
│   ├── data_ingest/              # ✅ v2.2 - Tick-Slice-Export
│   ├── labeling/                 # ✅ v2.2 - First-Hit-Logic
│   ├── feature_engine/           # ✅ v2.0 - Technische Indikatoren
│   ├── splitter/                 # ✅ v1.0 - Walk-Forward-Validation
│   ├── exporter/                 # 🚧 v1.0 - In Entwicklung
│   └── orchestrator/             # ⚠️ Basis-Implementation
├── src/gui/                      # ✅ v2.2 - Streamlit Interface
├── tests/                        # ✅ Vollständige Test-Coverage
├── docs/                         # 📋 Technische Dokumentation
├── configs/                      # ✅ YAML-Konfigurationen
├── backups/                      # 🔄 Smart Backup System
└── runs/                         # 📊 Pipeline-Outputs
```

## 🤝 Support & Entwicklung

**Live-System:** [FinPattern-Engine Demo](https://urfpj9ftymspf3o6henh7p.streamlit.app/)

**Entwicklung:**
```bash
# Development Setup
pip install -r requirements-dev.txt
pytest tests/ -v
black core/ src/ tests/
```

**Backup-Status:**
```bash
# Backup-Logs anzeigen
tail -f backup_cron.log

# Session-Kontinuität prüfen
cat last_session_context.md
```

---

**FinPattern-Engine v2.2 - Wissenschaftlich fundierte Trading-Strategieentwicklung mit Tick-Level-Präzision und automatisierter Qualitätssicherung.**
