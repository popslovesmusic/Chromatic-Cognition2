"""
HybridNode - Feature 025: Hybrid Node Integration (Analog–Digital Bridge)

Integrates D-ASE engine with real/simulated analog I/O and external Φ modulation sources.

Features:
- Real-time audio I/O using sounddevice callbacks
- Integration with ChromaticFieldProcessor for analog signal processing
- External Φ modulation source support (microphone, sensor, manual slider)
- Multi-channel (8-channel) @ 48 kHz processing
- Real-time metrics broadcasting (ICI, coherence, centroid)
- Low-latency operation (<2 ms)

Requirements:
- FR-001: HybridNode class manages analog I/O
- FR-002: Real-time audio I/O using sounddevice callback
- FR-006: Process 8 channels @ 48 kHz with < 2 ms latency
- FR-007: Broadcast metrics (ICI, coherence, centroid) ≤ 100 ms interval

Success Criteria:
- SC-001: Hybrid Mode operational without audio dropouts
- SC-002: Φ input propagates to metrics < 2 ms latency
- SC-003: ICI and coherence update visible @ ≥ 30 Hz
- SC-004: System remains below 50% CPU load under 8-channel processing
"""

import numpy as np
import sounddevice as sd
import threading
import time
import queue
from typing import Optional, Callable, Dict, List
from dataclasses import dataclass, asdict
from enum import Enum

from chromatic_field_processor import ChromaticFieldProcessor

# Optional PhiRouter support (Feature 011)
try:
    from phi_router import PhiRouter, PhiRouterConfig, PhiSourcePriority
    from phi_sensor_bridge import (MIDIInput, SerialSensorInput, AudioBeatDetector,
                                   SensorType, SensorConfig, SensorData)
    SENSOR_BINDING_AVAILABLE = True
except ImportError:
    SENSOR_BINDING_AVAILABLE = False


class PhiSource(Enum):
    """External Φ modulation source types"""
    MANUAL = "manual"              # Manual slider control
    MICROPHONE = "microphone"      # Live microphone input
    SENSOR = "sensor"              # External sensor (future)
    INTERNAL = "internal"          # Auto-generated Φ


@dataclass
class HybridNodeConfig:
    """Configuration for HybridNode"""
    sample_rate: int = 48000           # Audio sample rate (Hz)
    block_size: int = 512              # Processing block size in samples
    num_channels: int = 8              # Number of channels
    input_device: Optional[int] = None # Input device index (None = default)
    output_device: Optional[int] = None # Output device index (None = default)
    phi_source: PhiSource = PhiSource.INTERNAL  # Φ modulation source
    metrics_broadcast_interval: float = 0.033   # Metrics update interval (30 Hz)
    enable_logging: bool = True


@dataclass
class HybridMetrics:
    """Real-time metrics from hybrid processing"""
    timestamp: float
    ici: float                     # Inter-Criticality Interval
    phase_coherence: float         # Phase coherence [0, 1]
    spectral_centroid: float       # Spectral centroid (Hz)
    consciousness_level: float     # Consciousness level [0, 1]
    phi_phase: float               # Current Φ phase
    phi_depth: float               # Current Φ depth
    cpu_load: float                # Processing CPU load [0, 1]
    latency_ms: float              # Processing latency (ms)
    dropouts: int                  # Audio dropout count


