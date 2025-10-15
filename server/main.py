"""
Soundlab Main Server - Complete System Integration

Integrates all components:
- AudioServer (real-time audio processing)
- PresetAPI (preset management)
- MetricsAPI (real-time metrics streaming)
- LatencyAPI (latency diagnostics and compensation)
- WebSocket streams for metrics and latency
- Unified FastAPI application

Run with: python main.py
"""

import asyncio
import signal
import sys
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import os
from pathlib import Path

# Import all components
from audio_server import AudioServer
from preset_store import PresetStore
from ab_snapshot import ABSnapshot
from metrics_streamer import MetricsStreamer
from preset_api import create_preset_api
from latency_api import create_latency_api, LatencyStreamer


class SoundlabServer:
    """
    Complete Soundlab server with all features integrated

    Features:
    - Real-time audio processing (48kHz @ 512 samples)
    - REST APIs (presets, metrics, latency)
    - WebSocket streaming (metrics @ 30Hz, latency @ 10Hz)
    - A/B preset comparison
    - Latency compensation with calibration
    - Comprehensive logging
    """

    def __init__(self,
                 host: str = "0.0.0.0",
                 port: int = 8000,
                 audio_input_device: Optional[int] = None,
                 audio_output_device: Optional[int] = None,
                 enable_logging: bool = True,
                 enable_cors: bool = True):
        """
        Initialize Soundlab server

        Args:
            host: Server host address
            port: Server port
            audio_input_device: Audio input device index (None = default)
            audio_output_device: Audio output device index (None = default)
            enable_logging: Enable metrics/latency logging
            enable_cors: Enable CORS for web clients
        """
        print("=" * 60)
        print("SOUNDLAB SERVER")
        print("Real-Time Audio Processing & Consciousness Telemetry")
        print("=" * 60)

        self.host = host
        self.port = port
        self.enable_logging = enable_logging

        # Initialize audio server
        print("\n[Main] Initializing audio server...")
        self.audio_server = AudioServer(
            input_device=audio_input_device,
            output_device=audio_output_device,
            enable_logging=enable_logging
        )

        # Initialize preset management
        print("\n[Main] Initializing preset store...")
        self.preset_store = PresetStore()
        self.ab_snapshot = ABSnapshot()

        # Initialize metrics streamer
        print("\n[Main] Initializing metrics streamer...")
        self.metrics_streamer = MetricsStreamer()

        # Wire audio server metrics to streamer
        self.audio_server.metrics_callback = lambda frame: asyncio.run(
            self.metrics_streamer.enqueue_frame(frame)
        )

        # Initialize latency streamer (will be created by latency API)
        self.latency_streamer: Optional[LatencyStreamer] = None

        # Create FastAPI application
        print("\n[Main] Creating FastAPI application...")
        self.app = FastAPI(
            title="Soundlab API",
            version="1.0.0",
            description="Real-time audio processing with Φ-modulation and consciousness metrics"
        )

        # Enable CORS if requested
        if enable_cors:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],  # Configure appropriately for production
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        # Mount sub-applications
        self._mount_apis()

        # Add root endpoints
        self._add_root_endpoints()

        # Serve static files (frontend)
        self._mount_static_files()

        # Shutdown handler
        self.is_shutting_down = False

        print("\n[Main] ✓ Server initialization complete")

    def _mount_apis(self):
        """Mount all API sub-applications"""

        # Preset API
        preset_app = create_preset_api(self.preset_store, self.ab_snapshot)
        self.app.mount("/", preset_app)

        # Latency API
        latency_app = create_latency_api(self.audio_server.latency_manager)
        self.app.mount("/", latency_app)

        # Get reference to latency streamer
        from latency_api import latency_streamer
        self.latency_streamer = latency_streamer

        # Wire audio server latency to streamer
        if self.latency_streamer:
            self.audio_server.latency_callback = lambda frame: asyncio.run(
                self.latency_streamer.broadcast_frame(frame)
            )

    def _add_root_endpoints(self):
        """Add root-level endpoints"""

        @self.app.get("/")
        async def root():
            """Serve main HTML page"""
            frontend_path = Path(__file__).parent.parent / "soundlab_v2.html"

            if frontend_path.exists():
                return FileResponse(frontend_path)
            else:
                return {
                    "message": "Soundlab API Server",
                    "version": "1.0.0",
                    "status": "running",
                    "docs": "/docs",
                    "audio_running": self.audio_server.is_running
                }

        @self.app.get("/api/status")
        async def get_status():
            """Get server status"""
            return {
                "audio_running": self.audio_server.is_running,
                "sample_rate": self.audio_server.SAMPLE_RATE,
                "buffer_size": self.audio_server.BUFFER_SIZE,
                "callback_count": self.audio_server.callback_count,
                "latency_calibrated": self.audio_server.latency_manager.is_calibrated,
                "preset_loaded": self.audio_server.current_preset is not None,
                "metrics_clients": len(self.metrics_streamer.clients),
                "latency_clients": len(self.latency_streamer.clients) if self.latency_streamer else 0
            }

        @self.app.post("/api/audio/start")
        async def start_audio(calibrate: bool = False):
            """Start audio processing"""
            if self.audio_server.is_running:
                return {"ok": False, "message": "Audio already running"}

            success = self.audio_server.start(calibrate_latency=calibrate)

            return {
                "ok": success,
                "message": "Audio started" if success else "Failed to start audio"
            }

        @self.app.post("/api/audio/stop")
        async def stop_audio():
            """Stop audio processing"""
            if not self.audio_server.is_running:
                return {"ok": False, "message": "Audio not running"}

            self.audio_server.stop()

            return {"ok": True, "message": "Audio stopped"}

        @self.app.get("/api/audio/performance")
        async def get_performance():
            """Get audio processing performance metrics"""
            import numpy as np

            if not self.audio_server.processing_time_history:
                return {
                    "message": "No performance data available",
                    "callback_count": self.audio_server.callback_count
                }

            history = self.audio_server.processing_time_history
            buffer_duration_ms = (self.audio_server.BUFFER_SIZE / self.audio_server.SAMPLE_RATE) * 1000.0

            return {
                "callback_count": self.audio_server.callback_count,
                "buffer_duration_ms": buffer_duration_ms,
                "processing_time_ms": {
                    "current": history[-1] if history else 0,
                    "average": float(np.mean(history)),
                    "min": float(np.min(history)),
                    "max": float(np.max(history)),
                    "std": float(np.std(history))
                },
                "cpu_load": {
                    "current": history[-1] / buffer_duration_ms if history else 0,
                    "average": float(np.mean(history)) / buffer_duration_ms,
                    "peak": float(np.max(history)) / buffer_duration_ms if history else 0
                }
            }

        @self.app.post("/api/preset/apply")
        async def apply_preset_from_api(preset_data: dict):
            """Apply preset to audio server"""
            try:
                self.audio_server.apply_preset(preset_data)
                return {"ok": True, "message": "Preset applied"}
            except Exception as e:
                return {"ok": False, "message": str(e)}

        # Metrics WebSocket endpoint
        @self.app.websocket("/ws/metrics")
        async def websocket_metrics(websocket):
            """WebSocket endpoint for real-time metrics (30 Hz)"""
            await self.metrics_streamer.handle_websocket(websocket)

    def _mount_static_files(self):
        """Mount static file directories"""
        # Mount frontend files if they exist
        frontend_dir = Path(__file__).parent.parent

        if (frontend_dir / "static").exists():
            self.app.mount("/static", StaticFiles(directory=str(frontend_dir / "static")), name="static")

    async def startup(self):
        """Server startup tasks"""
        print("\n" + "=" * 60)
        print("STARTING SOUNDLAB SERVER")
        print("=" * 60)

        # Start metrics streamer
        print("\n[Main] Starting metrics streamer...")
        await self.metrics_streamer.start()

        # Start latency streamer
        if self.latency_streamer:
            print("[Main] Starting latency streamer...")
            await self.latency_streamer.start()

        print("\n[Main] ✓ All services started")
        print("\n" + "=" * 60)
        print(f"Server running at: http://{self.host}:{self.port}")
        print(f"API docs: http://{self.host}:{self.port}/docs")
        print("=" * 60)
        print("\nEndpoints:")
        print("  GET  /                              - Frontend UI")
        print("  GET  /api/status                    - Server status")
        print("  POST /api/audio/start               - Start audio processing")
        print("  POST /api/audio/stop                - Stop audio processing")
        print("  GET  /api/audio/performance         - Performance metrics")
        print("  POST /api/preset/apply              - Apply preset")
        print("")
        print("  GET  /api/presets                   - List presets")
        print("  GET  /api/presets/{id}              - Get preset")
        print("  POST /api/presets                   - Create preset")
        print("  PUT  /api/presets/{id}              - Update preset")
        print("  DELETE /api/presets/{id}            - Delete preset")
        print("  POST /api/presets/export            - Export all presets")
        print("  POST /api/presets/import            - Import preset bundle")
        print("  POST /api/presets/ab/store/{A|B}    - Store A/B snapshot")
        print("  POST /api/presets/ab/toggle         - Toggle A/B")
        print("")
        print("  GET  /api/latency/current           - Current latency")
        print("  GET  /api/latency/stats             - Latency statistics")
        print("  POST /api/latency/calibrate         - Run calibration")
        print("  POST /api/latency/compensation/set  - Set compensation")
        print("")
        print("  WS   /ws/metrics                    - Metrics stream (30 Hz)")
        print("  WS   /ws/latency                    - Latency stream (10 Hz)")
        print("=" * 60)
        print("\nPress Ctrl+C to stop server")
        print("=" * 60)

    async def shutdown(self):
        """Server shutdown tasks"""
        if self.is_shutting_down:
            return

        self.is_shutting_down = True

        print("\n" + "=" * 60)
        print("SHUTTING DOWN SOUNDLAB SERVER")
        print("=" * 60)

        # Stop audio server
        if self.audio_server.is_running:
            print("\n[Main] Stopping audio server...")
            self.audio_server.stop()

        # Stop metrics streamer
        print("[Main] Stopping metrics streamer...")
        await self.metrics_streamer.stop()

        # Stop latency streamer
        if self.latency_streamer:
            print("[Main] Stopping latency streamer...")
            await self.latency_streamer.stop()

        print("\n[Main] ✓ Shutdown complete")
        print("=" * 60)

    def run(self, auto_start_audio: bool = False, calibrate_on_start: bool = False):
        """
        Run the server

        Args:
            auto_start_audio: Automatically start audio processing
            calibrate_on_start: Run latency calibration on startup
        """

        # Setup signal handlers for graceful shutdown
        def signal_handler(sig, frame):
            print("\n[Main] Interrupt received, shutting down...")
            asyncio.run(self.shutdown())
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Register startup/shutdown events
        @self.app.on_event("startup")
        async def on_startup():
            await self.startup()

            # Auto-start audio if requested
            if auto_start_audio:
                print("\n[Main] Auto-starting audio processing...")
                self.audio_server.start(calibrate_latency=calibrate_on_start)

        @self.app.on_event("shutdown")
        async def on_shutdown():
            await self.shutdown()

        # Run server with uvicorn
        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Soundlab Audio Server")
    parser.add_argument("--host", default="0.0.0.0", help="Server host address")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument("--input-device", type=int, default=None, help="Audio input device index")
    parser.add_argument("--output-device", type=int, default=None, help="Audio output device index")
    parser.add_argument("--auto-start-audio", action="store_true", help="Automatically start audio processing")
    parser.add_argument("--calibrate", action="store_true", help="Run latency calibration on startup")
    parser.add_argument("--no-logging", action="store_true", help="Disable metrics/latency logging")
    parser.add_argument("--list-devices", action="store_true", help="List available audio devices and exit")

    args = parser.parse_args()

    # List devices if requested
    if args.list_devices:
        import sounddevice as sd
        print("\n" + "=" * 60)
        print("Available Audio Devices")
        print("=" * 60)
        print(sd.query_devices())
        print("\nUse --input-device and --output-device with device index")
        return

    # Create and run server
    server = SoundlabServer(
        host=args.host,
        port=args.port,
        audio_input_device=args.input_device,
        audio_output_device=args.output_device,
        enable_logging=not args.no_logging
    )

    server.run(
        auto_start_audio=args.auto_start_audio,
        calibrate_on_start=args.calibrate
    )


if __name__ == "__main__":
    main()
