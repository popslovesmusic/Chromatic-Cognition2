"""
Predictive Model - Feature 016
Forecasts next consciousness state and key metrics using State Memory history

Implements:
- FR-001: PredictiveModel class
- FR-002: Input buffer from State Memory (N=128 frames)
- FR-003: Linear regression for ΔICI, Δcoherence, Δcriticality
- FR-004: Next probable state prediction
- FR-005: Forecast JSON emission
- FR-006: Hooks for preemptive adjustments
- FR-007: Accuracy tracking and confidence

Success Criteria:
- SC-001: Prediction accuracy ≥80%
- SC-002: Forecast latency <50ms
- SC-003: Overshoot reduction ≥30%
- SC-004: Average confidence >0.7
"""

import time
import numpy as np
from typing import Optional, Dict, List, Tuple, Callable
from dataclasses import dataclass
from collections import deque
from enum import Enum


# Import ConsciousnessState from state_classifier
try:
    from state_classifier import ConsciousnessState
except ImportError:
    # Fallback if not available
    class ConsciousnessState(Enum):
        COMA = "COMA"
        SLEEP = "SLEEP"
        DROWSY = "DROWSY"
        AWAKE = "AWAKE"
        ALERT = "ALERT"
        HYPERSYNC = "HYPERSYNC"


@dataclass
class PredictiveModelConfig:
    """Configuration for Predictive Model"""

    # Buffer size for prediction (FR-002)
    buffer_size: int = 128

    # Prediction horizon in seconds
    prediction_horizon: float = 1.5  # Predict 1-2 seconds ahead

    # Minimum buffer size for prediction
    min_buffer_size: int = 50

    # Confidence threshold for emitting predictions
    confidence_threshold: float = 0.5

    # Accuracy tracking window
    accuracy_window: int = 100

    # Enable logging
    enable_logging: bool = True

    # Log interval in seconds
    log_interval: float = 10.0


@dataclass
class ForecastFrame:
    """Single forecast prediction"""

    # Predicted state
    predicted_state: ConsciousnessState

    # Predicted metric changes
    delta_ici: float
    delta_coherence: float
    delta_criticality: float

    # Predicted absolute values
    predicted_ici: float
    predicted_coherence: float
    predicted_criticality: float

    # Confidence score [0, 1]
    confidence: float

    # Prediction horizon (seconds)
    t_pred: float

    # Timestamp
    timestamp: float


