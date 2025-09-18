"""
Tests for the Exporter module (v2.1).
"""

import pandas as pd
from pathlib import Path
import pytest
import numpy as np

# Import from our project
from core.exporter.exporter import run as run_exporter

@pytest.fixture
def setup_exporter_data():
    dummy_dir = Path("temp_exporter_data_v2_1")
    dummy_dir.mkdir(exist_ok=True)
    dummy_feature_file = dummy_dir / "features.parquet"
    
    n_rows = 100
    df = pd.DataFrame({
        "timestamp": pd.to_datetime(pd.to_datetime("2025-01-01").value + np.arange(n_rows) * 3600 * 1_000_000_000, unit="ns", utc=True),
        "open": 1.1 + np.random.randn(n_rows) * 0.001,
        "high": 1.1 + np.random.randn(n_rows) * 0.001,
        "low": 1.1 + np.random.randn(n_rows) * 0.001,
        "close": 1.1 + np.random.randn(n_rows) * 0.001,
        "label": np.random.choice([-1, 0, 1], n_rows),
        "RSI_14": np.random.rand(n_rows) * 100,
        "MACD_12_26_9": np.random.randn(n_rows),
    })
    df.to_parquet(dummy_feature_file)
    
    yield str(dummy_feature_file), str(dummy_dir)
    
    import shutil
    shutil.rmtree(dummy_dir)

def test_pine_script_export(setup_exporter_data):
    feature_file, out_dir = setup_exporter_data
    
    config = {
        "input_file": feature_file,
        "output_dir": out_dir,
        "format": "pinescript",
        "strategy_name": "TestStrategy",
        "feature_map": {
            "RSI_14": "rsi",
            "MACD_12_26_9": "macd"
        },
        "entry_logic": "rsi > 70 and macd < 0",
        "exit_logic": "rsi < 30"
    }
    
    result = run_exporter(config)
    assert result["success"]
    pine_file = Path(result["pine_script_path"])
    assert pine_file.exists()
    content = pine_file.read_text()
    assert "strategy(\"TestStrategy\", overlay=true)" in content
    assert "longCondition = rsi > 70 and macd < 0" in content

def test_nautilus_trader_export(setup_exporter_data):
    feature_file, out_dir = setup_exporter_data
    
    config = {
        "input_file": feature_file,
        "output_dir": out_dir,
        "format": "nautilus",
        "strategy_name": "TestNautilusStrategy"
    }
    
    result = run_exporter(config)
    assert result["success"]
    nautilus_file = Path(result["nautilus_trader_path"])
    assert nautilus_file.exists()
    content = nautilus_file.read_text()
    assert "class TestNautilusStrategy(Strategy):" in content

