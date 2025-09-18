"""
Performance benchmark tests for the FinPattern-Engine v2.1 pipeline.
"""

import pandas as pd
from pathlib import Path
import pytest
import numpy as np

# Import from our project
from core.profiler.profiler import run as run_profiler

@pytest.fixture
def setup_benchmark_data():
    dummy_dir = Path("temp_benchmark_data_v2_1")
    dummy_dir.mkdir(exist_ok=True)
    dummy_csv = dummy_dir / "eurusd_1m_ticks.csv"
    n_ticks = 1_000_000
    start_ts = pd.to_datetime("2025-01-01T00:00:00Z")
    timestamps = pd.to_datetime(start_ts.value + np.arange(n_ticks) * 1_000_000_000, unit="ns", utc=True)
    bids = 1.1 + np.random.randn(n_ticks) * 0.0001
    asks = bids + 0.0001
    pd.DataFrame({"timestamp": timestamps, "bid": bids, "ask": asks}).to_csv(dummy_csv, index=False)
    yield str(dummy_csv), str(dummy_dir)
    import shutil
    shutil.rmtree(dummy_dir)

def test_performance_benchmark_v2_1(setup_benchmark_data):
    csv_path, out_dir = setup_benchmark_data
    
    config = {
        "data_ingest": {
            "csv": {"path": csv_path},
            "bar_frames": [{"type": "time", "unit": "1m"}],
            "out_dir": str(Path(out_dir) / "data_ingest")
        },
        "labeling": {
            "out_dir": str(Path(out_dir) / "labeling")
        },
        "feature_engine": {
            "out_dir": str(Path(out_dir) / "feature_engine")
        }
    }
    
    result = run_profiler(config)
    assert result["success"]
    assert result["bars_per_second"] > 1000

