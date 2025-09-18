"""
Core Implementation for Module 2: Triple-Barrier Labeling v2.1

This module now uses tick slices for precise first-hit detection in the
Triple-Barrier Labeling method.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
import yaml
from datetime import datetime
from typing import Dict, List, Any, Optional
from numba import njit

# Import from our project
from core.orchestrator.run_manager import run_manager
from core.orchestrator.progress_monitor import ProgressMonitor


@njit
def apply_labeling_v2_1_numba(prices_high: np.ndarray, prices_low: np.ndarray, 
                              tick_slices: List[np.ndarray], t_events: np.ndarray, 
                              pt_sl: np.ndarray, timeout_bars: int, side: int) -> np.ndarray:
    """Numba-optimized function for applying triple-barrier labeling v2.1 with tick-slice first-hit."""
    
    n_events = len(t_events)
    out = np.zeros((n_events, 3))  # [ret, label, t_final]
    
    for i in range(n_events):
        entry_time = t_events[i]
        entry_price = (prices_high[entry_time] + prices_low[entry_time]) / 2.0
        
        if side == 1:
            take_profit_price = entry_price + pt_sl[0]
            stop_loss_price = entry_price - pt_sl[1]
        else:
            take_profit_price = entry_price - pt_sl[0]
            stop_loss_price = entry_price + pt_sl[1]
        
        timeout_time = min(entry_time + timeout_bars, len(prices_high) - 1)
        
        for t in range(entry_time + 1, timeout_time + 1):
            # Use tick slice for this bar to find first hit
            slice_data = tick_slices[t]
            
            for tick_idx in range(len(slice_data)):
                tick_bid = slice_data[tick_idx, 0]
                tick_ask = slice_data[tick_idx, 1]
                
                if side == 1:
                    if tick_ask >= take_profit_price:
                        out[i, 0] = (take_profit_price - entry_price) / entry_price
                        out[i, 1] = 1
                        out[i, 2] = t
                        break
                    elif tick_bid <= stop_loss_price:
                        out[i, 0] = (stop_loss_price - entry_price) / entry_price
                        out[i, 1] = -1
                        out[i, 2] = t
                        break
                else:
                    if tick_bid <= take_profit_price:
                        out[i, 0] = (take_profit_price - entry_price) / entry_price
                        out[i, 1] = 1
                        out[i, 2] = t
                        break
                    elif tick_ask >= stop_loss_price:
                        out[i, 0] = (stop_loss_price - entry_price) / entry_price
                        out[i, 1] = -1
                        out[i, 2] = t
                        break
            if out[i, 1] != 0: break
        
        if out[i, 1] == 0:
            final_price = (prices_high[timeout_time] + prices_low[timeout_time]) / 2.0
            out[i, 0] = (final_price - entry_price) / entry_price
            out[i, 1] = 0
            out[i, 2] = timeout_time
            
    return out

def calculate_daily_volatility(close_prices: pd.Series, span: int = 100) -> pd.Series:
    daily_returns = close_prices.pct_change()
    volatility = daily_returns.ewm(span=span).std()
    return volatility.fillna(0)

def standardize_ohlc_columns(df: pd.DataFrame) -> pd.DataFrame:
    column_map = {
        'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume',
        'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume',
    }
    df = df.rename(columns=lambda c: column_map.get(c.lower(), c.lower()))
    required_cols = ['open', 'high', 'low', 'close']
    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"Missing required OHLC columns after standardization. Found: {list(df.columns)}")
    return df

def run(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    run_id = config.get("run_id")
    if not run_id:
        run_id = run_manager.create_run("labeling", config)
    
    out_dir = Path(config.get("out_dir", f"runs/{run_id}/labeling"))
    out_dir.mkdir(parents=True, exist_ok=True)
    
    monitor = ProgressMonitor(str(out_dir), run_id)
    
    try:
        with monitor:
            monitor.update("load", "Lade Bar- und Tick-Slice-Daten", 5)
            input_file = Path(config["input_file"])
            tick_slice_file = Path(config["tick_slice_file"])
            if not input_file.exists() or not tick_slice_file.exists():
                raise FileNotFoundError(f"Input or tick slice file not found.")
            
            df = pd.read_parquet(input_file)
            df = standardize_ohlc_columns(df.copy())
            tick_slices_df = pd.read_parquet(tick_slice_file)
            monitor.update("load", "Daten geladen", 10)
            
            monitor.update("volatility", "Berechne Volatilität", 20)
            volatility_span = config.get("volatility_span", 100)
            volatility = calculate_daily_volatility(df["close"], span=volatility_span)
            
            monitor.update("barriers", "Definiere Barrieren", 30)
            t_events = np.arange(len(df))
            
            pip_size = config.get("pip_size", 0.0001)
            tp_pips = config.get("tp_pips", 20)
            sl_pips = config.get("sl_pips", 10)
            
            if config.get("use_volatility_scaling", True):
                tp_mult = config.get("tp_mult", 2.0)
                sl_mult = config.get("sl_mult", 1.0)
                pt = volatility * tp_mult
                sl = volatility * sl_mult
                pt_sl = np.array([pt.mean(), sl.mean()])
            else:
                pt_sl = np.array([tp_pips * pip_size, sl_pips * pip_size])
            
            timeout_bars = config.get("timeout_bars", 24)
            side = 1 if config.get("side", "long") == "long" else -1
            
            monitor.update("labeling", "Wende Labeling an", 50)
            prices_high = df["high"].to_numpy()
            prices_low = df["low"].to_numpy()
            
            # Prepare tick slices for Numba
            tick_slices_grouped = tick_slices_df.groupby('bar_idx')
            tick_slices_list = [np.empty((0, 2), dtype=np.float64)] * len(df)

            for i, group in tick_slices_grouped:
                tick_slices_list[i] = np.ascontiguousarray(group[["bid", "ask"]].to_numpy())

            results = apply_labeling_v2_1_numba(prices_high, prices_low, tick_slices_list, t_events, pt_sl, timeout_bars, side)
            
            monitor.update("dataframe", "Erstelle gelabeltes DataFrame", 80)
            df_labeled = df.copy()
            df_labeled["ret"] = results[:, 0]
            df_labeled["label"] = results[:, 1].astype(int)
            df_labeled["t_final"] = df.index[results[:, 2].astype(int)]
            
            monitor.update("save", "Speichere Ergebnisse", 90)
            output_file = out_dir / f"{input_file.stem}_labeled_v2_1.parquet"
            df_labeled.to_parquet(output_file)
            
            report = {
                "n_events": len(df_labeled),
                "label_counts": df_labeled["label"].value_counts().to_dict(),
                "avg_return": df_labeled["ret"].mean(),
                "config_used": config
            }
            report_file = out_dir / "labeling_report_v2_1.json"
            with open(report_file, "w") as f:
                json.dump(report, f, indent=2)
            
            manifest = {
                "module": "labeling",
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
                "labeled_data_path": str(output_file),
                "report": report
            }
            
            run_manager.update_run_status(run_id, "success", result=final_result)
            return final_result

    except Exception as e:
        error_message = f"Fehler in Modul 2 (Labeling v2.1): {str(e)}"
        monitor.update("error", error_message, 0)
        run_manager.update_run_status(run_id, "error", error=error_message)
        return {"success": False, "error": error_message}


if __name__ == "__main__":
    print("Modul 2 (Labeling v2.1) - bereit für Integrationstests.")

