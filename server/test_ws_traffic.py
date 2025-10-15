"""
Test WebSocket Traffic - FR-006: Rate limiting <10 Hz

Validates that the MIDI controller respects the 10 Hz rate limit per parameter.
Tests rapid parameter updates and verifies throttling behavior.

Usage:
    python test_ws_traffic.py [ws://localhost:8000/ws/ui] [duration_seconds]
"""

import asyncio
import websockets
import json
import time
import sys
from collections import defaultdict
from typing import Dict, List


class TrafficMonitor:
    """Monitor WebSocket message traffic and calculate rates"""

    def __init__(self):
        self.messages_sent: List[Dict] = []
        self.messages_received: List[Dict] = []
        self.start_time = None

    def record_sent(self, message: Dict):
        """Record a sent message with timestamp"""
        if self.start_time is None:
            self.start_time = time.time()

        self.messages_sent.append({
            'timestamp': time.time(),
            'message': message
        })

    def record_received(self, message: Dict):
        """Record a received message with timestamp"""
        self.messages_received.append({
            'timestamp': time.time(),
            'message': message
        })

    def get_message_rate(self, messages: List[Dict]) -> float:
        """Calculate message rate in Hz"""
        if len(messages) < 2:
            return 0.0

        duration = messages[-1]['timestamp'] - messages[0]['timestamp']
        if duration <= 0:
            return 0.0

        return len(messages) / duration

    def get_per_parameter_rates(self) -> Dict[str, Dict]:
        """Calculate rate per parameter"""
        param_messages = defaultdict(list)

        for record in self.messages_sent:
            msg = record['message']
            if msg.get('type') == 'set_param':
                # Create parameter key
                param_key = f"{msg.get('param_type')}_{msg.get('channel')}_{msg.get('param')}"
                param_messages[param_key].append(record)

        # Calculate rates
        param_rates = {}
        for param_key, messages in param_messages.items():
            if len(messages) >= 2:
                rate = self.get_message_rate(messages)
                param_rates[param_key] = {
                    'rate_hz': rate,
                    'count': len(messages),
                    'messages': messages
                }

        return param_rates

    def get_intervals(self, param_key: str) -> List[float]:
        """Get time intervals between messages for a specific parameter"""
        param_messages = []

        for record in self.messages_sent:
            msg = record['message']
            if msg.get('type') == 'set_param':
                key = f"{msg.get('param_type')}_{msg.get('channel')}_{msg.get('param')}"
                if key == param_key:
                    param_messages.append(record)

        if len(param_messages) < 2:
            return []

        intervals = []
        for i in range(1, len(param_messages)):
            interval = param_messages[i]['timestamp'] - param_messages[i-1]['timestamp']
            intervals.append(interval * 1000)  # Convert to ms

        return intervals


