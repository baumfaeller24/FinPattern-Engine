#!/usr/bin/env python3
"""
Model Fallback System für regelbasierte Backup-Strategien
Phase 3 Implementation - Task 13

Features:
- Multi-Model-Management mit Fallback-Hierarchien
- Rule-based Backup-Strategien für AI-Model-Failures
- Model-Performance-Monitoring und Health-Checking
- Graceful Degradation zu einfacheren Modellen
- Ensemble-Methods und Model-Voting-Strategien
- Real-time Model-Switching und Load-Balancing
- Traditional-Algorithm-Fallbacks für AI-Model-Ausfälle
"""

import time
import threading
import logging
import pickle
from typing import Dict, List, Optional, Any, Union, Callable, Tuple, Type
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import json
from collections import deque, defaultdict
from abc import ABC, abstractmethod
import numpy as np

# ML Libraries
try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    import sklearn
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


class ModelType(Enum):
    """Typen von Modellen"""
    DEEP_LEARNING = "deep_learning"
    MACHINE_LEARNING = "machine_learning"
    STATISTICAL = "statistical"
    RULE_BASED = "rule_based"
    ENSEMBLE = "ensemble"
    TRADITIONAL = "traditional"


class ModelComplexity(Enum):
    """Model-Komplexitätsstufen"""
    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"


