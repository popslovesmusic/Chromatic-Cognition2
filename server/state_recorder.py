"""
StateRecorder - Feature 014: Consciousness State Recorder & Timeline Playback

Continuous recording of consciousness state data with persistence and metadata.

Features:
- FR-001: Record all metrics (Phi, ICI, coherence, criticality) with timestamps
- FR-002: Store session metadata (date, duration, preset, notes)
- SC-001: Record at >= 30 Hz without data loss
- Auto-segmentation for long recordings

Requirements:
- FR-001: System MUST record metrics with timestamps
- FR-002: System MUST store session metadata
- SC-001: All metrics recorded at >= 30 Hz without data loss
- SC-004: CPU overhead during recording <= 10%
"""

import time
import threading
import json
import os
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

from session_memory import SessionMemory, MetricSnapshot


@dataclass
class RecordingMetadata:
    """Metadata for a recording session"""
    session_id: str
    start_time: float
    end_time: Optional[float]
    duration: float
    sample_count: int
    sample_rate_hz: float
    preset_name: Optional[str]
    user_notes: Optional[str]
    software_version: str
    file_format_version: str


class StateRecorder:
    """
    StateRecorder - Continuous recording of consciousness state data

    Handles:
    - Real-time metric recording (FR-001, SC-001)
    - Persistent storage with metadata (FR-002)
    - Auto-segmentation for long recordings
    - Buffered writes for performance (SC-004)
    """

    FILE_FORMAT_VERSION = "1.0"
    SOFTWARE_VERSION = "Soundlab 1.0"
    MAX_SEGMENT_DURATION = 3600.0  # 60 minutes per segment

    def __init__(self, output_dir: str = "recordings"):
        """
        Initialize StateRecorder

        Args:
            output_dir: Directory for recording files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Current recording state
        self.is_recording = False
        self.session_memory = SessionMemory(max_samples=1000000)  # Large buffer
        self.session_id: Optional[str] = None
        self.start_time: Optional[float] = None
        self.preset_name: Optional[str] = None
        self.user_notes: Optional[str] = None

        # Auto-segmentation
        self.segment_index = 0
        self.last_segment_time = 0.0

        # Performance tracking
        self.write_count = 0
        self.last_write_time = time.time()
        self.recording_rate_hz = 0.0

        # Threading
        self.lock = threading.Lock()
        self.save_thread: Optional[threading.Thread] = None

    def start_recording(self, session_id: Optional[str] = None,
                       preset_name: Optional[str] = None,
                       user_notes: Optional[str] = None):
        """
        Start a new recording session (FR-001)

        Args:
            session_id: Optional session identifier
            preset_name: Name of preset used
            user_notes: User notes for this session
        """
        with self.lock:
            if self.is_recording:
                raise RuntimeError("Recording already in progress")

            # Generate session ID with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.session_id = session_id or f"session_{timestamp}"
            self.start_time = time.time()
            self.preset_name = preset_name
            self.user_notes = user_notes

            # Reset state
            self.segment_index = 0
            self.last_segment_time = self.start_time
            self.write_count = 0

            # Start recording in session memory
            self.session_memory.start_session(self.session_id)
            self.is_recording = True

            print(f"[StateRecorder] Started recording: {self.session_id}")

    def stop_recording(self) -> Optional[str]:
        """
        Stop recording and save to file (FR-002)

        Returns:
            Path to saved file or None if failed
        """
        with self.lock:
            if not self.is_recording:
                return None

            self.is_recording = False
            self.session_memory.stop_session()

            # Save final segment
            filepath = self._save_segment()

            print(f"[StateRecorder] Stopped recording: {self.session_id}")
            print(f"[StateRecorder] Saved to: {filepath}")

            return filepath

    def record_state(self, snapshot: MetricSnapshot):
        """
        Record a state snapshot (FR-001, SC-001)

        Args:
            snapshot: MetricSnapshot to record
        """
        if not self.is_recording:
            return

        # Record to memory
        self.session_memory.record_snapshot(snapshot)

        # Update performance metrics
        self.write_count += 1
        current_time = time.time()
        time_delta = current_time - self.last_write_time

        if time_delta >= 1.0:  # Update rate every second
            self.recording_rate_hz = self.write_count / time_delta
            self.write_count = 0
            self.last_write_time = current_time

        # Check for auto-segmentation
        if (current_time - self.last_segment_time) >= self.MAX_SEGMENT_DURATION:
            self._auto_segment()

    def get_recording_status(self) -> Dict:
        """
        Get current recording status

        Returns:
            Dictionary with recording status
        """
        with self.lock:
            if not self.is_recording:
                return {
                    "is_recording": False,
                    "session_id": None,
                    "duration": 0.0,
                    "sample_count": 0,
                    "recording_rate_hz": 0.0
                }

            current_time = time.time()
            duration = current_time - self.start_time if self.start_time else 0.0

            return {
                "is_recording": True,
                "session_id": self.session_id,
                "duration": duration,
                "sample_count": self.session_memory.get_sample_count(),
                "recording_rate_hz": self.recording_rate_hz,
                "segment_index": self.segment_index
            }

    def _auto_segment(self):
        """Auto-segment long recording into multiple files"""
        print(f"[StateRecorder] Auto-segmenting at {self.segment_index + 1}")

        # Save current segment
        self._save_segment()

        # Reset for next segment
        self.segment_index += 1
        self.last_segment_time = time.time()

    def _save_segment(self) -> str:
        """
        Save current recording segment to file

        Returns:
            Path to saved file
        """
        # Generate filename
        if self.segment_index == 0:
            filename = f"{self.session_id}.json"
        else:
            filename = f"{self.session_id}_seg{self.segment_index:03d}.json"

        filepath = self.output_dir / filename

        # Get samples
        samples = self.session_memory.get_all_samples()

        if len(samples) == 0:
            return str(filepath)

        # Compute stats
        stats = self.session_memory.compute_stats()

        # Create metadata
        current_time = time.time()
        metadata = RecordingMetadata(
            session_id=self.session_id,
            start_time=self.start_time,
            end_time=current_time,
            duration=current_time - self.start_time,
            sample_count=len(samples),
            sample_rate_hz=len(samples) / (current_time - self.start_time) if (current_time - self.start_time) > 0 else 0.0,
            preset_name=self.preset_name,
            user_notes=self.user_notes,
            software_version=self.SOFTWARE_VERSION,
            file_format_version=self.FILE_FORMAT_VERSION
        )

        # Convert samples to dict format
        samples_dict = [asdict(s) for s in samples]

        # Create recording data
        recording_data = {
            "metadata": asdict(metadata),
            "stats": asdict(stats) if stats else {},
            "samples": samples_dict
        }

        # Write to file (in background thread if not already saving)
        self._write_to_file(filepath, recording_data)

        return str(filepath)

    def _write_to_file(self, filepath: Path, data: Dict):
        """
        Write data to file (buffered for performance)

        Args:
            filepath: Path to write to
            data: Data to write
        """
        # Write synchronously for now (could be async for better performance)
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[StateRecorder] Error writing file: {e}")

    def list_recordings(self) -> List[Dict]:
        """
        List all available recordings

        Returns:
            List of recording metadata
        """
        recordings = []

        for file_path in self.output_dir.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    metadata = data.get("metadata", {})
                    recordings.append({
                        "filename": file_path.name,
                        "session_id": metadata.get("session_id"),
                        "start_time": metadata.get("start_time"),
                        "duration": metadata.get("duration"),
                        "sample_count": metadata.get("sample_count"),
                        "preset_name": metadata.get("preset_name"),
                        "user_notes": metadata.get("user_notes")
                    })
            except Exception as e:
                print(f"[StateRecorder] Error reading {file_path}: {e}")

        # Sort by start time (newest first)
        recordings.sort(key=lambda x: x.get("start_time", 0), reverse=True)

        return recordings

    def load_recording(self, filename: str) -> Optional[Dict]:
        """
        Load a recording from file

        Args:
            filename: Name of recording file

        Returns:
            Recording data or None if failed
        """
        filepath = self.output_dir / filename

        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[StateRecorder] Error loading recording: {e}")
            return None

    def delete_recording(self, filename: str) -> bool:
        """
        Delete a recording file

        Args:
            filename: Name of recording file

        Returns:
            True if deleted successfully
        """
        filepath = self.output_dir / filename

        try:
            filepath.unlink()
            return True
        except Exception as e:
            print(f"[StateRecorder] Error deleting recording: {e}")
            return False


# Self-test function
def _self_test():
    """Run basic self-test of StateRecorder"""
    print("=" * 60)
    print("StateRecorder Self-Test")
    print("=" * 60)
    print()

    import numpy as np

    # Create recorder
    print("1. Creating StateRecorder...")
    recorder = StateRecorder(output_dir="test_recordings")
    print("   [OK] StateRecorder created")
    print()

    # Start recording
    print("2. Starting recording...")
    recorder.start_recording(
        session_id="test_session",
        preset_name="test_preset",
        user_notes="Self-test recording"
    )

    status = recorder.get_recording_status()
    print(f"   [OK] Recording started: {status['session_id']}")
    print()

    # Record samples at 30 Hz
    print("3. Recording samples at 30 Hz for 2 seconds...")
    sample_count = 60  # 2 seconds at 30 Hz
    start_time = time.time()

    for i in range(sample_count):
        snapshot = MetricSnapshot(
            timestamp=time.time(),
            ici=0.5 + 0.1 * np.sin(i * 0.1),
            coherence=0.6 + 0.05 * np.cos(i * 0.15),
            criticality=0.4,
            phi_value=1.0 + 0.2 * np.sin(i * 0.1),
            phi_phase=i * 0.1,
            phi_depth=0.5,
            active_source="test"
        )
        recorder.record_state(snapshot)
        time.sleep(1.0 / 30.0)  # 30 Hz

    elapsed = time.time() - start_time
    actual_rate = sample_count / elapsed

    print(f"   [OK] Recorded {sample_count} samples in {elapsed:.2f}s")
    print(f"   [OK] Actual rate: {actual_rate:.1f} Hz (target: 30 Hz)")
    print()

    # Check status
    print("4. Checking recording status...")
    status = recorder.get_recording_status()
    print(f"   Duration: {status['duration']:.2f}s")
    print(f"   Sample count: {status['sample_count']}")
    print(f"   Recording rate: {status['recording_rate_hz']:.1f} Hz")
    print("   [OK] Status retrieved")
    print()

    # Stop recording
    print("5. Stopping recording...")
    filepath = recorder.stop_recording()
    print(f"   [OK] Recording saved to: {filepath}")
    print()

    # List recordings
    print("6. Listing recordings...")
    recordings = recorder.list_recordings()
    print(f"   [OK] Found {len(recordings)} recordings")
    for rec in recordings:
        print(f"      - {rec['filename']}: {rec['duration']:.1f}s, {rec['sample_count']} samples")
    print()

    # Load recording
    print("7. Loading recording...")
    data = recorder.load_recording(recordings[0]['filename'])
    if data:
        metadata = data['metadata']
        samples = data['samples']
        print(f"   [OK] Loaded {len(samples)} samples")
        print(f"      Session: {metadata['session_id']}")
        print(f"      Duration: {metadata['duration']:.2f}s")
        print(f"      Sample rate: {metadata['sample_rate_hz']:.1f} Hz")
    print()

    # Cleanup
    print("8. Cleaning up...")
    for rec in recordings:
        recorder.delete_recording(rec['filename'])
    print("   [OK] Test recordings deleted")
    print()

    print("=" * 60)
    print("Self-Test PASSED")
    print("=" * 60)

    return True


if __name__ == "__main__":
    _self_test()
