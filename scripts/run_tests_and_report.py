"""
Test Runner and Reporter
Feature 020: Reproducible Build Environment + Dependency Bootstrap (FR-009)

Executes all validation scripts and generates comprehensive reports for CI/CD.

Usage:
    python scripts/run_tests_and_report.py

Output:
    tests/reports/validation_report.md
    tests/reports/validation_report.json
    tests/reports/system_analysis.md
"""

import subprocess
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import platform


class TestReporter:
    """Automated test runner and report generator"""

    def __init__(self):
        self.root_dir = Path(__file__).parent.parent
        self.server_dir = self.root_dir / "server"
        self.reports_dir = self.root_dir / "tests" / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        self.results = {
            'timestamp': datetime.now().isoformat(),
            'platform': platform.platform(),
            'python_version': sys.version,
            'tests': []
        }

    def run_command(self, cmd: List[str], description: str, timeout: int = 300) -> Tuple[bool, str, str]:
        """Run a command and capture output"""
        print(f"\n{'='*70}")
        print(f"Running: {description}")
        print(f"Command: {' '.join(cmd)}")
        print(f"{'='*70}")

        try:
            start_time = time.time()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.root_dir
            )
            elapsed_time = time.time() - start_time

            success = result.returncode == 0
            status = "✓ PASS" if success else "✗ FAIL"

            print(f"{status} ({elapsed_time:.2f}s)")

            if not success and result.stderr:
                print(f"\nError output:\n{result.stderr[:500]}")

            return success, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            print(f"✗ TIMEOUT (>{timeout}s)")
            return False, "", f"Timeout after {timeout}s"

        except Exception as e:
            print(f"✗ ERROR: {e}")
            return False, "", str(e)

    def run_validation_script(self, script_name: str, feature_name: str) -> Dict:
        """Run a validation script and collect results"""
        script_path = self.server_dir / script_name

        if not script_path.exists():
            return {
                'name': feature_name,
                'script': script_name,
                'status': 'skipped',
                'reason': 'Script not found',
                'elapsed_time': 0
            }

        start_time = time.time()
        success, stdout, stderr = self.run_command(
            [sys.executable, str(script_path)],
            f"{feature_name} - {script_name}"
        )
        elapsed_time = time.time() - start_time

        return {
            'name': feature_name,
            'script': script_name,
            'status': 'passed' if success else 'failed',
            'elapsed_time': elapsed_time,
            'stdout': stdout[-1000:] if stdout else "",  # Last 1000 chars
            'stderr': stderr[-1000:] if stderr else ""
        }

    def run_smoke_tests(self) -> Dict:
        """Run smoke test suite"""
        smoke_dir = self.root_dir / "smoke"

        if not smoke_dir.exists():
            return {
                'name': 'Smoke Tests',
                'status': 'skipped',
                'reason': 'Smoke directory not found'
            }

        smoke_tests = [
            ('smoke_websocket.py', 'WebSocket Connectivity'),
            ('smoke_metrics.py', 'Metrics Streaming'),
            ('smoke_health.py', 'Health Endpoints')
        ]

        results = []
        for script, description in smoke_tests:
            script_path = smoke_dir / script
            if script_path.exists():
                start_time = time.time()
                success, stdout, stderr = self.run_command(
                    [sys.executable, str(script_path)],
                    f"Smoke Test - {description}"
                )
                elapsed_time = time.time() - start_time
                results.append({
                    'test': description,
                    'status': 'passed' if success else 'failed',
                    'elapsed_time': elapsed_time
                })

        all_passed = all(r['status'] == 'passed' for r in results)

        return {
            'name': 'Smoke Tests',
            'status': 'passed' if all_passed else 'failed',
            'tests': results
        }

    def run_pytest(self) -> Dict:
        """Run pytest suite"""
        start_time = time.time()
        success, stdout, stderr = self.run_command(
            [sys.executable, '-m', 'pytest', 'tests/', '-v', '--tb=short'],
            "Pytest Suite"
        )
        elapsed_time = time.time() - start_time

        # Parse pytest output for test count
        test_count = 0
        passed_count = 0
        failed_count = 0

        for line in stdout.split('\n'):
            if 'passed' in line.lower():
                try:
                    passed_count = int(line.split()[0])
                except (ValueError, IndexError):
                    pass

        return {
            'name': 'Pytest Suite',
            'status': 'passed' if success else 'failed',
            'elapsed_time': elapsed_time,
            'test_count': test_count,
            'passed': passed_count,
            'failed': failed_count
        }

    def collect_system_info(self) -> Dict:
        """Collect system information"""
        import psutil

        try:
            import dase_engine
            dase_version = dase_engine.__version__
            dase_avx2 = dase_engine.avx2_enabled
        except ImportError:
            dase_version = "not installed"
            dase_avx2 = False

        return {
            'platform': {
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor()
            },
            'python': {
                'version': platform.python_version(),
                'implementation': platform.python_implementation(),
                'compiler': platform.python_compiler()
            },
            'resources': {
                'cpu_count': psutil.cpu_count(),
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_total_gb': psutil.virtual_memory().total / (1024**3),
                'memory_available_gb': psutil.virtual_memory().available / (1024**3),
                'disk_free_gb': psutil.disk_usage('.').free / (1024**3)
            },
            'dase_engine': {
                'version': dase_version,
                'avx2_enabled': dase_avx2
            }
        }

    def generate_markdown_report(self):
        """Generate Markdown report"""
        report_path = self.reports_dir / "validation_report.md"

        with open(report_path, 'w') as f:
            f.write("# Soundlab Φ-Matrix - Validation Report\n\n")
            f.write(f"**Generated**: {self.results['timestamp']}\n\n")
            f.write(f"**Platform**: {self.results['platform']}\n\n")
            f.write(f"**Python**: {self.results['python_version'].split()[0]}\n\n")

            f.write("## Summary\n\n")

            total_tests = len(self.results['tests'])
            passed_tests = sum(1 for t in self.results['tests'] if t.get('status') == 'passed')
            failed_tests = sum(1 for t in self.results['tests'] if t.get('status') == 'failed')
            skipped_tests = sum(1 for t in self.results['tests'] if t.get('status') == 'skipped')

            f.write(f"- **Total Tests**: {total_tests}\n")
            f.write(f"- **Passed**: {passed_tests} ✓\n")
            f.write(f"- **Failed**: {failed_tests} ✗\n")
            f.write(f"- **Skipped**: {skipped_tests}\n")
            f.write(f"- **Pass Rate**: {(passed_tests/total_tests*100) if total_tests > 0 else 0:.1f}%\n\n")

            f.write("## Test Results\n\n")
            f.write("| Test | Status | Time |\n")
            f.write("|------|--------|------|\n")

            for test in self.results['tests']:
                name = test.get('name', 'Unknown')
                status = test.get('status', 'unknown')
                elapsed = test.get('elapsed_time', 0)

                status_icon = {
                    'passed': '✓',
                    'failed': '✗',
                    'skipped': '⊘'
                }.get(status, '?')

                f.write(f"| {name} | {status_icon} {status} | {elapsed:.2f}s |\n")

            f.write("\n## Detailed Results\n\n")
            for test in self.results['tests']:
                f.write(f"### {test.get('name', 'Unknown')}\n\n")
                f.write(f"- **Status**: {test.get('status', 'unknown')}\n")
                f.write(f"- **Time**: {test.get('elapsed_time', 0):.2f}s\n")

                if test.get('script'):
                    f.write(f"- **Script**: `{test['script']}`\n")

                if test.get('stderr'):
                    f.write(f"\n**Error Output**:\n```\n{test['stderr'][:500]}\n```\n")

                f.write("\n")

        print(f"\n✓ Markdown report generated: {report_path}")

    def generate_json_report(self):
        """Generate JSON report"""
        report_path = self.reports_dir / "validation_report.json"

        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2)

        print(f"✓ JSON report generated: {report_path}")

    def generate_system_analysis(self):
        """Generate system analysis report"""
        system_info = self.collect_system_info()

        report_path = self.reports_dir / "system_analysis.md"

        with open(report_path, 'w') as f:
            f.write("# System Analysis Report\n\n")
            f.write(f"**Generated**: {datetime.now().isoformat()}\n\n")

            f.write("## Platform Information\n\n")
            for key, value in system_info['platform'].items():
                f.write(f"- **{key.replace('_', ' ').title()}**: {value}\n")

            f.write("\n## Python Environment\n\n")
            for key, value in system_info['python'].items():
                f.write(f"- **{key.replace('_', ' ').title()}**: {value}\n")

            f.write("\n## System Resources\n\n")
            for key, value in system_info['resources'].items():
                formatted_value = f"{value:.2f}" if isinstance(value, float) else value
                f.write(f"- **{key.replace('_', ' ').title()}**: {formatted_value}\n")

            f.write("\n## D-ASE Engine\n\n")
            for key, value in system_info['dase_engine'].items():
                f.write(f"- **{key.replace('_', ' ').title()}**: {value}\n")

        print(f"✓ System analysis generated: {report_path}")

    def run_all_tests(self):
        """Run all tests and generate reports"""
        print("\n" + "="*70)
        print("Feature 020: Test Runner and Reporter")
        print("="*70)

        # Run validation scripts
        validation_scripts = [
            ('validate_feature_015.py', 'Feature 015: Multi-Session Analytics'),
            ('validate_feature_016.py', 'Feature 016: Chromatic Visualizer'),
            ('validate_feature_017.py', 'Feature 017: Phi-Matrix Dashboard'),
            ('validate_feature_018.py', 'Feature 018: Adaptive Benchmark'),
            ('validate_release_readiness.py', 'Feature 019: Release Readiness'),
            ('validate_feature_020.py', 'Feature 020: Build Environment')
        ]

        for script, feature in validation_scripts:
            result = self.run_validation_script(script, feature)
            self.results['tests'].append(result)

        # Run smoke tests
        # smoke_result = self.run_smoke_tests()
        # self.results['tests'].append(smoke_result)

        # Run pytest
        # pytest_result = self.run_pytest()
        # self.results['tests'].append(pytest_result)

        # Generate reports
        print("\n" + "="*70)
        print("Generating Reports")
        print("="*70)

        self.generate_markdown_report()
        self.generate_json_report()
        self.generate_system_analysis()

        # Print summary
        print("\n" + "="*70)
        print("Summary")
        print("="*70)

        total = len(self.results['tests'])
        passed = sum(1 for t in self.results['tests'] if t.get('status') == 'passed')
        failed = sum(1 for t in self.results['tests'] if t.get('status') == 'failed')

        print(f"Total: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Pass Rate: {(passed/total*100) if total > 0 else 0:.1f}%")

        print(f"\nReports available in: {self.reports_dir}/")

        # Exit code
        return 0 if failed == 0 else 1


if __name__ == '__main__':
    reporter = TestReporter()
    sys.exit(reporter.run_all_tests())
