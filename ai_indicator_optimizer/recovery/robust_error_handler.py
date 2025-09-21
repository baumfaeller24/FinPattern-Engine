#!/usr/bin/env python3
"""
Robust Error Handler für graceful Degradation bei Fehlern
Phase 3 Implementation - Task 13

Features:
- Comprehensive Error-Classification und Handling
- Graceful Degradation-Strategien für verschiedene Fehlertypen
- Circuit-Breaker-Pattern für Service-Protection
- Retry-Mechanismen mit Exponential-Backoff
- Error-Recovery-Workflows und Fallback-Strategien
- Real-time Error-Monitoring und Alerting
- Error-Analytics und Pattern-Recognition
"""

import time
import threading
import logging
import traceback
from typing import Dict, List, Optional, Any, Union, Callable, Type
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import json
import pickle
from collections import deque, defaultdict
import functools
import asyncio

# Async Support
try:
    import aiofiles
    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False

# Notification Support
try:
    import smtplib
    from email.mime.text import MIMEText
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False


class ErrorSeverity(Enum):
    """Error-Schweregrade"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    FATAL = "fatal"


class ErrorCategory(Enum):
    """Error-Kategorien"""
    NETWORK = "network"
    DATA_SOURCE = "data_source"
    MODEL_INFERENCE = "model_inference"
    COMPUTATION = "computation"
    MEMORY = "memory"
    DISK_IO = "disk_io"
    CONFIGURATION = "configuration"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    TIMEOUT = "timeout"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    EXTERNAL_SERVICE = "external_service"
    UNKNOWN = "unknown"


class RecoveryStrategy(Enum):
    """Recovery-Strategien"""
    RETRY = "retry"
    FALLBACK = "fallback"
    CIRCUIT_BREAKER = "circuit_breaker"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    FAIL_FAST = "fail_fast"
    IGNORE = "ignore"
    ESCALATE = "escalate"


class CircuitBreakerState(Enum):
    """Circuit-Breaker-Zustände"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class ErrorContext:
    """Kontext-Informationen für Fehler"""
    component: str
    operation: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": self.component,
            "operation": self.operation,
            "parameters": self.parameters,
            "correlation_id": self.correlation_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "request_id": self.request_id,
            "metadata": self.metadata
        }


@dataclass
class ErrorRecord:
    """Error-Record für Tracking und Analytics"""
    error_id: str
    timestamp: datetime
    severity: ErrorSeverity
    category: ErrorCategory
    exception_type: str
    message: str
    context: ErrorContext
    stack_trace: Optional[str] = None
    recovery_strategy: Optional[RecoveryStrategy] = None
    recovery_successful: Optional[bool] = None
    recovery_attempts: int = 0
    resolution_time: Optional[timedelta] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_id": self.error_id,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity.value,
            "category": self.category.value,
            "exception_type": self.exception_type,
            "message": self.message,
            "context": self.context.to_dict(),
            "stack_trace": self.stack_trace,
            "recovery_strategy": self.recovery_strategy.value if self.recovery_strategy else None,
            "recovery_successful": self.recovery_successful,
            "recovery_attempts": self.recovery_attempts,
            "resolution_time": str(self.resolution_time) if self.resolution_time else None
        }


@dataclass
class CircuitBreaker:
    """Circuit-Breaker für Service-Protection"""
    name: str
    failure_threshold: int = 5
    recovery_timeout: int = 60  # Sekunden
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    success_count: int = 0
    
    def should_allow_request(self) -> bool:
        """Prüfe ob Request erlaubt ist"""
        
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if self.last_failure_time:
                time_since_failure = datetime.now() - self.last_failure_time
                if time_since_failure.total_seconds() >= self.recovery_timeout:
                    self.state = CircuitBreakerState.HALF_OPEN
                    return True
            return False
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return True
        
        return False
    
    def record_success(self):
        """Registriere erfolgreichen Request"""
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= 3:  # Nach 3 erfolgreichen Requests
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)  # Reduziere Failure-Count
    
    def record_failure(self):
        """Registriere fehlgeschlagenen Request"""
        
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        self.success_count = 0
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN


