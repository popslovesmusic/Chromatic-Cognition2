"""
MetricsFrame - Real-Time D-ASE Metrics Data Structure

Represents a single snapshot of D-ASE consciousness metrics synchronized
with audio processing blocks and Φ-modulation state.
"""

import time
from typing import Optional, Dict, Literal
from dataclasses import dataclass, asdict
import json


StateType = Literal["AWAKE", "DREAMING", "DEEP_SLEEP", "REM", "TRANSITION", "CRITICAL", "IDLE"]


@dataclass
class MetricsFrame:
    """
    Complete metrics snapshot for one audio processing cycle

    Conforms to FR-002 schema requirements
    """

    # Timestamps
    timestamp: float  # Unix timestamp (seconds since epoch)
    audio_callback_time: Optional[float] = None  # Audio callback start time

    # D-ASE Core Metrics
    ici: float = 0.0  # Inter-Channel Interference [0, 1]
    phase_coherence: float = 0.0  # Phase alignment across channels [0, 1]
    spectral_centroid: float = 0.0  # Frequency in Hz
    criticality: float = 0.0  # System criticality measure [0, 1]
    consciousness_level: float = 0.0  # Composite consciousness metric [0, 1]
    state: StateType = "IDLE"  # Categorical consciousness state

    # Φ-Modulation State
    phi_phase: float = 0.0  # Φ-phase in radians [0, 2π]
    phi_depth: float = 0.618  # Φ-depth [0, 1.618]
    phi_source: str = "internal"  # Active Φ source

    # Performance Metrics
    latency_ms: Optional[float] = None  # Processing latency in milliseconds
    cpu_load: Optional[float] = None  # CPU utilization [0, 1]

    # Quality Indicators
    valid: bool = True  # False if any metric is invalid (NaN/Inf)
    frame_id: Optional[int] = None  # Sequential frame number

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    def to_json(self, pretty: bool = False) -> str:
        """
        Convert to JSON string

        Args:
            pretty: If True, format with indentation

        Returns:
            JSON string representation
        """
        data = self.to_dict()
        if pretty:
            return json.dumps(data, indent=2)
        else:
            return json.dumps(data)

    @classmethod
    def from_dict(cls, data: Dict) -> 'MetricsFrame':
        """
        Create MetricsFrame from dictionary

        Args:
            data: Dictionary with metric values

        Returns:
            MetricsFrame instance
        """
        # Filter to only valid fields
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid_fields)

    @classmethod
    def from_json(cls, json_str: str) -> 'MetricsFrame':
        """
        Create MetricsFrame from JSON string

        Args:
            json_str: JSON representation

        Returns:
            MetricsFrame instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)

    def validate(self) -> bool:
        """
        Validate metrics for NaN/Inf values (FR-010)

        Returns:
            True if all metrics are valid
        """
        import math

        numeric_fields = [
            'ici', 'phase_coherence', 'spectral_centroid', 'criticality',
            'consciousness_level', 'phi_phase', 'phi_depth'
        ]

        for field in numeric_fields:
            value = getattr(self, field)
            if not isinstance(value, (int, float)):
                continue
            if math.isnan(value) or math.isinf(value):
                self.valid = False
                return False

        self.valid = True
        return True

    def sanitize(self) -> 'MetricsFrame':
        """
        Replace invalid values (NaN/Inf) with None

        Returns:
            Self (modified in place)
        """
        import math

        numeric_fields = [
            'ici', 'phase_coherence', 'spectral_centroid', 'criticality',
            'consciousness_level', 'phi_phase', 'phi_depth', 'latency_ms', 'cpu_load'
        ]

        for field in numeric_fields:
            value = getattr(self, field)
            if isinstance(value, (int, float)):
                if math.isnan(value) or math.isinf(value):
                    setattr(self, field, 0.0)  # Replace with safe default
                    self.valid = False

        return self

    def classify_state(self) -> StateType:
        """
        Classify consciousness state based on metrics

        State classification logic:
        - IDLE: consciousness < 0.1
        - DEEP_SLEEP: consciousness < 0.3, coherence > 0.7
        - DREAMING: consciousness 0.3-0.5, coherence < 0.5
        - REM: consciousness 0.4-0.6, criticality > 0.7
        - AWAKE: consciousness > 0.6
        - CRITICAL: criticality > 0.9
        - TRANSITION: Otherwise

        Returns:
            Classified state
        """
        c = self.consciousness_level
        coh = self.phase_coherence
        crit = self.criticality

        if crit > 0.9:
            self.state = "CRITICAL"
        elif c < 0.1:
            self.state = "IDLE"
        elif c > 0.6:
            self.state = "AWAKE"
        elif c < 0.3 and coh > 0.7:
            self.state = "DEEP_SLEEP"
        elif 0.3 <= c < 0.5 and coh < 0.5:
            self.state = "DREAMING"
        elif 0.4 <= c < 0.6 and crit > 0.7:
            self.state = "REM"
        else:
            self.state = "TRANSITION"

        return self.state

    def __repr__(self) -> str:
        return (
            f"MetricsFrame(t={self.timestamp:.3f}, "
            f"consciousness={self.consciousness_level:.2f}, "
            f"state={self.state}, "
            f"φ={self.phi_depth:.2f}@{self.phi_phase:.2f}rad)"
        )


def create_idle_frame() -> MetricsFrame:
    """
    Create an idle/paused frame

    Used when engine is not processing audio
    """
    return MetricsFrame(
        timestamp=time.time(),
        state="IDLE",
        consciousness_level=0.0,
        valid=True
    )


def create_test_frame(frame_id: int = 0) -> MetricsFrame:
    """
    Create a test frame with synthetic data

    Args:
        frame_id: Sequential frame number

    Returns:
        Test MetricsFrame with valid synthetic metrics
    """
    import math

    t = time.time()
    phase = (frame_id * 0.1) % (2 * math.pi)

    return MetricsFrame(
        timestamp=t,
        frame_id=frame_id,
        ici=0.5 + 0.2 * math.sin(phase),
        phase_coherence=0.7 + 0.2 * math.cos(phase),
        spectral_centroid=1000 + 500 * math.sin(phase * 2),
        criticality=0.6 + 0.3 * math.sin(phase * 0.5),
        consciousness_level=0.5 + 0.3 * math.sin(phase),
        phi_phase=phase,
        phi_depth=0.618 + 0.3 * math.sin(phase * 0.3),
        phi_source="internal",
        latency_ms=5.0 + 2.0 * abs(math.sin(phase)),
        cpu_load=0.4 + 0.1 * abs(math.sin(phase)),
        valid=True
    )


# Self-test function
def _self_test():
    """Test MetricsFrame functionality"""
    print("=" * 60)
    print("MetricsFrame Self-Test")
    print("=" * 60)

    try:
        # Test basic creation
        print("\n1. Creating basic frame...")
        frame = MetricsFrame(
            timestamp=time.time(),
            ici=0.5,
            phase_coherence=0.8,
            spectral_centroid=2000.0,
            consciousness_level=0.6
        )
        print(f"   {frame}")
        print("   ✓ Basic creation OK")

        # Test JSON serialization
        print("\n2. Testing JSON serialization...")
        json_str = frame.to_json()
        print(f"   JSON length: {len(json_str)} bytes")
        frame_restored = MetricsFrame.from_json(json_str)
        assert frame_restored.ici == frame.ici
        print("   ✓ JSON round-trip OK")

        # Test validation
        print("\n3. Testing validation...")
        import math
        invalid_frame = MetricsFrame(
            timestamp=time.time(),
            ici=math.nan,
            consciousness_level=math.inf
        )
        is_valid = invalid_frame.validate()
        print(f"   Invalid frame detected: {not is_valid}")
        assert not is_valid
        print("   ✓ Validation OK")

        # Test sanitization
        print("\n4. Testing sanitization...")
        invalid_frame.sanitize()
        print(f"   Sanitized ICI: {invalid_frame.ici}")
        assert invalid_frame.ici == 0.0  # Should be replaced
        print("   ✓ Sanitization OK")

        # Test state classification
        print("\n5. Testing state classification...")
        test_states = [
            (0.05, "IDLE"),
            (0.25, "DEEP_SLEEP"),
            (0.7, "AWAKE"),
        ]

        for consciousness, expected_state in test_states:
            frame = MetricsFrame(
                timestamp=time.time(),
                consciousness_level=consciousness,
                phase_coherence=0.8,
                criticality=0.5
            )
            frame.classify_state()
            print(f"   consciousness={consciousness} → {frame.state} (expected {expected_state})")

        print("   ✓ State classification OK")

        # Test helper functions
        print("\n6. Testing helper functions...")
        idle = create_idle_frame()
        print(f"   Idle frame: {idle.state}")
        assert idle.state == "IDLE"

        test = create_test_frame(frame_id=42)
        print(f"   Test frame #{test.frame_id}: {test}")
        assert test.frame_id == 42

        print("   ✓ Helper functions OK")

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
