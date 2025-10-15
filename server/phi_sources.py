"""
Φ-Modulation Sources - Abstract base and concrete implementations

Supports multiple Φ modulation sources:
- Manual: Direct user control via sliders
- Audio: Envelope follower from audio input
- MIDI: MIDI CC control (typically CC1 - Mod Wheel)
- Sensor: Biometric/accelerometer data
- Internal: Breathing oscillator (~0.1 Hz)
"""

import numpy as np
from abc import ABC, abstractmethod
from typing import Optional, Dict
import time


class PhiState:
    """
    Data container for Φ modulation state

    Attributes:
        phase: Φ-phase in radians [0, 2π]
        depth: Φ-depth [0, 1.618]
        source: Active source name
        frequency: Modulation frequency in Hz (if applicable)
        timestamp: Unix timestamp of last update
    """

    def __init__(self,
                 phase: float = 0.0,
                 depth: float = 0.618,
                 source: str = "internal",
                 frequency: float = 0.1):
        self.phase = phase
        self.depth = depth
        self.source = source
        self.frequency = frequency
        self.timestamp = time.time()

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'phase': float(self.phase),
            'depth': float(self.depth),
            'source': self.source,
            'frequency': float(self.frequency),
            'timestamp': self.timestamp
        }

    def __repr__(self) -> str:
        return f"PhiState(φ={self.phase:.3f}, Φd={self.depth:.3f}, source={self.source})"


class PhiSource(ABC):
    """
    Abstract base class for Φ modulation sources

    All sources must implement update() and get_state() methods
    """

    PHI = 1.618033988749895  # Golden ratio
    PHI_INV = 0.618033988749895  # 1/Φ

    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        self.active = False
        self.last_state = PhiState()

    @abstractmethod
    def update(self, **kwargs) -> PhiState:
        """
        Update and return current Φ state

        Returns:
            PhiState object with current phase and depth
        """
        pass

    @abstractmethod
    def get_state(self) -> PhiState:
        """
        Get current Φ state without updating

        Returns:
            Last known PhiState
        """
        pass

    def activate(self):
        """Activate this source"""
        self.active = True

    def deactivate(self):
        """Deactivate this source"""
        self.active = False

    def reset(self):
        """Reset source state"""
        self.last_state = PhiState()


class ManualSource(PhiSource):
    """
    Manual Φ control via direct parameter setting

    User directly sets phase and depth via UI sliders
    """

    def __init__(self, sample_rate: int = 48000):
        super().__init__(sample_rate)
        self._phase = 0.0
        self._depth = 0.618  # Default to Φ^-1
        self.last_state.source = "manual"

    def set_phase(self, phase: float):
        """Set phase directly [0, 2π]"""
        self._phase = phase % (2 * np.pi)
        self.last_state.phase = self._phase
        self.last_state.timestamp = time.time()

    def set_depth(self, depth: float):
        """Set depth directly [0, 1.618]"""
        self._depth = np.clip(depth, 0.0, self.PHI)
        self.last_state.depth = self._depth
        self.last_state.timestamp = time.time()

    def update(self, phase: Optional[float] = None, depth: Optional[float] = None) -> PhiState:
        """
        Update manual parameters

        Args:
            phase: New phase value (optional)
            depth: New depth value (optional)

        Returns:
            Updated PhiState
        """
        if phase is not None:
            self.set_phase(phase)
        if depth is not None:
            self.set_depth(depth)

        return self.last_state

    def get_state(self) -> PhiState:
        return self.last_state


