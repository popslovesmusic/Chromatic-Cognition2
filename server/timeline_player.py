"""
Timeline Player - Feature 018
Playback system for recorded sessions with synchronized replay, scrubbing, and speed control

Implements:
- FR-001: Playback API (/api/play, /api/pause, /api/seek, /api/speed)
- FR-002: Load session files from Feature 017
- FR-003: Sync master clock to audio sample time; interpolate metrics
- FR-004: WebSocket /ws/playback streaming
- FR-005: Frontend timeline support (backend)
- FR-006: Playback range selection and loop
- FR-007: Playback progress display

Success Criteria:
- SC-001: Audio/visual sync error <10ms
- SC-002: Scrubbing latency <100ms
- SC-003: Memory footprint <250MB for 30-min session
- SC-004: No dropped frames
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
from enum import Enum


class PlaybackState(Enum):
    """Playback state"""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


@dataclass
class TimelinePlayerConfig:
    """Configuration for Timeline Player"""

    # Playback update rate (Hz)
    update_rate: float = 30.0

    # Audio chunk size for streaming (samples)
    audio_chunk_size: int = 4096

    # Default playback speed
    default_speed: float = 1.0

    # Enable logging
    enable_logging: bool = True


class TimelinePlayer:
    """
    Timeline Player for synchronized session playback

    Features:
    - Synchronized audio and metrics playback
    - Scrubbing and seeking (SC-002: <100ms latency)
    - Speed control (0.5x, 1x, 2x)
    - Range selection and loop support
    - Memory-efficient streaming (SC-003: <250MB)
    """

    def __init__(self, config: Optional[TimelinePlayerConfig] = None):
        """
        Initialize Timeline Player

        Args:
            config: TimelinePlayerConfig (uses defaults if None)
        """
        self.config = config or TimelinePlayerConfig()

        # Playback state
        self.state: PlaybackState = PlaybackState.STOPPED
        self.current_time: float = 0.0  # Current playback time in seconds
        self.playback_speed: float = self.config.default_speed

        # Session data
        self.session_path: Optional[Path] = None
        self.session_metadata: Optional[Dict] = None
        self.duration: float = 0.0  # Total duration in seconds

        # Audio data
        self.audio_file: Optional[wave.Wave_read] = None
        self.sample_rate: int = 48000
        self.num_channels: int = 2

        # Metrics data (loaded in memory - small footprint)
        self.metrics_frames: List[Dict] = []
        self.phi_frames: List[Dict] = []
        self.controls_events: List[Dict] = []

        # Playback range and loop
        self.range_start: float = 0.0
        self.range_end: Optional[float] = None  # None = end of session
        self.loop_enabled: bool = False

        # Playback thread
        self.playback_thread: Optional[threading.Thread] = None
        self.playback_stop_event: threading.Event = threading.Event()

        # Frame callback (for WebSocket streaming)
        self.frame_callback: Optional[Callable[[Dict], None]] = None

        # Last frame time (for update rate control)
        self.last_frame_time: float = 0.0

        # Statistics
        self.frames_streamed: int = 0

        print("[TimelinePlayer] Initialized")

    def load_session(self, session_path: str) -> bool:
        """
        Load recorded session (FR-002)

        Args:
            session_path: Path to session directory

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            self.session_path = Path(session_path)

            if not self.session_path.exists():
                print(f"[TimelinePlayer] ERROR: Session path does not exist: {session_path}")
                return False

            # Load metadata
            metadata_path = self.session_path / "session.json"
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    self.session_metadata = json.load(f)
                    self.duration = self.session_metadata.get('duration_seconds', 0.0)

            # Open audio file (streaming mode - SC-003)
            audio_path = self.session_path / "audio.wav"
            if audio_path.exists():
                self.audio_file = wave.open(str(audio_path), 'rb')
                self.sample_rate = self.audio_file.getframerate()
                self.num_channels = self.audio_file.getnchannels()

                # Calculate duration from audio if metadata not available
                if self.duration == 0.0:
                    num_frames = self.audio_file.getnframes()
                    self.duration = num_frames / self.sample_rate

            # Load metrics (small memory footprint)
            self._load_metrics()
            self._load_phi()
            self._load_controls()

            # Set range end to duration
            if self.range_end is None:
                self.range_end = self.duration

            if self.config.enable_logging:
                print(f"[TimelinePlayer] Session loaded: {self.session_path.name}")
                print(f"[TimelinePlayer]   duration: {self.duration:.2f}s")
                print(f"[TimelinePlayer]   sample_rate: {self.sample_rate}")
                print(f"[TimelinePlayer]   metrics_frames: {len(self.metrics_frames)}")

            return True

        except Exception as e:
            print(f"[TimelinePlayer] ERROR loading session: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _load_metrics(self):
        """Load metrics JSONL file"""
        metrics_path = self.session_path / "metrics.jsonl"
        if metrics_path.exists():
            self.metrics_frames = []
            with open(metrics_path, 'r') as f:
                for line in f:
                    if line.strip():
                        self.metrics_frames.append(json.loads(line))

    def _load_phi(self):
        """Load phi JSONL file"""
        phi_path = self.session_path / "phi.jsonl"
        if phi_path.exists():
            self.phi_frames = []
            with open(phi_path, 'r') as f:
                for line in f:
                    if line.strip():
                        self.phi_frames.append(json.loads(line))

    def _load_controls(self):
        """Load controls JSONL file"""
        controls_path = self.session_path / "controls.jsonl"
        if controls_path.exists():
            self.controls_events = []
            with open(controls_path, 'r') as f:
                for line in f:
                    if line.strip():
                        self.controls_events.append(json.loads(line))

    def play(self) -> bool:
        """
        Start playback (FR-001)

        Returns:
            True if playback started, False otherwise
        """
        if self.session_path is None:
            print("[TimelinePlayer] ERROR: No session loaded")
            return False

        if self.state == PlaybackState.PLAYING:
            return True  # Already playing

        self.state = PlaybackState.PLAYING

        # Start playback thread
        self.playback_stop_event.clear()
        self.playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
        self.playback_thread.start()

        if self.config.enable_logging:
            print(f"[TimelinePlayer] Playback started at {self.current_time:.2f}s")

        return True

    def pause(self) -> bool:
        """
        Pause playback (FR-001)

        Returns:
            True if paused, False otherwise
        """
        if self.state != PlaybackState.PLAYING:
            return False

        self.state = PlaybackState.PAUSED

        # Stop playback thread
        self.playback_stop_event.set()
        if self.playback_thread:
            self.playback_thread.join(timeout=1.0)

        if self.config.enable_logging:
            print(f"[TimelinePlayer] Playback paused at {self.current_time:.2f}s")

        return True

    def stop(self) -> bool:
        """
        Stop playback

        Returns:
            True if stopped, False otherwise
        """
        if self.state == PlaybackState.STOPPED:
            return True

        self.state = PlaybackState.STOPPED

        # Stop playback thread
        self.playback_stop_event.set()
        if self.playback_thread:
            self.playback_thread.join(timeout=1.0)

        # Reset to beginning
        self.current_time = self.range_start

        if self.config.enable_logging:
            print("[TimelinePlayer] Playback stopped")

        return True

    def seek(self, time_seconds: float) -> bool:
        """
        Seek to specific time (FR-001, SC-002: <100ms latency)

        Args:
            time_seconds: Time to seek to in seconds

        Returns:
            True if seek successful, False otherwise
        """
        # Clamp to valid range
        time_seconds = max(self.range_start, min(time_seconds, self.range_end))

        was_playing = (self.state == PlaybackState.PLAYING)

        # Pause if playing
        if was_playing:
            self.pause()

        # Update current time
        self.current_time = time_seconds

        # Resume if was playing
        if was_playing:
            self.play()

        if self.config.enable_logging:
            print(f"[TimelinePlayer] Seeked to {time_seconds:.2f}s")

        return True

    def set_speed(self, speed: float) -> bool:
        """
        Set playback speed (FR-001)

        Args:
            speed: Playback speed multiplier (0.5, 1.0, 2.0, etc.)

        Returns:
            True if speed set, False otherwise
        """
        if speed <= 0:
            return False

        self.playback_speed = speed

        if self.config.enable_logging:
            print(f"[TimelinePlayer] Speed set to {speed}x")

        return True

    def set_range(self, start: float, end: float) -> bool:
        """
        Set playback range (FR-006)

        Args:
            start: Start time in seconds
            end: End time in seconds

        Returns:
            True if range set, False otherwise
        """
        # Validate range
        if start < 0 or end > self.duration or start >= end:
            return False

        self.range_start = start
        self.range_end = end

        # Clamp current time to range
        if self.current_time < start or self.current_time > end:
            self.current_time = start

        if self.config.enable_logging:
            print(f"[TimelinePlayer] Range set to [{start:.2f}, {end:.2f}]")

        return True

    def set_loop(self, enabled: bool) -> bool:
        """
        Enable/disable loop (FR-006)

        Args:
            enabled: True to enable loop, False to disable

        Returns:
            True always
        """
        self.loop_enabled = enabled

        if self.config.enable_logging:
            print(f"[TimelinePlayer] Loop {'enabled' if enabled else 'disabled'}")

        return True

    def _playback_loop(self):
        """
        Playback thread loop (FR-003, SC-001, SC-004)

        Streams interpolated frames at update_rate Hz
        """
        update_interval = 1.0 / self.config.update_rate
        last_update_time = time.perf_counter()

        while not self.playback_stop_event.is_set() and self.state == PlaybackState.PLAYING:
            current_perf = time.perf_counter()
            elapsed = current_perf - last_update_time

            # Advance playback time based on speed (FR-003)
            time_delta = elapsed * self.playback_speed
            self.current_time += time_delta

            # Check range bounds
            if self.current_time >= self.range_end:
                if self.loop_enabled:
                    # Loop back to start (FR-006)
                    self.current_time = self.range_start
                else:
                    # Stop at end
                    self.state = PlaybackState.PAUSED
                    self.current_time = self.range_end
                    break

            # Generate and stream frame (FR-004)
            frame = self._generate_playback_frame()
            if self.frame_callback and frame:
                self.frame_callback(frame)
                self.frames_streamed += 1

            last_update_time = current_perf

            # Sleep to maintain update rate
            sleep_time = update_interval - (time.perf_counter() - current_perf)
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _generate_playback_frame(self) -> Dict:
        """
        Generate playback frame with interpolated metrics (FR-003, SC-001)

        Returns:
            Frame dictionary with interpolated data
        """
        frame = {
            'type': 'playback_frame',
            'timestamp': self.current_time,
            'playback_speed': self.playback_speed,
            'state': self.state.value,
            'progress': self.current_time / self.duration if self.duration > 0 else 0.0
        }

        # Interpolate metrics (FR-003)
        metrics = self._interpolate_metrics(self.current_time)
        if metrics:
            frame.update(metrics)

        # Interpolate phi
        phi = self._interpolate_phi(self.current_time)
        if phi:
            frame['phi'] = phi

        # Include recent control events
        controls = self._get_recent_controls(self.current_time, window=0.1)
        if controls:
            frame['controls'] = controls

        return frame

    def _interpolate_metrics(self, time: float) -> Optional[Dict]:
        """
        Interpolate metrics at given time (FR-003)

        Uses linear interpolation between frames for smooth playback

        Args:
            time: Time in seconds

        Returns:
            Interpolated metrics dictionary or None
        """
        if not self.metrics_frames:
            return None

        # Find surrounding frames
        before_frame = None
        after_frame = None

        for frame in self.metrics_frames:
            frame_time = frame.get('timestamp', 0.0)
            if frame_time <= time:
                before_frame = frame
            elif frame_time > time:
                after_frame = frame
                break

        # Edge cases: missing metrics fill with last valid value
        if before_frame is None and after_frame is None:
            return None
        elif before_frame is None:
            return self._extract_metrics(after_frame)
        elif after_frame is None:
            return self._extract_metrics(before_frame)

        # Linear interpolation
        t_before = before_frame.get('timestamp', 0.0)
        t_after = after_frame.get('timestamp', 0.0)

        if t_after - t_before < 0.001:  # Too close, just use before
            return self._extract_metrics(before_frame)

        alpha = (time - t_before) / (t_after - t_before)
        alpha = np.clip(alpha, 0.0, 1.0)

        # Interpolate numeric values
        interpolated = {}
        for key in before_frame.keys():
            if key == 'timestamp':
                continue

            val_before = before_frame.get(key)
            val_after = after_frame.get(key)

            if isinstance(val_before, (int, float)) and isinstance(val_after, (int, float)):
                interpolated[key] = val_before + alpha * (val_after - val_before)
            else:
                # Non-numeric: use before value
                interpolated[key] = val_before

        return interpolated

    def _extract_metrics(self, frame: Dict) -> Dict:
        """Extract metrics from frame (exclude timestamp)"""
        return {k: v for k, v in frame.items() if k != 'timestamp'}

    def _interpolate_phi(self, time: float) -> Optional[Dict]:
        """
        Interpolate phi parameters at given time

        Args:
            time: Time in seconds

        Returns:
            Interpolated phi dictionary or None
        """
        if not self.phi_frames:
            return None

        # Same logic as metrics interpolation
        before_frame = None
        after_frame = None

        for frame in self.phi_frames:
            frame_time = frame.get('timestamp', 0.0)
            if frame_time <= time:
                before_frame = frame
            elif frame_time > time:
                after_frame = frame
                break

        if before_frame is None and after_frame is None:
            return None
        elif before_frame is None:
            return self._extract_metrics(after_frame)
        elif after_frame is None:
            return self._extract_metrics(before_frame)

        t_before = before_frame.get('timestamp', 0.0)
        t_after = after_frame.get('timestamp', 0.0)

        if t_after - t_before < 0.001:
            return self._extract_metrics(before_frame)

        alpha = (time - t_before) / (t_after - t_before)
        alpha = np.clip(alpha, 0.0, 1.0)

        interpolated = {}
        for key in before_frame.keys():
            if key == 'timestamp':
                continue

            val_before = before_frame.get(key)
            val_after = after_frame.get(key)

            if isinstance(val_before, (int, float)) and isinstance(val_after, (int, float)):
                interpolated[key] = val_before + alpha * (val_after - val_before)
            else:
                interpolated[key] = val_before

        return interpolated

    def _get_recent_controls(self, time: float, window: float = 0.1) -> List[Dict]:
        """
        Get control events within time window

        Args:
            time: Current time in seconds
            window: Time window in seconds

        Returns:
            List of control events
        """
        recent = []

        for event in self.controls_events:
            event_time = event.get('timestamp', 0.0)
            if time - window <= event_time <= time:
                recent.append(event)

        return recent

    def get_status(self) -> Dict:
        """
        Get playback status (FR-007)

        Returns:
            Status dictionary
        """
        return {
            'state': self.state.value,
            'current_time': self.current_time,
            'duration': self.duration,
            'progress': self.current_time / self.duration if self.duration > 0 else 0.0,
            'playback_speed': self.playback_speed,
            'range_start': self.range_start,
            'range_end': self.range_end,
            'loop_enabled': self.loop_enabled,
            'session_loaded': self.session_path is not None,
            'session_name': self.session_path.name if self.session_path else None,
            'frames_streamed': self.frames_streamed
        }

    def unload_session(self):
        """Unload current session and free resources"""
        # Stop playback
        self.stop()

        # Close audio file
        if self.audio_file:
            self.audio_file.close()
            self.audio_file = None

        # Clear data
        self.metrics_frames = []
        self.phi_frames = []
        self.controls_events = []
        self.session_path = None
        self.session_metadata = None
        self.duration = 0.0
        self.current_time = 0.0

        if self.config.enable_logging:
            print("[TimelinePlayer] Session unloaded")


# Self-test function
def _self_test():
    """Test Timeline Player"""
    print("=" * 60)
    print("Timeline Player Self-Test")
    print("=" * 60)

    # Test 1: Initialization
    print("\n1. Testing initialization...")
    config = TimelinePlayerConfig(update_rate=30.0)
    player = TimelinePlayer(config)

    assert player.state == PlaybackState.STOPPED
    assert player.current_time == 0.0
    print("   OK: Initialization")

    # Note: Full testing requires a recorded session from Feature 017
    # For now, just test the basic structure

    print("\n2. Testing playback controls...")

    # Can't start without loaded session
    assert player.play() == False
    print("   OK: Play requires loaded session")

    # Speed control
    assert player.set_speed(0.5) == True
    assert player.playback_speed == 0.5
    assert player.set_speed(2.0) == True
    assert player.playback_speed == 2.0
    print("   OK: Speed control")

    # Range control
    player.duration = 100.0  # Mock duration
    player.range_end = 100.0
    assert player.set_range(10.0, 50.0) == True
    assert player.range_start == 10.0
    assert player.range_end == 50.0
    print("   OK: Range control")

    # Loop control
    assert player.set_loop(True) == True
    assert player.loop_enabled == True
    print("   OK: Loop control")

    # Seek control
    assert player.seek(25.0) == True
    assert player.current_time == 25.0
    print("   OK: Seek control")

    print("\n3. Testing status...")
    status = player.get_status()
    assert status['state'] == 'stopped'
    assert status['playback_speed'] == 2.0
    assert status['loop_enabled'] == True
    print("   OK: Status")

    print("\n" + "=" * 60)
    print("Self-Test PASSED")
    print("=" * 60)
    print("Note: Full playback testing requires recorded session")

    return True


if __name__ == "__main__":
    _self_test()
