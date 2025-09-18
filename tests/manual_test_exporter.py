import pandas as pd
from pathlib import Path
import sys
sys.path.append('/home/ubuntu/FinPattern-Engine')
from core.exporter import exporter

def _create_demo_labeled_events():
    """Create sample labeled events for demonstration"""
    import numpy as np
    
    np.random.seed(42)
    n_events = 50
    
    base_time = pd.Timestamp("2025-01-01 09:00:00", tz="UTC")
    
    events = []
    for i in range(n_events):
        entry_time = base_time + pd.Timedelta(minutes=i * 30)
        exit_time = entry_time + pd.Timedelta(minutes=np.random.randint(15, 120))
        
        label = np.random.choice([1, -1, 0], p=[0.3, 0.3, 0.4])
        hit_type = label if label != 0 else 0
        
        events.append({
            "event_index": i,
            "entry_time": entry_time,
            "exit_time": exit_time,
            "entry_price": 1.1000 + np.random.normal(0, 0.002),
            "label": label,
            "hit_type": hit_type,
            "return": np.random.normal(0, 0.001),
            "volatility_used": np.random.uniform(0.0001, 0.0005)
        })
    
    return pd.DataFrame(events)

if __name__ == "__main__":
    labeled_events = _create_demo_labeled_events()
    events_path = "/home/ubuntu/demo_labeled_events.parquet"
    labeled_events.to_parquet(events_path, index=False)

    config = {
        "labeled_events_path": events_path,
        "out_dir": "/home/ubuntu/export_output",
        "export_formats": ["pine_script", "nautilus_trader"],
        "strategy_name": "FinPattern Strategy"
    }

    result = exporter.run(config)
    print(result)

