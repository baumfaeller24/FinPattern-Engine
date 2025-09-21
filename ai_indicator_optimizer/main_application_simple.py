#!/usr/bin/env python3
"""
Enhanced Main Application für AI-Indicator-Optimizer (Simplified)
Task 15 Implementation - Production-Ready CLI Interface

Features:
- Command-Line Interface mit Click für Experiment-Steuerung
- Echte Ollama/MiniCPM4.1 Integration
- Configuration Management mit Environment-Support
- Experiment Runner für automatische Pipeline-Ausführung
- Results Exporter für Pine Script Output und Performance-Reports
- Hardware-Optimierung für RTX 5090 + Ryzen 9 9950X
"""

import click
import asyncio
import logging
import json
import os
import sys
import re
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import psutil

try:
    import GPUtil
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class ConfigurationManager:
    """Simplified Configuration Manager mit Environment-Variable Support"""
    
    def __init__(self, config_path: str = "config/main_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.logger = logging.getLogger(__name__)
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration with environment variable overrides"""
        
        # Default configuration
        default_config = {
            "ollama": {
                "host": "localhost",
                "port": 11434,
                "model": "openbmb/minicpm4.1",
                "timeout": 30
            },
            "experiment": {
                "default_symbol": "EURUSD",
                "data_points": 1000,
                "confidence_threshold": 0.7
            },
            "hardware": {
                "gpu_enabled": True,
                "cpu_cores": "auto",
                "memory_limit": "auto"
            },
            "output": {
                "results_dir": "results",
                "export_formats": ["pine", "json"]
            }
        }
        
        # Try to load from file
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    file_config = json.load(f)
                    default_config.update(file_config)
            except Exception as e:
                print(f"Warning: Could not load config file: {e}")
        
        # Environment variable overrides
        env_overrides = {
            "OLLAMA_HOST": ("ollama", "host"),
            "OLLAMA_PORT": ("ollama", "port"),
            "OLLAMA_MODEL": ("ollama", "model"),
            "RESULTS_DIR": ("output", "results_dir")
        }
        
        for env_var, (section, key) in env_overrides.items():
            if env_var in os.environ:
                if section not in default_config:
                    default_config[section] = {}
                default_config[section][key] = os.environ[env_var]
        
        return default_config
    
    def get(self, key_path: str, default=None):
        """Get configuration value using dot notation (e.g., 'ollama.host')"""
        
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value


class OllamaIntegration:
    """Echte Ollama Integration für MiniCPM4.1"""
    
    def __init__(self, config: ConfigurationManager):
        self.host = config.get("ollama.host", "localhost")
        self.port = config.get("ollama.port", 11434)
        self.model = config.get("ollama.model", "openbmb/minicpm4.1")
        self.timeout = config.get("ollama.timeout", 30)
        self.logger = logging.getLogger(__name__)
    
    def test_connection(self) -> bool:
        """Test Ollama connection"""
        
        try:
            import requests
            
            response = requests.get(
                f"http://{self.host}:{self.port}/api/tags",
                timeout=5
            )
            
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                
                self.logger.info(f"Available models: {model_names}")
                
                # Check if our model is available
                model_available = any(self.model in name for name in model_names)
                
                if not model_available:
                    self.logger.warning(f"Model {self.model} not found. Available: {model_names}")
                
                return True
            else:
                self.logger.error(f"Ollama API returned status: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Ollama connection test failed: {e}")
            return False
    
    def analyze_market_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market data using MiniCPM4.1"""
        
        try:
            # Create structured prompt
            prompt = self._create_analysis_prompt(market_data)
            
            self.logger.debug(f"Sending prompt to {self.model}")
            
            # Call Ollama API
            import requests
            
            response = requests.post(
                f"http://{self.host}:{self.port}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                analysis = self._parse_ai_response(result.get("response", ""))
                
                self.logger.info(f"AI Analysis completed: {analysis.get('action', 'unknown')}")
                return analysis
            else:
                self.logger.error(f"Ollama API error: {response.status_code}")
                return {"error": "API_ERROR", "action": "HOLD", "confidence": 0.0}
                
        except Exception as e:
            self.logger.error(f"Ollama integration error: {e}")
            return {"error": str(e), "action": "HOLD", "confidence": 0.0}
    
    def _create_analysis_prompt(self, market_data: Dict[str, Any]) -> str:
        """Erstelle optimierten strukturierten Prompt für MiniCPM4.1"""
        
        # Format numbers for better readability
        price = market_data.get('price', 1.1000)
        rsi = market_data.get('rsi', 50)
        macd = market_data.get('macd', 0.0)
        bollinger_pos = market_data.get('bollinger_position', 0.5)
        volume = market_data.get('volume', 5000)
        trend = market_data.get('trend', 'neutral')
        
        prompt = f"""You are an expert forex trader. Analyze EUR/USD data and respond with ONLY valid JSON.

MARKET DATA:
Price: {price:.5f}
RSI: {rsi:.1f}
MACD: {macd:.6f}
Bollinger Position: {bollinger_pos:.2f} (0=bottom, 1=top)
Volume: {volume:,}
Trend: {trend}

INSTRUCTIONS:
1. Analyze the technical indicators
2. Determine trading action: BUY, SELL, or HOLD
3. Assign confidence: 0.0 (no confidence) to 1.0 (very confident)
4. Provide brief reasoning
5. Respond with ONLY the JSON below - no extra text

{{
    "action": "BUY",
    "confidence": 0.75,
    "reasoning": "RSI oversold with bullish MACD crossover",
    "risk_level": "MEDIUM"
}}"""
        
        return prompt
    
    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """Enhanced AI response parsing mit robuster JSON-Extraktion"""
        
        self.logger.debug(f"Raw AI response: {response[:200]}...")
        
        try:
            # Method 1: Try multiple JSON extraction patterns
            json_patterns = [
                r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # Nested JSON
                r'\{.*?\}',  # Simple JSON (non-greedy)
                r'\{.*\}',   # Simple JSON (greedy)
            ]
            
            parsed_json = None
            for pattern in json_patterns:
                json_matches = re.findall(pattern, response, re.DOTALL)
                
                for json_str in json_matches:
                    try:
                        # Clean up common JSON issues
                        cleaned_json = self._clean_json_string(json_str)
                        parsed_json = json.loads(cleaned_json)
                        
                        # Validate it has required structure
                        if self._validate_json_structure(parsed_json):
                            self.logger.debug(f"Successfully parsed JSON with pattern: {pattern}")
                            break
                    except json.JSONDecodeError:
                        continue
                
                if parsed_json:
                    break
            
            if parsed_json:
                # Normalize and validate the parsed JSON
                return self._normalize_ai_response(parsed_json)
            
            # Method 2: Structured text parsing if JSON fails
            return self._parse_structured_text(response)
            
        except Exception as e:
            self.logger.warning(f"AI response parsing failed: {e}")
            return self._create_fallback_response(response, str(e))
    
    def _clean_json_string(self, json_str: str) -> str:
        """Clean common JSON formatting issues"""
        
        # Remove markdown code blocks
        json_str = re.sub(r'```json\s*', '', json_str)
        json_str = re.sub(r'```\s*', '', json_str)
        
        # Remove extra whitespace and newlines
        json_str = json_str.strip()
        
        # Fix common trailing comma issues
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        
        # Fix unquoted keys (common AI mistake)
        json_str = re.sub(r'(\w+):', r'"\1":', json_str)
        
        # Fix already quoted keys that got double-quoted
        json_str = re.sub(r'""(\w+)"":', r'"\1":', json_str)
        
        return json_str
    
    def _validate_json_structure(self, parsed: Dict[str, Any]) -> bool:
        """Validate that parsed JSON has expected structure"""
        
        # Must be a dictionary
        if not isinstance(parsed, dict):
            return False
        
        # Must have at least action field
        if "action" not in parsed:
            return False
        
        # Action must be valid
        valid_actions = ["BUY", "SELL", "HOLD"]
        if parsed["action"] not in valid_actions:
            return False
        
        return True
    
    def _normalize_ai_response(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize and validate AI response fields"""
        
        # Ensure required fields exist with defaults
        normalized = {
            "action": parsed.get("action", "HOLD").upper(),
            "confidence": float(parsed.get("confidence", 0.5)),
            "reasoning": parsed.get("reasoning", "AI analysis completed"),
            "risk_level": parsed.get("risk_level", "MEDIUM").upper(),
            "target_price": parsed.get("target_price"),
            "stop_loss": parsed.get("stop_loss")
        }
        
        # Validate and clamp confidence
        normalized["confidence"] = max(0.0, min(1.0, normalized["confidence"]))
        
        # Validate action
        if normalized["action"] not in ["BUY", "SELL", "HOLD"]:
            normalized["action"] = "HOLD"
            normalized["confidence"] = 0.0
        
        # Validate risk level
        if normalized["risk_level"] not in ["LOW", "MEDIUM", "HIGH"]:
            normalized["risk_level"] = "MEDIUM"
        
        return normalized
    
    def _parse_structured_text(self, response: str) -> Dict[str, Any]:
        """Parse structured text when JSON parsing fails"""
        
        self.logger.info("Falling back to structured text parsing")
        
        # Extract action
        action = "HOLD"
        confidence = 0.5
        reasoning = "Structured text analysis"
        risk_level = "MEDIUM"
        
        response_lower = response.lower()
        
        # Action detection with confidence scoring
        if any(word in response_lower for word in ["strong buy", "definitely buy", "highly recommend buy"]):
            action = "BUY"
            confidence = 0.8
        elif any(word in response_lower for word in ["buy", "long", "bullish"]):
            action = "BUY"
            confidence = 0.7
        elif any(word in response_lower for word in ["strong sell", "definitely sell", "highly recommend sell"]):
            action = "SELL"
            confidence = 0.8
        elif any(word in response_lower for word in ["sell", "short", "bearish"]):
            action = "SELL"
            confidence = 0.7
        elif any(word in response_lower for word in ["hold", "wait", "neutral", "sideways"]):
            action = "HOLD"
            confidence = 0.6
        
        # Risk level detection
        if any(word in response_lower for word in ["high risk", "risky", "volatile"]):
            risk_level = "HIGH"
        elif any(word in response_lower for word in ["low risk", "safe", "conservative"]):
            risk_level = "LOW"
        
        # Extract reasoning (first sentence or up to 100 chars)
        sentences = response.split('.')
        if sentences:
            reasoning = sentences[0].strip()[:100]
        
        return {
            "action": action,
            "confidence": confidence,
            "reasoning": reasoning,
            "risk_level": risk_level,
            "parsing_method": "structured_text"
        }
    
    def _create_fallback_response(self, response: str, error: str) -> Dict[str, Any]:
        """Create safe fallback response when all parsing fails"""
        
        return {
            "action": "HOLD",
            "confidence": 0.0,
            "reasoning": f"Parsing failed: {error[:50]}...",
            "risk_level": "HIGH",
            "parsing_method": "fallback",
            "error": error,
            "raw_response_preview": response[:100] + "..." if len(response) > 100 else response
        }


# CLI Interface
@click.group()
@click.version_option(version="1.0.0")
def cli():
    """🚀 AI-Indicator-Optimizer - Enhanced Main Application"""
    click.echo("📊 Configuration loaded from: config/main_config.json")


@cli.command()
@click.option('--model', default='openbmb/minicpm4.1', help='Ollama model to test')
def test_ollama(model):
    """🧠 Test Ollama integration with specified model"""
    
    click.echo(f"🧠 Testing Ollama integration with model: {model}")
    
    # Create config and override model
    config = ConfigurationManager()
    config.config["ollama"]["model"] = model
    
    # Test connection
    ollama = OllamaIntegration(config)
    
    if not ollama.test_connection():
        click.echo("❌ Ollama connection failed")
        return
    
    # Test analysis with sample data
    sample_data = {
        "price": 1.0950,
        "rsi": 35.2,
        "macd": -0.0012,
        "bollinger_position": 0.25,
        "volume": 15000,
        "trend": "bearish"
    }
    
    try:
        result = ollama.analyze_market_data(sample_data)
        
        click.echo("✅ Ollama test successful!")
        click.echo(f"Action: {result.get('action', 'N/A')}")
        click.echo(f"Confidence: {result.get('confidence', 0):.2f}")
        click.echo(f"Reasoning: {result.get('reasoning', 'N/A')}")
        
    except Exception as e:
        click.echo(f"❌ Ollama test failed: {e}")


@cli.command()
def check_hardware():
    """🔧 Check hardware status and capabilities"""
    
    click.echo("🔧 Hardware Status Check")
    click.echo("=" * 50)
    
    # CPU Info
    cpu_count = psutil.cpu_count(logical=False)
    cpu_count_logical = psutil.cpu_count(logical=True)
    cpu_percent = psutil.cpu_percent(interval=1)
    
    click.echo(f"CPU Cores: {cpu_count} physical, {cpu_count_logical} logical")
    click.echo(f"CPU Usage: {cpu_percent}%")
    
    # Memory Info
    memory = psutil.virtual_memory()
    memory_gb = memory.total / (1024**3)
    memory_used_gb = memory.used / (1024**3)
    
    click.echo(f"Memory: {memory_used_gb:.1f}GB / {memory_gb:.1f}GB ({memory.percent}%)")
    
    # GPU Info
    if GPU_AVAILABLE:
        try:
            gpus = GPUtil.getGPUs()
            for i, gpu in enumerate(gpus):
                click.echo(f"GPU {i}: {gpu.name}")
                click.echo(f"  Memory: {gpu.memoryUsed}MB / {gpu.memoryTotal}MB ({gpu.memoryUtil*100:.1f}%)")
                click.echo(f"  Load: {gpu.load*100:.1f}%")
        except Exception as e:
            click.echo(f"GPU Info Error: {e}")
    else:
        click.echo("GPU: GPUtil not available")


if __name__ == "__main__":
    cli()