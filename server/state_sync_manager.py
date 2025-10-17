"""
StateSyncManager - Feature 017: Phi-Matrix Dashboard

Manages synchronized state across all dashboard modules with shared clock
and bidirectional WebSocket communication.

Features:
- FR-002: Synchronized clock/timestamp base across all modules
- FR-003: Bidirectional WebSocket router (< 50 ms avg)
- SC-001: Dashboard operational at <= 100 ms latency
- SC-004: No metric/UI desync > 0.1 s for > 60 s runs

Requirements:
- FR-002: All modules share synchronized clock
- FR-003: WebSocket messages < 50 ms average
- SC-004: Maintain sync < 0.1 s desync for 60+ s
"""

import time
import asyncio
import threading
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
from collections import deque
import json


@dataclass
class SyncState:
    """Synchronized state across all dashboard modules"""
    timestamp: float           # Master clock timestamp

    # Metrics state
    ici: float
    coherence: float
    criticality: float

    # Phi state
    phi_phase: float
    phi_depth: float
    phi_breathing: float

    # Chromatic state
    chromatic_enabled: bool

    # Control matrix state
    control_matrix_active: bool

    # Adaptive control state
    adaptive_enabled: bool
    adaptive_mode: Optional[str]

    # Session state
    is_recording: bool
    is_playing: bool

    # Cluster state
    cluster_nodes_count: int


@dataclass
class SyncConfig:
    """Configuration for StateSyncManager"""
    max_latency_ms: float = 100.0          # SC-001: Max acceptable latency
    max_desync_ms: float = 100.0           # SC-004: Max desync tolerance
    websocket_timeout_ms: float = 50.0     # FR-003: WebSocket message timeout
    sync_check_interval_s: float = 1.0     # How often to check sync
    enable_logging: bool = False


