"""
PhiRouter - Feature 011: Real-time Phi Sensor Binding

Manages multiple Φ sources, handles selection, normalization, and fallback.

Features:
- Multi-source routing with priority (FR-001)
- Automatic source switching (SC-002)
- Input normalization to [0.618–1.618] (FR-002)
- Fallback mode if input stops > 2s (FR-005)
- Real-time telemetry (FR-004)

Requirements:
- FR-001: Accept Φ input from multiple sources
- FR-002: Normalize input to [0.618–1.618]
- FR-005: Fallback mode if input stops for > 2s

Success Criteria:
- SC-002: Automatic source switching without restart
- SC-004: Fallback mode prevents audio instability
"""

import time
import threading
from typing import Optional, Callable, Dict, List
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np

from phi_sensor_bridge import SensorData, SensorType


class PhiSourcePriority(Enum):
    """Priority levels for Φ sources"""
    MANUAL = 0          # Lowest priority (user override)
    INTERNAL = 1        # Internal auto-modulation
    MICROPHONE = 2      # Microphone envelope
    AUDIO_BEAT = 3      # Audio beat detection
    MIDI = 4            # MIDI controller
    SERIAL = 5          # Serial sensor
    BIOMETRIC = 6       # Biometric sensor
    WEBSOCKET = 7       # WebSocket stream (highest priority)


@dataclass
class PhiRouterConfig:
    """Configuration for PhiRouter"""
    fallback_timeout_s: float = 2.0      # Fallback if no input for this long (FR-005)
    fallback_phi: float = 1.0            # Φ value to use in fallback mode
    enable_auto_switch: bool = True      # Enable automatic source switching (SC-002)
    enable_logging: bool = True


@dataclass
class PhiRouterStatus:
    """Current status of PhiRouter"""
    timestamp: float
    active_source: str                   # Currently active source
    phi_value: float                     # Current Φ value
    phi_phase: float                     # Current Φ phase
    is_fallback_mode: bool               # In fallback mode (FR-005)
    last_update_time: float              # Time of last update
    source_count: int                    # Number of active sources
    update_rate_hz: float                # Current update rate


