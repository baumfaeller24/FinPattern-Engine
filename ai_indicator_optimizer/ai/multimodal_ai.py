"""
MiniCPM-4.1-8B Multimodal AI Engine - Optimiert für RTX 5090 + 191GB RAM
"""

import torch
import torch.nn as nn
from transformers import (
    AutoTokenizer, AutoProcessor, AutoModel,
    BitsAndBytesConfig, TrainingArguments
)
from PIL import Image
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union
import logging
from dataclasses import dataclass
import time
from pathlib import Path
import json
import gc
from concurrent.futures import ThreadPoolExecutor
import asyncio

from .models import PatternAnalysis, OptimizedParameters, MultimodalInput
from ..core.resource_manager import ResourceManager, ResourceContext
from ..core.config import SystemConfig


@dataclass
class ModelConfig:
    """MiniCPM Model Konfiguration für RTX 5090"""
    model_name: str = "openbmb/MiniCPM-V-2_6"  # Aktuell verfügbare Version
    device_map: str = "auto"
    torch_dtype: torch.dtype = torch.float16
    trust_remote_code: bool = True
    use_flash_attention: bool = True
    load_in_8bit: bool = False
    load_in_4bit: bool = False
    max_memory: Dict[int, str] = None
    
    # RTX 5090 spezifische Optimierungen
    use_tensor_cores: bool = True
    enable_mixed_precision: bool = True
    gradient_checkpointing: bool = True
    
    # Memory Management für 32GB VRAM
    max_batch_size: int = 8
    max_sequence_length: int = 4096
    image_resolution: int = 448  # MiniCPM-V optimal resolution


@dataclass
class InferenceConfig:
    """Inference-Konfiguration"""
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    max_new_tokens: int = 512
    do_sample: bool = True
    num_beams: int = 1
    repetition_penalty: float = 1.1