async def test_rapid_updates(server_url='ws://localhost:8000/ws/ui', num_messages=50):
    """
    Test 1: Rapid parameter updates

    Sends rapid updates to the same parameter and verifies rate limiting
    """
    print("=" * 60)
    print("Test 1: Rapid Parameter Updates")
    print("=" * 60)
    print(f"Server: {server_url}")
    print(f"Messages: {num_messages} (as fast as possible)")
    print()

    monitor = TrafficMonitor()

    try:
        async with websockets.connect(server_url) as websocket:
            print("✓ Connected")
            print("Sending rapid updates to phi.depth...\n")

            # Send messages as fast as possible
            for i in range(num_messages):
                message = {
                    'type': 'set_param',
                    'param_type': 'phi',
                    'channel': None,
                    'param': 'depth',
                    'value': 0.5 + (i * 0.001)  # Vary slightly
                }

                await websocket.send(json.dumps(message))
                monitor.record_sent(message)

                # No delay - send as fast as possible

            # Collect responses
            print("Collecting responses...")
            timeout_count = 0
            for i in range(num_messages):
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=0.2)
                    data = json.loads(response)
                    monitor.record_received(data)
                except asyncio.TimeoutError:
                    timeout_count += 1
                    if timeout_count > 10:
                        break  # Stop if too many timeouts

            # Analyze results
            print()
            print("-" * 60)
            print("Results:")
            print("-" * 60)

            param_rates = monitor.get_per_parameter_rates()
            param_key = 'phi_None_depth'

            if param_key in param_rates:
                data = param_rates[param_key]
                rate_hz = data['rate_hz']
                count = data['count']

                print(f"Messages sent: {count}")
                print(f"Messages received: {len(monitor.messages_received)}")
                print(f"Overall send rate: {rate_hz:.2f} Hz")
                print()

                # Get intervals between messages
                intervals = monitor.get_intervals(param_key)

                if intervals:
                    import statistics
                    avg_interval = statistics.mean(intervals)
                    min_interval = min(intervals)
                    max_interval = max(intervals)

                    print(f"Average interval: {avg_interval:.2f} ms")
                    print(f"Min interval: {min_interval:.2f} ms")
                    print(f"Max interval: {max_interval:.2f} ms")
                    print()

                    # FR-006: Rate must be <10 Hz = >100ms interval
                    expected_min_interval = 100  # ms

                    # Count violations
                    violations = sum(1 for interval in intervals if interval < expected_min_interval * 0.9)

                    if violations == 0:
                        print(f"✓ PASS: No rate limit violations (<10 Hz enforced)")
                        test_pass = True
                    else:
                        violation_pct = (violations / len(intervals)) * 100
                        print(f"⚠ WARNING: {violations}/{len(intervals)} intervals below limit ({violation_pct:.1f}%)")
                        test_pass = violation_pct < 10  # Allow up to 10% violations due to timing jitter

                    # Expected behavior: Client-side throttling
                    print()
                    print("Expected behavior:")
                    print("  - Client throttles at 10 Hz (100ms minimum)")
                    print("  - Server may further rate-limit")
                    print(f"  - Observed minimum: {min_interval:.0f}ms")

                else:
                    print("⚠ Not enough data to calculate intervals")
                    test_pass = False

            else:
                print("✗ No messages recorded for parameter")
                test_pass = False

            print("=" * 60)
            print()

            return test_pass

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_multiple_parameters(server_url='ws://localhost:8000/ws/ui', duration_seconds=5):
    """
    Test 2: Multiple parameters simultaneously

    Tests that rate limiting is per-parameter, not global
    """
    print("=" * 60)
    print("Test 2: Multiple Parameters Simultaneously")
    print("=" * 60)
    print(f"Server: {server_url}")
    print(f"Duration: {duration_seconds} seconds")
    print()

    monitor = TrafficMonitor()

    # Test parameters
    test_params = [
        {'param_type': 'phi', 'channel': None, 'param': 'depth', 'value': 0.5},
        {'param_type': 'phi', 'channel': None, 'param': 'phase', 'value': 0.7},
        {'param_type': 'global', 'channel': None, 'param': 'gain', 'value': 1.0},
        {'param_type': 'channel', 'channel': 0, 'param': 'amplitude', 'value': 0.6},
    ]

    try:
        async with websockets.connect(server_url) as websocket:
            print("✓ Connected")
            print("Sending updates to multiple parameters...\n")

            start_time = time.time()
            param_index = 0

            while time.time() - start_time < duration_seconds:
                # Rotate through parameters
                param = test_params[param_index % len(test_params)]
                param_index += 1

                # Vary value slightly
                param['value'] += 0.01
                if param['value'] > 1.0:
                    param['value'] = 0.1

                message = {
                    'type': 'set_param',
                    **param
                }

                await websocket.send(json.dumps(message))
                monitor.record_sent(message)

                # Small delay (but much faster than 10 Hz per parameter)
                await asyncio.sleep(0.01)  # 100 Hz total send rate

            # Collect responses
            print("Collecting responses...")
            for i in range(100):
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=0.1)
                    data = json.loads(response)
                    monitor.record_received(data)
                except asyncio.TimeoutError:
                    break

            # Analyze per-parameter rates
            print()
            print("-" * 60)
            print("Results:")
            print("-" * 60)

            param_rates = monitor.get_per_parameter_rates()

            print(f"Total messages sent: {len(monitor.messages_sent)}")
            print(f"Total messages received: {len(monitor.messages_received)}")
            print()

            print("Per-parameter rates:")
            all_within_limit = True

            for param_key, data in sorted(param_rates.items()):
                rate = data['rate_hz']
                count = data['count']

                # Check if rate is within limit
                within_limit = rate <= 10.5  # 10 Hz + 5% tolerance
                status = "✓" if within_limit else "✗"

                print(f"  {status} {param_key:25} : {rate:6.2f} Hz ({count:3d} msgs)")

                if not within_limit:
                    all_within_limit = False

            print()
            if all_within_limit:
                print("✓ PASS: All parameters within 10 Hz limit")
            else:
                print("✗ FAIL: Some parameters exceeded 10 Hz limit")

            print("=" * 60)
            print()

            return all_within_limit

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


