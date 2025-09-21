#!/usr/bin/env python3
"""
GPU Utilization Optimizer für maximale RTX 5090 Auslastung
Phase 3 Implementation - Task 11

Features:
- Maximale GPU-Auslastung für RTX 5090 (32GB VRAM)
- Dynamic Batch-Size-Optimization
- Memory-Management und VRAM-Optimierung
- Multi-GPU-Support und Load-Balancing
- CUDA-Stream-Optimierung
- Performance-Monitoring und Auto-Tuning
"""

import time
import threading
import logging
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import numpy as np
from collections import deque
import queue
import json

# GPU Libraries
try:
    import torch
    import torch.cuda
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    import pynvml
    pynvml.nvmlInit()
    PYNVML_AVAILABLE = True
except ImportError:
    PYNVML_AVAILABLE = False

try:
    import cupy as cp
    CUPY_AVAILABLE = True
except ImportError:
    CUPY_AVAILABLE = False


class GPUWorkloadType(Enum):
    """Typen von GPU-Workloads"""
    TRAINING = "training"
    INFERENCE = "inference"
    BACKTESTING = "backtesting"
    OPTIMIZATION = "optimization"
    FEATURE_EXTRACTION = "feature_extraction"
    PATTERN_ANALYSIS = "pattern_analysis"


class GPUMemoryStrategy(Enum):
    """GPU Memory Management Strategien"""
    CONSERVATIVE = "conservative"  # 70% VRAM Usage
    BALANCED = "balanced"         # 85% VRAM Usage
    AGGRESSIVE = "aggressive"     # 95% VRAM Usage
    DYNAMIC = "dynamic"          # Adaptive basierend auf Workload


@dataclass
class GPUWorkload:
    """GPU-Workload Definition"""
    workload_id: str
    workload_type: GPUWorkloadType
    priority: int  # 1-10, höher = wichtiger
    estimated_vram_mb: int
    estimated_compute_time: float
    batch_size: int
    callback: Optional[Callable] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.created_at = datetime.now()
        self.status = "pending"
        self.gpu_id: Optional[int] = None
        self.actual_vram_mb: Optional[int] = None
        self.actual_compute_time: Optional[float] = None


@dataclass
class GPUMetrics:
    """GPU Performance-Metriken"""
    gpu_id: int
    timestamp: datetime
    utilization_percent: float
    memory_used_mb: int
    memory_total_mb: int
    memory_percent: float
    temperature_c: float
    power_usage_w: float
    compute_capability: Tuple[int, int]
    cuda_cores: int
    tensor_cores: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "gpu_id": self.gpu_id,
            "timestamp": self.timestamp.isoformat(),
            "utilization_percent": self.utilization_percent,
            "memory_used_mb": self.memory_used_mb,
            "memory_total_mb": self.memory_total_mb,
            "memory_percent": self.memory_percent,
            "temperature_c": self.temperature_c,
            "power_usage_w": self.power_usage_w,
            "compute_capability": self.compute_capability,
            "cuda_cores": self.cuda_cores,
            "tensor_cores": self.tensor_cores
        }


