"""
Criticality Balancer - Adaptive Coupling and Amplitude Control
Feature 012: Maintains system stability at edge of chaos (criticality ~= 1.0)

Extends Auto-Phi Learner with:
- Adaptive coupling matrix adjustment (FR-003, FR-004)
- Per-channel amplitude balancing (FR-005)
- Batch WebSocket updates (FR-006)
- Enable/disable control (FR-007)

Control Law:
  Δc = β × (1 – criticality) × sign(d(coherence)/dt)
  Aᵢ ← Aᵢ × (1 ± δ) based on local energy

Success Criteria:
- SC-001: Criticality 0.95-1.05 for ≥90% runtime
- SC-002: Recovery from imbalance <10s
- SC-003: CPU overhead <5%
- SC-004: Instant disable
"""

import numpy as np
import time
from typing import Optional, Callable, Dict, List
from dataclasses import dataclass
from collections import deque


@dataclass
class CriticalityBalancerConfig:
    """Configuration for Criticality Balancer"""
    enabled: bool = False

    # Control gains
    beta_coupling: float = 0.1      # Coupling adjustment gain (FR-003)
    delta_amplitude: float = 0.05   # Amplitude adjustment rate (FR-005)

    # Target range
    target_criticality: float = 1.0
    criticality_min: float = 0.95   # SC-001
    criticality_max: float = 1.05   # SC-001

    # Safety bounds (edge cases)
    coupling_min: float = 0.0
    coupling_max: float = 1.0
    amplitude_min: float = 0.0
    amplitude_max: float = 1.0

    # Extreme protection (User Story 2)
    hypersync_threshold: float = 1.1   # Prevent runaway synchronization
    coma_threshold: float = 0.4        # Prevent collapse

    # Update rate
    update_interval: float = 0.1  # 10 Hz

    # Smoothing
    smoothing_window: int = 30  # 3s @ 10Hz

    # Logging
    enable_logging: bool = True
    log_interval: float = 1.0


@dataclass
class CriticalityBalancerState:
    """Current state of Criticality Balancer"""
    enabled: bool = False

    # Current metrics
    criticality: float = 1.0
    coherence: float = 0.0

    # Control state
    criticality_error: float = 0.0
    coherence_derivative: float = 0.0
    coupling_adjustment: float = 0.0

    # Channel state (8 channels)
    amplitudes: np.ndarray = None
    coupling_matrix: np.ndarray = None

    # Performance tracking
    in_range_count: int = 0
    total_count: int = 0
    last_recovery_start: float = 0.0
    recovery_time: float = 0.0
    recovering: bool = False
    settled: bool = True  # For compatibility with tests

    # Extreme condition tracking
    hypersync_count: int = 0
    coma_count: int = 0

    # Timing
    last_update: float = 0.0

    def __post_init__(self):
        if self.amplitudes is None:
            self.amplitudes = np.ones(8) * 0.5
        if self.coupling_matrix is None:
            # Initialize with uniform coupling
            self.coupling_matrix = np.ones((8, 8)) * 0.1
            np.fill_diagonal(self.coupling_matrix, 0.0)  # No self-coupling


