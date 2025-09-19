import pandas as pd
import numpy as np
from core.strategies.scalping_strategy_breakout import generate_breakout_signals
from core.strategies.scalping_strategy_mean_reversion import generate_mean_reversion_signals

def create_sample_data():
    data = {
        't': pd.to_datetime(pd.date_range(start='2025-01-01', periods=100, freq='T')),
        'o': np.random.uniform(1.0, 1.1, 100),
        'h': np.random.uniform(1.1, 1.2, 100),
        'l': np.random.uniform(0.9, 1.0, 100),
        'c': np.random.uniform(1.0, 1.1, 100),
    }
    return pd.DataFrame(data)

def test_generate_breakout_signals():
    df = create_sample_data()
    df = generate_breakout_signals(df)
    assert 'signal' in df.columns
    assert df['signal'].isin([0, 1, -1]).all()

def test_generate_mean_reversion_signals():
    df = create_sample_data()
    df = generate_mean_reversion_signals(df)
    assert 'signal' in df.columns
    assert df['signal'].isin([0, 1, -1]).all()
