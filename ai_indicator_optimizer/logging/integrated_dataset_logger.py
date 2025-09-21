#!/usr/bin/env python3
"""
Integrated Dataset Logger - Task 16 Implementation
Integration zwischen BarDatasetBuilder und Enhanced Feature Logging

Features:
- Seamless Integration zwischen Dataset Building und Logging
- Smart Buffer Management mit Groks Algorithmus
- Automatic Parquet Export mit Kompression
- Performance-optimierte Polars-Integration
- Real-time Feature + Prediction Logging
"""

import polars as pl
import time
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from pathlib import Path

from .smart_buffer_manager import SmartBufferManager, EnhancedBufferLogger
from .feature_prediction_logger import FeaturePredictionLogger
from ..dataset.bar_dataset_builder import BarDatasetBuilder


class IntegratedDatasetLogger:
    """
    Task 16 Implementation: Integrated Dataset + Feature + Prediction Logger
    
    Kombiniert:
    - BarDatasetBuilder (Task 6) für ML-Dataset-Generierung
    - FeaturePredictionLogger für AI-Prediction-Tracking
    - SmartBufferManager (Groks Empfehlung) für optimale Performance
    
    SCHEMA-CONSISTENCY: Verwendet Fixed Schema für konsistente Parquet-Files
    """
    
    # FIXED SCHEMA DEFINITION für konsistente Parquet-Files
    FIXED_FEATURE_SCHEMA = [
        # OHLCV Basis-Features
        "open", "high", "low", "close", "volume", "ts_event", "ts_init",
        # Technische Indikatoren
        "sma_5", "price_change", "volatility",
        # Candlestick-Features
        "price_range", "body_size", "upper_shadow", "lower_shadow", "is_bullish",
        # Zusätzliche Features
        "rsi", "mock_macd", "volume_sma", "test_feature"
    ]
    
    def __init__(
        self,
        output_base_path: str = "logs/integrated",
        dataset_horizon: int = 5,
        buffer_size: int = 5000,
        compression: str = "zstd",
        enable_smart_buffering: bool = True,
        logger: Optional[Callable[[str], None]] = None
    ):
        """
        Initialize Integrated Dataset Logger
        
        Args:
            output_base_path: Basis-Pfad für alle Output-Dateien
            dataset_horizon: Forward-Return-Horizont für Dataset Builder
            buffer_size: Initial Buffer-Größe
            compression: Parquet-Kompression
            enable_smart_buffering: Ob Groks Smart Buffer Management verwendet werden soll
            logger: Optional Logger-Funktion
        """
        self.output_base = Path(output_base_path)
        self.output_base.mkdir(parents=True, exist_ok=True)
        
        # Components
        self.dataset_builder = BarDatasetBuilder(
            horizon=dataset_horizon,
            min_bars=10,
            include_technical_indicators=True
        )
        
        # Feature + Prediction Logger mit Smart Buffering
        if enable_smart_buffering:
            self.feature_logger = self._create_smart_feature_logger(buffer_size, compression)
        else:
            self.feature_logger = FeaturePredictionLogger(
                output_path=str(self.output_base / "features.parquet"),
                buffer_size=buffer_size,
                compression=compression
            )
        
        # Dataset Export Logger (separate für ML-Training-Datasets)
        self.dataset_logger = FeaturePredictionLogger(
            output_path=str(self.output_base / "ml_dataset.parquet"),
            buffer_size=buffer_size // 2,  # Kleinerer Buffer für Dataset
            compression=compression
        )
        
        # Performance Tracking
        self.total_bars_processed = 0
        self.total_predictions_logged = 0
        self.total_dataset_entries = 0
        self.start_time = time.time()
        
        # Logging
        self._log = logger or (lambda msg: logging.getLogger(__name__).info(msg))
        self._log(f"IntegratedDatasetLogger initialized: {output_base_path}")
    
    def _create_smart_feature_logger(self, buffer_size: int, compression: str) -> EnhancedBufferLogger:
        """
        Erstelle Enhanced Feature Logger mit Groks Smart Buffer Management
        """
        from .smart_buffer_manager import create_smart_feature_logger
        
        return create_smart_feature_logger(
            output_path=str(self.output_base / "smart_features.parquet"),
            initial_buffer_size=buffer_size,
            rotating=True  # Tägliche Rotation für bessere Organisation
        )
    
    def process_bar_with_prediction(
        self,
        bar,  # Nautilus Bar object
        ai_prediction: Dict[str, Any],
        additional_features: Optional[Dict[str, Any]] = None,
        confidence_score: Optional[float] = None,
        risk_score: Optional[float] = None,
        market_regime: Optional[str] = None
    ) -> None:
        """
        Hauptfunktion: Verarbeite Bar mit AI-Prediction
        
        Führt aus:
        1. Bar-Processing durch BarDatasetBuilder
        2. Feature-Extraktion und -Logging
        3. AI-Prediction-Logging
        4. Smart Buffer Management
        
        Args:
            bar: Nautilus Bar-Objekt
            ai_prediction: AI-Prediction Dictionary
            additional_features: Zusätzliche Features (optional)
            confidence_score: Enhanced Confidence Score
            risk_score: Risk Assessment Score
            market_regime: Detected Market Regime
        """
        try:
            # 1. Process Bar durch Dataset Builder
            self.dataset_builder.on_bar(bar)
            self.total_bars_processed += 1
            
            # 2. Extrahiere Features für Logging
            features = self._extract_features_from_bar(bar, additional_features)
            
            # 3. Log Features + Prediction
            self._log_feature_prediction(
                bar=bar,
                features=features,
                prediction=ai_prediction,
                confidence_score=confidence_score,
                risk_score=risk_score,
                market_regime=market_regime
            )
            
            # 4. Export Dataset-Entries wenn verfügbar
            self._export_dataset_entries()
            
            # 5. Performance Logging (alle 1000 Bars)
            if self.total_bars_processed % 1000 == 0:
                self._log_performance_stats()
        
        except Exception as e:
            self._log(f"Error processing bar with prediction: {e}")
    
    def _extract_features_from_bar(
        self, 
        bar, 
        additional_features: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extrahiere Features aus Bar für Logging mit FIXED SCHEMA
        """
        import numpy as np  # Import hier hinzufügen
        
        # FIXED SCHEMA: Basis OHLCV Features (immer vorhanden)
        features = {
            "open": float(bar.open),
            "high": float(bar.high),
            "low": float(bar.low),
            "close": float(bar.close),
            "volume": float(bar.volume),
            "ts_event": int(bar.ts_event),
            "ts_init": int(bar.ts_init)
        }
        
        # FIXED SCHEMA: Technische Indikatoren (immer vorhanden, mit Default-Werten)
        prices = list(self.dataset_builder.price_history) if self.dataset_builder.price_history else []
        
        # SMA_5 (Simple Moving Average 5)
        if len(prices) >= 5:
            features["sma_5"] = sum(prices[-5:]) / 5
        else:
            features["sma_5"] = float(bar.close)  # Fallback: aktueller Preis
        
        # Price Change
        if len(prices) >= 2:
            features["price_change"] = (prices[-1] - prices[-2]) / prices[-2]
        else:
            features["price_change"] = 0.0  # Default: keine Änderung
        
        # Volatility (Standard Deviation)
        if len(prices) >= 10:
            features["volatility"] = float(np.std(prices[-10:]))
        elif len(prices) >= 2:
            features["volatility"] = float(np.std(prices))  # Verwende alle verfügbaren Preise
        else:
            features["volatility"] = 0.0  # Default: keine Volatilität
        
        # FIXED SCHEMA: Zusätzliche Standard-Features (immer vorhanden)
        features.update({
            "price_range": float(bar.high) - float(bar.low),
            "body_size": abs(float(bar.close) - float(bar.open)),
            "upper_shadow": float(bar.high) - max(float(bar.open), float(bar.close)),
            "lower_shadow": min(float(bar.open), float(bar.close)) - float(bar.low),
            "is_bullish": 1 if float(bar.close) > float(bar.open) else 0
        })
        
        # FIXED SCHEMA: Additional Features (mit Default-Werten)
        if additional_features:
            # Definiere erwartete zusätzliche Features mit Defaults
            expected_additional = {
                "rsi": 50.0,
                "mock_macd": 0.0,
                "volume_sma": float(bar.volume),
                "test_feature": 0.0
            }
            
            # Update mit tatsächlichen Werten, behalte Defaults für fehlende
            for key, default_value in expected_additional.items():
                features[key] = additional_features.get(key, default_value)
        else:
            # Füge Default-Werte hinzu wenn keine additional_features
            features.update({
                "rsi": 50.0,
                "mock_macd": 0.0,
                "volume_sma": float(bar.volume),
                "test_feature": 0.0
            })
        
        return features
    
    def _validate_and_normalize_features(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validiere und normalisiere Features für konsistentes Schema
        """
        normalized_features = {}
        
        # Stelle sicher, dass alle erwarteten Features vorhanden sind
        for field in self.FIXED_FEATURE_SCHEMA:
            if field in features:
                normalized_features[field] = features[field]
            else:
                # Default-Werte für fehlende Features
                if field in ["open", "high", "low", "close"]:
                    normalized_features[field] = 1.0  # Default Preis
                elif field in ["volume", "ts_event", "ts_init"]:
                    normalized_features[field] = 0
                elif field in ["sma_5", "price_change", "volatility", "price_range", "body_size", 
                              "upper_shadow", "lower_shadow", "rsi", "mock_macd", "volume_sma", "test_feature"]:
                    normalized_features[field] = 0.0
                elif field == "is_bullish":
                    normalized_features[field] = 0
                else:
                    normalized_features[field] = 0.0
        
        return normalized_features
    
    def _log_feature_prediction(
        self,
        bar,
        features: Dict[str, Any],
        prediction: Dict[str, Any],
        confidence_score: Optional[float] = None,
        risk_score: Optional[float] = None,
        market_regime: Optional[str] = None
    ) -> None:
        """
        Log Features + Prediction mit Smart Buffer Management und Schema-Validierung
        """
        # Schema-Validierung und Normalisierung
        normalized_features = self._validate_and_normalize_features(features)
        
        # Timestamp für Logging
        ts_ns = int(bar.ts_event)
        instrument = str(bar.instrument_id)
        
        # Log über Feature Logger (mit Smart Buffering)
        if hasattr(self.feature_logger, 'log'):
            # Enhanced Buffer Logger
            self.feature_logger.log(
                ts_ns=ts_ns,
                instrument=instrument,
                features=normalized_features,  # Verwende normalisierte Features
                prediction=prediction,
                confidence_score=confidence_score,
                risk_score=risk_score,
                market_regime=market_regime
            )
        else:
            # Standard Feature Logger
            self.feature_logger.log(
                ts_ns=ts_ns,
                instrument=instrument,
                features=normalized_features,  # Verwende normalisierte Features
                prediction=prediction,
                confidence_score=confidence_score,
                risk_score=risk_score,
                market_regime=market_regime
            )
        
        self.total_predictions_logged += 1
    
    def _export_dataset_entries(self) -> None:
        """
        Export neue Dataset-Entries aus BarDatasetBuilder
        """
        # Check ob neue Dataset-Entries verfügbar sind
        if hasattr(self.dataset_builder, 'rows') and self.dataset_builder.rows:
            new_entries = len(self.dataset_builder.rows) - self.total_dataset_entries
            
            if new_entries > 0:
                # Export neue Entries
                for i in range(self.total_dataset_entries, len(self.dataset_builder.rows)):
                    entry = self.dataset_builder.rows[i]
                    
                    # Log als Dataset-Entry
                    self.dataset_logger.log(
                        ts_ns=entry.get("ts_ns", int(time.time() * 1e9)),
                        instrument=entry.get("instrument", "EUR/USD"),
                        features=entry,
                        prediction={"action": entry.get("label", "HOLD"), "confidence": 1.0, "reasoning": "dataset_label"}
                    )
                
                self.total_dataset_entries = len(self.dataset_builder.rows)
    
    def _log_performance_stats(self) -> None:
        """
        Log Performance-Statistiken
        """
        elapsed = time.time() - self.start_time
        bars_per_sec = self.total_bars_processed / elapsed if elapsed > 0 else 0
        
        stats = {
            "bars_processed": self.total_bars_processed,
            "predictions_logged": self.total_predictions_logged,
            "dataset_entries": self.total_dataset_entries,
            "elapsed_time": elapsed,
            "bars_per_second": bars_per_sec
        }
        
        # Smart Buffer Metrics (falls verfügbar)
        if hasattr(self.feature_logger, 'get_smart_metrics'):
            smart_metrics = self.feature_logger.get_smart_metrics()
            stats["smart_buffer"] = smart_metrics["smart_buffer"]
        
        self._log(f"Performance Stats: {stats}")
    
    def flush_all(self) -> None:
        """
        Flush alle Buffer
        """
        try:
            self.feature_logger.flush() if hasattr(self.feature_logger, 'flush') else None
            self.dataset_logger.flush()
            self._log("All buffers flushed successfully")
        except Exception as e:
            self._log(f"Error flushing buffers: {e}")
    
    def export_final_dataset(self, output_path: Optional[str] = None) -> str:
        """
        Export finales ML-Training-Dataset
        
        Returns:
            str: Pfad zur exportierten Datei
        """
        if not output_path:
            output_path = str(self.output_base / f"final_dataset_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet")
        
        try:
            # Flush alle Buffer
            self.flush_all()
            
            # Export Dataset Builder Rows
            if self.dataset_builder.rows:
                df = pl.DataFrame(self.dataset_builder.rows)
                df.write_parquet(output_path, compression="zstd")
                
                self._log(f"Final dataset exported: {output_path} ({len(df)} entries)")
                return output_path
            else:
                self._log("No dataset entries to export")
                return ""
        
        except Exception as e:
            self._log(f"Error exporting final dataset: {e}")
            return ""
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """
        Erhalte umfassende Statistiken
        """
        elapsed = time.time() - self.start_time
        
        stats = {
            "processing": {
                "bars_processed": self.total_bars_processed,
                "predictions_logged": self.total_predictions_logged,
                "dataset_entries": self.total_dataset_entries,
                "elapsed_time": elapsed,
                "bars_per_second": self.total_bars_processed / elapsed if elapsed > 0 else 0
            },
            "feature_logger": self.feature_logger.get_stats() if hasattr(self.feature_logger, 'get_stats') else {},
            "dataset_logger": self.dataset_logger.get_stats(),
            "output_paths": {
                "base_path": str(self.output_base),
                "features": str(self.output_base / "smart_features.parquet"),
                "dataset": str(self.output_base / "ml_dataset.parquet")
            }
        }
        
        # Smart Buffer Metrics (falls verfügbar)
        if hasattr(self.feature_logger, 'get_smart_metrics'):
            stats["smart_buffer"] = self.feature_logger.get_smart_metrics()
        
        return stats
    
    def close(self) -> None:
        """
        Schließe Integrated Logger
        """
        try:
            # Final flush
            self.flush_all()
            
            # Close components
            if hasattr(self.feature_logger, 'close'):
                self.feature_logger.close()
            self.dataset_logger.close()
            
            # Log final stats
            final_stats = self.get_comprehensive_stats()
            self._log(f"IntegratedDatasetLogger closed. Final stats: {final_stats}")
        
        except Exception as e:
            self._log(f"Error closing IntegratedDatasetLogger: {e}")
    
    def __enter__(self):
        """Context Manager Support"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context Manager Support"""
        self.close()


# Factory Function für einfache Nutzung
def create_integrated_logger(
    output_base_path: str = "logs/integrated",
    dataset_horizon: int = 5,
    buffer_size: int = 5000,
    enable_smart_buffering: bool = True,
    **kwargs
) -> IntegratedDatasetLogger:
    """
    Factory Function für Integrated Dataset Logger
    
    Args:
        output_base_path: Basis-Pfad für Output
        dataset_horizon: Forward-Return-Horizont
        buffer_size: Initial Buffer-Größe
        enable_smart_buffering: Groks Smart Buffer Management
    
    Returns:
        IntegratedDatasetLogger Instance
    """
    return IntegratedDatasetLogger(
        output_base_path=output_base_path,
        dataset_horizon=dataset_horizon,
        buffer_size=buffer_size,
        enable_smart_buffering=enable_smart_buffering,
        **kwargs
    )


if __name__ == "__main__":
    # Test Integrated Dataset Logger
    import numpy as np
    from datetime import datetime, timezone
    
    print("🧪 Testing IntegratedDatasetLogger...")
    
    # Mock Bar class für Testing
    class MockBar:
        def __init__(self, open_price, high, low, close, volume, ts):
            self.open = open_price
            self.high = high
            self.low = low
            self.close = close
            self.volume = volume
            self.ts_event = ts
            self.ts_init = ts
            self.instrument_id = "EUR/USD"
    
    with create_integrated_logger("test_logs/integrated", buffer_size=5) as logger:
        # Test mit Mock-Daten
        base_price = 1.1000
        
        for i in range(20):
            # Generiere Mock Bar
            price_change = np.random.normal(0, 0.0001)
            open_price = base_price + price_change
            high = open_price + abs(np.random.normal(0, 0.0002))
            low = open_price - abs(np.random.normal(0, 0.0002))
            close = open_price + np.random.normal(0, 0.0001)
            volume = np.random.randint(1000, 5000)
            ts = int((datetime.now(timezone.utc).timestamp() + i) * 1e9)
            
            bar = MockBar(open_price, high, low, close, volume, ts)
            
            # Mock AI Prediction
            prediction = {
                "action": ["BUY", "SELL", "HOLD"][i % 3],
                "confidence": 0.7 + (i % 10) * 0.02,
                "reasoning": f"test_prediction_{i}"
            }
            
            # Process Bar mit Prediction
            logger.process_bar_with_prediction(
                bar=bar,
                ai_prediction=prediction,
                additional_features={"test_feature": i * 0.1},
                confidence_score=0.8 + (i % 5) * 0.02,
                risk_score=0.1 + (i % 3) * 0.05,
                market_regime="trending" if i % 2 == 0 else "ranging"
            )
            
            base_price = close
            
            if i % 5 == 0:
                print(f"  Processed {i+1} bars...")
    
    # Zeige finale Statistiken
    stats = logger.get_comprehensive_stats()
    print(f"📊 Final Stats: {stats}")
    
    print("✅ IntegratedDatasetLogger Test completed!")