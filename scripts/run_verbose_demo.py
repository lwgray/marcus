#!/usr/bin/env python3
"""
Run a complete verbose demo of PM Agent with mock workers
Shows full conversation and decision-making process
"""

import asyncio
import subprocess
import time
import os
import sys
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.table import Table

console = Console()


class VerboseDemo:
    """Orchestrate a verbose demo of PM Agent"""
    
    def __init__(self):
        self.pm_agent_process = None
        self.worker_processes = []
        self.recording_process = None
        
    def check_prerequisites(self):
        """Check if all prerequisites are met"""
        console.print(Panel.fit(
            "[bold cyan]PM Agent Verbose Demo[/bold cyan]\n"
            "This demo shows detailed conversation between PM Agent and Workers",
            title="🎬 Demo Setup",
            border_style="cyan"
        ))
        
        checks = {
            "Planka Running": self._check_planka(),
            "Python Environment": self._check_python(),
            "Required Packages": self._check_packages(),
            "FFmpeg (optional)": self._check_ffmpeg()
        }
        
        table = Table(title="Prerequisites Check", show_header=True)
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        
        all_good = True
        for component, status in checks.items():
            if "optional" in component.lower() and not status:
                table.add_row(component, "[yellow]⚠ Not found (optional)[/yellow]")
            elif status:
                table.add_row(component, "[green]✓ Ready[/green]")
            else:
                table.add_row(component, "[red]✗ Missing[/red]")
                if "optional" not in component.lower():
                    all_good = False
        
        console.print(table)
        return all_good
    
    def _check_planka(self):
        """Check if Planka is accessible"""
        try:
            import requests
            response = requests.get("http://localhost:3333", timeout=2)
            return response.status_code < 500
        except:
            return False
    
    def _check_python(self):
        """Check Python version"""
        return sys.version_info >= (3, 8)
    
    def _check_packages(self):
        """Check required packages"""
        try:
            import mcp
            import rich
            return True
        except ImportError:
            return False
    
    def _check_ffmpeg(self):
        """Check if ffmpeg is available for recording"""
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            return True
        except:
            return False
    
    async def start_pm_agent(self, verbose=True):
        """Start PM Agent in verbose mode"""
        console.print("\n[bold green]Starting PM Agent in verbose mode...[/bold green]")
        
        if verbose:
            # Use the verbose version
            cmd = [sys.executable, "pm_agent_mcp_server_verbose.py"]
        else:
            cmd = [sys.executable, "pm_agent_mcp_server.py"]
        
        self.pm_agent_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Wait for PM Agent to start
        await asyncio.sleep(3)
        console.print("[green]✓ PM Agent started[/green]")
    
    async def start_workers(self, num_workers=1, verbose=True):
        """Start mock workers"""
        console.print(f"\n[bold green]Starting {num_workers} mock worker(s)...[/bold green]")
        
        script = "mock_claude_worker_verbose.py" if verbose else "mock_claude_worker.py"
        
        for i in range(num_workers):
            # Each worker gets a different selection
            cmd = [sys.executable, f"scripts/{script}"]
            
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Send worker selection
            process.stdin.write(f"{i+1}\n")
            process.stdin.flush()
            
            self.worker_processes.append(process)
            await asyncio.sleep(1)
        
        console.print(f"[green]✓ {num_workers} worker(s) started[/green]")
    
    async def start_recording(self, duration):
        """Start screen recording if ffmpeg is available"""
        if self._check_ffmpeg():
            console.print("\n[bold yellow]Starting screen recording...[/bold yellow]")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"recordings/pm_agent_demo_{timestamp}.mp4"
            os.makedirs("recordings", exist_ok=True)
            
            cmd = [
                "ffmpeg",
                "-f", "avfoundation",
                "-framerate", "30",
                "-i", "1:none",  # Screen 1, no audio
                "-t", str(duration),
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                "-y",  # Overwrite
                output_file
            ]
            
            self.recording_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            console.print(f"[yellow]Recording to: {output_file}[/yellow]")
            return output_file
        return None
    
    async def monitor_output(self, duration):
        """Monitor and display output from PM Agent and workers"""
        console.print("\n[bold]Demo running... Watch the conversation unfold![/bold]\n")
        
        # Create a layout for split view if needed
        layout = Layout()
        
        start_time = time.time()
        
        while time.time() - start_time < duration:
            # Check if processes are still running
            if self.pm_agent_process and self.pm_agent_process.poll() is not None:
                console.print("[red]PM Agent has stopped unexpectedly[/red]")
                break
            
            # Show progress
            elapsed = int(time.time() - start_time)
            remaining = duration - elapsed
            console.print(f"\r[dim]Time: {elapsed}s / {duration}s[/dim]", end="")
            
            await asyncio.sleep(1)
        
        console.print("\n\n[bold green]Demo time complete![/bold green]")
    
    def cleanup(self):
        """Clean up all processes"""
        console.print("\n[bold yellow]Cleaning up...[/bold yellow]")
        
        # Terminate processes
        if self.pm_agent_process:
            self.pm_agent_process.terminate()
            self.pm_agent_process.wait()
        
        for process in self.worker_processes:
            process.terminate()
            process.wait()
        
        if self.recording_process:
            self.recording_process.terminate()
            self.recording_process.wait()
        
        console.print("[green]✓ Cleanup complete[/green]")
    
    async def run_demo(self, duration=300, num_workers=1, record=True):
        """Run the complete demo"""
        try:
            # Start components
            await self.start_pm_agent(verbose=True)
            await asyncio.sleep(2)
            
            await self.start_workers(num_workers, verbose=True)
            
            recording_file = None
            if record:
                recording_file = await self.start_recording(duration)
            
            # Monitor demo
            await self.monitor_output(duration)
            
            # Show summary
            console.print(Panel(
                "[bold green]Demo Complete![/bold green]\n\n"
                f"Duration: {duration} seconds\n"
                f"Workers: {num_workers}\n"
                f"Recording: {recording_file or 'Not recorded'}\n\n"
                "Check the logs for detailed conversation history:\n"
                "• pm_agent_conversation.log\n"
                "• Console output above",
                title="📊 Demo Summary",
                border_style="green"
            ))
            
        finally:
            self.cleanup()


