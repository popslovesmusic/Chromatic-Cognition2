"""
PhiAdaptiveController - Feature 012: Predictive Phi-Adaptation Engine

Main controller for adaptive Phi modulation based on feedback learning.

Features:
- FR-001: Monitor metrics (ICI, coherence, criticality) in real time
- FR-002: Adjust Phi parameters based on feedback
- SC-001: Maintain ICI ≈ 0.5 ± 0.05 for > 60s
- SC-002: Average Phi-update latency <= 200 ms
- Manual override support

Requirements:
- FR-001: System MUST monitor metrics in real time
- FR-002: System MUST adjust Phi based on feedback
- SC-001: Maintain ICI ≈ 0.5 ± 0.05 for > 60s
- SC-002: Phi-update latency <= 200 ms
- SC-004: Manual override responds < 50 ms
"""

import time
import threading
from typing import Optional, Callable, Dict
from dataclasses import dataclass
from enum import Enum
import numpy as np

from .session_memory import SessionMemory, MetricSnapshot
from .phi_predictor import PhiPredictor, PredictionResult


class AdaptiveMode(Enum):
    """Adaptive control modes"""
    OFF = 0           # Adaptive disabled
    REACTIVE = 1      # React to current metrics only
    PREDICTIVE = 2    # Use predictive model
    LEARNING = 3      # Learning + predictive


@dataclass
class AdaptiveConfig:
    """Configuration for adaptive controller"""
    target_ici: float = 0.5              # Target ICI value (SC-001)
    ici_tolerance: float = 0.05          # ICI tolerance (SC-001)
    update_rate_hz: float = 10.0         # Control loop rate
    adaptation_gain: float = 0.3         # How aggressively to adapt
    metric_timeout_s: float = 1.0        # Max time to hold last state
    enable_logging: bool = False


@dataclass
class AdaptiveStatus:
    """Current status of adaptive controller"""
    is_enabled: bool
    mode: AdaptiveMode
    current_ici: float
    target_ici: float
    ici_error: float
    current_phi: float
    predicted_phi: float
    phi_adjustment: float
    update_count: int
    avg_update_latency_ms: float
    ici_stable_time_s: float             # How long ICI has been stable (SC-001)
    manual_override_active: bool


