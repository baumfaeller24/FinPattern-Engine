#!/usr/bin/env python3
"""
Optimization Progress Monitor für Strategy-Testing-Status
Phase 3 Implementation - Task 12

Features:
- Real-time Strategy-Optimization-Monitoring
- Comprehensive Backtesting-Progress-Tracking
- Parameter-Sweep und Grid-Search-Monitoring
- Performance-Metriken und Profit-Tracking
- Multi-Strategy-Comparison und Ranking
- Optimization-Visualization und Reports
- Resource-Usage-Monitoring während Optimization
"""

import time
import json
import threading
from typing import Dict, List, Optional, Any, Union, Callable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
import numpy as np
from collections import deque, defaultdict
import pickle
import logging
import uuid

# Plotting für Visualisierung
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False

# Pandas für Datenanalyse
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


class OptimizationPhase(Enum):
    """Optimization-Phasen"""
    INITIALIZATION = "initialization"
    PARAMETER_GENERATION = "parameter_generation"
    BACKTESTING = "backtesting"
    EVALUATION = "evaluation"
    RANKING = "ranking"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class OptimizationType(Enum):
    """Typen von Optimierungen"""
    GRID_SEARCH = "grid_search"
    RANDOM_SEARCH = "random_search"
    BAYESIAN_OPTIMIZATION = "bayesian_optimization"
    GENETIC_ALGORITHM = "genetic_algorithm"
    PARTICLE_SWARM = "particle_swarm"
    HYPERBAND = "hyperband"
    CUSTOM = "custom"


class PerformanceMetric(Enum):
    """Performance-Metriken für Strategy-Evaluation"""
    TOTAL_RETURN = "total_return"
    SHARPE_RATIO = "sharpe_ratio"
    MAX_DRAWDOWN = "max_drawdown"
    WIN_RATE = "win_rate"
    PROFIT_FACTOR = "profit_factor"
    CALMAR_RATIO = "calmar_ratio"
    SORTINO_RATIO = "sortino_ratio"
    VOLATILITY = "volatility"
    TRADES_COUNT = "trades_count"
    AVG_TRADE_DURATION = "avg_trade_duration"
    CUSTOM = "custom"


@dataclass
class ParameterSet:
    """Parameter-Set für Strategy-Optimization"""
    parameter_id: str
    parameters: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "pending"  # pending, running, completed, failed
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    results: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "parameter_id": self.parameter_id,
            "parameters": self.parameters,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "results": self.results,
            "metadata": self.metadata
        }


@dataclass
class OptimizationRun:
    """Optimization-Run"""
    run_id: str
    strategy_name: str
    optimization_type: OptimizationType
    start_time: datetime
    end_time: Optional[datetime] = None
    phase: OptimizationPhase = OptimizationPhase.INITIALIZATION
    total_parameter_sets: Optional[int] = None
    completed_parameter_sets: int = 0
    failed_parameter_sets: int = 0
    best_parameters: Optional[Dict[str, Any]] = None
    best_performance: Optional[float] = None
    optimization_goal: PerformanceMetric = PerformanceMetric.SHARPE_RATIO
    config: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "strategy_name": self.strategy_name,
            "optimization_type": self.optimization_type.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "phase": self.phase.value,
            "total_parameter_sets": self.total_parameter_sets,
            "completed_parameter_sets": self.completed_parameter_sets,
            "failed_parameter_sets": self.failed_parameter_sets,
            "best_parameters": self.best_parameters,
            "best_performance": self.best_performance,
            "optimization_goal": self.optimization_goal.value,
            "config": self.config
        }


@dataclass
class OptimizationProgress:
    """Optimization-Progress-Snapshot"""
    timestamp: datetime
    run_id: str
    progress_percent: float
    current_parameter_set: Optional[str] = None
    estimated_time_remaining: Optional[timedelta] = None
    throughput_per_hour: float = 0.0
    resource_usage: Dict[str, float] = field(default_factory=dict)
    recent_results: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "run_id": self.run_id,
            "progress_percent": self.progress_percent,
            "current_parameter_set": self.current_parameter_set,
            "estimated_time_remaining": str(self.estimated_time_remaining) if self.estimated_time_remaining else None,
            "throughput_per_hour": self.throughput_per_hour,
            "resource_usage": self.resource_usage,
            "recent_results": self.recent_results
        }