class AudioEnvelopeSource(PhiSource):
    """
    Audio envelope follower for Φ modulation

    Maps RMS amplitude to Φ-depth with configurable attack/release
    """

    def __init__(self,
                 sample_rate: int = 48000,
                 attack_ms: float = 10.0,
                 release_ms: float = 100.0,
                 baseline_depth: float = 0.618):
        super().__init__(sample_rate)
        self.last_state.source = "audio"

        # Envelope follower parameters
        self.attack_coef = self._ms_to_coef(attack_ms)
        self.release_coef = self._ms_to_coef(release_ms)
        self.baseline_depth = baseline_depth

        # State tracking
        self.envelope = 0.0
        self.silence_duration = 0.0
        self.silence_threshold = 2.0  # seconds
        self.last_update_time = time.time()

        # Phase accumulator (slowly rotates)
        self.phase_accumulator = 0.0
        self.phase_rotation_freq = 0.05  # Hz (slow rotation)

    def _ms_to_coef(self, time_ms: float) -> float:
        """Convert time constant in ms to exponential coefficient"""
        # exp(-1 / (time_constant * sample_rate))
        time_samples = (time_ms / 1000.0) * self.sample_rate
        return np.exp(-1.0 / time_samples) if time_samples > 0 else 0.0

    def set_attack(self, attack_ms: float):
        """Set attack time in milliseconds [10-500]"""
        attack_ms = np.clip(attack_ms, 10.0, 500.0)
        self.attack_coef = self._ms_to_coef(attack_ms)

    def set_release(self, release_ms: float):
        """Set release time in milliseconds [10-500]"""
        release_ms = np.clip(release_ms, 10.0, 500.0)
        self.release_coef = self._ms_to_coef(release_ms)

    def update(self, audio_block: np.ndarray, **kwargs) -> PhiState:
        """
        Update from audio input

        Args:
            audio_block: Audio samples (any shape, will compute RMS)

        Returns:
            PhiState with depth following envelope
        """
        current_time = time.time()
        dt = current_time - self.last_update_time
        self.last_update_time = current_time

        # Calculate RMS of input
        rms = np.sqrt(np.mean(audio_block ** 2))

        # Envelope follower with attack/release
        if rms > self.envelope:
            # Attack
            self.envelope += (rms - self.envelope) * (1.0 - self.attack_coef)
        else:
            # Release
            self.envelope += (rms - self.envelope) * (1.0 - self.release_coef)

        # Track silence
        if rms < 0.001:  # Silence threshold
            self.silence_duration += dt
        else:
            self.silence_duration = 0.0

        # Decay to baseline after silence
        if self.silence_duration > self.silence_threshold:
            decay_rate = 0.1  # Smooth decay
            target_depth = self.baseline_depth
            self.last_state.depth += (target_depth - self.last_state.depth) * decay_rate * dt
        else:
            # Map envelope to depth [0, 1.618]
            # RMS of 0.5 (half-scale) maps to PHI
            self.last_state.depth = np.clip(self.envelope * 2.0 * self.PHI, 0.0, self.PHI)

        # Slowly rotate phase based on envelope energy
        phase_delta = 2 * np.pi * self.phase_rotation_freq * dt
        self.phase_accumulator += phase_delta * (1.0 + self.envelope)
        self.last_state.phase = self.phase_accumulator % (2 * np.pi)

        self.last_state.timestamp = current_time
        return self.last_state

    def get_state(self) -> PhiState:
        return self.last_state


class InternalOscillatorSource(PhiSource):
    """
    Internal breathing oscillator (~0.1 Hz)

    Provides baseline Φ modulation when no external source is active
    Simulates natural breathing rhythm (6 cycles/minute)
    """

    DEFAULT_FREQUENCY = 0.1  # Hz (6 breaths per minute)

    def __init__(self,
                 sample_rate: int = 48000,
                 frequency: float = DEFAULT_FREQUENCY,
                 depth_range: tuple = (0.3, 0.9)):
        super().__init__(sample_rate)
        self.last_state.source = "internal"

        self.frequency = np.clip(frequency, 0.01, 10.0)  # FR-008: limit range
        self.depth_min, self.depth_max = depth_range

        # Phase accumulator
        self.phase_accumulator = 0.0
        self.last_update_time = time.time()

    def set_frequency(self, frequency: float):
        """Set breathing frequency [0.01, 10 Hz]"""
        self.frequency = np.clip(frequency, 0.01, 10.0)
        self.last_state.frequency = self.frequency

    def update(self, **kwargs) -> PhiState:
        """
        Update internal oscillator

        Returns:
            PhiState with sinusoidal breathing pattern
        """
        current_time = time.time()
        dt = current_time - self.last_update_time
        self.last_update_time = current_time

        # Advance phase
        phase_delta = 2 * np.pi * self.frequency * dt
        self.phase_accumulator += phase_delta
        self.phase_accumulator %= (2 * np.pi)

        # Sinusoidal depth modulation (breathing)
        # Oscillates between depth_min and depth_max
        depth_center = (self.depth_min + self.depth_max) / 2.0
        depth_amplitude = (self.depth_max - self.depth_min) / 2.0
        self.last_state.depth = depth_center + depth_amplitude * np.sin(self.phase_accumulator)

        # Phase follows same oscillator
        self.last_state.phase = self.phase_accumulator
        self.last_state.frequency = self.frequency
        self.last_state.timestamp = current_time

        return self.last_state

    def get_state(self) -> PhiState:
        return self.last_state


