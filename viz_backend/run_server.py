#!/usr/bin/env python3
"""
Run the Marcus Visualization API server.

Usage:
    From Marcus root directory:
        python -m viz_backend.run_server

    Or use the convenience script:
        viz_backend/start_server.sh

Options:
    --no-frontend: Skip auto-starting the viz-dashboard frontend
    --restart: Kill any existing server processes before starting
"""

import argparse
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import uvicorn


def find_available_port(start_port: int = 4300, max_attempts: int = 10) -> int:
    """
    Find an available port starting from start_port.

    Parameters
    ----------
    start_port : int
        Port to start searching from
    max_attempts : int
        Maximum number of ports to try

    Returns
    -------
    int
        Available port number

    Raises
    ------
    RuntimeError
        If no available port found
    """
    for port in range(start_port, start_port + max_attempts):
        try:
            # Try to bind to the port
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("0.0.0.0", port))  # nosec B104
                return port
        except OSError:
            continue

    end_port = start_port + max_attempts
    raise RuntimeError(
        f"Could not find available port in range {start_port}-{end_port}"
    )


def update_frontend_env(port: int, dashboard_path: Path) -> bool:
    """
    Update or create .env file in viz-dashboard with the backend API URL.

    Parameters
    ----------
    port : int
        Backend API port number
    dashboard_path : Path
        Path to viz-dashboard directory

    Returns
    -------
    bool
        True if successful, False otherwise
    """
    try:
        env_file = dashboard_path / ".env"
        api_url = f"VITE_API_URL=http://localhost:{port}"

        if env_file.exists():
            # Read existing .env
            with open(env_file, "r") as f:
                lines = f.readlines()

            # Update or add VITE_API_URL
            updated = False
            for i, line in enumerate(lines):
                if line.startswith("VITE_API_URL="):
                    lines[i] = api_url + "\n"
                    updated = True
                    break

            if not updated:
                lines.append(api_url + "\n")

            # Write back
            with open(env_file, "w") as f:
                f.writelines(lines)
        else:
            # Create new .env
            with open(env_file, "w") as f:
                f.write(api_url + "\n")

        print(f"✅ Updated {env_file} with {api_url}")
        return True
    except Exception as e:
        print(f"⚠️  Failed to update .env: {e}")
        return False


def kill_existing_processes() -> None:
    """
    Kill any existing viz_backend server and frontend processes.

    This allows for clean restart without manual process killing.
    """
    try:
        # Kill backend processes
        result = subprocess.run(
            ["pgrep", "-f", "viz_backend.run_server"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            current_pid = str(os.getpid())
            for pid in pids:
                if pid and pid != current_pid:  # Don't kill ourselves
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                        print(f"🔪 Killed existing backend process (PID {pid})")
                    except ProcessLookupError:
                        pass  # Process already dead
                    except Exception as e:
                        print(f"⚠️  Failed to kill process {pid}: {e}")

        # Kill frontend processes (npm/vite)
        result = subprocess.run(
            ["pgrep", "-f", "vite.*viz-dashboard"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            for pid in pids:
                if pid:
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                        print(f"🔪 Killed existing frontend process (PID {pid})")
                    except ProcessLookupError:
                        pass  # Process already dead
                    except Exception as e:
                        print(f"⚠️  Failed to kill process {pid}: {e}")

        # Give processes time to terminate
        if result.stdout.strip():
            time.sleep(1)

    except Exception as e:
        print(f"⚠️  Error during process cleanup: {e}")


def start_frontend(dashboard_path: Path) -> "subprocess.Popen[str] | None":
    """
    Start the viz-dashboard frontend using npm.

    Parameters
    ----------
    dashboard_path : Path
        Path to viz-dashboard directory

    Returns
    -------
    subprocess.Popen | None
        Frontend process if started successfully, None otherwise
    """
    try:
        # Check if node_modules exists
        node_modules = dashboard_path / "node_modules"
        if not node_modules.exists():
            print("📦 Installing frontend dependencies (first time setup)...")
            install_result = subprocess.run(
                ["npm", "install"],
                cwd=dashboard_path,
                capture_output=True,
                text=True,
                check=False,
            )
            if install_result.returncode != 0:
                print(f"❌ npm install failed: {install_result.stderr}")
                return None

        print("🚀 Starting viz-dashboard frontend...")

        # Start frontend in background
        process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=dashboard_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Wait a moment for the server to start
        time.sleep(2)

        # Check if process is still running
        if process.poll() is not None:
            print("❌ Frontend failed to start")
            return None

        print("✅ Frontend started successfully")
        print("📱 Dashboard should open at: http://localhost:5173")
        return process
    except FileNotFoundError:
        print("⚠️  npm not found. Please install Node.js to auto-start the frontend.")
        return None
    except Exception as e:
        print(f"⚠️  Failed to start frontend: {e}")
        return None


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run Marcus Visualization Backend")
    parser.add_argument(
        "--no-frontend",
        action="store_true",
        help="Skip auto-starting the viz-dashboard frontend",
    )
    parser.add_argument(
        "--restart",
        action="store_true",
        help="Kill any existing server processes before starting",
    )
    args = parser.parse_args()

    # Kill existing processes if --restart flag is set
    if args.restart:
        print("🔄 Restart mode: Cleaning up existing processes...")
        kill_existing_processes()
        print("✅ Cleanup complete\n")

    frontend_process = None

    try:
        port = find_available_port(start_port=4300)
        print("=" * 60)
        print(f"🚀 Starting Marcus Viz Backend on http://localhost:{port}")
        print(f"📊 API Documentation: http://localhost:{port}/docs")
        print(f"✅ Health Check: http://localhost:{port}/health")
        print("=" * 60)

        # Find viz-dashboard directory
        dashboard_path = Path(__file__).parent.parent / "viz-dashboard"

        if not args.no_frontend:
            if dashboard_path.exists():
                # Update .env file
                update_frontend_env(port, dashboard_path)

                # Start frontend
                frontend_process = start_frontend(dashboard_path)
                if frontend_process:
                    print("=" * 60)
                    print("🎉 Full stack running:")
                    print(f"   Backend:  http://localhost:{port}")
                    print("   Frontend: http://localhost:5173")
                    print("=" * 60)
                else:
                    print("\n⚠️  Frontend auto-start failed. Start manually:")
                    print(f"   cd {dashboard_path}")
                    print("   npm run dev")
            else:
                print(f"\n⚠️  viz-dashboard not found at {dashboard_path}")
                print("   Frontend will not auto-start")
        else:
            print("\n💡 Frontend auto-start disabled. Start manually:")
            print(f"   cd {dashboard_path}")
            print("   npm run dev")

        print("\nPress Ctrl+C to stop all services\n")

        # Run backend server
        uvicorn.run(
            "viz_backend.api:app",
            host="0.0.0.0",  # nosec B104
            port=port,
            reload=True,  # Enable auto-reload during development
            log_level="info",
        )
    except RuntimeError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Stopping services...")
        if frontend_process:
            frontend_process.terminate()
            frontend_process.wait(timeout=5)
            print("✅ Frontend stopped")
        print("✅ Backend stopped")
        sys.exit(0)
    finally:
        # Cleanup frontend process if it exists
        if frontend_process and frontend_process.poll() is None:
            frontend_process.terminate()
