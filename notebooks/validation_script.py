import sys
import os
import json
import pandas as pd

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '..')))

from core.data_ingest.data_ingest import run as data_ingest_run

# Configuration for the DataIngest module
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
    "pip_size": 0.0001
}

# Run the DataIngest module
data_ingest_output = data_ingest_run(config)

# Print the output manifest
print(json.dumps(data_ingest_output, indent=2))

# Verify the output files
for frame, output in data_ingest_output["outputs"].items():
    path = output["path"]
    print(f"Checking {frame} output file: {path}")
    if os.path.exists(path):
        print(f"File exists.")
        df = pd.read_parquet(path)
        print(f"Successfully read {len(df)} rows.")
        print(df.head())
    else:
        print(f"File does not exist.")

