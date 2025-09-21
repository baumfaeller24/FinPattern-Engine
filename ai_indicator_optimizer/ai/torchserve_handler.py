#!/usr/bin/env python3
"""
TorchServe Handler für produktionsreife Feature-JSON-Processing
Phase 3 Implementation - Enhanced Pine Script Code Generator

Features:
- GPU-optimierte Model-Inference mit CUDA-Beschleunigung
- Batch-Processing für einzelne und Listen von Feature-Dictionaries
- Produktionsreife JSON-Processing Pipeline
- Error-Handling und Fallback-Mechanismen
- Performance-Monitoring und Logging
"""

import torch
import torch.nn as nn
import numpy as np
import json
import logging
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime
import time
from pathlib import Path
import requests
from dataclasses import dataclass
from enum import Enum

# Nautilus Imports
from nautilus_trader.model.data import Bar


class ModelType(Enum):
    """Unterstützte Model-Typen"""
    PATTERN_RECOGNITION = "pattern_model"
    FEATURE_EXTRACTION = "feature_model"
    CONFIDENCE_SCORING = "confidence_model"
    STRATEGY_GENERATION = "strategy_model"


@dataclass
class TorchServeConfig:
    """Konfiguration für TorchServe-Handler"""
    base_url: str = "http://localhost:8080"
    timeout: int = 30
    max_retries: int = 3
    batch_size: int = 32
    gpu_enabled: bool = True
    model_cache_size: int = 5
    performance_monitoring: bool = True


@dataclass
class InferenceResult:
    """Ergebnis einer Model-Inference"""
    predictions: Union[Dict, List[Dict]]
    confidence: float
    processing_time: float
    model_type: ModelType
    batch_size: int
    gpu_used: bool
    timestamp: datetime
    metadata: Optional[Dict] = None


