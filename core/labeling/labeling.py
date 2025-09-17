"""
Core Implementation for Module 2: Triple-Barrier Labeling

This module takes bar data from Module 1 and applies the Triple-Barrier
Labeling method as described by Marcos Lopez de Prado in "Advances in 
Financial Machine Learning".
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
def apply_labeling_numba(prices: np.ndarray, t_events: np.ndarray, 
                         pt_sl: np.ndarray, timeout_bars: int) -> np.ndarray:
    """Numba-optimized function for applying triple-barrier labeling."""
    
    n_events = len(t_events)
    out = np.zeros((n_events, 3))  # [ret, label, t_final]
    
    for i in range(n_events):
        entry_time = t_events[i]
        entry_price = prices[entry_time]
        
        # Barriers
        take_profit_price = entry_price * (1 + pt_sl[0])
        stop_loss_price = entry_price * (1 - pt_sl[1])
        
        # Vertical barrier (timeout)
        timeout_time = min(entry_time + timeout_bars, len(prices) - 1)
        
        # Iterate through future bars
        for t in range(entry_time + 1, timeout_time + 1):
            current_price = prices[t]
            
            # Check for TP/SL hits
            if current_price >= take_profit_price:
                out[i, 0] = (current_price - entry_price) / entry_price
                out[i, 1] = 1  # Take Profit
                out[i, 2] = t
                break
            
            elif current_price <= stop_loss_price:
                out[i, 0] = (current_price - entry_price) / entry_price
                out[i, 1] = -1  # Stop Loss
                out[i, 2] = t
                break
        
        # If no barrier was hit, it's a timeout
        if out[i, 1] == 0:
            final_price = prices[timeout_time]
            out[i, 0] = (final_price - entry_price) / entry_price
            out[i, 1] = 0  # Timeout
            out[i, 2] = timeout_time
            
    return out


def calculate_daily_volatility(close_prices: pd.Series, 
                               span: int = 100) -> pd.Series:
    """Calculate daily volatility using EWMA of returns."""
    
    # Daily returns
    daily_returns = close_prices.pct_change()
    
    # EWMA of standard deviation
    volatility = daily_returns.ewm(span=span).std()
    
    return volatility.fillna(0)


def run(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Main function to run the labeling module."""
    
    # --- 1. Setup & Configuration ---
    run_id = config.get("run_id")
    if not run_id:
        run_id = run_manager.create_run("labeling", config)
    
    out_dir = Path(config.get("out_dir", f"runs/{run_id}/labeling"))
    out_dir.mkdir(parents=True, exist_ok=True)
    
    monitor = ProgressMonitor(str(out_dir), run_id)
    
    try:
        with monitor:
            # --- 2. Load Input Data ---
            monitor.update("load", "Lade Bar-Daten", 5)
            
            input_file = Path(config["input_file"])
            if not input_file.exists():
                raise FileNotFoundError(f"Input file not found: {input_file}")
            
            df = pd.read_parquet(input_file)
            monitor.update("load", "Bar-Daten geladen", 10)
            
            # --- 3. Calculate Volatility ---
            monitor.update("volatility", "Berechne Volatilität", 20)
            
            volatility_span = config.get("volatility_span", 100)
            volatility = calculate_daily_volatility(df["close"], span=volatility_span)
            
            # --- 4. Define Barriers & Events ---
            monitor.update("barriers", "Definiere Barrieren", 30)
            
            # Events (e.g., every bar)
            t_events = np.arange(len(df))
            
            # Dynamic barriers based on volatility
            tp_mult = config.get("tp_mult", 2.0)
            sl_mult = config.get("sl_mult", 1.0)
            
            # Take profit and stop loss levels
            pt_sl = np.array([tp_mult, sl_mult])
            
            # Timeout in bars
            timeout_bars = config.get("timeout_bars", 24)
            
            # --- 5. Apply Labeling ---
            monitor.update("labeling", "Wende Labeling an", 50)
            
            prices = df["close"].to_numpy()
            
            # Run Numba-optimized function
            results = apply_labeling_numba(prices, t_events, pt_sl, timeout_bars)
            
            # --- 6. Create Labeled DataFrame ---
            monitor.update("dataframe", "Erstelle gelabeltes DataFrame", 80)
            
            df_labeled = df.copy()
            df_labeled["ret"] = results[:, 0]
            df_labeled["label"] = results[:, 1].astype(int)
            df_labeled["t_final"] = df.index[results[:, 2].astype(int)]
            
            # --- 7. Save Outputs ---
            monitor.update("save", "Speichere Ergebnisse", 90)
            
            # Save labeled data
            output_file = out_dir / f"{input_file.stem}_labeled.parquet"
            df_labeled.to_parquet(output_file)
            
            # Create labeling report
            report = {
                "n_events": len(df_labeled),
                "label_counts": df_labeled["label"].value_counts().to_dict(),
                "avg_return": df_labeled["ret"].mean(),
                "config_used": config
            }
            
            report_file = out_dir / "labeling_report.json"
            with open(report_file, "w") as f:
                json.dump(report, f, indent=2)
            
            # Create manifest
            manifest = {
                "module": "labeling",
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
            
            # Final result dictionary
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
        error_message = f"Fehler in Modul 2 (Labeling): {str(e)}"
        monitor.update("error", error_message, 0)
        run_manager.update_run_status(run_id, "error", error=error_message)
        return {"success": False, "error": error_message}


# Example usage (for testing)
if __name__ == "__main__":
    
    # Create dummy data for testing
    dummy_data = {
        "open": np.random.rand(1000) + 1.1,
        "high": np.random.rand(1000) + 1.11,
        "low": np.random.rand(1000) + 1.09,
        "close": np.random.rand(1000) + 1.1
    }
    
    df_dummy = pd.DataFrame(dummy_data)
    df_dummy.index = pd.to_datetime(pd.date_range("2025-01-01", periods=1000, freq="min"))
    
    # Create dummy input file
    dummy_dir = Path("temp_test_data")
    dummy_dir.mkdir(exist_ok=True)
    dummy_input_file = dummy_dir / "bars_1m.parquet"
    df_dummy.to_parquet(dummy_input_file)
    
    # Config for the run
    test_config = {
        "input_file": str(dummy_input_file),
        "tp_mult": 2.0,
        "sl_mult": 1.0,
        "timeout_bars": 24,
        "volatility_span": 100,
        "out_dir": "temp_test_data/labeling_output"
    }
    
    print("Starte Modul 2 (Labeling) Test...")
    result = run(test_config)
    
    if result and result["success"]:
        print("✅ Modul 2 Test erfolgreich abgeschlossen!")
        print(f"Ergebnisse in: {result.get('output_dir')}")
        print("\nLabel-Verteilung:")
        print(result.get("report", {}).get("label_counts"))
    else:
        print("❌ Modul 2 Test fehlgeschlagen.")
        if result:
            print(f"Fehler: {result.get('error')}")
    
    # Cleanup
    import shutil
    shutil.rmtree(dummy_dir)

