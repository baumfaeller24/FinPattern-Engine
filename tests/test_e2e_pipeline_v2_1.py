"""
End-to-End tests for the FinPattern-Engine v2.1 pipeline.
"""

import pandas as pd
from pathlib import Path
import pytest
import numpy as np

# Import from our project
from core.data_ingest.data_ingest import run as run_data_ingest
from core.labeling.labeling import run as run_labeling
from core.feature_engine.feature_engine import run as run_feature_engine

@pytest.fixture
def setup_test_data():
    dummy_dir = Path("temp_e2e_test_data_v2_1")
    dummy_dir.mkdir(exist_ok=True)
    dummy_csv = dummy_dir / "eurusd_e2e.csv"
    n_ticks = 10_000
    start_ts = pd.to_datetime("2025-01-01T09:00:00Z")
    timestamps = pd.to_datetime(start_ts.value + np.arange(n_ticks) * 1_000_000_000, unit="ns", utc=True)
    bids = 1.1 + np.random.randn(n_ticks) * 0.0001
    asks = bids + 0.0001
    pd.DataFrame({"timestamp": timestamps, "bid": bids, "ask": asks}).to_csv(dummy_csv, index=False)
    yield str(dummy_csv), str(dummy_dir)
    import shutil
    shutil.rmtree(dummy_dir)

def test_e2e_pipeline_v2_1(setup_test_data):
    csv_path, out_dir = setup_test_data
    
    # --- Data Ingest ---
    ingest_config = {
        "csv": {"path": csv_path},
        "bar_frames": [{"type": "time", "unit": "1m"}],
        "out_dir": str(Path(out_dir) / "data_ingest")
    }
    ingest_result = run_data_ingest(ingest_config)
    assert ingest_result["frames"]["1m"]["path"]
    assert ingest_result["frames"]["1m"]["tick_slice_path"]
    
    # --- Labeling ---
    labeling_config = {
        "input_file": ingest_result["frames"]["1m"]["path"],
        "tick_slice_file": ingest_result["frames"]["1m"]["tick_slice_path"],
        "out_dir": str(Path(out_dir) / "labeling")
    }
    labeling_result = run_labeling(labeling_config)
    assert labeling_result["labeled_data_path"]
    
    # --- Feature Engine ---
    feature_engine_config = {
        "input_file": labeling_result["labeled_data_path"],
        "out_dir": str(Path(out_dir) / "feature_engine")
    }
    feature_engine_result = run_feature_engine(feature_engine_config)
    assert feature_engine_result["feature_data_path"]
    
    # --- Final Checks ---
    df_final = pd.read_parquet(feature_engine_result["feature_data_path"])
    assert "rsi" in df_final.columns
    assert "sma_20" in df_final.columns
    assert "label" in df_final.columns
    assert df_final.shape[0] > 0