class StateSyncManager:
    """
    StateSyncManager - Central state synchronization manager

    Handles:
    - Unified clock synchronization (FR-002)
    - Bidirectional WebSocket routing (FR-003)
    - Pause/resume coordination (User Story 2)
    - Latency monitoring (SC-001, SC-004)
    """

    def __init__(self, config: Optional[SyncConfig] = None):
        """Initialize StateSyncManager"""
        self.config = config or SyncConfig()

        # Master clock
        self.start_time = time.time()
        self.paused = False
        self.pause_time: Optional[float] = None
        self.pause_offset = 0.0

        # Current synchronized state
        self.current_state: Optional[SyncState] = None
        self.state_lock = threading.Lock()

        # State history for desync detection
        self.state_history = deque(maxlen=100)

        # WebSocket clients
        self.ws_clients: List = []
        self.ws_lock = asyncio.Lock()

        # Latency tracking
        self.message_latencies = deque(maxlen=100)
        self.last_message_time = time.time()

        # Desync tracking
        self.desync_events: List[Dict] = []
        self.last_sync_check = time.time()

        # Background monitoring
        self.is_running = False
        self.monitor_thread: Optional[threading.Thread] = None

    def get_master_time(self) -> float:
        """
        Get master clock timestamp (FR-002)

        Returns:
            Master timestamp accounting for pause offset
        """
        if self.paused and self.pause_time:
            return self.pause_time - self.start_time - self.pause_offset
        else:
            return time.time() - self.start_time - self.pause_offset

    def pause(self):
        """Pause all synchronized modules (User Story 2)"""
        if not self.paused:
            self.paused = True
            self.pause_time = time.time()

            if self.config.enable_logging:
                print(f"[StateSyncManager] Paused at master time {self.get_master_time():.3f}s")

    def resume(self):
        """Resume all synchronized modules (User Story 2)"""
        if self.paused and self.pause_time:
            pause_duration = time.time() - self.pause_time
            self.pause_offset += pause_duration
            self.paused = False
            self.pause_time = None

            if self.config.enable_logging:
                print(f"[StateSyncManager] Resumed after {pause_duration:.3f}s pause")

    def update_state(self, **kwargs):
        """
        Update synchronized state (FR-002)

        Args:
            **kwargs: State fields to update
        """
        with self.state_lock:
            # Get current state or create new
            if self.current_state is None:
                # Initialize with defaults
                self.current_state = SyncState(
                    timestamp=self.get_master_time(),
                    ici=0.5,
                    coherence=0.5,
                    criticality=1.0,
                    phi_phase=0.0,
                    phi_depth=1.0,
                    phi_breathing=0.5,
                    chromatic_enabled=False,
                    control_matrix_active=False,
                    adaptive_enabled=False,
                    adaptive_mode=None,
                    is_recording=False,
                    is_playing=False,
                    cluster_nodes_count=0
                )

            # Update timestamp
            self.current_state.timestamp = self.get_master_time()

            # Update provided fields
            for key, value in kwargs.items():
                if hasattr(self.current_state, key):
                    setattr(self.current_state, key, value)

            # Add to history
            self.state_history.append(self.current_state)

    def get_state(self) -> Optional[Dict]:
        """
        Get current synchronized state

        Returns:
            State dictionary or None
        """
        with self.state_lock:
            if self.current_state:
                return asdict(self.current_state)
            return None

    async def register_client(self, websocket):
        """
        Register WebSocket client (FR-003)

        Args:
            websocket: WebSocket connection
        """
        async with self.ws_lock:
            self.ws_clients.append(websocket)

            if self.config.enable_logging:
                print(f"[StateSyncManager] Client registered ({len(self.ws_clients)} total)")

    async def unregister_client(self, websocket):
        """
        Unregister WebSocket client

        Args:
            websocket: WebSocket connection
        """
        async with self.ws_lock:
            if websocket in self.ws_clients:
                self.ws_clients.remove(websocket)

                if self.config.enable_logging:
                    print(f"[StateSyncManager] Client unregistered ({len(self.ws_clients)} total)")

    async def broadcast_state(self):
        """
        Broadcast current state to all WebSocket clients (FR-003, SC-001)
        """
        state = self.get_state()
        if not state:
            return

        message = {
            "type": "state_sync",
            "data": state,
            "server_time": time.time()
        }

        async with self.ws_lock:
            disconnected = []

            for client in self.ws_clients:
                try:
                    send_start = time.time()
                    await asyncio.wait_for(
                        client.send_json(message),
                        timeout=self.config.websocket_timeout_ms / 1000.0
                    )

                    # Track latency
                    latency_ms = (time.time() - send_start) * 1000.0
                    self.message_latencies.append(latency_ms)

                except asyncio.TimeoutError:
                    if self.config.enable_logging:
                        print(f"[StateSyncManager] WebSocket send timeout")
                    disconnected.append(client)
                except Exception as e:
                    if self.config.enable_logging:
                        print(f"[StateSyncManager] WebSocket send error: {e}")
                    disconnected.append(client)

            # Remove disconnected clients
            for client in disconnected:
                if client in self.ws_clients:
                    self.ws_clients.remove(client)

    async def handle_client_message(self, websocket, message: Dict):
        """
        Handle incoming message from client (FR-003, User Story 3)

        Args:
            websocket: Client WebSocket
            message: Message dictionary

        Returns:
            Response dictionary
        """
        receive_time = time.time()
        msg_type = message.get("type")

        if msg_type == "ping":
            # Latency check
            return {
                "type": "pong",
                "server_time": time.time(),
                "client_time": message.get("client_time", 0)
            }

        elif msg_type == "pause":
            # Pause request (User Story 2)
            self.pause()
            return {
                "type": "pause_ack",
                "master_time": self.get_master_time()
            }

        elif msg_type == "resume":
            # Resume request (User Story 2)
            self.resume()
            return {
                "type": "resume_ack",
                "master_time": self.get_master_time()
            }

        elif msg_type == "get_state":
            # State request
            return {
                "type": "state_response",
                "data": self.get_state()
            }

        else:
            return {
                "type": "error",
                "message": f"Unknown message type: {msg_type}"
            }

    def get_latency_stats(self) -> Dict:
        """
        Get WebSocket latency statistics (FR-003, SC-001)

        Returns:
            Latency stats dictionary
        """
        if not self.message_latencies:
            return {
                "avg_latency_ms": 0.0,
                "max_latency_ms": 0.0,
                "min_latency_ms": 0.0,
                "meets_sc001": True,
                "meets_fr003": True
            }

        import numpy as np
        latencies = list(self.message_latencies)

        avg_latency = np.mean(latencies)
        max_latency = np.max(latencies)
        min_latency = np.min(latencies)

        return {
            "avg_latency_ms": float(avg_latency),
            "max_latency_ms": float(max_latency),
            "min_latency_ms": float(min_latency),
            "meets_sc001": max_latency <= self.config.max_latency_ms,  # SC-001
            "meets_fr003": avg_latency <= self.config.websocket_timeout_ms  # FR-003
        }

    def check_sync_health(self) -> Dict:
        """
        Check synchronization health (SC-004)

        Returns:
            Sync health report
        """
        current_time = time.time()
        time_since_check = current_time - self.last_sync_check

        # Check for recent desync events
        recent_desyncs = [
            d for d in self.desync_events
            if (current_time - d['timestamp']) < 60.0
        ]

        # Check state update frequency
        if len(self.state_history) >= 2:
            timestamps = [s.timestamp for s in list(self.state_history)]
            diffs = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]

            import numpy as np
            max_diff = np.max(diffs) if diffs else 0.0
            avg_diff = np.mean(diffs) if diffs else 0.0
        else:
            max_diff = 0.0
            avg_diff = 0.0

        # SC-004: No desync > 0.1s
        meets_sc004 = max_diff <= (self.config.max_desync_ms / 1000.0)

        self.last_sync_check = current_time

        return {
            "is_paused": self.paused,
            "master_time": self.get_master_time(),
            "recent_desyncs": len(recent_desyncs),
            "max_state_diff_ms": max_diff * 1000.0,
            "avg_state_diff_ms": avg_diff * 1000.0,
            "meets_sc004": meets_sc004,
            "active_clients": len(self.ws_clients)
        }

    def start_monitoring(self):
        """Start background sync monitoring"""
        if self.is_running:
            return

        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

        if self.config.enable_logging:
            print("[StateSyncManager] Monitoring started")

    def stop_monitoring(self):
        """Stop background monitoring"""
        self.is_running = False

        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
            self.monitor_thread = None

        if self.config.enable_logging:
            print("[StateSyncManager] Monitoring stopped")

    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.is_running:
            try:
                # Check sync health
                health = self.check_sync_health()

                # Log warnings
                if not health['meets_sc004'] and self.config.enable_logging:
                    print(f"[StateSyncManager] WARNING: Desync detected: {health['max_state_diff_ms']:.1f}ms")

                # Sleep
                time.sleep(self.config.sync_check_interval_s)

            except Exception as e:
                if self.config.enable_logging:
                    print(f"[StateSyncManager] Monitor error: {e}")


