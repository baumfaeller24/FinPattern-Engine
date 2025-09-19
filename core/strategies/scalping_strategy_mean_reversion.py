import pandas as pd

def generate_mean_reversion_signals(df: pd.DataFrame, lookback_period: int = 20, std_dev: int = 2) -> pd.DataFrame:
    """
    Generates mean-reversion signals for a given DataFrame.

    Args:
        df: DataFrame with OHLC data.
        lookback_period: The number of bars for moving average.
        std_dev: The number of standard deviations for Bollinger Bands.

    Returns:
        DataFrame with signals.
    """
    df["sma"] = df["c"].rolling(window=lookback_period).mean()
    df["std"] = df["c"].rolling(window=lookback_period).std()
    df["upper_band"] = df["sma"] + (df["std"] * std_dev)
    df["lower_band"] = df["sma"] - (df["std"] * std_dev)

    df["signal"] = 0
    df.loc[df["c"] < df["lower_band"], "signal"] = 1  # Long signal
    df.loc[df["c"] > df["upper_band"], "signal"] = -1 # Short signal

    return df

