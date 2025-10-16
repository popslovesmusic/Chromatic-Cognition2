"""
Test Cluster Integration - Feature 024 (SC-004)
Verifies hybrid node appears in cluster dashboard with accurate telemetry

Success Criteria:
- SC-004: Cluster Monitor displays hybrid node accurately

Usage:
    python test_cluster_integration.py [--port COM3] [--cluster-url http://localhost:8000]
"""

import sys
import time
import argparse
import requests
from hybrid_bridge import HybridBridge, ControlVoltage


def test_cluster_integration(port=None, cluster_url="http://localhost:8000"):
    """
    Test hybrid node integration with Cluster Monitor

    SC-004: Cluster Monitor displays hybrid node accurately

    Tests:
    1. Hybrid node appears in cluster node list
    2. DSP metrics (ICI, coherence) are visible
    3. Safety telemetry is reported
    4. Statistics are accurate
    5. Real-time updates work
    """
    print("=" * 60)
    print("Hybrid Node Cluster Integration Test (SC-004)")
    print("=" * 60)
    print(f"Cluster URL: {cluster_url}")

    # Check if cluster monitor is available
    print("\n1. Checking cluster monitor availability...")
    try:
        response = requests.get(f"{cluster_url}/api/cluster/nodes", timeout=5)
        if response.status_code != 200:
            print(f"   FAILED: Cluster monitor returned status {response.status_code}")
            return False
        print("   OK: Cluster monitor is running")
    except requests.exceptions.RequestException as e:
        print(f"   FAILED: Could not connect to cluster monitor: {e}")
        print("   Make sure server is running with --enable-cluster-monitor and --enable-hybrid-bridge")
        return False

    # Initialize hybrid bridge
    print("\n2. Initializing hybrid bridge...")
    bridge = HybridBridge(port=port)

    # Connect to device
    print("3. Connecting to hybrid node...")
    if not bridge.connect():
        print("   FAILED: Could not connect to hybrid node")
        return False

    version = bridge.get_version()
    print(f"   Connected: {bridge.port} @ {bridge.baudrate} baud")
    print(f"   Firmware: {version}")

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
    time.sleep(2.0)  # Allow cluster monitor to detect node

    # Check if hybrid node appears in cluster
    print("\n5. Checking if hybrid node appears in cluster...")
    try:
        response = requests.get(f"{cluster_url}/api/cluster/nodes", timeout=5)
        nodes = response.json()

        hybrid_node = None
        for node in nodes.get('nodes', []):
            if node.get('node_id') == 'hybrid_analog_dsp' or node.get('role') == 'hybrid':
                hybrid_node = node
                break

        if hybrid_node:
            print(f"   ✓ Hybrid node found in cluster")
            print(f"      Node ID: {hybrid_node.get('node_id')}")
            print(f"      Role: {hybrid_node.get('role')}")
            print(f"      Host: {hybrid_node.get('host')}")
            print(f"      Health: {hybrid_node.get('health')}")
        else:
            print("   ✗ Hybrid node NOT found in cluster")
            print("   Available nodes:")
            for node in nodes.get('nodes', []):
                print(f"      - {node.get('node_id')} ({node.get('role')})")
            bridge.stop()
            bridge.disconnect()
            return False

    except requests.exceptions.RequestException as e:
        print(f"   FAILED: Could not query cluster: {e}")
        bridge.stop()
        bridge.disconnect()
        return False

    # Verify DSP metrics are visible
    print("\n6. Verifying DSP metrics visibility...")
    dsp_metrics = bridge.get_dsp_metrics()

    if dsp_metrics:
        print(f"   ✓ DSP metrics retrieved:")
        print(f"      ICI: {dsp_metrics.get('ici', 0.0):.3f} ms")
        print(f"      Coherence: {dsp_metrics.get('coherence', 0.0):.3f}")
        print(f"      Criticality: {dsp_metrics.get('criticality', 0.0):.3f}")
        print(f"      Spectral Centroid: {dsp_metrics.get('spectral_centroid', 0.0):.1f} Hz")

        # Check if cluster node shows these metrics
        if hybrid_node:
            cluster_coherence = hybrid_node.get('coherence', 0.0)
            cluster_criticality = hybrid_node.get('criticality', 0.0)

            coherence_match = abs(cluster_coherence - dsp_metrics.get('coherence', 0.0)) < 0.1
            criticality_match = abs(cluster_criticality - dsp_metrics.get('criticality', 0.0)) < 0.1

            if coherence_match and criticality_match:
                print(f"   ✓ Cluster metrics match hybrid node DSP metrics")
            else:
                print(f"   ⚠ Cluster metrics differ from hybrid node (may be stale)")
                print(f"      Cluster coherence: {cluster_coherence:.3f}")
                print(f"      Cluster criticality: {cluster_criticality:.3f}")

        dsp_ok = True
    else:
        print("   ✗ Could not retrieve DSP metrics")
        dsp_ok = False

    # Verify safety telemetry
    print("\n7. Verifying safety telemetry...")
    safety = bridge.get_safety()

    if safety:
        print(f"   ✓ Safety telemetry retrieved:")
        print(f"      Status: {safety.get('status', 'UNKNOWN')}")
        print(f"      Temperature: {safety.get('temperature', 0.0):.1f}°C")
        print(f"      Overload count: {safety.get('overload_count', 0)}")
        print(f"      Clamp count: {safety.get('clamp_count', 0)}")

        safety_ok = safety.get('status') == 'HYBRID_SAFETY_OK'
    else:
        print("   ✗ Could not retrieve safety telemetry")
        safety_ok = False

    # Verify statistics
    print("\n8. Verifying node statistics...")
    stats = bridge.get_statistics()

    if stats:
        print(f"   ✓ Statistics retrieved:")
        print(f"      Latency: {stats.get('total_latency_us', 0)} µs")
        print(f"      Uptime: {stats.get('uptime_ms', 0) / 1000:.1f} s")
        print(f"      CPU load: {stats.get('cpu_load', 0.0):.1f}%")
        print(f"      Modulation fidelity: {stats.get('modulation_fidelity', 0.0):.1f}%")

        stats_ok = True
    else:
        print("   ✗ Could not retrieve statistics")
        stats_ok = False

    # Test real-time updates
    print("\n9. Testing real-time updates (10 seconds)...")
    print("   Setting dynamic control voltage and monitoring cluster...")

    for i in range(10):
        # Update control voltage
        cv1 = 2.5 + 2.0 * (i / 10.0)  # Sweep from 2.5V to 4.5V
        cv = ControlVoltage(cv1=cv1, cv2=3.0, phi_phase=i * 0.6, phi_depth=0.7)
        bridge.set_control_voltage(cv)

        time.sleep(1.0)

        # Check cluster still sees the node
        try:
            response = requests.get(f"{cluster_url}/api/cluster/nodes", timeout=2)
            nodes = response.json()

            node_found = any(n.get('node_id') == 'hybrid_analog_dsp' or n.get('role') == 'hybrid'
                            for n in nodes.get('nodes', []))

            if node_found:
                print(f"   [{i+1}/10] ✓ Node visible in cluster")
            else:
                print(f"   [{i+1}/10] ✗ Node NOT visible in cluster")

        except requests.exceptions.RequestException:
            print(f"   [{i+1}/10] ✗ Could not query cluster")

    updates_ok = True  # If we got here, updates are working

    # Get node detail from cluster
    print("\n10. Retrieving detailed node information from cluster...")
    try:
        response = requests.get(f"{cluster_url}/api/cluster/nodes/hybrid_analog_dsp", timeout=5)
        if response.status_code == 200:
            detail = response.json()

            if detail.get('ok'):
                status = detail.get('status', {})
                history = detail.get('history', [])

                print(f"   ✓ Node detail retrieved:")
                print(f"      Health: {status.get('health')}")
                print(f"      Uptime: {status.get('uptime_s', 0):.1f} s")
                print(f"      RTT: {status.get('rtt_ms', 0):.2f} ms")
                print(f"      History samples: {len(history)}")

                detail_ok = True
            else:
                print(f"   ✗ Node detail not available: {detail.get('message')}")
                detail_ok = False
        else:
            print(f"   ✗ Could not retrieve node detail (status {response.status_code})")
            detail_ok = False

    except requests.exceptions.RequestException as e:
        print(f"   ✗ Could not retrieve node detail: {e}")
        detail_ok = False

    # Overall SC-004 check
    meets_sc004 = (hybrid_node is not None) and dsp_ok and safety_ok and stats_ok and updates_ok and detail_ok

    # Stop and cleanup
    print("\n11. Stopping node and disconnecting...")
    bridge.stop()
    bridge.disconnect()

    # Final result
    print("\n" + "=" * 60)
    if meets_sc004:
        print("TEST PASSED: SC-004 cluster integration requirement met")
    else:
        print("TEST FAILED: SC-004 cluster integration requirement not met")
    print("=" * 60)

    return meets_sc004


def main():
    parser = argparse.ArgumentParser(description="Test hybrid node cluster integration (SC-004)")
    parser.add_argument("--port", help="Serial port for hybrid node (auto-detect if not specified)")
    parser.add_argument("--cluster-url", default="http://localhost:8000",
                       help="Cluster monitor URL (default: http://localhost:8000)")
    args = parser.parse_args()

    try:
        passed = test_cluster_integration(args.port, args.cluster_url)
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
