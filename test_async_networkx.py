#!/usr/bin/env python3
"""
Test NetworkX under async conditions to see if there's a race condition
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

import networkx as nx


async def create_graph_async(i):
    """Create a NetworkX graph asynchronously"""
    try:
        G = nx.DiGraph()
        G.add_node(f"node_{i}")
        G.add_edge(f"node_{i}", f"node_{i+1}")
        
        # Try to iterate over some NetworkX internal structures
        for attr in nx.get_node_attributes(G, 'attr').items():
            pass
            
        return f"Graph {i} created successfully"
    except Exception as e:
        return f"Graph {i} failed: {e}"


async def test_concurrent_networkx():
    """Test NetworkX under concurrent conditions"""
    print("Testing NetworkX under concurrent async conditions...")
    
    # Create multiple concurrent tasks
    tasks = []
    for i in range(20):
        task = asyncio.create_task(create_graph_async(i))
        tasks.append(task)
    
    # Wait for all tasks
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"Task {i}: ERROR - {result}")
        else:
            print(f"Task {i}: {result}")


if __name__ == "__main__":
    try:
        asyncio.run(test_concurrent_networkx())
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()