class ModelStatus(Enum):
    """Model-Status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"
    LOADING = "loading"
    TRAINING = "training"
    UNKNOWN = "unknown"


class FallbackStrategy(Enum):
    """Fallback-Strategien"""
    COMPLEXITY_DEGRADATION = "complexity_degradation"
    TYPE_FALLBACK = "type_fallback"
    ENSEMBLE_VOTING = "ensemble_voting"
    RULE_BASED_FALLBACK = "rule_based_fallback"
    STATISTICAL_FALLBACK = "statistical_fallback"
    CUSTOM = "custom"


@dataclass
class ModelConfig:
    """Konfiguration für Model"""
    model_id: str
    model_type: ModelType
    complexity: ModelComplexity
    priority: int = 1  # 1 = höchste Priorität
    model_path: Optional[str] = None
    config_path: Optional[str] = None
    requirements: Dict[str, Any] = field(default_factory=dict)
    performance_thresholds: Dict[str, float] = field(default_factory=dict)
    timeout: float = 30.0
    memory_limit_mb: Optional[int] = None
    gpu_required: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "model_type": self.model_type.value,
            "complexity": self.complexity.value,
            "priority": self.priority,
            "model_path": self.model_path,
            "config_path": self.config_path,
            "requirements": self.requirements,
            "performance_thresholds": self.performance_thresholds,
            "timeout": self.timeout,
            "memory_limit_mb": self.memory_limit_mb,
            "gpu_required": self.gpu_required,
            "metadata": self.metadata
        }


@dataclass
class ModelPerformance:
    """Model-Performance-Metriken"""
    model_id: str
    timestamp: datetime
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    inference_time_ms: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    confidence_score: Optional[float] = None
    error_rate: float = 0.0
    custom_metrics: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "timestamp": self.timestamp.isoformat(),
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "inference_time_ms": self.inference_time_ms,
            "memory_usage_mb": self.memory_usage_mb,
            "confidence_score": self.confidence_score,
            "error_rate": self.error_rate,
            "custom_metrics": self.custom_metrics
        }


@dataclass
class ModelHealth:
    """Model-Health-Status"""
    model_id: str
    status: ModelStatus
    last_check: datetime
    consecutive_failures: int = 0
    success_rate: float = 1.0
    avg_inference_time: float = 0.0
    avg_accuracy: float = 0.0
    last_error: Optional[str] = None
    is_loaded: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "status": self.status.value,
            "last_check": self.last_check.isoformat(),
            "consecutive_failures": self.consecutive_failures,
            "success_rate": self.success_rate,
            "avg_inference_time": self.avg_inference_time,
            "avg_accuracy": self.avg_accuracy,
            "last_error": self.last_error,
            "is_loaded": self.is_loaded
        }


class BaseModel(ABC):
    """Abstract Base Class für Models"""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{config.model_id}")
        self.is_loaded = False
        self.model = None
    
    @abstractmethod
    async def load_model(self) -> bool:
        """Lade Model"""
        pass
    
    @abstractmethod
    async def predict(self, input_data: Any) -> Dict[str, Any]:
        """Führe Prediction durch"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Health-Check des Models"""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Erhalte Model-Informationen"""
        pass
    
    async def unload_model(self):
        """Entlade Model"""
        self.model = None
        self.is_loaded = False


class DeepLearningModel(BaseModel):
    """Deep Learning Model (PyTorch)"""
    
    async def load_model(self) -> bool:
        """Lade PyTorch-Model"""
        
        if not TORCH_AVAILABLE:
            self.logger.error("PyTorch not available")
            return False
        
        try:
            if self.config.model_path:
                model_path = Path(self.config.model_path)
                if model_path.exists():
                    # Lade Model-State
                    device = torch.device('cuda' if torch.cuda.is_available() and self.config.gpu_required else 'cpu')
                    self.model = torch.load(model_path, map_location=device)
                    self.model.eval()
                    
                    self.is_loaded = True
                    self.logger.info(f"Loaded PyTorch model from {model_path}")
                    return True
                else:
                    self.logger.error(f"Model file not found: {model_path}")
                    return False
            else:
                # Dummy-Model für Testing
                self.model = nn.Sequential(
                    nn.Linear(10, 50),
                    nn.ReLU(),
                    nn.Linear(50, 1),
                    nn.Sigmoid()
                )
                self.is_loaded = True
                return True
                
        except Exception as e:
            self.logger.error(f"Error loading PyTorch model: {e}")
            return False
    
    async def predict(self, input_data: Any) -> Dict[str, Any]:
        """PyTorch-Prediction"""
        
        if not self.is_loaded or self.model is None:
            return {"success": False, "error": "Model not loaded"}
        
        try:
            start_time = time.time()
            
            # Input-Preprocessing
            if isinstance(input_data, (list, np.ndarray)):
                tensor_input = torch.FloatTensor(input_data)
            elif isinstance(input_data, dict):
                # Extrahiere Features aus Dict
                features = input_data.get("features", [])
                tensor_input = torch.FloatTensor(features)
            else:
                return {"success": False, "error": "Invalid input format"}
            
            # Prediction
            with torch.no_grad():
                output = self.model(tensor_input)
                
                if output.dim() > 1:
                    prediction = output.squeeze().tolist()
                else:
                    prediction = output.item()
            
            inference_time = (time.time() - start_time) * 1000  # ms
            
            # Confidence-Score (für Classification)
            confidence = float(torch.max(torch.softmax(output, dim=-1)).item()) if output.dim() > 0 else 0.5
            
            return {
                "success": True,
                "prediction": prediction,
                "confidence": confidence,
                "inference_time_ms": inference_time,
                "model_id": self.config.model_id,
                "model_type": self.config.model_type.value
            }
            
        except Exception as e:
            self.logger.error(f"PyTorch prediction error: {e}")
            return {"success": False, "error": str(e)}
    
    async def health_check(self) -> bool:
        """Health-Check für PyTorch-Model"""
        
        try:
            if not self.is_loaded:
                return False
            
            # Dummy-Prediction für Health-Check
            dummy_input = torch.randn(1, 10)  # Angepasst an Model-Input
            
            with torch.no_grad():
                output = self.model(dummy_input)
                return output is not None
                
        except Exception as e:
            self.logger.error(f"PyTorch health check error: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """PyTorch-Model-Info"""
        
        info = {
            "model_id": self.config.model_id,
            "model_type": "PyTorch",
            "is_loaded": self.is_loaded,
            "parameters": 0,
            "device": "cpu"
        }
        
        if self.is_loaded and self.model:
            try:
                info["parameters"] = sum(p.numel() for p in self.model.parameters())
                info["device"] = str(next(self.model.parameters()).device)
            except Exception:
                pass
        
        return info


class MachineLearningModel(BaseModel):
    """Machine Learning Model (Scikit-learn)"""
    
    async def load_model(self) -> bool:
        """Lade Scikit-learn-Model"""
        
        if not SKLEARN_AVAILABLE:
            self.logger.error("Scikit-learn not available")
            return False
        
        try:
            if self.config.model_path:
                model_path = Path(self.config.model_path)
                if model_path.exists():
                    with open(model_path, 'rb') as f:
                        self.model = pickle.load(f)
                    
                    self.is_loaded = True
                    self.logger.info(f"Loaded sklearn model from {model_path}")
                    return True
                else:
                    self.logger.error(f"Model file not found: {model_path}")
                    return False
            else:
                # Default-Model erstellen
                model_type = self.config.metadata.get("sklearn_type", "random_forest")
                
                if model_type == "random_forest":
                    self.model = RandomForestClassifier(n_estimators=100, random_state=42)
                elif model_type == "gradient_boosting":
                    self.model = GradientBoostingClassifier(random_state=42)
                elif model_type == "logistic_regression":
                    self.model = LogisticRegression(random_state=42)
                else:
                    self.model = RandomForestClassifier(n_estimators=100, random_state=42)
                
                # Dummy-Training für Testing
                if PANDAS_AVAILABLE:
                    X_dummy = np.random.randn(100, 10)
                    y_dummy = np.random.randint(0, 2, 100)
                    self.model.fit(X_dummy, y_dummy)
                
                self.is_loaded = True
                return True
                
        except Exception as e:
            self.logger.error(f"Error loading sklearn model: {e}")
            return False
    
    async def predict(self, input_data: Any) -> Dict[str, Any]:
        """Scikit-learn-Prediction"""
        
        if not self.is_loaded or self.model is None:
            return {"success": False, "error": "Model not loaded"}
        
        try:
            start_time = time.time()
            
            # Input-Preprocessing
            if isinstance(input_data, (list, np.ndarray)):
                X = np.array(input_data).reshape(1, -1)
            elif isinstance(input_data, dict):
                features = input_data.get("features", [])
                X = np.array(features).reshape(1, -1)
            else:
                return {"success": False, "error": "Invalid input format"}
            
            # Prediction
            prediction = self.model.predict(X)[0]
            
            # Probability/Confidence
            confidence = 0.5
            if hasattr(self.model, 'predict_proba'):
                proba = self.model.predict_proba(X)[0]
                confidence = float(np.max(proba))
            
            inference_time = (time.time() - start_time) * 1000  # ms
            
            return {
                "success": True,
                "prediction": float(prediction) if isinstance(prediction, np.number) else prediction,
                "confidence": confidence,
                "inference_time_ms": inference_time,
                "model_id": self.config.model_id,
                "model_type": self.config.model_type.value
            }
            
        except Exception as e:
            self.logger.error(f"Sklearn prediction error: {e}")
            return {"success": False, "error": str(e)}
    
    async def health_check(self) -> bool:
        """Health-Check für Scikit-learn-Model"""
        
        try:
            if not self.is_loaded or self.model is None:
                return False
            
            # Dummy-Prediction
            X_dummy = np.random.randn(1, 10)
            prediction = self.model.predict(X_dummy)
            
            return prediction is not None
            
        except Exception as e:
            self.logger.error(f"Sklearn health check error: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Scikit-learn-Model-Info"""
        
        info = {
            "model_id": self.config.model_id,
            "model_type": "Scikit-learn",
            "is_loaded": self.is_loaded,
            "algorithm": "unknown"
        }
        
        if self.is_loaded and self.model:
            info["algorithm"] = type(self.model).__name__
            
            if hasattr(self.model, 'n_features_in_'):
                info["n_features"] = self.model.n_features_in_
        
        return info


