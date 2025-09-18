"""
Enhanced DataIngest Module v2.2 - Tick-Slice-Export Improvements

Key v2.2 Enhancements:
1. Enhanced tick-slice export with event-based storage
2. Improved manifest with pip_size, bar_rules_id, export_slices
3. Memory optimization with compression and row-groups
4. Event-based tick slice organization for precise First-Hit-Logic
"""

from __future__ import annotations
import pathlib, json, datetime as dt
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import numpy as np

from . import errors as E
from .schema import TICK_SCHEMA, BAR_COLUMNS, SCHEMA_VERSION, BAR_RULES_ID
from .util import sha256_of_file, write_json

MODULE_VERSION = "2.2"

def _log_line(out_dir: pathlib.Path, step: str, pct: int, msg: str):
    """Enhanced logging with more detailed progress tracking"""
    p = out_dir / "progress.jsonl"
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "timestamp": dt.datetime.utcnow().isoformat(),
            "module": "data_ingest",
            "module_version": MODULE_VERSION,
            "step": step,
            "percent": pct,
            "message": msg
        }) + "\n")

def _ensure_cols(df: pd.DataFrame):
    missing = [c for c in ["timestamp","bid","ask"] if c not in df.columns]
    if missing:
        raise ValueError(f"{E.MISSING_COLUMN}: {missing}")

def _normalize_time(df: pd.DataFrame) -> pd.DataFrame:
    ts = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    if ts.isna().any():
        raise ValueError(E.TIMEZONE_ERROR)
    df = df.copy()
    df["ts_ns"] = ts.view("int64")
    return df

def _sort_and_dedupe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("ts_ns", kind="mergesort")
    df = df.drop_duplicates(subset=["ts_ns","bid","ask"], keep="first")
    return df

def _neg_spread_check(df: pd.DataFrame):
    if (df["ask"] < df["bid"]).any():
        raise ValueError(E.NEGATIVE_SPREAD)

def _compute_mid(df: pd.DataFrame, basis: str) -> pd.Series:
    if basis == "mid":
        return (df["bid"] + df["ask"]) / 2
    elif basis == "bid":
        return df["bid"]
    elif basis == "ask":
        return df["ask"]
    else:
        raise ValueError(f"Unknown basis: {basis}")

def _gap_report(df: pd.DataFrame, max_gap_s: int) -> Tuple[List[Dict], float]:
    """Enhanced gap analysis with better reporting"""
    if len(df) < 2:
        return [], 100.0
    
    diffs = np.diff(df["ts_ns"].values) / 1_000_000_000
    gaps = []
    total_time = (df["ts_ns"].iloc[-1] - df["ts_ns"].iloc[0]) / 1_000_000_000
    gap_time = 0
    
    for i, gap_s in enumerate(diffs):
        if gap_s > max_gap_s:
            gap_start = pd.to_datetime(df["ts_ns"].iloc[i], unit='ns', utc=True)
            gap_end = pd.to_datetime(df["ts_ns"].iloc[i+1], unit='ns', utc=True)
            gaps.append({
                "start": gap_start.isoformat(),
                "end": gap_end.isoformat(),
                "duration_seconds": float(gap_s)
            })
            gap_time += gap_s
    
    coverage = max(0, 100 * (1 - gap_time / total_time)) if total_time > 0 else 100
    return gaps, coverage

def _write_parquet_optimized(df: pd.DataFrame, path: pathlib.Path, compress: bool = True):
    """Enhanced parquet writing with compression and optimization"""
    compression = 'zstd' if compress else None
    row_group_size = min(128 * 1024 * 1024, len(df))  # 128MB row groups max
    
    df.to_parquet(
        path, 
        compression=compression,
        row_group_size=row_group_size,
        index=False
    )

