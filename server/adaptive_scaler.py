"""
AdaptiveScaler - Feature 018: Phi-Adaptive Benchmark

Automatically scales visual complexity based on real-time performance metrics
to maintain target frame rate (>= 30 fps) and interaction delay (<= 50 ms).

Features:
- FR-003: Auto-adjust visual load based on real-time metrics
- SC-002: Maintain >= 30 fps continuous
- SC-005: Auto-scaling response time < 0.5s
- User Story 1: Adaptive Frame Scheduler

Requirements:
- Frame-rate drops < 10% under load
- CPU <= 60%, GPU <= 75%
- Response time < 0.5s to stabilize fps
"""

import time
import threading
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass
from collections import deque
import numpy as np


@dataclass
class PerformanceMetrics:
    """Current performance metrics"""
    timestamp: float
    fps: float
    cpu_percent: float
    gpu_percent: float
    memory_mb: float
    latency_ms: float
    interaction_delay_ms: float


@dataclass
class VisualComplexity:
    """Visual complexity settings"""
    level: int  # 0-5: 0=minimal, 5=maximum
    enable_phi_breathing: bool
    enable_topology_links: bool
    enable_gradients: bool
    particle_count: int
    render_resolution: float  # 0.5-1.0


@dataclass
class ScalerConfig:
    """Configuration for AdaptiveScaler"""
    target_fps: float = 30.0
    min_fps: float = 28.0
    max_fps: float = 60.0
    target_latency_ms: float = 50.0
    max_latency_ms: float = 100.0
    max_cpu_percent: float = 60.0
    max_gpu_percent: float = 75.0
    scaling_response_time_s: float = 0.5
    sample_window_size: int = 30
    enable_logging: bool = False


