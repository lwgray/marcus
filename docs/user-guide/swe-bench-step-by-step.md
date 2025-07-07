# SWE-Bench Step-by-Step Setup Guide

## Prerequisites Check

Before starting, verify you have:
- [ ] Python 3.8+ installed
- [ ] Docker installed and running
- [ ] 120GB+ free disk space
- [ ] 16GB+ RAM
- [ ] Git installed
- [ ] OpenAI API key (or other LLM provider)

## Step 1: Download and Install SWE-Bench

```bash
# 1.1 Clone SWE-Bench repository
cd ~/dev  # or wherever you keep projects
git clone https://github.com/SWE-bench/SWE-bench.git
cd SWE-bench

# 1.2 Create virtual environment
python -m venv swe_bench_env
source swe_bench_env/bin/activate  # On Windows: swe_bench_env\Scripts\activate

# 1.3 Install SWE-Bench
pip install -e .

# 1.4 Test installation
python -m swebench.harness.run_evaluation --help
```

## Step 2: Download SWE-Bench Lite Dataset

```bash
# 2.1 Install datasets library
pip install datasets

# 2.2 Download SWE-Bench Lite (300 easier instances)
python -c "
from datasets import load_dataset
import json

# Load dataset
dataset = load_dataset('princeton-nlp/SWE-bench_Lite')
print(f'Loaded {len(dataset[\"test\"])} test instances')

# Save first 10 instances for testing
test_instances = dataset['test'][:10]
with open('swe_bench_lite_sample.json', 'w') as f:
    json.dump(test_instances, f, indent=2)
    
print('Saved sample to swe_bench_lite_sample.json')
"
```

## Step 3: Set Up Marcus for SWE-Bench

```bash
# 3.1 Go to Marcus directory
cd /Users/lwgray/dev/marcus

# 3.2 Create SWE-Bench configuration
cp config_marcus.json config_swe_bench.json
```

Edit `config_swe_bench.json`:
```json
{
  "project_name": "SWE-Bench Challenge",
  "kanban": {
    "provider": "planka",
    "board_name": "SWE-Bench"
  },
  "features": {
    "events": {"enabled": true, "store_history": true},
    "context": {"enabled": true, "use_hybrid_inference": true},
    "memory": {"enabled": true, "use_v2_predictions": false},
    "visibility": {"enabled": true}
  }
}
```

## Step 4: Create SWE-Bench Integration Script

```bash
# 4.1 Create scripts directory
mkdir -p scripts

# 4.2 Create main SWE-Bench runner
```

