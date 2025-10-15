"""
AudioServer - Real-Time Audio Processing Pipeline

Integrates all components:
- sounddevice audio I/O
- ChromaticFieldProcessor (D-ASE engine)
- Φ-Modulation
- 8-channel → stereo downmix
- Latency compensation
- Metrics generation and streaming
- Synchronized timestamping

Implements FR-001, FR-002, FR-003, FR-004, FR-005, FR-008
"""

import numpy as np
import sounddevice as sd
import time
import threading
from queue import Queue, Empty
from typing import Optional, Callable, Dict
import traceback

from chromatic_field_processor import ChromaticFieldProcessor
from phi_modulator_controller import PhiModulatorController
from downmix import StereoDownmixer
from latency_manager import LatencyManager
from metrics_frame import MetricsFrame, create_default_metrics_frame
from latency_frame import LatencyFrame
from metrics_logger import MetricsLogger
from latency_logger import LatencyLogger


class AudioServer:
    """
    Complete real-time audio processing server

    Features:
    - 48kHz @ 512 samples audio processing
    - <10ms end-to-end latency
    - Real-time metrics at ≥30Hz
    - Latency compensation and drift correction
    - Thread-safe component integration
    """

    # Audio configuration (from FR-001)
    SAMPLE_RATE = 48000
    BUFFER_SIZE = 512
    INPUT_CHANNELS = 1  # Mono input
    OUTPUT_CHANNELS = 2  # Stereo output

    # Performance targets
    TARGET_LATENCY_MS = 10.0
    TARGET_METRICS_FPS = 30

    def __init__(self,
                 input_device: Optional[int] = None,
                 output_device: Optional[int] = None,
                 enable_logging: bool = True):
        """
        Initialize audio server

        Args:
            input_device: Input device index (None = default)
            output_device: Output device index (None = default)
            enable_logging: Enable metrics/latency logging
        """
        print("=" * 60)
        print("AudioServer Initialization")
        print("=" * 60)

        self.input_device = input_device
        self.output_device = output_device
        self.enable_logging = enable_logging

        # Audio stream
        self.stream: Optional[sd.Stream] = None
        self.is_running = False

        # Processing components
        print("\n[AudioServer] Initializing processing components...")

        self.processor = ChromaticFieldProcessor(
            sample_rate=self.SAMPLE_RATE,
            buffer_size=self.BUFFER_SIZE
        )

        self.phi_controller = PhiModulatorController(
            sample_rate=self.SAMPLE_RATE
        )

        self.downmixer = StereoDownmixer(
            num_channels=8,
            strategy="spatial"
        )

        self.latency_manager = LatencyManager(
            sample_rate=self.SAMPLE_RATE,
            buffer_size=self.BUFFER_SIZE,
            input_device=input_device,
            output_device=output_device
        )

        # Logging
        self.metrics_logger: Optional[MetricsLogger] = None
        self.latency_logger: Optional[LatencyLogger] = None

        if enable_logging:
            print("\n[AudioServer] Initializing loggers...")
            self.metrics_logger = MetricsLogger()
            self.latency_logger = LatencyLogger()

        # Metrics/latency frame queues (for API/WebSocket consumption)
        self.metrics_queue = Queue(maxsize=2)  # Double buffer
        self.latency_queue = Queue(maxsize=2)

        # Callbacks for external consumers (e.g., WebSocket streamers)
        self.metrics_callback: Optional[Callable[[MetricsFrame], None]] = None
        self.latency_callback: Optional[Callable[[LatencyFrame], None]] = None

        # Performance tracking
        self.callback_count = 0
        self.last_metrics_time = 0.0
        self.last_latency_update = 0.0
        self.processing_time_history = []

        # State
        self.current_preset: Optional[Dict] = None

        print("\n[AudioServer] ✓ Initialization complete")
        print("=" * 60)

    def _audio_callback(self, indata: np.ndarray, outdata: np.ndarray,
                       frames: int, time_info, status):
        """
        Audio callback - processes audio in real-time

        This is the critical path - must complete within buffer duration (~10.7ms)

        Args:
            indata: Input audio (frames, 1)
            outdata: Output audio (frames, 2)
            frames: Number of frames (should be BUFFER_SIZE)
            time_info: Timing information
            status: Stream status
        """
        callback_start = time.perf_counter()

        try:
            # Check for buffer issues
            if status:
                print(f"[AudioServer] Stream status: {status}")

            # Get monotonic timestamp for synchronization
            callback_time = time.time()

            # Extract mono input
            input_mono = indata[:, 0] if indata.shape[1] > 0 else np.zeros(frames)

            # --- Update Φ-Modulation ---
            # Pass audio block for envelope following
            phi_state = self.phi_controller.update(audio_block=input_mono)

            # --- Process through D-ASE Engine ---
            # Returns 8-channel output + metrics
            multi_channel, metrics_dict = self.processor.processBlock(
                input_mono,
                phi_phase=phi_state.phase,
                phi_depth=phi_state.depth
            )

            # --- Downmix 8-channel → Stereo ---
            stereo = self.downmixer.downmix(multi_channel)

            # --- Apply Latency Compensation ---
            compensated = self.latency_manager.compensate_block(stereo)

            # --- Update Latency Timing ---
            self.latency_manager.update_timing(callback_time)

            # --- Write to Output ---
            outdata[:] = compensated

            # --- Generate Metrics Frame ---
            metrics_frame = self._create_metrics_frame(
                metrics_dict,
                phi_state,
                callback_time
            )

            # --- Generate Latency Frame ---
            latency_frame = self.latency_manager.get_current_frame()
            latency_frame.timestamp = callback_time

            # Calculate actual processing time
            processing_time_ms = (time.perf_counter() - callback_start) * 1000.0
            self.processing_time_history.append(processing_time_ms)
            if len(self.processing_time_history) > 100:
                self.processing_time_history.pop(0)

            # Update CPU load estimate
            buffer_duration_ms = (self.BUFFER_SIZE / self.SAMPLE_RATE) * 1000.0
            cpu_load = processing_time_ms / buffer_duration_ms
            latency_frame.cpu_load = cpu_load

            # --- Publish Metrics (at target rate) ---
            time_since_metrics = callback_time - self.last_metrics_time
            metrics_interval = 1.0 / self.TARGET_METRICS_FPS

            if time_since_metrics >= metrics_interval:
                # Try to enqueue metrics (non-blocking)
                try:
                    self.metrics_queue.put_nowait(metrics_frame)

                    # Call external callback if set
                    if self.metrics_callback:
                        self.metrics_callback(metrics_frame)

                    # Log to file
                    if self.metrics_logger:
                        self.metrics_logger.log_frame(metrics_frame)

                    self.last_metrics_time = callback_time

                except:
                    pass  # Queue full, skip this frame

            # --- Publish Latency Updates (every 100ms) ---
            time_since_latency = callback_time - self.last_latency_update

            if time_since_latency >= 0.1:  # 10 Hz
                try:
                    self.latency_queue.put_nowait(latency_frame)

                    # Call external callback if set
                    if self.latency_callback:
                        self.latency_callback(latency_frame)

                    # Log to file
                    if self.latency_logger:
                        self.latency_logger.log_frame(latency_frame)

                    self.last_latency_update = callback_time

                except:
                    pass  # Queue full, skip this frame

            self.callback_count += 1

            # Warn if processing time exceeds threshold (80% of buffer duration)
            if processing_time_ms > buffer_duration_ms * 0.8:
                print(f"[AudioServer] WARNING: High CPU load: {processing_time_ms:.2f} ms / {buffer_duration_ms:.2f} ms ({cpu_load*100:.1f}%)")

        except Exception as e:
            print(f"[AudioServer] ERROR in audio callback: {e}")
            traceback.print_exc()
            # Fill output with silence on error
            outdata.fill(0)

    def _create_metrics_frame(self, metrics_dict: Dict, phi_state, timestamp: float) -> MetricsFrame:
        """
        Create MetricsFrame from engine metrics and Φ state

        Args:
            metrics_dict: Metrics from ChromaticFieldProcessor
            phi_state: Current PhiState
            timestamp: Monotonic timestamp

        Returns:
            Complete MetricsFrame
        """
        frame = MetricsFrame(
            timestamp=timestamp,
            ici=metrics_dict.get('ici', 0.0),
            phase_coherence=metrics_dict.get('phase_coherence', 0.0),
            spectral_centroid=metrics_dict.get('spectral_centroid', 0.0),
            criticality=metrics_dict.get('criticality', 0.0),
            consciousness_level=metrics_dict.get('consciousness_level', 0.0),
            state='IDLE',  # Will be classified by classify_state()
            phi_phase=phi_state.phase,
            phi_depth=phi_state.depth,
            phi_mode=phi_state.mode
        )

        # Classify state based on metrics
        frame.state = frame.classify_state()

        return frame

    def start(self, calibrate_latency: bool = False) -> bool:
        """
        Start audio server

        Args:
            calibrate_latency: Run latency calibration before starting

        Returns:
            True if started successfully
        """
        if self.is_running:
            print("[AudioServer] Already running")
            return True

        print("\n[AudioServer] Starting audio server...")

        # Optional latency calibration
        if calibrate_latency:
            print("\n[AudioServer] Running latency calibration...")
            print("[AudioServer] Ensure audio loopback is connected!")

            success = self.latency_manager.calibrate()

            if not success:
                print("[AudioServer] WARNING: Calibration failed, continuing with default latency estimates")
            else:
                print("[AudioServer] ✓ Calibration complete")

                # Log calibration event
                if self.latency_logger:
                    latency_frame = self.latency_manager.get_current_frame()
                    self.latency_logger.log_calibration_event(True, {
                        'total_latency_ms': latency_frame.total_measured_ms,
                        'quality': latency_frame.calibration_quality
                    })

        try:
            # Create audio stream
            print(f"\n[AudioServer] Opening audio stream...")
            print(f"[AudioServer]   Sample rate: {self.SAMPLE_RATE} Hz")
            print(f"[AudioServer]   Buffer size: {self.BUFFER_SIZE} samples")
            print(f"[AudioServer]   Input device: {self.input_device or 'default'}")
            print(f"[AudioServer]   Output device: {self.output_device or 'default'}")

            self.stream = sd.Stream(
                samplerate=self.SAMPLE_RATE,
                blocksize=self.BUFFER_SIZE,
                channels=(self.INPUT_CHANNELS, self.OUTPUT_CHANNELS),
                dtype=np.float32,
                callback=self._audio_callback,
                device=(self.input_device, self.output_device),
                latency='low'
            )

            # Start stream
            self.stream.start()
            self.is_running = True

            # Reset performance counters
            self.callback_count = 0
            self.last_metrics_time = time.time()
            self.last_latency_update = time.time()
            self.processing_time_history = []

            print("[AudioServer] ✓ Audio stream started")
            print("[AudioServer] Processing audio in real-time...")

            return True

        except Exception as e:
            print(f"[AudioServer] ✗ Failed to start audio stream: {e}")
            traceback.print_exc()
            return False

    def stop(self):
        """Stop audio server"""
        if not self.is_running:
            print("[AudioServer] Not running")
            return

        print("\n[AudioServer] Stopping audio server...")

        try:
            # Stop stream
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None

            self.is_running = False

            # Close loggers
            if self.metrics_logger:
                self.metrics_logger.close()

            if self.latency_logger:
                self.latency_logger.close()

            print("[AudioServer] ✓ Audio server stopped")

            # Print statistics
            self._print_statistics()

        except Exception as e:
            print(f"[AudioServer] Error stopping: {e}")
            traceback.print_exc()

    def _print_statistics(self):
        """Print session statistics"""
        print("\n" + "=" * 60)
        print("Audio Server Statistics")
        print("=" * 60)

        print(f"\nAudio Processing:")
        print(f"  Callbacks: {self.callback_count}")
        print(f"  Sample rate: {self.SAMPLE_RATE} Hz")
        print(f"  Buffer size: {self.BUFFER_SIZE} samples")

        if self.processing_time_history:
            avg_time = np.mean(self.processing_time_history)
            max_time = np.max(self.processing_time_history)
            buffer_duration = (self.BUFFER_SIZE / self.SAMPLE_RATE) * 1000.0

            print(f"\nProcessing Performance:")
            print(f"  Average: {avg_time:.2f} ms / {buffer_duration:.2f} ms ({avg_time/buffer_duration*100:.1f}%)")
            print(f"  Peak: {max_time:.2f} ms ({max_time/buffer_duration*100:.1f}%)")

        # Latency statistics
        latency_stats = self.latency_manager.get_statistics()
        print(f"\nLatency:")
        print(f"  Calibrated: {latency_stats['calibrated']}")
        print(f"  Total measured: {latency_stats['latency']['total_measured_ms']:.2f} ms")
        print(f"  Effective: {latency_stats['effective_latency_ms']:.2f} ms")
        print(f"  Aligned: {latency_stats['aligned']}")

        # Drift statistics
        drift_stats = latency_stats['drift']
        print(f"\nDrift:")
        print(f"  Current: {drift_stats['current_drift_ms']:.3f} ms")
        print(f"  Rate: {drift_stats['drift_rate_ms_per_sec']:.4f} ms/s")
        print(f"  Cumulative: {drift_stats['cumulative_drift_ms']:.3f} ms")

        # Logging statistics
        if self.metrics_logger:
            metrics_stats = self.metrics_logger.get_session_statistics()
            print(f"\nMetrics Logging:")
            print(f"  Frames: {metrics_stats['frame_count']}")
            print(f"  Average FPS: {metrics_stats['average_fps']:.1f}")
            print(f"  Gaps: {metrics_stats['gap_count']}")

        if self.latency_logger:
            latency_log_stats = self.latency_logger.get_session_statistics()
            print(f"\nLatency Logging:")
            print(f"  Frames: {latency_log_stats['frame_count']}")
            print(f"  Average FPS: {latency_log_stats['average_fps']:.1f}")

        print("=" * 60)

    def apply_preset(self, preset_data: Dict):
        """
        Apply preset configuration

        Args:
            preset_data: Preset dictionary
        """
        print(f"[AudioServer] Applying preset: {preset_data.get('name', 'Unknown')}")

        try:
            # Update engine parameters
            if 'engine' in preset_data:
                engine = preset_data['engine']

                # Update frequencies and amplitudes
                if 'frequencies' in engine:
                    self.processor.frequencies = np.array(engine['frequencies'], dtype=np.float64)

                if 'amplitudes' in engine:
                    self.processor.amplitudes = np.array(engine['amplitudes'], dtype=np.float64)

                if 'coupling_strength' in engine:
                    self.processor.coupling_strength = engine['coupling_strength']

            # Update Φ parameters
            if 'phi' in preset_data:
                phi = preset_data['phi']

                if 'mode' in phi:
                    self.phi_controller.set_mode(phi['mode'])

                if 'depth' in phi:
                    # Set manual depth if in manual mode
                    if self.phi_controller.get_current_mode() == 'manual':
                        self.phi_controller.sources['manual'].set_depth(phi['depth'])

                if 'phase' in phi:
                    if self.phi_controller.get_current_mode() == 'manual':
                        self.phi_controller.sources['manual'].set_phase(phi['phase'])

            # Update downmix parameters
            if 'downmix' in preset_data:
                downmix = preset_data['downmix']

                if 'strategy' in downmix:
                    self.downmixer.set_strategy(downmix['strategy'])

                if 'weights_l' in downmix:
                    self.downmixer.set_weights('L', np.array(downmix['weights_l']))

                if 'weights_r' in downmix:
                    self.downmixer.set_weights('R', np.array(downmix['weights_r']))

            self.current_preset = preset_data
            print("[AudioServer] ✓ Preset applied")

        except Exception as e:
            print(f"[AudioServer] ERROR applying preset: {e}")
            traceback.print_exc()

    def get_latest_metrics(self) -> Optional[MetricsFrame]:
        """
        Get latest metrics frame (non-blocking)

        Returns:
            Latest MetricsFrame or None
        """
        try:
            return self.metrics_queue.get_nowait()
        except Empty:
            return None

    def get_latest_latency(self) -> Optional[LatencyFrame]:
        """
        Get latest latency frame (non-blocking)

        Returns:
            Latest LatencyFrame or None
        """
        try:
            return self.latency_queue.get_nowait()
        except Empty:
            return None


