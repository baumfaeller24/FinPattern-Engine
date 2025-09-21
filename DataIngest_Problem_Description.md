# Problem Description: DataIngest Module

## 1. Goal

The `DataIngest` module is designed to process a large CSV file of tick data (timestamp, bid, ask) and generate two types of output files:

- **Bar Data:** Parquet files containing OHLCV bars for different timeframes (1-minute, 100-tick, 1000-tick).
- **Tick Slices:** A Parquet file containing the raw tick data, indexed by the bar they belong to. This is required by the downstream `Labeling` module.

## 2. The Problem

The module consistently fails with one of two errors:

- **`OSError: Couldn't deserialize thrift: TProtocolException: Invalid data`:** This indicates that the Parquet files are being corrupted during the incremental writing process.
- **`Killed`:** The process is terminated by the OS due to excessive memory usage.

I have tried several approaches to solve this, including:

- **Chunking:** Processing the CSV in smaller chunks to reduce memory usage.
- **Fixed Schema:** Using a fixed PyArrow schema to prevent schema inconsistencies between chunks.
- **Disabling Dictionaries:** Disabling dictionary encoding for string columns to avoid dictionary-related corruption.
- **Streaming:** Implementing a line-by-line processing approach to minimize memory overhead.

Despite these efforts, the problem persists. The core issue seems to be a fundamental conflict between the large data volume, the limited memory resources, and the complexities of incremental Parquet file generation.

## 3. Request for Assistance

I am requesting your assistance to develop a robust and memory-efficient Python script for the `DataIngest` module. The script must be able to:

1. Process a large CSV file (millions of rows) with the columns `symbol`, `timestamp`, `bid`, `ask`.
2. Generate Parquet files for 1-minute, 100-tick, and 1000-tick bars.
3. Generate a Parquet file of tick slices, indexed by the 1000-tick bar they belong to.
4. Operate within a memory-constrained environment (e.g., less than 2GB of RAM).

## 4. Current Code

Here is the latest version of the `data_ingest.py` script:

```python
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
```

## 5. Validation Script

This is the script I am using to validate the module:

```python
import sys
import os
import json
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '..')))

from core.data_ingest.data_ingest import run as data_ingest_run

config = {
    "out_dir": "/home/ubuntu/FinPattern-Engine/output/data_ingest",
    "csv": {
        "path": "/home/ubuntu/FinPattern-Engine/data/EURUSD-2025-07.csv"
    },
    "symbol": "EURUSD",
    "price_basis": "mid",
    "max_missing_gap_seconds": 60,
    "trim_weekend": True,
    "bar_frames": [
        {"type": "time", "unit": "1m"},
        {"type": "tick", "count": 100},
        {"type": "tick", "count": 1000}
    ],
    "pip_size": 0.0001,
    "chunksize": 50000
}

data_ingest_output = data_ingest_run(config)

print(json.dumps(data_ingest_output, indent=2))

for frame, output in data_ingest_output["outputs"].items():
    path = output["path"]
    print(f"Checking {frame} output file: {path}")
    if os.path.exists(path):
        print(f"File exists.")
        try:
            df = pd.read_parquet(path)
            print(f"Successfully read {len(df)} rows.")
            print(df.head())
        except Exception as e:
            print(f"Error reading Parquet file: {e}")
    else:
        print(f"File does not exist.")
```

## 6. Error Logs

Here are the most recent error logs:

```
ubuntu@sandbox:~/FinPattern-Engine/notebooks $ source /home/ubuntu/.user_env && cd . && cd /home/ubuntu/FinPattern-Engine/notebooks && python3 validation_script.py
Killed
```

```
OSError: Could not open Parquet input source '<Buffer>': Couldn't deserialize thrift: TProtocolException: Invalid data
```

I would appreciate a solution that is both correct and robust. Thank you for your help.

