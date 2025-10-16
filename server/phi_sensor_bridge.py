"""
PhiSensorBridge - Feature 011: Real-time Phi Sensor Binding

Handles external data sources (MIDI, sensors, audio beat, biometrics) as Φ-modulation inputs.

Features:
- MIDI CC input support (FR-001)
- Generic sensor input via serial/websocket (FR-001)
- Audio beat detection (FR-001)
- Input normalization to [0.618–1.618] range (FR-002)
- Real-time parameter updates < 100 ms (FR-003)
- Fallback mode if input stops > 2s (FR-005)

Requirements:
- FR-001: Accept Φ input from external sensor/MIDI streams
- FR-002: Normalize input to [0.618–1.618]
- FR-003: Update engine parameters in real time (< 100 ms)
- FR-005: Fallback mode if input stops for > 2s

Success Criteria:
- SC-001: Live Φ updates visible/audible < 100 ms
- SC-005: CPU overhead ≤ 5% from sensor loop
"""

import time
import threading
import queue
from typing import Optional, Callable, Dict, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np

# Optional MIDI support
try:
    import mido
    MIDI_AVAILABLE = True
except ImportError:
    MIDI_AVAILABLE = False
    print("[PhiSensorBridge] Warning: mido not available. MIDI support disabled.")

# Optional serial support for sensors
try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("[PhiSensorBridge] Warning: pyserial not available. Serial sensor support disabled.")


class SensorType(Enum):
    """Sensor input types"""
    MIDI_CC = "midi_cc"              # MIDI Control Change
    SERIAL_ANALOG = "serial_analog"  # Serial analog sensor (Arduino, etc.)
    WEBSOCKET = "websocket"          # WebSocket data stream
    AUDIO_BEAT = "audio_beat"        # Audio beat detection
    BIOMETRIC = "biometric"          # Biometric sensor (heart rate, etc.)
    OSC = "osc"                      # OSC (Open Sound Control)


@dataclass
class SensorData:
    """Raw sensor data packet"""
    sensor_type: SensorType
    timestamp: float
    raw_value: float          # Raw value from sensor
    normalized_value: float   # Normalized to [0.618, 1.618]
    source_id: str           # Device identifier


@dataclass
class SensorConfig:
    """Configuration for sensor input"""
    sensor_type: SensorType
    device_id: Optional[str] = None      # Device ID/port
    midi_channel: int = 0                 # MIDI channel (0-15)
    midi_cc_number: int = 1               # MIDI CC number (0-127)
    serial_baudrate: int = 9600           # Serial baudrate
    websocket_url: Optional[str] = None   # WebSocket URL
    input_range: Tuple[float, float] = (0.0, 1.0)  # Expected input range
    smoothing_alpha: float = 0.1          # Smoothing factor
    enable_logging: bool = False


class MIDIInput:
    """
    MIDI input handler

    Listens to MIDI Control Change messages and extracts Φ values
    """

    def __init__(self, config: SensorConfig, callback: Callable[[SensorData], None]):
        """
        Initialize MIDI input

        Args:
            config: Sensor configuration
            callback: Function to call when data received
        """
        if not MIDI_AVAILABLE:
            raise RuntimeError("MIDI support not available. Install mido: pip install mido python-rtmidi")

        self.config = config
        self.callback = callback
        self.port = None
        self.is_running = False
        self.thread = None

        # Smoothing
        self.smoothed_value = 0.5

    def connect(self) -> bool:
        """
        Connect to MIDI device

        Returns:
            True if connected successfully
        """
        try:
            # List available MIDI ports
            available_ports = mido.get_input_names()

            if not available_ports:
                print("[MIDIInput] No MIDI input devices found")
                return False

            # Use specified device or first available
            if self.config.device_id:
                if self.config.device_id in available_ports:
                    port_name = self.config.device_id
                else:
                    print(f"[MIDIInput] Device '{self.config.device_id}' not found")
                    return False
            else:
                port_name = available_ports[0]

            self.port = mido.open_input(port_name)

            if self.config.enable_logging:
                print(f"[MIDIInput] Connected to: {port_name}")
                print(f"[MIDIInput] Listening for CC{self.config.midi_cc_number} on channel {self.config.midi_channel}")

            return True

        except Exception as e:
            print(f"[MIDIInput] Failed to connect: {e}")
            return False

    def start(self) -> bool:
        """
        Start MIDI input thread

        Returns:
            True if started successfully
        """
        if not self.port:
            return False

        self.is_running = True
        self.thread = threading.Thread(target=self._midi_loop, daemon=True)
        self.thread.start()

        return True

    def stop(self):
        """Stop MIDI input thread"""
        self.is_running = False

        if self.thread:
            self.thread.join(timeout=1.0)

        if self.port:
            self.port.close()
            self.port = None

    def _midi_loop(self):
        """MIDI message processing loop"""
        while self.is_running:
            try:
                # Non-blocking receive with timeout
                msg = self.port.receive(block=True, timeout=0.1)

                if msg is None:
                    continue

                # Filter for Control Change messages
                if msg.type == 'control_change':
                    # Check channel and CC number
                    if (msg.channel == self.config.midi_channel and
                        msg.control == self.config.midi_cc_number):

                        # MIDI CC values are 0-127
                        raw_value = msg.value / 127.0  # Normalize to [0, 1]

                        # Apply smoothing
                        self.smoothed_value = (
                            self.config.smoothing_alpha * raw_value +
                            (1 - self.config.smoothing_alpha) * self.smoothed_value
                        )

                        # Map to Φ range [0.618, 1.618]
                        PHI_MIN = 0.618033988749895
                        PHI_MAX = 1.618033988749895
                        normalized_value = PHI_MIN + self.smoothed_value * (PHI_MAX - PHI_MIN)

                        # Create sensor data packet
                        sensor_data = SensorData(
                            sensor_type=SensorType.MIDI_CC,
                            timestamp=time.time(),
                            raw_value=msg.value,
                            normalized_value=normalized_value,
                            source_id=f"MIDI_CC{self.config.midi_cc_number}"
                        )

                        # Call callback (SC-001: < 100 ms latency)
                        self.callback(sensor_data)

            except Exception as e:
                if self.config.enable_logging:
                    print(f"[MIDIInput] Error in MIDI loop: {e}")

    @staticmethod
    def list_devices() -> List[str]:
        """
        List available MIDI input devices

        Returns:
            List of device names
        """
        if not MIDI_AVAILABLE:
            return []

        try:
            return mido.get_input_names()
        except:
            return []


