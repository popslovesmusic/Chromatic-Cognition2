"""
Performance Benchmark Harness for Φ-Matrix
Feature 021: Automated Validation & Regression Testing (FR-005)

Measures:
- FPS (frames per second)
- WebSocket RTT (round-trip time)
- CPU usage
- Memory usage
- Memory drift over time

Enforces performance budgets (FR-002):
- FPS ≥ 30
- RTT p95 ≤ 80ms
- CPU ≤ 60%
- Memory drift < 5% over 5 minutes

Usage:
    python tests/perf/bench_phi_matrix.py
    python tests/perf/bench_phi_matrix.py --duration 120
    SOUNDLAB_SIMULATE=1 python tests/perf/bench_phi_matrix.py
"""

import asyncio
import websockets
import json
import time
import server.psutil
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import numpy as np


class PerformanceBenchmark:
    """
    Performance benchmark harness for Φ-Matrix system

    Collects performance metrics and enforces budget thresholds.
    """

    def __init__(self, duration_seconds: int = 120, base_url: str = "http://localhost:8000"):
        self.duration = duration_seconds
        self.base_url = base_url
        self.ws_url = base_url.replace('http://', 'ws://') + '/ws/metrics'

        # Performance budgets (SC-003)
        self.budgets = {
            'fps_min': 30.0,
            'rtt_p95_max_ms': 80.0,
            'cpu_max_percent': 60.0,
            'memory_drift_max_percent': 5.0
        }

        # Metrics storage
        self.frame_times: List[float] = []
        self.rtt_samples: List[float] = []
        self.cpu_samples: List[float] = []
        self.memory_samples: List[float] = []

        # State
        self.start_time = None
        self.process = psutil.Process()

    async def measure_websocket_latency(self):
        """Measure WebSocket round-trip latency"""
        try:
            async with websockets.connect(self.ws_url, timeout=10) as websocket:
                for _ in range(10):  # 10 ping samples
                    start = time.perf_counter()
                    ping_msg = {"type": "ping", "timestamp": start * 1000}
                    await websocket.send(json.dumps(ping_msg))

                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        end = time.perf_counter()
                        rtt_ms = (end - start) * 1000
                        self.rtt_samples.append(rtt_ms)
                    except asyncio.TimeoutError:
                        print("  WebSocket timeout")

                    await asyncio.sleep(0.1)

        except Exception as e:
            print(f"  WebSocket error: {e}")

    async def collect_metrics_stream(self):
        """Collect metrics from WebSocket stream"""
        try:
            async with websockets.connect(self.ws_url, timeout=10) as websocket:
                last_frame_time = time.perf_counter()
                end_time = time.time() + self.duration

                while time.time() < end_time:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        current_time = time.perf_counter()

                        # Calculate frame time
                        frame_time = current_time - last_frame_time
                        self.frame_times.append(frame_time)
                        last_frame_time = current_time

                        # Sample system resources every ~1 second
                        if len(self.frame_times) % 25 == 0:  # Assuming ~25 Hz
                            self.cpu_samples.append(self.process.cpu_percent())
                            memory_info = self.process.memory_info()
                            self.memory_samples.append(memory_info.rss / (1024 ** 2))  # MB

                    except asyncio.TimeoutError:
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        break

        except Exception as e:
            print(f"  Metrics stream error: {e}")

    def calculate_fps(self) -> float:
        """Calculate average FPS from frame times"""
        if not self.frame_times:
            return 0.0
        avg_frame_time = np.mean(self.frame_times)
        return 1.0 / avg_frame_time if avg_frame_time > 0 else 0.0

    def calculate_statistics(self) -> Dict:
        """Calculate performance statistics"""
        stats = {
            'duration_seconds': self.duration,
            'timestamp': datetime.now().isoformat(),
            'frames_collected': len(self.frame_times),
        }

        # FPS
        if self.frame_times:
            fps = self.calculate_fps()
            stats['fps'] = {
                'average': fps,
                'min': 1.0 / max(self.frame_times) if self.frame_times else 0.0,
                'max': 1.0 / min(self.frame_times) if self.frame_times else 0.0,
                'p50': 1.0 / np.percentile(self.frame_times, 50) if self.frame_times else 0.0,
            }
        else:
            stats['fps'] = {'average': 0.0}

        # RTT
        if self.rtt_samples:
            stats['rtt_ms'] = {
                'average': np.mean(self.rtt_samples),
                'min': np.min(self.rtt_samples),
                'max': np.max(self.rtt_samples),
                'p50': np.percentile(self.rtt_samples, 50),
                'p95': np.percentile(self.rtt_samples, 95),
                'p99': np.percentile(self.rtt_samples, 99),
            }
        else:
            stats['rtt_ms'] = {'p95': 0.0}

        # CPU
        if self.cpu_samples:
            stats['cpu_percent'] = {
                'average': np.mean(self.cpu_samples),
                'min': np.min(self.cpu_samples),
                'max': np.max(self.cpu_samples),
                'p95': np.percentile(self.cpu_samples, 95),
            }
        else:
            stats['cpu_percent'] = {'average': 0.0}

        # Memory
        if self.memory_samples:
            initial_memory = self.memory_samples[0]
            final_memory = self.memory_samples[-1]
            memory_drift_percent = ((final_memory - initial_memory) / initial_memory) * 100

            stats['memory_mb'] = {
                'initial': initial_memory,
                'final': final_memory,
                'average': np.mean(self.memory_samples),
                'max': np.max(self.memory_samples),
                'drift_percent': memory_drift_percent,
            }
        else:
            stats['memory_mb'] = {'drift_percent': 0.0}

        return stats

    def check_budgets(self, stats: Dict) -> Dict[str, bool]:
        """Check if performance meets budget thresholds"""
        results = {}

        # FPS budget
        fps = stats['fps'].get('average', 0.0)
        results['fps_pass'] = fps >= self.budgets['fps_min']

        # RTT budget
        rtt_p95 = stats['rtt_ms'].get('p95', 0.0)
        results['rtt_pass'] = rtt_p95 <= self.budgets['rtt_p95_max_ms']

        # CPU budget
        cpu_avg = stats['cpu_percent'].get('average', 0.0)
        results['cpu_pass'] = cpu_avg <= self.budgets['cpu_max_percent']

        # Memory drift budget
        memory_drift = stats['memory_mb'].get('drift_percent', 0.0)
        results['memory_drift_pass'] = abs(memory_drift) <= self.budgets['memory_drift_max_percent']

        return results

    async def run(self) -> Dict:
        """Run the benchmark"""
        print(f"\n{'='*70}")
        print("Φ-Matrix Performance Benchmark")
        print(f"{'='*70}")
        print(f"Duration: {self.duration}s")
        print(f"Base URL: {self.base_url}")
        print(f"WS URL: {self.ws_url}")
        print()

        self.start_time = time.time()

        # Phase 1: WebSocket latency measurement
        print("[1/2] Measuring WebSocket latency...")
        await self.measure_websocket_latency()
        print(f"  Collected {len(self.rtt_samples)} RTT samples")

        # Phase 2: Continuous metrics collection
        print(f"[2/2] Collecting metrics for {self.duration}s...")
        await self.collect_metrics_stream()
        print(f"  Collected {len(self.frame_times)} frames")

        # Calculate statistics
        stats = self.calculate_statistics()
        budget_results = self.check_budgets(stats)

        # Add budget results and thresholds to stats
        stats['budgets'] = self.budgets
        stats['budget_results'] = budget_results
        stats['all_budgets_pass'] = all(budget_results.values())

        return stats

    def print_summary(self, stats: Dict):
        """Print benchmark summary"""
        print()
        print(f"{'='*70}")
        print("Performance Summary")
        print(f"{'='*70}")

        # FPS
        fps_data = stats['fps']
        fps_pass = stats['budget_results']['fps_pass']
        status = "PASS" if fps_pass else "FAIL"
        print(f"\nFPS:")
        print(f"  Average: {fps_data.get('average', 0):.2f} Hz [{status}] (target: >={self.budgets['fps_min']} Hz)")
        if 'min' in fps_data:
            print(f"  Range: {fps_data['min']:.2f} - {fps_data['max']:.2f} Hz")

        # RTT
        rtt_data = stats['rtt_ms']
        rtt_pass = stats['budget_results']['rtt_pass']
        status = "PASS" if rtt_pass else "FAIL"
        print(f"\nWebSocket RTT:")
        print(f"  P95: {rtt_data.get('p95', 0):.2f} ms [{status}] (target: <={self.budgets['rtt_p95_max_ms']} ms)")
        if 'average' in rtt_data:
            print(f"  Average: {rtt_data['average']:.2f} ms")
            print(f"  Range: {rtt_data['min']:.2f} - {rtt_data['max']:.2f} ms")

        # CPU
        cpu_data = stats['cpu_percent']
        cpu_pass = stats['budget_results']['cpu_pass']
        status = "PASS" if cpu_pass else "FAIL"
        print(f"\nCPU Usage:")
        print(f"  Average: {cpu_data.get('average', 0):.1f}% [{status}] (target: <={self.budgets['cpu_max_percent']}%)")
        if 'max' in cpu_data:
            print(f"  Range: {cpu_data['min']:.1f}% - {cpu_data['max']:.1f}%")

        # Memory
        memory_data = stats['memory_mb']
        memory_pass = stats['budget_results']['memory_drift_pass']
        status = "PASS" if memory_pass else "FAIL"
        print(f"\nMemory:")
        if 'initial' in memory_data:
            print(f"  Initial: {memory_data['initial']:.1f} MB")
            print(f"  Final: {memory_data['final']:.1f} MB")
            print(f"  Drift: {memory_data['drift_percent']:+.2f}% [{status}] (target: <{self.budgets['memory_drift_max_percent']}%)")

        # Overall
        print()
        print(f"{'='*70}")
        all_pass = stats['all_budgets_pass']
        if all_pass:
            print("Result: ALL BUDGETS MET")
        else:
            print("Result: BUDGET VIOLATIONS DETECTED")
            print("\nFailed budgets:")
            for key, passed in stats['budget_results'].items():
                if not passed:
                    print(f"  - {key}")

        print(f"{'='*70}")

    def save_report(self, stats: Dict, output_path: Path):
        """Save performance report to JSON"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(stats, f, indent=2)
        print(f"\nReport saved: {output_path}")


async def main():
    parser = argparse.ArgumentParser(description='Φ-Matrix Performance Benchmark')
    parser.add_argument('--duration', type=int, default=120, help='Benchmark duration in seconds')
    parser.add_argument('--url', type=str, default='http://localhost:8000', help='Base URL')
    parser.add_argument('--output', type=str, default='tests/reports/perf_summary.json', help='Output file')
    args = parser.parse_args()

    benchmark = PerformanceBenchmark(duration_seconds=args.duration, base_url=args.url)

    try:
        stats = await benchmark.run()
        benchmark.print_summary(stats)
        benchmark.save_report(stats, Path(args.output))

        # Exit with error code if budgets not met
        if not stats['all_budgets_pass']:
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
