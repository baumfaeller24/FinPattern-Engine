"""
Test suite for Exporter Module - TradingView Pine Script and NautilusTrader Export
"""

import pytest
import pandas as pd
import numpy as np
import pathlib
import json
import tempfile
import shutil
from datetime import datetime, timezone

# Import the exporter module
import sys
sys.path.append("/home/ubuntu/FinPattern-Engine")
from core.exporter import exporter

class TestExporter:
    
    @pytest.fixture
    def sample_labeled_events(self):
        """Create sample labeled events for testing"""
        np.random.seed(42)
        n_events = 100
        
        base_time = pd.Timestamp("2025-01-01 09:00:00", tz="UTC")
        
        events = []
        for i in range(n_events):
            entry_time = base_time + pd.Timedelta(minutes=i * 15)
            exit_time = entry_time + pd.Timedelta(minutes=np.random.randint(5, 60))
            
            label = np.random.choice([1, -1, 0])
            hit_type = label if label != 0 else 0
            
            events.append({
                "event_index": i,
                "entry_time": entry_time,
                "exit_time": exit_time,
                "entry_price": 1.1000 + np.random.normal(0, 0.001),
                "label": label,
                "hit_type": hit_type,
                "return": np.random.normal(0, 0.001),
                "volatility_used": np.random.uniform(0.0001, 0.0005)
            })
        
        return pd.DataFrame(events)
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for testing"""
        temp_dir = tempfile.mkdtemp()
        yield pathlib.Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    def test_pine_script_generation(self, sample_labeled_events, temp_workspace):
        """Test the generation of TradingView Pine Script v5"""
        
        # Save sample data
        events_path = temp_workspace / "labeled_events.parquet"
        sample_labeled_events.to_parquet(events_path, index=False)
        
        config = {
            "labeled_events_path": str(events_path),
            "out_dir": str(temp_workspace / "output"),
            "export_formats": ["pine_script"],
            "strategy_name": "Test Pine Strategy"
        }
        
        result = exporter.run(config)
        
        # Verify basic results
        assert "output_files" in result
        assert "pine_script" in result["output_files"]
        assert result["module_version"] == "1.0"
        
        # Check output file
        pine_script_path = pathlib.Path(result["output_files"]["pine_script"])
        assert pine_script_path.exists()
        
        # Read and verify script content
        with open(pine_script_path) as f:
            script_content = f.read()
        
        assert "//@version=5" in script_content
        assert "indicator(\"Test Pine Strategy\", overlay=true)" in script_content
        assert "long_entry_times" in script_content
        assert "short_entry_times" in script_content
        assert "tp_exit_times" in script_content
        assert "sl_exit_times" in script_content
        assert "plotshape(long_signal" in script_content
        assert "plotshape(short_signal" in script_content
    
    def test_pine_script_exporter_class(self, sample_labeled_events):
        """Test the PineScriptExporter class directly"""
        
        exporter_obj = exporter.PineScriptExporter(sample_labeled_events, "Direct Test")
        
        # Generate script
        script = exporter_obj.generate_script()
        
        # Verify content
        assert "indicator(\"Direct Test\", overlay=true)" in script
        assert "array.new_int()" in script
        assert "array.push(" in script
        assert "array.includes(" in script
    
    def test_run_function_error_handling(self, temp_workspace):
        """Test error handling in the main run function"""
        
        # Test with non-existent file
        config = {
            "labeled_events_path": str(temp_workspace / "nonexistent.parquet"),
            "out_dir": str(temp_workspace / "output"),
            "export_formats": ["pine_script"]
        }
        
        with pytest.raises(FileNotFoundError):
            exporter.run(config)
    
    def test_nautilus_trader_generation(self, sample_labeled_events, temp_workspace):
        """Test the generation of NautilusTrader strategy"""
        
        # Save sample data
        events_path = temp_workspace / "labeled_events.parquet"
        sample_labeled_events.to_parquet(events_path, index=False)
        
        config = {
            "labeled_events_path": str(events_path),
            "out_dir": str(temp_workspace / "output"),
            "export_formats": ["nautilus_trader"],
            "strategy_name": "Test Nautilus Strategy"
        }
        
        result = exporter.run(config)
        
        # Verify basic results
        assert "output_files" in result
        assert "nautilus_trader" in result["output_files"]
        
        # Check output file
        nautilus_strategy_path = pathlib.Path(result["output_files"]["nautilus_trader"])
        assert nautilus_strategy_path.exists()
        
        # Read and verify strategy content
        with open(nautilus_strategy_path) as f:
            strategy_content = f.read()
        
        assert "from nautilus_trader.trading.strategy import Strategy" in strategy_content
        assert "class TestNautilusStrategy(Strategy):" in strategy_content
        assert "def on_bar(self, bar: Bar):" in strategy_content
        assert "def _check_entry_signals" in strategy_content
        assert "def _check_exit_signals" in strategy_content
        assert "OrderSide.BUY" in strategy_content
        assert "OrderSide.SELL" in strategy_content
    
    def test_nautilus_trader_exporter_class(self, sample_labeled_events):
        """Test the NautilusTraderExporter class directly"""
        
        exporter_obj = exporter.NautilusTraderExporter(sample_labeled_events, "Direct Nautilus Test")
        
        # Generate strategy
        strategy = exporter_obj.generate_strategy()
        
        # Verify content
        assert "class DirectNautilusTest(Strategy):" in strategy
        assert "def _load_entry_signals(self):" in strategy
        assert "def _load_exit_signals(self):" in strategy
        assert "def on_bar(self, bar: Bar):" in strategy
    
    def test_both_formats_export(self, sample_labeled_events, temp_workspace):
        """Test exporting both Pine Script and NautilusTrader formats"""
        
        events_path = temp_workspace / "labeled_events.parquet"
        sample_labeled_events.to_parquet(events_path, index=False)
        
        config = {
            "labeled_events_path": str(events_path),
            "out_dir": str(temp_workspace / "output"),
            "export_formats": ["pine_script", "nautilus_trader"],
            "strategy_name": "Dual Export Test"
        }
        
        result = exporter.run(config)
        
        # Verify both formats were exported
        assert "pine_script" in result["output_files"]
        assert "nautilus_trader" in result["output_files"]
        
        # Check both files exist
        pine_path = pathlib.Path(result["output_files"]["pine_script"])
        nautilus_path = pathlib.Path(result["output_files"]["nautilus_trader"])
        
        assert pine_path.exists()
        assert nautilus_path.exists()
        
        # Verify summary reflects both formats
        summary = result["summary"]
        assert set(summary["exported_formats"]) == {"pine_script", "nautilus_trader"}
    
    def test_summary_generation(self, sample_labeled_events, temp_workspace):
        """Test the generation of the export summary"""
        
        events_path = temp_workspace / "labeled_events.parquet"
        sample_labeled_events.to_parquet(events_path, index=False)
        
        config = {
            "labeled_events_path": str(events_path),
            "out_dir": str(temp_workspace / "output"),
            "export_formats": ["pine_script"],
            "strategy_name": "Summary Test"
        }
        
        result = exporter.run(config)
        
        # Verify summary
        assert "summary" in result
        summary = result["summary"]
        
        assert "exported_formats" in summary
        assert summary["exported_formats"] == ["pine_script"]
        assert "total_events_exported" in summary
        assert summary["total_events_exported"] == len(sample_labeled_events)
        assert summary["strategy_name"] == "Summary Test"
        
        # Check summary file
        summary_path = pathlib.Path(result["summary_path"])
        assert summary_path.exists()
        
        with open(summary_path) as f:
            summary_from_file = json.load(f)
        
        assert summary_from_file == summary

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