class PhiModulator:
    """
    Feeds real or synthetic Φ waveform into HybridNode

    Supports multiple modulation sources:
    - Internal: Auto-generated golden ratio modulation
    - Manual: User-controlled slider values
    - Microphone: Live audio envelope extraction
    - Sensor: External sensor input (future)
    """

    def __init__(self, source: PhiSource = PhiSource.INTERNAL):
        """
        Initialize PhiModulator

        Args:
            source: Modulation source type
        """
        self.source = source
        self.manual_phase = 0.0
        self.manual_depth = 0.5

        # Microphone input buffer for envelope extraction
        self.mic_buffer = np.zeros(512, dtype=np.float32)
        self.mic_envelope = 0.0

        # Internal auto-modulation state
        self.internal_phase = 0.0
        self.internal_phase_increment = 0.0

        # Time tracking
        self.last_update_time = time.time()

    def update(self, dt: float = 0.0) -> tuple[float, float]:
        """
        Update and get current Φ phase and depth

        Args:
            dt: Time delta since last update (seconds)

        Returns:
            (phi_phase, phi_depth) tuple
        """
        if self.source == PhiSource.MANUAL:
            # Return user-controlled values
            return (self.manual_phase, self.manual_depth)

        elif self.source == PhiSource.MICROPHONE:
            # Extract envelope from microphone input
            envelope = np.mean(np.abs(self.mic_buffer))
            self.mic_envelope = 0.9 * self.mic_envelope + 0.1 * envelope

            # Map envelope to Φ depth
            phi_depth = np.clip(self.mic_envelope * 2.0, 0.0, 1.0)

            # Phase advances based on envelope
            phase_rate = 2 * np.pi * (1.0 + self.mic_envelope)
            self.internal_phase += phase_rate * dt
            self.internal_phase = self.internal_phase % (2 * np.pi)

            return (self.internal_phase, phi_depth)

        elif self.source == PhiSource.INTERNAL:
            # Auto-generated golden ratio modulation
            # Phase advances at Φ-related rate
            PHI_INV = 0.618033988749895
            phase_rate = 2 * np.pi * PHI_INV  # ~3.88 rad/s
            self.internal_phase += phase_rate * dt
            self.internal_phase = self.internal_phase % (2 * np.pi)

            # Depth varies sinusoidally
            phi_depth = 0.5 + 0.3 * np.sin(self.internal_phase * 0.5)

            return (self.internal_phase, phi_depth)

        elif self.source == PhiSource.SENSOR:
            # Future: external sensor integration
            return (0.0, 0.5)

        else:
            return (0.0, 0.5)

    def set_manual(self, phase: float, depth: float):
        """
        Set manual Φ values

        Args:
            phase: Phase in radians [0, 2π]
            depth: Depth [0, 1]
        """
        self.manual_phase = phase % (2 * np.pi)
        self.manual_depth = np.clip(depth, 0.0, 1.0)

    def set_source(self, source: PhiSource):
        """
        Change modulation source

        Args:
            source: New modulation source
        """
        self.source = source

    def feed_microphone_input(self, audio_data: np.ndarray):
        """
        Feed microphone data for envelope extraction

        Args:
            audio_data: Audio samples (mono, float32)
        """
        if audio_data.size > 0:
            self.mic_buffer = audio_data[:512].astype(np.float32)


