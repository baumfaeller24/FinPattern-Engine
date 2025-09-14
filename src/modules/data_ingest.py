"""
DataIngest Module - FinPattern-Engine

Handles raw tick data ingestion, normalization, quality assurance,
and bar generation (time-based and tick-based bars).
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import pyarrow.parquet as pq

logger = logging.getLogger(__name__)


class DataIngest:
    """
    Module for ingesting and preprocessing tick data.
    
    Responsibilities:
    - Load raw tick data from CSV/Parquet
    - Normalize timestamps and data format
    - Remove duplicates and filter outliers
    - Generate different bar types (time-based, tick-based)
    - Quality assurance and gap analysis
    """
    
    def __init__(self):
        self.config = None
        self.raw_data = None
        self.normalized_data = None
        self.bars = {}
        self.quality_report = {}
    
    def run(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for the DataIngest module.
        
        Args:
            config: Configuration dictionary containing data paths and parameters
            
        Returns:
            Dictionary with paths to generated files and quality report
        """
        self.config = config
        logger.info("Starting DataIngest module")
        
        try:
            # Load and normalize raw data
            self._load_raw_data()
            self._normalize_data()
            self._quality_check()
            
            # Generate bars
            self._generate_bars()
            
            # Save results
            output_paths = self._save_results()
            
            logger.info("DataIngest module completed successfully")
            return output_paths
            
        except Exception as e:
            logger.error(f"DataIngest module failed: {str(e)}")
            raise
    
    def _load_raw_data(self) -> None:
        """Load raw tick data from file."""
        data_path = Path(self.config['raw_data_path'])
        
        if not data_path.exists():
            raise FileNotFoundError(f"Data file not found: {data_path}")
        
        logger.info(f"Loading data from {data_path}")
        
        if data_path.suffix.lower() == '.csv':
            self.raw_data = pd.read_csv(data_path)
        elif data_path.suffix.lower() == '.parquet':
            self.raw_data = pd.read_parquet(data_path)
        else:
            raise ValueError(f"Unsupported file format: {data_path.suffix}")
        
        logger.info(f"Loaded {len(self.raw_data)} rows")
    
    def _normalize_data(self) -> None:
        """Normalize timestamps and data format."""
        logger.info("Normalizing data")
        
        # Copy raw data
        self.normalized_data = self.raw_data.copy()
        
        # Normalize timestamp
        if 'timestamp' in self.normalized_data.columns:
            self.normalized_data['timestamp'] = pd.to_datetime(
                self.normalized_data['timestamp'], 
                utc=True
            )
        else:
            raise ValueError("Required column 'timestamp' not found")
        
        # Ensure required columns exist
        required_cols = ['bid', 'ask']
        missing_cols = [col for col in required_cols if col not in self.normalized_data.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Calculate mid price
        self.normalized_data['mid'] = (self.normalized_data['bid'] + self.normalized_data['ask']) / 2
        
        # Sort by timestamp
        self.normalized_data = self.normalized_data.sort_values('timestamp').reset_index(drop=True)
        
        # Remove duplicates
        initial_count = len(self.normalized_data)
        self.normalized_data = self.normalized_data.drop_duplicates(subset=['timestamp'])
        duplicates_removed = initial_count - len(self.normalized_data)
        
        if duplicates_removed > 0:
            logger.warning(f"Removed {duplicates_removed} duplicate timestamps")
    
    def _quality_check(self) -> None:
        """Perform quality checks and generate quality report."""
        logger.info("Performing quality checks")
        
        data = self.normalized_data
        
        # Basic statistics
        self.quality_report = {
            'total_ticks': len(data),
            'date_range': {
                'start': data['timestamp'].min().isoformat(),
                'end': data['timestamp'].max().isoformat()
            },
            'price_stats': {
                'bid_min': float(data['bid'].min()),
                'bid_max': float(data['bid'].max()),
                'ask_min': float(data['ask'].min()),
                'ask_max': float(data['ask'].max()),
                'spread_mean': float((data['ask'] - data['bid']).mean()),
                'spread_std': float((data['ask'] - data['bid']).std())
            }
        }
        
        # Gap analysis
        time_diffs = data['timestamp'].diff().dt.total_seconds()
        max_gap_seconds = self.config.get('max_missing_gap_seconds', 60)
        
        gaps = time_diffs[time_diffs > max_gap_seconds]
        self.quality_report['gaps'] = {
            'count': len(gaps),
            'max_gap_seconds': float(gaps.max()) if len(gaps) > 0 else 0,
            'total_gap_time': float(gaps.sum()) if len(gaps) > 0 else 0
        }
        
        # Outlier detection (simple method)
        spread = data['ask'] - data['bid']
        spread_q99 = spread.quantile(0.99)
        outliers = spread > spread_q99 * 3
        
        self.quality_report['outliers'] = {
            'count': int(outliers.sum()),
            'percentage': float(outliers.mean() * 100)
        }
    
    def _generate_bars(self) -> None:
        """Generate different types of bars."""
        logger.info("Generating bars")
        
        for bar_config in self.config['bar_intervals']:
            bar_type = bar_config['type']
            
            if bar_type == 'time':
                self._generate_time_bars(bar_config)
            elif bar_type == 'tick':
                self._generate_tick_bars(bar_config)
            else:
                logger.warning(f"Unknown bar type: {bar_type}")
    
    def _generate_time_bars(self, bar_config: Dict[str, Any]) -> None:
        """Generate time-based bars."""
        unit = bar_config['unit']
        logger.info(f"Generating {unit} time bars")
        
        data = self.normalized_data.set_index('timestamp')
        
        # Resample to create OHLCV bars
        bars = data['mid'].resample(unit).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last'
        }).dropna()
        
        # Add volume (tick count)
        volume = data.resample(unit).size()
        bars['volume'] = volume
        
        # Add bid/ask info
        bars['bid_close'] = data['bid'].resample(unit).last()
        bars['ask_close'] = data['ask'].resample(unit).last()
        
        bars = bars.reset_index()
        self.bars[f'bars_{unit}'] = bars
        
        logger.info(f"Generated {len(bars)} {unit} bars")
    
    def _generate_tick_bars(self, bar_config: Dict[str, Any]) -> None:
        """Generate tick-based bars."""
        count = bar_config['count']
        logger.info(f"Generating {count}-tick bars")
        
        data = self.normalized_data
        bars_list = []
        
        # Group data into chunks of 'count' ticks
        for i in range(0, len(data), count):
            chunk = data.iloc[i:i+count]
            if len(chunk) < count:
                break  # Skip incomplete last bar
            
            bar = {
                'timestamp': chunk['timestamp'].iloc[-1],
                'open': chunk['mid'].iloc[0],
                'high': chunk['mid'].max(),
                'low': chunk['mid'].min(),
                'close': chunk['mid'].iloc[-1],
                'volume': len(chunk),
                'bid_close': chunk['bid'].iloc[-1],
                'ask_close': chunk['ask'].iloc[-1]
            }
            bars_list.append(bar)
        
        bars = pd.DataFrame(bars_list)
        self.bars[f'bars_{count}tick'] = bars
        
        logger.info(f"Generated {len(bars)} {count}-tick bars")
    
    def _save_results(self) -> Dict[str, Any]:
        """Save all results to files."""
        output_dir = Path(self.config.get('out_dir', './output'))
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_paths = {}
        
        # Save normalized raw data
        raw_path = output_dir / 'raw_norm.parquet'
        self.normalized_data.to_parquet(raw_path)
        output_paths['raw_normalized'] = str(raw_path)
        
        # Save bars
        bar_paths = []
        for bar_name, bar_data in self.bars.items():
            bar_path = output_dir / f'{bar_name}.parquet'
            bar_data.to_parquet(bar_path)
            bar_paths.append(str(bar_path))
        
        output_paths['bars_paths'] = bar_paths
        
        # Save quality report
        import json
        quality_path = output_dir / 'quality_report.json'
        with open(quality_path, 'w') as f:
            json.dump(self.quality_report, f, indent=2)
        output_paths['quality_report'] = str(quality_path)
        
        # Save config used
        config_path = output_dir / 'config_used.yaml'
        import yaml
        with open(config_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False)
        output_paths['config_used'] = str(config_path)
        
        logger.info(f"Results saved to {output_dir}")
        return output_paths


if __name__ == "__main__":
    # Example usage
    config = {
        'raw_data_path': './data/example_ticks.csv',
        'bar_intervals': [
            {'type': 'time', 'unit': '1min'},
            {'type': 'tick', 'count': 100}
        ],
        'out_dir': './output/test',
        'max_missing_gap_seconds': 60
    }
    
    ingest = DataIngest()
    result = ingest.run(config)
