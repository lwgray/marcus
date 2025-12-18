#!/usr/bin/env python3
"""
AppForge Evaluator.

Evaluates Marcus-generated Android implementations using AppForge test suite.
Uses the AppForge Python library for Docker management, compilation, and testing.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from AppForge import AppForge


def evaluate_benchmark(
    task_id: int,
    implementation_dir: Path,
    timeout: int = 1800,
    docker_port: int = 6080,
    use_local_emulator: bool = False,
    emulator_id: str | None = None,
    sdk_path: Path | None = None,
    bench_folder: Path | None = None,
) -> dict[str, Any]:
    """
    Evaluate Marcus implementation against AppForge tests.

    Uses AppForge library to:
    1. Start Docker Android emulator OR use local emulator
    2. Compile Marcus-generated Android app (modern toolchain)
    3. Run automated UI tests
    4. Return structured results

    IMPORTANT: Requires modern AppForge fork (github.com/lwgray/AppForge_Bench)
               with Gradle 8.9, AGP 8.7, Java 17, API 34. The modern toolchain
               compiles Marcus code directly without any adaptation layer.

    Parameters
    ----------
    task_id : int
        AppForge task ID (0-100)
    implementation_dir : Path
        Directory containing Marcus-generated Android app
    timeout : int
        Evaluation timeout in seconds (default: 1800 = 30 minutes)
    docker_port : int
        Docker VNC port (default: 6080, ignored if use_local_emulator=True)
    use_local_emulator : bool
        Use local Android emulator instead of Docker (default: False)
    emulator_id : str | None
        Local emulator ID (e.g., "emulator-5554"), required if
        use_local_emulator=True
    sdk_path : Path | None
        Android SDK path, required if use_local_emulator=True
    bench_folder : Path | None
        Modern AppForge bench folder path (e.g., ~/dev/AppForge_Bench_Modern),
        required if use_local_emulator=True

    Returns
    -------
    dict
        {
            "task_id": int,
            "compile": int,           # 1 if compiled, 0 if failed
            "pass_rate": float,       # Test pass rate (0.0-1.0)
            "all_pass": int,          # 1 if all tests passed, 0 otherwise
            "duration_seconds": float,
            "timestamp": str,
            "compile_error": str | None,
            "logs": str,
            "error": str | None
        }
    """
    start_time = time.time()
    timestamp = datetime.now(timezone.utc).isoformat()

    result = {
        "task_id": task_id,
        "compile": 0,
        "pass_rate": 0.0,
        "all_pass": 0,
        "duration_seconds": 0.0,
        "timestamp": timestamp,
        "compile_error": None,
        "logs": "",
        "error": None,
    }

    print("=" * 60)
    print(f"AppForge Benchmark Evaluation - Task {task_id}")
    print("=" * 60)
    print(f"Implementation: {implementation_dir}")
    print(f"Timeout: {timeout}s")
    print()

    evaluator = None
    original_cwd = None

    # Configure Java 17 for Gradle compatibility
    # AppForge template uses Gradle 7.2 which requires Java 17 (not Java 22)
    import os

    java17_home = "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
    if os.path.exists(java17_home):
        os.environ["JAVA_HOME"] = java17_home
        print(f"Setting JAVA_HOME to Java 17: {java17_home}")

    try:
        # Step 1: Initialize AppForge
        if use_local_emulator:
            print("[1/4] Initializing AppForge with local emulator...")
            if not emulator_id or not sdk_path or not bench_folder:
                raise ValueError(
                    "Local emulator mode requires: emulator_id, sdk_path, "
                    "and bench_folder"
                )
            # AppForge loads tasks/tasks.json from cwd, so change to bench_folder
            original_cwd = os.getcwd()
            os.chdir(bench_folder)

            evaluator = AppForge(
                runs=f"marcus_task_{task_id}",
                base_folder=Path.home() / "appforge_benchmarks" / "runs",
                use_docker=False,
                emulator_id=emulator_id,
                sdk_path=str(sdk_path),
                bench_folder=Path(bench_folder),
                record_video=False,
            )
            print(f"  ✓ Using local emulator: {emulator_id}")
            print(f"  ✓ SDK path: {sdk_path}")
        else:
            print("[1/4] Initializing AppForge with Docker...")
            evaluator = AppForge(
                runs=f"marcus_task_{task_id}",
                base_folder=Path.home() / "appforge_benchmarks" / "runs",
                use_docker=True,
                docker_name="zenithfocuslight/appforge:latest",
                docker_port=docker_port,
                record_video=False,
            )
            print("  ✓ Docker container started")
            print("  ✓ Android emulator ready")
        print()

        # Step 2: Modern AppForge - direct compilation
        # Modern fork (Gradle 8.9, AGP 8.7, Java 17, API 34) compiles Marcus code
        # directly without any adaptation layer.
        # DEPRECATION NOTE: Old adapter code removed as modern toolchain is now
        # required. See MODERNIZATION.md in AppForge_Bench_Modern fork.
        print("[2/4] Using modern AppForge toolchain...")
        print("  ✓ Modern fork compiles Marcus code directly (no adapter)")
        compile_dir = implementation_dir
        print()

        # Step 3: Compile with AppForge
        print("[3/4] Compiling with AppForge...")
        compile_error = evaluator.compile_folder(compile_dir, task_id)

        if compile_error:
            print(f"  ✗ Compilation failed")
            result["compile"] = 0
            result["compile_error"] = compile_error
            result["error"] = f"Compilation failed: {compile_error}"
            return result

        print("  ✓ Compilation successful")
        result["compile"] = 1
        print()

        # Step 4: Run AppForge tests
        print("[4/4] Running AppForge automated UI tests...")
        test_result = evaluator.test(task_id)

        # Step 5: Collect results
        result.update(
            {
                "compile": test_result.get("compile", 0),
                "pass_rate": test_result.get("pass_rate", 0.0),
                "all_pass": test_result.get("all_pass", 0),
            }
        )

        # Read logs if available
        test_log_path = (
            Path.home()
            / "appforge_benchmarks"
            / "runs"
            / f"marcus_task_{task_id}"
            / str(task_id)
            / "test.log"
        )
        if test_log_path.exists():
            result["logs"] = test_log_path.read_text()

        print()
        print("=" * 60)
        print("Evaluation Results")
        print("=" * 60)
        print(f"Compiled: {'✓' if result['compile'] else '✗'}")
        print(f"Pass Rate: {result['pass_rate'] * 100:.1f}%")
        print(f"All Tests Passed: {'✓' if result['all_pass'] else '✗'}")

    except Exception as e:
        result["error"] = str(e)
        print(f"✗ Evaluation failed: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Cleanup
        if evaluator:
            print()
            if use_local_emulator:
                print("[5/5] Cleaning up...")
            else:
                print("[5/5] Cleaning up Docker container...")
            try:
                evaluator.clean_up()
                if use_local_emulator:
                    print("  ✓ Cleanup complete")
                else:
                    print("  ✓ Docker container stopped")
            except Exception as e:
                print(f"  ⚠️  Cleanup warning: {e}")

        # Restore original directory if changed
        if original_cwd:
            import os

            os.chdir(original_cwd)

        # Calculate duration
        result["duration_seconds"] = time.time() - start_time
        print(f"\nTotal duration: {result['duration_seconds']:.1f}s")

    return result


def save_evaluation_results(result: dict, output_file: Path) -> None:
    """
    Save evaluation results to JSON file.

    Parameters
    ----------
    result : dict
        Evaluation results
    output_file : Path
        Output JSON file path
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n✓ Results saved to: {output_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Evaluate Marcus Android implementation with AppForge tests"
    )
    parser.add_argument(
        "--task-id", type=int, required=True, help="AppForge task ID (0-100)"
    )
    parser.add_argument(
        "--impl-dir", type=Path, required=True, help="Implementation directory"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSON file (default: ~/appforge_benchmarks/results/task_ID.json)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=1800,
        help="Evaluation timeout in seconds (default: 1800)",
    )
    parser.add_argument(
        "--docker-port", type=int, default=6080, help="Docker VNC port (default: 6080)"
    )
    parser.add_argument(
        "--use-local-emulator",
        action="store_true",
        help="Use local Android emulator instead of Docker",
    )
    parser.add_argument(
        "--emulator-id",
        type=str,
        help="Local emulator ID (e.g., emulator-5554), required for local mode",
    )
    parser.add_argument(
        "--sdk-path", type=Path, help="Android SDK path, required for local mode"
    )
    parser.add_argument(
        "--bench-folder",
        type=Path,
        help="AppForge bench folder path, required for local mode",
    )

    args = parser.parse_args()

    # Run evaluation
    result = evaluate_benchmark(
        task_id=args.task_id,
        implementation_dir=args.impl_dir,
        timeout=args.timeout,
        docker_port=args.docker_port,
        use_local_emulator=args.use_local_emulator,
        emulator_id=args.emulator_id,
        sdk_path=args.sdk_path,
        bench_folder=args.bench_folder,
    )

    # Save results
    if args.output:
        output_file = args.output
    else:
        output_file = (
            Path.home()
            / "appforge_benchmarks"
            / "results"
            / f"task_{args.task_id}.json"
        )

    save_evaluation_results(result, output_file)

    # Exit with appropriate code
    exit(0 if result.get("all_pass", 0) == 1 else 1)
