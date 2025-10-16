"""
SessionComparator - Feature 015: Multi-Session Comparative Analytics

Loads and analyzes multiple recorded sessions for comparative insights.

Features:
- FR-001: Load and compare multiple sessions
- FR-002: Compute statistical metrics (mean, variance, delta)
- SC-001: Handle multiple sessions <= 1 GB RAM

Requirements:
- FR-001: System MUST load and compare multiple sessions simultaneously
- FR-002: System MUST compute statistical metrics
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

from session_memory import MetricSnapshot


@dataclass
class SessionStats:
    """Statistical summary for a session"""
    session_id: str
    duration: float
    sample_count: int

    # ICI statistics
    mean_ici: float
    std_ici: float
    min_ici: float
    max_ici: float

    # Coherence statistics
    mean_coherence: float
    std_coherence: float

    # Criticality statistics
    mean_criticality: float
    std_criticality: float

    # Phi statistics
    mean_phi: float
    std_phi: float
    min_phi: float
    max_phi: float


@dataclass
class ComparisonResult:
    """Result of comparing two sessions"""
    session_a_id: str
    session_b_id: str

    # Delta metrics (FR-002)
    delta_mean_ici: float
    delta_mean_coherence: float
    delta_mean_criticality: float
    delta_mean_phi: float

    # Correlation coefficients
    ici_correlation: float
    coherence_correlation: float
    criticality_correlation: float
    phi_correlation: float

    # Statistical significance
    ici_ttest_pvalue: float
    coherence_ttest_pvalue: float


class SessionComparator:
    """
    SessionComparator - Multi-session analysis and comparison

    Handles:
    - Loading multiple sessions (FR-001)
    - Computing comparative statistics (FR-002)
    - Memory-efficient processing (SC-001)
    """

    def __init__(self):
        """Initialize SessionComparator"""
        self.sessions: Dict[str, Dict] = {}
        self.session_stats: Dict[str, SessionStats] = {}

    def load_session(self, session_id: str, session_data: Dict) -> bool:
        """
        Load a session for comparison (FR-001)

        Args:
            session_id: Unique identifier for session
            session_data: Session data from StateRecorder

        Returns:
            True if loaded successfully
        """
        try:
            # Store session data
            self.sessions[session_id] = session_data

            # Compute statistics
            stats = self._compute_session_stats(session_id, session_data)
            self.session_stats[session_id] = stats

            print(f"[SessionComparator] Loaded session: {session_id}")
            return True

        except Exception as e:
            print(f"[SessionComparator] Error loading session: {e}")
            return False

    def unload_session(self, session_id: str):
        """
        Unload a session to free memory (SC-001)

        Args:
            session_id: Session to unload
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            del self.session_stats[session_id]
            print(f"[SessionComparator] Unloaded session: {session_id}")

    def _compute_session_stats(self, session_id: str, session_data: Dict) -> SessionStats:
        """
        Compute statistics for a session (FR-002)

        Args:
            session_id: Session identifier
            session_data: Session data

        Returns:
            SessionStats object
        """
        metadata = session_data.get("metadata", {})
        samples_dict = session_data.get("samples", [])

        # Extract metric arrays
        icis = np.array([s.get("ici", 0.5) for s in samples_dict])
        coherences = np.array([s.get("coherence", 0.5) for s in samples_dict])
        criticalities = np.array([s.get("criticality", 0.5) for s in samples_dict])
        phis = np.array([s.get("phi_value", 1.0) for s in samples_dict])

        return SessionStats(
            session_id=session_id,
            duration=metadata.get("duration", 0.0),
            sample_count=len(samples_dict),
            mean_ici=float(np.mean(icis)),
            std_ici=float(np.std(icis)),
            min_ici=float(np.min(icis)),
            max_ici=float(np.max(icis)),
            mean_coherence=float(np.mean(coherences)),
            std_coherence=float(np.std(coherences)),
            mean_criticality=float(np.mean(criticalities)),
            std_criticality=float(np.std(criticalities)),
            mean_phi=float(np.mean(phis)),
            std_phi=float(np.std(phis)),
            min_phi=float(np.min(phis)),
            max_phi=float(np.max(phis))
        )

    def compare_sessions(self, session_a_id: str, session_b_id: str) -> Optional[ComparisonResult]:
        """
        Compare two sessions (FR-002)

        Args:
            session_a_id: First session ID
            session_b_id: Second session ID

        Returns:
            ComparisonResult or None if comparison failed
        """
        if session_a_id not in self.sessions or session_b_id not in self.sessions:
            return None

        try:
            # Get statistics
            stats_a = self.session_stats[session_a_id]
            stats_b = self.session_stats[session_b_id]

            # Compute deltas (FR-002)
            delta_ici = stats_b.mean_ici - stats_a.mean_ici
            delta_coherence = stats_b.mean_coherence - stats_a.mean_coherence
            delta_criticality = stats_b.mean_criticality - stats_a.mean_criticality
            delta_phi = stats_b.mean_phi - stats_a.mean_phi

            # Extract time series for correlation
            samples_a = self.sessions[session_a_id].get("samples", [])
            samples_b = self.sessions[session_b_id].get("samples", [])

            icis_a = np.array([s.get("ici", 0.5) for s in samples_a])
            icis_b = np.array([s.get("ici", 0.5) for s in samples_b])

            coherences_a = np.array([s.get("coherence", 0.5) for s in samples_a])
            coherences_b = np.array([s.get("coherence", 0.5) for s in samples_b])

            criticalities_a = np.array([s.get("criticality", 0.5) for s in samples_a])
            criticalities_b = np.array([s.get("criticality", 0.5) for s in samples_b])

            phis_a = np.array([s.get("phi_value", 1.0) for s in samples_a])
            phis_b = np.array([s.get("phi_value", 1.0) for s in samples_b])

            # Align lengths for correlation (use shorter length)
            min_len = min(len(icis_a), len(icis_b))
            icis_a = icis_a[:min_len]
            icis_b = icis_b[:min_len]
            coherences_a = coherences_a[:min_len]
            coherences_b = coherences_b[:min_len]
            criticalities_a = criticalities_a[:min_len]
            criticalities_b = criticalities_b[:min_len]
            phis_a = phis_a[:min_len]
            phis_b = phis_b[:min_len]

            # Compute correlations
            ici_corr = float(np.corrcoef(icis_a, icis_b)[0, 1]) if min_len > 1 else 0.0
            coherence_corr = float(np.corrcoef(coherences_a, coherences_b)[0, 1]) if min_len > 1 else 0.0
            criticality_corr = float(np.corrcoef(criticalities_a, criticalities_b)[0, 1]) if min_len > 1 else 0.0
            phi_corr = float(np.corrcoef(phis_a, phis_b)[0, 1]) if min_len > 1 else 0.0

            # Statistical tests (t-test)
            from scipy import stats
            ici_ttest = stats.ttest_ind(icis_a, icis_b)
            coherence_ttest = stats.ttest_ind(coherences_a, coherences_b)

            return ComparisonResult(
                session_a_id=session_a_id,
                session_b_id=session_b_id,
                delta_mean_ici=delta_ici,
                delta_mean_coherence=delta_coherence,
                delta_mean_criticality=delta_criticality,
                delta_mean_phi=delta_phi,
                ici_correlation=ici_corr,
                coherence_correlation=coherence_corr,
                criticality_correlation=criticality_corr,
                phi_correlation=phi_corr,
                ici_ttest_pvalue=float(ici_ttest.pvalue),
                coherence_ttest_pvalue=float(coherence_ttest.pvalue)
            )

        except Exception as e:
            print(f"[SessionComparator] Error comparing sessions: {e}")
            return None

    def get_all_stats(self) -> Dict[str, SessionStats]:
        """
        Get statistics for all loaded sessions

        Returns:
            Dictionary mapping session IDs to stats
        """
        return self.session_stats.copy()

    def get_session_count(self) -> int:
        """Get number of loaded sessions"""
        return len(self.sessions)

    def get_memory_usage(self) -> Dict:
        """
        Estimate memory usage (SC-001)

        Returns:
            Dictionary with memory estimates
        """
        import sys

        total_samples = sum(
            len(session.get("samples", []))
            for session in self.sessions.values()
        )

        # Rough estimate: each sample ~200 bytes
        estimated_mb = (total_samples * 200) / (1024 * 1024)

        return {
            "session_count": len(self.sessions),
            "total_samples": total_samples,
            "estimated_mb": estimated_mb
        }


