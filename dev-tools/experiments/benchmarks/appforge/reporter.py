#!/usr/bin/env python3
"""
AppForge Results Reporter.

Generates HTML reports from AppForge benchmark results.
"""

import json
from pathlib import Path

import pandas as pd


def generate_report(results_dir: Path, output_file: Path | None = None) -> Path:
    """
    Generate HTML report from AppForge benchmark results.

    Parameters
    ----------
    results_dir : Path
        Directory containing result JSON files
    output_file : Path, optional
        Output HTML file (default: results_dir/appforge_report.html)

    Returns
    -------
    Path
        Path to generated HTML report
    """
    if output_file is None:
        output_file = results_dir / "appforge_report.html"

    print(f"Generating report from: {results_dir}")

    # Load all JSON result files
    results = []
    for json_file in sorted(results_dir.glob("*.json")):
        if json_file.name == "appforge_report.json":
            continue  # Skip summary files

        with open(json_file) as f:
            result = json.load(f)
            results.append(result)

    if not results:
        print("⚠️  No results found")
        return output_file

    # Create DataFrame
    df = pd.DataFrame(results)

    # Calculate summary statistics
    total_benchmarks = len(df)
    passed_benchmarks = df["passed"].sum()
    pass_rate = (
        (passed_benchmarks / total_benchmarks * 100) if total_benchmarks > 0 else 0
    )
    avg_duration = df["duration_seconds"].mean()

    # Generate HTML
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>AppForge Benchmark Results</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 1200px;
            margin: 40px auto;
            padding: 0 20px;
            background: #f5f5f5;
        }}
        .summary {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .summary h1 {{
            margin-top: 0;
            color: #333;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .stat {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
        }}
        .stat-value {{
            font-size: 32px;
            font-weight: bold;
            color: #2196F3;
        }}
        .stat-label {{
            font-size: 14px;
            color: #666;
            margin-top: 5px;
        }}
        table {{
            width: 100%;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-collapse: collapse;
        }}
        th {{
            background: #2196F3;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 12px;
            border-bottom: 1px solid #eee;
        }}
        tr:last-child td {{
            border-bottom: none;
        }}
        .pass {{
            color: #4CAF50;
            font-weight: bold;
        }}
        .fail {{
            color: #f44336;
            font-weight: bold;
        }}
        .timestamp {{
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="summary">
        <h1>AppForge Benchmark Results</h1>
        <div class="stats">
            <div class="stat">
                <div class="stat-value">{total_benchmarks}</div>
                <div class="stat-label">Total Benchmarks</div>
            </div>
            <div class="stat">
                <div class="stat-value">{passed_benchmarks}</div>
                <div class="stat-label">Passed</div>
            </div>
            <div class="stat">
                <div class="stat-value">{pass_rate:.1f}%</div>
                <div class="stat-label">Pass Rate</div>
            </div>
            <div class="stat">
                <div class="stat-value">{avg_duration:.1f}s</div>
                <div class="stat-label">Avg Duration</div>
            </div>
        </div>
    </div>
"""

    # Add results table
    html += """
    <table>
        <thead>
            <tr>
                <th>Task ID</th>
                <th>Status</th>
                <th>Tests Run</th>
                <th>Tests Passed</th>
                <th>Duration (s)</th>
                <th>Timestamp</th>
            </tr>
        </thead>
        <tbody>
"""

    for _, row in df.iterrows():
        status_class = "pass" if row.get("passed", False) else "fail"
        status_text = "✓ PASSED" if row.get("passed", False) else "✗ FAILED"

        html += f"""
            <tr>
                <td>{row.get('task_id', 'N/A')}</td>
                <td class="{status_class}">{status_text}</td>
                <td>{row.get('tests_run', 0)}</td>
                <td>{row.get('tests_passed', 0)}</td>
                <td>{row.get('duration_seconds', 0):.1f}</td>
                <td class="timestamp">{row.get('timestamp', 'N/A')[:19]}</td>
            </tr>
"""

    html += """
        </tbody>
    </table>
</body>
</html>
"""

    # Write HTML file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        f.write(html)

    print(f"✓ Report generated: {output_file}")
    return output_file


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate HTML report from AppForge results"
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path.home() / "appforge_benchmarks" / "results",
        help="Directory containing result JSON files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output HTML file (default: results-dir/appforge_report.html)",
    )

    args = parser.parse_args()

    report_path = generate_report(args.results_dir, args.output)
    print(f"\nOpen report: file://{report_path.absolute()}")
