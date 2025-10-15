"""
MetricsStreamer - Real-Time WebSocket Metrics Broadcaster

Implements FR-001 through FR-006:
- WebSocket server at /ws/metrics
- ≥30 Hz broadcast rate
- Multi-client support (≥5 concurrent)
- Frame buffering with <100ms latency
- REST endpoint /api/metrics/latest
- Graceful reconnection handling
"""

import asyncio
import json
import time
from typing import Set, Optional, Dict
from collections import deque
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import logging

from metrics_frame import MetricsFrame, create_idle_frame
from metrics_logger import MetricsLogger


class MetricsStreamer:
    """
    WebSocket-based metrics broadcaster

    Manages multiple client connections and broadcasts metrics at ≥30 Hz
    """

    TARGET_FPS = 30  # FR-003: ≥30 Hz
    FRAME_INTERVAL = 1.0 / TARGET_FPS  # 0.033 seconds
    MAX_BUFFER_SIZE = 2  # FR-004: Buffer ≤2 frames
    MAX_CLIENTS = 10  # Support more than minimum 5

    def __init__(self,
                 enable_logging: bool = True,
                 log_dir: Optional[str] = None,
                 session_name: Optional[str] = None):
        """
        Initialize metrics streamer

        Args:
            enable_logging: Enable session logging to disk
            log_dir: Log directory (None = logs/metrics/)
            session_name: Session identifier (None = timestamp)
        """
        # WebSocket clients
        self.active_connections: Set[WebSocket] = set()
        self.connection_count = 0

        # Frame buffering
        self.frame_buffer = deque(maxlen=self.MAX_BUFFER_SIZE)
        self.latest_frame: Optional[MetricsFrame] = None
        self.frame_counter = 0

        # Broadcasting control
        self.broadcasting = False
        self.broadcast_task = None
        self.last_broadcast_time = 0.0

        # Session logging
        self.logger: Optional[MetricsLogger] = None
        if enable_logging:
            self.logger = MetricsLogger(
                log_dir=log_dir,
                session_name=session_name
            )

        # Statistics
        self.stats = {
            'total_frames_sent': 0,
            'total_bytes_sent': 0,
            'dropped_frames': 0,
            'avg_latency_ms': 0.0,
            'clients_connected': 0,
            'clients_disconnected': 0,
        }

        # Logging
        self.log = logging.getLogger(__name__)
        self.log.setLevel(logging.INFO)

        print("[MetricsStreamer] Initialized")

    async def connect(self, websocket: WebSocket):
        """
        Connect a new WebSocket client

        Args:
            websocket: FastAPI WebSocket connection

        Raises:
            RuntimeError: If max clients exceeded
        """
        if len(self.active_connections) >= self.MAX_CLIENTS:
            await websocket.close(code=1008, reason="Max clients reached")
            raise RuntimeError(f"Max clients ({self.MAX_CLIENTS}) exceeded")

        await websocket.accept()
        self.active_connections.add(websocket)
        self.connection_count += 1
        self.stats['clients_connected'] += 1

        client_id = id(websocket)
        self.log.info(f"Client {client_id} connected. Total: {len(self.active_connections)}")

        # Send current state immediately
        if self.latest_frame:
            try:
                await websocket.send_text(self.latest_frame.to_json())
            except:
                pass

    async def disconnect(self, websocket: WebSocket):
        """
        Disconnect a WebSocket client

        Args:
            websocket: Client to disconnect
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.stats['clients_disconnected'] += 1

            client_id = id(websocket)
            self.log.info(f"Client {client_id} disconnected. Remaining: {len(self.active_connections)}")

    def submit_frame(self, frame: MetricsFrame):
        """
        Submit a new metrics frame for broadcasting

        Called from audio callback thread (must be thread-safe)

        Args:
            frame: MetricsFrame to broadcast
        """
        # Validate and sanitize
        frame.sanitize()
        frame.frame_id = self.frame_counter
        self.frame_counter += 1

        # Update latest frame
        self.latest_frame = frame

        # Add to buffer (deque is thread-safe for single producer/consumer)
        self.frame_buffer.append(frame)

        # Log to disk if enabled
        if self.logger:
            self.logger.log_frame(frame)

    async def broadcast_frame(self, frame: MetricsFrame):
        """
        Broadcast frame to all connected clients

        Args:
            frame: Frame to broadcast
        """
        if not self.active_connections:
            return

        json_data = frame.to_json()
        data_size = len(json_data)

        # Broadcast to all clients
        disconnected_clients = set()

        for websocket in self.active_connections:
            try:
                await websocket.send_text(json_data)
                self.stats['total_bytes_sent'] += data_size
            except WebSocketDisconnect:
                disconnected_clients.add(websocket)
            except Exception as e:
                self.log.error(f"Error sending to client {id(websocket)}: {e}")
                disconnected_clients.add(websocket)

        # Remove disconnected clients
        for ws in disconnected_clients:
            await self.disconnect(ws)

        self.stats['total_frames_sent'] += 1

    async def broadcast_loop(self):
        """
        Main broadcasting loop (runs as async task)

        Broadcasts at ≥30 Hz from frame buffer
        """
        self.log.info("Broadcast loop started")
        self.broadcasting = True

        idle_frame_timer = 0.0
        last_time = time.time()

        while self.broadcasting:
            current_time = time.time()
            dt = current_time - last_time
            last_time = current_time

            # Check if we have frames to broadcast
            if self.frame_buffer:
                frame = self.frame_buffer.popleft()

                # Calculate latency
                if frame.timestamp > 0:
                    latency_ms = (current_time - frame.timestamp) * 1000
                    self.stats['avg_latency_ms'] = (
                        0.9 * self.stats['avg_latency_ms'] + 0.1 * latency_ms
                    )

                    # Warn if latency exceeds threshold
                    if latency_ms > 100.0:
                        self.log.warning(f"High latency: {latency_ms:.1f}ms")

                await self.broadcast_frame(frame)
                idle_frame_timer = 0.0

            else:
                # No frames available - send idle frame every 1 second (FR-009)
                idle_frame_timer += dt
                if idle_frame_timer >= 1.0:
                    idle_frame = create_idle_frame()
                    await self.broadcast_frame(idle_frame)
                    idle_frame_timer = 0.0

            # Sleep to maintain target frame rate
            # Account for processing time
            elapsed = time.time() - current_time
            sleep_time = max(0.001, self.FRAME_INTERVAL - elapsed)
            await asyncio.sleep(sleep_time)

        self.log.info("Broadcast loop stopped")

    def start_broadcasting(self):
        """Start the broadcast loop"""
        if not self.broadcasting and self.broadcast_task is None:
            self.broadcast_task = asyncio.create_task(self.broadcast_loop())
            print("[MetricsStreamer] Broadcasting started")

    async def stop_broadcasting(self):
        """Stop the broadcast loop"""
        self.broadcasting = False

        if self.broadcast_task:
            await self.broadcast_task
            self.broadcast_task = None

        print("[MetricsStreamer] Broadcasting stopped")

    def get_latest_frame(self) -> Optional[MetricsFrame]:
        """
        Get the most recent frame (for REST API)

        Returns:
            Latest MetricsFrame or None
        """
        return self.latest_frame

    def get_statistics(self) -> Dict:
        """
        Get streaming statistics

        Returns:
            Dictionary with performance metrics
        """
        uptime = time.time() - self.last_broadcast_time if self.last_broadcast_time > 0 else 0

        return {
            **self.stats,
            'active_connections': len(self.active_connections),
            'buffer_size': len(self.frame_buffer),
            'broadcasting': self.broadcasting,
            'frames_buffered': len(self.frame_buffer),
            'uptime_seconds': uptime,
        }

    async def close(self):
        """Cleanup and close all connections"""
        print("[MetricsStreamer] Shutting down")

        # Stop broadcasting
        await self.stop_broadcasting()

        # Close all client connections
        for websocket in list(self.active_connections):
            try:
                await websocket.close()
            except:
                pass
        self.active_connections.clear()

        # Close logger
        if self.logger:
            self.logger.close()

        print("[MetricsStreamer] Shutdown complete")

    def __del__(self):
        """Ensure cleanup"""
        if self.logger:
            self.logger.close()


# FastAPI Application Setup
def create_metrics_app(streamer: MetricsStreamer) -> FastAPI:
    """
    Create FastAPI application with metrics endpoints

    Args:
        streamer: MetricsStreamer instance

    Returns:
        FastAPI application
    """
    app = FastAPI(title="D-ASE Metrics API")

    @app.websocket("/ws/metrics")
    async def websocket_metrics_endpoint(websocket: WebSocket):
        """
        WebSocket endpoint for real-time metrics stream

        Implements FR-001, FR-003, FR-005
        """
        await streamer.connect(websocket)

        try:
            # Keep connection alive and handle incoming messages
            while True:
                # Wait for client messages (mostly ping/pong)
                data = await websocket.receive_text()

                # Handle control messages
                try:
                    msg = json.loads(data)
                    if msg.get('type') == 'ping':
                        await websocket.send_text(json.dumps({'type': 'pong'}))
                except:
                    pass  # Ignore malformed messages

        except WebSocketDisconnect:
            await streamer.disconnect(websocket)
        except Exception as e:
            logging.error(f"WebSocket error: {e}")
            await streamer.disconnect(websocket)

    @app.get("/api/metrics/latest")
    async def get_latest_metrics():
        """
        REST endpoint for latest metrics frame

        Implements FR-006

        Returns:
            JSON response with latest frame or 404 if not available
        """
        frame = streamer.get_latest_frame()

        if frame is None:
            return JSONResponse(
                status_code=404,
                content={"error": "No metrics available"}
            )

        return JSONResponse(content=frame.to_dict())

    @app.get("/api/metrics/stats")
    async def get_metrics_statistics():
        """
        Get streaming statistics

        Returns:
            JSON response with performance statistics
        """
        stats = streamer.get_statistics()
        return JSONResponse(content=stats)

    @app.on_event("startup")
    async def startup_event():
        """Start broadcasting on application startup"""
        streamer.start_broadcasting()
        logging.info("Metrics API started")

    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on application shutdown"""
        await streamer.close()
        logging.info("Metrics API shutdown")

    return app