def _create_event_tick_slices(df: pd.DataFrame, bars: pd.DataFrame, out_dir: pathlib.Path, 
                            frame_name: str, export_slices: bool = True) -> Dict[str, Any]:
    """
    Enhanced tick slice creation with event-based organization
    
    Creates individual tick slice files per bar/event for precise First-Hit-Logic
    """
    if not export_slices:
        return {"enabled": False}
    
    slice_dir = out_dir / f"tick_slices_{frame_name}"
    slice_dir.mkdir(exist_ok=True)
    
    # Create bar index mapping
    bar_idx_col = f"bar_idx_{frame_name}"
    if bar_idx_col not in df.columns:
        return {"enabled": False, "error": f"Missing {bar_idx_col} column"}
    
    slice_files = []
    slice_stats = {
        "total_events": 0,
        "total_ticks": 0,
        "avg_ticks_per_event": 0,
        "min_ticks": float('inf'),
        "max_ticks": 0
    }
    
    # Group ticks by bar and create individual slice files
    for bar_idx, group in df.groupby(bar_idx_col):
        if group.empty:
            continue
            
        event_id = int(bar_idx)
        slice_file = slice_dir / f"ticks_event_{event_id:06d}.parquet"
        
        # Prepare tick slice data with enhanced metadata
        tick_slice = group[["ts_ns", "bid", "ask"]].copy()
        tick_slice["event_id"] = event_id
        tick_slice["tick_sequence"] = range(len(tick_slice))
        
        # Add timing information for First-Hit-Logic
        if len(tick_slice) > 0:
            tick_slice["time_from_bar_start_ns"] = tick_slice["ts_ns"] - tick_slice["ts_ns"].iloc[0]
            tick_slice["mid_price"] = (tick_slice["bid"] + tick_slice["ask"]) / 2
        
        _write_parquet_optimized(tick_slice, slice_file, compress=True)
        
        slice_files.append({
            "event_id": event_id,
            "file": str(slice_file.relative_to(out_dir)),
            "tick_count": len(tick_slice),
            "time_span_ns": int(tick_slice["ts_ns"].iloc[-1] - tick_slice["ts_ns"].iloc[0]) if len(tick_slice) > 1 else 0
        })
        
        # Update statistics
        slice_stats["total_events"] += 1
        slice_stats["total_ticks"] += len(tick_slice)
        slice_stats["min_ticks"] = min(slice_stats["min_ticks"], len(tick_slice))
        slice_stats["max_ticks"] = max(slice_stats["max_ticks"], len(tick_slice))
    
    if slice_stats["total_events"] > 0:
        slice_stats["avg_ticks_per_event"] = slice_stats["total_ticks"] / slice_stats["total_events"]
        slice_stats["min_ticks"] = slice_stats["min_ticks"] if slice_stats["min_ticks"] != float('inf') else 0
    
    # Write slice manifest
    slice_manifest = {
        "frame_name": frame_name,
        "slice_directory": str(slice_dir.relative_to(out_dir)),
        "files": slice_files,
        "statistics": slice_stats,
        "created_at": dt.datetime.utcnow().isoformat()
    }
    
    manifest_path = slice_dir / "slice_manifest.json"
    write_json(manifest_path, slice_manifest)
    
    return {
        "enabled": True,
        "slice_directory": str(slice_dir.relative_to(out_dir)),
        "manifest_path": str(manifest_path.relative_to(out_dir)),
        "statistics": slice_stats
    }

