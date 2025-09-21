import sys
import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timezone

sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '..')))

from core.strategies.scalping_strategy_breakout import generate_breakout_signals
from core.strategies.scalping_strategy_mean_reversion import generate_mean_reversion_signals
from core.strategies.scalping_strategy_momentum import generate_momentum_signals

def calculate_performance_metrics(df: pd.DataFrame, signals: pd.Series, initial_capital: float = 10000) -> dict:
    """
    Calculate performance metrics for a trading strategy.
    """
    # Calculate returns
    df = df.copy()
    df['signal'] = signals
    df['position'] = df['signal'].shift(1).fillna(0)
    df['returns'] = df['c'].pct_change()
    df['strategy_returns'] = df['position'] * df['returns']
    
    # Calculate cumulative returns
    df['cumulative_returns'] = (1 + df['strategy_returns']).cumprod()
    
    # Performance metrics
    total_return = df['cumulative_returns'].iloc[-1] - 1
    
    # Sharpe ratio (annualized)
    if df['strategy_returns'].std() > 0:
        sharpe_ratio = (df['strategy_returns'].mean() / df['strategy_returns'].std()) * np.sqrt(252 * 24 * 60)  # Assuming minute data
    else:
        sharpe_ratio = 0
    
    # Maximum drawdown
    running_max = df['cumulative_returns'].expanding().max()
    drawdown = (df['cumulative_returns'] - running_max) / running_max
    max_drawdown = drawdown.min()
    
    # Win rate
    winning_trades = df[df['strategy_returns'] > 0]
    losing_trades = df[df['strategy_returns'] < 0]
    total_trades = len(winning_trades) + len(losing_trades)
    win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
    
    return {
        'total_return': total_return,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
        'total_trades': total_trades,
        'winning_trades': len(winning_trades),
        'losing_trades': len(losing_trades)
    }

def validate_scalping_strategies():
    """
    Validate the scalping strategies using real market data.
    """
    print("="*60)
    print("SCALPING STRATEGIES VALIDATION")
    print("="*60)
    
    # Load the 1000-tick bars data
    bars_path = "/home/ubuntu/FinPattern-Engine/output/data_ingest/bars_1000t"
    
    # Find the first parquet file in the directory
    bars_files = list(Path(bars_path).glob("*.parquet"))
    if not bars_files:
        print("❌ No bar data found for strategy validation")
        return False
    
    print(f"Loading bar data from: {bars_files[0]}")
    bars_df = pd.read_parquet(bars_files[0])
    
    # Convert timestamp columns to datetime
    bars_df['t_open_ns'] = pd.to_datetime(bars_df['t_open_ns'], unit='ns', utc=True)
    bars_df['t_close_ns'] = pd.to_datetime(bars_df['t_close_ns'], unit='ns', utc=True)
    
    print(f"Loaded {len(bars_df):,} bars for strategy validation")
    print(f"Time range: {bars_df['t_open_ns'].min()} to {bars_df['t_close_ns'].max()}")
    print(f"Columns: {list(bars_df.columns)}")
    
    # Initialize strategies
    strategies = {
        "Breakout": generate_breakout_signals,
        "Mean Reversion": generate_mean_reversion_signals,
        "Momentum": generate_momentum_signals
    }
    
    results = {}
    
    # Test each strategy
    for strategy_name, strategy_func in strategies.items():
        print(f"\n--- Testing {strategy_name} Strategy ---")
        
        try:
            # Generate signals
            df_with_signals = strategy_func(bars_df.copy())
            signals = df_with_signals['signal']
            
            # Calculate performance
            performance = calculate_performance_metrics(bars_df, signals)
            
            results[strategy_name] = {
                "signals_generated": len(signals[signals != 0]),
                "long_signals": len(signals[signals == 1]),
                "short_signals": len(signals[signals == -1]),
                "performance": performance
            }
            
            print(f"  ✅ Signals generated: {results[strategy_name]['signals_generated']:,}")
            print(f"  Long signals: {results[strategy_name]['long_signals']:,}")
            print(f"  Short signals: {results[strategy_name]['short_signals']:,}")
            
            if performance:
                print(f"  Sharpe Ratio: {performance.get('sharpe_ratio', 'N/A'):.3f}")
                print(f"  Total Return: {performance.get('total_return', 'N/A'):.2%}")
                print(f"  Max Drawdown: {performance.get('max_drawdown', 'N/A'):.2%}")
                print(f"  Win Rate: {performance.get('win_rate', 'N/A'):.2%}")
                print(f"  Total Trades: {performance.get('total_trades', 'N/A'):,}")
            
        except Exception as e:
            print(f"  ❌ Strategy {strategy_name} failed: {e}")
            import traceback
            traceback.print_exc()
            results[strategy_name] = {"error": str(e)}
    
    # Save results
    output_dir = Path("/home/ubuntu/FinPattern-Engine/output/strategy_validation")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results_file = output_dir / "strategy_validation_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n--- VALIDATION SUMMARY ---")
    successful_strategies = [name for name, result in results.items() if "error" not in result]
    failed_strategies = [name for name, result in results.items() if "error" in result]
    
    print(f"Successful strategies: {len(successful_strategies)}")
    print(f"Failed strategies: {len(failed_strategies)}")
    
    if successful_strategies:
        print(f"✅ Successful: {', '.join(successful_strategies)}")
    
    if failed_strategies:
        print(f"❌ Failed: {', '.join(failed_strategies)}")
    
    print(f"\nResults saved to: {results_file}")
    
    return len(successful_strategies) > 0

if __name__ == "__main__":
    success = validate_scalping_strategies()
    if success:
        print("\n🎉 SCALPING STRATEGIES VALIDATION PASSED!")
    else:
        print("\n❌ SCALPING STRATEGIES VALIDATION FAILED!")