# Self-test function
def _self_test():
    """Test MetricsStreamer (requires async runtime)"""
    print("=" * 60)
    print("MetricsStreamer Self-Test")
    print("=" * 60)

    try:
        from metrics_frame import create_test_frame
        import asyncio

        async def run_test():
            # Initialize streamer
            print("\n1. Initializing streamer...")
            streamer = MetricsStreamer(enable_logging=False)
            print("   ✓ Streamer initialized")

            # Start broadcasting
            print("\n2. Starting broadcast loop...")
            streamer.start_broadcasting()
            await asyncio.sleep(0.1)  # Let it start
            print("   ✓ Broadcasting started")

            # Submit test frames
            print("\n3. Submitting test frames...")
            for i in range(5):
                frame = create_test_frame(frame_id=i)
                streamer.submit_frame(frame)
                await asyncio.sleep(0.033)  # ~30 Hz

            print(f"   ✓ Submitted {streamer.frame_counter} frames")

            # Check latest frame
            print("\n4. Checking latest frame...")
            latest = streamer.get_latest_frame()
            print(f"   Latest frame: {latest}")
            assert latest is not None
            print("   ✓ Latest frame OK")

            # Get statistics
            print("\n5. Getting statistics...")
            stats = streamer.get_statistics()
            print(f"   Frames sent: {stats['total_frames_sent']}")
            print(f"   Avg latency: {stats['avg_latency_ms']:.2f}ms")
            print("   ✓ Statistics OK")

            # Stop broadcasting
            print("\n6. Stopping broadcast...")
            await streamer.stop_broadcasting()
            print("   ✓ Stopped")

            # Cleanup
            await streamer.close()
            print("   ✓ Cleanup complete")

        # Run async test
        asyncio.run(run_test())

        print("\n" + "=" * 60)
        print("Self-Test PASSED ✓")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n✗ Self-Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    _self_test()
