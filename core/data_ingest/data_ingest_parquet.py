'''
Core Implementation for Module 1: DataIngest v4.0 (Parquet Input)

This version reads from clean Parquet files and implements robust streaming processing.
'''
from __future__ import annotations
import os, pathlib, json, datetime as dt, uuid
from typing import Dict, Any, List, Tuple
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# ---------- Config helpers ----------
def _log_line(out_dir: pathlib.Path, step: str, pct: int, msg: str):
    p = out_dir / "progress.jsonl"
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "timestamp": dt.datetime.utcnow().isoformat(),
            "module": "data_ingest",
            "step": step, "percent": pct, "message": msg
        }) + "\n")

def _atomic_write_table(table: pa.Table, out_dir: pathlib.Path, subdir: str, compression: str = "zstd"):
    path_dir = out_dir / subdir
    path_dir.mkdir(parents=True, exist_ok=True)
    tmp = path_dir / (f".tmp-{uuid.uuid4().hex}.parquet")
    final = path_dir / (f"part-{uuid.uuid4().hex}.parquet")
    pq.write_table(table, tmp, compression=compression, use_dictionary=False)
    os.replace(tmp, final)
    return str(final)

# ---------- Schemas ----------
BAR_SCHEMA = pa.schema([
    ("symbol", pa.string()), ("frame", pa.string()),
    ("t_open_ns", pa.int64()), ("t_close_ns", pa.int64()),
    ("o", pa.float64()), ("h", pa.float64()), ("l", pa.float64()), ("c", pa.float64()),
    ("o_bid", pa.float64()), ("o_ask", pa.float64()), ("c_bid", pa.float64()), ("c_ask", pa.float64()),
    ("spread_mean", pa.float64()), ("n_ticks", pa.int32()),
    ("v_sum", pa.float64()),
    ("tick_first_id", pa.int64()), ("tick_last_id", pa.int64()),
    ("gap_flag", pa.int32()),
])

TICKS_SLICE_SCHEMA = pa.schema([
    ("bar_idx", pa.int64()),
    ("tick_id", pa.int64()),
    ("timestamp", pa.int64()),
    ("bid", pa.float64()),
    ("ask", pa.float64())
])

