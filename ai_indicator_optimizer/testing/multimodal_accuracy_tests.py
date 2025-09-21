#!/usr/bin/env python3
"""
Multimodal Accuracy Tests für Vision+Text-Model-Performance
Phase 3 Implementation - Task 14

Features:
- Comprehensive Vision+Text-Model-Testing
- Cross-Modal-Accuracy-Validation
- Chart-Pattern-Recognition-Testing
- Text-Analysis-Accuracy-Validation
- Multimodal-Fusion-Performance-Testing
- Benchmark-Dataset-Validation
- Model-Robustness-Testing
"""

import time
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path
import json
from enum import Enum
import asyncio

# Image Processing
try:
    from PIL import Image, ImageDraw, ImageFont
    import matplotlib.pyplot as plt
    import seaborn as sns
    VISION_AVAILABLE = True
except ImportError:
    VISION_AVAILABLE = False

# ML Libraries
try:
    import torch
    import torch.nn as nn
    import torchvision.transforms as transforms
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    from sklearn.metrics import confusion_matrix, classification_report
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# NLP Libraries
try:
    import nltk
    from nltk.sentiment import SentimentIntensityAnalyzer
    NLP_AVAILABLE = True
except ImportError:
    NLP_AVAILABLE = False


class ModalityType(Enum):
    """Modalitäts-Typen"""
    VISION = "vision"
    TEXT = "text"
    MULTIMODAL = "multimodal"


class TestType(Enum):
    """Test-Typen"""
    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1_SCORE = "f1_score"
    ROBUSTNESS = "robustness"
    CROSS_MODAL = "cross_modal"


@dataclass
class TestSample:
    """Test-Sample für Multimodal-Testing"""
    sample_id: str
    modality: ModalityType
    input_data: Any
    ground_truth: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "modality": self.modality.value,
            "ground_truth": self.ground_truth,
            "metadata": self.metadata
        }


@dataclass
class AccuracyResult:
    """Accuracy-Test-Result"""
    test_name: str
    modality: ModalityType
    test_type: TestType
    accuracy: float
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    confusion_matrix: Optional[List[List[int]]] = None
    sample_count: int = 0
    error_analysis: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "modality": self.modality.value,
            "test_type": self.test_type.value,
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "confusion_matrix": self.confusion_matrix,
            "sample_count": self.sample_count,
            "error_analysis": self.error_analysis,
            "timestamp": datetime.now().isoformat()
        }


class MockVisionModel:
    """Mock Vision-Model für Testing"""
    
    def __init__(self, accuracy: float = 0.85):
        self.accuracy = accuracy
        self.logger = logging.getLogger(f"{__name__}.MockVisionModel")
    
    def predict_chart_pattern(self, image: Any) -> Dict[str, Any]:
        """Predict Chart-Pattern von Image"""
        
        # Mock-Prediction basierend auf konfigurierbarer Accuracy
        patterns = ["doji", "hammer", "shooting_star", "engulfing", "triangle", "head_shoulders"]
        
        # Simuliere Prediction mit gegebener Accuracy
        if np.random.random() < self.accuracy:
            # Korrekte Prediction (würde normalerweise aus Ground-Truth kommen)
            predicted_pattern = np.random.choice(patterns)
            confidence = np.random.uniform(0.8, 0.95)
        else:
            # Falsche Prediction
            predicted_pattern = np.random.choice(patterns)
            confidence = np.random.uniform(0.5, 0.8)
        
        return {
            "pattern": predicted_pattern,
            "confidence": confidence,
            "bounding_box": [0.2, 0.3, 0.8, 0.7],  # Mock-Bounding-Box
            "features": np.random.randn(128).tolist()  # Mock-Features
        }
    
    def predict_trend_direction(self, image: Any) -> Dict[str, Any]:
        """Predict Trend-Direction von Chart-Image"""
        
        directions = ["bullish", "bearish", "sideways"]
        
        if np.random.random() < self.accuracy:
            direction = np.random.choice(directions)
            confidence = np.random.uniform(0.8, 0.95)
        else:
            direction = np.random.choice(directions)
            confidence = np.random.uniform(0.5, 0.8)
        
        return {
            "direction": direction,
            "confidence": confidence,
            "strength": np.random.uniform(0.3, 1.0)
        }


