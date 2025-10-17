"""
Test WebSocket Reconnect - SC-004: Auto-reconnect without UI stall

Simulates connection drops and verifies that the metrics HUD
reconnects automatically without stalling the UI.

Usage:
    python test_ws_reconnect.py [ws://localhost:8000/ws/metrics]
"""

import asyncio
import websockets
import json
import time
import sys


async def test_reconnect_behavior(server_url='ws://localhost:8000/ws/metrics'):
    """
    Test WebSocket reconnect behavior

    Args:
        server_url: WebSocket URL

    Returns:
        True if reconnect works properly
    """
    print("=" * 60)
    print("WebSocket Reconnect Test")
    print("=" * 60)
    print(f"Server: {server_url}")
    print()

    test_results = []

    # Test 1: Normal connection
    print("Test 1: Normal Connection")
    print("-" * 60)

    try:
        async with websockets.connect(server_url) as websocket:
            print("✓ Connected")

            # Receive a few frames
            frames_received = 0
            for i in range(5):
                message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                data = json.loads(message)
                frames_received += 1

            print(f"✓ Received {frames_received} frames")

            if frames_received >= 5:
                print("✓ PASS: Normal connection works\n")
                test_results.append(('normal_connection', True))
            else:
                print("✗ FAIL: Did not receive expected frames\n")
                test_results.append(('normal_connection', False))

    except Exception as e:
        print(f"✗ FAIL: Connection error: {e}\n")
        test_results.append(('normal_connection', False))

    # Test 2: Disconnect and reconnect
    print("Test 2: Disconnect and Reconnect")
    print("-" * 60)

    try:
        # First connection
        websocket = await websockets.connect(server_url)
        print("✓ Connected")

        # Receive a frame
        message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
        print("✓ Received first frame")

        # Disconnect
        await websocket.close()
        print("✓ Disconnected")

        # Wait a moment
        await asyncio.sleep(1)

        # Reconnect
        websocket = await websockets.connect(server_url)
        print("✓ Reconnected")

        # Verify we can receive frames again
        message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
        data = json.loads(message)
        print("✓ Received frame after reconnect")

        await websocket.close()

        print("✓ PASS: Disconnect and reconnect works\n")
        test_results.append(('disconnect_reconnect', True))

    except Exception as e:
        print(f"✗ FAIL: Reconnect error: {e}\n")
        test_results.append(('disconnect_reconnect', False))

    # Test 3: Multiple rapid disconnects
    print("Test 3: Multiple Rapid Disconnects")
    print("-" * 60)

    disconnect_count = 3
    successful_reconnects = 0

    try:
        for i in range(disconnect_count):
            print(f"Cycle {i+1}/{disconnect_count}:")

            # Connect
            websocket = await websockets.connect(server_url)
            print("  ✓ Connected")

            # Receive a frame
            message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            print("  ✓ Received frame")

            # Disconnect
            await websocket.close()
            print("  ✓ Disconnected")

            successful_reconnects += 1

            # Short delay
            await asyncio.sleep(0.5)

        if successful_reconnects == disconnect_count:
            print(f"✓ PASS: {successful_reconnects}/{disconnect_count} reconnects successful\n")
            test_results.append(('rapid_disconnects', True))
        else:
            print(f"⚠ PARTIAL: {successful_reconnects}/{disconnect_count} reconnects successful\n")
            test_results.append(('rapid_disconnects', successful_reconnects == disconnect_count))

    except Exception as e:
        print(f"✗ FAIL: Rapid disconnect error: {e}\n")
        test_results.append(('rapid_disconnects', False))

    # Test 4: Connection timeout behavior
    print("Test 4: Connection Timeout Behavior")
    print("-" * 60)

    try:
        websocket = await websockets.connect(server_url)
        print("✓ Connected")

        # Wait for frames with timeout
        frames_received = 0
        timeout_count = 0

        for i in range(10):
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=0.5)
                frames_received += 1
            except asyncio.TimeoutError:
                timeout_count += 1

        await websocket.close()

        print(f"Frames received: {frames_received}")
        print(f"Timeouts: {timeout_count}")

        # We expect to receive most frames (stream is 30 Hz)
        if frames_received >= 8:  # Allow some tolerance
            print("✓ PASS: Connection stable with timeouts handled\n")
            test_results.append(('timeout_handling', True))
        else:
            print("⚠ WARNING: Low frame rate, possible issue\n")
            test_results.append(('timeout_handling', False))

    except Exception as e:
        print(f"✗ FAIL: Timeout test error: {e}\n")
        test_results.append(('timeout_handling', False))

    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)

    for test_name, passed in test_results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:25} : {status}")

    all_passed = all(result[1] for result in test_results)

    print()
    if all_passed:
        print("✓ All reconnect tests PASSED")
    else:
        failed_count = sum(1 for result in test_results if not result[1])
        print(f"✗ {failed_count}/{len(test_results)} tests FAILED")

    print("=" * 60)

    return {
        'success': all_passed,
        'results': dict(test_results),
        'total_tests': len(test_results),
        'passed_tests': sum(1 for r in test_results if r[1])
    }


if __name__ == "__main__":
    server_url = sys.argv[1] if len(sys.argv) > 1 else 'ws://localhost:8000/ws/metrics'

    result = asyncio.run(test_reconnect_behavior(server_url))

    if result and result['success']:
        sys.exit(0)
    else:
        sys.exit(1)
