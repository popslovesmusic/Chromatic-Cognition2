"""
Mock D-ASE Engine Module
Feature 020: Reproducible Build Environment + Dependency Bootstrap (FR-007, FR-010)

Simulates dase_engine C++ extension for testing when the extension isn't built.
Provides Python-based fallback implementation of the D-ASE API.

Usage:
    try:
        import dase_engine
    except ImportError:
        from tests.mocks import mock_dase_engine as dase_engine
"""

import numpy as np
import time
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class EngineMetrics:
    """Mock engine metrics"""
    total_execution_time_ns: int = 0
    avx2_operation_time_ns: int = 0
    total_operations: int = 0
    avx2_operations: int = 0
    node_processes: int = 0
    harmonic_generations: int = 0
    current_ns_per_op: float = 0.0
    current_ops_per_second: float = 0.0
    speedup_factor: float = 1.0
    target_ns_per_op: float = 100.0

    def reset(self):
        """Reset metrics"""
        self.total_execution_time_ns = 0
        self.avx2_operation_time_ns = 0
        self.total_operations = 0
        self.avx2_operations = 0
        self.node_processes = 0
        self.harmonic_generations = 0

    def update_performance(self):
        """Update performance calculations"""
        if self.total_operations > 0:
            self.current_ns_per_op = self.total_execution_time_ns / self.total_operations
            self.current_ops_per_second = 1e9 / self.current_ns_per_op if self.current_ns_per_op > 0 else 0
            self.speedup_factor = self.target_ns_per_op / self.current_ns_per_op if self.current_ns_per_op > 0 else 1.0

    def print_metrics(self):
        """Print metrics to console"""
        print("=" * 70)
        print("D-ASE Engine Metrics (Mock)")
        print("=" * 70)
        print(f"Total Operations: {self.total_operations}")
        print(f"AVX2 Operations: {self.avx2_operations}")
        print(f"Node Processes: {self.node_processes}")
        print(f"Harmonic Generations: {self.harmonic_generations}")
        print(f"Total Execution Time: {self.total_execution_time_ns / 1e6:.2f} ms")
        print(f"Performance: {self.current_ops_per_second:.2f} ops/sec")
        print(f"ns/op: {self.current_ns_per_op:.2f}")
        print(f"Speedup Factor: {self.speedup_factor:.2f}x")
        print("=" * 70)


class AnalogUniversalNode:
    """Mock Analog Universal Node"""

    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        self.node_id = 0
        self._output = 0.0
        self._integrator_state = 0.0
        self._feedback_coefficient = 0.0

    def process_signal(self, input_signal: float, control_signal: float, aux_signal: float) -> float:
        """Process analog signal through the node"""
        # Simple processing: amplify + integrate + feedback
        amplified = input_signal * (1.0 + control_signal)
        integrated = self._integrator_state * 0.99 + amplified * 0.01
        self._integrator_state = integrated
        feedback = integrated * self._feedback_coefficient
        self._output = amplified + feedback + aux_signal * 0.1
        return self._output

    def process_signal_avx2(self, input_signal: float, control_signal: float, aux_signal: float) -> float:
        """Process analog signal with AVX2 optimization (mock)"""
        # Mock: same as non-AVX2 version
        return self.process_signal(input_signal, control_signal, aux_signal)

    def set_feedback(self, feedback_coefficient: float):
        """Set feedback coefficient"""
        self._feedback_coefficient = feedback_coefficient

    def get_output(self) -> float:
        """Get current output value"""
        return self._output

    def get_integrator_state(self) -> float:
        """Get current integrator state"""
        return self._integrator_state

    def reset_integrator(self):
        """Reset integrator state to zero"""
        self._integrator_state = 0.0

    def amplify(self, input_signal: float, gain: float) -> float:
        """Simple amplification"""
        return input_signal * gain

    def integrate(self, input_signal: float, time_constant: float) -> float:
        """Integration with time constant"""
        alpha = 1.0 / (1.0 + time_constant)
        self._integrator_state = self._integrator_state * (1.0 - alpha) + input_signal * alpha
        return self._integrator_state

    def apply_feedback(self, input_signal: float, feedback_gain: float) -> float:
        """Apply feedback to signal"""
        return input_signal + self._integrator_state * feedback_gain


