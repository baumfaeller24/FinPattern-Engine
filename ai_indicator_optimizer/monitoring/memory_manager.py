#!/usr/bin/env python3
"""
Memory Manager für effiziente 192GB RAM-Nutzung
Phase 3 Implementation - Task 11

Features:
- Intelligente Memory-Allocation für 192GB RAM
- Dynamic Memory-Pool-Management
- Memory-Leak-Detection und Prevention
- Cache-Optimierung und Memory-Mapping
- NUMA-Aware Memory-Allocation
- Memory-Compression und Swapping-Strategien
"""

import os
import gc
import mmap
import time
import threading
import logging
import psutil
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import numpy as np
from collections import deque, defaultdict
import weakref
import pickle
import json
import sys

# Memory-Profiling
try:
    import tracemalloc
    TRACEMALLOC_AVAILABLE = True
except ImportError:
    TRACEMALLOC_AVAILABLE = False

try:
    import pympler
    from pympler import tracker, muppy, summary
    PYMPLER_AVAILABLE = True
except ImportError:
    PYMPLER_AVAILABLE = False

# Memory-Mapping
try:
    import mmap
    MMAP_AVAILABLE = True
except ImportError:
    MMAP_AVAILABLE = False

# NUMA Support
try:
    import numa
    NUMA_AVAILABLE = True
except ImportError:
    NUMA_AVAILABLE = False


class MemoryStrategy(Enum):
    """Memory Management Strategien"""
    CONSERVATIVE = "conservative"  # 60% RAM Usage
    BALANCED = "balanced"         # 80% RAM Usage
    AGGRESSIVE = "aggressive"     # 95% RAM Usage
    ADAPTIVE = "adaptive"        # Dynamic basierend auf Workload


class MemoryPoolType(Enum):
    """Typen von Memory-Pools"""
    CACHE = "cache"
    BUFFER = "buffer"
    TEMPORARY = "temporary"
    PERSISTENT = "persistent"
    SHARED = "shared"


class MemoryPriority(Enum):
    """Memory-Prioritäten"""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


@dataclass
class MemoryBlock:
    """Memory-Block Definition"""
    block_id: str
    size_bytes: int
    pool_type: MemoryPoolType
    priority: MemoryPriority
    data: Any = None
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    is_compressed: bool = False
    is_memory_mapped: bool = False
    file_path: Optional[Path] = None
    
    def __post_init__(self):
        self.size_mb = self.size_bytes / (1024**2)
        self.size_gb = self.size_bytes / (1024**3)


@dataclass
class MemoryPool:
    """Memory-Pool für spezifische Datentypen"""
    pool_id: str
    pool_type: MemoryPoolType
    max_size_bytes: int
    current_size_bytes: int = 0
    blocks: Dict[str, MemoryBlock] = field(default_factory=dict)
    allocation_strategy: str = "lru"  # lru, lfu, fifo
    compression_enabled: bool = False
    memory_mapping_enabled: bool = False
    
    def __post_init__(self):
        self.max_size_mb = self.max_size_bytes / (1024**2)
        self.max_size_gb = self.max_size_bytes / (1024**3)
        self.created_at = datetime.now()


@dataclass
class MemoryMetrics:
    """Memory-System-Metriken"""
    timestamp: datetime
    total_ram_gb: float
    available_ram_gb: float
    used_ram_gb: float
    usage_percent: float
    swap_total_gb: float
    swap_used_gb: float
    swap_percent: float
    cache_size_gb: float
    buffer_size_gb: float
    process_memory_gb: float
    gc_collections: Dict[int, int]
    memory_pools: Dict[str, Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_ram_gb": self.total_ram_gb,
            "available_ram_gb": self.available_ram_gb,
            "used_ram_gb": self.used_ram_gb,
            "usage_percent": self.usage_percent,
            "swap_total_gb": self.swap_total_gb,
            "swap_used_gb": self.swap_used_gb,
            "swap_percent": self.swap_percent,
            "cache_size_gb": self.cache_size_gb,
            "buffer_size_gb": self.buffer_size_gb,
            "process_memory_gb": self.process_memory_gb,
            "gc_collections": self.gc_collections,
            "memory_pools": self.memory_pools
        }