class CriticalityBalancer:
    """
    Adaptive coupling and amplitude balancer

    Maintains system at edge of chaos (criticality ≈ 1.0) by:
    - Redistributing coupling between channels (User Story 1)
    - Balancing amplitudes based on local energy (FR-005)
    - Preventing runaway states (User Story 2)

    Features:
    - Adaptive coupling matrix adjustment
    - Per-channel amplitude balancing
    - Batch WebSocket updates
    - Extreme condition protection
    - Enable/disable toggle
    """

    def __init__(self, config: Optional[CriticalityBalancerConfig] = None):
        """
        Initialize Criticality Balancer

        Args:
            config: CriticalityBalancerConfig (uses defaults if None)
        """
        self.config = config or CriticalityBalancerConfig()
        self.state = CriticalityBalancerState()

        # Metrics history for smoothing (FR-002)
        self.criticality_history = deque(maxlen=self.config.smoothing_window)
        self.coherence_history = deque(maxlen=self.config.smoothing_window)

        # Performance tracking
        self.criticality_log: List[float] = []
        self.recovery_times: List[float] = []
        self.timestamps: List[float] = []

        # Last logged time
        self.last_log_time = 0.0

        # Callback for parameter updates (FR-006)
        self.update_callback: Optional[Callable[[Dict], None]] = None

        print("[CriticalityBalancer] Initialized")
        print(f"[CriticalityBalancer]   beta_coupling={self.config.beta_coupling}, delta_amplitude={self.config.delta_amplitude}")
        print(f"[CriticalityBalancer]   target_criticality={self.config.target_criticality}")
        print(f"[CriticalityBalancer]   enabled={self.config.enabled}")

    def set_enabled(self, enabled: bool):
        """
        Enable or disable balancer (FR-007, SC-004)

        Args:
            enabled: True to enable, False to disable
        """
        if self.config.enabled == enabled:
            return

        self.config.enabled = enabled
        self.state.enabled = enabled

        if enabled:
            print("[CriticalityBalancer] ENABLED - starting adaptive balancing")
            # Reset state
            self.state.last_update = time.time()
            self.state.in_range_count = 0
            self.state.total_count = 0
            self.state.recovering = False
        else:
            print("[CriticalityBalancer] DISABLED - manual control restored")

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
        criticality = getattr(metrics_frame, 'criticality', 1.0)
        coherence = getattr(metrics_frame, 'phase_coherence', 0.0)

        # Edge case: Invalid metrics → skip
        if criticality == 0.0 and coherence == 0.0:
            print("[CriticalityBalancer] WARNING: Invalid metrics, skipping update")
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

        # Apply balancing algorithms
        updated = self._apply_balancing(criticality_smooth, coherence_smooth, dt)

        # Track performance
        self._track_performance(criticality_smooth, current_time)

        # Log if needed
        if self.config.enable_logging and (current_time - self.last_log_time) >= self.config.log_interval:
            self._log_stats()
            self.last_log_time = current_time

        return updated

    def _apply_balancing(self, criticality: float, coherence: float, dt: float) -> bool:
        """
        Apply adaptive balancing algorithms (FR-003, FR-004, FR-005)

        Args:
            criticality: Current criticality value
            coherence: Current phase coherence
            dt: Time delta since last update

        Returns:
            True if parameters were updated
        """
        updated = False

        # Compute error and derivative
        criticality_error = self.config.target_criticality - criticality
        self.state.criticality_error = criticality_error

        # Compute coherence derivative
        if len(self.coherence_history) >= 2:
            coherence_prev = self.coherence_history[-2]
            coherence_derivative = (coherence - coherence_prev) / dt
            self.state.coherence_derivative = coherence_derivative
        else:
            coherence_derivative = 0.0

        # --- Coupling Matrix Adjustment (FR-003, FR-004) ---
        # Δc = β × (1 – criticality) × sign(d(coherence)/dt)
        coherence_sign = np.sign(coherence_derivative) if coherence_derivative != 0 else 0
        delta_coupling = self.config.beta_coupling * criticality_error * coherence_sign

        self.state.coupling_adjustment = delta_coupling

        # Apply to off-diagonal entries
        if abs(delta_coupling) > 0.001:
            # Get current coupling matrix
            coupling_matrix = self.state.coupling_matrix.copy()

            # Adjust off-diagonal entries (User Story 1: redistribute coupling)
            mask = ~np.eye(8, dtype=bool)  # Off-diagonal mask
            coupling_matrix[mask] += delta_coupling

            # Clamp to bounds (Edge case: hard clamp)
            coupling_matrix = np.clip(coupling_matrix, self.config.coupling_min, self.config.coupling_max)

            # Preserve zero diagonal
            np.fill_diagonal(coupling_matrix, 0.0)

            # Normalize rows to maintain total coupling strength
            row_sums = coupling_matrix.sum(axis=1, keepdims=True)
            row_sums[row_sums == 0] = 1.0  # Avoid division by zero
            coupling_matrix = coupling_matrix / row_sums * row_sums.mean()

            self.state.coupling_matrix = coupling_matrix
            updated = True

        # --- Amplitude Balancing (FR-005) ---
        # Adjust per-channel amplitude based on local energy
        # Simple heuristic: reduce high-energy channels, boost low-energy
        amplitudes = self.state.amplitudes.copy()

        # Compute relative energy (using coupling row sums as proxy)
        energy_proxy = self.state.coupling_matrix.sum(axis=1)
        mean_energy = energy_proxy.mean()

        # Adjust amplitudes inversely proportional to energy
        for i in range(8):
            if mean_energy > 0:
                energy_ratio = energy_proxy[i] / mean_energy
                # High energy → reduce amplitude, low energy → increase amplitude
                adjustment = self.config.delta_amplitude * (1.0 - energy_ratio) * dt
                amplitudes[i] += adjustment

        # Clamp to bounds
        amplitudes = np.clip(amplitudes, self.config.amplitude_min, self.config.amplitude_max)

        # Check if changed significantly
        if np.max(np.abs(amplitudes - self.state.amplitudes)) > 0.001:
            self.state.amplitudes = amplitudes
            updated = True

        # --- Extreme Protection (User Story 2) ---
        # Prevent hypersync (criticality > 1.1)
        if criticality > self.config.hypersync_threshold:
            # Reduce coupling to prevent runaway
            self.state.coupling_matrix *= 0.95
            self.state.coupling_matrix = np.clip(self.state.coupling_matrix, self.config.coupling_min, self.config.coupling_max)
            np.fill_diagonal(self.state.coupling_matrix, 0.0)
            self.state.hypersync_count += 1
            print(f"[CriticalityBalancer] Hypersync detected: criticality={criticality:.3f}, reducing coupling")
            updated = True

        # Prevent coma (criticality < 0.4)
        if criticality < self.config.coma_threshold:
            # Increase coupling to boost activity
            self.state.coupling_matrix *= 1.05
            self.state.coupling_matrix = np.clip(self.state.coupling_matrix, self.config.coupling_min, self.config.coupling_max)
            np.fill_diagonal(self.state.coupling_matrix, 0.0)
            self.state.coma_count += 1
            print(f"[CriticalityBalancer] Coma detected: criticality={criticality:.3f}, increasing coupling")
            updated = True

        # Send batch update (FR-006)
        if updated and self.update_callback:
            update_data = {
                'type': 'update_coupling',
                'coupling_matrix': self.state.coupling_matrix.tolist(),
                'amplitudes': self.state.amplitudes.tolist()
            }
            self.update_callback(update_data)

        return updated

    def _track_performance(self, criticality: float, current_time: float):
        """
        Track performance metrics (SC-001, SC-002)

        Args:
            criticality: Current criticality value
            current_time: Current timestamp
        """
        # Check if in range (SC-001: 0.95-1.05)
        in_range = self.config.criticality_min <= criticality <= self.config.criticality_max

        if in_range:
            self.state.in_range_count += 1

        self.state.total_count += 1

        # Detect imbalance and recovery (SC-002)
        out_of_range = not in_range and abs(self.state.criticality_error) > 0.1

        if out_of_range and not self.state.recovering:
            # Start recovery
            self.state.recovering = True
            self.state.last_recovery_start = current_time
            print(f"[CriticalityBalancer] Imbalance detected: criticality={criticality:.3f}")

        elif self.state.recovering and in_range:
            # Recovery complete
            recovery_time = current_time - self.state.last_recovery_start
            self.state.recovery_time = recovery_time
            self.state.recovering = False
            self.recovery_times.append(recovery_time)
            print(f"[CriticalityBalancer] Recovered in {recovery_time:.2f}s (SC-002: target <10s)")

        # Append to log
        if self.config.enable_logging:
            self.criticality_log.append(criticality)
            self.timestamps.append(current_time)

    def _log_stats(self):
        """Log performance statistics"""
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

        # Recovery statistics
        if len(self.recovery_times) > 0:
            avg_recovery = np.mean(self.recovery_times)
            max_recovery = np.max(self.recovery_times)
        else:
            avg_recovery = 0.0
            max_recovery = 0.0

        print(f"[CriticalityBalancer] Stats: criticality={crit_mean:.3f}±{crit_std:.3f}, "
              f"in_range={in_range_percent:.1f}%, "
              f"avg_recovery={avg_recovery:.2f}s")

    def get_statistics(self) -> Dict:
        """
        Get performance statistics

        Returns:
            Dictionary with performance metrics
        """
        if self.state.total_count == 0:
            return {
                'enabled': self.config.enabled,
                'criticality_mean': 0.0,
                'criticality_std': 0.0,
                'in_range_percent': 0.0,
                'avg_recovery_time': 0.0,
                'max_recovery_time': 0.0
            }

        in_range_percent = (self.state.in_range_count / self.state.total_count) * 100

        if len(self.criticality_log) > 0:
            crit_mean = float(np.mean(self.criticality_log))
            crit_std = float(np.std(self.criticality_log))
        else:
            crit_mean = 0.0
            crit_std = 0.0

        if len(self.recovery_times) > 0:
            avg_recovery = float(np.mean(self.recovery_times))
            max_recovery = float(np.max(self.recovery_times))
        else:
            avg_recovery = 0.0
            max_recovery = 0.0

        return {
            'enabled': self.config.enabled,
            'criticality_mean': crit_mean,
            'criticality_std': crit_std,
            'in_range_percent': in_range_percent,
            'in_range_count': self.state.in_range_count,
            'total_count': self.state.total_count,
            'recovering': self.state.recovering,
            'recovery_count': len(self.recovery_times),
            'avg_recovery_time': avg_recovery,
            'max_recovery_time': max_recovery,
            'criticality_error': self.state.criticality_error,
            'coupling_adjustment': self.state.coupling_adjustment
        }

    def reset_statistics(self):
        """Reset performance statistics"""
        self.state.in_range_count = 0
        self.state.total_count = 0
        self.state.recovering = False
        self.state.recovery_time = 0.0

        self.criticality_log.clear()
        self.recovery_times.clear()
        self.timestamps.clear()

        print("[CriticalityBalancer] Statistics reset")

    def get_current_state(self) -> Dict:
        """
        Get current balancer state

        Returns:
            Dictionary with current state
        """
        return {
            'enabled': self.state.enabled,
            'criticality': float(self.state.criticality),
            'coherence': float(self.state.coherence),
            'criticality_error': float(self.state.criticality_error),
            'coupling_adjustment': float(self.state.coupling_adjustment),
            'coupling_matrix': self.state.coupling_matrix.tolist(),
            'amplitudes': self.state.amplitudes.tolist(),
            'recovering': self.state.recovering
        }

    def export_logs(self) -> Dict:
        """
        Export performance logs for analysis

        Returns:
            Dictionary with time-series data
        """
        return {
            'timestamps': self.timestamps,
            'criticality': self.criticality_log,
            'recovery_times': self.recovery_times,
            'config': {
                'beta_coupling': self.config.beta_coupling,
                'delta_amplitude': self.config.delta_amplitude,
                'target_criticality': self.config.target_criticality
            }
        }