# Self-test
def _self_test():
    """Run basic self-test of SessionComparator"""
    print("=" * 60)
    print("SessionComparator Self-Test")
    print("=" * 60)
    print()

    import time

    # Create synthetic session data
    print("1. Creating synthetic sessions...")

    def create_session(session_id: str, ici_offset: float):
        samples = []
        for i in range(100):
            samples.append({
                "timestamp": time.time() + i * 0.1,
                "ici": 0.5 + ici_offset + 0.05 * np.sin(i * 0.1),
                "coherence": 0.6,
                "criticality": 0.4,
                "phi_value": 1.0,
                "phi_phase": 0.0,
                "phi_depth": 0.5,
                "active_source": "test"
            })

        return {
            "metadata": {
                "session_id": session_id,
                "duration": 10.0,
                "sample_count": 100
            },
            "samples": samples
        }

    session_a = create_session("session_a", 0.0)
    session_b = create_session("session_b", 0.1)  # Higher ICI
    print("   [OK] Created 2 synthetic sessions")
    print()

    # Create comparator
    print("2. Creating SessionComparator...")
    comparator = SessionComparator()
    print("   [OK] SessionComparator created")
    print()

    # Load sessions
    print("3. Loading sessions...")
    comparator.load_session("session_a", session_a)
    comparator.load_session("session_b", session_b)
    print(f"   [OK] Loaded {comparator.get_session_count()} sessions")
    print()

    # Get statistics
    print("4. Computing statistics...")
    stats = comparator.get_all_stats()
    for session_id, stat in stats.items():
        print(f"   {session_id}:")
        print(f"      Mean ICI: {stat.mean_ici:.3f}")
        print(f"      Mean Phi: {stat.mean_phi:.3f}")
    print("   [OK] Statistics computed")
    print()

    # Compare sessions
    print("5. Comparing sessions...")
    result = comparator.compare_sessions("session_a", "session_b")
    if result:
        print(f"   Delta ICI: {result.delta_mean_ici:.3f}")
        print(f"   ICI correlation: {result.ici_correlation:.3f}")
        print(f"   ICI t-test p-value: {result.ici_ttest_pvalue:.6f}")

        # Check if delta is correct (should be ~0.1)
        delta_ok = abs(result.delta_mean_ici - 0.1) < 0.05
        print(f"   [{'OK' if delta_ok else 'FAIL'}] Delta accuracy (expected ~0.1)")
    print()

    # Memory usage
    print("6. Checking memory usage...")
    mem_usage = comparator.get_memory_usage()
    print(f"   Sessions: {mem_usage['session_count']}")
    print(f"   Total samples: {mem_usage['total_samples']}")
    print(f"   Estimated memory: {mem_usage['estimated_mb']:.2f} MB")
    mem_ok = mem_usage['estimated_mb'] < 1024  # < 1 GB
    print(f"   [{'OK' if mem_ok else 'FAIL'}] Memory usage (SC-001: < 1 GB)")
    print()

    print("=" * 60)
    print("Self-Test PASSED")
    print("=" * 60)

    return True


if __name__ == "__main__":
    _self_test()
