import sys
import os
import json
import pandas as pd
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '..')))

from core.splitter.splitter import run as splitter_run
from core.exporter.exporter import run as exporter_run

def validate_splitter_exporter():
    """
    Validate the Splitter and Exporter modules.
    """
    print("="*60)
    print("SPLITTER & EXPORTER MODULES VALIDATION")
    print("="*60)
    
    # --- 1. Splitter Validation ---
    print("\n--- SPLITTER VALIDATION ---")
    splitter_config = {
        "out_dir": "/home/ubuntu/FinPattern-Engine/output/splitter",
        "data_path": "/home/ubuntu/FinPattern-Engine/output/feature_engine/sample_labeled_features_v2_1.parquet",
        "time_column": "t_close_ns",
        "split_method": "time_based",
        "split_params": {
            "train_ratio": 0.7,
            "val_ratio": 0.15,
            "test_ratio": 0.15
        }
    }
    
    print(f"Input file: {splitter_config['data_path']}")
    
    try:
        splitter_output = splitter_run(splitter_config)
        print("\nSplitter Results:")
        print(json.dumps(splitter_output, indent=2))
        
        if splitter_output.get("splits_created", 0) > 0:
            print("🎉 Splitter Validation Passed!")
            # Construct the paths to the split files manually
            splits_dir = Path(splitter_output["splits_directory"]) / "split_000"
            splitter_output["split_files"] = {
                "train": str(splits_dir / "train_data.parquet"),
                "validation": str(splits_dir / "val_data.parquet"),
                "test": str(splits_dir / "test_data.parquet")
            }
        else:
            print("❌ Splitter Validation Failed!")
            return False
            
    except Exception as e:
        print(f"❌ Splitter Validation Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # --- 2. Exporter Validation ---
    print("\n--- EXPORTER VALIDATION ---")
    exporter_config = {
        "out_dir": "/home/ubuntu/FinPattern-Engine/output/exporter",
        "labeled_events_path": splitter_output["split_files"]["train"], # Use train set for export
        "export_formats": ["pine_script", "nautilus_trader"],
        "strategy_name": "MyScalpingStrategy"
    }
    
    print(f"Input file: {exporter_config['labeled_events_path']}")
    
    try:
        exporter_output = exporter_run(exporter_config)
        print("\nExporter Results:")
        print(json.dumps(exporter_output, indent=2))
        
        if len(exporter_output.get("output_files", {})) > 0:
            print("🎉 Exporter Validation Passed!")
            for format, path in exporter_output["output_files"].items():
                print(f"  ✅ {format}: {path}")
        else:
            print("❌ Exporter Validation Failed!")
            return False
            
    except Exception as e:
        print(f"❌ Exporter Validation Failed: {e}")
        return False
        
    return True

if __name__ == "__main__":
    success = validate_splitter_exporter()
    if success:
        print("\n🎉 SPLITTER & EXPORTER VALIDATION PASSED!")
    else:
        print("\n❌ SPLITTER & EXPORTER VALIDATION FAILED!")