class OptimizationProgressMonitor:
    """
    Optimization Progress Monitor für Strategy-Testing-Status
    
    Features:
    - Real-time Optimization-Progress-Tracking
    - Parameter-Set-Management und Status-Monitoring
    - Performance-Metriken-Aggregation
    - Multi-Strategy-Optimization-Coordination
    - Resource-Usage-Monitoring
    - Progress-Visualization und Reporting
    - Best-Parameter-Tracking und Ranking
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Monitor-Konfiguration
        self.monitoring_enabled = self.config.get("monitoring_enabled", True)
        self.enable_visualization = self.config.get("enable_visualization", PLOTTING_AVAILABLE)
        self.enable_resource_monitoring = self.config.get("enable_resource_monitoring", True)
        self.progress_update_interval = self.config.get("progress_update_interval", 5.0)  # Sekunden
        self.auto_save_interval = self.config.get("auto_save_interval", 60.0)  # Sekunden
        
        # Storage-Konfiguration
        self.output_directory = Path(self.config.get("output_directory", "optimization_logs"))
        self.output_directory.mkdir(parents=True, exist_ok=True)
        
        self.results_directory = self.output_directory / "results"
        self.results_directory.mkdir(parents=True, exist_ok=True)
        
        self.plots_directory = self.output_directory / "plots"
        self.plots_directory.mkdir(parents=True, exist_ok=True)
        
        # Optimization-Runs
        self.active_runs: Dict[str, OptimizationRun] = {}
        self.completed_runs: List[OptimizationRun] = []
        
        # Parameter-Sets
        self.run_parameter_sets: Dict[str, List[ParameterSet]] = defaultdict(list)
        self.parameter_set_results: Dict[str, Dict[str, Any]] = {}
        
        # Progress-Tracking
        self.progress_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.performance_rankings: Dict[str, List[Tuple[str, float]]] = {}
        
        # Threading
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.auto_save_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Callbacks
        self.progress_callbacks: List[Callable] = []
        self.completion_callbacks: List[Callable] = []
        self.best_result_callbacks: List[Callable] = []
        
        # Resource-Monitoring
        self.resource_monitor = None
        if self.enable_resource_monitoring:
            try:
                import psutil
                self.resource_monitor = psutil
            except ImportError:
                self.logger.warning("psutil not available - resource monitoring disabled")
        
        # Statistiken
        self.stats = {
            "total_runs": 0,
            "completed_runs": 0,
            "failed_runs": 0,
            "total_parameter_sets": 0,
            "completed_parameter_sets": 0,
            "failed_parameter_sets": 0,
            "total_optimization_time": 0.0,
            "avg_parameter_set_time": 0.0
        }
        
        self.logger.info("OptimizationProgressMonitor initialized")
    
    def start_optimization_run(self, run_id: str, strategy_name: str,
                             optimization_type: OptimizationType,
                             optimization_goal: PerformanceMetric = PerformanceMetric.SHARPE_RATIO,
                             **kwargs) -> OptimizationRun:
        """Starte neue Optimization-Run"""
        
        try:
            # Prüfe ob Run bereits existiert
            if run_id in self.active_runs:
                self.logger.warning(f"Optimization run {run_id} already active")
                return self.active_runs[run_id]
            
            # Erstelle neue Run
            run = OptimizationRun(
                run_id=run_id,
                strategy_name=strategy_name,
                optimization_type=optimization_type,
                start_time=datetime.now(),
                optimization_goal=optimization_goal,
                config=kwargs
            )
            
            self.active_runs[run_id] = run
            self.stats["total_runs"] += 1
            
            # Monitoring starten falls noch nicht aktiv
            if not self.monitoring_active:
                self.start_monitoring()
            
            # Run-Datei erstellen
            self._save_run_metadata(run)
            
            self.logger.info(f"Started optimization run: {run_id} "
                           f"(strategy: {strategy_name}, type: {optimization_type.value})")
            
            return run
            
        except Exception as e:
            self.logger.error(f"Error starting optimization run: {e}")
            raise
    
    def add_parameter_sets(self, run_id: str, parameter_sets: List[Dict[str, Any]]):
        """Füge Parameter-Sets zu Run hinzu"""
        
        try:
            if run_id not in self.active_runs:
                self.logger.error(f"Optimization run {run_id} not found")
                return
            
            run = self.active_runs[run_id]
            
            # Konvertiere zu ParameterSet-Objekten
            for i, params in enumerate(parameter_sets):
                parameter_id = f"{run_id}_param_{i}_{int(time.time())}"
                
                param_set = ParameterSet(
                    parameter_id=parameter_id,
                    parameters=params
                )
                
                self.run_parameter_sets[run_id].append(param_set)
            
            # Update Run
            run.total_parameter_sets = len(self.run_parameter_sets[run_id])
            run.phase = OptimizationPhase.PARAMETER_GENERATION
            
            self.stats["total_parameter_sets"] += len(parameter_sets)
            
            self.logger.info(f"Added {len(parameter_sets)} parameter sets to run {run_id}")
            
        except Exception as e:
            self.logger.error(f"Error adding parameter sets: {e}")
    
    def start_parameter_set_execution(self, run_id: str, parameter_id: str):
        """Starte Ausführung eines Parameter-Sets"""
        
        try:
            if run_id not in self.active_runs:
                self.logger.error(f"Optimization run {run_id} not found")
                return
            
            # Finde Parameter-Set
            param_set = None
            for ps in self.run_parameter_sets[run_id]:
                if ps.parameter_id == parameter_id:
                    param_set = ps
                    break
            
            if not param_set:
                self.logger.error(f"Parameter set {parameter_id} not found")
                return
            
            # Update Status
            param_set.status = "running"
            param_set.start_time = datetime.now()
            
            # Update Run-Phase
            run = self.active_runs[run_id]
            if run.phase == OptimizationPhase.PARAMETER_GENERATION:
                run.phase = OptimizationPhase.BACKTESTING
            
            self.logger.debug(f"Started parameter set execution: {parameter_id}")
            
        except Exception as e:
            self.logger.error(f"Error starting parameter set execution: {e}")
    
    def complete_parameter_set_execution(self, run_id: str, parameter_id: str,
                                       results: Dict[str, float], **kwargs):
        """Beende Ausführung eines Parameter-Sets"""
        
        try:
            if run_id not in self.active_runs:
                self.logger.error(f"Optimization run {run_id} not found")
                return
            
            # Finde Parameter-Set
            param_set = None
            for ps in self.run_parameter_sets[run_id]:
                if ps.parameter_id == parameter_id:
                    param_set = ps
                    break
            
            if not param_set:
                self.logger.error(f"Parameter set {parameter_id} not found")
                return
            
            # Update Parameter-Set
            param_set.status = "completed"
            param_set.end_time = datetime.now()
            param_set.results = results
            param_set.metadata.update(kwargs)
            
            # Speichere Ergebnisse
            self.parameter_set_results[parameter_id] = {
                "parameters": param_set.parameters,
                "results": results,
                "execution_time": (param_set.end_time - param_set.start_time).total_seconds(),
                "metadata": param_set.metadata
            }
            
            # Update Run-Statistiken
            run = self.active_runs[run_id]
            run.completed_parameter_sets += 1
            
            # Prüfe ob neues Best-Result
            optimization_metric = results.get(run.optimization_goal.value)
            if optimization_metric is not None:
                self._update_best_result(run, param_set, optimization_metric)
            
            # Update globale Statistiken
            self.stats["completed_parameter_sets"] += 1
            
            # Execution-Time-Statistiken
            execution_time = (param_set.end_time - param_set.start_time).total_seconds()
            total_time = self.stats["total_optimization_time"] + execution_time
            total_completed = self.stats["completed_parameter_sets"]
            self.stats["total_optimization_time"] = total_time
            self.stats["avg_parameter_set_time"] = total_time / total_completed if total_completed > 0 else 0.0
            
            # Progress-Callbacks
            for callback in self.progress_callbacks:
                try:
                    callback(run, param_set, results)
                except Exception as e:
                    self.logger.error(f"Progress callback error: {e}")
            
            self.logger.debug(f"Completed parameter set: {parameter_id} "
                            f"(execution time: {execution_time:.2f}s)")
            
            # Prüfe ob Run komplett
            if run.completed_parameter_sets + run.failed_parameter_sets >= run.total_parameter_sets:
                self._complete_optimization_run(run_id)
            
        except Exception as e:
            self.logger.error(f"Error completing parameter set execution: {e}")
    
    def fail_parameter_set_execution(self, run_id: str, parameter_id: str, 
                                   error_message: str, **kwargs):
        """Markiere Parameter-Set-Ausführung als fehlgeschlagen"""
        
        try:
            if run_id not in self.active_runs:
                self.logger.error(f"Optimization run {run_id} not found")
                return
            
            # Finde Parameter-Set
            param_set = None
            for ps in self.run_parameter_sets[run_id]:
                if ps.parameter_id == parameter_id:
                    param_set = ps
                    break
            
            if not param_set:
                self.logger.error(f"Parameter set {parameter_id} not found")
                return
            
            # Update Parameter-Set
            param_set.status = "failed"
            param_set.end_time = datetime.now()
            param_set.metadata.update({
                "error_message": error_message,
                **kwargs
            })
            
            # Update Run-Statistiken
            run = self.active_runs[run_id]
            run.failed_parameter_sets += 1
            
            # Update globale Statistiken
            self.stats["failed_parameter_sets"] += 1
            
            self.logger.warning(f"Parameter set failed: {parameter_id} - {error_message}")
            
            # Prüfe ob Run komplett
            if run.completed_parameter_sets + run.failed_parameter_sets >= run.total_parameter_sets:
                self._complete_optimization_run(run_id)
            
        except Exception as e:
            self.logger.error(f"Error failing parameter set execution: {e}")
    
    def get_optimization_progress(self, run_id: str) -> Dict[str, Any]:
        """Erhalte Optimization-Progress für Run"""
        
        try:
            # Suche in aktiven Runs
            run = self.active_runs.get(run_id)
            if not run:
                # Suche in completed Runs
                for completed_run in self.completed_runs:
                    if completed_run.run_id == run_id:
                        run = completed_run
                        break
            
            if not run:
                return {"error": f"Run {run_id} not found"}
            
            # Progress-Berechnung
            progress_percent = 0.0
            if run.total_parameter_sets and run.total_parameter_sets > 0:
                completed = run.completed_parameter_sets + run.failed_parameter_sets
                progress_percent = (completed / run.total_parameter_sets) * 100
            
            # Aktueller Parameter-Set
            current_param_set = None
            for param_set in self.run_parameter_sets[run_id]:
                if param_set.status == "running":
                    current_param_set = param_set.parameter_id
                    break
            
            # Throughput-Berechnung
            throughput = self._calculate_throughput(run)
            
            # ETA-Berechnung
            eta = self._calculate_eta(run, throughput)
            
            # Resource-Usage
            resource_usage = self._get_current_resource_usage()
            
            # Letzte Ergebnisse
            recent_results = self._get_recent_results(run_id, limit=5)
            
            # Progress-Objekt erstellen
            progress = OptimizationProgress(
                timestamp=datetime.now(),
                run_id=run_id,
                progress_percent=progress_percent,
                current_parameter_set=current_param_set,
                estimated_time_remaining=eta,
                throughput_per_hour=throughput,
                resource_usage=resource_usage,
                recent_results=recent_results
            )
            
            # Zu History hinzufügen
            self.progress_history[run_id].append(progress)
            
            return {
                "run": run.to_dict(),
                "progress": progress.to_dict(),
                "parameter_sets": {
                    "total": run.total_parameter_sets or 0,
                    "completed": run.completed_parameter_sets,
                    "failed": run.failed_parameter_sets,
                    "running": len([ps for ps in self.run_parameter_sets[run_id] if ps.status == "running"]),
                    "pending": len([ps for ps in self.run_parameter_sets[run_id] if ps.status == "pending"])
                },
                "best_result": {
                    "parameters": run.best_parameters,
                    "performance": run.best_performance
                },
                "is_active": run_id in self.active_runs
            }
            
        except Exception as e:
            self.logger.error(f"Error getting optimization progress: {e}")
            return {"error": str(e)}
    
    def _update_best_result(self, run: OptimizationRun, param_set: ParameterSet, 
                          metric_value: float):
        """Aktualisiere Best-Result für Run"""
        
        try:
            is_better = False
            
            if run.best_performance is None:
                is_better = True
            else:
                # Bestimme ob höher oder niedriger besser ist
                maximize_metrics = [
                    PerformanceMetric.TOTAL_RETURN,
                    PerformanceMetric.SHARPE_RATIO,
                    PerformanceMetric.WIN_RATE,
                    PerformanceMetric.PROFIT_FACTOR,
                    PerformanceMetric.CALMAR_RATIO,
                    PerformanceMetric.SORTINO_RATIO
                ]
                
                if run.optimization_goal in maximize_metrics:
                    is_better = metric_value > run.best_performance
                else:
                    is_better = metric_value < run.best_performance
            
            if is_better:
                run.best_parameters = param_set.parameters.copy()
                run.best_performance = metric_value
                
                # Best-Result-Callbacks
                for callback in self.best_result_callbacks:
                    try:
                        callback(run, param_set, metric_value)
                    except Exception as e:
                        self.logger.error(f"Best result callback error: {e}")
                
                self.logger.info(f"New best result for {run.run_id}: "
                               f"{run.optimization_goal.value}={metric_value:.4f}")
            
            # Update Performance-Ranking
            self._update_performance_ranking(run.run_id, param_set.parameter_id, metric_value)
            
        except Exception as e:
            self.logger.error(f"Error updating best result: {e}")
    
    def _update_performance_ranking(self, run_id: str, parameter_id: str, performance: float):
        """Aktualisiere Performance-Ranking"""
        
        try:
            if run_id not in self.performance_rankings:
                self.performance_rankings[run_id] = []
            
            ranking = self.performance_rankings[run_id]
            
            # Füge neues Ergebnis hinzu
            ranking.append((parameter_id, performance))
            
            # Sortiere nach Performance (höchste zuerst für die meisten Metriken)
            run = self.active_runs.get(run_id)
            if run:
                minimize_metrics = [PerformanceMetric.MAX_DRAWDOWN, PerformanceMetric.VOLATILITY]
                reverse_sort = run.optimization_goal not in minimize_metrics
                ranking.sort(key=lambda x: x[1], reverse=reverse_sort)
            
            # Behalte nur Top-100
            self.performance_rankings[run_id] = ranking[:100]
            
        except Exception as e:
            self.logger.error(f"Error updating performance ranking: {e}")
    
    def _calculate_throughput(self, run: OptimizationRun) -> float:
        """Berechne Throughput (Parameter-Sets pro Stunde)"""
        
        try:
            if run.completed_parameter_sets == 0:
                return 0.0
            
            elapsed_time = datetime.now() - run.start_time
            hours = elapsed_time.total_seconds() / 3600
            
            if hours > 0:
                return run.completed_parameter_sets / hours
            
            return 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculating throughput: {e}")
            return 0.0
    
    def _calculate_eta(self, run: OptimizationRun, throughput: float) -> Optional[timedelta]:
        """Berechne ETA für Run-Completion"""
        
        try:
            if not run.total_parameter_sets or throughput <= 0:
                return None
            
            remaining_sets = run.total_parameter_sets - run.completed_parameter_sets - run.failed_parameter_sets
            
            if remaining_sets <= 0:
                return timedelta(0)
            
            remaining_hours = remaining_sets / throughput
            return timedelta(hours=remaining_hours)
            
        except Exception as e:
            self.logger.error(f"Error calculating ETA: {e}")
            return None
    
    def _get_current_resource_usage(self) -> Dict[str, float]:
        """Erhalte aktuelle Resource-Usage"""
        
        if not self.resource_monitor:
            return {}
        
        try:
            # CPU und Memory
            cpu_percent = self.resource_monitor.cpu_percent(interval=0.1)
            memory = self.resource_monitor.virtual_memory()
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_gb": memory.used / (1024**3),
                "memory_available_gb": memory.available / (1024**3)
            }
            
        except Exception as e:
            self.logger.debug(f"Error getting resource usage: {e}")
            return {}
    
    def _get_recent_results(self, run_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Erhalte letzte Ergebnisse für Run"""
        
        try:
            recent_results = []
            
            # Sortiere Parameter-Sets nach Completion-Zeit
            completed_sets = [
                ps for ps in self.run_parameter_sets[run_id] 
                if ps.status == "completed" and ps.end_time
            ]
            
            completed_sets.sort(key=lambda x: x.end_time, reverse=True)
            
            for param_set in completed_sets[:limit]:
                recent_results.append({
                    "parameter_id": param_set.parameter_id,
                    "parameters": param_set.parameters,
                    "results": param_set.results,
                    "execution_time": (param_set.end_time - param_set.start_time).total_seconds(),
                    "completed_at": param_set.end_time.isoformat()
                })
            
            return recent_results
            
        except Exception as e:
            self.logger.error(f"Error getting recent results: {e}")
            return [] 
   
    def _complete_optimization_run(self, run_id: str):
        """Beende Optimization-Run"""
        
        try:
            if run_id not in self.active_runs:
                return
            
            run = self.active_runs[run_id]
            run.end_time = datetime.now()
            run.phase = OptimizationPhase.COMPLETED
            
            # Statistiken aktualisieren
            self.stats["completed_runs"] += 1
            
            # Run zu completed verschieben
            self.completed_runs.append(run)
            del self.active_runs[run_id]
            
            # Finale Run-Datei speichern
            self._save_run_metadata(run)
            
            # Results-Export
            self._export_run_results(run_id)
            
            # Visualization generieren
            if self.enable_visualization:
                self.generate_optimization_report(run_id)
            
            # Completion-Callbacks
            for callback in self.completion_callbacks:
                try:
                    callback(run)
                except Exception as e:
                    self.logger.error(f"Completion callback error: {e}")
            
            optimization_duration = run.end_time - run.start_time
            self.logger.info(f"Completed optimization run: {run_id} "
                           f"(duration: {optimization_duration}, "
                           f"completed: {run.completed_parameter_sets}, "
                           f"failed: {run.failed_parameter_sets})")
            
        except Exception as e:
            self.logger.error(f"Error completing optimization run: {e}")
    
    def start_monitoring(self):
        """Starte Progress-Monitoring"""
        
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.stop_event.clear()
        
        # Monitoring-Thread
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            name="OptimizationMonitor",
            daemon=True
        )
        self.monitoring_thread.start()
        
        # Auto-Save-Thread
        self.auto_save_thread = threading.Thread(
            target=self._auto_save_loop,
            name="OptimizationAutoSave",
            daemon=True
        )
        self.auto_save_thread.start()
        
        self.logger.info("Optimization monitoring started")
    
    def stop_monitoring(self):
        """Stoppe Progress-Monitoring"""
        
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        self.stop_event.set()
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5.0)
        
        if self.auto_save_thread:
            self.auto_save_thread.join(timeout=5.0)
        
        self.logger.info("Optimization monitoring stopped")
    
    def _monitoring_loop(self):
        """Haupt-Monitoring-Loop"""
        
        while self.monitoring_active and not self.stop_event.is_set():
            try:
                # Update Progress für alle aktiven Runs
                for run_id in list(self.active_runs.keys()):
                    self.get_optimization_progress(run_id)
                
                # Warte bis zum nächsten Update
                self.stop_event.wait(self.progress_update_interval)
                
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                time.sleep(1.0)
    
    def _auto_save_loop(self):
        """Auto-Save-Loop"""
        
        while self.monitoring_active and not self.stop_event.is_set():
            try:
                # Speichere alle aktiven Runs
                for run in self.active_runs.values():
                    self._save_run_metadata(run)
                
                # Warte bis zum nächsten Save
                self.stop_event.wait(self.auto_save_interval)
                
            except Exception as e:
                self.logger.error(f"Auto-save loop error: {e}")
                time.sleep(5.0)
    
    def _save_run_metadata(self, run: OptimizationRun):
        """Speichere Run-Metadaten"""
        
        try:
            run_file = self.results_directory / f"run_{run.run_id}.json"
            
            # Sammle alle Daten
            run_data = {
                "run": run.to_dict(),
                "parameter_sets": [ps.to_dict() for ps in self.run_parameter_sets[run.run_id]],
                "performance_ranking": self.performance_rankings.get(run.run_id, []),
                "progress_history": [p.to_dict() for p in list(self.progress_history[run.run_id])[-100:]],  # Letzte 100
                "saved_at": datetime.now().isoformat()
            }
            
            with open(run_file, 'w') as f:
                json.dump(run_data, f, indent=2, default=str)
                
        except Exception as e:
            self.logger.error(f"Error saving run metadata: {e}")
    
    def _export_run_results(self, run_id: str):
        """Exportiere Run-Ergebnisse"""
        
        try:
            if not PANDAS_AVAILABLE:
                return
            
            # Sammle alle Parameter-Set-Ergebnisse
            results_data = []
            
            for param_set in self.run_parameter_sets[run_id]:
                if param_set.status == "completed" and param_set.results:
                    row = {
                        "parameter_id": param_set.parameter_id,
                        **param_set.parameters,  # Parameter als Spalten
                        **param_set.results,     # Ergebnisse als Spalten
                        "execution_time": (param_set.end_time - param_set.start_time).total_seconds() if param_set.end_time else None,
                        "status": param_set.status
                    }
                    results_data.append(row)
            
            if results_data:
                # DataFrame erstellen
                df = pd.DataFrame(results_data)
                
                # CSV-Export
                csv_file = self.results_directory / f"results_{run_id}.csv"
                df.to_csv(csv_file, index=False)
                
                # Excel-Export (falls verfügbar)
                try:
                    excel_file = self.results_directory / f"results_{run_id}.xlsx"
                    df.to_excel(excel_file, index=False)
                except ImportError:
                    pass  # openpyxl nicht verfügbar
                
                self.logger.info(f"Exported results for run {run_id}: {len(results_data)} parameter sets")
            
        except Exception as e:
            self.logger.error(f"Error exporting run results: {e}")
    
    def generate_optimization_report(self, run_id: str) -> Optional[Path]:
        """Generiere Optimization-Report mit Visualisierungen"""
        
        if not self.enable_visualization or not PLOTTING_AVAILABLE:
            return None
        
        try:
            # Run und Daten laden
            run = None
            for r in list(self.active_runs.values()) + self.completed_runs:
                if r.run_id == run_id:
                    run = r
                    break
            
            if not run:
                self.logger.error(f"Run {run_id} not found for report generation")
                return None
            
            parameter_sets = self.run_parameter_sets[run_id]
            completed_sets = [ps for ps in parameter_sets if ps.status == "completed" and ps.results]
            
            if not completed_sets:
                self.logger.warning(f"No completed parameter sets for run {run_id}")
                return None
            
            # Plot-Setup
            plt.style.use('seaborn-v0_8' if hasattr(plt.style, 'seaborn-v0_8') else 'default')
            fig, axes = plt.subplots(2, 3, figsize=(18, 12))
            fig.suptitle(f'Optimization Report: {run.strategy_name} ({run_id})', fontsize=16)
            
            # Daten für Plots vorbereiten
            results_data = []
            for ps in completed_sets:
                row = {
                    "parameter_id": ps.parameter_id,
                    "execution_time": (ps.end_time - ps.start_time).total_seconds(),
                    **ps.parameters,
                    **ps.results
                }
                results_data.append(row)
            
            if not PANDAS_AVAILABLE:
                self.logger.warning("Pandas not available - limited visualization")
                return None
            
            df = pd.DataFrame(results_data)
            
            # Plot 1: Performance-Distribution
            if run.optimization_goal.value in df.columns:
                metric_values = df[run.optimization_goal.value]
                axes[0, 0].hist(metric_values, bins=30, alpha=0.7, color='blue', edgecolor='black')
                axes[0, 0].axvline(metric_values.mean(), color='red', linestyle='--', 
                                 label=f'Mean: {metric_values.mean():.4f}')
                axes[0, 0].axvline(metric_values.median(), color='green', linestyle='--', 
                                 label=f'Median: {metric_values.median():.4f}')
                axes[0, 0].set_title(f'{run.optimization_goal.value} Distribution')
                axes[0, 0].set_xlabel(run.optimization_goal.value)
                axes[0, 0].set_ylabel('Frequency')
                axes[0, 0].legend()
                axes[0, 0].grid(True, alpha=0.3)
            
            # Plot 2: Performance über Zeit
            if 'execution_time' in df.columns and run.optimization_goal.value in df.columns:
                # Sortiere nach Parameter-ID (chronologisch)
                df_sorted = df.sort_values('parameter_id')
                axes[0, 1].plot(range(len(df_sorted)), df_sorted[run.optimization_goal.value], 
                              'b-', alpha=0.7, linewidth=1)
                axes[0, 1].scatter(range(len(df_sorted)), df_sorted[run.optimization_goal.value], 
                                 alpha=0.5, s=20)
                
                # Best-Result markieren
                best_idx = df_sorted[run.optimization_goal.value].idxmax()
                best_pos = df_sorted.index.get_loc(best_idx)
                axes[0, 1].scatter(best_pos, df_sorted.loc[best_idx, run.optimization_goal.value], 
                                 color='red', s=100, marker='*', label='Best Result')
                
                axes[0, 1].set_title('Performance Over Time')
                axes[0, 1].set_xlabel('Parameter Set (Chronological)')
                axes[0, 1].set_ylabel(run.optimization_goal.value)
                axes[0, 1].legend()
                axes[0, 1].grid(True, alpha=0.3)
            
            # Plot 3: Execution-Time-Distribution
            if 'execution_time' in df.columns:
                exec_times = df['execution_time']
                axes[0, 2].hist(exec_times, bins=20, alpha=0.7, color='green', edgecolor='black')
                axes[0, 2].axvline(exec_times.mean(), color='red', linestyle='--', 
                                 label=f'Mean: {exec_times.mean():.2f}s')
                axes[0, 2].set_title('Execution Time Distribution')
                axes[0, 2].set_xlabel('Execution Time (seconds)')
                axes[0, 2].set_ylabel('Frequency')
                axes[0, 2].legend()
                axes[0, 2].grid(True, alpha=0.3)
            
            # Plot 4: Parameter-Correlation (erste 2 numerische Parameter)
            numeric_params = []
            for col in df.columns:
                if col not in ['parameter_id', 'execution_time'] and pd.api.types.is_numeric_dtype(df[col]):
                    if col not in [metric.value for metric in PerformanceMetric]:
                        numeric_params.append(col)
            
            if len(numeric_params) >= 2:
                param1, param2 = numeric_params[0], numeric_params[1]
                scatter = axes[1, 0].scatter(df[param1], df[param2], 
                                           c=df[run.optimization_goal.value], 
                                           cmap='viridis', alpha=0.7)
                axes[1, 0].set_xlabel(param1)
                axes[1, 0].set_ylabel(param2)
                axes[1, 0].set_title(f'Parameter Correlation: {param1} vs {param2}')
                plt.colorbar(scatter, ax=axes[1, 0], label=run.optimization_goal.value)
            
            # Plot 5: Top-10 Results
            top_results = df.nlargest(10, run.optimization_goal.value)
            if len(top_results) > 0:
                y_pos = range(len(top_results))
                bars = axes[1, 1].barh(y_pos, top_results[run.optimization_goal.value], 
                                     color='orange', alpha=0.7)
                axes[1, 1].set_yticks(y_pos)
                axes[1, 1].set_yticklabels([f"#{i+1}" for i in range(len(top_results))])
                axes[1, 1].set_xlabel(run.optimization_goal.value)
                axes[1, 1].set_title('Top 10 Results')
                axes[1, 1].grid(True, alpha=0.3)
                
                # Werte auf Balken anzeigen
                for i, (bar, value) in enumerate(zip(bars, top_results[run.optimization_goal.value])):
                    axes[1, 1].text(bar.get_width(), bar.get_y() + bar.get_height()/2, 
                                   f'{value:.4f}', ha='left', va='center')
            
            # Plot 6: Progress über Zeit
            progress_history = list(self.progress_history[run_id])
            if progress_history:
                timestamps = [p.timestamp for p in progress_history]
                progress_values = [p.progress_percent for p in progress_history]
                
                axes[1, 2].plot(timestamps, progress_values, 'b-', linewidth=2)
                axes[1, 2].fill_between(timestamps, progress_values, alpha=0.3)
                axes[1, 2].set_title('Optimization Progress')
                axes[1, 2].set_xlabel('Time')
                axes[1, 2].set_ylabel('Progress (%)')
                axes[1, 2].grid(True, alpha=0.3)
                
                # Formatiere X-Achse
                import matplotlib.dates as mdates
                axes[1, 2].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                axes[1, 2].tick_params(axis='x', rotation=45)
            
            # Layout anpassen
            plt.tight_layout()
            
            # Report speichern
            report_file = self.plots_directory / f"optimization_report_{run_id}.png"
            plt.savefig(report_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.logger.info(f"Optimization report generated: {report_file}")
            
            return report_file
            
        except Exception as e:
            self.logger.error(f"Error generating optimization report: {e}")
            return None
    
    def compare_optimization_runs(self, run_ids: List[str]) -> Optional[Path]:
        """Vergleiche mehrere Optimization-Runs"""
        
        if not self.enable_visualization or not PLOTTING_AVAILABLE or not PANDAS_AVAILABLE:
            return None
        
        try:
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('Optimization Runs Comparison', fontsize=16)
            
            colors = ['blue', 'green', 'red', 'orange', 'purple', 'brown']
            run_data = {}
            
            # Sammle Daten für alle Runs
            for run_id in run_ids:
                run = None
                for r in list(self.active_runs.values()) + self.completed_runs:
                    if r.run_id == run_id:
                        run = r
                        break
                
                if run:
                    completed_sets = [ps for ps in self.run_parameter_sets[run_id] 
                                    if ps.status == "completed" and ps.results]
                    
                    if completed_sets:
                        results = [ps.results.get(run.optimization_goal.value, 0) for ps in completed_sets]
                        run_data[run_id] = {
                            "run": run,
                            "results": results,
                            "best_result": max(results) if results else 0,
                            "avg_result": np.mean(results) if results else 0,
                            "completed_count": len(completed_sets)
                        }
            
            if not run_data:
                self.logger.warning("No data available for comparison")
                return None
            
            # Plot 1: Best Results Comparison
            run_names = list(run_data.keys())
            best_results = [data["best_result"] for data in run_data.values()]
            
            bars = axes[0, 0].bar(range(len(run_names)), best_results, 
                                color=colors[:len(run_names)], alpha=0.7)
            axes[0, 0].set_xticks(range(len(run_names)))
            axes[0, 0].set_xticklabels([name[:8] + '...' if len(name) > 8 else name for name in run_names], 
                                     rotation=45)
            axes[0, 0].set_title('Best Results Comparison')
            axes[0, 0].set_ylabel('Best Performance')
            axes[0, 0].grid(True, alpha=0.3)
            
            # Werte auf Balken
            for bar, value in zip(bars, best_results):
                axes[0, 0].text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                              f'{value:.4f}', ha='center', va='bottom')
            
            # Plot 2: Results Distribution Comparison
            for i, (run_id, data) in enumerate(run_data.items()):
                color = colors[i % len(colors)]
                axes[0, 1].hist(data["results"], bins=20, alpha=0.5, 
                              label=run_id[:10], color=color, density=True)
            
            axes[0, 1].set_title('Results Distribution Comparison')
            axes[0, 1].set_xlabel('Performance')
            axes[0, 1].set_ylabel('Density')
            axes[0, 1].legend()
            axes[0, 1].grid(True, alpha=0.3)
            
            # Plot 3: Completion Statistics
            completion_stats = []
            for run_id, data in run_data.items():
                run = data["run"]
                total = run.total_parameter_sets or 0
                completed = run.completed_parameter_sets
                failed = run.failed_parameter_sets
                
                completion_stats.append({
                    "run_id": run_id,
                    "completed": completed,
                    "failed": failed,
                    "success_rate": (completed / total * 100) if total > 0 else 0
                })
            
            if completion_stats:
                run_names = [stat["run_id"][:8] + '...' if len(stat["run_id"]) > 8 else stat["run_id"] 
                           for stat in completion_stats]
                success_rates = [stat["success_rate"] for stat in completion_stats]
                
                bars = axes[1, 0].bar(range(len(run_names)), success_rates, 
                                    color=colors[:len(run_names)], alpha=0.7)
                axes[1, 0].set_xticks(range(len(run_names)))
                axes[1, 0].set_xticklabels(run_names, rotation=45)
                axes[1, 0].set_title('Success Rate Comparison')
                axes[1, 0].set_ylabel('Success Rate (%)')
                axes[1, 0].grid(True, alpha=0.3)
                
                # Werte auf Balken
                for bar, value in zip(bars, success_rates):
                    axes[1, 0].text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                                  f'{value:.1f}%', ha='center', va='bottom')
            
            # Plot 4: Summary Statistics Table
            axes[1, 1].axis('tight')
            axes[1, 1].axis('off')
            
            table_data = []
            for run_id, data in run_data.items():
                table_data.append([
                    run_id[:12] + '...' if len(run_id) > 12 else run_id,
                    f"{data['best_result']:.4f}",
                    f"{data['avg_result']:.4f}",
                    str(data['completed_count'])
                ])
            
            table = axes[1, 1].table(cellText=table_data,
                                   colLabels=['Run ID', 'Best', 'Avg', 'Count'],
                                   cellLoc='center',
                                   loc='center')
            table.auto_set_font_size(False)
            table.set_fontsize(10)
            axes[1, 1].set_title('Summary Statistics')
            
            plt.tight_layout()
            
            # Vergleichs-Report speichern
            comparison_file = self.plots_directory / f"runs_comparison_{int(time.time())}.png"
            plt.savefig(comparison_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.logger.info(f"Runs comparison generated: {comparison_file}")
            
            return comparison_file
            
        except Exception as e:
            self.logger.error(f"Error comparing optimization runs: {e}")
            return None
    
    def add_progress_callback(self, callback: Callable):
        """Füge Progress-Callback hinzu"""
        self.progress_callbacks.append(callback)
    
    def add_completion_callback(self, callback: Callable):
        """Füge Completion-Callback hinzu"""
        self.completion_callbacks.append(callback)
    
    def add_best_result_callback(self, callback: Callable):
        """Füge Best-Result-Callback hinzu"""
        self.best_result_callbacks.append(callback)
    
    def get_monitor_statistics(self) -> Dict[str, Any]:
        """Erhalte Monitor-Statistiken"""
        
        try:
            # Aktive Runs
            active_runs_info = {}
            for run_id, run in self.active_runs.items():
                progress = self.get_optimization_progress(run_id)
                active_runs_info[run_id] = {
                    "strategy_name": run.strategy_name,
                    "optimization_type": run.optimization_type.value,
                    "phase": run.phase.value,
                    "progress_percent": progress.get("progress", {}).get("progress_percent", 0),
                    "best_performance": run.best_performance
                }
            
            # Completed Runs (letzte 10)
            recent_completed = []
            for run in self.completed_runs[-10:]:
                duration = run.end_time - run.start_time if run.end_time else timedelta(0)
                recent_completed.append({
                    "run_id": run.run_id,
                    "strategy_name": run.strategy_name,
                    "optimization_type": run.optimization_type.value,
                    "duration": str(duration),
                    "completed_sets": run.completed_parameter_sets,
                    "best_performance": run.best_performance
                })
            
            return {
                "timestamp": datetime.now().isoformat(),
                "monitor_config": {
                    "monitoring_enabled": self.monitoring_enabled,
                    "enable_visualization": self.enable_visualization,
                    "enable_resource_monitoring": self.enable_resource_monitoring,
                    "progress_update_interval": self.progress_update_interval
                },
                "statistics": dict(self.stats),
                "active_runs": active_runs_info,
                "recent_completed_runs": recent_completed,
                "total_parameter_sets_in_progress": sum(
                    len(self.run_parameter_sets[run_id]) for run_id in self.active_runs.keys()
                ),
                "output_directory": str(self.output_directory)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting monitor statistics: {e}")
            return {"error": str(e)}
    
    def cleanup(self):
        """Cleanup Monitor-Ressourcen"""
        
        try:
            # Stoppe Monitoring
            self.stop_monitoring()
            
            # Beende alle aktiven Runs
            for run_id in list(self.active_runs.keys()):
                run = self.active_runs[run_id]
                run.end_time = datetime.now()
                run.phase = OptimizationPhase.COMPLETED
                self._save_run_metadata(run)
                
                self.completed_runs.append(run)
                del self.active_runs[run_id]
            
            self.logger.info("OptimizationProgressMonitor cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during monitor cleanup: {e}")


# Utility-Funktionen
def create_grid_search_parameters(parameter_ranges: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
    """Erstelle Parameter-Sets für Grid-Search"""
    
    import itertools
    
    parameter_names = list(parameter_ranges.keys())
    parameter_values = list(parameter_ranges.values())
    
    parameter_sets = []
    for combination in itertools.product(*parameter_values):
        param_set = dict(zip(parameter_names, combination))
        parameter_sets.append(param_set)
    
    return parameter_sets


def create_random_search_parameters(parameter_ranges: Dict[str, Tuple[Any, Any]], 
                                  num_samples: int, 
                                  random_seed: Optional[int] = None) -> List[Dict[str, Any]]:
    """Erstelle Parameter-Sets für Random-Search"""
    
    if random_seed is not None:
        np.random.seed(random_seed)
    
    parameter_sets = []
    
    for _ in range(num_samples):
        param_set = {}
        
        for param_name, (min_val, max_val) in parameter_ranges.items():
            if isinstance(min_val, int) and isinstance(max_val, int):
                # Integer-Parameter
                param_set[param_name] = np.random.randint(min_val, max_val + 1)
            elif isinstance(min_val, float) or isinstance(max_val, float):
                # Float-Parameter
                param_set[param_name] = np.random.uniform(min_val, max_val)
            else:
                # Andere Typen - zufällige Auswahl
                param_set[param_name] = np.random.choice([min_val, max_val])
        
        parameter_sets.append(param_set)
    
    return parameter_sets


def setup_optimization_monitoring(output_dir: str, 
                                enable_visualization: bool = True,
                                enable_resource_monitoring: bool = True) -> Dict[str, Any]:
    """Setup Optimization-Monitoring-Konfiguration"""
    
    return {
        "monitoring_enabled": True,
        "enable_visualization": enable_visualization and PLOTTING_AVAILABLE,
        "enable_resource_monitoring": enable_resource_monitoring,
        "output_directory": output_dir,
        "progress_update_interval": 5.0,
        "auto_save_interval": 60.0
    }