"""
LatencyFrame - Latency Telemetry Data Structure

Implements data container for latency measurements, drift tracking, and compensation state
"""

import time
from typing import Optional, Dict
from dataclasses import dataclass, asdict
import json


@dataclass
class LatencyFrame:
    """
    Complete latency state snapshot

    Holds:
    - Measured latency components (hardware, engine, OS)
    - Computed total and compensation offset
    - Drift metrics
    - Timestamps for synchronization
    """

    # Timestamps (monotonic time in seconds)
    timestamp: float  # When this frame was created
    audio_callback_time: Optional[float] = None  # Audio callback start time

    # Latency components (milliseconds)
    hw_input_latency_ms: float = 0.0  # Hardware input buffer latency
    hw_output_latency_ms: float = 0.0  # Hardware output buffer latency
    engine_latency_ms: float = 0.0  # D-ASE processing latency
    os_latency_ms: float = 0.0  # OS/driver latency
    total_measured_ms: float = 0.0  # Round-trip measured latency

    # Compensation
    compensation_offset_ms: float = 0.0  # Applied compensation offset
    manual_offset_ms: float = 0.0  # User manual adjustment

    # Drift tracking
    drift_ms: float = 0.0  # Cumulative drift from expected timing
    drift_rate_ms_per_sec: float = 0.0  # Rate of drift accumulation

    # Calibration state
    calibrated: bool = False  # True if calibration has been performed
    calibration_quality: float = 0.0  # 0-1, based on variance
    last_calibration_time: Optional[float] = None

    # Buffer state
    buffer_size_samples: int = 512  # Current audio buffer size
    sample_rate: int = 48000  # Sample rate
    buffer_fullness: float = 0.0  # 0-1, current buffer utilization

    # Performance
    cpu_load: float = 0.0  # 0-1, current CPU utilization

    def compute_total(self):
        """
        Compute total latency from components (FR-002)

        L_total = L_hw_in + L_hw_out + L_engine + L_os
        """
        self.total_measured_ms = (
            self.hw_input_latency_ms +
            self.hw_output_latency_ms +
            self.engine_latency_ms +
            self.os_latency_ms
        )

    def get_effective_latency(self) -> float:
        """
        Get effective latency after compensation

        Returns:
            Effective latency in milliseconds
        """
        return self.total_measured_ms - self.compensation_offset_ms - self.manual_offset_ms

    def is_aligned(self, tolerance_ms: float = 5.0) -> bool:
        """
        Check if latency is within alignment tolerance (SC-002)

        Args:
            tolerance_ms: Acceptable alignment error (default: 5ms)

        Returns:
            True if effective latency is within tolerance
        """
        effective = self.get_effective_latency()
        return abs(effective) <= tolerance_ms

    def get_buffer_latency_ms(self) -> float:
        """
        Calculate theoretical buffer latency from size and sample rate

        Returns:
            Buffer latency in milliseconds
        """
        if self.sample_rate > 0:
            return (self.buffer_size_samples / self.sample_rate) * 1000.0
        return 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    def to_json(self, pretty: bool = False) -> str:
        """
        Convert to JSON string

        Args:
            pretty: If True, format with indentation

        Returns:
            JSON string
        """
        data = self.to_dict()
        if pretty:
            return json.dumps(data, indent=2)
        else:
            return json.dumps(data)

    @classmethod
    def from_dict(cls, data: Dict) -> 'LatencyFrame':
        """Create LatencyFrame from dictionary"""
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid_fields)

    @classmethod
    def from_json(cls, json_str: str) -> 'LatencyFrame':
        """Create LatencyFrame from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def __repr__(self) -> str:
        return (
            f"LatencyFrame(total={self.total_measured_ms:.1f}ms, "
            f"offset={self.compensation_offset_ms:.1f}ms, "
            f"drift={self.drift_ms:.2f}ms, "
            f"calibrated={self.calibrated})"
        )


def create_default_latency_frame() -> LatencyFrame:
    """
    Create a default latency frame with typical values

    Returns:
        LatencyFrame with reasonable defaults
    """
    return LatencyFrame(
        timestamp=time.time(),
        hw_input_latency_ms=5.0,  # Typical input buffer
        hw_output_latency_ms=5.0,  # Typical output buffer
        engine_latency_ms=2.0,  # D-ASE processing
        os_latency_ms=1.0,  # OS overhead
        buffer_size_samples=512,
        sample_rate=48000
    )


# Self-test function
def _self_test():
    """Test LatencyFrame functionality"""
    print("=" * 60)
    print("LatencyFrame Self-Test")
    print("=" * 60)

    try:
        # Test basic creation
        print("\n1. Creating latency frame...")
        frame = create_default_latency_frame()
        print(f"   {frame}")
        print("   ✓ Creation OK")

        # Test total computation
        print("\n2. Testing total computation...")
        frame.compute_total()
        print(f"   Computed total: {frame.total_measured_ms:.1f}ms")
        expected = frame.hw_input_latency_ms + frame.hw_output_latency_ms + frame.engine_latency_ms + frame.os_latency_ms
        assert abs(frame.total_measured_ms - expected) < 0.01
        print("   ✓ Total computation OK")

        # Test effective latency
        print("\n3. Testing effective latency...")
        frame.compensation_offset_ms = 5.0
        frame.manual_offset_ms = 2.0
        effective = frame.get_effective_latency()
        print(f"   Effective latency: {effective:.1f}ms")
        print(f"   (total {frame.total_measured_ms:.1f}ms - compensation {frame.compensation_offset_ms:.1f}ms - manual {frame.manual_offset_ms:.1f}ms)")
        print("   ✓ Effective latency OK")

        # Test alignment check
        print("\n4. Testing alignment check...")
        frame.compensation_offset_ms = frame.total_measured_ms - 2.0  # 2ms effective
        is_aligned = frame.is_aligned(tolerance_ms=5.0)
        print(f"   Aligned (tolerance=5ms): {is_aligned}")
        assert is_aligned
        print("   ✓ Alignment check OK")

        # Test buffer latency calculation
        print("\n5. Testing buffer latency calculation...")
        buffer_latency = frame.get_buffer_latency_ms()
        expected_buffer = (512 / 48000) * 1000  # ~10.67ms
        print(f"   Buffer latency: {buffer_latency:.2f}ms (expected: {expected_buffer:.2f}ms)")
        assert abs(buffer_latency - expected_buffer) < 0.1
        print("   ✓ Buffer latency OK")

        # Test JSON serialization
        print("\n6. Testing JSON serialization...")
        json_str = frame.to_json()
        frame_restored = LatencyFrame.from_json(json_str)
        assert frame_restored.total_measured_ms == frame.total_measured_ms
        assert frame_restored.buffer_size_samples == frame.buffer_size_samples
        print(f"   JSON length: {len(json_str)} bytes")
        print("   ✓ JSON round-trip OK")

        # Test drift scenarios
        print("\n7. Testing drift scenarios...")
        frame.drift_ms = 3.5
        frame.drift_rate_ms_per_sec = 0.2
        print(f"   Drift: {frame.drift_ms:.2f}ms @ {frame.drift_rate_ms_per_sec:.2f}ms/s")
        print("   ✓ Drift tracking OK")

        print("\n" + "=" * 60)
        print("Self-Test PASSED ✓")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n✗ Self-Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    _self_test()
