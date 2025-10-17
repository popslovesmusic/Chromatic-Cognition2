"""
Sensor WebSocket Streamer - Feature 023 (FR-003)

Provides /ws/sensors WebSocket endpoint for real-time hardware sensor streaming
Streams Φ-sensor data, I²S metrics, and hardware telemetry at 30 Hz

Requirements:
- FR-003: /ws/sensors WebSocket endpoint
- SC-002: 30 Hz stream rate
"""

import asyncio
import json
import logging
from typing import Set, Dict, Any
from dataclasses import asdict
from fastapi import WebSocket, WebSocketDisconnect, FastAPI
from .sensor_manager import SensorManager, SensorReading


class SensorStreamer:
    """
    WebSocket streamer for hardware sensor data (FR-003)

    Broadcasts sensor readings to all connected WebSocket clients at 30 Hz
    """

    def __init__(self, sensor_manager: SensorManager):
        """
        Initialize sensor streamer

        Args:
            sensor_manager: SensorManager instance to stream from
        """
        self.sensor_manager = sensor_manager
        self.active_connections: Set[WebSocket] = set()
        self.logger = logging.getLogger(__name__)
        self.broadcast_task = None
        self.running = False

    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        self.logger.info("Sensor WebSocket connected (total: %d)", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        self.active_connections.discard(websocket)
        self.logger.info("Sensor WebSocket disconnected (total: %d)", len(self.active_connections))

    async def start_broadcast(self):
        """Start broadcasting sensor data to all connections"""
        if self.running:
            return

        self.running = True
        self.broadcast_task = asyncio.create_task(self._broadcast_loop())
        self.logger.info("Sensor broadcast started")

    async def stop_broadcast(self):
        """Stop broadcasting"""
        if not self.running:
            return

        self.running = False

        if self.broadcast_task:
            self.broadcast_task.cancel()
            try:
                await self.broadcast_task
            except asyncio.CancelledError:
                pass

        self.logger.info("Sensor broadcast stopped")

    async def _broadcast_loop(self):
        """Main broadcast loop at 30 Hz (SC-002)"""
        target_interval = 1.0 / 30.0  # 30 Hz

        while self.running:
            loop_start = asyncio.get_event_loop().time()

            try:
                # Get current sensor reading
                reading = self.sensor_manager.get_current_reading()

                if reading and self.active_connections:
                    # Get additional metrics
                    stats = self.sensor_manager.get_statistics()
                    hw_metrics = self.sensor_manager.get_hardware_metrics()

                    # Build message
                    message = {
                        'type': 'sensor_data',
                        'reading': asdict(reading),
                        'statistics': {
                            'sample_rate': stats.sample_rate_actual,
                            'jitter_hz': stats.sample_rate_jitter,
                            'uptime': stats.uptime_seconds,
                            'coherence_avg': stats.coherence_avg
                        },
                        'hardware': {
                            'i2s_latency_us': hw_metrics.i2s_latency_us,
                            'i2s_link_status': hw_metrics.i2s_link_status,
                            'coherence_hw_sw': hw_metrics.coherence_hw_sw,
                        }
                    }

                    # Broadcast to all connections
                    await self._broadcast(message)

            except Exception as e:
                self.logger.error("Broadcast error: %s", e)

            # Sleep to maintain target rate
            elapsed = asyncio.get_event_loop().time() - loop_start
            sleep_time = max(0, target_interval - elapsed)
            await asyncio.sleep(sleep_time)

    async def _broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return

        message_json = json.dumps(message)
        dead_connections = set()

        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                self.logger.warning("Failed to send to connection: %s", e)
                dead_connections.add(connection)

        # Remove dead connections
        for connection in dead_connections:
            self.disconnect(connection)

    async def send_event(self, event: Dict[str, Any]):
        """Send one-time event to all connections"""
        await self._broadcast(event)


def create_sensor_websocket_endpoint(app: FastAPI, sensor_manager: SensorManager) -> SensorStreamer:
    """
    Create /ws/sensors WebSocket endpoint (FR-003)

    Args:
        app: FastAPI application
        sensor_manager: SensorManager instance

    Returns:
        SensorStreamer instance
    """
    streamer = SensorStreamer(sensor_manager)

    @app.websocket("/ws/sensors")
    async def websocket_sensors_endpoint(websocket: WebSocket):
        """WebSocket endpoint for hardware sensor streaming (30 Hz)"""
        await streamer.connect(websocket)

        try:
            # Keep connection alive and handle client messages
            while True:
                try:
                    # Wait for client messages (keep-alive, config, etc.)
                    data = await websocket.receive_text()

                    # Handle client commands
                    try:
                        msg = json.loads(data)
                        msg_type = msg.get('type')

                        if msg_type == 'get_stats':
                            # Send statistics
                            stats = sensor_manager.get_statistics()
                            await websocket.send_json({
                                'type': 'statistics',
                                'data': asdict(stats)
                            })

                        elif msg_type == 'get_hardware_metrics':
                            # Send hardware metrics
                            hw_metrics = sensor_manager.get_hardware_metrics()
                            await websocket.send_json({
                                'type': 'hardware_metrics',
                                'data': asdict(hw_metrics)
                            })

                    except json.JSONDecodeError:
                        pass

                except WebSocketDisconnect:
                    break

        finally:
            streamer.disconnect(websocket)

    return streamer


# Example usage
if __name__ == "__main__":
    import uvicorn
    from fastapi import FastAPI

    # Create FastAPI app
    app = FastAPI()

    # Create sensor manager
    sensor_manager = SensorManager({'simulation_mode': True})

    # Create WebSocket endpoint
    streamer = create_sensor_websocket_endpoint(app, sensor_manager)

    @app.on_event("startup")
    async def startup():
        await sensor_manager.start()
        await streamer.start_broadcast()

    @app.on_event("shutdown")
    async def shutdown():
        await streamer.stop_broadcast()
        await sensor_manager.stop()

    # Run server
    uvicorn.run(app, host="0.0.0.0", port=8001)
