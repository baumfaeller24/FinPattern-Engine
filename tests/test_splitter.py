"""
Test suite for Splitter Module - Walk-Forward Validation and Data Splitting
"""

import pytest
import pandas as pd
import numpy as np
import pathlib
import json
import tempfile
import shutil
from datetime import datetime, timezone, timedelta

# Import the splitter module
import sys
sys.path.append('/home/ubuntu/FinPattern-Engine')
from core.splitter import splitter

class TestSplitter:
    
    @pytest.fixture
    def sample_time_series_data(self):
        """Create sample time series data for testing"""
        np.random.seed(42)
        
        # Generate 6 months of minute-level data
        start_date = pd.Timestamp('2025-01-01 09:00:00', tz='UTC')
        end_date = start_date + timedelta(days=180)
        
        # Create business hours only (9 AM to 5 PM, Monday to Friday)
        timestamps = []
        current_date = start_date
        
        while current_date <= end_date:
            if current_date.weekday() < 5:  # Monday to Friday
                for hour in range(9, 17):  # 9 AM to 5 PM
                    for minute in range(0, 60, 5):  # Every 5 minutes
                        timestamps.append(current_date.replace(hour=hour, minute=minute))
            current_date += timedelta(days=1)
        
        n_samples = len(timestamps)
        
        # Generate realistic price data
        base_price = 1.1000
        returns = np.random.normal(0, 0.0001, n_samples)
        prices = base_price + returns.cumsum()
        
        # Add some features
        data = pd.DataFrame({
            'timestamp': timestamps,
            'price': prices,
            'volume': np.random.lognormal(10, 1, n_samples),
            'spread': np.random.uniform(0.00005, 0.0002, n_samples),
            'returns': returns,
            'volatility': np.random.uniform(0.0001, 0.001, n_samples)
        })
        
        return data
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for testing"""
        temp_dir = tempfile.mkdtemp()
        yield pathlib.Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    def test_time_based_split(self, sample_time_series_data, temp_workspace):
        """Test basic time-based splitting"""
        
        # Save sample data
        data_path = temp_workspace / "test_data.parquet"
        sample_time_series_data.to_parquet(data_path, index=False)
        
        config = {
            "data_path": str(data_path),
            "out_dir": str(temp_workspace / "output"),
            "split_method": "time_based",
            "time_column": "timestamp",
            "split_params": {
                "train_ratio": 0.7,
                "val_ratio": 0.15,
                "test_ratio": 0.15
            },
            "run_leakage_audit": True
        }
        
        result = splitter.run(config)
        
        # Verify basic results
        assert result["splits_created"] == 1
        assert result["module_version"] == "1.0"
        assert result["leakage_issues"] == 0  # Should be no leakage
        
        # Check output structure
        out_dir = pathlib.Path(config["out_dir"])
        assert out_dir.exists()
        assert (out_dir / "split_manifest.json").exists()
        assert (out_dir / "split_summary.json").exists()
        
        # Check split directory
        splits_dir = out_dir / "splits" / "split_000"
        assert splits_dir.exists()
        assert (splits_dir / "train_data.parquet").exists()
        assert (splits_dir / "val_data.parquet").exists()
        assert (splits_dir / "test_data.parquet").exists()
        assert (splits_dir / "split_info.json").exists()
        assert (splits_dir / "leakage_report.json").exists()
        
        # Verify split ratios
        train_data = pd.read_parquet(splits_dir / "train_data.parquet")
        val_data = pd.read_parquet(splits_dir / "val_data.parquet")
        test_data = pd.read_parquet(splits_dir / "test_data.parquet")
        
        total_samples = len(train_data) + len(val_data) + len(test_data)
        train_ratio = len(train_data) / total_samples
        val_ratio = len(val_data) / total_samples
        test_ratio = len(test_data) / total_samples
        
        assert abs(train_ratio - 0.7) < 0.05  # Allow 5% tolerance
        assert abs(val_ratio - 0.15) < 0.05
        assert abs(test_ratio - 0.15) < 0.05
    
    def test_walk_forward_split(self, sample_time_series_data, temp_workspace):
        """Test Walk-Forward validation splitting"""
        
        data_path = temp_workspace / "test_data.parquet"
        sample_time_series_data.to_parquet(data_path, index=False)
        
        config = {
            "data_path": str(data_path),
            "out_dir": str(temp_workspace / "output"),
            "split_method": "walk_forward",
            "time_column": "timestamp",
            "split_params": {
                "train_window_days": 30,
                "test_window_days": 10,
                "step_days": 10,
                "min_train_samples": 100
            },
            "run_leakage_audit": True
        }
        
        result = splitter.run(config)
        
        # Should create multiple splits
        assert result["splits_created"] > 1
        assert result["leakage_issues"] == 0  # Should be no leakage
        
        # Check summary statistics
        summary = result["summary_stats"]
        assert "walk_forward_stats" in summary
        assert summary["walk_forward_stats"]["total_windows"] == result["splits_created"]
        
        # Verify temporal order in splits
        manifest_path = pathlib.Path(result["manifest_path"])
        with open(manifest_path) as f:
            manifest = json.load(f)
        
        splits = manifest["splits"]
        
        # Check that splits are in temporal order
        for i in range(len(splits) - 1):
            current_test_end = pd.to_datetime(splits[i]["test_period"]["end"])
            next_test_start = pd.to_datetime(splits[i+1]["test_period"]["start"])
            
            # Next split's test period should start after current split's test period
            # (allowing for overlapping training windows which is normal in walk-forward)
            assert next_test_start >= current_test_end or \
                   abs((next_test_start - current_test_end).days) <= 30  # Allow reasonable overlap
    
    def test_session_aware_split(self, sample_time_series_data, temp_workspace):
        """Test session-aware splitting"""
        
        data_path = temp_workspace / "test_data.parquet"
        sample_time_series_data.to_parquet(data_path, index=False)
        
        config = {
            "data_path": str(data_path),
            "out_dir": str(temp_workspace / "output"),
            "split_method": "session_aware",
            "time_column": "timestamp",
            "split_params": {
                "session_start_hour": 9,
                "session_end_hour": 17,
                "train_sessions": 10,
                "test_sessions": 3
            },
            "run_leakage_audit": True
        }
        
        result = splitter.run(config)
        
        # Should create multiple splits
        assert result["splits_created"] > 0
        
        # Verify session structure
        splits_dir = pathlib.Path(result["splits_directory"])
        first_split_dir = splits_dir / "split_000"
        
        train_data = pd.read_parquet(first_split_dir / "train_data.parquet")
        test_data = pd.read_parquet(first_split_dir / "test_data.parquet")
        
        # All data should be within session hours
        train_data['hour'] = pd.to_datetime(train_data['timestamp']).dt.hour
        test_data['hour'] = pd.to_datetime(test_data['timestamp']).dt.hour
        
        assert train_data['hour'].min() >= 9
        assert train_data['hour'].max() < 17
        assert test_data['hour'].min() >= 9
        assert test_data['hour'].max() < 17
    
    def test_rolling_window_split(self, sample_time_series_data, temp_workspace):
        """Test rolling window splitting"""
        
        data_path = temp_workspace / "test_data.parquet"
        sample_time_series_data.to_parquet(data_path, index=False)
        
        config = {
            "data_path": str(data_path),
            "out_dir": str(temp_workspace / "output"),
            "split_method": "rolling_window",
            "time_column": "timestamp",
            "split_params": {
                "window_size": 1000,
                "test_size": 200,
                "step_size": 100
            },
            "run_leakage_audit": True
        }
        
        result = splitter.run(config)
        
        # Should create multiple splits
        assert result["splits_created"] > 1
        
        # Verify window sizes
        splits_dir = pathlib.Path(result["splits_directory"])
        
        for i in range(min(3, result["splits_created"])):  # Check first 3 splits
            split_dir = splits_dir / f"split_{i:03d}"
            
            train_data = pd.read_parquet(split_dir / "train_data.parquet")
            test_data = pd.read_parquet(split_dir / "test_data.parquet")
            
            assert len(train_data) == 1000
            assert len(test_data) == 200
    
    def test_data_leakage_detection(self, temp_workspace):
        """Test data leakage detection functionality"""
        
        # Create data with intentional leakage
        base_time = pd.Timestamp('2025-01-01', tz='UTC')
        
        # Train data: Jan 1-15
        train_data = pd.DataFrame({
            'timestamp': pd.date_range(base_time, periods=15, freq='D'),
            'price': np.random.randn(15),
            'feature1': np.random.randn(15)
        })
        
        # Test data: Jan 10-25 (overlaps with train)
        test_data = pd.DataFrame({
            'timestamp': pd.date_range(base_time + timedelta(days=9), periods=15, freq='D'),
            'price': np.random.randn(15),
            'feature1': np.random.randn(15)
        })
        
        # Test leakage detection
        leakage_report = splitter.detect_data_leakage(train_data, test_data, "timestamp")
        
        # Should detect temporal leakage
        assert leakage_report["has_leakage"] == True
        assert leakage_report["temporal_leakage"] == True
        assert len(leakage_report["issues"]) > 0
        
        # Test with clean data
        clean_test_data = pd.DataFrame({
            'timestamp': pd.date_range(base_time + timedelta(days=20), periods=10, freq='D'),
            'price': np.random.randn(10),
            'feature1': np.random.randn(10)
        })
        
        clean_report = splitter.detect_data_leakage(train_data, clean_test_data, "timestamp")
        assert clean_report["has_leakage"] == False
        assert clean_report["temporal_leakage"] == False
    
    def test_data_splitter_class(self, sample_time_series_data):
        """Test the DataSplitter class directly"""
        
        splitter_obj = splitter.DataSplitter(sample_time_series_data, "timestamp")
        
        # Test time-based split
        time_split = splitter_obj.time_based_split(0.6, 0.2, 0.2)
        assert time_split["split_type"] == "time_based"
        assert len(time_split["train_indices"]) > 0
        assert len(time_split["val_indices"]) > 0
        assert len(time_split["test_indices"]) > 0
        
        # Test walk-forward split
        wf_splits = splitter_obj.walk_forward_split(
            train_window_days=30, 
            test_window_days=10, 
            step_days=15
        )
        assert len(wf_splits) > 0
        assert all(split["split_type"] == "walk_forward" for split in wf_splits)
        
        # Test rolling window split
        rolling_splits = splitter_obj.rolling_window_split(
            window_size=500, 
            test_size=100, 
            step_size=50
        )
        assert len(rolling_splits) > 0
        assert all(split["split_type"] == "rolling_window" for split in rolling_splits)
    
    def test_error_handling(self, temp_workspace):
        """Test error handling and edge cases"""
        
        # Test with non-existent file
        config = {
            "data_path": str(temp_workspace / "nonexistent.parquet"),
            "out_dir": str(temp_workspace / "output"),
            "split_method": "time_based"
        }
        
        with pytest.raises(FileNotFoundError):
            splitter.run(config)
        
        # Test with invalid split method
        sample_data = pd.DataFrame({
            'timestamp': pd.date_range('2025-01-01', periods=100, freq='H'),
            'value': np.random.randn(100)
        })
        
        data_path = temp_workspace / "test_data.parquet"
        sample_data.to_parquet(data_path, index=False)
        
        config = {
            "data_path": str(data_path),
            "out_dir": str(temp_workspace / "output"),
            "split_method": "invalid_method"
        }
        
        with pytest.raises(ValueError):
            splitter.run(config)
        
        # Test with invalid ratios for time-based split
        config = {
            "data_path": str(data_path),
            "out_dir": str(temp_workspace / "output"),
            "split_method": "time_based",
            "split_params": {
                "train_ratio": 0.5,
                "val_ratio": 0.3,
                "test_ratio": 0.3  # Sum > 1.0
            }
        }
        
        with pytest.raises(ValueError):
            splitter.run(config)

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
