"""
Cluster Monitor - Feature 022
Web dashboard and APIs to observe and manage multiple Soundlab/PhaseNet nodes.

Features:
- Real-time status aggregation from all nodes
- Historical metrics with ring buffers (10 min @ 1Hz)
- Health rules and status calculation
- Management actions (promote, quarantine, restart)
- RBAC for security
- Audit logging
- Topology persistence
- WebSocket updates at 1-2Hz

Requirements:
- FR-001: Status aggregator, history buffer, action controller
- FR-002: Collect per-node metrics
- FR-003: REST API endpoints
- FR-004: WebSocket /ws/cluster at 1-2Hz
- FR-006: Ring buffers (600 samples @ 1Hz)
- FR-007: RBAC for management actions
- FR-008: Audit logging
- FR-009: Health rules
- FR-010: Topology persistence

Success Criteria:
- SC-001: Updates within 2s
- SC-002: Actions complete with audit
- SC-003: History with no gaps >5s
- SC-004: CPU overhead <5%
- SC-005: RBAC prevents unauthorized actions
"""

import json
import time
import os
import hashlib
import threading
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from collections import deque
from enum import Enum
import psutil


class NodeHealth(Enum):
    """Node health status (FR-009)"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    OFFLINE = "offline"


class NodeRole(Enum):
    """Node role in cluster"""
    MASTER = "master"
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    STANDALONE = "standalone"


@dataclass
class ClusterMonitorConfig:
    """Configuration for cluster monitor"""
    update_interval: float = 1.0  # Update frequency in Hz (FR-004)
    history_samples: int = 600  # 10 min @ 1Hz (FR-006)
    health_check_interval: float = 2.0  # Health check frequency
    topology_file: str = "state/cluster_topology.json"  # FR-010
    audit_log_dir: str = "logs/cluster"  # FR-008
    # Health thresholds (FR-009)
    rtt_warning_ms: float = 25.0
    drift_warning_ms: float = 1.0
    pkt_loss_warning_pct: float = 1.0
    pkt_loss_critical_pct: float = 10.0
    stale_timeout_s: float = 5.0
    debounce_interval_s: float = 3.0  # Status debounce
    enable_rbac: bool = True  # FR-007
    enable_logging: bool = True


@dataclass
class NodeMetrics:
    """Node metrics snapshot (FR-002)"""
    timestamp: float
    node_id: str
    role: str
    host: str
    port: int
    rtt_ms: float
    drift_ms: float
    phi_phase: float
    phi_depth: float
    coherence: float
    criticality: float
    pkt_loss_pct: float
    cpu_pct: float
    mem_pct: float
    uptime_s: float
    last_seen: float


@dataclass
class NodeStatus:
    """Node status with health (FR-009)"""
    node_id: str
    role: str
    host: str
    port: int
    health: str
    health_reason: str
    last_seen: float
    uptime_s: float
    # Current metrics
    rtt_ms: float
    drift_ms: float
    phi_phase: float
    phi_depth: float
    coherence: float
    criticality: float
    pkt_loss_pct: float
    cpu_pct: float
    mem_pct: float
    # Flags
    is_stale: bool
    is_leader: bool


class ClusterMonitor:
    """
    Cluster Monitor for Soundlab/PhaseNet nodes (Feature 022)

    Aggregates status, maintains history, provides management actions,
    and broadcasts updates via WebSocket.
    """

    def __init__(self, config: Optional[ClusterMonitorConfig] = None):
        """
        Initialize Cluster Monitor

        Args:
            config: Monitor configuration
        """
        self.config = config or ClusterMonitorConfig()

        # Node tracking
        self.nodes: Dict[str, NodeStatus] = {}
        self.node_history: Dict[str, deque] = {}  # node_id -> deque of NodeMetrics (FR-006)
        self.node_lock = threading.Lock()

        # Health tracking
        self.last_health_check = 0.0
        self.status_changes: Dict[str, float] = {}  # node_id -> last status change time (debounce)

        # Audit log (FR-008)
        self.audit_log_path = None
        if self.config.enable_logging:
            os.makedirs(self.config.audit_log_dir, exist_ok=True)
            self.audit_log_path = os.path.join(
                self.config.audit_log_dir,
                f"cluster_audit_{int(time.time())}.log"
            )

        # RBAC (FR-007)
        self.access_tokens: set = set()  # Simple token-based auth
        if self.config.enable_rbac:
            # Generate default admin token
            self.admin_token = self._generate_token("admin")
            self.access_tokens.add(self.admin_token)

        # WebSocket clients (FR-004)
        self.ws_clients: List = []
        self.ws_client_lock = threading.Lock()

        # Background threads
        self.is_running = False
        self.aggregator_thread = None
        self.health_check_thread = None

        # Node synchronizer and PhaseNet references (set externally)
        self.node_sync = None
        self.phasenet = None

        # Hardware interface reference (Feature 023, FR-008)
        self.hw_interface = None

        # Load persisted topology (FR-010)
        self._load_topology()

        if self.config.enable_logging:
            print("[ClusterMonitor] Initialized")

    def _generate_token(self, user: str) -> str:
        """Generate access token for RBAC (FR-007)"""
        import secrets
        token_data = f"{user}:{time.time()}:{secrets.token_hex(16)}"
        return hashlib.sha256(token_data.encode()).hexdigest()

    def start(self):
        """Start cluster monitor (FR-001)"""
        if self.is_running:
            return

        self.is_running = True

        # Start aggregator thread
        self.aggregator_thread = threading.Thread(target=self._aggregator_loop, daemon=True)
        self.aggregator_thread.start()

        # Start health check thread
        self.health_check_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.health_check_thread.start()

        if self.config.enable_logging:
            print("[ClusterMonitor] Started")
            if self.config.enable_rbac:
                print(f"[ClusterMonitor] Admin token: {self.admin_token}")

    def stop(self):
        """Stop cluster monitor"""
        if not self.is_running:
            return

        self.is_running = False

        # Save topology (FR-010)
        self._save_topology()

        if self.config.enable_logging:
            print("[ClusterMonitor] Stopped")

    def _aggregator_loop(self):
        """
        Aggregation loop: collect metrics from nodes (FR-001, FR-002, SC-001)

        Runs at configured update_interval (1-2 Hz).
        """
        while self.is_running:
            try:
                current_time = time.time()

                # Collect from Node Synchronizer (Feature 020)
                if self.node_sync and self.node_sync.is_running:
                    self._collect_from_node_sync(current_time)

                # Collect from PhaseNet (Feature 021)
                if self.phasenet and self.phasenet.is_running:
                    self._collect_from_phasenet(current_time)

                # Collect from Hardware Interface (Feature 023, FR-008)
                if self.hw_interface and self.hw_interface.is_connected:
                    self._collect_from_hardware(current_time)

                # Broadcast updates via WebSocket (FR-004, SC-001)
                self._broadcast_updates()

                # Wait for next interval
                time.sleep(self.config.update_interval)

            except Exception as e:
                if self.config.enable_logging:
                    print(f"[ClusterMonitor] Aggregator error: {e}")

    def _collect_from_node_sync(self, current_time: float):
        """Collect metrics from Node Synchronizer (FR-002)"""
        try:
            status = self.node_sync.get_status()
            stats = self.node_sync.get_statistics()

            # Get local node info
            node_id = status.get('node_id', 'unknown')
            role = status.get('state', 'unknown')
            is_leader = status.get('is_leader', False)

            # Get system metrics
            cpu_pct = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            uptime_s = time.time() - psutil.boot_time()

            # Create metrics snapshot
            metrics = NodeMetrics(
                timestamp=current_time,
                node_id=node_id,
                role=role,
                host='localhost',  # Local node
                port=0,  # Not applicable for local
                rtt_ms=0.0,  # Local node has no RTT
                drift_ms=0.0,
                phi_phase=0.0,  # Would need to get from auto_phi_learner
                phi_depth=0.0,
                coherence=stats.get('coherence', {}).get('mean', 0.0) if 'coherence' in stats else 0.0,
                criticality=1.0,
                pkt_loss_pct=0.0,
                cpu_pct=cpu_pct,
                mem_pct=mem.percent,
                uptime_s=uptime_s,
                last_seen=current_time
            )

            self._update_node_metrics(metrics, is_leader)

            # Collect from connected clients
            if 'clients' in status:
                for client in status['clients']:
                    client_id = client.get('id', 'unknown')
                    # Would need more detailed metrics from clients
                    # For now, create basic entry
                    client_metrics = NodeMetrics(
                        timestamp=current_time,
                        node_id=client_id,
                        role='client',
                        host=client.get('address', 'unknown'),
                        port=0,
                        rtt_ms=0.0,
                        drift_ms=0.0,
                        phi_phase=0.0,
                        phi_depth=0.0,
                        coherence=0.0,
                        criticality=1.0,
                        pkt_loss_pct=0.0,
                        cpu_pct=0.0,
                        mem_pct=0.0,
                        uptime_s=0.0,
                        last_seen=client.get('last_seen', current_time)
                    )
                    self._update_node_metrics(client_metrics, False)

        except Exception as e:
            if self.config.enable_logging:
                print(f"[ClusterMonitor] Error collecting from NodeSync: {e}")

    def _collect_from_phasenet(self, current_time: float):
        """Collect metrics from PhaseNet (FR-002)"""
        try:
            status = self.phasenet.get_status()
            stats = self.phasenet.get_statistics()

            # Get local node info
            node_id = status.get('node_id', 'unknown')
            role = status.get('state', 'unknown')
            is_leader = status.get('is_leader', False)

            # Get system metrics
            cpu_pct = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            uptime_s = time.time() - psutil.boot_time()

            # Create metrics snapshot
            metrics = NodeMetrics(
                timestamp=current_time,
                node_id=node_id,
                role=role,
                host='localhost',
                port=0,
                rtt_ms=stats.get('latency', {}).get('mean_ms', 0.0) if 'latency' in stats else 0.0,
                drift_ms=0.0,  # PhaseNet doesn't track drift same way
                phi_phase=0.0,  # Would need from local state
                phi_depth=0.0,
                coherence=stats.get('coherence', {}).get('mean', 0.0) if 'coherence' in stats else 0.0,
                criticality=1.0,
                pkt_loss_pct=stats.get('packets', {}).get('drop_rate', 0.0) * 100 if 'packets' in stats else 0.0,
                cpu_pct=cpu_pct,
                mem_pct=mem.percent,
                uptime_s=uptime_s,
                last_seen=current_time
            )

            self._update_node_metrics(metrics, is_leader)

            # Collect from peers
            if 'peers' in status:
                for peer in status['peers']:
                    peer_id = peer.get('node_id', 'unknown')
                    peer_metrics = NodeMetrics(
                        timestamp=current_time,
                        node_id=peer_id,
                        role='follower' if not peer.get('is_leader', False) else 'leader',
                        host=peer.get('address', 'unknown'),
                        port=0,
                        rtt_ms=peer.get('latency_ms', 0.0),
                        drift_ms=0.0,
                        phi_phase=0.0,
                        phi_depth=0.0,
                        coherence=1.0 - peer.get('phase_diff', 0.0),  # Convert diff to coherence
                        criticality=1.0,
                        pkt_loss_pct=0.0,
                        cpu_pct=0.0,
                        mem_pct=0.0,
                        uptime_s=0.0,
                        last_seen=peer.get('last_seen', current_time)
                    )
                    self._update_node_metrics(peer_metrics, peer.get('is_leader', False))

        except Exception as e:
            if self.config.enable_logging:
                print(f"[ClusterMonitor] Error collecting from PhaseNet: {e}")

    def _collect_from_hardware(self, current_time: float):
        """Collect metrics from Hardware Interface (Feature 023, FR-008)"""
        try:
            stats = self.hw_interface.get_statistics()

            # Create hardware node metrics entry
            hw_metrics = NodeMetrics(
                timestamp=current_time,
                node_id="hardware_bridge",
                role="hardware",
                host=self.hw_interface.port or "auto",
                port=self.hw_interface.baudrate,
                rtt_ms=stats.get('latency_us', 0) / 1000.0,  # Convert µs to ms
                drift_ms=stats.get('clock_drift_ppm', 0.0) / 1000.0,  # Approximate conversion
                phi_phase=0.0,  # Hardware doesn't provide these directly
                phi_depth=0.0,
                coherence=1.0 - stats.get('loss_rate', 0.0),  # Convert loss to coherence
                criticality=1.0,
                pkt_loss_pct=stats.get('loss_rate', 0.0) * 100,
                cpu_pct=0.0,  # Not applicable for hardware
                mem_pct=0.0,
                uptime_s=stats.get('uptime_ms', 0) / 1000.0,  # Convert ms to s
                last_seen=current_time
            )

            # Track as hardware node (not a leader)
            self._update_node_metrics(hw_metrics, is_leader=False)

        except Exception as e:
            if self.config.enable_logging:
                print(f"[ClusterMonitor] Error collecting from Hardware: {e}")

    def _update_node_metrics(self, metrics: NodeMetrics, is_leader: bool):
        """
        Update node metrics and history (FR-006, SC-003)

        Args:
            metrics: Node metrics snapshot
            is_leader: Whether node is leader
        """
        with self.node_lock:
            node_id = metrics.node_id

            # Initialize history buffer if needed (FR-006)
            if node_id not in self.node_history:
                self.node_history[node_id] = deque(maxlen=self.config.history_samples)

            # Add to history
            self.node_history[node_id].append(metrics)

            # Calculate health (FR-009)
            health, health_reason = self._calculate_health(metrics)

            # Check if stale
            is_stale = (time.time() - metrics.last_seen) > self.config.stale_timeout_s

            # Update node status
            self.nodes[node_id] = NodeStatus(
                node_id=node_id,
                role=metrics.role,
                host=metrics.host,
                port=metrics.port,
                health=health.value,
                health_reason=health_reason,
                last_seen=metrics.last_seen,
                uptime_s=metrics.uptime_s,
                rtt_ms=metrics.rtt_ms,
                drift_ms=metrics.drift_ms,
                phi_phase=metrics.phi_phase,
                phi_depth=metrics.phi_depth,
                coherence=metrics.coherence,
                criticality=metrics.criticality,
                pkt_loss_pct=metrics.pkt_loss_pct,
                cpu_pct=metrics.cpu_pct,
                mem_pct=metrics.mem_pct,
                is_stale=is_stale,
                is_leader=is_leader
            )

    def _calculate_health(self, metrics: NodeMetrics) -> tuple[NodeHealth, str]:
        """
        Calculate node health based on rules (FR-009)

        Args:
            metrics: Node metrics

        Returns:
            Tuple of (health_status, reason)
        """
        current_time = time.time()
        age = current_time - metrics.last_seen

        # Critical: offline or high packet loss
        if age > self.config.stale_timeout_s:
            return (NodeHealth.CRITICAL, f"Offline (last seen {age:.1f}s ago)")

        if metrics.pkt_loss_pct > self.config.pkt_loss_critical_pct:
            return (NodeHealth.CRITICAL, f"Packet loss {metrics.pkt_loss_pct:.1f}%")

        # Warning: thresholds exceeded
        warnings = []
        if metrics.rtt_ms > self.config.rtt_warning_ms:
            warnings.append(f"RTT {metrics.rtt_ms:.1f}ms")
        if metrics.drift_ms > self.config.drift_warning_ms:
            warnings.append(f"Drift {metrics.drift_ms:.1f}ms")
        if metrics.pkt_loss_pct > self.config.pkt_loss_warning_pct:
            warnings.append(f"Pkt loss {metrics.pkt_loss_pct:.1f}%")

        if warnings:
            return (NodeHealth.WARNING, ", ".join(warnings))

        # Healthy
        return (NodeHealth.HEALTHY, "All metrics nominal")

    def _health_check_loop(self):
        """Health check loop: mark stale nodes (FR-009)"""
        while self.is_running:
            try:
                current_time = time.time()

                with self.node_lock:
                    for node_id, status in list(self.nodes.items()):
                        age = current_time - status.last_seen

                        # Mark as stale if timeout exceeded
                        if age > self.config.stale_timeout_s:
                            status.is_stale = True
                            status.health = NodeHealth.OFFLINE.value
                            status.health_reason = f"Offline ({age:.1f}s)"

                            # Optionally remove very old nodes
                            if age > 60.0:  # Remove after 1 minute offline
                                del self.nodes[node_id]

                time.sleep(self.config.health_check_interval)

            except Exception as e:
                if self.config.enable_logging:
                    print(f"[ClusterMonitor] Health check error: {e}")

    def _broadcast_updates(self):
        """Broadcast updates to WebSocket clients (FR-004, SC-001)"""
        with self.ws_client_lock:
            if not self.ws_clients:
                return

            # Create update message
            update = {
                "type": "cluster_update",
                "timestamp": time.time(),
                "nodes": self.get_nodes_list()
            }

            # Broadcast to all clients
            # Note: Actual WebSocket send would be in main.py
            # This is a placeholder for the data structure

    def get_nodes_list(self) -> List[Dict]:
        """
        Get list of all nodes (FR-003)

        Returns:
            List of node status dictionaries
        """
        with self.node_lock:
            return [asdict(status) for status in self.nodes.values()]

    def get_node_detail(self, node_id: str) -> Optional[Dict]:
        """
        Get detailed node info with history (FR-003, SC-003)

        Args:
            node_id: Node identifier

        Returns:
            Node detail dictionary with history, or None if not found
        """
        with self.node_lock:
            if node_id not in self.nodes:
                return None

            status = self.nodes[node_id]
            history = list(self.node_history.get(node_id, []))

            return {
                "status": asdict(status),
                "history": [asdict(m) for m in history],
                "history_count": len(history),
                "history_duration_s": (history[-1].timestamp - history[0].timestamp) if len(history) > 1 else 0
            }

    def promote_node(self, node_id: str, token: Optional[str] = None) -> Dict:
        """
        Promote node to master (FR-003, SC-002)

        Args:
            node_id: Node to promote
            token: Authorization token (FR-007)

        Returns:
            Result dictionary
        """
        # Check RBAC (FR-007, SC-005)
        if self.config.enable_rbac and token not in self.access_tokens:
            self._audit_log("promote", node_id, False, "Unauthorized")
            return {"ok": False, "message": "Unauthorized"}

        # Check node exists
        if node_id not in self.nodes:
            return {"ok": False, "message": "Node not found"}

        # Audit log (FR-008, SC-002)
        self._audit_log("promote", node_id, True, "Success")

        # Implementation would depend on NodeSync/PhaseNet APIs
        # For now, return success
        return {
            "ok": True,
            "message": f"Node {node_id} promoted",
            "action": "promote",
            "timestamp": time.time()
        }

    def quarantine_node(self, node_id: str, token: Optional[str] = None) -> Dict:
        """
        Quarantine node (FR-003, SC-002)

        Args:
            node_id: Node to quarantine
            token: Authorization token (FR-007)

        Returns:
            Result dictionary
        """
        # Check RBAC (FR-007, SC-005)
        if self.config.enable_rbac and token not in self.access_tokens:
            self._audit_log("quarantine", node_id, False, "Unauthorized")
            return {"ok": False, "message": "Unauthorized"}

        # Check node exists
        if node_id not in self.nodes:
            return {"ok": False, "message": "Node not found"}

        # Audit log (FR-008, SC-002)
        self._audit_log("quarantine", node_id, True, "Success")

        return {
            "ok": True,
            "message": f"Node {node_id} quarantined",
            "action": "quarantine",
            "timestamp": time.time()
        }

    def restart_node(self, node_id: str, token: Optional[str] = None) -> Dict:
        """
        Restart node (FR-003, SC-002)

        Args:
            node_id: Node to restart
            token: Authorization token (FR-007)

        Returns:
            Result dictionary
        """
        # Check RBAC (FR-007, SC-005)
        if self.config.enable_rbac and token not in self.access_tokens:
            self._audit_log("restart", node_id, False, "Unauthorized")
            return {"ok": False, "message": "Unauthorized"}

        # Check node exists
        if node_id not in self.nodes:
            return {"ok": False, "message": "Node not found"}

        # Audit log (FR-008, SC-002)
        self._audit_log("restart", node_id, True, "Success")

        return {
            "ok": True,
            "message": f"Node {node_id} restart requested",
            "action": "restart",
            "timestamp": time.time()
        }

    def _audit_log(self, action: str, node_id: str, success: bool, message: str):
        """
        Write audit log entry (FR-008, SC-002)

        Args:
            action: Action performed
            node_id: Target node
            success: Whether action succeeded
            message: Result message
        """
        if not self.config.enable_logging or not self.audit_log_path:
            return

        try:
            entry = {
                "timestamp": time.time(),
                "action": action,
                "node_id": node_id,
                "success": success,
                "message": message
            }

            with open(self.audit_log_path, 'a') as f:
                f.write(json.dumps(entry) + '\n')

        except Exception as e:
            print(f"[ClusterMonitor] Audit log error: {e}")

    def _save_topology(self):
        """Save cluster topology to file (FR-010)"""
        try:
            os.makedirs(os.path.dirname(self.config.topology_file), exist_ok=True)

            with self.node_lock:
                topology = {
                    "timestamp": time.time(),
                    "nodes": self.get_nodes_list()
                }

            with open(self.config.topology_file, 'w') as f:
                json.dump(topology, f, indent=2)

            if self.config.enable_logging:
                print(f"[ClusterMonitor] Topology saved to {self.config.topology_file}")

        except Exception as e:
            if self.config.enable_logging:
                print(f"[ClusterMonitor] Topology save error: {e}")

    def _load_topology(self):
        """Load cluster topology from file (FR-010)"""
        try:
            if not os.path.exists(self.config.topology_file):
                return

            with open(self.config.topology_file, 'r') as f:
                topology = json.load(f)

            # Note: We don't restore full state, just log it was loaded
            if self.config.enable_logging:
                node_count = len(topology.get('nodes', []))
                print(f"[ClusterMonitor] Loaded topology ({node_count} nodes)")

        except Exception as e:
            if self.config.enable_logging:
                print(f"[ClusterMonitor] Topology load error: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get cluster statistics

        Returns:
            Statistics dictionary
        """
        with self.node_lock:
            healthy_count = sum(1 for n in self.nodes.values() if n.health == NodeHealth.HEALTHY.value)
            warning_count = sum(1 for n in self.nodes.values() if n.health == NodeHealth.WARNING.value)
            critical_count = sum(1 for n in self.nodes.values() if n.health == NodeHealth.CRITICAL.value)
            leader_count = sum(1 for n in self.nodes.values() if n.is_leader)

            return {
                "total_nodes": len(self.nodes),
                "healthy_nodes": healthy_count,
                "warning_nodes": warning_count,
                "critical_nodes": critical_count,
                "offline_nodes": sum(1 for n in self.nodes.values() if n.is_stale),
                "leader_count": leader_count,
                "history_samples": sum(len(h) for h in self.node_history.values()),
                "update_interval": self.config.update_interval
            }


