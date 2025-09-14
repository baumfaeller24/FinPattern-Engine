"""
Enhanced Progress Monitor for FinPattern-Engine
Real-time progress tracking with ETA calculation and live updates
"""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
import threading
import queue


class ProgressMonitor:
    """Enhanced progress monitoring with ETA and live updates"""
    
    def __init__(self, run_dir: str, run_id: str):
        self.run_dir = Path(run_dir)
        self.run_id = run_id
        self.progress_file = self.run_dir / "progress.jsonl"
        self.abort_file = self.run_dir / "abort.flag"
        
        # Progress tracking
        self.start_time = datetime.now()
        self.last_update = self.start_time
        self.progress_history = []
        
        # Threading for live updates
        self.update_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.update_thread = None
        
        # Callbacks
        self.callbacks = []
        
        # Initialize progress file
        self.run_dir.mkdir(parents=True, exist_ok=True)
        if self.progress_file.exists():
            self.progress_file.unlink()
    
    def start_monitoring(self):
        """Start background monitoring thread"""
        if self.update_thread is None or not self.update_thread.is_alive():
            self.stop_event.clear()
            self.update_thread = threading.Thread(target=self._update_worker)
            self.update_thread.daemon = True
            self.update_thread.start()
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        if self.update_thread and self.update_thread.is_alive():
            self.stop_event.set()
            self.update_thread.join(timeout=1.0)
    
    def add_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add callback for progress updates"""
        self.callbacks.append(callback)
    
    def update(self, step: str, message: str, percent: float, 
               details: Optional[Dict[str, Any]] = None):
        """Update progress with step information"""
        
        now = datetime.now()
        
        progress_entry = {
            "timestamp": now.isoformat(),
            "run_id": self.run_id,
            "step": step,
            "message": message,
            "percent": min(100, max(0, percent)),
            "elapsed_seconds": (now - self.start_time).total_seconds(),
            "details": details or {}
        }
        
        # Add ETA calculation
        eta_info = self.calculate_eta(percent)
        if eta_info:
            progress_entry.update(eta_info)
        
        # Store in history
        self.progress_history.append(progress_entry)
        
        # Write to file
        self._write_progress_entry(progress_entry)
        
        # Queue for live updates
        self.update_queue.put(progress_entry)
        
        # Call callbacks
        for callback in self.callbacks:
            try:
                callback(progress_entry)
            except Exception:
                pass  # Don't let callback errors break progress
        
        self.last_update = now
    
    def calculate_eta(self, current_percent: float) -> Optional[Dict[str, Any]]:
        """Calculate ETA based on progress history"""
        
        if len(self.progress_history) < 2 or current_percent <= 0:
            return None
        
        try:
            # Use recent progress for better accuracy
            recent_entries = self.progress_history[-5:]  # Last 5 entries
            
            if len(recent_entries) < 2:
                return None
            
            # Calculate average speed
            time_span = (
                datetime.fromisoformat(recent_entries[-1]["timestamp"]) - 
                datetime.fromisoformat(recent_entries[0]["timestamp"])
            ).total_seconds()
            
            percent_span = recent_entries[-1]["percent"] - recent_entries[0]["percent"]
            
            if time_span <= 0 or percent_span <= 0:
                return None
            
            # Speed in percent per second
            speed = percent_span / time_span
            
            # Calculate ETA
            remaining_percent = 100 - current_percent
            eta_seconds = remaining_percent / speed
            
            eta_time = datetime.now() + timedelta(seconds=eta_seconds)
            
            return {
                "eta_seconds": eta_seconds,
                "eta_time": eta_time.isoformat(),
                "eta_formatted": self._format_duration(eta_seconds),
                "speed_percent_per_second": speed
            }
            
        except Exception:
            return None
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format"""
        
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"
    
    def _write_progress_entry(self, entry: Dict[str, Any]):
        """Write progress entry to JSONL file"""
        
        try:
            with open(self.progress_file, 'a') as f:
                f.write(json.dumps(entry) + '\\n')
        except Exception:
            pass  # Don't let file errors break progress
    
    def _update_worker(self):
        """Background worker for live updates"""
        
        while not self.stop_event.is_set():
            try:
                # Process queued updates
                while not self.update_queue.empty():
                    entry = self.update_queue.get_nowait()
                    # Could send to websocket, database, etc.
                    
                # Check for abort signal
                if self.abort_file.exists():
                    self.update("abort", "Abbruch angefordert", 0, {"aborted": True})
                    break
                
                time.sleep(0.1)  # 100ms update interval
                
            except Exception:
                continue
    
    def is_aborted(self) -> bool:
        """Check if run should be aborted"""
        return self.abort_file.exists()
    
    def request_abort(self):
        """Request abort of current run"""
        self.abort_file.touch()
        self.update("abort", "Abbruch angefordert", 0, {"aborted": True})
    
    def get_progress_history(self) -> List[Dict[str, Any]]:
        """Get complete progress history"""
        return self.progress_history.copy()
    
    def get_latest_progress(self) -> Optional[Dict[str, Any]]:
        """Get latest progress entry"""
        return self.progress_history[-1] if self.progress_history else None
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """Get progress summary statistics"""
        
        if not self.progress_history:
            return {"status": "no_progress"}
        
        latest = self.progress_history[-1]
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        # Calculate average speed
        if len(self.progress_history) > 1:
            total_percent = latest["percent"] - self.progress_history[0]["percent"]
            avg_speed = total_percent / elapsed if elapsed > 0 else 0
        else:
            avg_speed = 0
        
        return {
            "status": "in_progress" if latest["percent"] < 100 else "completed",
            "current_percent": latest["percent"],
            "current_step": latest["step"],
            "current_message": latest["message"],
            "elapsed_seconds": elapsed,
            "elapsed_formatted": self._format_duration(elapsed),
            "average_speed": avg_speed,
            "total_steps": len(set(entry["step"] for entry in self.progress_history)),
            "last_update": latest["timestamp"]
        }
    
    def load_from_file(self) -> bool:
        """Load progress history from existing file"""
        
        if not self.progress_file.exists():
            return False
        
        try:
            self.progress_history = []
            with open(self.progress_file) as f:
                for line in f:
                    if line.strip():
                        entry = json.loads(line)
                        self.progress_history.append(entry)
            
            # Update start time from first entry
            if self.progress_history:
                first_timestamp = datetime.fromisoformat(self.progress_history[0]["timestamp"])
                self.start_time = first_timestamp
            
            return True
            
        except Exception:
            return False
    
    def export_progress_data(self, format: str = "json") -> str:
        """Export progress data in specified format"""
        
        summary = self.get_progress_summary()
        data = {
            "run_id": self.run_id,
            "summary": summary,
            "history": self.progress_history
        }
        
        if format == "json":
            return json.dumps(data, indent=2)
        else:
            return str(data)
    
    def create_progress_chart_data(self) -> Dict[str, Any]:
        """Create data for progress visualization"""
        
        if not self.progress_history:
            return {"timestamps": [], "percentages": [], "steps": []}
        
        timestamps = []
        percentages = []
        steps = []
        
        for entry in self.progress_history:
            timestamps.append(entry["timestamp"])
            percentages.append(entry["percent"])
            steps.append(entry["step"])
        
        return {
            "timestamps": timestamps,
            "percentages": percentages,
            "steps": steps,
            "start_time": self.start_time.isoformat(),
            "duration": (datetime.now() - self.start_time).total_seconds()
        }
    
    def __enter__(self):
        """Context manager entry"""
        self.start_monitoring()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop_monitoring()
        
        # Final progress update
        if exc_type is None:
            self.update("completed", "Erfolgreich abgeschlossen", 100)
        else:
            self.update("error", f"Fehler: {exc_val}", 0, {"error": str(exc_val)})


class MultiProgressMonitor:
    """Monitor multiple concurrent runs"""
    
    def __init__(self):
        self.monitors = {}
    
    def create_monitor(self, run_id: str, run_dir: str) -> ProgressMonitor:
        """Create and register a new progress monitor"""
        monitor = ProgressMonitor(run_dir, run_id)
        self.monitors[run_id] = monitor
        return monitor
    
    def get_monitor(self, run_id: str) -> Optional[ProgressMonitor]:
        """Get existing monitor"""
        return self.monitors.get(run_id)
    
    def remove_monitor(self, run_id: str):
        """Remove monitor"""
        if run_id in self.monitors:
            self.monitors[run_id].stop_monitoring()
            del self.monitors[run_id]
    
    def get_all_progress(self) -> Dict[str, Dict[str, Any]]:
        """Get progress summary for all active runs"""
        return {
            run_id: monitor.get_progress_summary()
            for run_id, monitor in self.monitors.items()
        }
    
    def abort_all(self):
        """Abort all active runs"""
        for monitor in self.monitors.values():
            monitor.request_abort()


# Global instance
multi_progress_monitor = MultiProgressMonitor()
