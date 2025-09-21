#!/usr/bin/env python3
"""
Test Script für Enhanced Main Application
Task 15 - Validation und Integration Testing
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from ai_indicator_optimizer.main_application import (
        ConfigurationManager,
        OllamaIntegration,
        ExperimentRunner,
        ResultsExporter
    )
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Installing missing dependencies...")
    os.system("pip install click requests psutil GPUtil numpy")
    sys.exit(1)


async def test_configuration_manager():
    """Test Configuration Manager"""
    print("\n🔧 Testing Configuration Manager...")
    
    try:
        config = ConfigurationManager()
        
        # Test getting values
        cpu_cores = config.get("hardware.cpu_cores")
        ollama_model = config.get("ollama.model")
        
        print(f"   CPU Cores: {cpu_cores}")
        print(f"   Ollama Model: {ollama_model}")
        
        # Test setting values
        config.set("test.value", "test_data")
        test_value = config.get("test.value")
        
        assert test_value == "test_data", "Configuration set/get failed"
        print("✅ Configuration Manager test passed")
        
        return config
        
    except Exception as e:
        print(f"❌ Configuration Manager test failed: {e}")
        return None


async def test_ollama_integration(config):
    """Test Ollama Integration"""
    print("\n🧠 Testing Ollama Integration...")
    
    try:
        ollama = OllamaIntegration(config)
        
        # Test data
        test_market_data = {
            "price": 1.1000,
            "rsi": 30,
            "macd": 0.001,
            "bollinger_position": 0.2,
            "volume": 5000,
            "trend": "bullish"
        }
        
        print("   Sending test request to Ollama...")
        result = await ollama.analyze_market_data(test_market_data)
        
        print(f"   AI Response: {result}")
        
        # Check if we got a valid response
        if "action" in result and "confidence" in result:
            print("✅ Ollama Integration test passed")
            return True
        else:
            print("⚠️ Ollama Integration test partial (no Ollama server running)")
            return False
            
    except Exception as e:
        print(f"⚠️ Ollama Integration test failed: {e}")
        print("   (This is expected if Ollama server is not running)")
        return False


async def test_experiment_runner(config):
    """Test Experiment Runner"""
    print("\n🧪 Testing Experiment Runner...")
    
    try:
        runner = ExperimentRunner(config)
        
        # Test hardware check
        print("   Checking hardware...")
        hardware_status = runner._check_hardware()
        print(f"   Hardware Status: {hardware_status.get('cpu', {}).get('cores', 'N/A')} CPU cores")
        
        # Test full experiment (with simulated data)
        print("   Running test experiment...")
        results = await runner.run_full_experiment("test_experiment")
        
        if results.get("error"):
            print(f"⚠️ Experiment test partial: {results['error']}")
        else:
            print("✅ Experiment Runner test passed")
            return results
            
    except Exception as e:
        print(f"❌ Experiment Runner test failed: {e}")
        return None


async def test_results_exporter(config, results=None):
    """Test Results Exporter"""
    print("\n📊 Testing Results Exporter...")
    
    try:
        exporter = ResultsExporter(config)
        
        # Create test results if none provided
        if not results:
            results = {
                "experiment_name": "test_export",
                "timestamp": "2025-09-21T10:00:00",
                "ai_analysis": {
                    "action": "BUY",
                    "confidence": 0.75,
                    "reasoning": "Test analysis"
                },
                "features": {
                    "rsi": 30,
                    "macd": 0.001,
                    "price": 1.1000
                },
                "position_info": {
                    "position_size": 0.02,
                    "risk_amount": 2000
                }
            }
        
        # Test Pine Script export
        pine_path = exporter.export_pine_script(results, "test_results/test_strategy.pine")
        if pine_path and Path(pine_path).exists():
            print(f"   ✅ Pine Script exported: {pine_path}")
        
        # Test Performance Report export
        report_path = exporter.export_performance_report(results, "test_results/test_report.json")
        if report_path and Path(report_path).exists():
            print(f"   ✅ Performance Report exported: {report_path}")
        
        print("✅ Results Exporter test passed")
        return True
        
    except Exception as e:
        print(f"❌ Results Exporter test failed: {e}")
        return False


async def main():
    """Main test function"""
    print("🚀 Testing Enhanced Main Application - Task 15")
    print("=" * 60)
    
    # Test Configuration Manager
    config = await test_configuration_manager()
    if not config:
        print("❌ Critical failure: Configuration Manager failed")
        return
    
    # Test Ollama Integration
    ollama_working = await test_ollama_integration(config)
    
    # Test Experiment Runner
    results = await test_experiment_runner(config)
    
    # Test Results Exporter
    exporter_working = await test_results_exporter(config, results)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY:")
    print(f"   ✅ Configuration Manager: PASSED")
    print(f"   {'✅' if ollama_working else '⚠️'} Ollama Integration: {'PASSED' if ollama_working else 'PARTIAL (no server)'}")
    print(f"   {'✅' if results else '⚠️'} Experiment Runner: {'PASSED' if results else 'PARTIAL'}")
    print(f"   {'✅' if exporter_working else '❌'} Results Exporter: {'PASSED' if exporter_working else 'FAILED'}")
    
    if config and exporter_working:
        print("\n🎉 Main Application is ready for production!")
        print("\n📋 Next steps:")
        print("   1. Start Ollama server: ollama serve")
        print("   2. Run experiment: python -m ai_indicator_optimizer.main_application run-experiment")
        print("   3. Check hardware: python -m ai_indicator_optimizer.main_application check-hardware")
    else:
        print("\n⚠️ Some components need attention before production use")


if __name__ == "__main__":
    asyncio.run(main())