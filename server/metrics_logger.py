"""
MetricsLogger - Session Recording and Archival

Handles CSV and JSON logging of D-ASE metrics streams with rotation and compression.
Implements FR-007 requirements for session recording.
"""

import os
import csv
import json
import gzip
from typing import List, Optional
from datetime import datetime
from pathlib import Path

from metrics_frame import MetricsFrame


class MetricsLogger:
    """
    Records metrics streams to CSV and JSON files

    Features:
    - Dual-format logging (CSV for analysis, JSON for replay)
    - Automatic file rotation
    - Gzip compression for archived sessions
    - Frame gap detection (FR-007)
    """

    def __init__(self,
                 log_dir: Optional[str] = None,
                 session_name: Optional[str] = None,
                 enable_csv: bool = True,
                 enable_json: bool = True,
                 compress_on_close: bool = True):
        """
        Initialize metrics logger

        Args:
            log_dir: Directory for log files (None = logs/metrics/)
            session_name: Session identifier (None = timestamp)
            enable_csv: Enable CSV logging
            enable_json: Enable JSON logging
            compress_on_close: Compress files with gzip when session ends
        """
        # Setup logging directory
        if log_dir is None:
            log_dir = os.path.join(os.path.dirname(__file__), "..", "logs", "metrics")
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Session naming
        if session_name is None:
            session_name = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_name = session_name

        # Configuration
        self.enable_csv = enable_csv
        self.enable_json = enable_json
        self.compress_on_close = compress_on_close

        # File handles
        self.csv_file = None
        self.csv_writer = None
        self.json_file = None

        # Statistics
        self.frames_logged = 0
        self.last_timestamp = None
        self.gaps_detected = 0
        self.session_start_time = datetime.now()

        # Initialize log files
        self._init_csv()
        self._init_json()

        print(f"[MetricsLogger] Session '{session_name}' started")
        print(f"[MetricsLogger] Logging to {self.log_dir}")

    def _init_csv(self):
        """Initialize CSV log file"""
        if not self.enable_csv:
            return

        csv_path = self.log_dir / f"{self.session_name}_metrics.csv"

        try:
            self.csv_file = open(csv_path, 'w', newline='')
            self.csv_writer = csv.DictWriter(
                self.csv_file,
                fieldnames=[
                    'timestamp', 'frame_id', 'state',
                    'ici', 'phase_coherence', 'spectral_centroid',
                    'criticality', 'consciousness_level',
                    'phi_phase', 'phi_depth', 'phi_source',
                    'latency_ms', 'cpu_load', 'valid'
                ]
            )
            self.csv_writer.writeheader()
            self.csv_file.flush()

            print(f"[MetricsLogger] CSV logging to {csv_path}")

        except Exception as e:
            print(f"[MetricsLogger] ERROR: Could not init CSV: {e}")
            self.csv_file = None
            self.csv_writer = None

    def _init_json(self):
        """Initialize JSON log file"""
        if not self.enable_json:
            return

        json_path = self.log_dir / f"{self.session_name}_metrics.jsonl"

        try:
            self.json_file = open(json_path, 'w')
            # Write session header
            header = {
                "session_name": self.session_name,
                "start_time": self.session_start_time.isoformat(),
                "format_version": "1.0"
            }
            self.json_file.write(json.dumps(header) + '\n')
            self.json_file.flush()

            print(f"[MetricsLogger] JSON logging to {json_path}")

        except Exception as e:
            print(f"[MetricsLogger] ERROR: Could not init JSON: {e}")
            self.json_file = None

    def log_frame(self, frame: MetricsFrame):
        """
        Log a single metrics frame

        Args:
            frame: MetricsFrame to log
        """
        # Detect gaps (FR-007: no gaps > 50ms)
        if self.last_timestamp is not None:
            gap_ms = (frame.timestamp - self.last_timestamp) * 1000
            if gap_ms > 50.0:
                self.gaps_detected += 1
                print(f"[MetricsLogger] WARNING: Gap detected: {gap_ms:.1f}ms")

        self.last_timestamp = frame.timestamp

        # Log to CSV
        if self.csv_writer and self.csv_file:
            try:
                row = frame.to_dict()
                self.csv_writer.writerow(row)
            except Exception as e:
                print(f"[MetricsLogger] ERROR writing CSV: {e}")

        # Log to JSON (JSONL format - one frame per line)
        if self.json_file:
            try:
                self.json_file.write(frame.to_json() + '\n')
            except Exception as e:
                print(f"[MetricsLogger] ERROR writing JSON: {e}")

        self.frames_logged += 1

        # Flush periodically (every 100 frames)
        if self.frames_logged % 100 == 0:
            self.flush()

    def log_batch(self, frames: List[MetricsFrame]):
        """
        Log multiple frames at once

        Args:
            frames: List of MetricsFrames
        """
        for frame in frames:
            self.log_frame(frame)

    def flush(self):
        """Flush all buffers to disk"""
        if self.csv_file:
            try:
                self.csv_file.flush()
            except:
                pass

        if self.json_file:
            try:
                self.json_file.flush()
            except:
                pass

    def get_statistics(self) -> dict:
        """
        Get logging statistics

        Returns:
            Dictionary with session statistics
        """
        duration = (datetime.now() - self.session_start_time).total_seconds()

        return {
            'session_name': self.session_name,
            'start_time': self.session_start_time.isoformat(),
            'duration_seconds': duration,
            'frames_logged': self.frames_logged,
            'gaps_detected': self.gaps_detected,
            'average_fps': self.frames_logged / duration if duration > 0 else 0,
            'csv_enabled': self.enable_csv,
            'json_enabled': self.enable_json
        }

    def close(self):
        """Close log files and optionally compress"""
        print(f"[MetricsLogger] Closing session '{self.session_name}'")

        # Get final statistics
        stats = self.get_statistics()
        print(f"[MetricsLogger] Logged {stats['frames_logged']} frames over {stats['duration_seconds']:.1f}s")
        print(f"[MetricsLogger] Average: {stats['average_fps']:.1f} fps")
        if stats['gaps_detected'] > 0:
            print(f"[MetricsLogger] WARNING: {stats['gaps_detected']} gaps detected")

        # Close CSV
        if self.csv_file:
            try:
                self.csv_file.close()
                csv_path = self.log_dir / f"{self.session_name}_metrics.csv"

                if self.compress_on_close:
                    self._compress_file(csv_path)

            except Exception as e:
                print(f"[MetricsLogger] ERROR closing CSV: {e}")

        # Close JSON
        if self.json_file:
            try:
                # Write session footer
                footer = {
                    "session_end": datetime.now().isoformat(),
                    "statistics": stats
                }
                self.json_file.write(json.dumps(footer) + '\n')
                self.json_file.close()

                json_path = self.log_dir / f"{self.session_name}_metrics.jsonl"

                if self.compress_on_close:
                    self._compress_file(json_path)

            except Exception as e:
                print(f"[MetricsLogger] ERROR closing JSON: {e}")

        print(f"[MetricsLogger] Session closed")

    def _compress_file(self, filepath: Path):
        """
        Compress file with gzip and remove original

        Args:
            filepath: Path to file to compress
        """
        if not filepath.exists():
            return

        gz_path = filepath.with_suffix(filepath.suffix + '.gz')

        try:
            with open(filepath, 'rb') as f_in:
                with gzip.open(gz_path, 'wb') as f_out:
                    f_out.writelines(f_in)

            # Remove original
            filepath.unlink()

            original_size = filepath.stat().st_size if filepath.exists() else 0
            compressed_size = gz_path.stat().st_size
            ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0

            print(f"[MetricsLogger] Compressed {filepath.name} → {gz_path.name} ({ratio:.1f}% reduction)")

        except Exception as e:
            print(f"[MetricsLogger] ERROR compressing {filepath}: {e}")

    def __del__(self):
        """Ensure cleanup on destruction"""
        self.close()


