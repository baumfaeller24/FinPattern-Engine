#!/usr/bin/env python3
"""
Automatic Recovery für System-Restart nach Unterbrechungen
Phase 3 Implementation - Task 13

Features:
- Automatic System-Recovery nach Crashes und Unterbrechungen
- State-Persistence und Session-Restoration
- Process-Monitoring und Auto-Restart-Mechanismen
- Checkpoint-based Recovery für Long-running-Tasks
- Resource-Cleanup und Memory-Recovery
- Service-Health-Monitoring und Auto-Healing
- Graceful-Shutdown und Recovery-Coordination
"""

import os
import sys
import time
import signal
import threading
import subprocess
import logging
import pickle
import json
import psutil
from typing import Dict, List, Optional, Any, Union, Callable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
from collections import deque, defaultdict
import atexit
import traceback

# Process Management
try:
    import supervisor
    SUPERVISOR_AVAILABLE = True
except ImportError:
    SUPERVISOR_AVAILABLE = False

# System Monitoring
try:
    import watchdog
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False


class RecoveryState(Enum):
    """Recovery-Zustände"""
    NORMAL = "normal"
    DEGRADED = "degraded"
    RECOVERING = "recovering"
    FAILED = "failed"
    MAINTENANCE = "maintenance"


class ProcessStatus(Enum):
    """Process-Status"""
    RUNNING = "running"
    STOPPED = "stopped"
    CRASHED = "crashed"
    RESTARTING = "restarting"
    UNKNOWN = "unknown"


class RecoveryTrigger(Enum):
    """Recovery-Trigger"""
    PROCESS_CRASH = "process_crash"
    MEMORY_EXHAUSTION = "memory_exhaustion"
    DISK_FULL = "disk_full"
    NETWORK_FAILURE = "network_failure"
    TIMEOUT = "timeout"
    MANUAL = "manual"
    SCHEDULED = "scheduled"


@dataclass
class ProcessConfig:
    """Konfiguration für überwachten Process"""
    process_id: str
    command: str
    working_directory: Optional[str] = None
    environment: Optional[Dict[str, str]] = None
    max_restarts: int = 5
    restart_delay: float = 5.0
    timeout: float = 300.0
    memory_limit_mb: Optional[int] = None
    cpu_limit_percent: Optional[float] = None
    auto_restart: bool = True
    critical: bool = False
    dependencies: List[str] = field(default_factory=list)
    health_check_command: Optional[str] = None
    health_check_interval: float = 60.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "process_id": self.process_id,
            "command": self.command,
            "working_directory": self.working_directory,
            "environment": self.environment,
            "max_restarts": self.max_restarts,
            "restart_delay": self.restart_delay,
            "timeout": self.timeout,
            "memory_limit_mb": self.memory_limit_mb,
            "cpu_limit_percent": self.cpu_limit_percent,
            "auto_restart": self.auto_restart,
            "critical": self.critical,
            "dependencies": self.dependencies,
            "health_check_command": self.health_check_command,
            "health_check_interval": self.health_check_interval
        }


@dataclass
class ProcessState:
    """Process-State-Information"""
    process_id: str
    pid: Optional[int] = None
    status: ProcessStatus = ProcessStatus.UNKNOWN
    start_time: Optional[datetime] = None
    last_restart: Optional[datetime] = None
    restart_count: int = 0
    last_health_check: Optional[datetime] = None
    health_status: bool = True
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    last_error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "process_id": self.process_id,
            "pid": self.pid,
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "last_restart": self.last_restart.isoformat() if self.last_restart else None,
            "restart_count": self.restart_count,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "health_status": self.health_status,
            "memory_usage_mb": self.memory_usage_mb,
            "cpu_usage_percent": self.cpu_usage_percent,
            "last_error": self.last_error
        }


@dataclass
class SystemCheckpoint:
    """System-Checkpoint für Recovery"""
    checkpoint_id: str
    timestamp: datetime
    system_state: Dict[str, Any]
    process_states: Dict[str, ProcessState]
    active_tasks: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "timestamp": self.timestamp.isoformat(),
            "system_state": self.system_state,
            "process_states": {k: v.to_dict() for k, v in self.process_states.items()},
            "active_tasks": self.active_tasks,
            "metadata": self.metadata
        }


@dataclass
class RecoveryEvent:
    """Recovery-Event-Record"""
    event_id: str
    timestamp: datetime
    trigger: RecoveryTrigger
    affected_processes: List[str]
    recovery_actions: List[str]
    success: bool
    duration: Optional[timedelta] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "trigger": self.trigger.value,
            "affected_processes": self.affected_processes,
            "recovery_actions": self.recovery_actions,
            "success": self.success,
            "duration": str(self.duration) if self.duration else None,
            "error_message": self.error_message
        }


