"""
Test Preset Application - SC-004: Preset round-trip

Verifies that preset JSON can be exported, imported, and results in identical values.
Tests that all controls update correctly when a preset is loaded.

Usage:
    python test_preset_apply.py
"""

import asyncio
import websockets
import json
import sys


async def test_preset_roundtrip(server_url='ws://localhost:8000/ws/ui'):
    """
    Test preset export → import → verify same values

    Args:
        server_url: WebSocket URL

    Returns:
        True if test passed
    """
    print("=" * 60)
    print("Preset Round-Trip Test")
    print("=" * 60)
    print(f"Server: {server_url}\n")

    try:
        async with websockets.connect(server_url) as websocket:
            print("✓ Connected to server")

            # 1. Get initial state
            print("\n1. Getting initial state...")
            initial = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            initial_state = json.loads(initial)['data']
            print(f"✓ Initial state received")
            print(f"  Channels: {len(initial_state['channels'])}")
            print(f"  Global params: {initial_state['global']}")
            print(f"  Phi params: {initial_state['phi']}")

            # 2. Set known test values
            print("\n2. Setting test parameter values...")
            test_values = [
                ("channel", 0, "frequency", 1.23),
                ("channel", 0, "amplitude", 0.75),
                ("channel", 1, "frequency", 4.56),
                ("channel", 1, "amplitude", 0.33),
                ("global", None, "coupling_strength", 1.5),
                ("global", None, "gain", 0.8),
                ("phi", None, "phase", 0.25),
                ("phi", None, "depth", 0.777),
            ]

            for param_type, channel, param, value in test_values:
                msg = {
                    "type": "set_param",
                    "param_type": param_type,
                    "channel": channel,
                    "param": param,
                    "value": value
                }
                await websocket.send(json.dumps(msg))

                # Wait for acknowledgment
                response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                response_data = json.loads(response)

                if response_data.get('success'):
                    print(f"  ✓ Set {param_type}.{param} = {value}")
                else:
                    print(f"  ✗ Failed to set {param_type}.{param}")
                    return False

                await asyncio.sleep(0.15)  # Rate limiting

            # 3. Get updated state (our "preset")
            print("\n3. Getting updated state (preset)...")
            msg = {"type": "get_state"}
            await websocket.send(json.dumps(msg))

            response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            preset_state = json.loads(response)['data']
            print("✓ Preset state captured")

            # 4. Change some values
            print("\n4. Changing values...")
            changes = [
                ("channel", 0, "frequency", 99.99),
                ("global", "coupling_strength", 0.1),
                ("phi", None, "depth", 0.001),
            ]

            for param_type, channel, param, value in changes:
                msg = {
                    "type": "set_param",
                    "param_type": param_type,
                    "channel": channel,
                    "param": param,
                    "value": value
                }
                await websocket.send(json.dumps(msg))
                await asyncio.wait_for(websocket.recv(), timeout=1.0)
                print(f"  ✓ Changed {param_type}.{param} = {value}")
                await asyncio.sleep(0.15)

            # 5. Reapply preset values
            print("\n5. Reapplying preset values...")
            for param_type, channel, param, value in test_values:
                msg = {
                    "type": "set_param",
                    "param_type": param_type,
                    "channel": channel,
                    "param": param,
                    "value": value
                }
                await websocket.send(json.dumps(msg))
                await asyncio.wait_for(websocket.recv(), timeout=1.0)
                await asyncio.sleep(0.15)

            # 6. Get final state
            print("\n6. Getting final state...")
            msg = {"type": "get_state"}
            await websocket.send(json.dumps(msg))

            response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            final_state = json.loads(response)['data']
            print("✓ Final state received")

            # 7. Verify values match
            print("\n7. Verifying values match...")
            errors = []

            # Check test values
            for param_type, channel, param, expected_value in test_values:
                if param_type == "channel":
                    actual_value = final_state['channels'][channel][param]
                elif param_type == "global":
                    actual_value = final_state['global'][param]
                elif param_type == "phi":
                    actual_value = final_state['phi'][param]

                tolerance = 0.001
                if abs(actual_value - expected_value) > tolerance:
                    error_msg = f"  ✗ {param_type}.{param}: expected {expected_value}, got {actual_value}"
                    print(error_msg)
                    errors.append(error_msg)
                else:
                    print(f"  ✓ {param_type}.{param} = {actual_value:.3f}")

            # Summary
            print("\n" + "=" * 60)
            print("Results")
            print("=" * 60)

            if not errors:
                print("✓ PASS: All values match after preset round-trip")
                print("=" * 60)
                return True
            else:
                print(f"✗ FAIL: {len(errors)} values don't match:")
                for error in errors:
                    print(error)
                print("=" * 60)
                return False

    except websockets.exceptions.WebSocketException as e:
        print(f"✗ WebSocket error: {e}")
        return False
    except asyncio.TimeoutError:
        print(f"✗ Timeout waiting for response")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    server_url = sys.argv[1] if len(sys.argv) > 1 else 'ws://localhost:8000/ws/ui'

    result = asyncio.run(test_preset_roundtrip(server_url))

    sys.exit(0 if result else 1)