class GPUMemoryManager:
    """
    GPU Memory Manager für RTX 5090 (32GB VRAM)
    """
    
    def __init__(self, device_id: int = 0):
        self.device_id = device_id
        self.device = torch.device(f"cuda:{device_id}")
        self.logger = logging.getLogger(__name__)
        
        if torch.cuda.is_available():
            self.total_memory = torch.cuda.get_device_properties(device_id).total_memory
            self.logger.info(f"GPU {device_id}: {self.total_memory // (1024**3)} GB VRAM")
        else:
            self.total_memory = 0
    
    def get_memory_stats(self) -> Dict[str, int]:
        """Gibt aktuelle GPU Memory-Statistiken zurück"""
        if not torch.cuda.is_available():
            return {
                "total": 0, 
                "allocated": 0, 
                "cached": 0, 
                "free": 0,
                "allocated_gb": 0,
                "free_gb": 0
            }
        
        allocated = torch.cuda.memory_allocated(self.device_id)
        cached = torch.cuda.memory_reserved(self.device_id)
        free = self.total_memory - allocated
        
        return {
            "total": self.total_memory,
            "allocated": allocated,
            "cached": cached,
            "free": free,
            "allocated_gb": allocated // (1024**3),
            "free_gb": free // (1024**3)
        }
    
    def optimize_for_model_loading(self, model_size_gb: int = 8) -> Dict[str, Any]:
        """Optimiert GPU Memory für Model-Loading"""
        # Leere Cache
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        
        stats = self.get_memory_stats()
        
        # Berechne optimale Konfiguration
        available_gb = stats["free_gb"]
        
        config = {
            "can_load_model": available_gb >= model_size_gb,
            "recommended_batch_size": min(8, max(1, available_gb // 4)),
            "use_gradient_checkpointing": available_gb < 16,
            "use_8bit_loading": available_gb < 12,
            "use_4bit_loading": available_gb < 8,
            "max_sequence_length": 4096 if available_gb >= 16 else 2048
        }
        
        self.logger.info(f"GPU Memory optimization: {config}")
        return config
    
    def clear_memory(self):
        """Bereinigt GPU Memory"""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            gc.collect()


class MiniCPMModelWrapper:
    """
    High-Performance Wrapper für MiniCPM-4.1-8B Model
    Optimiert für RTX 5090 + 191GB RAM
    """
    
    def __init__(self, config: ModelConfig, resource_manager: Optional[ResourceManager] = None):
        self.config = config
        self.resource_manager = resource_manager
        self.gpu_manager = GPUMemoryManager()
        self.logger = logging.getLogger(__name__)
        
        # Model Components
        self.model = None
        self.processor = None
        self.tokenizer = None
        
        # Performance Tracking
        self.inference_times = []
        self.memory_usage = []
        
        # Setup Device
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.logger.info(f"MiniCPM Wrapper initialized on {self.device}")
    
    def load_model(self, force_reload: bool = False) -> bool:
        """
        Lädt MiniCPM-4.1-8B Model mit RTX 5090 Optimierungen
        """
        if self.model is not None and not force_reload:
            self.logger.info("Model already loaded")
            return True
        
        try:
            self.logger.info(f"Loading {self.config.model_name}...")
            
            # GPU Memory optimieren
            memory_config = self.gpu_manager.optimize_for_model_loading(model_size_gb=8)
            
            if not memory_config["can_load_model"]:
                self.logger.error("Insufficient GPU memory for model loading")
                return False
            
            # Quantization Config für Memory-Effizienz
            quantization_config = None
            if memory_config["use_4bit_loading"]:
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4"
                )
                self.logger.info("Using 4-bit quantization")
            elif memory_config["use_8bit_loading"]:
                quantization_config = BitsAndBytesConfig(load_in_8bit=True)
                self.logger.info("Using 8-bit quantization")
            
            # Model Loading mit optimierter Konfiguration
            model_kwargs = {
                "torch_dtype": self.config.torch_dtype,
                "device_map": self.config.device_map,
                "trust_remote_code": self.config.trust_remote_code,
                "use_flash_attention_2": self.config.use_flash_attention,
            }
            
            if quantization_config:
                model_kwargs["quantization_config"] = quantization_config
            
            # RTX 5090 Memory Mapping
            if self.config.max_memory is None and torch.cuda.is_available():
                # Nutze 90% der verfügbaren VRAM
                available_memory = self.gpu_manager.get_memory_stats()["free_gb"]
                self.config.max_memory = {0: f"{int(available_memory * 0.9)}GB"}
                model_kwargs["max_memory"] = self.config.max_memory
            
            # Lade Model
            self.model = AutoModel.from_pretrained(
                self.config.model_name,
                **model_kwargs
            )
            
            # Lade Processor
            self.processor = AutoProcessor.from_pretrained(
                self.config.model_name,
                trust_remote_code=self.config.trust_remote_code
            )
            
            # Lade Tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.config.model_name,
                trust_remote_code=self.config.trust_remote_code
            )
            
            # Model Optimierungen
            if self.config.gradient_checkpointing:
                self.model.gradient_checkpointing_enable()
            
            # Setze Model in Evaluation Mode
            self.model.eval()
            
            # Memory Stats nach Loading
            memory_stats = self.gpu_manager.get_memory_stats()
            self.logger.info(f"Model loaded successfully!")
            self.logger.info(f"GPU Memory: {memory_stats['allocated_gb']}GB allocated, {memory_stats['free_gb']}GB free")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Model loading failed: {e}")
            return False
    
    def prepare_multimodal_input(self, 
                                chart_images: List[Image.Image],
                                numerical_data: np.ndarray,
                                text_prompt: str) -> Dict[str, torch.Tensor]:
        """
        Bereitet multimodale Eingabe für MiniCPM vor
        """
        try:
            # Text + Images kombinieren
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": text_prompt}
                    ]
                }
            ]
            
            # Füge Chart-Images hinzu
            for i, image in enumerate(chart_images):
                # Resize für MiniCPM optimal resolution
                if image.size != (self.config.image_resolution, self.config.image_resolution):
                    image = image.resize(
                        (self.config.image_resolution, self.config.image_resolution),
                        Image.Resampling.LANCZOS
                    )
                
                messages[0]["content"].append({
                    "type": "image",
                    "image": image
                })
            
            # Füge numerische Daten als Text hinzu
            if numerical_data is not None and len(numerical_data) > 0:
                # Konvertiere wichtigste numerische Features zu Text
                numerical_summary = self._numerical_data_to_text(numerical_data)
                messages[0]["content"].append({
                    "type": "text", 
                    "text": f"Numerical indicators: {numerical_summary}"
                })
            
            # Process mit MiniCPM Processor
            inputs = self.processor(
                messages,
                return_tensors="pt",
                max_length=self.config.max_sequence_length
            )
            
            # Move zu GPU
            if torch.cuda.is_available():
                inputs = {k: v.to(self.device) if isinstance(v, torch.Tensor) else v 
                         for k, v in inputs.items()}
            
            return inputs
            
        except Exception as e:
            self.logger.error(f"Input preparation failed: {e}")
            return {}
    
    def _numerical_data_to_text(self, numerical_data: np.ndarray) -> str:
        """Konvertiert numerische Daten zu Text-Beschreibung"""
        if len(numerical_data) == 0:
            return "No numerical data available"
        
        # Einfache Statistiken
        mean_val = np.mean(numerical_data)
        std_val = np.std(numerical_data)
        min_val = np.min(numerical_data)
        max_val = np.max(numerical_data)
        
        return f"mean={mean_val:.4f}, std={std_val:.4f}, range=[{min_val:.4f}, {max_val:.4f}]"
    
    @torch.no_grad()
    def generate_response(self, inputs: Dict[str, torch.Tensor], 
                         inference_config: Optional[InferenceConfig] = None) -> str:
        """
        Generiert Response mit optimierter GPU-Inference
        """
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        config = inference_config or InferenceConfig()
        
        try:
            start_time = time.time()
            
            # RTX 5090 optimierte Inference
            with torch.cuda.amp.autocast(enabled=self.config.enable_mixed_precision):
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=config.max_new_tokens,
                    temperature=config.temperature,
                    top_p=config.top_p,
                    top_k=config.top_k,
                    do_sample=config.do_sample,
                    num_beams=config.num_beams,
                    repetition_penalty=config.repetition_penalty,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            # Dekodiere Response
            response = self.tokenizer.decode(
                outputs[0][inputs['input_ids'].shape[1]:], 
                skip_special_tokens=True
            )
            
            # Performance Tracking
            inference_time = time.time() - start_time
            self.inference_times.append(inference_time)
            
            memory_stats = self.gpu_manager.get_memory_stats()
            self.memory_usage.append(memory_stats)
            
            self.logger.debug(f"Inference completed in {inference_time:.2f}s")
            
            return response.strip()
            
        except Exception as e:
            self.logger.error(f"Generation failed: {e}")
            return ""
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Gibt Performance-Statistiken zurück"""
        if not self.inference_times:
            return {}
        
        return {
            "avg_inference_time": np.mean(self.inference_times),
            "min_inference_time": np.min(self.inference_times),
            "max_inference_time": np.max(self.inference_times),
            "total_inferences": len(self.inference_times),
            "avg_memory_usage_gb": np.mean([stats["allocated_gb"] for stats in self.memory_usage]),
            "peak_memory_usage_gb": np.max([stats["allocated_gb"] for stats in self.memory_usage])
        }
    
    def clear_cache(self):
        """Bereinigt Model Cache"""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        gc.collect()


class MultimodalAI:
    """
    MiniCPM-4.1-8B Multimodal AI Engine für Trading-Analyse
    UPDATED: Verwendet echte Ollama-Integration statt Mock-Daten
    """
    
    def __init__(self, 
                 model_config: Optional[ModelConfig] = None,
                 resource_manager: Optional[ResourceManager] = None,
                 use_ollama: bool = True):
        
        self.model_config = model_config or ModelConfig()
        self.resource_manager = resource_manager
        self.use_ollama = use_ollama
        self.logger = logging.getLogger(__name__)
        
        # Wähle AI-Backend
        if self.use_ollama:
            # Verwende echte Ollama-Integration
            from .ollama_multimodal_ai import create_ollama_multimodal_ai
            self.ai_backend = create_ollama_multimodal_ai()
            self.logger.info("Using REAL Ollama MiniCPM4.1 integration")
        else:
            # Fallback zu HuggingFace (falls verfügbar)
            self.model_wrapper = MiniCPMModelWrapper(self.model_config, resource_manager)
            self.ai_backend = None
            self.logger.info("Using HuggingFace integration (fallback)")
        
        # Trading-spezifische Prompts
        self.trading_prompts = self._load_trading_prompts()
        
        # Performance Tracking
        self.analysis_count = 0
        self.successful_analyses = 0
    
    def _load_trading_prompts(self) -> Dict[str, str]:
        """Lädt Trading-spezifische Prompts"""
        return {
            "pattern_analysis": """
