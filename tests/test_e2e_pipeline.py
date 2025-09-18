"""
End-to-End (E2E) Tests for the FinPattern-Engine Pipeline (v2.0)

This test simulates a full user workflow:
1. Run DataIngest (Module 1) with real EUR/USD data.
2. Run Labeling (Module 2) on the output of Module 1.
3. Run FeatureEngine (Module 3) on the output of Module 2.
4. Validate the final output and all intermediate artifacts.
"""

import pytest
import pandas as pd
from pathlib import Path
import shutil
import yaml

# Import core modules
from core.data_ingest.data_ingest import run as run_data_ingest
from core.labeling.labeling import run as run_labeling
from core.feature_engine.feature_engine import run as run_feature_engine

@pytest.fixture(scope="module")
def test_setup():
    """Set up the test environment and create test data."""
    test_dir = Path("temp_e2e_test")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a realistic EUR/USD sample CSV
    csv_path = test_dir / "eurusd_e2e_sample.csv"
    data = """
timestamp,bid,ask
2025-09-19T10:00:00.100Z,1.10000,1.10002
2025-09-19T10:00:00.200Z,1.10001,1.10003
2025-09-19T10:00:00.300Z,1.10002,1.10004
2025-09-19T10:00:01.100Z,1.10010,1.10012
2025-09-19T10:00:01.200Z,1.10011,1.10013
2025-09-19T10:00:01.300Z,1.10012,1.10014
"""
    with open(csv_path, "w") as f:
        f.write(data)
    
    yield test_dir, csv_path
    
    # Teardown
    shutil.rmtree(test_dir)

def test_e2e_pipeline(test_setup):
    """Test the full v2.0 pipeline from DataIngest to FeatureEngine."""
    test_dir, csv_path = test_setup
    
    # --- 1. Run DataIngest (Module 1) ---
    data_ingest_config = {
        "symbol": "EURUSD",
        "csv": {"path": str(csv_path)},
        "bar_frames": [{"type": "tick", "count": 3}],
        "pip_size": 0.0001,
        "out_dir": str(test_dir / "data_ingest_output")
    }
    
    data_ingest_result = run_data_ingest(data_ingest_config)
    assert data_ingest_result is not None
    assert data_ingest_result["frames"]
    bars_path = Path(data_ingest_result["frames"]["3t"])

    assert bars_path.exists()
    
    # --- 2. Run Labeling (Module 2) ---
    labeling_config = {
        "input_file": str(bars_path),
        "pip_size": 0.0001,
        "volatility_window": 1,
        "tp_sl_multipliers": [2.0, 1.0],
        "timeout_bars": 1,
        "out_dir": str(test_dir / "labeling_output")
    }
    
    labeling_result = run_labeling(labeling_config)
    assert labeling_result["success"]
    labeled_bars_path = Path(labeling_result["labeled_data_path"])
    assert labeled_bars_path.exists()
    
    # --- 3. Run FeatureEngine (Module 3) ---
    feature_engine_config = {
        "input_file": str(labeled_bars_path),
        "features": {"momentum": True, "trend": True},
        "out_dir": str(test_dir / "feature_engine_output")
    }
    
    feature_engine_result = run_feature_engine(feature_engine_config)
    assert feature_engine_result["success"]
    feature_bars_path = Path(feature_engine_result["feature_data_path"])
    assert feature_bars_path.exists()
    
    # --- 4. Validate Final Output ---
    df_final = pd.read_parquet(feature_bars_path)
    assert "rsi" in df_final.columns
    assert "sma_20" in df_final.columns
    assert "label" in df_final.columns
    assert "label" in df_final.columns
    assert df_final.shape[0] > 0

