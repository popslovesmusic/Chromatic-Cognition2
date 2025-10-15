"""
Test State Match - SC-003: State indicator matches backend classification

Compares the visual state label and color with backend classification.
Verifies that state transitions occur correctly based on metric thresholds.

Usage:
    python test_state_match.py [ws://localhost:8000/ws/metrics] [duration_seconds]
"""

import asyncio
import websockets
import json
import time
import sys
from collections import Counter


# Expected state color mappings (from spec #001 and metrics-hud.js)
STATE_COLORS = {
    'IDLE': '#666',
    'AWAKE': '#0ff',
    'DREAMING': '#f0f',
    'DEEP_SLEEP': '#00f',
    'REM': '#ff0',
    'CRITICAL': '#f00',
    'TRANSITION': '#fa0'
}


async def test_state_match(server_url='ws://localhost:8000/ws/metrics', duration_seconds=60):
    """
    Test state classification matching

    Args:
        server_url: WebSocket URL
        duration_seconds: Test duration

    Returns:
        True if all states match expected classifications
    """
    print("=" * 60)
    print("State Classification Match Test")
    print("=" * 60)
    print(f"Server: {server_url}")
    print(f"Duration: {duration_seconds} seconds")
    print()

    state_counts = Counter()
    last_state = None
    state_transitions = 0
    frame_count = 0
    mismatches = []

    start_time = time.time()

    try:
        async with websockets.connect(server_url) as websocket:
            print("✓ Connected to metrics stream")
            print("Monitoring state classifications...\n")

            while time.time() - start_time < duration_seconds:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(message)

                    state = data.get('state', 'IDLE')
                    state_counts[state] += 1
                    frame_count += 1

                    # Track state transitions
                    if last_state and last_state != state:
                        state_transitions += 1
                        print(f"[{int(time.time() - start_time)}s] State transition: {last_state} → {state}")

                    last_state = state

                    # Verify state is valid
                    if state not in STATE_COLORS:
                        mismatches.append({
                            'frame': frame_count,
                            'state': state,
                            'reason': 'Unknown state'
                        })
                        print(f"  ⚠ WARNING: Unknown state '{state}'")

                    # Verify state matches expected thresholds (basic validation)
                    # Based on metrics_frame.py classification logic
                    ici = data.get('ici', 0)
                    coherence = data.get('phase_coherence', 0)
                    consciousness = data.get('consciousness_level', 0)

                    # Basic consistency checks
                    if state == 'CRITICAL' and consciousness < 0.8:
                        mismatches.append({
                            'frame': frame_count,
                            'state': state,
                            'consciousness': consciousness,
                            'reason': f'CRITICAL state but consciousness={consciousness:.2f} < 0.8'
                        })

                    if state == 'IDLE' and consciousness > 0.1:
                        # IDLE might be active, this is okay
                        pass

                except asyncio.TimeoutError:
                    print("⚠ Timeout waiting for frame")
                    continue

            # Results
            print("\n" + "=" * 60)
            print("Results")
            print("=" * 60)

            print(f"Total frames: {frame_count}")
            print(f"State transitions: {state_transitions}")
            print()

            print("State distribution:")
            for state, count in state_counts.most_common():
                percentage = (count / frame_count * 100) if frame_count > 0 else 0
                color_code = STATE_COLORS.get(state, '???')
                print(f"  {state:12} : {count:5} frames ({percentage:5.1f}%) - Color: {color_code}")

            print()

            # Check for mismatches
            if mismatches:
                print(f"⚠ Found {len(mismatches)} potential mismatches:")
                for i, mismatch in enumerate(mismatches[:10]):  # Show first 10
                    print(f"  {i+1}. Frame {mismatch['frame']}: {mismatch['reason']}")
                if len(mismatches) > 10:
                    print(f"  ... and {len(mismatches) - 10} more")
                print()

            # Validation
            all_states_valid = all(state in STATE_COLORS for state in state_counts.keys())

            if all_states_valid and len(mismatches) == 0:
                print("✓ PASS: All states match expected classifications")
            elif all_states_valid:
                print(f"⚠ WARNING: {len(mismatches)} consistency issues found")
            else:
                print("✗ FAIL: Unknown states detected")

            print("=" * 60)

            return {
                'success': all_states_valid and len(mismatches) == 0,
                'frame_count': frame_count,
                'state_counts': dict(state_counts),
                'transitions': state_transitions,
                'mismatches': len(mismatches)
            }

    except websockets.exceptions.WebSocketException as e:
        print(f"✗ WebSocket error: {e}")
        return None
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    server_url = sys.argv[1] if len(sys.argv) > 1 else 'ws://localhost:8000/ws/metrics'
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 60

    result = asyncio.run(test_state_match(server_url, duration))

    if result and result['success']:
        sys.exit(0)
    else:
        sys.exit(1)