Analyze this forex chart image and numerical indicators for EUR/USD trading patterns.

Focus on:
1. Visual chart patterns (support/resistance, trends, reversals)
2. Technical indicator signals (RSI, MACD, Bollinger Bands)
3. Entry and exit opportunities
4. Risk assessment

Provide a structured analysis with confidence scores.
""",
            
            "indicator_optimization": """
Based on the chart patterns and current market conditions, suggest optimal parameters for technical indicators.

Consider:
1. Market volatility
2. Trend strength  
3. Time frame characteristics
4. Risk-reward ratios

Provide specific parameter recommendations with reasoning.
""",
            
            "strategy_generation": """
Generate a complete trading strategy based on the visual patterns and numerical indicators shown.

Include:
1. Entry conditions (specific rules)
2. Exit conditions (profit targets and stop losses)
3. Risk management parameters
4. Expected performance characteristics

Format as actionable trading rules.
"""
        }
    
    def load_model(self) -> bool:
        """Lädt MiniCPM Model"""
        return self.model_wrapper.load_model()
    
    def analyze_chart_pattern(self, 
                            chart_image: Image.Image,
                            numerical_indicators: Optional[Dict[str, Any]] = None,
                            market_context: Optional[Dict[str, Any]] = None) -> PatternAnalysis:
        """
        Analysiert Chart-Pattern mit MiniCPM Vision-Language Model
        UPDATED: Verwendet echte AI-Inference über Ollama
        """
        try:
            self.analysis_count += 1
            
            # Verwende echte Ollama-Integration wenn verfügbar
            if self.use_ollama and self.ai_backend:
                analysis = self.ai_backend.analyze_chart_pattern(
                    chart_image=chart_image,
                    numerical_indicators=numerical_indicators,
                    market_context=market_context
                )
                
                if analysis.pattern_type != "analysis_failed":
                    self.successful_analyses += 1
                    self.logger.info(f"REAL AI Pattern analysis completed: {analysis.pattern_type} (confidence: {analysis.confidence_score:.2f})")
                
                return analysis
            
            # Fallback zu HuggingFace-Integration (alter Code)
            else:
                # Bereite Eingabe vor
                numerical_data = self._extract_numerical_array(numerical_indicators) if numerical_indicators else np.array([])
                
                # Erstelle Trading-spezifischen Prompt
                prompt = self.trading_prompts["pattern_analysis"]
                
                if market_context:
                    prompt += f"\nMarket Context: {json.dumps(market_context, indent=2)}"
                
                # Bereite multimodale Eingabe vor
                inputs = self.model_wrapper.prepare_multimodal_input(
                    chart_images=[chart_image],
                    numerical_data=numerical_data,
                    text_prompt=prompt
                )
                
                if not inputs:
                    raise RuntimeError("Failed to prepare model inputs")
                
                # Generiere Analyse
                response = self.model_wrapper.generate_response(inputs)
                
                if not response:
                    raise RuntimeError("Model generated empty response")
                
                # Parse Response zu PatternAnalysis
                analysis = self._parse_pattern_analysis_response(response, chart_image)
                
                self.successful_analyses += 1
                self.logger.info(f"Pattern analysis completed: {analysis.pattern_type} (confidence: {analysis.confidence_score:.2f})")
                
                return analysis
            
        except Exception as e:
            self.logger.error(f"Chart pattern analysis failed: {e}")
            return PatternAnalysis(
                pattern_type="analysis_failed",
                confidence_score=0.0,
                description=f"Analysis failed: {str(e)}"
            )
    
    def optimize_indicators(self, 
                          chart_images: List[Image.Image],
                          current_indicators: Dict[str, Any],
                          market_context: Optional[Dict[str, Any]] = None) -> List[OptimizedParameters]:
        """
        Optimiert Indikator-Parameter basierend auf Chart-Analyse
        """
        try:
            # Bereite numerische Daten vor
            numerical_data = self._extract_numerical_array(current_indicators)
            
            # Erstelle Optimierungs-Prompt
            prompt = self.trading_prompts["indicator_optimization"]
            prompt += f"\nCurrent indicators: {json.dumps(current_indicators, indent=2)}"
            
            if market_context:
                prompt += f"\nMarket context: {json.dumps(market_context, indent=2)}"
            
            # Bereite multimodale Eingabe vor
            inputs = self.model_wrapper.prepare_multimodal_input(
                chart_images=chart_images,
                numerical_data=numerical_data,
                text_prompt=prompt
            )
            
            # Generiere Optimierungsvorschläge
            response = self.model_wrapper.generate_response(inputs)
            
            # Parse Response zu OptimizedParameters
            optimized_params = self._parse_optimization_response(response)
            
            self.logger.info(f"Indicator optimization completed: {len(optimized_params)} parameters optimized")
            
            return optimized_params
            
        except Exception as e:
            self.logger.error(f"Indicator optimization failed: {e}")
            return []
    
    def generate_strategy(self, multimodal_input: MultimodalInput) -> Dict[str, Any]:
        """
        Generiert komplette Trading-Strategie basierend auf multimodaler Analyse
        """
        try:
            if not multimodal_input.validate():
                raise ValueError("Invalid multimodal input")
            
            # Bereite Eingabe vor
            inputs = self.model_wrapper.prepare_multimodal_input(
                chart_images=multimodal_input.chart_images,
                numerical_data=multimodal_input.numerical_data,
                text_prompt=self.trading_prompts["strategy_generation"]
            )
            
            # Generiere Strategie
            response = self.model_wrapper.generate_response(inputs)
            
            # Parse Response zu Trading-Strategie
            strategy = self._parse_strategy_response(response, multimodal_input)
            
            self.logger.info(f"Strategy generation completed: {strategy['strategy_name']}")
            
            return strategy
            
        except Exception as e:
            self.logger.error(f"Strategy generation failed: {e}")
            return {
                "strategy_name": "generation_failed",
                "entry_conditions": [],
                "exit_conditions": [],
                "confidence": 0.0,
                "error": str(e)
            }
    
    def _extract_numerical_array(self, indicators: Dict[str, Any]) -> np.ndarray:
        """Extrahiert numerisches Array aus Indikatoren"""
        features = []
        
        for key, value in indicators.items():
            if isinstance(value, (int, float)):
                features.append(float(value))
            elif isinstance(value, list) and len(value) > 0:
                # Nehme letzte Werte
                if isinstance(value[-1], (int, float)):
                    features.extend([float(v) for v in value[-5:]])  # Letzte 5 Werte
            elif isinstance(value, dict):
                # Für MACD, Bollinger etc.
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, list) and len(sub_value) > 0:
                        if isinstance(sub_value[-1], (int, float)):
                            features.append(float(sub_value[-1]))
        
        return np.array(features, dtype=np.float32)
    
    def _parse_pattern_analysis_response(self, response: str, chart_image: Image.Image) -> PatternAnalysis:
        """Parsed Model-Response zu PatternAnalysis"""
        # Einfaches Parsing (würde in Produktion durch strukturiertes Parsing ersetzt)
        
        # Extrahiere Pattern-Typ
        pattern_type = "unknown"
        if "double top" in response.lower():
            pattern_type = "double_top"
        elif "double bottom" in response.lower():
            pattern_type = "double_bottom"
        elif "head and shoulders" in response.lower():
            pattern_type = "head_and_shoulders"
        elif "triangle" in response.lower():
            pattern_type = "triangle"
        elif "support" in response.lower():
            pattern_type = "support_resistance"
        elif "trend" in response.lower():
            pattern_type = "trend_line"
        
        # Extrahiere Confidence Score
        confidence_score = 0.5  # Default
        if "high confidence" in response.lower():
            confidence_score = 0.8
        elif "medium confidence" in response.lower():
            confidence_score = 0.6
        elif "low confidence" in response.lower():
            confidence_score = 0.3
        
        return PatternAnalysis(
            pattern_type=pattern_type,
            confidence_score=confidence_score,
            description=response[:500],  # Erste 500 Zeichen
            features={"response_length": len(response)}
        )
    
    def _parse_optimization_response(self, response: str) -> List[OptimizedParameters]:
        """Parsed Optimierungs-Response"""
        optimized_params = []
        
        # Einfaches Parsing für häufige Indikatoren
        indicators = ["RSI", "MACD", "SMA", "EMA", "Bollinger"]
        
        for indicator in indicators:
            if indicator.lower() in response.lower():
                # Extrahiere Parameter (vereinfacht)
                if indicator == "RSI":
                    period = 14  # Default, würde aus Response extrahiert
                    if "period" in response.lower():
                        # Vereinfachte Extraktion
                        period = 14  # Placeholder
                    
                    optimized_params.append(OptimizedParameters(
                        indicator_name=indicator,
                        parameters={"period": period},
                        performance_score=0.75
                    ))
        
        return optimized_params
    
    def _parse_strategy_response(self, response: str, multimodal_input: MultimodalInput) -> Dict[str, Any]:
        """Parsed Strategie-Response"""
        return {
            "strategy_name": "AI_Generated_Strategy",
            "entry_conditions": self._extract_conditions(response, "entry"),
            "exit_conditions": self._extract_conditions(response, "exit"),
            "risk_management": {
                "stop_loss": 0.02,
                "take_profit": 0.04
            },
            "confidence": 0.7,
            "analysis_text": response[:1000]
        }
    
    def _extract_conditions(self, response: str, condition_type: str) -> List[str]:
        """Extrahiert Trading-Conditions aus Response"""
        conditions = []
        
        # Einfache Keyword-Extraktion
        if condition_type == "entry":
            if "rsi" in response.lower() and "below" in response.lower():
                conditions.append("RSI < 30")
            if "macd" in response.lower() and "cross" in response.lower():
                conditions.append("MACD crosses above Signal")
        elif condition_type == "exit":
            if "rsi" in response.lower() and "above" in response.lower():
                conditions.append("RSI > 70")
            if "profit" in response.lower():
                conditions.append("Take Profit at 2%")
        
        return conditions if conditions else [f"AI-generated {condition_type} condition"]
    
    def get_model_info(self) -> Dict[str, Any]:
        """Gibt Model-Informationen zurück"""
        return {
            "model_name": self.model_config.model_name,
            "device": str(self.model_wrapper.device),
            "torch_dtype": str(self.model_config.torch_dtype),
            "loaded": self.model_wrapper.model is not None,
            "memory_stats": self.model_wrapper.gpu_manager.get_memory_stats(),
            "performance_stats": self.model_wrapper.get_performance_stats(),
            "analysis_count": self.analysis_count,
            "success_rate": self.successful_analyses / max(1, self.analysis_count)
        }
    
    def cleanup(self):
        """Bereinigt Model und GPU Memory"""
        if self.model_wrapper.model is not None:
            del self.model_wrapper.model
            del self.model_wrapper.processor
            del self.model_wrapper.tokenizer
            
            self.model_wrapper.model = None
            self.model_wrapper.processor = None
            self.model_wrapper.tokenizer = None
        
        self.model_wrapper.clear_cache()
        self.logger.info("Model cleanup completed")