#!/usr/bin/env python3
"""
🚀 Nautilus Performance Benchmark für RTX 5090 + Ryzen 9950X
Basiert auf ChatGPT-Empfehlungen für Tick-Processing-Performance
"""

import time
import numpy as np
import pandas as pd
import torch
import psutil
from pathlib import Path
from typing import Dict, Any
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

class NautilusBenchmark:
    """
    Comprehensive Performance Benchmark für Nautilus Trading System
    Ziel: 1-3 Millionen Ticks/Sekunde (ChatGPT-Benchmark)
    """
    
    def __init__(self):
        self.results = {}
        self.hardware_info = self._detect_hardware()
        
    def _detect_hardware(self) -> Dict[str, Any]:
        """Hardware-Erkennung für Benchmark-Kontext"""
        return {
            "cpu_cores_physical": psutil.cpu_count(logical=False),
            "cpu_cores_logical": psutil.cpu_count(logical=True),
            "memory_gb": psutil.virtual_memory().total // (1024**3),
            "gpu_available": torch.cuda.is_available(),
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "None",
            "gpu_memory_gb": torch.cuda.get_device_properties(0).total_memory // (1024**3) if torch.cuda.is_available() else 0
        }
    
    def generate_mock_tick_data(self, num_ticks: int = 10_000_000) -> pd.DataFrame:
        """
        Generiert Mock-Tick-Daten für Benchmark
        ChatGPT-Empfehlung: 10M Ticks für realistischen Test
        """
        print(f"📊 Generiere {num_ticks:,} Mock-Ticks...")
        
        start_time = time.time()
        
        # Realistische EUR/USD Tick-Daten
        base_price = 1.0850
        timestamps = pd.date_range(
            start=datetime.now() - timedelta(days=1),
            periods=num_ticks,
            freq='100ms'  # 10 Ticks/Sekunde
        )
        
        # Preisbewegung mit Random Walk
        price_changes = np.random.normal(0, 0.00005, num_ticks)  # 0.5 Pip Standardabweichung
        prices = base_price + np.cumsum(price_changes)
        
        # Bid/Ask Spread (1-2 Pips)
        spreads = np.random.uniform(0.00010, 0.00020, num_ticks)
        bids = prices - spreads / 2
        asks = prices + spreads / 2
        
        # Volumen (realistisch)
        volumes = np.random.exponential(1000, num_ticks).astype(int)
        
        df = pd.DataFrame({
            'timestamp': timestamps,
            'bid': bids,
            'ask': asks,
            'price': prices,
            'volume': volumes
        })
        
        generation_time = time.time() - start_time
        print(f"✅ {num_ticks:,} Ticks generiert in {generation_time:.2f}s")
        print(f"   Rate: {num_ticks / generation_time:,.0f} Ticks/Sekunde")
        
        return df
    
    def benchmark_pandas_processing(self, df: pd.DataFrame) -> Dict[str, float]:
        """Benchmark: Pandas Feature Engineering"""
        print("\n📈 Benchmark: Pandas Feature Engineering")
        
        start_time = time.time()
        
        # Feature Engineering (ChatGPT-Beispiel)
        df['spread'] = df['ask'] - df['bid']
        df['mid_price'] = (df['bid'] + df['ask']) / 2
        df['price_change'] = df['price'].diff()
        df['volume_ma'] = df['volume'].rolling(window=10).mean()
        df['price_ma'] = df['price'].rolling(window=20).mean()
        
        # Bollinger Bands
        df['price_std'] = df['price'].rolling(window=20).std()
        df['bb_upper'] = df['price_ma'] + (df['price_std'] * 2)
        df['bb_lower'] = df['price_ma'] - (df['price_std'] * 2)
        
        end_time = time.time()
        duration = end_time - start_time
        ticks_per_second = len(df) / duration
        
        print(f"✅ Pandas Processing: {duration:.2f}s")
        print(f"   Rate: {ticks_per_second:,.0f} Ticks/Sekunde")
        
        return {
            "duration": duration,
            "ticks_per_second": ticks_per_second,
            "memory_usage_mb": df.memory_usage(deep=True).sum() / (1024**2)
        }
    
    def benchmark_polars_processing(self, df: pd.DataFrame) -> Dict[str, float]:
        """Benchmark: Polars High-Performance Processing (ChatGPT-Empfehlung)"""
        print("\n⚡ Benchmark: Polars High-Performance Processing")
        
        try:
            import polars as pl
        except ImportError:
            print("❌ Polars nicht installiert - überspringe Benchmark")
            return {"error": "polars_not_installed"}
        
        # Konvertierung zu Polars
        convert_start = time.time()
        pl_df = pl.from_pandas(df)
        convert_time = time.time() - convert_start
        
        # Feature Engineering mit Polars (viel schneller)
        start_time = time.time()
        
        pl_df = pl_df.with_columns([
            (pl.col("ask") - pl.col("bid")).alias("spread"),
            ((pl.col("bid") + pl.col("ask")) / 2).alias("mid_price"),
            pl.col("price").diff().alias("price_change"),
            pl.col("volume").rolling_mean(window_size=10).alias("volume_ma"),
            pl.col("price").rolling_mean(window_size=20).alias("price_ma"),
            pl.col("price").rolling_std(window_size=20).alias("price_std"),
        ])
        
        # Bollinger Bands
        pl_df = pl_df.with_columns([
            (pl.col("price_ma") + (pl.col("price_std") * 2)).alias("bb_upper"),
            (pl.col("price_ma") - (pl.col("price_std") * 2)).alias("bb_lower"),
        ])
        
        end_time = time.time()
        duration = end_time - start_time
        ticks_per_second = len(pl_df) / duration
        
        print(f"✅ Polars Processing: {duration:.2f}s (Konvertierung: {convert_time:.2f}s)")
        print(f"   Rate: {ticks_per_second:,.0f} Ticks/Sekunde")
        print(f"   Speedup vs Pandas: {self.results.get('pandas', {}).get('ticks_per_second', 1) / ticks_per_second:.1f}x")
        
        return {
            "duration": duration,
            "convert_time": convert_time,
            "ticks_per_second": ticks_per_second,
            "memory_usage_mb": pl_df.estimated_size() / (1024**2)
        }
    
    def benchmark_pytorch_inference(self, df: pd.DataFrame) -> Dict[str, float]:
        """Benchmark: PyTorch GPU-Inferenz auf RTX 5090 (ChatGPT-Empfehlung)"""
        print("\n🧠 Benchmark: PyTorch GPU-Inferenz (RTX 5090)")
        
        if not torch.cuda.is_available():
            print("❌ CUDA nicht verfügbar - überspringe GPU-Benchmark")
            return {"error": "cuda_not_available"}
        
        # Feature-Matrix erstellen
        features = df[['spread', 'price_change', 'volume']].fillna(0).values
        
        # Zu PyTorch Tensor (GPU)
        start_time = time.time()
        x = torch.tensor(features, dtype=torch.float32).to("cuda")
        transfer_time = time.time() - start_time
        
        # Dummy-Modell (ChatGPT-Beispiel)
        model = torch.nn.Sequential(
            torch.nn.Linear(3, 64),
            torch.nn.ReLU(),
            torch.nn.Linear(64, 32),
            torch.nn.ReLU(),
            torch.nn.Linear(32, 3),  # Buy/Hold/Sell
            torch.nn.Softmax(dim=1)
        ).to("cuda")
        
        # Inferenz-Benchmark
        model.# SECURITY: eval() removed - was: eval()
