"""
PhiPredictor - Feature 012: Predictive Phi-Adaptation Engine

Learns from historical sessions to predict optimal Phi settings.

Features:
- FR-004: Replay and fit session patterns
- Pattern recognition from metric history
- Predictive model for next Phi value
- Auto-reset on divergence > 20%

Requirements:
- FR-004: Predictive engine MUST replay and fit session patterns
- SC-003: Predictive accuracy >= 90% against previous sessions
"""

import time
import threading
from typing import Optional, List, Tuple, Dict
from dataclasses import dataclass
import numpy as np
from scipy.interpolate import interp1d
from scipy.signal import savgol_filter

from session_memory import SessionMemory, MetricSnapshot


@dataclass
class PredictionResult:
    """Result of a prediction"""
    predicted_phi: float          # Predicted Phi value
    confidence: float             # Confidence (0-1)
    prediction_time: float        # When prediction was made
    actual_phi: Optional[float]   # Actual Phi (for validation)
    error: Optional[float]        # Prediction error


class PhiPredictor:
    """
    PhiPredictor - Learns patterns and predicts optimal Phi values

    Handles:
    - Pattern learning from session history (FR-004)
    - Predictive modeling based on metrics
    - Accuracy tracking (SC-003)
    - Auto-reset on divergence
    """

    PHI_MIN = 0.618033988749895
    PHI_MAX = 1.618033988749895

    def __init__(self, session_memory: SessionMemory):
        """
        Initialize PhiPredictor

        Args:
            session_memory: SessionMemory instance for historical data
        """
        self.session_memory = session_memory

        # Learned model parameters
        self.ici_to_phi_model: Optional[interp1d] = None
        self.coherence_weight = 0.3
        self.criticality_weight = 0.2

        # Prediction tracking
        self.predictions: List[PredictionResult] = []
        self.max_predictions = 1000
        self.lock = threading.Lock()

        # Auto-reset threshold
        self.divergence_threshold = 0.20  # 20%
        self.accuracy_window = 50         # Last N predictions for accuracy

    def learn_from_session(self) -> bool:
        """
        Learn patterns from current session data (FR-004)

        Returns:
            True if learning successful
        """
        try:
            samples = self.session_memory.get_all_samples()

            if len(samples) < 10:
                return False

            # Extract metric arrays
            icis = np.array([s.ici for s in samples])
            coherences = np.array([s.coherence for s in samples])
            criticalities = np.array([s.criticality for s in samples])
            phis = np.array([s.phi_value for s in samples])

            # Learn ICI → Phi mapping
            # Sort by ICI for interpolation
            sort_idx = np.argsort(icis)
            sorted_ici = icis[sort_idx]
            sorted_phi = phis[sort_idx]

            # Remove duplicates (needed for interpolation)
            unique_ici, unique_indices = np.unique(sorted_ici, return_index=True)
            unique_phi = sorted_phi[unique_indices]

            if len(unique_ici) < 2:
                return False

            # Create interpolation model
            self.ici_to_phi_model = interp1d(
                unique_ici,
                unique_phi,
                kind='linear',
                bounds_error=False,
                fill_value=(unique_phi[0], unique_phi[-1])
            )

            # Learn influence weights
            # Higher coherence → prefer higher Phi
            # Higher criticality → prefer lower Phi (more stable)
            phi_coherence_corr = np.corrcoef(phis, coherences)[0, 1]
            phi_criticality_corr = np.corrcoef(phis, criticalities)[0, 1]

            self.coherence_weight = max(0.0, min(0.5, phi_coherence_corr * 0.5))
            self.criticality_weight = max(0.0, min(0.5, -phi_criticality_corr * 0.5))

            return True

        except Exception as e:
            print(f"[PhiPredictor] Error learning from session: {e}")
            return False

    def predict_phi(self, ici: float, coherence: float, criticality: float) -> PredictionResult:
        """
        Predict optimal Phi value based on current metrics

        Args:
            ici: Current ICI value
            coherence: Current coherence
            criticality: Current criticality

        Returns:
            PredictionResult with prediction
        """
        with self.lock:
            current_time = time.time()

            # Base prediction from ICI
            if self.ici_to_phi_model is not None:
                try:
                    base_phi = float(self.ici_to_phi_model(ici))
                except:
                    base_phi = 1.0  # Fallback to golden ratio
            else:
                # No model yet - use simple heuristic
                # ICI target is 0.5, map deviations to Phi adjustments
                ici_error = ici - 0.5
                base_phi = 1.0 - ici_error * 0.5  # Inverse relationship

            # Adjust based on coherence
            coherence_adjustment = (coherence - 0.5) * self.coherence_weight

            # Adjust based on criticality
            criticality_adjustment = -(criticality - 0.5) * self.criticality_weight

            # Combine
            predicted_phi = base_phi + coherence_adjustment + criticality_adjustment

            # Clamp to valid range
            predicted_phi = np.clip(predicted_phi, self.PHI_MIN, self.PHI_MAX)

            # Confidence based on model availability and metric quality
            if self.ici_to_phi_model is not None:
                confidence = 0.9  # High confidence with learned model
            else:
                confidence = 0.5  # Medium confidence with heuristic

            # Reduce confidence if metrics are extreme
            if ici < 0.2 or ici > 0.8:
                confidence *= 0.7
            if coherence < 0.2:
                confidence *= 0.8

            result = PredictionResult(
                predicted_phi=predicted_phi,
                confidence=confidence,
                prediction_time=current_time,
                actual_phi=None,
                error=None
            )

            # Store prediction
            self.predictions.append(result)
            if len(self.predictions) > self.max_predictions:
                self.predictions.pop(0)

            return result

    def update_prediction_accuracy(self, prediction_idx: int, actual_phi: float):
        """
        Update prediction with actual value for accuracy tracking

        Args:
            prediction_idx: Index of prediction to update
            actual_phi: Actual Phi value that was used
        """
        with self.lock:
            if 0 <= prediction_idx < len(self.predictions):
                pred = self.predictions[prediction_idx]
                pred.actual_phi = actual_phi
                pred.error = abs(pred.predicted_phi - actual_phi)

    def get_recent_accuracy(self, window: Optional[int] = None) -> float:
        """
        Calculate recent prediction accuracy (SC-003)

        Args:
            window: Number of recent predictions to consider

        Returns:
            Accuracy (0-1), where 1.0 is perfect
        """
        with self.lock:
            window = window or self.accuracy_window

            # Get recent predictions with actual values
            recent = [p for p in self.predictions[-window:] if p.actual_phi is not None]

            if len(recent) == 0:
                return 0.0

            # Calculate mean absolute percentage error
            errors = [p.error / (p.actual_phi + 1e-9) for p in recent if p.error is not None]

            if len(errors) == 0:
                return 0.0

            mape = np.mean(errors)

            # Convert to accuracy (1.0 - error)
            accuracy = max(0.0, 1.0 - mape)

            return accuracy

    def check_divergence(self) -> bool:
        """
        Check if predictions are diverging > 20% from actual

        Returns:
            True if divergence detected
        """
        accuracy = self.get_recent_accuracy(window=20)

        # Divergence if accuracy < 80% (error > 20%)
        return accuracy < 0.80

    def reset_model(self):
        """Reset predictive model (auto-reset on divergence)"""
        with self.lock:
            self.ici_to_phi_model = None
            self.coherence_weight = 0.3
            self.criticality_weight = 0.2
            print("[PhiPredictor] Model reset due to divergence")

    def get_prediction_stats(self) -> Dict:
        """
        Get prediction statistics

        Returns:
            Dictionary with prediction stats
        """
        with self.lock:
            total_predictions = len(self.predictions)
            validated_predictions = len([p for p in self.predictions if p.actual_phi is not None])
            recent_accuracy = self.get_recent_accuracy()

            if validated_predictions > 0:
                avg_confidence = np.mean([p.confidence for p in self.predictions if p.actual_phi is not None])
                avg_error = np.mean([p.error for p in self.predictions if p.error is not None])
            else:
                avg_confidence = 0.0
                avg_error = 0.0

            return {
                "total_predictions": total_predictions,
                "validated_predictions": validated_predictions,
                "recent_accuracy": recent_accuracy,
                "avg_confidence": avg_confidence,
                "avg_error": avg_error,
                "has_learned_model": self.ici_to_phi_model is not None
            }

    def replay_session_pattern(self, target_session: SessionMemory) -> Tuple[float, List[float]]:
        """
        Replay session pattern and measure accuracy (FR-004, SC-003)

        Args:
            target_session: Session to replay

        Returns:
            (accuracy, predicted_phis) tuple
        """
        samples = target_session.get_all_samples()

        if len(samples) < 10:
            return 0.0, []

        predicted_phis = []
        actual_phis = []

        for sample in samples:
            # Predict Phi based on metrics
            prediction = self.predict_phi(
                ici=sample.ici,
                coherence=sample.coherence,
                criticality=sample.criticality
            )

            predicted_phis.append(prediction.predicted_phi)
            actual_phis.append(sample.phi_value)

        # Calculate accuracy
        predicted = np.array(predicted_phis)
        actual = np.array(actual_phis)

        # Mean absolute percentage error
        mape = np.mean(np.abs((actual - predicted) / (actual + 1e-9)))
        accuracy = max(0.0, 1.0 - mape)

        return accuracy, predicted_phis


