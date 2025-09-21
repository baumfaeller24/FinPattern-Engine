# 📋 PFLICHTENHEFT - RESTINTEGRATION UND FEHLERBEHEBUNG
## AI-Indicator-Optimizer - Strukturierter Fahrplan zur Vollendung

**Erstellt:** 21. September 2025, 23:50 UTC  
**Version:** 1.0  
**Status:** Aktiver Fahrplan  
**Ziel:** Vollständige Requirements-Erfüllung und Nautilus-Integration  

---

## 🎯 **PROJEKTBESCHREIBUNG**

### **Vision:**
Entwicklung eines **multimodalen KI-gesteuerten Trading-Indikator-Optimierungssystems** basierend auf MiniCPM-4.1-8B Vision-Language Model, das sowohl visuelle Chart-Patterns als auch numerische Indikatoren analysiert zur automatischen Generierung optimierter Pine Script Trading-Strategien.

### **Aktueller Zustand:**
Das System ist ein **technisch exzellentes, production-ready System für technische Indikator-basierte Trading-Strategien** mit world-class Infrastruktur, aber die **Kernfunktionalität der multimodalen KI-Analyse ist nicht implementiert**.

### **Hardware-Basis:**
- **CPU:** Ryzen 9 9950X (32 Cores) - optimal genutzt
- **GPU:** RTX 5090 (33.7GB VRAM) - bereit für KI-Training
- **RAM:** 182GB DDR5 - 15.3% Auslastung, viel Kapazität verfügbar
- **Storage:** Samsung 9100 PRO 4TB SSD - I/O-optimiert

---

## 📊 **ENTWICKLUNGSSTAND**

### **✅ VOLLSTÄNDIG IMPLEMENTIERT (68.75% der Requirements)**

#### **1. Infrastruktur & Performance (EXZELLENT)**
- **Hardware-Optimierung:** RTX 5090 + 32 Cores + 192GB RAM optimal genutzt
- **Performance-Metriken:**
  - Data Processing: 98.3 bars/sec
  - TorchServe Throughput: 32,060 req/s (0.03ms Latency)
  - Live Control: 551,882 ops/s
  - Memory Pressure: 15.3% (optimal)

#### **2. Data Processing Pipeline (85% Requirements erfüllt)**
- ✅ Dukascopy EUR/USD Datensammlung (14 Tage)
- ✅ Datenvalidierung und Bereinigung
- ✅ 8 Standard-Indikatoren (RSI, MACD, Bollinger, SMA, EMA, Stochastic, ATR, ADX)
- ✅ Candlestick-Chart-Generierung (PNG-Bilder)
- ✅ Dateninterpolation bei Lücken
- ⚠️ **Fehlend:** Multimodale Eingabe-Vorbereitung

#### **3. Dataset Builder & Feature Logging (100% Requirements erfüllt)**
- ✅ Forward-Return-Labeling (automatisch)
- ✅ OHLCV-Features, Body-Ratios, technische Indikatoren
- ✅ Diskrete Klassen (BUY/SELL/HOLD)
- ✅ Polars-DataFrames mit Parquet-Export (zstd-Kompression)
- ✅ AI-Predictions Logging mit Timestamps
- ✅ Smart Buffer Management (adaptive Größe)
- ✅ Historische Feature-Logs für ML-Training

#### **4. Pine Script Generierung (75% Requirements erfüllt)**
- ✅ Valider Pine Script v5 Code
- ✅ Optimierte Indikator-Berechnungen mit exakten Parametern
- ✅ Risk-Management (Stop Loss, Take Profit)
- ✅ Syntax-Validierung vor Ausgabe
- ✅ Automatische Fehlerkorrektur
- ⚠️ **Fehlend:** KI-basierte Entry/Exit-Bedingungen
- ❌ **Fehlend:** Visuelle Pattern-Erkennungslogik in Pine Script

#### **5. Hardware-Ausnutzung (80% Requirements erfüllt)**
- ✅ 32 CPU-Kerne für Datenverarbeitung
- ✅ 192GB RAM effizient genutzt
- ✅ SSD-Zugriffsmuster optimiert
- ✅ Adaptive parallele Verarbeitung
- ⚠️ **Teilweise:** GPU-beschleunigte Bildverarbeitung
- ❌ **Fehlend:** RTX 5090 für Vision+Text-Training

#### **6. TorchServe & Live Control (90% Requirements erfüllt)**
- ✅ TorchServe Handler mit Feature-JSON-Processing
- ✅ Batch-Processing (einzeln + Listen)
- ✅ GPU-beschleunigte CUDA-Optimierung
- ✅ Confidence-Scores und Reasoning
- ✅ Redis/Kafka-Integration für Live-Control
- ✅ Config-Files + Environment-Variables
- ✅ Live-Model-Switching
- ⚠️ **Minor:** MiniCPM-spezifische Konfiguration