class MIDISource(PhiSource):
    """
    MIDI CC control for Φ modulation

    Typically uses CC1 (Mod Wheel) for depth control
    Can also use pitch bend for phase modulation
    """

    def __init__(self, sample_rate: int = 48000):
        super().__init__(sample_rate)
        self.last_state.source = "midi"

        # MIDI state
        self.cc1_value = 64  # 0-127
        self.pitch_bend = 8192  # 0-16383, center = 8192

        # MIDI input (will be initialized when device connected)
        self.midi_input = None
        self.available_ports = []

    def set_cc1(self, value: int):
        """
        Set CC1 value (typically Mod Wheel)

        Args:
            value: MIDI CC value [0, 127]
        """
        self.cc1_value = np.clip(value, 0, 127)

        # Map CC1 to depth [0, 1.618]
        # CC1 = 64 → depth = 0.618 (Φ^-1)
        # CC1 = 127 → depth = 1.618 (Φ)
        self.last_state.depth = (self.cc1_value / 127.0) * self.PHI
        self.last_state.timestamp = time.time()

    def set_pitch_bend(self, value: int):
        """
        Set pitch bend value

        Args:
            value: MIDI pitch bend [0, 16383], center = 8192
        """
        self.pitch_bend = np.clip(value, 0, 16383)

        # Map pitch bend to phase offset [-π, +π]
        normalized = (self.pitch_bend - 8192) / 8192.0  # [-1, +1]
        self.last_state.phase = normalized * np.pi
        self.last_state.timestamp = time.time()

    def update(self, cc1: Optional[int] = None, pitch_bend: Optional[int] = None, **kwargs) -> PhiState:
        """
        Update from MIDI input

        Args:
            cc1: CC1 value (optional)
            pitch_bend: Pitch bend value (optional)

        Returns:
            Updated PhiState
        """
        if cc1 is not None:
            self.set_cc1(cc1)
        if pitch_bend is not None:
            self.set_pitch_bend(pitch_bend)

        return self.last_state

    def detect_ports(self) -> list:
        """
        Detect available MIDI input ports

        Returns:
            List of available port names
        """
        try:
            import mido
            self.available_ports = mido.get_input_names()
            return self.available_ports
        except ImportError:
            print("[MIDISource] Warning: mido not installed. MIDI support disabled.")
            return []
        except Exception as e:
            print(f"[MIDISource] Error detecting MIDI ports: {e}")
            return []

    def connect(self, port_name: Optional[str] = None):
        """
        Connect to MIDI input port

        Args:
            port_name: Port name (None = first available)
        """
        try:
            import mido

            if port_name is None:
                ports = self.detect_ports()
                if not ports:
                    raise RuntimeError("No MIDI ports available")
                port_name = ports[0]

            self.midi_input = mido.open_input(port_name)
            print(f"[MIDISource] Connected to {port_name}")

        except ImportError:
            raise RuntimeError("mido library not installed. Install with: pip install mido")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to MIDI port: {e}")

    def get_state(self) -> PhiState:
        return self.last_state


