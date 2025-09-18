"""
Test suite for Labeling v2.2 - Enhanced First-Hit-Logic and Volatility Scaling
"""

import pytest
import pandas as pd
import numpy as np
import pathlib
import json
import tempfile
import shutil
from datetime import datetime, timezone

# Import the enhanced module
import sys
sys.path.append('/home/ubuntu/FinPattern-Engine')
from core.labeling import labeling_v22 as labeling_v22

class TestLabelingV22:
    
    @pytest.fixture
    def sample_bars_data(self):
        """Create sample bar data for testing"""
        np.random.seed(42)
        n_bars = 1000
        
        # Generate realistic EUR/USD bar data
        base_time = pd.Timestamp('2025-01-01 09:00:00', tz='UTC')
        times = pd.date_range(base_time, periods=n_bars, freq='1min')
        
        # Realistic price movement
        base_price = 1.1000
        returns = np.random.normal(0, 0.0001, n_bars)
        prices = base_price + returns.cumsum()
        
        # Create OHLC bars
        bars_data = []
        for i, (time, price) in enumerate(zip(times, prices)):
            # Add some intrabar volatility
            high = price + np.random.uniform(0, 0.0005)
            low = price - np.random.uniform(0, 0.0005)
            open_price = prices[i-1] if i > 0 else price
            close_price = price
            
            bars_data.append({
                'symbol': 'EURUSD',
                'timeframe': '1m',
                't_open_ns': int(time.value),
                't_close_ns': int((time + pd.Timedelta(minutes=1)).value),
                'o': open_price,
                'h': high,
                'l': low,
                'c': close_price,
                'o_bid': open_price - 0.00005,
                'o_ask': open_price + 0.00005,
                'c_bid': close_price - 0.00005,
                'c_ask': close_price + 0.00005,
                'spread_mean': 0.0001,
                'n_ticks': np.random.randint(50, 200),
                'v_sum': 0.0,
                'tick_first_id': i * 100,
                'tick_last_id': (i + 1) * 100 - 1,
                'gap_flag': 0
            })
        
        return pd.DataFrame(bars_data)
    
    @pytest.fixture
    def sample_tick_slices(self, temp_workspace):
        """Create sample tick slice data"""
        slice_dir = temp_workspace / "tick_slices_1m"
        slice_dir.mkdir(exist_ok=True)
        
        # Create tick slices for first 10 events
        for event_id in range(10):
            n_ticks = np.random.randint(50, 150)
            base_price = 1.1000 + np.random.normal(0, 0.001)
            
            # Generate tick data for this event
            tick_data = []
            for tick_idx in range(n_ticks):
                price_change = np.random.normal(0, 0.00005)
                mid_price = base_price + price_change
                bid = mid_price - 0.00005
                ask = mid_price + 0.00005
                
                tick_data.append({
                    'event_id': event_id,
                    'tick_sequence': tick_idx,
                    'ts_ns': int(pd.Timestamp('2025-01-01 09:00:00', tz='UTC').value) + event_id * 60_000_000_000 + tick_idx * 1_000_000,
                    'time_from_bar_start_ns': tick_idx * 1_000_000,
                    'bid': bid,
                    'ask': ask,
                    'mid_price': mid_price
                })
            
            tick_df = pd.DataFrame(tick_data)
            slice_file = slice_dir / f"ticks_event_{event_id:06d}.parquet"
            tick_df.to_parquet(slice_file, index=False)
        
        return slice_dir
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for testing"""
        temp_dir = tempfile.mkdtemp()
        yield pathlib.Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    def test_enhanced_volatility_calculation(self, sample_bars_data, temp_workspace):
        """Test EWMA volatility calculation and dynamic scaling"""
        
        # Save sample data
        bars_path = temp_workspace / "bars_1m.parquet"
        sample_bars_data.to_parquet(bars_path, index=False)
        
        config = {
            "bars_path": str(bars_path),
            "out_dir": str(temp_workspace / "output"),
            "events": [{"index": i} for i in range(10, 100, 10)],  # Every 10 bars
            "tp_vol_multiple": 2.0,
            "sl_vol_multiple": 1.5,
            "vol_lookback": 20,
            "vol_alpha": 0.94,
            "use_tick_slices": False
        }
        
        result = labeling_v22.run(config)
        
        # Verify results
        assert "results_path" in result
        assert "summary_stats" in result
        assert result["module_version"] == "2.2"
        
        # Load and verify results
        results_df = pd.read_parquet(result["results_path"])
        
        # Check volatility columns
        assert "volatility_used" in results_df.columns
        assert "tp_level" in results_df.columns
        assert "sl_level" in results_df.columns
        
        # Verify volatility is reasonable
        assert results_df["volatility_used"].min() > 0
        assert results_df["volatility_used"].max() < 0.01  # Should be reasonable for EUR/USD
        
        # Verify TP/SL levels are calculated correctly
        expected_tp = 2.0 * results_df["volatility_used"]
        expected_sl = 1.5 * results_df["volatility_used"]
        
        np.testing.assert_array_almost_equal(results_df["tp_level"], expected_tp)
        np.testing.assert_array_almost_equal(results_df["sl_level"], expected_sl)
    
    def test_first_hit_logic_with_tick_slices(self, sample_bars_data, sample_tick_slices, temp_workspace):
        """Test First-Hit-Logic using tick slice data"""
        
        # Save sample data
        bars_path = temp_workspace / "bars_1m.parquet"
        sample_bars_data.to_parquet(bars_path, index=False)
        
        config = {
            "bars_path": str(bars_path),
            "tick_slices_dir": str(sample_tick_slices),
            "out_dir": str(temp_workspace / "output"),
            "events": [{"index": i} for i in range(5)],  # First 5 events (have tick slices)
            "tp_vol_multiple": 1.0,
            "sl_vol_multiple": 1.0,
            "side": 1,  # Long only
            "use_tick_slices": True
        }
        
        result = labeling_v22.run(config)
        
        # Verify tick enhancement was used
        assert result["tick_enhanced"] == True
        
        # Load results
        results_df = pd.read_parquet(result["results_path"])
        
        # Verify results structure
        assert len(results_df) == 5
        assert "hit_type" in results_df.columns
        assert "exit_time_ns" in results_df.columns
        assert "duration_seconds" in results_df.columns
        
        # Check that we have some hits (not all timeouts)
        hit_types = results_df["hit_type"].values
        assert not all(ht == 0 for ht in hit_types)  # Not all timeouts
    
    def test_timeout_in_seconds(self, sample_bars_data, temp_workspace):
        """Test timeout functionality in seconds"""
        
        bars_path = temp_workspace / "bars_1m.parquet"
        sample_bars_data.to_parquet(bars_path, index=False)
        
        config = {
            "bars_path": str(bars_path),
            "out_dir": str(temp_workspace / "output"),
            "events": [{"index": i} for i in range(10, 50, 10)],
            "tp_vol_multiple": 10.0,  # Very high TP (unlikely to hit)
            "sl_vol_multiple": 10.0,  # Very high SL (unlikely to hit)
            "timeout_bars": 100,  # High bar timeout
            "timeout_seconds": 300,  # 5 minutes timeout
            "side": 1
        }
        
        result = labeling_v22.run(config)
        results_df = pd.read_parquet(result["results_path"])
        
        # Most should be timeouts due to high TP/SL levels
        timeout_count = (results_df["hit_type"] == 0).sum()
        assert timeout_count > 0
        
        # Check duration is reasonable (should be around 5 minutes for timeouts)
        timeout_durations = results_df[results_df["hit_type"] == 0]["duration_seconds"]
        if len(timeout_durations) > 0:
            # Should be close to 300 seconds (5 minutes) or 100 bars * 60 seconds = 6000 seconds
            # The timeout is the minimum of bar timeout and time timeout
            assert timeout_durations.max() <= 6100  # Allow some tolerance for 100 bars
    
    def test_side_support(self, sample_bars_data, temp_workspace):
        """Test enhanced side support (long/short/both)"""
        
        bars_path = temp_workspace / "bars_1m.parquet"
        sample_bars_data.to_parquet(bars_path, index=False)
        
        # Test long side
        config_long = {
            "bars_path": str(bars_path),
            "out_dir": str(temp_workspace / "output_long"),
            "events": [{"index": i} for i in range(10, 30, 5)],
            "tp_vol_multiple": 1.5,
            "sl_vol_multiple": 1.5,
            "side": 1,  # Long
            "timeout_bars": 20
        }
        
        result_long = labeling_v22.run(config_long)
        results_long = pd.read_parquet(result_long["results_path"])
        
        # Test short side
        config_short = {
            "bars_path": str(bars_path),
            "out_dir": str(temp_workspace / "output_short"),
            "events": [{"index": i} for i in range(10, 30, 5)],
            "tp_vol_multiple": 1.5,
            "sl_vol_multiple": 1.5,
            "side": -1,  # Short
            "timeout_bars": 20
        }
        
        result_short = labeling_v22.run(config_short)
        results_short = pd.read_parquet(result_short["results_path"])
        
        # Verify both work
        assert len(results_long) > 0
        assert len(results_short) > 0
        
        # Returns should generally be opposite for same events
        # (what's profitable for long should be loss for short)
        assert results_long["return"].sum() != results_short["return"].sum()
    
    def test_enhanced_summary_statistics(self, sample_bars_data, temp_workspace):
        """Test enhanced summary statistics and reporting"""
        
        bars_path = temp_workspace / "bars_1m.parquet"
        sample_bars_data.to_parquet(bars_path, index=False)
        
        config = {
            "bars_path": str(bars_path),
            "out_dir": str(temp_workspace / "output"),
            "events": [{"index": i} for i in range(20, 100, 10)],
            "tp_vol_multiple": 2.0,
            "sl_vol_multiple": 1.5
        }
        
        result = labeling_v22.run(config)
        
        # Check summary statistics
        summary = result["summary_stats"]
        
        required_stats = [
            "total_events", "profitable_events", "loss_events", "timeout_events",
            "win_rate", "avg_return", "avg_duration_seconds", "avg_volatility"
        ]
        
        for stat in required_stats:
            assert stat in summary
        
        # Verify counts add up
        total = summary["total_events"]
        profitable = summary["profitable_events"]
        loss = summary["loss_events"]
        timeout = summary["timeout_events"]
        
        assert profitable + loss + timeout == total
        
        # Verify win rate calculation
        expected_win_rate = profitable / total if total > 0 else 0
        assert abs(summary["win_rate"] - expected_win_rate) < 0.001
    
    def test_backward_compatibility(self, sample_bars_data, temp_workspace):
        """Test backward compatibility with v2.1 configurations"""
        
        bars_path = temp_workspace / "bars_1m.parquet"
        sample_bars_data.to_parquet(bars_path, index=False)
        
        # Use v2.1 style configuration
        config_v21 = {
            "bars_path": str(bars_path),
            "out_dir": str(temp_workspace / "output"),
            "events": [{"index": i} for i in range(10, 50, 10)],
            "tp_vol_multiple": 2.0,
            "sl_vol_multiple": 2.0,
            "timeout_bars": 10,
            "side": 1
            # No v2.2 specific parameters
        }
        
        result = labeling_v22.run(config_v21)
        
        # Should work without errors
        assert "results_path" in result
        assert result["module_version"] == "2.2"
        
        results_df = pd.read_parquet(result["results_path"])
        assert len(results_df) > 0

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
