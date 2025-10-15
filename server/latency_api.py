"""
Latency REST API & WebSocket - Diagnostics and Monitoring

Implements FR-004, FR-008: Complete API for latency telemetry and calibration
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import JSONResponse
from typing import Optional, List
import asyncio
import json
import time

from latency_manager import LatencyManager
from latency_frame import LatencyFrame


# Initialize manager (will be set by main app)
latency_manager: Optional[LatencyManager] = None


class LatencyStreamer:
    """
    WebSocket broadcaster for real-time latency telemetry

    Similar to MetricsStreamer but for latency diagnostics
    """

    TARGET_FPS = 10  # 10 Hz for latency updates (less frequent than metrics)
    MAX_CLIENTS = 5

    def __init__(self, manager: LatencyManager):
        """
        Initialize latency streamer

        Args:
            manager: LatencyManager instance
        """
        self.manager = manager
        self.clients: List[WebSocket] = []
        self.is_running = False
        self.broadcast_task = None

    async def connect_client(self, websocket: WebSocket):
        """
        Connect new WebSocket client

        Args:
            websocket: WebSocket connection
        """
        if len(self.clients) >= self.MAX_CLIENTS:
            await websocket.close(code=1008, reason=f"Max clients ({self.MAX_CLIENTS}) reached")
            return

        await websocket.accept()
        self.clients.append(websocket)

        print(f"[LatencyStreamer] Client connected (total: {len(self.clients)})")

        # Send initial frame immediately
        frame = self.manager.get_current_frame()
        try:
            await websocket.send_text(frame.to_json())
        except:
            pass

    def disconnect_client(self, websocket: WebSocket):
        """
        Disconnect WebSocket client

        Args:
            websocket: WebSocket connection
        """
        if websocket in self.clients:
            self.clients.remove(websocket)
            print(f"[LatencyStreamer] Client disconnected (total: {len(self.clients)})")

    async def broadcast_frame(self, frame: LatencyFrame):
        """
        Broadcast latency frame to all connected clients

        Args:
            frame: LatencyFrame to broadcast
        """
        if not self.clients:
            return

        json_data = frame.to_json()

        # Send to all clients, remove disconnected ones
        disconnected = []

        for client in self.clients:
            try:
                await client.send_text(json_data)
            except:
                disconnected.append(client)

        # Remove disconnected clients
        for client in disconnected:
            self.disconnect_client(client)

    async def broadcast_loop(self):
        """Background task to broadcast latency frames at TARGET_FPS"""
        print(f"[LatencyStreamer] Broadcast loop started ({self.TARGET_FPS} Hz)")

        frame_interval = 1.0 / self.TARGET_FPS
        last_frame_time = 0.0

        while self.is_running:
            current_time = time.time()

            # Check if it's time for next frame
            if current_time - last_frame_time >= frame_interval:
                # Get current latency frame
                frame = self.manager.get_current_frame()

                # Broadcast to all clients
                await self.broadcast_frame(frame)

                last_frame_time = current_time

            # Sleep until next frame (with some margin)
            await asyncio.sleep(frame_interval * 0.5)

        print("[LatencyStreamer] Broadcast loop stopped")

    async def start(self):
        """Start broadcast loop"""
        if self.is_running:
            return

        self.is_running = True
        self.broadcast_task = asyncio.create_task(self.broadcast_loop())

    async def stop(self):
        """Stop broadcast loop"""
        self.is_running = False

        if self.broadcast_task:
            self.broadcast_task.cancel()
            try:
                await self.broadcast_task
            except asyncio.CancelledError:
                pass

        # Close all client connections
        for client in self.clients[:]:
            try:
                await client.close()
            except:
                pass

        self.clients.clear()


# Global streamer instance
latency_streamer: Optional[LatencyStreamer] = None


def create_latency_api(manager: LatencyManager) -> FastAPI:
    """
    Create FastAPI application with latency endpoints

    Args:
        manager: LatencyManager instance

    Returns:
        FastAPI application
    """
    app = FastAPI(title="Soundlab Latency API", version="1.0")

    # Store references
    global latency_manager, latency_streamer
    latency_manager = manager
    latency_streamer = LatencyStreamer(manager)

    # --- REST Endpoints ---

    @app.get("/api/latency/current")
    async def get_current_latency():
        """
        Get current latency frame

        Returns:
            Current LatencyFrame as JSON
        """
        frame = latency_manager.get_current_frame()
        return JSONResponse(content=frame.to_dict())

    @app.get("/api/latency/stats")
    async def get_latency_statistics():
        """
        Get comprehensive latency statistics

        Returns:
            Dictionary with latency metrics, drift stats, alignment status
        """
        stats = latency_manager.get_statistics()
        return JSONResponse(content=stats)

    @app.post("/api/latency/calibrate")
    async def run_calibration():
        """
        Trigger impulse response calibration

        Note: Requires audio loopback (output → input)

        Returns:
            Calibration results with success status
        """
        try:
            print("[LatencyAPI] Starting calibration...")

            # Run calibration (blocking operation)
            success = latency_manager.calibrate()

            if not success:
                raise HTTPException(
                    status_code=500,
                    detail="Calibration failed - check audio loopback connection"
                )

            # Get updated frame
            frame = latency_manager.get_current_frame()

            return JSONResponse(content={
                'success': True,
                'calibrated': latency_manager.is_calibrated,
                'total_latency_ms': frame.total_measured_ms,
                'effective_latency_ms': frame.get_effective_latency(),
                'quality': frame.calibration_quality,
                'aligned': latency_manager.is_aligned(),
                'latency_frame': frame.to_dict()
            })

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/latency/compensation/set")
    async def set_compensation_offset(offset_ms: float = Query(..., description="Compensation offset in ms")):
        """
        Manually set compensation offset

        Args:
            offset_ms: Compensation offset in milliseconds

        Returns:
            Updated latency frame
        """
        try:
            if offset_ms < 0 or offset_ms > 200:
                raise HTTPException(
                    status_code=400,
                    detail="Offset must be between 0 and 200 ms"
                )

            # Update compensation
            latency_manager.latency_frame.compensation_offset_ms = offset_ms
            latency_manager.delay_line.set_delay_ms(offset_ms, latency_manager.sample_rate)

            frame = latency_manager.get_current_frame()

            return JSONResponse(content={
                'ok': True,
                'compensation_offset_ms': offset_ms,
                'effective_latency_ms': frame.get_effective_latency(),
                'aligned': latency_manager.is_aligned()
            })

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/latency/compensation/adjust")
    async def adjust_compensation(delta_ms: float = Query(..., description="Compensation adjustment in ms")):
        """
        Adjust compensation offset by delta

        Args:
            delta_ms: Amount to adjust (positive = add delay, negative = reduce delay)

        Returns:
            Updated latency frame
        """
        try:
            current_offset = latency_manager.latency_frame.compensation_offset_ms
            new_offset = current_offset + delta_ms

            if new_offset < 0 or new_offset > 200:
                raise HTTPException(
                    status_code=400,
                    detail=f"Adjusted offset ({new_offset:.2f} ms) out of range [0, 200]"
                )

            # Update compensation
            latency_manager.latency_frame.compensation_offset_ms = new_offset
            latency_manager.delay_line.set_delay_ms(new_offset, latency_manager.sample_rate)

            frame = latency_manager.get_current_frame()

            return JSONResponse(content={
                'ok': True,
                'compensation_offset_ms': new_offset,
                'delta_applied_ms': delta_ms,
                'effective_latency_ms': frame.get_effective_latency(),
                'aligned': latency_manager.is_aligned()
            })

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/latency/compensation/manual")
    async def set_manual_offset(offset_ms: float = Query(..., description="Manual offset in ms")):
        """
        Set manual user offset (separate from auto compensation)

        Args:
            offset_ms: Manual offset in milliseconds

        Returns:
            Updated latency frame
        """
        try:
            if offset_ms < -50 or offset_ms > 50:
                raise HTTPException(
                    status_code=400,
                    detail="Manual offset must be between -50 and +50 ms"
                )

            latency_manager.latency_frame.manual_offset_ms = offset_ms

            frame = latency_manager.get_current_frame()

            return JSONResponse(content={
                'ok': True,
                'manual_offset_ms': offset_ms,
                'effective_latency_ms': frame.get_effective_latency(),
                'aligned': latency_manager.is_aligned()
            })

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/latency/drift")
    async def get_drift_statistics():
        """
        Get drift monitoring statistics

        Returns:
            Drift metrics and history
        """
        drift_stats = latency_manager.drift_monitor.get_statistics()
        return JSONResponse(content=drift_stats)

    @app.post("/api/latency/drift/reset")
    async def reset_drift_monitor():
        """
        Reset drift monitor (clear history)

        Returns:
            Success status
        """
        try:
            # Reset drift monitor
            latency_manager.drift_monitor = type(latency_manager.drift_monitor)()

            return JSONResponse(content={
                'ok': True,
                'message': 'Drift monitor reset'
            })

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/latency/aligned")
    async def check_alignment(tolerance_ms: float = Query(5.0, description="Alignment tolerance in ms")):
        """
        Check if system is aligned within tolerance

        Args:
            tolerance_ms: Tolerance in milliseconds (default: 5.0)

        Returns:
            Alignment status and effective latency
        """
        frame = latency_manager.get_current_frame()
        effective = frame.get_effective_latency()
        aligned = frame.is_aligned(tolerance_ms)

        return JSONResponse(content={
            'aligned': aligned,
            'effective_latency_ms': effective,
            'tolerance_ms': tolerance_ms,
            'within_tolerance': abs(effective) <= tolerance_ms
        })

    # --- WebSocket Endpoint ---

    @app.websocket("/ws/latency")
    async def websocket_latency_stream(websocket: WebSocket):
        """
        WebSocket endpoint for real-time latency telemetry

        Streams LatencyFrame JSON at 10 Hz
        """
        await latency_streamer.connect_client(websocket)

        try:
            # Keep connection alive and handle any incoming messages
            while True:
                # Wait for messages (ping/pong, commands, etc.)
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)

                    # Handle commands
                    try:
                        msg = json.loads(data)

                        if msg.get('type') == 'ping':
                            await websocket.send_text(json.dumps({'type': 'pong'}))

                        elif msg.get('type') == 'get_stats':
                            stats = latency_manager.get_statistics()
                            await websocket.send_text(json.dumps({
                                'type': 'stats',
                                'data': stats
                            }))

                    except json.JSONDecodeError:
                        pass  # Ignore invalid JSON

                except asyncio.TimeoutError:
                    # No message received, continue loop
                    pass

        except WebSocketDisconnect:
            latency_streamer.disconnect_client(websocket)
        except Exception as e:
            print(f"[LatencyAPI] WebSocket error: {e}")
            latency_streamer.disconnect_client(websocket)

    # --- Lifecycle Events ---

    @app.on_event("startup")
    async def startup_event():
        """Start latency streamer on app startup"""
        print("[LatencyAPI] Starting latency streamer...")
        await latency_streamer.start()

    @app.on_event("shutdown")
    async def shutdown_event():
        """Stop latency streamer on app shutdown"""
        print("[LatencyAPI] Stopping latency streamer...")
        await latency_streamer.stop()

    return app


# Standalone server for testing
if __name__ == "__main__":
    import uvicorn

    # Initialize manager
    manager = LatencyManager()

    # Create app
    app = create_latency_api(manager)

    print("=" * 60)
    print("Latency API Test Server")
    print("=" * 60)
    print("\nStarting server at http://localhost:8001")
    print("API docs at http://localhost:8001/docs")
    print("\nEndpoints:")
    print("  GET  /api/latency/current          - Current latency frame")
    print("  GET  /api/latency/stats            - Full statistics")
    print("  POST /api/latency/calibrate        - Run calibration")
    print("  POST /api/latency/compensation/set - Set compensation offset")
    print("  POST /api/latency/compensation/adjust - Adjust offset by delta")
    print("  POST /api/latency/compensation/manual - Set manual user offset")
    print("  GET  /api/latency/drift            - Drift statistics")
    print("  POST /api/latency/drift/reset      - Reset drift monitor")
    print("  GET  /api/latency/aligned          - Check alignment")
    print("  WS   /ws/latency                   - WebSocket stream (10 Hz)")
    print("\nPress Ctrl+C to stop")
    print("=" * 60)

    # Run server
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
