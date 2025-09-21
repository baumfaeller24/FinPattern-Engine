#!/usr/bin/env python3
"""
Live Control Manager für AI-Indicator-Optimizer
Task 18 Implementation - Live Control und Environment Configuration

Features:
- Redis/Kafka-Integration für Live-Strategy-Control
- Strategy-Pausierung und Parameter-Update-Funktionalität
- Live-Risk-Management mit dynamischen Stop-Loss-Anpassungen
- Real-time Control Interface
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor

# Redis/Kafka imports (optional dependencies)
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

try:
    from kafka import KafkaProducer, KafkaConsumer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    KafkaProducer = None
    KafkaConsumer = None


class ControlAction(Enum):
    """Live Control Actions"""
    PAUSE_STRATEGY = "pause_strategy"
    RESUME_STRATEGY = "resume_strategy"
    UPDATE_PARAMETERS = "update_parameters"
    ADJUST_RISK = "adjust_risk"
    EMERGENCY_STOP = "emergency_stop"
    RELOAD_CONFIG = "reload_config"
    SWITCH_ENVIRONMENT = "switch_environment"


@dataclass
class ControlMessage:
    """Live Control Message"""
    action: ControlAction
    strategy_id: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    timestamp: float = None
    source: str = "unknown"
    priority: int = 1  # 1=low, 5=high
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class StrategyState:
    """Strategy State Information"""
    strategy_id: str
    is_active: bool = True
    is_paused: bool = False
    parameters: Dict[str, Any] = None
    risk_settings: Dict[str, Any] = None
    last_update: float = None
    performance_metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}
        if self.risk_settings is None:
            self.risk_settings = {}
        if self.last_update is None:
            self.last_update = time.time()
        if self.performance_metrics is None:
            self.performance_metrics = {}


@dataclass
class RiskSettings:
    """Dynamic Risk Management Settings"""
    max_position_size: float = 0.1
    stop_loss_pct: float = 0.02
    take_profit_pct: float = 0.04
    max_daily_loss: float = 0.05
    max_drawdown: float = 0.10
    confidence_threshold: float = 0.7
    emergency_stop_enabled: bool = True
    dynamic_sizing: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RiskSettings':
        return cls(**data)


class LiveControlManager:
    """
    Live Control Manager für Real-time Strategy Control
    
    Features:
    - Redis/Kafka Integration
    - Strategy Pause/Resume
    - Parameter Updates
    - Risk Management
    - Emergency Controls
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Live Control Manager
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Strategy states
        self.strategies: Dict[str, StrategyState] = {}
        self.global_risk_settings = RiskSettings()
        
        # Control state
        self.is_running = False
        self.emergency_stop_active = False
        self.message_handlers: Dict[ControlAction, List[Callable]] = {}
        
        # Communication backends
        self.redis_client = None
        self.kafka_producer = None
        self.kafka_consumer = None
        
        # Threading
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.control_thread = None
        
        # Initialize backends
        self._initialize_redis()
        self._initialize_kafka()
        
        # Register default handlers
        self._register_default_handlers()
        
        self.logger.info(f"LiveControlManager initialized: Redis={self.redis_client is not None}, Kafka={self.kafka_producer is not None}")
    
    def _initialize_redis(self) -> None:
        """Initialize Redis connection"""
        
        if not REDIS_AVAILABLE:
            self.logger.warning("Redis not available - install redis-py for Redis support")
            return
        
        try:
            redis_config = self.config.get("redis", {})
            
            if redis_config.get("enabled", False):
                self.redis_client = redis.Redis(
                    host=redis_config.get("host", "localhost"),
                    port=redis_config.get("port", 6379),
                    db=redis_config.get("db", 0),
                    decode_responses=True,
                    socket_timeout=redis_config.get("timeout", 5)
                )
                
                # Test connection
                self.redis_client.ping()
                self.logger.info("Redis connection established")
            
        except Exception as e:
            self.logger.warning(f"Redis initialization failed: {e}")
            self.redis_client = None
    
    def _initialize_kafka(self) -> None:
        """Initialize Kafka connection"""
        
        if not KAFKA_AVAILABLE:
            self.logger.warning("Kafka not available - install kafka-python for Kafka support")
            return
        
        try:
            kafka_config = self.config.get("kafka", {})
            
            if kafka_config.get("enabled", False):
                bootstrap_servers = kafka_config.get("bootstrap_servers", ["localhost:9092"])
                
                # Producer
                self.kafka_producer = KafkaProducer(
                    bootstrap_servers=bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    key_serializer=lambda k: k.encode('utf-8') if k else None
                )
                
                # Consumer
                self.kafka_consumer = KafkaConsumer(
                    kafka_config.get("control_topic", "ai_strategy_control"),
                    bootstrap_servers=bootstrap_servers,
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                    key_deserializer=lambda k: k.decode('utf-8') if k else None,
                    group_id=kafka_config.get("group_id", "ai_control_group"),
                    auto_offset_reset='latest'
                )
                
                self.logger.info("Kafka connection established")
            
        except Exception as e:
            self.logger.warning(f"Kafka initialization failed: {e}")
            self.kafka_producer = None
            self.kafka_consumer = None
    
    def _register_default_handlers(self) -> None:
        """Register default message handlers"""
        
        self.register_handler(ControlAction.PAUSE_STRATEGY, self._handle_pause_strategy)
        self.register_handler(ControlAction.RESUME_STRATEGY, self._handle_resume_strategy)
        self.register_handler(ControlAction.UPDATE_PARAMETERS, self._handle_update_parameters)
        self.register_handler(ControlAction.ADJUST_RISK, self._handle_adjust_risk)
        self.register_handler(ControlAction.EMERGENCY_STOP, self._handle_emergency_stop)
        self.register_handler(ControlAction.RELOAD_CONFIG, self._handle_reload_config)
    
    def register_handler(self, action: ControlAction, handler: Callable[[ControlMessage], None]) -> None:
        """
        Register message handler for specific action
        
        Args:
            action: Control action type
            handler: Handler function
        """
        if action not in self.message_handlers:
            self.message_handlers[action] = []
        
        self.message_handlers[action].append(handler)
        self.logger.debug(f"Registered handler for {action.value}")
    
    def start(self) -> None:
        """Start live control system"""
        
        if self.is_running:
            self.logger.warning("Live control already running")
            return
        
        self.is_running = True
        self.emergency_stop_active = False
        
        # Start control thread
        self.control_thread = threading.Thread(target=self._control_loop, daemon=True)
        self.control_thread.start()
        
        self.logger.info("Live control system started")
    
    def stop(self) -> None:
        """Stop live control system"""
        
        self.is_running = False
        
        if self.control_thread and self.control_thread.is_alive():
            self.control_thread.join(timeout=5)
        
        # Close connections
        if self.kafka_consumer:
            self.kafka_consumer.close()
        
        if self.kafka_producer:
            self.kafka_producer.close()
        
        if self.redis_client:
            self.redis_client.close()
        
        self.executor.shutdown(wait=True)
        
        self.logger.info("Live control system stopped")
    
    def _control_loop(self) -> None:
        """Main control loop"""
        
        self.logger.info("Control loop started")
        
        while self.is_running:
            try:
                # Check Redis messages
                if self.redis_client:
                    self._check_redis_messages()
                
                # Check Kafka messages
                if self.kafka_consumer:
                    self._check_kafka_messages()
                
                # Periodic health checks
                self._perform_health_checks()
                
                time.sleep(0.1)  # 100ms polling interval
                
            except Exception as e:
                self.logger.error(f"Control loop error: {e}")
                time.sleep(1)
        
        self.logger.info("Control loop stopped")
    
    def _check_redis_messages(self) -> None:
        """Check for Redis control messages"""
        
        try:
            # Check control channel
            control_channel = self.config.get("redis", {}).get("control_channel", "ai_control")
            
            # Non-blocking check for messages
            message = self.redis_client.lpop(control_channel)
            
            if message:
                try:
                    message_data = json.loads(message)
                    control_message = ControlMessage(**message_data)
                    self._process_control_message(control_message)
                    
                except Exception as e:
                    self.logger.error(f"Invalid Redis message: {e}")
            
        except Exception as e:
            self.logger.error(f"Redis message check failed: {e}")
    
    def _check_kafka_messages(self) -> None:
        """Check for Kafka control messages"""
        
        try:
            # Non-blocking poll
            message_pack = self.kafka_consumer.poll(timeout_ms=10)
            
            for topic_partition, messages in message_pack.items():
                for message in messages:
                    try:
                        message_data = message.value
                        control_message = ControlMessage(**message_data)
                        self._process_control_message(control_message)
                        
                    except Exception as e:
                        self.logger.error(f"Invalid Kafka message: {e}")
            
        except Exception as e:
            self.logger.error(f"Kafka message check failed: {e}")
    
    def _process_control_message(self, message: ControlMessage) -> None:
        """Process control message"""
        
        try:
            self.logger.info(f"Processing control message: {message.action.value}")
            
            # Check emergency stop (allow emergency stop messages to pass through)
            if self.emergency_stop_active and message.action != ControlAction.EMERGENCY_STOP:
                self.logger.warning("Emergency stop active - ignoring non-emergency message")
                return
            
            # Execute handlers directly (not via executor for testing)
            handlers = self.message_handlers.get(message.action, [])
            
            for handler in handlers:
                try:
                    handler(message)  # Execute directly for immediate effect
                except Exception as e:
                    self.logger.error(f"Handler execution failed: {e}")
            
        except Exception as e:
            self.logger.error(f"Message processing failed: {e}")
    
    def _perform_health_checks(self) -> None:
        """Perform periodic health checks"""
        
        try:
            current_time = time.time()
            
            # Check strategy states
            for strategy_id, state in self.strategies.items():
                # Check for stale strategies
                if current_time - state.last_update > 300:  # 5 minutes
                    self.logger.warning(f"Strategy {strategy_id} appears stale")
                
                # Check risk limits
                if state.performance_metrics:
                    self._check_risk_limits(strategy_id, state)
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
    
    def _check_risk_limits(self, strategy_id: str, state: StrategyState) -> None:
        """Check risk limits for strategy"""
        
        try:
            metrics = state.performance_metrics
            risk_settings = state.risk_settings or self.global_risk_settings.to_dict()
            
            # Check drawdown
            current_drawdown = metrics.get("drawdown", 0)
            max_drawdown = risk_settings.get("max_drawdown", 0.10)
            
            if current_drawdown > max_drawdown:
                self.logger.warning(f"Strategy {strategy_id} exceeds max drawdown: {current_drawdown:.2%}")
                self._trigger_emergency_action(strategy_id, "max_drawdown_exceeded")
            
            # Check daily loss
            daily_loss = metrics.get("daily_pnl", 0)
            max_daily_loss = risk_settings.get("max_daily_loss", 0.05)
            
            if daily_loss < -max_daily_loss:
                self.logger.warning(f"Strategy {strategy_id} exceeds daily loss limit: {daily_loss:.2%}")
                self._trigger_emergency_action(strategy_id, "daily_loss_exceeded")
            
        except Exception as e:
            self.logger.error(f"Risk limit check failed for {strategy_id}: {e}")
    
    def _trigger_emergency_action(self, strategy_id: str, reason: str) -> None:
        """Trigger emergency action for strategy"""
        
        self.logger.critical(f"Emergency action triggered for {strategy_id}: {reason}")
        
        # Pause strategy immediately
        if strategy_id in self.strategies:
            self.strategies[strategy_id].is_paused = True
            self.strategies[strategy_id].last_update = time.time()
        
        # Send emergency notification
        self._send_emergency_notification(strategy_id, reason)
    
    def _send_emergency_notification(self, strategy_id: str, reason: str) -> None:
        """Send emergency notification"""
        
        notification = {
            "type": "emergency",
            "strategy_id": strategy_id,
            "reason": reason,
            "timestamp": time.time(),
            "action_taken": "strategy_paused"
        }
        
        # Send via Redis
        if self.redis_client:
            try:
                self.redis_client.lpush("ai_emergency_notifications", json.dumps(notification))
            except Exception as e:
                self.logger.error(f"Redis emergency notification failed: {e}")
        
        # Send via Kafka
        if self.kafka_producer:
            try:
                self.kafka_producer.send("ai_emergency_notifications", notification)
            except Exception as e:
                self.logger.error(f"Kafka emergency notification failed: {e}")
    
    # Message Handlers
    
    def _handle_pause_strategy(self, message: ControlMessage) -> None:
        """Handle strategy pause request"""
        
        strategy_id = message.strategy_id
        
        if not strategy_id:
            self.logger.error("Pause strategy: No strategy ID provided")
            return
        
        if strategy_id in self.strategies:
            self.strategies[strategy_id].is_paused = True
            self.strategies[strategy_id].last_update = time.time()
            self.logger.info(f"Strategy {strategy_id} paused")
        else:
            self.logger.warning(f"Strategy {strategy_id} not found for pause")
    
    def _handle_resume_strategy(self, message: ControlMessage) -> None:
        """Handle strategy resume request"""
        
        strategy_id = message.strategy_id
        
        if not strategy_id:
            self.logger.error("Resume strategy: No strategy ID provided")
            return
        
        if strategy_id in self.strategies:
            self.strategies[strategy_id].is_paused = False
            self.strategies[strategy_id].last_update = time.time()
            self.logger.info(f"Strategy {strategy_id} resumed")
        else:
            self.logger.warning(f"Strategy {strategy_id} not found for resume")
    
    def _handle_update_parameters(self, message: ControlMessage) -> None:
        """Handle parameter update request"""
        
        strategy_id = message.strategy_id
        parameters = message.parameters or {}
        
        if not strategy_id:
            self.logger.error("Update parameters: No strategy ID provided")
            return
        
        if strategy_id in self.strategies:
            self.strategies[strategy_id].parameters.update(parameters)
            self.strategies[strategy_id].last_update = time.time()
            self.logger.info(f"Strategy {strategy_id} parameters updated: {parameters}")
        else:
            self.logger.warning(f"Strategy {strategy_id} not found for parameter update")
    
    def _handle_adjust_risk(self, message: ControlMessage) -> None:
        """Handle risk adjustment request"""
        
        strategy_id = message.strategy_id
        risk_params = message.parameters or {}
        
        if strategy_id:
            # Update specific strategy risk settings
            if strategy_id in self.strategies:
                if not self.strategies[strategy_id].risk_settings:
                    self.strategies[strategy_id].risk_settings = {}
                
                self.strategies[strategy_id].risk_settings.update(risk_params)
                self.strategies[strategy_id].last_update = time.time()
                self.logger.info(f"Strategy {strategy_id} risk settings updated: {risk_params}")
            else:
                self.logger.warning(f"Strategy {strategy_id} not found for risk adjustment")
        else:
            # Update global risk settings
            for key, value in risk_params.items():
                if hasattr(self.global_risk_settings, key):
                    setattr(self.global_risk_settings, key, value)
            
            self.logger.info(f"Global risk settings updated: {risk_params}")
    
    def _handle_emergency_stop(self, message: ControlMessage) -> None:
        """Handle emergency stop request"""
        
        # Check if this is to deactivate emergency stop
        if message.parameters and message.parameters.get("deactivate", False):
            self.emergency_stop_active = False
            self.logger.info("Emergency stop deactivated")
            return
        
        self.emergency_stop_active = True
        
        # Pause all strategies
        for strategy_id, state in self.strategies.items():
            state.is_paused = True
            state.last_update = time.time()
        
        self.logger.critical("EMERGENCY STOP ACTIVATED - All strategies paused")
        
        # Send emergency notification
        self._send_emergency_notification("ALL", "manual_emergency_stop")
    
    def _handle_reload_config(self, message: ControlMessage) -> None:
        """Handle configuration reload request"""
        
        try:
            # This would typically reload from config file
            # For now, just log the request
            self.logger.info("Configuration reload requested")
            
            # Update risk settings if provided
            if message.parameters:
                config_updates = message.parameters
                
                if "risk_settings" in config_updates:
                    risk_data = config_updates["risk_settings"]
                    self.global_risk_settings = RiskSettings.from_dict(risk_data)
                    self.logger.info("Global risk settings reloaded")
            
        except Exception as e:
            self.logger.error(f"Configuration reload failed: {e}")
    
    # Public API Methods
    
    def register_strategy(self, strategy_id: str, initial_state: Optional[Dict[str, Any]] = None) -> None:
        """
        Register new strategy for control
        
        Args:
            strategy_id: Unique strategy identifier
            initial_state: Initial strategy state
        """
        
        state_data = initial_state or {}
        
        self.strategies[strategy_id] = StrategyState(
            strategy_id=strategy_id,
            **state_data
        )
        
        self.logger.info(f"Strategy {strategy_id} registered for live control")
    
    def unregister_strategy(self, strategy_id: str) -> None:
        """
        Unregister strategy from control
        
        Args:
            strategy_id: Strategy identifier
        """
        
        if strategy_id in self.strategies:
            del self.strategies[strategy_id]
            self.logger.info(f"Strategy {strategy_id} unregistered from live control")
    
    def update_strategy_metrics(self, strategy_id: str, metrics: Dict[str, Any]) -> None:
        """
        Update strategy performance metrics
        
        Args:
            strategy_id: Strategy identifier
            metrics: Performance metrics
        """
        
        if strategy_id in self.strategies:
            self.strategies[strategy_id].performance_metrics.update(metrics)
            self.strategies[strategy_id].last_update = time.time()
    
    def is_strategy_active(self, strategy_id: str) -> bool:
        """
        Check if strategy is active (not paused or stopped)
        
        Args:
            strategy_id: Strategy identifier
            
        Returns:
            True if strategy is active
        """
        
        if self.emergency_stop_active:
            return False
        
        if strategy_id not in self.strategies:
            return False
        
        state = self.strategies[strategy_id]
        return state.is_active and not state.is_paused
    
    def get_strategy_state(self, strategy_id: str) -> Optional[StrategyState]:
        """
        Get current strategy state
        
        Args:
            strategy_id: Strategy identifier
            
        Returns:
            Strategy state or None
        """
        
        return self.strategies.get(strategy_id)
    
    def get_all_strategies(self) -> Dict[str, StrategyState]:
        """Get all strategy states"""
        
        return self.strategies.copy()
    
    def send_control_message(self, message: ControlMessage) -> bool:
        """
        Send control message via available backends
        
        Args:
            message: Control message to send
            
        Returns:
            True if message was sent successfully
        """
        
        success = False
        message_data = asdict(message)
        
        # Send via Redis
        if self.redis_client:
            try:
                control_channel = self.config.get("redis", {}).get("control_channel", "ai_control")
                self.redis_client.lpush(control_channel, json.dumps(message_data))
                success = True
            except Exception as e:
                self.logger.error(f"Redis message send failed: {e}")
        
        # Send via Kafka
        if self.kafka_producer:
            try:
                control_topic = self.config.get("kafka", {}).get("control_topic", "ai_strategy_control")
                self.kafka_producer.send(control_topic, message_data)
                success = True
            except Exception as e:
                self.logger.error(f"Kafka message send failed: {e}")
        
        return success
    
    def get_status(self) -> Dict[str, Any]:
        """Get live control system status"""
        
        return {
            "is_running": self.is_running,
            "emergency_stop_active": self.emergency_stop_active,
            "strategies_count": len(self.strategies),
            "active_strategies": sum(1 for s in self.strategies.values() if s.is_active and not s.is_paused),
            "paused_strategies": sum(1 for s in self.strategies.values() if s.is_paused),
            "redis_connected": self.redis_client is not None,
            "kafka_connected": self.kafka_producer is not None,
            "global_risk_settings": self.global_risk_settings.to_dict(),
            "timestamp": time.time()
        }


