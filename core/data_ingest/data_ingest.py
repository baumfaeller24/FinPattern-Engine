"""
Core Implementation for Module 1: DataIngest v2.4 (Streaming with Schema Correction)

This version corrects the ArrowNotImplementedError by ensuring that the
Parquet schema is correctly inferred from the first chunk of data.
"""

from __future__ import annotations
import pathlib, json, datetime as dt
from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from . import errors as E
from .schema import TICK_SCHEMA, BAR_COLUMNS, SCHEMA_VERSION, BAR_RULES_ID
from .util import sha256_of_file, write_json

MODULE_VERSION = "2.4"

def _log_line(out_dir: pathlib.Path, step: str, pct: int, msg: str):
    p = out_dir / "progress.jsonl"
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "timestamp": dt.datetime.utcnow().isoformat(),
            "module": "data_ingest",
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
    df["ts_ns"] = ts.astype("int64")
    return df

def _sort_and_dedupe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("ts_ns", kind="mergesort")
    df = df.drop_duplicates(subset=["ts_ns","bid","ask"], keep="first")
    return df

def _neg_spread_check(df: pd.DataFrame):
    if (df["ask"] < df["bid"]).any():
        raise ValueError(E.NEGATIVE_SPREAD)

def _trim_weekend(df: pd.DataFrame) -> pd.DataFrame:
    ts = pd.to_datetime(df["ts_ns"], utc=True, unit="ns")
    wd = ts.dt.weekday
    mask = ~wd.isin([5,6])
    return df.loc[mask].copy()

def _time_bars_1m(df: pd.DataFrame, basis: str, symbol: str) -> pd.DataFrame:
    ts = pd.to_datetime(df["ts_ns"], utc=True, unit="ns")
    s = (df["bid"] + df["ask"]) / 2.0
    tmp = pd.DataFrame({"mid": s.values, "bid": df["bid"].values, "ask": df["ask"].values}, index=ts)
    
    o = tmp["mid"].resample("1min").first()
    h = tmp["mid"].resample("1min").max()
    l = tmp["mid"].resample("1min").min()
    c = tmp["mid"].resample("1min").last()
    o_bid = tmp["bid"].resample("1min").first()
    o_ask = tmp["ask"].resample("1min").first()
    c_bid = tmp["bid"].resample("1min").last()
    c_ask = tmp["ask"].resample("1min").last()
    spread_mean = (tmp["ask"] - tmp["bid"]).resample("1min").mean()
    n_ticks = tmp["mid"].resample("1min").count().astype("int32")

    out = pd.DataFrame({
        "symbol": symbol,
        "frame": "1m",
        "t_open_ns": o.index.astype("int64"),
        "t_close_ns": (o.index + pd.Timedelta(minutes=1) - pd.Timedelta(nanoseconds=1)).astype("int64"),
        "o": o.values,"h": h.values,"l": l.values,"c": c.values,
        "o_bid": o_bid.values,"o_ask": o_ask.values,"c_bid": c_bid.values,"c_ask": c_ask.values,
        "spread_mean": spread_mean.values,
        "n_ticks": n_ticks.values,
        "v_sum": np.zeros_like(n_ticks.values, dtype="float64"),
        "tick_first_id": -1,
        "tick_last_id": -1,
        "gap_flag": (n_ticks==0).astype("int32"),
    })
    return out.dropna().reset_index(drop=True)

