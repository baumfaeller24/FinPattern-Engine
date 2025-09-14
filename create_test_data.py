#!/usr/bin/env python3
"""
Create larger test data for better demonstration of DataIngest module
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

def create_realistic_tick_data(n_ticks=10000, start_time=None):
    """Create realistic EUR/USD tick data."""
    if start_time is None:
        start_time = datetime(2025, 8, 5, 9, 0, 0)  # Monday 9 AM
    
    # Generate timestamps (irregular intervals)
    np.random.seed(42)
    intervals = np.random.exponential(scale=0.5, size=n_ticks)  # Average 0.5 seconds
    timestamps = []
    current_time = start_time
    
    for interval in intervals:
        current_time += timedelta(seconds=interval)
        # Skip weekends (simple check)
        if current_time.weekday() >= 5:  # Saturday=5, Sunday=6
            current_time += timedelta(days=2)
        timestamps.append(current_time)
    
    # Generate realistic price movement
    base_price = 1.1000
    price_changes = np.random.normal(0, 0.00005, n_ticks)  # Small random walk
    
    # Add some trend and volatility clustering
    trend = np.sin(np.arange(n_ticks) / 1000) * 0.0002
    volatility = 1 + 0.5 * np.sin(np.arange(n_ticks) / 500)
    
    price_changes = price_changes * volatility + trend
    mid_prices = base_price + np.cumsum(price_changes)
    
    # Create bid/ask with realistic spread
    spread_base = 0.00015  # 1.5 pips
    spread_variation = np.random.normal(0, 0.00005, n_ticks)
    spreads = np.maximum(spread_base + spread_variation, 0.00005)  # Min 0.5 pip
    
    bids = mid_prices - spreads / 2
    asks = mid_prices + spreads / 2
    
    # Create DataFrame
    data = pd.DataFrame({
        'timestamp': [t.isoformat() + 'Z' for t in timestamps],
        'bid': bids,
        'ask': asks
    })
    
    return data

def main():
    """Create test data files."""
    print("🔄 Erstelle realistische Testdaten...")
    
    # Create different sized datasets
    datasets = {
        'eurusd_small.csv': 1000,      # 1K ticks
        'eurusd_medium.csv': 10000,    # 10K ticks  
        'eurusd_large.csv': 100000,    # 100K ticks
    }
    
    samples_dir = Path('samples/ticks')
    
    for filename, n_ticks in datasets.items():
        print(f"📊 Erstelle {filename} mit {n_ticks:,} Ticks...")
        
        data = create_realistic_tick_data(n_ticks)
        output_path = samples_dir / filename
        data.to_csv(output_path, index=False)
        
        print(f"   ✅ Gespeichert: {output_path} ({len(data):,} Zeilen)")
        
        # Show sample
        print(f"   📈 Preis-Range: {data['bid'].min():.5f} - {data['ask'].max():.5f}")
        print(f"   ⏱️  Zeit-Range: {data['timestamp'].iloc[0]} bis {data['timestamp'].iloc[-1]}")
        print()

if __name__ == "__main__":
    main()
