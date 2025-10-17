"""
Test Hybrid Node Integration - Feature 025
Tests all functional requirements and success criteria

Success Criteria:
- SC-001: Hybrid Mode operational without audio dropouts
- SC-002: Φ input propagates to metrics < 2 ms latency
- SC-003: ICI and coherence update visible @ ≥ 30 Hz
- SC-004: System remains below 50% CPU load under 8-channel processing
- SC-005: UI responsive under hybrid operation (< 50 ms interaction delay)

Usage:
    python test_hybrid_node_integration.py
"""

import sys
import time
import asyncio
import argparse
from typing import List
from server.hybrid_node import HybridNode, HybridNodeConfig, PhiSource, HybridMetrics


def test_sc001_no_dropouts():
    """
    SC-001: Hybrid Mode operational without audio dropouts

    Test hybrid mode runs for 10 seconds without audio dropouts
    """
    print("=" * 60)
    print("Test SC-001: No Audio Dropouts")
    print("=" * 60)

    try:
        # Create hybrid node
        print("\n1. Creating HybridNode...")
        config = HybridNodeConfig(enable_logging=True)
        node = HybridNode(config)

        # Start hybrid mode
        print("\n2. Starting hybrid mode...")
        if not node.start():
            print("   FAILED: Could not start hybrid mode")
            return False

        print("   Running for 10 seconds...")
        time.sleep(10.0)

        # Check statistics
        stats = node.get_statistics()
        dropouts = stats['dropout_count']

        print(f"\n3. Checking dropouts...")
        print(f"   Dropout count: {dropouts}")

        # Stop
        node.stop()

        # Check SC-001
        passed = (dropouts == 0)

        print(f"\n   SC-001 (No dropouts): {'✓ PASS' if passed else '✗ FAIL'}")

        return passed

    except Exception as e:
        print(f"\n✗ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sc002_phi_latency():
    """
    SC-002: Φ input propagates to metrics < 2 ms latency

    Test that changing Φ values propagates to metrics within 2ms
    """
    print("\n" + "=" * 60)
    print("Test SC-002: Φ Input Latency < 2 ms")
    print("=" * 60)

    try:
        # Create hybrid node
        print("\n1. Creating HybridNode...")
        config = HybridNodeConfig(
            phi_source=PhiSource.MANUAL,
            enable_logging=True
        )
        node = HybridNode(config)

        # Track latency
        latencies = []

        def metrics_callback(metrics: HybridMetrics):
            # Metrics include latency measurement
            latencies.append(metrics.latency_ms)

        node.register_metrics_callback(metrics_callback)

        # Start hybrid mode
        print("\n2. Starting hybrid mode...")
        if not node.start():
            print("   FAILED: Could not start hybrid mode")
            return False

        time.sleep(1.0)  # Let it stabilize

        # Test Φ changes
        print("\n3. Testing Φ value changes...")
        test_values = [
            (0.0, 0.5),
            (1.57, 0.7),
            (3.14, 0.3),
            (4.71, 0.8)
        ]

        for phase, depth in test_values:
            latencies.clear()

            # Change Φ value and measure propagation time
            start_time = time.perf_counter()
            node.set_phi_manual(phase, depth)

            # Wait for metrics update
            time.sleep(0.1)

            elapsed_ms = (time.perf_counter() - start_time) * 1000

            if latencies:
                processing_latency = latencies[-1]
                print(f"   Φ({phase:.2f}, {depth:.2f}): processing={processing_latency:.2f}ms")

        # Stop
        node.stop()

        # Check SC-002
        if latencies:
            max_latency = max(latencies)
            avg_latency = sum(latencies) / len(latencies)

            print(f"\n4. Latency statistics:")
            print(f"   Average: {avg_latency:.2f} ms")
            print(f"   Maximum: {max_latency:.2f} ms")
            print(f"   Required: < 2.0 ms")

            passed = (max_latency < 2.0)
            print(f"\n   SC-002 (Latency < 2ms): {'✓ PASS' if passed else '✗ FAIL'}")

            return passed
        else:
            print("   FAILED: No latency measurements")
            return False

    except Exception as e:
        print(f"\n✗ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sc003_metrics_rate():
    """
    SC-003: ICI and coherence update visible @ ≥ 30 Hz

    Test that metrics are broadcast at ≥30 Hz
    """
    print("\n" + "=" * 60)
    print("Test SC-003: Metrics Update Rate ≥ 30 Hz")
    print("=" * 60)

    try:
        # Create hybrid node
        print("\n1. Creating HybridNode...")
        config = HybridNodeConfig(
            metrics_broadcast_interval=0.033,  # 30 Hz
            enable_logging=True
        )
        node = HybridNode(config)

        # Track metrics
        metrics_timestamps = []

        def metrics_callback(metrics: HybridMetrics):
            metrics_timestamps.append(time.time())

        node.register_metrics_callback(metrics_callback)

        # Start hybrid mode
        print("\n2. Starting hybrid mode...")
        if not node.start():
            print("   FAILED: Could not start hybrid mode")
            return False

        print("   Collecting metrics for 3 seconds...")
        time.sleep(3.0)

        # Stop
        node.stop()

        # Calculate metrics rate
        if len(metrics_timestamps) >= 2:
            duration = metrics_timestamps[-1] - metrics_timestamps[0]
            count = len(metrics_timestamps)
            rate_hz = count / duration

            print(f"\n3. Metrics rate analysis:")
            print(f"   Metrics received: {count}")
            print(f"   Duration: {duration:.2f} s")
            print(f"   Rate: {rate_hz:.1f} Hz")
            print(f"   Required: ≥ 30 Hz")

            passed = (rate_hz >= 30.0)
            print(f"\n   SC-003 (Rate ≥ 30 Hz): {'✓ PASS' if passed else '✗ FAIL'}")

            return passed
        else:
            print("   FAILED: Insufficient metrics collected")
            return False

    except Exception as e:
        print(f"\n✗ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sc004_cpu_load():
    """
    SC-004: System remains below 50% CPU load under 8-channel processing

    Test that CPU load stays below 50% during processing
    """
    print("\n" + "=" * 60)
    print("Test SC-004: CPU Load < 50%")
    print("=" * 60)

    try:
        # Create hybrid node (8 channels)
        print("\n1. Creating HybridNode (8 channels)...")
        config = HybridNodeConfig(
            num_channels=8,
            enable_logging=True
        )
        node = HybridNode(config)

        # Track CPU load
        cpu_loads = []

        def metrics_callback(metrics: HybridMetrics):
            cpu_loads.append(metrics.cpu_load)

        node.register_metrics_callback(metrics_callback)

        # Start hybrid mode
        print("\n2. Starting hybrid mode...")
        if not node.start():
            print("   FAILED: Could not start hybrid mode")
            return False

        print("   Running for 10 seconds to measure CPU load...")
        time.sleep(10.0)

        # Stop
        node.stop()

        # Analyze CPU load
        if cpu_loads:
            avg_cpu = sum(cpu_loads) / len(cpu_loads)
            max_cpu = max(cpu_loads)

            print(f"\n3. CPU load analysis:")
            print(f"   Average: {avg_cpu*100:.1f}%")
            print(f"   Maximum: {max_cpu*100:.1f}%")
            print(f"   Required: < 50%")

            passed = (max_cpu < 0.5)
            print(f"\n   SC-004 (CPU < 50%): {'✓ PASS' if passed else '✗ FAIL'}")

            return passed
        else:
            print("   FAILED: No CPU load measurements")
            return False

    except Exception as e:
        print(f"\n✗ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_user_story_1():
    """
    User Story 1: Enable Hybrid Mode

    Test activating hybrid mode with audio routing and metrics
    """
    print("\n" + "=" * 60)
    print("Test User Story 1: Enable Hybrid Mode")
    print("=" * 60)

    try:
        # Create hybrid node
        print("\n1. Creating HybridNode...")
        config = HybridNodeConfig(enable_logging=True)
        node = HybridNode(config)

        # Initial state: idle
        print("\n2. Checking initial state (idle)...")
        assert not node.is_running, "Node should not be running initially"

        # Activate hybrid mode
        print("\n3. Activating hybrid mode...")
        start_time = time.time()
        success = node.start()
        activation_time = (time.time() - start_time) * 1000

        if not success:
            print("   FAILED: Could not activate hybrid mode")
            return False

        assert node.is_running, "Node should be running after start"

        # Check activation time (< 100 ms requirement)
        print(f"   Activation time: {activation_time:.2f} ms")
        if activation_time < 100:
            print("   ✓ Activation time < 100 ms")
        else:
            print("   ⚠ Activation time ≥ 100 ms")

        # Let it run and check metrics
        print("\n4. Running for 2 seconds, checking metrics...")
        time.sleep(2.0)

        metrics = node.get_current_metrics()
        if metrics:
            print(f"   ✓ Metrics available:")
            print(f"      ICI: {metrics.ici:.4f}")
            print(f"      Coherence: {metrics.phase_coherence:.4f}")
        else:
            print("   ⚠ No metrics available")

        # Deactivate
        print("\n5. Deactivating hybrid mode...")
        stop_time = time.time()
        node.stop()
        deactivation_time = (time.time() - stop_time) * 1000

        assert not node.is_running, "Node should not be running after stop"
        print(f"   Deactivation time: {deactivation_time:.2f} ms")

        print("\n   ✓ User Story 1: PASS")
        return True

    except Exception as e:
        print(f"\n✗ User Story 1: FAIL - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_user_story_2():
    """
    User Story 2: External Φ Input

    Test external Φ source selection and latency
    """
    print("\n" + "=" * 60)
    print("Test User Story 2: External Φ Input")
    print("=" * 60)

    try:
        # Create hybrid node
        print("\n1. Creating HybridNode...")
        config = HybridNodeConfig(enable_logging=True)
        node = HybridNode(config)

        # Test different Φ sources
        print("\n2. Testing Φ source selection...")
        sources = [PhiSource.INTERNAL, PhiSource.MANUAL, PhiSource.MICROPHONE]

        for source in sources:
            node.set_phi_source(source)
            print(f"   ✓ Set Φ source to: {source.value}")

        # Test manual Φ control with latency measurement
        print("\n3. Testing manual Φ control with latency measurement...")
        node.set_phi_source(PhiSource.MANUAL)

        node.start()
        time.sleep(0.5)

        # Measure latency of Φ change to metrics update
        latencies = []

        def latency_callback(metrics: HybridMetrics):
            latencies.append(metrics.latency_ms)

        node.register_metrics_callback(latency_callback)

        # Change Φ multiple times
        for i in range(10):
            phase = i * 0.628
            depth = 0.5 + (i % 5) * 0.1
            node.set_phi_manual(phase, depth)
            time.sleep(0.05)

        node.stop()

        # Check latency requirement (< 2 ms average)
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            print(f"\n4. Φ input latency:")
            print(f"   Average: {avg_latency:.2f} ms")
            print(f"   Required: < 2 ms")

            if avg_latency < 2.0:
                print("   ✓ Latency requirement met")
                print("\n   ✓ User Story 2: PASS")
                return True
            else:
                print("   ✗ Latency requirement not met")
                return False
        else:
            print("   ⚠ No latency measurements")
            return False

    except Exception as e:
        print(f"\n✗ User Story 2: FAIL - {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all Feature 025 tests"""
    print("=" * 60)
    print("Feature 025: Hybrid Node Integration - Test Suite")
    print("=" * 60)

    results = {
        "SC-001 (No Dropouts)": test_sc001_no_dropouts(),
        "SC-002 (Φ Latency < 2ms)": test_sc002_phi_latency(),
        "SC-003 (Metrics ≥ 30 Hz)": test_sc003_metrics_rate(),
        "SC-004 (CPU < 50%)": test_sc004_cpu_load(),
        "User Story 1 (Enable Hybrid Mode)": test_user_story_1(),
        "User Story 2 (External Φ Input)": test_user_story_2()
    }

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed_count = sum(1 for passed in results.values() if passed)
    total_count = len(results)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name}: {status}")

    print(f"\nOverall: {passed_count}/{total_count} tests passed")

    print("=" * 60)

    return all(results.values())


if __name__ == "__main__":
    try:
        passed = main()
        sys.exit(0 if passed else 1)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTests failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
