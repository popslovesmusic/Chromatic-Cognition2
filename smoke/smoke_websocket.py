"""
Smoke Test: WebSocket Connectivity
Feature 019: Release Readiness Validation

Tests basic WebSocket connectivity and ping/pong functionality.

Success Criteria:
- Connect to /ws/dashboard endpoint
- Send ping and receive pong
- RTT < 100ms
- No connection errors
"""

import asyncio
import websockets
import json
import time
import os
import sys

# Configuration
SOUNDLAB_URL = os.getenv('SOUNDLAB_URL', 'http://localhost:8000')
WS_URL = SOUNDLAB_URL.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws/dashboard'
TIMEOUT_SECONDS = 10


async def test_websocket_ping():
    """Test WebSocket ping/pong"""
    print("=" * 70)
    print("Smoke Test: WebSocket Connectivity")
    print("=" * 70)
    print(f"Target: {WS_URL}")
    print()

    try:
        # Connect to WebSocket
        print("Connecting to WebSocket...")
        async with websockets.connect(WS_URL, timeout=TIMEOUT_SECONDS) as websocket:
            print(f"✓ Connected to {WS_URL}")
            print()

            # Send ping
            ping_time = time.time()
            ping_message = {
                "type": "ping",
                "client_time": ping_time * 1000.0
            }

            print(f"Sending ping: {ping_message}")
            await websocket.send(json.dumps(ping_message))

            # Wait for pong
            try:
                response = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=TIMEOUT_SECONDS
                )

                pong_time = time.time()
                pong_message = json.loads(response)

                print(f"Received pong: {pong_message}")
                print()

                # Calculate RTT
                rtt_ms = (pong_time - ping_time) * 1000.0

                print(f"Round-trip time: {rtt_ms:.2f} ms")
                print()

                # Validate pong
                if pong_message.get('type') != 'pong':
                    print(f"✗ FAIL: Expected 'pong', got '{pong_message.get('type')}'")
                    return False

                if rtt_ms > 100:
                    print(f"✗ FAIL: RTT {rtt_ms:.2f}ms exceeds 100ms limit")
                    return False

                print("✓ PASS: WebSocket ping/pong successful")
                print(f"✓ PASS: RTT {rtt_ms:.2f}ms < 100ms")
                return True

            except asyncio.TimeoutError:
                print(f"✗ FAIL: Timeout waiting for pong ({TIMEOUT_SECONDS}s)")
                return False

    except websockets.exceptions.WebSocketException as e:
        print(f"✗ FAIL: WebSocket error: {e}")
        return False

    except Exception as e:
        print(f"✗ FAIL: Unexpected error: {e}")
        return False


async def test_websocket_state_request():
    """Test state request via WebSocket"""
    print("=" * 70)
    print("Smoke Test: WebSocket State Request")
    print("=" * 70)
    print(f"Target: {WS_URL}")
    print()

    try:
        async with websockets.connect(WS_URL, timeout=TIMEOUT_SECONDS) as websocket:
            print("✓ Connected")
            print()

            # Request state
            state_request = {
                "type": "get_state",
                "client_time": time.time() * 1000.0
            }

            print(f"Requesting state: {state_request}")
            await websocket.send(json.dumps(state_request))

            # Wait for response
            try:
                response = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=TIMEOUT_SECONDS
                )

                state_response = json.loads(response)
                print(f"Received state response")
                print()

                # Validate response
                if state_response.get('type') != 'state_response':
                    print(f"✗ FAIL: Expected 'state_response', got '{state_response.get('type')}'")
                    return False

                if 'data' not in state_response:
                    print("✗ FAIL: No 'data' in state response")
                    return False

                state_data = state_response['data']
                if state_data is None:
                    print("⚠ WARNING: State data is None (server may not have state yet)")
                    return True

                # Check for expected fields
                expected_fields = ['timestamp', 'ici', 'coherence', 'criticality']
                missing_fields = [f for f in expected_fields if f not in state_data]

                if missing_fields:
                    print(f"⚠ WARNING: Missing fields: {missing_fields}")

                print("✓ PASS: State request successful")
                print(f"  State data keys: {list(state_data.keys())}")
                return True

            except asyncio.TimeoutError:
                print(f"✗ FAIL: Timeout waiting for state response ({TIMEOUT_SECONDS}s)")
                return False

    except websockets.exceptions.WebSocketException as e:
        print(f"✗ FAIL: WebSocket error: {e}")
        return False

    except Exception as e:
        print(f"✗ FAIL: Unexpected error: {e}")
        return False


async def main():
    """Run all WebSocket smoke tests"""
    print()
    print("Running WebSocket Smoke Tests...")
    print()

    results = []

    # Test 1: Ping/Pong
    result1 = await test_websocket_ping()
    results.append(result1)
    print()

    # Test 2: State Request
    result2 = await test_websocket_state_request()
    results.append(result2)
    print()

    # Summary
    print("=" * 70)
    print("WebSocket Smoke Test Summary")
    print("=" * 70)
    passed = sum(results)
    total = len(results)

    print(f"Passed: {passed}/{total}")
    print()

    if all(results):
        print("✓ ALL WEBSOCKET SMOKE TESTS PASSED")
        sys.exit(0)
    else:
        print("✗ SOME WEBSOCKET SMOKE TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
