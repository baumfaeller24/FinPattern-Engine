#!/usr/bin/env python3
"""
Training Progress Tracker für Model-Training-Metriken
Phase 3 Implementation - Task 12

Features:
- Real-time Training-Progress-Tracking
- Comprehensive Model-Performance-Metriken
- Training-Loss und Validation-Accuracy-Monitoring
- Learning-Rate-Scheduling und Optimization-Tracking
- Early-Stopping und Checkpoint-Management
- Training-Visualization und Progress-Reports
- Multi-Model-Training-Coordination
"""

import time
import json
import threading
from typing import Dict, List, Optional, Any, Union, Callable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
import numpy as np
from collections import deque, defaultdict
import pickle
import logging

# Plotting für Visualisierung
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False

# TensorBoard-Integration
try:
    from torch.utils.tensorboard import SummaryWriter
    TENSORBOARD_AVAILABLE = True
except ImportError:
    TENSORBOARD_AVAILABLE = False

# Weights & Biases Integration
try:
    import wandb
    WANDB_AVAILABLE = True
except ImportError:
    WANDB_AVAILABLE = False


class TrainingPhase(Enum):
    """Training-Phasen"""
    INITIALIZATION = "initialization"
    TRAINING = "training"
    VALIDATION = "validation"
    TESTING = "testing"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class MetricType(Enum):
    """Typen von Training-Metriken"""
    LOSS = "loss"
    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1_SCORE = "f1_score"
    AUC = "auc"
    LEARNING_RATE = "learning_rate"
    GRADIENT_NORM = "gradient_norm"
    WEIGHT_NORM = "weight_norm"
    CUSTOM = "custom"


class OptimizationGoal(Enum):
    """Optimierungs-Ziele"""
    MINIMIZE_LOSS = "minimize_loss"
    MAXIMIZE_ACCURACY = "maximize_accuracy"
    MAXIMIZE_PROFIT = "maximize_profit"
    MINIMIZE_DRAWDOWN = "minimize_drawdown"
    MAXIMIZE_SHARPE = "maximize_sharpe"
    CUSTOM = "custom"


@dataclass
class TrainingMetric:
    """Training-Metrik"""
    metric_type: MetricType
    value: float
    epoch: int
    batch: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)
    phase: TrainingPhase = TrainingPhase.TRAINING
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_type": self.metric_type.value,
            "value": self.value,
            "epoch": self.epoch,
            "batch": self.batch,
            "timestamp": self.timestamp.isoformat(),
            "phase": self.phase.value,
            "metadata": self.metadata
        }


@dataclass
class TrainingCheckpoint:
    """Training-Checkpoint"""
    checkpoint_id: str
    epoch: int
    timestamp: datetime
    model_state: Optional[str] = None  # Path zu Model-State
    optimizer_state: Optional[str] = None  # Path zu Optimizer-State
    metrics: Dict[str, float] = field(default_factory=dict)
    is_best: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "epoch": self.epoch,
            "timestamp": self.timestamp.isoformat(),
            "model_state": self.model_state,
            "optimizer_state": self.optimizer_state,
            "metrics": self.metrics,
            "is_best": self.is_best,
            "metadata": self.metadata
        }


@dataclass
class TrainingSession:
    """Training-Session"""
    session_id: str
    model_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    phase: TrainingPhase = TrainingPhase.INITIALIZATION
    total_epochs: Optional[int] = None
    current_epoch: int = 0
    optimization_goal: OptimizationGoal = OptimizationGoal.MINIMIZE_LOSS
    best_metric_value: Optional[float] = None
    best_epoch: Optional[int] = None
    early_stopping_patience: int = 10
    early_stopping_counter: int = 0
    config: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "model_name": self.model_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "phase": self.phase.value,
            "total_epochs": self.total_epochs,
            "current_epoch": self.current_epoch,
            "optimization_goal": self.optimization_goal.value,
            "best_metric_value": self.best_metric_value,
            "best_epoch": self.best_epoch,
            "early_stopping_patience": self.early_stopping_patience,
            "early_stopping_counter": self.early_stopping_counter,
            "config": self.config
        }