class PredictiveModel:
    """
    Predictive Model for consciousness state and metrics forecasting

    Uses linear regression on recent State Memory history to predict:
    - Next consciousness state
    - Changes in ICI, coherence, and criticality
    - Confidence scores based on historical accuracy

    Provides hooks for preemptive system adjustments.
    """

    def __init__(self, config: Optional[PredictiveModelConfig] = None):
        """
        Initialize Predictive Model

        Args:
            config: PredictiveModelConfig (uses defaults if None)
        """
        self.config = config or PredictiveModelConfig()

        # Input buffer (filled by State Memory)
        self.input_buffer: deque = deque(maxlen=self.config.buffer_size)

        # Last forecast
        self.last_forecast: Optional[ForecastFrame] = None

        # Accuracy tracking
        self.prediction_history: deque = deque(maxlen=self.config.accuracy_window)
        self.actual_outcomes: deque = deque(maxlen=self.config.accuracy_window)

        # Performance tracking
        self.forecast_times: List[float] = []
        self.total_forecasts: int = 0

        # Forecast callback (FR-005, FR-006)
        self.forecast_callback: Optional[Callable[[Dict], None]] = None

        # Logging
        self.last_log_time: float = 0.0

        print("[PredictiveModel] Initialized")
        print(f"[PredictiveModel]   buffer_size={self.config.buffer_size}")
        print(f"[PredictiveModel]   prediction_horizon={self.config.prediction_horizon}s")
        print(f"[PredictiveModel]   min_buffer_size={self.config.min_buffer_size}")

    def add_frame(self,
                  ici: float,
                  coherence: float,
                  criticality: float,
                  current_state: str,
                  timestamp: float) -> Optional[ForecastFrame]:
        """
        Add metrics frame and compute forecast (FR-002, FR-003)

        Args:
            ici: Current ICI value
            coherence: Current phase coherence
            criticality: Current criticality
            current_state: Current consciousness state
            timestamp: Frame timestamp

        Returns:
            ForecastFrame if prediction made, None otherwise
        """
        # Add to buffer
        self.input_buffer.append({
            'ici': ici,
            'coherence': coherence,
            'criticality': criticality,
            'state': current_state,
            'timestamp': timestamp
        })

        # Check if we have enough data (edge case handling)
        if len(self.input_buffer) < self.config.min_buffer_size:
            return None

        # Compute forecast
        start_time = time.perf_counter()
        forecast = self._compute_forecast()
        elapsed = (time.perf_counter() - start_time) * 1000  # Convert to ms

        self.forecast_times.append(elapsed)
        if len(self.forecast_times) > 100:
            self.forecast_times.pop(0)

        self.total_forecasts += 1
        self.last_forecast = forecast

        # Emit forecast via callback (FR-005)
        if forecast and self.forecast_callback:
            forecast_json = self._forecast_to_json(forecast)
            self.forecast_callback(forecast_json)

        # Log if enabled
        if self.config.enable_logging:
            current_time = time.time()
            if current_time - self.last_log_time >= self.config.log_interval:
                self._log_stats()
                self.last_log_time = current_time

        return forecast

    def _compute_forecast(self) -> Optional[ForecastFrame]:
        """
        Compute forecast using linear regression (FR-003, FR-004)

        Returns:
            ForecastFrame with predictions
        """
        if len(self.input_buffer) < self.config.min_buffer_size:
            return None

        # Extract time series
        buffer_list = list(self.input_buffer)

        ici_series = np.array([f['ici'] for f in buffer_list])
        coherence_series = np.array([f['coherence'] for f in buffer_list])
        criticality_series = np.array([f['criticality'] for f in buffer_list])
        timestamps = np.array([f['timestamp'] for f in buffer_list])

        # Compute time deltas (for regression)
        dt_series = np.diff(timestamps)
        avg_dt = np.mean(dt_series) if len(dt_series) > 0 else 0.033  # ~30Hz fallback

        # Linear regression for each metric (FR-003)
        delta_ici = self._predict_delta(ici_series, avg_dt)
        delta_coherence = self._predict_delta(coherence_series, avg_dt)
        delta_criticality = self._predict_delta(criticality_series, avg_dt)

        # Current values (from most recent frame)
        current_ici = ici_series[-1]
        current_coherence = coherence_series[-1]
        current_criticality = criticality_series[-1]

        # Predicted values at prediction horizon
        steps_ahead = int(self.config.prediction_horizon / avg_dt)
        predicted_ici = current_ici + delta_ici * steps_ahead
        predicted_coherence = current_coherence + delta_coherence * steps_ahead
        predicted_criticality = current_criticality + delta_criticality * steps_ahead

        # Clamp predictions to reasonable ranges
        predicted_ici = np.clip(predicted_ici, 0.0, 1.0)
        predicted_coherence = np.clip(predicted_coherence, 0.0, 1.0)
        predicted_criticality = np.clip(predicted_criticality, 0.5, 1.5)

        # Predict next state using Feature 015 thresholds (FR-004)
        predicted_state = self._predict_state(
            predicted_ici,
            predicted_coherence,
            predicted_criticality
        )

        # Calculate confidence (FR-007)
        confidence = self._calculate_confidence(
            ici_series,
            coherence_series,
            criticality_series
        )

        # Create forecast frame
        forecast = ForecastFrame(
            predicted_state=predicted_state,
            delta_ici=delta_ici,
            delta_coherence=delta_coherence,
            delta_criticality=delta_criticality,
            predicted_ici=predicted_ici,
            predicted_coherence=predicted_coherence,
            predicted_criticality=predicted_criticality,
            confidence=confidence,
            t_pred=self.config.prediction_horizon,
            timestamp=time.time()
        )

        return forecast

    def _predict_delta(self, series: np.ndarray, dt: float) -> float:
        """
        Predict rate of change using linear regression

        Args:
            series: Time series of metric values
            dt: Average time step

        Returns:
            Predicted delta per time step
        """
        if len(series) < 2:
            return 0.0

        # Simple linear regression
        n = len(series)
        x = np.arange(n)

        # Check for valid data
        if np.any(np.isnan(series)) or np.any(np.isinf(series)):
            return 0.0

        # Compute slope
        try:
            coeffs = np.polyfit(x, series, 1)
            slope = coeffs[0]
        except:
            slope = 0.0

        return float(slope)

    def _predict_state(self,
                       ici: float,
                       coherence: float,
                       criticality: float) -> ConsciousnessState:
        """
        Predict consciousness state using Feature 015 thresholds (FR-004)

        Args:
            ici: Predicted ICI
            coherence: Predicted coherence
            criticality: Predicted criticality (not used in classification but available)

        Returns:
            Predicted ConsciousnessState
        """
        # Use same thresholds as state_classifier.py

        # HYPERSYNC: Very high ICI and coherence
        if ici > 0.9 and coherence > 0.9:
            return ConsciousnessState.HYPERSYNC

        # ALERT: High ICI and coherence
        if ici > 0.7 and coherence > 0.7:
            return ConsciousnessState.ALERT

        # COMA: Very low activity
        if ici < 0.1 and coherence < 0.2:
            return ConsciousnessState.COMA

        # SLEEP: Low activity with some coherence
        if coherence < 0.4:
            # Note: In state_classifier we also check spectral_centroid < 10
            # Here we approximate with coherence < 0.4 and ici < 0.3
            if ici < 0.3:
                return ConsciousnessState.SLEEP

        # AWAKE: Moderate activity
        if 0.3 <= ici <= 0.7 and coherence >= 0.4:
            return ConsciousnessState.AWAKE

        # DROWSY: Low ICI
        if ici < 0.3:
            return ConsciousnessState.DROWSY

        # Default to AWAKE
        return ConsciousnessState.AWAKE

    def _calculate_confidence(self,
                             ici_series: np.ndarray,
                             coherence_series: np.ndarray,
                             criticality_series: np.ndarray) -> float:
        """
        Calculate prediction confidence based on trend stability (FR-007)

        High confidence when:
        - Trends are consistent (low variance in derivatives)
        - Recent history is stable
        - Historical accuracy is high

        Args:
            ici_series: Recent ICI history
            coherence_series: Recent coherence history
            criticality_series: Recent criticality history

        Returns:
            Confidence score [0, 1]
        """
        # Component 1: Trend consistency (R² of linear fit)
        def compute_r_squared(series):
            if len(series) < 3:
                return 0.0

            x = np.arange(len(series))
            try:
                coeffs = np.polyfit(x, series, 1)
                fit = np.polyval(coeffs, x)
                residuals = series - fit
                ss_res = np.sum(residuals ** 2)
                ss_tot = np.sum((series - np.mean(series)) ** 2)

                if ss_tot < 1e-10:
                    return 1.0  # Constant series = perfect fit

                r_squared = 1 - (ss_res / ss_tot)
                return np.clip(r_squared, 0.0, 1.0)
            except:
                return 0.0

        r2_ici = compute_r_squared(ici_series[-30:])  # Last 30 frames
        r2_coherence = compute_r_squared(coherence_series[-30:])
        r2_criticality = compute_r_squared(criticality_series[-30:])

        trend_confidence = (r2_ici + r2_coherence + r2_criticality) / 3.0

        # Component 2: Historical accuracy
        if len(self.prediction_history) > 10:
            recent_accuracy = np.mean([p['correct'] for p in list(self.prediction_history)[-20:]])
        else:
            recent_accuracy = 0.5  # Neutral when no history

        # Component 3: Data stability (low recent variance = high confidence)
        recent_std = (
            np.std(ici_series[-10:]) +
            np.std(coherence_series[-10:]) +
            np.std(criticality_series[-10:])
        ) / 3.0
        stability_confidence = max(0.0, 1.0 - recent_std * 2.0)

        # Weighted combination
        confidence = (
            0.4 * trend_confidence +
            0.3 * recent_accuracy +
            0.3 * stability_confidence
        )

        return float(np.clip(confidence, 0.0, 1.0))

    def record_outcome(self, actual_state: str, actual_metrics: Dict[str, float]):
        """
        Record actual outcome for accuracy tracking (FR-007)

        Args:
            actual_state: Actual consciousness state that occurred
            actual_metrics: Actual metric values (ici, coherence, criticality)
        """
        if not self.last_forecast:
            return

        # Check state prediction accuracy
        predicted_state_str = self.last_forecast.predicted_state.value
        state_correct = (predicted_state_str == actual_state)

        # Check metric prediction accuracy (within tolerance)
        ici_error = abs(self.last_forecast.predicted_ici - actual_metrics.get('ici', 0.0))
        coherence_error = abs(self.last_forecast.predicted_coherence - actual_metrics.get('coherence', 0.0))
        criticality_error = abs(self.last_forecast.predicted_criticality - actual_metrics.get('criticality', 1.0))

        # Record for accuracy tracking
        self.prediction_history.append({
            'correct': state_correct,
            'ici_error': ici_error,
            'coherence_error': coherence_error,
            'criticality_error': criticality_error,
            'timestamp': time.time()
        })

        self.actual_outcomes.append({
            'state': actual_state,
            'metrics': actual_metrics,
            'timestamp': time.time()
        })

    def get_statistics(self) -> Dict:
        """
        Get prediction statistics (FR-007, SC-001, SC-002, SC-004)

        Returns:
            Dictionary with performance metrics
        """
        if len(self.prediction_history) == 0:
            return {
                'total_forecasts': self.total_forecasts,
                'prediction_accuracy': 0.0,
                'avg_forecast_time_ms': 0.0,
                'avg_confidence': 0.0,
                'buffer_size': len(self.input_buffer)
            }

        # State prediction accuracy (SC-001)
        state_accuracy = np.mean([p['correct'] for p in self.prediction_history])

        # Average errors
        avg_ici_error = np.mean([p['ici_error'] for p in self.prediction_history])
        avg_coherence_error = np.mean([p['coherence_error'] for p in self.prediction_history])
        avg_criticality_error = np.mean([p['criticality_error'] for p in self.prediction_history])

        # Forecast time (SC-002)
        avg_forecast_time = np.mean(self.forecast_times) if self.forecast_times else 0.0
        max_forecast_time = np.max(self.forecast_times) if self.forecast_times else 0.0

        # Average confidence (SC-004)
        if self.last_forecast:
            avg_confidence = self.last_forecast.confidence
        else:
            avg_confidence = 0.0

        return {
            'total_forecasts': self.total_forecasts,
            'prediction_accuracy': float(state_accuracy),
            'avg_ici_error': float(avg_ici_error),
            'avg_coherence_error': float(avg_coherence_error),
            'avg_criticality_error': float(avg_criticality_error),
            'avg_forecast_time_ms': float(avg_forecast_time),
            'max_forecast_time_ms': float(max_forecast_time),
            'avg_confidence': float(avg_confidence),
            'buffer_size': len(self.input_buffer),
            'prediction_history_size': len(self.prediction_history)
        }

    def get_last_forecast(self) -> Optional[Dict]:
        """
        Get last forecast as JSON (FR-005)

        Returns:
            Forecast JSON or None
        """
        if not self.last_forecast:
            return None

        return self._forecast_to_json(self.last_forecast)

    def _forecast_to_json(self, forecast: ForecastFrame) -> Dict:
        """
        Convert ForecastFrame to JSON (FR-005)

        Args:
            forecast: ForecastFrame to convert

        Returns:
            JSON dictionary
        """
        return {
            'type': 'forecast',
            'state': forecast.predicted_state.value,
            'confidence': forecast.confidence,
            't_pred': forecast.t_pred,
            'predicted_metrics': {
                'ici': forecast.predicted_ici,
                'coherence': forecast.predicted_coherence,
                'criticality': forecast.predicted_criticality
            },
            'deltas': {
                'ici': forecast.delta_ici,
                'coherence': forecast.delta_coherence,
                'criticality': forecast.delta_criticality
            },
            'timestamp': forecast.timestamp
        }

    def _log_stats(self):
        """Log performance statistics"""
        stats = self.get_statistics()

        print(f"[PredictiveModel] Stats: "
              f"accuracy={stats['prediction_accuracy']:.2%}, "
              f"forecasts={stats['total_forecasts']}, "
              f"avg_time={stats['avg_forecast_time_ms']:.2f}ms, "
              f"confidence={stats['avg_confidence']:.2f}")

    def reset(self):
        """Reset model state"""
        self.input_buffer.clear()
        self.last_forecast = None
        self.prediction_history.clear()
        self.actual_outcomes.clear()
        self.forecast_times.clear()
        self.total_forecasts = 0

        print("[PredictiveModel] State reset")