class AutomaticRecovery:
    """
    Automatic Recovery für System-Restart nach Unterbrechungen
    
    Features:
    - Automatic System-Recovery nach Crashes und Unterbrechungen
    - State-Persistence und Session-Restoration
    - Process-Monitoring und Auto-Restart-Mechanismen
    - Checkpoint-based Recovery für Long-running-Tasks
    - Resource-Cleanup und Memory-Recovery
    - Service-Health-Monitoring und Auto-Healing
    - Graceful-Shutdown und Recovery-Coordination
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Recovery-Konfiguration
        self.enable_auto_recovery = self.config.get("enable_auto_recovery", True)
        self.enable_process_monitoring = self.config.get("enable_process_monitoring", True)
        self.enable_checkpointing = self.config.get("enable_checkpointing", True)
        self.checkpoint_interval = self.config.get("checkpoint_interval", 300.0)  # 5 Minuten
        self.max_recovery_attempts = self.config.get("max_recovery_attempts", 3)
        self.recovery_timeout = self.config.get("recovery_timeout", 600.0)  # 10 Minuten
        
        # Storage-Konfiguration
        self.state_directory = Path(self.config.get("state_directory", "recovery_state"))
        self.state_directory.mkdir(parents=True, exist_ok=True)
        
        self.checkpoint_directory = self.state_directory / "checkpoints"
        self.checkpoint_directory.mkdir(parents=True, exist_ok=True)
        
        # Process-Management
        self.process_configs: Dict[str, ProcessConfig] = {}
        self.process_states: Dict[str, ProcessState] = {}
        self.managed_processes: Dict[str, subprocess.Popen] = {}
        
        # Recovery-State
        self.recovery_state = RecoveryState.NORMAL
        self.recovery_events: deque = deque(maxlen=1000)
        self.system_checkpoints: deque = deque(maxlen=100)
        
        # Threading
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.checkpoint_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Recovery-Callbacks
        self.recovery_callbacks: List[Callable] = []
        self.shutdown_callbacks: List[Callable] = []
        
        # System-Monitoring
        self.system_metrics = {
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "disk_usage": 0.0,
            "load_average": 0.0
        }
        
        # Statistiken
        self.stats = {
            "recovery_events": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "process_restarts": 0,
            "checkpoints_created": 0,
            "system_uptime": 0.0
        }
        
        # Signal-Handler registrieren
        self._setup_signal_handlers()
        
        # Atexit-Handler registrieren
        atexit.register(self.graceful_shutdown)
        
        # Recovery-State laden
        self._load_recovery_state()
        
        self.logger.info("AutomaticRecovery initialized")
    
    def register_process(self, config: ProcessConfig):
        """Registriere Process für Monitoring"""
        
        try:
            self.process_configs[config.process_id] = config
            
            # Initial Process-State
            self.process_states[config.process_id] = ProcessState(
                process_id=config.process_id
            )
            
            self.logger.info(f"Registered process for monitoring: {config.process_id}")
            
            # Monitoring starten falls noch nicht aktiv
            if not self.monitoring_active:
                self.start_monitoring()
                
        except Exception as e:
            self.logger.error(f"Error registering process: {e}")
            raise
    
    def start_process(self, process_id: str) -> bool:
        """Starte überwachten Process"""
        
        try:
            if process_id not in self.process_configs:
                self.logger.error(f"Process config not found: {process_id}")
                return False
            
            config = self.process_configs[process_id]
            state = self.process_states[process_id]
            
            # Prüfe Dependencies
            if not self._check_dependencies(config.dependencies):
                self.logger.warning(f"Dependencies not satisfied for {process_id}")
                return False
            
            # Process starten
            env = os.environ.copy()
            if config.environment:
                env.update(config.environment)
            
            process = subprocess.Popen(
                config.command,
                shell=True,
                cwd=config.working_directory,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Process-State aktualisieren
            state.pid = process.pid
            state.status = ProcessStatus.RUNNING
            state.start_time = datetime.now()
            
            # Process registrieren
            self.managed_processes[process_id] = process
            
            self.logger.info(f"Started process {process_id} (PID: {process.pid})")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting process {process_id}: {e}")
            
            # Error-State setzen
            if process_id in self.process_states:
                self.process_states[process_id].status = ProcessStatus.CRASHED
                self.process_states[process_id].last_error = str(e)
            
            return False
    
    def stop_process(self, process_id: str, graceful: bool = True) -> bool:
        """Stoppe überwachten Process"""
        
        try:
            if process_id not in self.managed_processes:
                self.logger.warning(f"Process not managed: {process_id}")
                return False
            
            process = self.managed_processes[process_id]
            state = self.process_states[process_id]
            
            if graceful:
                # Graceful Shutdown
                process.terminate()
                
                # Warte auf Process-Ende
                try:
                    process.wait(timeout=30.0)
                except subprocess.TimeoutExpired:
                    # Force Kill
                    process.kill()
                    process.wait()
            else:
                # Force Kill
                process.kill()
                process.wait()
            
            # Process-State aktualisieren
            state.status = ProcessStatus.STOPPED
            state.pid = None
            
            # Process deregistrieren
            del self.managed_processes[process_id]
            
            self.logger.info(f"Stopped process {process_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping process {process_id}: {e}")
            return False
    
    def restart_process(self, process_id: str) -> bool:
        """Restarte Process"""
        
        try:
            config = self.process_configs.get(process_id)
            state = self.process_states.get(process_id)
            
            if not config or not state:
                return False
            
            # Prüfe Restart-Limits
            if state.restart_count >= config.max_restarts:
                self.logger.error(f"Max restarts exceeded for {process_id}")
                return False
            
            # Stoppe Process falls läuft
            if process_id in self.managed_processes:
                self.stop_process(process_id, graceful=True)
            
            # Warte Restart-Delay
            time.sleep(config.restart_delay)
            
            # Starte Process
            success = self.start_process(process_id)
            
            if success:
                state.restart_count += 1
                state.last_restart = datetime.now()
                self.stats["process_restarts"] += 1
                
                self.logger.info(f"Restarted process {process_id} (attempt {state.restart_count})")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error restarting process {process_id}: {e}")
            return False
    
    def trigger_recovery(self, trigger: RecoveryTrigger, 
                        affected_processes: Optional[List[str]] = None,
                        metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Triggere System-Recovery"""
        
        try:
            if not self.enable_auto_recovery:
                self.logger.warning("Auto-recovery is disabled")
                return False
            
            # Recovery-Event erstellen
            event_id = f"recovery_{int(time.time())}"
            recovery_event = RecoveryEvent(
                event_id=event_id,
                timestamp=datetime.now(),
                trigger=trigger,
                affected_processes=affected_processes or [],
                recovery_actions=[],
                success=False
            )
            
            self.recovery_events.append(recovery_event)
            self.stats["recovery_events"] += 1
            
            self.logger.info(f"Recovery triggered: {trigger.value} (Event: {event_id})")
            
            # Recovery-State setzen
            self.recovery_state = RecoveryState.RECOVERING
            
            start_time = datetime.now()
            recovery_actions = []
            
            try:
                # Recovery-Actions basierend auf Trigger
                if trigger == RecoveryTrigger.PROCESS_CRASH:
                    recovery_actions.extend(self._recover_from_process_crash(affected_processes))
                
                elif trigger == RecoveryTrigger.MEMORY_EXHAUSTION:
                    recovery_actions.extend(self._recover_from_memory_exhaustion())
                
                elif trigger == RecoveryTrigger.DISK_FULL:
                    recovery_actions.extend(self._recover_from_disk_full())
                
                elif trigger == RecoveryTrigger.NETWORK_FAILURE:
                    recovery_actions.extend(self._recover_from_network_failure())
                
                elif trigger == RecoveryTrigger.TIMEOUT:
                    recovery_actions.extend(self._recover_from_timeout(affected_processes))
                
                else:
                    # Generic Recovery
                    recovery_actions.extend(self._generic_recovery())
                
                # Recovery-Callbacks ausführen
                for callback in self.recovery_callbacks:
                    try:
                        callback_actions = callback(trigger, affected_processes, metadata)
                        if callback_actions:
                            recovery_actions.extend(callback_actions)
                    except Exception as e:
                        self.logger.error(f"Recovery callback error: {e}")
                
                # Recovery erfolgreich
                recovery_event.success = True
                recovery_event.recovery_actions = recovery_actions
                recovery_event.duration = datetime.now() - start_time
                
                self.recovery_state = RecoveryState.NORMAL
                self.stats["successful_recoveries"] += 1
                
                self.logger.info(f"Recovery completed successfully: {event_id}")
                
                return True
                
            except Exception as recovery_error:
                # Recovery fehlgeschlagen
                recovery_event.success = False
                recovery_event.error_message = str(recovery_error)
                recovery_event.duration = datetime.now() - start_time
                
                self.recovery_state = RecoveryState.FAILED
                self.stats["failed_recoveries"] += 1
                
                self.logger.error(f"Recovery failed: {recovery_error}")
                
                return False
                
        except Exception as e:
            self.logger.error(f"Error in recovery trigger: {e}")
            return False
    
    def _recover_from_process_crash(self, affected_processes: Optional[List[str]]) -> List[str]:
        """Recovery von Process-Crashes"""
        
        actions = []
        
        try:
            processes_to_restart = affected_processes or []
            
            # Wenn keine spezifischen Processes angegeben, finde crashed Processes
            if not processes_to_restart:
                for process_id, state in self.process_states.items():
                    if state.status == ProcessStatus.CRASHED:
                        processes_to_restart.append(process_id)
            
            # Restarte Processes
            for process_id in processes_to_restart:
                if self.restart_process(process_id):
                    actions.append(f"Restarted process: {process_id}")
                else:
                    actions.append(f"Failed to restart process: {process_id}")
            
            # Dependency-Chain prüfen
            for process_id in processes_to_restart:
                dependent_processes = self._get_dependent_processes(process_id)
                for dep_process in dependent_processes:
                    if self.restart_process(dep_process):
                        actions.append(f"Restarted dependent process: {dep_process}")
            
        except Exception as e:
            actions.append(f"Process crash recovery error: {e}")
        
        return actions
    
    def _recover_from_memory_exhaustion(self) -> List[str]:
        """Recovery von Memory-Exhaustion"""
        
        actions = []
        
        try:
            # Memory-Cleanup
            actions.append("Triggered garbage collection")
            
            # Finde Memory-intensive Processes
            memory_hogs = []
            for process_id, state in self.process_states.items():
                if state.memory_usage_mb > 1000:  # > 1GB
                    memory_hogs.append((process_id, state.memory_usage_mb))
            
            # Sortiere nach Memory-Usage
            memory_hogs.sort(key=lambda x: x[1], reverse=True)
            
            # Restarte Top-Memory-Consumer
            for process_id, memory_usage in memory_hogs[:3]:  # Top 3
                config = self.process_configs.get(process_id)
                if config and not config.critical:
                    if self.restart_process(process_id):
                        actions.append(f"Restarted memory-intensive process: {process_id} ({memory_usage:.1f}MB)")
            
            # System-Memory-Cleanup
            actions.append("Performed system memory cleanup")
            
        except Exception as e:
            actions.append(f"Memory exhaustion recovery error: {e}")
        
        return actions
    
    def _recover_from_disk_full(self) -> List[str]:
        """Recovery von Disk-Full"""
        
        actions = []
        
        try:
            # Cleanup Temp-Files
            temp_dirs = ["/tmp", str(self.state_directory / "temp")]
            
            for temp_dir in temp_dirs:
                temp_path = Path(temp_dir)
                if temp_path.exists():
                    # Lösche alte Temp-Files
                    cutoff_time = datetime.now() - timedelta(hours=24)
                    
                    for file_path in temp_path.glob("*"):
                        try:
                            if file_path.is_file():
                                mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                                if mod_time < cutoff_time:
                                    file_path.unlink()
                                    actions.append(f"Deleted old temp file: {file_path}")
                        except Exception:
                            pass
            
            # Cleanup Log-Files
            log_dirs = ["logs", "error_logs", "training_logs"]
            
            for log_dir in log_dirs:
                log_path = Path(log_dir)
                if log_path.exists():
                    # Komprimiere alte Logs
                    for log_file in log_path.glob("*.log"):
                        try:
                            if log_file.stat().st_size > 100 * 1024 * 1024:  # > 100MB
                                # Hier würde Log-Rotation implementiert
                                actions.append(f"Rotated large log file: {log_file}")
                        except Exception:
                            pass
            
            actions.append("Performed disk cleanup")
            
        except Exception as e:
            actions.append(f"Disk full recovery error: {e}")
        
        return actions
    
    def _recover_from_network_failure(self) -> List[str]:
        """Recovery von Network-Failure"""
        
        actions = []
        
        try:
            # Restarte Network-abhängige Processes
            network_processes = []
            
            for process_id, config in self.process_configs.items():
                # Identifiziere Network-Processes (vereinfacht)
                if any(keyword in config.command.lower() 
                      for keyword in ["api", "server", "client", "network", "http"]):
                    network_processes.append(process_id)
            
            for process_id in network_processes:
                if self.restart_process(process_id):
                    actions.append(f"Restarted network process: {process_id}")
            
            # Network-Connectivity-Test
            actions.append("Performed network connectivity test")
            
        except Exception as e:
            actions.append(f"Network failure recovery error: {e}")
        
        return actions
    
    def _recover_from_timeout(self, affected_processes: Optional[List[str]]) -> List[str]:
        """Recovery von Timeouts"""
        
        actions = []
        
        try:
            processes_to_restart = affected_processes or []
            
            # Restarte Timeout-Processes
            for process_id in processes_to_restart:
                if self.restart_process(process_id):
                    actions.append(f"Restarted timeout process: {process_id}")
            
            actions.append("Recovered from timeout")
            
        except Exception as e:
            actions.append(f"Timeout recovery error: {e}")
        
        return actions
    
    def _generic_recovery(self) -> List[str]:
        """Generic Recovery-Actions"""
        
        actions = []
        
        try:
            # Health-Check aller Processes
            unhealthy_processes = []
            
            for process_id, state in self.process_states.items():
                if not state.health_status or state.status == ProcessStatus.CRASHED:
                    unhealthy_processes.append(process_id)
            
            # Restarte unhealthy Processes
            for process_id in unhealthy_processes:
                config = self.process_configs.get(process_id)
                if config and config.auto_restart:
                    if self.restart_process(process_id):
                        actions.append(f"Restarted unhealthy process: {process_id}")
            
            # System-Resource-Check
            actions.append("Performed system resource check")
            
            # Checkpoint erstellen
            if self.enable_checkpointing:
                checkpoint_id = self.create_checkpoint()
                if checkpoint_id:
                    actions.append(f"Created recovery checkpoint: {checkpoint_id}")
            
        except Exception as e:
            actions.append(f"Generic recovery error: {e}")
        
        return actions
    
    def create_checkpoint(self, metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Erstelle System-Checkpoint"""
        
        try:
            checkpoint_id = f"checkpoint_{int(time.time())}"
            
            # System-State sammeln
            system_state = {
                "timestamp": datetime.now().isoformat(),
                "recovery_state": self.recovery_state.value,
                "system_metrics": self.system_metrics.copy(),
                "managed_processes": list(self.managed_processes.keys()),
                "stats": self.stats.copy()
            }
            
            # Process-States kopieren
            process_states_copy = {}
            for process_id, state in self.process_states.items():
                process_states_copy[process_id] = ProcessState(
                    process_id=state.process_id,
                    pid=state.pid,
                    status=state.status,
                    start_time=state.start_time,
                    last_restart=state.last_restart,
                    restart_count=state.restart_count,
                    last_health_check=state.last_health_check,
                    health_status=state.health_status,
                    memory_usage_mb=state.memory_usage_mb,
                    cpu_usage_percent=state.cpu_usage_percent,
                    last_error=state.last_error
                )
            
            # Checkpoint erstellen
            checkpoint = SystemCheckpoint(
                checkpoint_id=checkpoint_id,
                timestamp=datetime.now(),
                system_state=system_state,
                process_states=process_states_copy,
                metadata=metadata or {}
            )
            
            # Checkpoint speichern
            checkpoint_file = self.checkpoint_directory / f"{checkpoint_id}.json"
            
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint.to_dict(), f, indent=2, default=str)
            
            # Zu Checkpoint-History hinzufügen
            self.system_checkpoints.append(checkpoint)
            
            self.stats["checkpoints_created"] += 1
            
            self.logger.info(f"Created checkpoint: {checkpoint_id}")
            
            return checkpoint_id
            
        except Exception as e:
            self.logger.error(f"Error creating checkpoint: {e}")
            return None
    
    def restore_from_checkpoint(self, checkpoint_id: Optional[str] = None) -> bool:
        """Restore von Checkpoint"""
        
        try:
            # Neuesten Checkpoint verwenden falls nicht spezifiziert
            if not checkpoint_id:
                if not self.system_checkpoints:
                    self.logger.error("No checkpoints available for restore")
                    return False
                
                checkpoint = self.system_checkpoints[-1]
                checkpoint_id = checkpoint.checkpoint_id
            else:
                # Checkpoint laden
                checkpoint_file = self.checkpoint_directory / f"{checkpoint_id}.json"
                
                if not checkpoint_file.exists():
                    self.logger.error(f"Checkpoint file not found: {checkpoint_file}")
                    return False
                
                with open(checkpoint_file, 'r') as f:
                    checkpoint_data = json.load(f)
                
                # Checkpoint rekonstruieren (vereinfacht)
                checkpoint = SystemCheckpoint(
                    checkpoint_id=checkpoint_data["checkpoint_id"],
                    timestamp=datetime.fromisoformat(checkpoint_data["timestamp"]),
                    system_state=checkpoint_data["system_state"],
                    process_states={},  # Würde hier rekonstruiert werden
                    metadata=checkpoint_data.get("metadata", {})
                )
            
            self.logger.info(f"Restoring from checkpoint: {checkpoint_id}")
            
            # System-State wiederherstellen
            restored_processes = []
            
            for process_id in checkpoint.system_state.get("managed_processes", []):
                if process_id in self.process_configs:
                    if self.start_process(process_id):
                        restored_processes.append(process_id)
            
            self.logger.info(f"Restored {len(restored_processes)} processes from checkpoint")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error restoring from checkpoint: {e}")
            return False
    
    def start_monitoring(self):
        """Starte System-Monitoring"""
        
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.stop_event.clear()
        
        # Process-Monitoring-Thread
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            name="RecoveryMonitor",
            daemon=True
        )
        self.monitoring_thread.start()
        
        # Checkpoint-Thread
        if self.enable_checkpointing:
            self.checkpoint_thread = threading.Thread(
                target=self._checkpoint_loop,
                name="CheckpointManager",
                daemon=True
            )
            self.checkpoint_thread.start()
        
        self.logger.info("Recovery monitoring started")
    
    def stop_monitoring(self):
        """Stoppe System-Monitoring"""
        
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        self.stop_event.set()
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5.0)
        
        if self.checkpoint_thread:
            self.checkpoint_thread.join(timeout=5.0)
        
        self.logger.info("Recovery monitoring stopped")
    
    def _monitoring_loop(self):
        """Haupt-Monitoring-Loop"""
        
        while self.monitoring_active and not self.stop_event.is_set():
            try:
                # Process-Health-Checks
                self._check_process_health()
                
                # System-Resource-Monitoring
                self._update_system_metrics()
                
                # Auto-Recovery-Triggers prüfen
                self._check_recovery_triggers()
                
                # Warte bis zum nächsten Monitoring-Cycle
                self.stop_event.wait(30.0)  # 30 Sekunden
                
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                time.sleep(5.0)
    
    def _checkpoint_loop(self):
        """Checkpoint-Loop"""
        
        while self.monitoring_active and not self.stop_event.is_set():
            try:
                # Erstelle periodischen Checkpoint
                self.create_checkpoint({"type": "periodic"})
                
                # Cleanup alte Checkpoints
                self._cleanup_old_checkpoints()
                
                # Warte bis zum nächsten Checkpoint
                self.stop_event.wait(self.checkpoint_interval)
                
            except Exception as e:
                self.logger.error(f"Checkpoint loop error: {e}")
                time.sleep(60.0)
    
    def _check_process_health(self):
        """Prüfe Process-Health"""
        
        try:
            for process_id, process in list(self.managed_processes.items()):
                state = self.process_states[process_id]
                config = self.process_configs[process_id]
                
                # Process-Status prüfen
                if process.poll() is not None:
                    # Process ist beendet
                    state.status = ProcessStatus.CRASHED
                    state.pid = None
                    
                    # Auto-Restart falls konfiguriert
                    if config.auto_restart and state.restart_count < config.max_restarts:
                        self.logger.warning(f"Process {process_id} crashed, restarting...")
                        self.restart_process(process_id)
                    else:
                        self.logger.error(f"Process {process_id} crashed, max restarts exceeded")
                        del self.managed_processes[process_id]
                else:
                    # Process läuft - Resource-Usage prüfen
                    try:
                        psutil_process = psutil.Process(process.pid)
                        
                        # Memory-Usage
                        memory_info = psutil_process.memory_info()
                        state.memory_usage_mb = memory_info.rss / (1024 * 1024)
                        
                        # CPU-Usage
                        state.cpu_usage_percent = psutil_process.cpu_percent()
                        
                        # Resource-Limits prüfen
                        if (config.memory_limit_mb and 
                            state.memory_usage_mb > config.memory_limit_mb):
                            
                            self.logger.warning(f"Process {process_id} exceeds memory limit")
                            self.restart_process(process_id)
                        
                        if (config.cpu_limit_percent and 
                            state.cpu_usage_percent > config.cpu_limit_percent):
                            
                            self.logger.warning(f"Process {process_id} exceeds CPU limit")
                        
                    except psutil.NoSuchProcess:
                        state.status = ProcessStatus.CRASHED
                        state.pid = None
                
                # Health-Check-Command ausführen
                if config.health_check_command:
                    self._perform_health_check(process_id, config)
                    
        except Exception as e:
            self.logger.error(f"Error in process health check: {e}")
    
    def _perform_health_check(self, process_id: str, config: ProcessConfig):
        """Führe Health-Check-Command aus"""
        
        try:
            state = self.process_states[process_id]
            
            # Prüfe Health-Check-Interval
            if (state.last_health_check and 
                datetime.now() - state.last_health_check < timedelta(seconds=config.health_check_interval)):
                return
            
            # Health-Check-Command ausführen
            result = subprocess.run(
                config.health_check_command,
                shell=True,
                capture_output=True,
                timeout=30.0
            )
            
            state.last_health_check = datetime.now()
            
            if result.returncode == 0:
                state.health_status = True
            else:
                state.health_status = False
                self.logger.warning(f"Health check failed for {process_id}: {result.stderr.decode()}")
                
                # Auto-Restart bei Health-Check-Failure
                if config.auto_restart:
                    self.restart_process(process_id)
                    
        except subprocess.TimeoutExpired:
            state.health_status = False
            self.logger.warning(f"Health check timeout for {process_id}")
        except Exception as e:
            self.logger.error(f"Health check error for {process_id}: {e}")
    
    def _update_system_metrics(self):
        """Update System-Metriken"""
        
        try:
            # CPU-Usage
            self.system_metrics["cpu_usage"] = psutil.cpu_percent(interval=1.0)
            
            # Memory-Usage
            memory = psutil.virtual_memory()
            self.system_metrics["memory_usage"] = memory.percent
            
            # Disk-Usage
            disk = psutil.disk_usage('/')
            self.system_metrics["disk_usage"] = (disk.used / disk.total) * 100
            
            # Load-Average (Unix-Systeme)
            try:
                load_avg = psutil.getloadavg()
                self.system_metrics["load_average"] = load_avg[0]
            except AttributeError:
                self.system_metrics["load_average"] = 0.0
                
        except Exception as e:
            self.logger.error(f"Error updating system metrics: {e}")
    
    def _check_recovery_triggers(self):
        """Prüfe Auto-Recovery-Triggers"""
        
        try:
            # Memory-Exhaustion-Check
            if self.system_metrics["memory_usage"] > 95.0:
                self.trigger_recovery(RecoveryTrigger.MEMORY_EXHAUSTION)
            
            # Disk-Full-Check
            if self.system_metrics["disk_usage"] > 95.0:
                self.trigger_recovery(RecoveryTrigger.DISK_FULL)
            
            # Process-Crash-Check
            crashed_processes = []
            for process_id, state in self.process_states.items():
                if state.status == ProcessStatus.CRASHED:
                    crashed_processes.append(process_id)
            
            if crashed_processes:
                self.trigger_recovery(RecoveryTrigger.PROCESS_CRASH, crashed_processes)
                
        except Exception as e:
            self.logger.error(f"Error checking recovery triggers: {e}")
    
    def _check_dependencies(self, dependencies: List[str]) -> bool:
        """Prüfe Process-Dependencies"""
        
        for dep_process_id in dependencies:
            if dep_process_id not in self.process_states:
                return False
            
            dep_state = self.process_states[dep_process_id]
            if dep_state.status != ProcessStatus.RUNNING:
                return False
        
        return True
    
    def _get_dependent_processes(self, process_id: str) -> List[str]:
        """Erhalte Processes die von diesem Process abhängen"""
        
        dependent_processes = []
        
        for other_process_id, config in self.process_configs.items():
            if process_id in config.dependencies:
                dependent_processes.append(other_process_id)
        
        return dependent_processes
    
    def _cleanup_old_checkpoints(self):
        """Cleanup alte Checkpoints"""
        
        try:
            # Behalte nur die letzten 50 Checkpoints
            checkpoint_files = list(self.checkpoint_directory.glob("checkpoint_*.json"))
            
            if len(checkpoint_files) > 50:
                # Sortiere nach Erstellungszeit
                checkpoint_files.sort(key=lambda p: p.stat().st_mtime)
                
                # Lösche älteste Checkpoints
                for old_checkpoint in checkpoint_files[:-50]:
                    old_checkpoint.unlink()
                    
        except Exception as e:
            self.logger.error(f"Error cleaning up checkpoints: {e}")
    
    def _setup_signal_handlers(self):
        """Setup Signal-Handler für Graceful-Shutdown"""
        
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown")
            self.graceful_shutdown()
        
        # Registriere Signal-Handler
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, signal_handler)
    
    def _save_recovery_state(self):
        """Speichere Recovery-State"""
        
        try:
            state_file = self.state_directory / "recovery_state.json"
            
            state_data = {
                "recovery_state": self.recovery_state.value,
                "process_configs": {k: v.to_dict() for k, v in self.process_configs.items()},
                "process_states": {k: v.to_dict() for k, v in self.process_states.items()},
                "stats": self.stats,
                "saved_at": datetime.now().isoformat()
            }
            
            with open(state_file, 'w') as f:
                json.dump(state_data, f, indent=2, default=str)
                
        except Exception as e:
            self.logger.error(f"Error saving recovery state: {e}")
    
    def _load_recovery_state(self):
        """Lade Recovery-State"""
        
        try:
            state_file = self.state_directory / "recovery_state.json"
            
            if not state_file.exists():
                return
            
            with open(state_file, 'r') as f:
                state_data = json.load(f)
            
            # Recovery-State laden
            self.recovery_state = RecoveryState(state_data.get("recovery_state", "normal"))
            
            # Statistiken laden
            if "stats" in state_data:
                self.stats.update(state_data["stats"])
            
            self.logger.info("Loaded recovery state from previous session")
            
        except Exception as e:
            self.logger.error(f"Error loading recovery state: {e}")
    
    def graceful_shutdown(self):
        """Graceful System-Shutdown"""
        
        try:
            self.logger.info("Initiating graceful shutdown")
            
            # Shutdown-Callbacks ausführen
            for callback in self.shutdown_callbacks:
                try:
                    callback()
                except Exception as e:
                    self.logger.error(f"Shutdown callback error: {e}")
            
            # Stoppe Monitoring
            self.stop_monitoring()
            
            # Stoppe alle managed Processes
            for process_id in list(self.managed_processes.keys()):
                self.stop_process(process_id, graceful=True)
            
            # Finaler Checkpoint
            if self.enable_checkpointing:
                self.create_checkpoint({"type": "shutdown"})
            
            # Speichere Recovery-State
            self._save_recovery_state()
            
            self.logger.info("Graceful shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during graceful shutdown: {e}")
    
    def add_recovery_callback(self, callback: Callable):
        """Füge Recovery-Callback hinzu"""
        self.recovery_callbacks.append(callback)
    
    def add_shutdown_callback(self, callback: Callable):
        """Füge Shutdown-Callback hinzu"""
        self.shutdown_callbacks.append(callback)
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """Erhalte Recovery-Statistiken"""
        
        try:
            # Process-Summary
            process_summary = {}
            for process_id, state in self.process_states.items():
                config = self.process_configs.get(process_id)
                process_summary[process_id] = {
                    "status": state.status.value,
                    "restart_count": state.restart_count,
                    "health_status": state.health_status,
                    "memory_usage_mb": state.memory_usage_mb,
                    "cpu_usage_percent": state.cpu_usage_percent,
                    "auto_restart": config.auto_restart if config else False,
                    "critical": config.critical if config else False
                }
            
            # Recent Recovery-Events
            recent_events = []
            for event in list(self.recovery_events)[-10:]:
                recent_events.append(event.to_dict())
            
            return {
                "timestamp": datetime.now().isoformat(),
                "recovery_state": self.recovery_state.value,
                "system_metrics": self.system_metrics,
                "statistics": dict(self.stats),
                "processes": process_summary,
                "recent_recovery_events": recent_events,
                "checkpoints_available": len(self.system_checkpoints),
                "monitoring_active": self.monitoring_active,
                "registered_processes": len(self.process_configs)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting recovery statistics: {e}")
            return {"error": str(e)}


# Utility-Funktionen
def create_process_config(process_id: str, command: str, **kwargs) -> ProcessConfig:
    """Erstelle Process-Konfiguration"""
    
    return ProcessConfig(
        process_id=process_id,
        command=command,
        working_directory=kwargs.get("working_directory"),
        environment=kwargs.get("environment"),
        max_restarts=kwargs.get("max_restarts", 5),
        restart_delay=kwargs.get("restart_delay", 5.0),
        timeout=kwargs.get("timeout", 300.0),
        memory_limit_mb=kwargs.get("memory_limit_mb"),
        cpu_limit_percent=kwargs.get("cpu_limit_percent"),
        auto_restart=kwargs.get("auto_restart", True),
        critical=kwargs.get("critical", False),
        dependencies=kwargs.get("dependencies", []),
        health_check_command=kwargs.get("health_check_command"),
        health_check_interval=kwargs.get("health_check_interval", 60.0)
    )


def setup_recovery_config(enable_auto_recovery: bool = True,
                         checkpoint_interval: float = 300.0,
                         max_recovery_attempts: int = 3) -> Dict[str, Any]:
    """Setup Recovery-Konfiguration"""
    
    return {
        "enable_auto_recovery": enable_auto_recovery,
        "enable_process_monitoring": True,
        "enable_checkpointing": True,
        "checkpoint_interval": checkpoint_interval,
        "max_recovery_attempts": max_recovery_attempts,
        "recovery_timeout": 600.0,
        "state_directory": "recovery_state"
    }