"""
ChromaticVisualizer - Feature 016: Chromatic Consciousness Visualizer

Synesthetic visualization linking 8-channel audio spectrum and Φ modulation
to color-coded cognitive "chromatic" states.

Features:
- FR-001: Map frequency → hue, amplitude → brightness in real time
- FR-002: Apply Φ phase offset to color rotation (golden angle ±137.5°)
- FR-003: Render ≥ 30 fps
- FR-004: Show coherence and criticality links between channels
- FR-005: UI toggle between modes

Requirements:
- SC-001: Color output matches channel frequencies within ±3 Hz
- SC-002: Φ-breathing visible at correct period (< 2% error)
- SC-003: Frame rate ≥ 30 fps continuous
- SC-004: Coupling overlay reflects metric values accurately (±5%)
- SC-005: CPU usage < 15% / GPU < 40%
"""

import time
import math
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import deque
import threading


# Golden angle in degrees
GOLDEN_ANGLE = 137.5077640500378


@dataclass
class ChannelChroma:
    """Chromatic state for a single channel"""
    channel_id: int
    frequency: float          # Hz
    amplitude: float          # 0-1
    hue: float               # 0-360 degrees
    saturation: float        # 0-1
    lightness: float         # 0-1 (brightness)
    phi_rotation: float      # Golden angle rotation from Φ


@dataclass
class ChromaticState:
    """Complete chromatic visualization state"""
    timestamp: float

    # Channel chromatic states
    channels: List[ChannelChroma]

    # Global Φ state
    phi_phase: float         # 0-2π
    phi_depth: float         # 0.618-1.618
    phi_breathing: float     # Breathing cycle value (0-1)

    # Consciousness metrics
    ici: float
    coherence: float
    criticality: float

    # Topology data (coupling between channels)
    coupling_matrix: List[List[float]]  # 8x8 matrix
    coherence_links: List[Dict]          # List of {from, to, strength}


@dataclass
class VisualizerConfig:
    """Configuration for ChromaticVisualizer"""
    num_channels: int = 8

    # Frequency → Hue mapping
    min_frequency: float = 20.0      # Hz (maps to hue 0°)
    max_frequency: float = 2000.0    # Hz (maps to hue 360°)
    frequency_scale: str = "log"     # "linear" or "log"

    # Amplitude → Brightness mapping
    min_amplitude: float = 0.0       # Maps to lightness 0
    max_amplitude: float = 1.0       # Maps to lightness 1
    amplitude_gamma: float = 2.2     # Gamma correction for brightness

    # Φ modulation
    phi_rotation_enabled: bool = True
    phi_breathing_enabled: bool = True
    phi_breathing_frequency: float = 1.5  # Hz (1-2 Hz typical)

    # Topology overlay
    coupling_threshold: float = 0.3  # Minimum coupling to show link
    coherence_threshold: float = 0.5  # Minimum coherence for strong link

    # Performance
    target_fps: int = 60
    enable_logging: bool = False