class GPUUtilizationOptimizer:
    """
    GPU Utilization Optimizer für maximale RTX 5090 Auslastung
    
    Features:
    - Maximale GPU-Auslastung (95%+ bei RTX 5090)
    - Dynamic Batch-Size-Optimization
    - VRAM-Management für 32GB RTX 5090
    - Multi-GPU-Support und Load-Balancing
    - CUDA-Stream-Optimierung
    - Performance-Monitoring und Auto-Tuning
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # GPU-Konfiguration
        self.memory_strategy = GPUMemoryStrategy(
            self.config.get("memory_strategy", "balanced")
        )
        self.target_utilization = self.config.get("target_utilization", 95.0)  # %
        self.max_batch_size = self.config.get("max_batch_size", 1024)
        self.min_batch_size = self.config.get("min_batch_size", 32)
        self.optimization_interval = self.config.get("optimization_interval", 5.0)  # Sekunden
        
        # GPU-Detection
        self.available_gpus: List[int] = []
        self.gpu_metrics: Dict[int, GPUMetrics] = {}
        self.gpu_capabilities: Dict[int, Dict[str, Any]] = {}
        
        # Workload-Management
        self.workload_queue = queue.PriorityQueue()
        self.active_workloads: Dict[str, GPUWorkload] = {}
        self.completed_workloads: List[GPUWorkload] = []
        
        # Performance-Tracking
        self.performance_history: deque = deque(maxlen=1000)
        self.optimization_stats = {
            "workloads_processed": 0,
            "total_compute_time": 0.0,
            "avg_gpu_utilization": 0.0,
            "vram_efficiency": 0.0,
            "batch_size_optimizations": 0
        }
        
        # Threading
        self.optimizer_active = False
        self.optimizer_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # CUDA-Streams für Parallelisierung
        self.cuda_streams: Dict[int, Any] = {}
        
        # Initialisierung
        self._initialize_gpu_detection()
        self._setup_cuda_streams()
        
        self.logger.info(f"GPUUtilizationOptimizer initialized with {len(self.available_gpus)} GPU(s)")
    
    def _initialize_gpu_detection(self):
        """Initialisiere GPU-Detection und Capabilities"""
        
        if not TORCH_AVAILABLE:
            self.logger.error("PyTorch not available - GPU optimization disabled")
            return
        
        if not torch.cuda.is_available():
            self.logger.error("CUDA not available - GPU optimization disabled")
            return
        
        # Verfügbare GPUs erkennen
        gpu_count = torch.cuda.device_count()
        self.logger.info(f"Detected {gpu_count} CUDA GPU(s)")
        
        for gpu_id in range(gpu_count):
            try:
                # GPU-Properties abrufen
                props = torch.cuda.get_device_properties(gpu_id)
                
                # RTX 5090 Detection (Beispiel-Werte)
                is_rtx_5090 = (
                    props.total_memory >= 30 * 1024**3 and  # >= 30GB VRAM
                    props.major >= 8  # Compute Capability >= 8.0
                )
                
                gpu_info = {
                    "name": props.name,
                    "total_memory_gb": props.total_memory / (1024**3),
                    "compute_capability": (props.major, props.minor),
                    "multiprocessor_count": props.multi_processor_count,
                    "is_rtx_5090": is_rtx_5090,
                    "max_threads_per_block": props.max_threads_per_block,
                    "max_shared_memory": props.shared_memory_per_block
                }
                
                self.available_gpus.append(gpu_id)
                self.gpu_capabilities[gpu_id] = gpu_info
                
                self.logger.info(f"GPU {gpu_id}: {props.name} "
                               f"({gpu_info['total_memory_gb']:.1f}GB VRAM, "
                               f"CC {props.major}.{props.minor})")
                
                if is_rtx_5090:
                    self.logger.info(f"RTX 5090 detected on GPU {gpu_id} - enabling maximum optimization")
                
            except Exception as e:
                self.logger.error(f"Error detecting GPU {gpu_id}: {e}")
    
    def _setup_cuda_streams(self):
        """Setup CUDA-Streams für Parallelisierung"""
        
        if not TORCH_AVAILABLE or not torch.cuda.is_available():
            return
        
        try:
            for gpu_id in self.available_gpus:
                with torch.cuda.device(gpu_id):
                    # Erstelle mehrere Streams pro GPU für Parallelisierung
                    streams = []
                    for i in range(4):  # 4 Streams pro GPU
                        stream = torch.cuda.Stream()
                        streams.append(stream)
                    
                    self.cuda_streams[gpu_id] = streams
                    self.logger.info(f"Created {len(streams)} CUDA streams for GPU {gpu_id}")
        
        except Exception as e:
            self.logger.error(f"Error setting up CUDA streams: {e}")
    
    def start_optimization(self):
        """Starte GPU-Optimierung"""
        
        if self.optimizer_active:
            self.logger.warning("GPU optimization already active")
            return
        
        if not self.available_gpus:
            self.logger.error("No GPUs available for optimization")
            return
        
        self.optimizer_active = True
        self.stop_event.clear()
        
        # Optimizer-Thread starten
        self.optimizer_thread = threading.Thread(
            target=self._optimization_loop,
            name="GPUOptimizer",
            daemon=True
        )
        self.optimizer_thread.start()
        
        self.logger.info("GPU optimization started")
    
    def stop_optimization(self):
        """Stoppe GPU-Optimierung"""
        
        if not self.optimizer_active:
            return
        
        self.optimizer_active = False
        self.stop_event.set()
        
        if self.optimizer_thread:
            self.optimizer_thread.join(timeout=10.0)
        
        self.logger.info("GPU optimization stopped")
    
    def submit_workload(self, workload: GPUWorkload) -> str:
        """Submitte GPU-Workload zur Verarbeitung"""
        
        try:
            # Priority-basierte Queue (niedrigere Zahl = höhere Priorität)
            priority = -workload.priority  # Negative für höchste Priorität zuerst
            
            self.workload_queue.put((priority, workload.workload_id, workload))
            
            self.logger.info(f"Workload {workload.workload_id} submitted "
                           f"(type: {workload.workload_type.value}, priority: {workload.priority})")
            
            return workload.workload_id
            
        except Exception as e:
            self.logger.error(f"Error submitting workload: {e}")
            raise
    
    def get_optimal_batch_size(self, workload_type: GPUWorkloadType, 
                              gpu_id: int, base_batch_size: int = 64) -> int:
        """Ermittle optimale Batch-Size für Workload-Typ und GPU"""
        
        try:
            if gpu_id not in self.available_gpus:
                return base_batch_size
            
            gpu_info = self.gpu_capabilities[gpu_id]
            available_vram_gb = gpu_info["total_memory_gb"]
            
            # RTX 5090 spezifische Optimierungen
            if gpu_info.get("is_rtx_5090", False):
                # Maximale Batch-Sizes für RTX 5090 (32GB VRAM)
                optimal_sizes = {
                    GPUWorkloadType.TRAINING: min(512, self.max_batch_size),
                    GPUWorkloadType.INFERENCE: min(1024, self.max_batch_size),
                    GPUWorkloadType.BACKTESTING: min(256, self.max_batch_size),
                    GPUWorkloadType.OPTIMIZATION: min(128, self.max_batch_size),
                    GPUWorkloadType.FEATURE_EXTRACTION: min(512, self.max_batch_size),
                    GPUWorkloadType.PATTERN_ANALYSIS: min(256, self.max_batch_size)
                }
            else:
                # Standard-Optimierungen basierend auf VRAM
                vram_factor = min(available_vram_gb / 8.0, 4.0)  # Skaliere basierend auf VRAM
                
                optimal_sizes = {
                    GPUWorkloadType.TRAINING: int(base_batch_size * vram_factor * 0.8),
                    GPUWorkloadType.INFERENCE: int(base_batch_size * vram_factor * 1.5),
                    GPUWorkloadType.BACKTESTING: int(base_batch_size * vram_factor * 1.0),
                    GPUWorkloadType.OPTIMIZATION: int(base_batch_size * vram_factor * 0.6),
                    GPUWorkloadType.FEATURE_EXTRACTION: int(base_batch_size * vram_factor * 1.2),
                    GPUWorkloadType.PATTERN_ANALYSIS: int(base_batch_size * vram_factor * 1.0)
                }
            
            optimal_batch_size = optimal_sizes.get(workload_type, base_batch_size)
            
            # Clamp zu Min/Max-Werten
            optimal_batch_size = max(self.min_batch_size, 
                                   min(optimal_batch_size, self.max_batch_size))
            
            self.logger.debug(f"Optimal batch size for {workload_type.value} on GPU {gpu_id}: {optimal_batch_size}")
            
            return optimal_batch_size
            
        except Exception as e:
            self.logger.error(f"Error calculating optimal batch size: {e}")
            return base_batch_size
    
    def get_gpu_metrics(self, gpu_id: int) -> Optional[GPUMetrics]:
        """Erhalte aktuelle GPU-Metriken"""
        
        try:
            if gpu_id not in self.available_gpus:
                return None
            
            if not TORCH_AVAILABLE or not torch.cuda.is_available():
                return None
            
            with torch.cuda.device(gpu_id):
                # Memory-Info
                memory_allocated = torch.cuda.memory_allocated(gpu_id)
                memory_reserved = torch.cuda.memory_reserved(gpu_id)
                memory_total = torch.cuda.get_device_properties(gpu_id).total_memory
                
                # GPU-Utilization (approximiert über Memory-Usage)
                utilization_percent = (memory_allocated / memory_total) * 100
                
                # Zusätzliche Metriken über PYNVML
                temperature_c = 0.0
                power_usage_w = 0.0
                
                if PYNVML_AVAILABLE:
                    try:
                        handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_id)
                        temperature_c = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                        power_usage_w = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # mW zu W
                    except Exception as e:
                        self.logger.debug(f"Could not get NVML metrics for GPU {gpu_id}: {e}")
                
                # GPU-Properties
                props = torch.cuda.get_device_properties(gpu_id)
                
                metrics = GPUMetrics(
                    gpu_id=gpu_id,
                    timestamp=datetime.now(),
                    utilization_percent=utilization_percent,
                    memory_used_mb=memory_allocated // (1024**2),
                    memory_total_mb=memory_total // (1024**2),
                    memory_percent=(memory_allocated / memory_total) * 100,
                    temperature_c=temperature_c,
                    power_usage_w=power_usage_w,
                    compute_capability=(props.major, props.minor),
                    cuda_cores=props.multi_processor_count * 128,  # Approximation
                    tensor_cores=props.multi_processor_count * 4 if props.major >= 7 else 0
                )
                
                self.gpu_metrics[gpu_id] = metrics
                return metrics
                
        except Exception as e:
            self.logger.error(f"Error getting GPU metrics for GPU {gpu_id}: {e}")
            return None
    
    def _optimization_loop(self):
        """Haupt-Optimierungs-Loop"""
        
        while self.optimizer_active and not self.stop_event.is_set():
            try:
                # GPU-Metriken aktualisieren
                for gpu_id in self.available_gpus:
                    self.get_gpu_metrics(gpu_id)
                
                # Workloads verarbeiten
                self._process_workload_queue()
                
                # Performance-Optimierungen
                self._optimize_performance()
                
                # Statistiken aktualisieren
                self._update_statistics()
                
                # Warte bis zum nächsten Optimization-Cycle
                self.stop_event.wait(self.optimization_interval)
                
            except Exception as e:
                self.logger.error(f"Optimization loop error: {e}")
                time.sleep(1.0)
    
    def _process_workload_queue(self):
        """Verarbeite Workload-Queue"""
        
        try:
            # Versuche Workloads aus der Queue zu holen
            while not self.workload_queue.empty():
                try:
                    priority, workload_id, workload = self.workload_queue.get_nowait()
                    
                    # Finde beste GPU für Workload
                    best_gpu = self._select_best_gpu(workload)
                    
                    if best_gpu is not None:
                        # Starte Workload auf GPU
                        self._execute_workload(workload, best_gpu)
                    else:
                        # Keine GPU verfügbar - zurück in Queue
                        self.workload_queue.put((priority, workload_id, workload))
                        break
                        
                except queue.Empty:
                    break
                    
        except Exception as e:
            self.logger.error(f"Error processing workload queue: {e}")
    
    def _select_best_gpu(self, workload: GPUWorkload) -> Optional[int]:
        """Wähle beste GPU für Workload"""
        
        try:
            best_gpu = None
            best_score = -1.0
            
            for gpu_id in self.available_gpus:
                metrics = self.gpu_metrics.get(gpu_id)
                if not metrics:
                    continue
                
                # Verfügbarer VRAM
                available_vram_mb = metrics.memory_total_mb - metrics.memory_used_mb
                
                # Prüfe ob genug VRAM verfügbar
                if available_vram_mb < workload.estimated_vram_mb:
                    continue
                
                # Score basierend auf verfügbarem VRAM und aktueller Utilization
                vram_score = available_vram_mb / metrics.memory_total_mb
                utilization_score = 1.0 - (metrics.utilization_percent / 100.0)
                
                # RTX 5090 Bonus
                gpu_info = self.gpu_capabilities[gpu_id]
                rtx_bonus = 1.2 if gpu_info.get("is_rtx_5090", False) else 1.0
                
                total_score = (vram_score * 0.6 + utilization_score * 0.4) * rtx_bonus
                
                if total_score > best_score:
                    best_score = total_score
                    best_gpu = gpu_id
            
            return best_gpu
            
        except Exception as e:
            self.logger.error(f"Error selecting best GPU: {e}")
            return None
    
    def _execute_workload(self, workload: GPUWorkload, gpu_id: int):
        """Führe Workload auf GPU aus"""
        
        try:
            workload.gpu_id = gpu_id
            workload.status = "running"
            self.active_workloads[workload.workload_id] = workload
            
            start_time = time.time()
            
            # Optimale Batch-Size ermitteln
            optimal_batch_size = self.get_optimal_batch_size(
                workload.workload_type, gpu_id, workload.batch_size
            )
            
            if optimal_batch_size != workload.batch_size:
                self.logger.info(f"Optimized batch size for {workload.workload_id}: "
                               f"{workload.batch_size} -> {optimal_batch_size}")
                workload.batch_size = optimal_batch_size
                self.optimization_stats["batch_size_optimizations"] += 1
            
            # Workload-Callback ausführen (falls vorhanden)
            if workload.callback:
                with torch.cuda.device(gpu_id):
                    # Verwende CUDA-Stream für Parallelisierung
                    stream = self.cuda_streams[gpu_id][0] if gpu_id in self.cuda_streams else None
                    
                    if stream:
                        with torch.cuda.stream(stream):
                            result = workload.callback(workload, gpu_id)
                    else:
                        result = workload.callback(workload, gpu_id)
                    
                    # Synchronisiere GPU
                    torch.cuda.synchronize(gpu_id)
            
            # Workload abschließen
            execution_time = time.time() - start_time
            workload.actual_compute_time = execution_time
            workload.status = "completed"
            
            # Von aktiven zu abgeschlossenen Workloads verschieben
            del self.active_workloads[workload.workload_id]
            self.completed_workloads.append(workload)
            
            # Statistiken aktualisieren
            self.optimization_stats["workloads_processed"] += 1
            self.optimization_stats["total_compute_time"] += execution_time
            
            self.logger.info(f"Workload {workload.workload_id} completed on GPU {gpu_id} "
                           f"in {execution_time:.2f}s")
            
        except Exception as e:
            self.logger.error(f"Error executing workload {workload.workload_id}: {e}")
            workload.status = "failed"
            if workload.workload_id in self.active_workloads:
                del self.active_workloads[workload.workload_id]
    
    def _optimize_performance(self):
        """Führe Performance-Optimierungen durch"""
        
        try:
            # Memory-Cleanup
            if TORCH_AVAILABLE and torch.cuda.is_available():
                for gpu_id in self.available_gpus:
                    with torch.cuda.device(gpu_id):
                        # Cache leeren wenn Utilization niedrig
                        metrics = self.gpu_metrics.get(gpu_id)
                        if metrics and metrics.utilization_percent < 20.0:
                            torch.cuda.empty_cache()
            
            # Performance-History aktualisieren
            current_metrics = {}
            for gpu_id in self.available_gpus:
                metrics = self.gpu_metrics.get(gpu_id)
                if metrics:
                    current_metrics[gpu_id] = metrics.to_dict()
            
            if current_metrics:
                self.performance_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "gpu_metrics": current_metrics,
                    "active_workloads": len(self.active_workloads),
                    "queue_size": self.workload_queue.qsize()
                })
            
        except Exception as e:
            self.logger.error(f"Error in performance optimization: {e}")
    
    def _update_statistics(self):
        """Aktualisiere Optimierungs-Statistiken"""
        
        try:
            if not self.gpu_metrics:
                return
            
            # Durchschnittliche GPU-Utilization
            total_utilization = sum(
                metrics.utilization_percent 
                for metrics in self.gpu_metrics.values()
            )
            avg_utilization = total_utilization / len(self.gpu_metrics)
            self.optimization_stats["avg_gpu_utilization"] = avg_utilization
            
            # VRAM-Effizienz
            total_vram_used = sum(
                metrics.memory_percent 
                for metrics in self.gpu_metrics.values()
            )
            vram_efficiency = total_vram_used / len(self.gpu_metrics)
            self.optimization_stats["vram_efficiency"] = vram_efficiency
            
        except Exception as e:
            self.logger.error(f"Error updating statistics: {e}")
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Erhalte Optimierungs-Report"""
        
        try:
            # Aktuelle GPU-Status
            gpu_status = {}
            for gpu_id in self.available_gpus:
                metrics = self.gpu_metrics.get(gpu_id)
                gpu_info = self.gpu_capabilities.get(gpu_id, {})
                
                if metrics:
                    gpu_status[gpu_id] = {
                        "name": gpu_info.get("name", "Unknown"),
                        "is_rtx_5090": gpu_info.get("is_rtx_5090", False),
                        "utilization_percent": metrics.utilization_percent,
                        "memory_percent": metrics.memory_percent,
                        "temperature_c": metrics.temperature_c,
                        "power_usage_w": metrics.power_usage_w,
                        "vram_total_gb": metrics.memory_total_mb / 1024,
                        "vram_used_gb": metrics.memory_used_mb / 1024,
                        "vram_free_gb": (metrics.memory_total_mb - metrics.memory_used_mb) / 1024
                    }
            
            return {
                "timestamp": datetime.now().isoformat(),
                "optimizer_active": self.optimizer_active,
                "gpu_count": len(self.available_gpus),
                "gpu_status": gpu_status,
                "active_workloads": len(self.active_workloads),
                "completed_workloads": len(self.completed_workloads),
                "queue_size": self.workload_queue.qsize(),
                "statistics": self.optimization_stats.copy(),
                "memory_strategy": self.memory_strategy.value,
                "target_utilization": self.target_utilization
            }
            
        except Exception as e:
            self.logger.error(f"Error generating optimization report: {e}")
            return {"error": str(e)}
    
    def cleanup(self):
        """Cleanup GPU-Ressourcen"""
        
        try:
            # Stoppe Optimierung
            self.stop_optimization()
            
            # GPU-Memory cleanup
            if TORCH_AVAILABLE and torch.cuda.is_available():
                for gpu_id in self.available_gpus:
                    with torch.cuda.device(gpu_id):
                        torch.cuda.empty_cache()
            
            self.logger.info("GPU optimization cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")