# ---------- Aggregators ----------
class MinuteBarAgg:
    def __init__(self, symbol: str, frame: str = "1m"):
        self.symbol = symbol; self.frame = frame
        self.reset()

    def reset(self):
        self.open_ns = None; self.close_ns = None
        self.o = None; self.h = None; self.l = None; self.c = None
        self.o_bid = None; self.o_ask = None; self.c_bid = None; self.c_ask = None
        self.spread_sum = 0.0; self.n = 0
        self.tick_first_id = None; self.tick_last_id = None
        self.gap_flag = 0

    def minute_bucket(self, ts_ns: int) -> int:
        return (ts_ns // 1_000_000_000) // 60

    def add_tick(self, ts_ns: int, bid: float, ask: float, tick_id: int):
        mid = (bid + ask) * 0.5
        if self.open_ns is None:
            self.open_ns = ts_ns
            self.o = mid; self.h = mid; self.l = mid; self.c = mid
            self.o_bid = bid; self.o_ask = ask
            self.tick_first_id = tick_id
        if mid > self.h: self.h = mid
        if mid < self.l: self.l = mid
        self.c = mid; self.c_bid = bid; self.c_ask = ask
        self.close_ns = ts_ns
        self.spread_sum += (ask - bid); self.n += 1
        self.tick_last_id = tick_id

    def should_flush(self, next_ts_ns: int) -> bool:
        if self.open_ns is None: return False
        return (self.minute_bucket(next_ts_ns) != self.minute_bucket(self.open_ns))

    def flush(self) -> dict | None:
        if self.open_ns is None or self.n == 0: return None
        out = {
            "symbol": self.symbol, "frame": self.frame,
            "t_open_ns": self.open_ns, "t_close_ns": self.close_ns,
            "o": self.o, "h": self.h, "l": self.l, "c": self.c,
            "o_bid": self.o_bid, "o_ask": self.o_ask,
            "c_bid": self.c_bid, "c_ask": self.c_ask,
            "spread_mean": (self.spread_sum / self.n) if self.n else 0.0,
            "n_ticks": self.n, "v_sum": 0.0,
            "tick_first_id": self.tick_first_id, "tick_last_id": self.tick_last_id,
            "gap_flag": self.gap_flag,
        }
        self.reset()
        return out

class TickBarAgg:
    def __init__(self, symbol: str, N: int):
        self.symbol = symbol; self.N = N
        self.reset()

    def reset(self):
        self.count = 0
        self.open_ns = None; self.close_ns = None
        self.o = None; self.h = None; self.l = None; self.c = None
        self.o_bid = None; self.o_ask = None; self.c_bid = None; self.c_ask = None
        self.spread_sum = 0.0; self.n = 0
        self.tick_first_id = None; self.tick_last_id = None

    def add_tick(self, ts_ns: int, bid: float, ask: float, tick_id: int):
        mid = (bid + ask) * 0.5
        if self.count == 0:
            self.open_ns = ts_ns
            self.o = mid; self.h = mid; self.l = mid; self.c = mid
            self.o_bid = bid; self.o_ask = ask
            self.tick_first_id = tick_id
        self.count += 1
        if mid > self.h: self.h = mid
        if mid < self.l: self.l = mid
        self.c = mid; self.c_bid = bid; self.c_ask = ask
        self.close_ns = ts_ns
        self.spread_sum += (ask - bid); self.n += 1
        self.tick_last_id = tick_id
        return (self.count == self.N)

    def flush(self, frame_name: str) -> dict:
        out = {
            "symbol": self.symbol, "frame": frame_name,
            "t_open_ns": self.open_ns, "t_close_ns": self.close_ns,
            "o": self.o, "h": self.h, "l": self.l, "c": self.c,
            "o_bid": self.o_bid, "o_ask": self.o_ask,
            "c_bid": self.c_bid, "c_ask": self.c_ask,
            "spread_mean": (self.spread_sum / self.n) if self.n else 0.0,
            "n_ticks": self.n, "v_sum": 0.0,
            "tick_first_id": self.tick_first_id, "tick_last_id": self.tick_last_id,
            "gap_flag": 0
        }
        self.reset()
        return out

# ---------- Main run ----------
def run(config: Dict[str, Any]) -> Dict[str, Any]:
    out_dir = pathlib.Path(config["out_dir"]); out_dir.mkdir(parents=True, exist_ok=True)
    symbol = config.get("symbol", "EURUSD")
    parquet_path = pathlib.Path(config["parquet"]["path"])
    chunksize = int(config.get("chunksize", 100_000))
    flush_every_bars = int(config.get("flush_every_bars", 1000))
    _log_line(out_dir, "init", 1, "Starting DataIngest with Parquet input")

    # Initialize aggregators
    agg_1m = MinuteBarAgg(symbol, "1m")
    agg_100t = TickBarAgg(symbol, 100)
    agg_1000t = TickBarAgg(symbol, 1000)
    
    # Buffers
    bars_1m: List[dict] = []
    bars_100t: List[dict] = []
    bars_1000t: List[dict] = []
    tick_slice_buffer: List[Tuple[int,int,int,float,float]] = []
    current_1000t_bar_idx = 0
    global_tick_id = 0

    # Read Parquet file in chunks
    parquet_file = pq.ParquetFile(parquet_path)
    total_rows = parquet_file.metadata.num_rows
    processed_rows = 0

    for batch in parquet_file.iter_batches(batch_size=chunksize):
        df = batch.to_pandas()
        
        for _, row in df.iterrows():
            ts_ns = row['timestamp'].value  # Convert to nanoseconds
            bid = float(row['bid'])
            ask = float(row['ask'])

            # Minute bars
            if agg_1m.open_ns is not None and agg_1m.should_flush(ts_ns):
                rec = agg_1m.flush()
                if rec: bars_1m.append(rec)
            agg_1m.add_tick(ts_ns, bid, ask, global_tick_id)

            # 100-tick bars
            if agg_100t.add_tick(ts_ns, bid, ask, global_tick_id):
                bars_100t.append(agg_100t.flush("100t"))

            # 1000-tick bars + tick slices
            tick_slice_buffer.append((current_1000t_bar_idx, global_tick_id, ts_ns, bid, ask))
            if agg_1000t.add_tick(ts_ns, bid, ask, global_tick_id):
                bars_1000t.append(agg_1000t.flush("1000t"))
                current_1000t_bar_idx += 1
                
                # Flush tick slices periodically
                if len(tick_slice_buffer) >= 1000:
                    slice_tbl = pa.Table.from_arrays([
                        pa.array([r[0] for r in tick_slice_buffer], type=pa.int64()),
                        pa.array([r[1] for r in tick_slice_buffer], type=pa.int64()),
                        pa.array([r[2] for r in tick_slice_buffer], type=pa.int64()),
                        pa.array([r[3] for r in tick_slice_buffer], type=pa.float64()),
                        pa.array([r[4] for r in tick_slice_buffer], type=pa.float64()),
                    ], schema=TICKS_SLICE_SCHEMA)
                    _atomic_write_table(slice_tbl, out_dir, "tick_slices_1000t")
                    tick_slice_buffer.clear()

            global_tick_id += 1

        processed_rows += len(df)
        progress = int((processed_rows / total_rows) * 90)
        _log_line(out_dir, "processing", 10 + progress, f"Processed {processed_rows:,} / {total_rows:,} rows")

        # Periodic flush of bars
        if len(bars_1m) >= flush_every_bars:
            _atomic_write_table(pa.Table.from_pylist(bars_1m, schema=BAR_SCHEMA), out_dir, "bars_1m")
            bars_1m.clear()
        if len(bars_100t) >= flush_every_bars:
            _atomic_write_table(pa.Table.from_pylist(bars_100t, schema=BAR_SCHEMA), out_dir, "bars_100t")
            bars_100t.clear()
        if len(bars_1000t) >= flush_every_bars:
            _atomic_write_table(pa.Table.from_pylist(bars_1000t, schema=BAR_SCHEMA), out_dir, "bars_1000t")
            bars_1000t.clear()

    # Final flush
    last = agg_1m.flush()
    if last: bars_1m.append(last)
    if bars_1m: _atomic_write_table(pa.Table.from_pylist(bars_1m, schema=BAR_SCHEMA), out_dir, "bars_1m")
    if bars_100t: _atomic_write_table(pa.Table.from_pylist(bars_100t, schema=BAR_SCHEMA), out_dir, "bars_100t")
    if bars_1000t: _atomic_write_table(pa.Table.from_pylist(bars_1000t, schema=BAR_SCHEMA), out_dir, "bars_1000t")
    if tick_slice_buffer:
        slice_tbl = pa.Table.from_arrays([
            pa.array([r[0] for r in tick_slice_buffer], type=pa.int64()),
            pa.array([r[1] for r in tick_slice_buffer], type=pa.int64()),
            pa.array([r[2] for r in tick_slice_buffer], type=pa.int64()),
            pa.array([r[3] for r in tick_slice_buffer], type=pa.float64()),
            pa.array([r[4] for r in tick_slice_buffer], type=pa.float64()),
        ], schema=TICKS_SLICE_SCHEMA)
        _atomic_write_table(slice_tbl, out_dir, "tick_slices_1000t")

    manifest = {
        "run_ts": dt.datetime.utcnow().isoformat(),
        "module": "data_ingest_parquet",
        "outputs": {
            "bars_1m": {"path": str(out_dir / "bars_1m")},
            "bars_100t": {"path": str(out_dir / "bars_100t")},
            "bars_1000t": {"path": str(out_dir / "bars_1000t")},
            "tick_slices_1000t": {"path": str(out_dir / "tick_slices_1000t")}
        }
    }
    with (out_dir / "manifest.json").open("w", encoding="utf-8") as f: json.dump(manifest, f, indent=2)
    _log_line(out_dir, "done", 100, "DataIngest completed successfully")
    return manifest

if __name__ == "__main__":
    import sys, json
    cfg = json.loads(sys.stdin.read())
    print(json.dumps(run(cfg), indent=2))