def _tick_bars(df: pd.DataFrame, N: int, basis: str, symbol: str) -> pd.DataFrame:
    total = len(df)
    k = total // N + (1 if total % N else 0)
    rows = []
    mid = ((df["bid"] + df["ask"]) / 2.0).values
    
    for i in range(k):
        s = i*N
        e = min((i+1)*N, total)
        seg = df.iloc[s:e]
        if seg.empty:
            continue
        mi = mid[s:e]
        o = mi[0]; h = mi.max(); l = mi.min(); c = mi[-1]
        o_bid = seg["bid"].iloc[0]; o_ask = seg["ask"].iloc[0]
        c_bid = seg["bid"].iloc[-1]; c_ask = seg["ask"].iloc[-1]
        spread_mean = float((seg["ask"] - seg["bid"]).mean())
        n_ticks = int(len(seg))
        t_open_ns = int(seg["ts_ns"].iloc[0])
        t_close_ns = int(seg["ts_ns"].iloc[-1])
        rows.append([symbol,f"{N}t",t_open_ns,t_close_ns,o,h,l,c,o_bid,o_ask,c_bid,c_ask,spread_mean,n_ticks,0.0,seg.index[0],seg.index[-1],0])
    return pd.DataFrame(rows, columns=BAR_COLUMNS)

def run(config: Dict[str, Any]) -> Dict[str, Any]:
    out_dir = pathlib.Path(config["out_dir"]); out_dir.mkdir(parents=True, exist_ok=True)
    _log_line(out_dir, "init", 1, "init")

    csv_path = pathlib.Path(config["csv"]["path"])
    symbol = config.get("symbol","EURUSD")
    basis = config.get("price_basis","mid")
    chunksize = int(config.get("chunksize", 100_000))

    frames_out = {}
    writers = {}
    
    reader = pd.read_csv(csv_path, header=None, names=["symbol", "timestamp", "bid", "ask"], chunksize=chunksize)
    
    # Initialize writers with schema from the first chunk
    try:
        first_chunk = next(reader)
    except StopIteration:
        _log_line(out_dir, "error", 10, "CSV file is empty")
        return {}

    first_chunk = first_chunk.rename(columns=str.lower)
    _ensure_cols(first_chunk)
    _neg_spread_check(first_chunk)
    first_chunk = _normalize_time(first_chunk)
    first_chunk = _sort_and_dedupe(first_chunk)
    first_chunk = first_chunk.reset_index(drop=True)

    for frame in config.get("bar_frames", []):
        frame_name = ""
        if frame.get("type") == "time" and frame.get("unit") == "1m":
            frame_name = "1m"
            bars = _time_bars_1m(first_chunk, basis, symbol)
        elif frame.get("type") == "tick":
            N = int(frame.get("count", 0))
            if N > 0:
                frame_name = f"{N}t"
                bars = _tick_bars(first_chunk, N, basis, symbol)
        
        if frame_name and not bars.empty:
            p = out_dir / f"bars_{frame_name}.parquet"
            frames_out[frame_name] = {"path": str(p)}
            table = pa.Table.from_pandas(bars)
            writers[frame_name] = pq.ParquetWriter(p, table.schema)
            writers[frame_name].write_table(table)

    # Process remaining chunks
    for i, chunk in enumerate(reader):
        _log_line(out_dir, "process_chunk", 10 + int(i*0.5), f"Processing chunk {i+2}")
        chunk = chunk.rename(columns=str.lower)
        _ensure_cols(chunk)
        _neg_spread_check(chunk)
        chunk = _normalize_time(chunk)
        chunk = _sort_and_dedupe(chunk)
        chunk = chunk.reset_index(drop=True)

        for frame_name, writer in writers.items():
            if "t" in frame_name:
                N = int(frame_name.replace("t",""))
                bars = _tick_bars(chunk, N, basis, symbol)
            elif frame_name == "1m":
                bars = _time_bars_1m(chunk, basis, symbol)
            
            if not bars.empty:
                table = pa.Table.from_pandas(bars, schema=writer.schema)
                writer.write_table(table)

    # Close all writers
    for writer in writers.values():
        writer.close()

    _log_line(out_dir, "done", 100, "done")

    manifest = {
        "run_ts": dt.datetime.utcnow().isoformat(),
        "module": "data_ingest",
        "module_version": MODULE_VERSION,
        "outputs": frames_out,
    }
    write_json(out_dir / "manifest.json", manifest)

    return manifest

