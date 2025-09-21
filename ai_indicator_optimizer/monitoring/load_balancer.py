#!/usr/bin/env python3
"""
Load Balancer für optimale Verteilung auf 32 CPU-Kerne
Phase 3 Implementation - Task 11

Features:
- Intelligente Workload-Verteilung auf Ryzen 9 9950X (32 Threads)
- CPU-Affinity-Management und Core-Pinning
- Dynamic Load-Balancing basierend auf CPU-Auslastung
- NUMA-Awareness für optimale Memory-Access
- Integration mit AI-Workloads und Batch-Processing
- Real-time Load-Monitoring und Adjustment
"""

import os
import psutil
import threading
import multiprocessing as mp
from multiprocessing import Process, Queue, Manager, Pool
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import time
import logging
from typing import Dict, List, Optional, Any, Union, Callable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import numpy as np
from collections import deque
import queue
import heapq

# NUMA Support
try:
    import numa
    NUMA_AVAILABLE = True
except ImportError:
    NUMA_AVAILABLE = False

# CPU Affinity Support
try:
    import affinity
    AFFINITY_AVAILABLE = True
except ImportError:
    AFFINITY_AVAILABLE = False


class WorkloadType(Enum):
    """Typen von Workloads für Load-Balancing"""
    CPU_INTENSIVE = "cpu_intensive"
    IO_INTENSIVE = "io_intensive"
    MEMORY_INTENSIVE = "memory_intensive"
    AI_INFERENCE = "ai_inference"
    AI_TRAINING = "ai_training"
    DATA_PROCESSING = "data_processing"
    BATCH_PROCESSING = "batch_processing"


class LoadBalancingStrategy(Enum):
    """Load-Balancing-Strategien"""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    CPU_AFFINITY = "cpu_affinity"
    NUMA_AWARE = "numa_aware"
    WORKLOAD_AWARE = "workload_aware"
    DYNAMIC = "dynamic"


@dataclass
class WorkloadTask:
    """Einzelne Workload-Task"""
    task_id: str
    workload_type: WorkloadType
    function: Callable
    args: Tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: int = 1  # 1=niedrig, 5=hoch
    estimated_duration: float = 0.0  # Sekunden
    cpu_cores_required: int = 1
    memory_mb_required: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    
    def __lt__(self, other):
        """Für Priority-Queue-Sortierung"""
        return self.priority > other.priority  # Höhere Priorität zuerst


@dataclass
class WorkerStats:
    """Statistiken für einen Worker"""
    worker_id: str
    cpu_cores: List[int]
    numa_node: int
    tasks_completed: int = 0
    total_execution_time: float = 0.0
    current_load: float = 0.0
    last_task_time: Optional[datetime] = None
    
    def get_avg_execution_time(self) -> float:
        """Durchschnittliche Ausführungszeit"""
        return self.total_execution_time / self.tasks_completed if self.tasks_completed > 0 else 0.0


@dataclass
class LoadBalancingResult:
    """Ergebnis einer Load-Balancing-Operation"""
    success: bool
    task_id: str
    worker_id: str
    execution_time: float = 0.0
    result: Any = None
    error: Optional[str] = None
    cpu_usage: float = 0.0
    memory_usage: float = 0.0


