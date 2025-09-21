#!/usr/bin/env python3
"""
Environment Manager für AI-Indicator-Optimizer
Task 18 Implementation - Environment Configuration

Features:
- Environment-Variable-basierte Konfiguration für produktive Deployments
- Configuration-Hot-Reload ohne System-Restart
- Multi-Environment-Support (Development, Staging, Production)
- Secure Configuration Management
"""

import os
import json
import yaml
import logging
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class Environment(Enum):
    """Supported environments"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


@dataclass
class ConfigSource:
    """Configuration source information"""
    source_type: str  # file, env, remote
    path: Optional[str] = None
    last_modified: Optional[float] = None
    checksum: Optional[str] = None
    priority: int = 1  # Higher number = higher priority


class ConfigFileHandler(FileSystemEventHandler):
    """File system event handler for config file changes"""
    
    def __init__(self, environment_manager):
        self.environment_manager = environment_manager
        self.logger = logging.getLogger(__name__)
    
    def on_modified(self, event):
        if not event.is_directory:
            file_path = Path(event.src_path)
            
            # Check if it's a config file we're watching
            if file_path.suffix in ['.json', '.yaml', '.yml', '.env']:
                self.logger.info(f"Config file changed: {file_path}")
                self.environment_manager._trigger_reload(str(file_path))


class EnvironmentManager:
    """
    Environment Manager für Multi-Environment Configuration
    
    Features:
    - Environment-based configuration
    - Hot-reload capabilities
    - Secure secret management
    - Configuration validation
    - Multi-source configuration merging
    """
    
    def __init__(self, 
                 environment: Union[Environment, str] = None,
                 config_dir: str = "config",
                 enable_hot_reload: bool = True):
        """
        Initialize Environment Manager
        
        Args:
            environment: Target environment
            config_dir: Configuration directory
            enable_hot_reload: Enable hot-reload functionality
        """
        self.logger = logging.getLogger(__name__)
        
        # Environment setup
        if isinstance(environment, str):
            environment = Environment(environment)
        self.environment = environment or self._detect_environment()
        
        # Paths
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # Configuration state
        self.config: Dict[str, Any] = {}
        self.config_sources: List[ConfigSource] = []
        self.reload_callbacks: List[callable] = []
        
        # Hot-reload setup
        self.enable_hot_reload = enable_hot_reload
        self.file_observer = None
        self.reload_lock = threading.Lock()
        
        # Load initial configuration
        self._load_configuration()
        
        # Start file watching if enabled
        if self.enable_hot_reload:
            self._start_file_watching()
        
        self.logger.info(f"EnvironmentManager initialized: {self.environment.value}")
    
    def _detect_environment(self) -> Environment:
        """Detect current environment from environment variables"""
        
        env_name = os.getenv("AI_ENVIRONMENT", os.getenv("ENVIRONMENT", "development")).lower()
        
        try:
            return Environment(env_name)
        except ValueError:
            self.logger.warning(f"Unknown environment '{env_name}', defaulting to development")
            return Environment.DEVELOPMENT
    
    def _load_configuration(self) -> None:
        """Load configuration from all sources"""
        
        with self.reload_lock:
            self.config = {}
            self.config_sources = []
            
            # Load in priority order
            self._load_base_config()
            self._load_environment_config()
            self._load_local_config()
            self._load_environment_variables()
            self._load_secrets()
            
            # Validate configuration
            self._validate_configuration()
            
            self.logger.info(f"Configuration loaded from {len(self.config_sources)} sources")
    
    def _load_base_config(self) -> None:
        """Load base configuration"""
        
        base_config_path = self.config_dir / "base.json"
        
        if base_config_path.exists():
            config_data = self._load_config_file(base_config_path)
            if config_data:
                self._merge_config(config_data)
                self.config_sources.append(ConfigSource(
                    source_type="file",
                    path=str(base_config_path),
                    last_modified=base_config_path.stat().st_mtime,
                    priority=1
                ))
    
    def _load_environment_config(self) -> None:
        """Load environment-specific configuration"""
        
        env_config_path = self.config_dir / f"{self.environment.value}.json"
        
        if env_config_path.exists():
            config_data = self._load_config_file(env_config_path)
            if config_data:
                self._merge_config(config_data)
                self.config_sources.append(ConfigSource(
                    source_type="file",
                    path=str(env_config_path),
                    last_modified=env_config_path.stat().st_mtime,
                    priority=2
                ))
    
    def _load_local_config(self) -> None:
        """Load local configuration (not in version control)"""
        
        local_config_path = self.config_dir / "local.json"
        
        if local_config_path.exists():
            config_data = self._load_config_file(local_config_path)
            if config_data:
                self._merge_config(config_data)
                self.config_sources.append(ConfigSource(
                    source_type="file",
                    path=str(local_config_path),
                    last_modified=local_config_path.stat().st_mtime,
                    priority=3
                ))
    
    def _load_environment_variables(self) -> None:
        """Load configuration from environment variables"""
        
        env_config = {}
        
        # AI-specific environment variables
        ai_env_vars = {
            "AI_ENVIRONMENT": "environment",
            "AI_LOG_LEVEL": "logging.level",
            "AI_CPU_CORES": "hardware.cpu_cores",
            "AI_GPU_MEMORY": "hardware.gpu_memory_gb",
            "AI_RAM_GB": "hardware.ram_gb",
            "AI_USE_GPU": "hardware.use_gpu",
            "OLLAMA_MODEL": "ollama.model",
            "OLLAMA_HOST": "ollama.host",
            "OLLAMA_PORT": "ollama.port",
            "TRADING_SYMBOL": "data.symbol",
            "TRADING_TIMEFRAME": "data.timeframe",
            "DATA_DAYS_BACK": "data.days_back",
            "USE_REAL_DATA": "data.use_real_data",
            "CONFIDENCE_THRESHOLD": "trading.confidence_threshold",
            "MAX_POSITION_SIZE": "trading.max_position_size",
            "RISK_PER_TRADE": "trading.risk_per_trade",
            "PARQUET_BUFFER_SIZE": "logging.parquet_buffer_size",
            "ENABLE_PERF_LOG": "logging.enable_performance_logging",
            "TORCHSERVE_URL": "torchserve.base_url",
            "TORCHSERVE_TIMEOUT": "torchserve.timeout",
            "TORCHSERVE_BATCH_SIZE": "torchserve.batch_size",
            "TORCHSERVE_GPU": "torchserve.gpu_enabled",
            "ENABLE_TORCHSERVE": "torchserve.enable_torchserve",
            "REDIS_HOST": "redis.host",
            "REDIS_PORT": "redis.port",
            "REDIS_DB": "redis.db",
            "ENABLE_REDIS": "redis.enabled",
            "KAFKA_BOOTSTRAP_SERVERS": "kafka.bootstrap_servers",
            "KAFKA_CONTROL_TOPIC": "kafka.control_topic",
            "ENABLE_KAFKA": "kafka.enabled"
        }
        
        for env_var, config_path in ai_env_vars.items():
            value = os.getenv(env_var)
            if value is not None:
                self._set_nested_value(env_config, config_path, self._convert_env_value(value))
        
        if env_config:
            self._merge_config(env_config)
            self.config_sources.append(ConfigSource(
                source_type="env",
                priority=4
            ))
    
    def _load_secrets(self) -> None:
        """Load secrets from secure sources"""
        
        secrets_path = self.config_dir / "secrets.json"
        
        if secrets_path.exists():
            try:
                config_data = self._load_config_file(secrets_path)
                if config_data:
                    self._merge_config(config_data)
                    self.config_sources.append(ConfigSource(
                        source_type="secrets",
                        path=str(secrets_path),
                        last_modified=secrets_path.stat().st_mtime,
                        priority=5
                    ))
            except Exception as e:
                self.logger.error(f"Failed to load secrets: {e}")
    
    def _load_config_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Load configuration from file"""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix == '.json':
                    return json.load(f)
                elif file_path.suffix in ['.yaml', '.yml']:
                    return yaml.safe_load(f)
                else:
                    self.logger.warning(f"Unsupported config file format: {file_path}")
                    return None
        
        except Exception as e:
            self.logger.error(f"Failed to load config file {file_path}: {e}")
            return None
    
    def _merge_config(self, new_config: Dict[str, Any]) -> None:
        """Merge new configuration into existing config"""
        
        def deep_merge(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
            for key, value in update.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    deep_merge(base[key], value)
                else:
                    base[key] = value
            return base
        
        deep_merge(self.config, new_config)
    
    def _set_nested_value(self, config: Dict[str, Any], path: str, value: Any) -> None:
        """Set nested configuration value using dot notation"""
        
        keys = path.split('.')
        current = config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable string to appropriate type"""
        
        # Boolean conversion
        if value.lower() in ['true', 'false']:
            return value.lower() == 'true'
        
        # Integer conversion
        try:
            if '.' not in value:
                return int(value)
        except ValueError:
            pass
        
        # Float conversion
        try:
            return float(value)
        except ValueError:
            pass
        
        # JSON conversion
        if value.startswith('{') or value.startswith('['):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        
        # String (default)
        return value
    
    def _validate_configuration(self) -> None:
        """Validate loaded configuration"""
        
        # Required configuration keys
        required_keys = [
            "hardware",
            "ollama",
            "data",
            "trading",
            "logging"
        ]
        
        for key in required_keys:
            if key not in self.config:
                self.logger.warning(f"Missing required configuration section: {key}")
        
        # Environment-specific validation
        if self.environment == Environment.PRODUCTION:
            self._validate_production_config()
    
    def _validate_production_config(self) -> None:
        """Validate production-specific configuration"""
        
        # Check for development settings in production
        dev_indicators = [
            ("data.use_real_data", True),
            ("logging.level", "INFO"),
            ("torchserve.enable_torchserve", True)
        ]
        
        for config_path, expected_value in dev_indicators:
            current_value = self.get(config_path)
            if current_value != expected_value:
                self.logger.warning(f"Production config check: {config_path} = {current_value}, expected {expected_value}")
    
    def _start_file_watching(self) -> None:
        """Start file system watching for hot-reload"""
        
        try:
            self.file_observer = Observer()
            event_handler = ConfigFileHandler(self)
            
            # Watch config directory
            self.file_observer.schedule(event_handler, str(self.config_dir), recursive=False)
            self.file_observer.start()
            
            self.logger.info("File watching started for hot-reload")
            
        except Exception as e:
            self.logger.error(f"Failed to start file watching: {e}")
            self.file_observer = None
    
    def _trigger_reload(self, file_path: str) -> None:
        """Trigger configuration reload"""
        
        try:
            # Debounce rapid file changes
            time.sleep(0.1)
            
            self.logger.info(f"Reloading configuration due to change in: {file_path}")
            
            old_config = self.config.copy()
            self._load_configuration()
            
            # Notify callbacks
            for callback in self.reload_callbacks:
                try:
                    callback(old_config, self.config)
                except Exception as e:
                    self.logger.error(f"Reload callback failed: {e}")
            
            self.logger.info("Configuration reloaded successfully")
            
        except Exception as e:
            self.logger.error(f"Configuration reload failed: {e}")
    
    def stop(self) -> None:
        """Stop environment manager"""
        
        if self.file_observer:
            self.file_observer.stop()
            self.file_observer.join()
            self.file_observer = None
        
        self.logger.info("EnvironmentManager stopped")
    
    # Public API
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with dot notation support
        
        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any, persist: bool = False) -> None:
        """
        Set configuration value
        
        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
            persist: Whether to persist to file
        """
        
        with self.reload_lock:
            self._set_nested_value(self.config, key, value)
            
            if persist:
                self._persist_config_change(key, value)
    
    def _persist_config_change(self, key: str, value: Any) -> None:
        """Persist configuration change to file"""
        
        try:
            # Save to local config file
            local_config_path = self.config_dir / "local.json"
            
            local_config = {}
            if local_config_path.exists():
                local_config = self._load_config_file(local_config_path) or {}
            
            self._set_nested_value(local_config, key, value)
            
            with open(local_config_path, 'w', encoding='utf-8') as f:
                json.dump(local_config, f, indent=2)
            
            self.logger.info(f"Configuration change persisted: {key} = {value}")
            
        except Exception as e:
            self.logger.error(f"Failed to persist config change: {e}")
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration"""
        
        return self.config.copy()
    
    def get_environment(self) -> Environment:
        """Get current environment"""
        
        return self.environment
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        
        return self.environment == Environment.PRODUCTION
    
    def is_development(self) -> bool:
        """Check if running in development environment"""
        
        return self.environment == Environment.DEVELOPMENT
    
    def register_reload_callback(self, callback: callable) -> None:
        """
        Register callback for configuration reload events
        
        Args:
            callback: Function to call on reload (old_config, new_config)
        """
        
        self.reload_callbacks.append(callback)
    
    def get_config_sources(self) -> List[ConfigSource]:
        """Get information about configuration sources"""
        
        return self.config_sources.copy()
    
    def reload(self) -> None:
        """Manually trigger configuration reload"""
        
        self._trigger_reload("manual_reload")
    
    def export_config(self, file_path: str, include_secrets: bool = False) -> None:
        """
        Export current configuration to file
        
        Args:
            file_path: Output file path
            include_secrets: Whether to include sensitive data
        """
        
        try:
            config_to_export = self.config.copy()
            
            if not include_secrets:
                # Remove sensitive keys
                sensitive_keys = ['secrets', 'passwords', 'tokens', 'keys']
                for key in sensitive_keys:
                    if key in config_to_export:
                        del config_to_export[key]
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_to_export, f, indent=2)
            
            self.logger.info(f"Configuration exported to: {file_path}")
            
        except Exception as e:
            self.logger.error(f"Configuration export failed: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get environment manager status"""
        
        return {
            "environment": self.environment.value,
            "config_dir": str(self.config_dir),
            "hot_reload_enabled": self.enable_hot_reload,
            "file_watching_active": self.file_observer is not None,
            "config_sources_count": len(self.config_sources),
            "config_keys_count": len(self._flatten_dict(self.config)),
            "reload_callbacks_count": len(self.reload_callbacks),
            "last_reload": datetime.now().isoformat()
        }
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """Flatten nested dictionary"""
        
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)


