import sys
import os
import json
import pyarrow.dataset as ds

sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '..')))

from core.data_ingest.data_ingest_parquet import run as data_ingest_run

config = {
    "out_dir": "/home/ubuntu/FinPattern-Engine/output/data_ingest",
    "parquet": {
        "path": "/home/ubuntu/FinPattern-Engine/data/EURUSD-2025-07.parquet"
    },
    "symbol": "EURUSD",
    "chunksize": 100_000,
    "flush_every_bars": 1000
}

print("Starting DataIngest validation with real EUR/USD tick data...")
print(f"Input file: {config['parquet']['path']}")
print(f"Output directory: {config['out_dir']}")

try:
    data_ingest_output = data_ingest_run(config)
    print("\n" + "="*60)
    print("VALIDATION RESULTS")
    print("="*60)
    print(json.dumps(data_ingest_output, indent=2))

    print("\n" + "="*60)
    print("OUTPUT FILE ANALYSIS")
    print("="*60)

    for frame, output in data_ingest_output["outputs"].items():
        path = output["path"]
        print(f"\n{frame.upper()} Dataset:")
        print(f"  Path: {path}")
        
        if os.path.exists(path):
            try:
                dataset = ds.dataset(path, format="parquet")
                table = dataset.to_table()
                df = table.to_pandas()
                
                print(f"  Status: ✅ SUCCESS")
                print(f"  Rows: {len(df):,}")
                print(f"  Columns: {list(df.columns)}")
                print(f"  Memory usage: {df.memory_usage(deep=True).sum() / 1024 / 1024:.1f} MB")
                
                if len(df) > 0:
                    print(f"  Time range: {df['t_open_ns'].min()} to {df['t_close_ns'].max()}")
                    print(f"  Sample data:")
                    print(f"    {df.head(3).to_string(index=False)}")
                
            except Exception as e:
                print(f"  Status: ❌ ERROR - {e}")
        else:
            print(f"  Status: ❌ FILE NOT FOUND")

    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    
    success_count = 0
    total_count = len(data_ingest_output["outputs"])
    
    for frame, output in data_ingest_output["outputs"].items():
        if os.path.exists(output["path"]):
            try:
                dataset = ds.dataset(output["path"], format="parquet")
                table = dataset.to_table()
                if len(table) > 0:
                    success_count += 1
                    print(f"✅ {frame}: {len(table):,} records")
                else:
                    print(f"⚠️  {frame}: Empty dataset")
            except:
                print(f"❌ {frame}: Read error")
        else:
            print(f"❌ {frame}: File not found")
    
    print(f"\nOverall: {success_count}/{total_count} modules successful")
    
    if success_count == total_count:
        print("🎉 BACKEND VALIDATION PASSED! All DataIngest outputs generated successfully.")
    else:
        print("⚠️  BACKEND VALIDATION PARTIAL - Some outputs missing or corrupted.")

except Exception as e:
    print(f"\n❌ VALIDATION FAILED: {e}")
    import traceback
    traceback.print_exc()