# Utility-Funktionen für GPU-Optimierung
def create_gpu_workload(workload_type: GPUWorkloadType, 
                       callback: Callable,
                       priority: int = 5,
                       estimated_vram_mb: int = 1024,
                       batch_size: int = 64,
                       **kwargs) -> GPUWorkload:
    """Erstelle GPU-Workload"""
    
    workload_id = f"{workload_type.value}_{int(time.time() * 1000)}"
    
    return GPUWorkload(
        workload_id=workload_id,
        workload_type=workload_type,
        priority=priority,
        estimated_vram_mb=estimated_vram_mb,
        estimated_compute_time=kwargs.get("estimated_compute_time", 1.0),
        batch_size=batch_size,
        callback=callback,
        metadata=kwargs
    )


def get_rtx_5090_optimal_config() -> Dict[str, Any]:
    """Erhalte optimale Konfiguration für RTX 5090"""
    
    return {
        "memory_strategy": "aggressive",
        "target_utilization": 98.0,
        "max_batch_size": 2048,
        "min_batch_size": 64,
        "optimization_interval": 2.0,
        "alert_thresholds": {
            "temperature": {"warning": 80.0, "critical": 90.0},
            "memory_usage": {"warning": 90.0, "critical": 98.0},
            "power_usage": {"warning": 400.0, "critical": 450.0}
        }
    }
    """GPU-Workload-Typen"""
    AI_INFERENCE = "ai_inference"
    AI_TRAINING = "ai_training"
    MATRIX_OPERATIONS = "matrix_operations"
    SIGNAL_PROCESSING = "signal_processing"
    PATTERN_RECOGNITION = "pattern_recognition"
    BATCH_PROCESSING = "batch_processing"