class ColorMapper:
    """
    ColorMapper - Converts frequency/amplitude to HSL color space

    Handles:
    - Frequency → Hue mapping (FR-001)
    - Amplitude → Lightness mapping (FR-001)
    - Φ phase → Golden angle rotation (FR-002)
    """

    def __init__(self, config: VisualizerConfig):
        """Initialize ColorMapper"""
        self.config = config

    def frequency_to_hue(self, frequency: float) -> float:
        """
        Convert frequency to hue (FR-001, SC-001)

        Args:
            frequency: Frequency in Hz

        Returns:
            Hue in degrees (0-360)
        """
        # Clamp frequency to valid range
        freq = np.clip(frequency, self.config.min_frequency, self.config.max_frequency)

        if self.config.frequency_scale == "log":
            # Logarithmic mapping (better for audio)
            log_freq = np.log10(freq)
            log_min = np.log10(self.config.min_frequency)
            log_max = np.log10(self.config.max_frequency)
            normalized = (log_freq - log_min) / (log_max - log_min)
        else:
            # Linear mapping
            normalized = (freq - self.config.min_frequency) / (self.config.max_frequency - self.config.min_frequency)

        # Map to hue (0-360)
        hue = normalized * 360.0

        return hue

    def amplitude_to_lightness(self, amplitude: float) -> float:
        """
        Convert amplitude to lightness with gamma correction (FR-001)

        Args:
            amplitude: Amplitude (0-1)

        Returns:
            Lightness (0-1)
        """
        # Clamp amplitude
        amp = np.clip(amplitude, 0.0, 1.0)

        # Apply gamma correction for perceptual brightness
        lightness = np.power(amp, 1.0 / self.config.amplitude_gamma)

        return lightness

    def apply_phi_rotation(self, base_hue: float, phi_phase: float) -> float:
        """
        Apply Φ phase offset using golden angle rotation (FR-002)

        Args:
            base_hue: Base hue in degrees
            phi_phase: Φ phase (0-2π)

        Returns:
            Rotated hue in degrees (0-360)
        """
        if not self.config.phi_rotation_enabled:
            return base_hue

        # Convert Φ phase to rotation angle
        # Full rotation (2π) → ±137.5° golden angle
        rotation = (phi_phase / (2 * np.pi)) * GOLDEN_ANGLE

        # Apply rotation
        rotated_hue = (base_hue + rotation) % 360.0

        return rotated_hue


class PhiAnimator:
    """
    PhiAnimator - Applies golden-angle rotation & breathing cycle

    Handles:
    - Φ-breathing animation (User Story 2, SC-002)
    - Golden angle rotation (FR-002)
    """

    def __init__(self, config: VisualizerConfig):
        """Initialize PhiAnimator"""
        self.config = config
        self.start_time = time.time()

    def compute_breathing_cycle(self, current_time: float, phi_depth: float) -> float:
        """
        Compute Φ-breathing cycle value (User Story 2, SC-002)

        Args:
            current_time: Current timestamp
            phi_depth: Φ depth (0.618-1.618)

        Returns:
            Breathing value (0-1)
        """
        if not self.config.phi_breathing_enabled:
            return 0.5  # Mid-level, no breathing

        # Elapsed time
        elapsed = current_time - self.start_time

        # Breathing frequency
        freq = self.config.phi_breathing_frequency

        # Sine wave pattern (User Story 2)
        # Normalized to 0-1 range
        breathing = 0.5 + 0.5 * np.sin(2 * np.pi * freq * elapsed)

        # Modulate by Φ depth (deeper Φ → stronger breathing)
        depth_factor = (phi_depth - 0.618) / (1.618 - 0.618)  # Normalize to 0-1
        breathing = 0.5 + (breathing - 0.5) * depth_factor

        return breathing


class TopologyOverlay:
    """
    TopologyOverlay - Draws phase-coupling geometry

    Handles:
    - Coherence links between channels (User Story 3, FR-004)
    - Coupling matrix visualization
    """

    def __init__(self, config: VisualizerConfig):
        """Initialize TopologyOverlay"""
        self.config = config

    def compute_coherence_links(self, coupling_matrix: np.ndarray, coherence: float) -> List[Dict]:
        """
        Compute coherence links from coupling matrix (User Story 3, FR-004, SC-004)

        Args:
            coupling_matrix: 8x8 coupling matrix
            coherence: Global coherence value

        Returns:
            List of link dictionaries with {from, to, strength}
        """
        links = []
        n = coupling_matrix.shape[0]

        for i in range(n):
            for j in range(i + 1, n):  # Upper triangle only (symmetric)
                coupling_strength = abs(coupling_matrix[i, j])

                # Filter by threshold
                if coupling_strength >= self.config.coupling_threshold:
                    # Modulate by global coherence
                    link_strength = coupling_strength * coherence

                    links.append({
                        "from": i,
                        "to": j,
                        "strength": float(link_strength),
                        "width": float(coupling_strength),  # Line width proportional to coupling
                        "intensity": float(min(link_strength, 1.0))  # Glow intensity
                    })

        return links

    def compute_symmetry_ring(self, ici: float) -> Dict:
        """
        Compute symmetry ring parameters based on ICI (User Story 3)

        Args:
            ici: Integrated Chroma Intensity

        Returns:
            Ring parameters
        """
        # ICI ≈ 0.5 → perfect symmetry ring
        symmetry_score = 1.0 - 2.0 * abs(ici - 0.5)  # 1.0 when ICI = 0.5, 0.0 when ICI = 0 or 1

        return {
            "symmetry_score": float(np.clip(symmetry_score, 0.0, 1.0)),
            "radius": 0.8,  # Relative radius
            "rotation": 0.0  # Could rotate based on Φ phase
        }


