"""
State Memory Loop - Temporal Memory for Consciousness States
Feature 013: Short-term memory for learning, hysteresis, and prediction

Implements:
- FR-001: StateMemory module
- FR-002: Rolling buffer of N=256 metric frames
- FR-003: Trend computation for prediction
- FR-004: Adaptive bias for Auto-Phi Learner
- FR-005: WebSocket summary (mean, std, trend)
- FR-006: Enable/disable setting
- FR-007: Buffer resets each session (no persistence)

Success Criteria:
- SC-001: Hysteresis visible (smooth transitions)
- SC-002: Predictive bias reduces overshoot by >=30%
- SC-003: No increase in latency > 2ms
- SC-004: Disable flag restores baseline
"""

import time
import numpy as np
from typing import Optional, Callable, Dict, List, Tuple
from dataclasses import dataclass, field
from collections import deque


@dataclass
class StateMemoryConfig:
    """Configuration for State Memory Loop"""
    enabled: bool = False

    # Buffer size (FR-002)
    buffer_size: int = 256  # Store last 256 frames

    # Prediction parameters (FR-003)
    trend_window: int = 30  # Use last 30 samples for trend (1s @ 30Hz)
    prediction_horizon: float = 1.0  # Predict 1s ahead

    # Bias parameters (FR-004)
    bias_gain: float = 0.3  # Gain for predictive bias
    bias_threshold: float = 0.15  # Minimum trend magnitude to apply bias

    # Safety limits
    max_bias: float = 0.2  # Maximum bias magnitude

    # Hysteresis parameters (SC-001)
    smoothing_alpha: float = 0.1  # Exponential smoothing factor

    # Logging
    enable_logging: bool = True
    log_interval: float = 2.0  # Log stats every 2s


@dataclass
class MetricsFrame:
    """Single frame of metrics"""
    timestamp: float
    criticality: float
    coherence: float
    ici: float  # Integrated information
    phi_depth: float
    phi_phase: float


@dataclass
class TrendVector:
    """Computed trend information"""
    d_criticality_dt: float = 0.0
    d_coherence_dt: float = 0.0
    d_phi_depth_dt: float = 0.0

    # Predicted values (current + trend * horizon)
    predicted_criticality: float = 0.0
    predicted_coherence: float = 0.0

    # Confidence based on trend stability
    confidence: float = 0.0


