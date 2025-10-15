"""
Auto-Φ Learner - Adaptive Modulation Control
Feature 011: Automatically adjusts Φ-depth and Φ-phase to maintain near-critical balance

Implements:
- FR-001: AutoPhiLearner class
- FR-002: Metrics stream subscription
- FR-003: Adaptive control law
- FR-004: Tunable parameters (k, γ)
- FR-005: WebSocket parameter updates
- FR-006: Enable/disable toggle
- FR-007: Performance logging

Control Law:
  phi_depth ← phi_depth + k × (1.0 – criticality) × Δt
  phi_phase ← phi_phase + γ × d(coherence)/dt

Success Criteria:
- SC-001: Criticality within ±0.05 for >90% of runtime
- SC-002: Reaction time ≤ 5s to disturbances
- SC-003: CPU load < 5%
- SC-004: Toggle changes state immediately
"""

import asyncio
import time
import numpy as np
from typing import Optional, Callable, Dict, List
from dataclasses import dataclass
import json
from collections import deque


@dataclass
class AutoPhiConfig:
    """Configuration for Auto-Φ Learner"""
    enabled: bool = False

    # Control gains (FR-004)
    k_depth: float = 0.25      # Depth control gain
    gamma_phase: float = 0.1   # Phase control gain

    # Target setpoint
    target_criticality: float = 1.0

    # Update rate
    update_interval: float = 0.1  # 10 Hz

    # Smoothing
    smoothing_window: int = 30  # 30 samples @ 10Hz = 3s

    # Safety limits
    depth_min: float = 0.0
    depth_max: float = 1.0
    phase_min: float = 0.0
    phase_max: float = 1.0

    # Disturbance detection
    disturbance_threshold: float = 0.15  # 15% change

    # Logging
    enable_logging: bool = True
    log_interval: float = 1.0  # Log stats every 1s


@dataclass
class AutoPhiState:
    """Current state of Auto-Φ Learner"""
    enabled: bool = False
    phi_depth: float = 0.5
    phi_phase: float = 0.5

    # Current metrics
    criticality: float = 0.0
    coherence: float = 0.0

    # Control state
    criticality_error: float = 0.0
    coherence_derivative: float = 0.0

    # Performance tracking
    in_range_count: int = 0
    total_count: int = 0
    last_disturbance_time: float = 0.0
    settled: bool = True

    # Timing
    last_update: float = 0.0


