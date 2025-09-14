# FinPattern-Engine Architektur

## Überblick

FinPattern-Engine ist ein modulares System zur Mustererkennung in Finanzmarktdaten. Die Architektur basiert auf dem Pipeline-Pattern mit einem zentralen Orchestrator, der den Datenfluss zwischen 14 spezialisierten Modulen koordiniert.

## Architektur-Prinzipien

### 1. Modularität
- Jedes Modul hat eine klar definierte Verantwortlichkeit
- Einheitliche Schnittstelle: `run(config: Dict) -> Result`
- Module sind unabhängig testbar und austauschbar
- Lose Kopplung zwischen Modulen

### 2. Reproduzierbarkeit
- Deterministische Ergebnisse bei gleichem Seed
- Vollständige Konfigurationsversionierung
- Nachvollziehbare Datenverarbeitung
- Persistierung aller Zwischenergebnisse

### 3. Skalierbarkeit
- Effiziente Verarbeitung großer Datenmengen
- Parallelisierungsmöglichkeiten
- Speicher-optimierte Datenstrukturen
- GPU/CPU/SSD-Offloading-Unterstützung

## System-Komponenten

### Orchestrator (State Machine)
Der zentrale Controller koordiniert die Ausführung aller Module:

```python
class FinPatternOrchestrator(StateMachine):
    # States
    idle = State('Idle', initial=True)
    data_ingesting = State('DataIngesting')
    labeling = State('Labeling')
    # ... weitere States
    
    # Transitions
    start = idle.to(data_ingesting)
    ingest_complete = data_ingesting.to(labeling)
    # ... weitere Transitions
```

### Datenfluss-Pipeline

```
Raw Ticks → DataIngest → Labeling → FeatureEngine → Splitter
                                                        ↓
Reporter ← Exporter ← Validator ← Backtester ← [FreeSearch|DBSearch]
                                                        ↓
                                              RLParamTuner
```

### Module-Spezifikationen

#### 1. DataIngest
- **Zweck**: Rohdaten einlesen und normalisieren
- **Input**: CSV/Parquet Tickdaten
- **Output**: Normalisierte Bars (Zeit-/Tick-basiert)
- **Features**: Gap-Analyse, Qualitätsprüfung, Duplikat-Entfernung

#### 2. Labeling
- **Zweck**: Triple-Barrier Labels generieren
- **Input**: Bar-Daten
- **Output**: Gelabelte Bars (TP/SL/Timeout)
- **Features**: Konfigurierbare Schwellwerte, Meta-Labeling

#### 3. FeatureEngine
- **Zweck**: Technische Indikatoren berechnen
- **Input**: Bar-Daten
- **Output**: Feature-erweiterte Bars
- **Features**: 50+ Indikatoren, Custom Features, Lag-Features

#### 4. Splitter
- **Zweck**: Daten in Train/Validation/Test aufteilen
- **Input**: Feature-Daten
- **Output**: Geteilte Datensätze
- **Features**: Walk-Forward, Purged CV, Embargo

#### 5. FreeSearch
- **Zweck**: Datengetriebene Mustererkennung
- **Input**: Trainingsdaten
- **Output**: Regel-Kandidaten
- **Features**: Decision Trees, RuleFit, Random Forest

#### 6. DBSearch
- **Zweck**: Template-basierte Mustersuche
- **Input**: Trainingsdaten, Pattern-DB
- **Output**: Optimierte Regeln
- **Features**: Grid Search, Bayesian Optimization

#### 7. RLParamTuner
- **Zweck**: RL-basierte Parameteroptimierung
- **Input**: Regel-Kandidaten
- **Output**: Optimierte Parameter
- **Features**: PPO, A3C, Custom Reward Functions

#### 8. Backtester
- **Zweck**: Historische Performance-Analyse
- **Input**: Regeln, Testdaten
- **Output**: Performance-Metriken
- **Features**: Realistische Kosten, Slippage, Position Sizing

#### 9. Validator
- **Zweck**: Out-of-Sample Validierung
- **Input**: Backtest-Ergebnisse
- **Output**: Validierte Regeln
- **Features**: Robustheitstests, Overfitting-Erkennung

#### 10. Exporter
- **Zweck**: Multi-Format Export
- **Input**: Validierte Regeln
- **Output**: PineScript, CSV, JSON
- **Features**: TradingView-Integration, Custom Templates

#### 11. Reporter
- **Zweck**: Visualisierung und Reporting
- **Input**: Alle Ergebnisse
- **Output**: Charts, HTML/PDF Reports
- **Features**: Interactive Charts, Performance Analytics

#### 12. Persistence
- **Zweck**: State Management
- **Input**: Pipeline-Zustand
- **Output**: Snapshots, Resume-Fähigkeit
- **Features**: Checkpoint/Restore, Versionierung

#### 13. GUI
- **Zweck**: Benutzeroberfläche
- **Input**: User Interactions
- **Output**: Web Interface
- **Features**: Real-time Progress, Result Viewer

## Datenmodell

### Zentrale Datenstrukturen

```python
# Bar Data Schema
{
    'timestamp': datetime,
    'open': float,
    'high': float, 
    'low': float,
    'close': float,
    'volume': int,
    'bid_close': float,
    'ask_close': float
}

# Feature Data (erweitert Bar Data)
{
    # ... Bar Data fields
    'RSI_14': float,
    'SMA_50': float,
    'MACD': float,
    # ... weitere Features
}

# Label Data (erweitert Feature Data)
{
    # ... Feature Data fields
    'label_tp': bool,
    'label_sl': bool, 
    'label_timeout': bool,
    'return_forward': float
}

# Rule Schema
{
    'id': str,
    'name': str,
    'conditions': List[Dict],
    'parameters': Dict,
    'performance': Dict,
    'validation_status': str
}
```

### Konfigurationsschema

```yaml
# Global Settings
run_id: str
seed: int
log_level: str

# Module Configs
data_ingest:
  raw_data_path: str
  bar_intervals: List[Dict]
  # ...

labeling:
  method: str
  take_profit_pips: float
  # ...

# ... weitere Module
```

## Performance-Optimierungen

### Speicher-Management
- Lazy Loading großer Datensätze
- Chunked Processing für sehr große Files
- Garbage Collection zwischen Modulen
- Memory Mapping für Read-Only Daten

### Parallelisierung
- Multi-Processing für unabhängige Berechnungen
- Vectorized Operations mit NumPy/Pandas
- GPU-Acceleration für ML-Algorithmen
- Distributed Computing für sehr große Datensätze

### I/O-Optimierung
- Parquet für spaltenorientierte Speicherung
- Kompression für Archivierung
- SSD-optimierte Zugriffsmuster
- Asynchrone I/O wo möglich

## Fehlerbehandlung

### Robustheit-Strategien
- Graceful Degradation bei Fehlern
- Automatische Retry-Mechanismen
- Detaillierte Error-Logging
- Rollback-Fähigkeiten

### Monitoring
- Progress-Tracking für lange Läufe
- Resource-Monitoring (CPU, RAM, Disk)
- Performance-Metriken
- Alert-System für kritische Fehler

## Erweiterbarkeit

### Plugin-Architektur
- Neue Module über Plugin-Interface
- Custom Indikatoren
- Eigene Export-Formate
- Benutzerdefinierte Validierungsregeln

### API-Integration
- REST API für externe Tools
- Webhook-Support für Notifications
- Database-Konnektoren
- Cloud-Storage Integration
