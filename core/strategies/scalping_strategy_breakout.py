import pandas as pd

def generate_breakout_signals(df: pd.DataFrame, lookback_period: int = 50, max_spread: float = 0.0002) -> pd.DataFrame:
    """
    Generates breakout signals for a given DataFrame.

    Args:
        df: DataFrame with OHLC data.
        lookback_period: The number of bars to look back for high/low.
        max_spread: The maximum allowed spread for a signal.

    Returns:
        DataFrame with signals.
    """
    df["rolling_high"] = df["h"].rolling(window=lookback_period).max().shift(1)
    df["rolling_low"] = df["l"].rolling(window=lookback_period).min().shift(1)

    df["signal"] = 0
    df.loc[df["c"] > df["rolling_high"], "signal"] = 1  # Long signal
    df.loc[df["c"] < df["rolling_low"], "signal"] = -1 # Short signal

    # Apply spread filter
    if "ask" in df.columns and "bid" in df.columns:
        df.loc[(df["ask"] - df["bid"]) > max_spread, "signal"] = 0

    return df

