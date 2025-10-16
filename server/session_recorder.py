"""
Session Recorder - Feature 017
Records all key data streams (audio, metrics, Φ-modulation, controls) into synchronized logs

Implements:
- FR-001: SessionRecorder class
- FR-002: Capture from audio, metrics, phi, controls
- FR-003: Store to session folder /sessions/YYYYMMDD_HHMMSS/
- FR-004: File outputs (audio.wav, metrics.jsonl, controls.jsonl, phi.jsonl)
- FR-005: Optional MP4 export (future enhancement)
- FR-006: REST endpoints
- FR-007: Size estimation

Success Criteria:
- SC-001: Synchronization drift ≤5ms
- SC-002: Recording stability ≥30 min
- SC-003: Export reproducible (100% round-trip)
- SC-004: Replay latency <50ms difference
"""

import os
import json
import time
import wave
import threading
import numpy as np
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass
from queue import Queue, Empty
from datetime import datetime


@dataclass
class SessionRecorderConfig:
    """Configuration for Session Recorder"""

    # Base directory for sessions
    sessions_dir: str = "sessions"

    # Sample rate for audio recording
    sample_rate: int = 48000

    # Number of audio channels (stereo downmix)
    audio_channels: int = 2

    # Queue sizes for buffering
    audio_queue_size: int = 100
    metrics_queue_size: int = 1000
    phi_queue_size: int = 1000
    controls_queue_size: int = 1000

    # Flush interval (seconds) for file writes
    flush_interval: float = 1.0

    # Enable logging
    enable_logging: bool = True