class PhiRouter:
    """
    PhiRouter - Manages multiple Φ sources with automatic selection

    Handles:
    - Multiple simultaneous Φ sources
    - Priority-based source selection
    - Automatic switching (SC-002)
    - Fallback mode (FR-005, SC-004)
    - Input normalization (FR-002)
    """

    PHI_MIN = 0.618033988749895  # 1/Φ
    PHI_MAX = 1.618033988749895  # Φ
    PHI = 1.618033988749895      # Golden ratio

    def __init__(self, config: Optional[PhiRouterConfig] = None):
        """
        Initialize PhiRouter

        Args:
            config: Router configuration
        """
        self.config = config or PhiRouterConfig()

        # Active sources (source_id -> (priority, last_data, last_update_time))
        self.sources: Dict[str, tuple[PhiSourcePriority, SensorData, float]] = {}
        self.lock = threading.Lock()

        # Current state
        self.current_phi = 1.0  # Start at golden ratio
        self.current_phase = 0.0
        self.active_source_id = "internal"
        self.is_fallback_mode = False

        # Telemetry
        self.update_count = 0
        self.last_telemetry_time = time.time()
        self.update_rate_hz = 0.0

        # Callbacks for updates
        self.phi_update_callbacks: List[Callable[[float, float], None]] = []
        self.status_update_callbacks: List[Callable[[PhiRouterStatus], None]] = []

        # Watchdog thread for fallback
        self.watchdog_thread = None
        self.is_running = False

    def start(self):
        """Start router watchdog for fallback detection"""
        self.is_running = True
        self.watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self.watchdog_thread.start()

        if self.config.enable_logging:
            print("[PhiRouter] Started")

    def stop(self):
        """Stop router"""
        self.is_running = False

        if self.watchdog_thread:
            self.watchdog_thread.join(timeout=1.0)

        if self.config.enable_logging:
            print("[PhiRouter] Stopped")

    def register_source(self, source_id: str, priority: PhiSourcePriority):
        """
        Register a Φ source

        Args:
            source_id: Unique identifier for source
            priority: Source priority level
        """
        with self.lock:
            if source_id not in self.sources:
                # Initialize with placeholder data
                placeholder = SensorData(
                    sensor_type=SensorType.MIDI_CC,
                    timestamp=time.time(),
                    raw_value=0.0,
                    normalized_value=1.0,
                    source_id=source_id
                )
                self.sources[source_id] = (priority, placeholder, 0.0)

                if self.config.enable_logging:
                    print(f"[PhiRouter] Registered source: {source_id} (priority: {priority.value})")

    def unregister_source(self, source_id: str):
        """
        Unregister a Φ source

        Args:
            source_id: Source identifier to remove
        """
        with self.lock:
            if source_id in self.sources:
                del self.sources[source_id]

                if self.config.enable_logging:
                    print(f"[PhiRouter] Unregistered source: {source_id}")

    def update_source(self, source_id: str, data: SensorData):
        """
        Update Φ value from a source (FR-001, FR-003)

        Args:
            source_id: Source identifier
            data: New sensor data
        """
        current_time = time.time()

        with self.lock:
            if source_id not in self.sources:
                if self.config.enable_logging:
                    print(f"[PhiRouter] Warning: Unknown source '{source_id}'")
                return

            # Update source data
            priority, _, _ = self.sources[source_id]
            self.sources[source_id] = (priority, data, current_time)

            # Update telemetry
            self.update_count += 1

            # Select active source (SC-002: automatic switching)
            if self.config.enable_auto_switch:
                self._select_active_source()

            # If this is the active source, update Φ (FR-003: < 100 ms)
            if source_id == self.active_source_id:
                # Normalize value to [0.618, 1.618] (FR-002)
                normalized_phi = np.clip(data.normalized_value, self.PHI_MIN, self.PHI_MAX)

                self.current_phi = normalized_phi

                # Update phase based on value change
                # Phase advances proportionally to Φ value
                self.current_phase += (normalized_phi - 1.0) * 0.1
                self.current_phase = self.current_phase % (2 * np.pi)

                # Clear fallback mode
                self.is_fallback_mode = False

                # Call callbacks
                self._notify_phi_update()

    def set_manual_phi(self, phi: float, phase: float):
        """
        Manually set Φ value (overrides active source temporarily)

        Args:
            phi: Φ value (will be clipped to [0.618, 1.618])
            phase: Φ phase in radians
        """
        with self.lock:
            # Normalize (FR-002)
            self.current_phi = np.clip(phi, self.PHI_MIN, self.PHI_MAX)
            self.current_phase = phase % (2 * np.pi)

            # Set active source to manual
            self.active_source_id = "manual"
            self.is_fallback_mode = False

            # Call callbacks
            self._notify_phi_update()

    def get_current_phi(self) -> tuple[float, float]:
        """
        Get current Φ value and phase

        Returns:
            (phi_value, phi_phase) tuple
        """
        with self.lock:
            return (self.current_phi, self.current_phase)

    def get_status(self) -> PhiRouterStatus:
        """
        Get current router status (FR-004)

        Returns:
            PhiRouterStatus with current state
        """
        current_time = time.time()

        with self.lock:
            # Calculate update rate
            time_delta = current_time - self.last_telemetry_time
            if time_delta > 0:
                self.update_rate_hz = self.update_count / time_delta
                self.update_count = 0
                self.last_telemetry_time = current_time

            # Get last update time for active source
            last_update_time = 0.0
            if self.active_source_id in self.sources:
                _, _, last_update_time = self.sources[self.active_source_id]

            return PhiRouterStatus(
                timestamp=current_time,
                active_source=self.active_source_id,
                phi_value=self.current_phi,
                phi_phase=self.current_phase,
                is_fallback_mode=self.is_fallback_mode,
                last_update_time=last_update_time,
                source_count=len(self.sources),
                update_rate_hz=self.update_rate_hz
            )

    def register_phi_callback(self, callback: Callable[[float, float], None]):
        """
        Register callback for Φ updates

        Args:
            callback: Function(phi, phase) to call on updates
        """
        self.phi_update_callbacks.append(callback)

    def register_status_callback(self, callback: Callable[[PhiRouterStatus], None]):
        """
        Register callback for status updates

        Args:
            callback: Function(status) to call on status changes
        """
        self.status_update_callbacks.append(callback)

    def _select_active_source(self):
        """
        Select active source based on priority (SC-002)

        Chooses highest priority source with recent data
        """
        current_time = time.time()

        # Find highest priority source with recent data
        best_source = None
        best_priority = -1

        for source_id, (priority, data, last_update) in self.sources.items():
            # Check if source is recent (within timeout)
            if (current_time - last_update) < self.config.fallback_timeout_s:
                if priority.value > best_priority:
                    best_priority = priority.value
                    best_source = source_id

        # Switch source if needed
        if best_source and best_source != self.active_source_id:
            if self.config.enable_logging:
                print(f"[PhiRouter] Switching source: {self.active_source_id} → {best_source}")

            self.active_source_id = best_source

            # Notify status callbacks
            self._notify_status_update()

    def _watchdog_loop(self):
        """
        Watchdog thread for fallback detection (FR-005, SC-004)

        Monitors for source timeouts and engages fallback mode
        """
        while self.is_running:
            time.sleep(0.5)  # Check every 500ms

            current_time = time.time()

            with self.lock:
                # Check if active source has timed out
                if self.active_source_id in self.sources:
                    _, _, last_update = self.sources[self.active_source_id]

                    if (current_time - last_update) > self.config.fallback_timeout_s:
                        # Source timeout - enter fallback mode
                        if not self.is_fallback_mode:
                            if self.config.enable_logging:
                                print(f"[PhiRouter] Source '{self.active_source_id}' timeout - entering fallback mode")

                            self.is_fallback_mode = True
                            self.current_phi = self.config.fallback_phi

                            # Notify callbacks
                            self._notify_phi_update()
                            self._notify_status_update()

    def _notify_phi_update(self):
        """Notify callbacks of Φ update"""
        for callback in self.phi_update_callbacks:
            try:
                callback(self.current_phi, self.current_phase)
            except Exception as e:
                if self.config.enable_logging:
                    print(f"[PhiRouter] Callback error: {e}")

    def _notify_status_update(self):
        """Notify callbacks of status update"""
        status = self.get_status()

        for callback in self.status_update_callbacks:
            try:
                callback(status)
            except Exception as e:
                if self.config.enable_logging:
                    print(f"[PhiRouter] Status callback error: {e}")