async def main():
    """Main demo runner"""
    demo = VerboseDemo()
    
    # Check prerequisites
    if not demo.check_prerequisites():
        console.print("\n[bold red]Please ensure all prerequisites are met before running the demo.[/bold red]")
        console.print("\nRequired setup:")
        console.print("1. Start Planka: docker-compose up -d")
        console.print("2. Install packages: pip install mcp rich requests")
        return
    
    # Demo options
    console.print("\n[bold]Demo Options:[/bold]")
    console.print("1. Quick Demo (1 worker, 2 minutes)")
    console.print("2. Standard Demo (2 workers, 5 minutes)")
    console.print("3. Full Demo (3 workers, 10 minutes)")
    console.print("4. Custom Demo")
    
    choice = console.input("\n[bold yellow]Select demo option (1-4):[/bold yellow] ").strip()
    
    demos = {
        "1": (120, 1, True),    # 2 minutes, 1 worker, record
        "2": (300, 2, True),    # 5 minutes, 2 workers, record
        "3": (600, 3, True),    # 10 minutes, 3 workers, record
    }
    
    if choice in demos:
        duration, workers, record = demos[choice]
    elif choice == "4":
        duration = int(console.input("Duration in seconds: "))
        workers = int(console.input("Number of workers (1-3): "))
        record = console.input("Record video? (y/n): ").lower() == 'y'
    else:
        console.print("[red]Invalid choice[/red]")
        return
    
    # Confirm
    console.print(f"\n[bold]Demo Configuration:[/bold]")
    console.print(f"• Duration: {duration} seconds ({duration/60:.1f} minutes)")
    console.print(f"• Workers: {workers}")
    console.print(f"• Recording: {'Yes' if record else 'No'}")
    
    if console.input("\n[bold yellow]Start demo? (y/n):[/bold yellow] ").lower() != 'y':
        console.print("[yellow]Demo cancelled[/yellow]")
        return
    
    # Run demo
    await demo.run_demo(duration, workers, record)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[bold red]Demo interrupted by user[/bold red]")
    except Exception as e:
        console.print(f"\n[bold red]Error: {e}[/bold red]")
        import traceback
        traceback.print_exc()