"""
Core Implementation for Module 3: FeatureEngine

This module takes labeled bar data from Module 2 and generates a wide range of
technical indicators and features for machine learning models.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, Any, Optional

# Import from our project
from core.orchestrator.run_manager import run_manager
from core.orchestrator.progress_monitor import ProgressMonitor

def calculate_rsi(prices: pd.Series, window: int = 14) -> pd.Series:
    """Calculate Relative Strength Index."""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """Calculate MACD indicator."""
    ema_fast = prices.ewm(span=fast).mean()
    ema_slow = prices.ewm(span=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal).mean()
    histogram = macd_line - signal_line
    
    return pd.DataFrame({
        'macd': macd_line,
        'macd_signal': signal_line,
        'macd_histogram': histogram
    })


def calculate_bollinger_bands(prices: pd.Series, window: int = 20, std_dev: float = 2) -> pd.DataFrame:
    """Calculate Bollinger Bands."""
    sma = prices.rolling(window=window).mean()
    std = prices.rolling(window=window).std()
    
    return pd.DataFrame({
        'bb_upper': sma + (std * std_dev),
        'bb_middle': sma,
        'bb_lower': sma - (std * std_dev),
        'bb_width': (sma + (std * std_dev)) - (sma - (std * std_dev)),
        'bb_percent': (prices - (sma - (std * std_dev))) / ((sma + (std * std_dev)) - (sma - (std * std_dev)))
    })


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    """Calculate Average True Range."""
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return true_range.rolling(window=window).mean()


def calculate_stochastic(high: pd.Series, low: pd.Series, close: pd.Series, 
                        k_window: int = 14, d_window: int = 3) -> pd.DataFrame:
    """Calculate Stochastic Oscillator."""
    lowest_low = low.rolling(window=k_window).min()
    highest_high = high.rolling(window=k_window).max()
    k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
    d_percent = k_percent.rolling(window=d_window).mean()
    
    return pd.DataFrame({
        'stoch_k': k_percent,
        'stoch_d': d_percent
    })


def generate_features(df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
    """Generate technical analysis features using custom implementations."""
    
    df_features = df.copy()
    
    # Get the list of enabled feature categories
    feature_categories = config.get("feature_categories", 
                                  ["momentum", "trend", "volatility", "volume"])
    
    # Ensure we have OHLC columns
    required_cols = ['open', 'high', 'low', 'close']
    if not all(col in df_features.columns for col in required_cols):
        raise ValueError(f"Missing required OHLC columns. Found: {list(df_features.columns)}")
    
    # -- Momentum Indicators --
    if "momentum" in feature_categories:
        # RSI
        df_features['rsi_14'] = calculate_rsi(df_features['close'], 14)
        
        # MACD
        macd_data = calculate_macd(df_features['close'])
        df_features = pd.concat([df_features, macd_data], axis=1)
        
        # Stochastic
        stoch_data = calculate_stochastic(df_features['high'], df_features['low'], df_features['close'])
        df_features = pd.concat([df_features, stoch_data], axis=1)
        
        # CCI (Commodity Channel Index)
        typical_price = (df_features['high'] + df_features['low'] + df_features['close']) / 3
        sma_tp = typical_price.rolling(window=20).mean()
        mad = typical_price.rolling(window=20).apply(lambda x: np.mean(np.abs(x - x.mean())))
        df_features['cci_20'] = (typical_price - sma_tp) / (0.015 * mad)

    # -- Trend Indicators --
    if "trend" in feature_categories:
        # Simple Moving Averages
        df_features['sma_20'] = df_features['close'].rolling(window=20).mean()
        df_features['sma_50'] = df_features['close'].rolling(window=50).mean()
        
        # Exponential Moving Averages
        df_features['ema_20'] = df_features['close'].ewm(span=20).mean()
        df_features['ema_50'] = df_features['close'].ewm(span=50).mean()
        
        # Price relative to moving averages
        df_features['price_vs_sma20'] = df_features['close'] / df_features['sma_20'] - 1
        df_features['price_vs_ema20'] = df_features['close'] / df_features['ema_20'] - 1

    # -- Volatility Indicators --
    if "volatility" in feature_categories:
        # Bollinger Bands
        bb_data = calculate_bollinger_bands(df_features['close'])
        df_features = pd.concat([df_features, bb_data], axis=1)
        
        # Average True Range
        df_features['atr_14'] = calculate_atr(df_features['high'], df_features['low'], df_features['close'])
        
        # Volatility (rolling standard deviation)
        df_features['volatility_20'] = df_features['close'].rolling(window=20).std()

    # -- Volume Indicators --
    if "volume" in feature_categories and "volume" in df_features.columns:
        # On-Balance Volume
        obv = []
        obv_val = 0
        for i in range(len(df_features)):
            if i == 0:
                obv_val = df_features['volume'].iloc[i]
            else:
                if df_features['close'].iloc[i] > df_features['close'].iloc[i-1]:
                    obv_val += df_features['volume'].iloc[i]
                elif df_features['close'].iloc[i] < df_features['close'].iloc[i-1]:
                    obv_val -= df_features['volume'].iloc[i]
            obv.append(obv_val)
        df_features['obv'] = obv
        
        # Volume Moving Average
        df_features['volume_sma_20'] = df_features['volume'].rolling(window=20).mean()
        df_features['volume_ratio'] = df_features['volume'] / df_features['volume_sma_20']

    # -- Price Action Features --
    # Always include these regardless of categories
    df_features['price_change'] = df_features['close'].pct_change()
    df_features['high_low_ratio'] = df_features['high'] / df_features['low'] - 1
    df_features['open_close_ratio'] = df_features['close'] / df_features['open'] - 1
    
    # Candle patterns (simplified)
    df_features['is_doji'] = (abs(df_features['close'] - df_features['open']) / 
                             (df_features['high'] - df_features['low'])) < 0.1
    df_features['is_hammer'] = ((df_features['close'] > df_features['open']) & 
                               ((df_features['open'] - df_features['low']) > 
                                2 * (df_features['close'] - df_features['open'])))
    
    # Handle potential NaN values
    df_features = df_features.ffill().fillna(0)
    
    return df_features


def run(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Main function to run the FeatureEngine module."""
    
    # --- 1. Setup & Configuration ---
    run_id = config.get("run_id")
    if not run_id:
        run_id = run_manager.create_run("feature_engine", config)
    
    out_dir = Path(config.get("out_dir", f"runs/{run_id}/feature_engine"))
    out_dir.mkdir(parents=True, exist_ok=True)
    
    monitor = ProgressMonitor(str(out_dir), run_id)
    
    try:
        with monitor:
            # --- 2. Load Input Data ---
            monitor.update("load", "Lade gelabelte Bar-Daten", 5)
            
            input_file = Path(config["input_file"])
            if not input_file.exists():
                raise FileNotFoundError(f"Input file not found: {input_file}")
            
            df = pd.read_parquet(input_file)
            monitor.update("load", "Daten geladen", 10)
            
            # --- 3. Generate Features ---
            monitor.update("features", "Generiere technische Indikatoren", 20)
            
            df_features = generate_features(df, config)
            
            monitor.update("features", f"{len(df_features.columns) - len(df.columns)} Features generiert", 80)
            
            # --- 4. Save Outputs ---
            monitor.update("save", "Speichere Ergebnisse", 90)
            
            # Save feature data
            output_file = out_dir / f"{input_file.stem}_features.parquet"
            df_features.to_parquet(output_file)
            
            # Create report
            report = {
                "n_bars": len(df_features),
                "n_original_features": len(df.columns),
                "n_new_features": len(df_features.columns) - len(df.columns),
                "new_feature_names": list(set(df_features.columns) - set(df.columns)),
                "config_used": config
            }
            
            report_file = out_dir / "feature_engine_report.json"
            with open(report_file, "w") as f:
                json.dump(report, f, indent=2)
            
            # Create manifest
            manifest = {
                "module": "feature_engine",
                "version": "1.0.0",
                "run_id": run_id,
                "input_file": str(input_file),
                "output_file": str(output_file),
                "report_file": str(report_file),
                "timestamp": datetime.now().isoformat()
            }
            
            manifest_file = out_dir / "manifest.json"
            with open(manifest_file, "w") as f:
                json.dump(manifest, f, indent=2)
            
            # Final result
            final_result = {
                "success": True,
                "run_id": run_id,
                "output_dir": str(out_dir),
                "feature_data_path": str(output_file),
                "report": report
            }
            
            run_manager.update_run_status(run_id, "success", result=final_result)
            return final_result

    except Exception as e:
        error_message = f"Fehler in Modul 3 (FeatureEngine): {str(e)}"
        monitor.update("error", error_message, 0)
        run_manager.update_run_status(run_id, "error", error=error_message)
        return {"success": False, "error": error_message}


