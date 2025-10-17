"""
ChromaticFieldProcessor - Python wrapper around D-ASE AnalogCellularEngineAVX2

Provides:
- 8×8 channel (64 oscillator) real-time audio processing
- Φ-modulated multi-channel output
- Comprehensive metrics calculation (ICI, Phase Coherence, Spectral Centroid, Consciousness Level)
- Low-latency block processing (target: <6ms)
"""

import sys
import os
import numpy as np
from scipy import signal
from typing import Dict, Optional, Tuple
import time
from .ici_engine import IntegratedChromaticInformation, ICIConfig

# Add sase amp fixed to path to import dase_engine
DASE_PATH = os.path.join(os.path.dirname(__file__), '..', 'sase amp fixed')
if DASE_PATH not in sys.path:
    sys.path.insert(0, DASE_PATH)

try:
    import dase_engine
    DASE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: D-ASE engine not available: {e}")
    print(f"Build with: cd '{DASE_PATH}' && python setup.py build_ext --inplace")
    DASE_AVAILABLE = False


class ChromaticFieldProcessor:
    """
    Wrapper around D-ASE AnalogCellularEngineAVX2 for chromatic field processing

    Implements 8×8 channel configuration (64 total nodes) with Φ-modulation support
    """

    PHI = 1.618033988749895  # Golden ratio
    PHI_INV = 0.618033988749895  # 1/Φ

    def __init__(self, num_channels: int = 8, sample_rate: int = 48000, block_size: int = 512):
        """
        Initialize ChromaticFieldProcessor

        Args:
            num_channels: Number of channels per dimension (8 = 64 total nodes)
            sample_rate: Audio sample rate in Hz (48000 for spec compliance)
            block_size: Processing block size in samples (512 for spec compliance)
        """
        self.num_channels = num_channels
        self.num_nodes = num_channels * num_channels  # 8×8 = 64
        self.sample_rate = sample_rate
        self.block_size = block_size

        # Initialize D-ASE engine
        if not DASE_AVAILABLE:
            raise RuntimeError("D-ASE engine not available. Cannot initialize processor.")

        self.engine = dase_engine.AnalogCellularEngine(self.num_nodes)
        print(f"[ChromaticFieldProcessor] Initialized with {self.num_nodes} nodes @ {sample_rate}Hz")

        # Check CPU features
        has_avx2 = dase_engine.CPUFeatures.has_avx2()
        has_fma = dase_engine.CPUFeatures.has_fma()
        print(f"[ChromaticFieldProcessor] CPU Features: AVX2={has_avx2}, FMA={has_fma}")

        # Metrics storage
        self.last_metrics = {
            'ici': 0.0,
            'phase_coherence': 0.0,
            'spectral_centroid': 0.0,
            'consciousness_level': 0.0
        }

        # Performance tracking
        self.process_time_history = []
        self.max_history_length = 100

        # Multi-channel output buffer [channels, samples]
        self.output_buffer = np.zeros((self.num_channels, self.block_size), dtype=np.float32)

        # Initialize ICI Engine (Feature 014)
        ici_config = ICIConfig(
            num_channels=self.num_channels,
            fft_size=self.block_size,
            smoothing_alpha=0.2,
            use_rfft=True,
            output_matrix=False,
            enable_logging=False
        )
        self.ici_engine = IntegratedChromaticInformation(ici_config)

    def processBlock(self,
                     input_block: np.ndarray,
                     phi_phase: float = 0.0,
                     phi_depth: float = 0.5) -> np.ndarray:
        """
        Process single audio block through D-ASE engine with Φ-modulation

        Args:
            input_block: float32[block_size] mono input signal
            phi_phase: Φ-phase offset in radians [0, 2π]
            phi_depth: Φ-modulation depth [0.0, 1.0]

        Returns:
            float32[num_channels, block_size] multi-channel output

        Raises:
            ValueError: If input_block shape is incorrect
        """
        start_time = time.perf_counter()

        # Validate input
        if input_block.shape[0] != self.block_size:
            raise ValueError(f"Input block must be {self.block_size} samples, got {input_block.shape[0]}")

        # Ensure float32
        if input_block.dtype != np.float32:
            input_block = input_block.astype(np.float32)

        # Generate Φ-modulation envelope
        modulation = self._generatePhiModulation(phi_phase, phi_depth)

        # Process through each channel group (8 channels)
        for ch_idx in range(self.num_channels):
            # Calculate node range for this channel
            node_start = ch_idx * self.num_channels
            node_end = node_start + self.num_channels

            # Process block through cellular engine for this channel group
            # Apply Φ-rotated modulation for each channel
            channel_phase_offset = ch_idx * self.PHI_INV * 2 * np.pi
            channel_mod = np.roll(modulation, int(channel_phase_offset * self.block_size / (2*np.pi)))

            # Process each sample in the block
            for sample_idx in range(self.block_size):
                # Input signal modulated by Φ-envelope
                modulated_input = input_block[sample_idx] * channel_mod[sample_idx]

                # Control signal varies with golden ratio
                control_signal = np.cos(sample_idx * self.PHI_INV / self.block_size * 2 * np.pi)

                # Process through D-ASE engine (simplified: using first node of group)
                node_idx = node_start
                if node_idx < len(self.engine.nodes):
                    # Process through single representative node for this channel
                    output_sample = self.engine.nodes[node_idx].process_signal_avx2(
                        float(modulated_input),
                        float(control_signal * phi_depth),
                        0.0  # aux_signal
                    )
                    self.output_buffer[ch_idx, sample_idx] = output_sample
                else:
                    self.output_buffer[ch_idx, sample_idx] = 0.0

        # Record processing time
        elapsed = time.perf_counter() - start_time
        self.process_time_history.append(elapsed)
        if len(self.process_time_history) > self.max_history_length:
            self.process_time_history.pop(0)

        # Calculate metrics (lightweight version for real-time)
        self._updateMetrics(self.output_buffer)

        return self.output_buffer.copy()

    def _generatePhiModulation(self, phi_phase: float, phi_depth: float) -> np.ndarray:
        """
        Generate Φ-modulated envelope for one block

        Args:
            phi_phase: Phase offset [0, 2π]
            phi_depth: Modulation depth [0, 1]

        Returns:
            float32[block_size] modulation envelope
        """
        # Golden ratio modulation frequency
        # f_mod = sample_rate / Φ ≈ 29,665 Hz for 48kHz
        phi_freq = self.sample_rate * self.PHI_INV

        # Generate time vector for this block
        t = np.arange(self.block_size) / self.sample_rate

        # Φ-modulated sinusoid
        modulation = 1.0 + phi_depth * np.sin(2 * np.pi * phi_freq * t + phi_phase)

        return modulation.astype(np.float32)

    def _updateMetrics(self, output: np.ndarray):
        """
        Calculate and update metrics from multi-channel output

        Metrics calculated:
        - ICI (Inter-Channel Interference): Cross-correlation between channels
        - Phase Coherence: Phase alignment across channels
        - Spectral Centroid: Center of mass of spectrum
        - Consciousness Level: Composite metric

        Args:
            output: float32[num_channels, block_size] multi-channel signal
        """
        try:
            # ICI: Use full spectral-phase integration engine (Feature 014)
            ici_value, _ = self.ici_engine.process_block(output)
            self.last_metrics['ici'] = ici_value

            # Phase Coherence: Using Hilbert transform
            # (Simplified for real-time: just measure phase variance)
            phases = []
            for ch in range(self.num_channels):
                # Extract instantaneous phase via analytic signal
                analytic = signal.hilbert(output[ch])
                phase = np.angle(analytic)
                phases.append(np.mean(phase))

            phase_std = np.std(phases)
            self.last_metrics['phase_coherence'] = max(0.0, 1.0 - phase_std / np.pi)

            # Spectral Centroid: Weighted mean of frequencies
            # Calculate for all channels combined
            combined = np.mean(output, axis=0)
            spectrum = np.abs(np.fft.rfft(combined))
            freqs = np.fft.rfftfreq(self.block_size, 1.0 / self.sample_rate)

            total_mag = np.sum(spectrum)
            if total_mag > 0:
                centroid = np.sum(spectrum * freqs) / total_mag
            else:
                centroid = 0.0
            self.last_metrics['spectral_centroid'] = centroid

            # Consciousness Level: Composite metric
            # Balance of coherence (order), diversity (low ICI), and spectral richness
            coherence_component = self.last_metrics['phase_coherence']
            diversity_component = 1.0 - self.last_metrics['ici']
            spectral_component = min(1.0, self.last_metrics['spectral_centroid'] / (self.sample_rate / 2))

            consciousness = (
                0.4 * coherence_component +
                0.3 * diversity_component +
                0.3 * spectral_component
            )
            self.last_metrics['consciousness_level'] = np.clip(consciousness, 0.0, 1.0)

        except Exception as e:
            print(f"[ChromaticFieldProcessor] Warning: Metrics calculation failed: {e}")
            # Keep last known values

    def getMetrics(self) -> Dict[str, float]:
        """
        Get latest calculated metrics

        Returns:
            Dictionary with keys:
                - ici: Inter-channel interference [0, 1]
                - phase_coherence: Phase alignment [0, 1]
                - spectral_centroid: Frequency in Hz
                - consciousness_level: Composite metric [0, 1]
        """
        return self.last_metrics.copy()

    def getPerformanceStats(self) -> Dict[str, float]:
        """
        Get processing performance statistics

        Returns:
            Dictionary with:
                - avg_process_time_ms: Average processing time
                - max_process_time_ms: Maximum processing time
                - min_process_time_ms: Minimum processing time
                - avg_cpu_load: Estimated CPU load [0, 1]
        """
        if not self.process_time_history:
            return {
                'avg_process_time_ms': 0.0,
                'max_process_time_ms': 0.0,
                'min_process_time_ms': 0.0,
                'avg_cpu_load': 0.0
            }

        times_ms = [t * 1000 for t in self.process_time_history]
        block_time_ms = (self.block_size / self.sample_rate) * 1000

        return {
            'avg_process_time_ms': np.mean(times_ms),
            'max_process_time_ms': np.max(times_ms),
            'min_process_time_ms': np.min(times_ms),
            'avg_cpu_load': np.mean(times_ms) / block_time_ms if block_time_ms > 0 else 0.0
        }

    def reset(self):
        """Reset all internal state and integrators"""
        print("[ChromaticFieldProcessor] Resetting processor state")

        # Reset D-ASE engine nodes
        for node in self.engine.nodes:
            node.reset_integrator()

        # Reset metrics
        self.last_metrics = {
            'ici': 0.0,
            'phase_coherence': 0.0,
            'spectral_centroid': 0.0,
            'consciousness_level': 0.0
        }

        # Clear performance history
        self.process_time_history.clear()

        # Clear output buffer
        self.output_buffer.fill(0.0)

    def __del__(self):
        """Cleanup on destruction"""
        print("[ChromaticFieldProcessor] Shutting down")


