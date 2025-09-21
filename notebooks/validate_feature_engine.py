import sys
import os
import json
import pandas as pd
import pyarrow.dataset as ds
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '..')))

from core.feature_engine.feature_engine import run as feature_engine_run

def validate_feature_engine():
    """
    Validate the FeatureEngine module using the labeled data from the previous step.
    """
    print("="*60)
    print("FEATURE ENGINE MODULE VALIDATION")
    print("="*60)
    
    # Configuration for feature engine
    config = {
        "out_dir": "/home/ubuntu/FinPattern-Engine/output/feature_engine",
        "input_file": "/home/ubuntu/FinPattern-Engine/output/labeling_sample/sample_labeled.parquet",
        "feature_config": {
            "sma_periods": [10, 20, 50],
            "ema_periods": [10, 20, 50],
            "rsi_period": 14,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "bbands_period": 20,
            "bbands_std_dev": 2.0
        }
    }
    
    print(f"Input file: {config['input_file']}")
    print(f"Output directory: {config['out_dir']}")
    
    # Check if input file exists
    input_file = Path(config['input_file'])
    if not input_file.exists():
        print(f"❌ ERROR: Input file not found: {input_file}")
        return False
    
    # Run feature engine
    try:
        print("\nStarting feature engineering process...")
        feature_engine_output = feature_engine_run(config)
        
        print("\n" + "="*40)
        print("FEATURE ENGINE RESULTS")
        print("="*40)
        print(json.dumps(feature_engine_output, indent=2))
        
        # Validate outputs
        if feature_engine_output.get("success", False):
            output_file = Path(feature_engine_output["feature_data_path"])
            
            if output_file.exists():
                df_features = pd.read_parquet(output_file)
                print(f"\n✅ SUCCESS: {len(df_features):,} records with {len(df_features.columns)} features")
                print(f"Columns: {list(df_features.columns)}")
                
                # Check for NaN values
                nan_counts = df_features.isnull().sum()
                print(f"\nNaN values per column:")
                print(nan_counts[nan_counts > 0])
                
                print(f"\nSample feature data:")
                print(df_features.head())
                
                return True
            else:
                print(f"❌ ERROR: Output file not found: {output_file}")
                return False
        else:
            print(f"❌ FEATURE ENGINEERING FAILED: {feature_engine_output.get('error', 'Unknown error')}")
            return False
        
    except Exception as e:
        print(f"❌ FEATURE ENGINEERING FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = validate_feature_engine()
    if success:
        print("\n🎉 FEATURE ENGINE MODULE VALIDATION PASSED!")
    else:
        print("\n❌ FEATURE ENGINE MODULE VALIDATION FAILED!")