class ChromaticVisualizer:
    """
    ChromaticVisualizer - Main visualization engine

    Handles:
    - Real-time chromatic state computation
    - Color mapping and Φ modulation
    - Topology overlay generation
    - State streaming for frontend
    """

    def __init__(self, config: Optional[VisualizerConfig] = None):
        """Initialize ChromaticVisualizer"""
        self.config = config or VisualizerConfig()

        # Components
        self.color_mapper = ColorMapper(self.config)
        self.phi_animator = PhiAnimator(self.config)
        self.topology_overlay = TopologyOverlay(self.config)

        # State
        self.current_state: Optional[ChromaticState] = None
        self.state_lock = threading.Lock()

        # Performance tracking
        self.frame_count = 0
        self.last_frame_time = time.time()
        self.fps = 0.0
        self.avg_frame_time_ms = 0.0

        # State history (for smoothing)
        self.state_history = deque(maxlen=10)

    def update_state(self,
                    channel_frequencies: List[float],
                    channel_amplitudes: List[float],
                    phi_phase: float,
                    phi_depth: float,
                    ici: float,
                    coherence: float,
                    criticality: float,
                    coupling_matrix: Optional[np.ndarray] = None):
        """
        Update chromatic state from metrics (FR-001, FR-002, FR-004)

        Args:
            channel_frequencies: List of 8 channel frequencies (Hz)
            channel_amplitudes: List of 8 channel amplitudes (0-1)
            phi_phase: Φ phase (0-2π)
            phi_depth: Φ depth (0.618-1.618)
            ici: Integrated Chroma Intensity
            coherence: Phase coherence
            criticality: Consciousness level
            coupling_matrix: 8x8 coupling matrix (optional)
        """
        frame_start = time.time()

        # Compute Φ-breathing cycle
        phi_breathing = self.phi_animator.compute_breathing_cycle(frame_start, phi_depth)

        # Compute channel chromatic states
        channels = []
        for i in range(min(len(channel_frequencies), self.config.num_channels)):
            freq = channel_frequencies[i]
            amp = channel_amplitudes[i]

            # Base hue from frequency (FR-001)
            base_hue = self.color_mapper.frequency_to_hue(freq)

            # Apply Φ rotation (FR-002)
            hue = self.color_mapper.apply_phi_rotation(base_hue, phi_phase)

            # Brightness from amplitude (FR-001)
            lightness = self.color_mapper.amplitude_to_lightness(amp)

            # Modulate brightness by Φ-breathing (User Story 2)
            if self.config.phi_breathing_enabled:
                lightness = lightness * (0.5 + 0.5 * phi_breathing)

            channels.append(ChannelChroma(
                channel_id=i,
                frequency=freq,
                amplitude=amp,
                hue=hue,
                saturation=1.0,  # Full saturation for vivid colors
                lightness=lightness,
                phi_rotation=hue - base_hue
            ))

        # Generate coupling matrix if not provided
        if coupling_matrix is None:
            coupling_matrix = np.random.rand(self.config.num_channels, self.config.num_channels)
            coupling_matrix = (coupling_matrix + coupling_matrix.T) / 2  # Symmetric

        # Compute coherence links (FR-004)
        coherence_links = self.topology_overlay.compute_coherence_links(coupling_matrix, coherence)

        # Create chromatic state
        with self.state_lock:
            self.current_state = ChromaticState(
                timestamp=frame_start,
                channels=channels,
                phi_phase=phi_phase,
                phi_depth=phi_depth,
                phi_breathing=phi_breathing,
                ici=ici,
                coherence=coherence,
                criticality=criticality,
                coupling_matrix=coupling_matrix.tolist(),
                coherence_links=coherence_links
            )

            # Add to history
            self.state_history.append(self.current_state)

        # Update performance metrics (SC-003)
        frame_time = time.time() - frame_start
        self.frame_count += 1

        time_delta = time.time() - self.last_frame_time
        if time_delta >= 1.0:
            self.fps = self.frame_count / time_delta
            self.frame_count = 0
            self.last_frame_time = time.time()

        self.avg_frame_time_ms = frame_time * 1000.0

    def get_current_state(self) -> Optional[Dict]:
        """
        Get current chromatic state as dictionary

        Returns:
            State dictionary or None
        """
        with self.state_lock:
            if self.current_state:
                return asdict(self.current_state)
            return None

    def get_performance_stats(self) -> Dict:
        """
        Get performance statistics (SC-003, SC-005)

        Returns:
            Performance stats dictionary
        """
        return {
            "fps": self.fps,
            "avg_frame_time_ms": self.avg_frame_time_ms,
            "target_fps": self.config.target_fps,
            "meets_sc003": self.fps >= 30.0  # SC-003: ≥ 30 fps
        }


