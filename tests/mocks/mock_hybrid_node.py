"""
Mock Hybrid Node Module
Feature 020: Reproducible Build Environment + Dependency Bootstrap (FR-007, FR-010)

Simulates Hybrid Node hardware for headless testing without physical sensors.
Automatically activates when SOUNDLAB_SIMULATE=1 environment variable is set.

Usage:
    import os
    if os.getenv('SOUNDLAB_SIMULATE') == '1':
        from tests.mocks.mock_hybrid_node import HybridNodeSimulator as HybridNode
    else:
        from server.hybrid_node import HybridNode
"""

import numpy as np
import time
import threading
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
import json


@dataclass
class MockSensorData:
    """Mock sensor readings"""
    timestamp: float
    analog_voltage: float  # 0.0 to 5.0V
    digital_state: int  # 0 or 1
    temperature: float  # Celsius
    phi_depth: float  # Φ depth reading
    phi_phase: float  # Φ phase reading


class HybridNodeSimulator:
    """
    Mock Hybrid Node for testing without hardware

    Simulates:
    - Analog voltage readings (ADC)
    - Digital I/O states
    - Temperature sensor
    - Φ-based modulation signals
    - I2C/SPI communication
    """

    def __init__(self, node_id: int = 0, simulate: bool = True):
        self.node_id = node_id
        self.simulate = simulate
        self.connected = False
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Sensor state
        self.analog_voltage = 2.5  # Mid-range
        self.digital_state = 0
        self.temperature = 25.0  # Room temperature
        self.phi_depth = 1.618  # Golden ratio
        self.phi_phase = 0.0

        # Callback
        self.data_callback: Optional[Callable] = None

        # Metrics
        self.samples_generated = 0
        self.last_update_time = time.time()

    def connect(self) -> bool:
        """Establish connection to mock hardware"""
        print(f"[Mock] Connecting to Hybrid Node {self.node_id}...")
        time.sleep(0.1)  # Simulate connection delay
        self.connected = True
        print(f"[Mock] Connected to Hybrid Node {self.node_id}")
        return True

    def disconnect(self):
        """Disconnect from mock hardware"""
        self.stop_stream()
        self.connected = False
        print(f"[Mock] Disconnected from Hybrid Node {self.node_id}")

    def start_stream(self, callback: Optional[Callable] = None, sample_rate: int = 100):
        """Start streaming mock sensor data"""
        if not self.connected:
            raise RuntimeError("Node not connected")

        if self._running:
            return

        self.data_callback = callback
        self._running = True
        self._thread = threading.Thread(
            target=self._generate_data_stream,
            args=(sample_rate,),
            daemon=True
        )
        self._thread.start()
        print(f"[Mock] Started data stream at {sample_rate} Hz")

    def stop_stream(self):
        """Stop streaming mock sensor data"""
        if not self._running:
            return

        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        print(f"[Mock] Stopped data stream")

    def _generate_data_stream(self, sample_rate: int):
        """Generate mock sensor data at specified rate"""
        interval = 1.0 / sample_rate

        while self._running:
            start_time = time.time()

            # Generate realistic sensor data
            t = time.time() - self.last_update_time

            # Analog voltage: sine wave + noise
            self.analog_voltage = 2.5 + 1.0 * np.sin(2 * np.pi * 0.5 * t) + \
                                 0.1 * np.random.randn()
            self.analog_voltage = np.clip(self.analog_voltage, 0.0, 5.0)

            # Digital state: toggle occasionally
            if np.random.rand() < 0.01:  # 1% chance per sample
                self.digital_state = 1 - self.digital_state

            # Temperature: slight drift
            self.temperature += 0.01 * np.random.randn()
            self.temperature = np.clip(self.temperature, 20.0, 30.0)

            # Φ depth: breathing pattern
            self.phi_depth = 1.618 + 0.2 * np.sin(2 * np.pi * 0.1 * t)

            # Φ phase: rotating
            self.phi_phase = (self.phi_phase + 0.01) % (2 * np.pi)

            # Create sensor data
            data = MockSensorData(
                timestamp=time.time(),
                analog_voltage=self.analog_voltage,
                digital_state=self.digital_state,
                temperature=self.temperature,
                phi_depth=self.phi_depth,
                phi_phase=self.phi_phase
            )

            # Call callback if registered
            if self.data_callback:
                try:
                    self.data_callback(data)
                except Exception as e:
                    print(f"[Mock] Callback error: {e}")

            self.samples_generated += 1

            # Sleep to maintain sample rate
            elapsed = time.time() - start_time
            sleep_time = max(0, interval - elapsed)
            time.sleep(sleep_time)

    def read_analog(self, channel: int = 0) -> float:
        """Read analog voltage from specified channel"""
        if not self.connected:
            raise RuntimeError("Node not connected")
        return self.analog_voltage

    def read_digital(self, pin: int = 0) -> int:
        """Read digital state from specified pin"""
        if not self.connected:
            raise RuntimeError("Node not connected")
        return self.digital_state

    def write_digital(self, pin: int, value: int):
        """Write digital state to specified pin"""
        if not self.connected:
            raise RuntimeError("Node not connected")
        self.digital_state = value
        print(f"[Mock] Set digital pin {pin} to {value}")

    def read_temperature(self) -> float:
        """Read temperature sensor"""
        if not self.connected:
            raise RuntimeError("Node not connected")
        return self.temperature

    def read_phi_depth(self) -> float:
        """Read Φ depth"""
        if not self.connected:
            raise RuntimeError("Node not connected")
        return self.phi_depth

    def read_phi_phase(self) -> float:
        """Read Φ phase"""
        if not self.connected:
            raise RuntimeError("Node not connected")
        return self.phi_phase

    def get_metrics(self) -> Dict:
        """Get mock node metrics"""
        return {
            'node_id': self.node_id,
            'connected': self.connected,
            'running': self._running,
            'samples_generated': self.samples_generated,
            'analog_voltage': self.analog_voltage,
            'digital_state': self.digital_state,
            'temperature': self.temperature,
            'phi_depth': self.phi_depth,
            'phi_phase': self.phi_phase,
        }

    def reset(self):
        """Reset mock node to initial state"""
        self.analog_voltage = 2.5
        self.digital_state = 0
        self.temperature = 25.0
        self.phi_depth = 1.618
        self.phi_phase = 0.0
        self.samples_generated = 0
        self.last_update_time = time.time()
        print(f"[Mock] Reset node {self.node_id}")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def __repr__(self):
        return f"HybridNodeSimulator(id={self.node_id}, connected={self.connected})"


# Compatibility alias
MockHybridNode = HybridNodeSimulator


if __name__ == '__main__':
    print("Mock Hybrid Node Simulator")
    print("="*50)

    # Test mock node
    node = HybridNodeSimulator(node_id=0)
    node.connect()

    # Read sensors
    print(f"Analog voltage: {node.read_analog():.2f}V")
    print(f"Digital state: {node.digital_state}")
    print(f"Temperature: {node.read_temperature():.1f}°C")
    print(f"Φ depth: {node.read_phi_depth():.3f}")
    print(f"Φ phase: {node.read_phi_phase():.3f}")

    # Stream data
    def on_data(data: MockSensorData):
        print(f"  Voltage: {data.analog_voltage:.2f}V, "
              f"Φ: {data.phi_depth:.3f} @ {data.phi_phase:.3f}")

    print("\nStreaming for 2 seconds...")
    node.start_stream(callback=on_data, sample_rate=10)
    time.sleep(2)
    node.stop_stream()

    # Show metrics
    metrics = node.get_metrics()
    print(f"\nMetrics: {json.dumps(metrics, indent=2)}")

    node.disconnect()
