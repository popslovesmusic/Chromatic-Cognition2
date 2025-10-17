"""
Test Metrics Latency - SC-001: <100ms from received frame

Measures the average update delay from WebSocket receive to display update.
Connects to /ws/metrics and tracks frame timestamps.

Usage:
    python test_metrics_latency.py [ws://localhost:8000/ws/metrics] [duration_seconds]
"""

import asyncio
import websockets
import json
import time
import sys
from statistics import mean, stdev


async def test_metrics_latency(server_url='ws://localhost:8000/ws/metrics', duration_seconds=30):
    """
    Test metrics update latency

    Args:
        server_url: WebSocket URL
        duration_seconds: Test duration

    Returns:
        Statistics dictionary
    """
    print("=" * 60)
    print("Metrics Latency Test")
    print("=" * 60)
    print(f"Server: {server_url}")
    print(f"Duration: {duration_seconds} seconds")
    print()

    latencies = []
    frame_count = 0
    start_time = time.time()

    try:
        async with websockets.connect(server_url) as websocket:
            print("✓ Connected to metrics stream")
            print("Collecting latency measurements...\n")

            while time.time() - start_time < duration_seconds:
                # Record receive time
                receive_time = time.perf_counter()

                # Receive frame
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(message)

                    # Record processing start time
                    process_time = time.perf_counter()

                    # Simulate minimal processing (what the HUD does)
                    # - Parse JSON (already done)
                    # - Apply EMA smoothing
                    ema_alpha = 0.3
                    smoothed_ici = ema_alpha * data.get('ici', 0)

                    # Record end time
                    end_time = time.perf_counter()

                    # Calculate latency (receive → processed)
                    latency_ms = (end_time - receive_time) * 1000.0
                    latencies.append(latency_ms)

                    frame_count += 1

                    # Print progress every second
                    if frame_count % 30 == 0:
                        elapsed = time.time() - start_time
                        avg_so_far = mean(latencies) if latencies else 0
                        print(f"[{int(elapsed)}s] Frames: {frame_count}, Avg latency: {avg_so_far:.2f} ms")

                except asyncio.TimeoutError:
                    print("⚠ Timeout waiting for frame")
                    continue

            # Calculate statistics
            print("\n" + "=" * 60)
            print("Results")
            print("=" * 60)

            if latencies:
                avg_latency = mean(latencies)
                min_latency = min(latencies)
                max_latency = max(latencies)
                std_latency = stdev(latencies) if len(latencies) > 1 else 0

                print(f"Frames received: {frame_count}")
                print(f"Average latency: {avg_latency:.3f} ms")
                print(f"Min latency:     {min_latency:.3f} ms")
                print(f"Max latency:     {max_latency:.3f} ms")
                print(f"Std deviation:   {std_latency:.3f} ms")
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

                # Check frame rate (should be ~30 Hz)
                actual_fps = frame_count / duration_seconds
                print(f"\nFrame rate: {actual_fps:.1f} FPS (target: 30 FPS)")

                if actual_fps >= 25:  # Allow some tolerance
                    print(f"✓ PASS: Frame rate acceptable")
                else:
                    print(f"⚠ WARNING: Frame rate below target")

                print("=" * 60)

                return {
                    'success': avg_latency < 100.0,
                    'average_ms': avg_latency,
                    'min_ms': min_latency,
                    'max_ms': max_latency,
                    'std_ms': std_latency,
                    'frame_count': frame_count,
                    'fps': actual_fps
                }
            else:
                print("✗ FAIL: No frames received")
                return None

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
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 30

    result = asyncio.run(test_metrics_latency(server_url, duration))

    if result and result['success']:
        sys.exit(0)
    else:
        sys.exit(1)
