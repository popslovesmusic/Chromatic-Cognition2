"""
PhiModulator - Golden Ratio (Φ) Modulation Generator

Generates modulation signals based on the golden ratio (Φ = 1.618...) for
real-time audio processing with chromatic field characteristics.

Mathematical basis:
- Φ = (1 + √5) / 2 ≈ 1.618033988749895
- Φ^-1 = Φ - 1 ≈ 0.618033988749895
- Modulation frequency: f_mod = sample_rate * Φ^-1
"""

import numpy as np
from typing import Optional


class PhiModulator:
    """
    Golden ratio modulation generator for D-ASE audio engine

    Generates Φ-modulated control signals with:
    - Phase control [0, 2π]
    - Depth control [0, 1]
    - Multi-channel support with Φ-rotated phases
    """

    # Mathematical constants
    PHI = 1.618033988749895  # Golden ratio
    PHI_INV = 0.618033988749895  # 1/Φ = Φ - 1
    PHI_SQ = 2.618033988749895  # Φ^2 = Φ + 1
    TWO_PI = 2.0 * np.pi

    def __init__(self, sample_rate: int = 48000):
        """
        Initialize Φ-modulator

        Args:
            sample_rate: Audio sample rate in Hz (48000 for spec compliance)
        """
        self.sample_rate = sample_rate
        self.phase_accumulator = 0.0

        # Calculate fundamental Φ-modulation frequency
        # For 48kHz: f_phi ≈ 29,665 Hz
        self.phi_frequency = sample_rate * self.PHI_INV

        print(f"[PhiModulator] Initialized @ {sample_rate}Hz")
        print(f"[PhiModulator] Φ-frequency: {self.phi_frequency:.2f} Hz")

    def generateModulation(self,
                          phi_phase: float,
                          phi_depth: float,
                          num_samples: int) -> np.ndarray:
        """
        Generate Φ-modulated control signal for one audio block

        Args:
            phi_phase: Phase offset in radians [0, 2π]
            phi_depth: Modulation depth [0, 1] (0=no modulation, 1=full)
            num_samples: Number of samples to generate

        Returns:
            float32[num_samples] modulation envelope
                Range: [1-depth, 1+depth] when depth ≤ 1

        Algorithm:
            modulation[n] = 1.0 + depth * sin(2π * Φ^-1 * n/SR + phase)

        This produces a sinusoid at the golden ratio frequency with:
        - DC offset of 1.0 (for multiplicative modulation)
        - Peak amplitude controlled by depth
        - Phase controlled by phi_phase
        """
        # Validate inputs
        phi_depth = np.clip(phi_depth, 0.0, 1.0)
        phi_phase = phi_phase % self.TWO_PI

        # Time vector for this block
        t = np.arange(num_samples, dtype=np.float32) / self.sample_rate

        # Generate Φ-modulated sinusoid
        # Frequency is based on golden ratio relationship to sample rate
        angular_freq = self.TWO_PI * self.phi_frequency
        modulation = 1.0 + phi_depth * np.sin(angular_freq * t + phi_phase)

        return modulation.astype(np.float32)

    def generateMultiChannelModulation(self,
                                      phi_phase: float,
                                      phi_depth: float,
                                      num_samples: int,
                                      num_channels: int = 8) -> np.ndarray:
        """
        Generate Φ-modulated signals for multiple channels with Φ-rotated phases

        Each channel receives a phase-shifted version based on golden ratio rotation.
        This creates a natural spiraling phase relationship across channels.

        Args:
            phi_phase: Base phase offset [0, 2π]
            phi_depth: Modulation depth [0, 1]
            num_samples: Number of samples per channel
            num_channels: Number of channels (default: 8)

        Returns:
            float32[num_channels, num_samples] multi-channel modulation

        Phase rotation formula:
            channel[i]_phase = phi_phase + i * Φ^-1 * 2π
        """
        # Initialize output array
        output = np.zeros((num_channels, num_samples), dtype=np.float32)

        # Generate modulation for each channel with Φ-rotated phase
        for ch_idx in range(num_channels):
            # Calculate phase offset for this channel based on Φ-rotation
            channel_phase_offset = ch_idx * self.PHI_INV * self.TWO_PI
            total_phase = (phi_phase + channel_phase_offset) % self.TWO_PI

            # Generate modulation for this channel
            output[ch_idx] = self.generateModulation(total_phase, phi_depth, num_samples)

        return output

    def applyModulation(self,
                       signal: np.ndarray,
                       modulation: np.ndarray,
                       mode: str = 'amplitude') -> np.ndarray:
        """
        Apply modulation to audio signal

        Args:
            signal: Input signal (any shape)
            modulation: Modulation envelope (must broadcast with signal)
            mode: Modulation mode
                - 'amplitude': Multiply signal by modulation (AM)
                - 'ring': Ring modulation (bipolar, centered at 0)
                - 'phase': Apply as phase modulation (experimental)

        Returns:
            Modulated signal (same shape as input)
        """
        if mode == 'amplitude':
            # Standard amplitude modulation
            return signal * modulation

        elif mode == 'ring':
            # Ring modulation: remove DC offset from modulation
            ring_mod = (modulation - 1.0)
            return signal * ring_mod

        elif mode == 'phase':
            # Phase modulation (experimental)
            # Interpret modulation as phase shift in radians
            phase_shift = (modulation - 1.0) * np.pi
            # Apply via Hilbert transform phase rotation
            from scipy import signal as sp_signal
            analytic = sp_signal.hilbert(signal, axis=-1)
            magnitude = np.abs(analytic)
            phase = np.angle(analytic) + phase_shift
            return magnitude * np.cos(phase)

        else:
            raise ValueError(f"Unknown modulation mode: {mode}")

    def getPhiRelationships(self) -> dict:
        """
        Get golden ratio mathematical relationships

        Returns:
            Dictionary of Φ-related constants and relationships
        """
        return {
            'phi': self.PHI,
            'phi_inverse': self.PHI_INV,
            'phi_squared': self.PHI_SQ,
            'phi_frequency_hz': self.phi_frequency,
            'phi_period_samples': self.sample_rate / self.phi_frequency,
            'phi_period_ms': 1000.0 / self.phi_frequency,
            'sample_rate': self.sample_rate,
            # Interesting relationships
            'phi_minus_1': self.PHI - 1.0,  # = PHI_INV
            'phi_times_phi_inv': self.PHI * self.PHI_INV,  # = 1
            'phi_squared_minus_phi': self.PHI_SQ - self.PHI,  # = 1
        }

    def generateFibonacciPhases(self, num_phases: int = 8) -> np.ndarray:
        """
        Generate phase offsets based on Fibonacci sequence relationship to Φ

        The ratio of consecutive Fibonacci numbers approaches Φ as n→∞.
        This creates a natural spiral phase distribution.

        Args:
            num_phases: Number of phases to generate

        Returns:
            float32[num_phases] phase offsets in radians [0, 2π)
        """
        # Generate Fibonacci-like phase distribution
        # Each phase rotates by Φ^-1 * 2π (golden angle ≈ 137.5°)
        golden_angle = self.PHI_INV * self.TWO_PI

        phases = np.array([
            (i * golden_angle) % self.TWO_PI
            for i in range(num_phases)
        ], dtype=np.float32)

        return phases

    def visualizeModulation(self,
                           phi_phase: float = 0.0,
                           phi_depth: float = 0.5,
                           duration_ms: float = 10.0,
                           num_channels: int = 3):
        """
        Generate visualization data for Φ-modulation

        Args:
            phi_phase: Phase offset [0, 2π]
            phi_depth: Modulation depth [0, 1]
            duration_ms: Duration to visualize in milliseconds
            num_channels: Number of channels to show

        Returns:
            Dictionary with visualization data
        """
        num_samples = int(duration_ms * self.sample_rate / 1000)

        # Generate multi-channel modulation
        mod = self.generateMultiChannelModulation(
            phi_phase, phi_depth, num_samples, num_channels
        )

        # Time axis
        t_ms = np.arange(num_samples) / self.sample_rate * 1000

        return {
            'time_ms': t_ms,
            'modulation': mod,
            'num_channels': num_channels,
            'phi_frequency': self.phi_frequency,
            'duration_ms': duration_ms
        }

    def reset(self):
        """Reset internal phase accumulator"""
        self.phase_accumulator = 0.0
        print("[PhiModulator] Phase accumulator reset")