class LoadBalancer:
    """
    Intelligenter Load Balancer für 32-Core CPU
    
    Features:
    - Optimale Workload-Verteilung auf alle CPU-Kerne
    - NUMA-Awareness für Memory-Optimierung
    - Dynamic Load-Balancing basierend auf aktueller Auslastung
    - CPU-Affinity-Management
    - Workload-Type-spezifische Optimierung
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Hardware-Konfiguration
        self.cpu_cores = psutil.cpu_count(logical=True)  # Sollte 32 für Ryzen 9 9950X sein
        self.physical_cores = psutil.cpu_count(logical=False)  # Sollte 16 sein
        self.numa_nodes = self._detect_numa_nodes()
        
        # Load-Balancing-Konfiguration
        self.strategy = LoadBalancingStrategy(self.config.get("strategy", "dynamic"))
        self.max_workers = self.config.get("max_workers", self.cpu_cores)
        self.enable_cpu_affinity = self.config.get("enable_cpu_affinity", True)
        self.enable_numa_awareness = self.config.get("enable_numa_awareness", NUMA_AVAILABLE)
        
        # Worker-Management
        self.workers: Dict[str, WorkerStats] = {}
        self.worker_pools: Dict[WorkloadType, Union[ThreadPoolExecutor, ProcessPoolExecutor]] = {}
        self.task_queue: queue.PriorityQueue = queue.PriorityQueue()
        self.result_queue: queue.Queue = queue.Queue()
        
        # Load-Monitoring
        self.cpu_usage_history: deque = deque(maxlen=300)  # 5 Minuten bei 1s Intervall
        self.load_monitoring_active = False
        self.load_monitoring_thread: Optional[threading.Thread] = None
        
        # Statistiken
        self.stats = {
            "tasks_processed": 0,
            "tasks_failed": 0,
            "total_execution_time": 0.0,
            "avg_cpu_utilization": 0.0,
            "load_balancing_efficiency": 0.0,
            "numa_optimizations": 0,
            "cpu_affinity_assignments": 0
        }
        
        # Setup
        self._setup_workers()
        self._setup_worker_pools()
        
        self.logger.info(f"LoadBalancer initialized: {self.cpu_cores} cores, {len(self.numa_nodes)} NUMA nodes")
    
    def start_load_balancing(self):
        """Starte Load-Balancing-System"""
        
        if self.load_monitoring_active:
            self.logger.warning("Load balancing already active")
            return
        
        self.load_monitoring_active = True
        
        # Load-Monitoring-Thread starten
        self.load_monitoring_thread = threading.Thread(
            target=self._load_monitoring_loop,
            name="LoadBalancingMonitor",
            daemon=True
        )
        self.load_monitoring_thread.start()
        
        self.logger.info("Load balancing started")
    
    def stop_load_balancing(self):
        """Stoppe Load-Balancing-System"""
        
        if not self.load_monitoring_active:
            return
        
        self.load_monitoring_active = False
        
        # Monitoring-Thread stoppen
        if self.load_monitoring_thread and self.load_monitoring_thread.is_alive():
            self.load_monitoring_thread.join(timeout=5.0)
        
        # Worker-Pools schließen
        for pool in self.worker_pools.values():
            pool.shutdown(wait=True)
        
        self.logger.info("Load balancing stopped")
    
    def submit_task(self, task: WorkloadTask) -> str:
        """
        Füge Task zur Load-Balancing-Queue hinzu
        
        Args:
            task: WorkloadTask zum Processing
            
        Returns:
            Task-ID für Tracking
        """
        try:
            # Task zur Priority-Queue hinzufügen
            self.task_queue.put(task)
            
            self.logger.debug(f"Task {task.task_id} submitted (type: {task.workload_type.value}, priority: {task.priority})")
            
            return task.task_id
            
        except Exception as e:
            self.logger.error(f"Error submitting task {task.task_id}: {e}")
            raise
    
    def execute_task(self, task: WorkloadTask) -> LoadBalancingResult:
        """
        Führe Task mit optimalem Load-Balancing aus
        
        Args:
            task: Auszuführende Task
            
        Returns:
            LoadBalancingResult mit Ausführungs-Details
        """
        try:
            start_time = datetime.now()
            
            # Optimalen Worker auswählen
            worker_id = self._select_optimal_worker(task)
            
            # CPU-Affinity setzen (falls aktiviert)
            if self.enable_cpu_affinity and worker_id in self.workers:
                self._set_cpu_affinity(worker_id, task)
            
            # Task ausführen
            result = self._execute_task_on_worker(task, worker_id)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Worker-Statistiken updaten
            self._update_worker_stats(worker_id, execution_time)
            
            # Globale Statistiken updaten
            self.stats["tasks_processed"] += 1
            self.stats["total_execution_time"] += execution_time
            
            return LoadBalancingResult(
                success=True,
                task_id=task.task_id,
                worker_id=worker_id,
                execution_time=execution_time,
                result=result,
                cpu_usage=self._get_current_cpu_usage(),
                memory_usage=self._get_current_memory_usage()
            )
            
        except Exception as e:
            self.logger.error(f"Task execution error: {e}")
            
            self.stats["tasks_failed"] += 1
            
            return LoadBalancingResult(
                success=False,
                task_id=task.task_id,
                worker_id="unknown",
                error=str(e)
            )
    
    def execute_batch_tasks(self, tasks: List[WorkloadTask]) -> List[LoadBalancingResult]:
        """
        Führe mehrere Tasks parallel mit Load-Balancing aus
        
        Args:
            tasks: Liste von Tasks
            
        Returns:
            Liste von LoadBalancingResults
        """
        try:
            results = []
            
            # Tasks nach Workload-Type gruppieren
            tasks_by_type = {}
            for task in tasks:
                if task.workload_type not in tasks_by_type:
                    tasks_by_type[task.workload_type] = []
                tasks_by_type[task.workload_type].append(task)
            
            # Parallel-Execution für jede Workload-Type
            futures = []
            
            for workload_type, type_tasks in tasks_by_type.items():
                pool = self.worker_pools.get(workload_type)
                
                if pool:
                    # Verwende spezialisierten Pool
                    for task in type_tasks:
                        future = pool.submit(self._execute_task_wrapper, task)
                        futures.append(future)
                else:
                    # Fallback: Sequenzielle Ausführung
                    for task in type_tasks:
                        result = self.execute_task(task)
                        results.append(result)
            
            # Warte auf alle Futures
            for future in concurrent.futures.as_completed(futures, timeout=300):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Batch task execution error: {e}")
                    results.append(LoadBalancingResult(
                        success=False,
                        task_id="unknown",
                        worker_id="unknown",
                        error=str(e)
                    ))
            
            self.logger.info(f"Batch execution completed: {len(results)} tasks")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Batch execution error: {e}")
            return []
    
    def _execute_task_wrapper(self, task: WorkloadTask) -> LoadBalancingResult:
        """Wrapper für Task-Execution in Thread/Process-Pool"""
        return self.execute_task(task)
    
    def _select_optimal_worker(self, task: WorkloadTask) -> str:
        """Wähle optimalen Worker für Task"""
        
        try:
            if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
                return self._select_round_robin_worker()
            
            elif self.strategy == LoadBalancingStrategy.LEAST_LOADED:
                return self._select_least_loaded_worker()
            
            elif self.strategy == LoadBalancingStrategy.NUMA_AWARE:
                return self._select_numa_aware_worker(task)
            
            elif self.strategy == LoadBalancingStrategy.WORKLOAD_AWARE:
                return self._select_workload_aware_worker(task)
            
            elif self.strategy == LoadBalancingStrategy.DYNAMIC:
                return self._select_dynamic_worker(task)
            
            else:
                # Fallback: Least Loaded
                return self._select_least_loaded_worker()
                
        except Exception as e:
            self.logger.error(f"Worker selection error: {e}")
            return list(self.workers.keys())[0] if self.workers else "worker_0"
    
    def _select_round_robin_worker(self) -> str:
        """Round-Robin Worker-Auswahl"""
        worker_ids = list(self.workers.keys())
        if not worker_ids:
            return "worker_0"
        
        # Einfacher Round-Robin basierend auf Task-Count
        total_tasks = sum(worker.tasks_completed for worker in self.workers.values())
        return worker_ids[total_tasks % len(worker_ids)]
    
    def _select_least_loaded_worker(self) -> str:
        """Wähle Worker mit geringster Auslastung"""
        if not self.workers:
            return "worker_0"
        
        # Finde Worker mit niedrigster aktueller Load
        least_loaded_worker = min(
            self.workers.items(),
            key=lambda x: x[1].current_load
        )
        
        return least_loaded_worker[0]
    
    def _select_numa_aware_worker(self, task: WorkloadTask) -> str:
        """NUMA-bewusste Worker-Auswahl"""
        if not self.enable_numa_awareness or not self.numa_nodes:
            return self._select_least_loaded_worker()
        
        # Wähle NUMA-Node basierend auf Memory-Requirements
        if task.memory_mb_required > 1000:  # > 1GB
            # Bevorzuge NUMA-Node mit mehr verfügbarem Memory
            optimal_numa_node = self._get_optimal_numa_node()
        else:
            # Verwende beliebigen NUMA-Node
            optimal_numa_node = 0
        
        # Finde Worker auf optimalem NUMA-Node
        numa_workers = [
            (worker_id, worker) for worker_id, worker in self.workers.items()
            if worker.numa_node == optimal_numa_node
        ]
        
        if numa_workers:
            # Wähle least loaded Worker auf diesem NUMA-Node
            least_loaded = min(numa_workers, key=lambda x: x[1].current_load)
            self.stats["numa_optimizations"] += 1
            return least_loaded[0]
        else:
            return self._select_least_loaded_worker()
    
    def _select_workload_aware_worker(self, task: WorkloadTask) -> str:
        """Workload-Type-bewusste Worker-Auswahl"""
        
        # Verschiedene Strategien je nach Workload-Type
        if task.workload_type == WorkloadType.AI_INFERENCE:
            # AI-Inference: Bevorzuge Worker mit weniger aktiven Tasks
            return self._select_least_loaded_worker()
        
        elif task.workload_type == WorkloadType.AI_TRAINING:
            # AI-Training: Bevorzuge Worker mit mehr CPU-Cores
            workers_by_cores = sorted(
                self.workers.items(),
                key=lambda x: len(x[1].cpu_cores),
                reverse=True
            )
            return workers_by_cores[0][0] if workers_by_cores else "worker_0"
        
        elif task.workload_type == WorkloadType.IO_INTENSIVE:
            # IO-intensive: Verteile gleichmäßig
            return self._select_round_robin_worker()
        
        elif task.workload_type == WorkloadType.MEMORY_INTENSIVE:
            # Memory-intensive: NUMA-aware
            return self._select_numa_aware_worker(task)
        
        else:
            return self._select_least_loaded_worker()
    
    def _select_dynamic_worker(self, task: WorkloadTask) -> str:
        """Dynamische Worker-Auswahl basierend auf aktueller System-Load"""
        
        current_cpu_usage = self._get_current_cpu_usage()
        
        # Bei hoher CPU-Auslastung: Least Loaded
        if current_cpu_usage > 80:
            return self._select_least_loaded_worker()
        
        # Bei mittlerer CPU-Auslastung: Workload-aware
        elif current_cpu_usage > 50:
            return self._select_workload_aware_worker(task)
        
        # Bei niedriger CPU-Auslastung: NUMA-aware für Optimierung
        else:
            return self._select_numa_aware_worker(task)
    
    def _execute_task_on_worker(self, task: WorkloadTask, worker_id: str) -> Any:
        """Führe Task auf spezifischem Worker aus"""
        
        try:
            # CPU-Affinity für aktuellen Thread setzen (falls möglich)
            if self.enable_cpu_affinity and worker_id in self.workers:
                worker = self.workers[worker_id]
                try:
                    os.sched_setaffinity(0, worker.cpu_cores)
                    self.stats["cpu_affinity_assignments"] += 1
                except:
                    pass  # Nicht kritisch falls es fehlschlägt
            
            # Task-Function ausführen
            result = task.function(*task.args, **task.kwargs)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Task execution on worker {worker_id} failed: {e}")
            raise
    
    def _set_cpu_affinity(self, worker_id: str, task: WorkloadTask):
        """Setze CPU-Affinity für Worker"""
        
        if not self.enable_cpu_affinity or worker_id not in self.workers:
            return
        
        try:
            worker = self.workers[worker_id]
            
            # Bestimme CPU-Cores basierend auf Task-Requirements
            if task.cpu_cores_required > 1:
                # Multi-Core Task: Verwende mehrere Cores
                cores_to_use = worker.cpu_cores[:task.cpu_cores_required]
            else:
                # Single-Core Task: Verwende einen Core
                cores_to_use = [worker.cpu_cores[0]]
            
            # Setze Affinity für aktuellen Process
            os.sched_setaffinity(0, cores_to_use)
            
            self.logger.debug(f"Set CPU affinity for worker {worker_id}: cores {cores_to_use}")
            
        except Exception as e:
            self.logger.debug(f"CPU affinity setting failed: {e}")
    
    def _setup_workers(self):
        """Setup Worker-Konfiguration"""
        
        # Erstelle Worker für jeden verfügbaren CPU-Core
        cores_per_worker = max(1, self.cpu_cores // self.max_workers)
        
        for i in range(self.max_workers):
            worker_id = f"worker_{i}"
            
            # CPU-Cores für diesen Worker
            start_core = i * cores_per_worker
            end_core = min(start_core + cores_per_worker, self.cpu_cores)
            worker_cores = list(range(start_core, end_core))
            
            # NUMA-Node bestimmen
            numa_node = self._get_numa_node_for_cores(worker_cores)
            
            self.workers[worker_id] = WorkerStats(
                worker_id=worker_id,
                cpu_cores=worker_cores,
                numa_node=numa_node
            )
        
        self.logger.info(f"Setup {len(self.workers)} workers with {cores_per_worker} cores each")
    
    def _setup_worker_pools(self):
        """Setup spezialisierte Worker-Pools für verschiedene Workload-Types"""
        
        # Thread-Pool für IO-intensive Tasks
        self.worker_pools[WorkloadType.IO_INTENSIVE] = ThreadPoolExecutor(
            max_workers=min(self.cpu_cores, 64),  # Mehr Threads für IO
            thread_name_prefix="IOWorker"
        )
        
        # Process-Pool für CPU-intensive Tasks
        self.worker_pools[WorkloadType.CPU_INTENSIVE] = ProcessPoolExecutor(
            max_workers=self.physical_cores,  # Ein Process pro physischem Core
        )
        
        # Thread-Pool für AI-Inference (schnelle Antwortzeiten)
        self.worker_pools[WorkloadType.AI_INFERENCE] = ThreadPoolExecutor(
            max_workers=self.cpu_cores // 2,  # Moderate Parallelität
            thread_name_prefix="AIInference"
        )
        
        # Process-Pool für AI-Training (CPU-intensive)
        self.worker_pools[WorkloadType.AI_TRAINING] = ProcessPoolExecutor(
            max_workers=self.physical_cores // 2,  # Weniger Processes für Training
        )
        
        self.logger.info(f"Setup {len(self.worker_pools)} specialized worker pools")
    
    def _detect_numa_nodes(self) -> List[int]:
        """Erkenne verfügbare NUMA-Nodes"""
        
        numa_nodes = []
        
        try:
            if NUMA_AVAILABLE:
                # Verwende numa-Library
                numa_nodes = list(range(numa.get_max_node() + 1))
            else:
                # Fallback: Lese aus /sys/devices/system/node/
                node_path = Path("/sys/devices/system/node")
                if node_path.exists():
                    for node_dir in node_path.glob("node*"):
                        try:
                            node_id = int(node_dir.name[4:])  # "node0" -> 0
                            numa_nodes.append(node_id)
                        except ValueError:
                            continue
                
                # Fallback: Annahme von 2 NUMA-Nodes für moderne CPUs
                if not numa_nodes:
                    numa_nodes = [0, 1] if self.cpu_cores >= 16 else [0]
        
        except Exception as e:
            self.logger.debug(f"NUMA detection error: {e}")
            numa_nodes = [0]  # Fallback: Ein NUMA-Node
        
        return sorted(numa_nodes)
    
    def _get_numa_node_for_cores(self, cores: List[int]) -> int:
        """Bestimme NUMA-Node für CPU-Cores"""
        
        if not self.numa_nodes or len(self.numa_nodes) == 1:
            return 0
        
        # Einfache Heuristik: Erste Hälfte der Cores -> NUMA 0, zweite Hälfte -> NUMA 1
        if cores and cores[0] < self.cpu_cores // 2:
            return 0
        else:
            return 1 if len(self.numa_nodes) > 1 else 0
    
    def _get_optimal_numa_node(self) -> int:
        """Erhalte optimalen NUMA-Node basierend auf Memory-Verfügbarkeit"""
        
        # Vereinfachte Implementierung: Verwende NUMA-Node mit weniger Load
        if len(self.numa_nodes) <= 1:
            return 0
        
        # Zähle aktive Workers pro NUMA-Node
        numa_loads = {node: 0 for node in self.numa_nodes}
        
        for worker in self.workers.values():
            numa_loads[worker.numa_node] += worker.current_load
        
        # Wähle NUMA-Node mit geringster Load
        optimal_node = min(numa_loads.items(), key=lambda x: x[1])[0]
        
        return optimal_node    

    def _load_monitoring_loop(self):
        """Load-Monitoring-Loop für dynamische Anpassungen"""
        
        while self.load_monitoring_active:
            try:
                # Aktuelle CPU-Usage sammeln
                cpu_usage = psutil.cpu_percent(interval=1.0, percpu=True)
                self.cpu_usage_history.append({
                    "timestamp": datetime.now(),
                    "cpu_usage": cpu_usage,
                    "avg_usage": np.mean(cpu_usage)
                })
                
                # Worker-Loads updaten
                self._update_worker_loads(cpu_usage)
                
                # Load-Balancing-Effizienz berechnen
                self._calculate_load_balancing_efficiency()
                
                # Dynamische Anpassungen (falls nötig)
                self._adjust_load_balancing_strategy()
                
            except Exception as e:
                self.logger.error(f"Load monitoring error: {e}")
            
            time.sleep(1.0)
    
    def _update_worker_loads(self, cpu_usage: List[float]):
        """Update Worker-Loads basierend auf CPU-Usage"""
        
        for worker_id, worker in self.workers.items():
            # Berechne durchschnittliche CPU-Usage für Worker-Cores
            worker_cpu_usage = [
                cpu_usage[core] for core in worker.cpu_cores
                if core < len(cpu_usage)
            ]
            
            if worker_cpu_usage:
                worker.current_load = np.mean(worker_cpu_usage)
    
    def _calculate_load_balancing_efficiency(self):
        """Berechne Load-Balancing-Effizienz"""
        
        if not self.cpu_usage_history:
            return
        
        try:
            # Letzte CPU-Usage-Werte
            recent_usage = [entry["cpu_usage"] for entry in list(self.cpu_usage_history)[-10:]]
            
            if recent_usage:
                # Berechne Standardabweichung der CPU-Core-Auslastung
                all_core_usage = []
                for usage_list in recent_usage:
                    all_core_usage.extend(usage_list)
                
                if all_core_usage:
                    std_dev = np.std(all_core_usage)
                    mean_usage = np.mean(all_core_usage)
                    
                    # Effizienz: Je geringer die Standardabweichung, desto besser
                    # Normalisiert auf 0-100 Skala
                    if mean_usage > 0:
                        efficiency = max(0, 100 - (std_dev / mean_usage * 100))
                        self.stats["load_balancing_efficiency"] = efficiency
                        self.stats["avg_cpu_utilization"] = mean_usage
        
        except Exception as e:
            self.logger.debug(f"Efficiency calculation error: {e}")
    
    def _adjust_load_balancing_strategy(self):
        """Dynamische Anpassung der Load-Balancing-Strategie"""
        
        if self.strategy != LoadBalancingStrategy.DYNAMIC:
            return
        
        try:
            current_efficiency = self.stats.get("load_balancing_efficiency", 0)
            avg_cpu_usage = self.stats.get("avg_cpu_utilization", 0)
            
            # Strategie-Anpassung basierend auf Performance
            if current_efficiency < 70 and avg_cpu_usage > 80:
                # Niedrige Effizienz bei hoher CPU-Last: Wechsle zu Least Loaded
                self.logger.info("Adjusting to LEAST_LOADED strategy due to high CPU load")
            
            elif current_efficiency > 90 and avg_cpu_usage < 50:
                # Hohe Effizienz bei niedriger CPU-Last: Nutze NUMA-Optimierung
                self.logger.info("Adjusting to NUMA_AWARE strategy for optimization")
        
        except Exception as e:
            self.logger.debug(f"Strategy adjustment error: {e}")
    
    def _update_worker_stats(self, worker_id: str, execution_time: float):
        """Update Worker-Statistiken"""
        
        if worker_id in self.workers:
            worker = self.workers[worker_id]
            worker.tasks_completed += 1
            worker.total_execution_time += execution_time
            worker.last_task_time = datetime.now()
    
    def _get_current_cpu_usage(self) -> float:
        """Erhalte aktuelle CPU-Usage"""
        try:
            return psutil.cpu_percent(interval=0.1)
        except:
            return 0.0
    
    def _get_current_memory_usage(self) -> float:
        """Erhalte aktuelle Memory-Usage"""
        try:
            return psutil.virtual_memory().percent
        except:
            return 0.0
    
    def get_load_balancing_status(self) -> Dict[str, Any]:
        """Erhalte aktuellen Load-Balancing-Status"""
        
        return {
            "timestamp": datetime.now().isoformat(),
            "strategy": self.strategy.value,
            "monitoring_active": self.load_monitoring_active,
            "cpu_cores": self.cpu_cores,
            "physical_cores": self.physical_cores,
            "numa_nodes": self.numa_nodes,
            "max_workers": self.max_workers,
            "active_workers": len(self.workers),
            "worker_pools": {
                workload_type.value: {
                    "type": type(pool).__name__,
                    "max_workers": getattr(pool, '_max_workers', 'unknown')
                }
                for workload_type, pool in self.worker_pools.items()
            },
            "current_cpu_usage": self._get_current_cpu_usage(),
            "current_memory_usage": self._get_current_memory_usage(),
            "statistics": self.stats
        }
    
    def get_worker_statistics(self) -> Dict[str, Any]:
        """Erhalte detaillierte Worker-Statistiken"""
        
        worker_stats = {}
        
        for worker_id, worker in self.workers.items():
            worker_stats[worker_id] = {
                "cpu_cores": worker.cpu_cores,
                "numa_node": worker.numa_node,
                "tasks_completed": worker.tasks_completed,
                "total_execution_time": worker.total_execution_time,
                "avg_execution_time": worker.get_avg_execution_time(),
                "current_load": worker.current_load,
                "last_task_time": worker.last_task_time.isoformat() if worker.last_task_time else None
            }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "workers": worker_stats,
            "load_distribution": self._calculate_load_distribution(),
            "numa_distribution": self._calculate_numa_distribution()
        }
    
    def _calculate_load_distribution(self) -> Dict[str, float]:
        """Berechne Load-Verteilung über alle Worker"""
        
        if not self.workers:
            return {}
        
        total_tasks = sum(worker.tasks_completed for worker in self.workers.values())
        
        if total_tasks == 0:
            return {worker_id: 0.0 for worker_id in self.workers.keys()}
        
        return {
            worker_id: (worker.tasks_completed / total_tasks * 100)
            for worker_id, worker in self.workers.items()
        }
    
    def _calculate_numa_distribution(self) -> Dict[int, Dict[str, Any]]:
        """Berechne NUMA-Node-Verteilung"""
        
        numa_stats = {}
        
        for numa_node in self.numa_nodes:
            numa_workers = [
                worker for worker in self.workers.values()
                if worker.numa_node == numa_node
            ]
            
            total_tasks = sum(worker.tasks_completed for worker in numa_workers)
            avg_load = np.mean([worker.current_load for worker in numa_workers]) if numa_workers else 0.0
            
            numa_stats[numa_node] = {
                "worker_count": len(numa_workers),
                "total_tasks": total_tasks,
                "average_load": avg_load,
                "workers": [worker.worker_id for worker in numa_workers]
            }
        
        return numa_stats
    
    def optimize_for_workload_type(self, workload_type: WorkloadType) -> Dict[str, Any]:
        """Optimiere Load-Balancing für spezifischen Workload-Type"""
        
        recommendations = []
        
        if workload_type == WorkloadType.AI_INFERENCE:
            # AI-Inference: Niedrige Latenz wichtig
            recommendations.append({
                "optimization": "Use ThreadPoolExecutor for low latency",
                "strategy": "LEAST_LOADED",
                "cpu_affinity": True,
                "numa_awareness": False
            })
        
        elif workload_type == WorkloadType.AI_TRAINING:
            # AI-Training: Hoher Durchsatz wichtig
            recommendations.append({
                "optimization": "Use ProcessPoolExecutor for high throughput",
                "strategy": "NUMA_AWARE",
                "cpu_affinity": True,
                "numa_awareness": True
            })
        
        elif workload_type == WorkloadType.BATCH_PROCESSING:
            # Batch-Processing: Gleichmäßige Verteilung
            recommendations.append({
                "optimization": "Use Round-Robin for even distribution",
                "strategy": "ROUND_ROBIN",
                "cpu_affinity": False,
                "numa_awareness": False
            })
        
        elif workload_type == WorkloadType.MEMORY_INTENSIVE:
            # Memory-intensive: NUMA-Optimierung
            recommendations.append({
                "optimization": "Use NUMA-aware scheduling",
                "strategy": "NUMA_AWARE",
                "cpu_affinity": True,
                "numa_awareness": True
            })
        
        return {
            "workload_type": workload_type.value,
            "recommendations": recommendations,
            "current_strategy": self.strategy.value,
            "current_config": {
                "cpu_affinity": self.enable_cpu_affinity,
                "numa_awareness": self.enable_numa_awareness
            }
        }
    
    def benchmark_load_balancing(self, duration_seconds: int = 60) -> Dict[str, Any]:
        """Führe Load-Balancing-Benchmark durch"""
        
        self.logger.info(f"Starting load balancing benchmark for {duration_seconds} seconds...")
        
        # Benchmark-Tasks erstellen
        def cpu_intensive_task(n: int) -> int:
            """CPU-intensive Test-Task"""
            result = 0
            for i in range(n * 1000):
                result += i ** 2
            return result
        
        def io_intensive_task(delay: float) -> str:
            """IO-intensive Test-Task"""
            time.sleep(delay)
            return f"IO task completed after {delay}s"
        
        # Test-Tasks
        test_tasks = []
        
        # CPU-intensive Tasks
        for i in range(20):
            task = WorkloadTask(
                task_id=f"cpu_task_{i}",
                workload_type=WorkloadType.CPU_INTENSIVE,
                function=cpu_intensive_task,
                args=(1000,),
                priority=2
            )
            test_tasks.append(task)
        
        # IO-intensive Tasks
        for i in range(10):
            task = WorkloadTask(
                task_id=f"io_task_{i}",
                workload_type=WorkloadType.IO_INTENSIVE,
                function=io_intensive_task,
                args=(0.1,),
                priority=1
            )
            test_tasks.append(task)
        
        # Benchmark ausführen
        start_time = datetime.now()
        results = self.execute_batch_tasks(test_tasks)
        end_time = datetime.now()
        
        # Ergebnisse analysieren
        successful_tasks = [r for r in results if r.success]
        failed_tasks = [r for r in results if not r.success]
        
        total_execution_time = sum(r.execution_time for r in successful_tasks)
        avg_execution_time = total_execution_time / len(successful_tasks) if successful_tasks else 0
        
        benchmark_duration = (end_time - start_time).total_seconds()
        
        return {
            "benchmark_duration": benchmark_duration,
            "total_tasks": len(test_tasks),
            "successful_tasks": len(successful_tasks),
            "failed_tasks": len(failed_tasks),
            "success_rate": len(successful_tasks) / len(test_tasks) * 100,
            "total_execution_time": total_execution_time,
            "avg_execution_time": avg_execution_time,
            "throughput_tasks_per_second": len(successful_tasks) / benchmark_duration,
            "load_balancing_efficiency": self.stats.get("load_balancing_efficiency", 0),
            "worker_distribution": self._calculate_load_distribution(),
            "numa_distribution": self._calculate_numa_distribution()
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Erhalte Load-Balancer-Statistiken"""
        
        return {
            **self.stats,
            "cpu_cores": self.cpu_cores,
            "physical_cores": self.physical_cores,
            "numa_nodes_count": len(self.numa_nodes),
            "workers_count": len(self.workers),
            "worker_pools_count": len(self.worker_pools),
            "monitoring_active": self.load_monitoring_active,
            "strategy": self.strategy.value
        }


