"""
AudioEngine - Compatibility Wrapper for Validation Scripts

This module provides backward compatibility for validation and test scripts
that expect an AudioEngine class. It wraps the AudioServer class which is
the actual production implementation.

Created: 2025-10-17 (Priority 1 Remediation)
Purpose: Fix validate_soundlab_v1_final.py import errors
"""

from .audio_server import AudioServer
from .chromatic_field_processor import ChromaticFieldProcessor
import numpy as np


class AudioEngine:
    """
    AudioEngine wrapper for validation compatibility

    This class wraps AudioServer to provide the interface expected by
    validation scripts, particularly validate_soundlab_v1_final.py.

    The actual production implementation is AudioServer, which includes
    real-time audio I/O, metrics streaming, and latency management.
    This wrapper provides a simplified interface for testing and validation.
    """

    def __init__(self, enable_logging: bool = False):
        """
        Initialize AudioEngine

        Args:
            enable_logging: Enable metrics/latency logging (default: False for tests)
        """
        # Create underlying AudioServer
        self._audio_server = AudioServer(enable_logging=enable_logging)

        # Expose processor for direct access (validation scripts expect this)
        self.processor = self._audio_server.processor

        # Configuration
        self.sample_rate = self._audio_server.SAMPLE_RATE
        self.buffer_size = self._audio_server.BUFFER_SIZE

    def start(self, calibrate_latency: bool = False) -> bool:
        """
        Start audio processing

        Args:
            calibrate_latency: Run latency calibration

        Returns:
            True if started successfully
        """
        return self._audio_server.start(calibrate_latency=calibrate_latency)

    def stop(self):
        """Stop audio processing"""
        self._audio_server.stop()

    def apply_preset(self, preset_data: dict):
        """
        Apply preset configuration

        Args:
            preset_data: Preset dictionary
        """
        self._audio_server.apply_preset(preset_data)

    def update_parameter(self, param_type: str, channel: int, param_name: str, value: float) -> bool:
        """
        Update a parameter in real-time

        Args:
            param_type: Type of parameter ('channel', 'global', 'phi')
            channel: Channel index (0-7) or None for global
            param_name: Parameter name
            value: New value

        Returns:
            True if successful
        """
        return self._audio_server.update_parameter(param_type, channel, param_name, value)

    def get_current_parameters(self) -> dict:
        """
        Get current parameter values

        Returns:
            Dictionary with all current parameters
        """
        return self._audio_server.get_current_parameters()

    def get_latest_metrics(self):
        """
        Get latest metrics frame

        Returns:
            Latest MetricsFrame or None
        """
        return self._audio_server.get_latest_metrics()

    def get_latest_latency(self):
        """
        Get latest latency frame

        Returns:
            Latest LatencyFrame or None
        """
        return self._audio_server.get_latest_latency()

    @property
    def is_running(self) -> bool:
        """Check if engine is running"""
        return self._audio_server.is_running


# Self-test function
def _self_test():
    """Test AudioEngine wrapper"""
    print("=" * 60)
    print("AudioEngine Wrapper Self-Test")
    print("=" * 60)

    try:
        print("\n1. Testing AudioEngine initialization...")
        engine = AudioEngine()

        assert engine.sample_rate == 48000
        assert engine.buffer_size == 512
        assert hasattr(engine, 'processor')
        assert isinstance(engine.processor, ChromaticFieldProcessor)
        assert not engine.is_running

        print("   ✓ Initialization OK")
        print(f"   ✓ Processor type: {type(engine.processor).__name__}")

        print("\n2. Testing processor access...")
        # Test that we can access processor methods
        assert hasattr(engine.processor, 'processBlock')
        print("   ✓ processor.processBlock() available")

        print("\n3. Testing preset application...")
        test_preset = {
            'name': 'Test Preset',
            'engine': {'coupling_strength': 1.5}
        }
        engine.apply_preset(test_preset)
        print("   ✓ Preset application OK")

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
    success = _self_test()

    if not success:
        import sys
        sys.exit(1)
