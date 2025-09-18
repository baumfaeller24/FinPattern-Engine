"""
Tests for Module 3: FeatureEngine

This module tests the technical analysis feature generation functionality.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import json
import os

# Import from our project
from core.feature_engine.feature_engine import (
    run as run_feature_engine,
    add_momentum_features,
    add_trend_features,
    add_volatility_features,
    add_volume_features,
    standardize_ohlc_columns
)


class TestFeatureEngineCore:
    """Test core FeatureEngine functionality."""
    
    @pytest.fixture
    def sample_labeled_data(self):
        """Create sample labeled OHLC data for testing."""
        np.random.seed(42)
        n_bars = 100
        
        # Generate realistic price data
        base_price = 1.10
        price_changes = np.random.normal(0, 0.001, n_bars)
        prices = [base_price]
        
        for change in price_changes:
            new_price = prices[-1] + change
            prices.append(max(1.05, min(1.15, new_price)))
        
        prices = np.array(prices[1:])
        
        data = {
            'open': prices,
            'high': prices + np.random.uniform(0, 0.002, n_bars),
            'low': prices - np.random.uniform(0, 0.002, n_bars),
            'close': prices + np.random.normal(0, 0.0005, n_bars),
            'volume': np.random.randint(1000, 10000, n_bars),
            'label': np.random.choice([-1, 0, 1], n_bars),
            'ret': np.random.normal(0, 0.001, n_bars),
            't_final': np.random.randint(1, 25, n_bars)
        }
        
        # Ensure OHLC consistency
        data['high'] = np.maximum(data['high'], np.maximum(data['open'], data['close']))
        data['low'] = np.minimum(data['low'], np.minimum(data['open'], data['close']))
        
        df = pd.DataFrame(data)
        df.index = pd.date_range('2025-01-01', periods=n_bars, freq='1min')
        
        return df
    
    def test_calculate_rsi(self, sample_labeled_data):
        """Test RSI calculation."""
        rsi = calculate_rsi(sample_labeled_data['close'], window=14)
        
        assert isinstance(rsi, pd.Series)
        assert len(rsi) == len(sample_labeled_data)
        
        # RSI should be between 0 and 100
        valid_rsi = rsi.dropna()
        assert all(0 <= val <= 100 for val in valid_rsi)
        
        # First 14 values should be NaN due to window
        assert rsi.iloc[:13].isna().all()
    
    def test_calculate_macd(self, sample_labeled_data):
        """Test MACD calculation."""
        macd_data = calculate_macd(sample_labeled_data['close'])
        
        assert isinstance(macd_data, pd.DataFrame)
        assert len(macd_data) == len(sample_labeled_data)
        assert 'macd' in macd_data.columns
        assert 'macd_signal' in macd_data.columns
        assert 'macd_histogram' in macd_data.columns
        
        # Check that histogram = macd - signal
        valid_data = macd_data.dropna()
        if len(valid_data) > 0:
            np.testing.assert_array_almost_equal(
                valid_data['macd_histogram'],
                valid_data['macd'] - valid_data['macd_signal'],
                decimal=10
            )
    
    def test_calculate_bollinger_bands(self, sample_labeled_data):
        """Test Bollinger Bands calculation."""
        bb_data = calculate_bollinger_bands(sample_labeled_data['close'])
        
        assert isinstance(bb_data, pd.DataFrame)
        assert len(bb_data) == len(sample_labeled_data)
        assert 'bb_upper' in bb_data.columns
        assert 'bb_middle' in bb_data.columns
        assert 'bb_lower' in bb_data.columns
        assert 'bb_width' in bb_data.columns
        assert 'bb_percent' in bb_data.columns
        
        # Check that upper > middle > lower
        valid_data = bb_data.dropna()
        if len(valid_data) > 0:
            assert all(valid_data['bb_upper'] >= valid_data['bb_middle'])
            assert all(valid_data['bb_middle'] >= valid_data['bb_lower'])
    
    def test_calculate_atr(self, sample_labeled_data):
        """Test ATR calculation."""
        atr = calculate_atr(
            sample_labeled_data['high'],
            sample_labeled_data['low'],
            sample_labeled_data['close']
        )
        
        assert isinstance(atr, pd.Series)
        assert len(atr) == len(sample_labeled_data)
        
        # ATR should be positive
        valid_atr = atr.dropna()
        assert all(val >= 0 for val in valid_atr)
    
    def test_calculate_stochastic(self, sample_labeled_data):
        """Test Stochastic Oscillator calculation."""
        stoch_data = calculate_stochastic(
            sample_labeled_data['high'],
            sample_labeled_data['low'],
            sample_labeled_data['close']
        )
        
        assert isinstance(stoch_data, pd.DataFrame)
        assert len(stoch_data) == len(sample_labeled_data)
        assert 'stoch_k' in stoch_data.columns
        assert 'stoch_d' in stoch_data.columns
        
        # Stochastic should be between 0 and 100
        valid_data = stoch_data.dropna()
        if len(valid_data) > 0:
            assert all(0 <= val <= 100 for val in valid_data['stoch_k'])
            assert all(0 <= val <= 100 for val in valid_data['stoch_d'])
    
    def test_generate_features_momentum(self, sample_labeled_data):
        """Test momentum feature generation."""
        config = {"feature_categories": ["momentum"]}
        
        df_features = generate_features(sample_labeled_data, config)
        
        assert len(df_features) == len(sample_labeled_data)
        assert len(df_features.columns) > len(sample_labeled_data.columns)
        
        # Check for momentum indicators
        assert 'rsi_14' in df_features.columns
        assert 'macd' in df_features.columns
        assert 'macd_signal' in df_features.columns
        assert 'macd_histogram' in df_features.columns
        assert 'stoch_k' in df_features.columns
        assert 'stoch_d' in df_features.columns
        assert 'cci_20' in df_features.columns
    
    def test_generate_features_trend(self, sample_labeled_data):
        """Test trend feature generation."""
        config = {"feature_categories": ["trend"]}
        
        df_features = generate_features(sample_labeled_data, config)
        
        # Check for trend indicators
        assert 'sma_20' in df_features.columns
        assert 'sma_50' in df_features.columns
        assert 'ema_20' in df_features.columns
        assert 'ema_50' in df_features.columns
        assert 'price_vs_sma20' in df_features.columns
        assert 'price_vs_ema20' in df_features.columns
    
    def test_generate_features_volatility(self, sample_labeled_data):
        """Test volatility feature generation."""
        config = {"feature_categories": ["volatility"]}
        
        df_features = generate_features(sample_labeled_data, config)
        
        # Check for volatility indicators
        assert 'bb_upper' in df_features.columns
        assert 'bb_middle' in df_features.columns
        assert 'bb_lower' in df_features.columns
        assert 'bb_width' in df_features.columns
        assert 'bb_percent' in df_features.columns
        assert 'atr_14' in df_features.columns
        assert 'volatility_20' in df_features.columns
    
    def test_generate_features_volume(self, sample_labeled_data):
        """Test volume feature generation."""
        config = {"feature_categories": ["volume"]}
        
        df_features = generate_features(sample_labeled_data, config)
        
        # Check for volume indicators
        assert 'obv' in df_features.columns
        assert 'volume_sma_20' in df_features.columns
        assert 'volume_ratio' in df_features.columns
    
    def test_generate_features_all_categories(self, sample_labeled_data):
        """Test feature generation with all categories."""
        config = {"feature_categories": ["momentum", "trend", "volatility", "volume"]}
        
        df_features = generate_features(sample_labeled_data, config)
        
        # Should have significantly more features
        original_features = len(sample_labeled_data.columns)
        new_features = len(df_features.columns)
        assert new_features > original_features + 20  # At least 20 new features
        
        # Check that price action features are always included
        assert 'price_change' in df_features.columns
        assert 'high_low_ratio' in df_features.columns
        assert 'open_close_ratio' in df_features.columns
        assert 'is_doji' in df_features.columns
        assert 'is_hammer' in df_features.columns
    
    def test_generate_features_missing_columns(self):
        """Test error handling for missing OHLC columns."""
        # Create data without required columns
        df_bad = pd.DataFrame({
            'price': [1.1, 1.2, 1.3],
            'label': [0, 1, -1]
        })
        
        config = {"feature_categories": ["momentum"]}
        
        with pytest.raises(ValueError, match="Missing required OHLC columns"):
            generate_features(df_bad, config)
    
    def test_run_feature_engine_module(self, sample_labeled_data, tmp_path):
        """Test the main run function of the FeatureEngine module."""
        # Create dummy input file
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        input_file = input_dir / "bars_labeled.parquet"
        sample_labeled_data.to_parquet(input_file)
        
        # Config for the run
        output_dir = tmp_path / "output"
        config = {
            "input_file": str(input_file),
            "feature_categories": ["momentum", "trend", "volatility"],
            "out_dir": str(output_dir)
        }
        
        result = run_feature_engine(config)
        
        assert result is not None
        assert result["success"] == True
        
        # Check outputs
        output_path = Path(result["feature_data_path"])
        report_path = output_dir / "feature_engine_report.json"
        manifest_path = output_dir / "manifest.json"
        
        assert output_path.exists()
        assert report_path.exists()
        assert manifest_path.exists()
        
        # Check feature data
        df_features = pd.read_parquet(output_path)
        assert len(df_features) == len(sample_labeled_data)
        assert len(df_features.columns) > len(sample_labeled_data.columns)
        
        # Check report
        with open(report_path) as f:
            report = json.load(f)
        assert "n_bars" in report
        assert "n_original_features" in report
        assert "n_new_features" in report
        assert "new_feature_names" in report
        assert report["n_new_features"] > 0
        
        # Check manifest
        with open(manifest_path) as f:
            manifest = json.load(f)
        assert manifest["module"] == "feature_engine"
        assert manifest["version"] == "1.0.0"
        assert "run_id" in manifest
    
    def test_run_feature_engine_missing_file(self, tmp_path):
        """Test error handling for missing input file."""
        config = {
            "input_file": str(tmp_path / "nonexistent.parquet"),
            "feature_categories": ["momentum"],
            "out_dir": str(tmp_path / "output")
        }
        
        result = run_feature_engine(config)
        
        assert result is not None
        assert result["success"] == False
        assert "error" in result
        assert "not found" in result["error"].lower()


class TestFeatureEngineIntegration:
    """Test FeatureEngine integration with other modules."""
    
    def test_pipeline_compatibility(self, tmp_path):
        """Test that FeatureEngine output is compatible with downstream modules."""
        # Create mock labeled data (output from Module 2)
        np.random.seed(42)
        n_bars = 50
        
        labeled_data = {
            'open': np.random.uniform(1.09, 1.11, n_bars),
            'high': np.random.uniform(1.10, 1.12, n_bars),
            'low': np.random.uniform(1.08, 1.10, n_bars),
            'close': np.random.uniform(1.09, 1.11, n_bars),
            'volume': np.random.randint(1000, 5000, n_bars),
            'label': np.random.choice([-1, 0, 1], n_bars),
            'ret': np.random.normal(0, 0.001, n_bars),
            't_final': np.random.randint(1, 25, n_bars)
        }
        
        df_labeled = pd.DataFrame(labeled_data)
        df_labeled.index = pd.date_range('2025-01-01', periods=n_bars, freq='1min')
        
        # Ensure OHLC consistency
        df_labeled['high'] = np.maximum(df_labeled['high'], 
                                       np.maximum(df_labeled['open'], df_labeled['close']))
        df_labeled['low'] = np.minimum(df_labeled['low'], 
                                      np.minimum(df_labeled['open'], df_labeled['close']))
        
        # Save labeled data
        input_file = tmp_path / "bars_labeled.parquet"
        df_labeled.to_parquet(input_file)
        
        # Run FeatureEngine
        config = {
            "input_file": str(input_file),
            "feature_categories": ["momentum", "trend", "volatility", "volume"],
            "out_dir": str(tmp_path / "feature_output")
        }
        
        result = run_feature_engine(config)
        
        assert result["success"] == True
        
        # Load feature data
        df_features = pd.read_parquet(result["feature_data_path"])
        
        # Check that original columns are preserved
        for col in df_labeled.columns:
            assert col in df_features.columns
        
        # Check that labels are preserved (needed for ML training)
        assert 'label' in df_features.columns
        assert 'ret' in df_features.columns
        
        # Check that we have enough features for ML
        feature_cols = [col for col in df_features.columns 
                       if col not in df_labeled.columns]
        assert len(feature_cols) >= 15  # Should have at least 15 new features
        
        # Check for no infinite or extremely large values
        numeric_cols = df_features.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            assert not df_features[col].isin([np.inf, -np.inf]).any()
            assert abs(df_features[col]).max() < 1e6  # Reasonable bounds


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