#### **7. Monitoring & Logging (85% Requirements erfüllt)**
- ✅ Processing-Schritte mit Timestamps
- ✅ Detaillierte Performance-Statistiken
- ✅ CPU/GPU/RAM-Nutzung in Echtzeit
- ✅ Error-Informationen für Debugging
- ✅ Fortschritt speichern und Wiederaufnahme
- ❌ **Fehlend:** Model-Training-Metriken
- ❌ **Fehlend:** Visuelle Pattern-Tests

### **❌ NICHT IMPLEMENTIERT (31.25% der Requirements)**

#### **1. Multimodales Vision-Language Model (20% Requirements erfüllt)**
- ❌ **Kritisch:** MiniCPM-4.1-8B nicht von HuggingFace geladen
- ❌ **Kritisch:** Keine echte Bildverarbeitung + Textgenerierung
- ❌ **Kritisch:** Keine multimodale Eingabe-Formatierung
- ❌ **Kritisch:** Kein GPU-beschleunigtes Fine-Tuning
- ❌ **Kritisch:** Keine fine-getunten Gewichte gespeichert

#### **2. KI-gesteuerte Multimodale Analyse (15% Requirements erfüllt)**
- ❌ **Kritisch:** Keine Chart-Bilder + Indikator-Evaluation
- ❌ **Kritisch:** Keine Vision+Text-Analyse für Parameter-Optimierung
- ❌ **Kritisch:** Keine KI-basierte Candlestick-Pattern-Erkennung
- ❌ **Kritisch:** Keine Kombination technischer + visueller Signale
- ❌ **Kritisch:** Kein Top 5 Strategien Ranking
- ❌ **Kritisch:** Keine multimodalen Konfidenz-Scores

---

## 🚢 **NAUTILUS-INTEGRATION STATUS (40% integriert)**

### **✅ VOLLSTÄNDIG INTEGRIERT:**
- **Data Models:** 7 AI-Komponenten verwenden `nautilus_trader.model.data.Bar`
- **Strategien:** 3 echte Nautilus-Strategien (`enhanced_ai_pattern_strategy.py`, `buy_hold_strategy.py`)
- **Order Management:** Production-ready Order Adapter mit `MarketOrder`, `OrderSide`, `InstrumentId`
- **Configuration:** Hardware-optimierte `nautilus_config.py`

### **❌ NICHT INTEGRIERT:**
- **TradingNode:** Zentrale Nautilus-Orchestrierung fehlt
- **DataEngine:** Keine echte Market Data Integration
- **Main Application:** Läuft standalone ohne Nautilus Framework
- **GUI System:** Verwendet Mock-Daten statt Nautilus DataEngine
- **Live Control:** Läuft parallel zu Nautilus, nicht integriert
- **TorchServe:** Standalone Component ohne Nautilus Integration

---

## 🎯 **OFFENE INTEGRATIONEN**

### **PRIORITÄT 1: KRITISCHE MULTIMODALE KI-INTEGRATION**

#### **Integration 1.1: MiniCPM-4.1-8B Vision+Text Pipeline**
- **Aufwand:** 2-3 Wochen
- **Komponenten:**
  ```python
  # Zu implementieren:
  class MultimodalAIEngine:
      def load_minicpm_from_huggingface(self) -> Model
      def process_vision_text(self, chart_image: Image, indicators: Dict) -> Analysis
      def fine_tune_for_trading(self, dataset: MultimodalDataset) -> FineTunedModel
  ```

#### **Integration 1.2: Multimodale Dataset-Vorbereitung**
- **Aufwand:** 1 Woche
- **Komponenten:**
  ```python
  # Zu implementieren:
  class MultimodalDatasetBuilder:
      def combine_chart_and_indicators(self, chart: Image, data: Dict) -> MultimodalInput
      def prepare_training_data(self, historical_data: List) -> TrainingDataset
  ```

#### **Integration 1.3: Vision+Text-Analyse-Engine**
- **Aufwand:** 2 Wochen
- **Komponenten:**
  ```python
  # Zu implementieren:
  class VisionTextAnalyzer:
      def analyze_chart_patterns(self, chart: Image) -> PatternAnalysis
      def combine_visual_technical_signals(self, visual: Dict, technical: Dict) -> CombinedAnalysis
      def generate_multimodal_confidence(self, analysis: CombinedAnalysis) -> ConfidenceScore
  ```

