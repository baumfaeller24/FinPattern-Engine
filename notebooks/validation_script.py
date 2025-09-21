import sys
import os
import json
import pyarrow.dataset as ds

sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '..')))

from core.data_ingest.data_ingest_streaming import run as data_ingest_run

config = {
    "out_dir": "/home/ubuntu/FinPattern-Engine/output/data_ingest",
    "csv": {
        "path": "/home/ubuntu/FinPattern-Engine/data/EURUSD-2025-07.csv"
    },
    "symbol": "EURUSD",
    "chunk_bytes": 64 * 1024 * 1024,
    "flush_every_bars": 2000
}

data_ingest_output = data_ingest_run(config)

print(json.dumps(data_ingest_output, indent=2))

for frame, output in data_ingest_output["outputs"].items():
    path = output["path"]
    print(f"Checking {frame} output directory: {path}")
    if os.path.exists(path):
        print(f"Directory exists.")
        try:
            dataset = ds.dataset(path, format="parquet")
            table = dataset.to_table()
            print(f"Successfully read {table.num_rows} rows.")
            print(table.to_pandas().head())
        except Exception as e:
            print(f"Error reading Parquet dataset: {e}")
    else:
        print(f"Directory does not exist.")

