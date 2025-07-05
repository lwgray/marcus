"""
Multi-agent coordination benchmark for Marcus MCP server
"""
import asyncio
import time
import json
from typing import List, Dict, Any
import random
from datetime import datetime
import statistics
from mcp_test_client import MCPTestClient


class MultiAgentBenchmark:
    """Benchmark Marcus with multiple concurrent agents"""
    
    def __init__(self, num_agents: int, tasks_per_agent: int):
        self.num_agents = num_agents
        self.tasks_per_agent = tasks_per_agent
        self.agents: List[MCPTestClient] = []
        self.results = {
            "agents": {},
            "overall": {},
            "timeline": []
        }
    
    async def simulate_agent_work(self, agent_id: str, agent_num: int) -> Dict[str, Any]:
        """Simulate a single agent doing work"""
        client = MCPTestClient()
        agent_results = {
            "agent_id": agent_id,
            "tasks_requested": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "blockers_reported": 0,
            "total_time_ms": 0,
            "task_times": []
        }
        
        # Register agent with random capabilities
        capabilities = random.sample(
            ["python", "javascript", "testing", "frontend", "backend", "database"],
            k=random.randint(2, 4)
        )
        await client.register_agent(agent_id, capabilities)
        
        # Work on tasks
        for i in range(self.tasks_per_agent):
            task_start = time.time()
            
            try:
                # Request task
                result = await client.request_task()
                agent_results["tasks_requested"] += 1
                
                if "error" not in result and result.get("result", {}).get("task_id"):
                    task_id = result["result"]["task_id"]
                    
                    # Simulate work with progress updates
                    for progress in [25, 50, 75]:
                        await asyncio.sleep(random.uniform(0.1, 0.3))
                        await client.update_progress(
                            task_id, 
                            progress, 
                            f"Agent {agent_num} at {progress}%"
                        )
                    
                    # Randomly report blockers (10% chance)
                    if random.random() < 0.1:
                        await client.report_blocker(
                            task_id,
                            f"Test blocker from agent {agent_num}"
                        )
                        agent_results["blockers_reported"] += 1
                    
                    # Complete task
                    await asyncio.sleep(random.uniform(0.1, 0.2))
                    await client.complete_task(
                        task_id,
                        {
                            "completed_by": agent_id,
                            "quality_score": random.uniform(0.8, 1.0)
                        }
                    )
                    agent_results["tasks_completed"] += 1
                    
                    task_time = (time.time() - task_start) * 1000
                    agent_results["task_times"].append(task_time)
                    
                else:
                    # No task available or error
                    agent_results["tasks_failed"] += 1
                    await asyncio.sleep(1)  # Wait before retry
                    
            except Exception as e:
                print(f"Agent {agent_id} error: {e}")
                agent_results["tasks_failed"] += 1
        
        agent_results["total_time_ms"] = sum(agent_results["task_times"])
        agent_results["avg_task_time_ms"] = (
            statistics.mean(agent_results["task_times"]) 
            if agent_results["task_times"] else 0
        )
        
        # Store client results
        agent_results["mcp_metrics"] = client.get_summary()
        
        return agent_results
    
    async def run_benchmark(self) -> Dict[str, Any]:
        """Run the multi-agent benchmark"""
        print(f"Starting multi-agent benchmark with {self.num_agents} agents...")
        print(f"Each agent will attempt {self.tasks_per_agent} tasks")
        
        start_time = time.time()
        
        # Create agent tasks
        agent_tasks = []
        for i in range(self.num_agents):
            agent_id = f"benchmark-agent-{i}"
            agent_task = self.simulate_agent_work(agent_id, i)
            agent_tasks.append(agent_task)
        
        # Run all agents concurrently
        agent_results = await asyncio.gather(*agent_tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Process results
        total_completed = 0
        total_failed = 0
        total_blockers = 0
        all_task_times = []
        
        for i, result in enumerate(agent_results):
            if isinstance(result, Exception):
                print(f"Agent {i} failed with exception: {result}")
                self.results["agents"][f"agent-{i}"] = {"error": str(result)}
            else:
                agent_id = result["agent_id"]
                self.results["agents"][agent_id] = result
                total_completed += result["tasks_completed"]
                total_failed += result["tasks_failed"]
                total_blockers += result["blockers_reported"]
                all_task_times.extend(result["task_times"])
        
        # Calculate overall metrics
        self.results["overall"] = {
            "num_agents": self.num_agents,
            "tasks_per_agent": self.tasks_per_agent,
            "total_tasks_attempted": self.num_agents * self.tasks_per_agent,
            "total_tasks_completed": total_completed,
            "total_tasks_failed": total_failed,
            "total_blockers_reported": total_blockers,
            "completion_rate": total_completed / (self.num_agents * self.tasks_per_agent) * 100,
            "total_time_seconds": total_time,
            "tasks_per_second": total_completed / total_time if total_time > 0 else 0,
            "average_task_time_ms": statistics.mean(all_task_times) if all_task_times else 0,
            "median_task_time_ms": statistics.median(all_task_times) if all_task_times else 0,
            "task_time_std_dev": statistics.stdev(all_task_times) if len(all_task_times) > 1 else 0
        }
        
        return self.results
    
    def save_results(self, filename: str):
        """Save benchmark results to file"""
        self.results["metadata"] = {
            "timestamp": datetime.now().isoformat(),
            "benchmark_type": "multi_agent",
            "num_agents": self.num_agents,
            "tasks_per_agent": self.tasks_per_agent
        }
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
    
    def print_summary(self):
        """Print a summary of the benchmark results"""
        overall = self.results["overall"]
        
        print("\n" + "="*50)
        print("MULTI-AGENT BENCHMARK RESULTS")
        print("="*50)
        print(f"Agents: {overall['num_agents']}")
        print(f"Tasks per agent: {overall['tasks_per_agent']}")
        print(f"Total tasks attempted: {overall['total_tasks_attempted']}")
        print(f"Total tasks completed: {overall['total_tasks_completed']}")
        print(f"Completion rate: {overall['completion_rate']:.1f}%")
        print(f"Total time: {overall['total_time_seconds']:.2f} seconds")
        print(f"Tasks per second: {overall['tasks_per_second']:.2f}")
        print(f"Average task time: {overall['average_task_time_ms']:.2f}ms")
        print(f"Median task time: {overall['median_task_time_ms']:.2f}ms")
        print(f"Blockers reported: {overall['total_blockers_reported']}")
        
        # Show per-agent statistics
        print("\nPer-Agent Performance:")
        print("-"*50)
        for agent_id, stats in self.results["agents"].items():
            if "error" not in stats:
                print(f"{agent_id}: {stats['tasks_completed']}/{stats['tasks_requested']} completed, "
                      f"avg time: {stats.get('avg_task_time_ms', 0):.2f}ms")


async def run_scaling_benchmark():
    """Run benchmarks with increasing number of agents"""
    agent_counts = [1, 5, 10, 20, 50]
    scaling_results = {}
    
    for num_agents in agent_counts:
        print(f"\n\nRunning benchmark with {num_agents} agents...")
        benchmark = MultiAgentBenchmark(num_agents=num_agents, tasks_per_agent=5)
        
        try:
            results = await benchmark.run_benchmark()
            benchmark.print_summary()
            benchmark.save_results(f"multi_agent_benchmark_{num_agents}_agents.json")
            
            scaling_results[num_agents] = {
                "tasks_per_second": results["overall"]["tasks_per_second"],
                "completion_rate": results["overall"]["completion_rate"],
                "avg_task_time": results["overall"]["average_task_time_ms"]
            }
        except Exception as e:
            print(f"Benchmark failed for {num_agents} agents: {e}")
            scaling_results[num_agents] = {"error": str(e)}
    
    # Save scaling results
    with open("scaling_benchmark_results.json", 'w') as f:
        json.dump({
            "scaling_results": scaling_results,
            "timestamp": datetime.now().isoformat()
        }, f, indent=2)
    
    print("\n\nSCALING SUMMARY:")
    print("Agents | Tasks/sec | Completion % | Avg Time (ms)")
    print("-"*50)
    for agents, metrics in scaling_results.items():
        if "error" not in metrics:
            print(f"{agents:6d} | {metrics['tasks_per_second']:9.2f} | "
                  f"{metrics['completion_rate']:11.1f} | {metrics['avg_task_time']:13.2f}")


if __name__ == "__main__":
    # Run single benchmark
    benchmark = MultiAgentBenchmark(num_agents=10, tasks_per_agent=10)
    asyncio.run(benchmark.run_benchmark())
    benchmark.print_summary()
    benchmark.save_results("multi_agent_benchmark_results.json")
    
    # Uncomment to run scaling benchmark
    # asyncio.run(run_scaling_benchmark())