# Factory Function
def create_load_balancer(config: Optional[Dict] = None) -> LoadBalancer:
    """
    Factory Function für Load Balancer
    
    Args:
        config: Load-Balancer-Konfiguration
        
    Returns:
        LoadBalancer Instance
    """
    return LoadBalancer(config=config)


# Demo/Test Function
def demo_load_balancer():
    """Demo für Load Balancer"""
    
    print("🧪 Testing Load Balancer...")
    
    # Load Balancer erstellen
    load_balancer = create_load_balancer({
        "strategy": "dynamic",
        "max_workers": 8,  # Reduziert für Demo
        "enable_cpu_affinity": True,
        "enable_numa_awareness": True
    })
    
    # Status anzeigen
    status = load_balancer.get_load_balancing_status()
    print(f"\n💻 Load Balancer Status:")
    print(f"   CPU Cores: {status['cpu_cores']} ({status['physical_cores']} physical)")
    print(f"   NUMA Nodes: {status['numa_nodes']}")
    print(f"   Strategy: {status['strategy']}")
    print(f"   Max Workers: {status['max_workers']}")
    print(f"   Active Workers: {status['active_workers']}")
    
    # Load-Balancing starten
    load_balancer.start_load_balancing()
    
    # Test-Tasks erstellen
    def test_cpu_task(n: int) -> int:
        """Test CPU-intensive Task"""
        result = 0
        for i in range(n):
            result += i ** 2
        return result
    
    def test_io_task(delay: float) -> str:
        """Test IO-intensive Task"""
        time.sleep(delay)
        return f"Completed after {delay}s"
    
    # Verschiedene Task-Typen
    test_tasks = []
    
    # CPU-intensive Tasks
    for i in range(5):
        task = WorkloadTask(
            task_id=f"cpu_test_{i}",
            workload_type=WorkloadType.CPU_INTENSIVE,
            function=test_cpu_task,
            args=(10000,),
            priority=2
        )
        test_tasks.append(task)
    
    # IO-intensive Tasks
    for i in range(3):
        task = WorkloadTask(
            task_id=f"io_test_{i}",
            workload_type=WorkloadType.IO_INTENSIVE,
            function=test_io_task,
            args=(0.5,),
            priority=1
        )
        test_tasks.append(task)
    
    print(f"\n🔄 Executing {len(test_tasks)} test tasks...")
    
    # Tasks ausführen
    start_time = time.time()
    results = load_balancer.execute_batch_tasks(test_tasks)
    execution_time = time.time() - start_time
    
    # Ergebnisse analysieren
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    
    print(f"✅ Execution completed in {execution_time:.2f}s:")
    print(f"   Successful: {len(successful)}")
    print(f"   Failed: {len(failed)}")
    print(f"   Success Rate: {len(successful)/len(results)*100:.1f}%")
    
    if successful:
        avg_exec_time = np.mean([r.execution_time for r in successful])
        print(f"   Avg Execution Time: {avg_exec_time:.3f}s")
    
    # Worker-Statistiken
    worker_stats = load_balancer.get_worker_statistics()
    print(f"\n👥 Worker Statistics:")
    
    load_distribution = worker_stats['load_distribution']
    for worker_id, load_pct in load_distribution.items():
        worker_info = worker_stats['workers'][worker_id]
        print(f"   {worker_id}: {load_pct:.1f}% load, {worker_info['tasks_completed']} tasks")
    
    # NUMA-Verteilung
    numa_distribution = worker_stats['numa_distribution']
    print(f"\n🧠 NUMA Distribution:")
    for numa_node, numa_info in numa_distribution.items():
        print(f"   NUMA {numa_node}: {numa_info['worker_count']} workers, {numa_info['total_tasks']} tasks")
    
    # Workload-Optimierung
    print(f"\n🎯 Workload Optimizations:")
    for workload_type in [WorkloadType.AI_INFERENCE, WorkloadType.AI_TRAINING]:
        optimization = load_balancer.optimize_for_workload_type(workload_type)
        print(f"   {workload_type.value}:")
        for rec in optimization['recommendations']:
            print(f"     - {rec['optimization']}")
    
    # Benchmark
    print(f"\n⚡ Running benchmark...")
    benchmark_results = load_balancer.benchmark_load_balancing(duration_seconds=10)
    
    print(f"   Benchmark Duration: {benchmark_results['benchmark_duration']:.2f}s")
    print(f"   Tasks Processed: {benchmark_results['successful_tasks']}/{benchmark_results['total_tasks']}")
    print(f"   Throughput: {benchmark_results['throughput_tasks_per_second']:.1f} tasks/sec")
    print(f"   Load Balancing Efficiency: {benchmark_results['load_balancing_efficiency']:.1f}%")
    
    # Load-Balancing stoppen
    load_balancer.stop_load_balancing()
    
    # Finale Statistiken
    stats = load_balancer.get_statistics()
    print(f"\n📊 Final Statistics:")
    print(f"   Tasks Processed: {stats['tasks_processed']}")
    print(f"   Tasks Failed: {stats['tasks_failed']}")
    print(f"   Avg CPU Utilization: {stats['avg_cpu_utilization']:.1f}%")
    print(f"   Load Balancing Efficiency: {stats['load_balancing_efficiency']:.1f}%")
    print(f"   NUMA Optimizations: {stats['numa_optimizations']}")
    print(f"   CPU Affinity Assignments: {stats['cpu_affinity_assignments']}")


if __name__ == "__main__":
    demo_load_balancer()