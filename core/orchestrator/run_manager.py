"""
Enhanced Run Manager for FinPattern-Engine
Handles run history, persistence, and metadata management
"""

import json
import yaml
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import uuid


class RunManager:
    """Manages runs, history, and metadata for reproducibility"""
    
    def __init__(self, base_dir: str = "runs"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        
        # Global run registry
        self.registry_file = self.base_dir / "run_registry.json"
        self.load_registry()
    
    def load_registry(self):
        """Load run registry from disk"""
        if self.registry_file.exists():
            with open(self.registry_file) as f:
                self.registry = json.load(f)
        else:
            self.registry = {
                "runs": [],
                "last_updated": datetime.now().isoformat()
            }
    
    def save_registry(self):
        """Save run registry to disk"""
        self.registry["last_updated"] = datetime.now().isoformat()
        with open(self.registry_file, 'w') as f:
            json.dump(self.registry, f, indent=2)
    
    def create_run(self, module_name: str, config: Dict[str, Any]) -> str:
        """Create a new run with unique ID"""
        
        # Generate run ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        config_hash = self.hash_config(config)[:8]
        run_id = f"run_{timestamp}_{config_hash}"
        
        # Create run directory
        run_dir = self.base_dir / run_id / module_name
        run_dir.mkdir(parents=True, exist_ok=True)
        
        # Save config
        config_file = run_dir / "config_used.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        
        # Create run metadata
        metadata = {
            "run_id": run_id,
            "module": module_name,
            "created_at": datetime.now().isoformat(),
            "config_hash": config_hash,
            "status": "created",
            "config_file": str(config_file),
            "run_dir": str(run_dir)
        }
        
        # Add to registry
        self.registry["runs"].append(metadata)
        self.save_registry()
        
        return run_id
    
    def update_run_status(self, run_id: str, status: str, 
                         result: Optional[Dict] = None, 
                         error: Optional[str] = None):
        """Update run status and results"""
        
        for run in self.registry["runs"]:
            if run["run_id"] == run_id:
                run["status"] = status
                run["updated_at"] = datetime.now().isoformat()
                
                if result:
                    run["result"] = result
                
                if error:
                    run["error"] = error
                
                break
        
        self.save_registry()
    
    def get_run_history(self, module_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get run history, optionally filtered by module"""
        
        runs = self.registry["runs"]
        
        if module_name:
            runs = [r for r in runs if r.get("module") == module_name]
        
        # Sort by creation time (newest first)
        return sorted(runs, key=lambda x: x.get("created_at", ""), reverse=True)
    
    def get_run_details(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific run"""
        
        for run in self.registry["runs"]:
            if run["run_id"] == run_id:
                # Load config
                config_file = Path(run["config_file"])
                if config_file.exists():
                    with open(config_file) as f:
                        run["config"] = yaml.safe_load(f)
                
                # Load manifest if available
                run_dir = Path(run["run_dir"])
                manifest_file = run_dir / "manifest.json"
                if manifest_file.exists():
                    with open(manifest_file) as f:
                        run["manifest"] = json.load(f)
                
                # Load quality report if available
                quality_file = run_dir / "quality_report.json"
                if quality_file.exists():
                    with open(quality_file) as f:
                        run["quality_report"] = json.load(f)
                
                return run
        
        return None
    
    def clone_run_config(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Clone configuration from an existing run"""
        
        run_details = self.get_run_details(run_id)
        if run_details and "config" in run_details:
            # Remove run-specific fields
            config = run_details["config"].copy()
            
            # Remove output directory (will be regenerated)
            if "out_dir" in config:
                del config["out_dir"]
            
            return config
        
        return None
    
    def find_duplicate_runs(self, config: Dict[str, Any]) -> List[str]:
        """Find runs with identical configuration"""
        
        config_hash = self.hash_config(config)
        
        duplicates = []
        for run in self.registry["runs"]:
            if run.get("config_hash") == config_hash:
                duplicates.append(run["run_id"])
        
        return duplicates
    
    def hash_config(self, config: Dict[str, Any]) -> str:
        """Create deterministic hash of configuration"""
        
        # Remove non-deterministic fields
        clean_config = config.copy()
        
        # Remove paths and timestamps
        fields_to_remove = ["out_dir", "csv.path", "timestamp"]
        for field in fields_to_remove:
            if "." in field:
                # Nested field
                parts = field.split(".")
                if parts[0] in clean_config and parts[1] in clean_config[parts[0]]:
                    del clean_config[parts[0]][parts[1]]
            else:
                if field in clean_config:
                    del clean_config[field]
        
        # Create deterministic string
        config_str = json.dumps(clean_config, sort_keys=True)
        
        # Return hash
        return hashlib.sha256(config_str.encode()).hexdigest()
    
    def cleanup_old_runs(self, days: int = 30) -> int:
        """Clean up runs older than specified days"""
        
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(days=days)
        
        runs_to_remove = []
        deleted_count = 0
        
        for i, run in enumerate(self.registry["runs"]):
            try:
                created_at = datetime.fromisoformat(run["created_at"])
                if created_at < cutoff:
                    # Delete run directory
                    run_dir = Path(run["run_dir"]).parent  # Go up to run_id level
                    if run_dir.exists():
                        import shutil
                        shutil.rmtree(run_dir)
                        deleted_count += 1
                    
                    runs_to_remove.append(i)
            except Exception:
                continue
        
        # Remove from registry (reverse order to maintain indices)
        for i in reversed(runs_to_remove):
            del self.registry["runs"][i]
        
        self.save_registry()
        return deleted_count
    
    def get_run_statistics(self) -> Dict[str, Any]:
        """Get statistics about runs"""
        
        total_runs = len(self.registry["runs"])
        
        # Count by status
        status_counts = {}
        module_counts = {}
        
        for run in self.registry["runs"]:
            status = run.get("status", "unknown")
            module = run.get("module", "unknown")
            
            status_counts[status] = status_counts.get(status, 0) + 1
            module_counts[module] = module_counts.get(module, 0) + 1
        
        # Recent activity (last 7 days)
        from datetime import timedelta
        week_ago = datetime.now() - timedelta(days=7)
        
        recent_runs = 0
        for run in self.registry["runs"]:
            try:
                created_at = datetime.fromisoformat(run["created_at"])
                if created_at > week_ago:
                    recent_runs += 1
            except Exception:
                continue
        
        return {
            "total_runs": total_runs,
            "status_counts": status_counts,
            "module_counts": module_counts,
            "recent_runs": recent_runs,
            "last_updated": self.registry["last_updated"]
        }
    
    def export_run_data(self, run_id: str, format: str = "json") -> Optional[str]:
        """Export run data in specified format"""
        
        run_details = self.get_run_details(run_id)
        if not run_details:
            return None
        
        if format == "json":
            return json.dumps(run_details, indent=2)
        elif format == "yaml":
            return yaml.dump(run_details, default_flow_style=False)
        else:
            return None
    
    def import_run_data(self, data: str, format: str = "json") -> bool:
        """Import run data from external source"""
        
        try:
            if format == "json":
                run_data = json.loads(data)
            elif format == "yaml":
                run_data = yaml.safe_load(data)
            else:
                return False
            
            # Validate required fields
            required_fields = ["run_id", "module", "created_at"]
            if not all(field in run_data for field in required_fields):
                return False
            
            # Add to registry if not exists
            existing_ids = [r["run_id"] for r in self.registry["runs"]]
            if run_data["run_id"] not in existing_ids:
                self.registry["runs"].append(run_data)
                self.save_registry()
                return True
            
            return False
            
        except Exception:
            return False


# Global instance
run_manager = RunManager()
