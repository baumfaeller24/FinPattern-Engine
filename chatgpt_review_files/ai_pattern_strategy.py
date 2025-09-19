"""
Enhanced AI-basierte Pattern-Recognition Strategie für NautilusTrader Integration
mit externem MiniCPM-4.1-8B Modell über TorchServe / REST API

ChatGPT-Verbesserungen integriert:
- Enhanced Feature Logging mit Parquet-Export
- BarDatasetBuilder für automatische Label-Generierung
- Environment-basierte Konfiguration
- Confidence-basierte Position-Sizing
- Live-Control via Redis/Kafka
"""
import requests
import numpy as np
import os
from typing import Dict, Optional
from datetime import datetime

from nautilus_trader.strategy.strategy import Strategy
from nautilus_trader.model.data import Bar
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.orders import MarketOrder

# ChatGPT Enhancement: Import der neuen Logging-Komponenten
try:
    from ai_indicator_optimizer.logging.feature_prediction_logger import FeaturePredictionLogger
    from ai_indicator_optimizer.dataset.bar_dataset_builder import BarDatasetBuilder
    ENHANCED_LOGGING_AVAILABLE = True
except ImportError:
    ENHANCED_LOGGING_AVAILABLE = False


class AIPatternStrategy(Strategy):
    """
    Enhanced AI-basierte Pattern-Recognition Strategie
    Integriert MiniCPM-4.1-8B über TorchServe für multimodale Trading-Analyse
    
    ChatGPT-Verbesserungen:
    - Enhanced Feature Logging mit Parquet-Export
    - BarDatasetBuilder für ML-Training-Daten
    - Environment-basierte Konfiguration
    - Confidence-basierte Position-Sizing
    - Live-Control via Redis/Kafka
    """
    
    def __init__(self, config=None):
        super().__init__(config)
        
        # ChatGPT Enhancement: Environment-basierte Konfiguration
        self.ai_endpoint = config.get("ai_endpoint", os.getenv("AI_ENDPOINT", "http://localhost:8080/predictions/pattern_model"))
        self.min_confidence = config.get("min_confidence", float(os.getenv("MIN_CONFIDENCE", "0.7")))
        self.base_position_size = config.get("position_size", int(os.getenv("POSITION_SIZE", "1000")))
        self.use_mock = config.get("use_mock", os.getenv("USE_MOCK", "True").lower() == "true")
        
        # ChatGPT Enhancement: Debug und Live-Control
        self.debug_mode = config.get("debug_mode", os.getenv("DEBUG_MODE", "False").lower() == "true")
        self.paused = False  # Für Live-Control via Redis/Kafka
        
        # ChatGPT Enhancement: Confidence-basierte Position-Sizing
        self.confidence_multiplier = config.get("confidence_multiplier", 1.5)
        self.max_position_multiplier = config.get("max_position_multiplier", 2.0)
        
        # ChatGPT Enhancement: Enhanced Logging Setup
        self.feature_logger = None
        self.dataset_builder = None
        
        if ENHANCED_LOGGING_AVAILABLE:
            # Feature Prediction Logger
            log_path = config.get("feature_log_path", "logs/ai_features.parquet")
            buffer_size = config.get("log_buffer_size", 1000)
            self.feature_logger = FeaturePredictionLogger(
                output_path=log_path,
                buffer_size=buffer_size,
                auto_flush=True
            )
            
            # Dataset Builder für ML-Training
            horizon = config.get("dataset_horizon", 5)
            self.dataset_builder = BarDatasetBuilder(
                horizon=horizon,
                min_bars=config.get("min_dataset_bars", 100),
                include_technical_indicators=True
            )
            
            self.log.info("✅ Enhanced Logging aktiviert: FeaturePredictionLogger + BarDatasetBuilder")
        else:
            self.log.warning("⚠️ Enhanced Logging nicht verfügbar - Module nicht gefunden")
        
        # Trading-Parameter
        self.max_positions = config.get("max_positions", 1)
        self.risk_per_trade = config.get("risk_per_trade", 0.02)  # 2% Risk
        
        # Performance-Tracking
        self.predictions_count = 0
        self.successful_predictions = 0
        
    def on_start(self):
        """Strategy startup"""
        self.log.info("✅ AI Pattern Strategy started")
        self.log.info(f"📡 AI Endpoint: {self.ai_endpoint}")
        self.log.info(f"🎯 Min Confidence: {self.min_confidence}")
        self.log.info(f"🔧 Mock Mode: {self.use_mock}")
        
    def on_stop(self):
        """Strategy shutdown"""
        accuracy = (self.successful_predictions / max(self.predictions_count, 1)) * 100
        self.log.info(f"📊 AI Strategy Performance: {accuracy:.1f}% accuracy ({self.successful_predictions}/{self.predictions_count})")
        
    def on_bar(self, bar: Bar):
        """Wird bei jedem Bar aufgerufen - Enhanced Hauptlogik mit ChatGPT-Verbesserungen"""
        try:
            # ChatGPT Enhancement: Live-Control Check
            if self.paused:
                self.log.debug("⚠️ Strategy paused via command channel")
                return
            
            # Features für AI-Modell extrahieren (Enhanced)
            features = self._extract_enhanced_features(bar)
            
            # ChatGPT Enhancement: Dataset Builder Update
            if self.dataset_builder:
                self.dataset_builder.on_bar(bar)
            
            # AI-Prediction abrufen
            prediction = self._get_ai_prediction(features)
            
            # ChatGPT Enhancement: Enhanced Confidence Scoring
            enhanced_confidence = self._calculate_enhanced_confidence(prediction, features)
            
            # ChatGPT Enhancement: Feature Logging
            if self.feature_logger and prediction:
                self.feature_logger.log(
                    ts_ns=int(bar.ts_init),
                    instrument=str(bar.bar_type.instrument_id),
                    features=features,
                    prediction=prediction,
                    confidence_score=enhanced_confidence,
                    risk_score=prediction.get("risk_score", 0.0),
                    market_regime=self._detect_market_regime(features)
                )
            
            # Signal ausführen wenn Enhanced Confidence hoch genug
            if prediction and enhanced_confidence > self.min_confidence:
                self._execute_enhanced_signal(prediction, bar, enhanced_confidence)
                
        except Exception as e:
            self.log.error(f"⚠️ AI analysis failed: {e}")
    
    def _extract_enhanced_features(self, bar: Bar) -> Dict:
        """
        ChatGPT Enhancement: Erweiterte Feature-Extraktion
        Integriert technische Indikatoren, Zeitnormierung und Pattern-Features
        """
        # Basis OHLCV-Features
        open_price = float(bar.open)
        high_price = float(bar.high)
        low_price = float(bar.low)
        close_price = float(bar.close)
        volume = float(bar.volume)
        
        # Berechnete Features
        price_change = close_price - open_price
        price_range = high_price - low_price
        body_ratio = abs(price_change) / max(price_range, 1e-6)
        
        # ChatGPT Enhancement: Zeitnormierung
        dt = datetime.utcfromtimestamp(bar.ts_init / 1e9)
        
        features = {
            # OHLCV-Daten
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "volume": volume,
            
            # Zeitstempel für Kontext
            "timestamp": bar.ts_init,
            "instrument": str(bar.bar_type.instrument_id),
            
            # ChatGPT Enhancement: Zeitnormierung
            "hour": dt.hour,
            "minute": dt.minute,
            "day_of_week": dt.weekday(),
            "is_market_open": 8 <= dt.hour <= 17,  # Vereinfacht
            
            # Erweiterte technische Features
            "price_change": price_change,
            "price_change_pct": price_change / max(open_price, 1e-6),
            "price_range": price_range,
            "body_ratio": body_ratio,
            
            # ChatGPT Enhancement: Candlestick Pattern Features
            "upper_shadow": high_price - max(open_price, close_price),
            "lower_shadow": min(open_price, close_price) - low_price,
            "is_doji": body_ratio < 0.1,
            "is_bullish": price_change > 0,
            "is_bearish": price_change < 0,
            
            # Markt-Kontext
            "bar_type": str(bar.bar_type),
        }
        
        # ChatGPT Enhancement: Technische Indikatoren (falls verfügbar)
        if hasattr(self, '_price_history'):
            tech_indicators = self._calculate_technical_indicators(close_price)
            features.update(tech_indicators)
        
        return features
    
    def _calculate_technical_indicators(self, current_price: float) -> Dict:
        """
        ChatGPT Enhancement: Berechne technische Indikatoren
        """
        if not hasattr(self, '_price_history'):
            self._price_history = []
        
        self._price_history.append(current_price)
        
        # Behalte nur die letzten 50 Preise
        if len(self._price_history) > 50:
            self._price_history = self._price_history[-50:]
        
        indicators = {}
        
        if len(self._price_history) >= 14:
            # RSI (vereinfacht)
            indicators["rsi_14"] = self._calculate_rsi(self._price_history, 14)
        
        if len(self._price_history) >= 20:
            # SMA
            indicators["sma_20"] = np.mean(self._price_history[-20:])
            
            # Volatilität
            indicators["volatility_20"] = np.std(self._price_history[-20:])
        
        if len(self._price_history) >= 5:
            # Momentum
            indicators["momentum_5"] = (current_price - self._price_history[-5]) / self._price_history[-5]
        
        return indicators
    
    def _calculate_rsi(self, prices: list, period: int = 14) -> float:
        """Vereinfachte RSI-Berechnung"""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _get_ai_prediction(self, features: Dict) -> Optional[Dict]:
        """Frage das AI-Modell an oder nutze Mock für Development"""
        
        if self.use_mock:
            # Mock-Prediction für Development/Testing
            return self._get_mock_prediction(features)
        
        try:
            # Echte AI-Inferenz über TorchServe
            response = requests.post(
                self.ai_endpoint, 
                json=features,
                timeout=5.0,  # 5s Timeout
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            prediction = response.json()
            self.predictions_count += 1
            
            self.log.debug(f"🤖 AI Prediction: {prediction}")
            return prediction
            
        except requests.exceptions.Timeout:
            self.log.warning("⏰ AI prediction timeout - using fallback")
            return None
        except requests.exceptions.RequestException as e:
            self.log.error(f"❌ AI prediction request failed: {e}")
            return None
        except Exception as e:
            self.log.error(f"❌ AI prediction failed: {e}")
            return None
    
    def _get_mock_prediction(self, features: Dict) -> Dict:
        """Mock-Prediction für Development und Testing"""
        
        # Einfache regelbasierte Mock-Logik
        price_change = features.get("price_change", 0)
        body_ratio = features.get("body_ratio", 0)
        
        # Simuliere AI-Entscheidung basierend auf einfachen Regeln
        if price_change > 0 and body_ratio > 0.7:
            action = "BUY"
            confidence = 0.75
            reasoning = "Strong bullish candle detected"
        elif price_change < 0 and body_ratio > 0.7:
            action = "SELL" 
            confidence = 0.75
            reasoning = "Strong bearish candle detected"
        else:
            action = "HOLD"
            confidence = 0.5
            reasoning = "No clear pattern detected"
        
        return {
            "action": action,
            "confidence": confidence,
            "reasoning": reasoning,
            "pattern_type": "mock_pattern",
            "risk_score": 0.3
        }
    
    def _execute_signal(self, prediction: Dict, bar: Bar):
        """Führe Handelssignal basierend auf AI-Prediction aus"""
        
        action = prediction.get("action", "HOLD")
        confidence = prediction.get("confidence", 0.0)
        reasoning = prediction.get("reasoning", "N/A")
        
        # Prüfe ob bereits Position vorhanden
        if len(self.portfolio.positions_open()) >= self.max_positions:
            self.log.info(f"⏸️ Max positions reached, skipping {action} signal")
            return
        
        # Führe Trading-Action aus
        if action == "BUY":
            self._submit_market_order(OrderSide.BUY, bar)
        elif action == "SELL":
            self._submit_market_order(OrderSide.SELL, bar)
        
        # Logging
        self.log.info(
            f"[AI] 🎯 Action: {action} | "
            f"📊 Confidence: {confidence:.2f} | "
            f"💭 Reason: {reasoning}"
        )
    
    def _submit_market_order(self, side: OrderSide, bar: Bar):
        """Sende Market-Order ab"""
        try:
            # Erstelle Market Order
            order = MarketOrder(
                trader_id=self.trader_id,
                strategy_id=self.id,
                instrument_id=bar.bar_type.instrument_id,
                order_side=side,
                quantity=self.instrument.make_qty(self.position_size),
                time_in_force=self.time_in_force,
                order_id=self.generate_order_id(),
                ts_init=self.clock.timestamp_ns(),
            )
            
            # Order einreichen
            self.submit_order(order)
            
            self.log.info(f"🟢 Submitted {side.name} order for {self.position_size} units")
            
        except Exception as e:
            self.log.error(f"❌ Order submission failed: {e}")
    
    def on_order_filled(self, event):
        """Callback wenn Order gefüllt wird"""
        self.log.info(f"✅ Order filled: {event.order_id}")
        
    def on_position_opened(self, position):
        """Callback wenn Position eröffnet wird"""
        self.log.info(f"📈 Position opened: {position.instrument_id} {position.side}")
        
    def on_position_closed(self, position):
        """Callback wenn Position geschlossen wird"""
        pnl = position.realized_pnl
        if pnl and pnl.as_double() > 0:
            self.successful_predictions += 1
            
        self.log.info(f"📉 Position closed: {position.instrument_id} PnL: {pnl}")
    
    def reset(self):
        """Reset Strategy State"""
        super().reset()
        self.predictions_count = 0
        self.successful_predictions = 0
    
    def _calculate_enhanced_confidence(self, prediction: Optional[Dict], features: Dict) -> float:
        """
        ChatGPT Enhancement: Erweiterte Confidence-Berechnung
        Kombiniert AI-Confidence mit Risk-Score und Market-Regime
        """
        if not prediction:
            return 0.0
        
        base_confidence = prediction.get("confidence", 0.0)
        risk_score = prediction.get("risk_score", 0.0)
        
        # ChatGPT Logic: Confidence-Adjustment basierend auf Risk
        adjusted_confidence = base_confidence * (1 - risk_score)
        
        # Market-Regime-Adjustment
        market_regime = self._detect_market_regime(features)
        if market_regime == "volatile":
            adjusted_confidence *= 0.8  # Reduziere Confidence in volatilen Märkten
        elif market_regime == "trending":
            adjusted_confidence *= 1.1  # Erhöhe Confidence in Trending-Märkten
        
        # Technical Indicator Confirmation
        if "rsi_14" in features:
            rsi = features["rsi_14"]
            if prediction.get("action") == "BUY" and rsi < 30:
                adjusted_confidence *= 1.1  # RSI bestätigt Oversold
            elif prediction.get("action") == "SELL" and rsi > 70:
                adjusted_confidence *= 1.1  # RSI bestätigt Overbought
        
        return min(adjusted_confidence, 1.0)
    
    def _detect_market_regime(self, features: Dict) -> str:
        """
        ChatGPT Enhancement: Market-Regime-Erkennung
        """
        volatility = features.get("volatility_20", 0.0)
        momentum = features.get("momentum_5", 0.0)
        
        if volatility > 0.002:  # Hohe Volatilität
            return "volatile"
        elif abs(momentum) > 0.001:  # Starker Momentum
            return "trending"
        elif volatility < 0.0005:  # Niedrige Volatilität
            return "quiet"
        else:
            return "ranging"
    
    def _execute_enhanced_signal(self, prediction: Dict, bar: Bar, enhanced_confidence: float):
        """
        ChatGPT Enhancement: Erweiterte Signal-Ausführung
        Mit Confidence-basierter Position-Sizing
        """
        action = prediction.get("action")
        
        if action in ["BUY", "SELL"]:
            # ChatGPT Enhancement: Confidence-basierte Position-Sizing
            position_size = self._calculate_dynamic_position_size(enhanced_confidence)
            
            # ChatGPT Enhancement: Dynamic Risk Management
            risk_pct = self._calculate_dynamic_risk(enhanced_confidence, prediction.get("risk_score", 0.0))
            
            side = OrderSide.BUY if action == "BUY" else OrderSide.SELL
            
            self.log.info(f"🎯 Enhanced Signal: {action}")
            self.log.info(f"   Confidence: {enhanced_confidence:.3f}")
            self.log.info(f"   Position Size: {position_size}")
            self.log.info(f"   Risk: {risk_pct:.3f}%")
            
            # TODO: Implementiere tatsächliche Order-Submission
            # self._submit_enhanced_order(side, position_size, risk_pct, bar)
    
    def _calculate_dynamic_position_size(self, confidence: float) -> int:
        """
        ChatGPT Enhancement: Confidence-basierte Position-Sizing
        """
        confidence_multiplier = min(confidence * self.confidence_multiplier, self.max_position_multiplier)
        dynamic_size = int(self.base_position_size * confidence_multiplier)
        
        return dynamic_size
    
    def _calculate_dynamic_risk(self, confidence: float, risk_score: float) -> float:
        """
        ChatGPT Enhancement: Dynamisches Risk Management
        """
        base_risk = self.risk_per_trade
        
        # Niedrigere Confidence = höheres Risiko-Management
        confidence_adjustment = (1 - confidence) * 0.01
        
        # Risk Score Adjustment
        risk_adjustment = risk_score * 0.005
        
        return base_risk + confidence_adjustment + risk_adjustment
    
    def on_stop(self):
        """Enhanced Strategy shutdown mit ChatGPT-Verbesserungen"""
        accuracy = (self.successful_predictions / max(self.predictions_count, 1)) * 100
        self.log.info(f"📊 AI Strategy Performance: {accuracy:.1f}% accuracy ({self.successful_predictions}/{self.predictions_count})")
        
        # ChatGPT Enhancement: Export Dataset und Feature Logs
        if self.dataset_builder:
            try:
                dataset_path = f"datasets/{datetime.now().strftime('%Y%m%d_%H%M%S')}_trading_dataset.parquet"
                if self.dataset_builder.to_parquet(dataset_path):
                    self.log.info(f"📁 Dataset exported: {dataset_path}")
                    
                    # Zeige Dataset-Statistiken
                    stats = self.dataset_builder.get_stats()
                    self.log.info(f"📊 Dataset Stats: {stats}")
            except Exception as e:
                self.log.error(f"❌ Dataset export failed: {e}")
        
        # ChatGPT Enhancement: Feature Logger schließen
        if self.feature_logger:
            try:
                self.feature_logger.close()
                stats = self.feature_logger.get_stats()
                self.log.info(f"📊 Feature Logger Stats: {stats}")
            except Exception as e:
                self.log.error(f"❌ Feature Logger close failed: {e}")