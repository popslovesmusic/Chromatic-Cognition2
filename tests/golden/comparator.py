"""
Golden Data Comparator
Feature 021: Automated Validation & Regression Testing (FR-006)

Compares current metrics against golden baseline data with tolerances.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np


class GoldenComparator:
    """Compare metrics against golden baseline with tolerances"""

    def __init__(self, tolerances_path: Path):
        with open(tolerances_path) as f:
            self.tolerances_config = json.load(f)
        self.metrics_tolerances = self.tolerances_config['metrics']
        self.default_tolerance = self.tolerances_config['global']['relative_tolerance']

    def compare_value(self, metric_name: str, actual: float, expected: float) -> Tuple[bool, float, float]:
        """
        Compare single metric value against golden baseline

        Returns: (passes, difference, tolerance)
        """
        # Get tolerance for this metric
        if metric_name in self.metrics_tolerances:
            tolerance = self.metrics_tolerances[metric_name]['tolerance']
        else:
            # Use relative tolerance
            tolerance = abs(expected * self.default_tolerance)

        difference = abs(actual - expected)
        passes = difference <= tolerance

        return passes, difference, tolerance

    def compare_dict(self, actual: Dict, expected: Dict, prefix: str = "") -> Dict:
        """Recursively compare dictionaries"""
        results = {
            'passed': True,
            'differences': [],
            'summary': {}
        }

        for key in expected:
            full_key = f"{prefix}.{key}" if prefix else key

            if key not in actual:
                results['passed'] = False
                results['differences'].append({
                    'metric': full_key,
                    'issue': 'missing',
                    'expected': expected[key]
                })
                continue

            actual_val = actual[key]
            expected_val = expected[key]

            if isinstance(expected_val, dict):
                # Recursive comparison
                sub_results = self.compare_dict(actual_val, expected_val, full_key)
                results['passed'] = results['passed'] and sub_results['passed']
                results['differences'].extend(sub_results['differences'])
            elif isinstance(expected_val, (int, float)):
                # Numeric comparison with tolerance
                passes, diff, tolerance = self.compare_value(full_key, float(actual_val), float(expected_val))

                if not passes:
                    results['passed'] = False
                    results['differences'].append({
                        'metric': full_key,
                        'actual': actual_val,
                        'expected': expected_val,
                        'difference': diff,
                        'tolerance': tolerance
                    })

        return results

    def compare_files(self, actual_path: Path, golden_path: Path) -> Dict:
        """Compare actual results file against golden baseline"""
        with open(actual_path) as f:
            actual_data = json.load(f)

        with open(golden_path) as f:
            golden_data = json.load(f)

        results = self.compare_dict(actual_data, golden_data)
        results['actual_file'] = str(actual_path)
        results['golden_file'] = str(golden_path)

        return results

    def print_report(self, results: Dict):
        """Print comparison report"""
        print("\n" + "="*70)
        print("Golden Data Comparison Report")
        print("="*70)

        if results['passed']:
            print("\n✓ ALL METRICS WITHIN TOLERANCE")
        else:
            print("\n✗ REGRESSION DETECTED")
            print(f"\nFailed metrics: {len(results['differences'])}")

            for diff in results['differences']:
                print(f"\n  Metric: {diff['metric']}")
                if 'issue' in diff:
                    print(f"  Issue: {diff['issue']}")
                    print(f"  Expected: {diff['expected']}")
                else:
                    print(f"  Actual: {diff['actual']}")
                    print(f"  Expected: {diff['expected']}")
                    print(f"  Difference: {diff['difference']:.4f}")
                    print(f"  Tolerance: {diff['tolerance']:.4f}")

        print("\n" + "="*70)

    def save_report(self, results: Dict, output_path: Path):
        """Save comparison report to JSON"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nReport saved: {output_path}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Golden Data Comparator')
    parser.add_argument('actual', type=Path, help='Actual results file')
    parser.add_argument('golden', type=Path, help='Golden baseline file')
    parser.add_argument('--tolerances', type=Path, default=Path('tests/golden/tolerances.json'))
    parser.add_argument('--output', type=Path, default=Path('tests/reports/golden_diff.json'))
    args = parser.parse_args()

    comparator = GoldenComparator(args.tolerances)
    results = comparator.compare_files(args.actual, args.golden)
    comparator.print_report(results)
    comparator.save_report(results, args.output)

    sys.exit(0 if results['passed'] else 1)
