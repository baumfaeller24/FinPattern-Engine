from __future__ import annotations
import pathlib, json, datetime as dt
from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np

from . import errors as E
from .schema import TICK_SCHEMA, BAR_COLUMNS, SCHEMA_VERSION, BAR_RULES_ID
from .util import sha256_of_file, write_json

MODULE_VERSION = "1.1"

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
    # assume ISO8601 UTC strings; convert to ns epoch
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

def _trim_weekend(df: pd.DataFrame) -> pd.DataFrame:
    # FX 24x5, simple rule: drop Saturday and Sunday by UTC weekday
    ts = pd.to_datetime(df["ts_ns"], utc=True, unit="ns")
    wd = ts.dt.weekday  # Monday=0 ... Sunday=6
    mask = ~wd.isin([5,6])
    return df.loc[mask].copy()

def _compute_mid(df: pd.DataFrame, basis: str) -> pd.Series:
    if basis == "bid":
        return df["bid"]
    if basis == "ask":
        return df["ask"]
    return (df["bid"] + df["ask"]) / 2.0

def _gap_report(df: pd.DataFrame, max_gap_s: int) -> Tuple[List[Tuple[str,str,float]], float]:
    ts = pd.to_datetime(df["ts_ns"], utc=True, unit="ns")
    dt_s = ts.diff().dt.total_seconds().fillna(0.0)
    gaps = dt_s[dt_s > max_gap_s]
    items = []
    for idx, val in gaps.items():
        t_prev = ts.iloc[int(idx)-1] if idx>0 else pd.NaT
        t_now = ts.iloc[int(idx)]
        items.append((t_prev.isoformat(), t_now.isoformat(), float(val)))
    coverage = float((dt_s <= max_gap_s).mean() * 100.0)
    return items, coverage

def _time_bars_1m(df: pd.DataFrame, basis: str, symbol: str) -> pd.DataFrame:
    # resample by minute on UTC
    ts = pd.to_datetime(df["ts_ns"], utc=True, unit="ns")
    s = _compute_mid(df, basis)
    # Create a DataFrame with required fields
    tmp = pd.DataFrame({"mid": s.values, "bid": df["bid"].values, "ask": df["ask"].values}, index=ts)
    o = tmp["mid"].resample("1T").first().ffill()
    h = tmp["mid"].resample("1T").max().ffill()
    l = tmp["mid"].resample("1T").min().ffill()
    c = tmp["mid"].resample("1T").last().ffill()
    o_bid = tmp["bid"].resample("1T").first().ffill()
    o_ask = tmp["ask"].resample("1T").first().ffill()
    c_bid = tmp["bid"].resample("1T").last().ffill()
    c_ask = tmp["ask"].resample("1T").last().ffill()
    spread_mean = (tmp["ask"] - tmp["bid"]).resample("1T").mean().fillna(0.0)
    n_ticks = tmp["mid"].resample("1T").count().fillna(0).astype("int32")

    out = pd.DataFrame({
        "symbol": symbol,
        "frame": "1m",
        "t_open_ns": o.index.view("int64"),
        "t_close_ns": (o.index + pd.Timedelta(minutes=1) - pd.Timedelta(nanoseconds=1)).view("int64"),
        "o": o.values,"h": h.values,"l": l.values,"c": c.values,
        "o_bid": o_bid.values,"o_ask": o_ask.values,"c_bid": c_bid.values,"c_ask": c_ask.values,
        "spread_mean": spread_mean.values,
        "n_ticks": n_ticks.values,
        "v_sum": np.zeros_like(n_ticks.values, dtype="float64"),
        "tick_first_id": -1,
        "tick_last_id": -1,
        "gap_flag": (n_ticks==0).astype("int32"),
    })
    return out[BAR_COLUMNS]

def _tick_bars(df: pd.DataFrame, N: int, basis: str, symbol: str) -> pd.DataFrame:
    # simple chunking: each N rows = one bar
    total = len(df)
    k = total // N + (1 if total % N else 0)
    rows = []
    mid = _compute_mid(df, basis).values
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
    out = pd.DataFrame(rows, columns=BAR_COLUMNS)
    return out