class AdaptiveScaler:
    """
    AdaptiveScaler - Automatic visual complexity adjustment

    Monitors real-time performance and adjusts visual settings to maintain
    target frame rate and interaction delay.

    Features:
    - Continuous performance monitoring
    - Automatic complexity scaling
    - Gradual transitions (< 0.5s response time)
    - Resource usage tracking
    """

    def __init__(self, config: Optional[ScalerConfig] = None):
        """Initialize AdaptiveScaler"""
        self.config = config or ScalerConfig()

        # Performance history
        self.metrics_history: deque = deque(maxlen=self.config.sample_window_size)

        # Current visual complexity
        self.complexity = VisualComplexity(
            level=5,  # Start at maximum
            enable_phi_breathing=True,
            enable_topology_links=True,
            enable_gradients=True,
            particle_count=100,
            render_resolution=1.0
        )

        # Scaling state
        self.last_scale_time = time.time()
        self.scaling_direction = 0  # -1: down, 0: stable, 1: up
        self.consecutive_low_fps = 0
        self.consecutive_high_fps = 0

        # Callbacks
        self.complexity_change_callback: Optional[Callable] = None

        # Monitoring
        self.is_running = False
        self.monitor_thread: Optional[threading.Thread] = None

        # Statistics
        self.scale_up_count = 0
        self.scale_down_count = 0
        self.total_adjustments = 0

    def add_metrics(self, metrics: PerformanceMetrics):
        """
        Add performance metrics sample

        Args:
            metrics: Current performance metrics
        """
        self.metrics_history.append(metrics)

        # Check if scaling is needed
        self._check_scaling_needed()

    def _check_scaling_needed(self):
        """Check if visual complexity should be adjusted"""
        if len(self.metrics_history) < 5:
            return

        # Get recent metrics
        recent_metrics = list(self.metrics_history)[-10:]
        avg_fps = np.mean([m.fps for m in recent_metrics])
        avg_latency = np.mean([m.latency_ms for m in recent_metrics])
        avg_cpu = np.mean([m.cpu_percent for m in recent_metrics])
        avg_gpu = np.mean([m.gpu_percent for m in recent_metrics])

        # Check if we need to scale down (reduce complexity)
        should_scale_down = (
            avg_fps < self.config.min_fps or
            avg_latency > self.config.max_latency_ms or
            avg_cpu > self.config.max_cpu_percent or
            avg_gpu > self.config.max_gpu_percent
        )

        # Check if we can scale up (increase complexity)
        should_scale_up = (
            avg_fps > (self.config.target_fps * 1.5) and
            avg_latency < (self.config.target_latency_ms * 0.5) and
            avg_cpu < (self.config.max_cpu_percent * 0.7) and
            avg_gpu < (self.config.max_gpu_percent * 0.7) and
            self.complexity.level < 5
        )

        current_time = time.time()
        time_since_last_scale = current_time - self.last_scale_time

        # Only scale if enough time has passed (response time < 0.5s)
        if time_since_last_scale < self.config.scaling_response_time_s:
            return

        if should_scale_down:
            self.consecutive_low_fps += 1
            self.consecutive_high_fps = 0

            # Scale down after 3 consecutive low readings
            if self.consecutive_low_fps >= 3:
                self._scale_down(avg_fps, avg_latency, avg_cpu, avg_gpu)
                self.consecutive_low_fps = 0

        elif should_scale_up:
            self.consecutive_high_fps += 1
            self.consecutive_low_fps = 0

            # Scale up after 5 consecutive high readings (be conservative)
            if self.consecutive_high_fps >= 5:
                self._scale_up(avg_fps, avg_latency, avg_cpu, avg_gpu)
                self.consecutive_high_fps = 0

        else:
            # Stable performance
            self.consecutive_low_fps = 0
            self.consecutive_high_fps = 0
            self.scaling_direction = 0

    def _scale_down(self, fps: float, latency: float, cpu: float, gpu: float):
        """
        Reduce visual complexity

        Args:
            fps: Current average FPS
            latency: Current average latency
            cpu: Current average CPU usage
            gpu: Current average GPU usage
        """
        if self.complexity.level <= 0:
            return

        old_level = self.complexity.level
        self.complexity.level -= 1
        self.scaling_direction = -1
        self.last_scale_time = time.time()
        self.scale_down_count += 1
        self.total_adjustments += 1

        # Adjust settings based on level
        self._update_complexity_settings()

        if self.config.enable_logging:
            print(f"[AdaptiveScaler] Scaled DOWN: {old_level} -> {self.complexity.level}")
            print(f"  Reason: FPS={fps:.1f}, Latency={latency:.1f}ms, CPU={cpu:.1f}%, GPU={gpu:.1f}%")

        # Notify callback
        if self.complexity_change_callback:
            self.complexity_change_callback(self.complexity)

    def _scale_up(self, fps: float, latency: float, cpu: float, gpu: float):
        """
        Increase visual complexity

        Args:
            fps: Current average FPS
            latency: Current average latency
            cpu: Current average CPU usage
            gpu: Current average GPU usage
        """
        if self.complexity.level >= 5:
            return

        old_level = self.complexity.level
        self.complexity.level += 1
        self.scaling_direction = 1
        self.last_scale_time = time.time()
        self.scale_up_count += 1
        self.total_adjustments += 1

        # Adjust settings based on level
        self._update_complexity_settings()

        if self.config.enable_logging:
            print(f"[AdaptiveScaler] Scaled UP: {old_level} -> {self.complexity.level}")
            print(f"  Performance: FPS={fps:.1f}, Latency={latency:.1f}ms, CPU={cpu:.1f}%, GPU={gpu:.1f}%")

        # Notify callback
        if self.complexity_change_callback:
            self.complexity_change_callback(self.complexity)

    def _update_complexity_settings(self):
        """Update visual settings based on complexity level"""
        level = self.complexity.level

        if level == 0:
            # Minimal - spectral grid only
            self.complexity.enable_phi_breathing = False
            self.complexity.enable_topology_links = False
            self.complexity.enable_gradients = False
            self.complexity.particle_count = 0
            self.complexity.render_resolution = 0.5

        elif level == 1:
            # Low - basic visualization
            self.complexity.enable_phi_breathing = False
            self.complexity.enable_topology_links = False
            self.complexity.enable_gradients = True
            self.complexity.particle_count = 20
            self.complexity.render_resolution = 0.6

        elif level == 2:
            # Medium-Low - add breathing
            self.complexity.enable_phi_breathing = True
            self.complexity.enable_topology_links = False
            self.complexity.enable_gradients = True
            self.complexity.particle_count = 40
            self.complexity.render_resolution = 0.7

        elif level == 3:
            # Medium - add topology
            self.complexity.enable_phi_breathing = True
            self.complexity.enable_topology_links = True
            self.complexity.enable_gradients = True
            self.complexity.particle_count = 60
            self.complexity.render_resolution = 0.8

        elif level == 4:
            # High - increased particles
            self.complexity.enable_phi_breathing = True
            self.complexity.enable_topology_links = True
            self.complexity.enable_gradients = True
            self.complexity.particle_count = 80
            self.complexity.render_resolution = 0.9

        else:  # level == 5
            # Maximum - all features
            self.complexity.enable_phi_breathing = True
            self.complexity.enable_topology_links = True
            self.complexity.enable_gradients = True
            self.complexity.particle_count = 100
            self.complexity.render_resolution = 1.0

    def get_current_complexity(self) -> VisualComplexity:
        """Get current visual complexity settings"""
        return self.complexity

    def set_complexity_callback(self, callback: Callable):
        """
        Set callback for complexity changes

        Args:
            callback: Function to call when complexity changes
        """
        self.complexity_change_callback = callback

    def get_performance_summary(self) -> Dict:
        """
        Get performance summary statistics

        Returns:
            Summary dictionary
        """
        if not self.metrics_history:
            return {
                "avg_fps": 0.0,
                "min_fps": 0.0,
                "max_fps": 0.0,
                "avg_latency_ms": 0.0,
                "max_latency_ms": 0.0,
                "avg_cpu_percent": 0.0,
                "avg_gpu_percent": 0.0,
                "current_complexity_level": self.complexity.level,
                "scale_up_count": self.scale_up_count,
                "scale_down_count": self.scale_down_count,
                "total_adjustments": self.total_adjustments
            }

        recent_metrics = list(self.metrics_history)

        fps_values = [m.fps for m in recent_metrics]
        latency_values = [m.latency_ms for m in recent_metrics]
        cpu_values = [m.cpu_percent for m in recent_metrics]
        gpu_values = [m.gpu_percent for m in recent_metrics]

        return {
            "avg_fps": float(np.mean(fps_values)),
            "min_fps": float(np.min(fps_values)),
            "max_fps": float(np.max(fps_values)),
            "avg_latency_ms": float(np.mean(latency_values)),
            "max_latency_ms": float(np.max(latency_values)),
            "avg_cpu_percent": float(np.mean(cpu_values)),
            "avg_gpu_percent": float(np.mean(gpu_values)),
            "current_complexity_level": self.complexity.level,
            "scale_up_count": self.scale_up_count,
            "scale_down_count": self.scale_down_count,
            "total_adjustments": self.total_adjustments,
            "meets_sc002": np.mean(fps_values) >= 30.0,
            "meets_sc005": (time.time() - self.last_scale_time) < 0.5 if self.total_adjustments > 0 else True
        }

    def reset_statistics(self):
        """Reset all statistics"""
        self.scale_up_count = 0
        self.scale_down_count = 0
        self.total_adjustments = 0
        self.metrics_history.clear()
        self.consecutive_low_fps = 0
        self.consecutive_high_fps = 0


