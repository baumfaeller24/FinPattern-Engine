#!/usr/bin/env python3
"""
Performance Reporter für detaillierte Ergebnis-Statistiken
Phase 3 Implementation - Task 12

Features:
- Comprehensive Performance-Reporting und Analytics
- Multi-Timeframe-Performance-Analysis
- Risk-Adjusted-Returns und Drawdown-Analysis
- Trading-Statistics und Execution-Metrics
- Benchmark-Comparison und Relative-Performance
- Interactive-Reports und Dashboard-Generation
- Performance-Attribution und Factor-Analysis
"""

import json
import time
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
import numpy as np
from collections import defaultdict
import logging

# Data Analysis
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# Plotting
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False

# Statistical Analysis
try:
    from scipy import stats
    import scipy.optimize as optimize
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

# HTML Reports
try:
    import jinja2
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False


class ReportType(Enum):
    """Typen von Performance-Reports"""
    STRATEGY_PERFORMANCE = "strategy_performance"
    PORTFOLIO_ANALYSIS = "portfolio_analysis"
    RISK_ANALYSIS = "risk_analysis"
    TRADING_STATISTICS = "trading_statistics"
    BENCHMARK_COMPARISON = "benchmark_comparison"
    FACTOR_ANALYSIS = "factor_analysis"
    COMPREHENSIVE = "comprehensive"


