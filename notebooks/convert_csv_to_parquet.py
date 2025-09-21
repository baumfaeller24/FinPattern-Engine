import pandas as pd

csv_path = "/home/ubuntu/FinPattern-Engine/data/EURUSD-2025-07.csv"
parquet_path = "/home/ubuntu/FinPattern-Engine/data/EURUSD-2025-07.parquet"

df = pd.read_csv(csv_path, header=None, names=["symbol", "timestamp", "bid", "ask"])
df["timestamp"] = pd.to_datetime(df["timestamp"], format="%Y%m%d %H:%M:%S.%f")
df.to_parquet(parquet_path, index=False)

print(f"Successfully converted {csv_path} to {parquet_path}")

