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
from auto_phi import AutoPhiLearner, AutoPhiConfig
from criticality_balancer import CriticalityBalancer, CriticalityBalancerConfig
from state_memory import StateMemory, StateMemoryConfig
from state_classifier import StateClassifierGraph, StateClassifierConfig
from predictive_model import PredictiveModel, PredictiveModelConfig
from session_recorder import SessionRecorder, SessionRecorderConfig
from timeline_player import TimelinePlayer, TimelinePlayerConfig
from data_exporter import DataExporter, ExportConfig, ExportRequest, ExportFormat
from node_sync import NodeSynchronizer, NodeSyncConfig, NodeRole
from phasenet_protocol import PhaseNetNode, PhaseNetConfig
from cluster_monitor import ClusterMonitor, ClusterMonitorConfig
from hw_interface import HardwareInterface
from hybrid_bridge import HybridBridge
from hybrid_node import HybridNode, HybridNodeConfig, PhiSource, HybridMetrics


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
                 enable_cors: bool = True,
                 enable_auto_phi: bool = False,
                 enable_criticality_balancer: bool = False,
                 enable_state_memory: bool = False,
                 enable_state_classifier: bool = False,
                 enable_predictive_model: bool = False,
                 enable_session_recorder: bool = True,
                 enable_timeline_player: bool = True,
                 enable_data_exporter: bool = True,
                 enable_node_sync: bool = False,
                 node_sync_role: str = "master",
                 node_sync_master_url: Optional[str] = None,
                 enable_phasenet: bool = False,
                 phasenet_port: int = 9000,
                 phasenet_key: Optional[str] = None,
                 enable_cluster_monitor: bool = False,
                 enable_hardware_bridge: bool = False,
                 hardware_port: Optional[str] = None,
                 hardware_baudrate: int = 115200,
                 enable_hybrid_bridge: bool = False,
                 hybrid_port: Optional[str] = None,
                 hybrid_baudrate: int = 115200,
                 enable_hybrid_node: bool = False,
                 hybrid_node_input_device: Optional[int] = None,
                 hybrid_node_output_device: Optional[int] = None):
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

        # Initialize Auto-Φ Learner (Feature 011)
        print("\n[Main] Initializing Auto-Φ Learner...")
        auto_phi_config = AutoPhiConfig(
            enabled=enable_auto_phi,
            k_depth=0.25,
            gamma_phase=0.1,
            enable_logging=enable_logging
        )
        self.auto_phi_learner = AutoPhiLearner(auto_phi_config)

        # Wire audio server metrics to streamer and auto-phi learner
        def metrics_callback(frame):
            # Send to metrics streamer
            asyncio.run(self.metrics_streamer.enqueue_frame(frame))
            # Send to auto-phi learner
            self.auto_phi_learner.process_metrics(frame)

        self.audio_server.metrics_callback = metrics_callback

        # Wire Auto-Φ Learner parameter updates to audio server (FR-005)
        def auto_phi_update_callback(param_name: str, value: float):
            """Callback for Auto-Φ Learner to update parameters"""
            self.audio_server.update_parameter(
                param_type='phi',
                channel=None,
                param_name=param_name.replace('phi_', ''),  # Remove 'phi_' prefix
                value=value
            )

        self.auto_phi_learner.update_callback = auto_phi_update_callback

        # Initialize Criticality Balancer (Feature 012)
        print("\n[Main] Initializing Criticality Balancer...")
        criticality_balancer_config = CriticalityBalancerConfig(
            enabled=enable_criticality_balancer,
            beta_coupling=0.1,
            delta_amplitude=0.05,
            enable_logging=enable_logging
        )
        self.criticality_balancer = CriticalityBalancer(criticality_balancer_config)

        # Wire Criticality Balancer to metrics stream
        def metrics_callback_extended(frame):
            # Send to metrics streamer
            asyncio.run(self.metrics_streamer.enqueue_frame(frame))
            # Send to auto-phi learner
            self.auto_phi_learner.process_metrics(frame)
            # Send to criticality balancer
            self.criticality_balancer.process_metrics(frame)

        self.audio_server.metrics_callback = metrics_callback_extended

        # Wire Criticality Balancer batch updates to audio server (FR-006)
        def criticality_balancer_update_callback(update_data):
            """Callback for Criticality Balancer batch updates"""
            if update_data.get('type') == 'update_coupling':
                # Apply coupling matrix
                coupling_matrix = update_data.get('coupling_matrix')
                amplitudes = update_data.get('amplitudes')

                # Update coupling in audio server (if supported)
                # For now, just update amplitudes
                if amplitudes:
                    for channel_idx, amplitude in enumerate(amplitudes):
                        self.audio_server.update_parameter(
                            param_type='channel',
                            channel=channel_idx,
                            param_name='amplitude',
                            value=amplitude
                        )

        self.criticality_balancer.update_callback = criticality_balancer_update_callback

        # Initialize State Memory (Feature 013)
        print("\n[Main] Initializing State Memory...")
        state_memory_config = StateMemoryConfig(
            enabled=enable_state_memory,
            buffer_size=256,
            trend_window=30,
            enable_logging=enable_logging
        )
        self.state_memory = StateMemory(state_memory_config)

        # Wire State Memory to metrics stream and Auto-Phi Learner
        def metrics_callback_with_memory(frame):
            # Send to metrics streamer
            asyncio.run(self.metrics_streamer.enqueue_frame(frame))
            # Send to auto-phi learner
            self.auto_phi_learner.process_metrics(frame)
            # Send to criticality balancer
            self.criticality_balancer.process_metrics(frame)
            # Send to state memory (FR-002)
            if self.state_memory.config.enabled:
                criticality = getattr(frame, 'criticality', 1.0)
                coherence = getattr(frame, 'phase_coherence', 0.0)
                ici = getattr(frame, 'ici', 0.0)
                phi_depth = self.auto_phi_learner.state.phi_depth
                phi_phase = self.auto_phi_learner.state.phi_phase
                self.state_memory.add_frame(criticality, coherence, ici, phi_depth, phi_phase)

        self.audio_server.metrics_callback = metrics_callback_with_memory

        # Wire State Memory bias to Auto-Phi Learner (FR-004)
        def state_memory_bias_callback(bias: float):
            """Feed predictive bias from State Memory to Auto-Phi Learner"""
            self.auto_phi_learner.external_bias = bias

        self.state_memory.bias_callback = state_memory_bias_callback

        # Initialize State Classifier (Feature 015)
        print("\n[Main] Initializing State Classifier...")
        state_classifier_config = StateClassifierConfig(
            hysteresis_threshold=0.1,
            min_state_duration=0.5,
            enable_logging=enable_logging
        )
        self.state_classifier = StateClassifierGraph(state_classifier_config)

        # Wire State Classifier to metrics stream
        def metrics_callback_with_classifier(frame):
            # Send to metrics streamer
            asyncio.run(self.metrics_streamer.enqueue_frame(frame))
            # Send to auto-phi learner
            self.auto_phi_learner.process_metrics(frame)
            # Send to criticality balancer
            self.criticality_balancer.process_metrics(frame)
            # Send to state memory
            if self.state_memory.config.enabled:
                criticality = getattr(frame, 'criticality', 1.0)
                coherence = getattr(frame, 'phase_coherence', 0.0)
                ici = getattr(frame, 'ici', 0.0)
                phi_depth = self.auto_phi_learner.state.phi_depth
                phi_phase = self.auto_phi_learner.state.phi_phase
                self.state_memory.add_frame(criticality, coherence, ici, phi_depth, phi_phase)
            # Send to state classifier
            if self.state_classifier:
                ici = getattr(frame, 'ici', 0.0)
                coherence = getattr(frame, 'phase_coherence', 0.0)
                centroid = getattr(frame, 'spectral_centroid', 0.0)
                self.state_classifier.classify_state(ici, coherence, centroid)

        self.audio_server.metrics_callback = metrics_callback_with_classifier

        # Wire State Classifier state changes to WebSocket broadcast
        def state_change_callback(event):
            """Broadcast state changes via WebSocket (FR-005)"""
            asyncio.run(self.metrics_streamer.broadcast_event(event))

        self.state_classifier.state_change_callback = state_change_callback

        # Initialize Predictive Model (Feature 016)
        print("\n[Main] Initializing Predictive Model...")
        predictive_model_config = PredictiveModelConfig(
            buffer_size=128,
            prediction_horizon=1.5,
            min_buffer_size=50,
            enable_logging=enable_logging
        )
        self.predictive_model = PredictiveModel(predictive_model_config) if enable_predictive_model else None

        # Wire Predictive Model to State Memory and State Classifier
        if self.predictive_model:
            # Update metrics callback to feed Predictive Model
            def metrics_callback_with_predictor(frame):
                # Send to metrics streamer
                asyncio.run(self.metrics_streamer.enqueue_frame(frame))
                # Send to auto-phi learner
                self.auto_phi_learner.process_metrics(frame)
                # Send to criticality balancer
                self.criticality_balancer.process_metrics(frame)
                # Send to state memory
                if self.state_memory.config.enabled:
                    criticality = getattr(frame, 'criticality', 1.0)
                    coherence = getattr(frame, 'phase_coherence', 0.0)
                    ici = getattr(frame, 'ici', 0.0)
                    phi_depth = self.auto_phi_learner.state.phi_depth
                    phi_phase = self.auto_phi_learner.state.phi_phase
                    self.state_memory.add_frame(criticality, coherence, ici, phi_depth, phi_phase)
                # Send to state classifier
                if self.state_classifier:
                    ici = getattr(frame, 'ici', 0.0)
                    coherence = getattr(frame, 'phase_coherence', 0.0)
                    centroid = getattr(frame, 'spectral_centroid', 0.0)
                    self.state_classifier.classify_state(ici, coherence, centroid)
                # Send to predictive model (FR-002)
                if self.predictive_model:
                    ici = getattr(frame, 'ici', 0.0)
                    coherence = getattr(frame, 'phase_coherence', 0.0)
                    criticality = getattr(frame, 'criticality', 1.0)
                    current_state = self.state_classifier.current_state.value if self.state_classifier else "AWAKE"
                    import time
                    self.predictive_model.add_frame(ici, coherence, criticality, current_state, time.time())
                # Send to PhaseNet (FR-004)
                if self.phasenet and self.phasenet.is_running:
                    phi_phase = self.auto_phi_learner.state.phi_phase
                    phi_depth = self.auto_phi_learner.state.phi_depth
                    criticality = getattr(frame, 'criticality', 1.0)
                    coherence = getattr(frame, 'phase_coherence', 0.0)
                    ici = getattr(frame, 'ici', 0.0)
                    self.phasenet.update_phase(phi_phase, phi_depth, criticality, coherence, ici)

            self.audio_server.metrics_callback = metrics_callback_with_predictor

            # Wire forecast callback to Auto-Phi and Criticality Balancer (FR-006)
            def forecast_callback(forecast_json):
                """Handle forecast for preemptive adjustments"""
                # Broadcast forecast via WebSocket
                asyncio.run(self.metrics_streamer.broadcast_event(forecast_json))

                # Preemptive adjustment based on predicted criticality (SC-003)
                predicted_criticality = forecast_json['predicted_metrics']['criticality']
                confidence = forecast_json['confidence']

                # Only act on high-confidence predictions
                if confidence > 0.7:
                    # If predicted criticality > 1.05, reduce phi_depth proactively
                    if predicted_criticality > 1.05:
                        # Calculate preemptive bias (similar to State Memory)
                        overshoot_expected = predicted_criticality - 1.0
                        preemptive_bias = -0.3 * overshoot_expected * confidence

                        # Apply via Auto-Phi Learner external bias
                        self.auto_phi_learner.external_bias = preemptive_bias

                        if self.enable_logging:
                            print(f"[PredictiveModel] Preemptive adjustment: bias={preemptive_bias:.3f}, "
                                  f"predicted_crit={predicted_criticality:.2f}, conf={confidence:.2f}")

                    # If predicted criticality < 0.95, increase phi_depth proactively
                    elif predicted_criticality < 0.95:
                        undershoot_expected = 1.0 - predicted_criticality
                        preemptive_bias = 0.3 * undershoot_expected * confidence

                        self.auto_phi_learner.external_bias = preemptive_bias

                        if self.enable_logging:
                            print(f"[PredictiveModel] Preemptive adjustment: bias={preemptive_bias:.3f}, "
                                  f"predicted_crit={predicted_criticality:.2f}, conf={confidence:.2f}")

            self.predictive_model.forecast_callback = forecast_callback

        # Initialize Session Recorder (Feature 017)
        if enable_session_recorder:
            print("\n[Main] Initializing Session Recorder...")
            session_recorder_config = SessionRecorderConfig(
                sessions_dir="sessions",
                sample_rate=self.audio_server.SAMPLE_RATE,
                enable_logging=enable_logging
            )
            self.session_recorder = SessionRecorder(session_recorder_config)
        else:
            self.session_recorder = None

        # Initialize Timeline Player (Feature 018)
        if enable_timeline_player:
            print("\n[Main] Initializing Timeline Player...")
            timeline_player_config = TimelinePlayerConfig(
                update_rate=30,
                enable_logging=enable_logging
            )
            self.timeline_player = TimelinePlayer(timeline_player_config)
        else:
            self.timeline_player = None

        # Initialize Data Exporter (Feature 019)
        if enable_data_exporter:
            print("\n[Main] Initializing Data Exporter...")
            data_exporter_config = ExportConfig(
                output_dir="exports",
                enable_compression=True,
                enable_checksum=True,
                enable_logging=enable_logging
            )
            self.data_exporter = DataExporter(data_exporter_config)
        else:
            self.data_exporter = None

        # Initialize Node Synchronizer (Feature 020)
        if enable_node_sync:
            print("\n[Main] Initializing Node Synchronizer...")
            node_role = NodeRole.MASTER if node_sync_role.lower() == "master" else NodeRole.CLIENT
            node_sync_config = NodeSyncConfig(
                role=node_role,
                master_url=node_sync_master_url,
                sync_rate=30,
                enable_logging=enable_logging
            )
            self.node_sync = NodeSynchronizer(node_sync_config)
        else:
            self.node_sync = None

        # Initialize PhaseNet Protocol (Feature 021)
        if enable_phasenet:
            print("\n[Main] Initializing PhaseNet Protocol...")
            phasenet_config = PhaseNetConfig(
                bind_port=phasenet_port,
                network_key=phasenet_key,
                enable_encryption=phasenet_key is not None,
                enable_logging=enable_logging
            )
            self.phasenet = PhaseNetNode(phasenet_config)
        else:
            self.phasenet = None

        # Initialize Cluster Monitor (Feature 022)
        if enable_cluster_monitor:
            print("\n[Main] Initializing Cluster Monitor...")
            cluster_monitor_config = ClusterMonitorConfig(
                update_interval=1.0,
                history_samples=600,
                enable_rbac=True,
                enable_logging=enable_logging
            )
            self.cluster_monitor = ClusterMonitor(cluster_monitor_config)
            # Wire references to node_sync and phasenet (FR-001, FR-002)
            self.cluster_monitor.node_sync = self.node_sync
            self.cluster_monitor.phasenet = self.phasenet
        else:
            self.cluster_monitor = None

        # Initialize Hardware Interface (Feature 023)
        if enable_hardware_bridge:
            print("\n[Main] Initializing Hardware I²S Bridge...")
            self.hw_interface = HardwareInterface(
                port=hardware_port,
                baudrate=hardware_baudrate,
                enable_logging=enable_logging
            )
            # Wire to cluster monitor (FR-008)
            if self.cluster_monitor:
                self.cluster_monitor.hw_interface = self.hw_interface
        else:
            self.hw_interface = None

        # Initialize Hybrid Analog-DSP Bridge (Feature 024)
        if enable_hybrid_bridge:
            print("\n[Main] Initializing Hybrid Analog-DSP Bridge...")
            self.hybrid_bridge = HybridBridge(
                port=hybrid_port,
                baudrate=hybrid_baudrate
            )
            # Wire to cluster monitor (FR-009)
            if self.cluster_monitor:
                self.cluster_monitor.hybrid_bridge = self.hybrid_bridge
        else:
            self.hybrid_bridge = None

        # Initialize Hybrid Node Integration (Feature 025)
        if enable_hybrid_node:
            print("\n[Main] Initializing Hybrid Node (Analog-Digital Bridge)...")
            hybrid_config = HybridNodeConfig(
                input_device=hybrid_node_input_device,
                output_device=hybrid_node_output_device,
                phi_source=PhiSource.INTERNAL,
                enable_logging=enable_logging
            )
            self.hybrid_node = HybridNode(hybrid_config)

            # Register metrics callback to stream to metrics_streamer
            def hybrid_metrics_callback(metrics: HybridMetrics):
                # Convert HybridMetrics to metrics frame format for streaming
                asyncio.run(self.metrics_streamer.broadcast_event({
                    'type': 'hybrid_metrics',
                    'timestamp': metrics.timestamp,
                    'ici': metrics.ici,
                    'phase_coherence': metrics.phase_coherence,
                    'spectral_centroid': metrics.spectral_centroid,
                    'consciousness_level': metrics.consciousness_level,
                    'phi_phase': metrics.phi_phase,
                    'phi_depth': metrics.phi_depth,
                    'cpu_load': metrics.cpu_load,
                    'latency_ms': metrics.latency_ms
                }))

            self.hybrid_node.register_metrics_callback(hybrid_metrics_callback)
        else:
            self.hybrid_node = None

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

        # Auto-Φ Learner API endpoints (Feature 011)
        @self.app.get("/api/auto-phi/status")
        async def get_auto_phi_status():
            """Get Auto-Φ Learner status"""
            return {
                "enabled": self.auto_phi_learner.config.enabled,
                "phi_depth": self.auto_phi_learner.state.phi_depth,
                "phi_phase": self.auto_phi_learner.state.phi_phase,
                "criticality": self.auto_phi_learner.state.criticality,
                "coherence": self.auto_phi_learner.state.coherence,
                "settled": self.auto_phi_learner.state.settled
            }

        @self.app.post("/api/auto-phi/enable")
        async def set_auto_phi_enabled(enabled: bool):
            """Enable or disable Auto-Φ Learner (FR-006, SC-004)"""
            self.auto_phi_learner.set_enabled(enabled)
            return {
                "ok": True,
                "enabled": self.auto_phi_learner.config.enabled,
                "message": f"Auto-Φ Learner {'enabled' if enabled else 'disabled'}"
            }

        @self.app.get("/api/auto-phi/stats")
        async def get_auto_phi_stats():
            """Get Auto-Φ Learner performance statistics (FR-007)"""
            return self.auto_phi_learner.get_statistics()

        @self.app.post("/api/auto-phi/reset")
        async def reset_auto_phi_stats():
            """Reset Auto-Φ Learner statistics"""
            self.auto_phi_learner.reset_statistics()
            return {"ok": True, "message": "Statistics reset"}

        @self.app.get("/api/auto-phi/logs")
        async def export_auto_phi_logs():
            """Export Auto-Φ Learner performance logs"""
            return self.auto_phi_learner.export_logs()

        # Criticality Balancer API endpoints (Feature 012)
        @self.app.get("/api/criticality-balancer/status")
        async def get_criticality_balancer_status():
            """Get Criticality Balancer status"""
            return self.criticality_balancer.get_current_state()

        @self.app.post("/api/criticality-balancer/enable")
        async def set_criticality_balancer_enabled(enabled: bool):
            """Enable or disable Criticality Balancer (FR-007, SC-004)"""
            self.criticality_balancer.set_enabled(enabled)
            return {
                "ok": True,
                "enabled": self.criticality_balancer.config.enabled,
                "message": f"Criticality Balancer {'enabled' if enabled else 'disabled'}"
            }

        @self.app.get("/api/criticality-balancer/stats")
        async def get_criticality_balancer_stats():
            """Get Criticality Balancer performance statistics"""
            return self.criticality_balancer.get_statistics()

        @self.app.post("/api/criticality-balancer/reset")
        async def reset_criticality_balancer_stats():
            """Reset Criticality Balancer statistics"""
            self.criticality_balancer.reset_statistics()
            return {"ok": True, "message": "Statistics reset"}

        @self.app.get("/api/criticality-balancer/logs")
        async def export_criticality_balancer_logs():
            """Export Criticality Balancer performance logs"""
            return self.criticality_balancer.export_logs()

        # State Memory API endpoints (Feature 013)
        @self.app.get("/api/state-memory/status")
        async def get_state_memory_status():
            """Get State Memory status (FR-005)"""
            return {
                "enabled": self.state_memory.config.enabled,
                "buffer_size": len(self.state_memory.buffer),
                "max_buffer_size": self.state_memory.config.buffer_size,
                "total_frames": self.state_memory.total_frames,
                "current_bias": self.state_memory.current_bias,
                "smoothed_values": self.state_memory.get_smoothed_values()
            }

        @self.app.post("/api/state-memory/enable")
        async def set_state_memory_enabled(enabled: bool):
            """Enable or disable State Memory (FR-006, SC-004)"""
            self.state_memory.set_enabled(enabled)
            return {
                "ok": True,
                "enabled": self.state_memory.config.enabled,
                "message": f"State Memory {'enabled' if enabled else 'disabled'}"
            }

        @self.app.get("/api/state-memory/stats")
        async def get_state_memory_stats():
            """Get State Memory statistics (FR-005)"""
            return self.state_memory.get_statistics()

        @self.app.get("/api/state-memory/trend")
        async def get_state_memory_trend():
            """Get trend summary (FR-003, FR-005)"""
            return self.state_memory.get_trend_summary()

        @self.app.post("/api/state-memory/reset")
        async def reset_state_memory_buffer():
            """Reset State Memory buffer (FR-007)"""
            self.state_memory.reset_buffer()
            return {"ok": True, "message": "Buffer reset"}

        @self.app.get("/api/state-memory/buffer")
        async def export_state_memory_buffer():
            """Export State Memory buffer for analysis"""
            return self.state_memory.export_buffer()

        # State Classifier API endpoints (Feature 015)
        @self.app.get("/api/state-classifier/status")
        async def get_state_classifier_status():
            """Get current consciousness state (FR-002)"""
            return self.state_classifier.get_current_state()

        @self.app.get("/api/state-classifier/stats")
        async def get_state_classifier_stats():
            """Get State Classifier statistics (FR-005)"""
            return self.state_classifier.get_statistics()

        @self.app.get("/api/state-classifier/transitions")
        async def get_state_classifier_transitions(n: int = 512):
            """Get recent transition history (FR-004)"""
            return {
                "transitions": self.state_classifier.get_transition_history(n)
            }

        @self.app.get("/api/state-classifier/matrix")
        async def get_state_classifier_matrix():
            """Get transition probability matrix (FR-004)"""
            matrix = self.state_classifier.get_transition_matrix()
            return {"matrix": matrix.tolist()}

        @self.app.post("/api/state-classifier/reset")
        async def reset_state_classifier():
            """Reset State Classifier state"""
            self.state_classifier.reset()
            return {"ok": True, "message": "State classifier reset"}

        # Predictive Model API endpoints (Feature 016)
        @self.app.get("/api/predictive-model/forecast")
        async def get_predictive_model_forecast():
            """Get latest forecast (FR-005)"""
            if not self.predictive_model:
                return {"ok": False, "message": "Predictive Model not enabled"}

            forecast = self.predictive_model.get_last_forecast()
            if forecast:
                return forecast
            else:
                return {"ok": False, "message": "No forecast available yet"}

        @self.app.get("/api/predictive-model/stats")
        async def get_predictive_model_stats():
            """Get prediction statistics (FR-007, SC-001, SC-002, SC-004)"""
            if not self.predictive_model:
                return {"ok": False, "message": "Predictive Model not enabled"}

            return self.predictive_model.get_statistics()

        @self.app.post("/api/predictive-model/reset")
        async def reset_predictive_model():
            """Reset Predictive Model state"""
            if not self.predictive_model:
                return {"ok": False, "message": "Predictive Model not enabled"}

            self.predictive_model.reset()
            return {"ok": True, "message": "Predictive model reset"}

        # Session Recorder API endpoints (Feature 017)
        @self.app.post("/api/record/start")
        async def start_recording():
            """Start session recording (FR-006)"""
            if not self.session_recorder:
                return {"ok": False, "message": "Session Recorder not enabled"}

            success = self.session_recorder.start_recording()
            if success:
                status = self.session_recorder.get_status()
                return {
                    "ok": True,
                    "message": "Recording started",
                    "session_name": status['session_name'],
                    "session_path": status['session_path']
                }
            else:
                return {
                    "ok": False,
                    "message": self.session_recorder.last_error or "Failed to start recording"
                }

        @self.app.post("/api/record/stop")
        async def stop_recording():
            """Stop session recording (FR-006)"""
            if not self.session_recorder:
                return {"ok": False, "message": "Session Recorder not enabled"}

            success = self.session_recorder.stop_recording()
            if success:
                status = self.session_recorder.get_status()
                return {
                    "ok": True,
                    "message": "Recording stopped",
                    "statistics": status.get('statistics', {})
                }
            else:
                return {
                    "ok": False,
                    "message": self.session_recorder.last_error or "Failed to stop recording"
                }

        @self.app.get("/api/record/status")
        async def get_recording_status():
            """Get recording status (FR-006)"""
            if not self.session_recorder:
                return {"ok": False, "message": "Session Recorder not enabled"}

            return self.session_recorder.get_status()

        @self.app.get("/api/record/sessions")
        async def list_sessions():
            """List all recorded sessions (FR-006)"""
            if not self.session_recorder:
                return {"ok": False, "message": "Session Recorder not enabled"}

            sessions = self.session_recorder.list_sessions()
            return {
                "ok": True,
                "sessions": sessions,
                "count": len(sessions)
            }

        @self.app.get("/api/record/estimate")
        async def estimate_size(duration: float = 60.0):
            """Estimate recording size (FR-007)"""
            if not self.session_recorder:
                return {"ok": False, "message": "Session Recorder not enabled"}

            estimate = self.session_recorder.get_size_estimate(duration)
            return {
                "ok": True,
                "duration_seconds": duration,
                **estimate
            }

        # Timeline Player API endpoints (Feature 018)
        @self.app.post("/api/playback/load")
        async def load_session_for_playback(session_path: str):
            """Load recorded session for playback (FR-002)"""
            if not self.timeline_player:
                return {"ok": False, "message": "Timeline Player not enabled"}

            success = self.timeline_player.load_session(session_path)
            if success:
                status = self.timeline_player.get_status()
                return {
                    "ok": True,
                    "message": "Session loaded",
                    "duration": status.get('total_duration', 0),
                    "session_path": session_path
                }
            else:
                return {
                    "ok": False,
                    "message": self.timeline_player.last_error or "Failed to load session"
                }

        @self.app.post("/api/playback/play")
        async def start_playback():
            """Start playback (FR-003, SC-001)"""
            if not self.timeline_player:
                return {"ok": False, "message": "Timeline Player not enabled"}

            success = self.timeline_player.play()
            if success:
                return {"ok": True, "message": "Playback started"}
            else:
                return {"ok": False, "message": "Failed to start playback"}

        @self.app.post("/api/playback/pause")
        async def pause_playback():
            """Pause playback (FR-003, SC-001)"""
            if not self.timeline_player:
                return {"ok": False, "message": "Timeline Player not enabled"}

            success = self.timeline_player.pause()
            if success:
                return {"ok": True, "message": "Playback paused"}
            else:
                return {"ok": False, "message": "Failed to pause playback"}

        @self.app.post("/api/playback/stop")
        async def stop_playback():
            """Stop playback (FR-003, SC-001)"""
            if not self.timeline_player:
                return {"ok": False, "message": "Timeline Player not enabled"}

            success = self.timeline_player.stop()
            if success:
                return {"ok": True, "message": "Playback stopped"}
            else:
                return {"ok": False, "message": "Failed to stop playback"}

        @self.app.post("/api/playback/seek")
        async def seek_playback(time: float):
            """Seek to specific time (FR-003, SC-002)"""
            if not self.timeline_player:
                return {"ok": False, "message": "Timeline Player not enabled"}

            success = self.timeline_player.seek(time)
            if success:
                return {"ok": True, "message": f"Seeked to {time:.2f}s"}
            else:
                return {"ok": False, "message": "Failed to seek"}

        @self.app.post("/api/playback/speed")
        async def set_playback_speed(speed: float):
            """Set playback speed (FR-003, SC-003)"""
            if not self.timeline_player:
                return {"ok": False, "message": "Timeline Player not enabled"}

            success = self.timeline_player.set_speed(speed)
            if success:
                return {"ok": True, "message": f"Speed set to {speed}x"}
            else:
                return {"ok": False, "message": "Failed to set speed"}

        @self.app.post("/api/playback/range")
        async def set_playback_range(start: float, end: float):
            """Set playback range (FR-003)"""
            if not self.timeline_player:
                return {"ok": False, "message": "Timeline Player not enabled"}

            success = self.timeline_player.set_range(start, end)
            if success:
                return {"ok": True, "message": f"Range set to [{start:.2f}, {end:.2f}]"}
            else:
                return {"ok": False, "message": "Failed to set range"}

        @self.app.post("/api/playback/loop")
        async def set_playback_loop(enabled: bool):
            """Enable or disable loop (FR-003)"""
            if not self.timeline_player:
                return {"ok": False, "message": "Timeline Player not enabled"}

            success = self.timeline_player.set_loop(enabled)
            if success:
                return {"ok": True, "message": f"Loop {'enabled' if enabled else 'disabled'}"}
            else:
                return {"ok": False, "message": "Failed to set loop"}

        @self.app.get("/api/playback/status")
        async def get_playback_status():
            """Get playback status (FR-003, SC-004)"""
            if not self.timeline_player:
                return {"ok": False, "message": "Timeline Player not enabled"}

            return self.timeline_player.get_status()

        # Data Exporter API endpoints (Feature 019)
        @self.app.post("/api/export")
        async def export_session(
            session_path: str,
            format: str,
            output_name: Optional[str] = None,
            time_range_start: Optional[float] = None,
            time_range_end: Optional[float] = None,
            compress: bool = True
        ):
            """
            Export session to specified format (FR-005)

            Args:
                session_path: Path to session folder
                format: Export format (csv, json, hdf5, mp4)
                output_name: Optional output filename (without extension)
                time_range_start: Optional start time in seconds (FR-004)
                time_range_end: Optional end time in seconds (FR-004)
                compress: Enable ZIP compression (FR-007)
            """
            if not self.data_exporter:
                return {"ok": False, "message": "Data Exporter not enabled"}

            try:
                # Parse format
                export_format = ExportFormat(format.lower())

                # Create time range tuple if specified
                time_range = None
                if time_range_start is not None and time_range_end is not None:
                    time_range = (time_range_start, time_range_end)

                # Create export request
                request = ExportRequest(
                    session_path=session_path,
                    format=export_format,
                    output_name=output_name,
                    time_range=time_range,
                    compress=compress
                )

                # Perform export
                result = self.data_exporter.export_session(request)

                return result

            except ValueError as e:
                return {"ok": False, "message": f"Invalid format: {format}"}
            except Exception as e:
                return {"ok": False, "message": str(e)}

        @self.app.get("/api/export/list")
        async def list_exported_files():
            """List all exported files"""
            if not self.data_exporter:
                return {"ok": False, "message": "Data Exporter not enabled"}

            exports = self.data_exporter.list_exports()
            return {
                "ok": True,
                "exports": exports,
                "count": len(exports)
            }

        @self.app.get("/api/export/stats")
        async def get_export_statistics():
            """Get export statistics"""
            if not self.data_exporter:
                return {"ok": False, "message": "Data Exporter not enabled"}

            stats = self.data_exporter.get_statistics()
            return {
                "ok": True,
                **stats
            }

        # Node Synchronizer API endpoints (Feature 020)
        @self.app.post("/api/node/register")
        async def register_node(node_id: str, node_info: Dict):
            """Register client node (master only) (FR-007)"""
            if not self.node_sync:
                return {"ok": False, "message": "Node Synchronizer not enabled"}

            if self.node_sync.role != NodeRole.MASTER:
                return {"ok": False, "message": "Only master can register clients"}

            self.node_sync.register_client(node_id, node_info)
            return {
                "ok": True,
                "message": f"Node {node_id} registered"
            }

        @self.app.post("/api/node/unregister")
        async def unregister_node(node_id: str):
            """Unregister client node (master only) (FR-007)"""
            if not self.node_sync:
                return {"ok": False, "message": "Node Synchronizer not enabled"}

            if self.node_sync.role != NodeRole.MASTER:
                return {"ok": False, "message": "Only master can unregister clients"}

            self.node_sync.unregister_client(node_id)
            return {
                "ok": True,
                "message": f"Node {node_id} unregistered"
            }

        @self.app.get("/api/node/status")
        async def get_node_status():
            """Get node synchronizer status (FR-007, FR-008)"""
            if not self.node_sync:
                return {"ok": False, "message": "Node Synchronizer not enabled"}

            status = self.node_sync.get_status()
            return {
                "ok": True,
                **status
            }

        @self.app.get("/api/node/stats")
        async def get_node_statistics():
            """Get node synchronizer statistics (SC-001, SC-002)"""
            if not self.node_sync:
                return {"ok": False, "message": "Node Synchronizer not enabled"}

            stats = self.node_sync.get_statistics()
            return {
                "ok": True,
                **stats
            }

        @self.app.post("/api/node/start")
        async def start_node_sync():
            """Start node synchronizer"""
            if not self.node_sync:
                return {"ok": False, "message": "Node Synchronizer not enabled"}

            await self.node_sync.start()
            return {
                "ok": True,
                "message": "Node synchronizer started"
            }

        @self.app.post("/api/node/stop")
        async def stop_node_sync():
            """Stop node synchronizer"""
            if not self.node_sync:
                return {"ok": False, "message": "Node Synchronizer not enabled"}

            await self.node_sync.stop()
            return {
                "ok": True,
                "message": "Node synchronizer stopped"
            }

        # PhaseNet Protocol API endpoints (Feature 021)
        @self.app.post("/api/network/start")
        async def start_phasenet():
            """Start PhaseNet node (FR-008)"""
            if not self.phasenet:
                return {"ok": False, "message": "PhaseNet not enabled"}

            self.phasenet.start()
            return {
                "ok": True,
                "message": "PhaseNet started",
                "node_id": self.phasenet.node_id
            }

        @self.app.post("/api/network/stop")
        async def stop_phasenet():
            """Stop PhaseNet node (FR-008)"""
            if not self.phasenet:
                return {"ok": False, "message": "PhaseNet not enabled"}

            self.phasenet.stop()
            return {
                "ok": True,
                "message": "PhaseNet stopped"
            }

        @self.app.get("/api/network/status")
        async def get_network_status():
            """Get network status (FR-008)"""
            if not self.phasenet:
                return {"ok": False, "message": "PhaseNet not enabled"}

            status = self.phasenet.get_status()
            return {
                "ok": True,
                **status
            }

        @self.app.get("/api/network/stats")
        async def get_network_statistics():
            """Get network statistics (SC-001, SC-002)"""
            if not self.phasenet:
                return {"ok": False, "message": "PhaseNet not enabled"}

            stats = self.phasenet.get_statistics()
            return {
                "ok": True,
                **stats
            }

        @self.app.post("/api/network/update-phase")
        async def update_network_phase(
            phi_phase: float,
            phi_depth: float,
            criticality: float,
            coherence: float,
            ici: float
        ):
            """Manually update phase on network (FR-004)"""
            if not self.phasenet:
                return {"ok": False, "message": "PhaseNet not enabled"}

            self.phasenet.update_phase(phi_phase, phi_depth, criticality, coherence, ici)
            return {
                "ok": True,
                "message": "Phase updated"
            }

        # Cluster Monitor API endpoints (Feature 022)
        @self.app.get("/api/cluster/nodes")
        async def get_cluster_nodes():
            """Get list of all nodes in cluster (FR-003, SC-001)"""
            if not self.cluster_monitor:
                return {"ok": False, "message": "Cluster Monitor not enabled"}

            nodes = self.cluster_monitor.get_nodes_list()
            return {
                "ok": True,
                "nodes": nodes,
                "count": len(nodes)
            }

        @self.app.get("/api/cluster/nodes/{node_id}")
        async def get_cluster_node_detail(node_id: str):
            """Get detailed node info with history (FR-003, SC-003)"""
            if not self.cluster_monitor:
                return {"ok": False, "message": "Cluster Monitor not enabled"}

            detail = self.cluster_monitor.get_node_detail(node_id)
            if detail:
                return {
                    "ok": True,
                    **detail
                }
            else:
                return {"ok": False, "message": f"Node {node_id} not found"}

        @self.app.post("/api/cluster/nodes/{node_id}/promote")
        async def promote_cluster_node(node_id: str, token: Optional[str] = None):
            """Promote node to master (FR-003, SC-002, SC-005)"""
            if not self.cluster_monitor:
                return {"ok": False, "message": "Cluster Monitor not enabled"}

            result = self.cluster_monitor.promote_node(node_id, token)
            return result

        @self.app.post("/api/cluster/nodes/{node_id}/quarantine")
        async def quarantine_cluster_node(node_id: str, token: Optional[str] = None):
            """Quarantine node (FR-003, SC-002, SC-005)"""
            if not self.cluster_monitor:
                return {"ok": False, "message": "Cluster Monitor not enabled"}

            result = self.cluster_monitor.quarantine_node(node_id, token)
            return result

        @self.app.post("/api/cluster/nodes/{node_id}/restart")
        async def restart_cluster_node(node_id: str, token: Optional[str] = None):
            """Restart node (FR-003, SC-002, SC-005)"""
            if not self.cluster_monitor:
                return {"ok": False, "message": "Cluster Monitor not enabled"}

            result = self.cluster_monitor.restart_node(node_id, token)
            return result

        @self.app.get("/api/cluster/stats")
        async def get_cluster_statistics():
            """Get cluster statistics (FR-001)"""
            if not self.cluster_monitor:
                return {"ok": False, "message": "Cluster Monitor not enabled"}

            stats = self.cluster_monitor.get_statistics()
            return {
                "ok": True,
                **stats
            }

        # Hardware Interface API endpoints (Feature 023)
        @self.app.get("/api/hardware/devices")
        async def list_hardware_devices():
            """List available serial devices (FR-007)"""
            if not self.hw_interface:
                return {"ok": False, "message": "Hardware Interface not enabled"}

            devices = self.hw_interface.list_devices()
            return {
                "ok": True,
                "devices": devices,
                "count": len(devices)
            }

        @self.app.post("/api/hardware/connect")
        async def connect_hardware(port: Optional[str] = None):
            """Connect to hardware device (FR-007)"""
            if not self.hw_interface:
                return {"ok": False, "message": "Hardware Interface not enabled"}

            # Update port if provided
            if port:
                self.hw_interface.port = port

            success = self.hw_interface.connect()
            if success:
                version = self.hw_interface.get_version()
                return {
                    "ok": True,
                    "message": "Connected to hardware",
                    "port": self.hw_interface.port,
                    "baudrate": self.hw_interface.baudrate,
                    "firmware_version": version
                }
            else:
                return {
                    "ok": False,
                    "message": "Failed to connect to hardware"
                }

        @self.app.post("/api/hardware/disconnect")
        async def disconnect_hardware():
            """Disconnect from hardware device"""
            if not self.hw_interface:
                return {"ok": False, "message": "Hardware Interface not enabled"}

            self.hw_interface.disconnect()
            return {
                "ok": True,
                "message": "Disconnected from hardware"
            }

        @self.app.post("/api/hardware/start")
        async def start_hardware():
            """Start hardware bridge (FR-002)"""
            if not self.hw_interface:
                return {"ok": False, "message": "Hardware Interface not enabled"}

            success = self.hw_interface.start()
            if success:
                return {
                    "ok": True,
                    "message": "Hardware bridge started"
                }
            else:
                return {
                    "ok": False,
                    "message": "Failed to start hardware bridge"
                }

        @self.app.post("/api/hardware/stop")
        async def stop_hardware():
            """Stop hardware bridge"""
            if not self.hw_interface:
                return {"ok": False, "message": "Hardware Interface not enabled"}

            success = self.hw_interface.stop()
            if success:
                return {
                    "ok": True,
                    "message": "Hardware bridge stopped"
                }
            else:
                return {
                    "ok": False,
                    "message": "Failed to stop hardware bridge"
                }

        @self.app.get("/api/hardware/status")
        async def get_hardware_status():
            """Get hardware link status (FR-008)"""
            if not self.hw_interface:
                return {"ok": False, "message": "Hardware Interface not enabled"}

            return {
                "ok": True,
                "is_connected": self.hw_interface.is_connected,
                "is_running": self.hw_interface.is_running,
                "port": self.hw_interface.port,
                "baudrate": self.hw_interface.baudrate,
                "link_status": self.hw_interface.stats.link_status
            }

        @self.app.get("/api/hardware/stats")
        async def get_hardware_statistics():
            """Get hardware statistics (SC-001, SC-002)"""
            if not self.hw_interface:
                return {"ok": False, "message": "Hardware Interface not enabled"}

            stats = self.hw_interface.get_statistics()
            return {
                "ok": True,
                **stats
            }

        @self.app.post("/api/hardware/self-test")
        async def run_hardware_self_test():
            """Run hardware self-test (FR-010, SC-001)"""
            if not self.hw_interface:
                return {"ok": False, "message": "Hardware Interface not enabled"}

            passed, latency_us, jitter_us = self.hw_interface.self_test()
            return {
                "ok": True,
                "passed": passed,
                "latency_us": latency_us,
                "jitter_us": jitter_us,
                "meets_sc001": latency_us <= 40 and jitter_us <= 5
            }

        @self.app.post("/api/hardware/calibrate")
        async def calibrate_hardware_drift():
            """Calibrate clock drift (FR-005)"""
            if not self.hw_interface:
                return {"ok": False, "message": "Hardware Interface not enabled"}

            drift_ppm = self.hw_interface.calibrate_drift()
            return {
                "ok": True,
                "drift_ppm": drift_ppm,
                "message": f"Clock drift: {drift_ppm:.3f} ppm"
            }

        @self.app.post("/api/hardware/reset-stats")
        async def reset_hardware_statistics():
            """Reset hardware statistics counters"""
            if not self.hw_interface:
                return {"ok": False, "message": "Hardware Interface not enabled"}

            success = self.hw_interface.reset_statistics()
            if success:
                return {
                    "ok": True,
                    "message": "Statistics reset"
                }
            else:
                return {
                    "ok": False,
                    "message": "Failed to reset statistics"
                }

        # Hybrid Analog-DSP Node API endpoints (Feature 024)
        @self.app.get("/api/hybrid/devices")
        async def list_hybrid_devices():
            """List available serial devices (FR-005)"""
            if not self.hybrid_bridge:
                return {"ok": False, "message": "Hybrid Bridge not enabled"}

            devices = self.hybrid_bridge.list_devices()
            return {
                "ok": True,
                "devices": devices,
                "count": len(devices)
            }

        @self.app.post("/api/hybrid/connect")
        async def connect_hybrid(port: Optional[str] = None):
            """Connect to hybrid node (FR-005)"""
            if not self.hybrid_bridge:
                return {"ok": False, "message": "Hybrid Bridge not enabled"}

            # Update port if provided
            if port:
                self.hybrid_bridge.port = port

            success = self.hybrid_bridge.connect()
            if success:
                version = self.hybrid_bridge.get_version()
                return {
                    "ok": True,
                    "message": "Connected to hybrid node",
                    "port": self.hybrid_bridge.port,
                    "baudrate": self.hybrid_bridge.baudrate,
                    "firmware_version": version
                }
            else:
                return {
                    "ok": False,
                    "message": "Failed to connect to hybrid node"
                }

        @self.app.post("/api/hybrid/disconnect")
        async def disconnect_hybrid():
            """Disconnect from hybrid node"""
            if not self.hybrid_bridge:
                return {"ok": False, "message": "Hybrid Bridge not enabled"}

            self.hybrid_bridge.disconnect()
            return {
                "ok": True,
                "message": "Disconnected from hybrid node"
            }

        @self.app.post("/api/hybrid/start")
        async def start_hybrid():
            """Start hybrid node processing (FR-001)"""
            if not self.hybrid_bridge:
                return {"ok": False, "message": "Hybrid Bridge not enabled"}

            success = self.hybrid_bridge.start()
            if success:
                return {
                    "ok": True,
                    "message": "Hybrid node started"
                }
            else:
                return {
                    "ok": False,
                    "message": "Failed to start hybrid node"
                }

        @self.app.post("/api/hybrid/stop")
        async def stop_hybrid():
            """Stop hybrid node processing"""
            if not self.hybrid_bridge:
                return {"ok": False, "message": "Hybrid Bridge not enabled"}

            success = self.hybrid_bridge.stop()
            if success:
                return {
                    "ok": True,
                    "message": "Hybrid node stopped"
                }
            else:
                return {
                    "ok": False,
                    "message": "Failed to stop hybrid node"
                }

        @self.app.get("/api/hybrid/status")
        async def get_hybrid_status():
            """Get hybrid node status (FR-009)"""
            if not self.hybrid_bridge:
                return {"ok": False, "message": "Hybrid Bridge not enabled"}

            status = self.hybrid_bridge.get_status()
            return {
                "ok": True,
                "is_connected": self.hybrid_bridge.is_connected,
                "is_running": self.hybrid_bridge.is_running,
                "port": self.hybrid_bridge.port,
                "baudrate": self.hybrid_bridge.baudrate,
                **status
            }

        @self.app.get("/api/hybrid/dsp-metrics")
        async def get_hybrid_dsp_metrics():
            """Get DSP metrics (ICI, coherence, spectral analysis) (FR-003)"""
            if not self.hybrid_bridge:
                return {"ok": False, "message": "Hybrid Bridge not enabled"}

            metrics = self.hybrid_bridge.get_dsp_metrics()
            if metrics:
                return {
                    "ok": True,
                    **metrics
                }
            else:
                return {
                    "ok": False,
                    "message": "Failed to get DSP metrics"
                }

        @self.app.get("/api/hybrid/safety")
        async def get_hybrid_safety():
            """Get safety telemetry (FR-007)"""
            if not self.hybrid_bridge:
                return {"ok": False, "message": "Hybrid Bridge not enabled"}

            safety = self.hybrid_bridge.get_safety()
            if safety:
                return {
                    "ok": True,
                    **safety
                }
            else:
                return {
                    "ok": False,
                    "message": "Failed to get safety telemetry"
                }

        @self.app.get("/api/hybrid/stats")
        async def get_hybrid_statistics():
            """Get hybrid node statistics (SC-001, SC-002, SC-003)"""
            if not self.hybrid_bridge:
                return {"ok": False, "message": "Hybrid Bridge not enabled"}

            stats = self.hybrid_bridge.get_statistics()
            return {
                "ok": True,
                **stats
            }

        @self.app.post("/api/hybrid/set-preamp-gain")
        async def set_hybrid_preamp_gain(gain: float):
            """Set analog preamp gain (FR-002)"""
            if not self.hybrid_bridge:
                return {"ok": False, "message": "Hybrid Bridge not enabled"}

            success = self.hybrid_bridge.set_preamp_gain(gain)
            if success:
                return {
                    "ok": True,
                    "message": f"Preamp gain set to {gain:.2f}"
                }
            else:
                return {
                    "ok": False,
                    "message": "Failed to set preamp gain"
                }

        @self.app.post("/api/hybrid/set-control-voltage")
        async def set_hybrid_control_voltage(cv1: float, cv2: float, phi_phase: float = 0.0, phi_depth: float = 0.0):
            """Set control voltage outputs (FR-004)"""
            if not self.hybrid_bridge:
                return {"ok": False, "message": "Hybrid Bridge not enabled"}

            from hybrid_bridge import ControlVoltage
            cv = ControlVoltage(cv1=cv1, cv2=cv2, phi_phase=phi_phase, phi_depth=phi_depth)
            success = self.hybrid_bridge.set_control_voltage(cv)
            if success:
                return {
                    "ok": True,
                    "message": "Control voltage set",
                    "cv1": cv1,
                    "cv2": cv2,
                    "phi_phase": phi_phase,
                    "phi_depth": phi_depth
                }
            else:
                return {
                    "ok": False,
                    "message": "Failed to set control voltage"
                }

        @self.app.post("/api/hybrid/calibrate")
        async def calibrate_hybrid():
            """Run calibration routine (FR-008, SC-001)"""
            if not self.hybrid_bridge:
                return {"ok": False, "message": "Hybrid Bridge not enabled"}

            calibration = self.hybrid_bridge.calibrate()
            if calibration:
                return {
                    "ok": True,
                    "message": "Calibration complete",
                    **calibration,
                    "meets_sc001": calibration.get('total_latency_us', 9999) <= 2000
                }
            else:
                return {
                    "ok": False,
                    "message": "Calibration failed"
                }

        @self.app.post("/api/hybrid/emergency-shutdown")
        async def hybrid_emergency_shutdown(reason: str = "Manual shutdown"):
            """Emergency shutdown hybrid node (FR-007)"""
            if not self.hybrid_bridge:
                return {"ok": False, "message": "Hybrid Bridge not enabled"}

            success = self.hybrid_bridge.emergency_shutdown(reason)
            if success:
                return {
                    "ok": True,
                    "message": f"Emergency shutdown executed: {reason}"
                }
            else:
                return {
                    "ok": False,
                    "message": "Failed to execute emergency shutdown"
                }

        @self.app.post("/api/hybrid/reset-stats")
        async def reset_hybrid_statistics():
            """Reset hybrid node statistics counters"""
            if not self.hybrid_bridge:
                return {"ok": False, "message": "Hybrid Bridge not enabled"}

            success = self.hybrid_bridge.reset_statistics()
            if success:
                return {
                    "ok": True,
                    "message": "Statistics reset"
                }
            else:
                return {
                    "ok": False,
                    "message": "Failed to reset statistics"
                }

        # Hybrid Node Integration API endpoints (Feature 025)
        @self.app.get("/api/hybrid-node/devices")
        async def list_hybrid_node_audio_devices():
            """List available audio devices for hybrid node (FR-005)"""
            if not self.hybrid_node:
                return {"ok": False, "message": "Hybrid Node not enabled"}

            devices = HybridNode.list_audio_devices()
            return {
                "ok": True,
                "devices": devices,
                "count": len(devices)
            }

        @self.app.post("/api/hybrid-node/start")
        async def start_hybrid_node():
            """Start hybrid mode processing (FR-003, SC-001)"""
            if not self.hybrid_node:
                return {"ok": False, "message": "Hybrid Node not enabled"}

            success = self.hybrid_node.start()
            if success:
                return {
                    "ok": True,
                    "message": "Hybrid mode started"
                }
            else:
                return {
                    "ok": False,
                    "message": "Failed to start hybrid mode"
                }

        @self.app.post("/api/hybrid-node/stop")
        async def stop_hybrid_node():
            """Stop hybrid mode processing"""
            if not self.hybrid_node:
                return {"ok": False, "message": "Hybrid Node not enabled"}

            success = self.hybrid_node.stop()
            if success:
                return {
                    "ok": True,
                    "message": "Hybrid mode stopped"
                }
            else:
                return {
                    "ok": False,
                    "message": "Failed to stop hybrid mode"
                }

        @self.app.get("/api/hybrid-node/status")
        async def get_hybrid_node_status():
            """Get hybrid node status (FR-007)"""
            if not self.hybrid_node:
                return {"ok": False, "message": "Hybrid Node not enabled"}

            metrics = self.hybrid_node.get_current_metrics()
            stats = self.hybrid_node.get_statistics()

            if metrics:
                return {
                    "ok": True,
                    "is_running": self.hybrid_node.is_running,
                    "metrics": {
                        "timestamp": metrics.timestamp,
                        "ici": metrics.ici,
                        "phase_coherence": metrics.phase_coherence,
                        "spectral_centroid": metrics.spectral_centroid,
                        "consciousness_level": metrics.consciousness_level,
                        "phi_phase": metrics.phi_phase,
                        "phi_depth": metrics.phi_depth,
                        "cpu_load": metrics.cpu_load,
                        "latency_ms": metrics.latency_ms,
                        "dropouts": metrics.dropouts
                    },
                    "statistics": stats
                }
            else:
                return {
                    "ok": True,
                    "is_running": self.hybrid_node.is_running,
                    "metrics": None,
                    "statistics": stats
                }

        @self.app.post("/api/hybrid-node/phi-source")
        async def set_hybrid_node_phi_source(source: str):
            """Set Φ modulation source (FR-004, User Story 2)"""
            if not self.hybrid_node:
                return {"ok": False, "message": "Hybrid Node not enabled"}

            try:
                phi_source = PhiSource(source)
                self.hybrid_node.set_phi_source(phi_source)
                return {
                    "ok": True,
                    "message": f"Φ source set to {source}",
                    "source": source
                }
            except ValueError:
                return {
                    "ok": False,
                    "message": f"Invalid Φ source: {source}. Valid: manual, microphone, sensor, internal"
                }

        @self.app.post("/api/hybrid-node/phi-manual")
        async def set_hybrid_node_phi_manual(phase: float, depth: float):
            """Set manual Φ values (FR-004, User Story 2)"""
            if not self.hybrid_node:
                return {"ok": False, "message": "Hybrid Node not enabled"}

            self.hybrid_node.set_phi_manual(phase, depth)
            return {
                "ok": True,
                "message": "Manual Φ values set",
                "phase": phase,
                "depth": depth
            }

        @self.app.get("/api/hybrid-node/stats")
        async def get_hybrid_node_statistics():
            """Get hybrid node performance statistics (SC-004)"""
            if not self.hybrid_node:
                return {"ok": False, "message": "Hybrid Node not enabled"}

            stats = self.hybrid_node.get_statistics()
            return {
                "ok": True,
                **stats
            }

        @self.app.post("/api/hybrid-node/reset-stats")
        async def reset_hybrid_node_statistics():
            """Reset hybrid node statistics"""
            if not self.hybrid_node:
                return {"ok": False, "message": "Hybrid Node not enabled"}

            self.hybrid_node.reset_statistics()
            return {
                "ok": True,
                "message": "Statistics reset"
            }

        # Sensor Binding API endpoints (Feature 011)
        @self.app.post("/api/sensor-binding/enable")
        async def enable_sensor_binding():
            """Enable sensor binding with PhiRouter (Feature 011)"""
            if not self.hybrid_node:
                return {"ok": False, "message": "Hybrid Node not enabled"}

            success = self.hybrid_node.enable_sensor_binding()
            return {
                "ok": success,
                "message": "Sensor binding enabled" if success else "Failed to enable sensor binding"
            }

        @self.app.post("/api/sensor-binding/disable")
        async def disable_sensor_binding():
            """Disable sensor binding"""
            if not self.hybrid_node:
                return {"ok": False, "message": "Hybrid Node not enabled"}

            self.hybrid_node.disable_sensor_binding()
            return {
                "ok": True,
                "message": "Sensor binding disabled"
            }

        @self.app.get("/api/sensor-binding/status")
        async def get_sensor_binding_status():
            """Get sensor binding status (FR-004)"""
            if not self.hybrid_node:
                return {"ok": False, "message": "Hybrid Node not enabled"}

            status = self.hybrid_node.get_sensor_status()
            return {
                "ok": True,
                **status
            }

        @self.app.get("/api/sensor-binding/midi-devices")
        async def list_midi_devices():
            """List available MIDI devices (User Story 1)"""
            devices = HybridNode.list_midi_devices()
            return {
                "ok": True,
                "devices": devices,
                "count": len(devices)
            }

        @self.app.get("/api/sensor-binding/serial-devices")
        async def list_serial_devices():
            """List available serial devices (User Story 1)"""
            devices = HybridNode.list_serial_devices()
            return {
                "ok": True,
                "devices": devices,
                "count": len(devices)
            }

        @self.app.post("/api/sensor-binding/bind-midi")
        async def bind_midi_sensor(device_id: Optional[str] = None, cc_number: int = 1, channel: int = 0):
            """Bind MIDI controller as Φ source (FR-001, User Story 1)"""
            if not self.hybrid_node:
                return {"ok": False, "message": "Hybrid Node not enabled"}

            success = self.hybrid_node.bind_midi_sensor(
                device_id=device_id,
                cc_number=cc_number,
                channel=channel
            )

            return {
                "ok": success,
                "message": f"MIDI CC{cc_number} bound" if success else "Failed to bind MIDI",
                "sensor_id": f"midi_cc{cc_number}"
            }

        @self.app.post("/api/sensor-binding/bind-serial")
        async def bind_serial_sensor(device_id: Optional[str] = None, baudrate: int = 9600,
                                     input_min: float = 0.0, input_max: float = 1.0):
            """Bind serial sensor as Φ source (FR-001, User Story 1)"""
            if not self.hybrid_node:
                return {"ok": False, "message": "Hybrid Node not enabled"}

            success = self.hybrid_node.bind_serial_sensor(
                device_id=device_id,
                baudrate=baudrate,
                input_range=(input_min, input_max)
            )

            return {
                "ok": success,
                "message": f"Serial sensor bound: {device_id}" if success else "Failed to bind serial sensor",
                "sensor_id": f"serial_{device_id or 'auto'}"
            }

        @self.app.post("/api/sensor-binding/bind-audio-beat")
        async def bind_audio_beat_detector():
            """Bind audio beat detector as Φ source (FR-001)"""
            if not self.hybrid_node:
                return {"ok": False, "message": "Hybrid Node not enabled"}

            success = self.hybrid_node.bind_audio_beat_detector()

            return {
                "ok": success,
                "message": "Audio beat detector bound" if success else "Failed to bind audio beat detector",
                "sensor_id": "audio_beat"
            }

        @self.app.post("/api/sensor-binding/unbind")
        async def unbind_sensor(sensor_id: str):
            """Unbind a sensor (User Story 2)"""
            if not self.hybrid_node:
                return {"ok": False, "message": "Hybrid Node not enabled"}

            success = self.hybrid_node.unbind_sensor(sensor_id)

            return {
                "ok": success,
                "message": f"Sensor unbound: {sensor_id}" if success else f"Failed to unbind sensor: {sensor_id}"
            }

        # Metrics WebSocket endpoint
        @self.app.websocket("/ws/metrics")
        async def websocket_metrics(websocket):
            """WebSocket endpoint for real-time metrics (30 Hz)"""
            await self.metrics_streamer.handle_websocket(websocket)

        # UI Control WebSocket endpoint
        @self.app.websocket("/ws/ui")
        async def websocket_ui_control(websocket):
            """WebSocket endpoint for real-time UI parameter control"""
            from fastapi import WebSocket, WebSocketDisconnect
            import json
            import time

            await websocket.accept()
            print("[Main] UI control WebSocket connected")

            # Track last update time for rate limiting (10 Hz max)
            last_update_time = 0.0
            MIN_UPDATE_INTERVAL = 0.1  # 100ms = 10 Hz

            try:
                # Send initial parameter state
                initial_params = self.audio_server.get_current_parameters()
                await websocket.send_json({
                    "type": "state",
                    "data": initial_params
                })

                # Message loop
                while True:
                    # Receive message from client
                    message = await websocket.receive_text()
                    data = json.loads(message)

                    msg_type = data.get("type")

                    if msg_type == "set_param":
                        # Rate limiting check
                        current_time = time.time()
                        if current_time - last_update_time < MIN_UPDATE_INTERVAL:
                            # Skip update if too frequent
                            continue

                        # Extract parameters
                        param_type = data.get("param_type", "channel")  # 'channel', 'global', 'phi'
                        channel = data.get("channel")  # None for global params
                        param_name = data.get("param")
                        value = data.get("value")

                        # Update parameter
                        success = self.audio_server.update_parameter(
                            param_type=param_type,
                            channel=channel,
                            param_name=param_name,
                            value=value
                        )

                        # Send acknowledgment
                        await websocket.send_json({
                            "type": "param_updated",
                            "success": success,
                            "param_type": param_type,
                            "channel": channel,
                            "param": param_name,
                            "value": value
                        })

                        last_update_time = current_time

                    elif msg_type == "get_state":
                        # Send current parameter state
                        current_params = self.audio_server.get_current_parameters()
                        await websocket.send_json({
                            "type": "state",
                            "parameters": current_params
                        })

                    elif msg_type == "apply_preset":
                        # Apply entire preset (Feature 010: Preset Browser)
                        preset_name = data.get("preset_name", "Unknown")
                        parameters = data.get("parameters", {})

                        try:
                            # Apply all channel parameters
                            if "channels" in parameters:
                                for channel_idx, channel_params in parameters["channels"].items():
                                    channel_idx = int(channel_idx)
                                    for param_name, value in channel_params.items():
                                        self.audio_server.update_parameter(
                                            param_type="channel",
                                            channel=channel_idx,
                                            param_name=param_name,
                                            value=value
                                        )

                            # Apply global parameters
                            if "global" in parameters:
                                for param_name, value in parameters["global"].items():
                                    self.audio_server.update_parameter(
                                        param_type="global",
                                        channel=None,
                                        param_name=param_name,
                                        value=value
                                    )

                            # Apply phi parameters
                            if "phi" in parameters:
                                for param_name, value in parameters["phi"].items():
                                    self.audio_server.update_parameter(
                                        param_type="phi",
                                        channel=None,
                                        param_name=param_name,
                                        value=value
                                    )

                            # Send confirmation
                            await websocket.send_json({
                                "type": "preset_applied",
                                "success": True,
                                "preset_name": preset_name
                            })

                            print(f"[Main] Applied preset: {preset_name}")

                        except Exception as e:
                            print(f"[Main] Error applying preset: {e}")
                            await websocket.send_json({
                                "type": "preset_applied",
                                "success": False,
                                "preset_name": preset_name,
                                "error": str(e)
                            })

                    elif msg_type == "ping":
                        # Respond to ping
                        await websocket.send_json({"type": "pong"})

            except WebSocketDisconnect:
                print("[Main] UI control WebSocket disconnected")
            except Exception as e:
                print(f"[Main] UI control WebSocket error: {e}")
                import traceback
                traceback.print_exc()

        # Playback WebSocket endpoint (Feature 018)
        @self.app.websocket("/ws/playback")
        async def websocket_playback(websocket):
            """WebSocket endpoint for playback frame streaming (FR-004)"""
            from fastapi import WebSocket, WebSocketDisconnect
            import json

            if not self.timeline_player:
                await websocket.close(code=1000, reason="Timeline Player not enabled")
                return

            await websocket.accept()
            print("[Main] Playback WebSocket connected")

            # List to store this client's frames
            playback_frames = []
            playback_lock = asyncio.Lock()

            # Define frame callback to capture frames for this client
            def frame_callback(frame):
                """Capture playback frames for streaming"""
                async def enqueue():
                    async with playback_lock:
                        playback_frames.append(frame)
                        # Keep only last 10 frames to prevent memory buildup
                        if len(playback_frames) > 10:
                            playback_frames.pop(0)

                asyncio.create_task(enqueue())

            # Set the frame callback
            old_callback = self.timeline_player.frame_callback
            self.timeline_player.frame_callback = frame_callback

            try:
                # Stream frames to client
                while True:
                    # Check if there are frames to send
                    async with playback_lock:
                        if playback_frames:
                            frame = playback_frames.pop(0)
                            await websocket.send_json(frame)
                        else:
                            # No frames, wait a bit
                            await asyncio.sleep(0.033)  # ~30 Hz

            except WebSocketDisconnect:
                print("[Main] Playback WebSocket disconnected")
            except Exception as e:
                print(f"[Main] Playback WebSocket error: {e}")
                import traceback
                traceback.print_exc()
            finally:
                # Restore old callback
                self.timeline_player.frame_callback = old_callback

        # Node Sync WebSocket endpoint (Feature 020)
        @self.app.websocket("/ws/sync")
        async def websocket_node_sync(websocket):
            """WebSocket endpoint for node synchronization (FR-003)"""
            from fastapi import WebSocket, WebSocketDisconnect
            import json

            if not self.node_sync:
                await websocket.close(code=1000, reason="Node Synchronizer not enabled")
                return

            await websocket.accept()
            print("[Main] Node sync WebSocket connected")

            # Determine if this is master or client
            if self.node_sync.role == NodeRole.MASTER:
                # Master mode: broadcast sync frames to this client
                client_id = None

                try:
                    # Wait for client registration
                    data = await websocket.receive_json()
                    if data.get("type") == "register":
                        client_id = data.get("node_id", f"client_{int(time.time() * 1000)}")
                        client_info = data.get("info", {})
                        self.node_sync.register_client(client_id, client_info)

                        # Send confirmation
                        await websocket.send_json({
                            "type": "registered",
                            "node_id": client_id
                        })

                        # Broadcast loop: send sync frames to this client
                        while True:
                            # Get current state from auto-phi learner
                            if self.auto_phi_learner:
                                phi_phase = self.auto_phi_learner.state.phi_phase
                                phi_depth = self.auto_phi_learner.state.phi_depth
                                criticality = self.auto_phi_learner.state.criticality
                                coherence = self.auto_phi_learner.state.coherence
                                ici = getattr(self.audio_server, 'last_ici', 0.0)

                                # Process and broadcast
                                self.node_sync.process_local_state(
                                    phi_phase, phi_depth, criticality, coherence, ici
                                )

                                # Send sync frame
                                frame_data = {
                                    "type": "sync_frame",
                                    "phi_phase": phi_phase,
                                    "phi_depth": phi_depth,
                                    "criticality": criticality,
                                    "coherence": coherence,
                                    "ici": ici,
                                    "timestamp": time.time(),
                                    "master_timestamp": time.time(),
                                    "sequence": self.node_sync.sequence_counter - 1
                                }

                                await websocket.send_json(frame_data)

                            # Wait for next sync interval (30 Hz)
                            await asyncio.sleep(1.0 / self.node_sync.config.sync_rate)

                except WebSocketDisconnect:
                    print(f"[Main] Node sync WebSocket disconnected (client={client_id})")
                    if client_id:
                        self.node_sync.unregister_client(client_id)

            else:
                # Client mode: receive sync frames from master
                try:
                    # Register with master
                    await websocket.send_json({
                        "type": "register",
                        "node_id": self.node_sync.node_id,
                        "info": {}
                    })

                    # Receive loop
                    while True:
                        data = await websocket.receive_json()

                        if data.get("type") == "sync_frame":
                            # Process received frame
                            await self.node_sync.receive_sync_frame(data)

                            # Apply sync frame to local state
                            if self.auto_phi_learner:
                                # Update phi parameters from master
                                self.audio_server.update_parameter(
                                    param_type='phi',
                                    channel=None,
                                    param_name='depth',
                                    value=data['phi_depth']
                                )
                                self.audio_server.update_parameter(
                                    param_type='phi',
                                    channel=None,
                                    param_name='phase',
                                    value=data['phi_phase']
                                )

                except WebSocketDisconnect:
                    print("[Main] Node sync WebSocket disconnected from master")

        # Cluster Monitor WebSocket endpoint (Feature 022)
        @self.app.websocket("/ws/cluster")
        async def websocket_cluster(websocket):
            """WebSocket endpoint for cluster monitoring (FR-004, SC-001)"""
            from fastapi import WebSocket, WebSocketDisconnect
            import json

            if not self.cluster_monitor:
                await websocket.close(code=1000, reason="Cluster Monitor not enabled")
                return

            await websocket.accept()
            print("[Main] Cluster monitor WebSocket connected")

            # Add client to cluster monitor's client list
            with self.cluster_monitor.ws_client_lock:
                self.cluster_monitor.ws_clients.append(websocket)

            try:
                # Broadcast loop: send cluster updates at configured interval
                while True:
                    # Get current cluster state
                    update = {
                        "type": "cluster_update",
                        "timestamp": time.time(),
                        "nodes": self.cluster_monitor.get_nodes_list(),
                        "stats": self.cluster_monitor.get_statistics()
                    }

                    await websocket.send_json(update)

                    # Wait for next update interval (1-2 Hz)
                    await asyncio.sleep(self.cluster_monitor.config.update_interval)

            except WebSocketDisconnect:
                print("[Main] Cluster monitor WebSocket disconnected")
            except Exception as e:
                print(f"[Main] Cluster monitor WebSocket error: {e}")
            finally:
                # Remove client from cluster monitor's client list
                with self.cluster_monitor.ws_client_lock:
                    if websocket in self.cluster_monitor.ws_clients:
                        self.cluster_monitor.ws_clients.remove(websocket)

        # Hybrid Node WebSocket endpoint (Feature 025)
        @self.app.websocket("/ws/hybrid")
        async def websocket_hybrid(websocket):
            """WebSocket endpoint for hybrid node Φ and gain control (FR-004)"""
            from fastapi import WebSocket, WebSocketDisconnect
            import json

            if not self.hybrid_node:
                await websocket.close(code=1000, reason="Hybrid Node not enabled")
                return

            await websocket.accept()
            print("[Main] Hybrid node WebSocket connected")

            # Track metrics streaming
            hybrid_metrics_queue = asyncio.Queue(maxsize=100)

            # Register callback for this client
            def metrics_callback(metrics: HybridMetrics):
                try:
                    hybrid_metrics_queue.put_nowait({
                        "type": "hybrid_metrics",
                        "timestamp": metrics.timestamp,
                        "ici": metrics.ici,
                        "phase_coherence": metrics.phase_coherence,
                        "spectral_centroid": metrics.spectral_centroid,
                        "consciousness_level": metrics.consciousness_level,
                        "phi_phase": metrics.phi_phase,
                        "phi_depth": metrics.phi_depth,
                        "cpu_load": metrics.cpu_load,
                        "latency_ms": metrics.latency_ms,
                        "dropouts": metrics.dropouts
                    })
                except asyncio.QueueFull:
                    pass  # Drop if queue full

            self.hybrid_node.register_metrics_callback(metrics_callback)

            try:
                # Bidirectional communication loop
                while True:
                    # Create tasks for both sending and receiving
                    receive_task = asyncio.create_task(websocket.receive_json())
                    send_task = asyncio.create_task(hybrid_metrics_queue.get())

                    # Wait for either task to complete
                    done, pending = await asyncio.wait(
                        {receive_task, send_task},
                        return_when=asyncio.FIRST_COMPLETED
                    )

                    # Cancel pending tasks
                    for task in pending:
                        task.cancel()

                    # Handle received message (Φ control commands)
                    if receive_task in done:
                        try:
                            data = receive_task.result()
                            msg_type = data.get("type")

                            if msg_type == "set_phi_source":
                                # Change Φ source
                                source = data.get("source")
                                try:
                                    phi_source = PhiSource(source)
                                    self.hybrid_node.set_phi_source(phi_source)
                                    await websocket.send_json({
                                        "type": "phi_source_changed",
                                        "source": source,
                                        "ok": True
                                    })
                                except ValueError:
                                    await websocket.send_json({
                                        "type": "error",
                                        "message": f"Invalid Φ source: {source}",
                                        "ok": False
                                    })

                            elif msg_type == "set_phi_manual":
                                # Set manual Φ values (SC-002: latency < 2ms)
                                phase = data.get("phase", 0.0)
                                depth = data.get("depth", 0.5)
                                self.hybrid_node.set_phi_manual(phase, depth)
                                await websocket.send_json({
                                    "type": "phi_manual_updated",
                                    "phase": phase,
                                    "depth": depth,
                                    "ok": True
                                })

                            elif msg_type == "ping":
                                # Ping response
                                await websocket.send_json({"type": "pong"})

                        except Exception as e:
                            print(f"[Main] Hybrid WebSocket receive error: {e}")

                    # Handle metrics to send
                    if send_task in done:
                        try:
                            metrics_data = send_task.result()
                            await websocket.send_json(metrics_data)
                        except Exception as e:
                            print(f"[Main] Hybrid WebSocket send error: {e}")

            except WebSocketDisconnect:
                print("[Main] Hybrid node WebSocket disconnected")
            except Exception as e:
                print(f"[Main] Hybrid node WebSocket error: {e}")
            finally:
                # Unregister callback
                self.hybrid_node.unregister_metrics_callback(metrics_callback)

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

        # Start cluster monitor (Feature 022)
        if self.cluster_monitor:
            print("[Main] Starting cluster monitor...")
            self.cluster_monitor.start()
            if self.cluster_monitor.config.enable_rbac:
                print(f"[Main] Cluster Monitor Admin Token: {self.cluster_monitor.admin_token}")

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
        print("  WS   /ws/ui                         - UI control (bidirectional)")
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

        # Stop cluster monitor (Feature 022)
        if self.cluster_monitor:
            print("[Main] Stopping cluster monitor...")
            self.cluster_monitor.stop()

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
    parser.add_argument("--enable-auto-phi", action="store_true", help="Enable Auto-Phi Learner (adaptive criticality control)")
    parser.add_argument("--enable-criticality-balancer", action="store_true", help="Enable Criticality Balancer (adaptive coupling and amplitude)")
    parser.add_argument("--enable-state-memory", action="store_true", help="Enable State Memory (temporal memory and prediction)")
    parser.add_argument("--enable-state-classifier", action="store_true", help="Enable State Classifier (consciousness state classification)")
    parser.add_argument("--enable-predictive-model", action="store_true", help="Enable Predictive Model (next-state forecasting)")
    parser.add_argument("--disable-session-recorder", action="store_true", help="Disable Session Recorder (recording enabled by default)")
    parser.add_argument("--disable-timeline-player", action="store_true", help="Disable Timeline Player (playback enabled by default)")
    parser.add_argument("--disable-data-exporter", action="store_true", help="Disable Data Exporter (export enabled by default)")
    parser.add_argument("--enable-node-sync", action="store_true", help="Enable Node Synchronizer (distributed phase-locked operation)")
    parser.add_argument("--node-sync-role", default="master", choices=["master", "client"], help="Node role: master (authority) or client (subscriber)")
    parser.add_argument("--node-sync-master-url", help="Master WebSocket URL for client nodes (e.g., ws://192.168.1.100:8000/ws/sync)")
    parser.add_argument("--enable-phasenet", action="store_true", help="Enable PhaseNet Protocol (mesh network for distributed sync)")
    parser.add_argument("--phasenet-port", type=int, default=9000, help="PhaseNet UDP port (default: 9000)")
    parser.add_argument("--phasenet-key", help="PhaseNet encryption key (enables AES-128 encryption)")
    parser.add_argument("--enable-cluster-monitor", action="store_true", help="Enable Cluster Monitor (centralized node monitoring and management)")
    parser.add_argument("--enable-hardware-bridge", action="store_true", help="Enable Hardware I²S Bridge (sync with embedded microcontrollers via serial)")
    parser.add_argument("--hardware-port", help="Serial port for hardware bridge (auto-detect if not specified)")
    parser.add_argument("--hardware-baudrate", type=int, default=115200, help="Serial baudrate for hardware bridge (default: 115200)")
    parser.add_argument("--enable-hybrid-bridge", action="store_true", help="Enable Hybrid Analog-DSP Bridge (analog signal processing with DSP analysis)")
    parser.add_argument("--hybrid-port", help="Serial port for hybrid bridge (auto-detect if not specified)")
    parser.add_argument("--hybrid-baudrate", type=int, default=115200, help="Serial baudrate for hybrid bridge (default: 115200)")
    parser.add_argument("--enable-hybrid-node", action="store_true", help="Enable Hybrid Node Integration (Feature 025: analog I/O with D-ASE engine)")
    parser.add_argument("--hybrid-node-input-device", type=int, help="Audio input device index for hybrid node (auto-detect if not specified)")
    parser.add_argument("--hybrid-node-output-device", type=int, help="Audio output device index for hybrid node (auto-detect if not specified)")
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
        enable_logging=not args.no_logging,
        enable_auto_phi=args.enable_auto_phi,
        enable_criticality_balancer=args.enable_criticality_balancer,
        enable_state_memory=args.enable_state_memory,
        enable_state_classifier=args.enable_state_classifier,
        enable_predictive_model=args.enable_predictive_model,
        enable_session_recorder=not args.disable_session_recorder,
        enable_timeline_player=not args.disable_timeline_player,
        enable_data_exporter=not args.disable_data_exporter,
        enable_node_sync=args.enable_node_sync,
        node_sync_role=args.node_sync_role,
        node_sync_master_url=args.node_sync_master_url,
        enable_phasenet=args.enable_phasenet,
        phasenet_port=args.phasenet_port,
        phasenet_key=args.phasenet_key,
        enable_cluster_monitor=args.enable_cluster_monitor,
        enable_hardware_bridge=args.enable_hardware_bridge,
        hardware_port=args.hardware_port,
        hardware_baudrate=args.hardware_baudrate,
        enable_hybrid_bridge=args.enable_hybrid_bridge,
        hybrid_port=args.hybrid_port,
        hybrid_baudrate=args.hybrid_baudrate,
        enable_hybrid_node=args.enable_hybrid_node,
        hybrid_node_input_device=args.hybrid_node_input_device,
        hybrid_node_output_device=args.hybrid_node_output_device
    )

    server.run(
        auto_start_audio=args.auto_start_audio,
        calibrate_on_start=args.calibrate
    )


if __name__ == "__main__":
    main()