class TrainingProgressTracker:
    """
    Training Progress Tracker für Model-Training-Metriken
    
    Features:
    - Real-time Training-Progress-Monitoring
    - Comprehensive Metric-Tracking (Loss, Accuracy, etc.)
    - Early-Stopping und Best-Model-Selection
    - Checkpoint-Management und Model-Persistence
    - Training-Visualization und Progress-Reports
    - Multi-Model-Training-Coordination
    - Integration mit TensorBoard und Weights & Biases
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Tracker-Konfiguration
        self.tracking_enabled = self.config.get("tracking_enabled", True)
        self.save_checkpoints = self.config.get("save_checkpoints", True)
        self.checkpoint_frequency = self.config.get("checkpoint_frequency", 5)  # Alle 5 Epochen
        self.enable_early_stopping = self.config.get("enable_early_stopping", True)
        self.enable_visualization = self.config.get("enable_visualization", PLOTTING_AVAILABLE)
        self.enable_tensorboard = self.config.get("enable_tensorboard", TENSORBOARD_AVAILABLE)
        self.enable_wandb = self.config.get("enable_wandb", WANDB_AVAILABLE)
        
        # Storage-Konfiguration
        self.output_directory = Path(self.config.get("output_directory", "training_logs"))
        self.output_directory.mkdir(parents=True, exist_ok=True)
        
        self.checkpoint_directory = self.output_directory / "checkpoints"
        self.checkpoint_directory.mkdir(parents=True, exist_ok=True)
        
        self.plots_directory = self.output_directory / "plots"
        self.plots_directory.mkdir(parents=True, exist_ok=True)
        
        # Training-Sessions
        self.active_sessions: Dict[str, TrainingSession] = {}
        self.completed_sessions: List[TrainingSession] = []
        
        # Metriken-Storage
        self.session_metrics: Dict[str, List[TrainingMetric]] = defaultdict(list)
        self.session_checkpoints: Dict[str, List[TrainingCheckpoint]] = defaultdict(list)
        
        # Real-time Monitoring
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Callbacks
        self.epoch_callbacks: List[Callable] = []
        self.checkpoint_callbacks: List[Callable] = []
        self.early_stopping_callbacks: List[Callable] = []
        
        # External Integrations
        self.tensorboard_writers: Dict[str, Any] = {}
        self.wandb_runs: Dict[str, Any] = {}
        
        # Statistiken
        self.stats = {
            "total_sessions": 0,
            "completed_sessions": 0,
            "failed_sessions": 0,
            "total_epochs_trained": 0,
            "total_checkpoints_saved": 0,
            "early_stops_triggered": 0
        }
        
        self.logger.info("TrainingProgressTracker initialized")
    
    def start_training_session(self, session_id: str, model_name: str,
                             total_epochs: Optional[int] = None,
                             optimization_goal: OptimizationGoal = OptimizationGoal.MINIMIZE_LOSS,
                             **kwargs) -> TrainingSession:
        """Starte neue Training-Session"""
        
        try:
            # Prüfe ob Session bereits existiert
            if session_id in self.active_sessions:
                self.logger.warning(f"Training session {session_id} already active")
                return self.active_sessions[session_id]
            
            # Erstelle neue Session
            session = TrainingSession(
                session_id=session_id,
                model_name=model_name,
                start_time=datetime.now(),
                total_epochs=total_epochs,
                optimization_goal=optimization_goal,
                early_stopping_patience=kwargs.get("early_stopping_patience", 10),
                config=kwargs
            )
            
            self.active_sessions[session_id] = session
            self.stats["total_sessions"] += 1
            
            # TensorBoard-Writer erstellen
            if self.enable_tensorboard and TENSORBOARD_AVAILABLE:
                tensorboard_dir = self.output_directory / "tensorboard" / session_id
                self.tensorboard_writers[session_id] = SummaryWriter(tensorboard_dir)
            
            # Weights & Biases Run starten
            if self.enable_wandb and WANDB_AVAILABLE:
                wandb_run = wandb.init(
                    project=kwargs.get("wandb_project", "ai_indicator_optimizer"),
                    name=f"{model_name}_{session_id}",
                    config=kwargs
                )
                self.wandb_runs[session_id] = wandb_run
            
            # Session-Datei erstellen
            self._save_session_metadata(session)
            
            self.logger.info(f"Started training session: {session_id} (model: {model_name})")
            
            return session
            
        except Exception as e:
            self.logger.error(f"Error starting training session: {e}")
            raise
    
    def log_metric(self, session_id: str, metric_type: MetricType, value: float,
                  epoch: int, batch: Optional[int] = None,
                  phase: TrainingPhase = TrainingPhase.TRAINING, **kwargs):
        """Logge Training-Metrik"""
        
        try:
            if session_id not in self.active_sessions:
                self.logger.error(f"Training session {session_id} not found")
                return
            
            # Metrik erstellen
            metric = TrainingMetric(
                metric_type=metric_type,
                value=value,
                epoch=epoch,
                batch=batch,
                phase=phase,
                metadata=kwargs
            )
            
            # Zu Session-Metriken hinzufügen
            self.session_metrics[session_id].append(metric)
            
            # Session aktualisieren
            session = self.active_sessions[session_id]
            session.current_epoch = max(session.current_epoch, epoch)
            
            # Best-Metric-Tracking
            self._update_best_metric(session, metric)
            
            # TensorBoard-Logging
            if session_id in self.tensorboard_writers:
                writer = self.tensorboard_writers[session_id]
                tag = f"{phase.value}/{metric_type.value}"
                step = epoch * 1000 + (batch or 0)  # Unique step
                writer.add_scalar(tag, value, step)
            
            # Weights & Biases Logging
            if session_id in self.wandb_runs:
                wandb_data = {f"{phase.value}_{metric_type.value}": value}
                if batch is not None:
                    wandb_data["batch"] = batch
                wandb.log(wandb_data, step=epoch)
            
            # Early-Stopping prüfen
            if self.enable_early_stopping and phase == TrainingPhase.VALIDATION:
                self._check_early_stopping(session, metric)
            
            self.logger.debug(f"Logged metric: {metric_type.value}={value:.4f} "
                            f"(session: {session_id}, epoch: {epoch})")
            
        except Exception as e:
            self.logger.error(f"Error logging metric: {e}")
    
    def log_multiple_metrics(self, session_id: str, metrics: Dict[str, float],
                           epoch: int, batch: Optional[int] = None,
                           phase: TrainingPhase = TrainingPhase.TRAINING):
        """Logge mehrere Metriken gleichzeitig"""
        
        for metric_name, value in metrics.items():
            try:
                # Konvertiere String zu MetricType
                if isinstance(metric_name, str):
                    metric_type = MetricType(metric_name.lower())
                else:
                    metric_type = metric_name
                
                self.log_metric(session_id, metric_type, value, epoch, batch, phase)
                
            except ValueError:
                # Custom-Metrik
                self.log_metric(session_id, MetricType.CUSTOM, value, epoch, batch, phase,
                              custom_name=metric_name)
    
    def save_checkpoint(self, session_id: str, epoch: int,
                       model_state_path: Optional[str] = None,
                       optimizer_state_path: Optional[str] = None,
                       metrics: Optional[Dict[str, float]] = None,
                       **kwargs) -> TrainingCheckpoint:
        """Speichere Training-Checkpoint"""
        
        try:
            if session_id not in self.active_sessions:
                self.logger.error(f"Training session {session_id} not found")
                return None
            
            session = self.active_sessions[session_id]
            
            # Checkpoint-ID generieren
            checkpoint_id = f"{session_id}_epoch_{epoch}_{int(time.time())}"
            
            # Aktuelle Metriken sammeln
            current_metrics = metrics or {}
            if not current_metrics:
                # Letzte Metriken aus Session holen
                recent_metrics = self._get_recent_metrics(session_id, epoch)
                current_metrics = recent_metrics
            
            # Prüfe ob bestes Model
            is_best = self._is_best_checkpoint(session, current_metrics)
            
            # Checkpoint erstellen
            checkpoint = TrainingCheckpoint(
                checkpoint_id=checkpoint_id,
                epoch=epoch,
                timestamp=datetime.now(),
                model_state=model_state_path,
                optimizer_state=optimizer_state_path,
                metrics=current_metrics,
                is_best=is_best,
                metadata=kwargs
            )
            
            # Zu Session-Checkpoints hinzufügen
            self.session_checkpoints[session_id].append(checkpoint)
            
            # Checkpoint-Datei speichern
            if self.save_checkpoints:
                self._save_checkpoint_metadata(checkpoint)
            
            # Statistiken
            self.stats["total_checkpoints_saved"] += 1
            
            # Callbacks ausführen
            for callback in self.checkpoint_callbacks:
                try:
                    callback(session, checkpoint)
                except Exception as e:
                    self.logger.error(f"Checkpoint callback error: {e}")
            
            self.logger.info(f"Saved checkpoint: {checkpoint_id} "
                           f"(epoch: {epoch}, is_best: {is_best})")
            
            return checkpoint
            
        except Exception as e:
            self.logger.error(f"Error saving checkpoint: {e}")
            return None
    
    def end_training_session(self, session_id: str, 
                           final_phase: TrainingPhase = TrainingPhase.COMPLETED):
        """Beende Training-Session"""
        
        try:
            if session_id not in self.active_sessions:
                self.logger.error(f"Training session {session_id} not found")
                return
            
            session = self.active_sessions[session_id]
            session.end_time = datetime.now()
            session.phase = final_phase
            
            # Statistiken aktualisieren
            self.stats["total_epochs_trained"] += session.current_epoch
            
            if final_phase == TrainingPhase.COMPLETED:
                self.stats["completed_sessions"] += 1
            elif final_phase == TrainingPhase.FAILED:
                self.stats["failed_sessions"] += 1
            
            # Session zu completed verschieben
            self.completed_sessions.append(session)
            del self.active_sessions[session_id]
            
            # External Integrations cleanup
            if session_id in self.tensorboard_writers:
                self.tensorboard_writers[session_id].close()
                del self.tensorboard_writers[session_id]
            
            if session_id in self.wandb_runs:
                wandb.finish()
                del self.wandb_runs[session_id]
            
            # Finale Session-Datei speichern
            self._save_session_metadata(session)
            
            # Training-Report generieren
            if self.enable_visualization:
                self.generate_training_report(session_id)
            
            training_duration = session.end_time - session.start_time
            self.logger.info(f"Ended training session: {session_id} "
                           f"(phase: {final_phase.value}, duration: {training_duration})")
            
        except Exception as e:
            self.logger.error(f"Error ending training session: {e}")
    
    def get_session_progress(self, session_id: str) -> Dict[str, Any]:
        """Erhalte Training-Progress für Session"""
        
        try:
            # Suche in aktiven Sessions
            session = self.active_sessions.get(session_id)
            if not session:
                # Suche in completed Sessions
                for completed_session in self.completed_sessions:
                    if completed_session.session_id == session_id:
                        session = completed_session
                        break
            
            if not session:
                return {"error": f"Session {session_id} not found"}
            
            # Aktuelle Metriken
            metrics = self.session_metrics.get(session_id, [])
            checkpoints = self.session_checkpoints.get(session_id, [])
            
            # Progress-Berechnung
            progress_percent = 0.0
            if session.total_epochs and session.total_epochs > 0:
                progress_percent = (session.current_epoch / session.total_epochs) * 100
            
            # Letzte Metriken pro Typ
            latest_metrics = {}
            for metric in reversed(metrics):
                if metric.metric_type.value not in latest_metrics:
                    latest_metrics[metric.metric_type.value] = metric.value
            
            # Training-Geschwindigkeit
            training_speed = self._calculate_training_speed(session, metrics)
            
            # ETA-Berechnung
            eta = self._calculate_eta(session, training_speed)
            
            return {
                "session": session.to_dict(),
                "progress_percent": progress_percent,
                "latest_metrics": latest_metrics,
                "total_metrics": len(metrics),
                "total_checkpoints": len(checkpoints),
                "best_checkpoint": self._get_best_checkpoint(session_id),
                "training_speed": training_speed,
                "eta": eta.isoformat() if eta else None,
                "is_active": session_id in self.active_sessions
            }
            
        except Exception as e:
            self.logger.error(f"Error getting session progress: {e}")
            return {"error": str(e)}
    
    def _update_best_metric(self, session: TrainingSession, metric: TrainingMetric):
        """Aktualisiere Best-Metric für Session"""
        
        try:
            # Nur relevante Metriken für Optimization-Goal
            relevant_metrics = {
                OptimizationGoal.MINIMIZE_LOSS: [MetricType.LOSS],
                OptimizationGoal.MAXIMIZE_ACCURACY: [MetricType.ACCURACY],
                OptimizationGoal.MAXIMIZE_PROFIT: [MetricType.CUSTOM],
                OptimizationGoal.MINIMIZE_DRAWDOWN: [MetricType.CUSTOM],
                OptimizationGoal.MAXIMIZE_SHARPE: [MetricType.CUSTOM]
            }
            
            target_metrics = relevant_metrics.get(session.optimization_goal, [MetricType.LOSS])
            
            if metric.metric_type not in target_metrics:
                return
            
            # Prüfe ob neuer Best-Wert
            is_better = False
            
            if session.best_metric_value is None:
                is_better = True
            else:
                if session.optimization_goal in [OptimizationGoal.MINIMIZE_LOSS, OptimizationGoal.MINIMIZE_DRAWDOWN]:
                    is_better = metric.value < session.best_metric_value
                else:
                    is_better = metric.value > session.best_metric_value
            
            if is_better:
                session.best_metric_value = metric.value
                session.best_epoch = metric.epoch
                session.early_stopping_counter = 0  # Reset counter
                
                self.logger.info(f"New best metric for {session.session_id}: "
                               f"{metric.metric_type.value}={metric.value:.4f} (epoch {metric.epoch})")
            else:
                session.early_stopping_counter += 1
                
        except Exception as e:
            self.logger.error(f"Error updating best metric: {e}")
    
    def _check_early_stopping(self, session: TrainingSession, metric: TrainingMetric):
        """Prüfe Early-Stopping-Kriterien"""
        
        try:
            if session.early_stopping_counter >= session.early_stopping_patience:
                self.logger.info(f"Early stopping triggered for {session.session_id} "
                               f"(patience: {session.early_stopping_patience})")
                
                # Early-Stopping-Callbacks
                for callback in self.early_stopping_callbacks:
                    try:
                        callback(session, metric)
                    except Exception as e:
                        self.logger.error(f"Early stopping callback error: {e}")
                
                # Session beenden
                self.end_training_session(session.session_id, TrainingPhase.COMPLETED)
                
                self.stats["early_stops_triggered"] += 1
                
        except Exception as e:
            self.logger.error(f"Error checking early stopping: {e}")
    
    def _get_recent_metrics(self, session_id: str, epoch: int) -> Dict[str, float]:
        """Erhalte letzte Metriken für Epoch"""
        
        recent_metrics = {}
        
        for metric in reversed(self.session_metrics.get(session_id, [])):
            if metric.epoch == epoch:
                if metric.metric_type.value not in recent_metrics:
                    recent_metrics[metric.metric_type.value] = metric.value
        
        return recent_metrics
    
    def _is_best_checkpoint(self, session: TrainingSession, metrics: Dict[str, float]) -> bool:
        """Prüfe ob Checkpoint der beste ist"""
        
        try:
            # Basiere auf Optimization-Goal
            if session.optimization_goal == OptimizationGoal.MINIMIZE_LOSS:
                current_value = metrics.get("loss")
            elif session.optimization_goal == OptimizationGoal.MAXIMIZE_ACCURACY:
                current_value = metrics.get("accuracy")
            else:
                # Verwende best_metric_value
                current_value = session.best_metric_value
            
            if current_value is None:
                return False
            
            return current_value == session.best_metric_value
            
        except Exception as e:
            self.logger.error(f"Error checking best checkpoint: {e}")
            return False 
   
    def _get_best_checkpoint(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Erhalte besten Checkpoint für Session"""
        
        checkpoints = self.session_checkpoints.get(session_id, [])
        
        for checkpoint in reversed(checkpoints):
            if checkpoint.is_best:
                return checkpoint.to_dict()
        
        return None
    
    def _calculate_training_speed(self, session: TrainingSession, 
                                metrics: List[TrainingMetric]) -> Dict[str, float]:
        """Berechne Training-Geschwindigkeit"""
        
        try:
            if not metrics or session.current_epoch == 0:
                return {"epochs_per_hour": 0.0, "batches_per_second": 0.0}
            
            # Epochen pro Stunde
            training_duration = datetime.now() - session.start_time
            hours = training_duration.total_seconds() / 3600
            epochs_per_hour = session.current_epoch / hours if hours > 0 else 0.0
            
            # Batches pro Sekunde (approximiert)
            batch_metrics = [m for m in metrics if m.batch is not None]
            if batch_metrics:
                total_batches = len(batch_metrics)
                seconds = training_duration.total_seconds()
                batches_per_second = total_batches / seconds if seconds > 0 else 0.0
            else:
                batches_per_second = 0.0
            
            return {
                "epochs_per_hour": epochs_per_hour,
                "batches_per_second": batches_per_second
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating training speed: {e}")
            return {"epochs_per_hour": 0.0, "batches_per_second": 0.0}
    
    def _calculate_eta(self, session: TrainingSession, 
                      training_speed: Dict[str, float]) -> Optional[datetime]:
        """Berechne ETA für Training-Completion"""
        
        try:
            if not session.total_epochs or session.current_epoch >= session.total_epochs:
                return None
            
            remaining_epochs = session.total_epochs - session.current_epoch
            epochs_per_hour = training_speed.get("epochs_per_hour", 0.0)
            
            if epochs_per_hour > 0:
                remaining_hours = remaining_epochs / epochs_per_hour
                eta = datetime.now() + timedelta(hours=remaining_hours)
                return eta
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error calculating ETA: {e}")
            return None
    
    def _save_session_metadata(self, session: TrainingSession):
        """Speichere Session-Metadaten"""
        
        try:
            session_file = self.output_directory / f"session_{session.session_id}.json"
            
            with open(session_file, 'w') as f:
                json.dump(session.to_dict(), f, indent=2, default=str)
                
        except Exception as e:
            self.logger.error(f"Error saving session metadata: {e}")
    
    def _save_checkpoint_metadata(self, checkpoint: TrainingCheckpoint):
        """Speichere Checkpoint-Metadaten"""
        
        try:
            checkpoint_file = self.checkpoint_directory / f"{checkpoint.checkpoint_id}.json"
            
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint.to_dict(), f, indent=2, default=str)
                
        except Exception as e:
            self.logger.error(f"Error saving checkpoint metadata: {e}")
    
    def generate_training_report(self, session_id: str) -> Optional[Path]:
        """Generiere Training-Report mit Visualisierungen"""
        
        if not self.enable_visualization or not PLOTTING_AVAILABLE:
            return None
        
        try:
            # Session und Metriken laden
            session = None
            for s in self.active_sessions.values():
                if s.session_id == session_id:
                    session = s
                    break
            
            if not session:
                for s in self.completed_sessions:
                    if s.session_id == session_id:
                        session = s
                        break
            
            if not session:
                self.logger.error(f"Session {session_id} not found for report generation")
                return None
            
            metrics = self.session_metrics.get(session_id, [])
            
            if not metrics:
                self.logger.warning(f"No metrics found for session {session_id}")
                return None
            
            # Plot-Setup
            plt.style.use('seaborn-v0_8' if hasattr(plt.style, 'seaborn-v0_8') else 'default')
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle(f'Training Report: {session.model_name} ({session_id})', fontsize=16)
            
            # Metriken nach Typ gruppieren
            metrics_by_type = defaultdict(list)
            for metric in metrics:
                metrics_by_type[metric.metric_type].append(metric)
            
            # Plot 1: Loss über Zeit
            if MetricType.LOSS in metrics_by_type:
                loss_metrics = metrics_by_type[MetricType.LOSS]
                epochs = [m.epoch for m in loss_metrics]
                values = [m.value for m in loss_metrics]
                
                axes[0, 0].plot(epochs, values, 'b-', linewidth=2, label='Training Loss')
                axes[0, 0].set_title('Training Loss')
                axes[0, 0].set_xlabel('Epoch')
                axes[0, 0].set_ylabel('Loss')
                axes[0, 0].grid(True, alpha=0.3)
                axes[0, 0].legend()
            
            # Plot 2: Accuracy über Zeit
            if MetricType.ACCURACY in metrics_by_type:
                acc_metrics = metrics_by_type[MetricType.ACCURACY]
                epochs = [m.epoch for m in acc_metrics]
                values = [m.value for m in acc_metrics]
                
                axes[0, 1].plot(epochs, values, 'g-', linewidth=2, label='Accuracy')
                axes[0, 1].set_title('Model Accuracy')
                axes[0, 1].set_xlabel('Epoch')
                axes[0, 1].set_ylabel('Accuracy')
                axes[0, 1].grid(True, alpha=0.3)
                axes[0, 1].legend()
            
            # Plot 3: Learning Rate über Zeit
            if MetricType.LEARNING_RATE in metrics_by_type:
                lr_metrics = metrics_by_type[MetricType.LEARNING_RATE]
                epochs = [m.epoch for m in lr_metrics]
                values = [m.value for m in lr_metrics]
                
                axes[1, 0].plot(epochs, values, 'r-', linewidth=2, label='Learning Rate')
                axes[1, 0].set_title('Learning Rate Schedule')
                axes[1, 0].set_xlabel('Epoch')
                axes[1, 0].set_ylabel('Learning Rate')
                axes[1, 0].set_yscale('log')
                axes[1, 0].grid(True, alpha=0.3)
                axes[1, 0].legend()
            
            # Plot 4: Alle Metriken zusammen (normalisiert)
            axes[1, 1].set_title('All Metrics (Normalized)')
            colors = ['blue', 'green', 'red', 'orange', 'purple', 'brown']
            
            for i, (metric_type, metric_list) in enumerate(metrics_by_type.items()):
                if len(metric_list) > 1:
                    epochs = [m.epoch for m in metric_list]
                    values = [m.value for m in metric_list]
                    
                    # Normalisierung
                    min_val, max_val = min(values), max(values)
                    if max_val > min_val:
                        normalized_values = [(v - min_val) / (max_val - min_val) for v in values]
                    else:
                        normalized_values = [0.5] * len(values)
                    
                    color = colors[i % len(colors)]
                    axes[1, 1].plot(epochs, normalized_values, color=color, 
                                   linewidth=2, label=metric_type.value, alpha=0.7)
            
            axes[1, 1].set_xlabel('Epoch')
            axes[1, 1].set_ylabel('Normalized Value')
            axes[1, 1].grid(True, alpha=0.3)
            axes[1, 1].legend()
            
            # Layout anpassen
            plt.tight_layout()
            
            # Report speichern
            report_file = self.plots_directory / f"training_report_{session_id}.png"
            plt.savefig(report_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.logger.info(f"Training report generated: {report_file}")
            
            return report_file
            
        except Exception as e:
            self.logger.error(f"Error generating training report: {e}")
            return None
    
    def compare_sessions(self, session_ids: List[str]) -> Optional[Path]:
        """Vergleiche mehrere Training-Sessions"""
        
        if not self.enable_visualization or not PLOTTING_AVAILABLE:
            return None
        
        try:
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('Training Sessions Comparison', fontsize=16)
            
            colors = ['blue', 'green', 'red', 'orange', 'purple', 'brown']
            
            for i, session_id in enumerate(session_ids):
                metrics = self.session_metrics.get(session_id, [])
                if not metrics:
                    continue
                
                color = colors[i % len(colors)]
                
                # Loss-Vergleich
                loss_metrics = [m for m in metrics if m.metric_type == MetricType.LOSS]
                if loss_metrics:
                    epochs = [m.epoch for m in loss_metrics]
                    values = [m.value for m in loss_metrics]
                    axes[0, 0].plot(epochs, values, color=color, linewidth=2, 
                                   label=f'{session_id}', alpha=0.7)
                
                # Accuracy-Vergleich
                acc_metrics = [m for m in metrics if m.metric_type == MetricType.ACCURACY]
                if acc_metrics:
                    epochs = [m.epoch for m in acc_metrics]
                    values = [m.value for m in acc_metrics]
                    axes[0, 1].plot(epochs, values, color=color, linewidth=2, 
                                   label=f'{session_id}', alpha=0.7)
            
            # Plot-Konfiguration
            axes[0, 0].set_title('Loss Comparison')
            axes[0, 0].set_xlabel('Epoch')
            axes[0, 0].set_ylabel('Loss')
            axes[0, 0].grid(True, alpha=0.3)
            axes[0, 0].legend()
            
            axes[0, 1].set_title('Accuracy Comparison')
            axes[0, 1].set_xlabel('Epoch')
            axes[0, 1].set_ylabel('Accuracy')
            axes[0, 1].grid(True, alpha=0.3)
            axes[0, 1].legend()
            
            # Session-Statistiken
            session_stats = []
            for session_id in session_ids:
                progress = self.get_session_progress(session_id)
                if 'error' not in progress:
                    session_stats.append({
                        'session_id': session_id,
                        'epochs': progress['session']['current_epoch'],
                        'best_metric': progress['session']['best_metric_value']
                    })
            
            # Statistiken-Tabelle
            if session_stats:
                axes[1, 0].axis('tight')
                axes[1, 0].axis('off')
                
                table_data = []
                for stat in session_stats:
                    table_data.append([
                        stat['session_id'][:10] + '...' if len(stat['session_id']) > 10 else stat['session_id'],
                        str(stat['epochs']),
                        f"{stat['best_metric']:.4f}" if stat['best_metric'] else "N/A"
                    ])
                
                table = axes[1, 0].table(cellText=table_data,
                                       colLabels=['Session ID', 'Epochs', 'Best Metric'],
                                       cellLoc='center',
                                       loc='center')
                table.auto_set_font_size(False)
                table.set_fontsize(10)
                axes[1, 0].set_title('Session Statistics')
            
            # Performance-Vergleich
            axes[1, 1].set_title('Training Speed Comparison')
            session_names = []
            speeds = []
            
            for session_id in session_ids:
                progress = self.get_session_progress(session_id)
                if 'error' not in progress and progress.get('training_speed'):
                    session_names.append(session_id[:8] + '...' if len(session_id) > 8 else session_id)
                    speeds.append(progress['training_speed']['epochs_per_hour'])
            
            if session_names and speeds:
                bars = axes[1, 1].bar(session_names, speeds, color=colors[:len(session_names)])
                axes[1, 1].set_ylabel('Epochs per Hour')
                axes[1, 1].tick_params(axis='x', rotation=45)
                
                # Werte auf Balken anzeigen
                for bar, speed in zip(bars, speeds):
                    height = bar.get_height()
                    axes[1, 1].text(bar.get_x() + bar.get_width()/2., height,
                                   f'{speed:.2f}', ha='center', va='bottom')
            
            plt.tight_layout()
            
            # Vergleichs-Report speichern
            comparison_file = self.plots_directory / f"session_comparison_{int(time.time())}.png"
            plt.savefig(comparison_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.logger.info(f"Session comparison generated: {comparison_file}")
            
            return comparison_file
            
        except Exception as e:
            self.logger.error(f"Error comparing sessions: {e}")
            return None
    
    def add_epoch_callback(self, callback: Callable):
        """Füge Epoch-Callback hinzu"""
        self.epoch_callbacks.append(callback)
    
    def add_checkpoint_callback(self, callback: Callable):
        """Füge Checkpoint-Callback hinzu"""
        self.checkpoint_callbacks.append(callback)
    
    def add_early_stopping_callback(self, callback: Callable):
        """Füge Early-Stopping-Callback hinzu"""
        self.early_stopping_callbacks.append(callback)
    
    def export_session_data(self, session_id: str, format: str = "json") -> Optional[Path]:
        """Exportiere Session-Daten"""
        
        try:
            # Session und Metriken sammeln
            session_data = self.get_session_progress(session_id)
            if 'error' in session_data:
                return None
            
            metrics = self.session_metrics.get(session_id, [])
            checkpoints = self.session_checkpoints.get(session_id, [])
            
            export_data = {
                "session": session_data,
                "metrics": [m.to_dict() for m in metrics],
                "checkpoints": [c.to_dict() for c in checkpoints],
                "export_timestamp": datetime.now().isoformat()
            }
            
            # Export basierend auf Format
            if format.lower() == "json":
                export_file = self.output_directory / f"export_{session_id}.json"
                with open(export_file, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
            
            elif format.lower() == "pickle":
                export_file = self.output_directory / f"export_{session_id}.pkl"
                with open(export_file, 'wb') as f:
                    pickle.dump(export_data, f)
            
            else:
                self.logger.error(f"Unsupported export format: {format}")
                return None
            
            self.logger.info(f"Session data exported: {export_file}")
            
            return export_file
            
        except Exception as e:
            self.logger.error(f"Error exporting session data: {e}")
            return None
    
    def get_tracker_statistics(self) -> Dict[str, Any]:
        """Erhalte Tracker-Statistiken"""
        
        try:
            # Aktuelle Sessions
            active_sessions_info = {}
            for session_id, session in self.active_sessions.items():
                active_sessions_info[session_id] = {
                    "model_name": session.model_name,
                    "current_epoch": session.current_epoch,
                    "total_epochs": session.total_epochs,
                    "phase": session.phase.value,
                    "best_metric": session.best_metric_value
                }
            
            # Completed Sessions
            completed_sessions_info = []
            for session in self.completed_sessions[-10:]:  # Letzte 10
                training_duration = session.end_time - session.start_time if session.end_time else timedelta(0)
                completed_sessions_info.append({
                    "session_id": session.session_id,
                    "model_name": session.model_name,
                    "duration": str(training_duration),
                    "final_phase": session.phase.value,
                    "total_epochs": session.current_epoch,
                    "best_metric": session.best_metric_value
                })
            
            return {
                "timestamp": datetime.now().isoformat(),
                "tracker_config": {
                    "tracking_enabled": self.tracking_enabled,
                    "save_checkpoints": self.save_checkpoints,
                    "enable_early_stopping": self.enable_early_stopping,
                    "enable_visualization": self.enable_visualization,
                    "enable_tensorboard": self.enable_tensorboard,
                    "enable_wandb": self.enable_wandb
                },
                "statistics": dict(self.stats),
                "active_sessions": active_sessions_info,
                "recent_completed_sessions": completed_sessions_info,
                "total_metrics_logged": sum(len(metrics) for metrics in self.session_metrics.values()),
                "total_checkpoints": sum(len(checkpoints) for checkpoints in self.session_checkpoints.values()),
                "output_directory": str(self.output_directory)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting tracker statistics: {e}")
            return {"error": str(e)}
    
    def cleanup(self):
        """Cleanup Tracker-Ressourcen"""
        
        try:
            # Beende alle aktiven Sessions
            for session_id in list(self.active_sessions.keys()):
                self.end_training_session(session_id, TrainingPhase.COMPLETED)
            
            # Stoppe Monitoring
            if self.monitoring_active:
                self.monitoring_active = False
                self.stop_event.set()
                
                if self.monitoring_thread:
                    self.monitoring_thread.join(timeout=5.0)
            
            # Cleanup External Integrations
            for writer in self.tensorboard_writers.values():
                writer.close()
            self.tensorboard_writers.clear()
            
            for run in self.wandb_runs.values():
                wandb.finish()
            self.wandb_runs.clear()
            
            self.logger.info("TrainingProgressTracker cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during tracker cleanup: {e}")


# Utility-Funktionen
def create_training_session_config(model_name: str, total_epochs: int,
                                 optimization_goal: OptimizationGoal = OptimizationGoal.MINIMIZE_LOSS,
                                 **kwargs) -> Dict[str, Any]:
    """Erstelle Training-Session-Konfiguration"""
    
    return {
        "model_name": model_name,
        "total_epochs": total_epochs,
        "optimization_goal": optimization_goal,
        "early_stopping_patience": kwargs.get("early_stopping_patience", 10),
        "checkpoint_frequency": kwargs.get("checkpoint_frequency", 5),
        "learning_rate": kwargs.get("learning_rate", 0.001),
        "batch_size": kwargs.get("batch_size", 32),
        "optimizer": kwargs.get("optimizer", "adam"),
        "loss_function": kwargs.get("loss_function", "mse"),
        **kwargs
    }


def setup_tensorboard_integration(log_dir: str) -> Dict[str, Any]:
    """Setup TensorBoard-Integration"""
    
    if not TENSORBOARD_AVAILABLE:
        return {"error": "TensorBoard not available"}
    
    return {
        "enable_tensorboard": True,
        "tensorboard_log_dir": log_dir,
        "tensorboard_comment": f"AI_Optimizer_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    }


def setup_wandb_integration(project_name: str, entity: Optional[str] = None) -> Dict[str, Any]:
    """Setup Weights & Biases Integration"""
    
    if not WANDB_AVAILABLE:
        return {"error": "Weights & Biases not available"}
    
    return {
        "enable_wandb": True,
        "wandb_project": project_name,
        "wandb_entity": entity,
        "wandb_tags": ["ai_indicator_optimizer", "trading", "ml"]
    }