class AutoPhiLearner:
    """
    Adaptive Φ-modulation controller

    Automatically adjusts phi_depth and phi_phase to maintain system criticality near 1.0

    Features:
    - Feedback control based on criticality and phase coherence
    - Smooth adaptation with configurable gains
    - Disturbance detection and recovery
    - Performance logging
    - Enable/disable toggle
    """

    def __init__(self, config: Optional[AutoPhiConfig] = None):
        """
        Initialize Auto-Φ Learner

        Args:
            config: AutoPhiConfig (uses defaults if None)
        """
        self.config = config or AutoPhiConfig()
        self.state = AutoPhiState()

        # Metrics history for smoothing (FR-002)
        self.criticality_history = deque(maxlen=self.config.smoothing_window)
        self.coherence_history = deque(maxlen=self.config.smoothing_window)

        # Performance tracking (FR-007)
        self.criticality_log: List[float] = []
        self.depth_log: List[float] = []
        self.phase_log: List[float] = []
        self.timestamps: List[float] = []

        # Last logged time
        self.last_log_time = 0.0

        # Callback for parameter updates (FR-005)
        self.update_callback: Optional[Callable[[str, float], None]] = None

        # External bias (for Feature 013: State Memory integration)
        self.external_bias: float = 0.0

        # Task control
        self.running = False
        self.task: Optional[asyncio.Task] = None

        print("[AutoPhiLearner] Initialized")
        print(f"[AutoPhiLearner]   k_depth={self.config.k_depth}, gamma_phase={self.config.gamma_phase}")
        print(f"[AutoPhiLearner]   target_criticality={self.config.target_criticality}")
        print(f"[AutoPhiLearner]   enabled={self.config.enabled}")

    def set_enabled(self, enabled: bool):
        """
        Enable or disable learner (FR-006, SC-004)

        Args:
            enabled: True to enable, False to disable
        """
        if self.config.enabled == enabled:
            return

        self.config.enabled = enabled
        self.state.enabled = enabled

        if enabled:
            print("[AutoPhiLearner] ENABLED - starting adaptive control")
            # Reset state
            self.state.last_update = time.time()
            self.state.in_range_count = 0
            self.state.total_count = 0
        else:
            print("[AutoPhiLearner] DISABLED - manual control restored")

    def process_metrics(self, metrics_frame) -> bool:
        """
        Process incoming metrics frame (FR-002)

        Args:
            metrics_frame: MetricsFrame with criticality, phase_coherence, etc.

        Returns:
            True if update was applied
        """
        if not self.config.enabled:
            return False

        current_time = time.time()

        # Check if we should update (rate limiting)
        if current_time - self.state.last_update < self.config.update_interval:
            return False

        # Extract metrics
        criticality = getattr(metrics_frame, 'criticality', 0.0)
        coherence = getattr(metrics_frame, 'phase_coherence', 0.0)

        # Edge case: Invalid metrics → skip (FR-002 edge case)
        if criticality == 0.0 and coherence == 0.0:
            print("[AutoPhiLearner] WARNING: Invalid metrics, skipping update")
            return False

        # Add to history
        self.criticality_history.append(criticality)
        self.coherence_history.append(coherence)

        # Need enough history for derivative
        if len(self.criticality_history) < 2:
            return False

        # Compute smoothed values
        criticality_smooth = np.mean(self.criticality_history)
        coherence_smooth = np.mean(self.coherence_history)

        # Store in state
        self.state.criticality = criticality_smooth
        self.state.coherence = coherence_smooth

        # Compute time delta
        dt = current_time - self.state.last_update
        self.state.last_update = current_time

        # Apply control law (FR-003)
        updated = self._apply_control_law(criticality_smooth, coherence_smooth, dt)

        # Track performance (FR-007)
        self._track_performance(criticality_smooth, current_time)

        # Log if needed
        if self.config.enable_logging and (current_time - self.last_log_time) >= self.config.log_interval:
            self._log_stats()
            self.last_log_time = current_time

        return updated

    def _apply_control_law(self, criticality: float, coherence: float, dt: float) -> bool:
        """
        Apply adaptive control law (FR-003)

        Control equations:
          phi_depth ← phi_depth + k × (target – criticality) × Δt
          phi_phase ← phi_phase + γ × d(coherence)/dt

        Args:
            criticality: Current criticality value
            coherence: Current phase coherence
            dt: Time delta since last update

        Returns:
            True if parameters were updated
        """
        updated = False

        # --- Depth Control ---
        # Error signal: positive when criticality is below target
        criticality_error = self.config.target_criticality - criticality
        self.state.criticality_error = criticality_error

        # Proportional control
        depth_delta = self.config.k_depth * criticality_error * dt

        # Add external bias (Feature 013: predictive feed-forward)
        depth_delta += self.external_bias

        new_depth = self.state.phi_depth + depth_delta

        # Clamp to limits (FR-003 edge case)
        new_depth = np.clip(new_depth, self.config.depth_min, self.config.depth_max)

        # Apply if changed significantly (avoid noise)
        if abs(new_depth - self.state.phi_depth) > 0.001:
            self.state.phi_depth = new_depth

            # Send update (FR-005)
            if self.update_callback:
                self.update_callback('phi_depth', float(new_depth))

            updated = True

        # --- Phase Control ---
        # Compute coherence derivative (rate of change)
        if len(self.coherence_history) >= 2:
            coherence_prev = self.coherence_history[-2]
            coherence_derivative = (coherence - coherence_prev) / dt
            self.state.coherence_derivative = coherence_derivative

            # Apply phase adjustment
            phase_delta = self.config.gamma_phase * coherence_derivative

            new_phase = self.state.phi_phase + phase_delta

            # Wrap phase to [0, 1] range
            new_phase = new_phase % 1.0

            # Apply if changed significantly
            if abs(new_phase - self.state.phi_phase) > 0.001:
                self.state.phi_phase = new_phase

                # Send update (FR-005)
                if self.update_callback:
                    self.update_callback('phi_phase', float(new_phase))

                updated = True

        return updated

    def _track_performance(self, criticality: float, current_time: float):
        """
        Track performance metrics (FR-007, SC-001, SC-002)

        Args:
            criticality: Current criticality value
            current_time: Current timestamp
        """
        # Check if in range (SC-001: ±0.05 tolerance)
        in_range = abs(criticality - self.config.target_criticality) <= 0.05

        if in_range:
            self.state.in_range_count += 1

        self.state.total_count += 1

        # Detect disturbances (SC-002)
        if abs(self.state.criticality_error) > self.config.disturbance_threshold:
            if self.state.settled:
                # Disturbance detected
                self.state.last_disturbance_time = current_time
                self.state.settled = False
                print(f"[AutoPhiLearner] Disturbance detected: criticality={criticality:.3f}, error={self.state.criticality_error:.3f}")
        else:
            # Check if settled (within tolerance)
            if not self.state.settled and in_range:
                settling_time = current_time - self.state.last_disturbance_time
                self.state.settled = True
                print(f"[AutoPhiLearner] SETTLED in {settling_time:.2f}s (SC-002: target <=5s)")

        # Append to log
        if self.config.enable_logging:
            self.criticality_log.append(criticality)
            self.depth_log.append(self.state.phi_depth)
            self.phase_log.append(self.state.phi_phase)
            self.timestamps.append(current_time)

    def _log_stats(self):
        """Log performance statistics (FR-007)"""
        if self.state.total_count == 0:
            return

        # Calculate in-range percentage (SC-001)
        in_range_percent = (self.state.in_range_count / self.state.total_count) * 100

        # Calculate criticality statistics
        if len(self.criticality_log) > 0:
            crit_mean = np.mean(self.criticality_log[-30:])  # Last 30 samples
            crit_std = np.std(self.criticality_log[-30:])
        else:
            crit_mean = 0.0
            crit_std = 0.0

        print(f"[AutoPhiLearner] Stats: criticality={crit_mean:.3f}±{crit_std:.3f}, "
              f"in_range={in_range_percent:.1f}%, "
              f"phi_depth={self.state.phi_depth:.3f}, phi_phase={self.state.phi_phase:.3f}")

    def get_statistics(self) -> Dict:
        """
        Get performance statistics (FR-007)

        Returns:
            Dictionary with performance metrics
        """
        if self.state.total_count == 0:
            return {
                'enabled': self.config.enabled,
                'criticality_mean': 0.0,
                'criticality_std': 0.0,
                'in_range_percent': 0.0,
                'settled': True,
                'phi_depth': self.state.phi_depth,
                'phi_phase': self.state.phi_phase
            }

        in_range_percent = (self.state.in_range_count / self.state.total_count) * 100

        if len(self.criticality_log) > 0:
            crit_mean = float(np.mean(self.criticality_log))
            crit_std = float(np.std(self.criticality_log))
        else:
            crit_mean = 0.0
            crit_std = 0.0

        return {
            'enabled': self.config.enabled,
            'criticality_mean': crit_mean,
            'criticality_std': crit_std,
            'in_range_percent': in_range_percent,
            'in_range_count': self.state.in_range_count,
            'total_count': self.state.total_count,
            'settled': self.state.settled,
            'phi_depth': self.state.phi_depth,
            'phi_phase': self.state.phi_phase,
            'criticality_error': self.state.criticality_error,
            'coherence_derivative': self.state.coherence_derivative
        }

    def reset_statistics(self):
        """Reset performance statistics"""
        self.state.in_range_count = 0
        self.state.total_count = 0
        self.state.last_disturbance_time = 0.0
        self.state.settled = True

        self.criticality_log.clear()
        self.depth_log.clear()
        self.phase_log.clear()
        self.timestamps.clear()

        print("[AutoPhiLearner] Statistics reset")

    def export_logs(self) -> Dict:
        """
        Export performance logs for analysis

        Returns:
            Dictionary with time-series data
        """
        return {
            'timestamps': self.timestamps,
            'criticality': self.criticality_log,
            'phi_depth': self.depth_log,
            'phi_phase': self.phase_log,
            'config': {
                'k_depth': self.config.k_depth,
                'gamma_phase': self.config.gamma_phase,
                'target_criticality': self.config.target_criticality
            }
        }