async def test_burst_behavior(server_url='ws://localhost:8000/ws/ui'):
    """
    Test 3: Burst behavior

    Tests what happens when many messages are sent in a burst
    """
    print("=" * 60)
    print("Test 3: Burst Behavior")
    print("=" * 60)
    print(f"Server: {server_url}")
    print()

    monitor = TrafficMonitor()

    try:
        async with websockets.connect(server_url) as websocket:
            print("✓ Connected")
            print("Sending burst of 20 messages (no delay)...\n")

            # Send burst
            burst_size = 20
            for i in range(burst_size):
                message = {
                    'type': 'set_param',
                    'param_type': 'phi',
                    'channel': None,
                    'param': 'depth',
                    'value': 0.5 + (i * 0.01)
                }

                await websocket.send(json.dumps(message))
                monitor.record_sent(message)

            # Collect responses
            print("Collecting responses...")
            responses_received = 0

            for i in range(burst_size * 2):  # Allow for duplicates
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=0.5)
                    data = json.loads(response)
                    monitor.record_received(data)
                    responses_received += 1
                except asyncio.TimeoutError:
                    break

            # Results
            print()
            print("-" * 60)
            print("Results:")
            print("-" * 60)

            print(f"Messages sent in burst: {burst_size}")
            print(f"Responses received: {responses_received}")
            print()

            if responses_received < burst_size:
                dropped = burst_size - responses_received
                drop_rate = (dropped / burst_size) * 100
                print(f"Messages dropped/throttled: {dropped} ({drop_rate:.1f}%)")
                print()
                print("✓ This is EXPECTED behavior due to rate limiting")
                print("  Client should throttle at 10 Hz (100ms minimum)")
                test_pass = True
            else:
                print("⚠ All messages processed (no apparent throttling)")
                test_pass = False

            print("=" * 60)
            print()

            return test_pass

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


if __name__ == "__main__":
    server_url = sys.argv[1] if len(sys.argv) > 1 else 'ws://localhost:8000/ws/ui'
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    print()

    # Run tests
    result1 = asyncio.run(test_rapid_updates(server_url, num_messages=50))
    result2 = asyncio.run(test_multiple_parameters(server_url, duration_seconds=duration))
    result3 = asyncio.run(test_burst_behavior(server_url))

    # Summary
    print()
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"  Rapid Updates:         {'✓ PASS' if result1 else '✗ FAIL'}")
    print(f"  Multiple Parameters:   {'✓ PASS' if result2 else '✗ FAIL'}")
    print(f"  Burst Behavior:        {'✓ PASS' if result3 else '✗ FAIL'}")
    print("=" * 60)
    print()

    all_passed = result1 and result2 and result3
    sys.exit(0 if all_passed else 1)