class StateMemory:
    """
    Temporal memory for consciousness states

    Stores recent metric frames and computes trends for:
    - Hysteresis (smooth transitions)
    - Prediction (pre-adjustment)
    - Learning (pattern recognition)

    Features:
    - Rolling buffer of 256 frames
    - Trend computation using linear regression
    - Adaptive bias for feed-forward control
    - Enable/disable toggle
    """

    def __init__(self, config: Optional[StateMemoryConfig] = None):
        """
        Initialize State Memory

        Args:
            config: StateMemoryConfig (uses defaults if None)
        """
        self.config = config or StateMemoryConfig()

        # Rolling buffer (FR-002)
        self.buffer: deque[MetricsFrame] = deque(maxlen=self.config.buffer_size)

        # Current trend vector
        self.trend: TrendVector = TrendVector()

        # Smoothed values (for hysteresis, SC-001)
        self.smoothed_criticality: float = 1.0
        self.smoothed_coherence: float = 0.0
        self.smoothed_phi_depth: float = 0.5

        # Predictive bias (FR-004)
        self.current_bias: float = 0.0

        # Statistics
        self.total_frames: int = 0
        self.prediction_errors: List[float] = []
        self.bias_history: List[float] = []

        # Logging
        self.last_log_time: float = 0.0

        # Callback for bias updates (feeds Auto-Phi Learner)
        self.bias_callback: Optional[Callable[[float], None]] = None

        print("[StateMemory] Initialized")
        print(f"[StateMemory]   buffer_size={self.config.buffer_size}")
        print(f"[StateMemory]   trend_window={self.config.trend_window}")
        print(f"[StateMemory]   enabled={self.config.enabled}")

    def set_enabled(self, enabled: bool):
        """
        Enable or disable state memory (FR-006, SC-004)

        Args:
            enabled: True to enable, False to disable
        """
        if self.config.enabled == enabled:
            return

        self.config.enabled = enabled

        if enabled:
            print("[StateMemory] ENABLED - temporal memory active")
        else:
            print("[StateMemory] DISABLED - baseline behavior restored")
            # Reset bias when disabled (SC-004)
            self.current_bias = 0.0
            if self.bias_callback:
                self.bias_callback(0.0)

    def add_frame(self, criticality: float, coherence: float, ici: float,
                  phi_depth: float, phi_phase: float) -> bool:
        """
        Add metrics frame to buffer (FR-002)

        Args:
            criticality: Current criticality value
            coherence: Current phase coherence
            ici: Integrated information
            phi_depth: Current phi depth
            phi_phase: Current phi phase

        Returns:
            True if processing occurred
        """
        if not self.config.enabled:
            return False

        current_time = time.time()

        # Create frame
        frame = MetricsFrame(
            timestamp=current_time,
            criticality=criticality,
            coherence=coherence,
            ici=ici,
            phi_depth=phi_depth,
            phi_phase=phi_phase
        )

        # Add to buffer
        self.buffer.append(frame)
        self.total_frames += 1

        # Apply exponential smoothing (SC-001: hysteresis)
        alpha = self.config.smoothing_alpha
        self.smoothed_criticality = alpha * criticality + (1 - alpha) * self.smoothed_criticality
        self.smoothed_coherence = alpha * coherence + (1 - alpha) * self.smoothed_coherence
        self.smoothed_phi_depth = alpha * phi_depth + (1 - alpha) * self.smoothed_phi_depth

        # Compute trends if we have enough history (FR-003)
        if len(self.buffer) >= self.config.trend_window:
            self._compute_trends()

            # Calculate predictive bias (FR-004)
            self._compute_bias()

            # Send bias update
            if self.bias_callback:
                self.bias_callback(self.current_bias)

        # Log if needed
        if self.config.enable_logging and (current_time - self.last_log_time) >= self.config.log_interval:
            self._log_stats()
            self.last_log_time = current_time

        return True

    def _compute_trends(self):
        """
        Compute trend vectors using linear regression (FR-003)

        Uses last trend_window samples to compute:
        - d(criticality)/dt
        - d(coherence)/dt
        - d(phi_depth)/dt
        """
        if len(self.buffer) < self.config.trend_window:
            return

        # Get recent frames
        recent = list(self.buffer)[-self.config.trend_window:]

        # Extract data
        timestamps = np.array([f.timestamp for f in recent])
        criticalities = np.array([f.criticality for f in recent])
        coherences = np.array([f.coherence for f in recent])
        phi_depths = np.array([f.phi_depth for f in recent])

        # Normalize time to start at 0
        t = timestamps - timestamps[0]

        # Linear regression for each signal
        # y = a + b*t, where b is the slope (derivative)

        # Criticality trend
        if len(t) > 1 and np.std(t) > 0:
            crit_slope, _ = np.polyfit(t, criticalities, 1)
            coh_slope, _ = np.polyfit(t, coherences, 1)
            depth_slope, _ = np.polyfit(t, phi_depths, 1)

            self.trend.d_criticality_dt = float(crit_slope)
            self.trend.d_coherence_dt = float(coh_slope)
            self.trend.d_phi_depth_dt = float(depth_slope)

            # Predict future values (FR-003)
            horizon = self.config.prediction_horizon
            current_crit = criticalities[-1]
            current_coh = coherences[-1]

            self.trend.predicted_criticality = current_crit + crit_slope * horizon
            self.trend.predicted_coherence = current_coh + coh_slope * horizon

            # Compute confidence based on R² (goodness of fit)
            # Higher R² = more confident in trend
            crit_r2 = self._compute_r_squared(t, criticalities, crit_slope)
            self.trend.confidence = float(crit_r2)

    def _compute_r_squared(self, x: np.ndarray, y: np.ndarray, slope: float) -> float:
        """
        Compute R² coefficient of determination

        Args:
            x: Independent variable
            y: Dependent variable
            slope: Linear slope

        Returns:
            R² value (0 to 1)
        """
        if len(x) < 2:
            return 0.0

        # Predicted values
        intercept = np.mean(y) - slope * np.mean(x)
        y_pred = slope * x + intercept

        # Total and residual sum of squares
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        ss_res = np.sum((y - y_pred) ** 2)

        if ss_tot == 0:
            return 0.0

        r_squared = 1.0 - (ss_res / ss_tot)
        return max(0.0, min(1.0, r_squared))  # Clamp to [0, 1]

    def _compute_bias(self):
        """
        Compute predictive bias for Auto-Phi Learner (FR-004, SC-002)

        Bias logic:
        - If criticality trending toward hypersync (>1.1), apply negative bias
        - If criticality trending toward coma (<0.4), apply positive bias
        - Magnitude proportional to trend slope and confidence
        """
        # Check if trend is significant
        if abs(self.trend.d_criticality_dt) < self.config.bias_threshold:
            self.current_bias = 0.0
            return

        # Get predicted criticality
        predicted = self.trend.predicted_criticality

        # Calculate bias based on predicted state
        bias = 0.0

        # Approaching hypersync (>1.1)
        if predicted > 1.1:
            # Negative bias to reduce phi_depth
            overshoot = predicted - 1.1
            bias = -self.config.bias_gain * overshoot

        # Approaching coma (<0.4)
        elif predicted < 0.4:
            # Positive bias to increase phi_depth
            undershoot = 0.4 - predicted
            bias = self.config.bias_gain * undershoot

        # Scale by confidence
        bias *= self.trend.confidence

        # Clamp to max bias
        bias = np.clip(bias, -self.config.max_bias, self.config.max_bias)

        self.current_bias = float(bias)
        self.bias_history.append(self.current_bias)

    def get_bias(self) -> float:
        """
        Get current predictive bias (FR-004)

        Returns:
            Current bias value
        """
        return self.current_bias

    def get_smoothed_values(self) -> Dict[str, float]:
        """
        Get smoothed values for hysteresis (SC-001)

        Returns:
            Dictionary with smoothed values
        """
        return {
            'criticality': self.smoothed_criticality,
            'coherence': self.smoothed_coherence,
            'phi_depth': self.smoothed_phi_depth
        }

    def get_trend_summary(self) -> Dict:
        """
        Get trend summary (FR-005)

        Returns:
            Dictionary with trend information
        """
        return {
            'd_criticality_dt': self.trend.d_criticality_dt,
            'd_coherence_dt': self.trend.d_coherence_dt,
            'd_phi_depth_dt': self.trend.d_phi_depth_dt,
            'predicted_criticality': self.trend.predicted_criticality,
            'predicted_coherence': self.trend.predicted_coherence,
            'confidence': self.trend.confidence,
            'current_bias': self.current_bias
        }

    def get_statistics(self) -> Dict:
        """
        Get memory statistics (FR-005)

        Returns:
            Dictionary with statistics
        """
        if len(self.buffer) == 0:
            return {
                'enabled': self.config.enabled,
                'buffer_size': 0,
                'total_frames': self.total_frames,
                'criticality_mean': 0.0,
                'criticality_std': 0.0,
                'coherence_mean': 0.0,
                'coherence_std': 0.0,
                'trend_summary': self.get_trend_summary()
            }

        # Extract buffer data
        criticalities = [f.criticality for f in self.buffer]
        coherences = [f.coherence for f in self.buffer]

        return {
            'enabled': self.config.enabled,
            'buffer_size': len(self.buffer),
            'total_frames': self.total_frames,
            'criticality_mean': float(np.mean(criticalities)),
            'criticality_std': float(np.std(criticalities)),
            'coherence_mean': float(np.mean(coherences)),
            'coherence_std': float(np.std(coherences)),
            'smoothed_criticality': self.smoothed_criticality,
            'smoothed_coherence': self.smoothed_coherence,
            'trend_summary': self.get_trend_summary()
        }

    def reset_buffer(self):
        """
        Reset memory buffer (FR-007)

        Clears all stored frames
        """
        self.buffer.clear()
        self.total_frames = 0
        self.current_bias = 0.0
        self.trend = TrendVector()
        self.prediction_errors.clear()
        self.bias_history.clear()

        # Reset smoothed values to neutral
        self.smoothed_criticality = 1.0
        self.smoothed_coherence = 0.0
        self.smoothed_phi_depth = 0.5

        print("[StateMemory] Buffer reset")

    def _log_stats(self):
        """Log memory statistics"""
        if len(self.buffer) == 0:
            return

        stats = self.get_statistics()

        print(f"[StateMemory] Stats: "
              f"buffer={stats['buffer_size']}/{self.config.buffer_size}, "
              f"criticality={stats['criticality_mean']:.3f}+/-{stats['criticality_std']:.3f}, "
              f"trend={self.trend.d_criticality_dt:.4f}, "
              f"bias={self.current_bias:.3f}")

    def export_buffer(self) -> Dict:
        """
        Export buffer contents for analysis

        Returns:
            Dictionary with time-series data
        """
        if len(self.buffer) == 0:
            return {
                'timestamps': [],
                'criticality': [],
                'coherence': [],
                'ici': [],
                'phi_depth': [],
                'phi_phase': []
            }

        return {
            'timestamps': [f.timestamp for f in self.buffer],
            'criticality': [f.criticality for f in self.buffer],
            'coherence': [f.coherence for f in self.buffer],
            'ici': [f.ici for f in self.buffer],
            'phi_depth': [f.phi_depth for f in self.buffer],
            'phi_phase': [f.phi_phase for f in self.buffer],
            'bias_history': self.bias_history[-256:]  # Last 256 bias values
        }


