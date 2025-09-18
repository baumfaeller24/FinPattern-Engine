"""
Core Implementation for Module 3: FeatureEngine v2.1

This module now includes systematic NaN handling and more advanced
institutional features.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

# Import from our project
from core.orchestrator.run_manager import run_manager
from core.orchestrator.progress_monitor import ProgressMonitor


def standardize_ohlc_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize OHLC column names to lowercase 'open', 'high', 'low', 'close'."""
    column_map = {
        'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume',
        'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume',
    }
    df = df.rename(columns=lambda c: column_map.get(c.lower(), c.lower()))
    required_cols = ['open', 'high', 'low', 'close']
    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"Missing required OHLC columns after standardization. Found: {list(df.columns)}")
    return df

# --- Feature Implementations (v2.1) ---

def add_momentum_features(df: pd.DataFrame, config: Dict) -> pd.DataFrame:
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    ema_12 = df['close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = ema_12 - ema_26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    return df

def add_trend_features(df: pd.DataFrame, config: Dict) -> pd.DataFrame:
    df['sma_20'] = df['close'].rolling(window=20).mean()
    df['sma_50'] = df['close'].rolling(window=50).mean()
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    return df

def add_volatility_features(df: pd.DataFrame, config: Dict) -> pd.DataFrame:
    df['bollinger_mid'] = df['close'].rolling(window=20).mean()
    df['bollinger_std'] = df['close'].rolling(window=20).std()
    df['bollinger_upper'] = df['bollinger_mid'] + (df['bollinger_std'] * 2)
    df['bollinger_lower'] = df['bollinger_mid'] - (df['bollinger_std'] * 2)
    return df

def add_pattern_features(df: pd.DataFrame, config: Dict) -> pd.DataFrame:
    body = abs(df['close'] - df['open'])
    prev_body = body.shift(1)
    df['two_bar_reversal'] = ((df['close'] > df['open']) & (df['close'].shift(1) < df['open'].shift(1)) & (body > prev_body)).astype(int)
    return df

def add_session_features(df: pd.DataFrame, config: Dict) -> pd.DataFrame:
    ts = pd.to_datetime(df.index, utc=True)
    df['hour'] = ts.hour
    df['day_of_week'] = ts.dayofweek
    df['session_london'] = ((df['hour'] >= 8) & (df['hour'] < 17)).astype(int)
    df['session_ny'] = ((df['hour'] >= 13) & (df['hour'] < 22)).astype(int)
    df['session_asia'] = ((df['hour'] >= 0) & (df['hour'] < 9)).astype(int)
    return df

def add_microstructural_features(df: pd.DataFrame, config: Dict) -> pd.DataFrame:
    if 'spread_mean' in df.columns:
        df['spread_vs_rolling_mean'] = df['spread_mean'] / df['spread_mean'].rolling(window=50).mean()
    if 'n_ticks' in df.columns:
        df['tick_imbalance'] = df['n_ticks'].diff()
    return df

def add_institutional_features(df: pd.DataFrame, config: Dict) -> pd.DataFrame:
    # Order-Flow Proxies (Tick Imbalance over n ticks)
    if 'tick_imbalance' in df.columns:
        df['tick_imbalance_5'] = df['tick_imbalance'].rolling(window=5).sum()
        df['tick_imbalance_20'] = df['tick_imbalance'].rolling(window=20).sum()
    
    # Liquidity Stress (Spread Stretch > p95)
    if 'spread_mean' in df.columns:
        p95_spread = df['spread_mean'].quantile(0.95)
        df['liquidity_stress'] = (df['spread_mean'] > p95_spread).astype(int)
        
    return df

def run(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    run_id = config.get("run_id")
    if not run_id:
        run_id = run_manager.create_run("feature_engine", config)
    
    out_dir = Path(config.get("out_dir", f"runs/{run_id}/feature_engine"))
    out_dir.mkdir(parents=True, exist_ok=True)
    
    monitor = ProgressMonitor(str(out_dir), run_id)
    
    try:
        with monitor:
            monitor.update("load", "Lade gelabelte Bar-Daten", 5)
            input_file = Path(config["input_file"])
            if not input_file.exists():
                raise FileNotFoundError(f"Input file not found: {input_file}")
            
            df = pd.read_parquet(input_file)
            df = standardize_ohlc_columns(df.copy())
            monitor.update("load", "Daten geladen", 10)
            
            feature_configs = config.get("features", {})
            if feature_configs.get("momentum", True):
                monitor.update("features", "Generiere Momentum Features", 20)
                df = add_momentum_features(df, feature_configs.get("momentum_config", {}))
            if feature_configs.get("trend", True):
                monitor.update("features", "Generiere Trend Features", 40)
                df = add_trend_features(df, feature_configs.get("trend_config", {}))
            if feature_configs.get("volatility", True):
                monitor.update("features", "Generiere Volatilitäts Features", 60)
                df = add_volatility_features(df, feature_configs.get("volatility_config", {}))
            if feature_configs.get("patterns", True):
                monitor.update("features", "Generiere Muster Features", 70)
                df = add_pattern_features(df, feature_configs.get("patterns_config", {}))
            if feature_configs.get("session", True):
                monitor.update("features", "Generiere Session Features", 80)
                df = add_session_features(df, feature_configs.get("session_config", {}))
            if feature_configs.get("microstructural", True):
                monitor.update("features", "Generiere Microstructural Features", 85)
                df = add_microstructural_features(df, feature_configs.get("microstructural_config", {}))
            if feature_configs.get("institutional", True):
                monitor.update("features", "Generiere Institutionelle Features", 88)
                df = add_institutional_features(df, feature_configs.get("institutional_config", {}))
            
            # NaN handling
            nan_policy = config.get("nan_policy", "drop")
            if nan_policy == "drop":
                df = df.dropna()
            elif nan_policy == "ffill":
                df = df.fillna(method="ffill")
            elif nan_policy == "bfill":
                df = df.fillna(method="bfill")
            
            monitor.update("save", "Speichere Feature-Daten", 90)
            output_file = out_dir / f"{input_file.stem}_features_v2_1.parquet"
            df.to_parquet(output_file)
            
            report = {
                "n_features": len(df.columns),
                "feature_columns": list(df.columns),
                "config_used": config
            }
            report_file = out_dir / "feature_engine_report_v2_1.json"
            with open(report_file, "w") as f:
                json.dump(report, f, indent=2)
            
            manifest = {
                "module": "feature_engine",
                "version": "2.1.0",
                "run_id": run_id,
                "input_file": str(input_file),
                "output_file": str(output_file),
                "report_file": str(report_file),
                "timestamp": datetime.now().isoformat()
            }
            manifest_file = out_dir / "manifest_v2_1.json"
            with open(manifest_file, "w") as f:
                json.dump(manifest, f, indent=2)
            
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
        error_message = f"Fehler in Modul 3 (FeatureEngine v2.1): {str(e)}"
        monitor.update("error", error_message, 0)
        run_manager.update_run_status(run_id, "error", error=error_message)
        return {"success": False, "error": error_message}


if __name__ == "__main__":
    print("Modul 3 (FeatureEngine v2.1) - bereit für Integrationstests.")