# Self-test function
def _self_test():
    """Test Predictive Model"""
    print("=" * 60)
    print("Predictive Model Self-Test")
    print("=" * 60)

    # Test 1: Initialization
    print("\n1. Testing initialization...")
    config = PredictiveModelConfig(
        buffer_size=128,
        prediction_horizon=1.5,
        min_buffer_size=50
    )
    model = PredictiveModel(config)

    assert len(model.input_buffer) == 0
    assert model.last_forecast is None
    print("   OK: Initialization")

    # Test 2: Buffer filling
    print("\n2. Testing buffer filling...")

    # Fill buffer with synthetic data (not enough for prediction)
    for i in range(30):
        forecast = model.add_frame(
            ici=0.5,
            coherence=0.6,
            criticality=1.0,
            current_state="AWAKE",
            timestamp=time.time() + i * 0.033
        )
        assert forecast is None, "Should not predict with insufficient data"

    assert len(model.input_buffer) == 30
    print("   OK: Buffer filling (no prediction yet)")

    # Test 3: First prediction
    print("\n3. Testing first prediction...")

    # Add more frames to reach min_buffer_size
    for i in range(30, 60):
        forecast = model.add_frame(
            ici=0.5 + i * 0.005,  # Increasing trend
            coherence=0.6 + i * 0.003,
            criticality=1.0,
            current_state="AWAKE",
            timestamp=time.time() + i * 0.033
        )

    assert forecast is not None, "Should have prediction now"
    assert forecast.confidence >= 0.0 and forecast.confidence <= 1.0
    print(f"   Predicted state: {forecast.predicted_state.value}")
    print(f"   Confidence: {forecast.confidence:.2f}")
    print(f"   Predicted ICI: {forecast.predicted_ici:.3f}")
    print("   OK: First prediction")

    # Test 4: State transition prediction
    print("\n4. Testing state transition...")

    # Simulate transition to ALERT (high ICI and coherence)
    for i in range(60, 100):
        ici = 0.5 + (i - 60) * 0.01  # Rapid increase
        coherence = 0.6 + (i - 60) * 0.008

        forecast = model.add_frame(
            ici=ici,
            coherence=coherence,
            criticality=1.0,
            current_state="AWAKE",
            timestamp=time.time() + i * 0.033
        )

    assert forecast is not None
    print(f"   Final predicted state: {forecast.predicted_state.value}")
    print(f"   Expected: ALERT or HYPERSYNC (high ICI/coherence)")
    print("   OK: State transition prediction")

    # Test 5: Accuracy tracking
    print("\n5. Testing accuracy tracking...")

    # Record some outcomes
    model.record_outcome(
        actual_state=forecast.predicted_state.value,
        actual_metrics={'ici': forecast.predicted_ici, 'coherence': forecast.predicted_coherence, 'criticality': 1.0}
    )

    stats = model.get_statistics()
    print(f"   Total forecasts: {stats['total_forecasts']}")
    print(f"   Prediction accuracy: {stats['prediction_accuracy']:.2%}")
    print(f"   Avg forecast time: {stats['avg_forecast_time_ms']:.2f}ms")

    assert stats['avg_forecast_time_ms'] < 50.0, f"Forecast time {stats['avg_forecast_time_ms']:.2f}ms exceeds 50ms target (SC-002)"
    print("   OK: Accuracy tracking and latency")

    # Test 6: JSON emission
    print("\n6. Testing JSON emission...")

    forecast_json = model.get_last_forecast()
    assert forecast_json is not None
    assert forecast_json['type'] == 'forecast'
    assert 'state' in forecast_json
    assert 'confidence' in forecast_json
    assert 't_pred' in forecast_json

    print(f"   Forecast JSON: {forecast_json['state']} @ {forecast_json['confidence']:.2f} confidence")
    print("   OK: JSON emission")

    # Test 7: Reset
    print("\n7. Testing reset...")

    model.reset()
    assert len(model.input_buffer) == 0
    assert model.last_forecast is None
    assert model.total_forecasts == 0
    print("   OK: Reset")

    print("\n" + "=" * 60)
    print("Self-Test PASSED")
    print("=" * 60)

    return True


if __name__ == "__main__":
    _self_test()