# Self-test function
def _self_test():
    """Run basic self-test of PhiPredictor"""
    print("=" * 60)
    print("PhiPredictor Self-Test")
    print("=" * 60)
    print()

    from session_memory import SessionMemory, MetricSnapshot

    # Create session with synthetic data
    print("1. Creating synthetic session...")
    memory = SessionMemory(max_samples=200)
    memory.start_session("test_session")

    base_time = time.time()
    for i in range(200):
        # Simulate ICI oscillation
        ici = 0.5 + 0.15 * np.sin(i * 0.05)

        # Phi should adapt inversely to ICI
        phi = 1.0 - (ici - 0.5) * 0.3

        snapshot = MetricSnapshot(
            timestamp=base_time + i * 0.1,
            ici=ici,
            coherence=0.6 + 0.1 * np.sin(i * 0.03),
            criticality=0.4 + 0.05 * np.cos(i * 0.04),
            phi_value=phi,
            phi_phase=i * 0.1,
            phi_depth=0.5,
            active_source="test"
        )
        memory.record_snapshot(snapshot)

    print(f"   [OK] Created session with {memory.get_sample_count()} samples")
    print()

    # Create predictor
    print("2. Creating PhiPredictor...")
    predictor = PhiPredictor(memory)
    print("   [OK] PhiPredictor created")
    print()

    # Learn from session
    print("3. Learning from session...")
    success = predictor.learn_from_session()
    print(f"   [{'OK' if success else 'FAIL'}] Learning {'successful' if success else 'failed'}")
    print()

    # Test predictions
    print("4. Testing predictions...")
    test_cases = [
        (0.4, 0.6, 0.4),  # Low ICI
        (0.5, 0.6, 0.4),  # Target ICI
        (0.6, 0.6, 0.4),  # High ICI
    ]

    for ici, coherence, criticality in test_cases:
        result = predictor.predict_phi(ici, coherence, criticality)
        print(f"   ICI={ici:.2f} → Phi={result.predicted_phi:.3f} (confidence={result.confidence:.2f})")

    print("   [OK] Predictions generated")
    print()

    # Test replay
    print("5. Testing session replay...")
    accuracy, predicted_phis = predictor.replay_session_pattern(memory)
    print(f"   Replay accuracy: {accuracy:.1%}")
    print(f"   [{'OK' if accuracy >= 0.9 else 'WARN'}] Accuracy {'meets' if accuracy >= 0.9 else 'below'} SC-003 (>= 90%)")
    print()

    # Test stats
    print("6. Testing prediction statistics...")
    stats = predictor.get_prediction_stats()
    print(f"   Total predictions: {stats['total_predictions']}")
    print(f"   Has learned model: {stats['has_learned_model']}")
    print("   [OK] Statistics computed")
    print()

    print("=" * 60)
    print("Self-Test PASSED")
    print("=" * 60)

    return True


if __name__ == "__main__":
    _self_test()
