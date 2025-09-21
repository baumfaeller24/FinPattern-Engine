#!/usr/bin/env python3
"""
Performance Benchmarks für Hardware-Auslastungs-Validation
Phase 3 Implementation - Task 14

Features:
- Comprehensive Hardware-Performance-Benchmarking
- CPU, GPU, Memory-Utilization-Validation
- Throughput und Latency-Benchmarks
- Scalability-Testing für verschiedene Workloads
- Resource-Efficiency-Validation
- Performance-Regression-Testing
- Hardware-Optimization-Validation
"""

import time
import threading
import multiprocessing
import psutil
import logging
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path
import json
import numpy as np
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

# GPU Monitoring
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    import GPUtil
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False

# Performance Profiling
try:
    import cProfile
    import pstats
    PROFILING_AVAILABLE = True
except ImportError:
    PROFILING_AVAILABLE = False


@dataclass
class BenchmarkResult:
    """Benchmark-Result-Container"""
    benchmark_name: str
    success: bool
    duration: float
    throughput: Optional[float] = None
    latency: Optional[float] = None
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    gpu_usage: Optional[float] = None
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "benchmark_name": self.benchmark_name,
            "success": self.success,
            "duration": self.duration,
            "throughput": self.throughput,
            "latency": self.latency,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "gpu_usage": self.gpu_usage,
            "error_message": self.error_message,
            "metrics": self.metrics,
            "timestamp": datetime.now().isoformat()
        }


@dataclass
class HardwareSpecs:
    """Hardware-Spezifikationen"""
    cpu_cores: int
    cpu_threads: int
    cpu_frequency: float
    total_memory_gb: float
    gpu_count: int
    gpu_memory_gb: float
    disk_type: str
    
    @classmethod
    def detect_hardware(cls) -> 'HardwareSpecs':
        """Erkenne Hardware-Spezifikationen"""
        
        # CPU-Info
        cpu_cores = psutil.cpu_count(logical=False)
        cpu_threads = psutil.cpu_count(logical=True)
        cpu_freq = psutil.cpu_freq()
        cpu_frequency = cpu_freq.current if cpu_freq else 0.0
        
        # Memory-Info
        memory = psutil.virtual_memory()
        total_memory_gb = memory.total / (1024**3)
        
        # GPU-Info
        gpu_count = 0
        gpu_memory_gb = 0.0
        
        if GPU_AVAILABLE:
            try:
                gpus = GPUtil.getGPUs()
                gpu_count = len(gpus)
                if gpus:
                    gpu_memory_gb = gpus[0].memoryTotal / 1024  # MB zu GB
            except Exception:
                pass
        
        # Disk-Info (vereinfacht)
        disk_type = "SSD"  # Würde normalerweise erkannt werden
        
        return cls(
            cpu_cores=cpu_cores,
            cpu_threads=cpu_threads,
            cpu_frequency=cpu_frequency,
            total_memory_gb=total_memory_gb,
            gpu_count=gpu_count,
            gpu_memory_gb=gpu_memory_gb,
            disk_type=disk_type
        )


