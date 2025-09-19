import pandas as pd

def generate_breakout_signals(df: pd.DataFrame, lookback_period: int = 50) -> pd.DataFrame:
    """
    Generates breakout signals for a given DataFrame.

    Args:
        df: DataFrame with OHLC data.
        lookback_period: The number of bars to look back for high/low.

    Returns:
        DataFrame with signals.
    """
    df['rolling_high'] = df['h'].rolling(window=lookback_period).max().shift(1)
    df['rolling_low'] = df['l'].rolling(window=lookback_period).min().shift(1)

    df['signal'] = 0
    df.loc[df['c'] > df['rolling_high'], 'signal'] = 1  # Long signal
    df.loc[df['c'] < df['rolling_low'], 'signal'] = -1 # Short signal

    return df

