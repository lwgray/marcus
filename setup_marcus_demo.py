#!/usr/bin/env python3
"""
Marcus Demo Setup Launcher

Quick launcher that ensures prerequisites and runs the full demo setup.
"""

import os
import subprocess  # nosec B404
import sys
from pathlib import Path


def check_python_version() -> bool:
    """Ensure Python 3.11+"""
    if sys.version_info < (3, 11):
        print("❌ Python 3.11+ required")
        print(f"   Current version: {sys.version}")
        return False
    return True


def check_docker() -> bool:
    """Check if Docker is running"""
    try:
        result = subprocess.run(
            ["docker", "ps"], capture_output=True, text=True
        )  # nosec B603 B607
        return result.returncode == 0
    except FileNotFoundError:
        print("❌ Docker not found. Please install Docker.")
        return False


def check_planka_running() -> bool:
    """Check if Planka is running on port 3333"""
    try:
        # Check if planka container is running
        result = subprocess.run(
            [
                "docker",
                "ps",
                "--filter",
                "name=kanban",
                "--filter",
                "status=running",
                "-q",
            ],
            capture_output=True,
            text=True,
        )  # nosec B603 B607
        return bool(result.stdout.strip())
    except:
        return False


def main() -> None:
    print("🏛️  Marcus Demo Setup")
    print("=" * 30)

    # Check prerequisites
    print("🔍 Checking prerequisites...")

    if not check_python_version():
        sys.exit(1)
    print("✅ Python 3.11+ found")

    if not check_docker():
        sys.exit(1)
    print("✅ Docker found")

    # Check if Planka is running
    if not check_planka_running():
        print("⚠️  Planka not running. Starting setup instructions...")
        print("\n📋 Setup Planka (one-time setup):")
        print("1. Clone kanban-mcp:")
        print(
            "   git clone https://github.com/bradrisse/kanban-mcp.git ~/dev/kanban-mcp"
        )
        print("2. Start Planka:")
        print("   cd ~/dev/kanban-mcp && docker-compose up -d")
        print("3. Wait for startup, then visit: http://localhost:3333")
        print("4. Login with: demo@demo.demo / demo")
        print("5. Run this script again: python setup_marcus_demo.py")
        return

    print("✅ Planka running on http://localhost:3333")

    # Run the full setup
    print("\n🚀 Running Marcus demo setup...")
    todo_setup = (
        Path(__file__).parent / "projects" / "todo_app" / "setup_demo_project.py"
    )

    try:
        subprocess.run([sys.executable, str(todo_setup)], check=True)  # nosec B603
    except subprocess.CalledProcessError as e:
        print(f"❌ Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