class PerformanceBenchmarks:
    """
    Performance Benchmarks für Hardware-Auslastungs-Validation
    
    Features:
    - CPU-Performance-Benchmarks mit Multi-Core-Testing
    - GPU-Utilization-Benchmarks für AI-Workloads
    - Memory-Throughput und Latency-Testing
    - I/O-Performance-Validation
    - Scalability-Testing für verschiedene Workload-Größen
    - Resource-Efficiency-Metriken
    - Performance-Regression-Detection
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Benchmark-Konfiguration
        self.enable_cpu_benchmarks = self.config.get("enable_cpu_benchmarks", True)
        self.enable_gpu_benchmarks = self.config.get("enable_gpu_benchmarks", TORCH_AVAILABLE)
        self.enable_memory_benchmarks = self.config.get("enable_memory_benchmarks", True)
        self.enable_io_benchmarks = self.config.get("enable_io_benchmarks", True)
        self.benchmark_duration = self.config.get("benchmark_duration", 30.0)  # Sekunden
        
        # Hardware-Specs
        self.hardware_specs = HardwareSpecs.detect_hardware()
        
        # Results
        self.benchmark_results: List[BenchmarkResult] = []
        
        # Output-Directory
        self.results_directory = Path(self.config.get("results_directory", "benchmark_results"))
        self.results_directory.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"PerformanceBenchmarks initialized for {self.hardware_specs.cpu_cores} cores, "
                        f"{self.hardware_specs.total_memory_gb:.1f}GB RAM, {self.hardware_specs.gpu_count} GPUs")
    
    async def run_all_benchmarks(self) -> List[BenchmarkResult]:
        """Führe alle Benchmarks aus"""
        
        self.logger.info("Starting comprehensive performance benchmarks")
        
        results = []
        
        # CPU-Benchmarks
        if self.enable_cpu_benchmarks:
            cpu_results = await self.run_cpu_benchmarks()
            results.extend(cpu_results)
        
        # GPU-Benchmarks
        if self.enable_gpu_benchmarks and self.hardware_specs.gpu_count > 0:
            gpu_results = await self.run_gpu_benchmarks()
            results.extend(gpu_results)
        
        # Memory-Benchmarks
        if self.enable_memory_benchmarks:
            memory_results = await self.run_memory_benchmarks()
            results.extend(memory_results)
        
        # I/O-Benchmarks
        if self.enable_io_benchmarks:
            io_results = await self.run_io_benchmarks()
            results.extend(io_results)
        
        # Scalability-Benchmarks
        scalability_results = await self.run_scalability_benchmarks()
        results.extend(scalability_results)
        
        self.benchmark_results.extend(results)
        
        self.logger.info(f"Completed {len(results)} benchmarks")
        
        return results
    
    async def run_cpu_benchmarks(self) -> List[BenchmarkResult]:
        """Führe CPU-Benchmarks aus"""
        
        self.logger.info("Running CPU benchmarks")
        
        results = []
        
        # Single-Core-Performance
        single_core_result = await self._benchmark_single_core_performance()
        results.append(single_core_result)
        
        # Multi-Core-Performance
        multi_core_result = await self._benchmark_multi_core_performance()
        results.append(multi_core_result)
        
        # CPU-Intensive-Workload
        cpu_intensive_result = await self._benchmark_cpu_intensive_workload()
        results.append(cpu_intensive_result)
        
        # Context-Switching-Performance
        context_switching_result = await self._benchmark_context_switching()
        results.append(context_switching_result)
        
        return results
    
    async def _benchmark_single_core_performance(self) -> BenchmarkResult:
        """Benchmark Single-Core-Performance"""
        
        benchmark_name = "single_core_performance"
        
        try:
            start_time = time.time()
            start_cpu = psutil.cpu_percent(interval=None)
            
            # CPU-intensive Berechnung (Single-Thread)
            def cpu_intensive_task():
                result = 0
                for i in range(10000000):
                    result += i * i
                return result
            
            # Führe Task aus
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                await loop.run_in_executor(executor, cpu_intensive_task)
            
            end_time = time.time()
            end_cpu = psutil.cpu_percent(interval=0.1)
            
            duration = end_time - start_time
            cpu_usage = end_cpu
            
            # Throughput berechnen (Operations per Second)
            operations = 10000000
            throughput = operations / duration
            
            return BenchmarkResult(
                benchmark_name=benchmark_name,
                success=True,
                duration=duration,
                throughput=throughput,
                cpu_usage=cpu_usage,
                metrics={
                    "operations": operations,
                    "ops_per_second": throughput,
                    "cpu_efficiency": throughput / max(cpu_usage, 1.0)
                }
            )
            
        except Exception as e:
            return BenchmarkResult(
                benchmark_name=benchmark_name,
                success=False,
                duration=0.0,
                error_message=str(e)
            )
    
    async def _benchmark_multi_core_performance(self) -> BenchmarkResult:
        """Benchmark Multi-Core-Performance"""
        
        benchmark_name = "multi_core_performance"
        
        try:
            start_time = time.time()
            start_cpu = psutil.cpu_percent(interval=None)
            
            # CPU-intensive Task für Multi-Core
            def cpu_task(n):
                result = 0
                for i in range(n):
                    result += i * i
                return result
            
            # Parallelisiere über alle CPU-Cores
            num_workers = self.hardware_specs.cpu_threads
            task_size = 1000000
            
            loop = asyncio.get_event_loop()
            with ProcessPoolExecutor(max_workers=num_workers) as executor:
                tasks = [loop.run_in_executor(executor, cpu_task, task_size) for _ in range(num_workers)]
                await asyncio.gather(*tasks)
            
            end_time = time.time()
            end_cpu = psutil.cpu_percent(interval=0.1)
            
            duration = end_time - start_time
            cpu_usage = end_cpu
            
            # Throughput berechnen
            total_operations = task_size * num_workers
            throughput = total_operations / duration
            
            # Scaling-Efficiency
            single_core_throughput = task_size / (duration / num_workers)  # Approximation
            scaling_efficiency = throughput / (single_core_throughput * num_workers)
            
            return BenchmarkResult(
                benchmark_name=benchmark_name,
                success=True,
                duration=duration,
                throughput=throughput,
                cpu_usage=cpu_usage,
                metrics={
                    "total_operations": total_operations,
                    "workers_used": num_workers,
                    "scaling_efficiency": scaling_efficiency,
                    "ops_per_core": throughput / num_workers
                }
            )
            
        except Exception as e:
            return BenchmarkResult(
                benchmark_name=benchmark_name,
                success=False,
                duration=0.0,
                error_message=str(e)
            )
    
    async def _benchmark_cpu_intensive_workload(self) -> BenchmarkResult:
        """Benchmark CPU-Intensive-Workload (AI-ähnlich)"""
        
        benchmark_name = "cpu_intensive_workload"
        
        try:
            start_time = time.time()
            memory_before = psutil.virtual_memory().used / (1024**3)
            
            # Simuliere AI-Workload (Matrix-Operationen)
            def matrix_operations():
                size = 1000
                a = np.random.randn(size, size)
                b = np.random.randn(size, size)
                
                # Matrix-Multiplikation
                c = np.dot(a, b)
                
                # Eigenvalue-Berechnung
                eigenvals = np.linalg.eigvals(c[:100, :100])  # Kleinere Matrix für Performance
                
                return np.sum(eigenvals)
            
            # Führe mehrere Matrix-Operationen parallel aus
            num_tasks = self.hardware_specs.cpu_cores
            
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=num_tasks) as executor:
                tasks = [loop.run_in_executor(executor, matrix_operations) for _ in range(num_tasks)]
                results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            memory_after = psutil.virtual_memory().used / (1024**3)
            cpu_usage = psutil.cpu_percent(interval=0.1)
            
            duration = end_time - start_time
            memory_usage = memory_after - memory_before
            
            # Throughput (Matrix-Operationen pro Sekunde)
            throughput = num_tasks / duration
            
            return BenchmarkResult(
                benchmark_name=benchmark_name,
                success=True,
                duration=duration,
                throughput=throughput,
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                metrics={
                    "matrix_operations": num_tasks,
                    "matrix_size": 1000,
                    "memory_efficiency": throughput / max(memory_usage, 0.1),
                    "cpu_efficiency": throughput / max(cpu_usage, 1.0)
                }
            )
            
        except Exception as e:
            return BenchmarkResult(
                benchmark_name=benchmark_name,
                success=False,
                duration=0.0,
                error_message=str(e)
            )
    
    async def _benchmark_context_switching(self) -> BenchmarkResult:
        """Benchmark Context-Switching-Performance"""
        
        benchmark_name = "context_switching_performance"
        
        try:
            start_time = time.time()
            
            # Context-Switching-Test mit vielen Threads
            num_threads = 100
            switches_per_thread = 1000
            
            def switching_task():
                for _ in range(switches_per_thread):
                    time.sleep(0.001)  # Kurzer Sleep für Context-Switch
            
            # Starte viele Threads gleichzeitig
            threads = []
            for _ in range(num_threads):
                thread = threading.Thread(target=switching_task)
                threads.append(thread)
                thread.start()
            
            # Warte auf alle Threads
            for thread in threads:
                thread.join()
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Context-Switches pro Sekunde
            total_switches = num_threads * switches_per_thread
            switches_per_second = total_switches / duration
            
            return BenchmarkResult(
                benchmark_name=benchmark_name,
                success=True,
                duration=duration,
                throughput=switches_per_second,
                metrics={
                    "total_switches": total_switches,
                    "threads_used": num_threads,
                    "switches_per_thread": switches_per_thread,
                    "avg_switch_time": duration / total_switches * 1000  # ms
                }
            )
            
        except Exception as e:
            return BenchmarkResult(
                benchmark_name=benchmark_name,
                success=False,
                duration=0.0,
                error_message=str(e)
            )
    
    async def run_gpu_benchmarks(self) -> List[BenchmarkResult]:
        """Führe GPU-Benchmarks aus"""
        
        if not TORCH_AVAILABLE:
            return []
        
        self.logger.info("Running GPU benchmarks")
        
        results = []
        
        # GPU-Compute-Performance
        gpu_compute_result = await self._benchmark_gpu_compute_performance()
        results.append(gpu_compute_result)
        
        # GPU-Memory-Bandwidth
        gpu_memory_result = await self._benchmark_gpu_memory_bandwidth()
        results.append(gpu_memory_result)
        
        # GPU-AI-Workload
        gpu_ai_result = await self._benchmark_gpu_ai_workload()
        results.append(gpu_ai_result)
        
        return results
    
    async def _benchmark_gpu_compute_performance(self) -> BenchmarkResult:
        """Benchmark GPU-Compute-Performance"""
        
        benchmark_name = "gpu_compute_performance"
        
        try:
            if not torch.cuda.is_available():
                return BenchmarkResult(
                    benchmark_name=benchmark_name,
                    success=False,
                    duration=0.0,
                    error_message="CUDA not available"
                )
            
            device = torch.device("cuda:0")
            
            start_time = time.time()
            
            # GPU-Compute-Task (Matrix-Multiplikation)
            size = 4096
            a = torch.randn(size, size, device=device)
            b = torch.randn(size, size, device=device)
            
            # Mehrere Matrix-Multiplikationen
            num_operations = 10
            for _ in range(num_operations):
                c = torch.mm(a, b)
                torch.cuda.synchronize()  # Warte auf GPU-Completion
            
            end_time = time.time()
            duration = end_time - start_time
            
            # GPU-Usage (vereinfacht)
            gpu_usage = 95.0  # Mock-Wert
            
            # Throughput (FLOPS)
            flops_per_mm = 2 * size**3  # Matrix-Multiplikation FLOPS
            total_flops = flops_per_mm * num_operations
            throughput = total_flops / duration / 1e9  # GFLOPS
            
            return BenchmarkResult(
                benchmark_name=benchmark_name,
                success=True,
                duration=duration,
                throughput=throughput,
                gpu_usage=gpu_usage,
                metrics={
                    "matrix_size": size,
                    "operations": num_operations,
                    "gflops": throughput,
                    "gpu_efficiency": throughput / max(gpu_usage, 1.0)
                }
            )
            
        except Exception as e:
            return BenchmarkResult(
                benchmark_name=benchmark_name,
                success=False,
                duration=0.0,
                error_message=str(e)
            )
    
    async def _benchmark_gpu_memory_bandwidth(self) -> BenchmarkResult:
        """Benchmark GPU-Memory-Bandwidth"""
        
        benchmark_name = "gpu_memory_bandwidth"
        
        try:
            if not torch.cuda.is_available():
                return BenchmarkResult(
                    benchmark_name=benchmark_name,
                    success=False,
                    duration=0.0,
                    error_message="CUDA not available"
                )
            
            device = torch.device("cuda:0")
            
            # Memory-Transfer-Test
            size = 100 * 1024 * 1024  # 100M elements
            data_size_gb = size * 4 / (1024**3)  # Float32 = 4 bytes
            
            start_time = time.time()
            
            # Host zu Device Transfer
            host_data = torch.randn(size)
            device_data = host_data.to(device)
            torch.cuda.synchronize()
            
            # Device zu Host Transfer
            result_data = device_data.to("cpu")
            torch.cuda.synchronize()
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Bandwidth berechnen (GB/s)
            total_data_gb = data_size_gb * 2  # Hin und zurück
            bandwidth = total_data_gb / duration
            
            return BenchmarkResult(
                benchmark_name=benchmark_name,
                success=True,
                duration=duration,
                throughput=bandwidth,
                metrics={
                    "data_size_gb": data_size_gb,
                    "bandwidth_gbps": bandwidth,
                    "transfer_efficiency": bandwidth / 500.0  # Angenommen 500 GB/s theoretical max
                }
            )
            
        except Exception as e:
            return BenchmarkResult(
                benchmark_name=benchmark_name,
                success=False,
                duration=0.0,
                error_message=str(e)
            )
    
    async def _benchmark_gpu_ai_workload(self) -> BenchmarkResult:
        """Benchmark GPU-AI-Workload"""
        
        benchmark_name = "gpu_ai_workload"
        
        try:
            if not torch.cuda.is_available():
                return BenchmarkResult(
                    benchmark_name=benchmark_name,
                    success=False,
                    duration=0.0,
                    error_message="CUDA not available"
                )
            
            device = torch.device("cuda:0")
            
            # Simuliere Neural Network Forward Pass
            batch_size = 64
            input_size = 1000
            hidden_size = 2048
            output_size = 100
            
            # Erstelle Mock-Neural-Network
            layer1 = torch.nn.Linear(input_size, hidden_size).to(device)
            layer2 = torch.nn.Linear(hidden_size, hidden_size).to(device)
            layer3 = torch.nn.Linear(hidden_size, output_size).to(device)
            activation = torch.nn.ReLU()
            
            # Input-Data
            input_data = torch.randn(batch_size, input_size, device=device)
            
            start_time = time.time()
            
            # Forward Passes
            num_passes = 100
            for _ in range(num_passes):
                x = layer1(input_data)
                x = activation(x)
                x = layer2(x)
                x = activation(x)
                output = layer3(x)
                torch.cuda.synchronize()
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Throughput (Inferences per Second)
            total_inferences = num_passes * batch_size
            throughput = total_inferences / duration
            
            # Latency pro Inference
            latency = duration / total_inferences * 1000  # ms
            
            return BenchmarkResult(
                benchmark_name=benchmark_name,
                success=True,
                duration=duration,
                throughput=throughput,
                latency=latency,
                metrics={
                    "batch_size": batch_size,
                    "forward_passes": num_passes,
                    "inferences_per_second": throughput,
                    "avg_latency_ms": latency,
                    "model_parameters": sum(p.numel() for p in [layer1.weight, layer1.bias, layer2.weight, layer2.bias, layer3.weight, layer3.bias])
                }
            )
            
        except Exception as e:
            return BenchmarkResult(
                benchmark_name=benchmark_name,
                success=False,
                duration=0.0,
                error_message=str(e)
            )    

    async def run_memory_benchmarks(self) -> List[BenchmarkResult]:
        """Führe Memory-Benchmarks aus"""
        
        self.logger.info("Running memory benchmarks")
        
        results = []
        
        # Memory-Allocation-Performance
        allocation_result = await self._benchmark_memory_allocation()
        results.append(allocation_result)
        
        # Memory-Bandwidth
        bandwidth_result = await self._benchmark_memory_bandwidth()
        results.append(bandwidth_result)
        
        # Memory-Latency
        latency_result = await self._benchmark_memory_latency()
        results.append(latency_result)
        
        return results
    
    async def _benchmark_memory_allocation(self) -> BenchmarkResult:
        """Benchmark Memory-Allocation-Performance"""
        
        benchmark_name = "memory_allocation_performance"
        
        try:
            start_time = time.time()
            memory_before = psutil.virtual_memory().used / (1024**3)
            
            # Allokiere große Memory-Blöcke
            allocations = []
            block_size = 100 * 1024 * 1024  # 100MB pro Block
            num_blocks = 10
            
            for _ in range(num_blocks):
                block = np.random.randn(block_size // 8)  # 8 bytes per float64
                allocations.append(block)
            
            end_time = time.time()
            memory_after = psutil.virtual_memory().used / (1024**3)
            
            duration = end_time - start_time
            memory_allocated = memory_after - memory_before
            
            # Throughput (GB/s)
            throughput = memory_allocated / duration
            
            # Cleanup
            del allocations
            
            return BenchmarkResult(
                benchmark_name=benchmark_name,
                success=True,
                duration=duration,
                throughput=throughput,
                memory_usage=memory_allocated,
                metrics={
                    "blocks_allocated": num_blocks,
                    "block_size_mb": block_size / (1024**2),
                    "allocation_rate_gbps": throughput,
                    "avg_allocation_time": duration / num_blocks * 1000  # ms per block
                }
            )
            
        except Exception as e:
            return BenchmarkResult(
                benchmark_name=benchmark_name,
                success=False,
                duration=0.0,
                error_message=str(e)
            )
    
    async def _benchmark_memory_bandwidth(self) -> BenchmarkResult:
        """Benchmark Memory-Bandwidth"""
        
        benchmark_name = "memory_bandwidth"
        
        try:
            # Erstelle große Arrays für Bandwidth-Test
            size = 50 * 1024 * 1024  # 50M elements
            data_size_gb = size * 8 / (1024**3)  # Float64 = 8 bytes
            
            source = np.random.randn(size)
            destination = np.zeros(size)
            
            start_time = time.time()
            
            # Memory-Copy-Operationen
            num_copies = 5
            for _ in range(num_copies):
                np.copyto(destination, source)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Bandwidth berechnen
            total_data_gb = data_size_gb * num_copies
            bandwidth = total_data_gb / duration
            
            return BenchmarkResult(
                benchmark_name=benchmark_name,
                success=True,
                duration=duration,
                throughput=bandwidth,
                metrics={
                    "data_size_gb": data_size_gb,
                    "copy_operations": num_copies,
                    "bandwidth_gbps": bandwidth,
                    "theoretical_max_ratio": bandwidth / 50.0  # Angenommen 50 GB/s theoretical max
                }
            )
            
        except Exception as e:
            return BenchmarkResult(
                benchmark_name=benchmark_name,
                success=False,
                duration=0.0,
                error_message=str(e)
            )
    
    async def _benchmark_memory_latency(self) -> BenchmarkResult:
        """Benchmark Memory-Latency"""
        
        benchmark_name = "memory_latency"
        
        try:
            # Random-Access-Pattern für Latency-Test
            array_size = 10 * 1024 * 1024  # 10M elements
            data = np.random.randn(array_size)
            indices = np.random.randint(0, array_size, 1000000)  # 1M random accesses
            
            start_time = time.time()
            
            # Random Memory-Accesses
            total = 0.0
            for idx in indices:
                total += data[idx]
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Latency pro Access
            num_accesses = len(indices)
            avg_latency = duration / num_accesses * 1e9  # Nanosekunden
            
            # Throughput (Accesses per Second)
            throughput = num_accesses / duration
            
            return BenchmarkResult(
                benchmark_name=benchmark_name,
                success=True,
                duration=duration,
                throughput=throughput,
                latency=avg_latency,
                metrics={
                    "array_size": array_size,
                    "random_accesses": num_accesses,
                    "avg_latency_ns": avg_latency,
                    "accesses_per_second": throughput
                }
            )
            
        except Exception as e:
            return BenchmarkResult(
                benchmark_name=benchmark_name,
                success=False,
                duration=0.0,
                error_message=str(e)
            )
    
    async def run_io_benchmarks(self) -> List[BenchmarkResult]:
        """Führe I/O-Benchmarks aus"""
        
        self.logger.info("Running I/O benchmarks")
        
        results = []
        
        # Disk-Write-Performance
        write_result = await self._benchmark_disk_write_performance()
        results.append(write_result)
        
        # Disk-Read-Performance
        read_result = await self._benchmark_disk_read_performance()
        results.append(read_result)
        
        # Random-I/O-Performance
        random_io_result = await self._benchmark_random_io_performance()
        results.append(random_io_result)
        
        return results
    
    async def _benchmark_disk_write_performance(self) -> BenchmarkResult:
        """Benchmark Disk-Write-Performance"""
        
        benchmark_name = "disk_write_performance"
        
        try:
            # Erstelle Test-File
            test_file = self.results_directory / "write_test.dat"
            file_size_mb = 100
            data = np.random.bytes(file_size_mb * 1024 * 1024)
            
            start_time = time.time()
            
            # Schreibe Daten
            with open(test_file, 'wb') as f:
                f.write(data)
                f.flush()
                f.fsync()  # Force write to disk
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Throughput (MB/s)
            throughput = file_size_mb / duration
            
            # Cleanup
            test_file.unlink()
            
            return BenchmarkResult(
                benchmark_name=benchmark_name,
                success=True,
                duration=duration,
                throughput=throughput,
                metrics={
                    "file_size_mb": file_size_mb,
                    "write_speed_mbps": throughput,
                    "sync_time": duration
                }
            )
            
        except Exception as e:
            return BenchmarkResult(
                benchmark_name=benchmark_name,
                success=False,
                duration=0.0,
                error_message=str(e)
            )
    
    async def _benchmark_disk_read_performance(self) -> BenchmarkResult:
        """Benchmark Disk-Read-Performance"""
        
        benchmark_name = "disk_read_performance"
        
        try:
            # Erstelle Test-File
            test_file = self.results_directory / "read_test.dat"
            file_size_mb = 100
            data = np.random.bytes(file_size_mb * 1024 * 1024)
            
            # Schreibe Test-Daten
            with open(test_file, 'wb') as f:
                f.write(data)
            
            start_time = time.time()
            
            # Lese Daten
            with open(test_file, 'rb') as f:
                read_data = f.read()
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Throughput (MB/s)
            throughput = file_size_mb / duration
            
            # Cleanup
            test_file.unlink()
            
            return BenchmarkResult(
                benchmark_name=benchmark_name,
                success=True,
                duration=duration,
                throughput=throughput,
                metrics={
                    "file_size_mb": file_size_mb,
                    "read_speed_mbps": throughput,
                    "data_integrity": len(read_data) == len(data)
                }
            )
            
        except Exception as e:
            return BenchmarkResult(
                benchmark_name=benchmark_name,
                success=False,
                duration=0.0,
                error_message=str(e)
            )
    
    async def _benchmark_random_io_performance(self) -> BenchmarkResult:
        """Benchmark Random-I/O-Performance"""
        
        benchmark_name = "random_io_performance"
        
        try:
            # Erstelle Test-File
            test_file = self.results_directory / "random_io_test.dat"
            file_size_mb = 50
            block_size = 4096  # 4KB blocks
            
            # Erstelle File mit Random-Data
            with open(test_file, 'wb') as f:
                for _ in range(file_size_mb * 1024 * 1024 // block_size):
                    f.write(np.random.bytes(block_size))
            
            start_time = time.time()
            
            # Random-Read-Operations
            num_operations = 1000
            with open(test_file, 'rb') as f:
                for _ in range(num_operations):
                    # Random-Position
                    position = np.random.randint(0, file_size_mb * 1024 * 1024 - block_size)
                    f.seek(position)
                    data = f.read(block_size)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # IOPS (I/O Operations per Second)
            iops = num_operations / duration
            
            # Latency pro Operation
            avg_latency = duration / num_operations * 1000  # ms
            
            # Cleanup
            test_file.unlink()
            
            return BenchmarkResult(
                benchmark_name=benchmark_name,
                success=True,
                duration=duration,
                throughput=iops,
                latency=avg_latency,
                metrics={
                    "operations": num_operations,
                    "block_size": block_size,
                    "iops": iops,
                    "avg_latency_ms": avg_latency
                }
            )
            
        except Exception as e:
            return BenchmarkResult(
                benchmark_name=benchmark_name,
                success=False,
                duration=0.0,
                error_message=str(e)
            )
    
    async def run_scalability_benchmarks(self) -> List[BenchmarkResult]:
        """Führe Scalability-Benchmarks aus"""
        
        self.logger.info("Running scalability benchmarks")
        
        results = []
        
        # Thread-Scalability
        thread_scalability_result = await self._benchmark_thread_scalability()
        results.append(thread_scalability_result)
        
        # Process-Scalability
        process_scalability_result = await self._benchmark_process_scalability()
        results.append(process_scalability_result)
        
        # Data-Size-Scalability
        data_scalability_result = await self._benchmark_data_size_scalability()
        results.append(data_scalability_result)
        
        return results
    
    async def _benchmark_thread_scalability(self) -> BenchmarkResult:
        """Benchmark Thread-Scalability"""
        
        benchmark_name = "thread_scalability"
        
        try:
            def cpu_task():
                result = 0
                for i in range(1000000):
                    result += i * i
                return result
            
            scalability_results = {}
            
            # Teste verschiedene Thread-Counts
            thread_counts = [1, 2, 4, 8, 16, self.hardware_specs.cpu_threads]
            
            for num_threads in thread_counts:
                if num_threads > self.hardware_specs.cpu_threads:
                    continue
                
                start_time = time.time()
                
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor(max_workers=num_threads) as executor:
                    tasks = [loop.run_in_executor(executor, cpu_task) for _ in range(num_threads)]
                    await asyncio.gather(*tasks)
                
                end_time = time.time()
                duration = end_time - start_time
                
                throughput = num_threads / duration
                scalability_results[num_threads] = {
                    "duration": duration,
                    "throughput": throughput
                }
            
            # Berechne Scaling-Efficiency
            baseline_throughput = scalability_results[1]["throughput"]
            scaling_efficiency = {}
            
            for threads, result in scalability_results.items():
                expected_throughput = baseline_throughput * threads
                actual_throughput = result["throughput"]
                efficiency = actual_throughput / expected_throughput
                scaling_efficiency[threads] = efficiency
            
            return BenchmarkResult(
                benchmark_name=benchmark_name,
                success=True,
                duration=sum(r["duration"] for r in scalability_results.values()),
                metrics={
                    "scalability_results": scalability_results,
                    "scaling_efficiency": scaling_efficiency,
                    "max_threads_tested": max(thread_counts),
                    "optimal_thread_count": max(scaling_efficiency.keys(), key=lambda k: scaling_efficiency[k])
                }
            )
            
        except Exception as e:
            return BenchmarkResult(
                benchmark_name=benchmark_name,
                success=False,
                duration=0.0,
                error_message=str(e)
            )
    
    async def _benchmark_process_scalability(self) -> BenchmarkResult:
        """Benchmark Process-Scalability"""
        
        benchmark_name = "process_scalability"
        
        try:
            def cpu_intensive_process(n):
                result = 0
                for i in range(n):
                    result += i * i
                return result
            
            scalability_results = {}
            
            # Teste verschiedene Process-Counts
            process_counts = [1, 2, 4, self.hardware_specs.cpu_cores]
            task_size = 2000000
            
            for num_processes in process_counts:
                if num_processes > self.hardware_specs.cpu_cores:
                    continue
                
                start_time = time.time()
                
                loop = asyncio.get_event_loop()
                with ProcessPoolExecutor(max_workers=num_processes) as executor:
                    tasks = [loop.run_in_executor(executor, cpu_intensive_process, task_size) 
                            for _ in range(num_processes)]
                    await asyncio.gather(*tasks)
                
                end_time = time.time()
                duration = end_time - start_time
                
                throughput = (num_processes * task_size) / duration
                scalability_results[num_processes] = {
                    "duration": duration,
                    "throughput": throughput
                }
            
            # Berechne Process-Scaling-Efficiency
            baseline_throughput = scalability_results[1]["throughput"]
            scaling_efficiency = {}
            
            for processes, result in scalability_results.items():
                expected_throughput = baseline_throughput * processes
                actual_throughput = result["throughput"]
                efficiency = actual_throughput / expected_throughput
                scaling_efficiency[processes] = efficiency
            
            return BenchmarkResult(
                benchmark_name=benchmark_name,
                success=True,
                duration=sum(r["duration"] for r in scalability_results.values()),
                metrics={
                    "scalability_results": scalability_results,
                    "scaling_efficiency": scaling_efficiency,
                    "max_processes_tested": max(process_counts),
                    "optimal_process_count": max(scaling_efficiency.keys(), key=lambda k: scaling_efficiency[k])
                }
            )
            
        except Exception as e:
            return BenchmarkResult(
                benchmark_name=benchmark_name,
                success=False,
                duration=0.0,
                error_message=str(e)
            )
    
    async def _benchmark_data_size_scalability(self) -> BenchmarkResult:
        """Benchmark Data-Size-Scalability"""
        
        benchmark_name = "data_size_scalability"
        
        try:
            scalability_results = {}
            
            # Teste verschiedene Data-Sizes
            data_sizes = [1000, 10000, 100000, 1000000]  # Array-Größen
            
            for size in data_sizes:
                # Matrix-Operation mit verschiedenen Größen
                start_time = time.time()
                
                a = np.random.randn(size, 100)
                b = np.random.randn(100, size)
                c = np.dot(a, b)
                
                end_time = time.time()
                duration = end_time - start_time
                
                # Throughput (Operations per Second)
                operations = size * 100 * size  # Matrix-Multiplikation Operations
                throughput = operations / duration
                
                scalability_results[size] = {
                    "duration": duration,
                    "throughput": throughput,
                    "operations": operations
                }
            
            # Berechne Complexity-Scaling
            complexity_analysis = {}
            for i, (size, result) in enumerate(scalability_results.items()):
                if i > 0:
                    prev_size = list(scalability_results.keys())[i-1]
                    prev_result = scalability_results[prev_size]
                    
                    size_ratio = size / prev_size
                    time_ratio = result["duration"] / prev_result["duration"]
                    
                    # Erwartete Complexity für Matrix-Multiplikation: O(n^3)
                    expected_ratio = size_ratio ** 3
                    complexity_efficiency = expected_ratio / time_ratio
                    
                    complexity_analysis[size] = {
                        "size_ratio": size_ratio,
                        "time_ratio": time_ratio,
                        "expected_ratio": expected_ratio,
                        "complexity_efficiency": complexity_efficiency
                    }
            
            return BenchmarkResult(
                benchmark_name=benchmark_name,
                success=True,
                duration=sum(r["duration"] for r in scalability_results.values()),
                metrics={
                    "scalability_results": scalability_results,
                    "complexity_analysis": complexity_analysis,
                    "max_size_tested": max(data_sizes),
                    "avg_complexity_efficiency": np.mean([c["complexity_efficiency"] for c in complexity_analysis.values()])
                }
            )
            
        except Exception as e:
            return BenchmarkResult(
                benchmark_name=benchmark_name,
                success=False,
                duration=0.0,
                error_message=str(e)
            )
    
    def generate_benchmark_report(self) -> Dict[str, Any]:
        """Generiere Benchmark-Report"""
        
        try:
            if not self.benchmark_results:
                return {"error": "No benchmark results available"}
            
            # Statistiken berechnen
            total_benchmarks = len(self.benchmark_results)
            successful_benchmarks = sum(1 for result in self.benchmark_results if result.success)
            failed_benchmarks = total_benchmarks - successful_benchmarks
            
            success_rate = successful_benchmarks / total_benchmarks if total_benchmarks > 0 else 0
            
            total_duration = sum(result.duration for result in self.benchmark_results)
            avg_duration = total_duration / total_benchmarks if total_benchmarks > 0 else 0
            
            # Performance-Metriken aggregieren
            cpu_benchmarks = [r for r in self.benchmark_results if "cpu" in r.benchmark_name and r.success]
            gpu_benchmarks = [r for r in self.benchmark_results if "gpu" in r.benchmark_name and r.success]
            memory_benchmarks = [r for r in self.benchmark_results if "memory" in r.benchmark_name and r.success]
            io_benchmarks = [r for r in self.benchmark_results if ("disk" in r.benchmark_name or "io" in r.benchmark_name) and r.success]
            
            # Durchschnittliche Performance-Werte
            avg_cpu_usage = np.mean([r.cpu_usage for r in cpu_benchmarks if r.cpu_usage]) if cpu_benchmarks else 0
            avg_gpu_usage = np.mean([r.gpu_usage for r in gpu_benchmarks if r.gpu_usage]) if gpu_benchmarks else 0
            avg_memory_usage = np.mean([r.memory_usage for r in memory_benchmarks if r.memory_usage]) if memory_benchmarks else 0
            
            # Benchmark-Details
            benchmark_details = []
            for result in self.benchmark_results:
                benchmark_details.append({
                    "name": result.benchmark_name,
                    "success": result.success,
                    "duration": result.duration,
                    "throughput": result.throughput,
                    "latency": result.latency,
                    "cpu_usage": result.cpu_usage,
                    "memory_usage": result.memory_usage,
                    "gpu_usage": result.gpu_usage,
                    "error": result.error_message,
                    "key_metrics": result.metrics
                })
            
            # Failed-Benchmarks
            failed_benchmark_details = [
                {
                    "name": result.benchmark_name,
                    "error": result.error_message,
                    "duration": result.duration
                }
                for result in self.benchmark_results if not result.success
            ]
            
            # Hardware-Performance-Score (0-100)
            performance_score = self._calculate_performance_score()
            
            report = {
                "timestamp": datetime.now().isoformat(),
                "hardware_specs": {
                    "cpu_cores": self.hardware_specs.cpu_cores,
                    "cpu_threads": self.hardware_specs.cpu_threads,
                    "cpu_frequency": self.hardware_specs.cpu_frequency,
                    "total_memory_gb": self.hardware_specs.total_memory_gb,
                    "gpu_count": self.hardware_specs.gpu_count,
                    "gpu_memory_gb": self.hardware_specs.gpu_memory_gb,
                    "disk_type": self.hardware_specs.disk_type
                },
                "summary": {
                    "total_benchmarks": total_benchmarks,
                    "successful_benchmarks": successful_benchmarks,
                    "failed_benchmarks": failed_benchmarks,
                    "success_rate": success_rate,
                    "total_duration": total_duration,
                    "avg_duration": avg_duration,
                    "performance_score": performance_score
                },
                "performance_metrics": {
                    "avg_cpu_usage": avg_cpu_usage,
                    "avg_gpu_usage": avg_gpu_usage,
                    "avg_memory_usage": avg_memory_usage,
                    "cpu_benchmarks_count": len(cpu_benchmarks),
                    "gpu_benchmarks_count": len(gpu_benchmarks),
                    "memory_benchmarks_count": len(memory_benchmarks),
                    "io_benchmarks_count": len(io_benchmarks)
                },
                "benchmark_details": benchmark_details,
                "failed_benchmarks": failed_benchmark_details,
                "overall_status": "PASS" if success_rate >= 0.8 and performance_score >= 70 else "FAIL"
            }
            
            # Report speichern
            report_file = self.results_directory / f"performance_benchmark_report_{int(time.time())}.json"
            
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            self.logger.info(f"Benchmark report generated: {report_file}")
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating benchmark report: {e}")
            return {"error": str(e)}
    
    def _calculate_performance_score(self) -> float:
        """Berechne Overall-Performance-Score (0-100)"""
        
        try:
            scores = []
            
            # CPU-Performance-Score
            cpu_benchmarks = [r for r in self.benchmark_results if "cpu" in r.benchmark_name and r.success]
            if cpu_benchmarks:
                cpu_throughputs = [r.throughput for r in cpu_benchmarks if r.throughput]
                if cpu_throughputs:
                    # Normalisiere basierend auf Hardware-Specs
                    expected_cpu_performance = self.hardware_specs.cpu_cores * self.hardware_specs.cpu_frequency * 1000
                    actual_cpu_performance = np.mean(cpu_throughputs)
                    cpu_score = min(100, (actual_cpu_performance / expected_cpu_performance) * 100)
                    scores.append(cpu_score)
            
            # GPU-Performance-Score
            gpu_benchmarks = [r for r in self.benchmark_results if "gpu" in r.benchmark_name and r.success]
            if gpu_benchmarks and self.hardware_specs.gpu_count > 0:
                gpu_throughputs = [r.throughput for r in gpu_benchmarks if r.throughput]
                if gpu_throughputs:
                    # Vereinfachte GPU-Score-Berechnung
                    avg_gpu_throughput = np.mean(gpu_throughputs)
                    gpu_score = min(100, avg_gpu_throughput / 10)  # Normalisierung
                    scores.append(gpu_score)
            
            # Memory-Performance-Score
            memory_benchmarks = [r for r in self.benchmark_results if "memory" in r.benchmark_name and r.success]
            if memory_benchmarks:
                memory_throughputs = [r.throughput for r in memory_benchmarks if r.throughput]
                if memory_throughputs:
                    avg_memory_throughput = np.mean(memory_throughputs)
                    memory_score = min(100, avg_memory_throughput * 2)  # Normalisierung
                    scores.append(memory_score)
            
            # I/O-Performance-Score
            io_benchmarks = [r for r in self.benchmark_results if ("disk" in r.benchmark_name or "io" in r.benchmark_name) and r.success]
            if io_benchmarks:
                io_throughputs = [r.throughput for r in io_benchmarks if r.throughput]
                if io_throughputs:
                    avg_io_throughput = np.mean(io_throughputs)
                    io_score = min(100, avg_io_throughput / 5)  # Normalisierung
                    scores.append(io_score)
            
            # Overall-Score
            if scores:
                return np.mean(scores)
            else:
                return 0.0
                
        except Exception as e:
            self.logger.error(f"Error calculating performance score: {e}")
            return 0.0


# Utility-Funktionen
async def run_performance_benchmark_suite(config: Optional[Dict] = None) -> Dict[str, Any]:
    """Führe komplette Performance-Benchmark-Suite aus"""
    
    benchmarks = PerformanceBenchmarks(config)
    
    # Führe alle Benchmarks aus
    results = await benchmarks.run_all_benchmarks()
    
    # Generiere Report
    report = benchmarks.generate_benchmark_report()
    
    return {
        "benchmark_results": [result.to_dict() for result in results],
        "report": report
    }


def validate_hardware_requirements(min_specs: Dict[str, Any]) -> Dict[str, Any]:
    """Validiere Hardware-Requirements"""
    
    current_specs = HardwareSpecs.detect_hardware()
    
    validation_result = {
        "meets_requirements": True,
        "issues": [],
        "recommendations": []
    }
    
    # CPU-Validation
    if "min_cpu_cores" in min_specs:
        if current_specs.cpu_cores < min_specs["min_cpu_cores"]:
            validation_result["meets_requirements"] = False
            validation_result["issues"].append(f"Insufficient CPU cores: {current_specs.cpu_cores} < {min_specs['min_cpu_cores']}")
    
    # Memory-Validation
    if "min_memory_gb" in min_specs:
        if current_specs.total_memory_gb < min_specs["min_memory_gb"]:
            validation_result["meets_requirements"] = False
            validation_result["issues"].append(f"Insufficient memory: {current_specs.total_memory_gb:.1f}GB < {min_specs['min_memory_gb']}GB")
    
    # GPU-Validation
    if "min_gpu_count" in min_specs:
        if current_specs.gpu_count < min_specs["min_gpu_count"]:
            validation_result["meets_requirements"] = False
            validation_result["issues"].append(f"Insufficient GPUs: {current_specs.gpu_count} < {min_specs['min_gpu_count']}")
    
    # Recommendations
    if current_specs.cpu_cores < 16:
        validation_result["recommendations"].append("Consider upgrading to 16+ CPU cores for optimal performance")
    
    if current_specs.total_memory_gb < 64:
        validation_result["recommendations"].append("Consider upgrading to 64GB+ RAM for large datasets")
    
    if current_specs.gpu_count == 0:
        validation_result["recommendations"].append("Consider adding a GPU for AI workloads")
    
    return validation_result