"""
MCP Test Client for benchmarking Marcus
"""
import asyncio
import json
import time
from typing import Dict, Any, List, Optional
import websockets
import aiohttp
from dataclasses import dataclass
from datetime import datetime


@dataclass
class BenchmarkResult:
    """Result from a benchmark test"""
    operation: str
    latency_ms: float
    success: bool
    error: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class MCPTestClient:
    """Test client for benchmarking Marcus MCP server"""
    
    def __init__(self, host: str = "localhost", port: int = 3333):
        self.host = host
        self.port = port
        self.ws_url = f"ws://{host}:{port}/ws"
        self.http_url = f"http://{host}:{port}"
        self.agent_id = None
        self.results: List[BenchmarkResult] = []
    
    async def connect_websocket(self) -> websockets.WebSocketClientProtocol:
        """Establish WebSocket connection"""
        return await websockets.connect(self.ws_url)
    
    async def send_mcp_command(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send MCP command and measure latency"""
        command = {
            "jsonrpc": "2.0",
            "id": str(time.time()),
            "method": method,
            "params": params
        }
        
        start = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.http_url}/mcp",
                    json=command,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    result = await response.json()
                    latency = (time.time() - start) * 1000
                    
                    benchmark_result = BenchmarkResult(
                        operation=method,
                        latency_ms=latency,
                        success="error" not in result,
                        error=result.get("error", {}).get("message") if "error" in result else None
                    )
                    self.results.append(benchmark_result)
                    
                    return result
        except Exception as e:
            latency = (time.time() - start) * 1000
            benchmark_result = BenchmarkResult(
                operation=method,
                latency_ms=latency,
                success=False,
                error=str(e)
            )
            self.results.append(benchmark_result)
            raise
    
    async def register_agent(self, agent_id: str, capabilities: List[str]) -> Dict[str, Any]:
        """Register an agent with Marcus"""
        self.agent_id = agent_id
        return await self.send_mcp_command(
            "marcus.register_agent",
            {
                "agent_id": agent_id,
                "capabilities": capabilities,
                "capacity": 5
            }
        )
    
    async def request_task(self) -> Dict[str, Any]:
        """Request a task from Marcus"""
        return await self.send_mcp_command(
            "marcus.request_task",
            {"agent_id": self.agent_id}
        )
    
    async def update_progress(self, task_id: str, progress: int, message: str = "") -> Dict[str, Any]:
        """Update task progress"""
        return await self.send_mcp_command(
            "marcus.update_progress",
            {
                "task_id": task_id,
                "progress": progress,
                "message": message,
                "agent_id": self.agent_id
            }
        )
    
    async def complete_task(self, task_id: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """Complete a task"""
        return await self.send_mcp_command(
            "marcus.complete_task",
            {
                "task_id": task_id,
                "results": results,
                "agent_id": self.agent_id
            }
        )
    
    async def report_blocker(self, task_id: str, blocker: str) -> Dict[str, Any]:
        """Report a blocker"""
        return await self.send_mcp_command(
            "marcus.report_blocker",
            {
                "task_id": task_id,
                "blocker": blocker,
                "agent_id": self.agent_id
            }
        )
    
    async def get_board_status(self) -> Dict[str, Any]:
        """Get current board status"""
        return await self.send_mcp_command(
            "marcus.get_board_status",
            {}
        )
    
    def get_summary(self) -> Dict[str, Any]:
        """Get benchmark summary"""
        if not self.results:
            return {"error": "No results collected"}
        
        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]
        
        latencies = [r.latency_ms for r in successful]
        
        return {
            "total_operations": len(self.results),
            "successful": len(successful),
            "failed": len(failed),
            "average_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
            "min_latency_ms": min(latencies) if latencies else 0,
            "max_latency_ms": max(latencies) if latencies else 0,
            "operations_per_second": len(successful) / (sum(latencies) / 1000) if latencies else 0,
            "errors": [{"operation": r.operation, "error": r.error} for r in failed]
        }
    
    def save_results(self, filename: str):
        """Save detailed results to file"""
        results_data = {
            "summary": self.get_summary(),
            "detailed_results": [
                {
                    "operation": r.operation,
                    "latency_ms": r.latency_ms,
                    "success": r.success,
                    "error": r.error,
                    "timestamp": r.timestamp.isoformat()
                }
                for r in self.results
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(results_data, f, indent=2)


async def basic_benchmark():
    """Run basic MCP operations benchmark"""
    client = MCPTestClient()
    
    print("Starting basic MCP benchmark...")
    
    # Register agent
    print("1. Testing agent registration...")
    await client.register_agent("benchmark-agent-1", ["python", "testing"])
    
    # Request multiple tasks
    print("2. Testing task requests...")
    for i in range(5):
        result = await client.request_task()
        if "error" not in result:
            task_id = result.get("result", {}).get("task_id")
            if task_id:
                # Update progress
                await client.update_progress(task_id, 50, "Working on it")
                await asyncio.sleep(0.1)  # Simulate work
                
                # Complete task
                await client.complete_task(task_id, {"tests_passed": True})
    
    # Get board status
    print("3. Testing board status...")
    await client.get_board_status()
    
    # Print summary
    summary = client.get_summary()
    print("\nBenchmark Results:")
    print(f"Total operations: {summary['total_operations']}")
    print(f"Successful: {summary['successful']}")
    print(f"Failed: {summary['failed']}")
    print(f"Average latency: {summary['average_latency_ms']:.2f}ms")
    print(f"Min latency: {summary['min_latency_ms']:.2f}ms")
    print(f"Max latency: {summary['max_latency_ms']:.2f}ms")
    
    # Save results
    client.save_results("basic_benchmark_results.json")
    print("\nDetailed results saved to basic_benchmark_results.json")


if __name__ == "__main__":
    asyncio.run(basic_benchmark())