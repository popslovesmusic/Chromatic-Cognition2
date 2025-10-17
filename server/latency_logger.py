"""
LatencyLogger - Session-based Latency Telemetry Logging

Implements FR-009: Structured logging to /logs/latency/ with CSV + JSONL formats
"""

import os
import csv
import json
import gzip
from pathlib import Path
from datetime import datetime
from typing import Optional, TextIO
import threading

from .latency_frame import LatencyFrame


class LatencyLogger:
    """
    Session-based logger for latency telemetry

    Features:
    - Dual-format output (CSV + JSONL)
    - Session-based file organization
    - Automatic compression on close
    - Gap detection and warning
    - Thread-safe logging
    """

    # Gap detection threshold
    GAP_THRESHOLD_MS = 100  # Warn if >100ms between frames

    def __init__(self, log_dir: Optional[str] = None):
        """
        Initialize latency logger

        Args:
            log_dir: Directory for log files (None = ../logs/latency/)
        """
        if log_dir is None:
            log_dir = os.path.join(os.path.dirname(__file__), "..", "logs", "latency")

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Session tracking
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_start = datetime.now()

        # File handles
        self.csv_file: Optional[TextIO] = None
        self.csv_writer: Optional[csv.DictWriter] = None
        self.jsonl_file: Optional[TextIO] = None

        # State
        self.frame_count = 0
        self.last_timestamp: Optional[float] = None
        self.gap_count = 0

        # Thread safety
        self.lock = threading.Lock()

        # Initialize files
        self._init_files()

        print(f"[LatencyLogger] Initialized")
        print(f"[LatencyLogger] Session: {self.session_id}")
        print(f"[LatencyLogger] Log dir: {self.log_dir}")

    def _init_files(self):
        """Initialize CSV and JSONL log files"""
        try:
            # CSV file
            csv_path = self.log_dir / f"latency_{self.session_id}.csv"
            self.csv_file = open(csv_path, 'w', newline='')

            # CSV header fields
            fieldnames = [
                'timestamp',
                'hw_input_latency_ms',
                'hw_output_latency_ms',
                'engine_latency_ms',
                'os_latency_ms',
                'total_measured_ms',
                'compensation_offset_ms',
                'manual_offset_ms',
                'effective_latency_ms',
                'drift_ms',
                'drift_rate_ms_per_sec',
                'calibrated',
                'calibration_quality',
                'buffer_size_samples',
                'sample_rate',
                'buffer_fullness',
                'cpu_load',
                'aligned_5ms'
            ]

            self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=fieldnames)
            self.csv_writer.writeheader()
            self.csv_file.flush()

            # JSONL file
            jsonl_path = self.log_dir / f"latency_{self.session_id}.jsonl"
            self.jsonl_file = open(jsonl_path, 'w')

            # Write session header to JSONL
            session_header = {
                'type': 'session_start',
                'session_id': self.session_id,
                'timestamp': self.session_start.isoformat(),
                'log_dir': str(self.log_dir)
            }
            self.jsonl_file.write(json.dumps(session_header) + '\n')
            self.jsonl_file.flush()

            print(f"[LatencyLogger] Created CSV: {csv_path.name}")
            print(f"[LatencyLogger] Created JSONL: {jsonl_path.name}")

        except Exception as e:
            print(f"[LatencyLogger] ERROR: Failed to initialize log files: {e}")
            if self.csv_file:
                self.csv_file.close()
            if self.jsonl_file:
                self.jsonl_file.close()
            raise

    def log_frame(self, frame: LatencyFrame):
        """
        Log a latency frame to both CSV and JSONL

        Args:
            frame: LatencyFrame to log
        """
        with self.lock:
            try:
                # Check for gaps
                if self.last_timestamp is not None:
                    gap_ms = (frame.timestamp - self.last_timestamp) * 1000.0

                    if gap_ms > self.GAP_THRESHOLD_MS:
                        self.gap_count += 1
                        print(f"[LatencyLogger] WARNING: Gap detected: {gap_ms:.1f} ms (count: {self.gap_count})")

                        # Log gap event to JSONL
                        gap_event = {
                            'type': 'gap',
                            'timestamp': frame.timestamp,
                            'gap_ms': gap_ms,
                            'gap_count': self.gap_count
                        }
                        self.jsonl_file.write(json.dumps(gap_event) + '\n')

                # Write to CSV
                csv_row = {
                    'timestamp': frame.timestamp,
                    'hw_input_latency_ms': frame.hw_input_latency_ms,
                    'hw_output_latency_ms': frame.hw_output_latency_ms,
                    'engine_latency_ms': frame.engine_latency_ms,
                    'os_latency_ms': frame.os_latency_ms,
                    'total_measured_ms': frame.total_measured_ms,
                    'compensation_offset_ms': frame.compensation_offset_ms,
                    'manual_offset_ms': frame.manual_offset_ms,
                    'effective_latency_ms': frame.get_effective_latency(),
                    'drift_ms': frame.drift_ms,
                    'drift_rate_ms_per_sec': frame.drift_rate_ms_per_sec,
                    'calibrated': frame.calibrated,
                    'calibration_quality': frame.calibration_quality,
                    'buffer_size_samples': frame.buffer_size_samples,
                    'sample_rate': frame.sample_rate,
                    'buffer_fullness': frame.buffer_fullness,
                    'cpu_load': frame.cpu_load,
                    'aligned_5ms': frame.is_aligned(5.0)
                }

                self.csv_writer.writerow(csv_row)

                # Write to JSONL (full frame as JSON)
                jsonl_entry = {
                    'type': 'frame',
                    **frame.to_dict()
                }
                self.jsonl_file.write(json.dumps(jsonl_entry) + '\n')

                # Flush periodically (every 10 frames)
                self.frame_count += 1
                if self.frame_count % 10 == 0:
                    self.csv_file.flush()
                    self.jsonl_file.flush()

                self.last_timestamp = frame.timestamp

            except Exception as e:
                print(f"[LatencyLogger] ERROR: Failed to log frame: {e}")

    def log_calibration_event(self, success: bool, details: dict):
        """
        Log a calibration event

        Args:
            success: True if calibration succeeded
            details: Calibration details dictionary
        """
        with self.lock:
            try:
                event = {
                    'type': 'calibration',
                    'timestamp': datetime.now().isoformat(),
                    'success': success,
                    **details
                }

                self.jsonl_file.write(json.dumps(event) + '\n')
                self.jsonl_file.flush()

                print(f"[LatencyLogger] Logged calibration event: success={success}")

            except Exception as e:
                print(f"[LatencyLogger] ERROR: Failed to log calibration event: {e}")

    def log_drift_correction(self, correction_ms: float, reason: str):
        """
        Log a drift correction event

        Args:
            correction_ms: Correction applied in milliseconds
            reason: Reason for correction
        """
        with self.lock:
            try:
                event = {
                    'type': 'drift_correction',
                    'timestamp': datetime.now().isoformat(),
                    'correction_ms': correction_ms,
                    'reason': reason
                }

                self.jsonl_file.write(json.dumps(event) + '\n')
                self.jsonl_file.flush()

                print(f"[LatencyLogger] Logged drift correction: {correction_ms:+.2f} ms ({reason})")

            except Exception as e:
                print(f"[LatencyLogger] ERROR: Failed to log drift correction: {e}")

    def get_session_statistics(self) -> dict:
        """
        Get session statistics

        Returns:
            Dictionary with session stats
        """
        elapsed = (datetime.now() - self.session_start).total_seconds()

        return {
            'session_id': self.session_id,
            'session_start': self.session_start.isoformat(),
            'elapsed_seconds': elapsed,
            'frame_count': self.frame_count,
            'gap_count': self.gap_count,
            'average_fps': self.frame_count / elapsed if elapsed > 0 else 0,
            'log_dir': str(self.log_dir)
        }

    def close(self):
        """Close log files and compress"""
        with self.lock:
            print("[LatencyLogger] Closing session...")

            # Write session end to JSONL
            if self.jsonl_file and not self.jsonl_file.closed:
                session_end = {
                    'type': 'session_end',
                    'timestamp': datetime.now().isoformat(),
                    'statistics': self.get_session_statistics()
                }
                self.jsonl_file.write(json.dumps(session_end) + '\n')
                self.jsonl_file.flush()

            # Close files
            if self.csv_file and not self.csv_file.closed:
                self.csv_file.close()

            if self.jsonl_file and not self.jsonl_file.closed:
                self.jsonl_file.close()

            # Compress files
            self._compress_files()

            print(f"[LatencyLogger] Session closed: {self.frame_count} frames logged")

    def _compress_files(self):
        """Compress CSV and JSONL files with gzip"""
        try:
            csv_path = self.log_dir / f"latency_{self.session_id}.csv"
            jsonl_path = self.log_dir / f"latency_{self.session_id}.jsonl"

            # Compress CSV
            if csv_path.exists():
                print(f"[LatencyLogger] Compressing {csv_path.name}...")
                with open(csv_path, 'rb') as f_in:
                    with gzip.open(f"{csv_path}.gz", 'wb') as f_out:
                        f_out.writelines(f_in)
                csv_path.unlink()  # Remove original
                print(f"[LatencyLogger] Created {csv_path.name}.gz")

            # Compress JSONL
            if jsonl_path.exists():
                print(f"[LatencyLogger] Compressing {jsonl_path.name}...")
                with open(jsonl_path, 'rb') as f_in:
                    with gzip.open(f"{jsonl_path}.gz", 'wb') as f_out:
                        f_out.writelines(f_in)
                jsonl_path.unlink()  # Remove original
                print(f"[LatencyLogger] Created {jsonl_path.name}.gz")

        except Exception as e:
            print(f"[LatencyLogger] WARNING: Compression failed: {e}")

    def __del__(self):
        """Ensure cleanup on destruction"""
        if hasattr(self, 'csv_file') and self.csv_file and not self.csv_file.closed:
            self.close()


