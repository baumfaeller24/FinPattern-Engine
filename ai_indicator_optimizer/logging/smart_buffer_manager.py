#!/usr/bin/env python3
"""
Smart Buffer Manager - Groks Empfehlung umgesetzt
Dynamische Buffer-Anpassung basierend auf RAM-Usage und System-Performance

Features:
- Intelligente Buffer-Größen-Anpassung basierend auf verfügbarem RAM
- Memory-Pressure-Detection mit automatischem Flush
- Performance-Monitoring für optimale Throughput
- Integration mit Hardware-Monitoring aus Task 15
"""

import psutil
import time
import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime


@dataclass
class BufferMetrics:
    """Metrics für Buffer-Performance-Tracking"""
    current_size: int
    max_size: int
    memory_usage_mb: float
    memory_pressure: float  # 0.0 - 1.0
    flush_frequency: float  # flushes per minute
    avg_flush_time: float   # seconds
    last_flush_timestamp: float


class SmartBufferManager:
    """
    Groks Smart-Flush-Agent Implementation
    
    Dynamische Buffer-Anpassung basierend auf:
    - Verfügbarer RAM
    - Memory-Pressure
    - System-Performance
    - Flush-Latenz
    """
    
    def __init__(
        self,
        initial_buffer_size: int = 5000,
        min_buffer_size: int = 1000,
        max_buffer_size: int = 50000,
        memory_threshold: float = 0.8,  # 80% RAM-Usage
        pressure_threshold: float = 0.7,  # 70% Memory-Pressure
        performance_window: int = 10,  # Letzte 10 Flushes für Performance-Calc
        logger: Optional[Callable[[str], None]] = None
    ):
        self.current_buffer_size = initial_buffer_size
        self.min_size = min_buffer_size
        self.max_size = max_buffer_size
        self.memory_threshold = memory_threshold
        self.pressure_threshold = pressure_threshold
        self.performance_window = performance_window
        
        # Performance Tracking
        self.flush_times = []
        self.flush_timestamps = []
        self.total_flushes = 0
        
        # System Monitoring
        self.last_memory_check = 0
        self.memory_check_interval = 5.0  # seconds
        
        # Logging
        self._log = logger or (lambda msg: logging.getLogger(__name__).info(msg))
        
        self._log(f"SmartBufferManager initialized: {initial_buffer_size} → {min_buffer_size}-{max_buffer_size}")
    
    def should_flush(self, current_buffer_length: int) -> bool:
        """
        Intelligente Flush-Entscheidung basierend auf:
        - Buffer-Größe
        - Memory-Pressure
        - System-Performance
        """
        # Standard Buffer-Size Check
        if current_buffer_length >= self.current_buffer_size:
            return True
        
        # Memory-Pressure Check (nur alle 5 Sekunden für Performance)
        now = time.time()
        if now - self.last_memory_check > self.memory_check_interval:
            self.last_memory_check = now
            
            memory_info = psutil.virtual_memory()
            memory_pressure = memory_info.percent / 100.0
            
            # Aggressive Flush bei hohem Memory-Pressure
            if memory_pressure > self.pressure_threshold:
                self._log(f"Memory pressure detected: {memory_pressure:.1%} → forcing flush")
                return True
            
            # Adaptive Buffer-Size basierend auf Memory-Usage
            self._adapt_buffer_size(memory_pressure)
        
        return False
    
    def record_flush(self, flush_time: float, buffer_size: int) -> None:
        """
        Zeichne Flush-Performance auf für adaptive Optimierung
        """
        self.flush_times.append(flush_time)
        self.flush_timestamps.append(time.time())
        self.total_flushes += 1
        
        # Behalte nur letzte N Flushes für Performance-Calc
        if len(self.flush_times) > self.performance_window:
            self.flush_times.pop(0)
            self.flush_timestamps.pop(0)
        
        # Performance-basierte Buffer-Anpassung
        if len(self.flush_times) >= 3:  # Mindestens 3 Samples
            avg_flush_time = sum(self.flush_times) / len(self.flush_times)
            
            # Wenn Flushes zu langsam werden, reduziere Buffer-Size
            if avg_flush_time > 2.0:  # > 2 Sekunden
                self._reduce_buffer_size("slow flush performance")
            elif avg_flush_time < 0.5 and self.current_buffer_size < self.max_size:
                self._increase_buffer_size("fast flush performance")
    
    def _adapt_buffer_size(self, memory_pressure: float) -> None:
        """
        Adaptive Buffer-Größen-Anpassung basierend auf Memory-Pressure
        """
        if memory_pressure > self.memory_threshold:
            # Hoher Memory-Usage → kleinere Buffer
            self._reduce_buffer_size(f"high memory pressure: {memory_pressure:.1%}")
        elif memory_pressure < 0.5 and self.current_buffer_size < self.max_size:
            # Niedriger Memory-Usage → größere Buffer für bessere Performance
            self._increase_buffer_size(f"low memory pressure: {memory_pressure:.1%}")
    
    def _reduce_buffer_size(self, reason: str) -> None:
        """Reduziere Buffer-Größe intelligent"""
        old_size = self.current_buffer_size
        # Reduziere um 20%, aber nicht unter Minimum
        new_size = max(self.min_size, int(self.current_buffer_size * 0.8))
        
        if new_size != old_size:
            self.current_buffer_size = new_size
            self._log(f"Buffer size reduced: {old_size} → {new_size} ({reason})")
    
    def _increase_buffer_size(self, reason: str) -> None:
        """Erhöhe Buffer-Größe intelligent"""
        old_size = self.current_buffer_size
        # Erhöhe um 25%, aber nicht über Maximum
        new_size = min(self.max_size, int(self.current_buffer_size * 1.25))
        
        if new_size != old_size:
            self.current_buffer_size = new_size
            self._log(f"Buffer size increased: {old_size} → {new_size} ({reason})")
    
    def get_metrics(self) -> BufferMetrics:
        """
        Erhalte aktuelle Buffer-Metriken für Monitoring
        """
        memory_info = psutil.virtual_memory()
        
        # Berechne Flush-Frequency (Flushes pro Minute)
        flush_frequency = 0.0
        if len(self.flush_timestamps) >= 2:
            time_span = self.flush_timestamps[-1] - self.flush_timestamps[0]
            if time_span > 0:
                flush_frequency = (len(self.flush_timestamps) - 1) / time_span * 60
        
        # Durchschnittliche Flush-Zeit
        avg_flush_time = 0.0
        if self.flush_times:
            avg_flush_time = sum(self.flush_times) / len(self.flush_times)
        
        return BufferMetrics(
            current_size=self.current_buffer_size,
            max_size=self.max_size,
            memory_usage_mb=memory_info.used / (1024**2),
            memory_pressure=memory_info.percent / 100.0,
            flush_frequency=flush_frequency,
            avg_flush_time=avg_flush_time,
            last_flush_timestamp=self.flush_timestamps[-1] if self.flush_timestamps else 0.0
        )
    
    def get_recommended_buffer_size(self) -> int:
        """
        Erhalte aktuelle empfohlene Buffer-Größe
        """
        return self.current_buffer_size
    
    def reset_performance_tracking(self) -> None:
        """
        Reset Performance-Tracking (z.B. nach System-Changes)
        """
        self.flush_times.clear()
        self.flush_timestamps.clear()
        self._log("Performance tracking reset")


