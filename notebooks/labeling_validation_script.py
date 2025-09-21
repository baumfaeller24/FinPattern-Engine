import sys
import os
import json
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '..')))

from core.labeling.labeling import run as labeling_run

config = {
    "out_dir": "/home/ubuntu/FinPattern-Engine/output/labeling",
    "input_file": "/home/ubuntu/FinPattern-Engine/output/data_ingest/bars_1000tick.parquet",
    "tick_slice_file": "/home/ubuntu/FinPattern-Engine/output/data_ingest/tick_slices_1000t.parquet",
    "volatility_span": 100,
    "tp_pips": 20,
    "sl_pips": 10,
    "timeout_bars": 24,
    "side": "long"
}

labeling_output = labeling_run(config)

print(json.dumps(labeling_output, indent=2))

output_dir = config["out_dir"]

labeled_data_path = labeling_output["labeled_data_path"]
df_labeled = pd.read_parquet(labeled_data_path)
print("Labeled data:")
print(df_labeled.head())
print(df_labeled.info())

report_file = labeling_output["report_file"]
with open(report_file, 'r') as f:
    report = json.load(f)
print("\nLabeling Report:")
print(json.dumps(report, indent=2))

