"""
Synthetic Pattern Generator für KI-generierte Pattern-Variationen
Nutzt MiniCPM-4.1-8B für kreative Pattern-Generierung
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import json
from dataclasses import dataclass
import random
import math
from PIL import Image, ImageDraw
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from ..ai.multimodal_ai import MultimodalAI
from ..ai.model_factory import ModelFactory
from ..data.models import OHLCVData, TradingData
from ..indicators.indicator_calculator import IndicatorCalculator
from .historical_pattern_miner import MinedPattern


@dataclass
class SyntheticConfig:
    """Konfiguration für Synthetic Pattern Generation"""
    
    # Generation Parameters
    base_patterns: List[str] = None
    variations_per_pattern: int = 5
    noise_level: float = 0.02
    
    # Market Parameters
    base_price: float = 1.1000
    volatility_range: Tuple[float, float] = (0.001, 0.005)
    trend_strength_range: Tuple[float, float] = (0.0, 0.002)
    
    # Technical Parameters
    candle_count: int = 100
    timeframe: str = "1H"
    
    # AI Generation
    use_ai_generation: bool = True
    creativity_level: float = 0.7
    
    def __post_init__(self):
        if self.base_patterns is None:
            self.base_patterns = [
                "double_top", "double_bottom", "head_shoulders",
                "triangle", "support_resistance", "breakout"
            ]


class PatternTemplate:
    """Template für Pattern-Generierung"""
    
    def __init__(self, pattern_type: str):
        self.pattern_type = pattern_type
        self.template_functions = {
            "double_top": self._generate_double_top,
            "double_bottom": self._generate_double_bottom,
            "head_shoulders": self._generate_head_shoulders,
            "triangle": self._generate_triangle,
            "support_resistance": self._generate_support_resistance,
            "breakout": self._generate_breakout
        }
    
    def generate(self, config: SyntheticConfig) -> pd.DataFrame:
        """Generiert Pattern basierend auf Template"""
        
        if self.pattern_type in self.template_functions:
            return self.template_functions[self.pattern_type](config)
        else:
            return self._generate_random_pattern(config)
    
    def _generate_double_top(self, config: SyntheticConfig) -> pd.DataFrame:
        """Generiert Double Top Pattern"""
        
        candles = []
        base_price = config.base_price
        
        # Phase 1: Aufwärtstrend zum ersten Peak
        for i in range(25):
            trend = 0.001 * (1 - i/25)  # Abnehmender Trend
            noise = np.random.normal(0, config.noise_level)
            price_change = trend + noise
            
            if i == 0:
                open_price = base_price
            else:
                open_price = candles[-1]["close"]
            
            close_price = open_price + price_change
            high_price = close_price + abs(np.random.normal(0, config.noise_level/2))
            low_price = open_price - abs(np.random.normal(0, config.noise_level/2))
            
            candles.append({
                "open": open_price,
                "high": max(open_price, close_price, high_price),
                "low": min(open_price, close_price, low_price),
                "close": close_price,
                "volume": np.random.uniform(1000000, 5000000)
            })
        
        # Phase 2: Rückgang
        peak1_price = candles[-1]["close"]
        
        for i in range(20):
            trend = -0.0008  # Abwärtstrend
            noise = np.random.normal(0, config.noise_level)
            price_change = trend + noise
            
            open_price = candles[-1]["close"]
            close_price = open_price + price_change
            high_price = open_price + abs(np.random.normal(0, config.noise_level/3))
            low_price = close_price - abs(np.random.normal(0, config.noise_level/3))
            
            candles.append({
                "open": open_price,
                "high": max(open_price, close_price, high_price),
                "low": min(open_price, close_price, low_price),
                "close": close_price,
                "volume": np.random.uniform(1000000, 5000000)
            })
        
        # Phase 3: Zweiter Peak (ähnlich dem ersten)
        for i in range(25):
            if i < 15:
                trend = 0.0008  # Aufwärtstrend
            else:
                trend = -0.0005  # Leichter Rückgang
            
            noise = np.random.normal(0, config.noise_level)
            price_change = trend + noise
            
            open_price = candles[-1]["close"]
            close_price = open_price + price_change
            
            # Zweiter Peak ähnlich dem ersten
            if i == 12:
                close_price = peak1_price + np.random.normal(0, 0.0002)
            
            high_price = close_price + abs(np.random.normal(0, config.noise_level/2))
            low_price = open_price - abs(np.random.normal(0, config.noise_level/2))
            
            candles.append({
                "open": open_price,
                "high": max(open_price, close_price, high_price),
                "low": min(open_price, close_price, low_price),
                "close": close_price,
                "volume": np.random.uniform(1000000, 5000000)
            })
        
        # Phase 4: Breakout nach unten
        for i in range(30):
            trend = -0.001  # Starker Abwärtstrend
            noise = np.random.normal(0, config.noise_level)
            price_change = trend + noise
            
            open_price = candles[-1]["close"]
            close_price = open_price + price_change
            high_price = open_price + abs(np.random.normal(0, config.noise_level/3))
            low_price = close_price - abs(np.random.normal(0, config.noise_level/2))
            
            candles.append({
                "open": open_price,
                "high": max(open_price, close_price, high_price),
                "low": min(open_price, close_price, low_price),
                "close": close_price,
                "volume": np.random.uniform(1500000, 6000000)  # Höheres Volumen
            })
        
        return self._create_dataframe_with_timestamps(candles, config)
    
    def _generate_double_bottom(self, config: SyntheticConfig) -> pd.DataFrame:
        """Generiert Double Bottom Pattern (umgekehrtes Double Top)"""
        
        # Generiere Double Top und invertiere
        double_top_df = self._generate_double_top(config)
        
        # Invertiere Preise um Mittelpunkt
        mid_price = (double_top_df["high"].max() + double_top_df["low"].min()) / 2
        
        inverted_df = double_top_df.copy()
        for col in ["open", "high", "low", "close"]:
            inverted_df[col] = 2 * mid_price - double_top_df[col]
        
        # Korrigiere High/Low nach Inversion
        for i in range(len(inverted_df)):
            row_values = [inverted_df.iloc[i]["open"], inverted_df.iloc[i]["close"]]
            inverted_df.iloc[i, inverted_df.columns.get_loc("high")] = max(row_values) + abs(np.random.normal(0, config.noise_level/3))
            inverted_df.iloc[i, inverted_df.columns.get_loc("low")] = min(row_values) - abs(np.random.normal(0, config.noise_level/3))
        
        return inverted_df    
    
def _generate_head_shoulders(self, config: SyntheticConfig) -> pd.DataFrame:
        """Generiert Head and Shoulders Pattern"""
        
        candles = []
        base_price = config.base_price
        
        # Left Shoulder
        for i in range(20):
            trend = 0.0008 if i < 15 else -0.0005
            noise = np.random.normal(0, config.noise_level)
            price_change = trend + noise
            
            if i == 0:
                open_price = base_price
            else:
                open_price = candles[-1]["close"]
            
            close_price = open_price + price_change
            high_price = close_price + abs(np.random.normal(0, config.noise_level/2))
            low_price = open_price - abs(np.random.normal(0, config.noise_level/2))
            
            candles.append({
                "open": open_price,
                "high": max(open_price, close_price, high_price),
                "low": min(open_price, close_price, low_price),
                "close": close_price,
                "volume": np.random.uniform(1000000, 4000000)
            })
        
        left_shoulder_high = max([c["high"] for c in candles[-5:]])
        
        # Valley 1
        for i in range(15):
            trend = -0.0006
            noise = np.random.normal(0, config.noise_level)
            price_change = trend + noise
            
            open_price = candles[-1]["close"]
            close_price = open_price + price_change
            high_price = open_price + abs(np.random.normal(0, config.noise_level/3))
            low_price = close_price - abs(np.random.normal(0, config.noise_level/3))
            
            candles.append({
                "open": open_price,
                "high": max(open_price, close_price, high_price),
                "low": min(open_price, close_price, low_price),
                "close": close_price,
                "volume": np.random.uniform(800000, 3000000)
            })
        
        # Head
        for i in range(25):
            if i < 18:
                trend = 0.001  # Stärkerer Aufwärtstrend für Head
            else:
                trend = -0.0008
            
            noise = np.random.normal(0, config.noise_level)
            price_change = trend + noise
            
            open_price = candles[-1]["close"]
            close_price = open_price + price_change
            high_price = close_price + abs(np.random.normal(0, config.noise_level/2))
            low_price = open_price - abs(np.random.normal(0, config.noise_level/2))
            
            candles.append({
                "open": open_price,
                "high": max(open_price, close_price, high_price),
                "low": min(open_price, close_price, low_price),
                "close": close_price,
                "volume": np.random.uniform(1200000, 5000000)
            })
        
        # Valley 2
        for i in range(15):
            trend = -0.0006
            noise = np.random.normal(0, config.noise_level)
            price_change = trend + noise
            
            open_price = candles[-1]["close"]
            close_price = open_price + price_change
            high_price = open_price + abs(np.random.normal(0, config.noise_level/3))
            low_price = close_price - abs(np.random.normal(0, config.noise_level/3))
            
            candles.append({
                "open": open_price,
                "high": max(open_price, close_price, high_price),
                "low": min(open_price, close_price, low_price),
                "close": close_price,
                "volume": np.random.uniform(800000, 3000000)
            })
        
        # Right Shoulder (ähnlich Left Shoulder)
        for i in range(20):
            if i < 12:
                trend = 0.0007
            else:
                trend = -0.001  # Breakout
            
            noise = np.random.normal(0, config.noise_level)
            price_change = trend + noise
            
            open_price = candles[-1]["close"]
            close_price = open_price + price_change
            
            # Right Shoulder ähnlich Left Shoulder
            if i == 8:
                target_price = left_shoulder_high + np.random.normal(0, 0.0003)
                close_price = min(close_price, target_price)
            
            high_price = close_price + abs(np.random.normal(0, config.noise_level/2))
            low_price = open_price - abs(np.random.normal(0, config.noise_level/2))
            
            candles.append({
                "open": open_price,
                "high": max(open_price, close_price, high_price),
                "low": min(open_price, close_price, low_price),
                "close": close_price,
                "volume": np.random.uniform(1000000, 4500000)
            })
        
        return self._create_dataframe_with_timestamps(candles, config)
    
    def _generate_triangle(self, config: SyntheticConfig) -> pd.DataFrame:
        """Generiert Triangle Pattern"""
        
        candles = []
        base_price = config.base_price
        
        # Initial Setup
        high_line_start = base_price + 0.005
        low_line_start = base_price - 0.003
        
        triangle_length = 80
        
        for i in range(triangle_length):
            # Konvergierende Linien
            progress = i / triangle_length
            
            current_high_bound = high_line_start - (high_line_start - base_price) * progress
            current_low_bound = low_line_start + (base_price - low_line_start) * progress
            
            # Preis zwischen konvergierenden Linien
            if i == 0:
                open_price = base_price
            else:
                open_price = candles[-1]["close"]
            
            # Zufällige Bewegung innerhalb der Grenzen
            range_size = current_high_bound - current_low_bound
            relative_position = np.random.uniform(0.2, 0.8)
            target_price = current_low_bound + range_size * relative_position
            
            # Trend zum Target
            price_change = (target_price - open_price) * 0.3 + np.random.normal(0, config.noise_level)
            close_price = open_price + price_change
            
            # Bounds einhalten
            close_price = max(current_low_bound, min(current_high_bound, close_price))
            
            high_price = min(current_high_bound, close_price + abs(np.random.normal(0, config.noise_level/3)))
            low_price = max(current_low_bound, close_price - abs(np.random.normal(0, config.noise_level/3)))
            
            # Abnehmende Volatilität
            volume_factor = 1 - progress * 0.5
            volume = np.random.uniform(800000, 3000000) * volume_factor
            
            candles.append({
                "open": open_price,
                "high": max(open_price, close_price, high_price),
                "low": min(open_price, close_price, low_price),
                "close": close_price,
                "volume": volume
            })
        
        # Breakout
        breakout_direction = np.random.choice(["up", "down"])
        
        for i in range(20):
            if breakout_direction == "up":
                trend = 0.002
                volume_multiplier = 2.0
            else:
                trend = -0.002
                volume_multiplier = 2.0
            
            noise = np.random.normal(0, config.noise_level * 1.5)  # Höhere Volatilität
            price_change = trend + noise
            
            open_price = candles[-1]["close"]
            close_price = open_price + price_change
            high_price = close_price + abs(np.random.normal(0, config.noise_level))
            low_price = open_price - abs(np.random.normal(0, config.noise_level))
            
            candles.append({
                "open": open_price,
                "high": max(open_price, close_price, high_price),
                "low": min(open_price, close_price, low_price),
                "close": close_price,
                "volume": np.random.uniform(2000000, 8000000)
            })
        
        return self._create_dataframe_with_timestamps(candles, config)
    
    def _generate_support_resistance(self, config: SyntheticConfig) -> pd.DataFrame:
        """Generiert Support/Resistance Pattern"""
        
        candles = []
        base_price = config.base_price
        
        # Support/Resistance Level
        sr_level = base_price + np.random.uniform(-0.002, 0.002)
        is_support = np.random.choice([True, False])
        
        for i in range(config.candle_count):
            if i == 0:
                open_price = base_price
            else:
                open_price = candles[-1]["close"]
            
            # Bewegung zum SR Level
            distance_to_sr = sr_level - open_price
            
            if is_support:
                # Support: Preis bounced von unten
                if distance_to_sr < 0.0005 and distance_to_sr > -0.0005:
                    # Nahe Support - Bounce
                    trend = 0.0008
                    volume_multiplier = 1.5
                else:
                    # Normale Bewegung
                    trend = np.random.normal(0, 0.0003)
                    volume_multiplier = 1.0
            else:
                # Resistance: Preis wird von oben abgewiesen
                if distance_to_sr > -0.0005 and distance_to_sr < 0.0005:
                    # Nahe Resistance - Rejection
                    trend = -0.0008
                    volume_multiplier = 1.5
                else:
                    # Normale Bewegung
                    trend = np.random.normal(0, 0.0003)
                    volume_multiplier = 1.0
            
            noise = np.random.normal(0, config.noise_level)
            price_change = trend + noise
            
            close_price = open_price + price_change
            high_price = close_price + abs(np.random.normal(0, config.noise_level/2))
            low_price = open_price - abs(np.random.normal(0, config.noise_level/2))
            
            # SR Level Touches simulieren
            if abs(close_price - sr_level) < 0.0003:
                if is_support:
                    low_price = min(low_price, sr_level - 0.0001)
                else:
                    high_price = max(high_price, sr_level + 0.0001)
            
            volume = np.random.uniform(1000000, 4000000) * volume_multiplier
            
            candles.append({
                "open": open_price,
                "high": max(open_price, close_price, high_price),
                "low": min(open_price, close_price, low_price),
                "close": close_price,
                "volume": volume
            })
        
        return self._create_dataframe_with_timestamps(candles, config)
    
    def _generate_breakout(self, config: SyntheticConfig) -> pd.DataFrame:
        """Generiert Breakout Pattern"""
        
        candles = []
        base_price = config.base_price
        
        # Konsolidierung Phase
        consolidation_range = 0.003
        consolidation_center = base_price
        consolidation_length = 60
        
        for i in range(consolidation_length):
            if i == 0:
                open_price = base_price
            else:
                open_price = candles[-1]["close"]
            
            # Bewegung innerhalb der Konsolidierung
            max_price = consolidation_center + consolidation_range/2
            min_price = consolidation_center - consolidation_range/2
            
            # Zufällige Bewegung mit Tendenz zur Mitte
            center_pull = (consolidation_center - open_price) * 0.1
            noise = np.random.normal(0, config.noise_level * 0.5)  # Niedrigere Volatilität
            
            price_change = center_pull + noise
            close_price = max(min_price, min(max_price, open_price + price_change))
            
            high_price = min(max_price, close_price + abs(np.random.normal(0, config.noise_level/3)))
            low_price = max(min_price, close_price - abs(np.random.normal(0, config.noise_level/3)))
            
            # Abnehmende Volatilität während Konsolidierung
            volume_factor = 1 - (i / consolidation_length) * 0.4
            volume = np.random.uniform(800000, 2500000) * volume_factor
            
            candles.append({
                "open": open_price,
                "high": max(open_price, close_price, high_price),
                "low": min(open_price, close_price, low_price),
                "close": close_price,
                "volume": volume
            })
        
        # Breakout Phase
        breakout_direction = np.random.choice(["up", "down"])
        breakout_length = 40
        
        for i in range(breakout_length):
            if breakout_direction == "up":
                trend = 0.002 * (1 + i/breakout_length)  # Beschleunigender Trend
            else:
                trend = -0.002 * (1 + i/breakout_length)
            
            noise = np.random.normal(0, config.noise_level * 1.5)  # Höhere Volatilität
            price_change = trend + noise
            
            open_price = candles[-1]["close"]
            close_price = open_price + price_change
            high_price = close_price + abs(np.random.normal(0, config.noise_level))
            low_price = open_price - abs(np.random.normal(0, config.noise_level))
            
            # Hohes Volumen beim Breakout
            volume_multiplier = 2.0 + i/breakout_length
            volume = np.random.uniform(2000000, 8000000) * volume_multiplier
            
            candles.append({
                "open": open_price,
                "high": max(open_price, close_price, high_price),
                "low": min(open_price, close_price, low_price),
                "close": close_price,
                "volume": volume
            })
        
        return self._create_dataframe_with_timestamps(candles, config)
    
    def _generate_random_pattern(self, config: SyntheticConfig) -> pd.DataFrame:
        """Generiert zufälliges Pattern als Fallback"""
        
        candles = []
        base_price = config.base_price
        
        for i in range(config.candle_count):
            if i == 0:
                open_price = base_price
            else:
                open_price = candles[-1]["close"]
            
            # Zufällige Bewegung
            trend = np.random.normal(0, 0.0005)
            noise = np.random.normal(0, config.noise_level)
            price_change = trend + noise
            
            close_price = open_price + price_change
            high_price = close_price + abs(np.random.normal(0, config.noise_level/2))
            low_price = open_price - abs(np.random.normal(0, config.noise_level/2))
            
            candles.append({
                "open": open_price,
                "high": max(open_price, close_price, high_price),
                "low": min(open_price, close_price, low_price),
                "close": close_price,
                "volume": np.random.uniform(1000000, 5000000)
            })
        
        return self._create_dataframe_with_timestamps(candles, config)
    
    def _create_dataframe_with_timestamps(self, candles: List[Dict], config: SyntheticConfig) -> pd.DataFrame:
        """Erstellt DataFrame mit Timestamps"""
        
        # Timestamps generieren
        start_time = datetime.now() - timedelta(hours=len(candles))
        timestamps = []
        
        for i in range(len(candles)):
            if config.timeframe == "1H":
                timestamp = start_time + timedelta(hours=i)
            elif config.timeframe == "4H":
                timestamp = start_time + timedelta(hours=i*4)
            elif config.timeframe == "1D":
                timestamp = start_time + timedelta(days=i)
            else:
                timestamp = start_time + timedelta(hours=i)
            
            timestamps.append(timestamp)
        
        # DataFrame erstellen
        df = pd.DataFrame(candles)
        df["timestamp"] = timestamps
        
        # Spalten-Reihenfolge
        df = df[["timestamp", "open", "high", "low", "close", "volume"]]
        
        return df


class SyntheticPatternGenerator:
    """
    Hauptklasse für Synthetic Pattern Generation
    """
    
    def __init__(self, config: Optional[SyntheticConfig] = None):
        self.config = config or SyntheticConfig()
        self.logger = logging.getLogger(__name__)
        
        # AI Components (optional)
        self.multimodal_ai = None
        if self.config.use_ai_generation:
            try:
                model_factory = ModelFactory()
                self.multimodal_ai = model_factory.create_multimodal_ai()
            except Exception as e:
                self.logger.warning(f"AI generation disabled: {e}")
                self.config.use_ai_generation = False
        
        # Pattern Templates
        self.pattern_templates = {
            pattern_type: PatternTemplate(pattern_type) 
            for pattern_type in self.config.base_patterns
        }
        
        self.logger.info(f"SyntheticPatternGenerator initialized with {len(self.config.base_patterns)} pattern types")
    
    def generate_pattern_variations(self, base_pattern_type: str) -> List[MinedPattern]:
        """Generiert Variationen eines Pattern-Typs"""
        
        variations = []
        
        try:
            for i in range(self.config.variations_per_pattern):
                # Variiere Konfiguration
                varied_config = self._create_varied_config(i)
                
                # Generiere Pattern
                if base_pattern_type in self.pattern_templates:
                    ohlcv_df = self.pattern_templates[base_pattern_type].generate(varied_config)
                else:
                    self.logger.warning(f"Unknown pattern type: {base_pattern_type}")
                    continue
                
                # Konvertiere zu MinedPattern
                synthetic_pattern = self._convert_to_mined_pattern(
                    ohlcv_df, base_pattern_type, f"synthetic_v{i}"
                )
                
                variations.append(synthetic_pattern)
            
            self.logger.info(f"Generated {len(variations)} variations for {base_pattern_type}")
            return variations
            
        except Exception as e:
            self.logger.error(f"Pattern variation generation failed: {e}")
            return []
    
    def _create_varied_config(self, variation_index: int) -> SyntheticConfig:
        """Erstellt variierte Konfiguration"""
        
        # Base Config kopieren
        varied_config = SyntheticConfig(
            base_patterns=self.config.base_patterns,
            variations_per_pattern=1,
            noise_level=self.config.noise_level,
            base_price=self.config.base_price,
            candle_count=self.config.candle_count,
            timeframe=self.config.timeframe
        )
        
        # Variationen
        variation_factor = (variation_index + 1) / self.config.variations_per_pattern
        
        # Noise Level variieren
        varied_config.noise_level *= (0.5 + variation_factor)
        
        # Base Price variieren
        price_variation = np.random.uniform(-0.01, 0.01)
        varied_config.base_price *= (1 + price_variation)
        
        # Volatility Range variieren
        vol_min, vol_max = self.config.volatility_range
        vol_factor = 0.5 + variation_factor
        varied_config.volatility_range = (vol_min * vol_factor, vol_max * vol_factor)
        
        return varied_config
    
    def _convert_to_mined_pattern(self, 
                                 ohlcv_df: pd.DataFrame,
                                 pattern_type: str,
                                 variation_id: str) -> MinedPattern:
        """Konvertiert DataFrame zu MinedPattern"""
        
        try:
            # Pattern ID
            pattern_id = f"synthetic_{pattern_type}_{variation_id}_{int(time.time())}"
            
            # Price Data
            price_data = {
                "ohlcv": ohlcv_df.to_dict("records"),
                "price_range": {
                    "high": float(ohlcv_df["high"].max()),
                    "low": float(ohlcv_df["low"].min())
                }
            }
            
            # Berechne Indikatoren (vereinfacht)
            indicators = self._calculate_basic_indicators(ohlcv_df)
            
            # Pattern Features (simuliert)
            pattern_features = {
                "pattern_type": pattern_type,
                "confidence": np.random.uniform(0.7, 0.9),  # Synthetic patterns haben hohe Confidence
                "synthetic": True,
                "variation_id": variation_id
            }
            
            # Market Context
            market_context = {
                "symbol": "SYNTHETIC",
                "timeframe": self.config.timeframe,
                "volatility": float(ohlcv_df["close"].pct_change().std()),
                "trend": "bullish" if ohlcv_df["close"].iloc[-1] > ohlcv_df["close"].iloc[0] else "bearish",
                "volume_avg": float(ohlcv_df["volume"].mean()),
                "synthetic_generation": True
            }
            
            return MinedPattern(
                pattern_id=pattern_id,
                symbol="SYNTHETIC",
                timeframe=self.config.timeframe,
                pattern_type=pattern_type,
                confidence=pattern_features["confidence"],
                start_time=ohlcv_df["timestamp"].iloc[0],
                end_time=ohlcv_df["timestamp"].iloc[-1],
                price_data=price_data,
                indicators=indicators,
                pattern_features=pattern_features,
                market_context=market_context,
                mining_timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Pattern conversion failed: {e}")
            raise
    
    def _calculate_basic_indicators(self, ohlcv_df: pd.DataFrame) -> Dict[str, Any]:
        """Berechnet grundlegende Indikatoren für synthetic patterns"""
        
        try:
            indicators = {}
            
            # RSI (vereinfacht)
            delta = ohlcv_df["close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = (100 - (100 / (1 + rs))).fillna(50).tolist()
            indicators["RSI"] = rsi
            
            # SMA
            indicators["SMA_20"] = ohlcv_df["close"].rolling(20).mean().fillna(ohlcv_df["close"]).tolist()
            
            # Volume
            indicators["Volume"] = ohlcv_df["volume"].tolist()
            
            return indicators
            
        except Exception as e:
            self.logger.error(f"Indicator calculation failed: {e}")
            return {}
    
    def generate_comprehensive_synthetic_library(self) -> List[MinedPattern]:
        """Generiert komplette Synthetic Pattern Library"""
        
        all_synthetic_patterns = []
        
        for pattern_type in self.config.base_patterns:
            self.logger.info(f"Generating variations for {pattern_type}...")
            
            variations = self.generate_pattern_variations(pattern_type)
            all_synthetic_patterns.extend(variations)
        
        self.logger.info(f"Generated {len(all_synthetic_patterns)} total synthetic patterns")
        return all_synthetic_patterns
    
    def save_synthetic_patterns(self, patterns: List[MinedPattern], output_dir: str):
        """Speichert Synthetic Patterns"""
        
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # JSON Export
            patterns_data = [pattern.to_dict() for pattern in patterns]
            
            json_file = output_path / f"synthetic_patterns_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(json_file, 'w') as f:
                json.dump(patterns_data, f, indent=2, default=str)
            
            self.logger.info(f"Synthetic patterns saved to {json_file}")
            
        except Exception as e:
            self.logger.error(f"Saving synthetic patterns failed: {e}")


# Convenience Functions
def quick_synthetic_generation(pattern_type: str = "double_top", 
                             variations: int = 3) -> List[MinedPattern]:
    """Schnelle Synthetic Pattern Generation"""
    
    config = SyntheticConfig(
        base_patterns=[pattern_type],
        variations_per_pattern=variations,
        use_ai_generation=False
    )
    
    generator = SyntheticPatternGenerator(config)
    return generator.generate_pattern_variations(pattern_type)


def generate_full_synthetic_library() -> List[MinedPattern]:
    """Generiert komplette Synthetic Library"""
    
    config = SyntheticConfig(
        variations_per_pattern=5,
        use_ai_generation=False
    )
    
    generator = SyntheticPatternGenerator(config)
    return generator.generate_comprehensive_synthetic_library()