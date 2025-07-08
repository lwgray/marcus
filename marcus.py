#!/usr/bin/env python3
"""
Marcus MCP Server - Entry Point

This is the main entry point for the Marcus MCP server.
It delegates to the modularized implementation in src/marcus_mcp/
"""

import asyncio
import os
import signal
import sys
from pathlib import Path

# Force Python to run in unbuffered mode to prevent vertical text in MCP
os.environ["PYTHONUNBUFFERED"] = "1"

# Force stdout/stderr to be unbuffered
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(line_buffering=True)

# Get the Marcus root directory
marcus_root = Path(__file__).parent.resolve()

# Add parent directory to path before imports
sys.path.insert(0, str(marcus_root))

# Only change directory if we're not already there
# This helps prevent stdio issues when running from different directories
if os.getcwd() != str(marcus_root):
    os.chdir(marcus_root)

from src.config.config_loader import get_config  # noqa: E402


def load_config():
    """Load configuration from marcus.config.json and set environment variables"""
    try:
        config = get_config()
        print(f"✅ Loaded configuration from {config.config_path}", file=sys.stderr)

        # Set environment variables that other parts of the code expect
        # This is temporary until we update all code to use config directly

        # Kanban provider
        os.environ["KANBAN_PROVIDER"] = config.get("kanban.provider", "planka")

        # Planka settings
        planka_config = config.get("kanban.planka", {})
        if planka_config:
            os.environ["PLANKA_BASE_URL"] = planka_config.get(
                "base_url", "http://localhost:3333"
            )
            os.environ["PLANKA_AGENT_EMAIL"] = planka_config.get(
                "email", "demo@demo.demo"
            )
            os.environ["PLANKA_AGENT_PASSWORD"] = planka_config.get("password", "demo")
            os.environ["PLANKA_PROJECT_ID"] = planka_config.get("project_id", "")
            os.environ["PLANKA_BOARD_ID"] = planka_config.get("board_id", "")

        # GitHub settings
        github_config = config.get("kanban.github", {})
        if github_config.get("token"):
            os.environ["GITHUB_TOKEN"] = github_config["token"]
            os.environ["GITHUB_OWNER"] = github_config.get("owner", "")
            os.environ["GITHUB_REPO"] = github_config.get("repo", "")

        # AI settings
        ai_config = config.get("ai", {})
        if ai_config.get("anthropic_api_key"):
            os.environ["ANTHROPIC_API_KEY"] = ai_config["anthropic_api_key"]
        if ai_config.get("openai_api_key"):
            os.environ["OPENAI_API_KEY"] = ai_config["openai_api_key"]

        # Monitoring settings
        monitoring_config = config.get("monitoring", {})
        os.environ["MARCUS_MONITORING_INTERVAL"] = str(
            monitoring_config.get("interval", 900)
        )

        # Communication settings
        comm_config = config.get("communication", {})
        os.environ["MARCUS_SLACK_ENABLED"] = str(
            comm_config.get("slack_enabled", False)
        ).lower()
        os.environ["MARCUS_EMAIL_ENABLED"] = str(
            comm_config.get("email_enabled", False)
        ).lower()

        # Debug settings
        advanced_config = config.get("advanced", {})
        os.environ["MARCUS_DEBUG"] = str(advanced_config.get("debug", False)).lower()
        os.environ["MARCUS_PORT"] = str(advanced_config.get("port", 8000))

    except FileNotFoundError as e:
        print(f"❌ Configuration error: {e}", file=sys.stderr)
        print("Please run: python scripts/migrate_config.py", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point - Web UI enabled by default"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Marcus - AI-Powered Project Management"
    )
    parser.add_argument(
        "--no-web",
        action="store_true",
        help="Disable web UI dashboard (run MCP server only)",
    )
    parser.add_argument(
        "--port", type=int, default=5000, help="Web UI port (default: 5000)"
    )

    args = parser.parse_args()

    # Load configuration before starting
    load_config()

    if args.no_web:
        # Run MCP server only
        print("🚀 Starting Marcus MCP Server (no web UI)...", file=sys.stderr)
        try:
            from src.marcus_mcp import main as mcp_main

            print("✅ Imported MCP server module", file=sys.stderr)
            asyncio.run(mcp_main())
        except Exception as e:
            print(f"❌ Failed to start MCP server: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc(file=sys.stderr)
            sys.exit(1)
    else:
        # Run integrated server with web UI (default)
        print("🚀 Starting Marcus with Web UI Dashboard...", file=sys.stderr)
        print(
            f"   MCP Server + Web Interface at http://localhost:{args.port}",
            file=sys.stderr,
        )
        print("", file=sys.stderr)

        # Kill any existing Flask processes
        os.system('pkill -f "python.*src.api.app" 2>/dev/null')

        from src.api.integrated_server import IntegratedMarcusServer

        server = IntegratedMarcusServer(enable_web_ui=True, web_port=args.port)

        # Set up signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            print("\n👋 Gracefully shutting down Marcus...", file=sys.stderr)
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            asyncio.run(server.run())
        except KeyboardInterrupt:
            print("\n👋 Marcus stopped by user", file=sys.stderr)
            sys.exit(0)


if __name__ == "__main__":
    main()