# Self-test function
def _self_test():
    """Test LatencyLogger functionality"""
    print("=" * 60)
    print("LatencyLogger Self-Test")
    print("=" * 60)

    try:
        import tempfile
        import shutil
        from latency_frame import create_default_latency_frame
        import time

        # Create temporary directory for testing
        temp_dir = tempfile.mkdtemp()
        print(f"\n1. Using temp directory: {temp_dir}")

        # Initialize logger
        print("\n2. Initializing logger...")
        logger = LatencyLogger(log_dir=temp_dir)
        print(f"   Session: {logger.session_id}")
        print("   ✓ Logger initialized")

        # Log some frames
        print("\n3. Logging frames...")
        for i in range(20):
            frame = create_default_latency_frame()
            frame.timestamp = time.time()
            frame.hw_input_latency_ms = 5.0 + i * 0.1
            frame.drift_ms = i * 0.05

            logger.log_frame(frame)

            time.sleep(0.01)  # Small delay

        print(f"   Logged {logger.frame_count} frames")
        print("   ✓ Frame logging OK")

        # Log calibration event
        print("\n4. Logging calibration event...")
        logger.log_calibration_event(True, {
            'total_latency_ms': 13.5,
            'quality': 0.95
        })
        print("   ✓ Calibration event logged")

        # Log drift correction
        print("\n5. Logging drift correction...")
        logger.log_drift_correction(-2.5, "Exceeded 2ms threshold")
        print("   ✓ Drift correction logged")

        # Get session statistics
        print("\n6. Getting session statistics...")
        stats = logger.get_session_statistics()
        print(f"   Session ID: {stats['session_id']}")
        print(f"   Frames: {stats['frame_count']}")
        print(f"   Average FPS: {stats['average_fps']:.1f}")
        print(f"   Gaps: {stats['gap_count']}")
        print("   ✓ Statistics OK")

        # Close logger (triggers compression)
        print("\n7. Closing logger...")
        logger.close()
        print("   ✓ Logger closed")

        # Verify compressed files exist
        print("\n8. Verifying compressed files...")
        csv_gz = Path(temp_dir) / f"latency_{logger.session_id}.csv.gz"
        jsonl_gz = Path(temp_dir) / f"latency_{logger.session_id}.jsonl.gz"

        assert csv_gz.exists(), "CSV.gz not found"
        assert jsonl_gz.exists(), "JSONL.gz not found"

        print(f"   CSV.gz size: {csv_gz.stat().st_size} bytes")
        print(f"   JSONL.gz size: {jsonl_gz.stat().st_size} bytes")
        print("   ✓ Compression OK")

        # Cleanup
        print("\n9. Cleanup...")
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