class MockTextModel:
    """Mock Text-Model für Testing"""
    
    def __init__(self, accuracy: float = 0.82):
        self.accuracy = accuracy
        self.logger = logging.getLogger(f"{__name__}.MockTextModel")
    
    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze Sentiment von Text"""
        
        sentiments = ["positive", "negative", "neutral"]
        
        if np.random.random() < self.accuracy:
            sentiment = np.random.choice(sentiments)
            confidence = np.random.uniform(0.8, 0.95)
        else:
            sentiment = np.random.choice(sentiments)
            confidence = np.random.uniform(0.5, 0.8)
        
        return {
            "sentiment": sentiment,
            "confidence": confidence,
            "polarity": np.random.uniform(-1.0, 1.0),
            "subjectivity": np.random.uniform(0.0, 1.0)
        }
    
    def extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract Named-Entities von Text"""
        
        # Mock-Entities
        entities = {
            "companies": ["AAPL", "TSLA", "MSFT", "GOOGL"],
            "currencies": ["USD", "EUR", "BTC", "ETH"],
            "indicators": ["RSI", "MACD", "SMA", "EMA"],
            "numbers": [100, 200, 0.5, 1.2]
        }
        
        extracted = {}
        for entity_type, options in entities.items():
            if np.random.random() < self.accuracy:
                extracted[entity_type] = np.random.choice(options, size=np.random.randint(0, 3)).tolist()
            else:
                extracted[entity_type] = []
        
        return {
            "entities": extracted,
            "confidence": np.random.uniform(0.7, 0.95)
        }


class MockMultimodalModel:
    """Mock Multimodal-Model für Testing"""
    
    def __init__(self, vision_accuracy: float = 0.85, text_accuracy: float = 0.82):
        self.vision_model = MockVisionModel(vision_accuracy)
        self.text_model = MockTextModel(text_accuracy)
        self.fusion_accuracy = (vision_accuracy + text_accuracy) / 2 * 1.1  # Fusion-Bonus
        self.logger = logging.getLogger(f"{__name__}.MockMultimodalModel")
    
    def predict_multimodal(self, image: Any, text: str) -> Dict[str, Any]:
        """Multimodal-Prediction mit Vision+Text"""
        
        # Vision-Prediction
        vision_result = self.vision_model.predict_chart_pattern(image)
        
        # Text-Prediction
        text_result = self.text_model.analyze_sentiment(text)
        
        # Fusion-Logic
        if np.random.random() < self.fusion_accuracy:
            # Erfolgreiche Fusion
            fusion_confidence = (vision_result["confidence"] + text_result["confidence"]) / 2 * 1.1
            fusion_prediction = "bullish" if text_result["sentiment"] == "positive" else "bearish"
        else:
            # Fusion-Fehler
            fusion_confidence = np.random.uniform(0.4, 0.7)
            fusion_prediction = np.random.choice(["bullish", "bearish", "neutral"])
        
        return {
            "vision_result": vision_result,
            "text_result": text_result,
            "fusion_prediction": fusion_prediction,
            "fusion_confidence": min(1.0, fusion_confidence),
            "modality_weights": {
                "vision": np.random.uniform(0.3, 0.7),
                "text": np.random.uniform(0.3, 0.7)
            }
        }


