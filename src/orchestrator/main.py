"""
Orchestrator - FinPattern-Engine

Central controller that manages the execution flow of all modules
using a state machine pattern.
"""

import yaml
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from statemachine import StateMachine, State
import click

# Import modules
from src.modules.data_ingest import DataIngest


class FinPatternOrchestrator(StateMachine):
    """
    State machine orchestrator for the FinPattern-Engine pipeline.
    
    States represent different phases of the pipeline execution.
    """
    
    # Define states
    idle = State('Idle', initial=True)
    data_ingesting = State('DataIngesting')
    labeling = State('Labeling')
    feature_engineering = State('FeatureEngineering')
    splitting = State('Splitting')
    pattern_searching = State('PatternSearching')
    parameter_tuning = State('ParameterTuning')
    backtesting = State('Backtesting')
    validating = State('Validating')
    exporting = State('Exporting')
    reporting = State('Reporting')
    completed = State('Completed')
    failed = State('Failed')
    
    # Define transitions
    start = idle.to(data_ingesting)
    ingest_complete = data_ingesting.to(labeling)
    label_complete = labeling.to(feature_engineering)
    feature_complete = feature_engineering.to(splitting)
    split_complete = splitting.to(pattern_searching)
    search_complete = pattern_searching.to(parameter_tuning)
    tuning_complete = parameter_tuning.to(backtesting)
    backtest_complete = backtesting.to(validating)
    validation_complete = validating.to(exporting)
    export_complete = exporting.to(reporting)
    report_complete = reporting.to(completed)
    
    # Error transitions
    error = (
        data_ingesting.to(failed) |
        labeling.to(failed) |
        feature_engineering.to(failed) |
        splitting.to(failed) |
        pattern_searching.to(failed) |
        parameter_tuning.to(failed) |
        backtesting.to(failed) |
        validating.to(failed) |
        exporting.to(failed) |
        reporting.to(failed)
    )
    
    def __init__(self, config_path: str):
        """Initialize orchestrator with configuration."""
        super().__init__()
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.run_id = self.config.get('run_id', f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        self.output_dir = Path(self.config.get('output', {}).get('base_dir', './runs')) / self.run_id
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self._setup_logging()
        
        # Initialize modules
        self.modules = {
            'data_ingest': DataIngest(),
            # TODO: Add other modules as they are implemented
        }
        
        # Pipeline state
        self.pipeline_data = {}
        self.module_outputs = {}
        
        self.logger.info(f"Orchestrator initialized for run: {self.run_id}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        log_level = self.config.get('log_level', 'INFO')
        log_file = self.output_dir / 'orchestrator.log'
        
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    def run_pipeline(self) -> Dict[str, Any]:
        """Execute the complete pipeline."""
        try:
            self.logger.info("Starting FinPattern-Engine pipeline")
            self.start()
            
            # Execute pipeline steps
            while not self.current_state.id in ['completed', 'failed']:
                self._execute_current_step()
            
            if self.current_state.id == 'completed':
                self.logger.info("Pipeline completed successfully")
                return self._generate_final_report()
            else:
                self.logger.error("Pipeline failed")
                raise RuntimeError("Pipeline execution failed")
                
        except Exception as e:
            self.logger.error(f"Pipeline error: {str(e)}")
            self.error()
            raise
    
    def _execute_current_step(self) -> None:
        """Execute the current pipeline step."""
        state_id = self.current_state.id
        self.logger.info(f"Executing step: {state_id}")
        
        try:
            if state_id == 'data_ingesting':
                self._run_data_ingest()
                self.ingest_complete()
                
            elif state_id == 'labeling':
                self._run_labeling()
                self.label_complete()
                
            elif state_id == 'feature_engineering':
                self._run_feature_engineering()
                self.feature_complete()
                
            elif state_id == 'splitting':
                self._run_splitting()
                self.split_complete()
                
            elif state_id == 'pattern_searching':
                self._run_pattern_searching()
                self.search_complete()
                
            elif state_id == 'parameter_tuning':
                self._run_parameter_tuning()
                self.tuning_complete()
                
            elif state_id == 'backtesting':
                self._run_backtesting()
                self.backtest_complete()
                
            elif state_id == 'validating':
                self._run_validating()
                self.validation_complete()
                
            elif state_id == 'exporting':
                self._run_exporting()
                self.export_complete()
                
            elif state_id == 'reporting':
                self._run_reporting()
                self.report_complete()
                
        except Exception as e:
            self.logger.error(f"Step {state_id} failed: {str(e)}")
            self.error()
            raise
    
    def _run_data_ingest(self) -> None:
        """Execute data ingestion step."""
        config = self.config.get('data_ingest', {})
        config['out_dir'] = str(self.output_dir / 'data_ingest')
        
        result = self.modules['data_ingest'].run(config)
        self.module_outputs['data_ingest'] = result
        
        self.logger.info("Data ingestion completed")
    
    def _run_labeling(self) -> None:
        """Execute labeling step."""
        # TODO: Implement when labeling module is ready
        self.logger.info("Labeling step - TODO: Implement")
        self.module_outputs['labeling'] = {}
    
    def _run_feature_engineering(self) -> None:
        """Execute feature engineering step."""
        # TODO: Implement when feature engine module is ready
        self.logger.info("Feature engineering step - TODO: Implement")
        self.module_outputs['feature_engineering'] = {}
    
    def _run_splitting(self) -> None:
        """Execute data splitting step."""
        # TODO: Implement when splitter module is ready
        self.logger.info("Data splitting step - TODO: Implement")
        self.module_outputs['splitting'] = {}
    
    def _run_pattern_searching(self) -> None:
        """Execute pattern searching step."""
        # TODO: Implement when search modules are ready
        self.logger.info("Pattern searching step - TODO: Implement")
        self.module_outputs['pattern_searching'] = {}
    
    def _run_parameter_tuning(self) -> None:
        """Execute parameter tuning step."""
        # TODO: Implement when RL tuner module is ready
        self.logger.info("Parameter tuning step - TODO: Implement")
        self.module_outputs['parameter_tuning'] = {}
    
    def _run_backtesting(self) -> None:
        """Execute backtesting step."""
        # TODO: Implement when backtester module is ready
        self.logger.info("Backtesting step - TODO: Implement")
        self.module_outputs['backtesting'] = {}
    
    def _run_validating(self) -> None:
        """Execute validation step."""
        # TODO: Implement when validator module is ready
        self.logger.info("Validation step - TODO: Implement")
        self.module_outputs['validating'] = {}
    
    def _run_exporting(self) -> None:
        """Execute export step."""
        # TODO: Implement when exporter module is ready
        self.logger.info("Export step - TODO: Implement")
        self.module_outputs['exporting'] = {}
    
    def _run_reporting(self) -> None:
        """Execute reporting step."""
        # TODO: Implement when reporter module is ready
        self.logger.info("Reporting step - TODO: Implement")
        self.module_outputs['reporting'] = {}
    
    def _generate_final_report(self) -> Dict[str, Any]:
        """Generate final pipeline report."""
        report = {
            'run_id': self.run_id,
            'config_path': str(self.config_path),
            'output_dir': str(self.output_dir),
            'status': 'completed',
            'timestamp': datetime.now().isoformat(),
            'module_outputs': self.module_outputs
        }
        
        # Save report
        report_path = self.output_dir / 'pipeline_report.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report


@click.command()
@click.option('--config', '-c', required=True, help='Path to configuration YAML file')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def main(config: str, verbose: bool):
    """
    FinPattern-Engine Orchestrator
    
    Execute the complete pattern recognition pipeline.
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        orchestrator = FinPatternOrchestrator(config)
        result = orchestrator.run_pipeline()
        
        click.echo(f"Pipeline completed successfully!")
        click.echo(f"Run ID: {result['run_id']}")
        click.echo(f"Output directory: {result['output_dir']}")
        
    except Exception as e:
        click.echo(f"Pipeline failed: {str(e)}", err=True)
        exit(1)


if __name__ == "__main__":
    main()