class OptimizationStrategy(Enum):
    """GPU-Optimierungs-Strategien"""
    MAX_THROUGHPUT = "max_throughput"
    MIN_LATENCY = "min_latency"
    BALANCED = "balanced"
    MEMORY_EFFICIENT = "memory_efficient"
    POWER_EFFICIENT = "power_efficient"


@dataclass
class GPUMetrics:
    """GPU-Performance-Metriken"""
    timestamp: datetime
    gpu_id: int
    
    # Utilization
    gpu_utilization: float = 0.0
    memory_utilization: float = 0.0
    
    # Memory
    memory_used: float = 0.0  # GB
    memory_total: float = 0.0  # GB
    memory_free: float = 0.0  # GB
    
    # Performance
    temperature: float = 0.0  # °C
    power_draw: float = 0.0  # Watts
    clock_speed: float = 0.0  # MHz
    memory_clock: float = 0.0  # MHz
    
    # Compute
    compute_processes: int = 0
    active_streams: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "gpu_id": self.gpu_id,
            "gpu_utilization": self.gpu_utilization,
            "memory_utilization": self.memory_utilization,
            "memory_used": self.memory_used,
            "memory_total": self.memory_total,
            "memory_free": self.memory_free,
            "temperature": self.temperature,
            "power_draw": self.power_draw,
            "clock_speed": self.clock_speed,
            "memory_clock": self.memory_clock,
            "compute_processes": self.compute_processes,
            "active_streams": self.active_streams
        }