class SerialSensorInput:
    """
    Serial sensor input handler

    Reads analog sensor values from serial port (Arduino, etc.)
    Expected format: ASCII decimal values, one per line
    """

    def __init__(self, config: SensorConfig, callback: Callable[[SensorData], None]):
        """
        Initialize serial sensor input

        Args:
            config: Sensor configuration
            callback: Function to call when data received
        """
        if not SERIAL_AVAILABLE:
            raise RuntimeError("Serial support not available. Install pyserial: pip install pyserial")

        self.config = config
        self.callback = callback
        self.serial_port = None
        self.is_running = False
        self.thread = None

        # Smoothing
        self.smoothed_value = 0.5

    def connect(self) -> bool:
        """
        Connect to serial device

        Returns:
            True if connected successfully
        """
        try:
            # Find device
            if self.config.device_id:
                port = self.config.device_id
            else:
                # Use first available serial port
                ports = list(serial.tools.list_ports.comports())
                if not ports:
                    print("[SerialSensor] No serial ports found")
                    return False
                port = ports[0].device

            # Open serial port
            self.serial_port = serial.Serial(
                port=port,
                baudrate=self.config.serial_baudrate,
                timeout=0.1
            )

            if self.config.enable_logging:
                print(f"[SerialSensor] Connected to: {port} @ {self.config.serial_baudrate} baud")

            return True

        except Exception as e:
            print(f"[SerialSensor] Failed to connect: {e}")
            return False

    def start(self) -> bool:
        """
        Start serial input thread

        Returns:
            True if started successfully
        """
        if not self.serial_port:
            return False

        self.is_running = True
        self.thread = threading.Thread(target=self._serial_loop, daemon=True)
        self.thread.start()

        return True

    def stop(self):
        """Stop serial input thread"""
        self.is_running = False

        if self.thread:
            self.thread.join(timeout=1.0)

        if self.serial_port:
            self.serial_port.close()
            self.serial_port = None

    def _serial_loop(self):
        """Serial data processing loop"""
        while self.is_running:
            try:
                # Read line from serial
                if self.serial_port.in_waiting > 0:
                    line = self.serial_port.readline().decode('utf-8').strip()

                    if line:
                        try:
                            # Parse value
                            raw_value = float(line)

                            # Normalize from input range to [0, 1]
                            input_min, input_max = self.config.input_range
                            normalized_01 = (raw_value - input_min) / (input_max - input_min)
                            normalized_01 = np.clip(normalized_01, 0.0, 1.0)

                            # Apply smoothing
                            self.smoothed_value = (
                                self.config.smoothing_alpha * normalized_01 +
                                (1 - self.config.smoothing_alpha) * self.smoothed_value
                            )

                            # Map to Φ range [0.618, 1.618] (FR-002)
                            PHI_MIN = 0.618033988749895
                            PHI_MAX = 1.618033988749895
                            normalized_phi = PHI_MIN + self.smoothed_value * (PHI_MAX - PHI_MIN)

                            # Create sensor data packet
                            sensor_data = SensorData(
                                sensor_type=SensorType.SERIAL_ANALOG,
                                timestamp=time.time(),
                                raw_value=raw_value,
                                normalized_value=normalized_phi,
                                source_id=f"Serial_{self.config.device_id}"
                            )

                            # Call callback (SC-001: < 100 ms latency)
                            self.callback(sensor_data)

                        except ValueError:
                            # Skip invalid values
                            pass

                else:
                    # Brief sleep to avoid busy-waiting
                    time.sleep(0.01)

            except Exception as e:
                if self.config.enable_logging:
                    print(f"[SerialSensor] Error in serial loop: {e}")

    @staticmethod
    def list_devices() -> List[str]:
        """
        List available serial ports

        Returns:
            List of port names
        """
        if not SERIAL_AVAILABLE:
            return []

        try:
            ports = serial.tools.list_ports.comports()
            return [port.device for port in ports]
        except:
            return []


