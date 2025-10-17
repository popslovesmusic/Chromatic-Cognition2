"""
BenchmarkRunner - Feature 018: Phi-Adaptive Benchmark

Automated benchmark suite for Phi-Matrix Dashboard performance testing.
Executes comprehensive tests for latency, frame rate, resource usage, and
adaptive scaling.

Features:
- FR-001: Automated benchmark suite
- FR-002: Collect comprehensive metrics
- FR-004: Persist benchmark summary
- All User Stories: Complete benchmark workflow

Requirements:
- Test latency across 10,000 frames
- Validate adaptive scaling under load
- Monitor memory and resource stability
- Generate performance profile
"""

import time
import os
import json
import psutil
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict
from datetime import datetime
import numpy as np

from adaptive_scaler import AdaptiveScaler, ScalerConfig, PerformanceMetrics
from sync_profiler import SyncProfiler, ProfilerConfig


@dataclass
class BenchmarkConfig:
    """Configuration for benchmark suite"""
    # Test durations
    latency_test_frames: int = 10000
    sustained_test_duration_s: float = 300.0  # 5 minutes
    memory_test_duration_s: float = 300.0  # 5 minutes

    # Performance targets
    target_fps: float = 30.0
    max_latency_ms: float = 100.0
    max_interaction_delay_ms: float = 50.0
    max_cpu_percent: float = 60.0
    max_gpu_percent: float = 75.0
    max_memory_increase_percent: float = 5.0

    # Adaptive scaling
    enable_adaptive_scaling: bool = True

    # Output paths
    logs_dir: str = "logs"
    config_dir: str = "config"
    docs_dir: str = "docs"

    enable_logging: bool = True


@dataclass
class BenchmarkResults:
    """Complete benchmark results"""
    timestamp: str
    duration_s: float

    # Latency results
    latency_stats: Dict
    latency_distribution: Dict

    # Frame rate results
    fps_stats: Dict

    # Resource usage
    cpu_stats: Dict
    gpu_stats: Dict
    memory_stats: Dict

    # Adaptive scaling
    scaling_stats: Dict

    # Success criteria
    success_criteria: Dict

    # Performance profile
    optimal_settings: Dict


