"""
Stress testing for Marcus MCP server
Tests performance limits and degradation patterns
"""
import asyncio
import time
import psutil
import json
from datetime import datetime
from typing import Dict, List, Any
import aiohttp
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
import signal
import sys


class StressTestRunner:
    """Run stress tests on Marcus MCP server"""
    
    def __init__(self, host: str = "localhost", port: int = 3333):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.results = {
            "stages": [],
            "system_metrics": [],
            "breaking_point": None
        }
        self.monitoring = True
        self.start_time = None
    
    async def send_mcp_request(self, session: aiohttp.ClientSession, method: str, params: Dict) -> Dict:
        """Send a single MCP request"""
        command = {
            "jsonrpc": "2.0",
            "id": str(time.time()),
            "method": method,
            "params": params
        }
        
        try:
            async with session.post(
                f"{self.base_url}/mcp",
                json=command,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                return await response.json()
        except asyncio.TimeoutError:
            return {"error": {"message": "Request timeout"}}
        except Exception as e:
            return {"error": {"message": str(e)}}
    
    async def agent_workload(self, agent_id: str, duration: int, requests_per_second: int):
        """Simulate an agent sending requests at a specific rate"""
        async with aiohttp.ClientSession() as session:
            # Register agent
            await self.send_mcp_request(
                session,
                "marcus.register_agent",
                {
                    "agent_id": agent_id,
                    "capabilities": ["python", "testing"],
                    "capacity": 10
                }
            )
            
            end_time = time.time() + duration
            request_interval = 1.0 / requests_per_second if requests_per_second > 0 else 1.0
            
            request_count = 0
            error_count = 0
            total_latency = 0
            
            while time.time() < end_time and self.monitoring:
                start = time.time()
                
                # Request task
                result = await self.send_mcp_request(
                    session,
                    "marcus.request_task",
                    {"agent_id": agent_id}
                )
                
                latency = time.time() - start
                total_latency += latency
                request_count += 1
                
                if "error" in result:
                    error_count += 1
                else:
                    # If we got a task, complete it quickly
                    task_id = result.get("result", {}).get("task_id")
                    if task_id:
                        await self.send_mcp_request(
                            session,
                            "marcus.complete_task",
                            {
                                "task_id": task_id,
                                "agent_id": agent_id,
                                "results": {"stress_test": True}
                            }
                        )
                
                # Maintain request rate
                elapsed = time.time() - start
                if elapsed < request_interval:
                    await asyncio.sleep(request_interval - elapsed)
            
            return {
                "agent_id": agent_id,
                "requests": request_count,
                "errors": error_count,
                "error_rate": error_count / request_count if request_count > 0 else 0,
                "avg_latency": total_latency / request_count if request_count > 0 else 0
            }
    
    async def monitor_system_resources(self):
        """Monitor system resources during test"""
        process = psutil.Process()
        
        while self.monitoring:
            cpu_percent = process.cpu_percent(interval=1)
            memory_info = process.memory_info()
            
            self.results["system_metrics"].append({
                "timestamp": time.time() - self.start_time,
                "cpu_percent": cpu_percent,
                "memory_mb": memory_info.rss / 1024 / 1024,
                "threads": process.num_threads()
            })
            
            await asyncio.sleep(1)
    
    async def run_stress_stage(self, num_agents: int, requests_per_second: int, duration: int):
        """Run a single stress test stage"""
        print(f"\nStage: {num_agents} agents, {requests_per_second} req/s each, {duration}s duration")
        
        stage_start = time.time()
        
        # Create agent tasks
        tasks = []
        for i in range(num_agents):
            agent_id = f"stress-agent-{i}"
            task = self.agent_workload(agent_id, duration, requests_per_second)
            tasks.append(task)
        
        # Run all agents
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        total_requests = 0
        total_errors = 0
        latencies = []
        
        for result in results:
            if isinstance(result, dict):
                total_requests += result["requests"]
                total_errors += result["errors"]
                latencies.append(result["avg_latency"])
        
        stage_duration = time.time() - stage_start
        
        stage_result = {
            "num_agents": num_agents,
            "target_rps_per_agent": requests_per_second,
            "duration": duration,
            "actual_duration": stage_duration,
            "total_requests": total_requests,
            "total_errors": total_errors,
            "error_rate": total_errors / total_requests if total_requests > 0 else 0,
            "actual_rps": total_requests / stage_duration,
            "avg_latency": sum(latencies) / len(latencies) if latencies else 0,
            "max_latency": max(latencies) if latencies else 0
        }
        
        print(f"  Total requests: {total_requests}")
        print(f"  Error rate: {stage_result['error_rate']:.2%}")
        print(f"  Actual RPS: {stage_result['actual_rps']:.2f}")
        print(f"  Avg latency: {stage_result['avg_latency']*1000:.2f}ms")
        
        return stage_result
    
    async def find_breaking_point(self):
        """Gradually increase load until system breaks"""
        print("Finding Marcus breaking point...")
        self.start_time = time.time()
        
        # Start resource monitoring
        monitor_task = asyncio.create_task(self.monitor_system_resources())
        
        # Test stages with increasing load
        stages = [
            (5, 1, 30),    # 5 agents, 1 req/s each, 30s
            (10, 2, 30),   # 10 agents, 2 req/s each
            (20, 2, 30),   # 20 agents, 2 req/s each
            (50, 2, 30),   # 50 agents, 2 req/s each
            (100, 1, 30),  # 100 agents, 1 req/s each
            (100, 2, 30),  # 100 agents, 2 req/s each
            (200, 1, 30),  # 200 agents, 1 req/s each
        ]
        
        breaking_point_found = False
        
        for num_agents, rps, duration in stages:
            try:
                result = await self.run_stress_stage(num_agents, rps, duration)
                self.results["stages"].append(result)
                
                # Check if we've hit breaking point (>10% errors or >1s latency)
                if result["error_rate"] > 0.1 or result["avg_latency"] > 1.0:
                    print(f"\nBreaking point found at {num_agents} agents!")
                    self.results["breaking_point"] = {
                        "num_agents": num_agents,
                        "total_rps": result["actual_rps"],
                        "error_rate": result["error_rate"],
                        "avg_latency": result["avg_latency"]
                    }
                    breaking_point_found = True
                    break
                    
            except Exception as e:
                print(f"Stage failed: {e}")
                break
        
        # Stop monitoring
        self.monitoring = False
        await monitor_task
        
        if not breaking_point_found:
            print("\nNo breaking point found within test limits!")
    
    def save_results(self, filename: str):
        """Save stress test results"""
        self.results["metadata"] = {
            "timestamp": datetime.now().isoformat(),
            "host": self.host,
            "port": self.port,
            "test_duration": time.time() - self.start_time if self.start_time else 0
        }
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
    
    def print_summary(self):
        """Print stress test summary"""
        print("\n" + "="*50)
        print("STRESS TEST SUMMARY")
        print("="*50)
        
        if self.results["breaking_point"]:
            bp = self.results["breaking_point"]
            print(f"Breaking point: {bp['num_agents']} agents")
            print(f"  Total RPS at breaking point: {bp['total_rps']:.2f}")
            print(f"  Error rate: {bp['error_rate']:.2%}")
            print(f"  Avg latency: {bp['avg_latency']*1000:.2f}ms")
        
        print("\nPerformance by stage:")
        print("Agents | Total RPS | Error % | Avg Latency")
        print("-"*45)
        for stage in self.results["stages"]:
            print(f"{stage['num_agents']:6d} | {stage['actual_rps']:9.2f} | "
                  f"{stage['error_rate']*100:7.1f} | {stage['avg_latency']*1000:8.2f}ms")
        
        # Find peak performance
        if self.results["stages"]:
            best_stage = max(self.results["stages"], 
                           key=lambda s: s["actual_rps"] if s["error_rate"] < 0.05 else 0)
            print(f"\nPeak performance: {best_stage['actual_rps']:.2f} RPS "
                  f"with {best_stage['num_agents']} agents")


async def quick_stress_test():
    """Run a quick stress test"""
    tester = StressTestRunner()
    
    print("Running quick stress test (3 stages)...")
    tester.start_time = time.time()
    
    # Run 3 quick stages
    stages = [
        (10, 2, 10),   # 10 agents, 2 req/s, 10 seconds
        (25, 2, 10),   # 25 agents
        (50, 2, 10),   # 50 agents
    ]
    
    for num_agents, rps, duration in stages:
        result = await tester.run_stress_stage(num_agents, rps, duration)
        tester.results["stages"].append(result)
    
    tester.print_summary()
    tester.save_results("quick_stress_test_results.json")


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\nStress test interrupted!")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    
    # Choose test type
    import argparse
    parser = argparse.ArgumentParser(description="Stress test Marcus MCP server")
    parser.add_argument("--quick", action="store_true", help="Run quick test")
    parser.add_argument("--full", action="store_true", help="Find breaking point")
    args = parser.parse_args()
    
    if args.quick:
        asyncio.run(quick_stress_test())
    else:
        # Default to full test
        tester = StressTestRunner()
        asyncio.run(tester.find_breaking_point())
        tester.print_summary()
        tester.save_results("stress_test_results.json")
        print("\nResults saved to stress_test_results.json")