#!/usr/bin/env python3
"""
Single Agent Trial Runner.

Runs multiple independent trials of a single agent completing a task.
Each trial is isolated in its own directory OUTSIDE the Marcus codebase
with a fresh Claude CLI instance and clean workspace.
"""

import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anthropic


class TrialRunner:
    """Manages execution of single-agent trials."""

    def __init__(
        self,
        prompt_file: Path,
        output_dir: Path,
        num_trials: int = 20,
        timeout_minutes: int = 10,
        judge_model: str = "claude-3-haiku-20240307",
        experiment_name: str | None = None,
        parallel: bool = False,
        max_workers: int = 10,
        validate: bool = False,
        show_browser: bool = False,
    ):
        """
        Initialize trial runner.

        Parameters
        ----------
        prompt_file : Path
            Path to the prompt markdown file
        output_dir : Path
            Base directory for experiments (e.g., ~/trials)
            A timestamped subfolder will be created for this run
        num_trials : int
            Number of independent trials to run
        timeout_minutes : int
            Maximum time per trial in minutes
        judge_model : str
            Claude model to use for evaluation
        experiment_name : str, optional
            Name for this experiment (default: uses prompt filename)
        parallel : bool
            Whether to run trials in parallel (default: False)
        max_workers : int
            Maximum number of parallel workers (default: 10)
        validate : bool
            Whether to validate that games actually work (default: False)
        """
        self.prompt_file = prompt_file
        self.num_trials = num_trials
        self.timeout_seconds = timeout_minutes * 60
        self.judge_model = judge_model
        self.parallel = parallel
        self.max_workers = max_workers
        self.validate = validate
        self.show_browser = show_browser
        self.shared_browser: subprocess.Popen[str] | None = None
        self.browser_ws_url: str | None = None

        # Generate experiment name from prompt file if not provided
        if experiment_name is None:
            experiment_name = prompt_file.stem  # e.g., "snake_game_single_agent"

        # Create timestamped experiment directory
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        experiment_dir_name = f"{experiment_name}_{timestamp}"
        self.output_dir = (output_dir / experiment_dir_name).resolve()

        # Validate output_dir is outside Marcus
        marcus_dir = Path(__file__).parent.parent.resolve()
        try:
            self.output_dir.relative_to(marcus_dir)
            print("ERROR: Output dir must be OUTSIDE Marcus directory!")
            print(f"Marcus: {marcus_dir}")
            print(f"Output: {self.output_dir}")
            sys.exit(1)
        except ValueError:
            # Good - output_dir is not inside marcus_dir
            pass

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Results tracking
        self.results_file = self.output_dir / "trial_results.json"
        self.results: dict[str, Any] = {
            "experiment_name": "single_agent_snake_game",
            "num_trials": num_trials,
            "timeout_minutes": timeout_minutes,
            "start_time": None,
            "end_time": None,
            "trials": [],
        }

    def get_trial_dir(self, trial_num: int) -> Path:
        """Get directory for a specific trial."""
        return self.output_dir / f"trial_{trial_num:03d}"

    def run_single_trial(self, trial_num: int) -> dict[str, Any]:
        """
        Run a single independent trial using Claude CLI.

        Parameters
        ----------
        trial_num : int
            Trial number (1-indexed)

        Returns
        -------
        dict
            Trial results including timing and success
        """
        trial_dir = self.get_trial_dir(trial_num)
        trial_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n[Trial {trial_num}/{self.num_trials}] Starting in {trial_dir}")

        # Read the prompt
        with open(self.prompt_file) as f:
            prompt_content = f.read()

        # Create prompt file for this trial
        trial_prompt_file = trial_dir / "prompt.md"
        with open(trial_prompt_file, "w") as f:
            f.write(prompt_content)

        # Track timing
        start_time = datetime.now(timezone.utc)
        start_timestamp = start_time.isoformat()

        trial_result = {
            "trial_number": trial_num,
            "trial_dir": str(trial_dir),
            "start_time": start_timestamp,
            "end_time": None,
            "duration_seconds": None,
            "success": False,
            "error": None,
            "timed_out": False,
        }

        # Create log file
        log_file = trial_dir / "trial.log"

        try:
            # Run Claude CLI using shell script approach (like Marcus does)
            # This ensures proper stdin redirection and environment setup
            print(f"  Working directory: {trial_dir}")
            print(f"  Timeout: {self.timeout_seconds}s")

            # Create shell script to run Claude with proper redirection
            # This matches the Marcus experiment spawner approach
            run_script = f"""#!/bin/bash
# Source shell profile to get claude in PATH
[ -f ~/.zshrc ] && source ~/.zshrc
[ -f ~/.bashrc ] && source ~/.bashrc

cd {trial_dir} || exit 1

# Run Claude CLI with stdin redirection (NOT --print flag)
# The --print flag causes early exit after scaffolding
claude --dangerously-skip-permissions < {trial_prompt_file}

exit $?
"""
            script_file = trial_dir / "run_trial.sh"
            with open(script_file, "w") as f:
                f.write(run_script)
            script_file.chmod(0o755)

            # Run the script and capture output
            with open(log_file, "w") as log_f:
                try:
                    result = subprocess.run(
                        ["bash", str(script_file)],
                        stdout=log_f,
                        stderr=subprocess.STDOUT,
                        timeout=self.timeout_seconds,
                        cwd=trial_dir,
                    )

                    if result.returncode == 0:
                        trial_result["success"] = True
                        print("  ✓ Completed successfully")
                    else:
                        trial_result["error"] = f"exit_code_{result.returncode}"
                        print(f"  ✗ Failed with exit code {result.returncode}")

                except subprocess.TimeoutExpired:
                    trial_result["error"] = "timeout"
                    trial_result["timed_out"] = True
                    print(f"  ✗ Timed out after {self.timeout_seconds}s")

        except Exception as e:
            print(f"  ✗ Error: {e}")
            trial_result["error"] = str(e)

        # Record end time
        end_time = datetime.now(timezone.utc)
        trial_result["end_time"] = end_time.isoformat()
        trial_result["duration_seconds"] = (end_time - start_time).total_seconds()

        print(f"  Duration: {trial_result['duration_seconds']:.1f}s")

        # Validate the game if requested
        if self.validate and trial_result["success"]:
            print("  Validating game functionality...")
            validation_result = self.validate_trial(trial_dir)
            trial_result["validation"] = validation_result

            if validation_result["validation_passed"]:
                proj_type = validation_result["project_type"]
                print(f"  ✓ Validation passed - {proj_type} game is functional!")
            else:
                print("  ✗ Validation failed")
                if validation_result.get("error"):
                    print(f"    - {validation_result['error']}")
                elif validation_result["game_functional"] is False:
                    print("    - Game did not respond to interactions")

        # Save individual trial result
        trial_result_file = trial_dir / "result.json"
        with open(trial_result_file, "w") as f:
            json.dump(trial_result, f, indent=2)

        return trial_result

    def _launch_shared_browser(self) -> None:
        """
        Launch a shared browser for all validations.

        Uses tabs instead of windows.
        """
        launch_script = """
const puppeteer = require('puppeteer');
(async () => {
    const browser = await puppeteer.launch({
        headless: false,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    const wsEndpoint = browser.wsEndpoint();
    console.log('WS_ENDPOINT:' + wsEndpoint);
    // Keep process alive
    await new Promise(() => {});
})();
"""
        script_file = self.output_dir / "_shared_browser.js"
        with open(script_file, "w") as f:
            f.write(launch_script)

        # Start browser process
        self.shared_browser = subprocess.Popen(
            ["node", str(script_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Read WebSocket endpoint from output
        if self.shared_browser.stdout:
            for line in self.shared_browser.stdout:
                if "WS_ENDPOINT:" in line:
                    self.browser_ws_url = line.strip().split("WS_ENDPOINT:")[1]
                    print(f"  Shared browser launched: {self.browser_ws_url}")
                    break

        time.sleep(1)  # Give browser time to fully initialize

    def _cleanup_shared_browser(self) -> None:
        """Clean up the shared browser process."""
        if self.shared_browser:
            print("\nClosing shared browser...")
            self.shared_browser.terminate()
            self.shared_browser.wait(timeout=5)

    def validate_trial(self, trial_dir: Path) -> dict[str, Any]:
        """
        Validate that the generated game actually works.

        Process:
        1. Inspecting directory to determine project type
        2. Starting the app (server if needed, or static file)
        3. Testing interactivity with flexible Puppeteer script

        Parameters
        ----------
        trial_dir : Path
            Directory containing the trial output

        Returns
        -------
        dict
            Validation results
        """
        validation: dict[str, Any] = {
            "project_type": None,
            "game_functional": None,
            "validation_passed": False,
            "error": None,
        }

        # Inspect directory to determine project type and how to run it
        html_files = list(trial_dir.glob("*.html"))
        has_package_json = (trial_dir / "package.json").exists()
        has_python = any(trial_dir.glob("*.py"))

        url = None
        server_process = None

        try:
            # Determine how to run the project
            if has_package_json:
                validation["project_type"] = "nodejs"
                # Start Node.js server
                subprocess.run(
                    ["npm", "install"],
                    cwd=trial_dir,
                    capture_output=True,
                    timeout=60,
                )
                server_process = subprocess.Popen(
                    ["npm", "start"],
                    cwd=trial_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                time.sleep(3)  # Wait for server to start
                url = "http://localhost:3000"
            elif has_python:
                validation["project_type"] = "python"
                # Try to start Python server
                server_process = subprocess.Popen(
                    ["python3", "-m", "http.server", "8000"],
                    cwd=trial_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                time.sleep(2)
                url = "http://localhost:8000"
            elif html_files:
                validation["project_type"] = "static_html"
                url = f"file://{html_files[0].resolve()}"
            else:
                validation["error"] = "No runnable files found"
                return validation

            # Create flexible validation script
            if self.browser_ws_url:
                # Connect to shared browser (creates new tab)
                browser_setup = f"""
    console.error('Connecting to shared browser: {self.browser_ws_url}');
    const browser = await puppeteer.connect({{
        browserWSEndpoint: '{self.browser_ws_url}'
    }});
    console.error('Connected successfully');
    const shouldCloseBrowser = false;"""
            else:
                # Launch new browser
                headless_mode = "false" if self.show_browser else "true"
                browser_setup = f"""
    console.error('Launching new browser');
    const browser = await puppeteer.launch({{
        headless: {headless_mode},
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    }});
    const shouldCloseBrowser = true;"""

            test_script = f"""
const puppeteer = require('puppeteer');
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

(async () => {{
    try {{
{browser_setup}

    try {{
        const page = await browser.newPage();
        await page.goto('{url}', {{ waitUntil: 'networkidle0', timeout: 10000 }});
        await delay(1000);

        // Take initial screenshot
        const before = await page.screenshot({{ encoding: 'base64' }});

        // Try multiple start methods
        await page.keyboard.press('Space');
        await page.keyboard.press('Enter');
        await page.click('body').catch(() => {{}});
        await delay(500);

        // Try multiple control schemes
        const keys = [
            'ArrowUp', 'ArrowRight', 'ArrowDown', 'ArrowLeft',
            'w', 'a', 's', 'd'
        ];
        for (const key of keys) {{
            await page.keyboard.press(key);
            await delay(100);
        }}

        // Run for a bit
        await delay(3000);

        // Take final screenshot
        const after = await page.screenshot({{ encoding: 'base64' }});

        // Check for changes
        const changed = before !== after;

        // Check for any numbers (score)
        const hasNumbers = await page.evaluate(() => {{
            return /\\d+/.test(document.body.textContent);
        }});

        // Check canvas activity
        const hasCanvas = await page.evaluate(() => {{
            const canvas = document.querySelector('canvas');
            if (!canvas) return false;
            const ctx = canvas.getContext('2d');
            const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            return imageData.data.some(pixel => pixel !== 0);
        }}).catch(() => false);

        if (changed || hasCanvas) {{
            console.log('FUNCTIONAL');
        }} else {{
            console.log('NOT_FUNCTIONAL');
        }}
    }} catch (error) {{
        console.error('Validation error:', error);
        console.log('ERROR:' + error.message);
    }} finally {{
        if (shouldCloseBrowser) {{
            await browser.close();
        }} else {{
            // Close only this page when using shared browser
            try {{
                await page.close();
            }} catch (e) {{
                console.error('Page close error:', e);
            }}
        }}
    }}
    }} catch (setupError) {{
        console.error('Browser setup error:', setupError);
        console.log('ERROR:' + setupError.message);
    }}
}})();
"""
            test_script_file = trial_dir / "validate_game.js"
            with open(test_script_file, "w") as f:
                f.write(test_script)

            result = subprocess.run(
                ["node", str(test_script_file)],
                capture_output=True,
                text=True,
                timeout=20,
                cwd=trial_dir,
            )

            output = result.stdout.strip()
            if "FUNCTIONAL" in output:
                validation["game_functional"] = True
                validation["validation_passed"] = True
            elif "NOT_FUNCTIONAL" in output:
                validation["game_functional"] = False
            else:
                validation["error"] = output

        except Exception as e:
            validation["error"] = str(e)
        finally:
            # Clean up server process
            if server_process:
                server_process.terminate()
                server_process.wait(timeout=5)

        return validation

    def _run_serial(self) -> list[dict[str, Any]]:
        """Run trials serially (one after another)."""
        trial_results = []
        for i in range(self.num_trials):
            result = self.run_single_trial(i + 1)
            trial_results.append(result)

            # Brief pause between trials
            if i < self.num_trials - 1:
                time.sleep(2)

        return trial_results

    def _run_parallel(self) -> list[dict[str, Any]]:
        """Run trials in parallel using thread pool."""
        trial_results: list[dict[str, Any] | None] = [
            None
        ] * self.num_trials  # Pre-allocate to maintain order

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all trials
            future_to_trial = {
                executor.submit(self.run_single_trial, i + 1): i
                for i in range(self.num_trials)
            }

            # Collect results as they complete
            for future in as_completed(future_to_trial):
                trial_idx = future_to_trial[future]
                try:
                    result = future.result()
                    trial_results[trial_idx] = result
                except Exception as e:
                    print(f"\n✗ Trial {trial_idx + 1} failed with exception: {e}")
                    trial_results[trial_idx] = {
                        "trial_number": trial_idx + 1,
                        "success": False,
                        "error": str(e),
                    }

        return [r for r in trial_results if r is not None]

    def run_all_trials(self) -> None:
        """Run all trials (serial or parallel based on config)."""
        self.results["start_time"] = datetime.now(timezone.utc).isoformat()

        mode = "PARALLEL" if self.parallel else "SERIAL"
        print("\n" + "=" * 70)
        print(f"RUNNING {self.num_trials} SINGLE-AGENT TRIALS ({mode})")
        print("=" * 70)
        print(f"Output directory: {self.output_dir}")
        print(f"Timeout per trial: {self.timeout_seconds / 60:.0f} minutes")
        if self.parallel:
            print(f"Max workers: {self.max_workers}")
        print("=" * 70)

        # Launch shared browser if showing browser windows
        if self.show_browser and self.validate:
            print("\nLaunching shared browser for validation...")
            self._launch_shared_browser()

        try:
            if self.parallel:
                trial_results = self._run_parallel()
            else:
                trial_results = self._run_serial()
        finally:
            # Clean up shared browser
            if self.shared_browser:
                self._cleanup_shared_browser()

        self.results["trials"] = trial_results
        self.results["end_time"] = datetime.now(timezone.utc).isoformat()

        # Calculate summary statistics
        successful_trials = sum(1 for t in trial_results if t["success"])
        timed_out = sum(1 for t in trial_results if t.get("timed_out", False))
        total_duration = sum(
            t["duration_seconds"]
            for t in trial_results
            if t["duration_seconds"] is not None
        )
        avg_duration = total_duration / len(trial_results) if trial_results else 0

        self.results["summary"] = {
            "successful_trials": successful_trials,
            "failed_trials": self.num_trials - successful_trials,
            "timed_out_trials": timed_out,
            "success_rate": successful_trials / self.num_trials,
            "total_duration_seconds": total_duration,
            "average_duration_seconds": avg_duration,
        }

        # Add validation statistics if validation was enabled
        if self.validate:
            validated_trials = sum(
                1
                for t in trial_results
                if "validation" in t and t["validation"]["validation_passed"]
            )
            self.results["summary"]["validated_trials"] = validated_trials
            self.results["summary"]["validation_pass_rate"] = (
                validated_trials / self.num_trials
            )

        # Save results
        with open(self.results_file, "w") as f:
            json.dump(self.results, f, indent=2)

        print("\n" + "=" * 70)
        print("TRIAL RESULTS")
        print("=" * 70)
        print(f"Successful:  {successful_trials}/{self.num_trials}")
        print(f"Failed:      {self.num_trials - successful_trials}/{self.num_trials}")
        print(f"Timed out:   {timed_out}/{self.num_trials}")
        print(f"Success Rate: {successful_trials / self.num_trials * 100:.1f}%")
        print(f"Avg Duration: {avg_duration:.1f}s ({avg_duration / 60:.1f}min)")

        if self.validate:
            validated = sum(
                1
                for t in trial_results
                if "validation" in t and t["validation"]["validation_passed"]
            )
            print(f"\nValidated:   {validated}/{self.num_trials}")
            print(f"Validation Rate: {validated / self.num_trials * 100:.1f}%")

        print(f"\nResults saved to: {self.results_file}")
        print("=" * 70)


def run_llm_judge(
    trial_dir: Path, model: str = "claude-3-5-sonnet-20241022"
) -> dict[str, Any]:
    """
    Use an LLM to judge the quality of a trial's output.

    Parameters
    ----------
    trial_dir : Path
        Directory containing trial output
    model : str
        Claude model to use for judging

    Returns
    -------
    dict
        Evaluation results with scores and feedback
    """
    print(f"\nEvaluating: {trial_dir.name}")

    # Look for deliverables
    html_files = list(trial_dir.glob("*.html"))
    js_files = list(trial_dir.glob("*.js"))
    css_files = list(trial_dir.glob("*.css"))
    md_files = list(trial_dir.glob("*.md"))

    files_found = {
        "html": [str(f.name) for f in html_files],
        "js": [str(f.name) for f in js_files],
        "css": [str(f.name) for f in css_files],
        "md": [str(f.name) for f in md_files],
    }

    # Read key files (limit size to avoid token issues)
    artifacts = {}
    for html_file in html_files[:2]:
        try:
            with open(html_file) as f:
                content = f.read()[:10000]  # Limit to 10KB
                artifacts[html_file.name] = content
        except Exception as e:
            artifacts[html_file.name] = f"Error reading: {e}"

    for js_file in js_files[:3]:
        try:
            with open(js_file) as f:
                content = f.read()[:10000]
                artifacts[js_file.name] = content
        except Exception as e:
            artifacts[js_file.name] = f"Error reading: {e}"

    for md_file in md_files[:2]:
        try:
            with open(md_file) as f:
                content = f.read()[:5000]
                artifacts[md_file.name] = content
        except Exception as e:
            artifacts[md_file.name] = f"Error reading: {e}"

    # Check trial result
    result_file = trial_dir / "result.json"
    trial_completed = False
    if result_file.exists():
        with open(result_file) as f:
            trial_result = json.load(f)
            trial_completed = trial_result.get("success", False)

    # Create evaluation prompt
    eval_prompt = f"""You are evaluating a Snake Game implementation.

TRIAL COMPLETED: {trial_completed}

FILES FOUND:
{json.dumps(files_found, indent=2)}

FILE CONTENTS (truncated):
{json.dumps(artifacts, indent=2)}

Evaluate this implementation on:

1. COMPLETENESS (0-40 points)
   - All required files present
   - Design document exists
   - Game is fully implemented

2. FUNCTIONALITY (0-30 points)
   - Code looks correct (game start, movement, collisions)
   - Proper HTML5 canvas usage
   - Event handlers for controls

3. CODE QUALITY (0-20 points)
   - Well-organized code structure
   - Functions are documented
   - No obvious bugs in code
   - Follows best practices

4. USER EXPERIENCE (0-10 points)
   - Has visual styling
   - Clear game board
   - Proper UI elements

IMPORTANT: Base your evaluation ONLY on the code and files present.
You cannot run the game, so judge based on code quality and completeness.

Return ONLY a valid JSON object (no markdown, no explanation) with this structure:
{{
  "completeness_score": <0-40>,
  "functionality_score": <0-30>,
  "code_quality_score": <0-20>,
  "user_experience_score": <0-10>,
  "total_score": <0-100>,
  "passing": <true if ≥80, false otherwise>,
  "feedback": "<1-2 sentence summary>"
}}"""

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=model,
            max_tokens=1000,
            messages=[{"role": "user", "content": eval_prompt}],
        )

        # Extract text from response
        response_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                response_text += block.text

        # Remove markdown code fences if present
        response_text = response_text.strip()
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])
        response_text = response_text.strip()

        # Parse JSON
        evaluation: dict[str, Any] = json.loads(response_text)
        evaluation["trial_dir"] = str(trial_dir.name)
        evaluation["trial_completed"] = trial_completed

        print(
            f"  Score: {evaluation['total_score']}/100 "
            f"({'PASS' if evaluation['passing'] else 'FAIL'})"
        )

        return evaluation

    except Exception as e:
        print(f"  ✗ Error during evaluation: {e}")
        return {
            "trial_dir": str(trial_dir.name),
            "trial_completed": trial_completed,
            "error": str(e),
            "total_score": 0,
            "passing": False,
            "feedback": f"Evaluation failed: {e}",
        }


def evaluate_all_trials(output_dir: Path, model: str) -> None:
    """Evaluate all trials using LLM judge."""
    results_file = output_dir / "trial_results.json"

    if not results_file.exists():
        print(f"Error: No results file found at {results_file}")
        return

    # Load trial results
    with open(results_file) as f:
        results = json.load(f)

    print("\n" + "=" * 70)
    print("EVALUATING TRIALS WITH LLM JUDGE")
    print("=" * 70)
    print(f"Model: {model}")

    evaluations = []
    for trial in results["trials"]:
        trial_dir = Path(trial["trial_dir"])
        if trial_dir.exists():
            evaluation = run_llm_judge(trial_dir, model)
            evaluations.append(evaluation)
            time.sleep(1)  # Rate limiting
        else:
            print(f"  Warning: {trial_dir} not found")

    # Save evaluations
    eval_file = output_dir / "evaluations.json"
    with open(eval_file, "w") as f:
        json.dump(evaluations, f, indent=2)

    # Calculate statistics
    passing = sum(1 for e in evaluations if e.get("passing", False))
    total_scores = [e.get("total_score", 0) for e in evaluations]
    avg_score = sum(total_scores) / len(total_scores) if total_scores else 0

    print("\n" + "=" * 70)
    print("EVALUATION RESULTS")
    print("=" * 70)
    print(f"Passing (≥80):  {passing}/{len(evaluations)}")
    print(f"Pass Rate:      {passing / len(evaluations) * 100:.1f}%")
    print(f"Avg Score:      {avg_score:.1f}/100")
    print(f"Min Score:      {min(total_scores)}/100")
    print(f"Max Score:      {max(total_scores)}/100")
    print(f"\nEvaluations saved to: {eval_file}")
    print("=" * 70)


def main() -> None:
    """Run the single-agent trial experiment."""
    parser = argparse.ArgumentParser(
        description="Run isolated single-agent trials outside Marcus directory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run 20 trials serially (creates timestamped folder in ~/trials/)
  python experiments/run_single_agent_trials.py \\
    experiments/snake_game_single_agent_prompt.md \\
    --output-dir ~/trials

  # Run 20 trials in PARALLEL (much faster!)
  python experiments/run_single_agent_trials.py \\
    experiments/snake_game_single_agent_prompt.md \\
    --output-dir ~/trials \\
    --parallel

  # Run 5 trials in parallel with custom settings
  python experiments/run_single_agent_trials.py \\
    experiments/snake_game_single_agent_prompt.md \\
    --output-dir ~/trials \\
    --num-trials 5 \\
    --name "snake_v2" \\
    --parallel \\
    --max-workers 5

  # Evaluate existing experiment
  python experiments/run_single_agent_trials.py \\
    experiments/snake_game_single_agent_prompt.md \\
    --output-dir ~/trials/snake_game_single_agent_20260314_153000 \\
    --evaluate-only
        """,
    )
    parser.add_argument(
        "prompt_file",
        type=Path,
        help="Path to prompt markdown file (e.g., snake_game_single_agent_prompt.md)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help=(
            "Base directory for experiments (e.g., ~/trials). "
            "A timestamped subfolder will be created for each run."
        ),
    )
    parser.add_argument(
        "--num-trials",
        type=int,
        default=20,
        help="Number of trials to run (default: 20)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Timeout per trial in minutes (default: 10)",
    )
    parser.add_argument(
        "--name",
        type=str,
        help="Experiment name (default: uses prompt filename)",
    )
    parser.add_argument(
        "--judge-model",
        type=str,
        default="claude-3-haiku-20240307",
        help="Model for LLM judge evaluation (default: claude-3-haiku-20240307)",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run trials in parallel (much faster but more resource intensive)",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=10,
        help="Maximum number of parallel workers (default: 10)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate that games actually work (requires Node.js and Puppeteer)",
    )
    parser.add_argument(
        "--show-browser",
        action="store_true",
        help="Show browser windows during validation (opens 1 window per trial)",
    )
    parser.add_argument(
        "--evaluate-only",
        action="store_true",
        help="Only run evaluation on existing trials (use full path to experiment dir)",
    )

    args = parser.parse_args()

    # Resolve paths
    prompt_file = args.prompt_file.resolve()
    if not prompt_file.exists():
        print(f"Error: Prompt file not found: {prompt_file}")
        sys.exit(1)

    if args.evaluate_only:
        # Evaluate existing trials - use output_dir as-is (full path to experiment)
        experiment_dir = args.output_dir.resolve()
        if not experiment_dir.exists():
            print(f"Error: Experiment directory not found: {experiment_dir}")
            sys.exit(1)
        evaluate_all_trials(experiment_dir, args.judge_model)
    else:
        # Run trials - output_dir is base directory, timestamped folder created
        runner = TrialRunner(
            prompt_file=prompt_file,
            output_dir=args.output_dir,
            num_trials=args.num_trials,
            timeout_minutes=args.timeout,
            judge_model=args.judge_model,
            experiment_name=args.name,
            parallel=args.parallel,
            max_workers=args.max_workers,
            validate=args.validate,
            show_browser=args.show_browser,
        )
        runner.run_all_trials()

        # Ask if they want to evaluate
        print("\n" + "=" * 70)
        print("Would you like to evaluate the trials now? (y/n): ", end="")
        sys.stdout.flush()
        if input().strip().lower() == "y":
            evaluate_all_trials(runner.output_dir, args.judge_model)


if __name__ == "__main__":
    main()
