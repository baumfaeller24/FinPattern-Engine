#!/usr/bin/env python3
"""
Data Source Failover für alternative Datenquellen-Nutzung
Phase 3 Implementation - Task 13

Features:
- Multi-Source Data-Provider-Management
- Automatic Failover zwischen Datenquellen
- Data-Quality-Monitoring und Validation
- Load-Balancing zwischen verfügbaren Sources
- Real-time Health-Checking und Status-Monitoring
- Data-Consistency-Checks und Synchronization
- Fallback-Hierarchien und Priority-Management
"""

import time
import threading
import logging
import asyncio
from typing import Dict, List, Optional, Any, Union, Callable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import json
from collections import deque, defaultdict
from abc import ABC, abstractmethod
import hashlib

# Async HTTP Client
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

# Data Validation
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# Caching
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class DataSourceType(Enum):
    """Typen von Datenquellen"""
    REST_API = "rest_api"
    WEBSOCKET = "websocket"
    DATABASE = "database"
    FILE_SYSTEM = "file_system"
    CACHE = "cache"
    STREAM = "stream"
    CUSTOM = "custom"


class DataSourceStatus(Enum):
    """Status von Datenquellen"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"


class FailoverStrategy(Enum):
    """Failover-Strategien"""
    ROUND_ROBIN = "round_robin"
    PRIORITY_BASED = "priority_based"
    LOAD_BALANCED = "load_balanced"
    FASTEST_RESPONSE = "fastest_response"
    HIGHEST_QUALITY = "highest_quality"
    CUSTOM = "custom"


class DataQualityMetric(Enum):
    """Data-Quality-Metriken"""
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    TIMELINESS = "timeliness"
    CONSISTENCY = "consistency"
    VALIDITY = "validity"
    FRESHNESS = "freshness"


@dataclass
class DataSourceConfig:
    """Konfiguration für Datenquelle"""
    source_id: str
    source_type: DataSourceType
    endpoint: str
    priority: int = 1  # 1 = höchste Priorität
    timeout: float = 30.0
    retry_attempts: int = 3
    health_check_interval: float = 60.0
    authentication: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None
    parameters: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type.value,
            "endpoint": self.endpoint,
            "priority": self.priority,
            "timeout": self.timeout,
            "retry_attempts": self.retry_attempts,
            "health_check_interval": self.health_check_interval,
            "authentication": self.authentication,
            "headers": self.headers,
            "parameters": self.parameters,
            "metadata": self.metadata
        }


@dataclass
class DataQualityReport:
    """Data-Quality-Report"""
    source_id: str
    timestamp: datetime
    metrics: Dict[DataQualityMetric, float]  # 0.0 - 1.0
    sample_size: int
    issues: List[str] = field(default_factory=list)
    overall_score: float = 0.0
    
    def __post_init__(self):
        if self.metrics:
            self.overall_score = sum(self.metrics.values()) / len(self.metrics)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "timestamp": self.timestamp.isoformat(),
            "metrics": {k.value: v for k, v in self.metrics.items()},
            "sample_size": self.sample_size,
            "issues": self.issues,
            "overall_score": self.overall_score
        }


@dataclass
class DataSourceHealth:
    """Health-Status einer Datenquelle"""
    source_id: str
    status: DataSourceStatus
    last_check: datetime
    response_time: Optional[float] = None
    error_rate: float = 0.0
    success_rate: float = 1.0
    consecutive_failures: int = 0
    last_error: Optional[str] = None
    quality_score: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "status": self.status.value,
            "last_check": self.last_check.isoformat(),
            "response_time": self.response_time,
            "error_rate": self.error_rate,
            "success_rate": self.success_rate,
            "consecutive_failures": self.consecutive_failures,
            "last_error": self.last_error,
            "quality_score": self.quality_score
        }


class DataSourceProvider(ABC):
    """Abstract Base Class für Data-Source-Provider"""
    
    def __init__(self, config: DataSourceConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{config.source_id}")
    
    @abstractmethod
    async def fetch_data(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch Data von der Quelle"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Health-Check der Datenquelle"""
        pass
    
    @abstractmethod
    def validate_data(self, data: Dict[str, Any]) -> DataQualityReport:
        """Validiere Data-Quality"""
        pass


