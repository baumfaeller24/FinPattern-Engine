#!/usr/bin/env python3
"""
Resource Monitor für Real-time CPU/GPU/RAM-Tracking
Phase 3 Implementation - Task 11

Features:
- Real-time Hardware-Monitoring (CPU, GPU, RAM, Disk)
- Performance-Metriken und Alerting
- Hardware-spezifische Optimierung für Ryzen 9 9950X + RTX 5090
- Multi-Threading für kontinuierliches Monitoring
- Integration mit AI-Workloads
- Predictive Resource-Management
"""

import psutil
import threading
import time
import json
import logging
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import numpy as np
from collections import deque
import queue

# GPU Monitoring
try:
    import GPUtil
    import pynvml
    pynvml.nvmlInit()
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False

# Advanced System Monitoring
try:
    import sensors  # lm-sensors für Temperatur-Monitoring
    SENSORS_AVAILABLE = True
except ImportError:
    SENSORS_AVAILABLE = False


class ResourceType(Enum):
    """Typen von Hardware-Ressourcen"""
    CPU = "cpu"
    GPU = "gpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    TEMPERATURE = "temperature"


class AlertLevel(Enum):
    """Alert-Level für Resource-Monitoring"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class ResourceMetrics:
    """Metriken für eine Hardware-Ressource"""
    resource_type: ResourceType
    timestamp: datetime
    
    # CPU Metriken
    cpu_percent: float = 0.0
    cpu_cores_usage: List[float] = field(default_factory=list)
    cpu_frequency: float = 0.0
    cpu_temperature: float = 0.0
    
    # GPU Metriken
    gpu_percent: float = 0.0
    gpu_memory_used: float = 0.0
    gpu_memory_total: float = 0.0
    gpu_temperature: float = 0.0
    gpu_power_draw: float = 0.0
    
    # Memory Metriken
    memory_percent: float = 0.0
    memory_used: float = 0.0
    memory_total: float = 0.0
    memory_available: float = 0.0
    swap_percent: float = 0.0
    
    # Disk Metriken
    disk_usage_percent: float = 0.0
    disk_read_speed: float = 0.0
    disk_write_speed: float = 0.0
    
    # Network Metriken
    network_sent: float = 0.0
    network_recv: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiere zu Dictionary"""
        return {
            "resource_type": self.resource_type.value,
            "timestamp": self.timestamp.isoformat(),
            "cpu_percent": self.cpu_percent,
            "cpu_cores_usage": self.cpu_cores_usage,
            "cpu_frequency": self.cpu_frequency,
            "cpu_temperature": self.cpu_temperature,
            "gpu_percent": self.gpu_percent,
            "gpu_memory_used": self.gpu_memory_used,
            "gpu_memory_total": self.gpu_memory_total,
            "gpu_temperature": self.gpu_temperature,
            "gpu_power_draw": self.gpu_power_draw,
            "memory_percent": self.memory_percent,
            "memory_used": self.memory_used,
            "memory_total": self.memory_total,
            "memory_available": self.memory_available,
            "swap_percent": self.swap_percent,
            "disk_usage_percent": self.disk_usage_percent,
            "disk_read_speed": self.disk_read_speed,
            "disk_write_speed": self.disk_write_speed,
            "network_sent": self.network_sent,
            "network_recv": self.network_recv
        }


@dataclass
class ResourceAlert:
    """Alert für Resource-Überschreitung"""
    alert_level: AlertLevel
    resource_type: ResourceType
    message: str
    value: float
    threshold: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_level": self.alert_level.value,
            "resource_type": self.resource_type.value,
            "message": self.message,
            "value": self.value,
            "threshold": self.threshold,
            "timestamp": self.timestamp.isoformat()
        }