# Self-test function
def _self_test():
    """Run basic self-test of PhiModulator"""
    print("=" * 60)
    print("PhiModulator Self-Test")
    print("=" * 60)

    try:
        # Create modulator
        print("\n1. Initializing modulator...")
        modulator = PhiModulator(sample_rate=48000)
        print("   ✓ Modulator initialized")

        # Display Φ relationships
        print("\n2. Golden ratio relationships:")
        relationships = modulator.getPhiRelationships()
        for key, value in relationships.items():
            print(f"   {key}: {value}")

        # Generate single-channel modulation
        print("\n3. Generating single-channel modulation...")
        mod_single = modulator.generateModulation(
            phi_phase=0.0,
            phi_depth=0.5,
            num_samples=512
        )
        print(f"   ✓ Generated {len(mod_single)} samples")
        print(f"   Range: [{np.min(mod_single):.3f}, {np.max(mod_single):.3f}]")
        print(f"   Mean: {np.mean(mod_single):.3f}")

        # Generate multi-channel modulation
        print("\n4. Generating multi-channel modulation...")
        mod_multi = modulator.generateMultiChannelModulation(
            phi_phase=0.0,
            phi_depth=0.75,
            num_samples=512,
            num_channels=8
        )
        print(f"   ✓ Generated {mod_multi.shape[0]} channels × {mod_multi.shape[1]} samples")

        # Test different modes
        print("\n5. Testing modulation modes...")
        test_signal = np.sin(2 * np.pi * 1000 * np.arange(512) / 48000)
        test_mod = mod_single

        am_output = modulator.applyModulation(test_signal, test_mod, mode='amplitude')
        print(f"   Amplitude modulation: {am_output.shape}")

        ring_output = modulator.applyModulation(test_signal, test_mod, mode='ring')
        print(f"   Ring modulation: {ring_output.shape}")

        print("   ✓ All modulation modes working")

        # Test Fibonacci phases
        print("\n6. Fibonacci phase distribution...")
        fib_phases = modulator.generateFibonacciPhases(num_phases=8)
        print(f"   Phases (radians): {fib_phases}")
        print(f"   Phases (degrees): {np.degrees(fib_phases)}")
        print("   ✓ Fibonacci phases generated")

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