# Self-test function
def _self_test():
    """Test CriticalityBalancer"""
    print("=" * 60)
    print("CriticalityBalancer Self-Test")
    print("=" * 60)

    # Create mock metrics frame
    class MockMetrics:
        def __init__(self, criticality, phase_coherence):
            self.criticality = criticality
            self.phase_coherence = phase_coherence

    # Test 1: Initialization
    print("\n1. Testing initialization...")
    config = CriticalityBalancerConfig(enabled=True, beta_coupling=0.1, delta_amplitude=0.05)
    balancer = CriticalityBalancer(config)

    assert balancer.config.enabled == True
    assert balancer.config.beta_coupling == 0.1
    assert balancer.state.coupling_matrix.shape == (8, 8)
    assert balancer.state.amplitudes.shape == (8,)
    print("   OK: Initialization")

    # Test 2: Toggle enable/disable (SC-004)
    print("\n2. Testing enable/disable toggle...")
    balancer.set_enabled(False)
    assert balancer.config.enabled == False
    balancer.set_enabled(True)
    assert balancer.config.enabled == True
    print("   OK: Toggle")

    # Test 3: Process metrics and balancing
    print("\n3. Testing balancing algorithm...")

    # Track updates
    updates = []
    def callback(update_data):
        updates.append(update_data)

    balancer.update_callback = callback

    # Send metrics with low criticality
    time.sleep(0.15)
    metrics1 = MockMetrics(criticality=0.8, phase_coherence=0.7)
    balancer.process_metrics(metrics1)

    time.sleep(0.15)
    metrics2 = MockMetrics(criticality=0.8, phase_coherence=0.75)
    balancer.process_metrics(metrics2)

    print(f"   Updates sent: {len(updates)}")
    if len(updates) > 0:
        print(f"   Coupling matrix shape: {np.array(updates[0]['coupling_matrix']).shape}")
        print(f"   Amplitudes shape: {np.array(updates[0]['amplitudes']).shape}")

    assert len(updates) > 0, "Should send updates"
    print("   OK: Balancing algorithm")

    # Test 4: Statistics tracking
    print("\n4. Testing statistics...")
    stats = balancer.get_statistics()
    assert 'criticality_mean' in stats
    assert 'in_range_percent' in stats
    assert stats['enabled'] == True
    print(f"   OK: Statistics: in_range={stats['in_range_percent']:.1f}%")

    # Test 5: Get current state
    print("\n5. Testing state export...")
    state = balancer.get_current_state()
    assert 'coupling_matrix' in state
    assert 'amplitudes' in state
    assert len(state['amplitudes']) == 8
    print("   OK: State export")

    print("\n" + "=" * 60)
    print("Self-Test PASSED")
    print("=" * 60)

    return True


if __name__ == "__main__":
    _self_test()