def _write_parquet(df: pd.DataFrame, path: pathlib.Path):
    # rely on pandas+pyarrow
    df.to_parquet(path)

def run(config: Dict[str, Any]) -> Dict[str, Any]:
    out_dir = pathlib.Path(config["out_dir"]); out_dir.mkdir(parents=True, exist_ok=True)
    _log_line(out_dir, "init", 1, "init")

    # Select input path
    demo = bool(config.get("demo", False))
    if demo:
        # relative to this module → samples
        csv_path = (pathlib.Path(__file__).resolve().parents[2] / "samples" / "ticks" / "eurusd_sample.csv")
    else:
        csv_path = pathlib.Path(config["csv"]["path"])

    symbol = config.get("symbol","EURUSD")
    basis = config.get("price_basis","mid")
    max_gap_s = int(config.get("max_missing_gap_seconds",60))

    # Load CSV
    _log_line(out_dir, "load_csv", 5, f"loading {csv_path}")
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        raise RuntimeError(f"{E.IO_ERROR}: {e!r}")

    _ensure_cols(df)
    _neg_spread_check(df)
    _log_line(out_dir, "normalize_time", 10, "normalize timestamps")
    df = _normalize_time(df)

    _log_line(out_dir, "sort_dedupe", 20, "sort & dedupe")
    df = _sort_and_dedupe(df)
    df = df.reset_index(drop=True)

    if config.get("trim_weekend", True):
        _log_line(out_dir, "trim_weekend", 25, "trim weekends")
        df = _trim_weekend(df)

    _log_line(out_dir, "gap_report", 30, "gap analysis")
    gaps, coverage = _gap_report(df, max_gap_s)

    # Save normalized raw
    raw_norm = out_dir / "raw_norm.parquet"
    _write_parquet(df[["timestamp","bid","ask","ts_ns"]], raw_norm)

    frames_out = {}
    for frame in config.get("bar_frames", []):
        if frame.get("type") == "time" and frame.get("unit") == "1m":
            _log_line(out_dir, "bars_1m", 50, "build 1m bars")
            bars = _time_bars_1m(df, basis, symbol)
            p = out_dir / "bars_1m.parquet"
            _write_parquet(bars, p); frames_out["1m"] = str(p)
        if frame.get("type") == "tick":
            N = int(frame.get("count", 0))
            if N > 0:
                _log_line(out_dir, f"bars_{N}t", 60, f"build {N}t bars")
                bars = _tick_bars(df, N, basis, symbol)
                p = out_dir / f"bars_{N}tick.parquet"
                _write_parquet(bars, p); frames_out[f"{N}t"] = str(p)

    # Quality report
    _log_line(out_dir, "quality", 80, "write quality report")
    quality = {
        "n_raw_rows": int(len(df)),
        "gap_items": gaps,
        "gap_coverage_percent": coverage,
        "neg_spread_found": False,
        "spread_stats": {
            "mean": float((df["ask"]-df["bid"]).mean()),
            "p95": float((df["ask"]-df["bid"]).quantile(0.95)),
        }
    }
    write_json(out_dir / "quality_report.json", quality)

    # Manifest
    _log_line(out_dir, "manifest", 90, "write manifest")
    manifest = {
        "run_ts": dt.datetime.utcnow().isoformat(),
        "module": "data_ingest",
        "module_version": MODULE_VERSION,
        "schema_version": SCHEMA_VERSION,
        "bar_rules_id": BAR_RULES_ID,
        "symbol": symbol,
        "price_basis": basis,
        "input": {
            "csv_path": str(csv_path),
            "sha256": sha256_of_file(csv_path) if csv_path.exists() else None
        },
        "outputs": frames_out,
    }
    write_json(out_dir / "manifest.json", manifest)

    # Save config copy
    (out_dir / "config_used.yaml").write_text(json.dumps(config, indent=2), encoding="utf-8")

    _log_line(out_dir, "done", 100, "done")

    return {
        "symbol": symbol,
        "frames": frames_out,
        "quality_report": str(out_dir / "quality_report.json"),
        "manifest": str(out_dir / "manifest.json"),
        "log": str(out_dir / "progress.jsonl")
    }
