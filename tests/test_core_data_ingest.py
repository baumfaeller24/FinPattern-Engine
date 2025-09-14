"""
Tests for the enhanced DataIngest module (core version)
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import shutil
import json
from datetime import datetime, timedelta

from core.data_ingest.data_ingest import run
from core.data_ingest import errors as E


class TestCoreDataIngest:
    """Test suite for enhanced DataIngest module."""
    
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
            'timestamp': [t.isoformat() + 'Z' for t in timestamps],
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
            'out_dir': str(temp_dir / 'output'),
            'csv': {
                'path': str(temp_dir / 'test_data.csv')
            },
            'symbol': 'EURUSD',
            'price_basis': 'mid',
            'max_missing_gap_seconds': 60,
            'trim_weekend': True,
            'bar_frames': [
                {'type': 'time', 'unit': '1m'},
                {'type': 'tick', 'count': 100}
            ]
        }
    
    def test_demo_mode(self, temp_dir):
        """Test demo mode with built-in sample data."""
        config = {
            'out_dir': str(temp_dir / 'output'),
            'demo': True,
            'symbol': 'EURUSD',
            'bar_frames': [
                {'type': 'time', 'unit': '1m'}
            ]
        }
        
        result = run(config)
        
        assert 'symbol' in result
        assert 'frames' in result
        assert 'manifest' in result
        assert result['symbol'] == 'EURUSD'
        
        # Check that output files exist
        output_dir = Path(config['out_dir'])
        assert (output_dir / 'manifest.json').exists()
        assert (output_dir / 'quality_report.json').exists()
        assert (output_dir / 'progress.jsonl').exists()
    
    def test_full_pipeline_with_time_bars(self, sample_tick_data, sample_config, temp_dir):
        """Test complete pipeline with time bars."""
        # Save sample data as CSV
        csv_path = temp_dir / 'test_data.csv'
        sample_tick_data.to_csv(csv_path, index=False)
        
        result = run(sample_config)
        
        # Check return structure
        assert 'symbol' in result
        assert 'frames' in result
        assert 'quality_report' in result
        assert 'manifest' in result
        assert 'log' in result
        
        # Check that files were created
        output_dir = Path(sample_config['out_dir'])
        assert output_dir.exists()
        
        # Check manifest
        manifest_path = Path(result['manifest'])
        assert manifest_path.exists()
        
        with open(manifest_path) as f:
            manifest = json.load(f)
        
        assert manifest['module'] == 'data_ingest'
        assert manifest['symbol'] == 'EURUSD'
        assert 'module_version' in manifest
        assert 'schema_version' in manifest
        assert 'bar_rules_id' in manifest
        
        # Check quality report
        quality_path = Path(result['quality_report'])
        assert quality_path.exists()
        
        with open(quality_path) as f:
            quality = json.load(f)
        
        assert 'n_raw_rows' in quality
        assert 'gap_coverage_percent' in quality
        assert 'spread_stats' in quality
        
        # Check progress log
        log_path = Path(result['log'])
        assert log_path.exists()
        
        # Read progress log
        with open(log_path) as f:
            log_lines = [json.loads(line) for line in f]
        
        assert len(log_lines) > 0
        assert log_lines[0]['module'] == 'data_ingest'
        assert log_lines[-1]['percent'] == 100
    
    def test_tick_bars_generation(self, sample_tick_data, sample_config, temp_dir):
        """Test tick bar generation."""
        # Save sample data as CSV
        csv_path = temp_dir / 'test_data.csv'
        sample_tick_data.to_csv(csv_path, index=False)
        
        # Configure for tick bars only
        sample_config['bar_frames'] = [
            {'type': 'tick', 'count': 100}
        ]
        
        result = run(sample_config)
        
        # Check that tick bars were created
        assert '100t' in result['frames']
        
        # Load and verify tick bars
        tick_bars_path = result['frames']['100t']
        bars = pd.read_parquet(tick_bars_path)
        
        # Check schema
        expected_columns = [
            'symbol', 'frame', 't_open_ns', 't_close_ns',
            'o', 'h', 'l', 'c',
            'o_bid', 'o_ask', 'c_bid', 'c_ask',
            'spread_mean', 'n_ticks', 'v_sum',
            'tick_first_id', 'tick_last_id', 'gap_flag'
        ]
        
        for col in expected_columns:
            assert col in bars.columns
        
        # Check that each bar has 100 ticks (except possibly the last one)
        assert (bars['n_ticks'] == 100).all()
        assert (bars['frame'] == '100t').all()
        assert (bars['symbol'] == 'EURUSD').all()
        
        # Check OHLC consistency
        assert (bars['h'] >= bars['l']).all()
        assert (bars['o'] >= bars['l']).all()
        assert (bars['o'] <= bars['h']).all()
        assert (bars['c'] >= bars['l']).all()
        assert (bars['c'] <= bars['h']).all()
    
    def test_price_basis_options(self, sample_tick_data, sample_config, temp_dir):
        """Test different price basis options."""
        csv_path = temp_dir / 'test_data.csv'
        sample_tick_data.to_csv(csv_path, index=False)
        
        for basis in ['mid', 'bid', 'ask']:
            config = sample_config.copy()
            config['price_basis'] = basis
            config['out_dir'] = str(temp_dir / f'output_{basis}')
            
            result = run(config)
            
            # Check that it completed successfully
            assert 'symbol' in result
            assert result['symbol'] == 'EURUSD'
            
            # Check manifest contains correct basis
            with open(result['manifest']) as f:
                manifest = json.load(f)
            assert manifest['price_basis'] == basis
    
    def test_gap_analysis(self, temp_dir):
        """Test gap analysis functionality."""
        # Create data with intentional gaps
        timestamps = []
        base_time = datetime(2025, 1, 1, 9, 0, 0)
        
        # Normal data for 5 minutes
        for i in range(300):
            timestamps.append(base_time + timedelta(seconds=i))
        
        # 2-minute gap
        gap_start = base_time + timedelta(seconds=300)
        gap_end = gap_start + timedelta(minutes=2)
        
        # Continue after gap
        for i in range(300):
            timestamps.append(gap_end + timedelta(seconds=i))
        
        # Create tick data
        base_price = 1.1000
        np.random.seed(42)
        price_changes = np.random.normal(0, 0.0001, len(timestamps))
        mid_prices = base_price + np.cumsum(price_changes)
        spread = 0.0001
        
        data = pd.DataFrame({
            'timestamp': [t.isoformat() + 'Z' for t in timestamps],
            'bid': mid_prices - spread/2,
            'ask': mid_prices + spread/2
        })
        
        csv_path = temp_dir / 'test_data.csv'
        data.to_csv(csv_path, index=False)
        
        config = {
            'out_dir': str(temp_dir / 'output'),
            'csv': {'path': str(csv_path)},
            'symbol': 'EURUSD',
            'max_missing_gap_seconds': 60,  # 1 minute threshold
            'bar_frames': []
        }
        
        result = run(config)
        
        # Check quality report for gap detection
        with open(result['quality_report']) as f:
            quality = json.load(f)
        
        assert 'gap_items' in quality
        assert len(quality['gap_items']) > 0  # Should detect the 2-minute gap
        assert quality['gap_coverage_percent'] < 100  # Coverage should be less than 100%
    
    def test_weekend_trimming(self, temp_dir):
        """Test weekend data trimming."""
        # Create data spanning a weekend
        start_time = datetime(2025, 1, 3, 22, 0, 0)  # Friday evening
        timestamps = []
        
        # Add data through weekend
        for i in range(72 * 3600):  # 72 hours of data (includes weekend)
            timestamps.append(start_time + timedelta(seconds=i))
        
        base_price = 1.1000
        np.random.seed(42)
        price_changes = np.random.normal(0, 0.0001, len(timestamps))
        mid_prices = base_price + np.cumsum(price_changes)
        spread = 0.0001
        
        data = pd.DataFrame({
            'timestamp': [t.isoformat() + 'Z' for t in timestamps],
            'bid': mid_prices - spread/2,
            'ask': mid_prices + spread/2
        })
        
        csv_path = temp_dir / 'test_data.csv'
        data.to_csv(csv_path, index=False)
        
        # Test with weekend trimming enabled
        config = {
            'out_dir': str(temp_dir / 'output_trim'),
            'csv': {'path': str(csv_path)},
            'symbol': 'EURUSD',
            'trim_weekend': True,
            'bar_frames': []
        }
        
        result_trim = run(config)
        
        # Test with weekend trimming disabled
        config['out_dir'] = str(temp_dir / 'output_no_trim')
        config['trim_weekend'] = False
        
        result_no_trim = run(config)
        
        # Compare quality reports
        with open(result_trim['quality_report']) as f:
            quality_trim = json.load(f)
        
        with open(result_no_trim['quality_report']) as f:
            quality_no_trim = json.load(f)
        
        # Trimmed version should have fewer rows
        assert quality_trim['n_raw_rows'] < quality_no_trim['n_raw_rows']
    
    def test_error_handling_missing_columns(self, temp_dir):
        """Test error handling for missing required columns."""
        # Create data with missing columns
        bad_data = pd.DataFrame({
            'timestamp': ['2025-01-01T09:00:00Z'],
            'price': [1.1000]  # Missing bid/ask
        })
        
        csv_path = temp_dir / 'bad_data.csv'
        bad_data.to_csv(csv_path, index=False)
        
        config = {
            'out_dir': str(temp_dir / 'output'),
            'csv': {'path': str(csv_path)},
            'symbol': 'EURUSD',
            'bar_frames': []
        }
        
        with pytest.raises(ValueError, match=E.MISSING_COLUMN):
            run(config)
    
    def test_error_handling_negative_spread(self, temp_dir):
        """Test error handling for negative spreads."""
        # Create data with negative spread (ask < bid)
        bad_data = pd.DataFrame({
            'timestamp': ['2025-01-01T09:00:00Z'],
            'bid': [1.1000],
            'ask': [1.0999]  # Ask < Bid
        })
        
        csv_path = temp_dir / 'bad_data.csv'
        bad_data.to_csv(csv_path, index=False)
        
        config = {
            'out_dir': str(temp_dir / 'output'),
            'csv': {'path': str(csv_path)},
            'symbol': 'EURUSD',
            'bar_frames': []
        }
        
        with pytest.raises(ValueError, match=E.NEGATIVE_SPREAD):
            run(config)
    
    def test_progress_logging(self, sample_tick_data, sample_config, temp_dir):
        """Test progress logging functionality."""
        csv_path = temp_dir / 'test_data.csv'
        sample_tick_data.to_csv(csv_path, index=False)
        
        result = run(sample_config)
        
        # Read and verify progress log
        log_path = Path(result['log'])
        with open(log_path) as f:
            log_lines = [json.loads(line) for line in f]
        
        # Check log structure
        for line in log_lines:
            assert 'timestamp' in line
            assert 'module' in line
            assert 'step' in line
            assert 'percent' in line
            assert 'message' in line
            assert line['module'] == 'data_ingest'
        
        # Check progress sequence
        percentages = [line['percent'] for line in log_lines]
        assert percentages[0] == 1  # Should start with init
        assert percentages[-1] == 100  # Should end with done
        
        # Check that percentages are non-decreasing
        for i in range(1, len(percentages)):
            assert percentages[i] >= percentages[i-1]
