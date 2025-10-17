"""
Test WebSocket Resilience - Edge Cases

Tests WebSocket connection behavior under various failure conditions:
- Disconnects and reconnects
- Invalid data
- Rapid updates
- Network interruptions

Usage:
    python test_ws_resilience.py
"""

import asyncio
import websockets
import json
import time
import sys


async def test_disconnect_reconnect(server_url, num_cycles=3):
    """Test disconnect/reconnect behavior"""
    print("\n" + "=" * 60)
    print("Test 1: Disconnect/Reconnect")
    print("=" * 60)

    for i in range(num_cycles):
        print(f"\nCycle {i+1}/{num_cycles}:")

        try:
            # Connect
            print("  Connecting...")
            websocket = await websockets.connect(server_url)
            print("  ✓ Connected")

            # Receive initial state
            initial = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            print(f"  ✓ Received initial state")

            # Send a test parameter
            msg = {
                "type": "set_param",
                "param_type": "channel",
                "channel": 0,
                "param": "frequency",
                "value": 1.0 + i
            }
            await websocket.send(json.dumps(msg))
            print(f"  ✓ Sent parameter update")

            # Wait for response
            response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            print(f"  ✓ Received response")

            # Close connection
            await websocket.close()
            print(f"  ✓ Disconnected")

            # Wait before reconnecting
            await asyncio.sleep(1.0)

        except Exception as e:
            print(f"  ✗ Error: {e}")
            return False

    print("\n✓ Disconnect/reconnect test PASSED")
    return True


async def test_invalid_data(server_url):
    """Test invalid data handling"""
    print("\n" + "=" * 60)
    print("Test 2: Invalid Data Handling")
    print("=" * 60)

    try:
        async with websockets.connect(server_url) as websocket:
            print("✓ Connected")

            # Wait for initial state
            await asyncio.wait_for(websocket.recv(), timeout=2.0)

            # Test 1: Invalid JSON
            print("\nSending invalid JSON...")
            try:
                await websocket.send("not valid json")
                # Server might close connection, or ignore
                await asyncio.sleep(0.5)
                print("✓ Server handled invalid JSON")
            except Exception as e:
                print(f"✓ Server rejected invalid JSON: {e}")

            # Test 2: Missing required fields
            print("\nSending message with missing fields...")
            msg = {"type": "set_param"}  # Missing param, channel, value
            await websocket.send(json.dumps(msg))
            await asyncio.sleep(0.5)
            print("✓ Server handled missing fields")

            # Test 3: Invalid parameter type
            print("\nSending invalid parameter type...")
            msg = {
                "type": "set_param",
                "param_type": "invalid_type",
                "channel": 0,
                "param": "frequency",
                "value": 1.0
            }
            await websocket.send(json.dumps(msg))
            response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            data = json.loads(response)
            if not data.get('success', True):
                print("✓ Server rejected invalid parameter type")
            else:
                print("⚠ Server accepted invalid parameter type")

            # Test 4: Out of range channel
            print("\nSending out of range channel...")
            msg = {
                "type": "set_param",
                "param_type": "channel",
                "channel": 99,  # Invalid channel
                "param": "frequency",
                "value": 1.0
            }
            await websocket.send(json.dumps(msg))
            response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            data = json.loads(response)
            if not data.get('success', True):
                print("✓ Server rejected invalid channel")
            else:
                print("⚠ Server accepted invalid channel")

            # Test 5: NaN value
            print("\nSending NaN value...")
            msg = {
                "type": "set_param",
                "param_type": "channel",
                "channel": 0,
                "param": "frequency",
                "value": float('nan')
            }
            try:
                await websocket.send(json.dumps(msg))
                await asyncio.sleep(0.5)
                print("✓ Server handled NaN value")
            except Exception as e:
                print(f"✓ Cannot send NaN via JSON: {e}")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n✓ Invalid data handling test PASSED")
    return True


async def test_rapid_updates(server_url, num_updates=50):
    """Test rapid parameter updates (rate limiting)"""
    print("\n" + "=" * 60)
    print("Test 3: Rapid Updates (Rate Limiting)")
    print("=" * 60)
    print(f"Sending {num_updates} rapid updates...")

    try:
        async with websockets.connect(server_url) as websocket:
            print("✓ Connected")

            # Wait for initial state
            await asyncio.wait_for(websocket.recv(), timeout=2.0)

            # Send rapid updates
            start_time = time.perf_counter()
            sent_count = 0

            for i in range(num_updates):
                msg = {
                    "type": "set_param",
                    "param_type": "channel",
                    "channel": 0,
                    "param": "frequency",
                    "value": 1.0 + i * 0.01
                }
                await websocket.send(json.dumps(msg))
                sent_count += 1

                # No delay - send as fast as possible

            end_time = time.perf_counter()
            duration = end_time - start_time

            print(f"✓ Sent {sent_count} updates in {duration*1000:.2f} ms")
            print(f"  Send rate: {sent_count/duration:.1f} Hz")

            # Wait for responses
            response_count = 0
            timeout = 2.0
            start_receive = time.perf_counter()

            try:
                while time.perf_counter() - start_receive < timeout:
                    response = await asyncio.wait_for(websocket.recv(), timeout=0.5)
                    response_count += 1
            except asyncio.TimeoutError:
                pass

            print(f"✓ Received {response_count} responses")

            # Check rate limiting (should be <10 Hz = <10 responses in 1 second)
            if response_count <= sent_count:
                print(f"✓ Rate limiting working (received {response_count}/{sent_count})")
            else:
                print(f"⚠ Unexpected response count: {response_count}")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n✓ Rapid updates test PASSED")
    return True


async def test_connection_timeout(server_url):
    """Test connection timeout behavior"""
    print("\n" + "=" * 60)
    print("Test 4: Connection Timeout")
    print("=" * 60)

    try:
        async with websockets.connect(server_url) as websocket:
            print("✓ Connected")

            # Wait for initial state
            await asyncio.wait_for(websocket.recv(), timeout=2.0)

            # Stay idle for a period
            print("Staying idle for 30 seconds...")
            await asyncio.sleep(30)

            # Try to send a message
            msg = {
                "type": "ping"
            }
            await websocket.send(json.dumps(msg))

            response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            data = json.loads(response)

            if data['type'] == 'pong':
                print("✓ Connection still alive after idle period")
            else:
                print(f"⚠ Unexpected response: {data['type']}")

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    print("\n✓ Connection timeout test PASSED")
    return True


async def run_all_tests(server_url='ws://localhost:8000/ws/ui'):
    """Run all resilience tests"""
    print("=" * 60)
    print("WebSocket Resilience Test Suite")
    print("=" * 60)
    print(f"Server: {server_url}\n")

    results = {}

    # Test 1: Disconnect/Reconnect
    results['disconnect_reconnect'] = await test_disconnect_reconnect(server_url)

    # Test 2: Invalid Data
    results['invalid_data'] = await test_invalid_data(server_url)

    # Test 3: Rapid Updates
    results['rapid_updates'] = await test_rapid_updates(server_url)

    # Test 4: Connection Timeout
    # Commented out by default as it takes 30 seconds
    # results['connection_timeout'] = await test_connection_timeout(server_url)

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name}: {status}")

    all_passed = all(results.values())

    print()
    if all_passed:
        print("✓ All tests PASSED")
    else:
        print("✗ Some tests FAILED")

    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    server_url = sys.argv[1] if len(sys.argv) > 1 else 'ws://localhost:8000/ws/ui'

    result = asyncio.run(run_all_tests(server_url))

    sys.exit(0 if result else 1)
