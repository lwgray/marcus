#!/usr/bin/env python3
"""Test the MVB initialization"""

import os
import sys
from pathlib import Path

# Add to path
script_dir = Path(__file__).parent.absolute()
os.chdir(script_dir)
sys.path.insert(0, str(script_dir))

# Load env
from dotenv import load_dotenv
load_dotenv()

print("Testing pm_agent_mvp_fixed initialization...")

try:
    from src.pm_agent_mvp_fixed import PMAgentMVP
    print("✅ Import successful")
    
    agent = PMAgentMVP()
    print("✅ PMAgentMVP created successfully")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()