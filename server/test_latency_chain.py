"""
Test Latency Chain - Feature 024 (SC-001)
Measures total ADC→DSP→DAC loop latency

Success Criteria:
- SC-001: Total latency ≤ 2000 µs (2 ms)

Usage:
    python test_latency_chain.py [--port COM3]
"""

import sys
import time
import argparse
from hybrid_bridge import HybridBridge


def test_latency_chain(port=None):
    """
    Test total loop latency from ADC input to DAC output

    SC-001: ADC→DSP→DAC full loop latency ≤2 ms
    """
    print("=" * 60)
    print("Hybrid Node Latency Chain Test (SC-001)")
    print("=" * 60)

    # Initialize bridge
    print("\n1. Initializing hybrid bridge...")
    bridge = HybridBridge(port=port)

    # Connect to device
    print("2. Connecting to hybrid node...")
    if not bridge.connect():
        print("   FAILED: Could not connect to hybrid node")
        return False

    version = bridge.get_version()
    print(f"   Connected: {bridge.port} @ {bridge.baudrate} baud")
    print(f"   Firmware: {version}")

    # Initialize node
    print("\n3. Initializing node...")
    if not bridge.init():
        print("   FAILED: Could not initialize node")
        bridge.disconnect()
        return False
    print("   OK: Node initialized")

    # Run calibration to measure latency
    print("\n4. Running calibration (loopback latency test)...")
    calibration = bridge.calibrate()

    if not calibration:
        print("   FAILED: Calibration failed")
        bridge.disconnect()
        return False

    print(f"\n   Calibration Results:")
    print(f"   - ADC latency:   {calibration['adc_latency_us']:>6} µs")
    print(f"   - DSP latency:   {calibration['dsp_latency_us']:>6} µs")
    print(f"   - DAC latency:   {calibration['dac_latency_us']:>6} µs")
    print(f"   - Total latency: {calibration['total_latency_us']:>6} µs")

    # Check SC-001
    total_latency_us = calibration['total_latency_us']
    latency_ms = total_latency_us / 1000.0

    print(f"\n5. Checking SC-001 (total latency ≤ 2000 µs)...")
    print(f"   - Measured: {total_latency_us} µs ({latency_ms:.2f} ms)")
    print(f"   - Required: ≤2000 µs (≤2.0 ms)")

    if total_latency_us <= 2000:
        print("   ✓ PASS: SC-001 met (latency within specification)")
    else:
        print("   ✗ FAIL: SC-001 violated (latency exceeds 2 ms)")

    # Measure multiple times for consistency
    print("\n6. Running additional latency samples...")
    latencies = [total_latency_us]

    for i in range(9):  # 10 total samples
        time.sleep(0.1)
        cal = bridge.calibrate()
        if cal:
            latencies.append(cal['total_latency_us'])
            print(f"   Sample {i+2}/10: {cal['total_latency_us']} µs")

    # Calculate statistics
    if len(latencies) >= 2:
        avg_latency = sum(latencies) / len(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)
        jitter = max_latency - min_latency

        print(f"\n   Latency Statistics:")
        print(f"   - Average: {avg_latency:.1f} µs ({avg_latency/1000:.2f} ms)")
        print(f"   - Minimum: {min_latency} µs")
        print(f"   - Maximum: {max_latency} µs")
        print(f"   - Jitter:  {jitter} µs")

        meets_sc001 = max_latency <= 2000
    else:
        meets_sc001 = total_latency_us <= 2000

    # Cleanup
    print("\n7. Disconnecting...")
    bridge.disconnect()

    # Final result
    print("\n" + "=" * 60)
    if meets_sc001:
        print("TEST PASSED: SC-001 latency requirement met")
    else:
        print("TEST FAILED: SC-001 latency requirement not met")
    print("=" * 60)

    return meets_sc001


def main():
    parser = argparse.ArgumentParser(description="Test hybrid node latency chain (SC-001)")
    parser.add_argument("--port", help="Serial port for hybrid node (auto-detect if not specified)")
    args = parser.parse_args()

    try:
        passed = test_latency_chain(args.port)
        sys.exit(0 if passed else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTest failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
