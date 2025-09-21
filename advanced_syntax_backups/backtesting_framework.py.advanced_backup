#!/usr/bin/env python3
"""
Backtesting Framework für automatische Strategy-Validation
Phase 3 Implementation - Task 14

Features:
- Comprehensive Strategy-Backtesting-Framework
- Multi-Timeframe-Backtesting-Support
- Risk-Metrics und Performance-Analysis
- Monte-Carlo-Simulation für Robustness-Testing
- Walk-Forward-Analysis und Out-of-Sample-Testing
- Strategy-Comparison und Ranking
- Automated-Validation-Pipeline
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
from collections import defaultdict
import asyncio

# Statistical Analysis
try:
    from scipy import stats
    except Exception as e:
        logger.error(f"Error: {e}")
        pass
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

# Plotting
try:
    import matplotlib.pyplot as plt
    except Exception as e:
        logger.error(f"Error: {e}")
        pass
    import seaborn as sns
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False


class OrderType(Enum):
    """Order-Typen"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    """Order-Seiten"""
    BUY = "buy"
    SELL = "sell"


class PositionSide(Enum):
    """Position-Seiten"""
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


@dataclass
class Order:
    """Order-Definition"""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    filled: bool = False
    fill_price: Optional[float] = None
    fill_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "quantity": self.quantity,
            "price": self.price,
            "stop_price": self.stop_price,
            "timestamp": self.timestamp.isoformat(),
            "filled": self.filled,
            "fill_price": self.fill_price,
            "fill_time": self.fill_time.isoformat() if self.fill_time else None
        }


@dataclass
class Trade:
    """Trade-Record"""
    trade_id: str
    symbol: str
    side: PositionSide
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    pnl_percent: float
    commission: float = 0.0
    slippage: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "entry_time": self.entry_time.isoformat(),
            "exit_time": self.exit_time.isoformat(),
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "quantity": self.quantity,
            "pnl": self.pnl,
            "pnl_percent": self.pnl_percent,
            "commission": self.commission,
            "slippage": self.slippage,
            "duration_hours": (self.exit_time - self.entry_time).total_seconds() / 3600
        }


@dataclass
class BacktestResult:
    """Backtest-Result"""
    strategy_name: str
    symbol: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_return: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[Tuple[datetime, float]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_name": self.strategy_name,
            "symbol": self.symbol,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "initial_capital": self.initial_capital,
            "final_capital": self.final_capital,
            "total_return": self.total_return,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "trades": [trade.to_dict() for trade in self.trades],
            "equity_curve": [(dt.isoformat(), value) for dt, value in self.equity_curve],
            "metrics": self.metrics
        }


class TradingStrategy:
    """Base-Class für Trading-Strategien"""
    
    def __init__(self, name: str, parameters: Dict[str, Any] = None):
        self.name = name
        self.parameters = parameters or {}
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generiere Trading-Signale"""
        # Implementierung in Subclasses
        return pd.Series(0, index=data.index)  # 0=Hold, 1=Buy, -1=Sell
    
    def get_position_size(self, signal: int, current_price: float, 
                         current_capital: float) -> float:
        """Berechne Position-Size"""
        if signal == 0:
            return 0.0
        
        # Standard: 10% des Kapitals pro Trade
        risk_per_trade = self.parameters.get("risk_per_trade", 0.1)
        return current_capital * risk_per_trade / current_price


class SimpleMovingAverageStrategy(TradingStrategy):
    """Simple Moving Average Crossover Strategy"""
    
    def __init__(self, fast_period: int = 10, slow_period: int = 20):
        super().__init__("SMA_Crossover", {
            "fast_period": fast_period,
            "slow_period": slow_period
        })
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generiere SMA-Crossover-Signale"""
        
        fast_sma = data['close'].rolling(window=self.parameters['fast_period']).mean()
        slow_sma = data['close'].rolling(window=self.parameters['slow_period']).mean()
        
        signals = pd.Series(0, index=data.index)
        
        # Buy-Signal: Fast SMA kreuzt über Slow SMA
        signals[(fast_sma > slow_sma) & (fast_sma.shift(1) <= slow_sma.shift(1))] = 1
        
        # Sell-Signal: Fast SMA kreuzt unter Slow SMA
        signals[(fast_sma < slow_sma) & (fast_sma.shift(1) >= slow_sma.shift(1))] = -1
        
        return signals


class RSIStrategy(TradingStrategy):
    """RSI-basierte Strategy"""
    
    def __init__(self, rsi_period: int = 14, oversold: float = 30, overbought: float = 70):
        super().__init__("RSI_Strategy", {
            "rsi_period": rsi_period,
            "oversold": oversold,
            "overbought": overbought
        })
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generiere RSI-Signale"""
        
        # RSI-Berechnung
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.parameters['rsi_period']).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.parameters['rsi_period']).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        signals = pd.Series(0, index=data.index)
        
        # Buy-Signal: RSI unter oversold
        signals[rsi < self.parameters['oversold']] = 1
        
        # Sell-Signal: RSI über overbought
        signals[rsi > self.parameters['overbought']] = -1
        
        return signals


