"""
Enhanced Labeling Module v2.2 - First-Hit-Logic and Volatility Scaling

Key v2.2 Enhancements:
1. Tick-slice based First-Hit-Logic for simultaneous TP/SL resolution
2. Dynamic volatility scaling with EWMA per event
3. Timeout in seconds in addition to bar-based timeout
4. Enhanced side support (long/short/both) with improved logic
5. Integration with DataIngest v2.2 tick-slice exports
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from numba import njit
import warnings

MODULE_VERSION = "2.2"

def _log_progress(out_dir: Path, step: str, percent: int, message: str):
    """Enhanced progress logging"""
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "module": "labeling",
        "module_version": MODULE_VERSION,
        "step": step,
        "percent": percent,
        "message": message
    }
    
    log_file = out_dir / "progress.jsonl"
    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

@njit
def _calculate_ewma_volatility(returns: np.ndarray, alpha: float = 0.94) -> np.ndarray:
    """
    Calculate EWMA volatility for dynamic scaling
    
    Args:
        returns: Array of price returns
        alpha: EWMA decay factor (default 0.94 for daily-like behavior)
    
    Returns:
        Array of EWMA volatilities
    """
    n = len(returns)
    if n == 0:
        return np.zeros(0, dtype=np.float64)
    
    ewma_var = np.zeros(n, dtype=np.float64)
    ewma_var[0] = returns[0] ** 2
    
    for i in range(1, n):
        ewma_var[i] = alpha * ewma_var[i-1] + (1 - alpha) * returns[i] ** 2
    
    return np.sqrt(ewma_var)

@njit
def _first_hit_detection(tick_prices: np.ndarray, tick_times_ns: np.ndarray, 
                        entry_price: float, tp_price: float, sl_price: float,
                        side: int) -> Tuple[int, float, int]:
    """
    Tick-level first-hit detection for simultaneous TP/SL resolution
    
    Args:
        tick_prices: Array of tick mid prices
        tick_times_ns: Array of tick timestamps in nanoseconds
        entry_price: Entry price for the trade
        tp_price: Take profit price level
        sl_price: Stop loss price level
        side: Trade side (1 for long, -1 for short)
    
    Returns:
        Tuple of (hit_type, exit_price, exit_time_ns)
        hit_type: 1 for TP, -1 for SL, 0 for no hit
    """
    if len(tick_prices) == 0:
        return 0, entry_price, 0
    
    for i in range(len(tick_prices)):
        price = tick_prices[i]
        time_ns = tick_times_ns[i]
        
        if side == 1:  # Long position
            if price >= tp_price:
                return 1, tp_price, time_ns  # Take profit hit
            elif price <= sl_price:
                return -1, sl_price, time_ns  # Stop loss hit
        else:  # Short position
            if price <= tp_price:
                return 1, tp_price, time_ns  # Take profit hit
            elif price >= sl_price:
                return -1, sl_price, time_ns  # Stop loss hit
    
    return 0, price, tick_times_ns[-1]  # No hit, return last price

@njit
def _apply_triple_barrier_v22(bar_prices: np.ndarray, bar_times_ns: np.ndarray,
                             event_indices: np.ndarray, tp_levels: np.ndarray, 
                             sl_levels: np.ndarray, timeout_bars: np.ndarray,
                             timeout_seconds: np.ndarray, sides: np.ndarray,
                             volatilities: np.ndarray) -> np.ndarray:
    """
    Enhanced triple-barrier labeling with First-Hit-Logic and dynamic volatility
    
    Args:
        bar_prices: Array of bar mid prices
        bar_times_ns: Array of bar timestamps in nanoseconds
        event_indices: Array of event start indices
        tp_levels: Array of take profit levels (in volatility units)
        sl_levels: Array of stop loss levels (in volatility units)
        timeout_bars: Array of timeout in bars
        timeout_seconds: Array of timeout in seconds
        sides: Array of trade sides (1 for long, -1 for short, 0 for both)
        volatilities: Array of volatilities for each event
    
    Returns:
        Array of shape (n_events, 5) with columns:
        [return, label, exit_time_ns, hit_type, volatility_used]
    """
    n_events = len(event_indices)
    n_bars = len(bar_prices)
    results = np.zeros((n_events, 5))
    
    for i in range(n_events):
        event_idx = event_indices[i]
        if event_idx >= n_bars - 1:
            continue
            
        entry_price = bar_prices[event_idx]
        entry_time_ns = bar_times_ns[event_idx]
        vol = volatilities[i]
        side = sides[i]
        
        # Calculate dynamic TP/SL levels
        tp_distance = tp_levels[i] * vol
        sl_distance = sl_levels[i] * vol
        
        if side == 1:  # Long
            tp_price = entry_price + tp_distance
            sl_price = entry_price - sl_distance
        elif side == -1:  # Short
            tp_price = entry_price - tp_distance
            sl_price = entry_price + sl_distance
        else:  # Both sides - use the side that hits first
            tp_price_long = entry_price + tp_distance
            sl_price_long = entry_price - sl_distance
            tp_price_short = entry_price - tp_distance
            sl_price_short = entry_price + sl_distance
        
        # Calculate timeout
        timeout_bar_idx = min(event_idx + timeout_bars[i], n_bars - 1)
        timeout_time_ns = entry_time_ns + timeout_seconds[i] * 1_000_000_000
        
        # Search for hits
        hit_type = 0
        exit_price = entry_price
        exit_time_ns = entry_time_ns
        
        for t in range(event_idx + 1, timeout_bar_idx + 1):
            current_time_ns = bar_times_ns[t]
            
            # Check time-based timeout
            if current_time_ns > timeout_time_ns:
                break
                
            current_price = bar_prices[t]
            
            if side == 1:  # Long position
                if current_price >= tp_price:
                    hit_type = 1  # TP hit
                    exit_price = tp_price
                    exit_time_ns = current_time_ns
                    break
                elif current_price <= sl_price:
                    hit_type = -1  # SL hit
                    exit_price = sl_price
                    exit_time_ns = current_time_ns
                    break
            elif side == -1:  # Short position
                if current_price <= tp_price:
                    hit_type = 1  # TP hit
                    exit_price = tp_price
                    exit_time_ns = current_time_ns
                    break
                elif current_price >= sl_price:
                    hit_type = -1  # SL hit
                    exit_price = sl_price
                    exit_time_ns = current_time_ns
                    break
            else:  # Both sides
                # Check long side
                if current_price >= tp_price_long:
                    hit_type = 1
                    exit_price = tp_price_long
                    exit_time_ns = current_time_ns
                    side = 1  # Record as long trade
                    break
                elif current_price <= sl_price_long:
                    hit_type = -1
                    exit_price = sl_price_long
                    exit_time_ns = current_time_ns
                    side = 1
                    break
                # Check short side
                elif current_price <= tp_price_short:
                    hit_type = 1
                    exit_price = tp_price_short
                    exit_time_ns = current_time_ns
                    side = -1  # Record as short trade
                    break
                elif current_price >= sl_price_short:
                    hit_type = -1
                    exit_price = sl_price_short
                    exit_time_ns = current_time_ns
                    side = -1
                    break
        
        # If no hit, use timeout exit
        if hit_type == 0:
            if timeout_bar_idx < n_bars:
                exit_price = bar_prices[timeout_bar_idx]
                exit_time_ns = bar_times_ns[timeout_bar_idx]
            hit_type = 0  # Timeout
        
        # Calculate return
        if side == 1:  # Long
            ret = (exit_price - entry_price) / entry_price
        elif side == -1:  # Short
            ret = (entry_price - exit_price) / entry_price
        else:
            ret = 0.0  # Should not happen
        
        # Assign label
        if hit_type == 1:
            label = 1  # Profitable
        elif hit_type == -1:
            label = -1  # Loss
        else:
            label = 0  # Timeout/Neutral
        
        results[i] = [ret, label, exit_time_ns, hit_type, vol]
    
    return results

def _load_tick_slices(slice_dir: Path, event_ids: List[int]) -> Dict[int, pd.DataFrame]:
    """
    Load tick slices for specified events
    
    Args:
        slice_dir: Directory containing tick slice files
        event_ids: List of event IDs to load
    
    Returns:
        Dictionary mapping event_id to tick slice DataFrame
    """
    tick_slices = {}
    
    for event_id in event_ids:
        slice_file = slice_dir / f"ticks_event_{event_id:06d}.parquet"
        if slice_file.exists():
            try:
                tick_slice = pd.read_parquet(slice_file)
                tick_slices[event_id] = tick_slice
            except Exception as e:
                warnings.warn(f"Failed to load tick slice for event {event_id}: {e}")
                continue
    
    return tick_slices

def _enhance_with_tick_slices(results: np.ndarray, tick_slices: Dict[int, pd.DataFrame],
                            event_indices: np.ndarray, bar_prices: np.ndarray,
                            tp_levels: np.ndarray, sl_levels: np.ndarray,
                            sides: np.ndarray, volatilities: np.ndarray) -> np.ndarray:
    """
    Enhance results with tick-level first-hit detection
    
    This function refines the bar-level results using tick-slice data
    for more precise exit timing and price determination.
    """
    enhanced_results = results.copy()
    
    for i, event_idx in enumerate(event_indices):
        if event_idx not in tick_slices:
            continue
            
        tick_slice = tick_slices[event_idx]
        if len(tick_slice) == 0:
            continue
        
        entry_price = bar_prices[event_idx]
        vol = volatilities[i]
        side = sides[i]
        
        # Calculate TP/SL levels
        tp_distance = tp_levels[i] * vol
        sl_distance = sl_levels[i] * vol
        
        if side == 1:  # Long
            tp_price = entry_price + tp_distance
            sl_price = entry_price - sl_distance
        elif side == -1:  # Short
            tp_price = entry_price - tp_distance
            sl_price = entry_price + sl_distance
        else:
            continue  # Skip both-sided for tick enhancement
        
        # Apply first-hit detection
        tick_prices = tick_slice['mid_price'].values
        tick_times = tick_slice['ts_ns'].values
        
        hit_type, exit_price, exit_time_ns = _first_hit_detection(
            tick_prices, tick_times, entry_price, tp_price, sl_price, side
        )
        
        if hit_type != 0:  # Update if we found a hit
            # Calculate refined return
            if side == 1:
                ret = (exit_price - entry_price) / entry_price
            else:
                ret = (entry_price - exit_price) / entry_price
            
            label = 1 if hit_type == 1 else -1
            
            enhanced_results[i] = [ret, label, exit_time_ns, hit_type, vol]
    
    return enhanced_results

def run(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhanced Triple-Barrier Labeling v2.2 with First-Hit-Logic and Dynamic Volatility
    
    Args:
        config: Configuration dictionary with the following keys:
            - bars_path: Path to bar data (parquet file)
            - tick_slices_dir: Path to tick slices directory (optional)
            - out_dir: Output directory
            - events: List of event configurations or path to events file
            - tp_vol_multiple: Take profit in volatility multiples (default: 2.0)
            - sl_vol_multiple: Stop loss in volatility multiples (default: 2.0)
            - timeout_bars: Timeout in number of bars (default: 10)
            - timeout_seconds: Timeout in seconds (default: 3600)
            - side: Trade side - 1 (long), -1 (short), 0 (both) (default: 0)
            - vol_lookback: Lookback period for volatility calculation (default: 20)
            - vol_alpha: EWMA alpha for volatility (default: 0.94)
            - use_tick_slices: Whether to use tick slices for first-hit (default: True)
    
    Returns:
        Dictionary with results and metadata
    """
    
    # Setup
    out_dir = Path(config["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    
    _log_progress(out_dir, "start", 0, f"Labeling v{MODULE_VERSION} starting")
    
    # Load bar data
    bars_path = Path(config["bars_path"])
    if not bars_path.exists():
        raise FileNotFoundError(f"Bars file not found: {bars_path}")
    
    _log_progress(out_dir, "load_bars", 10, f"Loading bars from {bars_path}")
    bars_df = pd.read_parquet(bars_path)
    
    # Ensure required columns
    required_cols = ["t_open_ns", "t_close_ns", "o", "h", "l", "c"]
    missing_cols = [col for col in required_cols if col not in bars_df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Calculate mid prices and returns
    bars_df["mid"] = (bars_df["o"] + bars_df["h"] + bars_df["l"] + bars_df["c"]) / 4
    bars_df["returns"] = bars_df["mid"].pct_change().fillna(0)
    
    # Load or generate events
    _log_progress(out_dir, "events", 20, "Processing events")
    events_config = config.get("events", [])
    
    if isinstance(events_config, str):
        # Load events from file
        events_path = Path(events_config)
        if events_path.suffix == ".json":
            with open(events_path) as f:
                events = json.load(f)
        else:
            events_df = pd.read_parquet(events_path)
            events = events_df.to_dict("records")
    elif isinstance(events_config, list):
        events = events_config
    else:
        # Generate events (every N bars)
        event_spacing = config.get("event_spacing", 10)
        events = [{"index": i} for i in range(0, len(bars_df), event_spacing)]
    
    if len(events) == 0:
        raise ValueError("No events to process")
    
    # Extract event indices
    event_indices = np.array([event.get("index", event.get("bar_index", 0)) for event in events])
    event_indices = event_indices[event_indices < len(bars_df) - 1]  # Ensure valid indices
    
    _log_progress(out_dir, "volatility", 30, "Calculating dynamic volatility")
    
    # Calculate EWMA volatility
    vol_lookback = config.get("vol_lookback", 20)
    vol_alpha = config.get("vol_alpha", 0.94)
    
    returns = bars_df["returns"].values
    ewma_vol = _calculate_ewma_volatility(returns, vol_alpha)
    
    # Get volatility for each event
    event_volatilities = np.array([
        ewma_vol[max(0, idx - vol_lookback):idx].mean() if idx >= vol_lookback 
        else ewma_vol[:idx+1].mean() if idx > 0 
        else 0.01  # Default volatility
        for idx in event_indices
    ])
    
    # Ensure minimum volatility
    event_volatilities = np.maximum(event_volatilities, 0.001)
    
    # Setup labeling parameters
    tp_vol_multiple = config.get("tp_vol_multiple", 2.0)
    sl_vol_multiple = config.get("sl_vol_multiple", 2.0)
    timeout_bars = config.get("timeout_bars", 10)
    timeout_seconds = config.get("timeout_seconds", 3600)
    side = config.get("side", 0)
    
    # Prepare arrays for numba function
    bar_prices = bars_df["mid"].values
    bar_times_ns = bars_df["t_close_ns"].values
    tp_levels = np.full(len(event_indices), tp_vol_multiple)
    sl_levels = np.full(len(event_indices), sl_vol_multiple)
    timeout_bars_array = np.full(len(event_indices), timeout_bars)
    timeout_seconds_array = np.full(len(event_indices), timeout_seconds)
    sides_array = np.full(len(event_indices), side)
    
    _log_progress(out_dir, "labeling", 50, "Applying triple-barrier labeling")
    
    # Apply triple-barrier labeling
    results = _apply_triple_barrier_v22(
        bar_prices, bar_times_ns, event_indices, tp_levels, sl_levels,
        timeout_bars_array, timeout_seconds_array, sides_array, event_volatilities
    )
    
    # Enhance with tick slices if available
    use_tick_slices = config.get("use_tick_slices", True)
    tick_slices_dir = config.get("tick_slices_dir")
    
    if use_tick_slices and tick_slices_dir:
        _log_progress(out_dir, "tick_enhancement", 70, "Enhancing with tick-slice first-hit")
        
        tick_slices_path = Path(tick_slices_dir)
        if tick_slices_path.exists():
            tick_slices = _load_tick_slices(tick_slices_path, event_indices.tolist())
            if tick_slices:
                results = _enhance_with_tick_slices(
                    results, tick_slices, event_indices, bar_prices,
                    tp_levels, sl_levels, sides_array, event_volatilities
                )
                _log_progress(out_dir, "tick_enhancement", 75, f"Enhanced {len(tick_slices)} events with tick data")
            else:
                _log_progress(out_dir, "tick_enhancement", 75, "No tick slices found for enhancement")
    
    # Create results DataFrame
    _log_progress(out_dir, "results", 80, "Creating results DataFrame")
    
    results_df = pd.DataFrame(results, columns=[
        "return", "label", "exit_time_ns", "hit_type", "volatility_used"
    ])
    
    # Add event metadata
    results_df["event_index"] = event_indices
    results_df["entry_time_ns"] = bar_times_ns[event_indices]
    results_df["entry_price"] = bar_prices[event_indices]
    
    # Convert timestamps to datetime
    results_df["entry_time"] = pd.to_datetime(results_df["entry_time_ns"], unit="ns", utc=True)
    results_df["exit_time"] = pd.to_datetime(results_df["exit_time_ns"], unit="ns", utc=True)
    
    # Calculate additional metrics
    results_df["duration_seconds"] = (results_df["exit_time_ns"] - results_df["entry_time_ns"]) / 1e9
    results_df["tp_level"] = tp_vol_multiple * results_df["volatility_used"]
    results_df["sl_level"] = sl_vol_multiple * results_df["volatility_used"]
    
    # Save results
    _log_progress(out_dir, "save", 90, "Saving results")
    
    results_path = out_dir / "labeled_events.parquet"
    results_df.to_parquet(results_path, index=False)
    
    # Generate summary statistics
    summary_stats = {
        "total_events": len(results_df),
        "profitable_events": int((results_df["label"] == 1).sum()),
        "loss_events": int((results_df["label"] == -1).sum()),
        "timeout_events": int((results_df["label"] == 0).sum()),
        "win_rate": float((results_df["label"] == 1).mean()),
        "avg_return": float(results_df["return"].mean()),
        "avg_duration_seconds": float(results_df["duration_seconds"].mean()),
        "avg_volatility": float(results_df["volatility_used"].mean()),
        "tick_enhanced_events": len(tick_slices) if use_tick_slices and tick_slices_dir else 0
    }
    
    # Save summary
    summary_path = out_dir / "labeling_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary_stats, f, indent=2)
    
    # Save configuration
    config_path = out_dir / "config_used.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    _log_progress(out_dir, "done", 100, f"Labeling v{MODULE_VERSION} completed successfully")
    
    return {
        "results_path": str(results_path),
        "summary_path": str(summary_path),
        "summary_stats": summary_stats,
        "module_version": MODULE_VERSION,
        "events_processed": len(results_df),
        "tick_enhanced": use_tick_slices and tick_slices_dir is not None
    }