class HybridNode:
    """
    HybridNode - Analog-Digital Bridge for D-ASE Engine

    Manages real-time audio I/O and integrates with ChromaticFieldProcessor
    for consciousness-aware analog signal processing.
    """

    def __init__(self, config: Optional[HybridNodeConfig] = None):
        """
        Initialize HybridNode

        Args:
            config: Configuration (uses defaults if None)
        """
        self.config = config or HybridNodeConfig()

        # Initialize ChromaticFieldProcessor (D-ASE engine)
        print(f"[HybridNode] Initializing ChromaticFieldProcessor...")
        self.processor = ChromaticFieldProcessor(
            num_channels=self.config.num_channels,
            sample_rate=self.config.sample_rate,
            block_size=self.config.block_size
        )

        # Initialize Φ modulator
        self.phi_modulator = PhiModulator(source=self.config.phi_source)

        # Optional PhiRouter for sensor binding (Feature 011)
        self.phi_router: Optional[PhiRouter] = None
        self.sensor_inputs: Dict[str, any] = {}  # Active sensor inputs
        self.audio_beat_detector: Optional[AudioBeatDetector] = None

        # Audio stream
        self.stream = None
        self.is_running = False

        # Metrics storage and broadcasting
        self.current_metrics = None
        self.metrics_queue = queue.Queue(maxsize=100)
        self.metrics_callbacks: List[Callable[[HybridMetrics], None]] = []

        # Performance tracking
        self.process_time_history = []
        self.dropout_count = 0
        self.frame_count = 0

        # Threading
        self.metrics_thread = None
        self.metrics_lock = threading.Lock()

        # Time tracking
        self.last_callback_time = time.time()

        if self.config.enable_logging:
            print(f"[HybridNode] Initialized:")
            print(f"  Sample rate: {self.config.sample_rate} Hz")
            print(f"  Block size: {self.config.block_size} samples")
            print(f"  Channels: {self.config.num_channels}")
            print(f"  Φ source: {self.config.phi_source.value}")

    def _audio_callback(self, indata: np.ndarray, outdata: np.ndarray, frames: int,
                       time_info, status):
        """
        Real-time audio callback (FR-002)

        Called by sounddevice for each audio block. Must be low-latency and lock-free.

        Args:
            indata: Input audio data [frames, channels]
            outdata: Output audio data [frames, channels]
            frames: Number of frames
            time_info: Timing information
            status: Stream status flags
        """
        start_time = time.perf_counter()

        # Check for dropouts
        if status:
            self.dropout_count += 1
            if self.config.enable_logging:
                print(f"[HybridNode] Audio dropout: {status}")

        try:
            # Extract mono input (mix down all input channels)
            if indata.ndim == 2:
                mono_input = np.mean(indata, axis=1).astype(np.float32)
            else:
                mono_input = indata[:, 0].astype(np.float32)

            # Update Φ modulator
            current_time = time.perf_counter()
            dt = current_time - self.last_callback_time
            self.last_callback_time = current_time

            # Use PhiRouter if available (Feature 011), otherwise use PhiModulator
            if self.phi_router:
                # Get Φ from router (which manages multiple sources)
                phi_value, phi_phase = self.phi_router.get_current_phi()
                phi_depth = phi_value  # Use Φ value as depth

                # Feed audio to beat detector if active
                if self.audio_beat_detector:
                    self.audio_beat_detector.process_audio(mono_input, self.config.sample_rate)
            else:
                # Use simple PhiModulator
                phi_phase, phi_depth = self.phi_modulator.update(dt)

                # Feed microphone input to modulator if needed
                if self.phi_modulator.source == PhiSource.MICROPHONE:
                    self.phi_modulator.feed_microphone_input(mono_input)

            # Process through ChromaticFieldProcessor (FR-006)
            # Returns [num_channels, block_size] multi-channel output
            processed_output = self.processor.processBlock(
                input_block=mono_input,
                phi_phase=phi_phase,
                phi_depth=phi_depth
            )

            # Mix multi-channel output to stereo/multi-channel output
            # For now, mix channels down to output channels
            num_output_channels = outdata.shape[1] if outdata.ndim == 2 else 1

            if num_output_channels == 1:
                # Mono output: average all channels
                outdata[:, 0] = np.mean(processed_output, axis=0)
            elif num_output_channels == 2:
                # Stereo output: split channels
                outdata[:, 0] = np.mean(processed_output[:4], axis=0)  # Left: channels 0-3
                outdata[:, 1] = np.mean(processed_output[4:], axis=0)  # Right: channels 4-7
            else:
                # Multi-channel output: map directly
                for ch in range(min(num_output_channels, self.config.num_channels)):
                    outdata[:, ch] = processed_output[ch]

            # Calculate processing time
            elapsed = time.perf_counter() - start_time
            self.process_time_history.append(elapsed)
            if len(self.process_time_history) > 100:
                self.process_time_history.pop(0)

            # Get metrics from processor (lightweight, already calculated)
            metrics_dict = self.processor.getMetrics()

            # Create metrics snapshot
            latency_ms = elapsed * 1000
            cpu_load = elapsed / (frames / self.config.sample_rate) if frames > 0 else 0.0

            metrics = HybridMetrics(
                timestamp=time.time(),
                ici=metrics_dict['ici'],
                phase_coherence=metrics_dict['phase_coherence'],
                spectral_centroid=metrics_dict['spectral_centroid'],
                consciousness_level=metrics_dict['consciousness_level'],
                phi_phase=phi_phase,
                phi_depth=phi_depth,
                cpu_load=cpu_load,
                latency_ms=latency_ms,
                dropouts=self.dropout_count
            )

            # Store current metrics (non-blocking)
            with self.metrics_lock:
                self.current_metrics = metrics

            # Enqueue for broadcasting (non-blocking)
            try:
                self.metrics_queue.put_nowait(metrics)
            except queue.Full:
                # Drop oldest if queue full
                try:
                    self.metrics_queue.get_nowait()
                    self.metrics_queue.put_nowait(metrics)
                except:
                    pass

            self.frame_count += 1

        except Exception as e:
            if self.config.enable_logging:
                print(f"[HybridNode] Audio callback error: {e}")
            # Output silence on error
            outdata.fill(0.0)

    def _metrics_broadcast_loop(self):
        """
        Metrics broadcasting thread (FR-007, SC-003)

        Runs in background, broadcasting metrics at configured interval (≥30 Hz)
        """
        while self.is_running:
            try:
                # Get metrics from queue (blocking with timeout)
                metrics = self.metrics_queue.get(timeout=self.config.metrics_broadcast_interval)

                # Call all registered callbacks
                for callback in self.metrics_callbacks:
                    try:
                        callback(metrics)
                    except Exception as e:
                        if self.config.enable_logging:
                            print(f"[HybridNode] Metrics callback error: {e}")

            except queue.Empty:
                # No new metrics, continue
                pass
            except Exception as e:
                if self.config.enable_logging:
                    print(f"[HybridNode] Metrics broadcast error: {e}")

    def start(self) -> bool:
        """
        Start hybrid mode processing (SC-001)

        Returns:
            True if started successfully, False otherwise
        """
        if self.is_running:
            if self.config.enable_logging:
                print("[HybridNode] Already running")
            return False

        try:
            if self.config.enable_logging:
                print("[HybridNode] Starting hybrid mode...")

            # Start audio stream
            self.stream = sd.Stream(
                samplerate=self.config.sample_rate,
                blocksize=self.config.block_size,
                device=(self.config.input_device, self.config.output_device),
                channels=(2, 2),  # Stereo I/O (can be configured)
                dtype=np.float32,
                callback=self._audio_callback,
                finished_callback=None
            )

            self.stream.start()
            self.is_running = True

            # Start metrics broadcasting thread
            self.metrics_thread = threading.Thread(
                target=self._metrics_broadcast_loop,
                daemon=True
            )
            self.metrics_thread.start()

            if self.config.enable_logging:
                print("[HybridNode] ✓ Hybrid mode started")

            return True

        except Exception as e:
            if self.config.enable_logging:
                print(f"[HybridNode] Failed to start: {e}")
            self.is_running = False
            return False

    def stop(self) -> bool:
        """
        Stop hybrid mode processing

        Returns:
            True if stopped successfully, False otherwise
        """
        if not self.is_running:
            if self.config.enable_logging:
                print("[HybridNode] Not running")
            return False

        try:
            if self.config.enable_logging:
                print("[HybridNode] Stopping hybrid mode...")

            self.is_running = False

            # Stop audio stream
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None

            # Wait for metrics thread
            if self.metrics_thread and self.metrics_thread.is_alive():
                self.metrics_thread.join(timeout=1.0)

            if self.config.enable_logging:
                print("[HybridNode] ✓ Hybrid mode stopped")

            return True

        except Exception as e:
            if self.config.enable_logging:
                print(f"[HybridNode] Failed to stop: {e}")
            return False

    def set_phi_source(self, source: PhiSource):
        """
        Change Φ modulation source (FR-004)

        Args:
            source: New modulation source
        """
        self.phi_modulator.set_source(source)
        if self.config.enable_logging:
            print(f"[HybridNode] Φ source changed to: {source.value}")

    def set_phi_manual(self, phase: float, depth: float):
        """
        Set manual Φ values (FR-004)

        Args:
            phase: Phase in radians [0, 2π]
            depth: Depth [0, 1]
        """
        self.phi_modulator.set_manual(phase, depth)

    def get_current_metrics(self) -> Optional[HybridMetrics]:
        """
        Get current metrics snapshot

        Returns:
            Latest HybridMetrics or None if not running
        """
        with self.metrics_lock:
            return self.current_metrics

    def register_metrics_callback(self, callback: Callable[[HybridMetrics], None]):
        """
        Register callback for metrics updates (FR-007)

        Callback will be called at configured interval (≥30 Hz)

        Args:
            callback: Function to call with HybridMetrics
        """
        self.metrics_callbacks.append(callback)

    def unregister_metrics_callback(self, callback: Callable[[HybridMetrics], None]):
        """
        Unregister metrics callback

        Args:
            callback: Function to remove
        """
        if callback in self.metrics_callbacks:
            self.metrics_callbacks.remove(callback)

    def get_statistics(self) -> Dict:
        """
        Get performance statistics

        Returns:
            Dictionary with performance stats
        """
        if not self.process_time_history:
            return {
                "avg_latency_ms": 0.0,
                "max_latency_ms": 0.0,
                "min_latency_ms": 0.0,
                "avg_cpu_load": 0.0,
                "dropout_count": self.dropout_count,
                "frame_count": self.frame_count,
                "is_running": self.is_running
            }

        times_ms = [t * 1000 for t in self.process_time_history]
        block_time_ms = (self.config.block_size / self.config.sample_rate) * 1000

        return {
            "avg_latency_ms": np.mean(times_ms),
            "max_latency_ms": np.max(times_ms),
            "min_latency_ms": np.min(times_ms),
            "avg_cpu_load": np.mean(times_ms) / block_time_ms if block_time_ms > 0 else 0.0,
            "dropout_count": self.dropout_count,
            "frame_count": self.frame_count,
            "is_running": self.is_running
        }

    def reset_statistics(self):
        """Reset performance statistics"""
        self.process_time_history.clear()
        self.dropout_count = 0
        self.frame_count = 0

    # Sensor Binding Methods (Feature 011)

    def enable_sensor_binding(self) -> bool:
        """
        Enable sensor binding with PhiRouter (Feature 011)

        Returns:
            True if enabled successfully
        """
        if not SENSOR_BINDING_AVAILABLE:
            if self.config.enable_logging:
                print("[HybridNode] Sensor binding not available (missing phi_router/phi_sensor_bridge)")
            return False

        if self.phi_router:
            if self.config.enable_logging:
                print("[HybridNode] Sensor binding already enabled")
            return True

        # Create PhiRouter
        router_config = PhiRouterConfig(enable_logging=self.config.enable_logging)
        self.phi_router = PhiRouter(router_config)

        # Register internal and manual sources
        self.phi_router.register_source("internal", PhiSourcePriority.INTERNAL)
        self.phi_router.register_source("manual", PhiSourcePriority.MANUAL)

        # Start router
        self.phi_router.start()

        if self.config.enable_logging:
            print("[HybridNode] ✓ Sensor binding enabled")

        return True

    def disable_sensor_binding(self):
        """Disable sensor binding and stop all sensor inputs"""
        # Stop all sensor inputs
        for sensor_id, sensor_input in self.sensor_inputs.items():
            if hasattr(sensor_input, 'stop'):
                sensor_input.stop()

        self.sensor_inputs.clear()

        # Stop router
        if self.phi_router:
            self.phi_router.stop()
            self.phi_router = None

        if self.config.enable_logging:
            print("[HybridNode] Sensor binding disabled")

    def bind_midi_sensor(self, device_id: Optional[str] = None, cc_number: int = 1, channel: int = 0) -> bool:
        """
        Bind MIDI controller as Φ source (Feature 011, FR-001)

        Args:
            device_id: MIDI device name (None = first available)
            cc_number: MIDI CC number to monitor (0-127)
            channel: MIDI channel (0-15)

        Returns:
            True if bound successfully
        """
        if not self.phi_router:
            if not self.enable_sensor_binding():
                return False

        sensor_id = f"midi_cc{cc_number}"

        # Create MIDI input
        config = SensorConfig(
            sensor_type=SensorType.MIDI_CC,
            device_id=device_id,
            midi_cc_number=cc_number,
            midi_channel=channel,
            enable_logging=self.config.enable_logging
        )

        def midi_callback(data: SensorData):
            self.phi_router.update_source(sensor_id, data)

        midi_input = MIDIInput(config, midi_callback)

        if not midi_input.connect():
            return False

        # Register with router
        self.phi_router.register_source(sensor_id, PhiSourcePriority.MIDI)

        # Start MIDI input
        if not midi_input.start():
            return False

        self.sensor_inputs[sensor_id] = midi_input

        if self.config.enable_logging:
            print(f"[HybridNode] ✓ MIDI CC{cc_number} bound")

        return True

    def bind_serial_sensor(self, device_id: Optional[str] = None, baudrate: int = 9600,
                          input_range: tuple[float, float] = (0.0, 1.0)) -> bool:
        """
        Bind serial sensor as Φ source (Feature 011, FR-001)

        Args:
            device_id: Serial port name (None = first available)
            baudrate: Serial baudrate
            input_range: Expected input value range

        Returns:
            True if bound successfully
        """
        if not self.phi_router:
            if not self.enable_sensor_binding():
                return False

        sensor_id = f"serial_{device_id or 'auto'}"

        # Create serial sensor input
        config = SensorConfig(
            sensor_type=SensorType.SERIAL_ANALOG,
            device_id=device_id,
            serial_baudrate=baudrate,
            input_range=input_range,
            enable_logging=self.config.enable_logging
        )

        def serial_callback(data: SensorData):
            self.phi_router.update_source(sensor_id, data)

        serial_input = SerialSensorInput(config, serial_callback)

        if not serial_input.connect():
            return False

        # Register with router
        self.phi_router.register_source(sensor_id, PhiSourcePriority.SERIAL)

        # Start serial input
        if not serial_input.start():
            return False

        self.sensor_inputs[sensor_id] = serial_input

        if self.config.enable_logging:
            print(f"[HybridNode] ✓ Serial sensor bound: {device_id}")

        return True

    def bind_audio_beat_detector(self) -> bool:
        """
        Bind audio beat detector as Φ source (Feature 011, FR-001)

        Returns:
            True if bound successfully
        """
        if not self.phi_router:
            if not self.enable_sensor_binding():
                return False

        sensor_id = "audio_beat"

        # Create beat detector
        config = SensorConfig(
            sensor_type=SensorType.AUDIO_BEAT,
            enable_logging=self.config.enable_logging
        )

        def beat_callback(data: SensorData):
            self.phi_router.update_source(sensor_id, data)

        self.audio_beat_detector = AudioBeatDetector(config, beat_callback)

        # Register with router
        self.phi_router.register_source(sensor_id, PhiSourcePriority.AUDIO_BEAT)

        if self.config.enable_logging:
            print(f"[HybridNode] ✓ Audio beat detector bound")

        return True

    def unbind_sensor(self, sensor_id: str) -> bool:
        """
        Unbind a sensor

        Args:
            sensor_id: Sensor identifier to unbind

        Returns:
            True if unbound successfully
        """
        if sensor_id in self.sensor_inputs:
            sensor_input = self.sensor_inputs[sensor_id]

            if hasattr(sensor_input, 'stop'):
                sensor_input.stop()

            del self.sensor_inputs[sensor_id]

            if self.phi_router:
                self.phi_router.unregister_source(sensor_id)

            if self.config.enable_logging:
                print(f"[HybridNode] Sensor unbound: {sensor_id}")

            return True

        return False

    def get_sensor_status(self) -> Dict:
        """
        Get sensor binding status (Feature 011, FR-004)

        Returns:
            Dictionary with sensor status
        """
        if not self.phi_router:
            return {
                "sensor_binding_enabled": False,
                "active_sensors": [],
                "router_status": None
            }

        router_status = self.phi_router.get_status()

        return {
            "sensor_binding_enabled": True,
            "active_sensors": list(self.sensor_inputs.keys()),
            "router_status": asdict(router_status)
        }

    @staticmethod
    def list_midi_devices() -> List[str]:
        """
        List available MIDI devices

        Returns:
            List of MIDI device names
        """
        if not SENSOR_BINDING_AVAILABLE:
            return []

        return MIDIInput.list_devices()

    @staticmethod
    def list_serial_devices() -> List[str]:
        """
        List available serial devices

        Returns:
            List of serial port names
        """
        if not SENSOR_BINDING_AVAILABLE:
            return []

        return SerialSensorInput.list_devices()

    @staticmethod
    def list_audio_devices() -> List[Dict]:
        """
        List available audio devices

        Returns:
            List of device dictionaries with name, channels, etc.
        """
        devices = []
        for i, dev in enumerate(sd.query_devices()):
            devices.append({
                "index": i,
                "name": dev['name'],
                "max_input_channels": dev['max_input_channels'],
                "max_output_channels": dev['max_output_channels'],
                "default_samplerate": dev['default_samplerate']
            })
        return devices


