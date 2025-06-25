#!/usr/bin/env python3
"""Test Anthropic initialization in PM Agent context"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

# Load environment
from dotenv import load_dotenv
load_dotenv()

print("Testing Anthropic initialization...")
print("=" * 50)

# Test 1: Direct import and init
print("\n1. Testing direct AIAnalysisEngine import:")
try:
    from src.integrations.ai_analysis_engine_fixed import AIAnalysisEngine
    engine1 = AIAnalysisEngine()
    print("✅ Direct import successful")
except Exception as e:
    print(f"❌ Direct import failed: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Import through monitoring
print("\n2. Testing ProjectMonitor import:")
try:
    from src.monitoring.project_monitor import ProjectMonitor
    monitor = ProjectMonitor()
    print("✅ ProjectMonitor import successful")
except Exception as e:
    print(f"❌ ProjectMonitor import failed: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Import through health monitor
print("\n3. Testing HealthMonitor import:")
try:
    from src.visualization.health_monitor import HealthMonitor
    health = HealthMonitor()
    print("✅ HealthMonitor import successful")
except Exception as e:
    print(f"❌ HealthMonitor import failed: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Full PM Agent state
print("\n4. Testing PM Agent State initialization:")
try:
    # Change to script directory
    os.chdir(project_root)
    
    # Import PMAgentState class
    from pm_agent_mcp_server_v2 import PMAgentState
    state = PMAgentState()
    print("✅ PM Agent State initialized successfully")
except Exception as e:
    print(f"❌ PM Agent State failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 50)
print("Testing complete.")