# Self-test function
def _self_test():
    """Test AutoPhiLearner"""
    print("=" * 60)
    print("AutoPhiLearner Self-Test")
    print("=" * 60)

    # Create mock metrics frame
    class MockMetrics:
        def __init__(self, criticality, phase_coherence):
            self.criticality = criticality
            self.phase_coherence = phase_coherence

    # Test 1: Initialization
    print("\n1. Testing initialization...")
    config = AutoPhiConfig(enabled=True, k_depth=0.5, gamma_phase=0.1)
    learner = AutoPhiLearner(config)

    assert learner.config.enabled == True
    assert learner.config.k_depth == 0.5
    print("   OK: Initialization")

    # Test 2: Toggle enable/disable (SC-004)
    print("\n2. Testing enable/disable toggle...")
    learner.set_enabled(False)
    assert learner.config.enabled == False
    learner.set_enabled(True)
    assert learner.config.enabled == True
    print("   OK: Toggle")

    # Test 3: Process metrics and control law
    print("\n3. Testing control law...")

    # Set update callback
    updates = []
    def mock_callback(param, value):
        updates.append((param, value))

    learner.update_callback = mock_callback

    # Wait for initial update interval to pass
    time.sleep(0.15)

    # Send low criticality (should increase depth)
    initial_depth = learner.state.phi_depth
    metrics = MockMetrics(criticality=0.5, phase_coherence=0.8)

    # Send first metrics frame
    result1 = learner.process_metrics(metrics)
    print(f"   First process_metrics: {result1}")

    # Wait for update interval and send second frame (needed for derivative calculation)
    time.sleep(0.15)
    metrics2 = MockMetrics(criticality=0.5, phase_coherence=0.82)
    result2 = learner.process_metrics(metrics2)
    print(f"   Second process_metrics: {result2}")

    # Depth should increase (criticality < target)
    print(f"   Depth: {initial_depth:.3f} -> {learner.state.phi_depth:.3f}")
    print(f"   Updates: {updates}")
    assert learner.state.phi_depth > initial_depth, f"Expected depth to increase, got {learner.state.phi_depth}"
    print(f"   OK: Control law applied: depth {initial_depth:.3f} -> {learner.state.phi_depth:.3f}")

    # Test 4: Statistics tracking
    print("\n4. Testing statistics...")
    stats = learner.get_statistics()
    assert 'criticality_mean' in stats
    assert 'in_range_percent' in stats
    assert stats['enabled'] == True
    print(f"   OK: Statistics: in_range={stats['in_range_percent']:.1f}%")

    print("\n" + "=" * 60)
    print("Self-Test PASSED")
    print("=" * 60)

    return True


if __name__ == "__main__":
    _self_test()