Create `scripts/swe_bench_runner.py`:
```python
#!/usr/bin/env python3
"""
SWE-Bench Runner for Marcus
Simple integration to get started with SWE-Bench evaluation
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Any
import asyncio
from datasets import load_dataset

class SimpleSWEBenchRunner:
    def __init__(self, workspace_dir: str = "./swe_bench_workspaces"):
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(exist_ok=True)
        
    def load_instances(self, dataset_name: str = "princeton-nlp/SWE-bench_Lite", limit: int = 10):
        """Load SWE-Bench instances"""
        print(f"Loading {dataset_name} (limit: {limit})")
        dataset = load_dataset(dataset_name)
        instances = dataset['test'][:limit]
        print(f"Loaded {len(instances)} instances")
        return instances
    
    def setup_repository(self, instance: Dict[str, Any]) -> str:
        """Set up repository for an instance"""
        repo_path = self.workspace_dir / f"repo_{instance['instance_id']}"
        
        if repo_path.exists():
            print(f"Repository already exists: {repo_path}")
            return str(repo_path)
            
        print(f"Cloning {instance['repo']} to {repo_path}")
        
        # Clone repository
        subprocess.run([
            "git", "clone", f"https://github.com/{instance['repo']}.git", str(repo_path)
        ], check=True)
        
        # Checkout base commit
        subprocess.run([
            "git", "checkout", instance['base_commit']
        ], cwd=repo_path, check=True)
        
        return str(repo_path)
    
    def analyze_issue(self, instance: Dict[str, Any]) -> Dict[str, str]:
        """Analyze the GitHub issue (simplified version)"""
        return {
            "problem_statement": instance['problem_statement'],
            "repo": instance['repo'],
            "instance_id": instance['instance_id'],
            "base_commit": instance['base_commit']
        }
    
    def generate_patch(self, instance: Dict[str, Any], repo_path: str) -> str:
        """Generate a patch for the issue (placeholder implementation)"""
        # This is where Marcus would analyze the code and generate a solution
        # For now, return empty patch
        print(f"Generating patch for {instance['instance_id']}")
        
        # TODO: Integrate with Marcus agents here
        # 1. Parse problem statement
        # 2. Analyze codebase using Marcus context system
        # 3. Generate solution using Marcus AI engine
        # 4. Create git patch
        
        return ""  # Empty patch for now
    
    def run_instance(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single SWE-Bench instance"""
        print(f"\n=== Processing {instance['instance_id']} ===")
        
        try:
            # 1. Set up repository
            repo_path = self.setup_repository(instance)
            
            # 2. Analyze issue
            analysis = self.analyze_issue(instance)
            print(f"Problem: {analysis['problem_statement'][:100]}...")
            
            # 3. Generate patch
            patch = self.generate_patch(instance, repo_path)
            
            return {
                "instance_id": instance['instance_id'],
                "model_patch": patch,
                "model_name_or_path": "marcus-v1",
                "status": "completed" if patch else "failed"
            }
            
        except Exception as e:
            print(f"Error processing {instance['instance_id']}: {e}")
            return {
                "instance_id": instance['instance_id'],
                "model_patch": "",
                "model_name_or_path": "marcus-v1",
                "status": "error",
                "error": str(e)
            }
    
    def run_evaluation(self, limit: int = 5):
        """Run evaluation on limited instances"""
        # Load instances
        instances = self.load_instances(limit=limit)
        
        # Process each instance
        results = []
        for i, instance in enumerate(instances):
            print(f"\nProgress: {i+1}/{len(instances)}")
            result = self.run_instance(instance)
            results.append(result)
        
        # Save results
        output_file = "marcus_swe_bench_predictions.jsonl"
        with open(output_file, 'w') as f:
            for result in results:
                f.write(json.dumps(result) + '\n')
        
        print(f"\nResults saved to {output_file}")
        print(f"Processed {len(results)} instances")
        
        return results

if __name__ == "__main__":
    runner = SimpleSWEBenchRunner()
    results = runner.run_evaluation(limit=3)  # Start with just 3 instances
    
    # Print summary
    successful = sum(1 for r in results if r['status'] == 'completed' and r['model_patch'])
    print(f"\nSummary:")
    print(f"- Total instances: {len(results)}")
    print(f"- Successful patches: {successful}")
    print(f"- Success rate: {successful/len(results)*100:.1f}%")
```

## Step 5: Test Basic Setup

```bash
# 5.1 Make script executable
chmod +x scripts/swe_bench_runner.py

# 5.2 Test with 3 instances
cd /Users/lwgray/dev/marcus
python scripts/swe_bench_runner.py
```

Expected output:
```
Loading princeton-nlp/SWE-bench_Lite (limit: 3)
Loaded 3 instances

=== Processing astropy__astropy-12907 ===
Cloning astropy/astropy to ./swe_bench_workspaces/repo_astropy__astropy-12907
Problem: BUG: Inconsistent behavior in `quantity_support()`...
Generating patch for astropy__astropy-12907

Progress: 1/3
...
Results saved to marcus_swe_bench_predictions.jsonl
Processed 3 instances
Summary:
- Total instances: 3
- Successful patches: 0
- Success rate: 0.0%
```

## Step 6: Set Up Kanban Board for SWE-Bench

```bash
# 6.1 Start Planka (if not already running)
docker run -d -p 3333:1337 --name planka meltyshev/planka

# 6.2 Create SWE-Bench board
# Open http://localhost:3333
# Create account: demo@demo.demo / demo
# Create board: "SWE-Bench"
# Create columns: TODO, ANALYZING, IMPLEMENTING, TESTING, DONE, FAILED
```

## Step 7: Create SWE-Bench MCP Tool