# Self-test
def _self_test():
    """Run basic self-test of AdaptiveScaler"""
    print("=" * 60)
    print("AdaptiveScaler Self-Test")
    print("=" * 60)
    print()

    all_ok = True

    # Test 1: Initialization
    print("1. Testing Initialization...")
    config = ScalerConfig(
        enable_logging=True,
        target_fps=30.0,
        scaling_response_time_s=0.1  # Faster response for testing
    )
    scaler = AdaptiveScaler(config)

    init_ok = scaler.complexity.level == 5
    all_ok = all_ok and init_ok

    print(f"   Initial complexity level: {scaler.complexity.level}")
    print(f"   [{'OK' if init_ok else 'FAIL'}] Initialization")
    print()

    # Test 2: Scale down on low FPS
    print("2. Testing Scale Down (low FPS)...")

    # Wait for initial response time to pass
    time.sleep(0.15)

    # Add metrics with low FPS (need at least 10 samples for averaging)
    for i in range(15):
        metrics = PerformanceMetrics(
            timestamp=time.time(),
            fps=20.0,  # Below target
            cpu_percent=50.0,
            gpu_percent=60.0,
            memory_mb=500.0,
            latency_ms=40.0,
            interaction_delay_ms=30.0
        )
        scaler.add_metrics(metrics)
        time.sleep(0.02)

    scale_down_ok = scaler.complexity.level < 5
    all_ok = all_ok and scale_down_ok

    print(f"   Complexity after low FPS: {scaler.complexity.level}")
    print(f"   [{'OK' if scale_down_ok else 'FAIL'}] Scale down")
    print()

    # Test 3: Scale up on high FPS
    print("3. Testing Scale Up (high FPS)...")

    # Wait for response time to pass
    time.sleep(0.15)

    # Add metrics with high FPS (need more samples for conservative scale-up)
    for i in range(20):
        metrics = PerformanceMetrics(
            timestamp=time.time(),
            fps=60.0,  # Above target
            cpu_percent=30.0,
            gpu_percent=40.0,
            memory_mb=500.0,
            latency_ms=20.0,
            interaction_delay_ms=15.0
        )
        scaler.add_metrics(metrics)
        time.sleep(0.02)

    initial_level = scaler.complexity.level
    scale_up_ok = scaler.scale_up_count > 0

    all_ok = all_ok and scale_up_ok

    print(f"   Complexity after high FPS: {scaler.complexity.level}")
    print(f"   Scale up count: {scaler.scale_up_count}")
    print(f"   [{'OK' if scale_up_ok else 'FAIL'}] Scale up")
    print()

    # Test 4: Performance summary
    print("4. Testing Performance Summary...")
    summary = scaler.get_performance_summary()

    summary_ok = (
        summary['avg_fps'] > 0 and
        summary['total_adjustments'] > 0
    )

    all_ok = all_ok and summary_ok

    print(f"   Avg FPS: {summary['avg_fps']:.1f}")
    print(f"   Total adjustments: {summary['total_adjustments']}")
    print(f"   [{'OK' if summary_ok else 'FAIL'}] Performance summary")
    print()

    # Test 5: Complexity settings
    print("5. Testing Complexity Settings...")

    # Manually set to level 0
    scaler.complexity.level = 0
    scaler._update_complexity_settings()

    level0_ok = (
        not scaler.complexity.enable_phi_breathing and
        not scaler.complexity.enable_topology_links and
        scaler.complexity.render_resolution == 0.5
    )

    all_ok = all_ok and level0_ok

    print(f"   Level 0 settings: breathing={scaler.complexity.enable_phi_breathing}, "
          f"topology={scaler.complexity.enable_topology_links}, "
          f"resolution={scaler.complexity.render_resolution}")

    # Set to level 5
    scaler.complexity.level = 5
    scaler._update_complexity_settings()

    level5_ok = (
        scaler.complexity.enable_phi_breathing and
        scaler.complexity.enable_topology_links and
        scaler.complexity.render_resolution == 1.0
    )

    all_ok = all_ok and level5_ok

    print(f"   Level 5 settings: breathing={scaler.complexity.enable_phi_breathing}, "
          f"topology={scaler.complexity.enable_topology_links}, "
          f"resolution={scaler.complexity.render_resolution}")
    print(f"   [{'OK' if level0_ok and level5_ok else 'FAIL'}] Complexity settings")
    print()

    print("=" * 60)
    if all_ok:
        print("Self-Test PASSED")
    else:
        print("Self-Test FAILED - Review failures above")
    print("=" * 60)

    return all_ok


if __name__ == "__main__":
    _self_test()