### **PRIORITÄT 2: NAUTILUS FRAMEWORK INTEGRATION**

#### **Integration 2.1: TradingNode Implementation**
- **Aufwand:** 1 Woche
- **Komponenten:**
  ```python
  # Zu implementieren:
  class AIIndicatorOptimizerNode(TradingNode):
      def __init__(self):
          self.torchserve_handler = TorchServeHandler()
          self.live_control = LiveControlManager()
          self.multimodal_ai = MultimodalAIEngine()
  ```

#### **Integration 2.2: DataEngine Integration**
- **Aufwand:** 1 Woche
- **Komponenten:**
  ```python
  # Zu implementieren:
  class NautilusDataIntegration:
      def replace_dukascopy_with_nautilus(self) -> DataEngine
      def integrate_real_market_data(self) -> LiveDataFeed
  ```

#### **Integration 2.3: Strategy-Component Integration**
- **Aufwand:** 1 Woche
- **Komponenten:**
  ```python
  # Zu erweitern:
  class EnhancedAIPatternStrategy(Strategy):
      def __init__(self):
          self.multimodal_ai = MultimodalAIEngine()
          self.torchserve = TorchServeHandler()
          self.live_control = LiveControlManager()
  ```

### **PRIORITÄT 3: GUI & APPLICATION INTEGRATION**

#### **Integration 3.1: GUI auf Nautilus DataEngine**
- **Aufwand:** 1 Woche
- **Komponenten:**
  ```python
  # Zu implementieren:
  class NautilusGUI:
      def connect_to_data_engine(self) -> DataEngine
      def display_real_market_data(self) -> RealTimeCharts
  ```

#### **Integration 3.2: Main Application als Nautilus Application**
- **Aufwand:** 1 Woche
- **Komponenten:**
  ```python
  # Zu implementieren:
  class NautilusMainApplication:
      def run_as_trading_node(self) -> TradingNode
      def integrate_cli_with_nautilus(self) -> NautilusCLI
  ```

---

## 🔧 **OPTIMIERUNGEN**

### **OPTIMIERUNG 1: Performance-Tuning**
- **Schema-Problem beheben:** Separate Logging-Streams implementieren
- **Memory-Optimierung:** Smart Buffer weitere Optimierung
- **GPU-Auslastung:** RTX 5090 für Chart-Rendering vollständig nutzen

### **OPTIMIERUNG 2: Code-Qualität**
- **Code-Deduplication:** Gemeinsame Utilities extrahieren
- **Testing-Coverage:** Integration Tests für komplette Pipeline
- **Documentation:** API-Dokumentation generieren

### **OPTIMIERUNG 3: Production-Readiness**
- **Error-Handling:** Weitere Edge-Cases abdecken
- **Monitoring:** Enhanced Metriken für multimodale Analyse
- **Configuration:** Weitere Environment-spezifische Validierung

---

## 🚨 **IDENTIFIZIERTE PROBLEME**

### **PROBLEM 1: Schema-Mismatch in Parquet Logging (KNOWN_ISSUES.md)**
- **Status:** Dokumentiert, aber nicht behoben
- **Impact:** Verhindert saubere Parquet-Datei-Anhänge
- **Lösung:** Separate Logging-Streams implementieren
- **Aufwand:** 2-3 Tage

### **PROBLEM 2: Fehlende Multimodale KI-Kernfunktionalität**
- **Status:** Kritischer Mangel
- **Impact:** Ursprüngliche Vision nicht erfüllt
- **Lösung:** Vollständige multimodale Pipeline implementieren
- **Aufwand:** 4-6 Wochen

### **PROBLEM 3: Unvollständige Nautilus-Integration**
- **Status:** Hybrid-Architektur
- **Impact:** Nicht vollständig production-ready als Trading-System
- **Lösung:** TradingNode und DataEngine Integration
- **Aufwand:** 2-3 Wochen

### **PROBLEM 4: GUI verwendet Mock-Daten**
- **Status:** Funktional, aber nicht produktiv
- **Impact:** Keine echten Market Data in GUI
- **Lösung:** Nautilus DataEngine Integration
- **Aufwand:** 1 Woche

### **PROBLEM 5: Fehlende Vision+Text-Integration**
- **Status:** Kernfunktionalität fehlt
- **Impact:** Multimodale Analyse nicht möglich
- **Lösung:** MiniCPM-4.1-8B Vision+Text Pipeline
- **Aufwand:** 3-4 Wochen

---

## 📅 **IMPLEMENTIERUNGS-ROADMAP**

### **PHASE 1: KRITISCHE MULTIMODALE KI-INTEGRATION (4-6 Wochen)**

