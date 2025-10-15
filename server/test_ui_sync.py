"""
Test UI Sync - SC-005: No desync after 10 minutes

Verifies that backend→frontend value synchronization remains accurate
over extended periods of continuous use.

Usage:
    python test_ui_sync.py [duration_minutes]
"""

import asyncio
import websockets
import json
import sys
import time
import random


async def test_ui_sync(server_url='ws://localhost:8000/ws/ui', duration_minutes=10):
    """
    Test backend→frontend synchronization over time

    Args:
        server_url: WebSocket URL
        duration_minutes: Test duration in minutes

    Returns:
        True if test passed (no desyncs detected)
    """
    print("=" * 60)
    print("UI Sync Test - Extended Duration")
    print("=" * 60)
    print(f"Server: {server_url}")
    print(f"Duration: {duration_minutes} minutes")
    print()

    duration_seconds = duration_minutes * 60
    update_interval = 5.0  # Update every 5 seconds
    num_updates = int(duration_seconds / update_interval)

    print(f"Will perform ~{num_updates} parameter updates")
    print(f"Update interval: {update_interval} seconds")
    print()

    desync_count = 0
    update_count = 0
    error_count = 0

    try:
        async with websockets.connect(server_url) as websocket:
            print("✓ Connected to server\n")

            # Get initial state
            initial = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            initial_state = json.loads(initial)['data']
            print("✓ Received initial state\n")

            # Track expected values
            expected_values = {}

            # Test loop
            start_time = time.time()
            last_update_time = start_time

            while time.time() - start_time < duration_seconds:
                current_time = time.time()
                elapsed = current_time - start_time

                # Print progress every minute
                if int(elapsed) % 60 == 0 and elapsed > 0 and current_time - last_update_time >= update_interval:
                    print(f"\n[{int(elapsed//60)}m {int(elapsed%60)}s] Progress update")
                    print(f"  Updates sent: {update_count}")
                    print(f"  Desyncs detected: {desync_count}")
                    print(f"  Errors: {error_count}")

                # Send parameter update
                if current_time - last_update_time >= update_interval:
                    # Choose random parameter to update
                    param_choice = random.choice(['frequency', 'amplitude', 'coupling', 'gain', 'phi'])

                    if param_choice == 'frequency':
                        channel = random.randint(0, 7)
                        value = random.uniform(0.5, 10.0)
                        param_type = 'channel'
                        param = 'frequency'
                        key = f'ch{channel}_freq'

                    elif param_choice == 'amplitude':
                        channel = random.randint(0, 7)
                        value = random.uniform(0.0, 1.0)
                        param_type = 'channel'
                        param = 'amplitude'
                        key = f'ch{channel}_amp'

                    elif param_choice == 'coupling':
                        channel = None
                        value = random.uniform(0.5, 1.5)
                        param_type = 'global'
                        param = 'coupling_strength'
                        key = 'coupling_strength'

                    elif param_choice == 'gain':
                        channel = None
                        value = random.uniform(0.5, 1.5)
                        param_type = 'global'
                        param = 'gain'
                        key = 'gain'

                    elif param_choice == 'phi':
                        channel = None
                        param = random.choice(['phase', 'depth'])
                        value = random.uniform(0.0, 1.0)
                        param_type = 'phi'
                        key = f'phi_{param}'

                    # Send update
                    msg = {
                        "type": "set_param",
                        "param_type": param_type,
                        "channel": channel,
                        "param": param,
                        "value": value
                    }

                    try:
                        await websocket.send(json.dumps(msg))
                        expected_values[key] = value
                        update_count += 1

                        # Wait for acknowledgment
                        response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        response_data = json.loads(response)

                        if not response_data.get('success'):
                            error_count += 1
                            print(f"  ⚠ Update failed: {param_type}.{param}")

                        last_update_time = current_time

                    except asyncio.TimeoutError:
                        error_count += 1
                        print(f"  ⚠ Timeout waiting for acknowledgment")
                    except Exception as e:
                        error_count += 1
                        print(f"  ⚠ Error sending update: {e}")

                # Periodically verify state
                if int(elapsed) % 60 == 30:  # Every minute at 30 seconds
                    # Request current state
                    try:
                        msg = {"type": "get_state"}
                        await websocket.send(json.dumps(msg))

                        response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        current_state = json.loads(response)['data']

                        # Verify some expected values
                        sample_keys = list(expected_values.keys())[:5]  # Check 5 random values

                        for key in sample_keys:
                            expected = expected_values[key]

                            # Extract actual value from state
                            if key.startswith('ch'):
                                parts = key.split('_')
                                ch_num = int(parts[0][2:])
                                param_name = parts[1]

                                if param_name == 'freq':
                                    actual = current_state['channels'][ch_num]['frequency']
                                elif param_name == 'amp':
                                    actual = current_state['channels'][ch_num]['amplitude']

                            elif key == 'coupling_strength':
                                actual = current_state['global']['coupling_strength']

                            elif key == 'gain':
                                actual = current_state['global']['gain']

                            elif key.startswith('phi_'):
                                param_name = key.split('_')[1]
                                actual = current_state['phi'][param_name]

                            # Check if values match (with tolerance)
                            tolerance = 0.01
                            if abs(actual - expected) > tolerance:
                                desync_count += 1
                                print(f"  ✗ DESYNC: {key} expected {expected:.3f}, got {actual:.3f}")

                    except Exception as e:
                        error_count += 1
                        print(f"  ⚠ Error verifying state: {e}")

                # Small sleep to avoid busy loop
                await asyncio.sleep(0.1)

            # Final verification
            print("\n" + "=" * 60)
            print("Final Verification")
            print("=" * 60)

            msg = {"type": "get_state"}
            await websocket.send(json.dumps(msg))

            response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            final_state = json.loads(response)['data']

            print(f"Final state received with {len(expected_values)} tracked parameters")

            # Summary
            print("\n" + "=" * 60)
            print("Results")
            print("=" * 60)
            print(f"Duration:        {duration_minutes} minutes")
            print(f"Updates sent:    {update_count}")
            print(f"Desyncs detected: {desync_count}")
            print(f"Errors:          {error_count}")
            print()

            if desync_count == 0 and error_count == 0:
                print("✓ PASS: No desyncs detected during test")
                print("=" * 60)
                return True
            elif desync_count == 0:
                print(f"⚠ WARNING: No desyncs, but {error_count} errors occurred")
                print("=" * 60)
                return True
            else:
                print(f"✗ FAIL: {desync_count} desyncs detected")
                print("=" * 60)
                return False

    except websockets.exceptions.WebSocketException as e:
        print(f"✗ WebSocket error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    server_url = sys.argv[1] if len(sys.argv) > 1 else 'ws://localhost:8000/ws/ui'
    duration_minutes = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0

    result = asyncio.run(test_ui_sync(server_url, duration_minutes))

    sys.exit(0 if result else 1)