# Example usage (for testing)
if __name__ == "__main__":
    
    # Create dummy labeled data
    dummy_data = {
        "open": np.random.rand(100) + 1.1,
        "high": np.random.rand(100) + 1.11,
        "low": np.random.rand(100) + 1.09,
        "close": np.random.rand(100) + 1.1,
        "volume": np.random.randint(1000, 5000, 100),
        "label": np.random.choice([-1, 0, 1], 100)
    }
    df_dummy = pd.DataFrame(dummy_data)
    df_dummy.index = pd.to_datetime(pd.date_range("2025-01-01", periods=100, freq="min"))
    
    dummy_dir = Path("temp_test_data_fe")
    dummy_dir.mkdir(exist_ok=True)
    dummy_input_file = dummy_dir / "bars_labeled.parquet"
    df_dummy.to_parquet(dummy_input_file)
    
    # Config for the run
    test_config = {
        "input_file": str(dummy_input_file),
        "feature_categories": ["momentum", "trend", "volatility", "volume"],
        "out_dir": "temp_test_data_fe/feature_engine_output"
    }
    
    print("Starte Modul 3 (FeatureEngine) Test...")
    result = run(test_config)
    
    if result and result["success"]:
        print("✅ Modul 3 Test erfolgreich abgeschlossen!")
        print(f"Ergebnisse in: {result.get('output_dir')}")
        print(f"\n{result['report']['n_new_features']} neue Features generiert.")
        print("Beispiel-Features:", result['report']['new_feature_names'][:5])
    else:
        print("❌ Modul 3 Test fehlgeschlagen.")
        if result:
            print(f"Fehler: {result.get('error')}")
    
    # Cleanup
    import shutil
    shutil.rmtree(dummy_dir)