# Self-test function
def _self_test():
    """Run basic self-test of HybridNode"""
    print("=" * 60)
    print("HybridNode Self-Test")
    print("=" * 60)

    try:
        # List audio devices
        print("\n1. Listing audio devices...")
        devices = HybridNode.list_audio_devices()
        print(f"   Found {len(devices)} audio devices:")
        for dev in devices[:5]:  # Show first 5
            print(f"   [{dev['index']}] {dev['name']}")

        # Create HybridNode
        print("\n2. Creating HybridNode...")
        config = HybridNodeConfig(enable_logging=True)
        node = HybridNode(config)
        print("   ✓ HybridNode created")

        # Test Φ modulator
        print("\n3. Testing Φ modulator...")
        phase, depth = node.phi_modulator.update(0.1)
        print(f"   Internal modulation: phase={phase:.2f}, depth={depth:.2f}")

        node.set_phi_source(PhiSource.MANUAL)
        node.set_phi_manual(1.57, 0.7)
        phase, depth = node.phi_modulator.update(0.0)
        print(f"   Manual modulation: phase={phase:.2f}, depth={depth:.2f}")
        print("   ✓ Φ modulator working")

        # Register metrics callback
        print("\n4. Registering metrics callback...")
        metrics_received = []

        def metrics_callback(metrics: HybridMetrics):
            metrics_received.append(metrics)

        node.register_metrics_callback(metrics_callback)
        print("   ✓ Callback registered")

        # Start hybrid mode (brief test)
        print("\n5. Starting hybrid mode (3 second test)...")
        if node.start():
            print("   ✓ Hybrid mode started")

            # Run for 3 seconds
            time.sleep(3.0)

            # Get statistics
            stats = node.get_statistics()
            print(f"\n   Performance Statistics:")
            print(f"   - Frames processed: {stats['frame_count']}")
            print(f"   - Average latency: {stats['avg_latency_ms']:.2f} ms")
            print(f"   - Max latency: {stats['max_latency_ms']:.2f} ms")
            print(f"   - CPU load: {stats['avg_cpu_load']*100:.1f}%")
            print(f"   - Dropouts: {stats['dropout_count']}")

            # Check metrics broadcasting
            print(f"\n   Metrics received: {len(metrics_received)}")
            if metrics_received:
                latest = metrics_received[-1]
                print(f"   Latest metrics:")
                print(f"   - ICI: {latest.ici:.4f}")
                print(f"   - Coherence: {latest.phase_coherence:.4f}")
                print(f"   - Centroid: {latest.spectral_centroid:.1f} Hz")
                print(f"   - Consciousness: {latest.consciousness_level:.4f}")

            # Check success criteria
            print(f"\n   Success Criteria:")
            sc001 = stats['dropout_count'] == 0
            sc002 = stats['max_latency_ms'] < 2.0
            sc003 = len(metrics_received) >= 90  # Should get ~90 metrics in 3s at 30Hz
            sc004 = stats['avg_cpu_load'] < 0.5

            print(f"   SC-001 (No dropouts): {'✓ PASS' if sc001 else '✗ FAIL'}")
            print(f"   SC-002 (Latency < 2ms): {'✓ PASS' if sc002 else '✗ FAIL'} ({stats['max_latency_ms']:.2f}ms)")
            print(f"   SC-003 (Metrics ≥30Hz): {'✓ PASS' if sc003 else '✗ FAIL'} ({len(metrics_received)/3:.1f}Hz)")
            print(f"   SC-004 (CPU < 50%): {'✓ PASS' if sc004 else '✗ FAIL'} ({stats['avg_cpu_load']*100:.1f}%)")

            # Stop
            node.stop()
            print("   ✓ Hybrid mode stopped")

            passed = sc001 and sc002 and sc003 and sc004
        else:
            print("   ✗ Failed to start hybrid mode")
            passed = False

        print("\n" + "=" * 60)
        if passed:
            print("Self-Test PASSED ✓")
        else:
            print("Self-Test FAILED ✗")
        print("=" * 60)
        return passed

    except Exception as e:
        print(f"\n✗ Self-Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    _self_test()
