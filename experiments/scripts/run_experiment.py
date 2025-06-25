#!/usr/bin/env python3
"""
Main experiment runner for PM Agent
Executes individual experiments with specified configurations
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import click
import yaml
import pandas as pd
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from dotenv import load_dotenv

from experiments.baseline import BaselineExperiment
from experiments.failure_recovery import FailureRecoveryExperiment
from experiments.scalability import ScalabilityExperiment
from experiments.real_world import RealWorldExperiment
from experiments.coordination import CoordinationExperiment
from experiments.collaboration import CollaborationExperiment
from experiments.cost_benefit import CostBenefitExperiment
from experiments.integration import IntegrationExperiment

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
console = Console()

class ExperimentRunner:
    """Main experiment runner"""
    
    EXPERIMENT_CLASSES = {
        'baseline': BaselineExperiment,
        'failure_recovery': FailureRecoveryExperiment,
        'scalability': ScalabilityExperiment,
        'real_world': RealWorldExperiment,
        'coordination': CoordinationExperiment,
        'collaboration': CollaborationExperiment,
        'cost_benefit': CostBenefitExperiment,
        'integration': IntegrationExperiment,
    }
    
    def __init__(self, config_path: str = "config/experiment_config.yaml"):
        self.config = self._load_config(config_path)
        self.results_dir = Path("./results")
        self.results = {}
        
    def _load_config(self, config_path: str) -> Dict:
        """Load experiment configuration"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    async def run_experiment(self, experiment_name: str, **kwargs) -> Dict[str, Any]:
        """Run a single experiment"""
        if experiment_name not in self.EXPERIMENT_CLASSES:
            raise ValueError(f"Unknown experiment: {experiment_name}")
        
        console.print(f"\n[bold blue]Running {experiment_name} experiment...[/bold blue]")
        
        # Get experiment class and config
        experiment_class = self.EXPERIMENT_CLASSES[experiment_name]
        experiment_config = self.config['experiments'].get(experiment_name, {})
        
        # Merge kwargs with config
        experiment_config.update(kwargs)
        
        # Initialize experiment
        experiment = experiment_class(experiment_config)
        
        # Run experiment with progress tracking
        start_time = datetime.now()
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=console,
            ) as progress:
                # Create progress task
                task = progress.add_task(f"Running {experiment_name}...", total=100)
                
                # Update callback for experiment
                def update_progress(percent: float, status: str):
                    progress.update(task, completed=percent, description=status)
                
                # Run experiment
                results = await experiment.run(progress_callback=update_progress)
                
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Store results
            results['metadata'] = {
                'experiment': experiment_name,
                'started_at': start_time.isoformat(),
                'completed_at': end_time.isoformat(),
                'duration_seconds': duration,
                'status': 'completed'
            }
            
            self._save_results(experiment_name, results)
            self._display_results(experiment_name, results)
            
            return results
            
        except Exception as e:
            logger.error(f"Experiment {experiment_name} failed: {e}")
            console.print(f"[red]✗ Experiment failed: {e}[/red]")
            
            results = {
                'metadata': {
                    'experiment': experiment_name,
                    'started_at': start_time.isoformat(),
                    'completed_at': datetime.now().isoformat(),
                    'status': 'failed',
                    'error': str(e)
                }
            }
            self._save_results(experiment_name, results)
            return results
    
    def _save_results(self, experiment_name: str, results: Dict[str, Any]):
        """Save experiment results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{experiment_name}_{timestamp}.json"
        filepath = self.results_dir / experiment_name / filename
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to {filepath}")
    
    def _display_results(self, experiment_name: str, results: Dict[str, Any]):
        """Display experiment results in a nice format"""
        console.print(f"\n[bold green]✓ {experiment_name} experiment completed![/bold green]")
        
        # Create results table
        table = Table(title=f"{experiment_name.replace('_', ' ').title()} Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        
        # Add key metrics based on experiment type
        if experiment_name == 'baseline':
            table.add_row("Task Completion Rate", f"{results.get('completion_rate', 0):.1f}%")
            table.add_row("Average Time (min)", f"{results.get('avg_time_minutes', 0):.1f}")
            table.add_row("Total Tasks", str(results.get('total_tasks', 0)))
            table.add_row("Successful Tasks", str(results.get('successful_tasks', 0)))
            
        elif experiment_name == 'failure_recovery':
            table.add_row("Overall Recovery Rate", f"{results.get('overall_recovery_rate', 0):.1f}%")
            table.add_row("Scenarios Tested", str(results.get('scenarios_tested', 0)))
            table.add_row("Avg Recovery Time (min)", f"{results.get('avg_recovery_time', 0):.1f}")
            
        elif experiment_name == 'scalability':
            optimal = results.get('optimal_configuration', {})
            table.add_row("Optimal Agent Count", str(optimal.get('agent_count', 'N/A')))
            table.add_row("Max Throughput (tasks/hr)", str(optimal.get('tasks_per_hour', 'N/A')))
            table.add_row("Efficiency at Optimal", f"{optimal.get('efficiency', 0):.2f}")
            
        elif experiment_name == 'cost_benefit':
            roi = results.get('roi', {})
            table.add_row("30-Day ROI", roi.get('30_days', 'N/A'))
            table.add_row("Break-even Days", str(roi.get('break_even_days', 'N/A')))
            table.add_row("Total Cost", f"${results.get('total_costs', {}).get('total', 0):,.2f}")
            table.add_row("Value Delivered", f"${results.get('value_delivered', {}).get('value_usd', 0):,.2f}")
        
        console.print(table)

@click.command()
@click.option('--experiment', required=True, type=click.Choice([
    'baseline', 'failure_recovery', 'scalability', 'real_world',
    'coordination', 'collaboration', 'cost_benefit', 'integration'
]), help='Experiment to run')
@click.option('--config', default='config/experiment_config.yaml', help='Path to config file')
@click.option('--agents', type=int, help='Number of agents (overrides config)')
@click.option('--tasks', type=int, help='Number of tasks (overrides config)')
@click.option('--timeout', type=int, help='Timeout in seconds')
@click.option('--dry-run', is_flag=True, help='Show what would be run without executing')
def main(experiment: str, config: str, agents: Optional[int], tasks: Optional[int], 
         timeout: Optional[int], dry_run: bool):
    """Run PM Agent experiments"""
    
    # Load environment variables
    load_dotenv()
    
    # Check for required environment variables
    required_vars = ['PM_AGENT_API_URL']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        console.print(f"[red]Missing required environment variables: {', '.join(missing_vars)}[/red]")
        console.print("Please copy .env.example to .env and fill in the values")
        sys.exit(1)
    
    # Initialize runner
    runner = ExperimentRunner(config)
    
    # Build kwargs from command line options
    kwargs = {}
    if agents is not None:
        kwargs['agents'] = agents
    if tasks is not None:
        kwargs['tasks'] = tasks
    if timeout is not None:
        kwargs['timeout'] = timeout
    
    if dry_run:
        console.print(f"[yellow]DRY RUN: Would run {experiment} with config:[/yellow]")
        console.print(runner.config['experiments'][experiment])
        if kwargs:
            console.print(f"[yellow]Overrides: {kwargs}[/yellow]")
        return
    
    # Run experiment
    asyncio.run(runner.run_experiment(experiment, **kwargs))

if __name__ == "__main__":
    main()