class EnhancedBufferLogger:
    """
    Enhanced Logger mit Smart Buffer Management
    Kombiniert bestehende Logging-Infrastruktur mit Groks Smart-Flush-Agent
    """
    
    def __init__(
        self,
        base_logger,  # RotatingParquetLogger oder FeaturePredictionLogger
        smart_manager: Optional[SmartBufferManager] = None
    ):
        self.base_logger = base_logger
        self.smart_manager = smart_manager or SmartBufferManager()
        self.logger = logging.getLogger(__name__)
        
        # Override base logger's buffer size with smart manager
        if hasattr(base_logger, 'buffer_size'):
            base_logger.buffer_size = self.smart_manager.get_recommended_buffer_size()
    
    def log(self, **kwargs) -> None:
        """
        Enhanced Logging mit Smart Buffer Management
        """
        # Standard Logging
        self.base_logger.log(**kwargs)
        
        # Check if smart flush is needed
        current_buffer_length = len(getattr(self.base_logger, 'buffer', []))
        
        if self.smart_manager.should_flush(current_buffer_length):
            self._smart_flush()
    
    def _smart_flush(self) -> None:
        """
        Intelligenter Flush mit Performance-Tracking
        """
        start_time = time.time()
        buffer_size = len(getattr(self.base_logger, 'buffer', []))
        
        try:
            # Führe Flush aus
            success = self.base_logger.flush()
            
            if success:
                flush_time = time.time() - start_time
                self.smart_manager.record_flush(flush_time, buffer_size)
                
                # Update base logger's buffer size
                if hasattr(self.base_logger, 'buffer_size'):
                    self.base_logger.buffer_size = self.smart_manager.get_recommended_buffer_size()
                
                self.logger.debug(f"Smart flush completed: {buffer_size} entries in {flush_time:.3f}s")
            
        except Exception as e:
            self.logger.error(f"Smart flush failed: {e}")
    
    def get_smart_metrics(self) -> Dict[str, Any]:
        """
        Erhalte Smart Buffer Metriken
        """
        metrics = self.smart_manager.get_metrics()
        base_stats = getattr(self.base_logger, 'get_stats', lambda: {})()
        
        return {
            "smart_buffer": {
                "current_size": metrics.current_size,
                "max_size": metrics.max_size,
                "memory_pressure": metrics.memory_pressure,
                "flush_frequency": metrics.flush_frequency,
                "avg_flush_time": metrics.avg_flush_time
            },
            "base_logger": base_stats
        }
    
    def close(self) -> None:
        """
        Schließe Enhanced Logger
        """
        self.base_logger.close()
        
        # Log final metrics
        metrics = self.get_smart_metrics()
        self.logger.info(f"EnhancedBufferLogger closed. Final metrics: {metrics}")