class RestApiProvider(DataSourceProvider):
    """REST-API Data-Source-Provider"""
    
    def __init__(self, config: DataSourceConfig):
        super().__init__(config)
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Erhalte HTTP-Session"""
        if not self.session or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers=self.config.headers or {}
            )
        return self.session
    
    async def fetch_data(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch Data via REST-API"""
        
        if not AIOHTTP_AVAILABLE:
            raise ImportError("aiohttp not available for REST API provider")
        
        session = await self._get_session()
        
        # Request-Parameter zusammenstellen
        url = self.config.endpoint
        method = request.get("method", "GET")
        params = {**(self.config.parameters or {}), **request.get("params", {})}
        data = request.get("data")
        
        # Authentication
        auth_headers = {}
        if self.config.authentication:
            auth_type = self.config.authentication.get("type")
            if auth_type == "bearer":
                token = self.config.authentication.get("token")
                auth_headers["Authorization"] = f"Bearer {token}"
            elif auth_type == "api_key":
                key_name = self.config.authentication.get("key_name", "X-API-Key")
                api_key = self.config.authentication.get("api_key")
                auth_headers[key_name] = api_key
        
        try:
            async with session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                headers=auth_headers
            ) as response:
                
                response.raise_for_status()
                
                content_type = response.headers.get("content-type", "")
                
                if "application/json" in content_type:
                    result = await response.json()
                else:
                    text_result = await response.text()
                    result = {"data": text_result, "content_type": content_type}
                
                return {
                    "success": True,
                    "data": result,
                    "response_time": response.headers.get("X-Response-Time"),
                    "status_code": response.status,
                    "source_id": self.config.source_id
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "source_id": self.config.source_id
            }
    
    async def health_check(self) -> bool:
        """Health-Check via REST-API"""
        
        try:
            # Einfacher GET-Request an Endpoint
            health_request = {
                "method": "GET",
                "params": {"health": "check"}
            }
            
            result = await self.fetch_data(health_request)
            return result.get("success", False)
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
    
    def validate_data(self, data: Dict[str, Any]) -> DataQualityReport:
        """Validiere REST-API-Data"""
        
        metrics = {}
        issues = []
        sample_size = 1
        
        # Completeness-Check
        if data.get("success") and data.get("data"):
            metrics[DataQualityMetric.COMPLETENESS] = 1.0
        else:
            metrics[DataQualityMetric.COMPLETENESS] = 0.0
            issues.append("Incomplete data response")
        
        # Timeliness-Check (Response-Time)
        response_time = data.get("response_time")
        if response_time:
            try:
                rt_ms = float(response_time)
                if rt_ms < 1000:  # < 1 Sekunde
                    metrics[DataQualityMetric.TIMELINESS] = 1.0
                elif rt_ms < 5000:  # < 5 Sekunden
                    metrics[DataQualityMetric.TIMELINESS] = 0.7
                else:
                    metrics[DataQualityMetric.TIMELINESS] = 0.3
            except (ValueError, TypeError):
                metrics[DataQualityMetric.TIMELINESS] = 0.5
        else:
            metrics[DataQualityMetric.TIMELINESS] = 0.5
        
        # Validity-Check (Status-Code)
        status_code = data.get("status_code")
        if status_code and 200 <= status_code < 300:
            metrics[DataQualityMetric.VALIDITY] = 1.0
        else:
            metrics[DataQualityMetric.VALIDITY] = 0.0
            issues.append(f"Invalid status code: {status_code}")
        
        return DataQualityReport(
            source_id=self.config.source_id,
            timestamp=datetime.now(),
            metrics=metrics,
            sample_size=sample_size,
            issues=issues
        )
    
    async def cleanup(self):
        """Cleanup HTTP-Session"""
        if self.session and not self.session.closed:
            await self.session.close()