Create `src/marcus_mcp/tools/swe_bench_tool.py`:
```python
"""SWE-Bench integration tool for Marcus MCP"""

import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List
from datasets import load_dataset

def get_swe_bench_tool_definition():
    """Define SWE-Bench tool for MCP"""
    return {
        "name": "swe_bench",
        "description": "Load and process SWE-Bench instances",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["load_instance", "setup_repo", "analyze_issue"],
                    "description": "Action to perform"
                },
                "instance_id": {
                    "type": "string", 
                    "description": "SWE-Bench instance ID"
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of instances to load",
                    "default": 10
                }
            },
            "required": ["action"]
        }
    }

async def handle_swe_bench_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle SWE-Bench tool calls"""
    action = arguments.get("action")
    
    if action == "load_instance":
        limit = arguments.get("limit", 10)
        try:
            dataset = load_dataset("princeton-nlp/SWE-bench_Lite")
            instances = dataset['test'][:limit]
            return {
                "success": True,
                "instances_loaded": len(instances),
                "sample_instance": instances[0] if instances else None
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    elif action == "setup_repo":
        instance_id = arguments.get("instance_id")
        if not instance_id:
            return {"success": False, "error": "instance_id required"}
        
        # TODO: Implement repository setup
        return {"success": True, "message": f"Repository setup for {instance_id} - TODO"}
    
    elif action == "analyze_issue":
        instance_id = arguments.get("instance_id")
        if not instance_id:
            return {"success": False, "error": "instance_id required"}
        
        # TODO: Implement issue analysis
        return {"success": True, "message": f"Issue analysis for {instance_id} - TODO"}
    
    else:
        return {"success": False, "error": f"Unknown action: {action}"}
```

## Step 8: Test SWE-Bench Tool with Marcus

```bash
# 8.1 Start Marcus MCP server
MARCUS_CONFIG=config_swe_bench.json python -m src.marcus_mcp.server &

# 8.2 Test the tool (in another terminal)
# Use your preferred MCP client or create a simple test script
```

## Step 9: Create Simple Marcus-SWE-Bench Integration

Create `scripts/marcus_swe_bench_simple.py`:
```python
#!/usr/bin/env python3
"""
Simple Marcus + SWE-Bench integration
Demonstrates basic workflow
"""

import asyncio
import json
from pathlib import Path

async def main():
    print("=== Marcus SWE-Bench Simple Integration ===")
    
    # Step 1: Load Marcus components
    print("1. Loading Marcus components...")
    # TODO: Initialize Marcus MCP client
    
    # Step 2: Load SWE-Bench instance
    print("2. Loading SWE-Bench instance...")
    # TODO: Call swe_bench tool to load instance
    
    # Step 3: Create Kanban task
    print("3. Creating Kanban task...")
    # TODO: Call kanban tool to create task
    
    # Step 4: Request task assignment
    print("4. Requesting task assignment...")
    # TODO: Use Marcus agent system
    
    # Step 5: Generate solution
    print("5. Generating solution...")
    # TODO: Use Marcus AI engine
    
    # Step 6: Validate solution
    print("6. Validating solution...")
    # TODO: Run tests
    
    print("Integration test complete!")

if __name__ == "__main__":
    asyncio.run(main())
```

## Step 10: Run End-to-End Test

```bash
# 10.1 Run the integration test
python scripts/marcus_swe_bench_simple.py

# 10.2 Check results
ls -la marcus_swe_bench_predictions.jsonl
cat marcus_swe_bench_predictions.jsonl | jq '.'
```

## Next Steps (Implementation Priority)

### Week 1: Core Integration
1. **Complete SWE-Bench tool implementation**
2. **Add repository setup and analysis**
3. **Integrate with Marcus MCP system**
4. **Test with 5-10 instances**

### Week 2: Basic Solution Generation
1. **Implement issue parsing**
2. **Add codebase analysis**
3. **Create simple patch generation**
4. **Test against SWE-Bench evaluation harness**

### Week 3: Marcus Enhancement
1. **Use Marcus context system for code understanding**
2. **Integrate memory system for learning**
3. **Add multi-agent collaboration**
4. **Optimize for 14% target**

## Troubleshooting

**If git clone fails:**
```bash
# Check network and retry
git config --global http.postBuffer 524288000
```

**If Docker fails:**
```bash
# Check Docker is running
docker ps
# Increase Docker memory to 8GB+ in Docker Desktop
```

**If dataset download fails:**
```bash
# Install with specific version
pip install datasets==2.14.0
# Or download manually
wget https://huggingface.co/datasets/princeton-nlp/SWE-bench_Lite/resolve/main/data/test-00000-of-00001.parquet
```

**If workspace directory fills up:**
```bash
# Clean old repositories
rm -rf swe_bench_workspaces/repo_*
```

## Success Metrics

- [ ] SWE-Bench installed and working
- [ ] Can load SWE-Bench Lite instances
- [ ] Can clone and setup repositories
- [ ] Marcus MCP integration working
- [ ] Can generate (empty) prediction files
- [ ] Ready for implementation phase

You're now ready to start implementing the actual solution generation with Marcus!