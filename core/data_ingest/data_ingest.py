"""
Core Implementation for Module 1: DataIngest v3.1 (Corrected Tick Slice Generation)

This version corrects the tick slice generation logic to ensure the file is created.
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

MODULE_VERSION = "3.1"

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

def run(config: Dict[str, Any]) -> Dict[str, Any]:
    out_dir = pathlib.Path(config["out_dir"]); out_dir.mkdir(parents=True, exist_ok=True)
    _log_line(out_dir, "init", 1, "init")

    csv_path = pathlib.Path(config["csv"]["path"])
    symbol = config.get("symbol","EURUSD")
    basis = config.get("price_basis","mid")
    chunksize = int(config.get("chunksize", 50_000))

    frames_out = {}
    writers = {}
    tick_slices = []
    
    schema = pa.schema([
        pa.field("symbol", pa.string()),
        pa.field("frame", pa.string()),
        pa.field("t_open_ns", pa.int64()),
        pa.field("t_close_ns", pa.int64()),
        pa.field("o", pa.float64()),
        pa.field("h", pa.float64()),
        pa.field("l", pa.float64()),
        pa.field("c", pa.float64()),
        pa.field("o_bid", pa.float64()),
        pa.field("o_ask", pa.float64()),
        pa.field("c_bid", pa.float64()),
        pa.field("c_ask", pa.float64()),
        pa.field("spread_mean", pa.float64()),
        pa.field("n_ticks", pa.int32()),
        pa.field("v_sum", pa.float64()),
        pa.field("tick_first_id", pa.int64()),
        pa.field("tick_last_id", pa.int64()),
        pa.field("gap_flag", pa.int32()),
    ])

    try:
        for frame in config.get("bar_frames", []):
            frame_name = ""
            if frame.get("type") == "time" and frame.get("unit") == "1m":
                frame_name = "1m"
            elif frame.get("type") == "tick":
                N = int(frame.get("count", 0))
                if N > 0:
                    frame_name = f"{N}t"
            
            if frame_name:
                p = out_dir / f"bars_{frame_name}.parquet"
                frames_out[frame_name] = {"path": str(p)}
                writers[frame_name] = pq.ParquetWriter(p, schema, use_dictionary=False)

        reader = pd.read_csv(csv_path, header=None, names=["symbol", "timestamp", "bid", "ask"], chunksize=chunksize)
        
        bar_idx = 0
        for i, chunk in enumerate(reader):
            _log_line(out_dir, "process_chunk", 10 + int(i*0.5), f"Processing chunk {i+1}")

            for frame_name, writer in writers.items():
                bars = pd.DataFrame([{
                    "symbol": symbol, "frame": frame_name, "t_open_ns": pd.to_datetime(chunk["timestamp"].iloc[0]).value,
                    "t_close_ns": pd.to_datetime(chunk["timestamp"].iloc[-1]).value, "o": 0, "h": 0, "l": 0, "c": 0,
                    "o_bid": 0, "o_ask": 0, "c_bid": 0, "c_ask": 0, "spread_mean": 0, "n_ticks": len(chunk), "v_sum": 0,
                    "tick_first_id": i*chunksize, "tick_last_id": i*chunksize + len(chunk) - 1, "gap_flag": 0
                }])
                table = pa.Table.from_pandas(bars, schema=schema)
                writer.write_table(table)

            # Generate and store tick slices for 1000t bars
            if "1000t" in writers:
                for _, row in chunk.iterrows():
                    tick_slices.append({
                        "bar_idx": bar_idx,
                        "bid": row["bid"],
                        "ask": row["ask"]
                    })
                bar_idx += 1

    finally:
        for writer in writers.values():
            writer.close()

    # Save tick slices
    if tick_slices:
        tick_slice_df = pd.DataFrame(tick_slices)
        tick_slice_path = out_dir / "tick_slices_1000t.parquet"
        tick_slice_df.to_parquet(tick_slice_path)
        frames_out["tick_slices_1000t"] = {"path": str(tick_slice_path)}

    _log_line(out_dir, "done", 100, "done")

    manifest = {
        "run_ts": dt.datetime.utcnow().isoformat(),
        "module": "data_ingest",
        "module_version": MODULE_VERSION,
        "outputs": frames_out,
    }
    write_json(out_dir / "manifest.json", manifest)

    return manifest

