"""
Module 4: Splitter - Walk-Forward Validation and Data Splitting

This module implements robust data splitting strategies for time series data,
including Walk-Forward validation, which is essential for preventing data leakage
and overfitting in trading strategy development.

Key Features:
1. Time-based splitting (respects temporal order)
2. Walk-Forward validation with configurable windows
3. Session-aware splitting (respects trading sessions)
4. Rolling window validation
5. Automated leakage detection and auditing
6. Comprehensive split reporting and visualization
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
import warnings

MODULE_VERSION = "1.0"

def _log_progress(out_dir: Path, step: str, percent: int, message: str):
    """Progress logging for the Splitter module"""
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "module": "splitter",
        "module_version": MODULE_VERSION,
        "step": step,
        "percent": percent,
        "message": message
    }
    
    log_file = out_dir / "progress.jsonl"
    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

class DataSplitter:
    """
    Advanced data splitting for time series with Walk-Forward validation
    """
    
    def __init__(self, data: pd.DataFrame, time_column: str = "timestamp"):
        """
        Initialize the DataSplitter
        
        Args:
            data: DataFrame with time series data
            time_column: Name of the timestamp column
        """
        self.data = data.copy()
        self.time_column = time_column
        
        # Ensure timestamp column is datetime
        if self.time_column in self.data.columns:
            self.data[self.time_column] = pd.to_datetime(self.data[self.time_column], utc=True)
            self.data = self.data.sort_values(self.time_column).reset_index(drop=True)
        else:
            raise ValueError(f"Time column '{time_column}' not found in data")
        
        self.splits = []
        self.split_metadata = {}
    
    def time_based_split(self, train_ratio: float = 0.7, val_ratio: float = 0.15, 
                        test_ratio: float = 0.15) -> Dict[str, Any]:
        """
        Simple time-based split maintaining temporal order
        
        Args:
            train_ratio: Proportion for training set
            val_ratio: Proportion for validation set  
            test_ratio: Proportion for test set
        
        Returns:
            Dictionary with split information
        """
        if abs(train_ratio + val_ratio + test_ratio - 1.0) > 1e-6:
            raise ValueError("Ratios must sum to 1.0")
        
        n = len(self.data)
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))
        
        split_info = {
            "split_type": "time_based",
            "train_indices": list(range(0, train_end)),
            "val_indices": list(range(train_end, val_end)),
            "test_indices": list(range(val_end, n)),
            "train_ratio": train_ratio,
            "val_ratio": val_ratio,
            "test_ratio": test_ratio,
            "train_period": {
                "start": self.data[self.time_column].iloc[0].isoformat(),
                "end": self.data[self.time_column].iloc[train_end-1].isoformat()
            },
            "val_period": {
                "start": self.data[self.time_column].iloc[train_end].isoformat(),
                "end": self.data[self.time_column].iloc[val_end-1].isoformat()
            },
            "test_period": {
                "start": self.data[self.time_column].iloc[val_end].isoformat(),
                "end": self.data[self.time_column].iloc[-1].isoformat()
            }
        }
        
        return split_info
    
    def walk_forward_split(self, train_window_days: int = 90, test_window_days: int = 30,
                          step_days: int = 30, min_train_samples: int = 100) -> List[Dict[str, Any]]:
        """
        Walk-Forward validation splits
        
        Args:
            train_window_days: Size of training window in days
            test_window_days: Size of test window in days
            step_days: Step size between splits in days
            min_train_samples: Minimum samples required for training
        
        Returns:
            List of split dictionaries
        """
        splits = []
        
        start_date = self.data[self.time_column].min()
        end_date = self.data[self.time_column].max()
        
        current_date = start_date + timedelta(days=train_window_days)
        split_id = 0
        
        while current_date + timedelta(days=test_window_days) <= end_date:
            # Define train period
            train_start = current_date - timedelta(days=train_window_days)
            train_end = current_date
            
            # Define test period
            test_start = current_date
            test_end = current_date + timedelta(days=test_window_days)
            
            # Get indices
            train_mask = (self.data[self.time_column] >= train_start) & \
                        (self.data[self.time_column] < train_end)
            test_mask = (self.data[self.time_column] >= test_start) & \
                       (self.data[self.time_column] < test_end)
            
            train_indices = self.data[train_mask].index.tolist()
            test_indices = self.data[test_mask].index.tolist()
            
            # Check minimum samples requirement
            if len(train_indices) < min_train_samples:
                current_date += timedelta(days=step_days)
                continue
            
            split_info = {
                "split_id": split_id,
                "split_type": "walk_forward",
                "train_indices": train_indices,
                "test_indices": test_indices,
                "train_period": {
                    "start": train_start.isoformat(),
                    "end": train_end.isoformat()
                },
                "test_period": {
                    "start": test_start.isoformat(),
                    "end": test_end.isoformat()
                },
                "train_samples": len(train_indices),
                "test_samples": len(test_indices),
                "train_window_days": train_window_days,
                "test_window_days": test_window_days
            }
            
            splits.append(split_info)
            split_id += 1
            current_date += timedelta(days=step_days)
        
        return splits
    
    def session_aware_split(self, session_start_hour: int = 9, session_end_hour: int = 17,
                           train_sessions: int = 20, test_sessions: int = 5) -> List[Dict[str, Any]]:
        """
        Split data respecting trading sessions
        
        Args:
            session_start_hour: Start hour of trading session (UTC)
            session_end_hour: End hour of trading session (UTC)
            train_sessions: Number of sessions for training
            test_sessions: Number of sessions for testing
        
        Returns:
            List of split dictionaries
        """
        # Identify trading sessions
        self.data['hour'] = self.data[self.time_column].dt.hour
        self.data['date'] = self.data[self.time_column].dt.date
        
        # Filter for trading hours
        session_mask = (self.data['hour'] >= session_start_hour) & \
                      (self.data['hour'] < session_end_hour)
        session_data = self.data[session_mask].copy()
        
        # Group by date to identify sessions
        sessions = session_data.groupby('date').apply(
            lambda x: x.index.tolist() if len(x) > 0 else []
        ).to_dict()
        
        # Remove empty sessions
        sessions = {date: indices for date, indices in sessions.items() if len(indices) > 0}
        session_dates = sorted(sessions.keys())
        
        splits = []
        split_id = 0
        
        # Create rolling session splits
        for i in range(len(session_dates) - train_sessions - test_sessions + 1):
            train_dates = session_dates[i:i + train_sessions]
            test_dates = session_dates[i + train_sessions:i + train_sessions + test_sessions]
            
            train_indices = []
            test_indices = []
            
            for date in train_dates:
                train_indices.extend(sessions[date])
            
            for date in test_dates:
                test_indices.extend(sessions[date])
            
            split_info = {
                "split_id": split_id,
                "split_type": "session_aware",
                "train_indices": train_indices,
                "test_indices": test_indices,
                "train_sessions": len(train_dates),
                "test_sessions": len(test_dates),
                "train_period": {
                    "start": str(train_dates[0]),
                    "end": str(train_dates[-1])
                },
                "test_period": {
                    "start": str(test_dates[0]),
                    "end": str(test_dates[-1])
                },
                "train_samples": len(train_indices),
                "test_samples": len(test_indices)
            }
            
            splits.append(split_info)
            split_id += 1
        
        # Clean up temporary columns
        self.data.drop(['hour', 'date'], axis=1, inplace=True)
        
        return splits
    
    def rolling_window_split(self, window_size: int = 1000, test_size: int = 200,
                           step_size: int = 100) -> List[Dict[str, Any]]:
        """
        Rolling window splits for time series
        
        Args:
            window_size: Size of training window in samples
            test_size: Size of test window in samples
            step_size: Step size between windows
        
        Returns:
            List of split dictionaries
        """
        splits = []
        split_id = 0
        n = len(self.data)
        
        start_idx = 0
        while start_idx + window_size + test_size <= n:
            train_end = start_idx + window_size
            test_end = train_end + test_size
            
            train_indices = list(range(start_idx, train_end))
            test_indices = list(range(train_end, test_end))
            
            split_info = {
                "split_id": split_id,
                "split_type": "rolling_window",
                "train_indices": train_indices,
                "test_indices": test_indices,
                "train_period": {
                    "start": self.data[self.time_column].iloc[start_idx].isoformat(),
                    "end": self.data[self.time_column].iloc[train_end-1].isoformat()
                },
                "test_period": {
                    "start": self.data[self.time_column].iloc[train_end].isoformat(),
                    "end": self.data[self.time_column].iloc[test_end-1].isoformat()
                },
                "train_samples": len(train_indices),
                "test_samples": len(test_indices),
                "window_size": window_size,
                "test_size": test_size
            }
            
            splits.append(split_info)
            split_id += 1
            start_idx += step_size
        
        return splits

def detect_data_leakage(train_data: pd.DataFrame, test_data: pd.DataFrame,
                       time_column: str = "timestamp") -> Dict[str, Any]:
    """
    Detect potential data leakage between train and test sets
    
    Args:
        train_data: Training dataset
        test_data: Test dataset
        time_column: Name of timestamp column
    
    Returns:
        Dictionary with leakage detection results
    """
    leakage_report = {
        "temporal_leakage": False,
        "duplicate_leakage": False,
        "feature_leakage": False,
        "issues": []
    }
    
    # Check temporal leakage
    if time_column in train_data.columns and time_column in test_data.columns:
        train_max_time = train_data[time_column].max()
        test_min_time = test_data[time_column].min()
        
        if train_max_time >= test_min_time:
            leakage_report["temporal_leakage"] = True
            leakage_report["issues"].append({
                "type": "temporal",
                "description": f"Training data extends into test period",
                "train_max": train_max_time.isoformat(),
                "test_min": test_min_time.isoformat()
            })
    
    # Check for duplicate rows
    if len(train_data.columns) == len(test_data.columns):
        # Find common columns
        common_cols = list(set(train_data.columns) & set(test_data.columns))
        if len(common_cols) > 0:
            # Check for exact duplicates
            train_subset = train_data[common_cols]
            test_subset = test_data[common_cols]
            
            # Convert to string for comparison (handles different dtypes)
            train_str = train_subset.astype(str)
            test_str = test_subset.astype(str)
            
            # Find duplicates
            train_tuples = set(train_str.apply(tuple, axis=1))
            test_tuples = set(test_str.apply(tuple, axis=1))
            
            duplicates = train_tuples & test_tuples
            
            if len(duplicates) > 0:
                leakage_report["duplicate_leakage"] = True
                leakage_report["issues"].append({
                    "type": "duplicate",
                    "description": f"Found {len(duplicates)} duplicate rows between train and test",
                    "duplicate_count": len(duplicates)
                })
    
    # Check for future-looking features (basic heuristic)
    suspicious_columns = []
    for col in train_data.columns:
        if any(keyword in col.lower() for keyword in ['future', 'next', 'forward', 'lead']):
            suspicious_columns.append(col)
    
    if suspicious_columns:
        leakage_report["feature_leakage"] = True
        leakage_report["issues"].append({
            "type": "feature",
            "description": "Found columns with suspicious names that might contain future information",
            "suspicious_columns": suspicious_columns
        })
    
    leakage_report["has_leakage"] = any([
        leakage_report["temporal_leakage"],
        leakage_report["duplicate_leakage"],
        leakage_report["feature_leakage"]
    ])
    
    return leakage_report

def run(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function for the Splitter module
    
    Args:
        config: Configuration dictionary with the following keys:
            - data_path: Path to input data (parquet file)
            - out_dir: Output directory
            - split_method: 'time_based', 'walk_forward', 'session_aware', or 'rolling_window'
            - time_column: Name of timestamp column (default: 'timestamp')
            - split_params: Parameters specific to the chosen split method
            - run_leakage_audit: Whether to run leakage detection (default: True)
    
    Returns:
        Dictionary with results and metadata
    """
    
    # Setup
    out_dir = Path(config["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    
    _log_progress(out_dir, "start", 0, f"Splitter v{MODULE_VERSION} starting")
    
    # Load data
    data_path = Path(config["data_path"])
    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")
    
    _log_progress(out_dir, "load_data", 10, f"Loading data from {data_path}")
    
    if data_path.suffix == '.parquet':
            data = pd.read_parquet(data_path)
    time_column = config.get("time_column", "timestamp")
    if time_column in data.columns and pd.api.types.is_integer_dtype(data[time_column]):
              data[time_column] = pd.to_datetime(data[time_column], unit='ns', utc=True)


    elif data_path.suffix == '.csv':
        data = pd.read_csv(data_path)
    else:
        raise ValueError(f"Unsupported file format: {data_path.suffix}")
    
    time_column = config.get("time_column", "timestamp")
    split_method = config.get("split_method", "time_based")
    split_params = config.get("split_params", {})
    run_leakage_audit = config.get("run_leakage_audit", True)
    
    # Initialize splitter
    _log_progress(out_dir, "init_splitter", 20, f"Initializing splitter with method: {split_method}")
    splitter = DataSplitter(data, time_column)
    
    # Perform splitting
    _log_progress(out_dir, "splitting", 40, f"Performing {split_method} splitting")
    
    if split_method == "time_based":
        splits = [splitter.time_based_split(**split_params)]
    elif split_method == "walk_forward":
        splits = splitter.walk_forward_split(**split_params)
    elif split_method == "session_aware":
        splits = splitter.session_aware_split(**split_params)
    elif split_method == "rolling_window":
        splits = splitter.rolling_window_split(**split_params)
    else:
        raise ValueError(f"Unknown split method: {split_method}")
    
    if len(splits) == 0:
        raise ValueError("No splits generated. Check your parameters.")
    
    # Save split data
    _log_progress(out_dir, "save_splits", 60, f"Saving {len(splits)} splits")
    
    splits_dir = out_dir / "splits"
    splits_dir.mkdir(exist_ok=True)
    
    leakage_reports = []
    
    for i, split_info in enumerate(splits):
        split_dir = splits_dir / f"split_{i:03d}"
        split_dir.mkdir(exist_ok=True)
        
        # Extract split data
        train_data = data.iloc[split_info["train_indices"]].copy()
        
        if "val_indices" in split_info:
            val_data = data.iloc[split_info["val_indices"]].copy()
            val_data.to_parquet(split_dir / "val_data.parquet", index=False)
        
        test_data = data.iloc[split_info["test_indices"]].copy()
        
        # Save split datasets
        train_data.to_parquet(split_dir / "train_data.parquet", index=False)
        test_data.to_parquet(split_dir / "test_data.parquet", index=False)
        
        # Run leakage audit if requested
        if run_leakage_audit:
            leakage_report = detect_data_leakage(train_data, test_data, time_column)
            leakage_report["split_id"] = i
            leakage_reports.append(leakage_report)
            
            # Save leakage report
            with open(split_dir / "leakage_report.json", "w") as f:
                json.dump(leakage_report, f, indent=2, default=str)
        
        # Save split info
        with open(split_dir / "split_info.json", "w") as f:
            json.dump(split_info, f, indent=2, default=str)
    
    # Generate summary statistics
    _log_progress(out_dir, "summary", 80, "Generating summary statistics")
    
    total_leakage_issues = sum(1 for report in leakage_reports if report.get("has_leakage", False))
    
    summary_stats = {
        "total_splits": len(splits),
        "split_method": split_method,
        "split_params": split_params,
        "data_samples": len(data),
        "time_range": {
            "start": data[time_column].min().isoformat(),
            "end": data[time_column].max().isoformat(),
            "duration_days": (data[time_column].max() - data[time_column].min()).days
        },
        "leakage_audit": {
            "enabled": run_leakage_audit,
            "splits_with_issues": total_leakage_issues,
            "clean_splits": len(splits) - total_leakage_issues
        }
    }
    
    # Add split-specific statistics
    if split_method == "walk_forward":
        avg_train_samples = np.mean([s["train_samples"] for s in splits])
        avg_test_samples = np.mean([s["test_samples"] for s in splits])
        summary_stats["walk_forward_stats"] = {
            "avg_train_samples": float(avg_train_samples),
            "avg_test_samples": float(avg_test_samples),
            "total_windows": len(splits)
        }
    
    # Save summary
    summary_path = out_dir / "split_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary_stats, f, indent=2, default=str)
    
    # Save split manifest
    _log_progress(out_dir, "manifest", 90, "Creating split manifest")
    
    split_manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "module": "splitter",
        "module_version": MODULE_VERSION,
        "split_method": split_method,
        "splits": splits,
        "leakage_reports": leakage_reports if run_leakage_audit else [],
        "summary": summary_stats
    }
    
    manifest_path = out_dir / "split_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(split_manifest, f, indent=2, default=str)
    
    # Save configuration
    config_path = out_dir / "config_used.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2, default=str)
    
    _log_progress(out_dir, "done", 100, f"Splitter v{MODULE_VERSION} completed successfully")
    
    return {
        "splits_created": len(splits),
        "splits_directory": str(splits_dir),
        "manifest_path": str(manifest_path),
        "summary_path": str(summary_path),
        "summary_stats": summary_stats,
        "leakage_issues": total_leakage_issues,
        "module_version": MODULE_VERSION
    }
