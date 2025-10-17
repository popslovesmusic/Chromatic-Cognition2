"""
SyncProfiler - Feature 018: Phi-Adaptive Benchmark

Measures WebSocket round-trip latency and synchronization health by injecting
ping/pong timestamps into the WebSocket communication loop.

Features:
- FR-002: Collect latency metrics
- SC-001: Round-trip latency <= 100 ms (max)
- SC-003: Interaction delay <= 50 ms
- User Story 2: Latency & Sync Benchmark

Requirements:
- Log round-trip time across 10,000 frames
- Avg latency <= 50ms, max <= 100ms
"""

import time
import asyncio
from typing import Optional, Dict, List
from dataclasses import dataclass
from collections import deque
import numpy as np


@dataclass
class LatencyMeasurement:
    """Single latency measurement"""
    timestamp: float
    round_trip_ms: float
    one_way_ms: float
    jitter_ms: float


@dataclass
class ProfilerConfig:
    """Configuration for SyncProfiler"""
    max_samples: int = 10000
    ping_interval_ms: float = 100.0  # Send ping every 100ms
    latency_threshold_ms: float = 100.0
    jitter_threshold_ms: float = 20.0
    enable_logging: bool = False


class SyncProfiler:
    """
    SyncProfiler - WebSocket latency and sync measurement

    Injects ping/pong messages into WebSocket communication to measure
    round-trip latency and detect synchronization drift.

    Features:
    - Continuous latency monitoring
    - Jitter calculation
    - Clock drift detection
    - Statistical analysis
    """

    def __init__(self, config: Optional[ProfilerConfig] = None):
        """Initialize SyncProfiler"""
        self.config = config or ProfilerConfig()

        # Latency measurements
        self.measurements: deque = deque(maxlen=self.config.max_samples)

        # Ping/pong state
        self.pending_pings: Dict[int, float] = {}  # ping_id -> send_time
        self.next_ping_id = 0

        # Statistics
        self.total_pings_sent = 0
        self.total_pongs_received = 0
        self.total_timeouts = 0

        # Clock drift tracking
        self.clock_offset_ms = 0.0
        self.clock_drift_samples = deque(maxlen=100)

    def create_ping_message(self) -> Dict:
        """
        Create a ping message with timestamp

        Returns:
            Ping message dictionary
        """
        ping_id = self.next_ping_id
        self.next_ping_id += 1

        send_time = time.time()
        self.pending_pings[ping_id] = send_time
        self.total_pings_sent += 1

        return {
            "type": "ping",
            "ping_id": ping_id,
            "client_time": send_time * 1000.0  # Convert to ms
        }

    def handle_pong_message(self, pong_msg: Dict):
        """
        Handle pong message and calculate latency

        Args:
            pong_msg: Pong message from server
        """
        receive_time = time.time()
        ping_id = pong_msg.get("ping_id")
        server_time = pong_msg.get("server_time", 0) / 1000.0  # Convert from ms
        client_send_time = pong_msg.get("client_time", 0) / 1000.0

        if ping_id not in self.pending_pings:
            if self.config.enable_logging:
                print(f"[SyncProfiler] Received pong for unknown ping_id: {ping_id}")
            return

        # Get send time
        send_time = self.pending_pings.pop(ping_id)
        self.total_pongs_received += 1

        # Calculate round-trip time
        round_trip_s = receive_time - send_time
        round_trip_ms = round_trip_s * 1000.0

        # Estimate one-way latency (half of round-trip)
        one_way_ms = round_trip_ms / 2.0

        # Calculate jitter (change from previous measurement)
        jitter_ms = 0.0
        if len(self.measurements) > 0:
            prev_measurement = self.measurements[-1]
            jitter_ms = abs(round_trip_ms - prev_measurement.round_trip_ms)

        # Calculate clock offset
        if server_time > 0:
            # Estimate server time at client receive
            estimated_server_time = server_time + (one_way_ms / 1000.0)
            clock_offset = (receive_time - estimated_server_time) * 1000.0
            self.clock_drift_samples.append(clock_offset)
            self.clock_offset_ms = float(np.mean(list(self.clock_drift_samples)))

        # Create measurement
        measurement = LatencyMeasurement(
            timestamp=receive_time,
            round_trip_ms=round_trip_ms,
            one_way_ms=one_way_ms,
            jitter_ms=jitter_ms
        )

        self.measurements.append(measurement)

        if self.config.enable_logging:
            print(f"[SyncProfiler] RTT: {round_trip_ms:.2f}ms, "
                  f"One-way: {one_way_ms:.2f}ms, "
                  f"Jitter: {jitter_ms:.2f}ms")

    def cleanup_pending_pings(self, timeout_s: float = 1.0):
        """
        Remove pending pings that have timed out

        Args:
            timeout_s: Timeout in seconds
        """
        current_time = time.time()
        timed_out = []

        for ping_id, send_time in self.pending_pings.items():
            if (current_time - send_time) > timeout_s:
                timed_out.append(ping_id)

        for ping_id in timed_out:
            self.pending_pings.pop(ping_id)
            self.total_timeouts += 1

            if self.config.enable_logging:
                print(f"[SyncProfiler] Ping {ping_id} timed out")

    def get_statistics(self) -> Dict:
        """
        Get latency statistics

        Returns:
            Statistics dictionary
        """
        if not self.measurements:
            return {
                "total_samples": 0,
                "avg_latency_ms": 0.0,
                "min_latency_ms": 0.0,
                "max_latency_ms": 0.0,
                "p50_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "p99_latency_ms": 0.0,
                "avg_jitter_ms": 0.0,
                "max_jitter_ms": 0.0,
                "clock_offset_ms": 0.0,
                "total_pings_sent": self.total_pings_sent,
                "total_pongs_received": self.total_pongs_received,
                "total_timeouts": self.total_timeouts,
                "success_rate": 0.0,
                "meets_sc001": False,
                "meets_sc003": False
            }

        measurements = list(self.measurements)
        latencies = [m.round_trip_ms for m in measurements]
        jitters = [m.jitter_ms for m in measurements]

        avg_latency = float(np.mean(latencies))
        min_latency = float(np.min(latencies))
        max_latency = float(np.max(latencies))
        p50_latency = float(np.percentile(latencies, 50))
        p95_latency = float(np.percentile(latencies, 95))
        p99_latency = float(np.percentile(latencies, 99))

        avg_jitter = float(np.mean(jitters))
        max_jitter = float(np.max(jitters))

        success_rate = 0.0
        if self.total_pings_sent > 0:
            success_rate = (self.total_pongs_received / self.total_pings_sent) * 100.0

        # Check success criteria
        meets_sc001 = max_latency <= 100.0  # SC-001: Max RTT <= 100ms
        meets_sc003 = avg_latency / 2.0 <= 50.0  # SC-003: Avg one-way <= 50ms

        return {
            "total_samples": len(measurements),
            "avg_latency_ms": avg_latency,
            "min_latency_ms": min_latency,
            "max_latency_ms": max_latency,
            "p50_latency_ms": p50_latency,
            "p95_latency_ms": p95_latency,
            "p99_latency_ms": p99_latency,
            "avg_jitter_ms": avg_jitter,
            "max_jitter_ms": max_jitter,
            "clock_offset_ms": self.clock_offset_ms,
            "total_pings_sent": self.total_pings_sent,
            "total_pongs_received": self.total_pongs_received,
            "total_timeouts": self.total_timeouts,
            "success_rate": success_rate,
            "meets_sc001": meets_sc001,
            "meets_sc003": meets_sc003
        }

    def get_latency_distribution(self, bucket_size_ms: float = 10.0) -> Dict:
        """
        Get latency distribution histogram

        Args:
            bucket_size_ms: Size of each histogram bucket in ms

        Returns:
            Distribution dictionary
        """
        if not self.measurements:
            return {
                "buckets": [],
                "counts": [],
                "percentages": []
            }

        latencies = [m.round_trip_ms for m in self.measurements]
        max_latency = max(latencies)

        # Create buckets
        num_buckets = int(np.ceil(max_latency / bucket_size_ms))
        buckets = [i * bucket_size_ms for i in range(num_buckets + 1)]

        # Calculate histogram
        counts, _ = np.histogram(latencies, bins=buckets)
        percentages = (counts / len(latencies)) * 100.0

        return {
            "buckets": [f"{buckets[i]:.0f}-{buckets[i+1]:.0f}ms" for i in range(len(buckets)-1)],
            "counts": counts.tolist(),
            "percentages": percentages.tolist()
        }

    def reset(self):
        """Reset all measurements and statistics"""
        self.measurements.clear()
        self.pending_pings.clear()
        self.clock_drift_samples.clear()
        self.next_ping_id = 0
        self.total_pings_sent = 0
        self.total_pongs_received = 0
        self.total_timeouts = 0
        self.clock_offset_ms = 0.0