class ResourceMonitor:
    """
    Real-time Hardware Resource Monitor
    
    Features:
    - Kontinuierliches CPU/GPU/RAM-Monitoring
    - Performance-Alerting und Threshold-Management
    - Hardware-spezifische Optimierung
    - Predictive Resource-Management
    - Integration mit AI-Workloads
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Monitoring-Konfiguration
        self.monitoring_interval = self.config.get("monitoring_interval", 1.0)  # Sekunden
        self.history_size = self.config.get("history_size", 3600)  # 1 Stunde bei 1s Intervall
        self.enable_alerts = self.config.get("enable_alerts", True)
        
        # Hardware-spezifische Konfiguration (Ryzen 9 9950X + RTX 5090)
        self.cpu_cores = self.config.get("cpu_cores", 32)  # 16 Kerne, 32 Threads
        self.expected_gpu_memory = self.config.get("gpu_memory_gb", 32)  # RTX 5090: 32GB
        self.expected_system_memory = self.config.get("system_memory_gb", 192)  # 192GB RAM
        
        # Monitoring-State
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.metrics_history: deque = deque(maxlen=self.history_size)
        self.alerts_queue: queue.Queue = queue.Queue()
        
        # Alert-Thresholds
        self.alert_thresholds = self._setup_alert_thresholds()
        
        # Performance-Tracking
        self.stats = {
            "monitoring_uptime": 0.0,
            "total_metrics_collected": 0,
            "alerts_generated": 0,
            "avg_cpu_usage": 0.0,
            "avg_gpu_usage": 0.0,
            "avg_memory_usage": 0.0,
            "peak_cpu_usage": 0.0,
            "peak_gpu_usage": 0.0,
            "peak_memory_usage": 0.0
        }
        
        # Hardware-Detection
        self.hardware_info = self._detect_hardware()
        
        self.logger.info("ResourceMonitor initialized")
        self.logger.info(f"Detected Hardware: {self.hardware_info}")
    
    def start_monitoring(self):
        """Starte kontinuierliches Resource-Monitoring"""
        
        if self.monitoring_active:
            self.logger.warning("Monitoring already active")
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            name="ResourceMonitor",
            daemon=True
        )
        self.monitoring_thread.start()
        
        self.logger.info(f"Resource monitoring started (interval: {self.monitoring_interval}s)")
    
    def stop_monitoring(self):
        """Stoppe Resource-Monitoring"""
        
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5.0)
        
        self.logger.info("Resource monitoring stopped")
    
    def get_current_metrics(self) -> ResourceMetrics:
        """Erhalte aktuelle Resource-Metriken"""
        
        try:
            current_time = datetime.now()
            
            # CPU Metriken
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_cores_usage = psutil.cpu_percent(interval=0.1, percpu=True)
            cpu_freq = psutil.cpu_freq()
            cpu_frequency = cpu_freq.current if cpu_freq else 0.0
            
            # CPU Temperatur (falls verfügbar)
            cpu_temperature = self._get_cpu_temperature()
            
            # GPU Metriken
            gpu_metrics = self._get_gpu_metrics()
            
            # Memory Metriken
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk Metriken
            disk_usage = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            
            # Network Metriken
            network_io = psutil.net_io_counters()
            
            metrics = ResourceMetrics(
                resource_type=ResourceType.CPU,  # Wird für alle Ressourcen verwendet
                timestamp=current_time,
                
                # CPU
                cpu_percent=cpu_percent,
                cpu_cores_usage=cpu_cores_usage,
                cpu_frequency=cpu_frequency,
                cpu_temperature=cpu_temperature,
                
                # GPU
                gpu_percent=gpu_metrics.get("utilization", 0.0),
                gpu_memory_used=gpu_metrics.get("memory_used", 0.0),
                gpu_memory_total=gpu_metrics.get("memory_total", 0.0),
                gpu_temperature=gpu_metrics.get("temperature", 0.0),
                gpu_power_draw=gpu_metrics.get("power_draw", 0.0),
                
                # Memory
                memory_percent=memory.percent,
                memory_used=memory.used / (1024**3),  # GB
                memory_total=memory.total / (1024**3),  # GB
                memory_available=memory.available / (1024**3),  # GB
                swap_percent=swap.percent,
                
                # Disk
                disk_usage_percent=disk_usage.percent,
                disk_read_speed=disk_io.read_bytes / (1024**2) if disk_io else 0.0,  # MB/s
                disk_write_speed=disk_io.write_bytes / (1024**2) if disk_io else 0.0,  # MB/s
                
                # Network
                network_sent=network_io.bytes_sent / (1024**2) if network_io else 0.0,  # MB
                network_recv=network_io.bytes_recv / (1024**2) if network_io else 0.0   # MB
            )
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error collecting metrics: {e}")
            return ResourceMetrics(
                resource_type=ResourceType.CPU,
                timestamp=datetime.now()
            )
    
    def _monitoring_loop(self):
        """Haupt-Monitoring-Loop"""
        
        start_time = datetime.now()
        
        while self.monitoring_active:
            try:
                # Aktuelle Metriken sammeln
                metrics = self.get_current_metrics()
                
                # Zu Historie hinzufügen
                self.metrics_history.append(metrics)
                
                # Alerts prüfen
                if self.enable_alerts:
                    self._check_alerts(metrics)
                
                # Statistiken updaten
                self._update_stats(metrics)
                
                # Warte bis zum nächsten Intervall
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                time.sleep(self.monitoring_interval)
        
        # Uptime berechnen
        self.stats["monitoring_uptime"] = (datetime.now() - start_time).total_seconds()
    
    def _get_gpu_metrics(self) -> Dict[str, float]:
        """Erhalte GPU-Metriken"""
        
        gpu_metrics = {
            "utilization": 0.0,
            "memory_used": 0.0,
            "memory_total": 0.0,
            "temperature": 0.0,
            "power_draw": 0.0
        }
        
        if not GPU_AVAILABLE:
            return gpu_metrics
        
        try:
            # NVIDIA GPU Metriken mit pynvml
            device_count = pynvml.nvmlDeviceGetCount()
            
            if device_count > 0:
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)  # Erste GPU
                
                # GPU Utilization
                utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
                gpu_metrics["utilization"] = utilization.gpu
                
                # Memory Info
                memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                gpu_metrics["memory_used"] = memory_info.used / (1024**3)  # GB
                gpu_metrics["memory_total"] = memory_info.total / (1024**3)  # GB
                
                # Temperatur
                try:
                    temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                    gpu_metrics["temperature"] = temperature
                except:
                    pass
                
                # Power Draw
                try:
                    power_draw = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # Watt
                    gpu_metrics["power_draw"] = power_draw
                except:
                    pass
            
        except Exception as e:
            self.logger.debug(f"GPU metrics error: {e}")
        
        return gpu_metrics
    
    def _get_cpu_temperature(self) -> float:
        """Erhalte CPU-Temperatur"""
        
        try:
            if SENSORS_AVAILABLE:
                # Verwende lm-sensors für Temperatur
                temps = psutil.sensors_temperatures()
                
                # Suche nach CPU-Temperatur
                for name, entries in temps.items():
                    if 'cpu' in name.lower() or 'core' in name.lower():
                        if entries:
                            return entries[0].current
            
            # Fallback: Versuche über /sys/class/thermal
            thermal_zones = Path("/sys/class/thermal").glob("thermal_zone*")
            for zone in thermal_zones:
                try:
                    temp_file = zone / "temp"
                    if temp_file.exists():
                        temp_raw = int(temp_file.read_text().strip())
                        return temp_raw / 1000.0  # milli-Celsius zu Celsius
                except:
                    continue
                    
        except Exception as e:
            self.logger.debug(f"CPU temperature error: {e}")
        
        return 0.0
    
    def _check_alerts(self, metrics: ResourceMetrics):
        """Prüfe Alert-Thresholds"""
        
        alerts = []
        
        # CPU Alerts
        if metrics.cpu_percent > self.alert_thresholds["cpu"]["critical"]:
            alerts.append(ResourceAlert(
                alert_level=AlertLevel.CRITICAL,
                resource_type=ResourceType.CPU,
                message=f"CPU usage critical: {metrics.cpu_percent:.1f}%",
                value=metrics.cpu_percent,
                threshold=self.alert_thresholds["cpu"]["critical"]
            ))
        elif metrics.cpu_percent > self.alert_thresholds["cpu"]["warning"]:
            alerts.append(ResourceAlert(
                alert_level=AlertLevel.WARNING,
                resource_type=ResourceType.CPU,
                message=f"CPU usage high: {metrics.cpu_percent:.1f}%",
                value=metrics.cpu_percent,
                threshold=self.alert_thresholds["cpu"]["warning"]
            ))
        
        # GPU Alerts
        if metrics.gpu_percent > self.alert_thresholds["gpu"]["critical"]:
            alerts.append(ResourceAlert(
                alert_level=AlertLevel.CRITICAL,
                resource_type=ResourceType.GPU,
                message=f"GPU usage critical: {metrics.gpu_percent:.1f}%",
                value=metrics.gpu_percent,
                threshold=self.alert_thresholds["gpu"]["critical"]
            ))
        
        # Memory Alerts
        if metrics.memory_percent > self.alert_thresholds["memory"]["critical"]:
            alerts.append(ResourceAlert(
                alert_level=AlertLevel.CRITICAL,
                resource_type=ResourceType.MEMORY,
                message=f"Memory usage critical: {metrics.memory_percent:.1f}%",
                value=metrics.memory_percent,
                threshold=self.alert_thresholds["memory"]["critical"]
            ))
        
        # Temperature Alerts
        if metrics.cpu_temperature > self.alert_thresholds["temperature"]["critical"]:
            alerts.append(ResourceAlert(
                alert_level=AlertLevel.CRITICAL,
                resource_type=ResourceType.TEMPERATURE,
                message=f"CPU temperature critical: {metrics.cpu_temperature:.1f}°C",
                value=metrics.cpu_temperature,
                threshold=self.alert_thresholds["temperature"]["critical"]
            ))
        
        if metrics.gpu_temperature > self.alert_thresholds["temperature"]["critical"]:
            alerts.append(ResourceAlert(
                alert_level=AlertLevel.CRITICAL,
                resource_type=ResourceType.TEMPERATURE,
                message=f"GPU temperature critical: {metrics.gpu_temperature:.1f}°C",
                value=metrics.gpu_temperature,
                threshold=self.alert_thresholds["temperature"]["critical"]
            ))
        
        # Alerts zur Queue hinzufügen
        for alert in alerts:
            self.alerts_queue.put(alert)
            self.stats["alerts_generated"] += 1
            self.logger.warning(f"Resource Alert: {alert.message}")
    
    def _update_stats(self, metrics: ResourceMetrics):
        """Update Performance-Statistiken"""
        
        self.stats["total_metrics_collected"] += 1
        
        # Durchschnittswerte berechnen
        count = self.stats["total_metrics_collected"]
        
        self.stats["avg_cpu_usage"] = (
            (self.stats["avg_cpu_usage"] * (count - 1) + metrics.cpu_percent) / count
        )
        
        self.stats["avg_gpu_usage"] = (
            (self.stats["avg_gpu_usage"] * (count - 1) + metrics.gpu_percent) / count
        )
        
        self.stats["avg_memory_usage"] = (
            (self.stats["avg_memory_usage"] * (count - 1) + metrics.memory_percent) / count
        )
        
        # Peak-Werte
        self.stats["peak_cpu_usage"] = max(self.stats["peak_cpu_usage"], metrics.cpu_percent)
        self.stats["peak_gpu_usage"] = max(self.stats["peak_gpu_usage"], metrics.gpu_percent)
        self.stats["peak_memory_usage"] = max(self.stats["peak_memory_usage"], metrics.memory_percent)
    
    def _setup_alert_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Setup Alert-Thresholds für verschiedene Ressourcen"""
        
        return {
            "cpu": {
                "warning": 80.0,    # 80% CPU Usage
                "critical": 95.0    # 95% CPU Usage
            },
            "gpu": {
                "warning": 85.0,    # 85% GPU Usage
                "critical": 98.0    # 98% GPU Usage
            },
            "memory": {
                "warning": 85.0,    # 85% Memory Usage
                "critical": 95.0    # 95% Memory Usage
            },
            "temperature": {
                "warning": 75.0,    # 75°C
                "critical": 85.0    # 85°C
            },
            "disk": {
                "warning": 85.0,    # 85% Disk Usage
                "critical": 95.0    # 95% Disk Usage
            }
        }
    
    def _detect_hardware(self) -> Dict[str, Any]:
        """Erkenne Hardware-Konfiguration"""
        
        hardware_info = {
            "cpu_cores": psutil.cpu_count(logical=False),
            "cpu_threads": psutil.cpu_count(logical=True),
            "memory_total_gb": psutil.virtual_memory().total / (1024**3),
            "gpu_available": GPU_AVAILABLE,
            "gpu_count": 0,
            "gpu_memory_total": 0.0
        }
        
        # CPU Info
        try:
            cpu_freq = psutil.cpu_freq()
            if cpu_freq:
                hardware_info["cpu_base_frequency"] = cpu_freq.current
                hardware_info["cpu_max_frequency"] = cpu_freq.max
        except:
            pass
        
        # GPU Info
        if GPU_AVAILABLE:
            try:
                device_count = pynvml.nvmlDeviceGetCount()
                hardware_info["gpu_count"] = device_count
                
                if device_count > 0:
                    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    gpu_name = pynvml.nvmlDeviceGetName(handle).decode('utf-8')
                    memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    
                    hardware_info["gpu_name"] = gpu_name
                    hardware_info["gpu_memory_total"] = memory_info.total / (1024**3)  # GB
            except Exception as e:
                self.logger.debug(f"GPU detection error: {e}")
        
        return hardware_info    

    def get_metrics_history(self, duration_minutes: int = 60) -> List[ResourceMetrics]:
        """Erhalte Metriken-Historie für bestimmte Dauer"""
        
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        
        return [
            metrics for metrics in self.metrics_history
            if metrics.timestamp >= cutoff_time
        ]
    
    def get_alerts(self, max_alerts: int = 100) -> List[ResourceAlert]:
        """Erhalte aktuelle Alerts"""
        
        alerts = []
        
        try:
            while not self.alerts_queue.empty() and len(alerts) < max_alerts:
                alert = self.alerts_queue.get_nowait()
                alerts.append(alert)
        except queue.Empty:
            pass
        
        return alerts
    
    def get_resource_summary(self) -> Dict[str, Any]:
        """Erhalte Resource-Summary"""
        
        current_metrics = self.get_current_metrics()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "monitoring_active": self.monitoring_active,
            "hardware_info": self.hardware_info,
            "current_usage": {
                "cpu_percent": current_metrics.cpu_percent,
                "cpu_cores_usage": current_metrics.cpu_cores_usage,
                "gpu_percent": current_metrics.gpu_percent,
                "gpu_memory_percent": (
                    (current_metrics.gpu_memory_used / current_metrics.gpu_memory_total * 100)
                    if current_metrics.gpu_memory_total > 0 else 0
                ),
                "memory_percent": current_metrics.memory_percent,
                "disk_usage_percent": current_metrics.disk_usage_percent
            },
            "temperatures": {
                "cpu_temperature": current_metrics.cpu_temperature,
                "gpu_temperature": current_metrics.gpu_temperature
            },
            "statistics": self.stats,
            "alert_thresholds": self.alert_thresholds
        }
    
    def predict_resource_usage(self, minutes_ahead: int = 30) -> Dict[str, float]:
        """Vorhersage der Resource-Nutzung basierend auf Historie"""
        
        try:
            if len(self.metrics_history) < 10:
                return {"error": "Insufficient data for prediction"}
            
            # Letzte Metriken für Trend-Analyse
            recent_metrics = list(self.metrics_history)[-60:]  # Letzte 60 Messungen
            
            # CPU Trend
            cpu_values = [m.cpu_percent for m in recent_metrics]
            cpu_trend = np.polyfit(range(len(cpu_values)), cpu_values, 1)[0]
            cpu_prediction = cpu_values[-1] + (cpu_trend * minutes_ahead)
            
            # GPU Trend
            gpu_values = [m.gpu_percent for m in recent_metrics]
            gpu_trend = np.polyfit(range(len(gpu_values)), gpu_values, 1)[0]
            gpu_prediction = gpu_values[-1] + (gpu_trend * minutes_ahead)
            
            # Memory Trend
            memory_values = [m.memory_percent for m in recent_metrics]
            memory_trend = np.polyfit(range(len(memory_values)), memory_values, 1)[0]
            memory_prediction = memory_values[-1] + (memory_trend * minutes_ahead)
            
            return {
                "prediction_minutes_ahead": minutes_ahead,
                "predicted_cpu_percent": max(0, min(100, cpu_prediction)),
                "predicted_gpu_percent": max(0, min(100, gpu_prediction)),
                "predicted_memory_percent": max(0, min(100, memory_prediction)),
                "cpu_trend": cpu_trend,
                "gpu_trend": gpu_trend,
                "memory_trend": memory_trend
            }
            
        except Exception as e:
            self.logger.error(f"Prediction error: {e}")
            return {"error": str(e)}
    
    def optimize_for_ai_workload(self) -> Dict[str, Any]:
        """Optimiere System für AI-Workloads"""
        
        recommendations = []
        current_metrics = self.get_current_metrics()
        
        # CPU Optimierung
        if current_metrics.cpu_percent > 80:
            recommendations.append({
                "type": "cpu",
                "priority": "high",
                "message": "CPU usage high - consider reducing parallel processes",
                "action": "reduce_cpu_load"
            })
        elif current_metrics.cpu_percent < 30:
            recommendations.append({
                "type": "cpu",
                "priority": "low",
                "message": "CPU underutilized - can increase parallel processing",
                "action": "increase_cpu_load"
            })
        
        # GPU Optimierung
        if current_metrics.gpu_percent < 70 and current_metrics.gpu_memory_used > 0:
            recommendations.append({
                "type": "gpu",
                "priority": "medium",
                "message": "GPU underutilized - increase batch size or model complexity",
                "action": "increase_gpu_utilization"
            })
        
        # Memory Optimierung
        memory_usage_gb = current_metrics.memory_used
        if memory_usage_gb > 150:  # > 150GB von 192GB
            recommendations.append({
                "type": "memory",
                "priority": "high",
                "message": "High memory usage - consider memory optimization",
                "action": "optimize_memory"
            })
        elif memory_usage_gb < 50:  # < 50GB von 192GB
            recommendations.append({
                "type": "memory",
                "priority": "low",
                "message": "Memory underutilized - can increase batch sizes",
                "action": "increase_memory_usage"
            })
        
        # Temperatur-Checks
        if current_metrics.cpu_temperature > 70:
            recommendations.append({
                "type": "temperature",
                "priority": "high",
                "message": f"CPU temperature high: {current_metrics.cpu_temperature:.1f}°C",
                "action": "reduce_cpu_load"
            })
        
        if current_metrics.gpu_temperature > 75:
            recommendations.append({
                "type": "temperature",
                "priority": "high",
                "message": f"GPU temperature high: {current_metrics.gpu_temperature:.1f}°C",
                "action": "reduce_gpu_load"
            })
        
        return {
            "timestamp": datetime.now().isoformat(),
            "recommendations": recommendations,
            "current_metrics": current_metrics.to_dict(),
            "optimization_score": self._calculate_optimization_score(current_metrics)
        }
    
    def _calculate_optimization_score(self, metrics: ResourceMetrics) -> float:
        """Berechne Optimierungs-Score (0-100, höher = besser optimiert)"""
        
        try:
            score = 100.0
            
            # CPU Score (optimal bei 70-85% Nutzung)
            if metrics.cpu_percent < 30:
                score -= (30 - metrics.cpu_percent) * 0.5  # Unterauslastung
            elif metrics.cpu_percent > 90:
                score -= (metrics.cpu_percent - 90) * 2.0  # Überauslastung
            
            # GPU Score (optimal bei 80-95% Nutzung)
            if metrics.gpu_percent < 50:
                score -= (50 - metrics.gpu_percent) * 0.3
            elif metrics.gpu_percent > 98:
                score -= (metrics.gpu_percent - 98) * 3.0
            
            # Memory Score (optimal bei 60-80% Nutzung)
            if metrics.memory_percent < 40:
                score -= (40 - metrics.memory_percent) * 0.2
            elif metrics.memory_percent > 90:
                score -= (metrics.memory_percent - 90) * 2.0
            
            # Temperatur-Penalty
            if metrics.cpu_temperature > 70:
                score -= (metrics.cpu_temperature - 70) * 2.0
            
            if metrics.gpu_temperature > 75:
                score -= (metrics.gpu_temperature - 75) * 2.0
            
            return max(0, min(100, score))
            
        except Exception as e:
            self.logger.error(f"Optimization score calculation error: {e}")
            return 50.0
    
    def export_metrics(self, filepath: str, format: str = "json") -> bool:
        """Exportiere Metriken zu Datei"""
        
        try:
            metrics_data = [metrics.to_dict() for metrics in self.metrics_history]
            
            if format.lower() == "json":
                with open(filepath, 'w') as f:
                    json.dump({
                        "export_timestamp": datetime.now().isoformat(),
                        "hardware_info": self.hardware_info,
                        "statistics": self.stats,
                        "metrics_count": len(metrics_data),
                        "metrics": metrics_data
                    }, f, indent=2)
            
            elif format.lower() == "csv":
                import pandas as pd
                df = pd.DataFrame(metrics_data)
                df.to_csv(filepath, index=False)
            
            self.logger.info(f"Metrics exported to {filepath} ({format})")
            return True
            
        except Exception as e:
            self.logger.error(f"Export error: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Erhalte Monitor-Statistiken"""
        
        return {
            **self.stats,
            "monitoring_active": self.monitoring_active,
            "metrics_history_size": len(self.metrics_history),
            "alerts_in_queue": self.alerts_queue.qsize(),
            "hardware_info": self.hardware_info
        }


# Factory Function
def create_resource_monitor(config: Optional[Dict] = None) -> ResourceMonitor:
    """
    Factory Function für Resource Monitor
    
    Args:
        config: Monitor-Konfiguration
        
    Returns:
        ResourceMonitor Instance
    """
    return ResourceMonitor(config=config)


# Demo/Test Function
def demo_resource_monitor():
    """Demo für Resource Monitor"""
    
    print("🧪 Testing Resource Monitor...")
    
    # Monitor erstellen
    monitor = create_resource_monitor({
        "monitoring_interval": 2.0,  # 2 Sekunden für Demo
        "history_size": 100,
        "enable_alerts": True
    })
    
    # Hardware-Info anzeigen
    hardware_info = monitor.hardware_info
    print(f"\n💻 Detected Hardware:")
    print(f"   CPU: {hardware_info['cpu_threads']} threads ({hardware_info['cpu_cores']} cores)")
    print(f"   Memory: {hardware_info['memory_total_gb']:.1f} GB")
    if hardware_info['gpu_available']:
        print(f"   GPU: {hardware_info.get('gpu_name', 'Unknown')} ({hardware_info['gpu_memory_total']:.1f} GB)")
    else:
        print(f"   GPU: Not available")
    
    # Aktuelle Metriken
    print(f"\n📊 Current Resource Usage:")
    current_metrics = monitor.get_current_metrics()
    
    print(f"   CPU: {current_metrics.cpu_percent:.1f}% ({current_metrics.cpu_temperature:.1f}°C)")
    print(f"   GPU: {current_metrics.gpu_percent:.1f}% ({current_metrics.gpu_temperature:.1f}°C)")
    print(f"   Memory: {current_metrics.memory_percent:.1f}% ({current_metrics.memory_used:.1f}/{current_metrics.memory_total:.1f} GB)")
    print(f"   Disk: {current_metrics.disk_usage_percent:.1f}%")
    
    # Monitoring starten
    print(f"\n🔄 Starting monitoring for 10 seconds...")
    monitor.start_monitoring()
    
    # 10 Sekunden warten
    time.sleep(10)
    
    # Monitoring stoppen
    monitor.stop_monitoring()
    
    # Gesammelte Metriken anzeigen
    history = monitor.get_metrics_history(duration_minutes=1)
    print(f"\n📈 Collected {len(history)} metric samples")
    
    if history:
        avg_cpu = np.mean([m.cpu_percent for m in history])
        avg_gpu = np.mean([m.gpu_percent for m in history])
        avg_memory = np.mean([m.memory_percent for m in history])
        
        print(f"   Average CPU: {avg_cpu:.1f}%")
        print(f"   Average GPU: {avg_gpu:.1f}%")
        print(f"   Average Memory: {avg_memory:.1f}%")
    
    # Alerts prüfen
    alerts = monitor.get_alerts()
    if alerts:
        print(f"\n🚨 Alerts ({len(alerts)}):")
        for alert in alerts[:3]:  # Zeige nur erste 3
            print(f"   {alert.alert_level.value.upper()}: {alert.message}")
    else:
        print(f"\n✅ No alerts generated")
    
    # Resource-Summary
    summary = monitor.get_resource_summary()
    print(f"\n📋 Resource Summary:")
    print(f"   Monitoring Active: {summary['monitoring_active']}")
    print(f"   Current CPU: {summary['current_usage']['cpu_percent']:.1f}%")
    print(f"   Current GPU: {summary['current_usage']['gpu_percent']:.1f}%")
    print(f"   Current Memory: {summary['current_usage']['memory_percent']:.1f}%")
    
    # AI-Workload-Optimierung
    optimization = monitor.optimize_for_ai_workload()
    print(f"\n🎯 AI Workload Optimization:")
    print(f"   Optimization Score: {optimization['optimization_score']:.1f}/100")
    
    if optimization['recommendations']:
        print(f"   Recommendations ({len(optimization['recommendations'])}):")
        for rec in optimization['recommendations'][:3]:
            print(f"     {rec['priority'].upper()}: {rec['message']}")
    else:
        print(f"   No optimization recommendations")
    
    # Vorhersage
    if len(history) >= 5:
        prediction = monitor.predict_resource_usage(minutes_ahead=15)
        if "error" not in prediction:
            print(f"\n🔮 Resource Prediction (15 minutes):")
            print(f"   Predicted CPU: {prediction['predicted_cpu_percent']:.1f}%")
            print(f"   Predicted GPU: {prediction['predicted_gpu_percent']:.1f}%")
            print(f"   Predicted Memory: {prediction['predicted_memory_percent']:.1f}%")
    
    # Statistiken
    stats = monitor.get_statistics()
    print(f"\n📊 Monitor Statistics:")
    print(f"   Metrics Collected: {stats['total_metrics_collected']}")
    print(f"   Alerts Generated: {stats['alerts_generated']}")
    print(f"   Peak CPU Usage: {stats['peak_cpu_usage']:.1f}%")
    print(f"   Peak GPU Usage: {stats['peak_gpu_usage']:.1f}%")
    print(f"   Peak Memory Usage: {stats['peak_memory_usage']:.1f}%")


if __name__ == "__main__":
    demo_resource_monitor()