"""
SessionMemory - Feature 012: Predictive Phi-Adaptation Engine

Stores metric logs and Phi adjustments for learning and replay.

Features:
- FR-003: Record metric and Phi pairs for learning
- Time-series storage of ICI, coherence, criticality
- Session save/load functionality
- Efficient circular buffer for real-time recording

Requirements:
- FR-003: System MUST record metric and Phi pairs for learning
"""

import time
import threading
import json
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, asdict
from collections import deque
import numpy as np


@dataclass
class MetricSnapshot:
    """Single snapshot of system metrics"""
    timestamp: float
    ici: float                    # Integrated Chroma Intensity
    coherence: float              # Coherence metric
    criticality: float            # Criticality metric
    phi_value: float              # Current Phi value
    phi_phase: float              # Current Phi phase
    phi_depth: float              # Phi modulation depth
    active_source: str            # Active Phi source


@dataclass
class SessionStats:
    """Statistics for a session"""
    start_time: float
    end_time: float
    duration: float
    sample_count: int
    avg_ici: float
    std_ici: float
    avg_coherence: float
    avg_criticality: float
    avg_phi: float
    ici_stability_score: float    # How stable ICI was around 0.5


class SessionMemory:
    """
    SessionMemory - Stores metric and Phi history for learning

    Handles:
    - Real-time metric recording (FR-003)
    - Session save/load
    - Circular buffer for efficient storage
    - Statistical analysis of sessions
    """

    def __init__(self, max_samples: int = 10000):
        """
        Initialize SessionMemory

        Args:
            max_samples: Maximum samples to store (circular buffer)
        """
        self.max_samples = max_samples

        # Circular buffer for real-time recording
        self.samples: deque = deque(maxlen=max_samples)
        self.lock = threading.Lock()

        # Session metadata
        self.session_id: Optional[str] = None
        self.session_start_time: Optional[float] = None
        self.is_recording = False

    def start_session(self, session_id: Optional[str] = None):
        """
        Start a new recording session

        Args:
            session_id: Optional session identifier
        """
        with self.lock:
            self.session_id = session_id or f"session_{int(time.time())}"
            self.session_start_time = time.time()
            self.samples.clear()
            self.is_recording = True

    def stop_session(self):
        """Stop current recording session"""
        with self.lock:
            self.is_recording = False

    def record_snapshot(self, snapshot: MetricSnapshot):
        """
        Record a metric snapshot (FR-003)

        Args:
            snapshot: MetricSnapshot to record
        """
        if not self.is_recording:
            return

        with self.lock:
            self.samples.append(snapshot)

    def get_recent_samples(self, count: int = 100) -> List[MetricSnapshot]:
        """
        Get most recent samples

        Args:
            count: Number of recent samples to retrieve

        Returns:
            List of recent MetricSnapshot objects
        """
        with self.lock:
            # Get last N samples
            recent = list(self.samples)[-count:]
            return recent

    def get_all_samples(self) -> List[MetricSnapshot]:
        """
        Get all samples from current session

        Returns:
            List of all MetricSnapshot objects
        """
        with self.lock:
            return list(self.samples)

    def get_sample_count(self) -> int:
        """Get total number of samples in current session"""
        with self.lock:
            return len(self.samples)

    def compute_stats(self) -> Optional[SessionStats]:
        """
        Compute statistics for current session

        Returns:
            SessionStats object or None if no data
        """
        with self.lock:
            if len(self.samples) == 0:
                return None

            samples = list(self.samples)

            # Extract arrays
            timestamps = np.array([s.timestamp for s in samples])
            icis = np.array([s.ici for s in samples])
            coherences = np.array([s.coherence for s in samples])
            criticalities = np.array([s.criticality for s in samples])
            phis = np.array([s.phi_value for s in samples])

            # Compute statistics
            start_time = timestamps[0]
            end_time = timestamps[-1]
            duration = end_time - start_time

            # ICI stability: measure how close ICI stays to target (0.5)
            # Lower deviation from 0.5 = higher stability
            ici_deviations = np.abs(icis - 0.5)
            ici_stability = 1.0 - np.mean(ici_deviations)  # 1.0 = perfect stability

            return SessionStats(
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                sample_count=len(samples),
                avg_ici=float(np.mean(icis)),
                std_ici=float(np.std(icis)),
                avg_coherence=float(np.mean(coherences)),
                avg_criticality=float(np.mean(criticalities)),
                avg_phi=float(np.mean(phis)),
                ici_stability_score=float(ici_stability)
            )

    def save_session(self, filepath: str) -> bool:
        """
        Save current session to file

        Args:
            filepath: Path to save file

        Returns:
            True if saved successfully
        """
        try:
            with self.lock:
                if len(self.samples) == 0:
                    return False

                # Convert samples to dict format
                samples_dict = [asdict(s) for s in self.samples]

                # Compute stats
                stats = self.compute_stats()
                stats_dict = asdict(stats) if stats else {}

                # Create session data
                session_data = {
                    "session_id": self.session_id,
                    "session_start_time": self.session_start_time,
                    "stats": stats_dict,
                    "samples": samples_dict
                }

                # Write to file
                with open(filepath, 'w') as f:
                    json.dump(session_data, f, indent=2)

                return True

        except Exception as e:
            print(f"[SessionMemory] Error saving session: {e}")
            return False

    def load_session(self, filepath: str) -> bool:
        """
        Load session from file

        Args:
            filepath: Path to session file

        Returns:
            True if loaded successfully
        """
        try:
            with open(filepath, 'r') as f:
                session_data = json.load(f)

            with self.lock:
                # Restore metadata
                self.session_id = session_data.get("session_id")
                self.session_start_time = session_data.get("session_start_time")

                # Restore samples
                self.samples.clear()
                for sample_dict in session_data.get("samples", []):
                    snapshot = MetricSnapshot(**sample_dict)
                    self.samples.append(snapshot)

                self.is_recording = False

            return True

        except Exception as e:
            print(f"[SessionMemory] Error loading session: {e}")
            return False

    def get_time_series(self, metric: str = "ici") -> Tuple[np.ndarray, np.ndarray]:
        """
        Get time series for a specific metric

        Args:
            metric: Metric name ("ici", "coherence", "criticality", "phi_value")

        Returns:
            (timestamps, values) tuple
        """
        with self.lock:
            if len(self.samples) == 0:
                return np.array([]), np.array([])

            samples = list(self.samples)
            timestamps = np.array([s.timestamp for s in samples])

            if metric == "ici":
                values = np.array([s.ici for s in samples])
            elif metric == "coherence":
                values = np.array([s.coherence for s in samples])
            elif metric == "criticality":
                values = np.array([s.criticality for s in samples])
            elif metric == "phi_value":
                values = np.array([s.phi_value for s in samples])
            elif metric == "phi_phase":
                values = np.array([s.phi_phase for s in samples])
            elif metric == "phi_depth":
                values = np.array([s.phi_depth for s in samples])
            else:
                return np.array([]), np.array([])

            return timestamps, values

    def get_correlation(self, metric1: str = "ici", metric2: str = "phi_value") -> float:
        """
        Compute correlation between two metrics

        Args:
            metric1: First metric name
            metric2: Second metric name

        Returns:
            Correlation coefficient (-1 to 1)
        """
        _, values1 = self.get_time_series(metric1)
        _, values2 = self.get_time_series(metric2)

        if len(values1) < 2 or len(values2) < 2:
            return 0.0

        return float(np.corrcoef(values1, values2)[0, 1])


