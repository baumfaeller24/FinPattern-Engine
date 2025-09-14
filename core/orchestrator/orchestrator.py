from __future__ import annotations
import importlib, json, pathlib, uuid, datetime as dt

def run(config: dict, module_path: str) -> dict:
    run_id = config.get("run_id") or dt.datetime.utcnow().strftime("%Y%m%dT%H%M%S") + "_" + uuid.uuid4().hex[:6]
    module_name = module_path.split(".")[-1]
    out_root = pathlib.Path(config.get("out_dir", "./runs/")) / run_id / module_name
    out_root.mkdir(parents=True, exist_ok=True)
    progress_path = out_root / "progress.jsonl"

    def log(step, pct, msg):
        with progress_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "timestamp": dt.datetime.utcnow().isoformat(),
                "module": module_name,
                "step": step,
                "percent": pct,
                "message": msg
            }) + "\n")

    log("start", 1, "module start")
    try:
        mod = importlib.import_module(module_path)
        cfg = dict(config)
        cfg["out_dir"] = str(out_root)
        result = mod.run(cfg)
        log("done", 100, "module done")
        return {"run_id": run_id, "module": module_name, "out_dir": str(out_root), "result": result}
    except Exception as e:
        log("error", 0, f"error: {e!r}")
        raise
