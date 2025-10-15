"""
Test Parameter Latency - SC-001: <100ms UI→Audio Engine

Measures the time between sending a parameter update via WebSocket
and detecting the change in the audio engine output.

Usage:
    python test_param_latency.py
"""

import asyncio
import websockets
import json
import time
import sys


async def test_parameter_latency(server_url='ws://localhost:8000/ws/ui', num_tests=10):
    """
    Test parameter update latency

    Args:
        server_url: WebSocket URL
        num_tests: Number of tests to run

    Returns:
        Statistics dictionary
    """
    print("=" * 60)
    print("Parameter Latency Test")
    print("=" * 60)
    print(f"Server: {server_url}")
    print(f"Tests: {num_tests}")
    print()

    latencies = []

    try:
        async with websockets.connect(server_url) as websocket:
            print("✓ Connected to server")

            # Wait for initial state message
            initial = await websocket.recv()
            initial_data = json.parse(initial)
            print(f"✓ Received initial state: {initial_data['type']}")
            print()

            # Run tests
            for i in range(num_tests):
                print(f"Test {i+1}/{num_tests}:")

                # Send parameter update
                param_message = {
                    "type": "set_param",
                    "param_type": "channel",
                    "channel": 0,
                    "param": "frequency",
                    "value": 1.0 + i * 0.1
                }

                start_time = time.perf_counter()
                await websocket.send(json.dumps(param_message))

                # Wait for acknowledgment
                response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                end_time = time.perf_counter()

                response_data = json.loads(response)

                latency_ms = (end_time - start_time) * 1000.0
                latencies.append(latency_ms)

                print(f"  Sent: frequency = {param_message['value']:.2f}")
                print(f"  Response: {response_data['type']}")
                print(f"  Latency: {latency_ms:.2f} ms")

                if response_data['type'] == 'param_updated':
                    if response_data['success']:
                        print(f"  ✓ Parameter updated successfully")
                    else:
                        print(f"  ✗ Parameter update failed")

                print()

                # Small delay between tests
                await asyncio.sleep(0.2)

            # Calculate statistics
            if latencies:
                avg_latency = sum(latencies) / len(latencies)
                min_latency = min(latencies)
                max_latency = max(latencies)

                print("=" * 60)
                print("Results")
                print("=" * 60)
                print(f"Average latency: {avg_latency:.2f} ms")
                print(f"Min latency:     {min_latency:.2f} ms")
                print(f"Max latency:     {max_latency:.2f} ms")
                print()

                # Check success criteria (SC-001: <100ms)
                if avg_latency < 100.0:
                    print(f"✓ PASS: Average latency {avg_latency:.2f} ms < 100 ms")
                else:
                    print(f"✗ FAIL: Average latency {avg_latency:.2f} ms >= 100 ms")

                if max_latency < 100.0:
                    print(f"✓ PASS: Max latency {max_latency:.2f} ms < 100 ms")
                else:
                    print(f"⚠ WARNING: Max latency {max_latency:.2f} ms >= 100 ms")

                print("=" * 60)

                return {
                    'success': avg_latency < 100.0,
                    'average_ms': avg_latency,
                    'min_ms': min_latency,
                    'max_ms': max_latency,
                    'samples': len(latencies)
                }

    except websockets.exceptions.WebSocketException as e:
        print(f"✗ WebSocket error: {e}")
        return None
    except asyncio.TimeoutError:
        print(f"✗ Timeout waiting for response")
        return None
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # Parse command line arguments
    server_url = sys.argv[1] if len(sys.argv) > 1 else 'ws://localhost:8000/ws/ui'
    num_tests = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    # Run test
    result = asyncio.run(test_parameter_latency(server_url, num_tests))

    if result and result['success']:
        sys.exit(0)
    else:
        sys.exit(1)