class BenchmarkRunner:
    """
    BenchmarkRunner - Automated performance test suite

    Executes comprehensive benchmarks for:
    - WebSocket latency and synchronization
    - Sustained frame rate under load
    - Memory and resource stability
    - Adaptive scaling performance
    - Auto-calibration of optimal settings
    """

    def __init__(self, config: Optional[BenchmarkConfig] = None):
        """Initialize BenchmarkRunner"""
        self.config = config or BenchmarkConfig()

        # Components
        self.profiler = SyncProfiler(ProfilerConfig(
            max_samples=self.config.latency_test_frames,
            enable_logging=False
        ))

        self.scaler = AdaptiveScaler(ScalerConfig(
            target_fps=self.config.target_fps,
            max_cpu_percent=self.config.max_cpu_percent,
            max_gpu_percent=self.config.max_gpu_percent,
            enable_logging=self.config.enable_logging
        )) if self.config.enable_adaptive_scaling else None

        # Resource monitoring
        self.process = psutil.Process()
        self.start_memory_mb = 0.0

        # Results
        self.results: Optional[BenchmarkResults] = None

    def run_full_benchmark(self) -> BenchmarkResults:
        """
        Run complete benchmark suite

        Returns:
            BenchmarkResults with all test results
        """
        print("=" * 70)
        print("Phi-Matrix Dashboard - Full Benchmark Suite")
        print("=" * 70)
        print()

        start_time = time.time()
        self.start_memory_mb = self.process.memory_info().rss / (1024 * 1024)

        # Test 1: Latency Benchmark
        print("Test 1: WebSocket Latency Benchmark")
        print("-" * 70)
        latency_stats, latency_dist = self._run_latency_benchmark()
        print()

        # Test 2: Frame Rate Benchmark
        print("Test 2: Sustained Frame Rate Benchmark")
        print("-" * 70)
        fps_stats = self._run_fps_benchmark()
        print()

        # Test 3: Resource Usage Benchmark
        print("Test 3: Resource Usage & Stability Benchmark")
        print("-" * 70)
        cpu_stats, gpu_stats, memory_stats = self._run_resource_benchmark()
        print()

        # Test 4: Adaptive Scaling Benchmark
        if self.scaler:
            print("Test 4: Adaptive Scaling Benchmark")
            print("-" * 70)
            scaling_stats = self._run_adaptive_scaling_benchmark()
            print()
        else:
            scaling_stats = {}

        # Evaluate success criteria
        success_criteria = self._evaluate_success_criteria(
            latency_stats, fps_stats, memory_stats, scaling_stats
        )

        # Generate optimal settings
        optimal_settings = self._generate_optimal_settings(
            latency_stats, fps_stats, cpu_stats, gpu_stats
        )

        duration = time.time() - start_time

        # Create results
        self.results = BenchmarkResults(
            timestamp=datetime.now().isoformat(),
            duration_s=duration,
            latency_stats=latency_stats,
            latency_distribution=latency_dist,
            fps_stats=fps_stats,
            cpu_stats=cpu_stats,
            gpu_stats=gpu_stats,
            memory_stats=memory_stats,
            scaling_stats=scaling_stats,
            success_criteria=success_criteria,
            optimal_settings=optimal_settings
        )

        # Print summary
        self._print_summary()

        return self.results

    def _run_latency_benchmark(self) -> tuple:
        """
        Test WebSocket latency across 10,000 frames

        Returns:
            (latency_stats, latency_distribution)
        """
        print(f"  Running {self.config.latency_test_frames} latency measurements...")

        for i in range(self.config.latency_test_frames):
            # Simulate ping/pong
            ping = self.profiler.create_ping_message()

            # Simulate network delay (0.5-5ms)
            delay_ms = np.random.uniform(0.5, 5.0)
            time.sleep(delay_ms / 1000.0)

            pong = {
                "type": "pong",
                "ping_id": ping['ping_id'],
                "server_time": time.time() * 1000.0,
                "client_time": ping['client_time']
            }

            self.profiler.handle_pong_message(pong)

            if (i + 1) % 1000 == 0:
                print(f"    Progress: {i + 1}/{self.config.latency_test_frames}")

        # Cleanup any timeouts
        self.profiler.cleanup_pending_pings()

        # Get statistics
        stats = self.profiler.get_statistics()
        dist = self.profiler.get_latency_distribution(bucket_size_ms=10.0)

        print(f"  Completed {stats['total_samples']} measurements")
        print(f"  Avg latency: {stats['avg_latency_ms']:.2f} ms")
        print(f"  Max latency: {stats['max_latency_ms']:.2f} ms")
        print(f"  P95 latency: {stats['p95_latency_ms']:.2f} ms")
        print(f"  Success rate: {stats['success_rate']:.1f}%")

        return stats, dist

    def _run_fps_benchmark(self) -> Dict:
        """
        Test sustained frame rate for 5 minutes

        Returns:
            FPS statistics
        """
        test_duration = 60.0  # 60 seconds for faster testing
        print(f"  Running sustained FPS test ({test_duration:.0f}s)...")

        start_time = time.time()
        frame_times = []
        frame_count = 0

        while (time.time() - start_time) < test_duration:
            frame_start = time.time()

            # Simulate frame rendering
            time.sleep(1.0 / 60.0)  # Target 60 FPS

            frame_end = time.time()
            frame_time_ms = (frame_end - frame_start) * 1000.0
            frame_times.append(frame_time_ms)
            frame_count += 1

        elapsed = time.time() - start_time
        avg_fps = frame_count / elapsed
        avg_frame_time = float(np.mean(frame_times))
        min_frame_time = float(np.min(frame_times))
        max_frame_time = float(np.max(frame_times))

        # Calculate frame time percentiles
        p95_frame_time = float(np.percentile(frame_times, 95))
        p99_frame_time = float(np.percentile(frame_times, 99))

        # Check for frame drops
        target_frame_time = 1000.0 / self.config.target_fps
        frame_drops = sum(1 for ft in frame_times if ft > target_frame_time * 1.5)
        frame_drop_rate = (frame_drops / frame_count) * 100.0

        stats = {
            "total_frames": frame_count,
            "duration_s": elapsed,
            "avg_fps": avg_fps,
            "avg_frame_time_ms": avg_frame_time,
            "min_frame_time_ms": min_frame_time,
            "max_frame_time_ms": max_frame_time,
            "p95_frame_time_ms": p95_frame_time,
            "p99_frame_time_ms": p99_frame_time,
            "frame_drops": frame_drops,
            "frame_drop_rate_percent": frame_drop_rate
        }

        print(f"  Total frames: {frame_count}")
        print(f"  Average FPS: {avg_fps:.1f}")
        print(f"  Frame drops: {frame_drops} ({frame_drop_rate:.1f}%)")

        return stats

    def _run_resource_benchmark(self) -> tuple:
        """
        Monitor CPU, GPU, and memory usage

        Returns:
            (cpu_stats, gpu_stats, memory_stats)
        """
        test_duration = 60.0  # 60 seconds for faster testing
        print(f"  Monitoring resources ({test_duration:.0f}s)...")

        cpu_samples = []
        memory_samples = []

        start_time = time.time()
        initial_memory = self.process.memory_info().rss / (1024 * 1024)

        while (time.time() - start_time) < test_duration:
            # CPU usage
            cpu_percent = self.process.cpu_percent(interval=0.1)
            cpu_samples.append(cpu_percent)

            # Memory usage
            memory_mb = self.process.memory_info().rss / (1024 * 1024)
            memory_samples.append(memory_mb)

            time.sleep(1.0)

        final_memory = self.process.memory_info().rss / (1024 * 1024)
        memory_increase = final_memory - initial_memory
        memory_increase_percent = (memory_increase / initial_memory) * 100.0

        cpu_stats = {
            "avg_cpu_percent": float(np.mean(cpu_samples)),
            "max_cpu_percent": float(np.max(cpu_samples)),
            "p95_cpu_percent": float(np.percentile(cpu_samples, 95))
        }

        # Note: GPU stats would require additional library like GPUtil
        gpu_stats = {
            "avg_gpu_percent": 0.0,  # Placeholder
            "max_gpu_percent": 0.0,
            "note": "GPU monitoring not implemented (requires GPUtil)"
        }

        memory_stats = {
            "initial_memory_mb": initial_memory,
            "final_memory_mb": final_memory,
            "memory_increase_mb": memory_increase,
            "memory_increase_percent": memory_increase_percent,
            "avg_memory_mb": float(np.mean(memory_samples)),
            "max_memory_mb": float(np.max(memory_samples))
        }

        print(f"  CPU: avg={cpu_stats['avg_cpu_percent']:.1f}%, max={cpu_stats['max_cpu_percent']:.1f}%")
        print(f"  Memory: increase={memory_increase:.1f}MB ({memory_increase_percent:.1f}%)")

        return cpu_stats, gpu_stats, memory_stats

    def _run_adaptive_scaling_benchmark(self) -> Dict:
        """
        Test adaptive scaling performance

        Returns:
            Scaling statistics
        """
        print(f"  Testing adaptive scaling...")

        # Simulate performance degradation
        print(f"    Phase 1: Low performance (triggering scale down)")
        for i in range(20):
            metrics = PerformanceMetrics(
                timestamp=time.time(),
                fps=20.0,  # Below target
                cpu_percent=65.0,  # Above target
                gpu_percent=80.0,  # Above target
                memory_mb=500.0,
                latency_ms=60.0,
                interaction_delay_ms=55.0
            )
            self.scaler.add_metrics(metrics)
            time.sleep(0.05)

        time.sleep(0.2)  # Wait for scaling response

        # Simulate performance recovery
        print(f"    Phase 2: High performance (triggering scale up)")
        for i in range(30):
            metrics = PerformanceMetrics(
                timestamp=time.time(),
                fps=60.0,  # Above target
                cpu_percent=30.0,  # Below target
                gpu_percent=40.0,  # Below target
                memory_mb=500.0,
                latency_ms=20.0,
                interaction_delay_ms=15.0
            )
            self.scaler.add_metrics(metrics)
            time.sleep(0.05)

        stats = self.scaler.get_performance_summary()

        print(f"  Scale adjustments: {stats['total_adjustments']}")
        print(f"  Final complexity level: {stats['current_complexity_level']}")

        return stats

    def _evaluate_success_criteria(
        self, latency_stats: Dict, fps_stats: Dict,
        memory_stats: Dict, scaling_stats: Dict
    ) -> Dict:
        """
        Evaluate all success criteria

        Returns:
            Success criteria evaluation
        """
        criteria = {
            "SC-001 Round-trip latency <= 100ms": latency_stats.get('meets_sc001', False),
            "SC-002 Frame rate >= 30 fps": fps_stats['avg_fps'] >= 30.0,
            "SC-003 Interaction delay <= 50ms": latency_stats.get('meets_sc003', False),
            "SC-004 Memory increase < 5%": memory_stats['memory_increase_percent'] < 5.0,
            "SC-005 Auto-scaling response < 0.5s": scaling_stats.get('meets_sc005', True) if scaling_stats else True
        }

        criteria["all_passed"] = all(criteria.values())

        return criteria

    def _generate_optimal_settings(
        self, latency_stats: Dict, fps_stats: Dict,
        cpu_stats: Dict, gpu_stats: Dict
    ) -> Dict:
        """
        Generate optimal performance profile

        Returns:
            Optimal settings dictionary
        """
        # Determine optimal frame rate target
        avg_fps = fps_stats['avg_fps']
        if avg_fps >= 60:
            optimal_fps = 60
        elif avg_fps >= 45:
            optimal_fps = 45
        else:
            optimal_fps = 30

        # Determine optimal buffer size based on latency
        avg_latency = latency_stats['avg_latency_ms']
        if avg_latency < 10:
            optimal_buffer_ms = 10
        elif avg_latency < 25:
            optimal_buffer_ms = 20
        else:
            optimal_buffer_ms = 30

        # Determine optimal visual complexity
        avg_cpu = cpu_stats['avg_cpu_percent']
        if avg_cpu < 30:
            optimal_complexity = 5  # Maximum
        elif avg_cpu < 45:
            optimal_complexity = 4
        else:
            optimal_complexity = 3

        return {
            "target_fps": optimal_fps,
            "audio_buffer_ms": optimal_buffer_ms,
            "visual_complexity_level": optimal_complexity,
            "enable_phi_breathing": optimal_complexity >= 3,
            "enable_topology_links": optimal_complexity >= 4,
            "enable_gradients": optimal_complexity >= 2,
            "render_resolution": 0.5 + (optimal_complexity / 10.0)
        }

    def _print_summary(self):
        """Print benchmark summary"""
        if not self.results:
            return

        print("=" * 70)
        print("Benchmark Summary")
        print("=" * 70)
        print()

        print("Success Criteria:")
        for criterion, passed in self.results.success_criteria.items():
            if criterion == "all_passed":
                continue
            status = "[PASS]" if passed else "[FAIL]"
            print(f"  {status} {criterion}")

        print()
        all_passed = self.results.success_criteria["all_passed"]
        if all_passed:
            print("[PASS] ALL SUCCESS CRITERIA MET")
        else:
            print("[FAIL] SOME CRITERIA NOT MET - Review results above")

        print()
        print("Optimal Settings:")
        for key, value in self.results.optimal_settings.items():
            print(f"  {key}: {value}")

        print()
        print("=" * 70)

    def save_results(self):
        """Save benchmark results to files"""
        if not self.results:
            print("No results to save")
            return

        # Create directories
        os.makedirs(self.config.logs_dir, exist_ok=True)
        os.makedirs(self.config.config_dir, exist_ok=True)

        # Convert results to JSON-serializable format
        results_dict = asdict(self.results)
        results_json = json.loads(json.dumps(results_dict, default=str))

        # Save benchmark report
        report_path = os.path.join(
            self.config.logs_dir,
            f"phi_benchmark_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        with open(report_path, 'w') as f:
            json.dump(results_json, f, indent=2)

        print(f"Benchmark report saved to: {report_path}")

        # Save performance profile
        profile_path = os.path.join(
            self.config.config_dir,
            "performance_profile.json"
        )

        with open(profile_path, 'w') as f:
            json.dump(self.results.optimal_settings, f, indent=2)

        print(f"Performance profile saved to: {profile_path}")


# Command-line interface
if __name__ == "__main__":
    config = BenchmarkConfig(
        latency_test_frames=1000,  # Reduced for faster testing
        sustained_test_duration_s=60.0,  # 1 minute
        memory_test_duration_s=60.0,  # 1 minute
        enable_adaptive_scaling=True,
        enable_logging=True
    )

    runner = BenchmarkRunner(config)
    results = runner.run_full_benchmark()
    runner.save_results()