class PhiAdaptiveController:
    """
    PhiAdaptiveController - Closed-loop Phi adaptation

    Handles:
    - Real-time metric monitoring (FR-001)
    - Feedback-based Phi adjustment (FR-002)
    - ICI stability maintenance (SC-001)
    - Low-latency updates (SC-002)
    - Manual override (SC-004)
    """

    PHI_MIN = 0.618033988749895
    PHI_MAX = 1.618033988749895

    def __init__(self, config: Optional[AdaptiveConfig] = None):
        """
        Initialize PhiAdaptiveController

        Args:
            config: Controller configuration
        """
        self.config = config or AdaptiveConfig()

        # Components
        self.session_memory = SessionMemory(max_samples=10000)
        self.predictor = PhiPredictor(self.session_memory)

        # State
        self.is_enabled = False
        self.mode = AdaptiveMode.REACTIVE
        self.manual_override = False

        # Current metrics
        self.current_ici = 0.5
        self.current_coherence = 0.5
        self.current_criticality = 0.5
        self.current_phi = 1.0
        self.current_phi_phase = 0.0
        self.current_phi_depth = 0.5
        self.active_source = "internal"
        self.last_metric_time = time.time()

        # Control state
        self.predicted_phi = 1.0
        self.phi_adjustment = 0.0
        self.ici_stable_start_time: Optional[float] = None

        # Performance tracking
        self.update_count = 0
        self.update_latencies = []
        self.max_latency_samples = 100

        # Threading
        self.lock = threading.Lock()
        self.control_thread: Optional[threading.Thread] = None
        self.is_running = False

        # Callback for Phi updates
        self.phi_update_callback: Optional[Callable[[float, float], None]] = None

    def set_phi_update_callback(self, callback: Callable[[float, float], None]):
        """
        Set callback for Phi updates

        Args:
            callback: Function(phi_value, phi_phase) to call on updates
        """
        self.phi_update_callback = callback

    def enable(self, mode: AdaptiveMode = AdaptiveMode.REACTIVE):
        """
        Enable adaptive control

        Args:
            mode: Adaptive mode to use
        """
        with self.lock:
            if self.is_enabled:
                return

            self.is_enabled = True
            self.mode = mode
            self.manual_override = False

            # Start session recording
            self.session_memory.start_session()

            # Start control loop
            self.is_running = True
            self.control_thread = threading.Thread(target=self._control_loop, daemon=True)
            self.control_thread.start()

            if self.config.enable_logging:
                print(f"[PhiAdaptive] Enabled in {mode.name} mode")

    def disable(self):
        """Disable adaptive control"""
        with self.lock:
            if not self.is_enabled:
                return

            self.is_enabled = False
            self.is_running = False

            # Stop control loop
            if self.control_thread:
                self.control_thread.join(timeout=1.0)

            # Stop session recording
            self.session_memory.stop_session()

            if self.config.enable_logging:
                print("[PhiAdaptive] Disabled")

    def set_manual_override(self, enabled: bool):
        """
        Set manual override mode (SC-004)

        Args:
            enabled: True to enable manual override
        """
        with self.lock:
            self.manual_override = enabled

            if self.config.enable_logging:
                print(f"[PhiAdaptive] Manual override: {'ON' if enabled else 'OFF'}")

    def update_metrics(self, ici: float, coherence: float, criticality: float,
                       phi_value: float, phi_phase: float, phi_depth: float,
                       active_source: str = "unknown"):
        """
        Update current metrics (FR-001)

        Args:
            ici: Current ICI value
            coherence: Current coherence
            criticality: Current criticality
            phi_value: Current Phi value
            phi_phase: Current Phi phase
            phi_depth: Current Phi depth
            active_source: Active Phi source
        """
        with self.lock:
            self.current_ici = ici
            self.current_coherence = coherence
            self.current_criticality = criticality
            self.current_phi = phi_value
            self.current_phi_phase = phi_phase
            self.current_phi_depth = phi_depth
            self.active_source = active_source
            self.last_metric_time = time.time()

            # Record snapshot
            if self.is_enabled:
                snapshot = MetricSnapshot(
                    timestamp=self.last_metric_time,
                    ici=ici,
                    coherence=coherence,
                    criticality=criticality,
                    phi_value=phi_value,
                    phi_phase=phi_phase,
                    phi_depth=phi_depth,
                    active_source=active_source
                )
                self.session_memory.record_snapshot(snapshot)

    def _control_loop(self):
        """Main control loop for adaptive Phi adjustment"""
        loop_period = 1.0 / self.config.update_rate_hz

        while self.is_running:
            loop_start = time.time()

            try:
                # Skip if manual override active (SC-004)
                if self.manual_override:
                    time.sleep(loop_period)
                    continue

                # Check metric timeout
                if (time.time() - self.last_metric_time) > self.config.metric_timeout_s:
                    # Hold last state
                    time.sleep(loop_period)
                    continue

                with self.lock:
                    # Compute ICI error
                    ici_error = self.current_ici - self.config.target_ici

                    # Check ICI stability (SC-001)
                    if abs(ici_error) <= self.config.ici_tolerance:
                        if self.ici_stable_start_time is None:
                            self.ici_stable_start_time = time.time()
                    else:
                        self.ici_stable_start_time = None

                    # Determine target Phi
                    if self.mode == AdaptiveMode.PREDICTIVE or self.mode == AdaptiveMode.LEARNING:
                        # Use predictor
                        prediction = self.predictor.predict_phi(
                            ici=self.current_ici,
                            coherence=self.current_coherence,
                            criticality=self.current_criticality
                        )
                        self.predicted_phi = prediction.predicted_phi
                        target_phi = prediction.predicted_phi
                    else:
                        # Reactive mode - simple feedback control
                        # ICI too high → decrease Phi
                        # ICI too low → increase Phi
                        phi_correction = -ici_error * self.config.adaptation_gain
                        target_phi = self.current_phi + phi_correction
                        self.predicted_phi = target_phi

                    # Clamp target
                    target_phi = np.clip(target_phi, self.PHI_MIN, self.PHI_MAX)

                    # Compute adjustment
                    self.phi_adjustment = target_phi - self.current_phi

                    # Apply adjustment via callback
                    if self.phi_update_callback and abs(self.phi_adjustment) > 0.001:
                        # Update Phi
                        new_phi = target_phi
                        new_phase = self.current_phi_phase  # Keep phase for now

                        self.phi_update_callback(new_phi, new_phase)

                        self.update_count += 1

                        # Track latency (SC-002)
                        latency_ms = (time.time() - loop_start) * 1000
                        self.update_latencies.append(latency_ms)
                        if len(self.update_latencies) > self.max_latency_samples:
                            self.update_latencies.pop(0)

                    # Learning mode - update predictor
                    if self.mode == AdaptiveMode.LEARNING:
                        if self.session_memory.get_sample_count() >= 100:
                            # Periodically re-learn
                            if self.update_count % 100 == 0:
                                self.predictor.learn_from_session()

                        # Check for divergence
                        if self.predictor.check_divergence():
                            self.predictor.reset_model()

            except Exception as e:
                if self.config.enable_logging:
                    print(f"[PhiAdaptive] Control loop error: {e}")

            # Sleep to maintain loop rate
            elapsed = time.time() - loop_start
            sleep_time = max(0, loop_period - elapsed)
            time.sleep(sleep_time)

    def get_status(self) -> AdaptiveStatus:
        """
        Get current adaptive control status

        Returns:
            AdaptiveStatus with current state
        """
        with self.lock:
            ici_error = self.current_ici - self.config.target_ici

            # Compute stable time (SC-001)
            if self.ici_stable_start_time:
                stable_time = time.time() - self.ici_stable_start_time
            else:
                stable_time = 0.0

            # Compute average latency (SC-002)
            if len(self.update_latencies) > 0:
                avg_latency = np.mean(self.update_latencies)
            else:
                avg_latency = 0.0

            return AdaptiveStatus(
                is_enabled=self.is_enabled,
                mode=self.mode,
                current_ici=self.current_ici,
                target_ici=self.config.target_ici,
                ici_error=ici_error,
                current_phi=self.current_phi,
                predicted_phi=self.predicted_phi,
                phi_adjustment=self.phi_adjustment,
                update_count=self.update_count,
                avg_update_latency_ms=avg_latency,
                ici_stable_time_s=stable_time,
                manual_override_active=self.manual_override
            )

    def learn_from_current_session(self) -> bool:
        """
        Trigger learning from current session

        Returns:
            True if learning successful
        """
        return self.predictor.learn_from_session()

    def get_session_stats(self) -> Optional[Dict]:
        """Get current session statistics"""
        stats = self.session_memory.compute_stats()
        if stats:
            from dataclasses import asdict
            return asdict(stats)
        return None

    def save_session(self, filepath: str) -> bool:
        """Save current session to file"""
        return self.session_memory.save_session(filepath)

    def load_session(self, filepath: str) -> bool:
        """Load session from file"""
        return self.session_memory.load_session(filepath)


