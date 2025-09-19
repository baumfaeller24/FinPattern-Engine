import numpy as np

def calculate_sharpe_ratio(returns, risk_free_rate=0.0):
    """
    Calculates the Sharpe ratio of a returns series.
    """
    return (returns.mean() - risk_free_rate) / returns.std() if returns.std() != 0 else 0

def calculate_win_rate(trades):
    """
    Calculates the win rate of a series of trades.
    """
    return (trades > 0).sum() / len(trades) if len(trades) > 0 else 0

def calculate_profit_factor(trades):
    """
    Calculates the profit factor of a series of trades.
    """
    gross_profit = trades[trades > 0].sum()
    gross_loss = abs(trades[trades < 0].sum())
    return gross_profit / gross_loss if gross_loss != 0 else np.inf