# Factory function
def create_live_control_manager(config: Dict[str, Any]) -> LiveControlManager:
    """
    Factory function for Live Control Manager
    
    Args:
        config: Configuration dictionary
        
    Returns:
        LiveControlManager instance
    """
    return LiveControlManager(config)


if __name__ == "__main__":
    # Test Live Control Manager
    print("🧪 Testing LiveControlManager...")
    
    # Test configuration
    test_config = {
        "redis": {
            "enabled": False,  # Set to True if Redis is available
            "host": "localhost",
            "port": 6379,
            "db": 0,
            "control_channel": "ai_control"
        },
        "kafka": {
            "enabled": False,  # Set to True if Kafka is available
            "bootstrap_servers": ["localhost:9092"],
            "control_topic": "ai_strategy_control",
            "group_id": "ai_control_group"
        }
    }
    
    # Create manager
    manager = create_live_control_manager(test_config)
    
    # Register test strategy
    manager.register_strategy("test_strategy_1", {
        "parameters": {"confidence_threshold": 0.7},
        "risk_settings": {"max_position_size": 0.05}
    })
    
    # Start manager
    manager.start()
    
    print(f"✅ Manager started: {manager.get_status()}")
    
    # Test control messages
    test_messages = [
        ControlMessage(ControlAction.PAUSE_STRATEGY, strategy_id="test_strategy_1"),
        ControlMessage(ControlAction.UPDATE_PARAMETERS, strategy_id="test_strategy_1", 
                      parameters={"confidence_threshold": 0.8}),
        ControlMessage(ControlAction.ADJUST_RISK, strategy_id="test_strategy_1",
                      parameters={"max_position_size": 0.03}),
        ControlMessage(ControlAction.RESUME_STRATEGY, strategy_id="test_strategy_1")
    ]
    
    # Process test messages
    for msg in test_messages:
        manager._process_control_message(msg)
        time.sleep(0.1)
    
    # Check final state
    final_state = manager.get_strategy_state("test_strategy_1")
    print(f"📊 Final strategy state: {final_state}")
    
    # Stop manager
    time.sleep(1)
    manager.stop()
    
    print("✅ LiveControlManager test completed!")