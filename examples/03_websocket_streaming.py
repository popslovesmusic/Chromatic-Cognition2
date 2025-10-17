#!/usr/bin/env python3
"""
Example 03: WebSocket Metrics Streaming

Demonstrates real-time metrics streaming via WebSocket:
- Connect to metrics stream
- Process real-time metrics (30 Hz)
- Monitor Φ-depth, criticality, ICI
- Handle state changes

Usage:
    python examples/03_websocket_streaming.py

Requirements:
    pip install websockets
"""

import asyncio
import websockets
import json
import os
from datetime import datetime
from typing import Dict, Any


class MetricsStreamClient:
    """WebSocket client for real-time metrics streaming"""

    def __init__(self, ws_url: str = "ws://localhost:8000"):
        self.ws_url = ws_url.rstrip('/')
        self.metrics_url = f"{self.ws_url}/ws/metrics"
        self.running = False
        self.frame_count = 0
        self.start_time = None

    async def connect_and_stream(self, duration: int = 10):
        """Connect to metrics stream and process frames"""
        print(f"Connecting to {self.metrics_url}...")

        try:
            async with websockets.connect(self.metrics_url) as websocket:
                print("✓ Connected to metrics stream")
                print(f"Streaming for {duration} seconds...\n")

                self.running = True
                self.start_time = datetime.now()
                end_time = asyncio.get_event_loop().time() + duration

                while self.running and asyncio.get_event_loop().time() < end_time:
                    try:
                        # Wait for next message
                        message = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=1.0
                        )

                        # Parse JSON
                        data = json.loads(message)
                        self.process_frame(data)

                    except asyncio.TimeoutError:
                        continue
                    except json.JSONDecodeError as e:
                        print(f"✗ JSON decode error: {e}")
                        continue

                print("\n✓ Stream ended")
                self.print_summary()

        except websockets.exceptions.WebSocketException as e:
            print(f"✗ WebSocket error: {e}")
        except Exception as e:
            print(f"✗ Unexpected error: {e}")

    def process_frame(self, data: Dict[str, Any]):
        """Process a single metrics frame"""
        self.frame_count += 1

        # Extract key metrics
        frame_num = data.get('frame', 0)
        ici = data.get('ici', 0.0)
        criticality = data.get('criticality', 0.0)
        coherence = data.get('phase_coherence', 0.0)
        phi_depth = data.get('phi_depth', 0.0)
        phi_phase = data.get('phi_phase', 0.0)

        # Print every 30th frame (approximately once per second at 30 Hz)
        if self.frame_count % 30 == 0:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            fps = self.frame_count / elapsed if elapsed > 0 else 0

            print(f"[{elapsed:6.2f}s] Frame {frame_num:6d} | "
                  f"ICI: {ici:6.3f} | "
                  f"Crit: {criticality:6.3f} | "
                  f"Coh: {coherence:6.3f} | "
                  f"Φ: {phi_depth:6.3f}∠{phi_phase:6.3f} | "
                  f"FPS: {fps:5.1f}")

        # Detect interesting events
        self.detect_events(data)

    def detect_events(self, data: Dict[str, Any]):
        """Detect and print interesting events"""
        criticality = data.get('criticality', 0.0)
        ici = data.get('ici', 0.0)

        # High criticality
        if criticality > 2.5:
            print(f"  ⚡ HIGH CRITICALITY: {criticality:.3f}")

        # Critical ICI
        if ici > 0.9:
            print(f"  🎯 CRITICAL ICI: {ici:.3f}")

        # State changes (if present)
        if 'state_change' in data:
            state = data['state_change']
            print(f"  🔄 STATE CHANGE: {state.get('from_state')} → {state.get('to_state')}")

    def print_summary(self):
        """Print streaming summary"""
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            avg_fps = self.frame_count / duration if duration > 0 else 0

            print("\n" + "=" * 70)
            print("Stream Summary")
            print("=" * 70)
            print(f"Duration: {duration:.2f}s")
            print(f"Total frames: {self.frame_count}")
            print(f"Average FPS: {avg_fps:.1f}")
            print("=" * 70)


async def main():
    """Main async entry point"""
    print("=" * 70)
    print("Soundlab WebSocket Metrics Streaming Example")
    print("=" * 70)

    # Get WebSocket URL from environment or use default
    ws_url = os.getenv('SOUNDLAB_WS_URL', 'ws://localhost:8000')
    print(f"\nWebSocket URL: {ws_url}\n")

    # Create client
    client = MetricsStreamClient(ws_url)

    # Stream for 10 seconds
    await client.connect_and_stream(duration=10)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n✓ Interrupted by user")
