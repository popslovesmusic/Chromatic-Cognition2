"""
Multi-Channel Downmix Utilities

Converts 8-channel D-ASE output to stereo for browser playback with spatial preservation.
Implements multiple downmix strategies optimized for different use cases.
"""

import numpy as np
from typing import Optional, Literal


class StereoDownmixer:
    """
    8-channel to stereo downmixer with spatial panning

    Supports multiple downmix strategies to preserve spatial characteristics
    of the multi-channel D-ASE output while preventing clipping.
    """

    def __init__(self, num_channels: int = 8, strategy: Literal['spatial', 'energy', 'linear', 'phi'] = 'spatial'):
        """
        Initialize downmixer

        Args:
            num_channels: Number of input channels (default: 8)
            strategy: Downmix strategy
                - 'spatial': Spatial panning with weighted coefficients
                - 'energy': Energy-preserving (RMS-based)
                - 'linear': Simple averaging
                - 'phi': Golden-ratio weighted distribution
        """
        self.num_channels = num_channels
        self.strategy = strategy
        self.gain = 1.0  # Master output gain
        self._setup_coefficients()

        print(f"[StereoDownmixer] Initialized with '{strategy}' strategy")

    def _setup_coefficients(self):
        """Setup mixing coefficients based on selected strategy"""

        if self.strategy == 'spatial':
            # Spatial panning: channels distributed across stereo field
            # Left side gets more of channels 0-3, right side gets 4-7
            # Using power-law panning for natural spatial distribution
            self.left_weights = np.array([0.8, 0.6, 0.4, 0.2, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)
            self.right_weights = np.array([0.0, 0.0, 0.0, 0.0, 0.2, 0.4, 0.6, 0.8], dtype=np.float32)
            self.normalization = 2.0  # Prevent clipping

        elif self.strategy == 'energy':
            # Energy-preserving: maintain RMS level
            # Each channel contributes equally to total energy
            self.left_weights = np.ones(8, dtype=np.float32) / np.sqrt(8)
            self.right_weights = np.ones(8, dtype=np.float32) / np.sqrt(8)
            self.normalization = 1.0

        elif self.strategy == 'linear':
            # Simple averaging: all channels contribute equally
            self.left_weights = np.ones(8, dtype=np.float32) / 8
            self.right_weights = np.ones(8, dtype=np.float32) / 8
            self.normalization = 1.0

        elif self.strategy == 'phi':
            # Golden-ratio weighted distribution
            # Creates natural harmonic relationships in the downmix
            PHI_INV = 0.618033988749895
            weights = np.array([
                PHI_INV ** i for i in range(8)
            ], dtype=np.float32)
            weights /= np.sum(weights)  # Normalize

            # Distribute: lower indices → left, higher indices → right
            self.left_weights = weights * np.linspace(1.0, 0.0, 8, dtype=np.float32)
            self.right_weights = weights * np.linspace(0.0, 1.0, 8, dtype=np.float32)
            self.normalization = 1.5

        else:
            raise ValueError(f"Unknown downmix strategy: {self.strategy}")

    def downmix(self, multi_channel: np.ndarray) -> np.ndarray:
        """
        Downmix 8 channels to stereo

        Args:
            multi_channel: float32[8, num_samples] or [num_samples, 8]
                Multi-channel input signal

        Returns:
            float32[2, num_samples] stereo output

        Raises:
            ValueError: If input doesn't have 8 channels
        """
        # Handle both channel orderings
        if multi_channel.ndim != 2:
            raise ValueError(f"Expected 2D array, got shape {multi_channel.shape}")

        if multi_channel.shape[0] == 8:
            # Already in [channels, samples] format
            channels = multi_channel
        elif multi_channel.shape[1] == 8:
            # Transpose from [samples, channels]
            channels = multi_channel.T
        else:
            raise ValueError(f"Expected 8 channels, got shape {multi_channel.shape}")

        num_samples = channels.shape[1]

        # Apply weighted mixing
        left = np.zeros(num_samples, dtype=np.float32)
        right = np.zeros(num_samples, dtype=np.float32)

        for ch_idx in range(8):
            left += channels[ch_idx] * self.left_weights[ch_idx]
            right += channels[ch_idx] * self.right_weights[ch_idx]

        # Apply normalization to prevent clipping
        left /= self.normalization
        right /= self.normalization

        # Apply master gain
        left *= self.gain
        right *= self.gain

        # Stack to stereo format [2, num_samples]
        stereo = np.vstack([left, right])

        return stereo

    def downmix_with_monitoring(self, multi_channel: np.ndarray) -> tuple[np.ndarray, dict]:
        """
        Downmix with additional monitoring information

        Args:
            multi_channel: float32[8, num_samples] input

        Returns:
            Tuple of (stereo_output, monitoring_dict)
                monitoring_dict contains:
                    - peak_left: Peak level in left channel
                    - peak_right: Peak level in right channel
                    - rms_left: RMS level in left channel
                    - rms_right: RMS level in right channel
                    - clipped: Boolean, True if any clipping occurred
        """
        stereo = self.downmix(multi_channel)

        # Calculate monitoring metrics
        left = stereo[0]
        right = stereo[1]

        monitoring = {
            'peak_left': float(np.max(np.abs(left))),
            'peak_right': float(np.max(np.abs(right))),
            'rms_left': float(np.sqrt(np.mean(left ** 2))),
            'rms_right': float(np.sqrt(np.mean(right ** 2))),
            'clipped': bool(np.any(np.abs(stereo) > 1.0))
        }

        return stereo, monitoring

    def set_strategy(self, strategy: Literal['spatial', 'energy', 'linear', 'phi']):
        """
        Change downmix strategy

        Args:
            strategy: New downmix strategy
        """
        self.strategy = strategy
        self._setup_coefficients()

    def set_weights(self, channel: Literal['L', 'R'], weights: np.ndarray):
        """
        Set custom weights for left or right channel

        Args:
            channel: 'L' for left or 'R' for right
            weights: Array of weights (length must match num_channels)
        """
        if len(weights) != self.num_channels:
            raise ValueError(f"Expected {self.num_channels} weights, got {len(weights)}")

        if channel == 'L':
            self.left_weights = np.array(weights, dtype=np.float32)
        elif channel == 'R':
            self.right_weights = np.array(weights, dtype=np.float32)
        else:
            raise ValueError(f"Invalid channel: {channel}. Use 'L' or 'R'")

    def get_strategy_info(self) -> dict:
        """
        Get information about current downmix strategy

        Returns:
            Dictionary with strategy details
        """
        return {
            'strategy': self.strategy,
            'left_weights': self.left_weights.tolist(),
            'right_weights': self.right_weights.tolist(),
            'normalization': float(self.normalization),
            'gain': float(self.gain),
            'total_left_gain': float(np.sum(self.left_weights)),
            'total_right_gain': float(np.sum(self.right_weights))
        }


# Convenience functions
def downmix_to_stereo(multi_channel: np.ndarray,
                     strategy: str = 'spatial') -> np.ndarray:
    """
    Quick downmix function for simple use cases

    Args:
        multi_channel: float32[8, num_samples] input
        strategy: Downmix strategy (see StereoDownmixer)

    Returns:
        float32[2, num_samples] stereo output
    """
    downmixer = StereoDownmixer(strategy=strategy)
    return downmixer.downmix(multi_channel)


def adaptive_downmix(multi_channel: np.ndarray,
                    target_lufs: Optional[float] = -18.0) -> np.ndarray:
    """
    Adaptive downmix with automatic loudness normalization

    Args:
        multi_channel: float32[8, num_samples] input
        target_lufs: Target LUFS level (None = no normalization)

    Returns:
        float32[2, num_samples] stereo output
    """
    # Start with spatial downmix
    downmixer = StereoDownmixer(strategy='spatial')
    stereo = downmixer.downmix(multi_channel)

    if target_lufs is not None:
        # Simplified loudness normalization (not true LUFS, but close enough)
        # True LUFS requires K-weighting filter, but RMS is sufficient for real-time
        rms = np.sqrt(np.mean(stereo ** 2))
        if rms > 0:
            # Convert target LUFS to linear gain (approximate)
            # -18 LUFS ≈ 0.126 RMS for full-scale sine
            target_rms = 0.126 * (10 ** (target_lufs / 20))
            gain = target_rms / rms
            # Limit gain to prevent excessive boost
            gain = np.clip(gain, 0.1, 2.0)
            stereo *= gain

    return stereo


# Self-test function
def _self_test():
    """Run basic self-test of downmix module"""
    print("=" * 60)
    print("StereoDownmixer Self-Test")
    print("=" * 60)

    try:
        # Generate test multi-channel signal
        print("\n1. Generating 8-channel test signal...")
        num_samples = 512
        sample_rate = 48000
        t = np.linspace(0, num_samples/sample_rate, num_samples, endpoint=False)

        # Each channel has a different frequency
        test_signal = np.zeros((8, num_samples), dtype=np.float32)
        for ch in range(8):
            freq = 440 * (2 ** (ch / 12))  # Chromatic scale
            test_signal[ch] = 0.3 * np.sin(2 * np.pi * freq * t)

        print(f"   ✓ Generated test signal: {test_signal.shape}")
        print(f"   RMS per channel: {np.sqrt(np.mean(test_signal**2, axis=1))}")

        # Test all strategies
        print("\n2. Testing all downmix strategies...")
        strategies = ['spatial', 'energy', 'linear', 'phi']

        for strategy in strategies:
            downmixer = StereoDownmixer(strategy=strategy)
            stereo = downmixer.downmix(test_signal)

            info = downmixer.get_strategy_info()
            peak = np.max(np.abs(stereo))
            rms = np.sqrt(np.mean(stereo ** 2))

            print(f"\n   {strategy.upper()} strategy:")
            print(f"     Output shape: {stereo.shape}")
            print(f"     Peak level: {peak:.4f}")
            print(f"     RMS level: {rms:.4f}")
            print(f"     Clipping: {'YES' if peak > 1.0 else 'NO'}")

        # Test monitoring
        print("\n3. Testing downmix with monitoring...")
        downmixer = StereoDownmixer(strategy='spatial')
        stereo, monitoring = downmixer.downmix_with_monitoring(test_signal)

        print("   Monitoring metrics:")
        for key, value in monitoring.items():
            print(f"     {key}: {value}")

        # Test convenience functions
        print("\n4. Testing convenience functions...")
        quick_stereo = downmix_to_stereo(test_signal, strategy='phi')
        print(f"   Quick downmix: {quick_stereo.shape}")

        adaptive_stereo = adaptive_downmix(test_signal, target_lufs=-18.0)
        print(f"   Adaptive downmix: {adaptive_stereo.shape}")

        # Test transposed input
        print("\n5. Testing transposed input [samples, channels]...")
        test_transposed = test_signal.T  # [512, 8]
        stereo_transposed = downmix_to_stereo(test_transposed)
        print(f"   ✓ Transposed input handled: {stereo_transposed.shape}")

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