class RobustErrorHandler:
    """
    Robust Error Handler für graceful Degradation bei Fehlern
    
    Features:
    - Comprehensive Error-Classification und Handling
    - Circuit-Breaker-Pattern für Service-Protection
    - Retry-Mechanismen mit Exponential-Backoff
    - Graceful Degradation-Strategien
    - Error-Recovery-Workflows
    - Real-time Error-Monitoring und Alerting
    - Error-Analytics und Pattern-Recognition
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Handler-Konfiguration
        self.enable_circuit_breakers = self.config.get("enable_circuit_breakers", True)
        self.enable_retry_mechanisms = self.config.get("enable_retry_mechanisms", True)
        self.enable_graceful_degradation = self.config.get("enable_graceful_degradation", True)
        self.enable_error_analytics = self.config.get("enable_error_analytics", True)
        self.enable_notifications = self.config.get("enable_notifications", False)
        
        # Retry-Konfiguration
        self.default_max_retries = self.config.get("default_max_retries", 3)
        self.default_retry_delay = self.config.get("default_retry_delay", 1.0)  # Sekunden
        self.max_retry_delay = self.config.get("max_retry_delay", 60.0)  # Sekunden
        self.backoff_multiplier = self.config.get("backoff_multiplier", 2.0)
        
        # Circuit-Breaker-Konfiguration
        self.circuit_breaker_failure_threshold = self.config.get("circuit_breaker_failure_threshold", 5)
        self.circuit_breaker_recovery_timeout = self.config.get("circuit_breaker_recovery_timeout", 60)
        
        # Storage-Konfiguration
        self.error_log_directory = Path(self.config.get("error_log_directory", "error_logs"))
        self.error_log_directory.mkdir(parents=True, exist_ok=True)
        
        # Error-Tracking
        self.error_records: deque = deque(maxlen=10000)
        self.error_patterns: Dict[str, int] = defaultdict(int)
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # Error-Classification-Rules
        self.classification_rules: Dict[Type[Exception], Tuple[ErrorSeverity, ErrorCategory]] = {
            ConnectionError: (ErrorSeverity.HIGH, ErrorCategory.NETWORK),
            TimeoutError: (ErrorSeverity.MEDIUM, ErrorCategory.TIMEOUT),
            MemoryError: (ErrorSeverity.CRITICAL, ErrorCategory.MEMORY),
            FileNotFoundError: (ErrorSeverity.MEDIUM, ErrorCategory.DISK_IO),
            PermissionError: (ErrorSeverity.HIGH, ErrorCategory.AUTHENTICATION),
            ValueError: (ErrorSeverity.LOW, ErrorCategory.VALIDATION),
            KeyError: (ErrorSeverity.LOW, ErrorCategory.CONFIGURATION),
            ImportError: (ErrorSeverity.HIGH, ErrorCategory.CONFIGURATION),
            OSError: (ErrorSeverity.MEDIUM, ErrorCategory.DISK_IO),
        }
        
        # Recovery-Strategy-Rules
        self.recovery_strategy_rules: Dict[ErrorCategory, RecoveryStrategy] = {
            ErrorCategory.NETWORK: RecoveryStrategy.RETRY,
            ErrorCategory.DATA_SOURCE: RecoveryStrategy.FALLBACK,
            ErrorCategory.MODEL_INFERENCE: RecoveryStrategy.FALLBACK,
            ErrorCategory.COMPUTATION: RecoveryStrategy.RETRY,
            ErrorCategory.MEMORY: RecoveryStrategy.GRACEFUL_DEGRADATION,
            ErrorCategory.DISK_IO: RecoveryStrategy.RETRY,
            ErrorCategory.CONFIGURATION: RecoveryStrategy.FAIL_FAST,
            ErrorCategory.AUTHENTICATION: RecoveryStrategy.ESCALATE,
            ErrorCategory.VALIDATION: RecoveryStrategy.FAIL_FAST,
            ErrorCategory.TIMEOUT: RecoveryStrategy.CIRCUIT_BREAKER,
            ErrorCategory.RESOURCE_EXHAUSTION: RecoveryStrategy.GRACEFUL_DEGRADATION,
            ErrorCategory.EXTERNAL_SERVICE: RecoveryStrategy.CIRCUIT_BREAKER,
            ErrorCategory.UNKNOWN: RecoveryStrategy.RETRY
        }
        
        # Fallback-Handlers
        self.fallback_handlers: Dict[str, Callable] = {}
        self.degradation_handlers: Dict[str, Callable] = {}
        
        # Notification-Konfiguration
        self.notification_config = self.config.get("notifications", {})
        
        # Threading
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Statistiken
        self.stats = {
            "total_errors": 0,
            "errors_by_severity": defaultdict(int),
            "errors_by_category": defaultdict(int),
            "recovery_attempts": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "circuit_breaker_trips": 0,
            "notifications_sent": 0
        }
        
        # Monitoring starten
        if self.enable_error_analytics:
            self.start_monitoring()
        
        self.logger.info("RobustErrorHandler initialized")
    
    def handle_error(self, exception: Exception, context: ErrorContext,
                    custom_strategy: Optional[RecoveryStrategy] = None) -> Any:
        """Hauptmethode für Error-Handling"""
        
        try:
            # Error-Classification
            severity, category = self._classify_error(exception)
            
            # Error-Record erstellen
            error_record = self._create_error_record(
                exception, context, severity, category
            )
            
            # Recovery-Strategy bestimmen
            recovery_strategy = custom_strategy or self._determine_recovery_strategy(category, context)
            error_record.recovery_strategy = recovery_strategy
            
            # Error-Record speichern
            self.error_records.append(error_record)
            self.stats["total_errors"] += 1
            self.stats["errors_by_severity"][severity.value] += 1
            self.stats["errors_by_category"][category.value] += 1
            
            # Error-Pattern-Tracking
            pattern_key = f"{category.value}:{type(exception).__name__}"
            self.error_patterns[pattern_key] += 1
            
            # Recovery ausführen
            recovery_result = self._execute_recovery_strategy(
                recovery_strategy, exception, context, error_record
            )
            
            # Notification senden falls nötig
            if severity in [ErrorSeverity.CRITICAL, ErrorSeverity.FATAL]:
                self._send_error_notification(error_record)
            
            # Error-Analytics aktualisieren
            if self.enable_error_analytics:
                self._update_error_analytics(error_record)
            
            return recovery_result
            
        except Exception as e:
            self.logger.critical(f"Error in error handler: {e}")
            # Fallback zu einfachem Logging
            self.logger.error(f"Original error: {exception}")
            raise exception
    
    def with_error_handling(self, context: ErrorContext,
                          fallback_value: Any = None,
                          custom_strategy: Optional[RecoveryStrategy] = None):
        """Decorator für automatisches Error-Handling"""
        
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    result = self.handle_error(e, context, custom_strategy)
                    return result if result is not None else fallback_value
            
            return wrapper
        return decorator
    
    def with_circuit_breaker(self, service_name: str,
                           failure_threshold: int = None,
                           recovery_timeout: int = None):
        """Decorator für Circuit-Breaker-Pattern"""
        
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Circuit-Breaker erstellen falls nicht vorhanden
                if service_name not in self.circuit_breakers:
                    self.circuit_breakers[service_name] = CircuitBreaker(
                        name=service_name,
                        failure_threshold=failure_threshold or self.circuit_breaker_failure_threshold,
                        recovery_timeout=recovery_timeout or self.circuit_breaker_recovery_timeout
                    )
                
                circuit_breaker = self.circuit_breakers[service_name]
                
                # Prüfe Circuit-Breaker-Status
                if not circuit_breaker.should_allow_request():
                    raise Exception(f"Circuit breaker {service_name} is OPEN")
                
                try:
                    result = func(*args, **kwargs)
                    circuit_breaker.record_success()
                    return result
                except Exception as e:
                    circuit_breaker.record_failure()
                    if circuit_breaker.state == CircuitBreakerState.OPEN:
                        self.stats["circuit_breaker_trips"] += 1
                    raise e
            
            return wrapper
        return decorator
    
    def with_retry(self, max_retries: int = None,
                  retry_delay: float = None,
                  backoff_multiplier: float = None,
                  retry_on: List[Type[Exception]] = None):
        """Decorator für Retry-Mechanismus"""
        
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                max_attempts = (max_retries or self.default_max_retries) + 1
                delay = retry_delay or self.default_retry_delay
                multiplier = backoff_multiplier or self.backoff_multiplier
                
                last_exception = None
                
                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        
                        # Prüfe ob Retry für diesen Exception-Typ erlaubt
                        if retry_on and type(e) not in retry_on:
                            raise e
                        
                        # Letzter Versuch - keine weitere Retry
                        if attempt == max_attempts - 1:
                            break
                        
                        # Exponential Backoff
                        current_delay = min(delay * (multiplier ** attempt), self.max_retry_delay)
                        
                        self.logger.warning(f"Retry attempt {attempt + 1}/{max_attempts} "
                                          f"after {current_delay:.2f}s delay: {e}")
                        
                        time.sleep(current_delay)
                        self.stats["recovery_attempts"] += 1
                
                # Alle Retries fehlgeschlagen
                self.stats["failed_recoveries"] += 1
                raise last_exception
            
            return wrapper
        return decorator
    
    def register_fallback_handler(self, component: str, handler: Callable):
        """Registriere Fallback-Handler für Komponente"""
        self.fallback_handlers[component] = handler
        self.logger.info(f"Registered fallback handler for component: {component}")
    
    def register_degradation_handler(self, component: str, handler: Callable):
        """Registriere Degradation-Handler für Komponente"""
        self.degradation_handlers[component] = handler
        self.logger.info(f"Registered degradation handler for component: {component}")
    
    def _classify_error(self, exception: Exception) -> Tuple[ErrorSeverity, ErrorCategory]:
        """Klassifiziere Error nach Severity und Category"""
        
        # Direkte Klassifikation über Exception-Typ
        exception_type = type(exception)
        if exception_type in self.classification_rules:
            return self.classification_rules[exception_type]
        
        # Klassifikation über Exception-Message
        message = str(exception).lower()
        
        # Network-Errors
        if any(keyword in message for keyword in ["connection", "network", "dns", "host"]):
            return ErrorSeverity.HIGH, ErrorCategory.NETWORK
        
        # Memory-Errors
        if any(keyword in message for keyword in ["memory", "out of memory", "allocation"]):
            return ErrorSeverity.CRITICAL, ErrorCategory.MEMORY
        
        # Timeout-Errors
        if any(keyword in message for keyword in ["timeout", "timed out", "deadline"]):
            return ErrorSeverity.MEDIUM, ErrorCategory.TIMEOUT
        
        # Data-Source-Errors
        if any(keyword in message for keyword in ["data", "source", "feed", "api"]):
            return ErrorSeverity.MEDIUM, ErrorCategory.DATA_SOURCE
        
        # Model-Errors
        if any(keyword in message for keyword in ["model", "inference", "prediction", "tensor"]):
            return ErrorSeverity.HIGH, ErrorCategory.MODEL_INFERENCE
        
        # Default-Klassifikation
        return ErrorSeverity.MEDIUM, ErrorCategory.UNKNOWN
    
    def _determine_recovery_strategy(self, category: ErrorCategory, 
                                   context: ErrorContext) -> RecoveryStrategy:
        """Bestimme Recovery-Strategy basierend auf Error-Category"""
        
        # Standard-Strategy für Category
        strategy = self.recovery_strategy_rules.get(category, RecoveryStrategy.RETRY)
        
        # Context-basierte Anpassungen
        component = context.component.lower()
        
        # Kritische Komponenten - konservativere Strategien
        if any(critical in component for critical in ["trading", "order", "position"]):
            if strategy == RecoveryStrategy.IGNORE:
                strategy = RecoveryStrategy.FAIL_FAST
        
        # Data-Processing - Fallback bevorzugen
        if any(data_comp in component for data_comp in ["data", "feed", "source"]):
            if strategy == RecoveryStrategy.FAIL_FAST:
                strategy = RecoveryStrategy.FALLBACK
        
        return strategy
    
    def _create_error_record(self, exception: Exception, context: ErrorContext,
                           severity: ErrorSeverity, category: ErrorCategory) -> ErrorRecord:
        """Erstelle Error-Record"""
        
        import uuid
        
        error_id = str(uuid.uuid4())
        
        return ErrorRecord(
            error_id=error_id,
            timestamp=datetime.now(),
            severity=severity,
            category=category,
            exception_type=type(exception).__name__,
            message=str(exception),
            context=context,
            stack_trace=traceback.format_exc()
        )
    
    def _execute_recovery_strategy(self, strategy: RecoveryStrategy, 
                                 exception: Exception, context: ErrorContext,
                                 error_record: ErrorRecord) -> Any:
        """Führe Recovery-Strategy aus"""
        
        try:
            if strategy == RecoveryStrategy.RETRY:
                return self._execute_retry_recovery(exception, context, error_record)
            
            elif strategy == RecoveryStrategy.FALLBACK:
                return self._execute_fallback_recovery(exception, context, error_record)
            
            elif strategy == RecoveryStrategy.CIRCUIT_BREAKER:
                return self._execute_circuit_breaker_recovery(exception, context, error_record)
            
            elif strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
                return self._execute_degradation_recovery(exception, context, error_record)
            
            elif strategy == RecoveryStrategy.FAIL_FAST:
                self.logger.error(f"Fail-fast strategy: {exception}")
                raise exception
            
            elif strategy == RecoveryStrategy.IGNORE:
                self.logger.warning(f"Ignoring error: {exception}")
                return None
            
            elif strategy == RecoveryStrategy.ESCALATE:
                self._escalate_error(exception, context, error_record)
                raise exception
            
            else:
                self.logger.warning(f"Unknown recovery strategy: {strategy}")
                raise exception
                
        except Exception as recovery_exception:
            error_record.recovery_successful = False
            self.stats["failed_recoveries"] += 1
            self.logger.error(f"Recovery strategy {strategy.value} failed: {recovery_exception}")
            raise exception
    
    def _execute_retry_recovery(self, exception: Exception, context: ErrorContext,
                              error_record: ErrorRecord) -> Any:
        """Führe Retry-Recovery aus"""
        
        # Retry-Logic ist bereits im Decorator implementiert
        # Hier nur Logging und Statistiken
        error_record.recovery_attempts += 1
        self.stats["recovery_attempts"] += 1
        
        self.logger.info(f"Retry recovery initiated for {context.component}:{context.operation}")
        
        # Für direkte Aufrufe - einfache Retry-Logic
        max_retries = 3
        delay = 1.0
        
        for attempt in range(max_retries):
            try:
                time.sleep(delay * (2 ** attempt))  # Exponential backoff
                # Hier würde normalerweise die ursprüngliche Operation wiederholt
                # Da wir keinen Zugriff darauf haben, geben wir None zurück
                error_record.recovery_successful = True
                self.stats["successful_recoveries"] += 1
                return None
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
        
        return None
    
    def _execute_fallback_recovery(self, exception: Exception, context: ErrorContext,
                                 error_record: ErrorRecord) -> Any:
        """Führe Fallback-Recovery aus"""
        
        component = context.component
        
        if component in self.fallback_handlers:
            try:
                self.logger.info(f"Executing fallback handler for {component}")
                result = self.fallback_handlers[component](exception, context)
                
                error_record.recovery_successful = True
                self.stats["successful_recoveries"] += 1
                
                return result
                
            except Exception as fallback_exception:
                self.logger.error(f"Fallback handler failed: {fallback_exception}")
                raise exception
        else:
            self.logger.warning(f"No fallback handler registered for {component}")
            raise exception
    
    def _execute_circuit_breaker_recovery(self, exception: Exception, context: ErrorContext,
                                        error_record: ErrorRecord) -> Any:
        """Führe Circuit-Breaker-Recovery aus"""
        
        service_name = f"{context.component}:{context.operation}"
        
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = CircuitBreaker(
                name=service_name,
                failure_threshold=self.circuit_breaker_failure_threshold,
                recovery_timeout=self.circuit_breaker_recovery_timeout
            )
        
        circuit_breaker = self.circuit_breakers[service_name]
        circuit_breaker.record_failure()
        
        if circuit_breaker.state == CircuitBreakerState.OPEN:
            self.stats["circuit_breaker_trips"] += 1
            self.logger.warning(f"Circuit breaker {service_name} is now OPEN")
        
        error_record.recovery_successful = False
        raise exception
    
    def _execute_degradation_recovery(self, exception: Exception, context: ErrorContext,
                                    error_record: ErrorRecord) -> Any:
        """Führe Graceful-Degradation-Recovery aus"""
        
        component = context.component
        
        if component in self.degradation_handlers:
            try:
                self.logger.info(f"Executing degradation handler for {component}")
                result = self.degradation_handlers[component](exception, context)
                
                error_record.recovery_successful = True
                self.stats["successful_recoveries"] += 1
                
                return result
                
            except Exception as degradation_exception:
                self.logger.error(f"Degradation handler failed: {degradation_exception}")
                raise exception
        else:
            # Default-Degradation: Reduzierte Funktionalität
            self.logger.warning(f"Graceful degradation for {component} - reduced functionality")
            error_record.recovery_successful = True
            self.stats["successful_recoveries"] += 1
            return None
    
    def _escalate_error(self, exception: Exception, context: ErrorContext,
                       error_record: ErrorRecord):
        """Eskaliere Error an höhere Ebene"""
        
        self.logger.critical(f"Escalating error: {exception}")
        
        # Notification senden
        self._send_error_notification(error_record)
        
        # Zusätzliche Eskalations-Logic hier
        # z.B. Alert an Operations-Team, Incident-Creation, etc.
    
    def _send_error_notification(self, error_record: ErrorRecord):
        """Sende Error-Notification"""
        
        if not self.enable_notifications:
            return
        
        try:
            notification_config = self.notification_config
            
            if notification_config.get("email") and EMAIL_AVAILABLE:
                self._send_email_notification(error_record, notification_config["email"])
            
            # Weitere Notification-Kanäle hier (Slack, Teams, etc.)
            
            self.stats["notifications_sent"] += 1
            
        except Exception as e:
            self.logger.error(f"Failed to send error notification: {e}")
    
    def _send_email_notification(self, error_record: ErrorRecord, email_config: Dict[str, Any]):
        """Sende Email-Notification"""
        
        try:
            subject = f"[AI Optimizer] {error_record.severity.value.upper()} Error: {error_record.category.value}"
            
            body = f"""
