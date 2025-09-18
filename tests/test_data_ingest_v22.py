"""
Test suite for DataIngest v2.2 - Enhanced Tick-Slice-Export functionality
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
from core.data_ingest import data_ingest_v22 as di_v22

class TestDataIngestV22:
    
    @pytest.fixture
    def sample_tick_data(self):
        """Create sample tick data for testing"""
        np.random.seed(42)
        n_ticks = 1000
        
        # Generate realistic EUR/USD tick data
        base_time = pd.Timestamp('2025-01-01 09:00:00', tz='UTC')
        timestamps = pd.date_range(base_time, periods=n_ticks, freq='1s')
        
        # Realistic EUR/USD prices around 1.1000
        base_price = 1.1000
        price_changes = np.random.normal(0, 0.0001, n_ticks).cumsum()
        mid_prices = base_price + price_changes
        
        # Realistic spreads (0.5-2 pips)
        spreads = np.random.uniform(0.00005, 0.0002, n_ticks)
        
        bids = mid_prices - spreads / 2
        asks = mid_prices + spreads / 2
        
        return pd.DataFrame({
            'timestamp': timestamps,
            'bid': bids,
            'ask': asks
        })
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for testing"""
        temp_dir = tempfile.mkdtemp()
        yield pathlib.Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    def test_enhanced_tick_slice_export(self, sample_tick_data, temp_workspace):
        """Test the enhanced tick slice export functionality"""
        
        # Save sample data
        csv_path = temp_workspace / "test_data.csv"
        sample_tick_data.to_csv(csv_path, index=False)
        
        # Configuration for v2.2
        config = {
            "csv_path": str(csv_path),
            "out_dir": str(temp_workspace / "output"),
            "symbol": "EURUSD",
            "price_basis": "mid",
            "pip_size": 0.0001,
            "export_slices": True,
            "max_gap_seconds": 300,
            "bar_frames": [
                {"type": "time", "unit": "1m"},
                {"type": "tick", "count": 100}
            ]
        }
        
        # Run enhanced DataIngest
        result = di_v22.run(config)
        
        # Verify basic results
        assert "symbol" in result
        assert result["symbol"] == "EURUSD"
        assert "frames" in result
        assert "module_version" in result
        assert result["module_version"] == "2.2"
        
        # Check output directory structure
        out_dir = pathlib.Path(config["out_dir"])
        assert out_dir.exists()
        assert (out_dir / "manifest.json").exists()
        assert (out_dir / "quality_report.json").exists()
        
        # Verify enhanced manifest
        with open(out_dir / "manifest.json") as f:
            manifest = json.load(f)
        
        assert manifest["module_version"] == "2.2"
        assert "export_slices" in manifest
        assert manifest["export_slices"] == True
        assert "compression_enabled" in manifest
        assert "performance" in manifest
        
        # Check tick slice directories
        if "1m" in result["frames"]:
            slice_info = result["frames"]["1m"]["tick_slices"]
            assert slice_info["enabled"] == True
            
            slice_dir = out_dir / slice_info["slice_directory"]
            assert slice_dir.exists()
            assert (slice_dir / "slice_manifest.json").exists()
            
            # Verify slice manifest
            with open(slice_dir / "slice_manifest.json") as f:
                slice_manifest = json.load(f)
            
            assert "statistics" in slice_manifest
            assert "files" in slice_manifest
            assert slice_manifest["statistics"]["total_events"] > 0
            
            # Check individual slice files
            for file_info in slice_manifest["files"][:3]:  # Check first 3 files
                slice_file = out_dir / file_info["file"]
                assert slice_file.exists()
                
                # Load and verify slice data
                slice_df = pd.read_parquet(slice_file)
                assert "event_id" in slice_df.columns
                assert "tick_sequence" in slice_df.columns
                assert "time_from_bar_start_ns" in slice_df.columns
                assert "mid_price" in slice_df.columns
                assert len(slice_df) == file_info["tick_count"]
    
    def test_compression_and_optimization(self, sample_tick_data, temp_workspace):
        """Test compression and memory optimization features"""
        
        csv_path = temp_workspace / "test_data.csv"
        sample_tick_data.to_csv(csv_path, index=False)
        
        config = {
            "csv_path": str(csv_path),
            "out_dir": str(temp_workspace / "output"),
            "symbol": "EURUSD",
            "export_slices": True,
            "bar_frames": [{"type": "tick", "count": 50}]
        }
        
        result = di_v22.run(config)
        out_dir = pathlib.Path(config["out_dir"])
        
        # Check that parquet files are compressed
        bars_file = out_dir / "bars_50tick.parquet"
        assert bars_file.exists()
        
        # Verify file is reasonably small (compression working)
        file_size = bars_file.stat().st_size
        assert file_size < len(sample_tick_data) * 100  # Should be much smaller than raw data
    
    def test_enhanced_quality_report(self, sample_tick_data, temp_workspace):
        """Test enhanced quality reporting"""
        
        csv_path = temp_workspace / "test_data.csv"
        sample_tick_data.to_csv(csv_path, index=False)
        
        config = {
            "csv_path": str(csv_path),
            "out_dir": str(temp_workspace / "output"),
            "symbol": "EURUSD",
            "bar_frames": [{"type": "time", "unit": "1m"}]
        }
        
        result = di_v22.run(config)
        
        # Load and verify enhanced quality report
        with open(result["quality_report"]) as f:
            quality = json.load(f)
        
        # Check enhanced spread statistics
        assert "spread_stats" in quality
        spread_stats = quality["spread_stats"]
        assert "mean" in spread_stats
        assert "std" in spread_stats
        assert "p50" in spread_stats
        assert "p95" in spread_stats
        assert "p99" in spread_stats
        
        # Check time range information
        assert "time_range" in quality
        time_range = quality["time_range"]
        assert "start" in time_range
        assert "end" in time_range
        assert "duration_hours" in time_range
        assert time_range["duration_hours"] > 0
    
    def test_event_based_organization(self, sample_tick_data, temp_workspace):
        """Test event-based tick slice organization for First-Hit-Logic"""
        
        csv_path = temp_workspace / "test_data.csv"
        sample_tick_data.to_csv(csv_path, index=False)
        
        config = {
            "csv_path": str(csv_path),
            "out_dir": str(temp_workspace / "output"),
            "symbol": "EURUSD",
            "export_slices": True,
            "bar_frames": [{"type": "tick", "count": 100}]
        }
        
        result = di_v22.run(config)
        
        # Get tick slice information
        slice_info = result["frames"]["100t"]["tick_slices"]
        out_dir = pathlib.Path(config["out_dir"])
        slice_dir = out_dir / slice_info["slice_directory"]
        
        # Load slice manifest
        with open(slice_dir / "slice_manifest.json") as f:
            slice_manifest = json.load(f)
        
        # Verify event organization
        assert len(slice_manifest["files"]) > 0
        
        # Check first event slice
        first_file = slice_manifest["files"][0]
        slice_file = out_dir / first_file["file"]
        slice_df = pd.read_parquet(slice_file)
        
        # Verify event-based structure
        assert slice_df["event_id"].nunique() == 1  # Single event per file
        assert "tick_sequence" in slice_df.columns
        assert slice_df["tick_sequence"].is_monotonic_increasing
        
        # Verify timing information for First-Hit-Logic
        if len(slice_df) > 1:
            assert "time_from_bar_start_ns" in slice_df.columns
            assert slice_df["time_from_bar_start_ns"].iloc[0] == 0
            assert slice_df["time_from_bar_start_ns"].is_monotonic_increasing
    
    def test_backward_compatibility(self, sample_tick_data, temp_workspace):
        """Test that v2.2 maintains backward compatibility"""
        
        csv_path = temp_workspace / "test_data.csv"
        sample_tick_data.to_csv(csv_path, index=False)
        
        # Test with export_slices disabled (v2.1 behavior)
        config = {
            "csv_path": str(csv_path),
            "out_dir": str(temp_workspace / "output"),
            "symbol": "EURUSD",
            "export_slices": False,
            "bar_frames": [{"type": "time", "unit": "1m"}]
        }
        
        result = di_v22.run(config)
        
        # Should still work but without tick slices
        assert "frames" in result
        if "1m" in result["frames"]:
            slice_info = result["frames"]["1m"]["tick_slices"]
            assert slice_info["enabled"] == False

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