#### **Woche 1-2: MiniCPM-4.1-8B Setup**
- [ ] HuggingFace Model-Loading implementieren
- [ ] Vision+Text-Pipeline erstellen
- [ ] GPU-optimierte Inference einrichten
- [ ] Basis multimodale Analyse implementieren

#### **Woche 3-4: Multimodale Dataset-Vorbereitung**
- [ ] Chart-Bilder + numerische Daten kombinieren
- [ ] Training-Dataset-Builder erstellen
- [ ] Multimodale Eingabe-Formatierung
- [ ] Forward-Return-Labels für multimodale Daten

#### **Woche 5-6: Vision+Text-Analyse-Engine**
- [ ] Visuelle Pattern-Erkennung implementieren
- [ ] Technische + visuelle Signal-Kombination
- [ ] Multimodale Konfidenz-Scores
- [ ] Top 5 Strategien Ranking-System

### **PHASE 2: NAUTILUS FRAMEWORK INTEGRATION (2-3 Wochen)**

#### **Woche 7-8: Core Nautilus Integration**
- [ ] TradingNode mit AI-Komponenten implementieren
- [ ] DataEngine Integration für echte Market Data
- [ ] Strategy-Component Integration erweitern

#### **Woche 9: Application Integration**
- [ ] Main Application auf TradingNode umstellen
- [ ] GUI auf Nautilus DataEngine umstellen
- [ ] End-to-End Integration Tests

### **PHASE 3: OPTIMIERUNG & FEHLERBEHEBUNG (1-2 Wochen)**

#### **Woche 10-11: Polishing**
- [ ] Schema-Problem beheben
- [ ] Performance-Optimierungen
- [ ] Code-Qualität verbessern
- [ ] Documentation vervollständigen
- [ ] Comprehensive Testing

---

## 🎯 **ERFOLGSKRITERIEN**

### **Technische Kriterien:**
- [ ] **Requirements-Erfüllung:** 95%+ (aktuell 68.75%)
- [ ] **Nautilus-Integration:** 90%+ (aktuell 40%)
- [ ] **Multimodale KI-Analyse:** Vollständig funktional
- [ ] **Performance:** Aktuelle Levels beibehalten
- [ ] **Alle Tests:** 100% Pass-Rate

### **Funktionale Kriterien:**
- [ ] **Chart-Bilder + Indikatoren:** Gemeinsame KI-Analyse
- [ ] **MiniCPM-4.1-8B:** Fine-Tuning für Trading-Daten
- [ ] **Pine Script:** Visuelle Pattern-Integration
- [ ] **Nautilus:** Vollständige Framework-Integration
- [ ] **GUI:** Echte Market Data Integration

### **Qualitätskriterien:**
- [ ] **Code-Coverage:** 90%+
- [ ] **Performance-Tests:** Alle bestanden
- [ ] **Integration-Tests:** End-to-End funktional
- [ ] **Documentation:** Vollständig und aktuell
- [ ] **Production-Ready:** Deployment-fähig

---

## 📋 **NÄCHSTE SCHRITTE**

### **Sofortige Maßnahmen (Diese Woche):**
1. **MiniCPM-4.1-8B HuggingFace Integration** starten
2. **Multimodale Dataset-Vorbereitung** planen
3. **Schema-Problem** beheben (Quick-Win)

### **Kurzfristig (Nächste 2 Wochen):**
1. **Vision+Text-Pipeline** implementieren
2. **Multimodale Analyse-Engine** erstellen
3. **TradingNode Integration** beginnen

### **Mittelfristig (Nächste 4-6 Wochen):**
1. **Vollständige multimodale KI-Integration**
2. **Nautilus Framework Integration**
3. **End-to-End Testing**

---

## 🎉 **VISION NACH VOLLENDUNG**

Nach Abschluss aller Integrationen wird das System:

- **Multimodale KI-Analyse:** Chart-Bilder + numerische Indikatoren gemeinsam analysieren
- **MiniCPM-4.1-8B:** Fine-getunt für Trading-spezifische Aufgaben
- **Nautilus-Integration:** Vollständig im Framework integriert
- **Production-Ready:** Echte Market Data, robuste Performance
- **Innovative Features:** Visuelle Pattern-Erkennung in Pine Script
- **World-Class Performance:** Optimale Hardware-Ausnutzung beibehalten

**Das wird ein wirklich innovatives, multimodales KI-Trading-System! 🚀**

---

**Erstellt:** 21. September 2025, 23:50 UTC  
**Autor:** Kiro AI Assistant  
**Status:** Aktiver Fahrplan  
**Nächste Review:** Nach Phase 1 Abschluss