class MetricsArchive:
    """
    Read and query archived metrics sessions

    Allows loading historical data for analysis
    """

    def __init__(self, log_dir: Optional[str] = None):
        """
        Initialize archive reader

        Args:
            log_dir: Directory containing log files
        """
        if log_dir is None:
            log_dir = os.path.join(os.path.dirname(__file__), "..", "logs", "metrics")
        self.log_dir = Path(log_dir)

    def list_sessions(self) -> List[dict]:
        """
        List all available sessions

        Returns:
            List of session info dictionaries
        """
        sessions = []

        if not self.log_dir.exists():
            return sessions

        # Find all CSV/JSONL files
        for file_path in self.log_dir.glob("*_metrics.*"):
            # Skip compressed files for now
            if file_path.suffix == '.gz':
                continue

            session_name = file_path.stem.replace('_metrics', '')
            file_type = file_path.suffix[1:]  # Remove leading dot

            sessions.append({
                'session_name': session_name,
                'file_path': str(file_path),
                'file_type': file_type,
                'size_bytes': file_path.stat().st_size,
                'modified_time': datetime.fromtimestamp(file_path.stat().st_mtime)
            })

        return sorted(sessions, key=lambda x: x['modified_time'], reverse=True)

    def load_session_jsonl(self, session_name: str) -> List[MetricsFrame]:
        """
        Load metrics from JSONL file

        Args:
            session_name: Session identifier

        Returns:
            List of MetricsFrames
        """
        json_path = self.log_dir / f"{session_name}_metrics.jsonl"

        if not json_path.exists():
            # Try compressed version
            json_path = json_path.with_suffix('.jsonl.gz')
            if not json_path.exists():
                raise FileNotFoundError(f"Session not found: {session_name}")

        frames = []

        try:
            if json_path.suffix == '.gz':
                open_func = gzip.open
            else:
                open_func = open

            with open_func(json_path, 'rt') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        # Skip header/footer lines
                        if 'timestamp' in data:
                            frame = MetricsFrame.from_dict(data)
                            frames.append(frame)
                    except:
                        pass  # Skip invalid lines

        except Exception as e:
            print(f"[MetricsArchive] ERROR loading session: {e}")

        return frames