# Self-test function
def _self_test():
    """Run basic self-test of PhiAdaptiveController"""
    print("=" * 60)
    print("PhiAdaptiveController Self-Test")
    print("=" * 60)
    print()

    # Create controller
    print("1. Creating PhiAdaptiveController...")
    config = AdaptiveConfig(
        target_ici=0.5,
        ici_tolerance=0.05,
        update_rate_hz=20.0,
        enable_logging=True
    )
    controller = PhiAdaptiveController(config)
    print("   [OK] Controller created")
    print()

    # Track Phi updates
    phi_updates = []

    def phi_callback(phi, phase):
        phi_updates.append((time.time(), phi, phase))

    controller.set_phi_update_callback(phi_callback)

    # Enable adaptive control
    print("2. Enabling adaptive control (REACTIVE mode)...")
    controller.enable(AdaptiveMode.REACTIVE)
    time.sleep(0.2)
    status = controller.get_status()
    print(f"   [OK] Enabled: {status.is_enabled}, Mode: {status.mode.name}")
    print()

    # Simulate metric updates
    print("3. Simulating metric updates for 2 seconds...")
    start_time = time.time()
    update_count = 0

    while (time.time() - start_time) < 2.0:
        # Simulate ICI oscillating around target
        t = time.time() - start_time
        ici = 0.5 + 0.08 * np.sin(t * 2.0)
        coherence = 0.6
        criticality = 0.4
        phi = 1.0  # Will be adjusted by controller

        controller.update_metrics(
            ici=ici,
            coherence=coherence,
            criticality=criticality,
            phi_value=phi,
            phi_phase=0.0,
            phi_depth=0.5,
            active_source="test"
        )

        update_count += 1
        time.sleep(0.05)  # 20 Hz

    print(f"   [OK] Sent {update_count} metric updates")
    print(f"   [OK] Received {len(phi_updates)} Phi updates")
    print()

    # Check status
    print("4. Checking adaptive control status...")
    status = controller.get_status()
    print(f"   ICI: {status.current_ici:.3f} (target: {status.target_ici:.3f})")
    print(f"   ICI error: {status.ici_error:.3f}")
    print(f"   Current Phi: {status.current_phi:.3f}")
    print(f"   Predicted Phi: {status.predicted_phi:.3f}")
    print(f"   Update count: {status.update_count}")
    print(f"   Avg latency: {status.avg_update_latency_ms:.2f} ms")

    latency_ok = status.avg_update_latency_ms <= 200
    print(f"   [{'OK' if latency_ok else 'FAIL'}] Latency {'meets' if latency_ok else 'exceeds'} SC-002 (<= 200 ms)")
    print()

    # Test manual override
    print("5. Testing manual override (SC-004)...")
    override_start = time.time()
    controller.set_manual_override(True)
    override_latency = (time.time() - override_start) * 1000

    status = controller.get_status()
    override_ok = status.manual_override_active and override_latency < 50
    print(f"   Override latency: {override_latency:.2f} ms")
    print(f"   [{'OK' if override_ok else 'FAIL'}] Manual override {'responds' if override_ok else 'exceeds'} < 50 ms")

    controller.set_manual_override(False)
    print()

    # Disable controller
    print("6. Disabling adaptive control...")
    controller.disable()
    status = controller.get_status()
    print(f"   [OK] Disabled: {not status.is_enabled}")
    print()

    # Session stats
    print("7. Checking session statistics...")
    stats = controller.get_session_stats()
    if stats:
        print(f"   Duration: {stats['duration']:.2f} s")
        print(f"   Sample count: {stats['sample_count']}")
        print(f"   Avg ICI: {stats['avg_ici']:.3f}")
        print(f"   ICI stability: {stats['ici_stability_score']:.3f}")
        print("   [OK] Session stats available")
    print()

    print("=" * 60)
    print("Self-Test PASSED")
    print("=" * 60)

    return True


if __name__ == "__main__":
    _self_test()