# Self-test function
def _self_test():
    """Test AudioServer initialization"""
    print("=" * 60)
    print("AudioServer Self-Test")
    print("=" * 60)

    try:
        # Test initialization
        print("\n1. Testing AudioServer initialization...")
        server = AudioServer(enable_logging=False)

        assert server.SAMPLE_RATE == 48000
        assert server.BUFFER_SIZE == 512
        assert not server.is_running

        print("   ✓ Initialization OK")

        # Test preset application (without running)
        print("\n2. Testing preset application...")
        test_preset = {
            'name': 'Test Preset',
            'engine': {
                'coupling_strength': 1.5
            },
            'phi': {
                'mode': 'manual',
                'depth': 0.618
            },
            'downmix': {
                'strategy': 'energy'
            }
        }

        server.apply_preset(test_preset)
        print("   ✓ Preset application OK")

        print("\n" + "=" * 60)
        print("Self-Test PASSED ✓")
        print("=" * 60)
        print("\nNote: Full audio test requires audio hardware")
        print("To test audio processing:")
        print("  1. Ensure audio input/output devices are available")
        print("  2. Run: python audio_server.py")
        print("  3. Follow interactive prompts")

        return True

    except Exception as e:
        print(f"\n✗ Self-Test FAILED: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Run self-test
    success = _self_test()

    if success:
        print("\n" + "=" * 60)
        print("Interactive Audio Server Test")
        print("=" * 60)

        response = input("\nRun interactive audio test? (requires audio I/O) [y/N]: ")

        if response.lower() == 'y':
            print("\n[Test] Creating audio server...")
            server = AudioServer(enable_logging=True)

            calibrate = input("\nRun latency calibration? (requires loopback) [y/N]: ")
            should_calibrate = calibrate.lower() == 'y'

            print("\n[Test] Starting audio server...")
            if server.start(calibrate_latency=should_calibrate):
                print("\n✓ Audio server running!")
                print("\nSpeak into microphone or play audio...")
                print("Press Enter to stop")

                input()

                print("\n[Test] Stopping audio server...")
                server.stop()

                print("\n✓ Test complete")
            else:
                print("\n✗ Failed to start audio server")