class BacktestEngine:
    """Backtesting-Engine"""
    
    def __init__(self, initial_capital: float = 100000, 
                 commission: float = 0.001, slippage: float = 0.0005):
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.logger = logging.getLogger(__name__)
        
        # State
        self.reset()
    
    def reset(self):
        """Reset Engine-State"""
        self.capital = self.initial_capital
        self.position = 0.0  # Aktuelle Position-Size
        self.position_side = PositionSide.FLAT
        self.entry_price = 0.0
        self.entry_time = None
        
        self.trades: List[Trade] = []
        self.orders: List[Order] = []
        self.equity_curve: List[Tuple[datetime, float]] = []
        
        self.trade_counter = 0
        self.order_counter = 0
    
    def run_backtest(self, strategy: TradingStrategy, data: pd.DataFrame) -> BacktestResult:
        """Führe Backtest durch"""
        
        self.reset()
        
        # Generiere Signale
        signals = strategy.generate_signals(data)
        
        # Iteriere durch Daten
        for i, (timestamp, row) in enumerate(data.iterrows()):
            current_price = row['close']
            signal = signals.iloc[i] if i < len(signals) else 0
            
            # Update Equity-Curve
            current_equity = self._calculate_current_equity(current_price)
            self.equity_curve.append((timestamp, current_equity))
            
            # Verarbeite Signal
            if signal != 0:
                self._process_signal(signal, current_price, timestamp, strategy)
        
        # Schließe offene Position am Ende
        if self.position != 0:
            final_price = data['close'].iloc[-1]
            final_timestamp = data.index[-1]
            self._close_position(final_price, final_timestamp)
        
        # Berechne Metriken
        return self._calculate_backtest_result(strategy, data)
    
    def _process_signal(self, signal: int, price: float, timestamp: datetime, 
                       strategy: TradingStrategy):
        """Verarbeite Trading-Signal"""
        
        if signal == 1 and self.position_side != PositionSide.LONG:
            # Buy-Signal
            if self.position_side == PositionSide.SHORT:
                # Schließe Short-Position
                self._close_position(price, timestamp)
            
            # Öffne Long-Position
            position_size = strategy.get_position_size(signal, price, self.capital)
            self._open_position(PositionSide.LONG, position_size, price, timestamp)
            
        elif signal == -1 and self.position_side != PositionSide.SHORT:
            # Sell-Signal
            if self.position_side == PositionSide.LONG:
                # Schließe Long-Position
                self._close_position(price, timestamp)
            
            # Öffne Short-Position (falls erlaubt)
            position_size = strategy.get_position_size(signal, price, self.capital)
            self._open_position(PositionSide.SHORT, position_size, price, timestamp)
    
    def _open_position(self, side: PositionSide, size: float, price: float, timestamp: datetime):
        """Öffne Position"""
        
        if size <= 0:
            return
        
        # Berücksichtige Slippage
        execution_price = price * (1 + self.slippage) if side == PositionSide.LONG else price * (1 - self.slippage)
        
        # Berechne Kosten
        cost = size * execution_price
        commission_cost = cost * self.commission
        
        if cost + commission_cost > self.capital:
            # Nicht genug Kapital
            return
        
        self.position = size
        self.position_side = side
        self.entry_price = execution_price
        self.entry_time = timestamp
        
        # Update Kapital
        if side == PositionSide.LONG:
            self.capital -= (cost + commission_cost)
        else:
            self.capital += (cost - commission_cost)  # Short-Verkauf
    
    def _close_position(self, price: float, timestamp: datetime):
        """Schließe Position"""
        
        if self.position == 0:
            return
        
        # Berücksichtige Slippage
        execution_price = price * (1 - self.slippage) if self.position_side == PositionSide.LONG else price * (1 + self.slippage)
        
        # Berechne PnL
        if self.position_side == PositionSide.LONG:
            pnl = (execution_price - self.entry_price) * self.position
            self.capital += (self.position * execution_price)
        else:
            pnl = (self.entry_price - execution_price) * self.position
            self.capital -= (self.position * execution_price)
        
        # Commission
        commission_cost = self.position * execution_price * self.commission
        pnl -= commission_cost
        self.capital -= commission_cost
        
        # PnL-Prozent
        pnl_percent = pnl / (self.entry_price * self.position) * 100
        
        # Trade-Record erstellen
        trade = Trade(
            trade_id=f"trade_{self.trade_counter}",
            symbol="BTCUSDT",  # Würde normalerweise aus Daten kommen
            side=self.position_side,
            entry_time=self.entry_time,
            exit_time=timestamp,
            entry_price=self.entry_price,
            exit_price=execution_price,
            quantity=self.position,
            pnl=pnl,
            pnl_percent=pnl_percent,
            commission=commission_cost,
            slippage=abs(price - execution_price) * self.position
        )
        
        self.trades.append(trade)
        self.trade_counter += 1
        
        # Reset Position
        self.position = 0.0
        self.position_side = PositionSide.FLAT
        self.entry_price = 0.0
        self.entry_time = None
    
    def _calculate_current_equity(self, current_price: float) -> float:
        """Berechne aktuelles Equity"""
        
        if self.position == 0:
            return self.capital
        
        # Unrealized PnL
        if self.position_side == PositionSide.LONG:
            unrealized_pnl = (current_price - self.entry_price) * self.position
            return self.capital + (self.position * current_price)
        else:
            unrealized_pnl = (self.entry_price - current_price) * self.position
            return self.capital - (self.position * current_price)
    
    def _calculate_backtest_result(self, strategy: TradingStrategy, data: pd.DataFrame) -> BacktestResult:
        """Berechne Backtest-Result"""
        
        # Basic-Metriken
        final_capital = self.equity_curve[-1][1] if self.equity_curve else self.initial_capital
        total_return = (final_capital - self.initial_capital) / self.initial_capital
        
        # Trade-Statistiken
        total_trades = len(self.trades)
        winning_trades = len([t for t in self.trades if t.pnl > 0])
        losing_trades = len([t for t in self.trades if t.pnl < 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Profit-Factor
        gross_profit = sum([t.pnl for t in self.trades if t.pnl > 0])
        gross_loss = abs(sum([t.pnl for t in self.trades if t.pnl < 0]))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Sharpe-Ratio
        returns = self._calculate_returns()
        sharpe_ratio = self._calculate_sharpe_ratio(returns)
        
        # Max-Drawdown
        max_drawdown = self._calculate_max_drawdown()
        
        # Erweiterte Metriken
        metrics = self._calculate_extended_metrics()
        
        return BacktestResult(
            strategy_name=strategy.name,
            symbol="BTCUSDT",
            start_date=data.index[0],
            end_date=data.index[-1],
            initial_capital=self.initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            trades=self.trades,
            equity_curve=self.equity_curve,
            metrics=metrics
        )
    
    def _calculate_returns(self) -> List[float]:
        """Berechne tägliche Returns"""
        
        if len(self.equity_curve) < 2:
            return []
        
        returns = []
        for i in range(1, len(self.equity_curve)):
            prev_equity = self.equity_curve[i-1][1]
            curr_equity = self.equity_curve[i][1]
            
            if prev_equity > 0:
                daily_return = (curr_equity - prev_equity) / prev_equity
                returns.append(daily_return)
        
        return returns
    
    def _calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.02) -> float:
        """Berechne Sharpe-Ratio"""
        
        if not returns or len(returns) < 2:
            return 0.0
        
        returns_array = np.array(returns)
        excess_returns = returns_array - (risk_free_rate / 252)  # Daily risk-free rate
        
        if np.std(excess_returns) == 0:
            return 0.0
        
        return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
    
    def _calculate_max_drawdown(self) -> float:
        """Berechne Maximum-Drawdown"""
        
        if not self.equity_curve:
            return 0.0
        
        equity_values = [eq[1] for eq in self.equity_curve]
        peak = equity_values[0]
        max_dd = 0.0
        
        for value in equity_values:
            if value > peak:
                peak = value
            
            drawdown = (peak - value) / peak if peak > 0 else 0
            max_dd = max(max_dd, drawdown)
        
        return max_dd
    
    def _calculate_extended_metrics(self) -> Dict[str, Any]:
        """Berechne erweiterte Metriken"""
        
        metrics = {}
        
        if self.trades:
            # Trade-Metriken
            pnls = [t.pnl for t in self.trades]
            
            metrics["avg_trade_pnl"] = np.mean(pnls)
            metrics["median_trade_pnl"] = np.median(pnls)
            metrics["std_trade_pnl"] = np.std(pnls)
            metrics["best_trade"] = max(pnls)
            metrics["worst_trade"] = min(pnls)
            
            # Win/Loss-Statistiken
            winning_pnls = [t.pnl for t in self.trades if t.pnl > 0]
            losing_pnls = [t.pnl for t in self.trades if t.pnl < 0]
            
            if winning_pnls:
                metrics["avg_winning_trade"] = np.mean(winning_pnls)
                metrics["largest_winning_trade"] = max(winning_pnls)
            
            if losing_pnls:
                metrics["avg_losing_trade"] = np.mean(losing_pnls)
                metrics["largest_losing_trade"] = min(losing_pnls)
            
            # Trade-Duration
            durations = [(t.exit_time - t.entry_time).total_seconds() / 3600 for t in self.trades]
            metrics["avg_trade_duration_hours"] = np.mean(durations)
            metrics["median_trade_duration_hours"] = np.median(durations)
            
            # Consecutive-Wins/Losses
            consecutive_wins, consecutive_losses = self._calculate_consecutive_trades()
            metrics["max_consecutive_wins"] = consecutive_wins
            metrics["max_consecutive_losses"] = consecutive_losses
        
        # Returns-Metriken
        returns = self._calculate_returns()
        if returns:
            metrics["volatility"] = np.std(returns) * np.sqrt(252)
            
            if SCIPY_AVAILABLE:
                metrics["skewness"] = stats.skew(returns)
                metrics["kurtosis"] = stats.kurtosis(returns)
        
        return metrics
    
    def _calculate_consecutive_trades(self) -> Tuple[int, int]:
        """Berechne maximale consecutive Wins/Losses"""
        
        if not self.trades:
            return 0, 0
        
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0
        
        for trade in self.trades:
            if trade.pnl > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)
        
        return max_wins, max_losses


