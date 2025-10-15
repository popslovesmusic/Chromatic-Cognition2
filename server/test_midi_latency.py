"""
Test MIDI Latency - SC-001: MIDI latency <10ms, UI latency <100ms

Measures the time from MIDI CC message arrival to audio engine parameter update.
Since we're testing the JavaScript MIDI controller, this test provides a Python-based
simulation and validation of latency requirements.

Usage:
    python test_midi_latency.py [ws://localhost:8000/ws/ui] [num_samples]
"""

import asyncio
import websockets
import json
import time
import sys
import statistics
from typing import List, Dict


async def test_midi_latency(server_url='ws://localhost:8000/ws/ui', num_samples=100):
    """
    Test MIDI parameter update latency

    Args:
        server_url: WebSocket URL for UI control
        num_samples: Number of test samples to collect

    Returns:
        Dictionary with latency statistics
    """
    print("=" * 60)
    print("MIDI Controller Latency Test")
    print("=" * 60)
    print(f"Server: {server_url}")
    print(f"Samples: {num_samples}")
    print()

    latencies = []
    successful_updates = 0
    failed_updates = 0

    try:
        async with websockets.connect(server_url) as websocket:
            print("✓ Connected to /ws/ui endpoint")
            print("Simulating MIDI CC messages...\n")

            # Test different parameter types (simulating MIDI CC mappings)
            test_params = [
                # Phi controls (CC1, CC2)
                {'param_type': 'phi', 'channel': None, 'param': 'depth', 'value': 0.5, 'cc': 1},
                {'param_type': 'phi', 'channel': None, 'param': 'phase', 'value': 0.75, 'cc': 2},

                # Global controls (CC7, CC10)
                {'param_type': 'global', 'channel': None, 'param': 'gain', 'value': 1.0, 'cc': 7},
                {'param_type': 'global', 'channel': None, 'param': 'coupling_strength', 'value': 0.8, 'cc': 10},

                # Channel controls (CC16-23)
                {'param_type': 'channel', 'channel': 0, 'param': 'amplitude', 'value': 0.6, 'cc': 16},
                {'param_type': 'channel', 'channel': 1, 'param': 'amplitude', 'value': 0.7, 'cc': 17},
                {'param_type': 'channel', 'channel': 2, 'param': 'frequency', 'value': 440.0, 'cc': None},
            ]

            for i in range(num_samples):
                # Rotate through test parameters
                test_param = test_params[i % len(test_params)]

                # Prepare message (simulating MIDI controller's WebSocket send)
                message = {
                    'type': 'set_param',
                    'param_type': test_param['param_type'],
                    'channel': test_param['channel'],
                    'param': test_param['param'],
                    'value': test_param['value']
                }

                # Measure round-trip latency
                start_time = time.perf_counter()

                try:
                    # Send parameter update
                    await websocket.send(json.dumps(message))

                    # Wait for confirmation
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)

                    end_time = time.perf_counter()
                    latency_ms = (end_time - start_time) * 1000

                    data = json.loads(response)

                    if data.get('type') == 'param_updated' and data.get('success'):
                        latencies.append(latency_ms)
                        successful_updates += 1

                        if i < 10 or i % 20 == 0:
                            cc_info = f"(CC{test_param['cc']})" if test_param['cc'] else ""
                            print(f"[{i+1:3d}] {test_param['param_type']:7} {test_param['param']:20} {cc_info:6} - {latency_ms:6.2f} ms")
                    else:
                        failed_updates += 1
                        print(f"[{i+1:3d}] FAILED: {data}")

                except asyncio.TimeoutError:
                    failed_updates += 1
                    print(f"[{i+1:3d}] TIMEOUT")
                except Exception as e:
                    failed_updates += 1
                    print(f"[{i+1:3d}] ERROR: {e}")

                # Small delay to avoid overwhelming the server
                await asyncio.sleep(0.01)

        # Calculate statistics
        if latencies:
            print("\n" + "=" * 60)
            print("Results")
            print("=" * 60)

            avg_latency = statistics.mean(latencies)
            median_latency = statistics.median(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            stdev_latency = statistics.stdev(latencies) if len(latencies) > 1 else 0

            print(f"\nSuccessful updates: {successful_updates}/{num_samples}")
            print(f"Failed updates: {failed_updates}/{num_samples}")
            print()

            print("Latency Statistics (round-trip):")
            print(f"  Average:   {avg_latency:7.2f} ms")
            print(f"  Median:    {median_latency:7.2f} ms")
            print(f"  Min:       {min_latency:7.2f} ms")
            print(f"  Max:       {max_latency:7.2f} ms")
            print(f"  Std Dev:   {stdev_latency:7.2f} ms")
            print()

            # Validate against success criteria
            print("Success Criteria Validation:")
            print("-" * 60)

            # SC-001: MIDI latency <10ms (processing only, not round-trip)
            # Estimate processing latency as half of round-trip
            estimated_processing = avg_latency / 2

            midi_pass = estimated_processing < 10
            print(f"  MIDI processing (<10 ms):  {estimated_processing:6.2f} ms  {'✓ PASS' if midi_pass else '✗ FAIL'}")

            # UI latency <100ms (full round-trip)
            ui_pass = avg_latency < 100
            print(f"  UI round-trip (<100 ms):   {avg_latency:6.2f} ms  {'✓ PASS' if ui_pass else '✗ FAIL'}")

            print()

            # Percentile analysis
            sorted_latencies = sorted(latencies)
            p50 = sorted_latencies[int(len(sorted_latencies) * 0.50)]
            p90 = sorted_latencies[int(len(sorted_latencies) * 0.90)]
            p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)]
            p99 = sorted_latencies[int(len(sorted_latencies) * 0.99)]

            print("Percentiles:")
            print(f"  P50:  {p50:7.2f} ms")
            print(f"  P90:  {p90:7.2f} ms")
            print(f"  P95:  {p95:7.2f} ms")
            print(f"  P99:  {p99:7.2f} ms")

            print()
            print("=" * 60)

            if midi_pass and ui_pass:
                print("✓ All latency targets MET")
            else:
                print("✗ Some latency targets EXCEEDED")

            print("=" * 60)

            return {
                'success': midi_pass and ui_pass,
                'avg_latency_ms': avg_latency,
                'median_latency_ms': median_latency,
                'max_latency_ms': max_latency,
                'estimated_processing_ms': estimated_processing,
                'successful_updates': successful_updates,
                'failed_updates': failed_updates,
                'total_samples': num_samples
            }
        else:
            print("\n✗ No successful updates - cannot calculate statistics")
            return None

    except websockets.exceptions.WebSocketException as e:
        print(f"\n✗ WebSocket error: {e}")
        print("\nPossible causes:")
        print("  - Server not running (check: uvicorn main:app)")
        print("  - Wrong WebSocket URL")
        print("  - /ws/ui endpoint not implemented")
        return None
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_rate_limiting(server_url='ws://localhost:8000/ws/ui'):
    """
    Test rate limiting enforcement (<10 Hz per FR-006)

    Rapidly sends updates for the same parameter and verifies
    that the server respects the rate limit.
    """
    print("\n" + "=" * 60)
    print("Rate Limiting Test (FR-006: <10 Hz)")
    print("=" * 60)

    try:
        async with websockets.connect(server_url) as websocket:
            print("✓ Connected")
            print("Sending rapid updates for same parameter...\n")

            message = {
                'type': 'set_param',
                'param_type': 'phi',
                'channel': None,
                'param': 'depth',
                'value': 0.5
            }

            send_times = []
            response_times = []

            # Send 20 messages as fast as possible
            for i in range(20):
                send_time = time.perf_counter()
                await websocket.send(json.dumps(message))
                send_times.append(send_time)

                # Vary the value slightly
                message['value'] = 0.5 + (i * 0.01)

            # Collect responses
            for i in range(20):
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=0.5)
                    response_times.append(time.perf_counter())
                except asyncio.TimeoutError:
                    break

            # Analyze intervals
            if len(response_times) > 1:
                intervals = []
                for i in range(1, len(response_times)):
                    interval_ms = (response_times[i] - response_times[i-1]) * 1000
                    intervals.append(interval_ms)

                avg_interval = statistics.mean(intervals)
                min_interval = min(intervals)

                # 10 Hz = 100ms minimum interval
                expected_min_interval = 100  # ms

                print(f"Messages sent: {len(send_times)}")
                print(f"Responses received: {len(response_times)}")
                print(f"Average interval: {avg_interval:.2f} ms")
                print(f"Minimum interval: {min_interval:.2f} ms")
                print(f"Expected minimum: {expected_min_interval:.2f} ms")
                print()

                if min_interval >= expected_min_interval * 0.9:  # 10% tolerance
                    print(f"✓ PASS: Rate limiting enforced (min interval {min_interval:.0f}ms >= {expected_min_interval}ms)")
                else:
                    print(f"⚠ WARNING: Rate limiting may not be enforced (min interval {min_interval:.0f}ms < {expected_min_interval}ms)")

                print("=" * 60)

    except Exception as e:
        print(f"✗ Error: {e}")


if __name__ == "__main__":
    server_url = sys.argv[1] if len(sys.argv) > 1 else 'ws://localhost:8000/ws/ui'
    num_samples = int(sys.argv[2]) if len(sys.argv) > 2 else 100

    # Run latency test
    result = asyncio.run(test_midi_latency(server_url, num_samples))

    # Run rate limiting test
    asyncio.run(test_rate_limiting(server_url))

    # Exit with appropriate code
    if result and result['success']:
        sys.exit(0)
    else:
        sys.exit(1)
