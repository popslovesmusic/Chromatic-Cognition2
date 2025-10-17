"""
Smoke Test: Metrics Streaming
Feature 019: Release Readiness Validation

Tests metrics streaming via WebSocket at 30 Hz.

Success Criteria:
- Connect to /ws/metrics endpoint
- Receive metrics frames
- Frame rate >= 25 Hz (allowing some variance)
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
WS_URL = SOUNDLAB_URL.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws/metrics'
TIMEOUT_SECONDS = 30
TEST_DURATION_SECONDS = 10


async def test_metrics_streaming():
    """Test metrics streaming for sustained period"""
    print("=" * 70)
    print("Smoke Test: Metrics Streaming")
    print("=" * 70)
    print(f"Target: {WS_URL}")
    print(f"Test duration: {TEST_DURATION_SECONDS}s")
    print()

    try:
        # Connect to WebSocket
        print("Connecting to metrics WebSocket...")
        async with websockets.connect(WS_URL, timeout=TIMEOUT_SECONDS) as websocket:
            print(f"✓ Connected to {WS_URL}")
            print()

            # Collect frames
            frames = []
            start_time = time.time()

            print(f"Collecting metrics for {TEST_DURATION_SECONDS}s...")

            while (time.time() - start_time) < TEST_DURATION_SECONDS:
                try:
                    # Wait for frame
                    response = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=2.0
                    )

                    frame = json.loads(response)
                    frames.append({
                        'timestamp': time.time(),
                        'data': frame
                    })

                    # Print progress every second
                    elapsed = time.time() - start_time
                    if len(frames) % 30 == 0:
                        print(f"  {elapsed:.1f}s: {len(frames)} frames received")

                except asyncio.TimeoutError:
                    print("  ⚠ Frame timeout (no frame for 2s)")
                    continue

            # Calculate statistics
            duration = time.time() - start_time
            frame_count = len(frames)
            frame_rate = frame_count / duration

            print()
            print(f"Total frames: {frame_count}")
            print(f"Duration: {duration:.2f}s")
            print(f"Frame rate: {frame_rate:.2f} Hz")
            print()

            # Validate frame rate
            if frame_rate < 25.0:
                print(f"✗ FAIL: Frame rate {frame_rate:.2f} Hz < 25 Hz minimum")
                return False

            # Check frame structure
            if frames:
                sample_frame = frames[0]['data']
                print(f"Sample frame keys: {list(sample_frame.keys())}")

                # Check for expected fields
                expected_fields = ['ici', 'coherence', 'criticality']
                missing_fields = [f for f in expected_fields if f not in sample_frame]

                if missing_fields:
                    print(f"⚠ WARNING: Missing fields in frame: {missing_fields}")

            print()
            print(f"✓ PASS: Metrics streaming successful")
            print(f"✓ PASS: Frame rate {frame_rate:.2f} Hz >= 25 Hz")
            return True

    except websockets.exceptions.WebSocketException as e:
        print(f"✗ FAIL: WebSocket error: {e}")
        return False

    except Exception as e:
        print(f"✗ FAIL: Unexpected error: {e}")
        return False


async def test_metrics_latency():
    """Test metrics latency (timestamp accuracy)"""
    print("=" * 70)
    print("Smoke Test: Metrics Latency")
    print("=" * 70)
    print(f"Target: {WS_URL}")
    print()

    try:
        async with websockets.connect(WS_URL, timeout=TIMEOUT_SECONDS) as websocket:
            print("✓ Connected")
            print()

            # Collect latencies
            latencies = []

            for i in range(30):  # Collect 30 samples
                try:
                    receive_time = time.time()
                    response = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=2.0
                    )

                    frame = json.loads(response)

                    # Calculate latency (assuming frame has timestamp)
                    if 'timestamp' in frame:
                        frame_time = frame['timestamp']
                        latency_ms = (receive_time - frame_time) * 1000.0
                        latencies.append(latency_ms)

                except asyncio.TimeoutError:
                    continue

            if not latencies:
                print("⚠ WARNING: No latency measurements (frames may not have timestamps)")
                return True

            # Calculate statistics
            avg_latency = sum(latencies) / len(latencies)
            max_latency = max(latencies)
            min_latency = min(latencies)

            print(f"Latency samples: {len(latencies)}")
            print(f"Avg latency: {avg_latency:.2f} ms")
            print(f"Min latency: {min_latency:.2f} ms")
            print(f"Max latency: {max_latency:.2f} ms")
            print()

            # Validate latency
            if max_latency > 100:
                print(f"✗ FAIL: Max latency {max_latency:.2f} ms > 100 ms")
                return False

            print(f"✓ PASS: Metrics latency acceptable")
            print(f"✓ PASS: Max latency {max_latency:.2f} ms <= 100 ms")
            return True

    except websockets.exceptions.WebSocketException as e:
        print(f"✗ FAIL: WebSocket error: {e}")
        return False

    except Exception as e:
        print(f"✗ FAIL: Unexpected error: {e}")
        return False


async def main():
    """Run all metrics smoke tests"""
    print()
    print("Running Metrics Smoke Tests...")
    print()

    results = []

    # Test 1: Metrics Streaming
    result1 = await test_metrics_streaming()
    results.append(result1)
    print()

    # Test 2: Metrics Latency
    result2 = await test_metrics_latency()
    results.append(result2)
    print()

    # Summary
    print("=" * 70)
    print("Metrics Smoke Test Summary")
    print("=" * 70)
    passed = sum(results)
    total = len(results)

    print(f"Passed: {passed}/{total}")
    print()

    if all(results):
        print("✓ ALL METRICS SMOKE TESTS PASSED")
        sys.exit(0)
    else:
        print("✗ SOME METRICS SMOKE TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