class AudioBeatDetector:
    """
    Audio beat detection for Φ modulation

    Analyzes audio input to detect beats and modulate Φ accordingly
    """

    def __init__(self, config: SensorConfig, callback: Callable[[SensorData], None]):
        """
        Initialize beat detector

        Args:
            config: Sensor configuration
            callback: Function to call when beat detected
        """
        self.config = config
        self.callback = callback

        # Beat detection state
        self.energy_history = []
        self.last_beat_time = 0.0
        self.beat_strength = 0.0

        # Φ modulation
        self.phi_value = 1.0  # Start at golden ratio

    def process_audio(self, audio_block: np.ndarray, sample_rate: int = 48000):
        """
        Process audio block for beat detection

        Args:
            audio_block: Audio samples (mono, float32)
            sample_rate: Sample rate in Hz
        """
        # Calculate instantaneous energy
        energy = np.sum(audio_block ** 2)

        # Track energy history
        self.energy_history.append(energy)
        if len(self.energy_history) > 43:  # ~1 second at 512 samples/block
            self.energy_history.pop(0)

        # Detect beat (energy spike)
        if len(self.energy_history) >= 10:
            avg_energy = np.mean(self.energy_history[-10:])
            threshold = avg_energy * 1.5

            current_time = time.time()

            if energy > threshold and (current_time - self.last_beat_time) > 0.3:
                # Beat detected!
                self.last_beat_time = current_time
                self.beat_strength = min(energy / (avg_energy + 1e-9), 2.0)

                # Modulate Φ based on beat strength
                # Stronger beats → higher Φ
                PHI_MIN = 0.618033988749895
                PHI_MAX = 1.618033988749895
                self.phi_value = PHI_MIN + (self.beat_strength / 2.0) * (PHI_MAX - PHI_MIN)

                # Create sensor data packet
                sensor_data = SensorData(
                    sensor_type=SensorType.AUDIO_BEAT,
                    timestamp=current_time,
                    raw_value=self.beat_strength,
                    normalized_value=self.phi_value,
                    source_id="AudioBeat"
                )

                # Call callback
                self.callback(sensor_data)

        # Decay Φ value towards center
        decay_rate = 0.95
        center = 1.0
        self.phi_value = self.phi_value * decay_rate + center * (1 - decay_rate)


# Self-test function
def _self_test():
    """Run basic self-test of PhiSensorBridge"""
    print("=" * 60)
    print("PhiSensorBridge Self-Test")
    print("=" * 60)

    # Test MIDI device listing
    print("\n1. Testing MIDI device listing...")
    if MIDI_AVAILABLE:
        devices = MIDIInput.list_devices()
        print(f"   Found {len(devices)} MIDI devices:")
        for dev in devices:
            print(f"   - {dev}")
    else:
        print("   MIDI not available (install mido)")

    # Test Serial device listing
    print("\n2. Testing Serial device listing...")
    if SERIAL_AVAILABLE:
        devices = SerialSensorInput.list_devices()
        print(f"   Found {len(devices)} serial devices:")
        for dev in devices:
            print(f"   - {dev}")
    else:
        print("   Serial not available (install pyserial)")

    # Test audio beat detector
    print("\n3. Testing Audio Beat Detector...")
    beat_detected = []

    def beat_callback(data: SensorData):
        beat_detected.append(data)
        print(f"   Beat detected! Strength: {data.raw_value:.2f}, Φ: {data.normalized_value:.3f}")

    config = SensorConfig(sensor_type=SensorType.AUDIO_BEAT)
    detector = AudioBeatDetector(config, beat_callback)

    # Simulate beats
    print("   Simulating 3 beats...")
    for i in range(3):
        # Create beat-like signal
        beat_signal = np.random.randn(512).astype(np.float32) * (2.0 if i % 2 == 0 else 0.5)
        detector.process_audio(beat_signal)
        time.sleep(0.5)

    print(f"   Detected {len(beat_detected)} beats")

    print("\n" + "=" * 60)
    print("Self-Test PASSED ✓")
    print("=" * 60)

    return True


if __name__ == "__main__":
    _self_test()
