#!/usr/bin/env python3
"""
Setup script for PM Agent experiments
Initializes environment, downloads datasets, and prepares infrastructure
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Dict, List

import click
import yaml
from datasets import load_dataset
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
console = Console()

class ExperimentSetup:
    """Handles experiment environment setup"""
    
    def __init__(self, config_path: str = "config/experiment_config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.data_dir = Path("./data")
        self.cache_dir = Path("./cache")
        self.results_dir = Path("./results")
        
    def _load_config(self) -> Dict:
        """Load experiment configuration"""
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def setup_directories(self):
        """Create necessary directories"""
        directories = [
            self.data_dir,
            self.cache_dir,
            self.results_dir,
            self.cache_dir / "swebench",
            self.results_dir / "baseline",
            self.results_dir / "failure_recovery",
            self.results_dir / "scalability",
            self.results_dir / "real_world",
            self.results_dir / "coordination",
            self.results_dir / "collaboration",
            self.results_dir / "cost_benefit",
            self.results_dir / "integration",
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {directory}")
    
    def download_swebench_datasets(self):
        """Download SWE-bench datasets from Hugging Face"""
        console.print("[bold blue]Downloading SWE-bench datasets...[/bold blue]")
        
        datasets_to_download = [
            ("princeton-nlp/SWE-bench_Lite", "swebench_lite"),
            ("princeton-nlp/SWE-bench_Verified", "swebench_verified"),
        ]
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            for dataset_name, save_name in datasets_to_download:
                task = progress.add_task(f"Downloading {dataset_name}...", total=None)
                
                try:
                    dataset = load_dataset(dataset_name, split='test')
                    save_path = self.cache_dir / "swebench" / f"{save_name}.parquet"
                    dataset.to_parquet(save_path)
                    
                    progress.update(task, completed=True)
                    console.print(f"[green]✓[/green] Downloaded {dataset_name} ({len(dataset)} samples)")
                except Exception as e:
                    console.print(f"[red]✗[/red] Failed to download {dataset_name}: {e}")
    
    def create_sample_tasks(self):
        """Create sample custom tasks for testing"""
        sample_tasks = [
            {
                "id": "custom_001",
                "type": "feature",
                "difficulty": "easy",
                "description": "Add input validation to user registration endpoint",
                "repository": "sample_app",
                "files": ["src/routes/auth.js", "src/validators/user.js"],
                "tests": ["test/auth.test.js"],
                "expected_changes": 3
            },
            {
                "id": "custom_002",
                "type": "bug_fix",
                "difficulty": "medium",
                "description": "Fix race condition in concurrent database updates",
                "repository": "sample_app",
                "files": ["src/db/transactions.js"],
                "tests": ["test/db/concurrent.test.js"],
                "expected_changes": 2
            },
            {
                "id": "custom_003",
                "type": "refactor",
                "difficulty": "hard",
                "description": "Refactor authentication middleware to use JWT tokens",
                "repository": "sample_app",
                "files": ["src/middleware/auth.js", "src/utils/jwt.js"],
                "tests": ["test/middleware/auth.test.js"],
                "expected_changes": 5
            }
        ]
        
        import json
        custom_tasks_path = self.data_dir / "custom_tasks.json"
        with open(custom_tasks_path, 'w') as f:
            json.dump(sample_tasks, f, indent=2)
        
        console.print(f"[green]✓[/green] Created {len(sample_tasks)} sample tasks")
    
    def setup_monitoring(self):
        """Setup Prometheus and Grafana configs"""
        prometheus_config = """
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'pm_agent_experiments'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    
  - job_name: 'node_exporter'
    static_configs:
      - targets: ['localhost:9100']
