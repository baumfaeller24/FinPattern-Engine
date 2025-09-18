"""
Core Implementation for Module 11: Profiler v2.1

This module runs performance benchmarks on the FinPattern-Engine pipeline
to ensure it meets the >2000 Bars/s performance target.
"""

import time
import pandas as pd
from pathlib import Path
import json
from typing import Dict, Any

# Import from our project
from core.data_ingest.data_ingest import run as run_data_ingest
from core.labeling.labeling import run as run_labeling
from core.feature_engine.feature_engine import run as run_feature_engine

def run_benchmark(config: Dict[str, Any]) -> Dict[str, Any]:
    """Runs a full pipeline benchmark and returns performance metrics."""
    
    # --- Data Ingest ---
    start_time = time.time()
    ingest_result = run_data_ingest(config["data_ingest"])
    ingest_time = time.time() - start_time
    
    # --- Labeling ---
    labeling_config = config["labeling"]
    labeling_config["input_file"] = ingest_result["frames"]["1m"]["path"]
    labeling_config["tick_slice_file"] = ingest_result["frames"]["1m"]["tick_slice_path"]
    start_time = time.time()
    labeling_result = run_labeling(labeling_config)
    if not labeling_result.get("success"):
        raise Exception(f"Labeling module failed: {labeling_result.get('error')}")
    labeling_time = time.time() - start_time
    
    # --- Feature Engine ---
    feature_engine_config = config["feature_engine"]
    feature_engine_config["input_file"] = labeling_result["labeled_data_path"]
    start_time = time.time()
    feature_engine_result = run_feature_engine(feature_engine_config)
    feature_engine_time = time.time() - start_time
    
    # --- Performance Metrics ---
    df_final = pd.read_parquet(feature_engine_result["feature_data_path"])
    n_bars = len(df_final)
    total_time = ingest_time + labeling_time + feature_engine_time
    bars_per_second = n_bars / total_time
    
    return {
        "n_bars": n_bars,
        "total_time_seconds": total_time,
        "bars_per_second": bars_per_second,
        "ingest_time": ingest_time,
        "labeling_time": labeling_time,
        "feature_engine_time": feature_engine_time
    }

def run(config: Dict[str, Any]) -> Dict[str, Any]:
    out_dir = Path(config.get("out_dir", "runs/profiler"))
    out_dir.mkdir(parents=True, exist_ok=True)
    
    benchmark_result = run_benchmark(config)
    
    report_file = out_dir / "performance_report.json"
    with open(report_file, "w") as f:
        json.dump(benchmark_result, f, indent=2)
        
    return {
        "success": True,
        "report_path": str(report_file),
        "bars_per_second": benchmark_result["bars_per_second"]
    }

if __name__ == "__main__":
    # Create a dummy 1M tick CSV for testing
    print("Creating 1M tick dummy CSV...")
    dummy_dir = Path("temp_profiler_data")
    dummy_dir.mkdir(exist_ok=True)
    dummy_csv = dummy_dir / "eurusd_1m_ticks.csv"
    n_ticks = 1_000_000
    start_ts = pd.to_datetime("2025-01-01T00:00:00Z")
    timestamps = pd.to_datetime(start_ts.value + np.arange(n_ticks) * 1_000_000_000, unit="ns", utc=True)
    bids = 1.1 + np.random.randn(n_ticks) * 0.0001
    asks = bids + 0.0001
    pd.DataFrame({"timestamp": timestamps, "bid": bids, "ask": asks}).to_csv(dummy_csv, index=False)
    
    test_config = {
        "data_ingest": {
            "csv": {"path": str(dummy_csv)},
            "bar_frames": [{"type": "time", "unit": "1m"}],
            "out_dir": str(dummy_dir / "data_ingest")
        },
        "labeling": {
            "out_dir": str(dummy_dir / "labeling")
        },
        "feature_engine": {
            "out_dir": str(dummy_dir / "feature_engine")
        }
    }
    
    print("Running profiler benchmark...")
    result = run(test_config)
    
    if result["success"]:
        print("✅ Profiler module test successful!")
        print(f"Performance report saved to: {result['report_path']}")
        print(f"Bars per second: {result['bars_per_second']:.2f}")
    
    import shutil
    shutil.rmtree(dummy_dir)

