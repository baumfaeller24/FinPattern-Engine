"""
FeatureEngine Module for FinPattern-Engine

This module generates technical analysis features from labeled bar data.
"""

from .feature_engine import run, generate_features

__all__ = ["run", "generate_features"]
