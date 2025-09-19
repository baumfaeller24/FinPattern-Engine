import pandas as pd

def generate_momentum_signals(df: pd.DataFrame, fast_period: int = 10, slow_period: int = 30) -> pd.DataFrame:
    """
    Generates momentum signals based on moving average crossover.

    Args:
        df: DataFrame with OHLC data.
        fast_period: The period for the fast moving average.
        slow_period: The period for the slow moving average.

    Returns:
        DataFrame with signals.
    """
    df["fast_ma"] = df["c"].rolling(window=fast_period).mean()
    df["slow_ma"] = df["c"].rolling(window=slow_period).mean()

    df["signal"] = 0
    df.loc[df["fast_ma"] > df["slow_ma"], "signal"] = 1  # Long signal
    df.loc[df["fast_ma"] < df["slow_ma"], "signal"] = -1 # Short signal

    return df

