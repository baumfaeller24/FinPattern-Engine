"""
Splitter Module - Walk-Forward Validation and Data Splitting

This module provides robust data splitting strategies for time series data,
essential for preventing data leakage and overfitting in trading strategies.
"""

from .splitter import run, DataSplitter, detect_data_leakage

__all__ = ['run', 'DataSplitter', 'detect_data_leakage']
