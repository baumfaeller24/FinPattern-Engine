"""
Core Implementation for Module 10: Exporter v2.1

This module exports trading strategies to Pine Script for TradingView and
auto-generates strategy classes for NautilusTrader.
"""

import pandas as pd
from pathlib import Path
import json
from typing import Dict, Any

# Pine Script v5 Template
PINE_TEMPLATE = """
// @version=5
strategy("{strategy_name}", overlay=true)

// Inputs
{inputs}

// Logic
longCondition = {long_condition}
shortCondition = {short_condition}

if (longCondition)
    strategy.entry("Long", strategy.long)

if (shortCondition)
    strategy.entry("Short", strategy.short)

// Exit Logic (optional)
if (strategy.position_size > 0)
    strategy.exit("Exit Long", from_entry="Long", profit={tp}, loss={sl})

if (strategy.position_size < 0)
    strategy.exit("Exit Short", from_entry="Short", profit={tp}, loss={sl})
"""

# NautilusTrader Strategy Template
NAUTILUS_TEMPLATE = """
from nautilus_trader.model.strategy import Strategy
from nautilus_trader.model.data import Bar
from nautilus_trader.model.order import OrderSide

class {strategy_name}(Strategy):
    def __init__(self, config):
        super().__init__(config)
        # Add your indicators here

    def on_bar(self, bar: Bar):
        # Implement your strategy logic here
        if {long_condition}:
            self.buy(bar.instrument_id, 1)
        
        if {short_condition}:
            self.sell(bar.instrument_id, 1)
"""

def to_pine_script(config: Dict[str, Any]) -> str:
    strategy_name = config.get("strategy_name", "FinPatternStrategy")
    inputs = "" # Simplified for now
    long_condition = config.get("entry_logic", "false")
    short_condition = config.get("short_condition", "false")
    tp = config.get("tp_pips", 20) * config.get("pip_size", 0.0001)
    sl = config.get("sl_pips", 10) * config.get("pip_size", 0.0001)
    
    return PINE_TEMPLATE.format(
        strategy_name=strategy_name,
        inputs=inputs,
        long_condition=long_condition,
        short_condition=short_condition,
        tp=tp,
        sl=sl
    )

def to_nautilus_trader(config: Dict[str, Any]) -> str:
    strategy_name = config.get("strategy_name", "FinPatternStrategy")
    long_condition = config.get("long_condition", "False")
    short_condition = config.get("short_condition", "False")
    
    return NAUTILUS_TEMPLATE.format(
        strategy_name=strategy_name,
        long_condition=long_condition,
        short_condition=short_condition
    )

def run(config: Dict[str, Any]) -> Dict[str, Any]:
    out_dir = Path(config.get("out_dir", "runs/exporter"))
    out_dir.mkdir(parents=True, exist_ok=True)
    
    strategy_name = config.get("strategy_name", "FinPatternStrategy")

    # Generate Pine Script
    pine_script = to_pine_script(config)
    pine_file = out_dir / f"{strategy_name}.pine"
    with open(pine_file, "w") as f:
        f.write(pine_script)
        
    # Generate NautilusTrader Strategy
    nautilus_script = to_nautilus_trader(config)
    nautilus_file = out_dir / f"{strategy_name}.py"
    with open(nautilus_file, "w") as f:
        f.write(nautilus_script)
        
    return {
        "success": True,
        "pine_script_path": str(pine_file),
        "nautilus_trader_path": str(nautilus_file)
    }

if __name__ == "__main__":
    test_config = {
        "strategy_name": "MyRSIStrategy",
        "long_condition": "ta.rsi(close, 14) < 30",
        "short_condition": "ta.rsi(close, 14) > 70",
        "tp_pips": 20,
        "sl_pips": 10,
        "pip_size": 0.0001
    }
    result = run(test_config)
    if result["success"]:
        print("✅ Exporter module test successful!")
        print(f'Pine Script saved to: {result["pine_script_path"]}')
        print(f'NautilusTrader strategy saved to: {result["nautilus_trader_path"]}')