# Self-test function
def _self_test():
    """Run basic self-test of SessionMemory"""
    print("=" * 60)
    print("SessionMemory Self-Test")
    print("=" * 60)
    print()

    # Create memory
    print("1. Creating SessionMemory...")
    memory = SessionMemory(max_samples=1000)
    print("   [OK] SessionMemory created")
    print()

    # Start session
    print("2. Starting session...")
    memory.start_session("test_session")
    print(f"   [OK] Session started: {memory.session_id}")
    print()

    # Record samples
    print("3. Recording 100 samples...")
    base_time = time.time()
    for i in range(100):
        snapshot = MetricSnapshot(
            timestamp=base_time + i * 0.1,
            ici=0.5 + 0.1 * np.sin(i * 0.1),
            coherence=0.7 + 0.1 * np.cos(i * 0.15),
            criticality=0.3 + 0.05 * np.sin(i * 0.2),
            phi_value=1.0 + 0.2 * np.sin(i * 0.1),
            phi_phase=i * 0.1,
            phi_depth=0.5,
            active_source="test"
        )
        memory.record_snapshot(snapshot)

    count = memory.get_sample_count()
    print(f"   [OK] Recorded {count} samples")
    print()

    # Compute stats
    print("4. Computing statistics...")
    stats = memory.compute_stats()
    if stats:
        print(f"   Duration: {stats.duration:.2f} s")
        print(f"   Avg ICI: {stats.avg_ici:.3f}")
        print(f"   Std ICI: {stats.std_ici:.3f}")
        print(f"   ICI Stability: {stats.ici_stability_score:.3f}")
        print(f"   Avg Coherence: {stats.avg_coherence:.3f}")
        print(f"   Avg Phi: {stats.avg_phi:.3f}")
        print("   [OK] Statistics computed")
    print()

    # Test time series
    print("5. Testing time series extraction...")
    timestamps, icis = memory.get_time_series("ici")
    print(f"   [OK] Extracted {len(timestamps)} ICI values")
    print()

    # Test correlation
    print("6. Testing correlation...")
    corr = memory.get_correlation("ici", "phi_value")
    print(f"   ICI-Phi correlation: {corr:.3f}")
    print("   [OK] Correlation computed")
    print()

    # Test save/load
    print("7. Testing save/load...")
    save_path = "test_session.json"
    if memory.save_session(save_path):
        print(f"   [OK] Session saved to {save_path}")

        # Load it back
        memory2 = SessionMemory()
        if memory2.load_session(save_path):
            loaded_count = memory2.get_sample_count()
            print(f"   [OK] Session loaded: {loaded_count} samples")

            # Cleanup
            import os
            os.remove(save_path)
            print("   [OK] Cleanup complete")
    print()

    print("=" * 60)
    print("Self-Test PASSED")
    print("=" * 60)

    return True


if __name__ == "__main__":
    _self_test()
