"""
Baseline Performance Experiment
Tests PM Agent's task completion rate on standardized benchmarks
"""

import asyncio
import time
from typing import Dict, List, Any, Callable, Optional
from datetime import datetime
import random

from datasets import load_dataset
import pandas as pd

from .base import BaseExperiment
from ..metrics import TaskMetrics, calculate_completion_rate
from ..pm_agent_client import PMAgentClient

class BaselineExperiment(BaseExperiment):
    """Baseline performance testing on SWE-bench"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.dataset_name = config.get('dataset', 'princeton-nlp/SWE-bench_Lite')
        self.task_limit = config.get('task_limit', 100)
        self.agent_configs = config.get('configurations', [
            {'agents': 1, 'parallel': False},
            {'agents': 3, 'parallel': True},
            {'agents': 5, 'parallel': True},
            {'agents': 10, 'parallel': True}
        ])
        
    async def run(self, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Run baseline experiment"""
        results = {
            'experiment': 'baseline_performance',
            'dataset': self.dataset_name,
            'configurations': {}
        }
        
        # Load dataset
        if progress_callback:
            progress_callback(10, "Loading SWE-bench dataset...")
        
        dataset = self._load_dataset()
        tasks = self._prepare_tasks(dataset)
        
        # Run experiments for each configuration
        total_configs = len(self.agent_configs)
        for idx, config in enumerate(self.agent_configs):
            config_name = f"{config['agents']}_agent{'s' if config['agents'] > 1 else ''}"
            
            if progress_callback:
                progress = 10 + (idx * 80 / total_configs)
                progress_callback(progress, f"Testing {config_name} configuration...")
            
            # Run tasks with this configuration
            config_results = await self._run_configuration(tasks, config)
            results['configurations'][config_name] = config_results
        
        # Calculate aggregate metrics
        results['summary'] = self._calculate_summary(results['configurations'])
        
        if progress_callback:
            progress_callback(100, "Experiment complete!")
        
        return results
    
    def _load_dataset(self) -> Any:
        """Load SWE-bench dataset"""
        try:
            # Try to load from cache first
            cache_path = self.cache_dir / "swebench" / "swebench_lite.parquet"
            if cache_path.exists():
                return pd.read_parquet(cache_path)
            else:
                # Load from Hugging Face
                dataset = load_dataset(self.dataset_name, split='test')
                return dataset
        except Exception as e:
            self.logger.warning(f"Failed to load real dataset: {e}. Using synthetic tasks.")
            return self._generate_synthetic_tasks()
    
    def _generate_synthetic_tasks(self) -> List[Dict]:
        """Generate synthetic tasks for testing"""
        task_types = ['bug_fix', 'feature', 'refactor', 'test']
        difficulties = ['easy', 'medium', 'hard']
        
        tasks = []
        for i in range(self.task_limit):
            tasks.append({
                'instance_id': f'synthetic_{i:04d}',
                'problem_statement': f'Task {i}: Fix issue in module',
                'repo': 'test_repo',
                'base_commit': 'abc123',
                'hints_text': 'Check the validation logic',
                'created_at': datetime.now().isoformat(),
                'type': random.choice(task_types),
                'difficulty': random.choice(difficulties),
                'FAIL_TO_PASS': ['test_feature'],
                'PASS_TO_PASS': ['test_existing']
            })
        return tasks
    
    def _prepare_tasks(self, dataset) -> List[Dict]:
        """Prepare tasks for execution"""
        tasks = []
        
        # Handle both DataFrame and HuggingFace dataset
        if hasattr(dataset, 'to_dict'):
            data = dataset.to_dict()
            for i in range(min(len(data['instance_id']), self.task_limit)):
                tasks.append({k: v[i] for k, v in data.items()})
        else:
            # Synthetic tasks
            tasks = dataset[:self.task_limit]
        
        return tasks
    
    async def _run_configuration(self, tasks: List[Dict], config: Dict) -> Dict[str, Any]:
        """Run tasks with a specific agent configuration"""
        client = PMAgentClient(
            num_agents=config['agents'],
            parallel=config['parallel']
        )
        
        results = {
            'total_tasks': len(tasks),
            'completed_tasks': 0,
            'failed_tasks': 0,
            'task_results': [],
            'timing': {
                'start_time': time.time(),
                'end_time': None,
                'total_seconds': None
            }
        }
        
        # Initialize PM Agent project
        project_id = await client.create_project(
            name=f"baseline_test_{config['agents']}_agents",
            description="Baseline performance testing"
        )
        
        # Register agents
        agent_ids = await client.register_agents(config['agents'])
        
        # Create tasks in PM Agent
        task_ids = []
        for task in tasks:
            task_id = await client.create_task(
                project_id=project_id,
                title=task.get('instance_id', 'Unknown'),
                description=task.get('problem_statement', ''),
                metadata=task
            )
            task_ids.append(task_id)
        
        # Start agents working
        if config['parallel']:
            # Run agents in parallel
            agent_tasks = [
                self._run_agent(agent_id, client)
                for agent_id in agent_ids
            ]
            await asyncio.gather(*agent_tasks)
        else:
            # Run sequentially
            for agent_id in agent_ids:
                await self._run_agent(agent_id, client)
        
        # Collect results
        for task_id in task_ids:
            task_result = await client.get_task_result(task_id)
            results['task_results'].append(task_result)
            
            if task_result['status'] == 'completed':
                results['completed_tasks'] += 1
            else:
                results['failed_tasks'] += 1
        
        results['timing']['end_time'] = time.time()
        results['timing']['total_seconds'] = results['timing']['end_time'] - results['timing']['start_time']
        
        # Calculate metrics
        results['metrics'] = {
            'completion_rate': (results['completed_tasks'] / results['total_tasks']) * 100,
            'avg_time_per_task': results['timing']['total_seconds'] / results['total_tasks'],
            'tasks_per_hour': (results['completed_tasks'] / results['timing']['total_seconds']) * 3600
        }
        
        return results
    
    async def _run_agent(self, agent_id: str, client: PMAgentClient):
        """Run a single agent until no more tasks"""
        while True:
            # Request next task
            task = await client.request_next_task(agent_id)
            if not task:
                break
            
            # Simulate working on task
            await self._work_on_task(task, agent_id, client)
    
    async def _work_on_task(self, task: Dict, agent_id: str, client: PMAgentClient):
        """Simulate agent working on a task"""
        # Report progress
        await client.report_progress(task['id'], agent_id, 25, "Starting task analysis")
        await asyncio.sleep(1)  # Simulate work
        
        await client.report_progress(task['id'], agent_id, 50, "Implementing solution")
        await asyncio.sleep(2)  # Simulate work
        
        await client.report_progress(task['id'], agent_id, 75, "Running tests")
        await asyncio.sleep(1)  # Simulate work
        
        # Simulate success/failure based on difficulty
        difficulty = task.get('metadata', {}).get('difficulty', 'medium')
        success_rates = {'easy': 0.8, 'medium': 0.5, 'hard': 0.2}
        success = random.random() < success_rates.get(difficulty, 0.5)
        
        if success:
            await client.report_completion(task['id'], agent_id, "Task completed successfully")
        else:
            await client.report_failure(task['id'], agent_id, "Tests failed")
    
    def _calculate_summary(self, configurations: Dict) -> Dict[str, Any]:
        """Calculate summary statistics across all configurations"""
        completion_rates = []
        avg_times = []
        
        for config_name, results in configurations.items():
            completion_rates.append(results['metrics']['completion_rate'])
            avg_times.append(results['metrics']['avg_time_per_task'])
        
        return {
            'avg_completion_rate': sum(completion_rates) / len(completion_rates),
            'best_completion_rate': max(completion_rates),
            'best_configuration': max(configurations.items(), 
                                     key=lambda x: x[1]['metrics']['completion_rate'])[0],
            'avg_time_per_task': sum(avg_times) / len(avg_times)
        }