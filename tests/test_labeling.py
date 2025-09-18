"""
Tests for Module 2: Triple-Barrier Labeling
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import shutil
import json

# Add project root to path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from core.labeling.labeling import run as run_labeling, _apply_labeling_numba, _calculate_daily_volatility


@pytest.fixture
def sample_bar_data():
    """Create sample bar data for testing with higher volatility."""
    np.random.seed(42)
    n_bars = 200
    base_price = 1.10000
    # Increased volatility for more dynamic price action
    returns = np.random.normal(0, 0.0005, n_bars)
    prices = base_price * np.exp(np.cumsum(returns))
    
    data = []
    for i in range(n_bars):
        price = prices[i]
        noise = np.random.normal(0, 0.0001, 4)
        open_price = price + noise[0]
        high_price = price + abs(noise[1])
        low_price = price - abs(noise[2])
        close_price = price + noise[3]
        high_price = max(open_price, high_price, low_price, close_price)
        low_price = min(open_price, high_price, low_price, close_price)
        data.append({
            "open": open_price, "high": high_price, 
            "low": low_price, "close": close_price
        })
    
    df = pd.DataFrame(data)
    df.index = pd.to_datetime(pd.date_range("2025-09-01", periods=n_bars, freq="min"))
    return df


class TestLabelingCore:
    """Tests for the core labeling logic."""

    def test_calculate_daily_volatility(self, sample_bar_data):
        """Test volatility calculation."""
        volatility = _calculate_daily_volatility(sample_bar_data["close"], span=20)
        assert isinstance(volatility, pd.Series)
        assert len(volatility) == len(sample_bar_data)
        assert not volatility.isnull().any() # Should be filled with 0

    def test_apply_labeling_numba(self):
        """Test the Numba-optimized labeling function with clear cases."""
        # Prices: 100 -> 104 (TP) -> 98 (SL) -> 100 (Timeout)
        prices = np.array([100, 101, 102, 104, 103, 101, 98, 99, 100])
        t_events = np.array([0, 2, 6]) # Events at start, mid, and near end
        pt_sl = np.array([0.03, 0.02])  # 3% TP, 2% SL
        timeout_bars = 3

        results = _apply_labeling_numba(prices, t_events, pt_sl, timeout_bars)

        # Event 1 (index 0, price 100): TP at 103, SL at 98
        # Should hit TP at index 3 (price 104)
        assert results[0, 1] == 1  # Label: Take Profit
        assert results[0, 2] == 3  # Final time

        # Event 2 (index 2, price 102): TP at 105.06, SL at 99.96
        # Should hit SL at index 6 (price 98)
        assert results[1, 1] == -1 # Label: Stop Loss
        assert results[1, 2] == 6  # Final time

        # Event 3 (index 6, price 98): TP at 100.94, SL at 96.04
        # Should time out at index 6+3=9 (or end of array)
        assert results[2, 1] == 0  # Label: Timeout
        assert results[2, 2] == 8  # Final time is end of array

    def test_run_labeling_module(self, sample_bar_data, tmp_path):
        """Test the main run function of the labeling module."""
        # Create dummy input file
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        input_file = input_dir / "bars.parquet"
        sample_bar_data.to_parquet(input_file)

        # Config for the run
        output_dir = tmp_path / "output"
        config = {
            "input_file": str(input_file),
            "tp_mult": 1.5,
            "sl_mult": 1.5,
            "timeout_bars": 10,
            "volatility_span": 20,
            "out_dir": str(output_dir)
        }

        result = run_labeling(config)

        assert result is not None
        assert result["success"] == True
        
        # Check outputs
        output_path = Path(result["labeled_data_path"])
        report_path = output_dir / "labeling_report.json"
        manifest_path = output_dir / "manifest.json"

        assert output_path.exists()
        assert report_path.exists()
        assert manifest_path.exists()

        # Check labeled data
        df_labeled = pd.read_parquet(output_path)
        assert "label" in df_labeled.columns
        assert "ret" in df_labeled.columns
        assert "t_final" in df_labeled.columns
        assert len(df_labeled) == len(sample_bar_data)

        # Check report
        with open(report_path) as f:
            report = json.load(f)
        assert "label_counts" in report
        # Use string keys as they come from JSON
        assert "1" in report["label_counts"] # Take Profit
        assert "-1" in report["label_counts"] # Stop Loss
        assert "0" in report["label_counts"] # Timeout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