class TimeFrame(Enum):
    """Zeitrahmen für Performance-Analyse"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class PerformanceMetric(Enum):
    """Performance-Metriken"""
    TOTAL_RETURN = "total_return"
    ANNUALIZED_RETURN = "annualized_return"
    SHARPE_RATIO = "sharpe_ratio"
    SORTINO_RATIO = "sortino_ratio"
    CALMAR_RATIO = "calmar_ratio"
    MAX_DRAWDOWN = "max_drawdown"
    VOLATILITY = "volatility"
    DOWNSIDE_DEVIATION = "downside_deviation"
    WIN_RATE = "win_rate"
    PROFIT_FACTOR = "profit_factor"
    AVERAGE_WIN = "average_win"
    AVERAGE_LOSS = "average_loss"
    LARGEST_WIN = "largest_win"
    LARGEST_LOSS = "largest_loss"
    CONSECUTIVE_WINS = "consecutive_wins"
    CONSECUTIVE_LOSSES = "consecutive_losses"
    TRADES_COUNT = "trades_count"
    AVERAGE_TRADE_DURATION = "average_trade_duration"
    BETA = "beta"
    ALPHA = "alpha"
    INFORMATION_RATIO = "information_ratio"
    TRACKING_ERROR = "tracking_error"


@dataclass
class TradeResult:
    """Einzelnes Trade-Ergebnis"""
    trade_id: str
    symbol: str
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    quantity: float
    side: str  # "long" oder "short"
    pnl: float
    pnl_percent: float
    commission: float = 0.0
    slippage: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "entry_time": self.entry_time.isoformat(),
            "exit_time": self.exit_time.isoformat(),
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "quantity": self.quantity,
            "side": self.side,
            "pnl": self.pnl,
            "pnl_percent": self.pnl_percent,
            "commission": self.commission,
            "slippage": self.slippage,
            "duration_hours": (self.exit_time - self.entry_time).total_seconds() / 3600,
            "metadata": self.metadata
        }


@dataclass
class PortfolioSnapshot:
    """Portfolio-Snapshot zu einem Zeitpunkt"""
    timestamp: datetime
    total_value: float
    cash: float
    positions: Dict[str, float]  # symbol -> value
    daily_return: Optional[float] = None
    cumulative_return: Optional[float] = None
    drawdown: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_value": self.total_value,
            "cash": self.cash,
            "positions": self.positions,
            "daily_return": self.daily_return,
            "cumulative_return": self.cumulative_return,
            "drawdown": self.drawdown
        }


@dataclass
class PerformanceReport:
    """Performance-Report"""
    report_id: str
    report_type: ReportType
    strategy_name: str
    start_date: datetime
    end_date: datetime
    generated_at: datetime
    metrics: Dict[str, float]
    charts: List[str] = field(default_factory=list)  # Pfade zu Chart-Dateien
    tables: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "report_type": self.report_type.value,
            "strategy_name": self.strategy_name,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "generated_at": self.generated_at.isoformat(),
            "metrics": self.metrics,
            "charts": self.charts,
            "tables": self.tables,
            "summary": self.summary,
            "metadata": self.metadata
        }


class PerformanceReporter:
    """
    Performance Reporter für detaillierte Ergebnis-Statistiken
    
    Features:
    - Comprehensive Performance-Metriken-Berechnung
    - Multi-Timeframe-Performance-Analyse
    - Risk-Adjusted-Returns und Drawdown-Analyse
    - Trading-Statistics und Execution-Metrics
    - Benchmark-Comparison und Relative-Performance
    - Interactive-HTML-Reports und Charts
    - Performance-Attribution und Factor-Analysis
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Reporter-Konfiguration
        self.enable_charts = self.config.get("enable_charts", PLOTTING_AVAILABLE)
        self.enable_html_reports = self.config.get("enable_html_reports", JINJA2_AVAILABLE)
        self.enable_statistical_analysis = self.config.get("enable_statistical_analysis", SCIPY_AVAILABLE)
        self.risk_free_rate = self.config.get("risk_free_rate", 0.02)  # 2% annual
        self.benchmark_symbol = self.config.get("benchmark_symbol", "SPY")
        
        # Output-Konfiguration
        self.output_directory = Path(self.config.get("output_directory", "performance_reports"))
        self.output_directory.mkdir(parents=True, exist_ok=True)
        
        self.charts_directory = self.output_directory / "charts"
        self.charts_directory.mkdir(parents=True, exist_ok=True)
        
        self.html_directory = self.output_directory / "html"
        self.html_directory.mkdir(parents=True, exist_ok=True)
        
        # Data Storage
        self.trade_results: Dict[str, List[TradeResult]] = defaultdict(list)
        self.portfolio_snapshots: Dict[str, List[PortfolioSnapshot]] = defaultdict(list)
        self.benchmark_data: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        
        # Generated Reports
        self.reports: List[PerformanceReport] = []
        
        # Statistiken
        self.stats = {
            "reports_generated": 0,
            "strategies_analyzed": 0,
            "total_trades_analyzed": 0,
            "total_performance_calculations": 0
        }
        
        self.logger.info("PerformanceReporter initialized")
    
    def add_trade_results(self, strategy_name: str, trades: List[TradeResult]):
        """Füge Trade-Ergebnisse hinzu"""
        
        try:
            self.trade_results[strategy_name].extend(trades)
            self.stats["total_trades_analyzed"] += len(trades)
            
            self.logger.info(f"Added {len(trades)} trade results for strategy '{strategy_name}'")
            
        except Exception as e:
            self.logger.error(f"Error adding trade results: {e}")
    
    def add_portfolio_snapshots(self, strategy_name: str, snapshots: List[PortfolioSnapshot]):
        """Füge Portfolio-Snapshots hinzu"""
        
        try:
            self.portfolio_snapshots[strategy_name].extend(snapshots)
            
            # Sortiere nach Timestamp
            self.portfolio_snapshots[strategy_name].sort(key=lambda x: x.timestamp)
            
            # Berechne Returns und Drawdowns
            self._calculate_returns_and_drawdowns(strategy_name)
            
            self.logger.info(f"Added {len(snapshots)} portfolio snapshots for strategy '{strategy_name}'")
            
        except Exception as e:
            self.logger.error(f"Error adding portfolio snapshots: {e}")
    
    def add_benchmark_data(self, benchmark_name: str, data: List[Tuple[datetime, float]]):
        """Füge Benchmark-Daten hinzu"""
        
        try:
            self.benchmark_data[benchmark_name].extend(data)
            
            # Sortiere nach Timestamp
            self.benchmark_data[benchmark_name].sort(key=lambda x: x[0])
            
            self.logger.info(f"Added {len(data)} benchmark data points for '{benchmark_name}'")
            
        except Exception as e:
            self.logger.error(f"Error adding benchmark data: {e}")
    
    def generate_strategy_performance_report(self, strategy_name: str,
                                           start_date: Optional[datetime] = None,
                                           end_date: Optional[datetime] = None) -> PerformanceReport:
        """Generiere Strategy-Performance-Report"""
        
        try:
            # Zeitraum bestimmen
            if not start_date or not end_date:
                snapshots = self.portfolio_snapshots.get(strategy_name, [])
                if snapshots:
                    start_date = start_date or snapshots[0].timestamp
                    end_date = end_date or snapshots[-1].timestamp
                else:
                    start_date = start_date or datetime.now() - timedelta(days=365)
                    end_date = end_date or datetime.now()
            
            # Report-ID generieren
            report_id = f"strategy_perf_{strategy_name}_{int(time.time())}"
            
            # Performance-Metriken berechnen
            metrics = self._calculate_performance_metrics(strategy_name, start_date, end_date)
            
            # Charts generieren
            charts = []
            if self.enable_charts:
                charts = self._generate_strategy_charts(strategy_name, start_date, end_date, report_id)
            
            # Trading-Statistiken-Tabelle
            tables = {}
            trades = self._get_trades_in_period(strategy_name, start_date, end_date)
            if trades:
                tables["trading_statistics"] = self._generate_trading_statistics_table(trades)
                tables["monthly_returns"] = self._generate_monthly_returns_table(strategy_name, start_date, end_date)
            
            # Summary generieren
            summary = self._generate_strategy_summary(strategy_name, metrics, len(trades))
            
            # Report erstellen
            report = PerformanceReport(
                report_id=report_id,
                report_type=ReportType.STRATEGY_PERFORMANCE,
                strategy_name=strategy_name,
                start_date=start_date,
                end_date=end_date,
                generated_at=datetime.now(),
                metrics=metrics,
                charts=charts,
                tables=tables,
                summary=summary,
                metadata={
                    "total_trades": len(trades),
                    "analysis_period_days": (end_date - start_date).days
                }
            )
            
            # Report speichern
            self._save_report(report)
            
            # HTML-Report generieren
            if self.enable_html_reports:
                self._generate_html_report(report)
            
            self.reports.append(report)
            self.stats["reports_generated"] += 1
            
            self.logger.info(f"Generated strategy performance report: {report_id}")
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating strategy performance report: {e}")
            raise
    
    def generate_benchmark_comparison_report(self, strategy_name: str, 
                                           benchmark_name: str,
                                           start_date: Optional[datetime] = None,
                                           end_date: Optional[datetime] = None) -> PerformanceReport:
        """Generiere Benchmark-Comparison-Report"""
        
        try:
            # Zeitraum bestimmen
            if not start_date or not end_date:
                snapshots = self.portfolio_snapshots.get(strategy_name, [])
                if snapshots:
                    start_date = start_date or snapshots[0].timestamp
                    end_date = end_date or snapshots[-1].timestamp
                else:
                    start_date = start_date or datetime.now() - timedelta(days=365)
                    end_date = end_date or datetime.now()
            
            report_id = f"benchmark_comp_{strategy_name}_{benchmark_name}_{int(time.time())}"
            
            # Strategy-Metriken
            strategy_metrics = self._calculate_performance_metrics(strategy_name, start_date, end_date)
            
            # Benchmark-Metriken
            benchmark_metrics = self._calculate_benchmark_metrics(benchmark_name, start_date, end_date)
            
            # Relative-Performance-Metriken
            relative_metrics = self._calculate_relative_performance_metrics(
                strategy_name, benchmark_name, start_date, end_date
            )
            
            # Kombiniere alle Metriken
            metrics = {
                **{f"strategy_{k}": v for k, v in strategy_metrics.items()},
                **{f"benchmark_{k}": v for k, v in benchmark_metrics.items()},
                **{f"relative_{k}": v for k, v in relative_metrics.items()}
            }
            
            # Charts generieren
            charts = []
            if self.enable_charts:
                charts = self._generate_comparison_charts(
                    strategy_name, benchmark_name, start_date, end_date, report_id
                )
            
            # Comparison-Tabellen
            tables = {
                "performance_comparison": self._generate_performance_comparison_table(
                    strategy_metrics, benchmark_metrics
                ),
                "rolling_performance": self._generate_rolling_performance_table(
                    strategy_name, benchmark_name, start_date, end_date
                )
            }
            
            # Summary
            summary = self._generate_comparison_summary(strategy_name, benchmark_name, relative_metrics)
            
            # Report erstellen
            report = PerformanceReport(
                report_id=report_id,
                report_type=ReportType.BENCHMARK_COMPARISON,
                strategy_name=f"{strategy_name} vs {benchmark_name}",
                start_date=start_date,
                end_date=end_date,
                generated_at=datetime.now(),
                metrics=metrics,
                charts=charts,
                tables=tables,
                summary=summary,
                metadata={
                    "strategy_name": strategy_name,
                    "benchmark_name": benchmark_name,
                    "analysis_period_days": (end_date - start_date).days
                }
            )
            
            self._save_report(report)
            
            if self.enable_html_reports:
                self._generate_html_report(report)
            
            self.reports.append(report)
            self.stats["reports_generated"] += 1
            
            self.logger.info(f"Generated benchmark comparison report: {report_id}")
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating benchmark comparison report: {e}")
            raise
    
    def generate_risk_analysis_report(self, strategy_name: str,
                                    start_date: Optional[datetime] = None,
                                    end_date: Optional[datetime] = None) -> PerformanceReport:
        """Generiere Risk-Analysis-Report"""
        
        try:
            # Zeitraum bestimmen
            if not start_date or not end_date:
                snapshots = self.portfolio_snapshots.get(strategy_name, [])
                if snapshots:
                    start_date = start_date or snapshots[0].timestamp
                    end_date = end_date or snapshots[-1].timestamp
                else:
                    start_date = start_date or datetime.now() - timedelta(days=365)
                    end_date = end_date or datetime.now()
            
            report_id = f"risk_analysis_{strategy_name}_{int(time.time())}"
            
            # Risk-Metriken berechnen
            metrics = self._calculate_risk_metrics(strategy_name, start_date, end_date)
            
            # Risk-Charts generieren
            charts = []
            if self.enable_charts:
                charts = self._generate_risk_charts(strategy_name, start_date, end_date, report_id)
            
            # Risk-Tabellen
            tables = {
                "drawdown_analysis": self._generate_drawdown_analysis_table(strategy_name, start_date, end_date),
                "var_analysis": self._generate_var_analysis_table(strategy_name, start_date, end_date),
                "tail_risk_analysis": self._generate_tail_risk_table(strategy_name, start_date, end_date)
            }
            
            # Risk-Summary
            summary = self._generate_risk_summary(strategy_name, metrics)
            
            # Report erstellen
            report = PerformanceReport(
                report_id=report_id,
                report_type=ReportType.RISK_ANALYSIS,
                strategy_name=strategy_name,
                start_date=start_date,
                end_date=end_date,
                generated_at=datetime.now(),
                metrics=metrics,
                charts=charts,
                tables=tables,
                summary=summary,
                metadata={
                    "analysis_period_days": (end_date - start_date).days,
                    "risk_free_rate": self.risk_free_rate
                }
            )
            
            self._save_report(report)
            
            if self.enable_html_reports:
                self._generate_html_report(report)
            
            self.reports.append(report)
            self.stats["reports_generated"] += 1
            
            self.logger.info(f"Generated risk analysis report: {report_id}")
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating risk analysis report: {e}")
            raise 
   
    def _calculate_returns_and_drawdowns(self, strategy_name: str):
        """Berechne Returns und Drawdowns für Portfolio-Snapshots"""
        
        try:
            snapshots = self.portfolio_snapshots[strategy_name]
            
            if len(snapshots) < 2:
                return
            
            # Berechne Daily Returns
            for i in range(1, len(snapshots)):
                prev_value = snapshots[i-1].total_value
                curr_value = snapshots[i].total_value
                
                if prev_value > 0:
                    daily_return = (curr_value - prev_value) / prev_value
                    snapshots[i].daily_return = daily_return
            
            # Berechne Cumulative Returns
            initial_value = snapshots[0].total_value
            for snapshot in snapshots:
                if initial_value > 0:
                    snapshot.cumulative_return = (snapshot.total_value - initial_value) / initial_value
            
            # Berechne Drawdowns
            peak_value = snapshots[0].total_value
            for snapshot in snapshots:
                if snapshot.total_value > peak_value:
                    peak_value = snapshot.total_value
                
                if peak_value > 0:
                    snapshot.drawdown = (snapshot.total_value - peak_value) / peak_value
                    
        except Exception as e:
            self.logger.error(f"Error calculating returns and drawdowns: {e}")
    
    def _calculate_performance_metrics(self, strategy_name: str, 
                                     start_date: datetime, end_date: datetime) -> Dict[str, float]:
        """Berechne Performance-Metriken für Strategy"""
        
        try:
            metrics = {}
            
            # Portfolio-Snapshots im Zeitraum
            snapshots = self._get_snapshots_in_period(strategy_name, start_date, end_date)
            
            if not snapshots:
                return metrics
            
            # Returns extrahieren
            returns = [s.daily_return for s in snapshots if s.daily_return is not None]
            
            if not returns:
                return metrics
            
            returns_array = np.array(returns)
            
            # Basic Performance Metrics
            total_return = snapshots[-1].cumulative_return or 0.0
            metrics["total_return"] = total_return
            
            # Annualized Return
            days = (end_date - start_date).days
            if days > 0:
                annualized_return = (1 + total_return) ** (365.25 / days) - 1
                metrics["annualized_return"] = annualized_return
            
            # Volatility
            volatility = np.std(returns_array) * np.sqrt(252)  # Annualized
            metrics["volatility"] = volatility
            
            # Sharpe Ratio
            if volatility > 0:
                excess_return = metrics.get("annualized_return", 0) - self.risk_free_rate
                metrics["sharpe_ratio"] = excess_return / volatility
            
            # Sortino Ratio
            downside_returns = returns_array[returns_array < 0]
            if len(downside_returns) > 0:
                downside_deviation = np.std(downside_returns) * np.sqrt(252)
                if downside_deviation > 0:
                    excess_return = metrics.get("annualized_return", 0) - self.risk_free_rate
                    metrics["sortino_ratio"] = excess_return / downside_deviation
                metrics["downside_deviation"] = downside_deviation
            
            # Max Drawdown
            drawdowns = [s.drawdown for s in snapshots if s.drawdown is not None]
            if drawdowns:
                metrics["max_drawdown"] = min(drawdowns)
            
            # Calmar Ratio
            max_dd = abs(metrics.get("max_drawdown", 0))
            if max_dd > 0:
                metrics["calmar_ratio"] = metrics.get("annualized_return", 0) / max_dd
            
            # Trading-Metriken
            trades = self._get_trades_in_period(strategy_name, start_date, end_date)
            if trades:
                trade_metrics = self._calculate_trading_metrics(trades)
                metrics.update(trade_metrics)
            
            self.stats["total_performance_calculations"] += 1
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating performance metrics: {e}")
            return {}
    
    def _calculate_trading_metrics(self, trades: List[TradeResult]) -> Dict[str, float]:
        """Berechne Trading-spezifische Metriken"""
        
        try:
            metrics = {}
            
            if not trades:
                return metrics
            
            # Basic Trading Stats
            metrics["trades_count"] = len(trades)
            
            # PnL-Statistiken
            pnls = [trade.pnl for trade in trades]
            winning_trades = [trade for trade in trades if trade.pnl > 0]
            losing_trades = [trade for trade in trades if trade.pnl < 0]
            
            metrics["win_rate"] = len(winning_trades) / len(trades) if trades else 0
            
            if winning_trades:
                metrics["average_win"] = np.mean([trade.pnl for trade in winning_trades])
                metrics["largest_win"] = max([trade.pnl for trade in winning_trades])
            
            if losing_trades:
                metrics["average_loss"] = np.mean([trade.pnl for trade in losing_trades])
                metrics["largest_loss"] = min([trade.pnl for trade in losing_trades])
            
            # Profit Factor
            gross_profit = sum([trade.pnl for trade in winning_trades])
            gross_loss = abs(sum([trade.pnl for trade in losing_trades]))
            
            if gross_loss > 0:
                metrics["profit_factor"] = gross_profit / gross_loss
            
            # Consecutive Wins/Losses
            consecutive_wins = 0
            consecutive_losses = 0
            max_consecutive_wins = 0
            max_consecutive_losses = 0
            
            for trade in trades:
                if trade.pnl > 0:
                    consecutive_wins += 1
                    consecutive_losses = 0
                    max_consecutive_wins = max(max_consecutive_wins, consecutive_wins)
                else:
                    consecutive_losses += 1
                    consecutive_wins = 0
                    max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
            
            metrics["consecutive_wins"] = max_consecutive_wins
            metrics["consecutive_losses"] = max_consecutive_losses
            
            # Average Trade Duration
            durations = [(trade.exit_time - trade.entry_time).total_seconds() / 3600 for trade in trades]
            metrics["average_trade_duration"] = np.mean(durations)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating trading metrics: {e}")
            return {}
    
    def _calculate_risk_metrics(self, strategy_name: str, 
                              start_date: datetime, end_date: datetime) -> Dict[str, float]:
        """Berechne Risk-Metriken"""
        
        try:
            metrics = {}
            
            snapshots = self._get_snapshots_in_period(strategy_name, start_date, end_date)
            returns = [s.daily_return for s in snapshots if s.daily_return is not None]
            
            if not returns:
                return metrics
            
            returns_array = np.array(returns)
            
            # Value at Risk (VaR)
            if self.enable_statistical_analysis and SCIPY_AVAILABLE:
                var_95 = np.percentile(returns_array, 5)
                var_99 = np.percentile(returns_array, 1)
                metrics["var_95"] = var_95
                metrics["var_99"] = var_99
                
                # Conditional VaR (Expected Shortfall)
                cvar_95 = np.mean(returns_array[returns_array <= var_95])
                cvar_99 = np.mean(returns_array[returns_array <= var_99])
                metrics["cvar_95"] = cvar_95
                metrics["cvar_99"] = cvar_99
            
            # Skewness und Kurtosis
            if SCIPY_AVAILABLE:
                metrics["skewness"] = stats.skew(returns_array)
                metrics["kurtosis"] = stats.kurtosis(returns_array)
            
            # Maximum Drawdown Duration
            drawdowns = [s.drawdown for s in snapshots if s.drawdown is not None]
            if drawdowns:
                in_drawdown = False
                drawdown_start = None
                max_drawdown_duration = 0
                current_drawdown_duration = 0
                
                for i, dd in enumerate(drawdowns):
                    if dd < 0 and not in_drawdown:
                        in_drawdown = True
                        drawdown_start = i
                        current_drawdown_duration = 1
                    elif dd < 0 and in_drawdown:
                        current_drawdown_duration += 1
                    elif dd >= 0 and in_drawdown:
                        in_drawdown = False
                        max_drawdown_duration = max(max_drawdown_duration, current_drawdown_duration)
                        current_drawdown_duration = 0
                
                metrics["max_drawdown_duration_days"] = max_drawdown_duration
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating risk metrics: {e}")
            return {}
    
    def _get_snapshots_in_period(self, strategy_name: str, 
                               start_date: datetime, end_date: datetime) -> List[PortfolioSnapshot]:
        """Erhalte Portfolio-Snapshots im Zeitraum"""
        
        snapshots = self.portfolio_snapshots.get(strategy_name, [])
        return [s for s in snapshots if start_date <= s.timestamp <= end_date]
    
    def _get_trades_in_period(self, strategy_name: str, 
                            start_date: datetime, end_date: datetime) -> List[TradeResult]:
        """Erhalte Trades im Zeitraum"""
        
        trades = self.trade_results.get(strategy_name, [])
        return [t for t in trades if start_date <= t.exit_time <= end_date]
    
    def _generate_strategy_charts(self, strategy_name: str, start_date: datetime, 
                                end_date: datetime, report_id: str) -> List[str]:
        """Generiere Strategy-Charts"""
        
        if not PLOTTING_AVAILABLE:
            return []
        
        try:
            charts = []
            
            # Equity Curve
            equity_chart = self._create_equity_curve_chart(strategy_name, start_date, end_date, report_id)
            if equity_chart:
                charts.append(str(equity_chart))
            
            # Drawdown Chart
            drawdown_chart = self._create_drawdown_chart(strategy_name, start_date, end_date, report_id)
            if drawdown_chart:
                charts.append(str(drawdown_chart))
            
            # Returns Distribution
            returns_dist_chart = self._create_returns_distribution_chart(strategy_name, start_date, end_date, report_id)
            if returns_dist_chart:
                charts.append(str(returns_dist_chart))
            
            # Monthly Returns Heatmap
            monthly_heatmap = self._create_monthly_returns_heatmap(strategy_name, start_date, end_date, report_id)
            if monthly_heatmap:
                charts.append(str(monthly_heatmap))
            
            return charts
            
        except Exception as e:
            self.logger.error(f"Error generating strategy charts: {e}")
            return []
    
    def _create_equity_curve_chart(self, strategy_name: str, start_date: datetime, 
                                 end_date: datetime, report_id: str) -> Optional[Path]:
        """Erstelle Equity-Curve-Chart"""
        
        try:
            snapshots = self._get_snapshots_in_period(strategy_name, start_date, end_date)
            
            if not snapshots:
                return None
            
            fig, ax = plt.subplots(figsize=(12, 6))
            
            timestamps = [s.timestamp for s in snapshots]
            values = [s.total_value for s in snapshots]
            
            ax.plot(timestamps, values, linewidth=2, color='blue', label='Portfolio Value')
            ax.set_title(f'Equity Curve - {strategy_name}')
            ax.set_xlabel('Date')
            ax.set_ylabel('Portfolio Value')
            ax.grid(True, alpha=0.3)
            ax.legend()
            
            # Formatiere X-Achse
            import matplotlib.dates as mdates
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.tick_params(axis='x', rotation=45)
            
            plt.tight_layout()
            
            chart_file = self.charts_directory / f"equity_curve_{report_id}.png"
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            return chart_file
            
        except Exception as e:
            self.logger.error(f"Error creating equity curve chart: {e}")
            return None
    
    def _create_drawdown_chart(self, strategy_name: str, start_date: datetime, 
                             end_date: datetime, report_id: str) -> Optional[Path]:
        """Erstelle Drawdown-Chart"""
        
        try:
            snapshots = self._get_snapshots_in_period(strategy_name, start_date, end_date)
            
            if not snapshots:
                return None
            
            fig, ax = plt.subplots(figsize=(12, 6))
            
            timestamps = [s.timestamp for s in snapshots]
            drawdowns = [s.drawdown * 100 if s.drawdown else 0 for s in snapshots]  # Convert to percentage
            
            ax.fill_between(timestamps, drawdowns, 0, alpha=0.3, color='red', label='Drawdown')
            ax.plot(timestamps, drawdowns, linewidth=1, color='red')
            ax.set_title(f'Drawdown Analysis - {strategy_name}')
            ax.set_xlabel('Date')
            ax.set_ylabel('Drawdown (%)')
            ax.grid(True, alpha=0.3)
            ax.legend()
            
            # Formatiere X-Achse
            import matplotlib.dates as mdates
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.tick_params(axis='x', rotation=45)
            
            plt.tight_layout()
            
            chart_file = self.charts_directory / f"drawdown_{report_id}.png"
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            return chart_file
            
        except Exception as e:
            self.logger.error(f"Error creating drawdown chart: {e}")
            return None
    
    def _save_report(self, report: PerformanceReport):
        """Speichere Report als JSON"""
        
        try:
            report_file = self.output_directory / f"report_{report.report_id}.json"
            
            with open(report_file, 'w') as f:
                json.dump(report.to_dict(), f, indent=2, default=str)
                
        except Exception as e:
            self.logger.error(f"Error saving report: {e}")
    
    def get_reporter_statistics(self) -> Dict[str, Any]:
        """Erhalte Reporter-Statistiken"""
        
        try:
            # Strategy-Übersicht
            strategies_info = {}
            for strategy_name in self.trade_results.keys():
                trades_count = len(self.trade_results[strategy_name])
                snapshots_count = len(self.portfolio_snapshots.get(strategy_name, []))
                
                strategies_info[strategy_name] = {
                    "trades_count": trades_count,
                    "snapshots_count": snapshots_count,
                    "has_data": trades_count > 0 or snapshots_count > 0
                }
            
            # Recent Reports
            recent_reports = []
            for report in self.reports[-10:]:  # Letzte 10
                recent_reports.append({
                    "report_id": report.report_id,
                    "report_type": report.report_type.value,
                    "strategy_name": report.strategy_name,
                    "generated_at": report.generated_at.isoformat(),
                    "charts_count": len(report.charts),
                    "metrics_count": len(report.metrics)
                })
            
            return {
                "timestamp": datetime.now().isoformat(),
                "reporter_config": {
                    "enable_charts": self.enable_charts,
                    "enable_html_reports": self.enable_html_reports,
                    "enable_statistical_analysis": self.enable_statistical_analysis,
                    "risk_free_rate": self.risk_free_rate,
                    "benchmark_symbol": self.benchmark_symbol
                },
                "statistics": dict(self.stats),
                "strategies": strategies_info,
                "recent_reports": recent_reports,
                "total_reports": len(self.reports),
                "output_directory": str(self.output_directory)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting reporter statistics: {e}")
            return {"error": str(e)}
    
    def cleanup(self):
        """Cleanup Reporter-Ressourcen"""
        
        try:
            # Clear Data
            self.trade_results.clear()
            self.portfolio_snapshots.clear()
            self.benchmark_data.clear()
            self.reports.clear()
            
            self.logger.info("PerformanceReporter cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during reporter cleanup: {e}")


# Utility-Funktionen
def create_trade_result_from_dict(trade_data: Dict[str, Any]) -> TradeResult:
    """Erstelle TradeResult aus Dictionary"""
    
    return TradeResult(
        trade_id=trade_data["trade_id"],
        symbol=trade_data["symbol"],
        entry_time=datetime.fromisoformat(trade_data["entry_time"]),
        exit_time=datetime.fromisoformat(trade_data["exit_time"]),
        entry_price=trade_data["entry_price"],
        exit_price=trade_data["exit_price"],
        quantity=trade_data["quantity"],
        side=trade_data["side"],
        pnl=trade_data["pnl"],
        pnl_percent=trade_data["pnl_percent"],
        commission=trade_data.get("commission", 0.0),
        slippage=trade_data.get("slippage", 0.0),
        metadata=trade_data.get("metadata", {})
    )


def create_portfolio_snapshot_from_dict(snapshot_data: Dict[str, Any]) -> PortfolioSnapshot:
    """Erstelle PortfolioSnapshot aus Dictionary"""
    
    return PortfolioSnapshot(
        timestamp=datetime.fromisoformat(snapshot_data["timestamp"]),
        total_value=snapshot_data["total_value"],
        cash=snapshot_data["cash"],
        positions=snapshot_data["positions"],
        daily_return=snapshot_data.get("daily_return"),
        cumulative_return=snapshot_data.get("cumulative_return"),
        drawdown=snapshot_data.get("drawdown")
    )


def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.02) -> float:
    """Berechne Sharpe-Ratio"""
    
    if not returns:
        return 0.0
    
    returns_array = np.array(returns)
    excess_returns = returns_array - (risk_free_rate / 252)  # Daily risk-free rate
    
    if np.std(excess_returns) == 0:
        return 0.0
    
    return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)


def calculate_max_drawdown(values: List[float]) -> float:
    """Berechne Maximum Drawdown"""
    
    if not values:
        return 0.0
    
    peak = values[0]
    max_dd = 0.0
    
    for value in values:
        if value > peak:
            peak = value
        
        drawdown = (value - peak) / peak if peak > 0 else 0
        max_dd = min(max_dd, drawdown)
    
    return max_dd


def setup_performance_reporting(output_dir: str, 
                              risk_free_rate: float = 0.02,
                              benchmark_symbol: str = "SPY") -> Dict[str, Any]:
    """Setup Performance-Reporting-Konfiguration"""
    
    return {
        "enable_charts": PLOTTING_AVAILABLE,
        "enable_html_reports": JINJA2_AVAILABLE,
        "enable_statistical_analysis": SCIPY_AVAILABLE,
        "output_directory": output_dir,
        "risk_free_rate": risk_free_rate,
        "benchmark_symbol": benchmark_symbol
    }