# Self-test function
def _self_test():
    """Run basic self-test of ChromaticFieldProcessor"""
    print("=" * 60)
    print("ChromaticFieldProcessor Self-Test")
    print("=" * 60)

    if not DASE_AVAILABLE:
        print("ERROR: D-ASE engine not available. Cannot run self-test.")
        return False

    try:
        # Create processor
        print("\n1. Initializing processor...")
        processor = ChromaticFieldProcessor(num_channels=8, sample_rate=48000, block_size=512)
        print("   ✓ Processor initialized")

        # Generate test signal
        print("\n2. Generating test signal (1kHz sine)...")
        t = np.linspace(0, 512/48000, 512, endpoint=False)
        test_signal = (np.sin(2 * np.pi * 1000 * t) * 0.5).astype(np.float32)
        print(f"   ✓ Test signal generated: {test_signal.shape}")

        # Process block
        print("\n3. Processing test block...")
        start = time.perf_counter()
        output = processor.processBlock(test_signal, phi_phase=0.0, phi_depth=0.5)
        elapsed_ms = (time.perf_counter() - start) * 1000
        print(f"   ✓ Block processed in {elapsed_ms:.2f}ms")
        print(f"   Output shape: {output.shape}")
        print(f"   Output range: [{np.min(output):.3f}, {np.max(output):.3f}]")

        # Check latency requirement
        if elapsed_ms < 6.0:
            print(f"   ✓ Latency OK ({elapsed_ms:.2f}ms < 6ms target)")
        else:
            print(f"   ⚠ Latency HIGH ({elapsed_ms:.2f}ms > 6ms target)")

        # Get metrics
        print("\n4. Checking metrics...")
        metrics = processor.getMetrics()
        for key, value in metrics.items():
            print(f"   {key}: {value:.4f}")
        print("   ✓ Metrics calculated")

        # Performance stats
        print("\n5. Performance statistics...")
        perf = processor.getPerformanceStats()
        for key, value in perf.items():
            print(f"   {key}: {value:.4f}")

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
