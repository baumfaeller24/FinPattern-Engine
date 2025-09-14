"""
Sample Loader for DataIngest Module
Provides sample loading and validation functionality for GUI
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import io


class SampleLoader:
    """Load and validate data samples for preview and validation"""
    
    def __init__(self):
        self.supported_formats = ['.csv', '.gz']
        self.required_columns = ['timestamp', 'bid', 'ask']
    
    def load_sample(self, file_path: str, n_rows: int = 100) -> Dict[str, Any]:
        """Load sample data from file for preview"""
        
        try:
            path = Path(file_path)
            
            if not path.exists():
                return self._error_result("FILE_NOT_FOUND", f"Datei nicht gefunden: {file_path}")
            
            # Determine file type and load
            if path.suffix.lower() == '.csv':
                df = pd.read_csv(file_path, nrows=n_rows)
            elif path.suffix.lower() == '.gz':
                df = pd.read_csv(file_path, compression='gzip', nrows=n_rows)
            else:
                return self._error_result("UNSUPPORTED_FORMAT", f"Nicht unterstütztes Format: {path.suffix}")
            
            return self._analyze_sample(df, file_path)
            
        except Exception as e:
            return self._error_result("LOAD_ERROR", f"Fehler beim Laden: {str(e)}")
    
    def load_sample_from_upload(self, uploaded_file, n_rows: int = 100) -> Dict[str, Any]:
        """Load sample from Streamlit uploaded file"""
        
        try:
            # Read file content
            content = uploaded_file.getvalue()
            
            # Determine if compressed
            if uploaded_file.name.endswith('.gz'):
                df = pd.read_csv(io.BytesIO(content), compression='gzip', nrows=n_rows)
            else:
                df = pd.read_csv(io.BytesIO(content), nrows=n_rows)
            
            return self._analyze_sample(df, uploaded_file.name)
            
        except Exception as e:
            return self._error_result("UPLOAD_ERROR", f"Fehler beim Upload: {str(e)}")
    
    def _analyze_sample(self, df: pd.DataFrame, source: str) -> Dict[str, Any]:
        """Analyze loaded sample data"""
        
        analysis = {
            "success": True,
            "source": source,
            "n_rows": len(df),
            "columns": list(df.columns),
            "sample_data": df.head(10).to_dict('records'),
            "validation": self._validate_sample(df),
            "statistics": self._calculate_statistics(df),
            "quality_issues": []
        }
        
        # Add quality checks
        quality_issues = self._check_data_quality(df)
        analysis["quality_issues"] = quality_issues
        
        return analysis
    
    def _validate_sample(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate sample data structure and content"""
        
        validation = {
            "header_valid": True,
            "missing_columns": [],
            "extra_columns": [],
            "timestamp_format": "unknown",
            "timestamp_valid": False,
            "price_data_valid": False,
            "spread_valid": False,
            "issues": []
        }
        
        # Check required columns
        df_columns = [col.strip().lower() for col in df.columns]
        required_lower = [col.lower() for col in self.required_columns]
        
        missing = [col for col in required_lower if col not in df_columns]
        extra = [col for col in df_columns if col not in required_lower]
        
        validation["missing_columns"] = missing
        validation["extra_columns"] = extra
        
        if missing:
            validation["header_valid"] = False
            validation["issues"].append(f"Fehlende Spalten: {missing}")
        
        # Validate timestamp format (if timestamp column exists)
        timestamp_col = None
        for col in df.columns:
            if col.strip().lower() == 'timestamp':
                timestamp_col = col
                break
        
        if timestamp_col and not df.empty:
            timestamp_validation = self._validate_timestamps(df[timestamp_col])
            validation.update(timestamp_validation)
        
        # Validate price data (if bid/ask columns exist)
        bid_col = ask_col = None
        for col in df.columns:
            col_lower = col.strip().lower()
            if col_lower == 'bid':
                bid_col = col
            elif col_lower == 'ask':
                ask_col = col
        
        if bid_col and ask_col and not df.empty:
            price_validation = self._validate_prices(df[bid_col], df[ask_col])
            validation.update(price_validation)
        
        return validation
    
    def _validate_timestamps(self, timestamp_series: pd.Series) -> Dict[str, Any]:
        """Validate timestamp format and content"""
        
        validation = {
            "timestamp_format": "unknown",
            "timestamp_valid": False,
            "timezone_info": "unknown",
            "timestamp_issues": []
        }
        
        try:
            # Try to parse first few timestamps
            sample_timestamps = timestamp_series.head(5).dropna()
            
            if sample_timestamps.empty:
                validation["timestamp_issues"].append("Keine gültigen Zeitstempel gefunden")
                return validation
            
            # Check for common formats
            first_ts = str(sample_timestamps.iloc[0])
            
            # ISO 8601 format check
            if 'T' in first_ts:
                validation["timestamp_format"] = "ISO8601"
                
                if first_ts.endswith('Z'):
                    validation["timezone_info"] = "UTC (Z)"
                elif '+' in first_ts or first_ts.count('-') > 2:
                    validation["timezone_info"] = "Mit Timezone"
                else:
                    validation["timezone_info"] = "Ohne Timezone"
                
                # Try to parse
                try:
                    pd.to_datetime(sample_timestamps)
                    validation["timestamp_valid"] = True
                except Exception as e:
                    validation["timestamp_issues"].append(f"Parse-Fehler: {str(e)}")
            
            else:
                # Try other common formats
                try:
                    pd.to_datetime(sample_timestamps)
                    validation["timestamp_valid"] = True
                    validation["timestamp_format"] = "Standard"
                except Exception as e:
                    validation["timestamp_issues"].append(f"Unbekanntes Format: {str(e)}")
            
            # Check for chronological order
            if validation["timestamp_valid"]:
                try:
                    ts_parsed = pd.to_datetime(sample_timestamps)
                    if not ts_parsed.is_monotonic_increasing:
                        validation["timestamp_issues"].append("Zeitstempel nicht chronologisch sortiert")
                except Exception:
                    pass
            
        except Exception as e:
            validation["timestamp_issues"].append(f"Validierung fehlgeschlagen: {str(e)}")
        
        return validation
    
    def _validate_prices(self, bid_series: pd.Series, ask_series: pd.Series) -> Dict[str, Any]:
        """Validate bid/ask price data"""
        
        validation = {
            "price_data_valid": False,
            "spread_valid": False,
            "price_issues": []
        }
        
        try:
            # Convert to numeric
            bid_numeric = pd.to_numeric(bid_series, errors='coerce')
            ask_numeric = pd.to_numeric(ask_series, errors='coerce')
            
            # Check for NaN values
            bid_nan_count = bid_numeric.isna().sum()
            ask_nan_count = ask_numeric.isna().sum()
            
            if bid_nan_count > 0:
                validation["price_issues"].append(f"{bid_nan_count} ungültige Bid-Preise")
            
            if ask_nan_count > 0:
                validation["price_issues"].append(f"{ask_nan_count} ungültige Ask-Preise")
            
            # Check for positive prices
            if (bid_numeric <= 0).any():
                validation["price_issues"].append("Negative oder null Bid-Preise gefunden")
            
            if (ask_numeric <= 0).any():
                validation["price_issues"].append("Negative oder null Ask-Preise gefunden")
            
            # Check spread (ask > bid)
            valid_rows = ~(bid_numeric.isna() | ask_numeric.isna())
            if valid_rows.any():
                spreads = ask_numeric[valid_rows] - bid_numeric[valid_rows]
                negative_spreads = (spreads <= 0).sum()
                
                if negative_spreads > 0:
                    validation["price_issues"].append(f"{negative_spreads} negative Spreads (Ask <= Bid)")
                else:
                    validation["spread_valid"] = True
                
                # Calculate spread statistics
                if spreads.size > 0:
                    validation["spread_stats"] = {
                        "mean": float(spreads.mean()),
                        "median": float(spreads.median()),
                        "min": float(spreads.min()),
                        "max": float(spreads.max()),
                        "std": float(spreads.std())
                    }
            
            # Overall price data validity
            if not validation["price_issues"]:
                validation["price_data_valid"] = True
            
        except Exception as e:
            validation["price_issues"].append(f"Preis-Validierung fehlgeschlagen: {str(e)}")
        
        return validation
    
    def _calculate_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate basic statistics for the sample"""
        
        stats = {
            "row_count": len(df),
            "column_count": len(df.columns),
            "memory_usage": df.memory_usage(deep=True).sum(),
            "null_counts": df.isnull().sum().to_dict()
        }
        
        # Numeric column statistics
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            stats["numeric_summary"] = df[numeric_cols].describe().to_dict()
        
        return stats
    
    def _check_data_quality(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Check for data quality issues"""
        
        issues = []
        
        # Check for duplicate rows
        duplicate_count = df.duplicated().sum()
        if duplicate_count > 0:
            issues.append({
                "type": "duplicates",
                "severity": "warning",
                "message": f"{duplicate_count} doppelte Zeilen gefunden",
                "count": duplicate_count
            })
        
        # Check for missing values
        null_counts = df.isnull().sum()
        for col, count in null_counts.items():
            if count > 0:
                issues.append({
                    "type": "missing_values",
                    "severity": "warning",
                    "message": f"Spalte '{col}': {count} fehlende Werte",
                    "column": col,
                    "count": count
                })
        
        # Check for outliers in numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            outliers = self._detect_outliers(df[col])
            if outliers > 0:
                issues.append({
                    "type": "outliers",
                    "severity": "info",
                    "message": f"Spalte '{col}': {outliers} mögliche Ausreißer",
                    "column": col,
                    "count": outliers
                })
        
        return issues
    
    def _detect_outliers(self, series: pd.Series, z_threshold: float = 3.0) -> int:
        """Detect outliers using Z-score method"""
        
        try:
            numeric_series = pd.to_numeric(series, errors='coerce').dropna()
            if len(numeric_series) < 3:
                return 0
            
            z_scores = np.abs((numeric_series - numeric_series.mean()) / numeric_series.std())
            return (z_scores > z_threshold).sum()
            
        except Exception:
            return 0
    
    def _error_result(self, error_code: str, message: str) -> Dict[str, Any]:
        """Create error result"""
        
        return {
            "success": False,
            "error_code": error_code,
            "error_message": message,
            "validation": {"header_valid": False, "issues": [message]}
        }
    
    def create_sample_report(self, analysis: Dict[str, Any]) -> str:
        """Create human-readable sample report"""
        
        if not analysis["success"]:
            return f"❌ Fehler: {analysis['error_message']}"
        
        report = []
        report.append(f"📊 **Sample-Analyse: {analysis['source']}**\\n")
        
        # Basic info
        report.append(f"**Zeilen:** {analysis['n_rows']:,}")
        report.append(f"**Spalten:** {len(analysis['columns'])}")
        report.append(f"**Spalten-Namen:** {', '.join(analysis['columns'])}\\n")
        
        # Validation results
        validation = analysis["validation"]
        if validation["header_valid"]:
            report.append("✅ **Header:** Alle erforderlichen Spalten vorhanden")
        else:
            report.append("❌ **Header:** Probleme gefunden")
            if validation["missing_columns"]:
                report.append(f"   - Fehlende Spalten: {validation['missing_columns']}")
        
        if validation["timestamp_valid"]:
            report.append(f"✅ **Zeitstempel:** {validation['timestamp_format']} Format erkannt")
            report.append(f"   - Timezone: {validation['timezone_info']}")
        else:
            report.append("❌ **Zeitstempel:** Probleme gefunden")
            for issue in validation.get("timestamp_issues", []):
                report.append(f"   - {issue}")
        
        if validation["price_data_valid"]:
            report.append("✅ **Preisdaten:** Gültig")
            if validation["spread_valid"]:
                report.append("✅ **Spreads:** Alle positiv")
                if "spread_stats" in validation:
                    stats = validation["spread_stats"]
                    report.append(f"   - Durchschnitt: {stats['mean']:.5f}")
                    report.append(f"   - Bereich: {stats['min']:.5f} - {stats['max']:.5f}")
        else:
            report.append("❌ **Preisdaten:** Probleme gefunden")
            for issue in validation.get("price_issues", []):
                report.append(f"   - {issue}")
        
        # Quality issues
        if analysis["quality_issues"]:
            report.append("\\n⚠️ **Qualitätsprobleme:**")
            for issue in analysis["quality_issues"]:
                severity_icon = {"warning": "⚠️", "error": "❌", "info": "ℹ️"}.get(issue["severity"], "•")
                report.append(f"{severity_icon} {issue['message']}")
        
        return "\\n".join(report)
    
    def get_sample_preview_data(self, analysis: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """Get sample data as DataFrame for display"""
        
        if not analysis["success"] or "sample_data" not in analysis:
            return None
        
        try:
            return pd.DataFrame(analysis["sample_data"])
        except Exception:
            return None


# Global instance
sample_loader = SampleLoader()