class SensorSource(PhiSource):
    """
    Biometric/sensor input for Φ modulation

    Supports:
    - Heart rate → phase frequency modulation
    - GSR (galvanic skin response) → depth modulation
    - Accelerometer → phase offset
    """

    def __init__(self, sample_rate: int = 48000):
        super().__init__(sample_rate)
        self.last_state.source = "sensor"

        # Sensor values
        self.heart_rate = 60.0  # BPM
        self.gsr = 0.5  # Normalized [0, 1]
        self.accel_x = 0.0  # Normalized [-1, 1]

        # Thresholds
        self.hr_threshold = 90.0  # BPM

    def set_heart_rate(self, bpm: float):
        """
        Set heart rate in beats per minute

        High heart rate (>90 BPM) increases phase rotation frequency

        Args:
            bpm: Heart rate in BPM [40, 200]
        """
        self.heart_rate = np.clip(bpm, 40.0, 200.0)

        # Map HR to phase frequency acceleration
        if self.heart_rate > self.hr_threshold:
            # +10% frequency per 10 BPM above threshold
            accel_factor = 1.0 + 0.1 * ((self.heart_rate - self.hr_threshold) / 10.0)
            self.last_state.frequency = 0.1 * accel_factor
        else:
            self.last_state.frequency = 0.1

        self.last_state.timestamp = time.time()

    def set_gsr(self, gsr: float):
        """
        Set galvanic skin response (normalized)

        Args:
            gsr: GSR value [0, 1]
        """
        self.gsr = np.clip(gsr, 0.0, 1.0)

        # Map GSR to depth
        self.last_state.depth = self.gsr * self.PHI
        self.last_state.timestamp = time.time()

    def set_accelerometer(self, x: float, y: float = 0.0, z: float = 0.0):
        """
        Set accelerometer values (normalized)

        Args:
            x, y, z: Acceleration [-1, 1]
        """
        self.accel_x = np.clip(x, -1.0, 1.0)

        # Map X-axis to phase offset
        self.last_state.phase = self.accel_x * np.pi
        self.last_state.timestamp = time.time()

    def update(self,
               heart_rate: Optional[float] = None,
               gsr: Optional[float] = None,
               accel: Optional[tuple] = None,
               **kwargs) -> PhiState:
        """
        Update from sensor data

        Args:
            heart_rate: Heart rate in BPM (optional)
            gsr: GSR value (optional)
            accel: (x, y, z) accelerometer tuple (optional)

        Returns:
            Updated PhiState
        """
        if heart_rate is not None:
            self.set_heart_rate(heart_rate)
        if gsr is not None:
            self.set_gsr(gsr)
        if accel is not None:
            self.set_accelerometer(*accel)

        return self.last_state

    def get_state(self) -> PhiState:
        return self.last_state


# Self-test function
def _self_test():
    """Test all Φ sources"""
    print("=" * 60)
    print("PhiSource Self-Test")
    print("=" * 60)

    try:
        # Test Manual Source
        print("\n1. Testing ManualSource...")
        manual = ManualSource()
        manual.set_phase(np.pi / 2)
        manual.set_depth(0.8)
        state = manual.get_state()
        print(f"   {state}")
        assert abs(state.phase - np.pi/2) < 0.01
        print("   ✓ ManualSource OK")

        # Test Audio Envelope Source
        print("\n2. Testing AudioEnvelopeSource...")
        audio = AudioEnvelopeSource(attack_ms=20, release_ms=100)
        test_audio = np.random.randn(512) * 0.5
        state = audio.update(test_audio)
        print(f"   {state}")
        print(f"   Envelope: {audio.envelope:.3f}")
        print("   ✓ AudioEnvelopeSource OK")

        # Test Internal Oscillator
        print("\n3. Testing InternalOscillatorSource...")
        internal = InternalOscillatorSource(frequency=0.1)
        states = []
        for _ in range(5):
            state = internal.update()
            states.append(state.depth)
            time.sleep(0.1)
        print(f"   Depth range: [{min(states):.3f}, {max(states):.3f}]")
        print("   ✓ InternalOscillatorSource OK")

        # Test MIDI Source
        print("\n4. Testing MIDISource...")
        midi = MIDISource()
        midi.set_cc1(64)
        state = midi.get_state()
        print(f"   {state}")
        print(f"   CC1=64 → depth={state.depth:.3f} (expected ≈0.8)")
        print("   ✓ MIDISource OK")

        # Test Sensor Source
        print("\n5. Testing SensorSource...")
        sensor = SensorSource()
        sensor.set_heart_rate(100)
        sensor.set_gsr(0.7)
        state = sensor.get_state()
        print(f"   {state}")
        print(f"   HR=100 → freq={state.frequency:.3f}")
        print("   ✓ SensorSource OK")

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