class RuleBasedModel(BaseModel):
    """Rule-based Model"""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.rules = []
    
    async def load_model(self) -> bool:
        """Lade Rule-based-Model"""
        
        try:
            if self.config.config_path:
                config_path = Path(self.config.config_path)
                if config_path.exists():
                    with open(config_path, 'r') as f:
                        rules_config = json.load(f)
                    
                    self.rules = rules_config.get("rules", [])
                    self.is_loaded = True
                    self.logger.info(f"Loaded {len(self.rules)} rules from {config_path}")
                    return True
            
            # Default-Rules
            self.rules = [
                {"condition": "rsi < 30", "action": "buy", "confidence": 0.7},
                {"condition": "rsi > 70", "action": "sell", "confidence": 0.7},
                {"condition": "macd_signal == 'bullish'", "action": "buy", "confidence": 0.6},
                {"condition": "macd_signal == 'bearish'", "action": "sell", "confidence": 0.6}
            ]
            
            self.is_loaded = True
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading rule-based model: {e}")
            return False
    
    async def predict(self, input_data: Any) -> Dict[str, Any]:
        """Rule-based-Prediction"""
        
        if not self.is_loaded:
            return {"success": False, "error": "Model not loaded"}
        
        try:
            start_time = time.time()
            
            # Input-Data-Processing
            if isinstance(input_data, dict):
                indicators = input_data
            else:
                # Default-Indicators für Testing
                indicators = {
                    "rsi": 45.0,
                    "macd_signal": "neutral",
                    "price": 100.0
                }
            
            # Rule-Evaluation
            matched_rules = []
            
            for rule in self.rules:
                condition = rule.get("condition", "")
                
                try:
                    # Einfache Rule-Evaluation
                    if self._evaluate_condition(condition, indicators):
                        matched_rules.append(rule)
                except Exception as e:
                    self.logger.debug(f"Rule evaluation error: {e}")
            
            # Prediction basierend auf Rules
            if matched_rules:
                # Wähle Rule mit höchster Confidence
                best_rule = max(matched_rules, key=lambda r: r.get("confidence", 0))
                prediction = best_rule.get("action", "hold")
                confidence = best_rule.get("confidence", 0.5)
            else:
                prediction = "hold"
                confidence = 0.3
            
            inference_time = (time.time() - start_time) * 1000  # ms
            
            return {
                "success": True,
                "prediction": prediction,
                "confidence": confidence,
                "inference_time_ms": inference_time,
                "matched_rules": len(matched_rules),
                "model_id": self.config.model_id,
                "model_type": self.config.model_type.value
            }
            
        except Exception as e:
            self.logger.error(f"Rule-based prediction error: {e}")
            return {"success": False, "error": str(e)}
    
    def _evaluate_condition(self, condition: str, indicators: Dict[str, Any]) -> bool:
        """Evaluiere Rule-Condition"""
        
        try:
            # Einfache Condition-Evaluation
            # In einer echten Implementierung würde hier ein sicherer Expression-Parser verwendet
            
            # RSI-Rules
            if "rsi" in condition:
                rsi_value = indicators.get("rsi", 50)
                
                if "< 30" in condition:
                    return rsi_value < 30
                elif "> 70" in condition:
                    return rsi_value > 70
            
            # MACD-Rules
            if "macd_signal" in condition:
                macd_signal = indicators.get("macd_signal", "neutral")
                
                if "'bullish'" in condition:
                    return macd_signal == "bullish"
                elif "'bearish'" in condition:
                    return macd_signal == "bearish"
            
            return False
            
        except Exception:
            return False
    
    async def health_check(self) -> bool:
        """Health-Check für Rule-based-Model"""
        return self.is_loaded and len(self.rules) > 0
    
    def get_model_info(self) -> Dict[str, Any]:
        """Rule-based-Model-Info"""
        
        return {
            "model_id": self.config.model_id,
            "model_type": "Rule-based",
            "is_loaded": self.is_loaded,
            "rules_count": len(self.rules)
        }


