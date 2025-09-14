#!/usr/bin/env python3
import sys, yaml, importlib, json
from core.orchestrator.orchestrator import run as orch_run

def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/run_module.py <module_path> <config_yaml>")
        sys.exit(1)
    module_path = sys.argv[1]
    cfg_path = sys.argv[2]
    with open(cfg_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    result = orch_run(config, module_path)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
