#!/usr/bin/env python3
"""
Structured Logger für detailliertes Processing-Logging mit Timestamps
Phase 3 Implementation - Task 12

Features:
- Structured JSON-Logging mit detaillierten Timestamps
- Multi-Level-Logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Context-aware Logging mit Correlation-IDs
- Performance-Logging mit Execution-Time-Tracking
- Async-Logging für High-Performance-Scenarios
- Log-Aggregation und Filtering
- Real-time Log-Streaming und Monitoring
"""

import json
import time
import logging
import threading
import asyncio
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
import uuid
import traceback
import sys
import os
from collections import deque, defaultdict
import queue
import gzip
import pickle

# Async-Logging
try:
    import aiofiles
    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False

# Performance-Profiling
try:
    import cProfile
    import pstats
    PROFILING_AVAILABLE = True
except ImportError:
    PROFILING_AVAILABLE = False

# Log-Rotation
try:
    from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
    ROTATION_AVAILABLE = True
except ImportError:
    ROTATION_AVAILABLE = False


class LogLevel(Enum):
    """Log-Level Definitionen"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    PERFORMANCE = "PERFORMANCE"
    AUDIT = "AUDIT"


class LogCategory(Enum):
    """Log-Kategorien für bessere Organisation"""
    SYSTEM = "system"
    TRADING = "trading"
    AI_MODEL = "ai_model"
    DATA_PROCESSING = "data_processing"
    OPTIMIZATION = "optimization"
    HARDWARE = "hardware"
    NETWORK = "network"
    SECURITY = "security"
    USER_ACTION = "user_action"
    PERFORMANCE = "performance"


@dataclass
class LogContext:
    """Logging-Context für Correlation und Tracing"""
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    component: Optional[str] = None
    operation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LogEntry:
    """Strukturierter Log-Eintrag"""
    timestamp: datetime
    level: LogLevel
    category: LogCategory
    message: str
    context: LogContext
    source_file: Optional[str] = None
    source_line: Optional[int] = None
    source_function: Optional[str] = None
    execution_time_ms: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    exception_info: Optional[Dict[str, Any]] = None
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "category": self.category.value,
            "message": self.message,
            "context": self.context.to_dict(),
            "source": {
                "file": self.source_file,
                "line": self.source_line,
                "function": self.source_function
            },
            "performance": {
                "execution_time_ms": self.execution_time_ms,
                "memory_usage_mb": self.memory_usage_mb,
                "cpu_usage_percent": self.cpu_usage_percent
            },
            "exception": self.exception_info,
            "custom": self.custom_fields
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str, ensure_ascii=False)


@dataclass
class LogFilter:
    """Log-Filter für selektives Logging"""
    min_level: Optional[LogLevel] = None
    max_level: Optional[LogLevel] = None
    categories: Optional[List[LogCategory]] = None
    components: Optional[List[str]] = None
    correlation_ids: Optional[List[str]] = None
    time_range: Optional[Tuple[datetime, datetime]] = None
    custom_filter: Optional[Callable[[LogEntry], bool]] = None


class PerformanceTimer:
    """Context-Manager für Performance-Timing"""
    
    def __init__(self, logger: 'StructuredLogger', operation: str, 
                 context: Optional[LogContext] = None):
        self.logger = logger
        self.operation = operation
        self.context = context or LogContext()
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.debug(
            f"Starting operation: {self.operation}",
            LogCategory.PERFORMANCE,
            self.context
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        execution_time_ms = (self.end_time - self.start_time) * 1000
        
        if exc_type is None:
            self.logger.performance(
                f"Operation completed: {self.operation}",
                self.context,
                execution_time_ms=execution_time_ms
            )
        else:
            self.logger.error(
                f"Operation failed: {self.operation}",
                LogCategory.PERFORMANCE,
                self.context,
                exception_info={
                    "type": exc_type.__name__,
                    "message": str(exc_val),
                    "traceback": traceback.format_tb(exc_tb)
                },
                execution_time_ms=execution_time_ms
            )


class StructuredLogger:
    """
    Structured Logger für detailliertes Processing-Logging
    
    Features:
    - JSON-strukturiertes Logging mit Timestamps
    - Context-aware Logging mit Correlation-IDs
    - Performance-Tracking und Profiling
    - Async-Logging für High-Performance
    - Log-Aggregation und Real-time-Streaming
    - Flexible Filtering und Routing
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Logger-Konfiguration
        self.logger_name = self.config.get("logger_name", "ai_indicator_optimizer")
        self.log_level = LogLevel(self.config.get("log_level", "INFO"))
        self.enable_console_output = self.config.get("enable_console_output", True)
        self.enable_file_output = self.config.get("enable_file_output", True)
        self.enable_async_logging = self.config.get("enable_async_logging", True)
        self.enable_performance_tracking = self.config.get("enable_performance_tracking", True)
        
        # File-Konfiguration
        self.log_directory = Path(self.config.get("log_directory", "logs"))
        self.log_directory.mkdir(parents=True, exist_ok=True)
        
        self.log_file_pattern = self.config.get("log_file_pattern", "{category}_{date}.jsonl")
        self.max_file_size_mb = self.config.get("max_file_size_mb", 100)
        self.max_backup_count = self.config.get("max_backup_count", 10)
        self.compress_backups = self.config.get("compress_backups", True)
        
        # Buffer-Konfiguration
        self.buffer_size = self.config.get("buffer_size", 1000)
        self.flush_interval_seconds = self.config.get("flush_interval_seconds", 5.0)
        self.auto_flush_on_error = self.config.get("auto_flush_on_error", True)
        
        # Context-Management
        self.default_context = LogContext()
        self.context_stack: List[LogContext] = []
        
        # Log-Buffer und Threading
        self.log_buffer: deque = deque(maxlen=self.buffer_size)
        self.async_queue: queue.Queue = queue.Queue(maxsize=self.buffer_size * 2)
        
        # Threading
        self.logging_active = False
        self.async_thread: Optional[threading.Thread] = None
        self.flush_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Filters und Handlers
        self.filters: List[LogFilter] = []
        self.custom_handlers: List[Callable[[LogEntry], None]] = []
        
        # Statistiken
        self.stats = {
            "total_logs": 0,
            "logs_by_level": defaultdict(int),
            "logs_by_category": defaultdict(int),
            "errors_count": 0,
            "performance_logs": 0,
            "buffer_overflows": 0,
            "async_queue_overflows": 0
        }
        
        # Performance-Tracking
        self.performance_data: deque = deque(maxlen=10000)
        
        # Standard-Logger Setup
        self._setup_standard_logger()
        
        # Async-Logging starten
        if self.enable_async_logging:
            self.start_async_logging()
    
    def _setup_standard_logger(self):
        """Setup Standard-Python-Logger als Fallback"""
        
        self.standard_logger = logging.getLogger(self.logger_name)
        self.standard_logger.setLevel(getattr(logging, self.log_level.value))
        
        # Console-Handler
        if self.enable_console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            self.standard_logger.addHandler(console_handler)
        
        # File-Handler
        if self.enable_file_output and ROTATION_AVAILABLE:
            log_file = self.log_directory / "fallback.log"
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=self.max_file_size_mb * 1024 * 1024,
                backupCount=self.max_backup_count
            )
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            self.standard_logger.addHandler(file_handler)
    
    def start_async_logging(self):
        """Starte Async-Logging-Threads"""
        
        if self.logging_active:
            return
        
        self.logging_active = True
        self.stop_event.clear()
        
        # Async-Processing-Thread
        self.async_thread = threading.Thread(
            target=self._async_logging_loop,
            name="AsyncLogger",
            daemon=True
        )
        self.async_thread.start()
        
        # Flush-Thread
        self.flush_thread = threading.Thread(
            target=self._flush_loop,
            name="LogFlusher",
            daemon=True
        )
        self.flush_thread.start()
    
    def stop_async_logging(self):
        """Stoppe Async-Logging"""
        
        if not self.logging_active:
            return
        
        self.logging_active = False
        self.stop_event.set()
        
        # Flush remaining logs
        self.flush_logs()
        
        # Wait for threads
        if self.async_thread:
            self.async_thread.join(timeout=5.0)
        
        if self.flush_thread:
            self.flush_thread.join(timeout=5.0)
    
    def log(self, level: LogLevel, message: str, category: LogCategory,
            context: Optional[LogContext] = None, **kwargs):
        """Hauptmethode für strukturiertes Logging"""
        
        try:
            # Context bestimmen
            if context is None:
                context = self._get_current_context()
            
            # Source-Info ermitteln
            frame = sys._getframe(2)  # Caller's frame
            source_file = frame.f_code.co_filename
            source_line = frame.f_lineno
            source_function = frame.f_code.co_name
            
            # Performance-Metriken sammeln
            execution_time_ms = kwargs.get("execution_time_ms")
            memory_usage_mb = kwargs.get("memory_usage_mb")
            cpu_usage_percent = kwargs.get("cpu_usage_percent")
            
            # Exception-Info
            exception_info = kwargs.get("exception_info")
            if exception_info is None and level in [LogLevel.ERROR, LogLevel.CRITICAL]:
                exc_info = sys.exc_info()
                if exc_info[0] is not None:
                    exception_info = {
                        "type": exc_info[0].__name__,
                        "message": str(exc_info[1]),
                        "traceback": traceback.format_tb(exc_info[2])
                    }
            
            # Log-Entry erstellen
            log_entry = LogEntry(
                timestamp=datetime.now(),
                level=level,
                category=category,
                message=message,
                context=context,
                source_file=source_file,
                source_line=source_line,
                source_function=source_function,
                execution_time_ms=execution_time_ms,
                memory_usage_mb=memory_usage_mb,
                cpu_usage_percent=cpu_usage_percent,
                exception_info=exception_info,
                custom_fields=kwargs.get("custom_fields", {})
            )
            
            # Filter anwenden
            if not self._should_log(log_entry):
                return
            
            # Statistiken aktualisieren
            self.stats["total_logs"] += 1
            self.stats["logs_by_level"][level.value] += 1
            self.stats["logs_by_category"][category.value] += 1
            
            if level in [LogLevel.ERROR, LogLevel.CRITICAL]:
                self.stats["errors_count"] += 1
            
            if level == LogLevel.PERFORMANCE:
                self.stats["performance_logs"] += 1
                if execution_time_ms:
                    self.performance_data.append({
                        "timestamp": log_entry.timestamp,
                        "operation": context.operation,
                        "execution_time_ms": execution_time_ms
                    })
            
            # Async-Logging
            if self.enable_async_logging and self.logging_active:
                try:
                    self.async_queue.put_nowait(log_entry)
                except queue.Full:
                    self.stats["async_queue_overflows"] += 1
                    # Fallback zu synchronem Logging
                    self._write_log_entry(log_entry)
            else:
                # Synchrones Logging
                self._write_log_entry(log_entry)
            
            # Custom-Handlers
            for handler in self.custom_handlers:
                try:
                    handler(log_entry)
                except Exception as e:
                    self.standard_logger.error(f"Custom handler error: {e}")
            
            # Auto-Flush bei Fehlern
            if self.auto_flush_on_error and level in [LogLevel.ERROR, LogLevel.CRITICAL]:
                self.flush_logs()
                
        except Exception as e:
            # Fallback zu Standard-Logger
            self.standard_logger.error(f"Structured logging error: {e}")
            self.standard_logger.log(getattr(logging, level.value), message)
    
    def debug(self, message: str, category: LogCategory = LogCategory.SYSTEM,
              context: Optional[LogContext] = None, **kwargs):
        """Debug-Level Logging"""
        self.log(LogLevel.DEBUG, message, category, context, **kwargs)
    
    def info(self, message: str, category: LogCategory = LogCategory.SYSTEM,
             context: Optional[LogContext] = None, **kwargs):
        """Info-Level Logging"""
        self.log(LogLevel.INFO, message, category, context, **kwargs)
    
    def warning(self, message: str, category: LogCategory = LogCategory.SYSTEM,
                context: Optional[LogContext] = None, **kwargs):
        """Warning-Level Logging"""
        self.log(LogLevel.WARNING, message, category, context, **kwargs)
    
    def error(self, message: str, category: LogCategory = LogCategory.SYSTEM,
              context: Optional[LogContext] = None, **kwargs):
        """Error-Level Logging"""
        self.log(LogLevel.ERROR, message, category, context, **kwargs)
    
    def critical(self, message: str, category: LogCategory = LogCategory.SYSTEM,
                 context: Optional[LogContext] = None, **kwargs):
        """Critical-Level Logging"""
        self.log(LogLevel.CRITICAL, message, category, context, **kwargs)
    
    def performance(self, message: str, context: Optional[LogContext] = None,
                   execution_time_ms: Optional[float] = None, **kwargs):
        """Performance-Level Logging"""
        self.log(LogLevel.PERFORMANCE, message, LogCategory.PERFORMANCE, 
                context, execution_time_ms=execution_time_ms, **kwargs)
    
    def audit(self, message: str, context: Optional[LogContext] = None, **kwargs):
        """Audit-Level Logging"""
        self.log(LogLevel.AUDIT, message, LogCategory.SECURITY, context, **kwargs) 
   
    def timer(self, operation: str, context: Optional[LogContext] = None) -> PerformanceTimer:
        """Erstelle Performance-Timer Context-Manager"""
        return PerformanceTimer(self, operation, context)
    
    def push_context(self, context: LogContext):
        """Füge Context zum Stack hinzu"""
        self.context_stack.append(context)
    
    def pop_context(self) -> Optional[LogContext]:
        """Entferne Context vom Stack"""
        return self.context_stack.pop() if self.context_stack else None
    
    def with_context(self, **kwargs) -> LogContext:
        """Erstelle neuen Context mit aktuellen Werten"""
        current_context = self._get_current_context()
        
        new_context = LogContext(
            correlation_id=kwargs.get("correlation_id", current_context.correlation_id),
            session_id=kwargs.get("session_id", current_context.session_id),
            user_id=kwargs.get("user_id", current_context.user_id),
            request_id=kwargs.get("request_id", current_context.request_id),
            component=kwargs.get("component", current_context.component),
            operation=kwargs.get("operation", current_context.operation),
            metadata={**current_context.metadata, **kwargs.get("metadata", {})}
        )
        
        return new_context
    
    def add_filter(self, log_filter: LogFilter):
        """Füge Log-Filter hinzu"""
        self.filters.append(log_filter)
    
    def add_handler(self, handler: Callable[[LogEntry], None]):
        """Füge Custom-Handler hinzu"""
        self.custom_handlers.append(handler)
    
    def _get_current_context(self) -> LogContext:
        """Erhalte aktuellen Context"""
        if self.context_stack:
            return self.context_stack[-1]
        return self.default_context
    
    def _should_log(self, log_entry: LogEntry) -> bool:
        """Prüfe ob Log-Entry gefiltert werden soll"""
        
        for log_filter in self.filters:
            # Level-Filter
            if log_filter.min_level and log_entry.level.value < log_filter.min_level.value:
                return False
            if log_filter.max_level and log_entry.level.value > log_filter.max_level.value:
                return False
            
            # Category-Filter
            if log_filter.categories and log_entry.category not in log_filter.categories:
                return False
            
            # Component-Filter
            if (log_filter.components and 
                log_entry.context.component not in log_filter.components):
                return False
            
            # Correlation-ID-Filter
            if (log_filter.correlation_ids and 
                log_entry.context.correlation_id not in log_filter.correlation_ids):
                return False
            
            # Time-Range-Filter
            if log_filter.time_range:
                start_time, end_time = log_filter.time_range
                if not (start_time <= log_entry.timestamp <= end_time):
                    return False
            
            # Custom-Filter
            if log_filter.custom_filter and not log_filter.custom_filter(log_entry):
                return False
        
        return True
    
    def _write_log_entry(self, log_entry: LogEntry):
        """Schreibe Log-Entry in Buffer"""
        
        try:
            # Zu Buffer hinzufügen
            if len(self.log_buffer) >= self.buffer_size:
                self.stats["buffer_overflows"] += 1
                # Ältesten Eintrag entfernen
                self.log_buffer.popleft()
            
            self.log_buffer.append(log_entry)
            
            # Fallback zu Standard-Logger für Console-Output
            if self.enable_console_output:
                level_mapping = {
                    LogLevel.DEBUG: logging.DEBUG,
                    LogLevel.INFO: logging.INFO,
                    LogLevel.WARNING: logging.WARNING,
                    LogLevel.ERROR: logging.ERROR,
                    LogLevel.CRITICAL: logging.CRITICAL,
                    LogLevel.PERFORMANCE: logging.INFO,
                    LogLevel.AUDIT: logging.INFO
                }
                
                std_level = level_mapping.get(log_entry.level, logging.INFO)
                self.standard_logger.log(std_level, f"[{log_entry.category.value}] {log_entry.message}")
                
        except Exception as e:
            self.standard_logger.error(f"Error writing log entry: {e}")
    
    def _async_logging_loop(self):
        """Async-Logging-Loop"""
        
        while self.logging_active and not self.stop_event.is_set():
            try:
                # Warte auf Log-Entries
                try:
                    log_entry = self.async_queue.get(timeout=1.0)
                    self._write_log_entry(log_entry)
                    self.async_queue.task_done()
                except queue.Empty:
                    continue
                    
            except Exception as e:
                self.standard_logger.error(f"Async logging loop error: {e}")
                time.sleep(0.1)
    
    def _flush_loop(self):
        """Periodischer Flush-Loop"""
        
        while self.logging_active and not self.stop_event.is_set():
            try:
                # Warte Flush-Interval
                self.stop_event.wait(self.flush_interval_seconds)
                
                # Flush Logs
                if not self.stop_event.is_set():
                    self.flush_logs()
                    
            except Exception as e:
                self.standard_logger.error(f"Flush loop error: {e}")
                time.sleep(1.0)
    
    def flush_logs(self):
        """Flush Log-Buffer zu Files"""
        
        try:
            if not self.log_buffer:
                return
            
            # Gruppiere Logs nach Kategorie
            logs_by_category = defaultdict(list)
            
            # Kopiere Buffer (thread-safe)
            buffer_copy = list(self.log_buffer)
            self.log_buffer.clear()
            
            for log_entry in buffer_copy:
                logs_by_category[log_entry.category].append(log_entry)
            
            # Schreibe jede Kategorie in separate Datei
            for category, log_entries in logs_by_category.items():
                self._write_category_logs(category, log_entries)
                
        except Exception as e:
            self.standard_logger.error(f"Error flushing logs: {e}")
    
    def _write_category_logs(self, category: LogCategory, log_entries: List[LogEntry]):
        """Schreibe Logs einer Kategorie in Datei"""
        
        try:
            # Dateiname generieren
            date_str = datetime.now().strftime("%Y-%m-%d")
            filename = self.log_file_pattern.format(
                category=category.value,
                date=date_str
            )
            
            log_file_path = self.log_directory / filename
            
            # Logs in JSONL-Format schreiben
            with open(log_file_path, 'a', encoding='utf-8') as f:
                for log_entry in log_entries:
                    f.write(log_entry.to_json() + '\n')
            
            # Rotation prüfen
            self._check_file_rotation(log_file_path)
            
        except Exception as e:
            self.standard_logger.error(f"Error writing category logs: {e}")
    
    def _check_file_rotation(self, log_file_path: Path):
        """Prüfe und führe Log-Rotation durch"""
        
        try:
            if not log_file_path.exists():
                return
            
            file_size_mb = log_file_path.stat().st_size / (1024 * 1024)
            
            if file_size_mb > self.max_file_size_mb:
                # Rotation durchführen
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                rotated_name = f"{log_file_path.stem}_{timestamp}{log_file_path.suffix}"
                rotated_path = log_file_path.parent / rotated_name
                
                # Datei umbenennen
                log_file_path.rename(rotated_path)
                
                # Komprimieren falls aktiviert
                if self.compress_backups:
                    compressed_path = rotated_path.with_suffix(rotated_path.suffix + '.gz')
                    with open(rotated_path, 'rb') as f_in:
                        with gzip.open(compressed_path, 'wb') as f_out:
                            f_out.writelines(f_in)
                    rotated_path.unlink()  # Original löschen
                
                # Alte Backups cleanup
                self._cleanup_old_backups(log_file_path)
                
        except Exception as e:
            self.standard_logger.error(f"Error in file rotation: {e}")
    
    def _cleanup_old_backups(self, log_file_path: Path):
        """Cleanup alte Backup-Dateien"""
        
        try:
            # Finde alle Backup-Dateien
            pattern = f"{log_file_path.stem}_*"
            backup_files = list(log_file_path.parent.glob(pattern))
            
            # Sortiere nach Erstellungszeit (neueste zuerst)
            backup_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            
            # Lösche überschüssige Backups
            for backup_file in backup_files[self.max_backup_count:]:
                backup_file.unlink()
                
        except Exception as e:
            self.standard_logger.error(f"Error cleaning up backups: {e}")
    
    def search_logs(self, query: str, category: Optional[LogCategory] = None,
                   level: Optional[LogLevel] = None, 
                   time_range: Optional[Tuple[datetime, datetime]] = None,
                   limit: int = 100) -> List[LogEntry]:
        """Suche in Log-Einträgen"""
        
        try:
            results = []
            
            # Durchsuche aktuellen Buffer
            for log_entry in self.log_buffer:
                if self._matches_search_criteria(log_entry, query, category, level, time_range):
                    results.append(log_entry)
            
            # Durchsuche Log-Dateien falls nötig
            if len(results) < limit:
                file_results = self._search_log_files(query, category, level, time_range, limit - len(results))
                results.extend(file_results)
            
            return results[:limit]
            
        except Exception as e:
            self.standard_logger.error(f"Error searching logs: {e}")
            return []
    
    def _matches_search_criteria(self, log_entry: LogEntry, query: str,
                               category: Optional[LogCategory] = None,
                               level: Optional[LogLevel] = None,
                               time_range: Optional[Tuple[datetime, datetime]] = None) -> bool:
        """Prüfe ob Log-Entry Suchkriterien erfüllt"""
        
        # Text-Suche
        if query and query.lower() not in log_entry.message.lower():
            return False
        
        # Category-Filter
        if category and log_entry.category != category:
            return False
        
        # Level-Filter
        if level and log_entry.level != level:
            return False
        
        # Time-Range-Filter
        if time_range:
            start_time, end_time = time_range
            if not (start_time <= log_entry.timestamp <= end_time):
                return False
        
        return True
    
    def _search_log_files(self, query: str, category: Optional[LogCategory] = None,
                         level: Optional[LogLevel] = None,
                         time_range: Optional[Tuple[datetime, datetime]] = None,
                         limit: int = 100) -> List[LogEntry]:
        """Durchsuche Log-Dateien"""
        
        results = []
        
        try:
            # Bestimme relevante Log-Dateien
            log_files = []
            if category:
                pattern = f"{category.value}_*.jsonl*"
                log_files = list(self.log_directory.glob(pattern))
            else:
                log_files = list(self.log_directory.glob("*.jsonl*"))
            
            # Sortiere nach Datum (neueste zuerst)
            log_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            
            for log_file in log_files:
                if len(results) >= limit:
                    break
                
                file_results = self._search_single_log_file(
                    log_file, query, category, level, time_range, limit - len(results)
                )
                results.extend(file_results)
            
        except Exception as e:
            self.standard_logger.error(f"Error searching log files: {e}")
        
        return results
    
    def _search_single_log_file(self, log_file: Path, query: str,
                              category: Optional[LogCategory] = None,
                              level: Optional[LogLevel] = None,
                              time_range: Optional[Tuple[datetime, datetime]] = None,
                              limit: int = 100) -> List[LogEntry]:
        """Durchsuche einzelne Log-Datei"""
        
        results = []
        
        try:
            # Öffne Datei (ggf. komprimiert)
            if log_file.suffix == '.gz':
                file_obj = gzip.open(log_file, 'rt', encoding='utf-8')
            else:
                file_obj = open(log_file, 'r', encoding='utf-8')
            
            with file_obj as f:
                for line in f:
                    if len(results) >= limit:
                        break
                    
                    try:
                        # Parse JSON-Log-Entry
                        log_data = json.loads(line.strip())
                        
                        # Rekonstruiere LogEntry
                        log_entry = self._reconstruct_log_entry(log_data)
                        
                        # Prüfe Suchkriterien
                        if self._matches_search_criteria(log_entry, query, category, level, time_range):
                            results.append(log_entry)
                            
                    except (json.JSONDecodeError, KeyError):
                        continue  # Überspringe fehlerhafte Zeilen
            
        except Exception as e:
            self.standard_logger.error(f"Error searching log file {log_file}: {e}")
        
        return results
    
    def _reconstruct_log_entry(self, log_data: Dict[str, Any]) -> LogEntry:
        """Rekonstruiere LogEntry aus JSON-Daten"""
        
        # Context rekonstruieren
        context_data = log_data.get("context", {})
        context = LogContext(
            correlation_id=context_data.get("correlation_id", ""),
            session_id=context_data.get("session_id"),
            user_id=context_data.get("user_id"),
            request_id=context_data.get("request_id"),
            component=context_data.get("component"),
            operation=context_data.get("operation"),
            metadata=context_data.get("metadata", {})
        )
        
        # Performance-Daten
        performance_data = log_data.get("performance", {})
        
        # LogEntry rekonstruieren
        log_entry = LogEntry(
            timestamp=datetime.fromisoformat(log_data["timestamp"]),
            level=LogLevel(log_data["level"]),
            category=LogCategory(log_data["category"]),
            message=log_data["message"],
            context=context,
            source_file=log_data.get("source", {}).get("file"),
            source_line=log_data.get("source", {}).get("line"),
            source_function=log_data.get("source", {}).get("function"),
            execution_time_ms=performance_data.get("execution_time_ms"),
            memory_usage_mb=performance_data.get("memory_usage_mb"),
            cpu_usage_percent=performance_data.get("cpu_usage_percent"),
            exception_info=log_data.get("exception"),
            custom_fields=log_data.get("custom", {})
        )
        
        return log_entry
    
    def get_statistics(self) -> Dict[str, Any]:
        """Erhalte Logging-Statistiken"""
        
        try:
            # Performance-Statistiken
            performance_stats = {}
            if self.performance_data:
                execution_times = [p["execution_time_ms"] for p in self.performance_data if p.get("execution_time_ms")]
                if execution_times:
                    performance_stats = {
                        "avg_execution_time_ms": sum(execution_times) / len(execution_times),
                        "min_execution_time_ms": min(execution_times),
                        "max_execution_time_ms": max(execution_times),
                        "total_operations": len(execution_times)
                    }
            
            return {
                "timestamp": datetime.now().isoformat(),
                "logging_active": self.logging_active,
                "buffer_size": len(self.log_buffer),
                "async_queue_size": self.async_queue.qsize(),
                "statistics": dict(self.stats),
                "performance": performance_stats,
                "filters_count": len(self.filters),
                "handlers_count": len(self.custom_handlers),
                "log_directory": str(self.log_directory),
                "config": {
                    "log_level": self.log_level.value,
                    "enable_async_logging": self.enable_async_logging,
                    "enable_performance_tracking": self.enable_performance_tracking,
                    "buffer_size": self.buffer_size,
                    "flush_interval_seconds": self.flush_interval_seconds
                }
            }
            
        except Exception as e:
            self.standard_logger.error(f"Error getting statistics: {e}")
            return {"error": str(e)}
    
    def cleanup(self):
        """Cleanup Logger-Ressourcen"""
        
        try:
            # Stoppe Async-Logging
            self.stop_async_logging()
            
            # Finale Flush
            self.flush_logs()
            
            # Clear Buffers
            self.log_buffer.clear()
            
            # Clear Handlers
            for handler in self.standard_logger.handlers[:]:
                handler.close()
                self.standard_logger.removeHandler(handler)
            
        except Exception as e:
            self.standard_logger.error(f"Error during logger cleanup: {e}")