class ModelFallbackSystem:
    """
    Model Fallback System für regelbasierte Backup-Strategien
    
    Features:
    - Multi-Model-Management mit Fallback-Hierarchien
    - Rule-based Backup-Strategien für AI-Model-Failures
    - Model-Performance-Monitoring und Health-Checking
    - Graceful Degradation zu einfacheren Modellen
    - Ensemble-Methods und Model-Voting-Strategien
    - Real-time Model-Switching und Load-Balancing
    - Traditional-Algorithm-Fallbacks für AI-Model-Ausfälle
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Fallback-Konfiguration
        self.fallback_strategy = FallbackStrategy(
            self.config.get("fallback_strategy", "complexity_degradation")
        )
        self.enable_ensemble_voting = self.config.get("enable_ensemble_voting", True)
        self.health_check_interval = self.config.get("health_check_interval", 300.0)  # 5 Minuten
        self.performance_window = self.config.get("performance_window", 100)  # Letzte 100 Predictions
        
        # Performance-Thresholds
        self.min_accuracy_threshold = self.config.get("min_accuracy_threshold", 0.6)
        self.max_inference_time_ms = self.config.get("max_inference_time_ms", 5000)
        self.max_consecutive_failures = self.config.get("max_consecutive_failures", 5)
        
        # Models
        self.models: Dict[str, BaseModel] = {}
        self.model_configs: Dict[str, ModelConfig] = {}
        self.model_health: Dict[str, ModelHealth] = {}
        
        # Performance-Tracking
        self.performance_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self.performance_window))
        
        # Fallback-Hierarchie
        self.fallback_hierarchy: List[str] = []
        
        # Threading
        self.health_monitoring_active = False
        self.health_monitoring_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Statistiken
        self.stats = {
            "total_predictions": 0,
            "successful_predictions": 0,
            "failed_predictions": 0,
            "fallback_events": 0,
            "ensemble_predictions": 0,
            "model_switches": 0,
            "health_checks": 0
        }
        
        self.logger.info("ModelFallbackSystem initialized")
    
    def register_model(self, config: ModelConfig):
        """Registriere neues Model"""
        
        try:
            # Model-Instance erstellen
            if config.model_type == ModelType.DEEP_LEARNING:
                model = DeepLearningModel(config)
            elif config.model_type == ModelType.MACHINE_LEARNING:
                model = MachineLearningModel(config)
            elif config.model_type == ModelType.RULE_BASED:
                model = RuleBasedModel(config)
            else:
                raise ValueError(f"Unsupported model type: {config.model_type}")
            
            self.models[config.model_id] = model
            self.model_configs[config.model_id] = config
            
            # Initial Health-Status
            self.model_health[config.model_id] = ModelHealth(
                model_id=config.model_id,
                status=ModelStatus.UNKNOWN,
                last_check=datetime.now()
            )
            
            # Fallback-Hierarchie aktualisieren
            self._update_fallback_hierarchy()
            
            self.logger.info(f"Registered model: {config.model_id} ({config.model_type.value})")
            
            # Health-Monitoring starten falls noch nicht aktiv
            if not self.health_monitoring_active:
                self.start_health_monitoring()
                
        except Exception as e:
            self.logger.error(f"Error registering model: {e}")
            raise
    
    async def predict(self, input_data: Any, preferred_models: Optional[List[str]] = None) -> Dict[str, Any]:
        """Prediction mit Fallback-Logic"""
        
        self.stats["total_predictions"] += 1
        
        try:
            # Model-Selection
            model_order = self._select_models(preferred_models)
            
            if not model_order:
                return {
                    "success": False,
                    "error": "No healthy models available",
                    "attempted_models": []
                }
            
            attempted_models = []
            last_error = None
            
            # Ensemble-Voting falls aktiviert
            if (self.enable_ensemble_voting and 
                len([m for m in model_order if self._is_model_healthy(m)]) >= 2):
                
                ensemble_result = await self._ensemble_predict(input_data, model_order[:3])
                if ensemble_result.get("success"):
                    self.stats["ensemble_predictions"] += 1
                    return ensemble_result
            
            # Sequential Fallback
            for model_id in model_order:
                try:
                    attempted_models.append(model_id)
                    
                    # Health-Check
                    if not self._is_model_healthy(model_id):
                        continue
                    
                    # Model laden falls nötig
                    model = self.models[model_id]
                    if not model.is_loaded:
                        load_success = await model.load_model()
                        if not load_success:
                            self._update_model_health(model_id, False, None, "Failed to load model")
                            continue
                    
                    # Prediction
                    start_time = time.time()
                    result = await model.predict(input_data)
                    inference_time = (time.time() - start_time) * 1000
                    
                    if result.get("success"):
                        # Performance-Tracking
                        performance = ModelPerformance(
                            model_id=model_id,
                            timestamp=datetime.now(),
                            inference_time_ms=inference_time,
                            confidence_score=result.get("confidence")
                        )
                        
                        self.performance_history[model_id].append(performance)
                        
                        # Health-Update
                        self._update_model_health(model_id, True, performance)
                        
                        # Result erweitern
                        result["model_used"] = model_id
                        result["attempted_models"] = attempted_models
                        result["fallback_level"] = attempted_models.index(model_id)
                        
                        self.stats["successful_predictions"] += 1
                        
                        return result
                    else:
                        # Model-Failure
                        error_msg = result.get("error", "Unknown error")
                        self._update_model_health(model_id, False, None, error_msg)
                        last_error = error_msg
                        
                        # Fallback-Event
                        self.stats["fallback_events"] += 1
                        
                        self.logger.warning(f"Model {model_id} failed: {error_msg}")
                        
                except Exception as e:
                    self._update_model_health(model_id, False, None, str(e))
                    last_error = str(e)
                    self.logger.error(f"Exception with model {model_id}: {e}")
            
            # Alle Models fehlgeschlagen
            self.stats["failed_predictions"] += 1
            
            return {
                "success": False,
                "error": f"All models failed. Last error: {last_error}",
                "attempted_models": attempted_models
            }
            
        except Exception as e:
            self.stats["failed_predictions"] += 1
            self.logger.error(f"Error in predict: {e}")
            return {
                "success": False,
                "error": str(e),
                "attempted_models": []
            }
    
    async def _ensemble_predict(self, input_data: Any, model_ids: List[str]) -> Dict[str, Any]:
        """Ensemble-Prediction mit Voting"""
        
        try:
            predictions = []
            confidences = []
            successful_models = []
            
            # Sammle Predictions von verfügbaren Models
            for model_id in model_ids:
                if not self._is_model_healthy(model_id):
                    continue
                
                try:
                    model = self.models[model_id]
                    
                    if not model.is_loaded:
                        await model.load_model()
                    
                    result = await model.predict(input_data)
                    
                    if result.get("success"):
                        predictions.append(result.get("prediction"))
                        confidences.append(result.get("confidence", 0.5))
                        successful_models.append(model_id)
                        
                except Exception as e:
                    self.logger.debug(f"Ensemble model {model_id} failed: {e}")
            
            if len(predictions) < 2:
                return {"success": False, "error": "Insufficient models for ensemble"}
            
            # Voting-Strategy
            if all(isinstance(p, (int, float)) for p in predictions):
                # Numerical predictions - weighted average
                weights = np.array(confidences)
                weights = weights / np.sum(weights)  # Normalize
                
                ensemble_prediction = np.average(predictions, weights=weights)
                ensemble_confidence = np.mean(confidences)
            else:
                # Categorical predictions - majority vote
                from collections import Counter
                vote_counts = Counter(predictions)
                ensemble_prediction = vote_counts.most_common(1)[0][0]
                
                # Confidence basierend auf Vote-Ratio
                total_votes = len(predictions)
                max_votes = vote_counts.most_common(1)[0][1]
                ensemble_confidence = max_votes / total_votes
            
            return {
                "success": True,
                "prediction": ensemble_prediction,
                "confidence": ensemble_confidence,
                "ensemble_size": len(predictions),
                "models_used": successful_models,
                "individual_predictions": predictions,
                "individual_confidences": confidences,
                "model_type": "ensemble"
            }
            
        except Exception as e:
            self.logger.error(f"Ensemble prediction error: {e}")
            return {"success": False, "error": str(e)}
    
    def _select_models(self, preferred_models: Optional[List[str]] = None) -> List[str]:
        """Wähle Models basierend auf Fallback-Strategy"""
        
        available_models = []
        
        # Filtere verfügbare Models
        for model_id, health in self.model_health.items():
            if health.status not in [ModelStatus.OFFLINE, ModelStatus.UNKNOWN]:
                available_models.append(model_id)
        
        if not available_models:
            return []
        
        # Preferred Models zuerst
        if preferred_models:
            ordered_models = []
            for model_id in preferred_models:
                if model_id in available_models:
                    ordered_models.append(model_id)
            
            # Füge restliche Models hinzu
            for model_id in available_models:
                if model_id not in ordered_models:
                    ordered_models.append(model_id)
            
            available_models = ordered_models
        
        # Strategy-basierte Sortierung
        if self.fallback_strategy == FallbackStrategy.COMPLEXITY_DEGRADATION:
            # Sortiere nach Komplexität (höchste zuerst)
            complexity_order = {
                ModelComplexity.VERY_HIGH: 5,
                ModelComplexity.HIGH: 4,
                ModelComplexity.MEDIUM: 3,
                ModelComplexity.LOW: 2,
                ModelComplexity.VERY_LOW: 1
            }
            
            available_models.sort(
                key=lambda x: complexity_order.get(self.model_configs[x].complexity, 0),
                reverse=True
            )
        
        elif self.fallback_strategy == FallbackStrategy.TYPE_FALLBACK:
            # Sortiere nach Model-Type (AI zuerst, dann Traditional)
            type_order = {
                ModelType.DEEP_LEARNING: 4,
                ModelType.MACHINE_LEARNING: 3,
                ModelType.STATISTICAL: 2,
                ModelType.RULE_BASED: 1,
                ModelType.TRADITIONAL: 0
            }
            
            available_models.sort(
                key=lambda x: type_order.get(self.model_configs[x].model_type, 0),
                reverse=True
            )
        
        else:
            # Fallback-Hierarchie verwenden
            hierarchical_order = []
            for model_id in self.fallback_hierarchy:
                if model_id in available_models:
                    hierarchical_order.append(model_id)
            
            # Füge nicht-hierarchische Models hinzu
            for model_id in available_models:
                if model_id not in hierarchical_order:
                    hierarchical_order.append(model_id)
            
            available_models = hierarchical_order
        
        return available_models
    
    def _is_model_healthy(self, model_id: str) -> bool:
        """Prüfe ob Model gesund ist"""
        
        health = self.model_health.get(model_id)
        if not health:
            return False
        
        return health.status in [ModelStatus.HEALTHY, ModelStatus.DEGRADED]
    
    def _update_model_health(self, model_id: str, success: bool, 
                           performance: Optional[ModelPerformance] = None,
                           error: Optional[str] = None):
        """Update Model-Health-Status"""
        
        try:
            health = self.model_health.get(model_id)
            if not health:
                return
            
            health.last_check = datetime.now()
            
            if success:
                health.consecutive_failures = 0
                health.last_error = None
                
                # Success-Rate aktualisieren
                health.success_rate = 0.9 * health.success_rate + 0.1 * 1.0
                
                # Performance-Metriken aktualisieren
                if performance:
                    if performance.inference_time_ms:
                        health.avg_inference_time = (0.9 * health.avg_inference_time + 
                                                   0.1 * performance.inference_time_ms)
                    
                    if performance.confidence_score:
                        health.avg_accuracy = (0.9 * health.avg_accuracy + 
                                             0.1 * performance.confidence_score)
                
                # Status bestimmen
                if health.success_rate > 0.95 and health.avg_inference_time < self.max_inference_time_ms:
                    health.status = ModelStatus.HEALTHY
                elif health.success_rate > 0.8:
                    health.status = ModelStatus.DEGRADED
                else:
                    health.status = ModelStatus.UNHEALTHY
                
                # Model als geladen markieren
                health.is_loaded = True
                
            else:
                health.consecutive_failures += 1
                health.last_error = error
                
                # Success-Rate aktualisieren
                health.success_rate = 0.9 * health.success_rate + 0.1 * 0.0
                
                # Status bestimmen
                if health.consecutive_failures >= self.max_consecutive_failures:
                    health.status = ModelStatus.OFFLINE
                elif health.success_rate < 0.5:
                    health.status = ModelStatus.UNHEALTHY
                else:
                    health.status = ModelStatus.DEGRADED
            
        except Exception as e:
            self.logger.error(f"Error updating model health: {e}")
    
    def _update_fallback_hierarchy(self):
        """Aktualisiere Fallback-Hierarchie"""
        
        try:
            # Sortiere Models nach Priorität und Komplexität
            model_items = []
            
            for model_id, config in self.model_configs.items():
                complexity_score = {
                    ModelComplexity.VERY_HIGH: 5,
                    ModelComplexity.HIGH: 4,
                    ModelComplexity.MEDIUM: 3,
                    ModelComplexity.LOW: 2,
                    ModelComplexity.VERY_LOW: 1
                }.get(config.complexity, 3)
                
                model_items.append((model_id, config.priority, complexity_score))
            
            # Sortiere: Priorität (niedrigere Zahl = höher), dann Komplexität (höher = besser)
            model_items.sort(key=lambda x: (x[1], -x[2]))
            
            self.fallback_hierarchy = [item[0] for item in model_items]
            
            self.logger.info(f"Updated fallback hierarchy: {self.fallback_hierarchy}")
            
        except Exception as e:
            self.logger.error(f"Error updating fallback hierarchy: {e}")
    
    def start_health_monitoring(self):
        """Starte Model-Health-Monitoring"""
        
        if self.health_monitoring_active:
            return
        
        self.health_monitoring_active = True
        self.stop_event.clear()
        
        self.health_monitoring_thread = threading.Thread(
            target=self._health_monitoring_loop,
            name="ModelHealthMonitor",
            daemon=True
        )
        self.health_monitoring_thread.start()
        
        self.logger.info("Model health monitoring started")
    
    def stop_health_monitoring(self):
        """Stoppe Model-Health-Monitoring"""
        
        if not self.health_monitoring_active:
            return
        
        self.health_monitoring_active = False
        self.stop_event.set()
        
        if self.health_monitoring_thread:
            self.health_monitoring_thread.join(timeout=5.0)
        
        self.logger.info("Model health monitoring stopped")
    
    def _health_monitoring_loop(self):
        """Model-Health-Monitoring-Loop"""
        
        import asyncio
        
        async def run_health_checks():
            tasks = []
            for model_id, model in self.models.items():
                task = asyncio.create_task(self._perform_model_health_check(model_id, model))
                tasks.append(task)
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        
        while self.health_monitoring_active and not self.stop_event.is_set():
            try:
                # Async Health-Checks ausführen
                asyncio.run(run_health_checks())
                
                # Warte bis zum nächsten Health-Check
                self.stop_event.wait(self.health_check_interval)
                
            except Exception as e:
                self.logger.error(f"Health monitoring loop error: {e}")
                time.sleep(30.0)
    
    async def _perform_model_health_check(self, model_id: str, model: BaseModel):
        """Führe Health-Check für Model durch"""
        
        try:
            is_healthy = await model.health_check()
            
            if is_healthy:
                self._update_model_health(model_id, True)
            else:
                self._update_model_health(model_id, False, None, "Health check failed")
            
            self.stats["health_checks"] += 1
            
            self.logger.debug(f"Health check for {model_id}: {'healthy' if is_healthy else 'unhealthy'}")
            
        except Exception as e:
            self._update_model_health(model_id, False, None, str(e))
            self.logger.error(f"Health check error for {model_id}: {e}")
    
    def get_fallback_statistics(self) -> Dict[str, Any]:
        """Erhalte Fallback-Statistiken"""
        
        try:
            # Model-Health-Summary
            model_summary = {}
            for model_id, health in self.model_health.items():
                config = self.model_configs.get(model_id)
                model_info = self.models[model_id].get_model_info() if model_id in self.models else {}
                
                model_summary[model_id] = {
                    "status": health.status.value,
                    "success_rate": health.success_rate,
                    "avg_inference_time": health.avg_inference_time,
                    "consecutive_failures": health.consecutive_failures,
                    "is_loaded": health.is_loaded,
                    "model_type": config.model_type.value if config else "unknown",
                    "complexity": config.complexity.value if config else "unknown",
                    "priority": config.priority if config else 0,
                    **model_info
                }
            
            # Performance-Summary
            performance_summary = {}
            for model_id, performances in self.performance_history.items():
                if performances:
                    recent_performances = list(performances)[-10:]
                    avg_inference_time = np.mean([p.inference_time_ms for p in recent_performances if p.inference_time_ms])
                    avg_confidence = np.mean([p.confidence_score for p in recent_performances if p.confidence_score])
                    
                    performance_summary[model_id] = {
                        "avg_inference_time_ms": float(avg_inference_time) if not np.isnan(avg_inference_time) else 0,
                        "avg_confidence": float(avg_confidence) if not np.isnan(avg_confidence) else 0,
                        "total_predictions": len(performances)
                    }
            
            return {
                "timestamp": datetime.now().isoformat(),
                "fallback_config": {
                    "strategy": self.fallback_strategy.value,
                    "enable_ensemble_voting": self.enable_ensemble_voting,
                    "health_check_interval": self.health_check_interval,
                    "min_accuracy_threshold": self.min_accuracy_threshold,
                    "max_inference_time_ms": self.max_inference_time_ms
                },
                "statistics": dict(self.stats),
                "models": model_summary,
                "performance": performance_summary,
                "fallback_hierarchy": self.fallback_hierarchy,
                "registered_models": len(self.models)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting fallback statistics: {e}")
            return {"error": str(e)}
    
    async def cleanup(self):
        """Cleanup Fallback-System-Ressourcen"""
        
        try:
            # Stoppe Health-Monitoring
            self.stop_health_monitoring()
            
            # Unload alle Models
            for model in self.models.values():
                await model.unload_model()
            
            # Clear Data
            self.models.clear()
            self.model_configs.clear()
            self.model_health.clear()
            self.performance_history.clear()
            
            self.logger.info("ModelFallbackSystem cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")


# Utility-Funktionen
def create_deep_learning_config(model_id: str, model_path: str, 
                              complexity: ModelComplexity = ModelComplexity.HIGH,
                              priority: int = 1, **kwargs) -> ModelConfig:
    """Erstelle Deep-Learning-Model-Konfiguration"""
    
    return ModelConfig(
        model_id=model_id,
        model_type=ModelType.DEEP_LEARNING,
        complexity=complexity,
        priority=priority,
        model_path=model_path,
        gpu_required=kwargs.get("gpu_required", True),
        **kwargs
    )


def create_ml_config(model_id: str, model_path: Optional[str] = None,
                    sklearn_type: str = "random_forest",
                    complexity: ModelComplexity = ModelComplexity.MEDIUM,
                    priority: int = 2, **kwargs) -> ModelConfig:
    """Erstelle Machine-Learning-Model-Konfiguration"""
    
    metadata = {"sklearn_type": sklearn_type}
    metadata.update(kwargs.get("metadata", {}))
    
    return ModelConfig(
        model_id=model_id,
        model_type=ModelType.MACHINE_LEARNING,
        complexity=complexity,
        priority=priority,
        model_path=model_path,
        metadata=metadata,
        **kwargs
    )


def create_rule_based_config(model_id: str, rules_path: Optional[str] = None,
                           complexity: ModelComplexity = ModelComplexity.LOW,
                           priority: int = 3, **kwargs) -> ModelConfig:
    """Erstelle Rule-based-Model-Konfiguration"""
    
    return ModelConfig(
        model_id=model_id,
        model_type=ModelType.RULE_BASED,
        complexity=complexity,
        priority=priority,
        config_path=rules_path,
        **kwargs
    )


def setup_fallback_config(strategy: str = "complexity_degradation",
                         enable_ensemble: bool = True,
                         health_check_interval: float = 300.0) -> Dict[str, Any]:
    """Setup Fallback-System-Konfiguration"""
    
    return {
        "fallback_strategy": strategy,
        "enable_ensemble_voting": enable_ensemble,
        "health_check_interval": health_check_interval,
        "performance_window": 100,
        "min_accuracy_threshold": 0.6,
        "max_inference_time_ms": 5000,
        "max_consecutive_failures": 5
    }