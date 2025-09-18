# Architektur v2.0 & Implementierungsplan

**Datum:** 17. September 2025  
**Status:** 📋 In Planung  
**Autor:** Manus AI  

---

## 1. Einleitung

Dieses Dokument beschreibt die überarbeitete Architektur (v2.0) und den detaillierten Implementierungsplan für die FinPattern-Engine, basierend auf dem kritischen Feedback von ChatGPT. Ziel ist es, das System von einem funktionalen Prototyp zu einem **production-ready Tick-Scalping System** zu transformieren, das institutionellen Standards entspricht.

---

## 2. Architektur v2.0: Kernverbesserungen

### 2.1. Einheitliches Daten-Schema

**Problem:** Inkonsistente Spaltennamen (`o,h,l,c` vs. `open,high,low,close`) zwischen den Modulen.

**Lösung:**
- **Einheitliches OHLC-Schema:** Alle Module verwenden `open, high, low, close`.
- **Schema-Mapper:** Ein robuster Mapper in jedem Modul, der verschiedene Input-Formate erkennt und standardisiert.
- **Manifest v2.0:** Das `manifest.json` wird um `schema_version`, `price_basis`, `pip_size` und `ohlc_columns` erweitert.

### 2.2. Triple-Barrier v2.0 (High/Low-Präzision)

**Problem:** Aktuelle Implementierung prüft nur auf `close`-Preis, was intra-bar Treffer verfehlt.

**Lösung:**
- **High/Low-Barriere-Prüfung:** Der Numba-Kernel wird erweitert, um `high >= tp` und `low <= sl` zu prüfen.
- **Tick-genaue First-Hit Auflösung:** Modul 1 generiert optional `tick_range.parquet` für jede Bar. Modul 2 nutzt diese Tick-Slices, um den exakten Zeitpunkt des ersten Treffers zu ermitteln.
- **Volatilitäts-skalierte Barrieren:** Take-Profit und Stop-Loss werden dynamisch an die aktuelle Marktvolatilität (EWMA) angepasst.
- **Pip-Konfiguration:** Barrieren können in Pips (`tp_pips`, `sl_pips`) definiert werden, basierend auf `pip_size` (z.B. 0.0001 für EUR/USD).
- **Side-Support:** Das Modul unterstützt `long`, `short` und `both` Positionen.

### 2.3. Feature-Engine v2.0 (Leakage-frei & Muster-spezifisch)

**Problem:** Potenzielles Look-ahead-Bias (Leakage) und fehlende Features für spezifische Trading-Muster.

**Lösung:**
- **Leakage-Audit:** Jeder Indikator wird auf kausale Korrektheit geprüft (keine zukünftigen Daten).
- **NaN-Handling:** Korrektes Handling von NaN-Werten nach dem Label-Alignment.
- **Muster-Features:**
  - **Dreieck:** Konvergenz-Maß, Bollinger-Band-Squeeze.
  - **Two-Bar-Reversal:** Engulfing-Pattern, Body-Ratio.
- **Microstructural Features:** Spread, Tick-Imbalance, Order-Flow-Proxies.
- **Session-Features:** Asia, London, NY Sessions als kategoriale Features.

### 2.4. Institutional-Grade Features (Großbank-Vorsprung)

**Ziel:** Features implementieren, die über Standard-Indikatoren hinausgehen.

**Lösung:**
- **Order-Flow Analyse:** Rekonstruktion des Order-Flows aus Tick-Daten.
- **Market-Making Indikatoren:** Bid-Ask-Spread Regime-Analyse.
- **Liquidity-Stress Detection:** Erkennung von Liquiditätsengpässen.
- **Algorithmic-Footprint Detection:** Identifizierung von algorithmischen Handelsaktivitäten.

---

## 3. Implementierungsplan (Priorisierte To-Do-Liste)

### **Phase 1: Schema-Standardisierung & Pip-Integration (2-3h)**

- **[ ] M1:** `manifest.json` um `pip_size`, `schema_version` erweitern.
- **[ ] M1:** OHLC-Standardisierung im DataIngest-Modul.
- **[ ] M2:** Schema-Mapper für verschiedene Input-Formate.
- **[ ] M2:** Pip-basierte Barrieren-Konfiguration in GUI und Core.
- **[ ] M3:** Schema-Mapper für Feature-Engine.

### **Phase 2: Triple-Barrier Überarbeitung (3-4h)**

- **[ ] M2:** Numba-Kernel für High/Low-Barriere-Prüfung erweitern.
- **[ ] M1:** Optionale `tick_range.parquet` Generierung.
- **[ ] M2:** First-Hit Auflösung mit Tick-Slices.
- **[ ] M2:** Volatilitäts-skalierte Barrieren implementieren.
- **[ ] M2:** Side-Support (long/short/both) in GUI und Core.

### **Phase 3: Feature-Engine Erweiterung (3-4h)**

- **[ ] M3:** Leakage-Audit für alle Indikatoren (Unit-Tests).
- **[ ] M3:** Muster-Features (Dreieck, Two-Bar-Reversal) implementieren.
- **[ ] M3:** Microstructural & Session-Features hinzufügen.
- **[ ] M3:** Institutional-Grade Features (Order-Flow, Market-Making).

### **Phase 4: GUI-Updates & KPI-Dashboard (2h)**

- **[ ] M1:** KPI-Dashboard in GUI fertigstellen (Gap-Coverage, Spread).
- **[ ] M1:** Run-Historie GUI nachrüsten.
- **[ ] M2:** GUI für Pip-Konfiguration und Side-Support erweitern.
- **[ ] M3:** GUI für neue Feature-Kategorien (Muster, Microstructural).

### **Phase 5: E2E-Testing & Performance-Optimierung (2h)**

- **[ ] Tests:** E2E-Testpfad mit realer EUR/USD-CSV (M1 → M2 → M3).
- **[ ] Tests:** Deterministische Artefakte prüfen (gleicher Input → gleicher Output).
- **[ ] Performance:** Alle Module auf >2,000 Bars/Sekunde optimieren.
- **[ ] Doku:** Alle neuen Features und Änderungen dokumentieren.

---

## 4. Erwartetes Ergebnis

Nach Abschluss dieses Plans wird die FinPattern-Engine ein **robustes, tick-scalping-taugliches System** sein, das:

- **Präzise Trading-Labels** generiert.
- **Leakage-freie Features** für ML-Modelle bereitstellt.
- **Institutionelle Einblicke** durch erweiterte Indikatoren bietet.
- **Vollständig getestet** und **performance-optimiert** ist.

**Das System wird bereit sein für die Entwicklung und das Backtesting von hochfrequenten Trading-Strategien für EUR/USD.**