# Utility-Funktionen
def create_trading_context(strategy_name: str, symbol: str, 
                          timeframe: str, **kwargs) -> LogContext:
    """Erstelle Trading-spezifischen Context"""
    
    return LogContext(
        component="trading_engine",
        operation=f"execute_strategy_{strategy_name}",
        metadata={
            "strategy_name": strategy_name,
            "symbol": symbol,
            "timeframe": timeframe,
            **kwargs
        }
    )


def create_ai_model_context(model_name: str, operation: str, **kwargs) -> LogContext:
    """Erstelle AI-Model-spezifischen Context"""
    
    return LogContext(
        component="ai_model",
        operation=f"{operation}_{model_name}",
        metadata={
            "model_name": model_name,
            "operation_type": operation,
            **kwargs
        }
    )


def create_optimization_context(optimization_type: str, target: str, **kwargs) -> LogContext:
    """Erstelle Optimization-spezifischen Context"""
    
    return LogContext(
        component="optimizer",
        operation=f"optimize_{optimization_type}",
        metadata={
            "optimization_type": optimization_type,
            "target": target,
            **kwargs
        }
    )


# Global Logger-Instance
_global_logger: Optional[StructuredLogger] = None


def get_logger(config: Optional[Dict] = None) -> StructuredLogger:
    """Erhalte globale Logger-Instance"""
    
    global _global_logger
    
    if _global_logger is None:
        _global_logger = StructuredLogger(config)
    
    return _global_logger


def setup_logging(config: Dict[str, Any]):
    """Setup globales Logging"""
    
    global _global_logger
    
    if _global_logger:
        _global_logger.cleanup()
    
    _global_logger = StructuredLogger(config)
    
    return _global_logger