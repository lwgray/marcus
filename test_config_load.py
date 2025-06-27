#!/usr/bin/env python3
"""Test if SimpleMCPKanbanClient loads config properly"""

import os
import sys
from pathlib import Path

# Change to script directory like marcus does
script_dir = Path(__file__).parent.absolute()
os.chdir(script_dir)
sys.path.insert(0, str(script_dir))

print(f"Working directory: {os.getcwd()}")
print(f"Config files in directory:")
for f in os.listdir('.'):
    if f.startswith('config'):
        print(f"  - {f}")

from src.integrations.mcp_kanban_client_simple import SimpleMCPKanbanClient

client = SimpleMCPKanbanClient()
print(f"\nClient initialized:")
print(f"  board_id: {client.board_id}")
print(f"  project_id: {client.project_id}")