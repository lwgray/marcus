"""
Performance benchmarking suite for Marcus scaling.

This module provides comprehensive benchmarking tools to test
Marcus's performance at different scales.
"""

import asyncio
import aiohttp
import websockets
import time
import json
import statistics
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging
import random
import string
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """
    Results from a benchmark run.
    
    This dataclass captures comprehensive performance metrics from
    a benchmark scenario including connection statistics, response times,
    and error tracking.
    
    Attributes
    ----------
    scenario : str
        Name of the benchmark scenario.
    total_connections: int
    successful_connections: int
    failed_connections: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    p50_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    connections_per_second: float
    total_duration: float
    errors: Dict[str, int] = field(default_factory=dict)
    timestamps: List[float] = field(default_factory=list)


class AgentSimulator:
    """
    Simulate a Marcus client for performance testing.
    
    This class simulates the behavior of a Marcus client, including
    registration, task requests, progress reporting, and blocker handling.
    It's designed to stress test the Marcus server under various load conditions.
    
    Notes
    -----
    The simulator generates realistic agent behavior patterns to ensure
    benchmarks reflect actual usage scenarios.
    """
    
    def __init__(self, agent_id: str, server_url: str):
        self.agent_id = agent_id
        self.server_url = server_url
        self.ws_url = server_url.replace("http", "ws")
        self.session = None
        self.websocket = None
        self.connected = False
        self.response_times = []
        self.errors = []
    
    async def connect_http(self):
        """Connect using HTTP session."""
        self.session = aiohttp.ClientSession()
        return self.session
    
    async def connect_websocket(self):
        """Connect using WebSocket."""
        try:
            self.websocket = await websockets.connect(
                f"{self.ws_url}/ws/agent/{self.agent_id}",
                ping_interval=20,
                ping_timeout=10
            )
            self.connected = True
            
            # Send registration
            await self.websocket.send(json.dumps({
                "type": "register",
                "name": f"Test Agent {self.agent_id}",
                "capabilities": {"test": True}
            }))
            
            # Wait for registration confirmation
            response = await self.websocket.recv()
            data = json.loads(response)
            if data.get("type") != "registered":
                raise Exception(f"Registration failed: {data}")
                
        except Exception as e:
            self.errors.append(f"WebSocket connection failed: {e}")
            raise
    
    async def register_agent(self):
        """Register agent via HTTP."""
        start_time = time.time()
        try:
            async with self.session.post(
                f"{self.server_url}/api/v1/agents/register",
                json={
                    "agent_id": self.agent_id,
                    "name": f"Test Agent {self.agent_id}",
                    "capabilities": {"test": True}
                }
            ) as response:
                if response.status != 200:
                    raise Exception(f"Registration failed: {await response.text()}")
                
                self.response_times.append(time.time() - start_time)
                return await response.json()
        except Exception as e:
            self.errors.append(f"Registration error: {e}")
            raise
    
    async def request_task(self):
        """Request a task."""
        start_time = time.time()
        
        if self.websocket and self.connected:
            # WebSocket request
            try:
                await self.websocket.send(json.dumps({
                    "type": "request_task"
                }))
                response = await self.websocket.recv()
                data = json.loads(response)
                self.response_times.append(time.time() - start_time)
                return data.get("task")
            except Exception as e:
                self.errors.append(f"Task request error (WS): {e}")
                raise
        else:
            # HTTP request
            try:
                async with self.session.post(
                    f"{self.server_url}/api/v1/tasks/request",
                    json={"agent_id": self.agent_id}
                ) as response:
                    if response.status != 200:
                        raise Exception(f"Task request failed: {await response.text()}")
                    
                    self.response_times.append(time.time() - start_time)
                    data = await response.json()
                    return data.get("task")
            except Exception as e:
                self.errors.append(f"Task request error (HTTP): {e}")
                raise
    
    async def report_progress(self, task_id: str, progress: int):
        """Report task progress."""
        start_time = time.time()
        
        if self.websocket and self.connected:
            # WebSocket report
            try:
                await self.websocket.send(json.dumps({
                    "type": "report_progress",
                    "task_id": task_id,
                    "progress": progress,
                    "status": "in_progress",
                    "message": f"Progress: {progress}%"
                }))
                response = await self.websocket.recv()
                self.response_times.append(time.time() - start_time)
            except Exception as e:
                self.errors.append(f"Progress report error (WS): {e}")
                raise
        else:
            # HTTP report
            try:
                async with self.session.post(
                    f"{self.server_url}/api/v1/tasks/progress",
                    json={
                        "agent_id": self.agent_id,
                        "task_id": task_id,
                        "progress": progress,
                        "status": "in_progress",
                        "message": f"Progress: {progress}%"
                    }
                ) as response:
                    if response.status != 200:
                        raise Exception(f"Progress report failed: {await response.text()}")
                    
                    self.response_times.append(time.time() - start_time)
            except Exception as e:
                self.errors.append(f"Progress report error (HTTP): {e}")
                raise
    
    async def simulate_work_cycle(self, duration: int = 60):
        """Simulate a complete work cycle."""
        end_time = time.time() + duration
        cycles = 0
        
        while time.time() < end_time:
            try:
                # Request task
                task = await self.request_task()
                
                if task:
                    # Simulate work with progress reports
                    for progress in [25, 50, 75, 100]:
                        await asyncio.sleep(random.uniform(0.5, 2.0))
                        await self.report_progress(task["id"], progress)
                else:
                    # No task available, wait before retry
                    await asyncio.sleep(random.uniform(1.0, 3.0))
                
                cycles += 1
                
            except Exception as e:
                logger.error(f"Work cycle error for {self.agent_id}: {e}")
                await asyncio.sleep(1.0)
        
        return cycles
    
    async def cleanup(self):
        """Clean up connections."""
        if self.websocket:
            await self.websocket.close()
        if self.session:
            await self.session.close()


class LoadTester:
    """Main load testing orchestrator."""
    
    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        self.results = []
    
    async def run_scenario(
        self,
        name: str,
        num_agents: int,
        duration: int = 60,
        connection_type: str = "http",
        ramp_up_time: int = 10
    ) -> BenchmarkResult:
        """Run a load test scenario."""
        logger.info(f"Starting scenario: {name}")
        logger.info(f"Agents: {num_agents}, Duration: {duration}s, Type: {connection_type}")
        
        start_time = time.time()
        agents = []
        connection_times = []
        all_response_times = []
        all_errors = {}
        
        # Create agents with ramp-up
        ramp_up_delay = ramp_up_time / num_agents if num_agents > 0 else 0
        
        async def create_agent(index: int):
            await asyncio.sleep(index * ramp_up_delay)
            
            agent_id = f"test-agent-{index}-{random.randint(1000, 9999)}"
            agent = AgentSimulator(agent_id, self.server_url)
            
            try:
                conn_start = time.time()
                
                if connection_type == "websocket":
                    await agent.connect_websocket()
                else:
                    await agent.connect_http()
                    await agent.register_agent()
                
                connection_times.append(time.time() - conn_start)
                return agent
            except Exception as e:
                logger.error(f"Failed to create agent {index}: {e}")
                return None
        
        # Create all agents concurrently
        agent_tasks = [create_agent(i) for i in range(num_agents)]
        created_agents = await asyncio.gather(*agent_tasks, return_exceptions=True)
        
        # Filter out failed agents
        agents = [a for a in created_agents if a and not isinstance(a, Exception)]
        failed_connections = num_agents - len(agents)
        
        logger.info(f"Successfully connected {len(agents)} out of {num_agents} agents")
        
        # Run work cycles
        if agents:
            work_tasks = [agent.simulate_work_cycle(duration) for agent in agents]
            await asyncio.gather(*work_tasks, return_exceptions=True)
        
        # Collect metrics
        total_requests = 0
        successful_requests = 0
        
        for agent in agents:
            all_response_times.extend(agent.response_times)
            total_requests += len(agent.response_times) + len(agent.errors)
            successful_requests += len(agent.response_times)
            
            # Aggregate errors
            for error in agent.errors:
                error_type = error.split(":")[0]
                all_errors[error_type] = all_errors.get(error_type, 0) + 1
        
        # Clean up
        cleanup_tasks = [agent.cleanup() for agent in agents]
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        total_duration = time.time() - start_time
        
        # Calculate statistics
        if all_response_times:
            all_response_times.sort()
            avg_response = statistics.mean(all_response_times)
            p50_response = all_response_times[len(all_response_times) // 2]
            p95_response = all_response_times[int(len(all_response_times) * 0.95)]
            p99_response = all_response_times[int(len(all_response_times) * 0.99)]
        else:
            avg_response = p50_response = p95_response = p99_response = 0
        
        # Create result
        result = BenchmarkResult(
            scenario=name,
            total_connections=num_agents,
            successful_connections=len(agents),
            failed_connections=failed_connections,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=total_requests - successful_requests,
            avg_response_time=avg_response,
            p50_response_time=p50_response,
            p95_response_time=p95_response,
            p99_response_time=p99_response,
            requests_per_second=successful_requests / total_duration if total_duration > 0 else 0,
            connections_per_second=len(agents) / ramp_up_time if ramp_up_time > 0 else 0,
            total_duration=total_duration,
            errors=all_errors,
            timestamps=all_response_times
        )
        
        self.results.append(result)
        return result
    
    async def run_scaling_test(self):
        """Run complete scaling test suite."""
        scenarios = [
            # Tier 1: 10-20 connections
            ("Small Scale - HTTP", 10, 60, "http", 5),
            ("Small Scale - WebSocket", 10, 60, "websocket", 5),
            ("Small Scale Peak - HTTP", 20, 60, "http", 10),
            
            # Tier 2: 100 connections
            ("Medium Scale - HTTP", 50, 120, "http", 20),
            ("Medium Scale - WebSocket", 50, 120, "websocket", 20),
            ("Medium Scale Peak - Mixed", 100, 120, "http", 30),
            
            # Tier 3: 1000 connections (requires proper infrastructure)
            # ("Large Scale - HTTP", 500, 180, "http", 60),
            # ("Large Scale - WebSocket", 500, 180, "websocket", 60),
            # ("Large Scale Peak - Mixed", 1000, 180, "http", 120),
        ]
        
        for scenario in scenarios:
            try:
                result = await self.run_scenario(*scenario)
                self.print_result(result)
                
                # Cool down between scenarios
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Scenario {scenario[0]} failed: {e}")
    
    def print_result(self, result: BenchmarkResult):
        """Print benchmark results."""
        print(f"\n{'='*60}")
        print(f"Scenario: {result.scenario}")
        print(f"{'='*60}")
        print(f"Connections:")
        print(f"  Total:      {result.total_connections}")
        print(f"  Successful: {result.successful_connections}")
        print(f"  Failed:     {result.failed_connections}")
        print(f"  Rate:       {result.connections_per_second:.2f}/sec")
        print(f"\nRequests:")
        print(f"  Total:      {result.total_requests}")
        print(f"  Successful: {result.successful_requests}")
        print(f"  Failed:     {result.failed_requests}")
        print(f"  Rate:       {result.requests_per_second:.2f}/sec")
        print(f"\nResponse Times (ms):")
        print(f"  Average:    {result.avg_response_time*1000:.2f}")
        print(f"  P50:        {result.p50_response_time*1000:.2f}")
        print(f"  P95:        {result.p95_response_time*1000:.2f}")
        print(f"  P99:        {result.p99_response_time*1000:.2f}")
        print(f"\nDuration:     {result.total_duration:.2f} seconds")
        
        if result.errors:
            print(f"\nErrors:")
            for error_type, count in result.errors.items():
                print(f"  {error_type}: {count}")
    
    def generate_report(self, filename: str = "benchmark_results.json"):
        """Generate detailed report."""
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "server_url": self.server_url,
            "scenarios": []
        }
        
        for result in self.results:
            report["scenarios"].append({
                "name": result.scenario,
                "metrics": {
                    "connections": {
                        "total": result.total_connections,
                        "successful": result.successful_connections,
                        "failed": result.failed_connections,
                        "rate_per_sec": result.connections_per_second
                    },
                    "requests": {
                        "total": result.total_requests,
                        "successful": result.successful_requests,
                        "failed": result.failed_requests,
                        "rate_per_sec": result.requests_per_second
                    },
                    "response_times_ms": {
                        "avg": result.avg_response_time * 1000,
                        "p50": result.p50_response_time * 1000,
                        "p95": result.p95_response_time * 1000,
                        "p99": result.p99_response_time * 1000
                    },
                    "duration_sec": result.total_duration,
                    "errors": result.errors
                }
            })
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Report saved to {filename}")


async def stress_test_connection_limit(server_url: str, max_connections: int = 200):
    """Test server connection limits."""
    logger.info(f"Testing connection limit up to {max_connections}")
    
    connections = []
    successful = 0
    
    async def create_connection(index: int):
        try:
            ws = await websockets.connect(
                f"{server_url.replace('http', 'ws')}/ws/agent/stress-{index}"
            )
            return ws
        except Exception as e:
            logger.debug(f"Connection {index} failed: {e}")
            return None
    
    # Try to create connections in batches
    batch_size = 50
    for i in range(0, max_connections, batch_size):
        batch_end = min(i + batch_size, max_connections)
        tasks = [create_connection(j) for j in range(i, batch_end)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for ws in results:
            if ws and not isinstance(ws, Exception):
                connections.append(ws)
                successful += 1
        
        logger.info(f"Connected: {successful}/{batch_end}")
        
        # Stop if connections start failing
        if len([r for r in results if r and not isinstance(r, Exception)]) == 0:
            break
    
    logger.info(f"Maximum successful connections: {successful}")
    
    # Clean up
    for ws in connections:
        await ws.close()
    
    return successful


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Marcus Performance Benchmarking")
    parser.add_argument("--server", default="http://localhost:8000", help="Server URL")
    parser.add_argument("--scenario", help="Run specific scenario")
    parser.add_argument("--agents", type=int, default=10, help="Number of agents")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    parser.add_argument("--connection-limit-test", action="store_true", help="Test connection limits")
    
    args = parser.parse_args()
    
    if args.connection_limit_test:
        max_conn = await stress_test_connection_limit(args.server)
        print(f"\nMaximum connections achieved: {max_conn}")
    else:
        tester = LoadTester(args.server)
        
        if args.scenario:
            result = await tester.run_scenario(
                args.scenario,
                args.agents,
                args.duration,
                "http",
                min(args.agents // 2, 30)
            )
            tester.print_result(result)
        else:
            await tester.run_scaling_test()
        
        tester.generate_report()


if __name__ == "__main__":
    asyncio.run(main())