class SessionRecorder:
    """
    Session Recorder for capturing synchronized data streams

    Records:
    - Audio output buffer (WAV format)
    - Metrics stream (JSONL format)
    - Phi parameters (JSONL format)
    - Control events (JSONL format)

    All streams synchronized with microsecond-precision timestamps.
    """

    def __init__(self, config: Optional[SessionRecorderConfig] = None):
        """
        Initialize Session Recorder

        Args:
            config: SessionRecorderConfig (uses defaults if None)
        """
        self.config = config or SessionRecorderConfig()

        # Recording state
        self.is_recording: bool = False
        self.session_path: Optional[Path] = None
        self.start_time: Optional[float] = None  # perf_counter for precise timing
        self.start_timestamp: Optional[datetime] = None  # datetime for folder name

        # Data queues (thread-safe)
        self.audio_queue: Queue = Queue(maxsize=self.config.audio_queue_size)
        self.metrics_queue: Queue = Queue(maxsize=self.config.metrics_queue_size)
        self.phi_queue: Queue = Queue(maxsize=self.config.phi_queue_size)
        self.controls_queue: Queue = Queue(maxsize=self.config.controls_queue_size)

        # File handles
        self.audio_file: Optional[wave.Wave_write] = None
        self.metrics_file: Optional[Any] = None
        self.phi_file: Optional[Any] = None
        self.controls_file: Optional[Any] = None

        # Writer threads
        self.audio_writer_thread: Optional[threading.Thread] = None
        self.data_writer_thread: Optional[threading.Thread] = None
        self.writer_stop_event: threading.Event = threading.Event()

        # Statistics
        self.audio_frames_written: int = 0
        self.metrics_frames_written: int = 0
        self.phi_frames_written: int = 0
        self.controls_events_written: int = 0
        self.total_bytes_written: int = 0

        # Last flush time
        self.last_flush_time: float = 0.0

        # Error state
        self.last_error: Optional[str] = None

        print("[SessionRecorder] Initialized")
        print(f"[SessionRecorder]   sessions_dir={self.config.sessions_dir}")
        print(f"[SessionRecorder]   sample_rate={self.config.sample_rate}")

    def start_recording(self) -> bool:
        """
        Start recording session (FR-002, FR-003)

        Returns:
            True if recording started successfully, False otherwise
        """
        if self.is_recording:
            self.last_error = "Already recording"
            return False

        try:
            # Create session folder with timestamp (FR-003)
            self.start_timestamp = datetime.now()
            session_name = self.start_timestamp.strftime("%Y%m%d_%H%M%S")

            sessions_dir = Path(self.config.sessions_dir)
            sessions_dir.mkdir(parents=True, exist_ok=True)

            self.session_path = sessions_dir / session_name
            self.session_path.mkdir(parents=True, exist_ok=True)

            # Reset start time for synchronized timestamps (SC-001)
            self.start_time = time.perf_counter()

            # Open files (FR-004)
            self._open_files()

            # Start writer threads
            self.writer_stop_event.clear()
            self.audio_writer_thread = threading.Thread(target=self._audio_writer_loop, daemon=True)
            self.data_writer_thread = threading.Thread(target=self._data_writer_loop, daemon=True)

            self.audio_writer_thread.start()
            self.data_writer_thread.start()

            # Reset statistics
            self.audio_frames_written = 0
            self.metrics_frames_written = 0
            self.phi_frames_written = 0
            self.controls_events_written = 0
            self.total_bytes_written = 0
            self.last_flush_time = time.time()

            self.is_recording = True
            self.last_error = None

            if self.config.enable_logging:
                print(f"[SessionRecorder] Recording started: {self.session_path}")

            return True

        except Exception as e:
            self.last_error = f"Failed to start recording: {e}"
            print(f"[SessionRecorder] ERROR: {self.last_error}")
            self._cleanup()
            return False

    def stop_recording(self) -> bool:
        """
        Stop recording session and close files

        Returns:
            True if stopped successfully, False otherwise
        """
        if not self.is_recording:
            self.last_error = "Not recording"
            return False

        try:
            if self.config.enable_logging:
                print("[SessionRecorder] Stopping recording...")

            # Signal writer threads to stop
            self.writer_stop_event.set()

            # Wait for threads to finish (with timeout)
            if self.audio_writer_thread:
                self.audio_writer_thread.join(timeout=5.0)
            if self.data_writer_thread:
                self.data_writer_thread.join(timeout=5.0)

            # Close files
            self._close_files()

            # Write session metadata
            self._write_metadata()

            self.is_recording = False

            if self.config.enable_logging:
                print(f"[SessionRecorder] Recording stopped")
                print(f"[SessionRecorder]   audio_frames: {self.audio_frames_written}")
                print(f"[SessionRecorder]   metrics_frames: {self.metrics_frames_written}")
                print(f"[SessionRecorder]   phi_frames: {self.phi_frames_written}")
                print(f"[SessionRecorder]   control_events: {self.controls_events_written}")
                print(f"[SessionRecorder]   total_bytes: {self.total_bytes_written}")

            return True

        except Exception as e:
            self.last_error = f"Failed to stop recording: {e}"
            print(f"[SessionRecorder] ERROR: {self.last_error}")
            return False

    def record_audio(self, audio_buffer: np.ndarray):
        """
        Record audio buffer (FR-002)

        Args:
            audio_buffer: Audio samples (multi-channel or mono)
        """
        if not self.is_recording:
            return

        try:
            # Calculate relative timestamp (SC-001)
            timestamp = time.perf_counter() - self.start_time

            # Put in queue (non-blocking to avoid audio glitches)
            self.audio_queue.put_nowait({
                'timestamp': timestamp,
                'buffer': audio_buffer.copy()
            })

        except Exception as e:
            if self.config.enable_logging:
                print(f"[SessionRecorder] Audio queue full or error: {e}")

    def record_metrics(self, metrics_frame: Dict[str, Any]):
        """
        Record metrics frame (FR-002)

        Args:
            metrics_frame: Metrics data dictionary
        """
        if not self.is_recording:
            return

        try:
            # Calculate relative timestamp
            timestamp = time.perf_counter() - self.start_time

            # Add timestamp to frame
            frame_with_time = {
                'timestamp': timestamp,
                **metrics_frame
            }

            self.metrics_queue.put_nowait(frame_with_time)

        except Exception as e:
            if self.config.enable_logging:
                print(f"[SessionRecorder] Metrics queue full or error: {e}")

    def record_phi(self, phi_data: Dict[str, Any]):
        """
        Record Phi parameters (FR-002)

        Args:
            phi_data: Phi parameter data
        """
        if not self.is_recording:
            return

        try:
            timestamp = time.perf_counter() - self.start_time

            frame_with_time = {
                'timestamp': timestamp,
                **phi_data
            }

            self.phi_queue.put_nowait(frame_with_time)

        except Exception as e:
            if self.config.enable_logging:
                print(f"[SessionRecorder] Phi queue full or error: {e}")

    def record_control(self, control_event: Dict[str, Any]):
        """
        Record control event (FR-002)

        Args:
            control_event: Control event data
        """
        if not self.is_recording:
            return

        try:
            timestamp = time.perf_counter() - self.start_time

            event_with_time = {
                'timestamp': timestamp,
                **control_event
            }

            self.controls_queue.put_nowait(event_with_time)

        except Exception as e:
            if self.config.enable_logging:
                print(f"[SessionRecorder] Controls queue full or error: {e}")

    def _open_files(self):
        """Open output files (FR-004)"""
        # Open audio WAV file
        audio_path = self.session_path / "audio.wav"
        self.audio_file = wave.open(str(audio_path), 'wb')
        self.audio_file.setnchannels(self.config.audio_channels)
        self.audio_file.setsampwidth(2)  # 16-bit
        self.audio_file.setframerate(self.config.sample_rate)

        # Open JSONL files
        self.metrics_file = open(self.session_path / "metrics.jsonl", 'w')
        self.phi_file = open(self.session_path / "phi.jsonl", 'w')
        self.controls_file = open(self.session_path / "controls.jsonl", 'w')

    def _close_files(self):
        """Close output files"""
        if self.audio_file:
            self.audio_file.close()
            self.audio_file = None

        if self.metrics_file:
            self.metrics_file.close()
            self.metrics_file = None

        if self.phi_file:
            self.phi_file.close()
            self.phi_file = None

        if self.controls_file:
            self.controls_file.close()
            self.controls_file = None

    def _audio_writer_loop(self):
        """Background thread for writing audio data (SC-002)"""
        while not self.writer_stop_event.is_set() or not self.audio_queue.empty():
            try:
                # Get audio data with timeout
                data = self.audio_queue.get(timeout=0.1)

                buffer = data['buffer']

                # Convert to stereo if needed
                if buffer.ndim == 1:
                    # Mono to stereo
                    stereo = np.stack([buffer, buffer], axis=0)
                elif buffer.shape[0] > 2:
                    # Multi-channel to stereo (downmix)
                    stereo = buffer[:2]
                else:
                    stereo = buffer

                # Ensure stereo shape is (2, samples)
                if stereo.shape[0] != 2:
                    stereo = np.stack([stereo[0], stereo[0]], axis=0)

                # Interleave channels and convert to int16
                interleaved = np.empty((2 * stereo.shape[1],), dtype=np.int16)
                interleaved[0::2] = (stereo[0] * 32767).astype(np.int16)
                interleaved[1::2] = (stereo[1] * 32767).astype(np.int16)

                # Write to WAV file
                if self.audio_file:
                    self.audio_file.writeframes(interleaved.tobytes())
                    self.audio_frames_written += stereo.shape[1]
                    self.total_bytes_written += len(interleaved.tobytes())

                # Periodic flush
                current_time = time.time()
                if current_time - self.last_flush_time >= self.config.flush_interval:
                    if self.audio_file:
                        self.audio_file._file.flush()
                    self.last_flush_time = current_time

            except Empty:
                continue
            except Exception as e:
                self.last_error = f"Audio writer error: {e}"
                if self.config.enable_logging:
                    print(f"[SessionRecorder] {self.last_error}")
                break

    def _data_writer_loop(self):
        """Background thread for writing metrics/phi/controls (SC-002)"""
        while not self.writer_stop_event.is_set() or not self._all_data_queues_empty():
            try:
                # Write metrics
                while not self.metrics_queue.empty():
                    frame = self.metrics_queue.get_nowait()
                    if self.metrics_file:
                        line = json.dumps(frame) + '\n'
                        self.metrics_file.write(line)
                        self.metrics_frames_written += 1
                        self.total_bytes_written += len(line.encode('utf-8'))

                # Write phi
                while not self.phi_queue.empty():
                    frame = self.phi_queue.get_nowait()
                    if self.phi_file:
                        line = json.dumps(frame) + '\n'
                        self.phi_file.write(line)
                        self.phi_frames_written += 1
                        self.total_bytes_written += len(line.encode('utf-8'))

                # Write controls
                while not self.controls_queue.empty():
                    event = self.controls_queue.get_nowait()
                    if self.controls_file:
                        line = json.dumps(event) + '\n'
                        self.controls_file.write(line)
                        self.controls_events_written += 1
                        self.total_bytes_written += len(line.encode('utf-8'))

                # Periodic flush
                current_time = time.time()
                if current_time - self.last_flush_time >= self.config.flush_interval:
                    if self.metrics_file:
                        self.metrics_file.flush()
                    if self.phi_file:
                        self.phi_file.flush()
                    if self.controls_file:
                        self.controls_file.flush()
                    self.last_flush_time = current_time

                # Small sleep to avoid busy-waiting
                time.sleep(0.01)

            except Exception as e:
                self.last_error = f"Data writer error: {e}"
                if self.config.enable_logging:
                    print(f"[SessionRecorder] {self.last_error}")
                break

    def _all_data_queues_empty(self) -> bool:
        """Check if all data queues are empty"""
        return (self.metrics_queue.empty() and
                self.phi_queue.empty() and
                self.controls_queue.empty())

    def _write_metadata(self):
        """Write session metadata file (FR-004)"""
        if not self.session_path:
            return

        metadata = {
            'session_name': self.session_path.name,
            'start_timestamp': self.start_timestamp.isoformat() if self.start_timestamp else None,
            'duration_seconds': time.perf_counter() - self.start_time if self.start_time else 0,
            'sample_rate': self.config.sample_rate,
            'audio_channels': self.config.audio_channels,
            'statistics': {
                'audio_frames': self.audio_frames_written,
                'metrics_frames': self.metrics_frames_written,
                'phi_frames': self.phi_frames_written,
                'control_events': self.controls_events_written,
                'total_bytes': self.total_bytes_written
            },
            'files': {
                'audio': 'audio.wav',
                'metrics': 'metrics.jsonl',
                'phi': 'phi.jsonl',
                'controls': 'controls.jsonl'
            }
        }

        metadata_path = self.session_path / "session.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

    def _cleanup(self):
        """Cleanup resources on error"""
        self.is_recording = False
        self._close_files()

    def get_status(self) -> Dict[str, Any]:
        """
        Get recording status

        Returns:
            Status dictionary
        """
        if not self.is_recording:
            return {
                'is_recording': False,
                'session_path': None,
                'duration': 0,
                'statistics': {},
                'last_error': self.last_error
            }

        duration = time.perf_counter() - self.start_time if self.start_time else 0

        return {
            'is_recording': True,
            'session_path': str(self.session_path) if self.session_path else None,
            'session_name': self.session_path.name if self.session_path else None,
            'duration': duration,
            'statistics': {
                'audio_frames': self.audio_frames_written,
                'metrics_frames': self.metrics_frames_written,
                'phi_frames': self.phi_frames_written,
                'control_events': self.controls_events_written,
                'total_bytes': self.total_bytes_written,
                'estimated_size_mb': self.total_bytes_written / (1024 * 1024)
            },
            'last_error': self.last_error
        }

    def get_size_estimate(self, duration_seconds: float) -> Dict[str, float]:
        """
        Estimate recording size (FR-007)

        Args:
            duration_seconds: Expected duration in seconds

        Returns:
            Size estimates in MB
        """
        # Audio: sample_rate * channels * 2 bytes * duration
        audio_size = self.config.sample_rate * self.config.audio_channels * 2 * duration_seconds

        # Metrics: ~30 Hz * ~500 bytes per frame
        metrics_size = 30 * 500 * duration_seconds

        # Phi: ~30 Hz * ~200 bytes per frame
        phi_size = 30 * 200 * duration_seconds

        # Controls: ~1 Hz * ~100 bytes per event
        controls_size = 1 * 100 * duration_seconds

        total_size = audio_size + metrics_size + phi_size + controls_size

        return {
            'audio_mb': audio_size / (1024 * 1024),
            'metrics_mb': metrics_size / (1024 * 1024),
            'phi_mb': phi_size / (1024 * 1024),
            'controls_mb': controls_size / (1024 * 1024),
            'total_mb': total_size / (1024 * 1024)
        }

    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        List all recorded sessions

        Returns:
            List of session information dictionaries
        """
        sessions_dir = Path(self.config.sessions_dir)

        if not sessions_dir.exists():
            return []

        sessions = []

        for session_path in sorted(sessions_dir.iterdir(), reverse=True):
            if not session_path.is_dir():
                continue

            # Try to read metadata
            metadata_path = session_path / "session.json"
            if metadata_path.exists():
                try:
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                        sessions.append(metadata)
                except Exception:
                    # If metadata can't be read, provide basic info
                    sessions.append({
                        'session_name': session_path.name,
                        'path': str(session_path)
                    })
            else:
                sessions.append({
                    'session_name': session_path.name,
                    'path': str(session_path)
                })

        return sessions


# Self-test function
def _self_test():
    """Test Session Recorder"""
    print("=" * 60)
    print("Session Recorder Self-Test")
    print("=" * 60)

    # Test 1: Initialization
    print("\n1. Testing initialization...")
    config = SessionRecorderConfig(
        sessions_dir="test_sessions",
        sample_rate=48000
    )
    recorder = SessionRecorder(config)

    assert not recorder.is_recording
    print("   OK: Initialization")

    # Test 2: Start recording
    print("\n2. Testing start recording...")
    success = recorder.start_recording()
    assert success, "Should start recording successfully"
    assert recorder.is_recording
    assert recorder.session_path is not None
    print(f"   Session path: {recorder.session_path}")
    print("   OK: Start recording")

    # Test 3: Record data
    print("\n3. Testing data recording...")

    # Record audio
    for i in range(10):
        audio_buffer = np.random.randn(2, 512).astype(np.float32) * 0.1
        recorder.record_audio(audio_buffer)
        time.sleep(0.01)

    # Record metrics
    for i in range(10):
        metrics = {
            'ici': 0.5 + i * 0.01,
            'coherence': 0.7,
            'criticality': 1.0
        }
        recorder.record_metrics(metrics)

    # Record phi
    for i in range(10):
        phi = {
            'phi_depth': 0.5,
            'phi_phase': 0.0
        }
        recorder.record_phi(phi)

    # Record controls
    control = {
        'type': 'set_param',
        'param': 'phi_depth',
        'value': 0.6
    }
    recorder.record_control(control)

    time.sleep(0.5)  # Let writers process

    print("   OK: Data recording")

    # Test 4: Get status
    print("\n4. Testing status...")
    status = recorder.get_status()
    print(f"   Duration: {status['duration']:.2f}s")
    print(f"   Audio frames: {status['statistics']['audio_frames']}")
    print(f"   Metrics frames: {status['statistics']['metrics_frames']}")
    print("   OK: Status")

    # Test 5: Size estimate
    print("\n5. Testing size estimate...")
    estimate = recorder.get_size_estimate(60.0)
    print(f"   Estimated size for 60s: {estimate['total_mb']:.2f} MB")
    print("   OK: Size estimate")

    # Test 6: Stop recording
    print("\n6. Testing stop recording...")
    success = recorder.stop_recording()
    assert success, "Should stop recording successfully"
    assert not recorder.is_recording
    print("   OK: Stop recording")

    # Test 7: Verify files
    print("\n7. Testing file verification...")
    assert (recorder.session_path / "audio.wav").exists()
    assert (recorder.session_path / "metrics.jsonl").exists()
    assert (recorder.session_path / "phi.jsonl").exists()
    assert (recorder.session_path / "controls.jsonl").exists()
    assert (recorder.session_path / "session.json").exists()
    print("   OK: Files exist")

    # Test 8: List sessions
    print("\n8. Testing list sessions...")
    sessions = recorder.list_sessions()
    assert len(sessions) > 0
    print(f"   Found {len(sessions)} session(s)")
    print("   OK: List sessions")

    print("\n" + "=" * 60)
    print("Self-Test PASSED")
    print("=" * 60)

    # Cleanup test session
    import shutil
    if Path("test_sessions").exists():
        shutil.rmtree("test_sessions")

    return True


if __name__ == "__main__":
    _self_test()