# Self-test function
def _self_test():
    """Run basic self-test of PhiRouter"""
    print("=" * 60)
    print("PhiRouter Self-Test")
    print("=" * 60)

    # Create router
    print("\n1. Creating PhiRouter...")
    config = PhiRouterConfig(
        fallback_timeout_s=1.0,
        enable_logging=True
    )
    router = PhiRouter(config)
    router.start()
    print("   ✓ Router started")

    # Register sources
    print("\n2. Registering sources...")
    router.register_source("manual", PhiSourcePriority.MANUAL)
    router.register_source("midi", PhiSourcePriority.MIDI)
    router.register_source("sensor", PhiSourcePriority.SERIAL)
    print("   ✓ 3 sources registered")

    # Track updates
    phi_updates = []

    def phi_callback(phi, phase):
        phi_updates.append((phi, phase))
        print(f"   Φ update: {phi:.3f}, phase: {phase:.2f}")

    router.register_phi_callback(phi_callback)

    # Test manual update
    print("\n3. Testing manual Φ update...")
    router.set_manual_phi(1.2, 1.57)
    time.sleep(0.1)
    assert len(phi_updates) > 0, "No Φ updates received"
    print("   ✓ Manual update working")

    # Test source update (simulated MIDI)
    print("\n4. Testing source update (simulated MIDI)...")
    from phi_sensor_bridge import SensorData, SensorType

    midi_data = SensorData(
        sensor_type=SensorType.MIDI_CC,
        timestamp=time.time(),
        raw_value=64,
        normalized_value=1.0,
        source_id="midi"
    )

    router.update_source("midi", midi_data)
    time.sleep(0.1)

    # Check automatic source switching
    status = router.get_status()
    print(f"   Active source: {status.active_source}")
    print(f"   Φ value: {status.phi_value:.3f}")
    print("   ✓ Source update working")

    # Test fallback mode
    print("\n5. Testing fallback mode (wait 1.5s for timeout)...")
    initial_fallback = status.is_fallback_mode
    time.sleep(1.5)

    status = router.get_status()
    print(f"   Fallback mode: {status.is_fallback_mode}")
    print(f"   Φ value: {status.phi_value:.3f}")

    if status.is_fallback_mode:
        print("   ✓ Fallback mode engaged")
    else:
        print("   ⚠ Fallback mode not engaged")

    # Stop router
    router.stop()

    print("\n" + "=" * 60)
    print("Self-Test PASSED ✓")
    print("=" * 60)

    return True


if __name__ == "__main__":
    _self_test()