"""
        
        grafana_dashboard = {
            "dashboard": {
                "title": "PM Agent Experiment Metrics",
                "panels": [
                    {
                        "title": "Task Completion Rate",
                        "type": "graph",
                        "targets": [{"expr": "pm_agent_task_completion_rate"}]
                    },
                    {
                        "title": "Agent Utilization",
                        "type": "graph",
                        "targets": [{"expr": "pm_agent_utilization"}]
                    },
                    {
                        "title": "API Costs",
                        "type": "graph",
                        "targets": [{"expr": "pm_agent_api_costs_total"}]
                    }
                ]
            }
        }
        
        # Save configurations
        monitoring_dir = Path("./monitoring")
        monitoring_dir.mkdir(exist_ok=True)
        
        with open(monitoring_dir / "prometheus.yml", 'w') as f:
            f.write(prometheus_config)
        
        import json
        with open(monitoring_dir / "grafana_dashboard.json", 'w') as f:
            json.dump(grafana_dashboard, f, indent=2)
        
        console.print("[green]✓[/green] Created monitoring configurations")
    
    def setup_database(self):
        """Initialize experiment database"""
        from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, DateTime, JSON
        from sqlalchemy.sql import func
        
        # Create database engine
        db_url = os.getenv("DATABASE_URL", "sqlite:///experiments.db")
        engine = create_engine(db_url)
        metadata = MetaData()
        
        # Define tables
        experiments_table = Table(
            'experiments',
            metadata,
            Column('id', Integer, primary_key=True),
            Column('name', String(100)),
            Column('started_at', DateTime, default=func.now()),
            Column('completed_at', DateTime),
            Column('status', String(50)),
            Column('config', JSON),
            Column('results', JSON),
        )
        
        task_results_table = Table(
            'task_results',
            metadata,
            Column('id', Integer, primary_key=True),
            Column('experiment_id', Integer),
            Column('task_id', String(100)),
            Column('agent_id', String(50)),
            Column('started_at', DateTime),
            Column('completed_at', DateTime),
            Column('status', String(50)),
            Column('attempts', Integer),
            Column('error_message', String(500)),
            Column('metrics', JSON),
        )
        
        # Create tables
        metadata.create_all(engine)
        console.print("[green]✓[/green] Database initialized")
    
    async def verify_pm_agent_connection(self):
        """Verify connection to PM Agent API"""
        import aiohttp
        
        pm_agent_url = os.getenv("PM_AGENT_API_URL", "http://localhost:8000")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{pm_agent_url}/health") as response:
                    if response.status == 200:
                        console.print("[green]✓[/green] PM Agent API connection verified")
                    else:
                        console.print(f"[yellow]⚠[/yellow] PM Agent API returned status {response.status}")
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to connect to PM Agent API: {e}")
            console.print("[yellow]Make sure PM Agent is running on {pm_agent_url}[/yellow]")

@click.command()
@click.option('--skip-downloads', is_flag=True, help='Skip downloading datasets')
@click.option('--skip-db', is_flag=True, help='Skip database setup')
@click.option('--config', default='config/experiment_config.yaml', help='Path to config file')
def main(skip_downloads: bool, skip_db: bool, config: str):
    """Setup PM Agent experiment environment"""
    console.print("[bold]Setting up PM Agent experiments...[/bold]")
    
    # Load environment variables
    load_dotenv()
    
    # Initialize setup
    setup = ExperimentSetup(config)
    
    # Create directories
    setup.setup_directories()
    
    # Download datasets
    if not skip_downloads:
        setup.download_swebench_datasets()
    
    # Create sample tasks
    setup.create_sample_tasks()
    
    # Setup monitoring
    setup.setup_monitoring()
    
    # Setup database
    if not skip_db:
        setup.setup_database()
    
    # Verify PM Agent connection
    asyncio.run(setup.verify_pm_agent_connection())
    
    console.print("\n[bold green]✓ Setup complete![/bold green]")
    console.print("\nNext steps:")
    console.print("1. Copy .env.example to .env and fill in your API keys")
    console.print("2. Run experiments with: python scripts/run_experiments.py")
    console.print("3. View results at: http://localhost:3000 (Grafana)")

if __name__ == "__main__":
    main()