class BacktestingFramework:
    """
    Comprehensive Backtesting Framework für Strategy-Validation
    
    Features:
    - Multi-Strategy-Backtesting
    - Walk-Forward-Analysis
    - Monte-Carlo-Simulation
    - Out-of-Sample-Testing
    - Strategy-Comparison und Ranking
    - Risk-Metrics und Performance-Analysis
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Framework-Konfiguration
        self.initial_capital = self.config.get("initial_capital", 100000)
        self.commission = self.config.get("commission", 0.001)
        self.slippage = self.config.get("slippage", 0.0005)
        self.enable_monte_carlo = self.config.get("enable_monte_carlo", True)
        self.monte_carlo_runs = self.config.get("monte_carlo_runs", 1000)
        
        # Results
        self.backtest_results: List[BacktestResult] = []
        
        # Output-Directory
        self.results_directory = Path(self.config.get("results_directory", "backtest_results"))
        self.results_directory.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("BacktestingFramework initialized")
    
    async def run_strategy_validation(self, strategies: List[TradingStrategy], 
                                    data: pd.DataFrame) -> List[BacktestResult]:
        """Führe Strategy-Validation durch"""
        
        self.logger.info(f"Running validation for {len(strategies)} strategies")
        
        results = []
        
        for strategy in strategies:
            try:
                # Standard-Backtest
                except Exception as e:
                    logger.error(f"Error: {e}")
                    pass
                result = await self._run_single_backtest(strategy, data)
                results.append(result)
                
                # Walk-Forward-Analysis
                if self.config.get("enable_walk_forward", False):
                    wf_results = await self._run_walk_forward_analysis(strategy, data)
                    results.extend(wf_results)
                
                # Monte-Carlo-Simulation
                if self.enable_monte_carlo:
                    mc_result = await self._run_monte_carlo_simulation(strategy, data)
                    if mc_result:
                        results.append(mc_result)
                
            except Exception as e:
                self.logger.error(f"Error validating strategy {strategy.name}: {e}")
        
        self.backtest_results.extend(results)
        
        return results
    
    async def _run_single_backtest(self, strategy: TradingStrategy, 
                                 data: pd.DataFrame) -> BacktestResult:
        """Führe einzelnen Backtest durch"""
        
        engine = BacktestEngine(
            initial_capital=self.initial_capital,
            commission=self.commission,
            slippage=self.slippage
        )
        
        result = engine.run_backtest(strategy, data)
        
        self.logger.info(f"Backtest completed for {strategy.name}: "
                        f"Return: {result.total_return:.2%}, "
                        f"Sharpe: {result.sharpe_ratio:.2f}, "
                        f"Trades: {result.total_trades}")
        
        return result
    
    async def _run_walk_forward_analysis(self, strategy: TradingStrategy, 
                                       data: pd.DataFrame) -> List[BacktestResult]:
        """Führe Walk-Forward-Analysis durch"""
        
        window_size = self.config.get("walk_forward_window", 252)  # 1 Jahr
        step_size = self.config.get("walk_forward_step", 63)  # 1 Quartal
        
        results = []
        
        for start_idx in range(0, len(data) - window_size, step_size):
            end_idx = start_idx + window_size
            
            if end_idx >= len(data):
                break
            
            window_data = data.iloc[start_idx:end_idx]
            
            engine = BacktestEngine(
                initial_capital=self.initial_capital,
                commission=self.commission,
                slippage=self.slippage
            )
            
            result = engine.run_backtest(strategy, window_data)
            result.strategy_name = f"{strategy.name}_WF_{start_idx}"
            
            results.append(result)
        
        self.logger.info(f"Walk-forward analysis completed for {strategy.name}: {len(results)} windows")
        
        return results
    
    async def _run_monte_carlo_simulation(self, strategy: TradingStrategy, 
                                        data: pd.DataFrame) -> Optional[BacktestResult]:
        """Führe Monte-Carlo-Simulation durch"""
        
        try:
            mc_results = []
            
            except Exception as e:
            
                logger.error(f"Error: {e}")
            
                pass
            
            for run in range(self.monte_carlo_runs):
                # Bootstrapping der Daten
                bootstrapped_data = self._bootstrap_data(data)
                
                engine = BacktestEngine(
                    initial_capital=self.initial_capital,
                    commission=self.commission,
                    slippage=self.slippage
                )
                
                result = engine.run_backtest(strategy, bootstrapped_data)
                mc_results.append(result)
            
            # Aggregiere Monte-Carlo-Ergebnisse
            aggregated_result = self._aggregate_monte_carlo_results(strategy, mc_results)
            
            self.logger.info(f"Monte Carlo simulation completed for {strategy.name}: "
                           f"{self.monte_carlo_runs} runs")
            
            return aggregated_result
            
        except Exception as e:
            self.logger.error(f"Monte Carlo simulation failed for {strategy.name}: {e}")
            return None
    
    def _bootstrap_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Bootstrap Market-Data für Monte-Carlo"""
        
        # Einfaches Block-Bootstrap
        block_size = 20  # 20-Tage-Blöcke
        num_blocks = len(data) // block_size
        
        bootstrapped_indices = []
        
        for _ in range(num_blocks):
            start_idx = np.random.randint(0, len(data) - block_size)
            block_indices = list(range(start_idx, start_idx + block_size))
            bootstrapped_indices.extend(block_indices)
        
        # Fülle auf ursprüngliche Länge auf
        while len(bootstrapped_indices) < len(data):
            bootstrapped_indices.append(np.random.randint(0, len(data)))
        
        bootstrapped_indices = bootstrapped_indices[:len(data)]
        
        return data.iloc[bootstrapped_indices].reset_index(drop=True)
    
    def _aggregate_monte_carlo_results(self, strategy: TradingStrategy, 
                                     results: List[BacktestResult]) -> BacktestResult:
        """Aggregiere Monte-Carlo-Ergebnisse"""
        
        # Sammle Metriken
        returns = [r.total_return for r in results]
        sharpe_ratios = [r.sharpe_ratio for r in results]
        max_drawdowns = [r.max_drawdown for r in results]
        win_rates = [r.win_rate for r in results]
        
        # Berechne Statistiken
        mc_metrics = {
            "monte_carlo_runs": len(results),
            "return_mean": np.mean(returns),
            "return_std": np.std(returns),
            "return_percentiles": {
                "5th": np.percentile(returns, 5),
                "25th": np.percentile(returns, 25),
                "50th": np.percentile(returns, 50),
                "75th": np.percentile(returns, 75),
                "95th": np.percentile(returns, 95)
            },
            "sharpe_mean": np.mean(sharpe_ratios),
            "sharpe_std": np.std(sharpe_ratios),
            "max_drawdown_mean": np.mean(max_drawdowns),
            "max_drawdown_worst": max(max_drawdowns),
            "win_rate_mean": np.mean(win_rates),
            "positive_return_probability": sum(1 for r in returns if r > 0) / len(returns)
        }
        
        # Erstelle aggregiertes Result
        median_result = results[np.argmin([abs(r.total_return - mc_metrics["return_mean"]) for r in results])]
        
        aggregated_result = BacktestResult(
            strategy_name=f"{strategy.name}_MonteCarlo",
            symbol=median_result.symbol,
            start_date=median_result.start_date,
            end_date=median_result.end_date,
            initial_capital=median_result.initial_capital,
            final_capital=median_result.initial_capital * (1 + mc_metrics["return_mean"]),
            total_return=mc_metrics["return_mean"],
            total_trades=int(np.mean([r.total_trades for r in results])),
            winning_trades=int(np.mean([r.winning_trades for r in results])),
            losing_trades=int(np.mean([r.losing_trades for r in results])),
            win_rate=mc_metrics["win_rate_mean"],
            profit_factor=np.mean([r.profit_factor for r in results if r.profit_factor != float('inf')]),
            sharpe_ratio=mc_metrics["sharpe_mean"],
            max_drawdown=mc_metrics["max_drawdown_mean"],
            trades=[],  # Keine individuellen Trades für MC-Aggregat
            equity_curve=[],
            metrics=mc_metrics
        )
        
        return aggregated_result
    
    def compare_strategies(self, results: List[BacktestResult]) -> Dict[str, Any]:
        """Vergleiche Strategien"""
        
        if not results:
            return {"error": "No results to compare"}
        
        # Ranking-Metriken
        ranking_metrics = {
            "total_return": {},
            "sharpe_ratio": {},
            "max_drawdown": {},
            "win_rate": {},
            "profit_factor": {},
            "composite_score": {}
        }
        
        # Sammle Metriken
        for result in results:
            name = result.strategy_name
            
            ranking_metrics["total_return"][name] = result.total_return
            ranking_metrics["sharpe_ratio"][name] = result.sharpe_ratio
            ranking_metrics["max_drawdown"][name] = result.max_drawdown
            ranking_metrics["win_rate"][name] = result.win_rate
            ranking_metrics["profit_factor"][name] = result.profit_factor if result.profit_factor != float('inf') else 10.0
        
        # Berechne Composite-Score
        for name in ranking_metrics["total_return"].keys():
            # Normalisierte Scores (0-1)
            return_score = max(0, ranking_metrics["total_return"][name])
            sharpe_score = max(0, ranking_metrics["sharpe_ratio"][name] / 3.0)  # Normalisiere auf 3.0
            drawdown_score = max(0, 1 - ranking_metrics["max_drawdown"][name])  # Niedrigerer DD = besser
            winrate_score = ranking_metrics["win_rate"][name]
            pf_score = min(1.0, ranking_metrics["profit_factor"][name] / 5.0)  # Normalisiere auf 5.0
            
            # Gewichteter Composite-Score
            composite = (
                return_score * 0.3 +
                sharpe_score * 0.25 +
                drawdown_score * 0.2 +
                winrate_score * 0.15 +
                pf_score * 0.1
            )
            
            ranking_metrics["composite_score"][name] = composite
        
        # Erstelle Rankings
        rankings = {}
        for metric, values in ranking_metrics.items():
            if metric == "max_drawdown":
                # Niedrigerer Drawdown = besseres Ranking
                sorted_items = sorted(values.items(), key=lambda x: x[1])
            else:
                # Höhere Werte = besseres Ranking
                sorted_items = sorted(values.items(), key=lambda x: x[1], reverse=True)
            
            rankings[metric] = [{"strategy": name, "value": value, "rank": i+1} 
                              for i, (name, value) in enumerate(sorted_items)]
        
        # Best-Strategy basierend auf Composite-Score
        best_strategy = rankings["composite_score"][0]["strategy"]
        
        return {
            "timestamp": datetime.now().isoformat(),
            "strategies_compared": len(results),
            "best_strategy": best_strategy,
            "rankings": rankings,
            "summary_statistics": {
                "avg_return": np.mean(list(ranking_metrics["total_return"].values())),
                "avg_sharpe": np.mean(list(ranking_metrics["sharpe_ratio"].values())),
                "avg_drawdown": np.mean(list(ranking_metrics["max_drawdown"].values())),
                "avg_winrate": np.mean(list(ranking_metrics["win_rate"].values()))
            }
        }
    
    def generate_backtest_report(self) -> Dict[str, Any]:
        """Generiere Backtest-Report"""
        
        try:
            if not self.backtest_results:
                except Exception as e:
                    logger.error(f"Error: {e}")
                    pass
                return {"error": "No backtest results available"}
            
            # Statistiken
            total_backtests = len(self.backtest_results)
            successful_backtests = sum(1 for r in self.backtest_results if r.total_trades > 0)
            
            # Performance-Metriken
            returns = [r.total_return for r in self.backtest_results]
            sharpe_ratios = [r.sharpe_ratio for r in self.backtest_results]
            max_drawdowns = [r.max_drawdown for r in self.backtest_results]
            
            # Strategy-Comparison
            comparison = self.compare_strategies(self.backtest_results)
            
            # Detailed-Results
            detailed_results = []
            for result in self.backtest_results:
                detailed_results.append({
                    "strategy_name": result.strategy_name,
                    "total_return": result.total_return,
                    "sharpe_ratio": result.sharpe_ratio,
                    "max_drawdown": result.max_drawdown,
                    "win_rate": result.win_rate,
                    "total_trades": result.total_trades,
                    "profit_factor": result.profit_factor,
                    "start_date": result.start_date.isoformat(),
                    "end_date": result.end_date.isoformat()
                })
            
            report = {
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total_backtests": total_backtests,
                    "successful_backtests": successful_backtests,
                    "success_rate": successful_backtests / total_backtests if total_backtests > 0 else 0
                },
                "performance_statistics": {
                    "avg_return": np.mean(returns) if returns else 0,
                    "median_return": np.median(returns) if returns else 0,
                    "std_return": np.std(returns) if returns else 0,
                    "best_return": max(returns) if returns else 0,
                    "worst_return": min(returns) if returns else 0,
                    "avg_sharpe": np.mean(sharpe_ratios) if sharpe_ratios else 0,
                    "avg_max_drawdown": np.mean(max_drawdowns) if max_drawdowns else 0
                },
                "strategy_comparison": comparison,
                "detailed_results": detailed_results
            }
            
            # Report speichern
            report_file = self.results_directory / f"backtest_report_{int(time.time())}.json"
            
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            self.logger.info(f"Backtest report generated: {report_file}")
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating backtest report: {e}")
            return {"error": str(e)}
    
    def generate_performance_charts(self, results: List[BacktestResult]) -> List[str]:
        """Generiere Performance-Charts"""
        
        if not PLOTTING_AVAILABLE or not results:
            return []
        
        chart_files = []
        
        try:
            # Equity-Curves-Chart
            except Exception as e:
                logger.error(f"Error: {e}")
                pass
            equity_chart = self._create_equity_curves_chart(results)
            if equity_chart:
                chart_files.append(str(equity_chart))
            
            # Returns-Distribution-Chart
            returns_chart = self._create_returns_distribution_chart(results)
            if returns_chart:
                chart_files.append(str(returns_chart))
            
            # Risk-Return-Scatter
            risk_return_chart = self._create_risk_return_scatter(results)
            if risk_return_chart:
                chart_files.append(str(risk_return_chart))
            
            # Drawdown-Chart
            drawdown_chart = self._create_drawdown_chart(results)
            if drawdown_chart:
                chart_files.append(str(drawdown_chart))
            
        except Exception as e:
            self.logger.error(f"Error generating performance charts: {e}")
        
        return chart_files
    
    def _create_equity_curves_chart(self, results: List[BacktestResult]) -> Optional[Path]:
        """Erstelle Equity-Curves-Chart"""
        
        try:
            fig, ax = plt.subplots(figsize=(12, 8))
            
            except Exception as e:
            
                logger.error(f"Error: {e}")
            
                pass
            
            colors = ['blue', 'green', 'red', 'orange', 'purple', 'brown']
            
            for i, result in enumerate(results[:6]):  # Max 6 Strategien
                if not result.equity_curve:
                    continue
                
                timestamps = [eq[0] for eq in result.equity_curve]
                values = [eq[1] for eq in result.equity_curve]
                
                color = colors[i % len(colors)]
                ax.plot(timestamps, values, label=result.strategy_name, 
                       color=color, linewidth=2, alpha=0.8)
            
            ax.set_title('Strategy Equity Curves Comparison')
            ax.set_xlabel('Date')
            ax.set_ylabel('Portfolio Value')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            # Formatiere X-Achse
            import matplotlib.dates as mdates
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.tick_params(axis='x', rotation=45)
            
            plt.tight_layout()
            
            chart_file = self.results_directory / f"equity_curves_{int(time.time())}.png"
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            return chart_file
            
        except Exception as e:
            self.logger.error(f"Error creating equity curves chart: {e}")
            return None
    
    def _create_returns_distribution_chart(self, results: List[BacktestResult]) -> Optional[Path]:
        """Erstelle Returns-Distribution-Chart"""
        
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            except Exception as e:
            
                logger.error(f"Error: {e}")
            
                pass
            
            returns = [r.total_return * 100 for r in results]  # Convert to percentage
            
            ax.hist(returns, bins=20, alpha=0.7, color='blue', edgecolor='black')
            ax.axvline(np.mean(returns), color='red', linestyle='--', 
                      label=f'Mean: {np.mean(returns):.1f}%')
            ax.axvline(np.median(returns), color='green', linestyle='--', 
                      label=f'Median: {np.median(returns):.1f}%')
            
            ax.set_title('Strategy Returns Distribution')
            ax.set_xlabel('Total Return (%)')
            ax.set_ylabel('Frequency')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            chart_file = self.results_directory / f"returns_distribution_{int(time.time())}.png"
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            return chart_file
            
        except Exception as e:
            self.logger.error(f"Error creating returns distribution chart: {e}")
            return None
    
    def _create_risk_return_scatter(self, results: List[BacktestResult]) -> Optional[Path]:
        """Erstelle Risk-Return-Scatter-Plot"""
        
        try:
            fig, ax = plt.subplots(figsize=(10, 8))
            
            except Exception as e:
            
                logger.error(f"Error: {e}")
            
                pass
            
            returns = [r.total_return * 100 for r in results]
            risks = [r.max_drawdown * 100 for r in results]
            sharpe_ratios = [r.sharpe_ratio for r in results]
            
            # Scatter mit Sharpe-Ratio als Farbe
            scatter = ax.scatter(risks, returns, c=sharpe_ratios, 
                               cmap='viridis', s=100, alpha=0.7)
            
            # Annotate Strategien
            for i, result in enumerate(results):
                ax.annotate(result.strategy_name[:10], 
                          (risks[i], returns[i]), 
                          xytext=(5, 5), textcoords='offset points',
                          fontsize=8, alpha=0.8)
            
            ax.set_title('Risk-Return Analysis')
            ax.set_xlabel('Maximum Drawdown (%)')
            ax.set_ylabel('Total Return (%)')
            ax.grid(True, alpha=0.3)
            
            # Colorbar für Sharpe-Ratio
            cbar = plt.colorbar(scatter, ax=ax)
            cbar.set_label('Sharpe Ratio')
            
            plt.tight_layout()
            
            chart_file = self.results_directory / f"risk_return_scatter_{int(time.time())}.png"
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            return chart_file
            
        except Exception as e:
            self.logger.error(f"Error creating risk-return scatter: {e}")
            return None
    
    def _create_drawdown_chart(self, results: List[BacktestResult]) -> Optional[Path]:
        """Erstelle Drawdown-Chart"""
        
        try:
            fig, ax = plt.subplots(figsize=(12, 6))
            
            except Exception as e:
            
                logger.error(f"Error: {e}")
            
                pass
            
            # Zeige Drawdown für beste Strategy
            if not results:
                return None
            
            best_result = max(results, key=lambda r: r.sharpe_ratio)
            
            if not best_result.equity_curve:
                return None
            
            # Berechne Drawdown-Curve
            equity_values = [eq[1] for eq in best_result.equity_curve]
            timestamps = [eq[0] for eq in best_result.equity_curve]
            
            peak = equity_values[0]
            drawdowns = []
            
            for value in equity_values:
                if value > peak:
                    peak = value
                
                drawdown = (peak - value) / peak * 100 if peak > 0 else 0
                drawdowns.append(-drawdown)  # Negative für bessere Visualisierung
            
            ax.fill_between(timestamps, drawdowns, 0, alpha=0.3, color='red', label='Drawdown')
            ax.plot(timestamps, drawdowns, color='red', linewidth=1)
            
            ax.set_title(f'Drawdown Analysis - {best_result.strategy_name}')
            ax.set_xlabel('Date')
            ax.set_ylabel('Drawdown (%)')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            # Formatiere X-Achse
            import matplotlib.dates as mdates
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.tick_params(axis='x', rotation=45)
            
            plt.tight_layout()
            
            chart_file = self.results_directory / f"drawdown_analysis_{int(time.time())}.png"
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            return chart_file
            
        except Exception as e:
            self.logger.error(f"Error creating drawdown chart: {e}")
            return None