# Factory Functions
def create_smart_feature_logger(
    output_path: str = "logs/smart_ai_features.parquet",
    initial_buffer_size: int = 5000,
    **kwargs
) -> EnhancedBufferLogger:
    """
    Factory für Smart Feature Logger mit Groks Buffer-Management
    """
    from .feature_prediction_logger import create_feature_logger
    
    base_logger = create_feature_logger(output_path, buffer_size=initial_buffer_size, **kwargs)
    smart_manager = SmartBufferManager(initial_buffer_size=initial_buffer_size)
    
    return EnhancedBufferLogger(base_logger, smart_manager)


def create_smart_rotating_logger(
    base_path: str = "logs/smart_rotating",
    initial_buffer_size: int = 2000,
    **kwargs
) -> EnhancedBufferLogger:
    """
    Factory für Smart Rotating Logger mit Groks Buffer-Management
    """
    from .rotating_parquet_logger import create_rotating_logger
    
    base_logger = create_rotating_logger(base_path, buffer_size=initial_buffer_size, **kwargs)
    smart_manager = SmartBufferManager(initial_buffer_size=initial_buffer_size)
    
    return EnhancedBufferLogger(base_logger, smart_manager)


if __name__ == "__main__":
    # Test Smart Buffer Manager
    import time
    
    print("🧪 Testing SmartBufferManager...")
    
    # Test Smart Buffer Manager
    manager = SmartBufferManager(initial_buffer_size=100, min_buffer_size=50, max_buffer_size=500)
    
    # Simuliere verschiedene Flush-Szenarien
    for i in range(10):
        # Simuliere langsame Flushes
        flush_time = 0.1 + (i * 0.1)  # Wird langsamer
        manager.record_flush(flush_time, 100)
        
        print(f"Flush {i+1}: {flush_time:.2f}s → Buffer size: {manager.get_recommended_buffer_size()}")
        
        time.sleep(0.1)
    
    # Zeige finale Metriken
    metrics = manager.get_metrics()
    print(f"📊 Final Metrics:")
    print(f"  Buffer Size: {metrics.current_size}")
    print(f"  Memory Pressure: {metrics.memory_pressure:.1%}")
    print(f"  Flush Frequency: {metrics.flush_frequency:.1f}/min")
    print(f"  Avg Flush Time: {metrics.avg_flush_time:.3f}s")
    
    print("✅ SmartBufferManager Test completed!")