# TODO: Implement safe alternative
        start_inference = time.time()
        
        with torch.no_grad():
            predictions = model(x)
            # Synchronisation für genaue Zeitmessung
            torch.cuda.synchronize()
        
        end_inference = time.time()
        inference_duration = end_inference - start_inference
        inferences_per_second = len(x) / inference_duration
        
        print(f"✅ PyTorch Inferenz: {inference_duration:.2f}s (Transfer: {transfer_time:.2f}s)")
        print(f"   Rate: {inferences_per_second:,.0f} Inferenzen/Sekunde")
        print(f"   GPU Memory: {torch.cuda.memory_allocated() / (1024**3):.1f} GB")
        
        return {
            "inference_duration": inference_duration,
            "transfer_time": transfer_time,
            "inferences_per_second": inferences_per_second,
            "gpu_memory_gb": torch.cuda.memory_allocated() / (1024**3)
        }
    
    def benchmark_memory_usage(self, df: pd.DataFrame) -> Dict[str, float]:
        """Benchmark: Memory-Effizienz bei 192GB RAM"""
        print("\n💾 Benchmark: Memory-Effizienz")
        
        process = psutil.Process()
        memory_before = process.memory_info().rss / (1024**3)  # GB
        
        # Memory-intensive Operation: Multiple DataFrames
        start_time = time.time()
        dataframes = []
        
        for i in range(5):  # 5 Kopien für Memory-Test
            df_copy = df.copy()
            df_copy['synthetic_feature'] = np.random.random(len(df))
            dataframes.append(df_copy)
        
        memory_after = process.memory_info().rss / (1024**3)  # GB
        duration = time.time() - start_time
        
        memory_used = memory_after - memory_before
        
        print(f"✅ Memory Test: {duration:.2f}s")
        print(f"   Memory Used: {memory_used:.1f} GB")
        print(f"   Total Memory: {memory_after:.1f} GB / {self.hardware_info['memory_gb']} GB")
        print(f"   Memory Efficiency: {(memory_used / len(df)) * 1_000_000:.2f} MB/Million Ticks")
        
        # Cleanup
        del dataframes
        
        return {
            "duration": duration,
            "memory_used_gb": memory_used,
            "memory_efficiency_mb_per_million": (memory_used / len(df)) * 1_000_000
        }
    
    def run_full_benchmark(self, num_ticks: int = 5_000_000) -> Dict[str, Any]:
        """Führt vollständigen Performance-Benchmark durch"""
        print("🚀 Nautilus Performance Benchmark")
        print("=" * 60)
        print(f"Hardware: {self.hardware_info['cpu_cores_physical']}C/{self.hardware_info['cpu_cores_logical']}T, "
              f"{self.hardware_info['memory_gb']}GB RAM, {self.hardware_info['gpu_name']}")
        print("=" * 60)
        
        # 1. Mock-Daten generieren
        df = self.generate_mock_tick_data(num_ticks)
        
        # 2. Pandas Benchmark
        self.results['pandas'] = self.benchmark_pandas_processing(df.copy())
        
        # 3. Polars Benchmark
        self.results['polars'] = self.benchmark_polars_processing(df.copy())
        
        # 4. PyTorch GPU Benchmark
        self.results['pytorch'] = self.benchmark_pytorch_inference(df.copy())
        
        # 5. Memory Benchmark
        self.results['memory'] = self.benchmark_memory_usage(df.copy())
        
        # 6. Zusammenfassung
        self._print_summary()
        
        return self.results
    
    def _print_summary(self):
        """Druckt Benchmark-Zusammenfassung"""
        print("\n" + "=" * 60)
        print("📊 BENCHMARK SUMMARY")
        print("=" * 60)
        
        if 'pandas' in self.results:
            pandas_tps = self.results['pandas']['ticks_per_second']
            print(f"📈 Pandas Processing:     {pandas_tps:>10,.0f} Ticks/Sek")
        
        if 'polars' in self.results and 'error' not in self.results['polars']:
            polars_tps = self.results['polars']['ticks_per_second']
            print(f"⚡ Polars Processing:     {polars_tps:>10,.0f} Ticks/Sek")
        
        if 'pytorch' in self.results and 'error' not in self.results['pytorch']:
            pytorch_ips = self.results['pytorch']['inferences_per_second']
            print(f"🧠 PyTorch Inferenz:     {pytorch_ips:>10,.0f} Inferenzen/Sek")
        
        if 'memory' in self.results:
            memory_eff = self.results['memory']['memory_efficiency_mb_per_million']
            print(f"💾 Memory Effizienz:     {memory_eff:>10.1f} MB/Million Ticks")
        
        print("\n🎯 ChatGPT-Ziel: 1-3 Millionen Ticks/Sekunde")
        
        # Performance-Bewertung
        if 'polars' in self.results and 'error' not in self.results['polars']:
            polars_tps = self.results['polars']['ticks_per_second']
            if polars_tps >= 3_000_000:
                print("🏆 EXCELLENT: Über 3M Ticks/Sek erreicht!")
            elif polars_tps >= 1_000_000:
                print("✅ GOOD: ChatGPT-Ziel erreicht (1M+ Ticks/Sek)")
            else:
                print("⚠️ BELOW TARGET: Unter 1M Ticks/Sek")

def main():
    """Hauptfunktion"""
    benchmark = NautilusBenchmark()
    
    # Benchmark mit 5M Ticks (realistisch für Trading)
    results = benchmark.run_full_benchmark(num_ticks=5_000_000)
    
    # Ergebnisse speichern
    import json
    with open("nautilus_benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Ergebnisse gespeichert in: nautilus_benchmark_results.json")

if __name__ == "__main__":
    main()