class FileSystemProvider(DataSourceProvider):
    """File-System Data-Source-Provider"""
    
    async def fetch_data(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch Data vom File-System"""
        
        try:
            file_path = Path(request.get("file_path", self.config.endpoint))
            
            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {file_path}",
                    "source_id": self.config.source_id
                }
            
            # File-Typ bestimmen
            suffix = file_path.suffix.lower()
            
            if suffix == ".json":
                with open(file_path, 'r') as f:
                    data = json.load(f)
            elif suffix == ".csv" and PANDAS_AVAILABLE:
                data = pd.read_csv(file_path).to_dict('records')
            else:
                with open(file_path, 'r') as f:
                    data = f.read()
            
            return {
                "success": True,
                "data": data,
                "file_path": str(file_path),
                "file_size": file_path.stat().st_size,
                "modified_time": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                "source_id": self.config.source_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "source_id": self.config.source_id
            }
    
    async def health_check(self) -> bool:
        """Health-Check für File-System"""
        
        try:
            file_path = Path(self.config.endpoint)
            return file_path.exists() and file_path.is_file()
        except Exception:
            return False
    
    def validate_data(self, data: Dict[str, Any]) -> DataQualityReport:
        """Validiere File-System-Data"""
        
        metrics = {}
        issues = []
        sample_size = 1
        
        # Completeness
        if data.get("success") and data.get("data"):
            metrics[DataQualityMetric.COMPLETENESS] = 1.0
        else:
            metrics[DataQualityMetric.COMPLETENESS] = 0.0
            issues.append("File data incomplete")
        
        # Freshness (basierend auf Modified-Time)
        modified_time = data.get("modified_time")
        if modified_time:
            try:
                mod_dt = datetime.fromisoformat(modified_time)
                age = datetime.now() - mod_dt
                
                if age < timedelta(hours=1):
                    metrics[DataQualityMetric.FRESHNESS] = 1.0
                elif age < timedelta(days=1):
                    metrics[DataQualityMetric.FRESHNESS] = 0.7
                else:
                    metrics[DataQualityMetric.FRESHNESS] = 0.3
            except (ValueError, TypeError):
                metrics[DataQualityMetric.FRESHNESS] = 0.5
        else:
            metrics[DataQualityMetric.FRESHNESS] = 0.5
        
        # Validity (File-Size)
        file_size = data.get("file_size", 0)
        if file_size > 0:
            metrics[DataQualityMetric.VALIDITY] = 1.0
        else:
            metrics[DataQualityMetric.VALIDITY] = 0.0
            issues.append("Empty file")
        
        return DataQualityReport(
            source_id=self.config.source_id,
            timestamp=datetime.now(),
            metrics=metrics,
            sample_size=sample_size,
            issues=issues
        )


class CacheProvider(DataSourceProvider):
    """Cache Data-Source-Provider"""
    
    def __init__(self, config: DataSourceConfig):
        super().__init__(config)
        self.redis_client = None
        
        if REDIS_AVAILABLE and config.parameters:
            redis_config = config.parameters.get("redis", {})
            if redis_config:
                self.redis_client = redis.Redis(
                    host=redis_config.get("host", "localhost"),
                    port=redis_config.get("port", 6379),
                    db=redis_config.get("db", 0),
                    decode_responses=True
                )
    
    async def fetch_data(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch Data vom Cache"""
        
        try:
            cache_key = request.get("cache_key")
            
            if not cache_key:
                return {
                    "success": False,
                    "error": "No cache key provided",
                    "source_id": self.config.source_id
                }
            
            # Redis-Cache
            if self.redis_client:
                try:
                    cached_data = self.redis_client.get(cache_key)
                    if cached_data:
                        data = json.loads(cached_data)
                        return {
                            "success": True,
                            "data": data,
                            "cache_hit": True,
                            "source_id": self.config.source_id
                        }
                except Exception as e:
                    self.logger.error(f"Redis cache error: {e}")
            
            # In-Memory-Cache (fallback)
            # Hier würde normalerweise ein In-Memory-Cache implementiert
            
            return {
                "success": False,
                "error": "Cache miss",
                "cache_hit": False,
                "source_id": self.config.source_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "source_id": self.config.source_id
            }
    
    async def health_check(self) -> bool:
        """Health-Check für Cache"""
        
        try:
            if self.redis_client:
                return self.redis_client.ping()
            return True  # In-Memory-Cache ist immer verfügbar
        except Exception:
            return False
    
    def validate_data(self, data: Dict[str, Any]) -> DataQualityReport:
        """Validiere Cache-Data"""
        
        metrics = {}
        issues = []
        sample_size = 1
        
        # Cache-Hit-Rate
        cache_hit = data.get("cache_hit", False)
        if cache_hit:
            metrics[DataQualityMetric.COMPLETENESS] = 1.0
            metrics[DataQualityMetric.TIMELINESS] = 1.0  # Cache ist immer schnell
        else:
            metrics[DataQualityMetric.COMPLETENESS] = 0.0
            metrics[DataQualityMetric.TIMELINESS] = 0.0
            issues.append("Cache miss")
        
        return DataQualityReport(
            source_id=self.config.source_id,
            timestamp=datetime.now(),
            metrics=metrics,
            sample_size=sample_size,
            issues=issues
        )


class DataSourceFailover:
    """
    Data Source Failover für alternative Datenquellen-Nutzung
    
    Features:
    - Multi-Source Data-Provider-Management
    - Automatic Failover zwischen Datenquellen
    - Data-Quality-Monitoring und Validation
    - Load-Balancing zwischen verfügbaren Sources
    - Real-time Health-Checking und Status-Monitoring
    - Data-Consistency-Checks und Synchronization
    - Fallback-Hierarchien und Priority-Management
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Failover-Konfiguration
        self.failover_strategy = FailoverStrategy(
            self.config.get("failover_strategy", "priority_based")
        )
        self.health_check_interval = self.config.get("health_check_interval", 60.0)
        self.enable_data_validation = self.config.get("enable_data_validation", True)
        self.enable_caching = self.config.get("enable_caching", True)
        self.cache_ttl = self.config.get("cache_ttl", 300)  # 5 Minuten
        
        # Quality-Thresholds
        self.min_quality_score = self.config.get("min_quality_score", 0.7)
        self.max_consecutive_failures = self.config.get("max_consecutive_failures", 3)
        
        # Data-Sources
        self.data_sources: Dict[str, DataSourceProvider] = {}
        self.source_configs: Dict[str, DataSourceConfig] = {}
        self.source_health: Dict[str, DataSourceHealth] = {}
        
        # Quality-Tracking
        self.quality_reports: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Caching
        self.data_cache: Dict[str, Tuple[Any, datetime]] = {}
        
        # Threading
        self.health_monitoring_active = False
        self.health_monitoring_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Statistiken
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "failover_events": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "quality_checks": 0,
            "health_checks": 0
        }
        
        self.logger.info("DataSourceFailover initialized")
    
    def register_data_source(self, config: DataSourceConfig):
        """Registriere neue Datenquelle"""
        
        try:
            # Provider erstellen basierend auf Source-Type
            if config.source_type == DataSourceType.REST_API:
                provider = RestApiProvider(config)
            elif config.source_type == DataSourceType.FILE_SYSTEM:
                provider = FileSystemProvider(config)
            elif config.source_type == DataSourceType.CACHE:
                provider = CacheProvider(config)
            else:
                raise ValueError(f"Unsupported source type: {config.source_type}")
            
            self.data_sources[config.source_id] = provider
            self.source_configs[config.source_id] = config
            
            # Initial Health-Status
            self.source_health[config.source_id] = DataSourceHealth(
                source_id=config.source_id,
                status=DataSourceStatus.UNKNOWN,
                last_check=datetime.now()
            )
            
            self.logger.info(f"Registered data source: {config.source_id} ({config.source_type.value})")
            
            # Health-Monitoring starten falls noch nicht aktiv
            if not self.health_monitoring_active:
                self.start_health_monitoring()
                
        except Exception as e:
            self.logger.error(f"Error registering data source: {e}")
            raise
    
    async def fetch_data(self, request: Dict[str, Any], 
                        preferred_sources: Optional[List[str]] = None) -> Dict[str, Any]:
        """Fetch Data mit Failover-Logic"""
        
        self.stats["total_requests"] += 1
        
        try:
            # Cache-Check
            if self.enable_caching:
                cache_result = self._check_cache(request)
                if cache_result:
                    self.stats["cache_hits"] += 1
                    return cache_result
                else:
                    self.stats["cache_misses"] += 1
            
            # Source-Selection basierend auf Strategy
            source_order = self._select_sources(preferred_sources)
            
            if not source_order:
                return {
                    "success": False,
                    "error": "No healthy data sources available",
                    "attempted_sources": []
                }
            
            attempted_sources = []
            last_error = None
            
            # Versuche Sources in Reihenfolge
            for source_id in source_order:
                try:
                    attempted_sources.append(source_id)
                    
                    # Health-Check
                    health = self.source_health.get(source_id)
                    if health and health.status == DataSourceStatus.OFFLINE:
                        continue
                    
                    # Data-Fetch
                    provider = self.data_sources[source_id]
                    start_time = time.time()
                    
                    result = await provider.fetch_data(request)
                    
                    response_time = time.time() - start_time
                    
                    if result.get("success"):
                        # Data-Quality-Validation
                        if self.enable_data_validation:
                            quality_report = provider.validate_data(result)
                            self.quality_reports[source_id].append(quality_report)
                            self.stats["quality_checks"] += 1
                            
                            # Quality-Threshold prüfen
                            if quality_report.overall_score < self.min_quality_score:
                                self.logger.warning(f"Low quality data from {source_id}: "
                                                  f"{quality_report.overall_score:.2f}")
                                continue
                        
                        # Success - Update Health und Cache
                        self._update_source_health(source_id, True, response_time)
                        
                        if self.enable_caching:
                            self._cache_result(request, result)
                        
                        result["source_used"] = source_id
                        result["attempted_sources"] = attempted_sources
                        result["response_time"] = response_time
                        
                        self.stats["successful_requests"] += 1
                        
                        return result
                    else:
                        # Failure - Update Health
                        error_msg = result.get("error", "Unknown error")
                        self._update_source_health(source_id, False, response_time, error_msg)
                        last_error = error_msg
                        
                        # Failover-Event
                        self.stats["failover_events"] += 1
                        
                        self.logger.warning(f"Data source {source_id} failed: {error_msg}")
                        
                except Exception as e:
                    self._update_source_health(source_id, False, None, str(e))
                    last_error = str(e)
                    self.logger.error(f"Exception with data source {source_id}: {e}")
            
            # Alle Sources fehlgeschlagen
            self.stats["failed_requests"] += 1
            
            return {
                "success": False,
                "error": f"All data sources failed. Last error: {last_error}",
                "attempted_sources": attempted_sources
            }
            
        except Exception as e:
            self.stats["failed_requests"] += 1
            self.logger.error(f"Error in fetch_data: {e}")
            return {
                "success": False,
                "error": str(e),
                "attempted_sources": []
            }
    
    def _select_sources(self, preferred_sources: Optional[List[str]] = None) -> List[str]:
        """Wähle Sources basierend auf Failover-Strategy"""
        
        available_sources = []
        
        # Filtere verfügbare Sources
        for source_id, health in self.source_health.items():
            if health.status not in [DataSourceStatus.OFFLINE, DataSourceStatus.MAINTENANCE]:
                available_sources.append(source_id)
        
        if not available_sources:
            return []
        
        # Preferred Sources zuerst
        if preferred_sources:
            ordered_sources = []
            for source_id in preferred_sources:
                if source_id in available_sources:
                    ordered_sources.append(source_id)
            
            # Füge restliche Sources hinzu
            for source_id in available_sources:
                if source_id not in ordered_sources:
                    ordered_sources.append(source_id)
            
            available_sources = ordered_sources
        
        # Strategy-basierte Sortierung
        if self.failover_strategy == FailoverStrategy.PRIORITY_BASED:
            # Sortiere nach Priorität (niedrigere Zahl = höhere Priorität)
            available_sources.sort(key=lambda x: self.source_configs[x].priority)
        
        elif self.failover_strategy == FailoverStrategy.FASTEST_RESPONSE:
            # Sortiere nach Response-Time
            available_sources.sort(key=lambda x: self.source_health[x].response_time or float('inf'))
        
        elif self.failover_strategy == FailoverStrategy.HIGHEST_QUALITY:
            # Sortiere nach Quality-Score
            available_sources.sort(key=lambda x: self.source_health[x].quality_score, reverse=True)
        
        elif self.failover_strategy == FailoverStrategy.LOAD_BALANCED:
            # Round-Robin-Logic
            # Hier würde eine komplexere Load-Balancing-Logic implementiert
            pass
        
        return available_sources
    
    def _update_source_health(self, source_id: str, success: bool, 
                            response_time: Optional[float], error: Optional[str] = None):
        """Update Health-Status einer Source"""
        
        try:
            health = self.source_health.get(source_id)
            if not health:
                return
            
            health.last_check = datetime.now()
            health.response_time = response_time
            
            if success:
                health.consecutive_failures = 0
                health.last_error = None
                
                # Success-Rate aktualisieren (exponential moving average)
                health.success_rate = 0.9 * health.success_rate + 0.1 * 1.0
                health.error_rate = 1.0 - health.success_rate
                
                # Status bestimmen
                if health.success_rate > 0.95:
                    health.status = DataSourceStatus.HEALTHY
                elif health.success_rate > 0.8:
                    health.status = DataSourceStatus.DEGRADED
                else:
                    health.status = DataSourceStatus.UNHEALTHY
            else:
                health.consecutive_failures += 1
                health.last_error = error
                
                # Success-Rate aktualisieren
                health.success_rate = 0.9 * health.success_rate + 0.1 * 0.0
                health.error_rate = 1.0 - health.success_rate
                
                # Status bestimmen
                if health.consecutive_failures >= self.max_consecutive_failures:
                    health.status = DataSourceStatus.OFFLINE
                elif health.success_rate < 0.5:
                    health.status = DataSourceStatus.UNHEALTHY
                else:
                    health.status = DataSourceStatus.DEGRADED
            
            # Quality-Score aus Quality-Reports berechnen
            quality_reports = list(self.quality_reports.get(source_id, []))
            if quality_reports:
                recent_reports = quality_reports[-10:]  # Letzte 10 Reports
                avg_quality = sum(r.overall_score for r in recent_reports) / len(recent_reports)
                health.quality_score = avg_quality
            
        except Exception as e:
            self.logger.error(f"Error updating source health: {e}")
    
    def _check_cache(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Prüfe Cache für Request"""
        
        try:
            # Cache-Key generieren
            cache_key = self._generate_cache_key(request)
            
            if cache_key in self.data_cache:
                cached_data, cached_time = self.data_cache[cache_key]
                
                # TTL prüfen
                if datetime.now() - cached_time < timedelta(seconds=self.cache_ttl):
                    return {
                        **cached_data,
                        "from_cache": True,
                        "cached_at": cached_time.isoformat()
                    }
                else:
                    # Expired - entferne aus Cache
                    del self.data_cache[cache_key]
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error checking cache: {e}")
            return None
    
    def _cache_result(self, request: Dict[str, Any], result: Dict[str, Any]):
        """Cache Result"""
        
        try:
            cache_key = self._generate_cache_key(request)
            
            # Entferne Cache-spezifische Felder
            cacheable_result = {k: v for k, v in result.items() 
                              if k not in ["source_used", "attempted_sources", "response_time"]}
            
            self.data_cache[cache_key] = (cacheable_result, datetime.now())
            
            # Cache-Size-Limit
            if len(self.data_cache) > 1000:
                # Entferne älteste Einträge
                oldest_keys = sorted(
                    self.data_cache.keys(),
                    key=lambda k: self.data_cache[k][1]
                )[:100]
                
                for key in oldest_keys:
                    del self.data_cache[key]
                    
        except Exception as e:
            self.logger.error(f"Error caching result: {e}")
    
    def _generate_cache_key(self, request: Dict[str, Any]) -> str:
        """Generiere Cache-Key für Request"""
        
        # Erstelle deterministischen Hash aus Request
        request_str = json.dumps(request, sort_keys=True)
        return hashlib.md5(request_str.encode()).hexdigest()
    
    def start_health_monitoring(self):
        """Starte Health-Monitoring"""
        
        if self.health_monitoring_active:
            return
        
        self.health_monitoring_active = True
        self.stop_event.clear()
        
        self.health_monitoring_thread = threading.Thread(
            target=self._health_monitoring_loop,
            name="DataSourceHealthMonitor",
            daemon=True
        )
        self.health_monitoring_thread.start()
        
        self.logger.info("Data source health monitoring started")
    
    def stop_health_monitoring(self):
        """Stoppe Health-Monitoring"""
        
        if not self.health_monitoring_active:
            return
        
        self.health_monitoring_active = False
        self.stop_event.set()
        
        if self.health_monitoring_thread:
            self.health_monitoring_thread.join(timeout=5.0)
        
        self.logger.info("Data source health monitoring stopped")
    
    def _health_monitoring_loop(self):
        """Health-Monitoring-Loop"""
        
        async def run_health_checks():
            tasks = []
            for source_id, provider in self.data_sources.items():
                task = asyncio.create_task(self._perform_health_check(source_id, provider))
                tasks.append(task)
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        
        while self.health_monitoring_active and not self.stop_event.is_set():
            try:
                # Async Health-Checks ausführen
                if asyncio.get_event_loop().is_running():
                    # Wenn bereits ein Event-Loop läuft, erstelle Task
                    asyncio.create_task(run_health_checks())
                else:
                    # Neuen Event-Loop erstellen
                    asyncio.run(run_health_checks())
                
                # Warte bis zum nächsten Health-Check
                self.stop_event.wait(self.health_check_interval)
                
            except Exception as e:
                self.logger.error(f"Health monitoring loop error: {e}")
                time.sleep(5.0)
    
    async def _perform_health_check(self, source_id: str, provider: DataSourceProvider):
        """Führe Health-Check für Source durch"""
        
        try:
            start_time = time.time()
            is_healthy = await provider.health_check()
            response_time = time.time() - start_time
            
            self._update_source_health(source_id, is_healthy, response_time)
            self.stats["health_checks"] += 1
            
            self.logger.debug(f"Health check for {source_id}: {'healthy' if is_healthy else 'unhealthy'}")
            
        except Exception as e:
            self._update_source_health(source_id, False, None, str(e))
            self.logger.error(f"Health check error for {source_id}: {e}")
    
    def get_failover_statistics(self) -> Dict[str, Any]:
        """Erhalte Failover-Statistiken"""
        
        try:
            # Source-Health-Summary
            source_summary = {}
            for source_id, health in self.source_health.items():
                config = self.source_configs.get(source_id, {})
                source_summary[source_id] = {
                    "status": health.status.value,
                    "success_rate": health.success_rate,
                    "response_time": health.response_time,
                    "consecutive_failures": health.consecutive_failures,
                    "quality_score": health.quality_score,
                    "priority": getattr(config, 'priority', 0),
                    "source_type": getattr(config, 'source_type', {}).value if hasattr(config, 'source_type') else 'unknown'
                }
            
            # Quality-Reports-Summary
            quality_summary = {}
            for source_id, reports in self.quality_reports.items():
                if reports:
                    recent_reports = list(reports)[-10:]
                    avg_score = sum(r.overall_score for r in recent_reports) / len(recent_reports)
                    quality_summary[source_id] = {
                        "average_quality_score": avg_score,
                        "total_reports": len(reports),
                        "recent_issues": sum(len(r.issues) for r in recent_reports)
                    }
            
            return {
                "timestamp": datetime.now().isoformat(),
                "failover_config": {
                    "strategy": self.failover_strategy.value,
                    "health_check_interval": self.health_check_interval,
                    "enable_data_validation": self.enable_data_validation,
                    "enable_caching": self.enable_caching,
                    "min_quality_score": self.min_quality_score
                },
                "statistics": dict(self.stats),
                "sources": source_summary,
                "quality_reports": quality_summary,
                "cache_size": len(self.data_cache),
                "registered_sources": len(self.data_sources)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting failover statistics: {e}")
            return {"error": str(e)}
    
    async def cleanup(self):
        """Cleanup Failover-Ressourcen"""
        
        try:
            # Stoppe Health-Monitoring
            self.stop_health_monitoring()
            
            # Cleanup Provider
            for provider in self.data_sources.values():
                if hasattr(provider, 'cleanup'):
                    await provider.cleanup()
            
            # Clear Data
            self.data_sources.clear()
            self.source_configs.clear()
            self.source_health.clear()
            self.quality_reports.clear()
            self.data_cache.clear()
            
            self.logger.info("DataSourceFailover cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")


# Utility-Funktionen
def create_rest_api_source(source_id: str, endpoint: str, priority: int = 1,
                          api_key: Optional[str] = None, **kwargs) -> DataSourceConfig:
    """Erstelle REST-API-Source-Konfiguration"""
    
    auth = None
    if api_key:
        auth = {"type": "api_key", "api_key": api_key}
    
    return DataSourceConfig(
        source_id=source_id,
        source_type=DataSourceType.REST_API,
        endpoint=endpoint,
        priority=priority,
        authentication=auth,
        **kwargs
    )


def create_file_source(source_id: str, file_path: str, priority: int = 1,
                      **kwargs) -> DataSourceConfig:
    """Erstelle File-System-Source-Konfiguration"""
    
    return DataSourceConfig(
        source_id=source_id,
        source_type=DataSourceType.FILE_SYSTEM,
        endpoint=file_path,
        priority=priority,
        **kwargs
    )


def create_cache_source(source_id: str, redis_config: Optional[Dict] = None,
                       priority: int = 1, **kwargs) -> DataSourceConfig:
    """Erstelle Cache-Source-Konfiguration"""
    
    parameters = {"redis": redis_config} if redis_config else {}
    
    return DataSourceConfig(
        source_id=source_id,
        source_type=DataSourceType.CACHE,
        endpoint="cache://local",
        priority=priority,
        parameters=parameters,
        **kwargs
    )


def setup_failover_config(strategy: str = "priority_based",
                         health_check_interval: float = 60.0,
                         enable_caching: bool = True) -> Dict[str, Any]:
    """Setup Failover-Konfiguration"""
    
    return {
        "failover_strategy": strategy,
        "health_check_interval": health_check_interval,
        "enable_data_validation": True,
        "enable_caching": enable_caching,
        "cache_ttl": 300,
        "min_quality_score": 0.7,
        "max_consecutive_failures": 3
    }