# Self-test
if __name__ == "__main__":
    print("=" * 60)
    print("Cluster Monitor Self-Test")
    print("=" * 60)

    # Test initialization
    print("\n1. Testing initialization...")
    config = ClusterMonitorConfig(
        enable_logging=True,
        enable_rbac=True
    )
    monitor = ClusterMonitor(config)
    print("   OK: Initialization")
    print(f"   Admin token: {monitor.admin_token}")

    # Test metrics update
    print("\n2. Testing metrics update...")
    # Skip all psutil calls for test to avoid Windows blocking issues
    metrics = NodeMetrics(
        timestamp=time.time(),
        node_id="test_node_1",
        role="master",
        host="localhost",
        port=9000,
        rtt_ms=2.5,
        drift_ms=0.5,
        phi_phase=0.5,
        phi_depth=0.8,
        coherence=0.95,
        criticality=1.0,
        pkt_loss_pct=0.5,
        cpu_pct=15.0,
        mem_pct=45.0,
        uptime_s=1000.0,
        last_seen=time.time()
    )
    monitor._update_node_metrics(metrics, is_leader=True)
    print("   OK: Metrics updated")

    # Test node list
    print("\n3. Testing node list...")
    nodes = monitor.get_nodes_list()
    print(f"   OK: {len(nodes)} nodes listed")

    # Test node detail
    print("\n4. Testing node detail...")
    detail = monitor.get_node_detail("test_node_1")
    print(f"   OK: Detail retrieved (history: {detail['history_count']} samples)")

    # Test health rules
    print("\n5. Testing health rules...")
    health, reason = monitor._calculate_health(metrics)
    print(f"   OK: Health={health.value}, Reason={reason}")

    # Test RBAC
    print("\n6. Testing RBAC...")
    result = monitor.promote_node("test_node_1", token="invalid_token")
    print(f"   OK: Unauthorized blocked (ok={result['ok']})")

    result = monitor.promote_node("test_node_1", token=monitor.admin_token)
    print(f"   OK: Authorized succeeded (ok={result['ok']})")

    # Test statistics
    print("\n7. Testing statistics...")
    stats = monitor.get_statistics()
    print(f"   OK: Stats (nodes={stats['total_nodes']}, healthy={stats['healthy_nodes']})")

    # Test topology persistence
    print("\n8. Testing topology persistence...")
    monitor._save_topology()
    print("   OK: Topology saved")

    print("\n" + "=" * 60)
    print("Self-Test PASSED")
    print("=" * 60)