def _time_bars_1m_enhanced(df: pd.DataFrame, basis: str, symbol: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Enhanced 1-minute bars with improved tick slice organization"""
    bar_idx_raw = df["ts_ns"] // (60 * 1_000_000_000)
    df["bar_idx_1m"] = pd.factorize(bar_idx_raw)[0]
    
    mid = _compute_mid(df, basis)
    grouped = df.groupby("bar_idx_1m")
    
    rows = []
    for bar_idx, group in grouped:
        if group.empty:
            continue
            
        mi = _compute_mid(group, basis)
        o, h, l, c = mi.iloc[0], mi.max(), mi.min(), mi.iloc[-1]
        o_bid, o_ask = group["bid"].iloc[0], group["ask"].iloc[0]
        c_bid, c_ask = group["bid"].iloc[-1], group["ask"].iloc[-1]
        spread_mean = float((group["ask"] - group["bid"]).mean())
        n_ticks = len(group)
        t_open_ns = int(group["ts_ns"].iloc[0])
        t_close_ns = int(group["ts_ns"].iloc[-1])
        
        rows.append([
            symbol, "1m", t_open_ns, t_close_ns, o, h, l, c,
            o_bid, o_ask, c_bid, c_ask, spread_mean, n_ticks, 0.0,
            group.index[0], group.index[-1], 0
        ])
    
    bars = pd.DataFrame(rows, columns=BAR_COLUMNS)
    tick_slices = df[["bar_idx_1m", "ts_ns", "bid", "ask"]].copy()
    
    return bars, tick_slices

def _tick_bars_enhanced(df: pd.DataFrame, N: int, basis: str, symbol: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Enhanced tick bars with improved organization"""
    total = len(df)
    k = total // N + (1 if total % N else 0)
    
    bar_indices = np.repeat(np.arange(k), N)[:total]
    df[f"bar_idx_{N}t"] = bar_indices
    
    rows = []
    mid = _compute_mid(df, basis).values
    
    for i in range(k):
        s = i * N
        e = min((i + 1) * N, total)
        seg = df.iloc[s:e]
        if seg.empty:
            continue
            
        mi = mid[s:e]
        o, h, l, c = mi[0], mi.max(), mi.min(), mi[-1]
        o_bid, o_ask = seg["bid"].iloc[0], seg["ask"].iloc[0]
        c_bid, c_ask = seg["bid"].iloc[-1], seg["ask"].iloc[-1]
        spread_mean = float((seg["ask"] - seg["bid"]).mean())
        n_ticks = len(seg)
        t_open_ns = int(seg["ts_ns"].iloc[0])
        t_close_ns = int(seg["ts_ns"].iloc[-1])
        
        rows.append([
            symbol, f"{N}t", t_open_ns, t_close_ns, o, h, l, c,
            o_bid, o_ask, c_bid, c_ask, spread_mean, n_ticks, 0.0,
            seg.index[0], seg.index[-1], 0
        ])
    
    bars = pd.DataFrame(rows, columns=BAR_COLUMNS)
    tick_slices = df[[f"bar_idx_{N}t", "ts_ns", "bid", "ask"]].copy()
    
    return bars, tick_slices

def run(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhanced DataIngest v2.2 with improved tick-slice export and manifest
    """
    csv_path = pathlib.Path(config["csv_path"])
    out_dir = pathlib.Path(config["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    
    symbol = config.get("symbol", "UNKNOWN")
    basis = config.get("price_basis", "mid")
    max_gap_s = config.get("max_gap_seconds", 300)
    export_slices = config.get("export_slices", True)
    
    _log_line(out_dir, "start", 0, f"DataIngest v{MODULE_VERSION} starting")
    
    # Load and validate data
    _log_line(out_dir, "load", 10, f"loading {csv_path}")
    df = pd.read_csv(csv_path)
    _ensure_cols(df)
    
    _log_line(out_dir, "normalize", 20, "normalize timestamps")
    df = _normalize_time(df)
    
    _log_line(out_dir, "sort", 30, "sort and dedupe")
    df = _sort_and_dedupe(df)
    
    _log_line(out_dir, "validate", 35, "quality checks")
    _neg_spread_check(df)
    
    _log_line(out_dir, "gaps", 40, "gap analysis")
    gaps, coverage = _gap_report(df, max_gap_s)
    
    # Save normalized raw data
    raw_norm = out_dir / "raw_norm.parquet"
    _write_parquet_optimized(df[["timestamp", "bid", "ask", "ts_ns"]], raw_norm)
    
    frames_out = {}
    
    # Process bar frames with enhanced tick slice export
    for frame in config.get("bar_frames", []):
        if frame.get("type") == "time" and frame.get("unit") == "1m":
            _log_line(out_dir, "bars_1m", 50, "building 1m bars with enhanced tick slices")
            bars, tick_slices = _time_bars_1m_enhanced(df, basis, symbol)
            
            # Save bars
            bars_path = out_dir / "bars_1m.parquet"
            _write_parquet_optimized(bars, bars_path)
            
            # Create event-based tick slices
            slice_info = _create_event_tick_slices(
                tick_slices, bars, out_dir, "1m", export_slices
            )
            
            frames_out["1m"] = {
                "path": str(bars_path.relative_to(out_dir)),
                "tick_slices": slice_info
            }
            
        elif frame.get("type") == "tick":
            N = int(frame.get("count", 0))
            if N > 0:
                _log_line(out_dir, f"bars_{N}t", 60, f"building {N}t bars with enhanced tick slices")
                bars, tick_slices = _tick_bars_enhanced(df, N, basis, symbol)
                
                # Save bars
                bars_path = out_dir / f"bars_{N}tick.parquet"
                _write_parquet_optimized(bars, bars_path)
                
                # Create event-based tick slices
                slice_info = _create_event_tick_slices(
                    tick_slices, bars, out_dir, f"{N}t", export_slices
                )
                
                frames_out[f"{N}t"] = {
                    "path": str(bars_path.relative_to(out_dir)),
                    "tick_slices": slice_info
                }
    
    # Enhanced quality report
    _log_line(out_dir, "quality", 80, "generating enhanced quality report")
    quality = {
        "n_raw_rows": int(len(df)),
        "gap_items": gaps,
        "gap_coverage_percent": coverage,
        "neg_spread_found": False,
        "spread_stats": {
            "mean": float((df["ask"] - df["bid"]).mean()),
            "std": float((df["ask"] - df["bid"]).std()),
            "p50": float((df["ask"] - df["bid"]).quantile(0.5)),
            "p95": float((df["ask"] - df["bid"]).quantile(0.95)),
            "p99": float((df["ask"] - df["bid"]).quantile(0.99)),
        },
        "time_range": {
            "start": pd.to_datetime(df["ts_ns"].iloc[0], unit='ns', utc=True).isoformat(),
            "end": pd.to_datetime(df["ts_ns"].iloc[-1], unit='ns', utc=True).isoformat(),
            "duration_hours": float((df["ts_ns"].iloc[-1] - df["ts_ns"].iloc[0]) / (3600 * 1_000_000_000))
        }
    }
    write_json(out_dir / "quality_report.json", quality)
    
    # Enhanced manifest with v2.2 features
    _log_line(out_dir, "manifest", 90, "generating enhanced manifest")
    manifest = {
        "run_ts": dt.datetime.utcnow().isoformat(),
        "module": "data_ingest",
        "module_version": MODULE_VERSION,
        "schema_version": SCHEMA_VERSION,
        "bar_rules_id": BAR_RULES_ID,
        "symbol": symbol,
        "price_basis": basis,
        "pip_size": config.get("pip_size", 0.0001),
        "export_slices": export_slices,
        "compression_enabled": True,
        "input": {
            "csv_path": str(csv_path),
            "sha256": sha256_of_file(csv_path) if csv_path.exists() else None,
            "file_size_bytes": csv_path.stat().st_size if csv_path.exists() else 0
        },
        "outputs": frames_out,
        "performance": {
            "total_ticks_processed": int(len(df)),
            "processing_time_estimate": "calculated_during_run"
        }
    }
    write_json(out_dir / "manifest.json", manifest)
    
    # Save configuration
    config_path = out_dir / "config_used.json"
    write_json(config_path, config)
    
    _log_line(out_dir, "done", 100, f"DataIngest v{MODULE_VERSION} completed successfully")
    
    return {
        "symbol": symbol,
        "frames": frames_out,
        "quality_report": str(out_dir / "quality_report.json"),
        "manifest": str(out_dir / "manifest.json"),
        "log": str(out_dir / "progress.jsonl"),
        "module_version": MODULE_VERSION
    }