# Self-test
def _self_test():
    """Run basic self-test of StateSyncManager"""
    print("=" * 60)
    print("StateSyncManager Self-Test")
    print("=" * 60)
    print()

    all_ok = True

    # Test 1: Master clock
    print("1. Testing Master Clock (FR-002)...")
    manager = StateSyncManager(SyncConfig(enable_logging=True))

    t1 = manager.get_master_time()
    time.sleep(0.1)
    t2 = manager.get_master_time()

    time_ok = 0.09 < (t2 - t1) < 0.11
    all_ok = all_ok and time_ok

    print(f"   Time delta: {t2 - t1:.3f}s (expected ~0.1s)")
    print(f"   [{'OK' if time_ok else 'FAIL'}] Master clock (FR-002)")
    print()

    # Test 2: Pause/Resume
    print("2. Testing Pause/Resume (User Story 2)...")
    t_before_pause = manager.get_master_time()
    manager.pause()

    time.sleep(0.2)

    t_during_pause = manager.get_master_time()
    pause_ok = abs(t_during_pause - t_before_pause) < 0.01

    manager.resume()
    time.sleep(0.1)

    t_after_resume = manager.get_master_time()
    resume_ok = 0.09 < (t_after_resume - t_during_pause) < 0.11

    all_ok = all_ok and pause_ok and resume_ok

    print(f"   Pause: {t_during_pause - t_before_pause:.3f}s (expected ~0s)")
    print(f"   Resume: {t_after_resume - t_during_pause:.3f}s (expected ~0.1s)")
    print(f"   [{'OK' if pause_ok and resume_ok else 'FAIL'}] Pause/Resume")
    print()

    # Test 3: State update
    print("3. Testing State Update...")
    manager.update_state(
        ici=0.52,
        coherence=0.88,
        phi_depth=1.2
    )

    state = manager.get_state()
    state_ok = (
        state is not None and
        state['ici'] == 0.52 and
        state['coherence'] == 0.88 and
        state['phi_depth'] == 1.2
    )

    all_ok = all_ok and state_ok

    print(f"   State: ICI={state['ici']:.2f}, Coherence={state['coherence']:.2f}")
    print(f"   [{'OK' if state_ok else 'FAIL'}] State update")
    print()

    # Test 4: Sync health
    print("4. Testing Sync Health (SC-004)...")

    # Generate some state updates
    for i in range(10):
        manager.update_state(ici=0.5 + i*0.01)
        time.sleep(0.01)

    health = manager.check_sync_health()
    health_ok = health['meets_sc004']

    all_ok = all_ok and health_ok

    print(f"   Max state diff: {health['max_state_diff_ms']:.2f}ms")
    print(f"   Avg state diff: {health['avg_state_diff_ms']:.2f}ms")
    print(f"   [{'OK' if health_ok else 'FAIL'}] Sync health (SC-004: < 100ms)")
    print()

    # Test 5: Latency tracking
    print("5. Testing Latency Tracking (FR-003)...")

    # Simulate message latencies
    manager.message_latencies.extend([5.0, 10.0, 8.0, 12.0, 7.0])

    latency_stats = manager.get_latency_stats()
    latency_ok = latency_stats['meets_fr003']

    all_ok = all_ok and latency_ok

    print(f"   Avg latency: {latency_stats['avg_latency_ms']:.2f}ms")
    print(f"   Max latency: {latency_stats['max_latency_ms']:.2f}ms")
    print(f"   [{'OK' if latency_ok else 'FAIL'}] Latency tracking (FR-003: < 50ms)")
    print()

    print("=" * 60)
    if all_ok:
        print("Self-Test PASSED")
    else:
        print("Self-Test FAILED - Review failures above")
    print("=" * 60)

    return all_ok


if __name__ == "__main__":
    _self_test()
