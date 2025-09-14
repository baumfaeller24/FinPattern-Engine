"""
Tests for DataIngest module
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import shutil
from datetime import datetime, timedelta

from src.modules.data_ingest import DataIngest


class TestDataIngest:
    """Test suite for DataIngest module."""
    
    @pytest.fixture
    def sample_tick_data(self):
        """Create sample tick data for testing."""
        start_time = datetime(2025, 1, 1, 9, 0, 0)
        timestamps = [start_time + timedelta(seconds=i) for i in range(1000)]
        
        # Generate realistic EUR/USD tick data
        base_price = 1.1000
        np.random.seed(42)
        price_changes = np.random.normal(0, 0.0001, len(timestamps))
        mid_prices = base_price + np.cumsum(price_changes)
        
        # Create bid/ask with spread
        spread = 0.0001  # 1 pip spread
        bids = mid_prices - spread/2
        asks = mid_prices + spread/2
        
        data = pd.DataFrame({
            'timestamp': timestamps,
            'bid': bids,
            'ask': asks
        })
        
        return data
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test outputs."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def sample_config(self, temp_dir):
        """Create sample configuration for testing."""
        return {
            'raw_data_path': str(temp_dir / 'test_data.csv'),
            'bar_intervals': [
                {'type': 'time', 'unit': '1min'},
                {'type': 'tick', 'count': 100}
            ],
            'out_dir': str(temp_dir / 'output'),
            'max_missing_gap_seconds': 60
        }
    
    def test_data_ingest_initialization(self):
        """Test DataIngest module initialization."""
        ingest = DataIngest()
        assert ingest.config is None
        assert ingest.raw_data is None
        assert ingest.normalized_data is None
        assert ingest.bars == {}
        assert ingest.quality_report == {}
    
    def test_load_csv_data(self, sample_tick_data, sample_config, temp_dir):
        """Test loading CSV data."""
        # Save sample data as CSV
        csv_path = temp_dir / 'test_data.csv'
        sample_tick_data.to_csv(csv_path, index=False)
        
        ingest = DataIngest()
        ingest.config = sample_config
        ingest._load_raw_data()
        
        assert ingest.raw_data is not None
        assert len(ingest.raw_data) == len(sample_tick_data)
        assert 'timestamp' in ingest.raw_data.columns
        assert 'bid' in ingest.raw_data.columns
        assert 'ask' in ingest.raw_data.columns
    
    def test_data_normalization(self, sample_tick_data, sample_config, temp_dir):
        """Test data normalization."""
        # Save sample data as CSV
        csv_path = temp_dir / 'test_data.csv'
        sample_tick_data.to_csv(csv_path, index=False)
        
        ingest = DataIngest()
        ingest.config = sample_config
        ingest._load_raw_data()
        ingest._normalize_data()
        
        assert ingest.normalized_data is not None
        assert 'mid' in ingest.normalized_data.columns
        assert pd.api.types.is_datetime64_any_dtype(ingest.normalized_data['timestamp'])
        
        # Check mid price calculation
        expected_mid = (ingest.normalized_data['bid'] + ingest.normalized_data['ask']) / 2
        pd.testing.assert_series_equal(ingest.normalized_data['mid'], expected_mid)
    
    def test_quality_check(self, sample_tick_data, sample_config, temp_dir):
        """Test quality check functionality."""
        # Save sample data as CSV
        csv_path = temp_dir / 'test_data.csv'
        sample_tick_data.to_csv(csv_path, index=False)
        
        ingest = DataIngest()
        ingest.config = sample_config
        ingest._load_raw_data()
        ingest._normalize_data()
        ingest._quality_check()
        
        assert ingest.quality_report is not None
        assert 'total_ticks' in ingest.quality_report
        assert 'date_range' in ingest.quality_report
        assert 'price_stats' in ingest.quality_report
        assert 'gaps' in ingest.quality_report
        assert 'outliers' in ingest.quality_report
        
        assert ingest.quality_report['total_ticks'] == len(sample_tick_data)
    
    def test_time_bar_generation(self, sample_tick_data, sample_config, temp_dir):
        """Test time-based bar generation."""
        # Save sample data as CSV
        csv_path = temp_dir / 'test_data.csv'
        sample_tick_data.to_csv(csv_path, index=False)
        
        ingest = DataIngest()
        ingest.config = sample_config
        ingest._load_raw_data()
        ingest._normalize_data()
        
        # Generate time bars
        bar_config = {'type': 'time', 'unit': '1min'}
        ingest._generate_time_bars(bar_config)
        
        assert 'bars_1min' in ingest.bars
        bars = ingest.bars['bars_1min']
        
        # Check OHLCV structure
        expected_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        for col in expected_columns:
            assert col in bars.columns
        
        # Check that high >= low for all bars
        assert (bars['high'] >= bars['low']).all()
        
        # Check that open and close are within high/low range
        assert (bars['open'] >= bars['low']).all()
        assert (bars['open'] <= bars['high']).all()
        assert (bars['close'] >= bars['low']).all()
        assert (bars['close'] <= bars['high']).all()
    
    def test_tick_bar_generation(self, sample_tick_data, sample_config, temp_dir):
        """Test tick-based bar generation."""
        # Save sample data as CSV
        csv_path = temp_dir / 'test_data.csv'
        sample_tick_data.to_csv(csv_path, index=False)
        
        ingest = DataIngest()
        ingest.config = sample_config
        ingest._load_raw_data()
        ingest._normalize_data()
        
        # Generate tick bars
        bar_config = {'type': 'tick', 'count': 100}
        ingest._generate_tick_bars(bar_config)
        
        assert 'bars_100tick' in ingest.bars
        bars = ingest.bars['bars_100tick']
        
        # Check that each bar has exactly 100 volume (except possibly the last one)
        assert (bars['volume'] == 100).all()
        
        # Check expected number of bars
        expected_bars = len(sample_tick_data) // 100
        assert len(bars) == expected_bars
    
    def test_full_pipeline(self, sample_tick_data, sample_config, temp_dir):
        """Test complete DataIngest pipeline."""
        # Save sample data as CSV
        csv_path = temp_dir / 'test_data.csv'
        sample_tick_data.to_csv(csv_path, index=False)
        
        ingest = DataIngest()
        result = ingest.run(sample_config)
        
        # Check return structure
        assert 'bars_paths' in result
        assert 'quality_report' in result
        assert 'raw_normalized' in result
        assert 'config_used' in result
        
        # Check that files were created
        output_dir = Path(sample_config['out_dir'])
        assert output_dir.exists()
        assert (output_dir / 'quality_report.json').exists()
        assert (output_dir / 'raw_norm.parquet').exists()
        assert (output_dir / 'config_used.yaml').exists()
        
        # Check that bar files were created
        for bar_path in result['bars_paths']:
            assert Path(bar_path).exists()
    
    def test_missing_file_error(self, sample_config):
        """Test error handling for missing input file."""
        ingest = DataIngest()
        
        with pytest.raises(FileNotFoundError):
            ingest.run(sample_config)
    
    def test_missing_columns_error(self, sample_config, temp_dir):
        """Test error handling for missing required columns."""
        # Create data with missing columns
        bad_data = pd.DataFrame({
            'timestamp': [datetime.now()],
            'price': [1.1000]  # Missing bid/ask
        })
        
        csv_path = temp_dir / 'test_data.csv'
        bad_data.to_csv(csv_path, index=False)
        
        ingest = DataIngest()
        
        with pytest.raises(ValueError, match="Missing required columns"):
            ingest.run(sample_config)