# Self-test function
def _self_test():
    """Test MetricsLogger functionality"""
    print("=" * 60)
    print("MetricsLogger Self-Test")
    print("=" * 60)

    try:
        from metrics_frame import create_test_frame
        import tempfile
        import shutil

        # Create temporary directory for testing
        temp_dir = tempfile.mkdtemp()
        print(f"\n1. Using temp directory: {temp_dir}")

        # Initialize logger
        print("\n2. Initializing logger...")
        logger = MetricsLogger(
            log_dir=temp_dir,
            session_name="test_session",
            compress_on_close=False  # Disable for testing
        )
        print("   ✓ Logger initialized")

        # Log some test frames
        print("\n3. Logging test frames...")
        for i in range(10):
            frame = create_test_frame(frame_id=i)
            logger.log_frame(frame)

        print(f"   ✓ Logged {logger.frames_logged} frames")

        # Get statistics
        print("\n4. Checking statistics...")
        stats = logger.get_statistics()
        print(f"   Frames: {stats['frames_logged']}")
        print(f"   Duration: {stats['duration_seconds']:.2f}s")
        print(f"   FPS: {stats['average_fps']:.1f}")
        print("   ✓ Statistics OK")

        # Close logger
        print("\n5. Closing logger...")
        logger.close()
        print("   ✓ Logger closed")

        # Test archive reading
        print("\n6. Testing archive reading...")
        archive = MetricsArchive(log_dir=temp_dir)
        sessions = archive.list_sessions()
        print(f"   Found {len(sessions)} sessions")

        if len(sessions) > 0:
            loaded_frames = archive.load_session_jsonl("test_session")
            print(f"   Loaded {len(loaded_frames)} frames")
            assert len(loaded_frames) == 10
            print("   ✓ Archive reading OK")

        # Cleanup
        print("\n7. Cleanup...")
        shutil.rmtree(temp_dir)
        print("   ✓ Cleanup complete")

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