@dataclass
class OptimizationResult:
    """Ergebnis einer GPU-Optimierung"""
    success: bool
    optimization_type: str
    original_batch_size: int
    optimized_batch_size: int
    performance_improvement: float = 0.0  # Prozent
    memory_efficiency: float = 0.0  # Prozent
    execution_time: float = 0.0
    error: Optional[str] = None


@dataclass
class GPUWorkload:
    """GPU-Workload-Definition"""
    workload_id: str
    workload_type: GPUWorkloadType
    function: Callable
    args: Tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    
    # Resource-Requirements
    min_memory_gb: float = 1.0
    preferred_batch_size: int = 32
    max_batch_size: int = 1024
    
    # Optimization-Preferences
    strategy: OptimizationStrategy = OptimizationStrategy.BALANCED
    priority: int = 1  # 1=niedrig, 5=hoch
    
    created_at: datetime = field(default_factory=datetime.now)


class GPUUtilizationOptimizer:
    """
    GPU-Utilization-Optimizer für RTX 5090
    
    Features:
    - Maximale GPU-Auslastung durch dynamische Batch-Size-Optimierung
    - VRAM-Management für 32GB RTX 5090
    - Multi-GPU-Load-Balancing
    - CUDA-Stream-Optimierung
    - Performance-Auto-Tuning
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # GPU-Detection
        self.gpu_count = self._detect_gpu_count()
        self.gpu_info = self._detect_gpu_info()
        
        # Optimization-Konfiguration
        self.target_gpu_utilization = self.config.get("target_gpu_utilization", 90.0)  # 90%
        self.target_memory_utilization = self.config.get("target_memory_utilization", 85.0)  # 85%
        self.optimization_strategy = OptimizationStrategy(self.config.get("strategy", "balanced"))
        
        # Monitoring
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.metrics_history: deque = deque(maxlen=3600)  # 1 Stunde
        
        # Optimization-State
        self.current_workloads: Dict[str, GPUWorkload] = {}
        self.optimization_history: List[OptimizationResult] = []
        self.optimal_batch_sizes: Dict[str, int] = {}  # Cache für optimale Batch-Sizes
        
        # CUDA-Streams für Parallelisierung
        self.cuda_streams: List[torch.cuda.Stream] = []
        if TORCH_AVAILABLE and torch.cuda.is_available():
            self._setup_cuda_streams()
        
        # Performance-Tracking
        self.stats = {
            "optimizations_performed": 0,
            "avg_gpu_utilization": 0.0,
            "avg_memory_utilization": 0.0,
            "total_performance_improvement": 0.0,
            "batch_size_optimizations": 0,
            "memory_optimizations": 0,
            "stream_optimizations": 0
        }
        
        self.logger.info(f"GPUUtilizationOptimizer initialized: {self.gpu_count} GPUs detected")
        if self.gpu_info:
            for gpu_id, info in self.gpu_info.items():
                self.logger.info(f"  GPU {gpu_id}: {info.get('name', 'Unknown')} ({info.get('memory_gb', 0):.1f}GB)")
    
    def start_monitoring(self):
        """Starte GPU-Monitoring"""
        
        if self.monitoring_active:
            self.logger.warning("GPU monitoring already active")
            return
        
        if not TORCH_AVAILABLE or not torch.cuda.is_available():
            self.logger.error("CUDA not available, cannot start GPU monitoring")
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            name="GPUMonitor",
            daemon=True
        )
        self.monitoring_thread.start()
        
        self.logger.info("GPU monitoring started")
    
    def stop_monitoring(self):
        """Stoppe GPU-Monitoring"""
        
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5.0)
        
        self.logger.info("GPU monitoring stopped")
    
    def optimize_workload(self, workload: GPUWorkload) -> OptimizationResult:
        """
        Optimiere GPU-Workload für maximale Auslastung
        
        Args:
            workload: GPU-Workload zum Optimieren
            
        Returns:
            OptimizationResult mit Optimierungs-Details
        """
        try:
            start_time = datetime.now()
            
            self.logger.info(f"Optimizing workload {workload.workload_id} ({workload.workload_type.value})")
            
            # Aktuelle GPU-Metriken
            current_metrics = self.get_current_gpu_metrics()
            
            # Optimale Batch-Size finden
            optimal_batch_size = self._find_optimal_batch_size(workload, current_metrics)
            
            # Memory-Optimierung
            memory_optimization = self._optimize_memory_usage(workload, current_metrics)
            
            # CUDA-Stream-Optimierung
            stream_optimization = self._optimize_cuda_streams(workload)
            
            # Performance-Verbesserung berechnen
            performance_improvement = self._calculate_performance_improvement(
                workload, optimal_batch_size, current_metrics
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = OptimizationResult(
                success=True,
                optimization_type=f"{workload.workload_type.value}_optimization",
                original_batch_size=workload.preferred_batch_size,
                optimized_batch_size=optimal_batch_size,
                performance_improvement=performance_improvement,
                memory_efficiency=memory_optimization.get("efficiency_improvement", 0.0),
                execution_time=execution_time
            )
            
            # Cache optimale Batch-Size
            self.optimal_batch_sizes[workload.workload_id] = optimal_batch_size
            
            # Statistiken updaten
            self.stats["optimizations_performed"] += 1
            self.stats["total_performance_improvement"] += performance_improvement
            if optimal_batch_size != workload.preferred_batch_size:
                self.stats["batch_size_optimizations"] += 1
            
            self.optimization_history.append(result)
            
            self.logger.info(f"Workload optimization completed: {performance_improvement:.1f}% improvement")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Workload optimization error: {e}")
            return OptimizationResult(
                success=False,
                optimization_type="error",
                original_batch_size=workload.preferred_batch_size,
                optimized_batch_size=workload.preferred_batch_size,
                error=str(e)
            )
    
    def execute_optimized_workload(self, workload: GPUWorkload) -> Any:
        """
        Führe Workload mit GPU-Optimierung aus
        
        Args:
            workload: Auszuführende GPU-Workload
            
        Returns:
            Workload-Ergebnis
        """
        try:
            # Optimierung durchführen
            optimization_result = self.optimize_workload(workload)
            
            if not optimization_result.success:
                self.logger.warning(f"Optimization failed, using original parameters")
                return workload.function(*workload.args, **workload.kwargs)
            
            # Optimierte Parameter anwenden
            optimized_kwargs = workload.kwargs.copy()
            
            # Batch-Size anpassen
            if "batch_size" in optimized_kwargs:
                optimized_kwargs["batch_size"] = optimization_result.optimized_batch_size
            
            # CUDA-Stream zuweisen
            if TORCH_AVAILABLE and self.cuda_streams:
                stream = self._get_optimal_cuda_stream()
                if "stream" not in optimized_kwargs:
                    optimized_kwargs["stream"] = stream
            
            # GPU-Device zuweisen
            optimal_gpu = self._select_optimal_gpu()
            if "device" not in optimized_kwargs:
                optimized_kwargs["device"] = f"cuda:{optimal_gpu}"
            
            # Workload ausführen
            with torch.cuda.device(optimal_gpu):
                result = workload.function(*workload.args, **optimized_kwargs)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Optimized workload execution error: {e}")
            # Fallback: Normale Ausführung
            return workload.function(*workload.args, **workload.kwargs)
    
    def _find_optimal_batch_size(self, workload: GPUWorkload, current_metrics: List[GPUMetrics]) -> int:
        """Finde optimale Batch-Size für Workload"""
        
        try:
            # Prüfe Cache
            if workload.workload_id in self.optimal_batch_sizes:
                cached_size = self.optimal_batch_sizes[workload.workload_id]
                self.logger.debug(f"Using cached batch size: {cached_size}")
                return cached_size
            
            # Verfügbares GPU-Memory
            if current_metrics:
                available_memory = current_metrics[0].memory_free
            else:
                available_memory = 16.0  # Fallback: 16GB
            
            # Batch-Size basierend auf Memory-Requirements
            memory_per_sample = workload.min_memory_gb
            max_memory_batch_size = int(available_memory * 0.8 / memory_per_sample)  # 80% des verfügbaren Memory
            
            # Batch-Size basierend auf Workload-Type
            if workload.workload_type == GPUWorkloadType.AI_INFERENCE:
                # Inference: Kleinere Batches für niedrige Latenz
                optimal_batch_size = min(workload.preferred_batch_size * 2, max_memory_batch_size)
            
            elif workload.workload_type == GPUWorkloadType.AI_TRAINING:
                # Training: Größere Batches für hohen Durchsatz
                optimal_batch_size = min(workload.max_batch_size, max_memory_batch_size)
            
            elif workload.workload_type == GPUWorkloadType.BATCH_PROCESSING:
                # Batch-Processing: Maximale Batch-Size
                optimal_batch_size = max_memory_batch_size
            
            else:
                # Default: Bevorzugte Batch-Size
                optimal_batch_size = min(workload.preferred_batch_size, max_memory_batch_size)
            
            # Sicherheits-Checks
            optimal_batch_size = max(1, min(optimal_batch_size, workload.max_batch_size))
            
            self.logger.debug(f"Optimal batch size calculated: {optimal_batch_size} (memory limit: {max_memory_batch_size})")
            
            return optimal_batch_size
            
        except Exception as e:
            self.logger.error(f"Batch size optimization error: {e}")
            return workload.preferred_batch_size
    
    def _optimize_memory_usage(self, workload: GPUWorkload, current_metrics: List[GPUMetrics]) -> Dict[str, Any]:
        """Optimiere GPU-Memory-Usage"""
        
        optimization_result = {
            "efficiency_improvement": 0.0,
            "recommendations": []
        }
        
        try:
            if not current_metrics:
                return optimization_result
            
            current_memory_usage = current_metrics[0].memory_utilization
            
            # Memory-Optimierungs-Empfehlungen
            if current_memory_usage > 90:
                optimization_result["recommendations"].append("Reduce batch size to prevent OOM")
                optimization_result["efficiency_improvement"] = -10.0
            
            elif current_memory_usage < 50:
                optimization_result["recommendations"].append("Increase batch size to utilize more memory")
                optimization_result["efficiency_improvement"] = 20.0
            
            elif current_memory_usage < 70:
                optimization_result["recommendations"].append("Moderate batch size increase possible")
                optimization_result["efficiency_improvement"] = 10.0
            
            # Memory-Fragmentierung vermeiden
            if workload.workload_type == GPUWorkloadType.AI_TRAINING:
                optimization_result["recommendations"].append("Use gradient checkpointing for large models")
            
            # Mixed Precision für Memory-Einsparung
            optimization_result["recommendations"].append("Consider using mixed precision (FP16) for memory efficiency")
            
            self.stats["memory_optimizations"] += 1
            
        except Exception as e:
            self.logger.error(f"Memory optimization error: {e}")
        
        return optimization_result
    
    def _optimize_cuda_streams(self, workload: GPUWorkload) -> Dict[str, Any]:
        """Optimiere CUDA-Stream-Usage"""
        
        optimization_result = {
            "streams_recommended": 1,
            "parallelization_factor": 1.0
        }
        
        try:
            if not TORCH_AVAILABLE or not self.cuda_streams:
                return optimization_result
            
            # Stream-Anzahl basierend auf Workload-Type
            if workload.workload_type == GPUWorkloadType.AI_INFERENCE:
                # Inference: Mehrere Streams für Parallelisierung
                optimization_result["streams_recommended"] = min(4, len(self.cuda_streams))
                optimization_result["parallelization_factor"] = 2.0
            
            elif workload.workload_type == GPUWorkloadType.BATCH_PROCESSING:
                # Batch-Processing: Maximale Stream-Nutzung
                optimization_result["streams_recommended"] = len(self.cuda_streams)
                optimization_result["parallelization_factor"] = 3.0
            
            elif workload.workload_type == GPUWorkloadType.MATRIX_OPERATIONS:
                # Matrix-Ops: Moderate Stream-Nutzung
                optimization_result["streams_recommended"] = 2
                optimization_result["parallelization_factor"] = 1.5
            
            self.stats["stream_optimizations"] += 1
            
        except Exception as e:
            self.logger.error(f"CUDA stream optimization error: {e}")
        
        return optimization_result
    
    def _calculate_performance_improvement(
        self, 
        workload: GPUWorkload, 
        optimal_batch_size: int, 
        current_metrics: List[GPUMetrics]
    ) -> float:
        """Berechne geschätzte Performance-Verbesserung"""
        
        try:
            improvement = 0.0
            
            # Batch-Size-Verbesserung
            batch_size_ratio = optimal_batch_size / workload.preferred_batch_size
            if batch_size_ratio > 1.0:
                improvement += (batch_size_ratio - 1.0) * 30.0  # Bis zu 30% durch größere Batches
            
            # GPU-Utilization-Verbesserung
            if current_metrics:
                current_utilization = current_metrics[0].gpu_utilization
                if current_utilization < self.target_gpu_utilization:
                    utilization_gap = self.target_gpu_utilization - current_utilization
                    improvement += utilization_gap * 0.5  # 0.5% Verbesserung pro % Utilization
            
            # Workload-Type-spezifische Verbesserungen
            if workload.workload_type == GPUWorkloadType.AI_TRAINING:
                improvement += 10.0  # Training profitiert stark von Optimierung
            elif workload.workload_type == GPUWorkloadType.BATCH_PROCESSING:
                improvement += 15.0  # Batch-Processing hat hohes Optimierungs-Potenzial
            
            # Strategy-basierte Anpassungen
            if self.optimization_strategy == OptimizationStrategy.MAX_THROUGHPUT:
                improvement *= 1.2  # 20% Bonus für Durchsatz-Optimierung
            elif self.optimization_strategy == OptimizationStrategy.MIN_LATENCY:
                improvement *= 0.8  # Latenz-Optimierung reduziert Durchsatz-Gains
            
            return min(improvement, 100.0)  # Max 100% Verbesserung
            
        except Exception as e:
            self.logger.error(f"Performance improvement calculation error: {e}")
            return 0.0
    
    def _setup_cuda_streams(self):
        """Setup CUDA-Streams für Parallelisierung"""
        
        try:
            if not TORCH_AVAILABLE or not torch.cuda.is_available():
                return
            
            # Erstelle mehrere CUDA-Streams
            stream_count = min(8, self.gpu_count * 4)  # 4 Streams pro GPU
            
            for i in range(stream_count):
                stream = torch.cuda.Stream()
                self.cuda_streams.append(stream)
            
            self.logger.info(f"Created {len(self.cuda_streams)} CUDA streams")
            
        except Exception as e:
            self.logger.error(f"CUDA stream setup error: {e}")
    
    def _get_optimal_cuda_stream(self) -> Optional[torch.cuda.Stream]:
        """Erhalte optimalen CUDA-Stream"""
        
        if not self.cuda_streams:
            return None
        
        # Einfache Round-Robin-Auswahl
        # In einer echten Implementierung würde man die Stream-Auslastung prüfen
        stream_index = len(self.optimization_history) % len(self.cuda_streams)
        return self.cuda_streams[stream_index]
    
    def _select_optimal_gpu(self) -> int:
        """Wähle optimale GPU für Workload"""
        
        try:
            if self.gpu_count <= 1:
                return 0
            
            # Erhalte aktuelle GPU-Metriken
            current_metrics = self.get_current_gpu_metrics()
            
            if not current_metrics:
                return 0
            
            # Wähle GPU mit niedrigster Auslastung
            optimal_gpu = min(
                current_metrics,
                key=lambda m: m.gpu_utilization + m.memory_utilization
            )
            
            return optimal_gpu.gpu_id
            
        except Exception as e:
            self.logger.error(f"GPU selection error: {e}")
            return 0
    
    def _monitoring_loop(self):
        """GPU-Monitoring-Loop"""
        
        while self.monitoring_active:
            try:
                # GPU-Metriken sammeln
                metrics = self.get_current_gpu_metrics()
                
                for metric in metrics:
                    self.metrics_history.append(metric)
                
                # Statistiken updaten
                self._update_monitoring_stats(metrics)
                
                # Auto-Optimierung (falls aktiviert)
                if self.config.get("auto_optimization", False):
                    self._auto_optimize_based_on_metrics(metrics)
                
                time.sleep(1.0)  # 1 Sekunde Intervall
                
            except Exception as e:
                self.logger.error(f"GPU monitoring error: {e}")
                time.sleep(1.0)
    
    def _update_monitoring_stats(self, metrics: List[GPUMetrics]):
        """Update Monitoring-Statistiken"""
        
        if not metrics:
            return
        
        try:
            # Durchschnittliche GPU-Utilization
            avg_gpu_util = np.mean([m.gpu_utilization for m in metrics])
            avg_memory_util = np.mean([m.memory_utilization for m in metrics])
            
            # Gleitender Durchschnitt
            alpha = 0.1  # Smoothing-Faktor
            self.stats["avg_gpu_utilization"] = (
                (1 - alpha) * self.stats["avg_gpu_utilization"] + alpha * avg_gpu_util
            )
            self.stats["avg_memory_utilization"] = (
                (1 - alpha) * self.stats["avg_memory_utilization"] + alpha * avg_memory_util
            )
            
        except Exception as e:
            self.logger.debug(f"Stats update error: {e}")
    
    def _auto_optimize_based_on_metrics(self, metrics: List[GPUMetrics]):
        """Automatische Optimierung basierend auf Metriken"""
        
        try:
            for metric in metrics:
                # Niedrige GPU-Utilization
                if metric.gpu_utilization < 50:
                    self.logger.info(f"GPU {metric.gpu_id} underutilized ({metric.gpu_utilization:.1f}%)")
                
                # Hohe Memory-Utilization
                if metric.memory_utilization > 90:
                    self.logger.warning(f"GPU {metric.gpu_id} memory critical ({metric.memory_utilization:.1f}%)")
                
                # Hohe Temperatur
                if metric.temperature > 80:
                    self.logger.warning(f"GPU {metric.gpu_id} temperature high ({metric.temperature:.1f}°C)")
                
        except Exception as e:
            self.logger.debug(f"Auto-optimization error: {e}")
    
    def get_current_gpu_metrics(self) -> List[GPUMetrics]:
        """Erhalte aktuelle GPU-Metriken"""
        
        metrics = []
        
        try:
            if not PYNVML_AVAILABLE:
                return metrics
            
            device_count = pynvml.nvmlDeviceGetCount()
            
            for gpu_id in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_id)
                
                # Utilization
                try:
                    utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    gpu_util = utilization.gpu
                    memory_util = utilization.memory
                except:
                    gpu_util = 0.0
                    memory_util = 0.0
                
                # Memory Info
                try:
                    memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    memory_used = memory_info.used / (1024**3)  # GB
                    memory_total = memory_info.total / (1024**3)  # GB
                    memory_free = memory_info.free / (1024**3)  # GB
                    memory_utilization = (memory_info.used / memory_info.total) * 100
                except:
                    memory_used = memory_total = memory_free = 0.0
                    memory_utilization = 0.0
                
                # Temperature
                try:
                    temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                except:
                    temperature = 0.0
                
                # Power Draw
                try:
                    power_draw = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # Watt
                except:
                    power_draw = 0.0
                
                # Clock Speeds
                try:
                    clock_speed = pynvml.nvmlDeviceGetClockInfo(handle, pynvml.NVML_CLOCK_GRAPHICS)
                    memory_clock = pynvml.nvmlDeviceGetClockInfo(handle, pynvml.NVML_CLOCK_MEM)
                except:
                    clock_speed = memory_clock = 0.0
                
                # Compute Processes
                try:
                    processes = pynvml.nvmlDeviceGetComputeRunningProcesses(handle)
                    compute_processes = len(processes)
                except:
                    compute_processes = 0
                
                metric = GPUMetrics(
                    timestamp=datetime.now(),
                    gpu_id=gpu_id,
                    gpu_utilization=gpu_util,
                    memory_utilization=memory_utilization,
                    memory_used=memory_used,
                    memory_total=memory_total,
                    memory_free=memory_free,
                    temperature=temperature,
                    power_draw=power_draw,
                    clock_speed=clock_speed,
                    memory_clock=memory_clock,
                    compute_processes=compute_processes,
                    active_streams=len(self.cuda_streams)
                )
                
                metrics.append(metric)
        
        except Exception as e:
            self.logger.error(f"GPU metrics collection error: {e}")
        
        return metrics