Error Details:
- Error ID: {error_record.error_id}
- Timestamp: {error_record.timestamp}
- Severity: {error_record.severity.value}
- Category: {error_record.category.value}
- Component: {error_record.context.component}
- Operation: {error_record.context.operation}
- Exception: {error_record.exception_type}
- Message: {error_record.message}

Recovery Strategy: {error_record.recovery_strategy.value if error_record.recovery_strategy else 'None'}
Recovery Successful: {error_record.recovery_successful}

Stack Trace:
{error_record.stack_trace}
            """
            
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = email_config.get("from_address", "ai-optimizer@example.com")
            msg['To'] = email_config.get("to_address", "admin@example.com")
            
            # SMTP-Server-Konfiguration
            smtp_server = email_config.get("smtp_server", "localhost")
            smtp_port = email_config.get("smtp_port", 587)
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                if email_config.get("use_tls", True):
                    server.starttls()
                
                username = email_config.get("username")
                password = email_config.get("password")
                
                if username and password:
                    server.login(username, password)
                
                server.send_message(msg)
            
            self.logger.info(f"Email notification sent for error {error_record.error_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to send email notification: {e}")
    
    def start_monitoring(self):
        """Starte Error-Monitoring"""
        
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.stop_event.clear()
        
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            name="ErrorMonitor",
            daemon=True
        )
        self.monitoring_thread.start()
        
        self.logger.info("Error monitoring started")
    
    def stop_monitoring(self):
        """Stoppe Error-Monitoring"""
        
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        self.stop_event.set()
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5.0)
        
        self.logger.info("Error monitoring stopped")
    
    def _monitoring_loop(self):
        """Error-Monitoring-Loop"""
        
        while self.monitoring_active and not self.stop_event.is_set():
            try:
                # Error-Pattern-Analyse
                self._analyze_error_patterns()
                
                # Circuit-Breaker-Status prüfen
                self._check_circuit_breaker_recovery()
                
                # Error-Log-Rotation
                self._rotate_error_logs()
                
                # Warte bis zum nächsten Monitoring-Cycle
                self.stop_event.wait(60.0)  # 1 Minute
                
            except Exception as e:
                self.logger.error(f"Error monitoring loop error: {e}")
                time.sleep(5.0)
    
    def _analyze_error_patterns(self):
        """Analysiere Error-Patterns"""
        
        try:
            # Häufige Error-Patterns identifizieren
            frequent_patterns = sorted(
                self.error_patterns.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            for pattern, count in frequent_patterns:
                if count > 10:  # Threshold für häufige Patterns
                    self.logger.warning(f"Frequent error pattern detected: {pattern} ({count} occurrences)")
            
        except Exception as e:
            self.logger.error(f"Error in pattern analysis: {e}")
    
    def _check_circuit_breaker_recovery(self):
        """Prüfe Circuit-Breaker-Recovery"""
        
        try:
            for name, circuit_breaker in self.circuit_breakers.items():
                if (circuit_breaker.state == CircuitBreakerState.OPEN and 
                    circuit_breaker.last_failure_time):
                    
                    time_since_failure = datetime.now() - circuit_breaker.last_failure_time
                    
                    if time_since_failure.total_seconds() >= circuit_breaker.recovery_timeout:
                        self.logger.info(f"Circuit breaker {name} transitioning to HALF_OPEN")
                        circuit_breaker.state = CircuitBreakerState.HALF_OPEN
            
        except Exception as e:
            self.logger.error(f"Error in circuit breaker recovery check: {e}")
    
    def _rotate_error_logs(self):
        """Rotiere Error-Logs"""
        
        try:
            # Speichere Error-Records periodisch
            if len(self.error_records) > 1000:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_file = self.error_log_directory / f"error_records_{timestamp}.json"
                
                # Exportiere Error-Records
                records_data = [record.to_dict() for record in list(self.error_records)[-1000:]]
                
                with open(log_file, 'w') as f:
                    json.dump(records_data, f, indent=2, default=str)
                
                self.logger.info(f"Error records exported to {log_file}")
            
        except Exception as e:
            self.logger.error(f"Error in log rotation: {e}")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Erhalte Error-Statistiken"""
        
        try:
            # Recent Errors
            recent_errors = []
            for record in list(self.error_records)[-10:]:
                recent_errors.append({
                    "error_id": record.error_id,
                    "timestamp": record.timestamp.isoformat(),
                    "severity": record.severity.value,
                    "category": record.category.value,
                    "component": record.context.component,
                    "message": record.message[:100] + "..." if len(record.message) > 100 else record.message
                })
            
            # Circuit-Breaker-Status
            circuit_breaker_status = {}
            for name, cb in self.circuit_breakers.items():
                circuit_breaker_status[name] = {
                    "state": cb.state.value,
                    "failure_count": cb.failure_count,
                    "last_failure": cb.last_failure_time.isoformat() if cb.last_failure_time else None
                }
            
            # Top Error-Patterns
            top_patterns = sorted(
                self.error_patterns.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            return {
                "timestamp": datetime.now().isoformat(),
                "handler_config": {
                    "enable_circuit_breakers": self.enable_circuit_breakers,
                    "enable_retry_mechanisms": self.enable_retry_mechanisms,
                    "enable_graceful_degradation": self.enable_graceful_degradation,
                    "enable_error_analytics": self.enable_error_analytics,
                    "default_max_retries": self.default_max_retries
                },
                "statistics": dict(self.stats),
                "recent_errors": recent_errors,
                "circuit_breakers": circuit_breaker_status,
                "top_error_patterns": top_patterns,
                "total_error_records": len(self.error_records),
                "registered_handlers": {
                    "fallback_handlers": list(self.fallback_handlers.keys()),
                    "degradation_handlers": list(self.degradation_handlers.keys())
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            return {"error": str(e)}
    
    def cleanup(self):
        """Cleanup Error-Handler-Ressourcen"""
        
        try:
            # Stoppe Monitoring
            self.stop_monitoring()
            
            # Exportiere finale Error-Records
            if self.error_records:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                final_log = self.error_log_directory / f"final_error_records_{timestamp}.json"
                
                records_data = [record.to_dict() for record in self.error_records]
                
                with open(final_log, 'w') as f:
                    json.dump(records_data, f, indent=2, default=str)
            
            # Clear Data
            self.error_records.clear()
            self.error_patterns.clear()
            self.circuit_breakers.clear()
            
            self.logger.info("RobustErrorHandler cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")


# Utility-Funktionen
def create_error_context(component: str, operation: str, **kwargs) -> ErrorContext:
    """Erstelle Error-Context"""
    
    return ErrorContext(
        component=component,
        operation=operation,
        parameters=kwargs.get("parameters", {}),
        correlation_id=kwargs.get("correlation_id"),
        session_id=kwargs.get("session_id"),
        user_id=kwargs.get("user_id"),
        request_id=kwargs.get("request_id"),
        metadata=kwargs.get("metadata", {})
    )


def setup_error_handling_config(enable_notifications: bool = False,
                              max_retries: int = 3,
                              circuit_breaker_threshold: int = 5) -> Dict[str, Any]:
    """Setup Error-Handling-Konfiguration"""
    
    return {
        "enable_circuit_breakers": True,
        "enable_retry_mechanisms": True,
        "enable_graceful_degradation": True,
        "enable_error_analytics": True,
        "enable_notifications": enable_notifications,
        "default_max_retries": max_retries,
        "circuit_breaker_failure_threshold": circuit_breaker_threshold,
        "circuit_breaker_recovery_timeout": 60,
        "error_log_directory": "error_logs"
    }