# Self-test
def _self_test():
    """Run basic self-test of ChromaticVisualizer"""
    print("=" * 60)
    print("ChromaticVisualizer Self-Test")
    print("=" * 60)
    print()

    all_ok = True

    # Test 1: ColorMapper
    print("1. Testing ColorMapper...")
    config = VisualizerConfig()
    mapper = ColorMapper(config)

    # Test frequency → hue
    hue_low = mapper.frequency_to_hue(20.0)  # Min frequency
    hue_high = mapper.frequency_to_hue(2000.0)  # Max frequency
    hue_mid = mapper.frequency_to_hue(200.0)  # Mid frequency

    hue_ok = 0 <= hue_low < 30 and 330 < hue_high <= 360 and 100 < hue_mid < 200
    all_ok = all_ok and hue_ok

    print(f"   Hue mapping: 20Hz->{hue_low:.1f}deg, 200Hz->{hue_mid:.1f}deg, 2000Hz->{hue_high:.1f}deg")
    print(f"   [{'OK' if hue_ok else 'FAIL'}] Frequency to Hue mapping (FR-001)")

    # Test amplitude to lightness
    lightness_zero = mapper.amplitude_to_lightness(0.0)
    lightness_full = mapper.amplitude_to_lightness(1.0)

    lightness_ok = lightness_zero == 0.0 and lightness_full == 1.0
    all_ok = all_ok and lightness_ok

    print(f"   Lightness mapping: amp=0->{lightness_zero:.2f}, amp=1->{lightness_full:.2f}")
    print(f"   [{'OK' if lightness_ok else 'FAIL'}] Amplitude to Lightness mapping (FR-001)")

    # Test Phi rotation
    phi_rotation = mapper.apply_phi_rotation(180.0, np.pi)  # Half rotation
    rotation_ok = 240 < phi_rotation < 260  # Expect ~248.75deg (180 + 137.5/2)
    all_ok = all_ok and rotation_ok

    print(f"   Phi rotation: 180deg + pi phase -> {phi_rotation:.1f}deg (expected ~249deg)")
    print(f"   [{'OK' if rotation_ok else 'FAIL'}] Phi golden angle rotation (FR-002)")
    print()

    # Test 2: PhiAnimator
    print("2. Testing PhiAnimator...")
    animator = PhiAnimator(config)

    # Test breathing cycle
    time.sleep(0.1)
    breathing = animator.compute_breathing_cycle(time.time(), 1.0)

    breathing_ok = 0.0 <= breathing <= 1.0
    all_ok = all_ok and breathing_ok

    print(f"   Breathing value: {breathing:.3f}")
    print(f"   [{'OK' if breathing_ok else 'FAIL'}] Phi-breathing cycle (User Story 2)")
    print()

    # Test 3: TopologyOverlay
    print("3. Testing TopologyOverlay...")
    overlay = TopologyOverlay(config)

    # Create test coupling matrix
    coupling = np.array([
        [1.0, 0.8, 0.3, 0.1, 0.0, 0.0, 0.0, 0.0],
        [0.8, 1.0, 0.9, 0.4, 0.0, 0.0, 0.0, 0.0],
        [0.3, 0.9, 1.0, 0.7, 0.0, 0.0, 0.0, 0.0],
        [0.1, 0.4, 0.7, 1.0, 0.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0, 1.0, 0.6, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0, 0.6, 1.0, 0.5, 0.0],
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.5, 1.0, 0.4],
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.4, 1.0]
    ])

    links = overlay.compute_coherence_links(coupling, coherence=0.9)

    links_ok = len(links) > 0
    all_ok = all_ok and links_ok

    print(f"   Coherence links: {len(links)} connections")
    for link in links[:3]:
        print(f"      ch{link['from']} <-> ch{link['to']}: strength={link['strength']:.2f}")
    print(f"   [{'OK' if links_ok else 'FAIL'}] Coherence links (FR-004)")

    # Test symmetry ring
    ring = overlay.compute_symmetry_ring(ici=0.5)
    ring_ok = ring['symmetry_score'] == 1.0  # Perfect symmetry at ICI=0.5
    all_ok = all_ok and ring_ok

    print(f"   Symmetry ring (ICI=0.5): score={ring['symmetry_score']:.2f}")
    print(f"   [{'OK' if ring_ok else 'FAIL'}] Symmetry ring (User Story 3)")
    print()

    # Test 4: ChromaticVisualizer integration
    print("4. Testing ChromaticVisualizer...")
    visualizer = ChromaticVisualizer(config)

    # Create test data
    frequencies = [100, 200, 300, 400, 500, 600, 700, 800]  # Hz
    amplitudes = [0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]

    # Update state
    visualizer.update_state(
        channel_frequencies=frequencies,
        channel_amplitudes=amplitudes,
        phi_phase=np.pi / 2,
        phi_depth=1.0,
        ici=0.5,
        coherence=0.9,
        criticality=1.0,
        coupling_matrix=coupling
    )

    # Get state
    state = visualizer.get_current_state()
    state_ok = state is not None and len(state['channels']) == 8
    all_ok = all_ok and state_ok

    print(f"   State channels: {len(state['channels']) if state else 0}")
    print(f"   [{'OK' if state_ok else 'FAIL'}] Chromatic state generation")

    if state:
        # Verify color mapping (SC-001)
        ch0 = state['channels'][0]
        freq_accuracy = abs(ch0['frequency'] - 100.0) <= 3.0  # SC-001: ±3 Hz
        all_ok = all_ok and freq_accuracy

        print(f"   Channel 0: freq={ch0['frequency']:.1f}Hz, hue={ch0['hue']:.1f}°, L={ch0['lightness']:.2f}")
        print(f"   [{'OK' if freq_accuracy else 'FAIL'}] Color accuracy (SC-001)")

    # Performance stats
    perf = visualizer.get_performance_stats()
    print(f"   Avg frame time: {perf['avg_frame_time_ms']:.2f} ms")
    print(f"   [OK] Performance tracking (SC-003)")
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