# Factory function
def create_environment_manager(environment: Union[Environment, str] = None,
                             config_dir: str = "config",
                             enable_hot_reload: bool = True) -> EnvironmentManager:
    """
    Factory function for Environment Manager
    
    Args:
        environment: Target environment
        config_dir: Configuration directory
        enable_hot_reload: Enable hot-reload functionality
        
    Returns:
        EnvironmentManager instance
    """
    return EnvironmentManager(environment, config_dir, enable_hot_reload)


if __name__ == "__main__":
    # Test Environment Manager
    print("🧪 Testing EnvironmentManager...")
    
    # Create test config directory
    test_config_dir = Path("test_config")
    test_config_dir.mkdir(exist_ok=True)
    
    # Create test config files
    base_config = {
        "hardware": {
            "cpu_cores": 32,
            "gpu_memory_gb": 32,
            "ram_gb": 192
        },
        "ollama": {
            "model": "openbmb/minicpm4.1",
            "host": "localhost",
            "port": 11434
        }
    }
    
    dev_config = {
        "data": {
            "use_real_data": False,
            "symbol": "EURUSD"
        },
        "logging": {
            "level": "DEBUG"
        }
    }
    
    # Write test config files
    with open(test_config_dir / "base.json", 'w') as f:
        json.dump(base_config, f, indent=2)
    
    with open(test_config_dir / "development.json", 'w') as f:
        json.dump(dev_config, f, indent=2)
    
    # Test environment manager
    env_manager = create_environment_manager(
        environment=Environment.DEVELOPMENT,
        config_dir=str(test_config_dir),
        enable_hot_reload=False  # Disable for testing
    )
    
    print(f"✅ Environment: {env_manager.get_environment().value}")
    print(f"📊 CPU Cores: {env_manager.get('hardware.cpu_cores')}")
    print(f"🧠 Ollama Model: {env_manager.get('ollama.model')}")
    print(f"📈 Use Real Data: {env_manager.get('data.use_real_data')}")
    print(f"📝 Log Level: {env_manager.get('logging.level')}")
    
    # Test status
    status = env_manager.get_status()
    print(f"📊 Status: {status}")
    
    # Cleanup
    env_manager.stop()
    
    # Remove test files
    import shutil
    shutil.rmtree(test_config_dir)
    
    print("✅ EnvironmentManager test completed!")