class MemoryManager:
    """
    Memory Manager für effiziente 192GB RAM-Nutzung
    
    Features:
    - Intelligente Memory-Allocation und Pool-Management
    - Memory-Leak-Detection und Prevention
    - Cache-Optimierung mit LRU/LFU-Strategien
    - Memory-Mapping für große Dateien
    - NUMA-Aware Allocation
    - Compression und Swapping
    - Real-time Memory-Monitoring
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Memory-Konfiguration
        self.memory_strategy = MemoryStrategy(
            self.config.get("memory_strategy", "balanced")
        )
        self.max_ram_usage_percent = self.config.get("max_ram_usage_percent", 80.0)
        self.enable_compression = self.config.get("enable_compression", True)
        self.enable_memory_mapping = self.config.get("enable_memory_mapping", True)
        self.enable_numa = self.config.get("enable_numa", NUMA_AVAILABLE)
        self.gc_threshold = self.config.get("gc_threshold", 0.85)  # GC bei 85% RAM
        
        # Memory-Pools
        self.memory_pools: Dict[str, MemoryPool] = {}
        self.total_allocated_bytes = 0
        
        # System-Memory-Info
        self.system_memory = psutil.virtual_memory()
        self.total_ram_gb = self.system_memory.total / (1024**3)
        self.max_usable_ram_gb = self.total_ram_gb * (self.max_ram_usage_percent / 100.0)
        
        # Memory-Tracking
        self.memory_history: deque = deque(maxlen=1000)
        self.allocation_history: deque = deque(maxlen=10000)
        self.leak_detection_enabled = self.config.get("leak_detection", True)
        
        # Threading
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.cleanup_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Memory-Mapping
        self.memory_mapped_files: Dict[str, mmap.mmap] = {}
        self.temp_dir = Path(self.config.get("temp_dir", "/tmp/ai_optimizer_memory"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Statistiken
        self.stats = {
            "allocations": 0,
            "deallocations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "compressions": 0,
            "decompressions": 0,
            "memory_mappings": 0,
            "gc_collections": 0,
            "leak_detections": 0
        }
        
        # Memory-Profiling Setup
        if TRACEMALLOC_AVAILABLE and self.leak_detection_enabled:
            tracemalloc.start()
        
        if PYMPLER_AVAILABLE:
            self.memory_tracker = tracker.SummaryTracker()
        
        # Initialisierung
        self._setup_default_pools()
        self._setup_numa_policy()
        
        self.logger.info(f"MemoryManager initialized for {self.total_ram_gb:.1f}GB RAM "
                        f"(max usage: {self.max_usable_ram_gb:.1f}GB)")
    
    def start_monitoring(self):
        """Starte Memory-Monitoring"""
        
        if self.monitoring_active:
            self.logger.warning("Memory monitoring already active")
            return
        
        self.monitoring_active = True
        self.stop_event.clear()
        
        # Monitoring-Thread starten
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            name="MemoryMonitor",
            daemon=True
        )
        self.monitoring_thread.start()
        
        # Cleanup-Thread starten
        self.cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            name="MemoryCleanup",
            daemon=True
        )
        self.cleanup_thread.start()
        
        self.logger.info("Memory monitoring started")
    
    def stop_monitoring(self):
        """Stoppe Memory-Monitoring"""
        
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        self.stop_event.set()
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5.0)
        
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5.0)
        
        self.logger.info("Memory monitoring stopped")
    
    def create_memory_pool(self, pool_id: str, pool_type: MemoryPoolType,
                          max_size_gb: float, **kwargs) -> MemoryPool:
        """Erstelle Memory-Pool"""
        
        try:
            max_size_bytes = int(max_size_gb * 1024**3)
            
            # Prüfe verfügbaren Speicher
            available_bytes = self._get_available_memory_bytes()
            if max_size_bytes > available_bytes:
                self.logger.warning(f"Pool size {max_size_gb:.1f}GB exceeds available memory "
                                  f"{available_bytes / (1024**3):.1f}GB")
            
            pool = MemoryPool(
                pool_id=pool_id,
                pool_type=pool_type,
                max_size_bytes=max_size_bytes,
                allocation_strategy=kwargs.get("allocation_strategy", "lru"),
                compression_enabled=kwargs.get("compression_enabled", self.enable_compression),
                memory_mapping_enabled=kwargs.get("memory_mapping_enabled", self.enable_memory_mapping)
            )
            
            self.memory_pools[pool_id] = pool
            
            self.logger.info(f"Created memory pool '{pool_id}' "
                           f"({pool_type.value}, {max_size_gb:.1f}GB)")
            
            return pool
            
        except Exception as e:
            self.logger.error(f"Error creating memory pool: {e}")
            raise
    
    def allocate_memory(self, pool_id: str, block_id: str, data: Any,
                       priority: MemoryPriority = MemoryPriority.NORMAL) -> bool:
        """Allokiere Memory-Block in Pool"""
        
        try:
            if pool_id not in self.memory_pools:
                self.logger.error(f"Memory pool '{pool_id}' not found")
                return False
            
            pool = self.memory_pools[pool_id]
            
            # Berechne Daten-Größe
            data_size = self._calculate_object_size(data)
            
            # Prüfe Pool-Kapazität
            if pool.current_size_bytes + data_size > pool.max_size_bytes:
                # Versuche Platz zu schaffen
                freed_bytes = self._free_pool_space(pool, data_size)
                if freed_bytes < data_size:
                    self.logger.warning(f"Cannot allocate {data_size / (1024**2):.1f}MB "
                                      f"in pool '{pool_id}' - insufficient space")
                    return False
            
            # Komprimiere Daten falls aktiviert
            compressed_data = data
            is_compressed = False
            if pool.compression_enabled and data_size > 1024**2:  # > 1MB
                compressed_data = self._compress_data(data)
                if compressed_data and len(compressed_data) < data_size * 0.8:
                    is_compressed = True
                    data_size = len(compressed_data)
                    self.stats["compressions"] += 1
                else:
                    compressed_data = data
            
            # Memory-Mapping für große Objekte
            is_memory_mapped = False
            file_path = None
            if (pool.memory_mapping_enabled and 
                data_size > 100 * 1024**2 and  # > 100MB
                MMAP_AVAILABLE):
                
                file_path = self._create_memory_mapped_file(block_id, compressed_data)
                if file_path:
                    is_memory_mapped = True
                    compressed_data = None  # Daten sind in File
                    self.stats["memory_mappings"] += 1
            
            # Memory-Block erstellen
            memory_block = MemoryBlock(
                block_id=block_id,
                size_bytes=data_size,
                pool_type=pool.pool_type,
                priority=priority,
                data=compressed_data,
                is_compressed=is_compressed,
                is_memory_mapped=is_memory_mapped,
                file_path=file_path
            )
            
            # Zu Pool hinzufügen
            pool.blocks[block_id] = memory_block
            pool.current_size_bytes += data_size
            self.total_allocated_bytes += data_size
            
            # Statistiken
            self.stats["allocations"] += 1
            self.allocation_history.append({
                "timestamp": datetime.now().isoformat(),
                "action": "allocate",
                "pool_id": pool_id,
                "block_id": block_id,
                "size_mb": data_size / (1024**2),
                "compressed": is_compressed,
                "memory_mapped": is_memory_mapped
            })
            
            self.logger.debug(f"Allocated {data_size / (1024**2):.1f}MB "
                            f"in pool '{pool_id}' (block: {block_id})")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error allocating memory: {e}")
            return False
    
    def get_memory_block(self, pool_id: str, block_id: str) -> Optional[Any]:
        """Erhalte Memory-Block aus Pool"""
        
        try:
            if pool_id not in self.memory_pools:
                self.stats["cache_misses"] += 1
                return None
            
            pool = self.memory_pools[pool_id]
            
            if block_id not in pool.blocks:
                self.stats["cache_misses"] += 1
                return None
            
            memory_block = pool.blocks[block_id]
            
            # Access-Tracking
            memory_block.last_accessed = datetime.now()
            memory_block.access_count += 1
            
            # Daten laden
            data = None
            
            if memory_block.is_memory_mapped and memory_block.file_path:
                # Aus Memory-Mapped File laden
                data = self._load_from_memory_mapped_file(memory_block.file_path)
            else:
                data = memory_block.data
            
            # Dekomprimieren falls nötig
            if memory_block.is_compressed and data:
                data = self._decompress_data(data)
                self.stats["decompressions"] += 1
            
            self.stats["cache_hits"] += 1
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error getting memory block: {e}")
            self.stats["cache_misses"] += 1
            return None
    
    def deallocate_memory(self, pool_id: str, block_id: str) -> bool:
        """Deallokiere Memory-Block"""
        
        try:
            if pool_id not in self.memory_pools:
                return False
            
            pool = self.memory_pools[pool_id]
            
            if block_id not in pool.blocks:
                return False
            
            memory_block = pool.blocks[block_id]
            
            # Memory-Mapped File löschen
            if memory_block.is_memory_mapped and memory_block.file_path:
                self._cleanup_memory_mapped_file(memory_block.file_path)
            
            # Aus Pool entfernen
            pool.current_size_bytes -= memory_block.size_bytes
            self.total_allocated_bytes -= memory_block.size_bytes
            del pool.blocks[block_id]
            
            # Statistiken
            self.stats["deallocations"] += 1
            self.allocation_history.append({
                "timestamp": datetime.now().isoformat(),
                "action": "deallocate",
                "pool_id": pool_id,
                "block_id": block_id,
                "size_mb": memory_block.size_bytes / (1024**2)
            })
            
            self.logger.debug(f"Deallocated {memory_block.size_bytes / (1024**2):.1f}MB "
                            f"from pool '{pool_id}' (block: {block_id})")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error deallocating memory: {e}")
            return False    

    def get_memory_metrics(self) -> MemoryMetrics:
        """Erhalte aktuelle Memory-Metriken"""
        
        try:
            # System-Memory
            virtual_memory = psutil.virtual_memory()
            swap_memory = psutil.swap_memory()
            
            # Process-Memory
            process = psutil.Process()
            process_memory = process.memory_info()
            
            # GC-Statistiken
            gc_stats = {}
            for i in range(3):
                gc_stats[i] = gc.get_count()[i]
            
            # Memory-Pool-Statistiken
            pool_stats = {}
            for pool_id, pool in self.memory_pools.items():
                pool_stats[pool_id] = {
                    "type": pool.pool_type.value,
                    "max_size_gb": pool.max_size_gb,
                    "current_size_gb": pool.current_size_bytes / (1024**3),
                    "usage_percent": (pool.current_size_bytes / pool.max_size_bytes) * 100,
                    "block_count": len(pool.blocks),
                    "allocation_strategy": pool.allocation_strategy,
                    "compression_enabled": pool.compression_enabled,
                    "memory_mapping_enabled": pool.memory_mapping_enabled
                }
            
            metrics = MemoryMetrics(
                timestamp=datetime.now(),
                total_ram_gb=virtual_memory.total / (1024**3),
                available_ram_gb=virtual_memory.available / (1024**3),
                used_ram_gb=virtual_memory.used / (1024**3),
                usage_percent=virtual_memory.percent,
                swap_total_gb=swap_memory.total / (1024**3),
                swap_used_gb=swap_memory.used / (1024**3),
                swap_percent=swap_memory.percent,
                cache_size_gb=getattr(virtual_memory, 'cached', 0) / (1024**3),
                buffer_size_gb=getattr(virtual_memory, 'buffers', 0) / (1024**3),
                process_memory_gb=process_memory.rss / (1024**3),
                gc_collections=gc_stats,
                memory_pools=pool_stats
            )
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error getting memory metrics: {e}")
            return MemoryMetrics(
                timestamp=datetime.now(),
                total_ram_gb=0.0,
                available_ram_gb=0.0,
                used_ram_gb=0.0,
                usage_percent=0.0,
                swap_total_gb=0.0,
                swap_used_gb=0.0,
                swap_percent=0.0,
                cache_size_gb=0.0,
                buffer_size_gb=0.0,
                process_memory_gb=0.0,
                gc_collections={},
                memory_pools={}
            )
    
    def _monitoring_loop(self):
        """Haupt-Monitoring-Loop"""
        
        while self.monitoring_active and not self.stop_event.is_set():
            try:
                # Memory-Metriken sammeln
                metrics = self.get_memory_metrics()
                self.memory_history.append(metrics)
                
                # Memory-Leak-Detection
                if self.leak_detection_enabled:
                    self._detect_memory_leaks()
                
                # Automatische GC bei hoher Memory-Usage
                if metrics.usage_percent > self.gc_threshold * 100:
                    self._trigger_garbage_collection()
                
                # Memory-Pool-Optimierung
                self._optimize_memory_pools()
                
                # Warte bis zum nächsten Monitoring-Cycle
                self.stop_event.wait(5.0)  # 5 Sekunden Interval
                
            except Exception as e:
                self.logger.error(f"Memory monitoring loop error: {e}")
                time.sleep(1.0)
    
    def _cleanup_loop(self):
        """Memory-Cleanup-Loop"""
        
        while self.monitoring_active and not self.stop_event.is_set():
            try:
                # Cleanup alte Memory-Blocks
                self._cleanup_expired_blocks()
                
                # Cleanup Memory-Mapped Files
                self._cleanup_orphaned_files()
                
                # Defragmentierung
                self._defragment_pools()
                
                # Warte bis zum nächsten Cleanup-Cycle
                self.stop_event.wait(60.0)  # 1 Minute Interval
                
            except Exception as e:
                self.logger.error(f"Memory cleanup loop error: {e}")
                time.sleep(5.0)
    
    def _setup_default_pools(self):
        """Setup Standard-Memory-Pools"""
        
        try:
            # Cache-Pool (30% der verfügbaren RAM)
            cache_size_gb = self.max_usable_ram_gb * 0.3
            self.create_memory_pool(
                "cache", MemoryPoolType.CACHE, cache_size_gb,
                allocation_strategy="lru", compression_enabled=True
            )
            
            # Buffer-Pool (20% der verfügbaren RAM)
            buffer_size_gb = self.max_usable_ram_gb * 0.2
            self.create_memory_pool(
                "buffer", MemoryPoolType.BUFFER, buffer_size_gb,
                allocation_strategy="fifo", compression_enabled=False
            )
            
            # Temporary-Pool (25% der verfügbaren RAM)
            temp_size_gb = self.max_usable_ram_gb * 0.25
            self.create_memory_pool(
                "temporary", MemoryPoolType.TEMPORARY, temp_size_gb,
                allocation_strategy="lru", compression_enabled=True,
                memory_mapping_enabled=True
            )
            
            # Persistent-Pool (25% der verfügbaren RAM)
            persistent_size_gb = self.max_usable_ram_gb * 0.25
            self.create_memory_pool(
                "persistent", MemoryPoolType.PERSISTENT, persistent_size_gb,
                allocation_strategy="lfu", compression_enabled=True,
                memory_mapping_enabled=True
            )
            
            self.logger.info(f"Created default memory pools: "
                           f"cache={cache_size_gb:.1f}GB, "
                           f"buffer={buffer_size_gb:.1f}GB, "
                           f"temp={temp_size_gb:.1f}GB, "
                           f"persistent={persistent_size_gb:.1f}GB")
            
        except Exception as e:
            self.logger.error(f"Error setting up default pools: {e}")
    
    def _setup_numa_policy(self):
        """Setup NUMA-Policy falls verfügbar"""
        
        if not self.enable_numa or not NUMA_AVAILABLE:
            return
        
        try:
            # NUMA-Nodes erkennen
            numa_nodes = numa.get_max_node() + 1
            
            if numa_nodes > 1:
                # Setze Memory-Policy für bessere Performance
                numa.set_mempolicy(numa.MPOL_INTERLEAVE, numa.get_mems_allowed())
                self.logger.info(f"NUMA policy set for {numa_nodes} nodes")
            
        except Exception as e:
            self.logger.debug(f"NUMA setup failed: {e}")
    
    def _calculate_object_size(self, obj: Any) -> int:
        """Berechne Objekt-Größe in Bytes"""
        
        try:
            if hasattr(obj, '__sizeof__'):
                return obj.__sizeof__()
            elif isinstance(obj, (list, tuple)):
                return sum(self._calculate_object_size(item) for item in obj)
            elif isinstance(obj, dict):
                return sum(self._calculate_object_size(k) + self._calculate_object_size(v) 
                          for k, v in obj.items())
            elif isinstance(obj, np.ndarray):
                return obj.nbytes
            else:
                return sys.getsizeof(obj)
                
        except Exception as e:
            self.logger.debug(f"Error calculating object size: {e}")
            return sys.getsizeof(obj)
    
    def _compress_data(self, data: Any) -> Optional[bytes]:
        """Komprimiere Daten"""
        
        try:
            import zlib
            
            # Serialisiere Objekt
            serialized = pickle.dumps(data)
            
            # Komprimiere
            compressed = zlib.compress(serialized, level=6)
            
            return compressed
            
        except Exception as e:
            self.logger.debug(f"Error compressing data: {e}")
            return None
    
    def _decompress_data(self, compressed_data: bytes) -> Any:
        """Dekomprimiere Daten"""
        
        try:
            import zlib
            
            # Dekomprimiere
            decompressed = zlib.decompress(compressed_data)
            
            # Deserialisiere
            data = pickle.loads(decompressed)
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error decompressing data: {e}")
            return None
    
    def _create_memory_mapped_file(self, block_id: str, data: Any) -> Optional[Path]:
        """Erstelle Memory-Mapped File"""
        
        try:
            file_path = self.temp_dir / f"{block_id}.mmap"
            
            # Serialisiere Daten
            serialized = pickle.dumps(data)
            
            # Schreibe in File
            with open(file_path, 'wb') as f:
                f.write(serialized)
            
            # Erstelle Memory-Mapping
            with open(file_path, 'r+b') as f:
                mm = mmap.mmap(f.fileno(), 0)
                self.memory_mapped_files[str(file_path)] = mm
            
            return file_path
            
        except Exception as e:
            self.logger.error(f"Error creating memory mapped file: {e}")
            return None
    
    def _load_from_memory_mapped_file(self, file_path: Path) -> Any:
        """Lade Daten aus Memory-Mapped File"""
        
        try:
            file_path_str = str(file_path)
            
            if file_path_str in self.memory_mapped_files:
                mm = self.memory_mapped_files[file_path_str]
                mm.seek(0)
                data = pickle.loads(mm.read())
                return data
            else:
                # Fallback: Direkt aus File laden
                with open(file_path, 'rb') as f:
                    data = pickle.load(f)
                return data
                
        except Exception as e:
            self.logger.error(f"Error loading from memory mapped file: {e}")
            return None
    
    def _cleanup_memory_mapped_file(self, file_path: Path):
        """Cleanup Memory-Mapped File"""
        
        try:
            file_path_str = str(file_path)
            
            # Memory-Mapping schließen
            if file_path_str in self.memory_mapped_files:
                mm = self.memory_mapped_files[file_path_str]
                mm.close()
                del self.memory_mapped_files[file_path_str]
            
            # File löschen
            if file_path.exists():
                file_path.unlink()
                
        except Exception as e:
            self.logger.debug(f"Error cleaning up memory mapped file: {e}")
    
    def _get_available_memory_bytes(self) -> int:
        """Erhalte verfügbare Memory in Bytes"""
        
        try:
            virtual_memory = psutil.virtual_memory()
            max_usable_bytes = int(self.total_ram_gb * (self.max_ram_usage_percent / 100.0) * 1024**3)
            current_usage_bytes = virtual_memory.used
            
            available_bytes = max_usable_bytes - current_usage_bytes - self.total_allocated_bytes
            
            return max(0, available_bytes)
            
        except Exception as e:
            self.logger.error(f"Error getting available memory: {e}")
            return 0
    
    def _free_pool_space(self, pool: MemoryPool, required_bytes: int) -> int:
        """Schaffe Platz in Memory-Pool"""
        
        try:
            freed_bytes = 0
            blocks_to_remove = []
            
            # Sortiere Blocks nach Allocation-Strategy
            if pool.allocation_strategy == "lru":
                # Least Recently Used zuerst
                sorted_blocks = sorted(
                    pool.blocks.items(),
                    key=lambda x: x[1].last_accessed
                )
            elif pool.allocation_strategy == "lfu":
                # Least Frequently Used zuerst
                sorted_blocks = sorted(
                    pool.blocks.items(),
                    key=lambda x: x[1].access_count
                )
            elif pool.allocation_strategy == "fifo":
                # First In First Out
                sorted_blocks = sorted(
                    pool.blocks.items(),
                    key=lambda x: x[1].created_at
                )
            else:
                # Default: nach Größe (größte zuerst)
                sorted_blocks = sorted(
                    pool.blocks.items(),
                    key=lambda x: x[1].size_bytes,
                    reverse=True
                )
            
            # Entferne Blocks bis genug Platz frei ist
            for block_id, memory_block in sorted_blocks:
                if freed_bytes >= required_bytes:
                    break
                
                # Prüfe Priorität
                if memory_block.priority == MemoryPriority.CRITICAL:
                    continue
                
                blocks_to_remove.append(block_id)
                freed_bytes += memory_block.size_bytes
            
            # Entferne markierte Blocks
            for block_id in blocks_to_remove:
                self.deallocate_memory(pool.pool_id, block_id)
            
            self.logger.debug(f"Freed {freed_bytes / (1024**2):.1f}MB "
                            f"from pool '{pool.pool_id}' ({len(blocks_to_remove)} blocks)")
            
            return freed_bytes
            
        except Exception as e:
            self.logger.error(f"Error freeing pool space: {e}")
            return 0
    
    def _detect_memory_leaks(self):
        """Erkenne Memory-Leaks"""
        
        if not TRACEMALLOC_AVAILABLE:
            return
        
        try:
            # Aktuelle Memory-Statistiken
            current, peak = tracemalloc.get_traced_memory()
            
            # Prüfe auf ungewöhnliches Memory-Wachstum
            if len(self.memory_history) > 10:
                recent_usage = [m.process_memory_gb for m in list(self.memory_history)[-10:]]
                avg_recent = sum(recent_usage) / len(recent_usage)
                current_gb = current / (1024**3)
                
                # Memory-Leak-Detection
                if current_gb > avg_recent * 1.5:  # 50% Anstieg
                    self.logger.warning(f"Potential memory leak detected: "
                                      f"current={current_gb:.2f}GB, "
                                      f"avg_recent={avg_recent:.2f}GB")
                    
                    self.stats["leak_detections"] += 1
                    
                    # Automatische Garbage Collection
                    self._trigger_garbage_collection()
            
        except Exception as e:
            self.logger.debug(f"Error in memory leak detection: {e}")
    
    def _trigger_garbage_collection(self):
        """Triggere Garbage Collection"""
        
        try:
            # Manuelle GC
            collected = gc.collect()
            
            self.stats["gc_collections"] += 1
            
            self.logger.info(f"Garbage collection completed: {collected} objects collected")
            
        except Exception as e:
            self.logger.error(f"Error in garbage collection: {e}")
    
    def _optimize_memory_pools(self):
        """Optimiere Memory-Pools"""
        
        try:
            for pool_id, pool in self.memory_pools.items():
                # Prüfe Pool-Utilization
                utilization = (pool.current_size_bytes / pool.max_size_bytes) * 100
                
                # Komprimiere wenig genutzte Blocks
                if utilization > 80.0 and pool.compression_enabled:
                    self._compress_pool_blocks(pool)
                
                # Memory-Mapping für große Blocks
                if utilization > 90.0 and pool.memory_mapping_enabled:
                    self._memory_map_large_blocks(pool)
            
        except Exception as e:
            self.logger.error(f"Error optimizing memory pools: {e}")
    
    def _compress_pool_blocks(self, pool: MemoryPool):
        """Komprimiere Pool-Blocks"""
        
        try:
            compressed_count = 0
            
            for block_id, memory_block in pool.blocks.items():
                if (not memory_block.is_compressed and 
                    memory_block.size_bytes > 1024**2 and  # > 1MB
                    memory_block.access_count < 5):  # Wenig genutzt
                    
                    # Komprimiere Block
                    if memory_block.data:
                        compressed_data = self._compress_data(memory_block.data)
                        
                        if compressed_data and len(compressed_data) < memory_block.size_bytes * 0.8:
                            # Update Block
                            old_size = memory_block.size_bytes
                            memory_block.data = compressed_data
                            memory_block.size_bytes = len(compressed_data)
                            memory_block.is_compressed = True
                            
                            # Update Pool-Size
                            pool.current_size_bytes -= (old_size - memory_block.size_bytes)
                            self.total_allocated_bytes -= (old_size - memory_block.size_bytes)
                            
                            compressed_count += 1
                            self.stats["compressions"] += 1
            
            if compressed_count > 0:
                self.logger.debug(f"Compressed {compressed_count} blocks in pool '{pool.pool_id}'")
                
        except Exception as e:
            self.logger.error(f"Error compressing pool blocks: {e}")
    
    def _memory_map_large_blocks(self, pool: MemoryPool):
        """Memory-Mapping für große Blocks"""
        
        try:
            mapped_count = 0
            
            for block_id, memory_block in pool.blocks.items():
                if (not memory_block.is_memory_mapped and 
                    memory_block.size_bytes > 100 * 1024**2 and  # > 100MB
                    memory_block.access_count < 3):  # Sehr wenig genutzt
                    
                    # Erstelle Memory-Mapped File
                    file_path = self._create_memory_mapped_file(block_id, memory_block.data)
                    
                    if file_path:
                        # Update Block
                        memory_block.data = None  # Daten sind jetzt in File
                        memory_block.is_memory_mapped = True
                        memory_block.file_path = file_path
                        
                        mapped_count += 1
                        self.stats["memory_mappings"] += 1
            
            if mapped_count > 0:
                self.logger.debug(f"Memory-mapped {mapped_count} blocks in pool '{pool.pool_id}'")
                
        except Exception as e:
            self.logger.error(f"Error memory-mapping blocks: {e}")
    
    def _cleanup_expired_blocks(self):
        """Cleanup abgelaufene Memory-Blocks"""
        
        try:
            current_time = datetime.now()
            cleanup_threshold = timedelta(hours=1)  # 1 Stunde
            
            for pool_id, pool in self.memory_pools.items():
                expired_blocks = []
                
                for block_id, memory_block in pool.blocks.items():
                    # Prüfe Alter und Zugriff
                    age = current_time - memory_block.created_at
                    last_access_age = current_time - memory_block.last_accessed
                    
                    # Markiere als abgelaufen wenn:
                    # - Älter als Threshold UND nicht kürzlich zugegriffen
                    # - Temporary-Pool und älter als 30 Minuten
                    if ((age > cleanup_threshold and last_access_age > cleanup_threshold) or
                        (pool.pool_type == MemoryPoolType.TEMPORARY and age > timedelta(minutes=30))):
                        
                        # Prüfe Priorität
                        if memory_block.priority not in [MemoryPriority.CRITICAL, MemoryPriority.HIGH]:
                            expired_blocks.append(block_id)
                
                # Entferne abgelaufene Blocks
                for block_id in expired_blocks:
                    self.deallocate_memory(pool_id, block_id)
                
                if expired_blocks:
                    self.logger.debug(f"Cleaned up {len(expired_blocks)} expired blocks "
                                    f"from pool '{pool_id}'")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up expired blocks: {e}")
    
    def _cleanup_orphaned_files(self):
        """Cleanup verwaiste Memory-Mapped Files"""
        
        try:
            if not self.temp_dir.exists():
                return
            
            # Sammle alle aktiven File-Paths
            active_files = set()
            for pool in self.memory_pools.values():
                for memory_block in pool.blocks.values():
                    if memory_block.file_path:
                        active_files.add(memory_block.file_path)
            
            # Prüfe alle Files im Temp-Directory
            orphaned_count = 0
            for file_path in self.temp_dir.glob("*.mmap"):
                if file_path not in active_files:
                    # Verwaistes File gefunden
                    self._cleanup_memory_mapped_file(file_path)
                    orphaned_count += 1
            
            if orphaned_count > 0:
                self.logger.debug(f"Cleaned up {orphaned_count} orphaned memory-mapped files")
                
        except Exception as e:
            self.logger.error(f"Error cleaning up orphaned files: {e}")
    
    def _defragment_pools(self):
        """Defragmentiere Memory-Pools"""
        
        try:
            # Einfache Defragmentierung durch Reorganisation der Blocks
            for pool_id, pool in self.memory_pools.items():
                if len(pool.blocks) > 100:  # Nur bei vielen Blocks
                    
                    # Sortiere Blocks nach Zugriffshäufigkeit
                    sorted_blocks = sorted(
                        pool.blocks.items(),
                        key=lambda x: x[1].access_count,
                        reverse=True
                    )
                    
                    # Reorganisiere (in-place)
                    pool.blocks = dict(sorted_blocks)
            
        except Exception as e:
            self.logger.error(f"Error defragmenting pools: {e}")
    
    def get_memory_report(self) -> Dict[str, Any]:
        """Erhalte Memory-Report"""
        
        try:
            metrics = self.get_memory_metrics()
            
            # Pool-Details
            pool_details = {}
            for pool_id, pool in self.memory_pools.items():
                pool_details[pool_id] = {
                    "type": pool.pool_type.value,
                    "max_size_gb": pool.max_size_gb,
                    "current_size_gb": pool.current_size_bytes / (1024**3),
                    "usage_percent": (pool.current_size_bytes / pool.max_size_bytes) * 100,
                    "block_count": len(pool.blocks),
                    "allocation_strategy": pool.allocation_strategy,
                    "compression_enabled": pool.compression_enabled,
                    "memory_mapping_enabled": pool.memory_mapping_enabled,
                    "compressed_blocks": sum(1 for b in pool.blocks.values() if b.is_compressed),
                    "memory_mapped_blocks": sum(1 for b in pool.blocks.values() if b.is_memory_mapped)
                }
            
            return {
                "timestamp": datetime.now().isoformat(),
                "system_memory": metrics.to_dict(),
                "memory_pools": pool_details,
                "total_allocated_gb": self.total_allocated_bytes / (1024**3),
                "max_usable_ram_gb": self.max_usable_ram_gb,
                "memory_strategy": self.memory_strategy.value,
                "statistics": self.stats.copy(),
                "monitoring_active": self.monitoring_active,
                "memory_mapped_files": len(self.memory_mapped_files),
                "temp_directory": str(self.temp_dir)
            }
            
        except Exception as e:
            self.logger.error(f"Error generating memory report: {e}")
            return {"error": str(e)}
    
    def cleanup(self):
        """Cleanup Memory-Manager"""
        
        try:
            # Stoppe Monitoring
            self.stop_monitoring()
            
            # Cleanup alle Memory-Pools
            for pool_id in list(self.memory_pools.keys()):
                pool = self.memory_pools[pool_id]
                
                # Cleanup alle Blocks
                for block_id in list(pool.blocks.keys()):
                    self.deallocate_memory(pool_id, block_id)
                
                del self.memory_pools[pool_id]
            
            # Cleanup Memory-Mapped Files
            for mm in self.memory_mapped_files.values():
                mm.close()
            self.memory_mapped_files.clear()
            
            # Cleanup Temp-Directory
            if self.temp_dir.exists():
                for file_path in self.temp_dir.glob("*.mmap"):
                    file_path.unlink()
            
            # Finale Garbage Collection
            gc.collect()
            
            self.logger.info("Memory manager cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during memory manager cleanup: {e}")


# Utility-Funktionen für Memory-Management
def create_optimized_memory_config(total_ram_gb: float) -> Dict[str, Any]:
    """Erstelle optimierte Memory-Konfiguration basierend auf verfügbarer RAM"""
    
    if total_ram_gb >= 128:  # 128GB+ (High-End System)
        return {
            "memory_strategy": "aggressive",
            "max_ram_usage_percent": 90.0,
            "enable_compression": True,
            "enable_memory_mapping": True,
            "enable_numa": True,
            "gc_threshold": 0.90,
            "leak_detection": True
        }
    elif total_ram_gb >= 64:  # 64-128GB (Mid-High System)
        return {
            "memory_strategy": "balanced",
            "max_ram_usage_percent": 85.0,
            "enable_compression": True,
            "enable_memory_mapping": True,
            "enable_numa": True,
            "gc_threshold": 0.85,
            "leak_detection": True
        }
    elif total_ram_gb >= 32:  # 32-64GB (Mid System)
        return {
            "memory_strategy": "balanced",
            "max_ram_usage_percent": 80.0,
            "enable_compression": True,
            "enable_memory_mapping": False,
            "enable_numa": False,
            "gc_threshold": 0.80,
            "leak_detection": True
        }
    else:  # < 32GB (Low-End System)
        return {
            "memory_strategy": "conservative",
            "max_ram_usage_percent": 70.0,
            "enable_compression": False,
            "enable_memory_mapping": False,
            "enable_numa": False,
            "gc_threshold": 0.75,
            "leak_detection": False
        }


def get_192gb_optimal_config() -> Dict[str, Any]:
    """Erhalte optimale Konfiguration für 192GB RAM-System"""
    
    return {
        "memory_strategy": "aggressive",
        "max_ram_usage_percent": 95.0,
        "enable_compression": True,
        "enable_memory_mapping": True,
        "enable_numa": True,
        "gc_threshold": 0.92,
        "leak_detection": True,
        "temp_dir": "/tmp/ai_optimizer_memory_192gb",
        "pool_configurations": {
            "cache": {"size_percent": 35, "strategy": "lru"},
            "buffer": {"size_percent": 25, "strategy": "fifo"},
            "temporary": {"size_percent": 20, "strategy": "lru"},
            "persistent": {"size_percent": 20, "strategy": "lfu"}
        }
    }