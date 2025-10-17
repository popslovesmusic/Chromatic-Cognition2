"""
Unit Tests for Φ Calculations
Feature 021: Automated Validation & Regression Testing

Pure unit tests for mathematical functions - no I/O, fast execution.
"""

import pytest
import numpy as np


@pytest.mark.unit
class TestPhiCalculations:
    """Test Φ (golden ratio) mathematical operations"""

    PHI = 1.618033988749895

    def test_golden_ratio_value(self):
        """Test that Φ is calculated correctly"""
        calculated_phi = (1 + np.sqrt(5)) / 2
        assert abs(calculated_phi - self.PHI) < 1e-10

    def test_phi_conjugate(self):
        """Test Φ conjugate (1/Φ = Φ - 1)"""
        phi_conjugate = 1 / self.PHI
        phi_minus_one = self.PHI - 1
        assert abs(phi_conjugate - phi_minus_one) < 1e-10

    def test_phi_squared(self):
        """Test Φ² = Φ + 1"""
        phi_squared = self.PHI ** 2
        phi_plus_one = self.PHI + 1
        assert abs(phi_squared - phi_plus_one) < 1e-10

    @pytest.mark.parametrize("n,expected", [
        (0, 0),
        (1, 1),
        (2, 1),
        (3, 2),
        (4, 3),
        (5, 5),
        (6, 8),
        (10, 55),
    ])
    def test_fibonacci_sequence(self, n, expected):
        """Test Fibonacci sequence generation"""
        def fibonacci(n):
            if n <= 1:
                return n
            a, b = 0, 1
            for _ in range(2, n + 1):
                a, b = b, a + b
            return b

        result = fibonacci(n)
        assert result == expected

    def test_phi_from_fibonacci_ratio(self):
        """Test that ratio of large Fibonacci numbers approximates Φ"""
        def fibonacci(n):
            if n <= 1:
                return n
            a, b = 0, 1
            for _ in range(2, n + 1):
                a, b = b, a + b
            return b

        # Large Fibonacci numbers
        fib_n = fibonacci(30)
        fib_n_minus_1 = fibonacci(29)
        ratio = fib_n / fib_n_minus_1

        assert abs(ratio - self.PHI) < 1e-6


@pytest.mark.unit
class TestPhiModulation:
    """Test Φ-based modulation functions"""

    def test_phi_depth_range(self):
        """Test Φ depth stays within valid range"""
        # Simulate depth calculation
        base_depth = 1.618
        modulation = np.sin(np.linspace(0, 2 * np.pi, 100))
        depths = base_depth + 0.2 * modulation

        assert np.all(depths >= 1.4)
        assert np.all(depths <= 1.9)

    def test_phi_phase_wraparound(self):
        """Test Φ phase wraps around correctly"""
        phase = 0.0
        increment = 0.1

        for _ in range(100):
            phase = (phase + increment) % (2 * np.pi)

        assert 0 <= phase < 2 * np.pi

    def test_breathing_pattern(self):
        """Test Φ breathing pattern generation"""
        t = np.linspace(0, 10, 1000)  # 10 seconds
        frequency = 0.1  # 0.1 Hz breathing
        breathing = np.sin(2 * np.pi * frequency * t)

        # Check amplitude
        assert np.max(breathing) <= 1.0
        assert np.min(breathing) >= -1.0

        # Check period
        peaks = np.where(np.diff(np.sign(np.diff(breathing))) == -2)[0]
        if len(peaks) >= 2:
            period = (t[peaks[1]] - t[peaks[0]])
            expected_period = 1.0 / frequency
            assert abs(period - expected_period) < 0.1


@pytest.mark.unit
def test_numpy_available():
    """Test that numpy is available and working"""
    arr = np.array([1, 2, 3, 4, 5])
    assert np.sum(arr) == 15
    assert np.mean(arr) == 3.0


@pytest.mark.unit
def test_scipy_available():
    """Test that scipy is available"""
    from scipy import signal
    # Simple signal processing test
    fs = 1000  # Sample rate
    t = np.linspace(0, 1, fs, endpoint=False)
    sig = np.sin(2 * np.pi * 10 * t)  # 10 Hz signal
    assert len(sig) == fs


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
