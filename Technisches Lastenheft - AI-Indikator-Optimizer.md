# Technisches Lastenheft - AI-Indikator-Optimizer

## Projektübersicht

Entwicklung eines KI-gesteuerten Trading-Indikator-Optimierungssystems basierend auf dem multimodalen MiniCPM-4.1-8B Vision-Language Model. Das System analysiert EUR/USD Forex-Daten der letzten 14 Tage sowohl numerisch (Indikatoren) als auch visuell (Chart-Patterns) zur automatischen Generierung optimierter Pine Script Trading-Strategien. Vollständige Ausnutzung der verfügbaren Hardware-Ressourcen (Ryzen 9 9950X, RTX 5090, 192GB RAM).

## Technische Anforderungen

### Requirement 1: Multimodales Vision-Language Model Setup

**User Story:** Als Trading-Forscher möchte ich das MiniCPM-4.1-8B Vision-Language Model für multimodale Forex-Analyse fine-tunen, damit es sowohl Chart-Bilder als auch numerische Indikatoren verstehen kann.

#### Acceptance Criteria

1. WHEN das System initialisiert wird THEN SHALL es das MiniCPM-4.1-8B Model von HuggingFace laden und für Vision+Text konfigurieren

2. WHEN Model-Setup erfolgt THEN SHALL es sowohl Bildverarbeitung als auch Textgenerierung unterstützen

3. WHEN Trainingsdaten vorbereitet werden THEN SHALL das System EUR/USD Daten als Chart-Bilder UND numerische Arrays formatieren

4. WHEN Fine-Tuning startet THEN SHALL es GPU-Beschleunigung für multimodale Model-Optimierung nutzen

5. WHEN Training abgeschlossen ist THEN SHALL es die fine-getunten Gewichte für Vision- und Text-Inference speichern

### Requirement 2: Multimodale Datenaufbereitung

**User Story:** Als Trading-Forscher möchte ich EUR/USD Daten der letzten 14 Tage sowohl numerisch als auch visuell aufbereiten, damit das KI-Model umfassende Marktanalysen durchführen kann.

#### Acceptance Criteria

1. WHEN Datensammlung startet THEN SHALL das System EUR/USD 1-Minuten OHLCV-Daten für 14 Tage abrufen

2. WHEN Rohdaten vorliegen THEN SHALL es die Daten validieren und bereinigen

3. WHEN Preprocessing beginnt THEN SHALL es Standard-Indikatoren berechnen (RSI, MACD, Bollinger Bands, SMA, EMA, Stochastic, ATR, ADX)

4. WHEN Chart-Generierung erfolgt THEN SHALL es Candlestick-Charts als PNG-Bilder mit verschiedenen Zeitfenstern erstellen

5. WHEN Daten strukturiert werden THEN SHALL es sowohl numerische Arrays als auch Chart-Bilder für multimodale Eingabe vorbereiten

6. IF Datenlücken existieren THEN SHALL das System fehlende Werte interpolieren

### Requirement 3: KI-gesteuerte Multimodale Analyse

**User Story:** Als Trading-Forscher möchte ich, dass das KI-Model sowohl visuelle Chart-Patterns als auch numerische Indikatoren analysiert, um optimale Trading-Strategien zu identifizieren.

#### Acceptance Criteria

1. WHEN Analyse startet THEN SHALL das System Chart-Bilder UND Indikator-Kombinationen systematisch evaluieren

2. WHEN Parameter getestet werden THEN SHALL es Indikator-Einstellungen mittels Vision+Text-Analyse optimieren

3. WHEN visuelle Patterns erkannt werden THEN SHALL es Candlestick-Formationen, Support/Resistance und Trendlinien identifizieren

4. WHEN Kombinationen bewertet werden THEN SHALL es sowohl technische als auch visuelle Signale in die Bewertung einbeziehen

5. WHEN Optimierung abgeschlossen ist THEN SHALL es die Top 5 Strategien nach Profitabilität und visueller Bestätigung ranken

6. IF mehrere optimale Setups existieren THEN SHALL das System multimodale Konfidenz-Scores bereitstellen

### Requirement 4: Automatische Pine Script Generierung

**User Story:** Als Trading-Forscher möchte ich, dass das System automatisch Pine Script Code generiert, der sowohl numerische Indikatoren als auch visuelle Pattern-Erkennungslogik implementiert.

#### Acceptance Criteria

1. WHEN optimale Strategien identifiziert sind THEN SHALL das System validen Pine Script v5 Code generieren

2. WHEN Code generiert wird THEN SHALL es alle optimierten Indikator-Berechnungen mit exakten Parametern einschließen

3. WHEN Trading-Logik erstellt wird THEN SHALL es Entry/Exit-Bedingungen basierend auf KI-Erkenntnissen implementieren

4. WHEN visuelle Patterns integriert werden THEN SHALL es Pattern-Erkennungslogik in Pine Script übersetzen

5. WHEN Code vollständig ist THEN SHALL es Risk-Management (Stop Loss, Take Profit) einbauen

6. WHEN Script generiert ist THEN SHALL es Pine Script Syntax vor Ausgabe validieren

