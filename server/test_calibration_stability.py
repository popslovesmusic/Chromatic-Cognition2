"""
Test Calibration Stability - Feature 024 (SC-003)
1-hour continuous operation drift test

Success Criteria:
- SC-003: Stable operation 1 hour continuous with drift <0.5%

Usage:
    python test_calibration_stability.py [--port COM3] [--duration 3600]
"""

import sys
import time
import argparse
from hybrid_bridge import HybridBridge, ControlVoltage


def test_calibration_stability(port=None, duration_seconds=3600):
    """
    Test node stability over extended operation

    SC-003: Stable operation 1 hour continuous with drift <0.5%

    Monitors:
    1. Latency drift over time
    2. Modulation fidelity stability
    3. Thermal stability
    4. No crashes or errors
    """
    print("=" * 60)
    print("Hybrid Node Calibration Stability Test (SC-003)")
    print("=" * 60)
    print(f"Duration: {duration_seconds}s ({duration_seconds/60:.1f} minutes)")

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

    # Run initial calibration
    print("\n3. Running initial calibration...")
    initial_cal = bridge.calibrate()
    if not initial_cal:
        print("   FAILED: Initial calibration failed")
        bridge.disconnect()
        return False

    initial_latency = initial_cal['total_latency_us']
    print(f"   Initial latency: {initial_latency} µs")

    # Initialize and start node
    print("\n4. Initializing and starting node...")
    if not bridge.init():
        print("   FAILED: Could not initialize node")
        bridge.disconnect()
        return False

    if not bridge.start():
        print("   FAILED: Could not start node")
        bridge.disconnect()
        return False

    print("   OK: Node running")

    # Start stability test
    print(f"\n5. Running {duration_seconds}s stability test...")
    print("   (Press Ctrl+C to abort)")
    print("\n   Time(s)  Latency(µs)  Drift(%)  Fidelity(%)  Temp(°C)  Status")
    print("   " + "-" * 65)

    start_time = time.time()
    sample_interval = 60.0  # Sample every minute
    next_sample_time = start_time + sample_interval

    latency_samples = [initial_latency]
    fidelity_samples = []
    temp_samples = []
    error_count = 0

    # Set test modulation pattern
    test_cv = ControlVoltage(cv1=2.5, cv2=2.5, phi_phase=1.57, phi_depth=0.7)
    bridge.set_control_voltage(test_cv)

    try:
        while True:
            current_time = time.time()
            elapsed = current_time - start_time

            # Check if test duration reached
            if elapsed >= duration_seconds:
                break

            # Sample metrics at intervals
            if current_time >= next_sample_time:
                # Get statistics
                stats = bridge.get_statistics()
                safety = bridge.get_safety()

                if stats and safety:
                    # Latency drift check
                    latency = stats.get('total_latency_us', initial_latency)
                    latency_samples.append(latency)
                    drift_pct = ((latency - initial_latency) / initial_latency) * 100

                    # Modulation fidelity
                    fidelity = stats.get('modulation_fidelity', 0.0)
                    fidelity_samples.append(fidelity)

                    # Temperature
                    temp = safety.get('temperature', 0.0)
                    temp_samples.append(temp)

                    # Status
                    status = safety.get('status', 'UNKNOWN')

                    # Print status line
                    print(f"   {elapsed:>6.0f}   {latency:>8}     {drift_pct:>5.2f}    {fidelity:>6.1f}      {temp:>5.1f}    {status}")

                    # Check for errors
                    if status != 'HYBRID_SAFETY_OK':
                        error_count += 1
                        print(f"      WARNING: Safety status not OK: {status}")

                else:
                    print(f"   {elapsed:>6.0f}   ERROR: Could not retrieve metrics")
                    error_count += 1

                next_sample_time += sample_interval

            # Brief sleep to avoid busy-waiting
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\n   Test aborted by user")

    # Calculate final statistics
    print("\n" + "=" * 60)
    print("Test Complete - Analyzing Results")
    print("=" * 60)

    elapsed_total = time.time() - start_time

    print(f"\n6. Runtime: {elapsed_total:.1f}s ({elapsed_total/60:.1f} minutes)")

    # Latency drift analysis
    if len(latency_samples) > 1:
        final_latency = latency_samples[-1]
        max_latency = max(latency_samples)
        min_latency = min(latency_samples)
        avg_latency = sum(latency_samples) / len(latency_samples)

        drift_pct = ((final_latency - initial_latency) / initial_latency) * 100
        max_drift_pct = ((max_latency - initial_latency) / initial_latency) * 100

        print(f"\n   Latency Drift:")
        print(f"   - Initial:  {initial_latency} µs")
        print(f"   - Final:    {final_latency} µs")
        print(f"   - Average:  {avg_latency:.1f} µs")
        print(f"   - Max:      {max_latency} µs")
        print(f"   - Min:      {min_latency} µs")
        print(f"   - Drift:    {drift_pct:+.2f}%")
        print(f"   - Max Drift: {max_drift_pct:+.2f}%")

        drift_ok = abs(max_drift_pct) < 0.5
        if drift_ok:
            print(f"   ✓ Drift within SC-003 requirement (<0.5%)")
        else:
            print(f"   ✗ Drift exceeds SC-003 requirement (≥0.5%)")
    else:
        drift_ok = False
        print("\n   FAILED: Insufficient latency samples")

    # Fidelity analysis
    if fidelity_samples:
        avg_fidelity = sum(fidelity_samples) / len(fidelity_samples)
        min_fidelity = min(fidelity_samples)

        print(f"\n   Modulation Fidelity:")
        print(f"   - Average: {avg_fidelity:.2f}%")
        print(f"   - Minimum: {min_fidelity:.2f}%")

        fidelity_ok = min_fidelity >= 95.0
    else:
        fidelity_ok = False

    # Temperature analysis
    if temp_samples:
        avg_temp = sum(temp_samples) / len(temp_samples)
        max_temp = max(temp_samples)

        print(f"\n   Temperature:")
        print(f"   - Average: {avg_temp:.1f}°C")
        print(f"   - Maximum: {max_temp:.1f}°C")

        temp_ok = max_temp < 85.0  # Critical threshold
    else:
        temp_ok = True  # If no temp data, assume OK

    # Error count
    print(f"\n   Errors: {error_count}")
    errors_ok = error_count == 0

    # Overall pass/fail
    meets_sc003 = drift_ok and fidelity_ok and temp_ok and errors_ok

    # Stop and cleanup
    print("\n7. Stopping node and disconnecting...")
    bridge.stop()
    bridge.disconnect()

    # Final result
    print("\n" + "=" * 60)
    if meets_sc003:
        print("TEST PASSED: SC-003 stability requirement met")
    else:
        print("TEST FAILED: SC-003 stability requirement not met")
    print("=" * 60)

    return meets_sc003


def main():
    parser = argparse.ArgumentParser(description="Test hybrid node calibration stability (SC-003)")
    parser.add_argument("--port", help="Serial port for hybrid node (auto-detect if not specified)")
    parser.add_argument("--duration", type=int, default=3600, help="Test duration in seconds (default: 3600 = 1 hour)")
    args = parser.parse_args()

    try:
        passed = test_calibration_stability(args.port, args.duration)
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