# Utility-Funktionen
def create_sample_market_data(days: int = 252, start_price: float = 100.0) -> pd.DataFrame:
    """Erstelle Sample-Market-Data für Testing"""
    
    dates = pd.date_range(start='2023-01-01', periods=days, freq='D')
    
    # Random-Walk mit Trend
    returns = np.random.normal(0.0005, 0.02, days)  # 0.05% daily return, 2% volatility
    prices = [start_price]
    
    for ret in returns[1:]:
        new_price = prices[-1] * (1 + ret)
        prices.append(new_price)
    
    # OHLC-Daten generieren
    data = []
    for i, (date, close) in enumerate(zip(dates, prices)):
        # Simuliere Intraday-Bewegungen
        high = close * (1 + abs(np.random.normal(0, 0.01)))
        low = close * (1 - abs(np.random.normal(0, 0.01)))
        open_price = prices[i-1] if i > 0 else close
        volume = np.random.uniform(1000000, 5000000)
        
        data.append({
            'open': open_price,
            'high': max(open_price, high, close),
            'low': min(open_price, low, close),
            'close': close,
            'volume': volume
        })
    
    df = pd.DataFrame(data, index=dates)
    return df


async def run_backtesting_validation_suite(config: Optional[Dict] = None) -> Dict[str, Any]:
    """Führe komplette Backtesting-Validation-Suite aus"""
    
    framework = BacktestingFramework(config)
    
    # Erstelle Sample-Daten
    sample_data = create_sample_market_data(days=500)
    
    # Erstelle Test-Strategien
    strategies = [
        SimpleMovingAverageStrategy(fast_period=10, slow_period=20),
        SimpleMovingAverageStrategy(fast_period=5, slow_period=15),
        RSIStrategy(rsi_period=14, oversold=30, overbought=70),
        RSIStrategy(rsi_period=21, oversold=25, overbought=75)
    ]
    
    # Führe Validation durch
    results = await framework.run_strategy_validation(strategies, sample_data)
    
    # Generiere Report
    report = framework.generate_backtest_report()
    
    # Generiere Charts
    charts = framework.generate_performance_charts(results)
    
    return {
        "backtest_results": [result.to_dict() for result in results],
        "report": report,
        "charts": charts
    }