7. IF Syntax-Validierung fehlschlägt THEN SHALL das System automatisch Fehler korrigieren

### Requirement 5: Maximale Hardware-Ausnutzung

**User Story:** Als Trading-Forscher möchte ich die komplette Hardware-Power (Ryzen 9 9950X, RTX 5090, 192GB RAM) maximal ausnutzen, um das Experiment effizient durchzuführen.

#### Acceptance Criteria

1. WHEN Processing startet THEN SHALL das System alle 32 CPU-Kerne für Datenverarbeitung nutzen

2. WHEN Model-Training erfolgt THEN SHALL es RTX 5090 GPU-Beschleunigung für Vision+Text-Training verwenden

3. WHEN große Datasets analysiert werden THEN SHALL es bis zu 192GB RAM effizient nutzen

4. WHEN I/O-Operationen durchgeführt werden THEN SHALL es SSD-Zugriffsmuster für Samsung 9100 PRO optimieren

5. WHEN Chart-Rendering erfolgt THEN SHALL es GPU-beschleunigte Bildverarbeitung verwenden

6. IF System-Ressourcen unterausgelastet sind THEN SHALL das System parallele Verarbeitung erhöhen

### Requirement 6: Enhanced Dataset Builder und Feature Logging

**User Story:** Als Trading-Forscher möchte ich ein automatisches Dataset-Building-System mit Forward-Return-Labeling und strukturiertes Feature-Logging für ML-Training, damit ich kontinuierlich hochwertige Trainingsdaten generieren kann.

#### Acceptance Criteria

1. WHEN Bar-Daten verarbeitet werden THEN SHALL das System automatisch Forward-Return-Labels für verschiedene Horizonte generieren

2. WHEN Features extrahiert werden THEN SHALL es OHLCV-Daten, Body-Ratios, Price-Changes und technische Indikatoren berechnen

3. WHEN Labels erstellt werden THEN SHALL es diskrete Klassen (BUY/SELL/HOLD) basierend auf Forward-Returns zuweisen

4. WHEN Datasets exportiert werden THEN SHALL es Polars-DataFrames in Parquet-Format mit Kompression speichern

5. WHEN Feature-Logging aktiviert ist THEN SHALL es alle AI-Predictions mit Timestamps und Instrumenten-IDs loggen

6. WHEN Logging-Buffer voll ist THEN SHALL es automatisch in Parquet-Dateien mit konfigurierbarer Buffer-Größe flushen

7. IF Training-Daten benötigt werden THEN SHALL das System historische Feature-Logs für Model-Training bereitstellen

### Requirement 7: TorchServe Integration und Live Control

**User Story:** Als Trading-Forscher möchte ich eine produktionsreife TorchServe-Integration mit Live-Control-Funktionen, damit ich AI-Modelle dynamisch steuern und skalieren kann.

#### Acceptance Criteria

1. WHEN TorchServe-Handler initialisiert wird THEN SHALL es MiniCPM-4.1-8B für Feature-JSON-Processing konfigurieren

2. WHEN Batch-Requests verarbeitet werden THEN SHALL es sowohl einzelne als auch Listen von Feature-Dictionaries unterstützen

3. WHEN Model-Inference läuft THEN SHALL es GPU-beschleunigte Verarbeitung mit CUDA-Optimierung nutzen

4. WHEN Predictions generiert werden THEN SHALL es Confidence-Scores und Reasoning-Informationen zurückgeben

5. WHEN Live-Control aktiviert ist THEN SHALL es Redis/Kafka-Integration für Strategy-Pausierung und Parameter-Updates unterstützen

6. WHEN Environment-Konfiguration geladen wird THEN SHALL es sowohl Config-Files als auch Environment-Variables unterstützen

7. IF Model-Switching erforderlich ist THEN SHALL das System Live-Wechsel zwischen verschiedenen TorchServe-Modellen ermöglichen

### Requirement 8: Umfassendes Monitoring und Logging

**User Story:** Als Trading-Forscher möchte ich detailliertes Monitoring mit erweiterten Logging-Funktionen, um den Experiment-Fortschritt zu verfolgen und Ergebnisse zu analysieren.

#### Acceptance Criteria

1. WHEN das System läuft THEN SHALL es alle wichtigen Processing-Schritte mit Timestamps loggen

2. WHEN Model-Training erfolgt THEN SHALL es Training-Metriken und Fortschritt anzeigen

3. WHEN Optimierung läuft THEN SHALL es aktuelle Indikator-Kombinationen und visuelle Pattern-Tests zeigen

4. WHEN Ergebnisse generiert werden THEN SHALL es detaillierte Performance-Statistiken bereitstellen

5. WHEN Hardware-Auslastung gemessen wird THEN SHALL es CPU/GPU/RAM-Nutzung in Echtzeit anzeigen

6. WHEN Fehler auftreten THEN SHALL es detaillierte Error-Informationen für Debugging loggen

7. IF der Prozess unterbrochen wird THEN SHALL es Fortschritt speichern und Wiederaufnahme ermöglichen