class AnalogCellularEngine:
    """Mock Analog Cellular Engine"""

    def __init__(self, num_nodes: int):
        self.num_nodes = num_nodes
        self.nodes = [AnalogUniversalNode() for _ in range(num_nodes)]
        self.metrics = EngineMetrics()

    def process_signal_wave(self, input_signal: np.ndarray, control_pattern: np.ndarray) -> np.ndarray:
        """Process signal wave through cellular array"""
        start_time = time.perf_counter_ns()

        output = np.zeros_like(input_signal)
        for i in range(len(input_signal)):
            node_idx = i % self.num_nodes
            control = control_pattern[i] if i < len(control_pattern) else 0.0
            output[i] = self.nodes[node_idx].process_signal(input_signal[i], control, 0.0)

        end_time = time.perf_counter_ns()
        self.metrics.total_execution_time_ns += (end_time - start_time)
        self.metrics.total_operations += len(input_signal)
        self.metrics.node_processes += len(input_signal)

        return output

    def perform_signal_sweep(self, frequency: float) -> Dict:
        """Perform frequency sweep operation"""
        start_time = time.perf_counter_ns()

        # Generate sweep signal
        duration = 1.0  # 1 second
        sample_rate = 48000
        t = np.linspace(0, duration, int(sample_rate * duration))
        signal = np.sin(2 * np.pi * frequency * t)

        # Process through engine
        control = np.ones_like(signal) * 0.5
        output = self.process_signal_wave(signal, control)

        end_time = time.perf_counter_ns()
        elapsed_ms = (end_time - start_time) / 1e6

        return {
            'frequency': frequency,
            'duration_ms': elapsed_ms,
            'samples_processed': len(signal),
            'rms_output': float(np.sqrt(np.mean(output**2)))
        }

    def run_builtin_benchmark(self, iterations: int = 1000) -> Dict:
        """Run performance benchmark"""
        print(f"[Mock] Running benchmark with {iterations} iterations...")
        start_time = time.perf_counter_ns()

        for i in range(iterations):
            signal = np.random.randn(512).astype(np.float32)
            control = np.ones(512, dtype=np.float32) * 0.5
            self.process_signal_wave(signal, control)

        end_time = time.perf_counter_ns()
        total_time_ms = (end_time - start_time) / 1e6

        self.metrics.update_performance()

        return {
            'iterations': iterations,
            'total_time_ms': total_time_ms,
            'avg_time_per_iteration_us': (total_time_ms * 1000) / iterations,
            'ops_per_second': self.metrics.current_ops_per_second
        }

    def run_massive_benchmark(self, iterations: int = 10000) -> Dict:
        """Run massive performance benchmark"""
        return self.run_builtin_benchmark(iterations)

    def run_drag_race_benchmark(self, num_runs: int = 5) -> Dict:
        """Run drag race benchmark"""
        results = []
        for run in range(num_runs):
            result = self.run_builtin_benchmark(iterations=1000)
            results.append(result)

        return {
            'num_runs': num_runs,
            'results': results,
            'avg_time_ms': np.mean([r['total_time_ms'] for r in results]),
        }

    def run_mission(self, num_steps: int):
        """Run mission loop"""
        for step in range(num_steps):
            signal = np.random.randn(512).astype(np.float32)
            control = np.ones(512, dtype=np.float32) * 0.5
            self.process_signal_wave(signal, control)

    def process_block_frequency_domain(self, signal_block: np.ndarray) -> np.ndarray:
        """Process signal block in frequency domain"""
        # FFT -> process -> IFFT
        fft = np.fft.fft(signal_block)
        # Apply some frequency domain processing
        fft *= 0.9  # Slight attenuation
        return np.fft.ifft(fft).real.astype(np.float32)

    def get_metrics(self) -> EngineMetrics:
        """Get current performance metrics"""
        self.metrics.update_performance()
        return self.metrics

    def print_live_metrics(self):
        """Print current performance metrics"""
        self.metrics.print_metrics()

    def reset_metrics(self):
        """Reset performance counters"""
        self.metrics.reset()

    def generate_noise_signal(self) -> np.ndarray:
        """Generate random noise signal"""
        return np.random.randn(512).astype(np.float32)

    def calculate_inter_node_coupling(self, node_index: int) -> float:
        """Calculate coupling between nodes"""
        if node_index >= self.num_nodes:
            return 0.0
        # Simple coupling calculation
        if node_index > 0:
            prev_state = self.nodes[node_index - 1].get_integrator_state()
            curr_state = self.nodes[node_index].get_integrator_state()
            return abs(curr_state - prev_state)
        return 0.0


class CPUFeatures:
    """Mock CPU features detection"""

    @staticmethod
    def has_avx2() -> bool:
        """Check if CPU supports AVX2 instructions (mock always true)"""
        return True

    @staticmethod
    def has_fma() -> bool:
        """Check if CPU supports FMA instructions (mock always true)"""
        return True

    @staticmethod
    def print_capabilities():
        """Print detected CPU capabilities"""
        print("=" * 70)
        print("CPU Capabilities (Mock)")
        print("=" * 70)
        print("AVX2 Support: TRUE (simulated)")
        print("FMA Support: TRUE (simulated)")
        print("OpenMP: FALSE (Python fallback)")
        print("=" * 70)


# Module attributes
__version__ = "1.0.0-mock"
avx2_enabled = False  # Mock doesn't use AVX2
openmp_enabled = False


if __name__ == '__main__':
    print("Mock D-ASE Engine Module")
    print(f"Version: {__version__}")
    print()

    # Test CPU features
    CPUFeatures.print_capabilities()
    print()

    # Test single node
    print("Testing AnalogUniversalNode...")
    node = AnalogUniversalNode()
    node.set_feedback(0.5)
    output = node.process_signal_avx2(1.0, 0.5, 0.1)
    print(f"Output: {output:.4f}")
    print()

    # Test engine
    print("Testing AnalogCellularEngine...")
    engine = AnalogCellularEngine(num_nodes=8)
    result = engine.run_builtin_benchmark(iterations=100)
    print(f"Benchmark: {result['total_time_ms']:.2f} ms")
    engine.print_live_metrics()