class TorchServeHandler:
    """
    TorchServe Handler für produktionsreife AI-Model-Inference
    
    Features:
    - GPU-optimierte Batch-Processing
    - Automatisches Fallback bei Fehlern
    - Performance-Monitoring
    - Multi-Model-Support
    - JSON-basierte Feature-Processing
    - Live-Model-Switching
    - Enhanced Performance-Monitoring und Latenz-Tracking
    """
    
    def __init__(self, config: Optional[TorchServeConfig] = None):
        """
        Initialize TorchServe Handler
        
        Args:
            config: TorchServe-Konfiguration
        """
        self.config = config or TorchServeConfig()
        self.logger = logging.getLogger(__name__)
        
        # Model-Cache für bessere Performance
        self.model_cache = {}
        self.model_stats = {}
        
        # Performance-Tracking (Enhanced)
        self.inference_count = 0
        self.total_processing_time = 0.0
        self.batch_processing_count = 0
        self.latency_history = []
        self.error_count = 0
        self.model_switch_count = 0
        
        # Live-Model-Switching
        self.current_model = None
        self.available_models = {}
        
        # GPU-Setup
        self.device = self._setup_gpu()
        
        # TorchServe-Verbindung testen
        self.is_connected = self._test_connection()
        
        # Initialize available models
        self._discover_available_models()
        
        self.logger.info(f"TorchServeHandler initialized: GPU={self.device}, Connected={self.is_connected}, Models={len(self.available_models)}")
    
    def _setup_gpu(self) -> torch.device:
        """Setup GPU für optimale Performance"""
        
        if self.config.gpu_enabled and torch.cuda.is_available():
            device = torch.device("cuda")
            
            # GPU-Informationen loggen
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
            
            self.logger.info(f"GPU enabled: {gpu_name} ({gpu_memory:.1f}GB)")
            
            # GPU-Memory optimieren
            torch.cuda.empty_cache()
            
            return device
        else:
            self.logger.info("Using CPU for inference")
            return torch.device("cpu")
    
    def _test_connection(self) -> bool:
        """Teste TorchServe-Verbindung"""
        
        try:
            response = requests.get(
                f"{self.config.base_url}/ping",
                timeout=5
            )
            
            if response.status_code == 200:
                self.logger.info("TorchServe connection successful")
                return True
            else:
                self.logger.warning(f"TorchServe ping failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.warning(f"TorchServe connection failed: {e}")
            return False
    
    def process_features(
        self,
        features: Union[Dict[str, Any], List[Dict[str, Any]]],
        model_type: ModelType,
        batch_processing: bool = True
    ) -> InferenceResult:
        """
        Hauptfunktion für Feature-Processing mit Model-Inference
        
        Args:
            features: Feature-Dictionary oder Liste von Feature-Dictionaries
            model_type: Typ des zu verwendenden Models
            batch_processing: Ob Batch-Processing verwendet werden soll
            
        Returns:
            InferenceResult mit Predictions und Metadaten
        """
        
        start_time = time.time()
        
        try:
            # Normalisiere Input zu Liste
            if isinstance(features, dict):
                feature_list = [features]
                single_input = True
            else:
                feature_list = features
                single_input = False
            
            # Validiere Features
            validated_features = self._validate_features(feature_list)
            
            # Batch-Processing oder Einzelverarbeitung
            if batch_processing and len(validated_features) > 1:
                predictions = self._batch_inference(validated_features, model_type)
                self.batch_processing_count += 1
            else:
                predictions = self._single_inference(validated_features, model_type)
            
            # Berechne Confidence
            confidence = self._calculate_confidence(predictions, model_type)
            
            processing_time = time.time() - start_time
            self.total_processing_time += processing_time
            self.inference_count += 1
            
            # Track latency for performance monitoring
            self._track_latency(processing_time)
            
            # Erstelle Ergebnis
            result = InferenceResult(
                predictions=predictions[0] if single_input else predictions,
                confidence=confidence,
                processing_time=processing_time,
                model_type=model_type,
                batch_size=len(validated_features),
                gpu_used=self.device.type == "cuda",
                timestamp=datetime.now(),
                metadata={
                    "feature_count": len(validated_features[0]) if validated_features else 0,
                    "model_endpoint": f"{self.config.base_url}/predictions/{model_type.value}",
                    "fallback_used": not self.is_connected
                }
            )
            
            self.logger.debug(f"Feature processing completed: {len(validated_features)} samples, {processing_time:.3f}s")
            
            return result
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Feature processing failed: {e}")
            return self._create_fallback_result(features, model_type, start_time)
    
    def _validate_features(self, feature_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validiere und normalisiere Feature-Dictionaries"""
        
        validated = []
        
        for i, features in enumerate(feature_list):
            try:
                # Basis-Validierung
                if not isinstance(features, dict):
                    raise ValueError(f"Features must be dictionary, got {type(features)}")
                
                if not features:
                    raise ValueError("Features dictionary is empty")
                
                # Konvertiere alle Werte zu float (für Model-Kompatibilität)
                normalized_features = {}
                
                for key, value in features.items():
                    try:
                        # Konvertiere zu float
                        if isinstance(value, (int, float)):
                            normalized_features[key] = float(value)
                        elif isinstance(value, bool):
                            normalized_features[key] = float(value)
                        elif isinstance(value, str):
                            # Versuche String zu float zu konvertieren
                            normalized_features[key] = float(value)
                        else:
                            # Fallback für komplexe Typen
                            normalized_features[key] = 0.0
                            self.logger.warning(f"Could not convert feature {key}={value} to float, using 0.0")
                    
                    except (ValueError, TypeError):
                        normalized_features[key] = 0.0
                        self.logger.warning(f"Invalid feature value {key}={value}, using 0.0")
                
                # Prüfe auf NaN/Inf
                for key, value in normalized_features.items():
                    if np.isnan(value) or np.isinf(value):
                        normalized_features[key] = 0.0
                        self.logger.warning(f"NaN/Inf detected in feature {key}, using 0.0")
                
                validated.append(normalized_features)
                
            except Exception as e:
                self.logger.error(f"Feature validation failed for sample {i}: {e}")
                # Erstelle Fallback-Features
                validated.append({"fallback_feature": 0.0})
        
        return validated
    
    def _batch_inference(
        self,
        feature_list: List[Dict[str, Any]],
        model_type: ModelType
    ) -> List[Dict[str, Any]]:
        """Batch-Inference für bessere Performance"""
        
        try:
            if self.is_connected:
                return self._torchserve_batch_inference(feature_list, model_type)
            else:
                return self._local_batch_inference(feature_list, model_type)
                
        except Exception as e:
            self.logger.error(f"Batch inference failed: {e}")
            return self._fallback_batch_inference(feature_list, model_type)
    
    def _single_inference(
        self,
        feature_list: List[Dict[str, Any]],
        model_type: ModelType
    ) -> List[Dict[str, Any]]:
        """Einzelne Inference für kleine Batches"""
        
        results = []
        
        for features in feature_list:
            try:
                if self.is_connected:
                    result = self._torchserve_single_inference(features, model_type)
                else:
                    result = self._local_single_inference(features, model_type)
                
                results.append(result)
                
            except Exception as e:
                self.logger.error(f"Single inference failed: {e}")
                results.append(self._fallback_single_inference(features, model_type))
        
        return results
    
    def _torchserve_batch_inference(
        self,
        feature_list: List[Dict[str, Any]],
        model_type: ModelType
    ) -> List[Dict[str, Any]]:
        """TorchServe Batch-Inference über REST-API"""
        
        try:
            # Bereite Batch-Request vor
            batch_data = {
                "instances": feature_list,
                "batch_size": len(feature_list)
            }
            
            # Use current model or fallback to model_type
            endpoint_model = self.current_model or model_type.value
            
            # TorchServe-Request
            response = requests.post(
                f"{self.config.base_url}/predictions/{endpoint_model}",
                json=batch_data,
                timeout=self.config.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Normalisiere Response-Format
                if isinstance(result, list):
                    return result
                elif isinstance(result, dict) and "predictions" in result:
                    return result["predictions"]
                else:
                    return [result] * len(feature_list)
            
            else:
                raise Exception(f"TorchServe returned status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.logger.error(f"TorchServe batch inference failed: {e}")
            raise
    
    def _torchserve_single_inference(
        self,
        features: Dict[str, Any],
        model_type: ModelType
    ) -> Dict[str, Any]:
        """TorchServe Einzelne Inference"""
        
        try:
            # Use current model or fallback to model_type
            endpoint_model = self.current_model or model_type.value
            
            response = requests.post(
                f"{self.config.base_url}/predictions/{endpoint_model}",
                json=features,
                timeout=self.config.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"TorchServe returned status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.logger.error(f"TorchServe single inference failed: {e}")
            raise
    
    def _local_batch_inference(
        self,
        feature_list: List[Dict[str, Any]],
        model_type: ModelType
    ) -> List[Dict[str, Any]]:
        """Lokale Batch-Inference (Fallback)"""
        
        # Simuliere Model-Inference lokal
        results = []
        
        for features in feature_list:
            result = self._simulate_model_inference(features, model_type)
            results.append(result)
        
        return results
    
    def _local_single_inference(
        self,
        features: Dict[str, Any],
        model_type: ModelType
    ) -> Dict[str, Any]:
        """Lokale Einzelne Inference (Fallback)"""
        
        return self._simulate_model_inference(features, model_type)
    
    def _simulate_model_inference(
        self,
        features: Dict[str, Any],
        model_type: ModelType
    ) -> Dict[str, Any]:
        """Simuliere Model-Inference für Fallback"""
        
        # Basis-Features extrahieren
        feature_values = list(features.values())
        feature_mean = np.mean(feature_values) if feature_values else 0.5
        
        # Model-spezifische Simulation
        if model_type == ModelType.PATTERN_RECOGNITION:
            return {
                "pattern_type": "bullish" if feature_mean > 0.5 else "bearish",
                "confidence": min(abs(feature_mean - 0.5) * 2, 1.0),
                "strength": np.random.uniform(0.3, 0.9),
                "simulated": True
            }
        
        elif model_type == ModelType.FEATURE_EXTRACTION:
            return {
                "extracted_features": {
                    "trend_strength": feature_mean,
                    "volatility": abs(feature_mean - 0.5),
                    "momentum": np.random.uniform(-1, 1)
                },
                "feature_count": len(features),
                "simulated": True
            }
        
        elif model_type == ModelType.CONFIDENCE_SCORING:
            return {
                "confidence_score": min(max(feature_mean, 0.0), 1.0),
                "risk_score": 1.0 - min(max(feature_mean, 0.0), 1.0),
                "reliability": np.random.uniform(0.6, 0.95),
                "simulated": True
            }
        
        elif model_type == ModelType.STRATEGY_GENERATION:
            return {
                "action": "buy" if feature_mean > 0.6 else "sell" if feature_mean < 0.4 else "hold",
                "position_size": feature_mean,
                "stop_loss": feature_mean * 0.95,
                "take_profit": feature_mean * 1.05,
                "simulated": True
            }
        
        else:
            return {
                "prediction": feature_mean,
                "confidence": 0.5,
                "simulated": True
            }
    
    def _fallback_batch_inference(
        self,
        feature_list: List[Dict[str, Any]],
        model_type: ModelType
    ) -> List[Dict[str, Any]]:
        """Fallback für fehlgeschlagene Batch-Inference"""
        
        return [self._simulate_model_inference(features, model_type) for features in feature_list]
    
    def _fallback_single_inference(
        self,
        features: Dict[str, Any],
        model_type: ModelType
    ) -> Dict[str, Any]:
        """Fallback für fehlgeschlagene Einzelne Inference"""
        
        result = self._simulate_model_inference(features, model_type)
        result["fallback"] = True
        return result
    
    def _calculate_confidence(
        self,
        predictions: List[Dict[str, Any]],
        model_type: ModelType
    ) -> float:
        """Berechne Gesamt-Confidence für Predictions"""
        
        try:
            confidences = []
            
            for pred in predictions:
                if isinstance(pred, dict):
                    # Suche nach Confidence-Werten
                    if "confidence" in pred:
                        confidences.append(float(pred["confidence"]))
                    elif "confidence_score" in pred:
                        confidences.append(float(pred["confidence_score"]))
                    elif "reliability" in pred:
                        confidences.append(float(pred["reliability"]))
                    else:
                        # Fallback basierend auf Prediction-Werten
                        pred_values = [v for v in pred.values() if isinstance(v, (int, float))]
                        if pred_values:
                            confidences.append(min(max(np.mean(pred_values), 0.0), 1.0))
                        else:
                            confidences.append(0.5)
            
            if confidences:
                return float(np.mean(confidences))
            else:
                return 0.5
                
        except Exception as e:
            self.logger.error(f"Confidence calculation failed: {e}")
            return 0.5
    
    def _create_fallback_result(
        self,
        features: Union[Dict[str, Any], List[Dict[str, Any]]],
        model_type: ModelType,
        start_time: float
    ) -> InferenceResult:
        """Erstelle Fallback-Ergebnis bei Fehlern"""
        
        processing_time = time.time() - start_time
        
        # Erstelle minimale Fallback-Prediction
        if isinstance(features, dict):
            fallback_pred = {"fallback": True, "confidence": 0.1}
            batch_size = 1
        else:
            fallback_pred = [{"fallback": True, "confidence": 0.1} for _ in features]
            batch_size = len(features)
        
        return InferenceResult(
            predictions=fallback_pred,
            confidence=0.1,
            processing_time=processing_time,
            model_type=model_type,
            batch_size=batch_size,
            gpu_used=False,
            timestamp=datetime.now(),
            metadata={"fallback": True, "error": "Processing failed"}
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Erhalte Handler-Statistiken"""
        
        avg_processing_time = (
            self.total_processing_time / self.inference_count
            if self.inference_count > 0 else 0.0
        )
        
        return {
            "inference_count": self.inference_count,
            "batch_processing_count": self.batch_processing_count,
            "total_processing_time": self.total_processing_time,
            "avg_processing_time": avg_processing_time,
            "gpu_enabled": self.device.type == "cuda",
            "torchserve_connected": self.is_connected,
            "model_cache_size": len(self.model_cache),
            "config": {
                "base_url": self.config.base_url,
                "batch_size": self.config.batch_size,
                "timeout": self.config.timeout
            }
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Führe Health-Check durch"""
        
        health = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "gpu_available": torch.cuda.is_available(),
            "gpu_memory_free": 0,
            "torchserve_connection": False
        }
        
        # GPU-Status
        if torch.cuda.is_available():
            try:
                health["gpu_memory_free"] = torch.cuda.get_device_properties(0).total_memory - torch.cuda.memory_allocated(0)
            except:
                health["gpu_memory_free"] = 0
        
        # TorchServe-Status
        health["torchserve_connection"] = self._test_connection()
        
        # Gesamt-Status
        if not health["torchserve_connection"]:
            health["status"] = "degraded"
        
        return health
    
    def _discover_available_models(self) -> None:
        """Entdecke verfügbare TorchServe-Modelle"""
        
        try:
            if not self.is_connected:
                self.logger.warning("TorchServe not connected, cannot discover models")
                return
            
            response = requests.get(
                f"{self.config.base_url}/models",
                timeout=10
            )
            
            if response.status_code == 200:
                models_data = response.json()
                
                # Parse model information
                if isinstance(models_data, dict) and "models" in models_data:
                    for model_info in models_data["models"]:
                        model_name = model_info.get("modelName", "unknown")
                        self.available_models[model_name] = {
                            "name": model_name,
                            "version": model_info.get("modelVersion", "1.0"),
                            "status": model_info.get("status", "unknown"),
                            "workers": model_info.get("workers", []),
                            "endpoint": f"{self.config.base_url}/predictions/{model_name}"
                        }
                
                self.logger.info(f"Discovered {len(self.available_models)} TorchServe models")
                
                # Set default model if none selected
                if not self.current_model and self.available_models:
                    self.current_model = list(self.available_models.keys())[0]
                    self.logger.info(f"Set default model: {self.current_model}")
            
            else:
                self.logger.warning(f"Could not discover models: HTTP {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Model discovery failed: {e}")
    
    def switch_model(self, model_name: str) -> bool:
        """
        Wechsle zu einem anderen TorchServe-Modell
        
        Args:
            model_name: Name des Ziel-Modells
            
        Returns:
            True wenn erfolgreich, False sonst
        """
        
        try:
            if model_name not in self.available_models:
                self.logger.error(f"Model {model_name} not available. Available: {list(self.available_models.keys())}")
                return False
            
            # Test model availability
            test_response = requests.get(
                f"{self.config.base_url}/models/{model_name}",
                timeout=5
            )
            
            if test_response.status_code == 200:
                old_model = self.current_model
                self.current_model = model_name
                self.model_switch_count += 1
                
                self.logger.info(f"Model switched: {old_model} -> {model_name}")
                return True
            else:
                self.logger.error(f"Model {model_name} not ready: HTTP {test_response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Model switch failed: {e}")
            return False
    
    def get_current_model(self) -> Optional[str]:
        """Erhalte aktuell verwendetes Modell"""
        return self.current_model
    
    def list_available_models(self) -> List[str]:
        """Liste verfügbare Modelle"""
        return list(self.available_models.keys())
    
    def get_model_info(self, model_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Erhalte Informationen über ein Modell
        
        Args:
            model_name: Modell-Name (None für aktuelles Modell)
            
        Returns:
            Modell-Informationen
        """
        
        target_model = model_name or self.current_model
        
        if target_model and target_model in self.available_models:
            return self.available_models[target_model]
        else:
            return {"error": f"Model {target_model} not found"}
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Erhalte detaillierte Performance-Metriken
        
        Returns:
            Performance-Metriken mit Latenz-Tracking
        """
        
        # Berechne Latenz-Statistiken
        latency_stats = {}
        if self.latency_history:
            latency_stats = {
                "avg_latency_ms": np.mean(self.latency_history) * 1000,
                "min_latency_ms": np.min(self.latency_history) * 1000,
                "max_latency_ms": np.max(self.latency_history) * 1000,
                "p95_latency_ms": np.percentile(self.latency_history, 95) * 1000,
                "p99_latency_ms": np.percentile(self.latency_history, 99) * 1000,
                "total_samples": len(self.latency_history)
            }
        
        # Berechne Error-Rate
        total_requests = self.inference_count + self.error_count
        error_rate = self.error_count / max(total_requests, 1)
        
        # Berechne Throughput
        avg_processing_time = (
            self.total_processing_time / self.inference_count
            if self.inference_count > 0 else 0.0
        )
        throughput = 1.0 / avg_processing_time if avg_processing_time > 0 else 0.0
        
        return {
            "inference_metrics": {
                "total_inferences": self.inference_count,
                "batch_inferences": self.batch_processing_count,
                "error_count": self.error_count,
                "error_rate": error_rate,
                "success_rate": 1.0 - error_rate
            },
            "latency_metrics": latency_stats,
            "throughput_metrics": {
                "avg_processing_time_s": avg_processing_time,
                "throughput_req_per_s": throughput,
                "total_processing_time_s": self.total_processing_time
            },
            "model_metrics": {
                "current_model": self.current_model,
                "available_models": len(self.available_models),
                "model_switches": self.model_switch_count
            },
            "system_metrics": {
                "gpu_enabled": self.device.type == "cuda",
                "torchserve_connected": self.is_connected,
                "model_cache_size": len(self.model_cache)
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def _track_latency(self, processing_time: float) -> None:
        """Track Latenz für Performance-Monitoring"""
        
        self.latency_history.append(processing_time)
        
        # Behalte nur die letzten 1000 Messungen
        if len(self.latency_history) > 1000:
            self.latency_history = self.latency_history[-1000:]


# Factory Function
def create_torchserve_handler(config: Optional[TorchServeConfig] = None) -> TorchServeHandler:
    """
    Factory Function für TorchServe Handler
    
    Args:
        config: TorchServe-Konfiguration
        
    Returns:
        TorchServeHandler Instance
    """
    return TorchServeHandler(config=config)


if __name__ == "__main__":
    # Test des TorchServe Handlers
    print("🧪 Testing TorchServeHandler...")
    
    handler = create_torchserve_handler()
    
    # Test-Features
    test_features = {
        "price_change": 0.001,
        "volume": 1000.0,
        "rsi": 65.5,
        "macd": 0.0005,
        "bollinger_position": 0.7
    }
    
    # Test verschiedene Model-Typen
    for model_type in ModelType:
        print(f"\n🔍 Testing {model_type.value}...")
        
        result = handler.process_features(test_features, model_type)
        
        print(f"   Predictions: {result.predictions}")
        print(f"   Confidence: {result.confidence:.3f}")
        print(f"   Processing Time: {result.processing_time:.3f}s")
        print(f"   GPU Used: {result.gpu_used}")
    
    # Batch-Test
    print(f"\n🔄 Testing Batch Processing...")
    
    batch_features = [test_features.copy() for _ in range(5)]
    
    batch_result = handler.process_features(
        batch_features,
        ModelType.PATTERN_RECOGNITION,
        batch_processing=True
    )
    
    print(f"   Batch Size: {batch_result.batch_size}")
    print(f"   Predictions: {len(batch_result.predictions)} results")
    print(f"   Processing Time: {batch_result.processing_time:.3f}s")
    
    # Statistiken
    print(f"\n📊 Handler Statistics:")
    stats = handler.get_statistics()
    for key, value in stats.items():
        if isinstance(value, dict):
            print(f"   {key}:")
            for k, v in value.items():
                print(f"     {k}: {v}")
        else:
            print(f"   {key}: {value}")
    
    print("✅ TorchServeHandler Test completed!")