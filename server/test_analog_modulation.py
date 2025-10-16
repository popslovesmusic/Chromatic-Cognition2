"""
Test Analog Modulation - Feature 024 (SC-002)
Verifies analog modulation fidelity and control response

Success Criteria:
- SC-002: Analog modulation fidelity >95%

Usage:
    python test_analog_modulation.py [--port COM3]
"""

import sys
import time
import math
import argparse
from hybrid_bridge import HybridBridge, ControlVoltage


def test_analog_modulation(port=None):
    """
    Test analog modulation fidelity and control voltage response

    SC-002: Analog modulation fidelity >95%

    Tests:
    1. Control voltage output accuracy
    2. Modulation response time
    3. Fidelity tracking over multiple cycles
    """
    print("=" * 60)
    print("Hybrid Node Analog Modulation Test (SC-002)")
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

    # Initialize and start node
    print("\n3. Initializing and starting node...")
    if not bridge.init():
        print("   FAILED: Could not initialize node")
        bridge.disconnect()
        return False

    if not bridge.start():
        print("   FAILED: Could not start node")
        bridge.disconnect()
        return False

    print("   OK: Node running")
    time.sleep(0.5)  # Allow node to settle

    # Test control voltage accuracy
    print("\n4. Testing control voltage output accuracy...")
    test_voltages = [
        (0.0, 0.0, 0.0, 0.0),      # Minimum
        (2.5, 2.5, math.pi, 0.5),  # Mid-range
        (5.0, 5.0, 2*math.pi, 1.0) # Maximum
    ]

    fidelity_samples = []

    for cv1_target, cv2_target, phi_phase, phi_depth in test_voltages:
        print(f"\n   Testing CV1={cv1_target:.1f}V, CV2={cv2_target:.1f}V, φ={phi_phase:.2f}, depth={phi_depth:.2f}")

        # Set control voltage
        cv = ControlVoltage(cv1=cv1_target, cv2=cv2_target, phi_phase=phi_phase, phi_depth=phi_depth)
        if not bridge.set_control_voltage(cv):
            print("      FAILED: Could not set control voltage")
            continue

        time.sleep(0.1)  # Settling time

        # Get statistics to check fidelity
        stats = bridge.get_statistics()
        if stats:
            fidelity = stats.get('modulation_fidelity', 0.0)
            fidelity_samples.append(fidelity)
            print(f"      Modulation fidelity: {fidelity:.2f}%")

            if fidelity >= 95.0:
                print(f"      ✓ Fidelity meets SC-002 (>{95}%)")
            else:
                print(f"      ✗ Fidelity below SC-002 (<{95}%)")

    # Test dynamic modulation (sweep)
    print("\n5. Testing dynamic modulation sweep...")
    print("   Sweeping control voltage from 0V to 5V over 2 seconds...")

    sweep_start = time.time()
    sweep_duration = 2.0
    samples = []

    while (time.time() - sweep_start) < sweep_duration:
        t = (time.time() - sweep_start) / sweep_duration  # 0.0 to 1.0

        # Generate swept control voltage
        cv1 = t * 5.0  # 0V → 5V
        cv2 = (1.0 - t) * 5.0  # 5V → 0V
        phi_phase = t * 2 * math.pi  # 0 → 2π
        phi_depth = 0.5 + 0.5 * math.sin(2 * math.pi * t * 5)  # Sine wave

        cv = ControlVoltage(cv1=cv1, cv2=cv2, phi_phase=phi_phase, phi_depth=phi_depth)
        bridge.set_control_voltage(cv)

        # Sample fidelity
        stats = bridge.get_statistics()
        if stats:
            fidelity = stats.get('modulation_fidelity', 0.0)
            samples.append(fidelity)

        time.sleep(0.05)  # 20 Hz update rate

    # Calculate sweep statistics
    if samples:
        avg_fidelity = sum(samples) / len(samples)
        min_fidelity = min(samples)
        print(f"\n   Sweep results:")
        print(f"   - Average fidelity: {avg_fidelity:.2f}%")
        print(f"   - Minimum fidelity: {min_fidelity:.2f}%")
        print(f"   - Samples: {len(samples)}")

        if min_fidelity >= 95.0:
            print(f"   ✓ All samples meet SC-002 (>{95}%)")
        else:
            print(f"   ✗ Some samples below SC-002")

        fidelity_samples.extend(samples)

    # Final fidelity check
    print("\n6. Checking SC-002 (analog modulation fidelity >95%)...")

    if fidelity_samples:
        overall_avg = sum(fidelity_samples) / len(fidelity_samples)
        overall_min = min(fidelity_samples)

        print(f"   - Average fidelity: {overall_avg:.2f}%")
        print(f"   - Minimum fidelity: {overall_min:.2f}%")
        print(f"   - Required: >95%")

        meets_sc002 = overall_min >= 95.0
    else:
        print("   FAILED: No fidelity samples collected")
        meets_sc002 = False

    # Stop and cleanup
    print("\n7. Stopping node and disconnecting...")
    bridge.stop()
    bridge.disconnect()

    # Final result
    print("\n" + "=" * 60)
    if meets_sc002:
        print("TEST PASSED: SC-002 modulation fidelity requirement met")
    else:
        print("TEST FAILED: SC-002 modulation fidelity requirement not met")
    print("=" * 60)

    return meets_sc002


def main():
    parser = argparse.ArgumentParser(description="Test hybrid node analog modulation (SC-002)")
    parser.add_argument("--port", help="Serial port for hybrid node (auto-detect if not specified)")
    args = parser.parse_args()

    try:
        passed = test_analog_modulation(args.port)
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
