"""
Mock Sounddevice Module
Feature 020: Reproducible Build Environment + Dependency Bootstrap (FR-007, FR-010)

Simulates sounddevice API for headless testing without audio hardware.
Automatically activates when SOUNDLAB_SIMULATE=1 environment variable is set.

Usage:
    import sys
    import os
    if os.getenv('SOUNDLAB_SIMULATE') == '1':
        from tests.mocks import mock_sounddevice as sounddevice
    else:
        import sounddevice

Example:
    export SOUNDLAB_SIMULATE=1
    python -m pytest tests/
"""

import numpy as np
import time
import threading
from typing import Optional, Callable, Any, List, Tuple


class MockCallbackException(Exception):
    """Exception raised during mock callback execution"""
    pass


class MockInputStream:
    """Mock input stream for simulating audio input"""

    def __init__(self, callback: Callable, channels: int = 2, samplerate: int = 48000,
                 blocksize: int = 512, device: Optional[int] = None):
        self.callback = callback
        self.channels = channels
        self.samplerate = samplerate
        self.blocksize = blocksize
        self.device = device or 0
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._frames_processed = 0

    def start(self):
        """Start the mock input stream"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._generate_audio, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the mock input stream"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)

    def close(self):
        """Close the mock input stream"""
        self.stop()

    def _generate_audio(self):
        """Generate mock audio data and call callback"""
        while self._running:
            # Generate mock audio data (sine wave + noise)
            t = np.arange(self.blocksize) / self.samplerate + (self._frames_processed / self.samplerate)
            frequency = 440.0  # A4 note
            audio_data = 0.1 * np.sin(2 * np.pi * frequency * t)
            audio_data += 0.01 * np.random.randn(self.blocksize)  # Add noise
            audio_data = audio_data.reshape(-1, 1)
            if self.channels == 2:
                audio_data = np.hstack([audio_data, audio_data])  # Stereo

            try:
                self.callback(audio_data, self.blocksize, None, None)
                self._frames_processed += self.blocksize
            except Exception as e:
                print(f"Mock callback error: {e}")

            # Sleep to simulate real-time audio (slightly faster than real-time for testing)
            time.sleep(self.blocksize / self.samplerate * 0.8)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class MockOutputStream:
    """Mock output stream for simulating audio output"""

    def __init__(self, callback: Callable, channels: int = 2, samplerate: int = 48000,
                 blocksize: int = 512, device: Optional[int] = None):
        self.callback = callback
        self.channels = channels
        self.samplerate = samplerate
        self.blocksize = blocksize
        self.device = device or 0
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._frames_processed = 0

    def start(self):
        """Start the mock output stream"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._consume_audio, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the mock output stream"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)

    def close(self):
        """Close the mock output stream"""
        self.stop()

    def _consume_audio(self):
        """Request audio data from callback"""
        while self._running:
            outdata = np.zeros((self.blocksize, self.channels), dtype=np.float32)
            try:
                self.callback(outdata, self.blocksize, None, None)
                self._frames_processed += self.blocksize
            except Exception as e:
                print(f"Mock callback error: {e}")

            # Sleep to simulate real-time audio
            time.sleep(self.blocksize / self.samplerate * 0.8)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Mock device info
_mock_devices = [
    {
        'name': 'Mock Audio Device (Input)',
        'index': 0,
        'hostapi': 0,
        'max_input_channels': 2,
        'max_output_channels': 0,
        'default_low_input_latency': 0.01,
        'default_low_output_latency': 0.0,
        'default_high_input_latency': 0.1,
        'default_high_output_latency': 0.0,
        'default_samplerate': 48000.0,
    },
    {
        'name': 'Mock Audio Device (Output)',
        'index': 1,
        'hostapi': 0,
        'max_input_channels': 0,
        'max_output_channels': 2,
        'default_low_input_latency': 0.0,
        'default_low_output_latency': 0.01,
        'default_high_input_latency': 0.0,
        'default_high_output_latency': 0.1,
        'default_samplerate': 48000.0,
    },
]


def query_devices(device: Optional[int] = None, kind: Optional[str] = None):
    """Mock query_devices function"""
    if device is None:
        return _mock_devices
    if isinstance(device, int) and 0 <= device < len(_mock_devices):
        return _mock_devices[device]
    return _mock_devices[0]


def default_device():
    """Mock default_device function"""
    return (0, 1)  # (input, output)


def check_input_settings(device: Optional[int] = None, channels: Optional[int] = None,
                         dtype: Optional[type] = None, samplerate: Optional[float] = None):
    """Mock check_input_settings function"""
    return {
        'device': device or 0,
        'channels': channels or 2,
        'dtype': dtype or np.float32,
        'samplerate': samplerate or 48000.0,
    }


def check_output_settings(device: Optional[int] = None, channels: Optional[int] = None,
                          dtype: Optional[type] = None, samplerate: Optional[float] = None):
    """Mock check_output_settings function"""
    return {
        'device': device or 1,
        'channels': channels or 2,
        'dtype': dtype or np.float32,
        'samplerate': samplerate or 48000.0,
    }


# Aliases
InputStream = MockInputStream
OutputStream = MockOutputStream


# Mock module-level attributes
__version__ = '0.4.6-mock'


if __name__ == '__main__':
    print("Mock Sounddevice Module")
    print(f"Version: {__version__}")
    print(f"Devices: {len(_mock_devices)}")
    print("\nAvailable Devices:")
    for device in query_devices():
        print(f"  [{device['index']}] {device['name']} - "
              f"{device['max_input_channels']} in, {device['max_output_channels']} out")