# Self-test
def _self_test():
    """Run basic self-test of SyncProfiler"""
    print("=" * 60)
    print("SyncProfiler Self-Test")
    print("=" * 60)
    print()

    all_ok = True

    # Test 1: Initialization
    print("1. Testing Initialization...")
    config = ProfilerConfig(enable_logging=True)
    profiler = SyncProfiler(config)

    init_ok = profiler.total_pings_sent == 0
    all_ok = all_ok and init_ok

    print(f"   Initial state: pings={profiler.total_pings_sent}, pongs={profiler.total_pongs_received}")
    print(f"   [{'OK' if init_ok else 'FAIL'}] Initialization")
    print()

    # Test 2: Create ping message
    print("2. Testing Ping Message Creation...")
    ping_msg = profiler.create_ping_message()

    ping_ok = (
        ping_msg['type'] == 'ping' and
        'ping_id' in ping_msg and
        'client_time' in ping_msg and
        profiler.total_pings_sent == 1
    )

    all_ok = all_ok and ping_ok

    print(f"   Ping message: {ping_msg}")
    print(f"   Total pings sent: {profiler.total_pings_sent}")
    print(f"   [{'OK' if ping_ok else 'FAIL'}] Ping creation")
    print()

    # Test 3: Handle pong message
    print("3. Testing Pong Message Handling...")

    # Simulate server response
    time.sleep(0.05)  # Simulate 50ms latency
    pong_msg = {
        "type": "pong",
        "ping_id": ping_msg['ping_id'],
        "server_time": time.time() * 1000.0,
        "client_time": ping_msg['client_time']
    }

    profiler.handle_pong_message(pong_msg)

    pong_ok = (
        profiler.total_pongs_received == 1 and
        len(profiler.measurements) == 1 and
        profiler.measurements[0].round_trip_ms >= 50.0
    )

    all_ok = all_ok and pong_ok

    if profiler.measurements:
        m = profiler.measurements[0]
        print(f"   RTT: {m.round_trip_ms:.2f}ms")
        print(f"   One-way: {m.one_way_ms:.2f}ms")
        print(f"   Jitter: {m.jitter_ms:.2f}ms")

    print(f"   [{'OK' if pong_ok else 'FAIL'}] Pong handling")
    print()

    # Test 4: Multiple measurements
    print("4. Testing Multiple Measurements...")

    for i in range(100):
        ping = profiler.create_ping_message()
        time.sleep(0.001)  # Simulate small delay

        pong = {
            "type": "pong",
            "ping_id": ping['ping_id'],
            "server_time": time.time() * 1000.0,
            "client_time": ping['client_time']
        }

        profiler.handle_pong_message(pong)

    multi_ok = (
        profiler.total_pings_sent == 101 and
        profiler.total_pongs_received == 101 and
        len(profiler.measurements) == 101
    )

    all_ok = all_ok and multi_ok

    print(f"   Total measurements: {len(profiler.measurements)}")
    print(f"   Success rate: {profiler.total_pongs_received / profiler.total_pings_sent * 100:.1f}%")
    print(f"   [{'OK' if multi_ok else 'FAIL'}] Multiple measurements")
    print()

    # Test 5: Statistics
    print("5. Testing Statistics...")
    stats = profiler.get_statistics()

    stats_ok = (
        stats['total_samples'] == 101 and
        stats['avg_latency_ms'] > 0 and
        stats['success_rate'] == 100.0
    )

    all_ok = all_ok and stats_ok

    print(f"   Avg latency: {stats['avg_latency_ms']:.2f}ms")
    print(f"   Min latency: {stats['min_latency_ms']:.2f}ms")
    print(f"   Max latency: {stats['max_latency_ms']:.2f}ms")
    print(f"   P95 latency: {stats['p95_latency_ms']:.2f}ms")
    print(f"   P99 latency: {stats['p99_latency_ms']:.2f}ms")
    print(f"   Avg jitter: {stats['avg_jitter_ms']:.2f}ms")
    print(f"   Success rate: {stats['success_rate']:.1f}%")
    print(f"   Meets SC-001: {stats['meets_sc001']}")
    print(f"   Meets SC-003: {stats['meets_sc003']}")
    print(f"   [{'OK' if stats_ok else 'FAIL'}] Statistics")
    print()

    # Test 6: Latency distribution
    print("6. Testing Latency Distribution...")
    dist = profiler.get_latency_distribution(bucket_size_ms=10.0)

    dist_ok = len(dist['buckets']) > 0

    all_ok = all_ok and dist_ok

    print(f"   Distribution buckets: {len(dist['buckets'])}")
    for i in range(min(5, len(dist['buckets']))):
        print(f"     {dist['buckets'][i]}: {dist['counts'][i]} ({dist['percentages'][i]:.1f}%)")

    print(f"   [{'OK' if dist_ok else 'FAIL'}] Distribution")
    print()

    # Test 7: Timeout handling
    print("7. Testing Timeout Handling...")

    # Create ping but don't respond
    timeout_ping = profiler.create_ping_message()
    time.sleep(1.1)  # Wait longer than timeout

    profiler.cleanup_pending_pings(timeout_s=1.0)

    timeout_ok = profiler.total_timeouts == 1

    all_ok = all_ok and timeout_ok

    print(f"   Total timeouts: {profiler.total_timeouts}")
    print(f"   [{'OK' if timeout_ok else 'FAIL'}] Timeout handling")
    print()

    print("=" * 60)
    if all_ok:
        print("Self-Test PASSED")
    else:
        print("Self-Test FAILED - Review failures above")
    print("=" * 60)

    return all_ok


if __name__ == "__main__":
    _self_test()