# Self-test function
def _self_test():
    """Test StateMemory"""
    print("=" * 60)
    print("StateMemory Self-Test")
    print("=" * 60)

    # Test 1: Initialization
    print("\n1. Testing initialization...")
    config = StateMemoryConfig(enabled=True, buffer_size=256, trend_window=30)
    memory = StateMemory(config)

    assert memory.config.enabled == True
    assert memory.config.buffer_size == 256
    assert len(memory.buffer) == 0
    print("   OK: Initialization")

    # Test 2: Add frames
    print("\n2. Testing frame addition...")

    # Add some frames with increasing criticality
    for i in range(50):
        criticality = 0.9 + i * 0.01  # Increasing trend
        coherence = 0.8 + np.random.randn() * 0.02
        ici = 1.5
        phi_depth = 0.5
        phi_phase = 0.3

        memory.add_frame(criticality, coherence, ici, phi_depth, phi_phase)
        time.sleep(0.01)

    assert len(memory.buffer) == 50
    assert memory.total_frames == 50
    print(f"   OK: Added 50 frames, buffer size = {len(memory.buffer)}")

    # Test 3: Trend computation
    print("\n3. Testing trend computation...")
    stats = memory.get_statistics()
    trend_summary = stats['trend_summary']

    print(f"   d(criticality)/dt = {trend_summary['d_criticality_dt']:.4f}")
    print(f"   Predicted criticality = {trend_summary['predicted_criticality']:.3f}")
    print(f"   Confidence = {trend_summary['confidence']:.3f}")
    print(f"   Current bias = {trend_summary['current_bias']:.3f}")

    # Should detect upward trend
    assert trend_summary['d_criticality_dt'] > 0, "Should detect upward trend"
    print("   OK: Trend detection working")

    # Test 4: Bias computation
    print("\n4. Testing bias computation...")

    # Add frames that push toward hypersync
    for i in range(30):
        criticality = 1.0 + i * 0.02  # Rapidly increasing
        memory.add_frame(criticality, 0.8, 1.5, 0.5, 0.3)
        time.sleep(0.01)

    bias = memory.get_bias()
    print(f"   Current bias: {bias:.3f}")

    # Should have negative bias to counteract upward trend
    assert bias < 0, "Should provide negative bias for hypersync trend"
    print("   OK: Predictive bias working")

    # Test 5: Reset
    print("\n5. Testing reset...")
    memory.reset_buffer()
    assert len(memory.buffer) == 0
    assert memory.current_bias == 0.0
    print("   OK: Reset working")

    # Test 6: Disable
    print("\n6. Testing enable/disable...")
    memory.set_enabled(False)
    assert memory.config.enabled == False

    # Should not add frames when disabled
    result = memory.add_frame(1.0, 0.8, 1.5, 0.5, 0.3)
    assert result == False
    assert len(memory.buffer) == 0
    print("   OK: Enable/disable working")

    print("\n" + "=" * 60)
    print("Self-Test PASSED")
    print("=" * 60)

    return True


if __name__ == "__main__":
    _self_test()
