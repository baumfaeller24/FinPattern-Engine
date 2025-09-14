from __future__ import annotations
import hashlib, json, pathlib

def sha256_of_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def write_json(path: pathlib.Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")
