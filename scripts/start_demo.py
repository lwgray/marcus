#!/usr/bin/env python3
"""
PM Agent Demo Launcher

This script sets up and launches a complete PM Agent demo with:
1. PM Agent MCP server (with chosen kanban provider)
2. Mock Claude workers
3. Visualization UI
"""

import os
import sys
import asyncio
import subprocess
import time
import signal
from pathlib import Path
from typing import List, Optional

# ANSI color codes
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'


class DemoLauncher:
    """Manages the PM Agent demo environment"""
    
    def __init__(self):
        self.processes: List[subprocess.Popen] = []
        self.project_root = Path(__file__).parent
        
    def print_header(self):
        """Print demo header"""
        print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
        print(f"{BOLD}{BLUE}    PM Agent Demo Launcher{RESET}")
        print(f"{BOLD}{BLUE}{'='*60}{RESET}\n")
        
    def select_kanban_provider(self) -> str:
        """Let user select kanban provider"""
        print(f"{BOLD}Select Kanban Provider:{RESET}")
        print("1. Planka (requires local MCP server)")
        print("2. Linear (requires API key)")
        print("3. GitHub Projects (requires token)")
        
        while True:
            choice = input(f"\n{YELLOW}Enter choice (1-3): {RESET}")
            if choice == '1':
                return 'planka'
            elif choice == '2':
                return 'linear'
            elif choice == '3':
                return 'github'
            else:
                print(f"{RED}Invalid choice. Please enter 1, 2, or 3.{RESET}")
                
    def check_environment(self, provider: str) -> bool:
        """Check if required environment variables are set"""
        print(f"\n{BOLD}Checking environment for {provider.upper()}...{RESET}")
        
        required_vars = {
            'planka': ['PLANKA_PROJECT_NAME'],
            'linear': ['LINEAR_API_KEY', 'LINEAR_TEAM_ID'],
            'github': ['GITHUB_TOKEN', 'GITHUB_OWNER', 'GITHUB_REPO']
        }
        
        missing = []
        for var in required_vars.get(provider, []):
            if not os.getenv(var):
                missing.append(var)
                
        if missing:
            print(f"{RED}Missing environment variables:{RESET}")
            for var in missing:
                print(f"  - {var}")
            print(f"\n{YELLOW}Please set these in your .env file or environment{RESET}")
            return False
            
        print(f"{GREEN}✓ Environment configured{RESET}")
        return True
        
    def setup_logging(self):
        """Ensure log directories exist"""
        log_dirs = [
            self.project_root / "logs" / "conversations",
            self.project_root / "logs" / "raw"
        ]
        
        for log_dir in log_dirs:
            log_dir.mkdir(parents=True, exist_ok=True)
            
        print(f"{GREEN}✓ Log directories created{RESET}")
        
    def start_pm_agent(self, provider: str):
        """Start the PM Agent MCP server"""
        print(f"\n{BOLD}Starting PM Agent MCP Server ({provider.upper()})...{RESET}")
        
        env = os.environ.copy()
        env['KANBAN_PROVIDER'] = provider
        env['PYTHONPATH'] = str(self.project_root)
        
        cmd = [
            sys.executable,
            str(self.project_root / "pm_agent_mcp_server_unified.py")
        ]
        
        # Start in new terminal for visibility
        if sys.platform == "darwin":  # macOS
            terminal_cmd = [
                "osascript", "-e",
                f'tell app "Terminal" to do script "cd {self.project_root} && {" ".join(cmd)}"'
            ]
            subprocess.Popen(terminal_cmd)
        else:  # Linux/Windows
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.processes.append(process)
            
        print(f"{GREEN}✓ PM Agent server starting...{RESET}")
        time.sleep(3)  # Give it time to start
        
    def start_mock_workers(self, count: int = 2):
        """Start mock Claude workers"""
        print(f"\n{BOLD}Starting {count} Mock Claude Workers...{RESET}")
        
        for i in range(count):
            worker_name = f"worker_{i+1}"
            cmd = [
                sys.executable,
                str(self.project_root / "mock_claude_worker.py"),
                "--name", worker_name,
                "--skills", "backend,api,database" if i == 0 else "frontend,ui,testing"
            ]
            
            # Start in new terminal
            if sys.platform == "darwin":  # macOS
                terminal_cmd = [
                    "osascript", "-e",
                    f'tell app "Terminal" to do script "cd {self.project_root} && {" ".join(cmd)}"'
                ]
                subprocess.Popen(terminal_cmd)
            else:
                process = subprocess.Popen(cmd)
                self.processes.append(process)
                
            print(f"{GREEN}✓ Started {worker_name}{RESET}")
            time.sleep(2)
            
    def start_visualization(self):
        """Start the visualization UI"""
        print(f"\n{BOLD}Starting Visualization UI...{RESET}")
        
        viz_path = self.project_root / "visualization-ui"
        
        # Check if npm dependencies are installed
        if not (viz_path / "node_modules").exists():
            print(f"{YELLOW}Installing npm dependencies...{RESET}")
            subprocess.run(["npm", "install"], cwd=viz_path, check=True)
            
        # Start the dev server
        if sys.platform == "darwin":  # macOS
            terminal_cmd = [
                "osascript", "-e",
                f'tell app "Terminal" to do script "cd {viz_path} && npm run dev"'
            ]
            subprocess.Popen(terminal_cmd)
        else:
            process = subprocess.Popen(
                ["npm", "run", "dev"],
                cwd=viz_path
            )
            self.processes.append(process)
            
        print(f"{GREEN}✓ Visualization UI starting at http://localhost:4298{RESET}")
        
    def create_sample_tasks(self, provider: str):
        """Create sample tasks in the kanban board"""
        print(f"\n{BOLD}Creating sample tasks...{RESET}")
        
        # This would normally use the kanban API directly
        # For now, we'll just print instructions
        
        if provider == 'planka':
            print(f"{YELLOW}Please create tasks in your Planka board:{RESET}")
            print("1. 'Implement user authentication' (High priority)")
            print("2. 'Create API endpoints' (Medium priority)")
            print("3. 'Add database migrations' (Low priority)")
        elif provider == 'linear':
            print(f"{YELLOW}Sample Linear tasks will be created via API{RESET}")
            # TODO: Implement Linear task creation
        elif provider == 'github':
            print(f"{YELLOW}Please create issues in your GitHub project:{RESET}")
            print("1. 'Implement user authentication' with 'priority/high' label")
            print("2. 'Create API endpoints' with 'priority/medium' label")
            print("3. 'Add database migrations' with 'priority/low' label")
            
    def print_instructions(self):
        """Print usage instructions"""
        print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
        print(f"{BOLD}Demo Environment Running!{RESET}")
        print(f"{BOLD}{BLUE}{'='*60}{RESET}\n")
        
        print(f"{BOLD}Services:{RESET}")
        print(f"  • PM Agent MCP Server: Running")
        print(f"  • Mock Workers: 3 specialized agents (Backend, Frontend, QA)")
        print(f"  • Visualization: http://localhost:4298")
        print(f"  • Logs: ./logs/conversations/")
        
        print(f"\n{BOLD}Next Steps:{RESET}")
        print(f"1. Open http://localhost:4298 to see the visualization")
        print(f"2. Watch as workers request and complete tasks")
        print(f"3. Check logs for detailed conversation flow")
        
        print(f"\n{YELLOW}Press Ctrl+C to stop all services{RESET}")
        
    def cleanup(self, signum=None, frame=None):
        """Clean up all processes"""
        print(f"\n{BOLD}Stopping all services...{RESET}")
        
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                process.kill()
                
        print(f"{GREEN}✓ All services stopped{RESET}")
        sys.exit(0)
        
    def run(self):
        """Run the demo"""
        # Set up signal handler
        signal.signal(signal.SIGINT, self.cleanup)
        
        try:
            # Print header
            self.print_header()
            
            # Select provider
            provider = self.select_kanban_provider()
            
            # Check environment
            if not self.check_environment(provider):
                return
                
            # Setup
            self.setup_logging()
            
            # Start services
            self.start_pm_agent(provider)
            self.start_mock_workers(3)  # Start all 3 specialized workers
            self.start_visualization()
            
            # Create sample tasks
            self.create_sample_tasks(provider)
            
            # Print instructions
            self.print_instructions()
            
            # Keep running
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.cleanup()
        except Exception as e:
            print(f"{RED}Error: {e}{RESET}")
            self.cleanup()


if __name__ == "__main__":
    launcher = DemoLauncher()
    launcher.run()