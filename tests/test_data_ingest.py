#!/usr/bin/env python3
"""
Simple test script for the DataIngest module
"""

import sys
from pathlib import Path
import json
import yaml

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from core.data_ingest.data_ingest import run


def test_demo_mode():
    """Test DataIngest with demo data."""
    print("🚀 Testing DataIngest module with demo data...")
    
    # Load config from file
    config_path = Path("configs/ingest_demo.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    # Override output directory
    config['out_dir'] = './runs/test_demo'
    
    try:
        result = run(config)
        
        print("✅ DataIngest completed successfully!")
        print(f"📊 Symbol: {result['symbol']}")
        print(f"📁 Generated frames: {len(result['frames'])}")
        
        # Show generated files
        for frame_name, frame_path in result['frames'].items():
            print(f"   - {frame_name}: {frame_path}")
        
        # Show quality report
        if 'quality_report' in result:
            with open(result['quality_report']) as f:
                quality = json.load(f)
            print(f"📈 Processed ticks: {quality['n_raw_rows']:,}")
            print(f"📊 Gap coverage: {quality['gap_coverage_percent']:.1f}%")
        
        # Show manifest
        if 'manifest' in result:
            with open(result['manifest']) as f:
                manifest = json.load(f)
            print(f"🔖 Module version: {manifest['module_version']}")
            print(f"🔖 Schema version: {manifest['schema_version']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_demo_mode()
    sys.exit(0 if success else 1)