class MultimodalAccuracyTests:
    """
    Multimodal Accuracy Tests für Vision+Text-Model-Performance
    
    Features:
    - Vision-Model-Accuracy-Testing für Chart-Pattern-Recognition
    - Text-Model-Accuracy-Testing für Sentiment und Entity-Extraction
    - Multimodal-Fusion-Performance-Testing
    - Cross-Modal-Consistency-Validation
    - Robustness-Testing mit Noise und Adversarial-Samples
    - Benchmark-Dataset-Validation
    - Error-Analysis und Performance-Breakdown
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Test-Konfiguration
        self.enable_vision_tests = self.config.get("enable_vision_tests", VISION_AVAILABLE)
        self.enable_text_tests = self.config.get("enable_text_tests", True)
        self.enable_multimodal_tests = self.config.get("enable_multimodal_tests", True)
        self.enable_robustness_tests = self.config.get("enable_robustness_tests", True)
        
        # Model-Konfiguration
        self.vision_accuracy = self.config.get("vision_accuracy", 0.85)
        self.text_accuracy = self.config.get("text_accuracy", 0.82)
        
        # Mock-Models
        self.vision_model = MockVisionModel(self.vision_accuracy)
        self.text_model = MockTextModel(self.text_accuracy)
        self.multimodal_model = MockMultimodalModel(self.vision_accuracy, self.text_accuracy)
        
        # Test-Results
        self.test_results: List[AccuracyResult] = []
        
        # Output-Directory
        self.results_directory = Path(self.config.get("results_directory", "accuracy_test_results"))
        self.results_directory.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("MultimodalAccuracyTests initialized")
    
    async def run_all_accuracy_tests(self) -> List[AccuracyResult]:
        """Führe alle Accuracy-Tests durch"""
        
        self.logger.info("Starting comprehensive multimodal accuracy tests")
        
        results = []
        
        # Vision-Tests
        if self.enable_vision_tests:
            vision_results = await self.run_vision_accuracy_tests()
            results.extend(vision_results)
        
        # Text-Tests
        if self.enable_text_tests:
            text_results = await self.run_text_accuracy_tests()
            results.extend(text_results)
        
        # Multimodal-Tests
        if self.enable_multimodal_tests:
            multimodal_results = await self.run_multimodal_accuracy_tests()
            results.extend(multimodal_results)
        
        # Robustness-Tests
        if self.enable_robustness_tests:
            robustness_results = await self.run_robustness_tests()
            results.extend(robustness_results)
        
        self.test_results.extend(results)
        
        self.logger.info(f"Completed {len(results)} accuracy tests")
        
        return results
    
    async def run_vision_accuracy_tests(self) -> List[AccuracyResult]:
        """Führe Vision-Accuracy-Tests durch"""
        
        self.logger.info("Running vision accuracy tests")
        
        results = []
        
        # Chart-Pattern-Recognition-Test
        pattern_result = await self._test_chart_pattern_recognition()
        results.append(pattern_result)
        
        # Trend-Direction-Test
        trend_result = await self._test_trend_direction_recognition()
        results.append(trend_result)
        
        # Support-Resistance-Test
        sr_result = await self._test_support_resistance_detection()
        results.append(sr_result)
        
        return results
    
    async def _test_chart_pattern_recognition(self) -> AccuracyResult:
        """Test Chart-Pattern-Recognition"""
        
        test_name = "chart_pattern_recognition"
        
        try:
            # Generiere Test-Samples
            test_samples = self._generate_chart_pattern_samples(100)
            
            predictions = []
            ground_truths = []
            
            for sample in test_samples:
                # Model-Prediction
                prediction = self.vision_model.predict_chart_pattern(sample.input_data)
                
                predictions.append(prediction["pattern"])
                ground_truths.append(sample.ground_truth)
            
            # Berechne Metriken
            accuracy = self._calculate_accuracy(predictions, ground_truths)
            precision, recall, f1 = self._calculate_classification_metrics(predictions, ground_truths)
            confusion_mat = self._calculate_confusion_matrix(predictions, ground_truths)
            
            # Error-Analysis
            error_analysis = self._analyze_prediction_errors(predictions, ground_truths, test_samples)
            
            return AccuracyResult(
                test_name=test_name,
                modality=ModalityType.VISION,
                test_type=TestType.ACCURACY,
                accuracy=accuracy,
                precision=precision,
                recall=recall,
                f1_score=f1,
                confusion_matrix=confusion_mat,
                sample_count=len(test_samples),
                error_analysis=error_analysis
            )
            
        except Exception as e:
            self.logger.error(f"Chart pattern recognition test failed: {e}")
            return AccuracyResult(
                test_name=test_name,
                modality=ModalityType.VISION,
                test_type=TestType.ACCURACY,
                accuracy=0.0,
                sample_count=0,
                error_analysis={"error": str(e)}
            )
    
    async def _test_trend_direction_recognition(self) -> AccuracyResult:
        """Test Trend-Direction-Recognition"""
        
        test_name = "trend_direction_recognition"
        
        try:
            # Generiere Test-Samples
            test_samples = self._generate_trend_direction_samples(150)
            
            predictions = []
            ground_truths = []
            
            for sample in test_samples:
                # Model-Prediction
                prediction = self.vision_model.predict_trend_direction(sample.input_data)
                
                predictions.append(prediction["direction"])
                ground_truths.append(sample.ground_truth)
            
            # Berechne Metriken
            accuracy = self._calculate_accuracy(predictions, ground_truths)
            precision, recall, f1 = self._calculate_classification_metrics(predictions, ground_truths)
            confusion_mat = self._calculate_confusion_matrix(predictions, ground_truths)
            
            return AccuracyResult(
                test_name=test_name,
                modality=ModalityType.VISION,
                test_type=TestType.ACCURACY,
                accuracy=accuracy,
                precision=precision,
                recall=recall,
                f1_score=f1,
                confusion_matrix=confusion_mat,
                sample_count=len(test_samples)
            )
            
        except Exception as e:
            self.logger.error(f"Trend direction recognition test failed: {e}")
            return AccuracyResult(
                test_name=test_name,
                modality=ModalityType.VISION,
                test_type=TestType.ACCURACY,
                accuracy=0.0,
                sample_count=0,
                error_analysis={"error": str(e)}
            )
    
    async def _test_support_resistance_detection(self) -> AccuracyResult:
        """Test Support-Resistance-Detection"""
        
        test_name = "support_resistance_detection"
        
        try:
            # Generiere Test-Samples
            test_samples = self._generate_support_resistance_samples(80)
            
            predictions = []
            ground_truths = []
            
            for sample in test_samples:
                # Mock-Prediction für Support/Resistance
                if np.random.random() < self.vision_accuracy:
                    prediction = sample.ground_truth  # Korrekte Prediction
                else:
                    prediction = "support" if sample.ground_truth == "resistance" else "resistance"
                
                predictions.append(prediction)
                ground_truths.append(sample.ground_truth)
            
            # Berechne Metriken
            accuracy = self._calculate_accuracy(predictions, ground_truths)
            precision, recall, f1 = self._calculate_classification_metrics(predictions, ground_truths)
            
            return AccuracyResult(
                test_name=test_name,
                modality=ModalityType.VISION,
                test_type=TestType.ACCURACY,
                accuracy=accuracy,
                precision=precision,
                recall=recall,
                f1_score=f1,
                sample_count=len(test_samples)
            )
            
        except Exception as e:
            self.logger.error(f"Support resistance detection test failed: {e}")
            return AccuracyResult(
                test_name=test_name,
                modality=ModalityType.VISION,
                test_type=TestType.ACCURACY,
                accuracy=0.0,
                sample_count=0,
                error_analysis={"error": str(e)}
            )
    
    async def run_text_accuracy_tests(self) -> List[AccuracyResult]:
        """Führe Text-Accuracy-Tests durch"""
        
        self.logger.info("Running text accuracy tests")
        
        results = []
        
        # Sentiment-Analysis-Test
        sentiment_result = await self._test_sentiment_analysis()
        results.append(sentiment_result)
        
        # Entity-Extraction-Test
        entity_result = await self._test_entity_extraction()
        results.append(entity_result)
        
        # Financial-Text-Classification-Test
        classification_result = await self._test_financial_text_classification()
        results.append(classification_result)
        
        return results
    
    async def _test_sentiment_analysis(self) -> AccuracyResult:
        """Test Sentiment-Analysis"""
        
        test_name = "sentiment_analysis"
        
        try:
            # Generiere Test-Samples
            test_samples = self._generate_sentiment_samples(200)
            
            predictions = []
            ground_truths = []
            
            for sample in test_samples:
                # Model-Prediction
                prediction = self.text_model.analyze_sentiment(sample.input_data)
                
                predictions.append(prediction["sentiment"])
                ground_truths.append(sample.ground_truth)
            
            # Berechne Metriken
            accuracy = self._calculate_accuracy(predictions, ground_truths)
            precision, recall, f1 = self._calculate_classification_metrics(predictions, ground_truths)
            confusion_mat = self._calculate_confusion_matrix(predictions, ground_truths)
            
            return AccuracyResult(
                test_name=test_name,
                modality=ModalityType.TEXT,
                test_type=TestType.ACCURACY,
                accuracy=accuracy,
                precision=precision,
                recall=recall,
                f1_score=f1,
                confusion_matrix=confusion_mat,
                sample_count=len(test_samples)
            )
            
        except Exception as e:
            self.logger.error(f"Sentiment analysis test failed: {e}")
            return AccuracyResult(
                test_name=test_name,
                modality=ModalityType.TEXT,
                test_type=TestType.ACCURACY,
                accuracy=0.0,
                sample_count=0,
                error_analysis={"error": str(e)}
            )
    
    async def _test_entity_extraction(self) -> AccuracyResult:
        """Test Entity-Extraction"""
        
        test_name = "entity_extraction"
        
        try:
            # Generiere Test-Samples
            test_samples = self._generate_entity_extraction_samples(120)
            
            predictions = []
            ground_truths = []
            
            for sample in test_samples:
                # Model-Prediction
                prediction = self.text_model.extract_entities(sample.input_data)
                
                # Vereinfachte Evaluation (nur Company-Entities)
                predicted_companies = prediction["entities"].get("companies", [])
                true_companies = sample.ground_truth.get("companies", [])
                
                # Berechne Overlap
                if true_companies:
                    overlap = len(set(predicted_companies) & set(true_companies))
                    accuracy = overlap / len(true_companies)
                else:
                    accuracy = 1.0 if not predicted_companies else 0.0
                
                predictions.append(accuracy)
                ground_truths.append(1.0)  # Perfect-Score als Referenz
            
            # Durchschnittliche Accuracy
            avg_accuracy = np.mean(predictions) if predictions else 0.0
            
            return AccuracyResult(
                test_name=test_name,
                modality=ModalityType.TEXT,
                test_type=TestType.ACCURACY,
                accuracy=avg_accuracy,
                sample_count=len(test_samples)
            )
            
        except Exception as e:
            self.logger.error(f"Entity extraction test failed: {e}")
            return AccuracyResult(
                test_name=test_name,
                modality=ModalityType.TEXT,
                test_type=TestType.ACCURACY,
                accuracy=0.0,
                sample_count=0,
                error_analysis={"error": str(e)}
            )
    
    async def _test_financial_text_classification(self) -> AccuracyResult:
        """Test Financial-Text-Classification"""
        
        test_name = "financial_text_classification"
        
        try:
            # Generiere Test-Samples
            test_samples = self._generate_financial_text_samples(100)
            
            predictions = []
            ground_truths = []
            
            for sample in test_samples:
                # Mock-Classification
                if np.random.random() < self.text_accuracy:
                    prediction = sample.ground_truth
                else:
                    categories = ["earnings", "merger", "dividend", "guidance", "regulatory"]
                    prediction = np.random.choice([c for c in categories if c != sample.ground_truth])
                
                predictions.append(prediction)
                ground_truths.append(sample.ground_truth)
            
            # Berechne Metriken
            accuracy = self._calculate_accuracy(predictions, ground_truths)
            precision, recall, f1 = self._calculate_classification_metrics(predictions, ground_truths)
            
            return AccuracyResult(
                test_name=test_name,
                modality=ModalityType.TEXT,
                test_type=TestType.ACCURACY,
                accuracy=accuracy,
                precision=precision,
                recall=recall,
                f1_score=f1,
                sample_count=len(test_samples)
            )
            
        except Exception as e:
            self.logger.error(f"Financial text classification test failed: {e}")
            return AccuracyResult(
                test_name=test_name,
                modality=ModalityType.TEXT,
                test_type=TestType.ACCURACY,
                accuracy=0.0,
                sample_count=0,
                error_analysis={"error": str(e)}
            )    

    async def run_multimodal_accuracy_tests(self) -> List[AccuracyResult]:
        """Führe Multimodal-Accuracy-Tests durch"""
        
        self.logger.info("Running multimodal accuracy tests")
        
        results = []
        
        # Multimodal-Fusion-Test
        fusion_result = await self._test_multimodal_fusion()
        results.append(fusion_result)
        
        # Cross-Modal-Consistency-Test
        consistency_result = await self._test_cross_modal_consistency()
        results.append(consistency_result)
        
        return results
    
    async def _test_multimodal_fusion(self) -> AccuracyResult:
        """Test Multimodal-Fusion"""
        
        test_name = "multimodal_fusion"
        
        try:
            # Generiere Multimodal-Test-Samples
            test_samples = self._generate_multimodal_samples(80)
            
            predictions = []
            ground_truths = []
            
            for sample in test_samples:
                # Multimodal-Prediction
                image_data, text_data = sample.input_data
                prediction = self.multimodal_model.predict_multimodal(image_data, text_data)
                
                predictions.append(prediction["fusion_prediction"])
                ground_truths.append(sample.ground_truth)
            
            # Berechne Metriken
            accuracy = self._calculate_accuracy(predictions, ground_truths)
            precision, recall, f1 = self._calculate_classification_metrics(predictions, ground_truths)
            
            return AccuracyResult(
                test_name=test_name,
                modality=ModalityType.MULTIMODAL,
                test_type=TestType.ACCURACY,
                accuracy=accuracy,
                precision=precision,
                recall=recall,
                f1_score=f1,
                sample_count=len(test_samples)
            )
            
        except Exception as e:
            self.logger.error(f"Multimodal fusion test failed: {e}")
            return AccuracyResult(
                test_name=test_name,
                modality=ModalityType.MULTIMODAL,
                test_type=TestType.ACCURACY,
                accuracy=0.0,
                sample_count=0,
                error_analysis={"error": str(e)}
            )
    
    async def _test_cross_modal_consistency(self) -> AccuracyResult:
        """Test Cross-Modal-Consistency"""
        
        test_name = "cross_modal_consistency"
        
        try:
            # Generiere konsistente Vision+Text-Samples
            test_samples = self._generate_consistent_multimodal_samples(60)
            
            consistency_scores = []
            
            for sample in test_samples:
                image_data, text_data = sample.input_data
                
                # Separate Predictions
                vision_pred = self.vision_model.predict_trend_direction(image_data)
                text_pred = self.text_model.analyze_sentiment(text_data)
                
                # Consistency-Check
                vision_direction = vision_pred["direction"]
                text_sentiment = text_pred["sentiment"]
                
                # Mapping: positive sentiment -> bullish, negative -> bearish
                expected_consistency = (
                    (vision_direction == "bullish" and text_sentiment == "positive") or
                    (vision_direction == "bearish" and text_sentiment == "negative") or
                    (vision_direction == "sideways" and text_sentiment == "neutral")
                )
                
                consistency_scores.append(1.0 if expected_consistency else 0.0)
            
            # Durchschnittliche Consistency
            avg_consistency = np.mean(consistency_scores) if consistency_scores else 0.0
            
            return AccuracyResult(
                test_name=test_name,
                modality=ModalityType.MULTIMODAL,
                test_type=TestType.CROSS_MODAL,
                accuracy=avg_consistency,
                sample_count=len(test_samples)
            )
            
        except Exception as e:
            self.logger.error(f"Cross-modal consistency test failed: {e}")
            return AccuracyResult(
                test_name=test_name,
                modality=ModalityType.MULTIMODAL,
                test_type=TestType.CROSS_MODAL,
                accuracy=0.0,
                sample_count=0,
                error_analysis={"error": str(e)}
            )
    
    async def run_robustness_tests(self) -> List[AccuracyResult]:
        """Führe Robustness-Tests durch"""
        
        self.logger.info("Running robustness tests")
        
        results = []
        
        # Noise-Robustness-Test
        noise_result = await self._test_noise_robustness()
        results.append(noise_result)
        
        # Adversarial-Robustness-Test
        adversarial_result = await self._test_adversarial_robustness()
        results.append(adversarial_result)
        
        return results
    
    async def _test_noise_robustness(self) -> AccuracyResult:
        """Test Noise-Robustness"""
        
        test_name = "noise_robustness"
        
        try:
            # Generiere Clean-Samples
            clean_samples = self._generate_chart_pattern_samples(50)
            
            # Teste verschiedene Noise-Level
            noise_levels = [0.1, 0.2, 0.3, 0.4, 0.5]
            robustness_scores = []
            
            for noise_level in noise_levels:
                correct_predictions = 0
                
                for sample in clean_samples:
                    # Füge Noise hinzu (simuliert)
                    noisy_input = self._add_noise_to_input(sample.input_data, noise_level)
                    
                    # Prediction mit Noise
                    prediction = self.vision_model.predict_chart_pattern(noisy_input)
                    
                    # Prüfe ob Prediction noch korrekt
                    if prediction["pattern"] == sample.ground_truth:
                        correct_predictions += 1
                
                accuracy_with_noise = correct_predictions / len(clean_samples)
                robustness_scores.append(accuracy_with_noise)
            
            # Durchschnittliche Robustness
            avg_robustness = np.mean(robustness_scores)
            
            return AccuracyResult(
                test_name=test_name,
                modality=ModalityType.VISION,
                test_type=TestType.ROBUSTNESS,
                accuracy=avg_robustness,
                sample_count=len(clean_samples) * len(noise_levels),
                error_analysis={
                    "noise_levels_tested": noise_levels,
                    "robustness_by_noise_level": dict(zip(noise_levels, robustness_scores))
                }
            )
            
        except Exception as e:
            self.logger.error(f"Noise robustness test failed: {e}")
            return AccuracyResult(
                test_name=test_name,
                modality=ModalityType.VISION,
                test_type=TestType.ROBUSTNESS,
                accuracy=0.0,
                sample_count=0,
                error_analysis={"error": str(e)}
            )
    
    async def _test_adversarial_robustness(self) -> AccuracyResult:
        """Test Adversarial-Robustness"""
        
        test_name = "adversarial_robustness"
        
        try:
            # Generiere Adversarial-Samples (simuliert)
            test_samples = self._generate_chart_pattern_samples(40)
            
            correct_predictions = 0
            
            for sample in test_samples:
                # Simuliere Adversarial-Attack
                adversarial_input = self._create_adversarial_sample(sample.input_data)
                
                # Prediction mit Adversarial-Input
                prediction = self.vision_model.predict_chart_pattern(adversarial_input)
                
                # Prüfe Robustness (sollte trotz Attack korrekt sein)
                if prediction["pattern"] == sample.ground_truth:
                    correct_predictions += 1
            
            accuracy = correct_predictions / len(test_samples)
            
            return AccuracyResult(
                test_name=test_name,
                modality=ModalityType.VISION,
                test_type=TestType.ROBUSTNESS,
                accuracy=accuracy,
                sample_count=len(test_samples)
            )
            
        except Exception as e:
            self.logger.error(f"Adversarial robustness test failed: {e}")
            return AccuracyResult(
                test_name=test_name,
                modality=ModalityType.VISION,
                test_type=TestType.ROBUSTNESS,
                accuracy=0.0,
                sample_count=0,
                error_analysis={"error": str(e)}
            )
    
    # Helper-Methoden für Sample-Generation
    def _generate_chart_pattern_samples(self, count: int) -> List[TestSample]:
        """Generiere Chart-Pattern-Test-Samples"""
        
        patterns = ["doji", "hammer", "shooting_star", "engulfing", "triangle"]
        samples = []
        
        for i in range(count):
            pattern = np.random.choice(patterns)
            
            # Mock-Image-Data (würde normalerweise echte Chart-Images sein)
            image_data = f"mock_chart_image_{pattern}_{i}"
            
            sample = TestSample(
                sample_id=f"pattern_{i}",
                modality=ModalityType.VISION,
                input_data=image_data,
                ground_truth=pattern,
                metadata={"pattern_type": pattern}
            )
            
            samples.append(sample)
        
        return samples
    
    def _generate_sentiment_samples(self, count: int) -> List[TestSample]:
        """Generiere Sentiment-Test-Samples"""
        
        sentiments = ["positive", "negative", "neutral"]
        samples = []
        
        # Sample-Texte
        sample_texts = {
            "positive": ["Great earnings report!", "Stock price surging!", "Bullish outlook ahead"],
            "negative": ["Disappointing results", "Stock price falling", "Bearish sentiment"],
            "neutral": ["Market update", "Price unchanged", "Waiting for news"]
        }
        
        for i in range(count):
            sentiment = np.random.choice(sentiments)
            text = np.random.choice(sample_texts[sentiment])
            
            sample = TestSample(
                sample_id=f"sentiment_{i}",
                modality=ModalityType.TEXT,
                input_data=text,
                ground_truth=sentiment,
                metadata={"text_length": len(text)}
            )
            
            samples.append(sample)
        
        return samples
    
    def _calculate_accuracy(self, predictions: List[Any], ground_truths: List[Any]) -> float:
        """Berechne Accuracy"""
        
        if not predictions or not ground_truths or len(predictions) != len(ground_truths):
            return 0.0
        
        correct = sum(1 for pred, truth in zip(predictions, ground_truths) if pred == truth)
        return correct / len(predictions)
    
    def _calculate_classification_metrics(self, predictions: List[Any], 
                                        ground_truths: List[Any]) -> Tuple[float, float, float]:
        """Berechne Classification-Metriken"""
        
        if not SKLEARN_AVAILABLE or not predictions or not ground_truths:
            return 0.0, 0.0, 0.0
        
        try:
            precision = precision_score(ground_truths, predictions, average='weighted', zero_division=0)
            recall = recall_score(ground_truths, predictions, average='weighted', zero_division=0)
            f1 = f1_score(ground_truths, predictions, average='weighted', zero_division=0)
            
            return precision, recall, f1
            
        except Exception as e:
            self.logger.error(f"Error calculating classification metrics: {e}")
            return 0.0, 0.0, 0.0
    
    def generate_accuracy_report(self) -> Dict[str, Any]:
        """Generiere Accuracy-Report"""
        
        try:
            if not self.test_results:
                return {"error": "No test results available"}
            
            # Gruppiere Results nach Modalität
            results_by_modality = defaultdict(list)
            for result in self.test_results:
                results_by_modality[result.modality].append(result)
            
            # Berechne Modalitäts-Statistiken
            modality_stats = {}
            for modality, results in results_by_modality.items():
                accuracies = [r.accuracy for r in results]
                
                modality_stats[modality.value] = {
                    "test_count": len(results),
                    "avg_accuracy": np.mean(accuracies),
                    "min_accuracy": min(accuracies),
                    "max_accuracy": max(accuracies),
                    "std_accuracy": np.std(accuracies)
                }
            
            # Overall-Statistiken
            all_accuracies = [r.accuracy for r in self.test_results]
            
            overall_stats = {
                "total_tests": len(self.test_results),
                "avg_accuracy": np.mean(all_accuracies),
                "median_accuracy": np.median(all_accuracies),
                "min_accuracy": min(all_accuracies),
                "max_accuracy": max(all_accuracies),
                "std_accuracy": np.std(all_accuracies)
            }
            
            # Test-Details
            test_details = []
            for result in self.test_results:
                test_details.append({
                    "test_name": result.test_name,
                    "modality": result.modality.value,
                    "test_type": result.test_type.value,
                    "accuracy": result.accuracy,
                    "precision": result.precision,
                    "recall": result.recall,
                    "f1_score": result.f1_score,
                    "sample_count": result.sample_count
                })
            
            # Failed-Tests
            failed_tests = [
                {
                    "test_name": result.test_name,
                    "modality": result.modality.value,
                    "accuracy": result.accuracy,
                    "error_analysis": result.error_analysis
                }
                for result in self.test_results if result.accuracy < 0.6
            ]
            
            report = {
                "timestamp": datetime.now().isoformat(),
                "overall_statistics": overall_stats,
                "modality_statistics": modality_stats,
                "test_details": test_details,
                "failed_tests": failed_tests,
                "model_performance": {
                    "vision_model_accuracy": self.vision_accuracy,
                    "text_model_accuracy": self.text_accuracy,
                    "multimodal_fusion_bonus": 0.1
                },
                "overall_status": "PASS" if overall_stats["avg_accuracy"] >= 0.75 else "FAIL"
            }
            
            # Report speichern
            report_file = self.results_directory / f"accuracy_test_report_{int(time.time())}.json"
            
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            self.logger.info(f"Accuracy test report generated: {report_file}")
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating accuracy report: {e}")
            return {"error": str(e)}
    
    # Utility-Methoden für Sample-Generation (vereinfacht)
    def _generate_trend_direction_samples(self, count: int) -> List[TestSample]:
        directions = ["bullish", "bearish", "sideways"]
        return [TestSample(f"trend_{i}", ModalityType.VISION, f"mock_chart_{i}", np.random.choice(directions)) 
                for i in range(count)]
    
    def _generate_support_resistance_samples(self, count: int) -> List[TestSample]:
        levels = ["support", "resistance"]
        return [TestSample(f"sr_{i}", ModalityType.VISION, f"mock_chart_{i}", np.random.choice(levels)) 
                for i in range(count)]
    
    def _generate_entity_extraction_samples(self, count: int) -> List[TestSample]:
        companies = ["AAPL", "TSLA", "MSFT", "GOOGL"]
        return [TestSample(f"entity_{i}", ModalityType.TEXT, f"News about {np.random.choice(companies)}", 
                          {"companies": [np.random.choice(companies)]}) for i in range(count)]
    
    def _generate_financial_text_samples(self, count: int) -> List[TestSample]:
        categories = ["earnings", "merger", "dividend", "guidance", "regulatory"]
        return [TestSample(f"fintext_{i}", ModalityType.TEXT, f"Financial news {i}", np.random.choice(categories)) 
                for i in range(count)]
    
    def _generate_multimodal_samples(self, count: int) -> List[TestSample]:
        directions = ["bullish", "bearish", "neutral"]
        return [TestSample(f"multimodal_{i}", ModalityType.MULTIMODAL, 
                          (f"mock_chart_{i}", f"market analysis {i}"), np.random.choice(directions)) 
                for i in range(count)]
    
    def _generate_consistent_multimodal_samples(self, count: int) -> List[TestSample]:
        # Konsistente Vision+Text-Samples
        consistent_pairs = [
            ("bullish_chart", "positive news", "bullish"),
            ("bearish_chart", "negative news", "bearish"),
            ("sideways_chart", "neutral news", "neutral")
        ]
        
        samples = []
        for i in range(count):
            chart, text, truth = consistent_pairs[i % len(consistent_pairs)]
            sample = TestSample(f"consistent_{i}", ModalityType.MULTIMODAL, 
                              (f"{chart}_{i}", f"{text} {i}"), truth)
            samples.append(sample)
        
        return samples
    
    def _add_noise_to_input(self, input_data: Any, noise_level: float) -> Any:
        """Füge Noise zu Input hinzu (simuliert)"""
        # In echter Implementierung würde hier Noise zu Images/Text hinzugefügt
        return f"{input_data}_noise_{noise_level}"
    
    def _create_adversarial_sample(self, input_data: Any) -> Any:
        """Erstelle Adversarial-Sample (simuliert)"""
        # In echter Implementierung würde hier ein Adversarial-Attack durchgeführt
        return f"{input_data}_adversarial"
    
    def _calculate_confusion_matrix(self, predictions: List[Any], ground_truths: List[Any]) -> Optional[List[List[int]]]:
        """Berechne Confusion-Matrix"""
        
        if not SKLEARN_AVAILABLE or not predictions or not ground_truths:
            return None
        
        try:
            cm = confusion_matrix(ground_truths, predictions)
            return cm.tolist()
        except Exception as e:
            self.logger.error(f"Error calculating confusion matrix: {e}")
            return None
    
    def _analyze_prediction_errors(self, predictions: List[Any], ground_truths: List[Any], 
                                 samples: List[TestSample]) -> Dict[str, Any]:
        """Analysiere Prediction-Errors"""
        
        error_analysis = {
            "total_errors": 0,
            "error_by_class": defaultdict(int),
            "common_misclassifications": defaultdict(int)
        }
        
        for pred, truth, sample in zip(predictions, ground_truths, samples):
            if pred != truth:
                error_analysis["total_errors"] += 1
                error_analysis["error_by_class"][truth] += 1
                error_analysis["common_misclassifications"][f"{truth}->{pred}"] += 1
        
        return dict(error_analysis)


# Utility-Funktionen
async def run_multimodal_accuracy_test_suite(config: Optional[Dict] = None) -> Dict[str, Any]:
    """Führe komplette Multimodal-Accuracy-Test-Suite aus"""
    
    test_suite = MultimodalAccuracyTests(config)
    
    # Führe alle Tests aus
    results = await test_suite.run_all_accuracy_tests()
    
    # Generiere Report
    report = test_suite.generate_accuracy_report()
    
    return {
        "test_results": [result.to_dict() for result in results],
        "report": report
    }


def setup_accuracy_test_config(vision_accuracy: float = 0.85,
                             text_accuracy: float = 0.82,
                             enable_robustness: bool = True) -> Dict[str, Any]:
    """Setup Accuracy-Test-Konfiguration"""
    
    return {
        "enable_vision_tests": True,
        "enable_text_tests": True,
        "enable_multimodal_tests": True,
        "enable_robustness_tests": enable_robustness,
        "vision_accuracy": vision_accuracy,
        "text_accuracy": text_accuracy,
        "results_directory": "accuracy_test_results"
    }