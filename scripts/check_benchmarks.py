#!/usr/bin/env python3
"""
Benchmark comparison script
Feature 026 (FR-006): Compare current performance against baselines

This script loads baseline and current benchmark data, compares them,
and reports on performance regressions or improvements.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Tuple


def load_json(filepath: Path) -> Dict[str, Any]:
    """Load a JSON file."""
    with open(filepath) as f:
        return json.load(f)


def compare_value(current: float, baseline: float, tolerance: float) -> Tuple[str, float]:
    """
    Compare a current value against a baseline.

    Args:
        current: Current measured value
        baseline: Baseline value to compare against
        tolerance: Acceptable variance as a decimal (e.g., 0.05 for 5%)

    Returns:
        Tuple of (status, difference_percent)
        status is one of: "pass", "regression", "improvement"
    """
    if baseline == 0:
        return ("unknown", 0.0)

    diff_percent = ((current - baseline) / baseline) * 100

    if abs(diff_percent) <= (tolerance * 100):
        return ("pass", diff_percent)
    elif diff_percent > 0:
        return ("regression", diff_percent)
    else:
        return ("improvement", diff_percent)


def print_comparison_table(
    metric_name: str,
    current: float,
    baseline: float,
    tolerance: float,
    lower_is_better: bool = True
):
    """Print a formatted comparison of a single metric."""
    status, diff = compare_value(current, baseline, tolerance)

    # Adjust status based on whether lower is better
    if not lower_is_better and status in ("regression", "improvement"):
        status = "improvement" if status == "regression" else "regression"

    status_symbol = {
        "pass": "✓",
        "regression": "✗",
        "improvement": "↑",
        "unknown": "?"
    }[status]

    status_color = {
        "pass": "\033[32m",  # Green
        "regression": "\033[31m",  # Red
        "improvement": "\033[34m",  # Blue
        "unknown": "\033[33m"  # Yellow
    }[status]

    reset = "\033[0m"

    print(
        f"  {status_symbol} {status_color}{metric_name:30s}{reset} "
        f"Current: {current:8.3f}  Baseline: {baseline:8.3f}  "
        f"Diff: {diff:+6.2f}%"
    )

    return status


def main():
    """Main benchmark comparison routine."""
    # Paths
    repo_root = Path(__file__).parent.parent
    baseline_file = repo_root / "tests/regression/baselines/performance_latency_v1.0.json"
    current_file = repo_root / "benchmarks/latency_v1.1.json"

    print("=" * 80)
    print("Soundlab + D-ASE Performance Benchmark Comparison")
    print("=" * 80)
    print()

    # Check files exist
    if not baseline_file.exists():
        print(f"✗ Baseline file not found: {baseline_file}")
        return 1

    if not current_file.exists():
        print(f"✗ Current benchmark file not found: {current_file}")
        return 1

    # Load data
    baseline = load_json(baseline_file)
    current = load_json(current_file)

    print(f"Baseline version: {baseline.get('version', 'unknown')}")
    print(f"Current version:  {current.get('version', 'unknown')}")
    print()

    # Get tolerance from current benchmark
    tolerance = current.get("regression_tolerance", {}).get("latency_variance_percent", 5) / 100

    print(f"Regression tolerance: ±{tolerance * 100:.0f}%")
    print()

    # Compare metrics
    print("Latency Metrics (lower is better):")
    print("-" * 80)

    results = []

    metrics_to_compare = [
        ("Φ-matrix latency", "phi_matrix_latency_ms", True),
        ("D-ASE latency", "dase_latency_ms", True),
        ("I²S latency", "i2s_latency_ms", True),
        ("Total pipeline latency", "total_pipeline_latency_ms", True),
    ]

    for name, key, lower_is_better in metrics_to_compare:
        baseline_val = baseline.get(key, 0)

        # For current, try target_metrics first, then v1_0_baseline
        current_val = current.get("target_metrics", {}).get(key)
        if current_val is None:
            current_val = current.get("v1_0_baseline", {}).get(key, 0)

        if current_val and baseline_val:
            status = print_comparison_table(name, current_val, baseline_val, tolerance, lower_is_better)
            results.append(status)

    print()
    print("Throughput Metrics (higher is better):")
    print("-" * 80)

    # WebSocket rate (higher is better)
    baseline_rate = baseline.get("websocket_update_rate_hz", 0)
    current_rate = current.get("target_metrics", {}).get("websocket_update_rate_hz")
    if current_rate is None:
        current_rate = current.get("v1_0_baseline", {}).get("websocket_update_rate_hz", 0)

    if current_rate and baseline_rate:
        status = print_comparison_table("WebSocket update rate", current_rate, baseline_rate, tolerance, False)
        results.append(status)

    print()
    print("=" * 80)

    # Summary
    regressions = results.count("regression")
    improvements = results.count("improvement")
    passes = results.count("pass")

    print(f"Summary: {passes} pass, {improvements} improvements, {regressions} regressions")

    if regressions > 0:
        print("\n\033[31m✗ REGRESSION DETECTED\033[0m")
        print(f"{regressions} metric(s) regressed beyond tolerance.")
        print("Review recent changes for performance impacts.")
        return 1
    elif improvements > 0:
        print(f"\n\033[34m↑ PERFORMANCE IMPROVEMENT\033[0m")
        print(f"{improvements} metric(s) showed improvement!")
        return 0
    else:
        print("\n\033[32m✓ ALL BENCHMARKS PASS\033[0m")
        print("Performance is within tolerance of baseline.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
