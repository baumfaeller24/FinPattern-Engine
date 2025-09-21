#!/bin/bash
# Automated Error Fix Rollback Script
# Generated: 2025-09-21T09:03:46.138934

echo "Restoring ai_indicator_optimizer/ai/pine_script_validator.py..."
cp "error_fix_backups/pine_script_validator.py.backup" "ai_indicator_optimizer/ai/pine_script_validator.py"

echo "Restoring ai_indicator_optimizer/ai/indicator_code_builder.py..."
cp "error_fix_backups/indicator_code_builder.py.backup" "ai_indicator_optimizer/ai/indicator_code_builder.py"

echo "Restoring ai_indicator_optimizer/testing/backtesting_framework.py..."
cp "error_fix_backups/backtesting_framework.py.backup" "ai_indicator_optimizer/testing/backtesting_framework.py"

echo "Restoring ai_indicator_optimizer/library/synthetic_pattern_generator.py..."
cp "error_fix_backups/synthetic_pattern_generator.py.backup" "ai_indicator_optimizer/library/synthetic_pattern_generator.py"

echo "Restoring strategies/ai_strategies/ai_pattern_strategy.py..."
cp "error_fix_backups/ai_pattern_strategy.py.backup" "strategies/ai_strategies/ai_pattern_strategy.py"

echo "Restoring nautilus_benchmark.py..."
cp "error_fix_backups/nautilus_benchmark.py.security_backup" "nautilus_benchmark.py"

echo "Restoring autonomous_project_analysis.py..."
cp "error_fix_backups/autonomous_project_analysis.py.security_backup" "autonomous_project_analysis.py"

echo "Rollback completed!"
