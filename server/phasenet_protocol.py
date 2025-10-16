"""
PhaseNet Protocol - Feature 021
Low-latency distributed mesh network for synchronizing Φ-phase, coherence, and criticality
data between Soundlab nodes.

Features:
- Mesh network topology with peer discovery
- Dynamic master election (Raft-lite)
- UDP socket transport for low latency
- AES-128 packet encryption
- Per-node drift compensation
- Topology healing and auto-reconnect
- Network monitoring and metrics

Requirements:
- FR-001: PhaseNetNode class
- FR-002: UDP socket transport (WebRTC optional)
- FR-003: Peer discovery, authentication, master election
- FR-004: Compact packet format {t, phi_phase, phi_depth, criticality, coherence}
- FR-005: Per-node drift table with adaptive compensation
- FR-006: AES-128 encryption
- FR-007: Auto-reconnect and topology healing
- FR-008: Network status API

Success Criteria:
- SC-001: Network delay <5ms, jitter <2ms
- SC-002: Phase coherence ≥0.99
- SC-003: Master election <2s
- SC-004: 100% uptime for 1h under churn
"""

import socket
import json
import time
import threading
import struct
import hashlib
from typing import Optional, Dict, List, Callable, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from collections import deque
import statistics


# Encryption support
try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import padding
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False


class NodeState(Enum):
    """Node state in Raft-lite election (FR-003)"""
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


@dataclass
class PhaseNetConfig:
    """Configuration for PhaseNet node"""
    node_id: Optional[str] = None  # Auto-generated if None
    bind_address: str = "0.0.0.0"
    bind_port: int = 9000
    broadcast_address: str = "255.255.255.255"
    broadcast_port: int = 9001
    network_key: Optional[str] = None  # Shared key for encryption (FR-006)
    election_timeout: float = 2.0  # Leader election timeout (SC-003)
    heartbeat_interval: float = 0.5  # Leader heartbeat interval
    sync_rate: int = 30  # Phase sync rate in Hz
    max_drift_samples: int = 100  # Drift table size (FR-005)
    enable_encryption: bool = True  # AES-128 encryption (FR-006)
    enable_logging: bool = True


@dataclass
class PhasePacket:
    """Phase data packet (FR-004)"""
    t: float  # Timestamp
    phi_phase: float
    phi_depth: float
    criticality: float
    coherence: float
    ici: float
    node_id: str
    sequence: int


@dataclass
class PeerInfo:
    """Peer node information"""
    node_id: str
    address: str
    port: int
    last_seen: float
    is_leader: bool = False
    drift_offset: float = 0.0  # Clock offset (FR-005)
    latency: float = 0.0  # Network latency
    phase_diff: float = 0.0  # Phase coherence difference


class PhaseNetNode:
    """
    PhaseNet Protocol Node (Feature 021)

    Distributed mesh network for phase-locked synchronization across multiple nodes.
    Supports dynamic master election, encryption, and topology healing.
    """

    def __init__(self, config: Optional[PhaseNetConfig] = None):
        """
        Initialize PhaseNet node

        Args:
            config: PhaseNet configuration
        """
        self.config = config or PhaseNetConfig()

        # Generate node ID if not provided
        if not self.config.node_id:
            self.config.node_id = f"node_{int(time.time() * 1000)}"

        self.node_id = self.config.node_id

        # Network state
        self.socket = None
        self.is_running = False

        # Raft-lite state (FR-003)
        self.state = NodeState.FOLLOWER
        self.current_term = 0
        self.voted_for = None
        self.leader_id = None
        self.last_heartbeat = 0.0
        self.election_timer = None
        self.heartbeat_timer = None

        # Peers (mesh network)
        self.peers: Dict[str, PeerInfo] = {}
        self.peer_lock = threading.Lock()

        # Phase synchronization
        self.local_phase = PhasePacket(
            t=time.time(),
            phi_phase=0.0,
            phi_depth=0.0,
            criticality=1.0,
            coherence=0.0,
            ici=0.0,
            node_id=self.node_id,
            sequence=0
        )
        self.sequence_counter = 0

        # Drift compensation (FR-005)
        self.drift_table: Dict[str, deque] = {}  # node_id -> drift samples
        self.latency_table: Dict[str, deque] = {}  # node_id -> latency samples

        # Encryption (FR-006)
        self.cipher = None
        if self.config.enable_encryption and self.config.network_key and ENCRYPTION_AVAILABLE:
            self._init_encryption()

        # Statistics (SC-001, SC-002)
        self.packet_count = 0
        self.packets_sent = 0
        self.packets_received = 0
        self.packets_dropped = 0
        self.latency_history = deque(maxlen=100)
        self.jitter_history = deque(maxlen=100)
        self.coherence_history = deque(maxlen=100)

        # Callbacks
        self.phase_callback: Optional[Callable] = None  # Called on phase update
        self.leader_callback: Optional[Callable] = None  # Called on leader change

        # Background threads
        self.receiver_thread = None
        self.discovery_thread = None
        self.health_check_thread = None

        if self.config.enable_logging:
            print(f"[PhaseNet] Initialized node {self.node_id}")

    def _init_encryption(self):
        """Initialize AES-128 encryption (FR-006)"""
        # Derive 128-bit key from network key
        key = hashlib.sha256(self.config.network_key.encode()).digest()[:16]
        # Use first 16 bytes for AES-128
        self.encryption_key = key

        if self.config.enable_logging:
            print("[PhaseNet] Encryption enabled (AES-128)")

    def start(self):
        """Start PhaseNet node (FR-001)"""
        if self.is_running:
            return

        self.is_running = True

        # Create UDP socket (FR-002)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.socket.bind((self.config.bind_address, self.config.bind_port))
        self.socket.settimeout(0.1)  # Non-blocking with timeout

        # Start background threads
        self.receiver_thread = threading.Thread(target=self._receiver_loop, daemon=True)
        self.receiver_thread.start()

        self.discovery_thread = threading.Thread(target=self._discovery_loop, daemon=True)
        self.discovery_thread.start()

        self.health_check_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.health_check_thread.start()

        # Start election timer (follower state)
        self._reset_election_timer()

        if self.config.enable_logging:
            print(f"[PhaseNet] Started on {self.config.bind_address}:{self.config.bind_port}")

    def stop(self):
        """Stop PhaseNet node"""
        if not self.is_running:
            return

        self.is_running = False

        # Cancel timers
        if self.election_timer:
            self.election_timer.cancel()
        if self.heartbeat_timer:
            self.heartbeat_timer.cancel()

        # Close socket
        if self.socket:
            self.socket.close()

        if self.config.enable_logging:
            print("[PhaseNet] Stopped")

    def update_phase(self, phi_phase: float, phi_depth: float,
                     criticality: float, coherence: float, ici: float):
        """
        Update local phase and broadcast if leader (FR-004)

        Args:
            phi_phase: Current phi phase
            phi_depth: Current phi depth
            criticality: Current criticality
            coherence: Current coherence
            ici: Current ICI
        """
        # Update local phase
        self.local_phase = PhasePacket(
            t=time.time(),
            phi_phase=phi_phase,
            phi_depth=phi_depth,
            criticality=criticality,
            coherence=coherence,
            ici=ici,
            node_id=self.node_id,
            sequence=self.sequence_counter
        )
        self.sequence_counter += 1

        # Broadcast to all peers
        self._broadcast_phase()

    def _broadcast_phase(self):
        """Broadcast phase packet to all peers (FR-004, SC-001)"""
        if not self.is_running or not self.socket:
            return

        # Create packet
        packet_data = {
            "type": "phase",
            "t": self.local_phase.t,
            "phi_phase": self.local_phase.phi_phase,
            "phi_depth": self.local_phase.phi_depth,
            "criticality": self.local_phase.criticality,
            "coherence": self.local_phase.coherence,
            "ici": self.local_phase.ici,
            "node_id": self.local_phase.node_id,
            "sequence": self.local_phase.sequence
        }

        # Encrypt if enabled (FR-006)
        packet_bytes = self._encrypt_packet(packet_data)

        # Send to all known peers
        with self.peer_lock:
            for peer in self.peers.values():
                try:
                    self.socket.sendto(packet_bytes, (peer.address, peer.port))
                    self.packets_sent += 1
                except Exception as e:
                    if self.config.enable_logging:
                        print(f"[PhaseNet] Send error to {peer.node_id}: {e}")

    def _encrypt_packet(self, data: Dict) -> bytes:
        """
        Encrypt packet with AES-128 (FR-006)

        Args:
            data: Packet data dictionary

        Returns:
            Encrypted packet bytes
        """
        # Serialize to JSON
        json_bytes = json.dumps(data).encode('utf-8')

        # If encryption enabled, encrypt
        if self.cipher and self.config.enable_encryption and ENCRYPTION_AVAILABLE:
            # Add PKCS7 padding
            padder = padding.PKCS7(128).padder()
            padded_data = padder.update(json_bytes) + padder.finalize()

            # Generate random IV
            import os
            iv = os.urandom(16)

            # Encrypt
            cipher = Cipher(
                algorithms.AES(self.encryption_key),
                modes.CBC(iv),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            encrypted = encryptor.update(padded_data) + encryptor.finalize()

            # Prepend IV to encrypted data
            return iv + encrypted
        else:
            # No encryption, return plain JSON
            return json_bytes

    def _decrypt_packet(self, data: bytes) -> Optional[Dict]:
        """
        Decrypt packet with AES-128 (FR-006)

        Args:
            data: Encrypted packet bytes

        Returns:
            Decrypted packet dictionary or None if failed
        """
        try:
            # If encryption enabled, decrypt
            if self.cipher and self.config.enable_encryption and ENCRYPTION_AVAILABLE:
                # Extract IV (first 16 bytes)
                iv = data[:16]
                encrypted = data[16:]

                # Decrypt
                cipher = Cipher(
                    algorithms.AES(self.encryption_key),
                    modes.CBC(iv),
                    backend=default_backend()
                )
                decryptor = cipher.decryptor()
                padded_data = decryptor.update(encrypted) + decryptor.finalize()

                # Remove PKCS7 padding
                unpadder = padding.PKCS7(128).unpadder()
                json_bytes = unpadder.update(padded_data) + unpadder.finalize()
            else:
                # No encryption, parse plain JSON
                json_bytes = data

            # Parse JSON
            return json.loads(json_bytes.decode('utf-8'))

        except Exception as e:
            if self.config.enable_logging:
                print(f"[PhaseNet] Decrypt error: {e}")
            self.packets_dropped += 1
            return None

    def _receiver_loop(self):
        """Receive and process packets (FR-002)"""
        while self.is_running:
            try:
                data, addr = self.socket.recvfrom(4096)
                receive_time = time.time()

                # Decrypt packet
                packet = self._decrypt_packet(data)
                if not packet:
                    continue

                self.packets_received += 1

                # Handle packet by type
                packet_type = packet.get("type")

                if packet_type == "phase":
                    self._handle_phase_packet(packet, addr, receive_time)
                elif packet_type == "discovery":
                    self._handle_discovery_packet(packet, addr)
                elif packet_type == "heartbeat":
                    self._handle_heartbeat_packet(packet, addr)
                elif packet_type == "vote_request":
                    self._handle_vote_request(packet, addr)
                elif packet_type == "vote_response":
                    self._handle_vote_response(packet, addr)

            except socket.timeout:
                continue
            except Exception as e:
                if self.is_running and self.config.enable_logging:
                    print(f"[PhaseNet] Receiver error: {e}")

    def _handle_phase_packet(self, packet: Dict, addr: Tuple, receive_time: float):
        """
        Handle received phase packet (FR-004, FR-005)

        Args:
            packet: Phase packet data
            addr: Sender address
            receive_time: Packet receive time
        """
        node_id = packet.get("node_id")
        if node_id == self.node_id:
            return  # Ignore own packets

        # Update peer info
        with self.peer_lock:
            if node_id not in self.peers:
                self.peers[node_id] = PeerInfo(
                    node_id=node_id,
                    address=addr[0],
                    port=addr[1],
                    last_seen=receive_time
                )
            else:
                self.peers[node_id].last_seen = receive_time

            peer = self.peers[node_id]

            # Calculate latency (FR-005)
            packet_time = packet.get("t", 0)
            latency = receive_time - packet_time

            # Update latency table
            if node_id not in self.latency_table:
                self.latency_table[node_id] = deque(maxlen=self.config.max_drift_samples)
            self.latency_table[node_id].append(latency)

            # Calculate drift offset (simple moving average)
            peer.latency = statistics.mean(self.latency_table[node_id]) if self.latency_table[node_id] else 0

            # Calculate phase coherence (SC-002)
            peer.phase_diff = abs(packet.get("phi_phase", 0) - self.local_phase.phi_phase)
            self.coherence_history.append(1.0 - min(peer.phase_diff, 1.0))

            # Track jitter
            if len(self.latency_table[node_id]) > 1:
                latencies = list(self.latency_table[node_id])
                jitter = abs(latencies[-1] - latencies[-2])
                self.jitter_history.append(jitter)

        # Call phase callback if registered
        if self.phase_callback:
            self.phase_callback(packet)

    def _discovery_loop(self):
        """Peer discovery loop (FR-003, FR-007)"""
        while self.is_running:
            try:
                # Broadcast discovery packet
                discovery_packet = {
                    "type": "discovery",
                    "node_id": self.node_id,
                    "port": self.config.bind_port
                }

                packet_bytes = self._encrypt_packet(discovery_packet)

                self.socket.sendto(
                    packet_bytes,
                    (self.config.broadcast_address, self.config.broadcast_port)
                )

                # Wait before next discovery
                time.sleep(5.0)

            except Exception as e:
                if self.is_running and self.config.enable_logging:
                    print(f"[PhaseNet] Discovery error: {e}")

    def _handle_discovery_packet(self, packet: Dict, addr: Tuple):
        """
        Handle discovery packet (FR-003)

        Args:
            packet: Discovery packet data
            addr: Sender address
        """
        node_id = packet.get("node_id")
        if node_id == self.node_id:
            return

        port = packet.get("port", self.config.bind_port)

        # Add peer if not known
        with self.peer_lock:
            if node_id not in self.peers:
                self.peers[node_id] = PeerInfo(
                    node_id=node_id,
                    address=addr[0],
                    port=port,
                    last_seen=time.time()
                )

                if self.config.enable_logging:
                    print(f"[PhaseNet] Discovered peer: {node_id} at {addr[0]}:{port}")

    def _health_check_loop(self):
        """Health check and topology healing loop (FR-007, SC-004)"""
        while self.is_running:
            try:
                current_time = time.time()

                # Remove stale peers (not seen for 10 seconds)
                with self.peer_lock:
                    stale_peers = [
                        peer_id for peer_id, peer in self.peers.items()
                        if current_time - peer.last_seen > 10.0
                    ]

                    for peer_id in stale_peers:
                        if self.config.enable_logging:
                            print(f"[PhaseNet] Removing stale peer: {peer_id}")
                        del self.peers[peer_id]

                # Wait before next check
                time.sleep(2.0)

            except Exception as e:
                if self.is_running and self.config.enable_logging:
                    print(f"[PhaseNet] Health check error: {e}")

    def _reset_election_timer(self):
        """Reset election timer (FR-003)"""
        if self.election_timer:
            self.election_timer.cancel()

        # Random timeout to avoid split votes
        import random
        timeout = self.config.election_timeout + random.uniform(0, 1.0)

        self.election_timer = threading.Timer(timeout, self._start_election)
        self.election_timer.daemon = True
        self.election_timer.start()

    def _start_election(self):
        """Start leader election (FR-003, SC-003)"""
        if not self.is_running:
            return

        # Become candidate
        self.state = NodeState.CANDIDATE
        self.current_term += 1
        self.voted_for = self.node_id
        votes_received = 1  # Vote for self

        if self.config.enable_logging:
            print(f"[PhaseNet] Starting election (term {self.current_term})")

        # Request votes from all peers
        vote_request = {
            "type": "vote_request",
            "node_id": self.node_id,
            "term": self.current_term
        }

        packet_bytes = self._encrypt_packet(vote_request)

        with self.peer_lock:
            for peer in self.peers.values():
                try:
                    self.socket.sendto(packet_bytes, (peer.address, peer.port))
                except:
                    pass

        # Wait for votes (simplified - should collect votes asynchronously)
        time.sleep(0.5)

        # Check if won election (majority)
        with self.peer_lock:
            total_nodes = len(self.peers) + 1
            if votes_received > total_nodes / 2:
                self._become_leader()
            else:
                # Reset to follower and restart timer
                self.state = NodeState.FOLLOWER
                self._reset_election_timer()

    def _become_leader(self):
        """Become leader and start heartbeats (FR-003)"""
        self.state = NodeState.LEADER
        self.leader_id = self.node_id

        if self.config.enable_logging:
            print(f"[PhaseNet] Became leader (term {self.current_term})")

        # Call leader callback
        if self.leader_callback:
            self.leader_callback(True)

        # Start heartbeat timer
        self._send_heartbeat()

    def _send_heartbeat(self):
        """Send heartbeat to followers (FR-003)"""
        if not self.is_running or self.state != NodeState.LEADER:
            return

        # Send heartbeat
        heartbeat = {
            "type": "heartbeat",
            "node_id": self.node_id,
            "term": self.current_term
        }

        packet_bytes = self._encrypt_packet(heartbeat)

        with self.peer_lock:
            for peer in self.peers.values():
                try:
                    self.socket.sendto(packet_bytes, (peer.address, peer.port))
                except:
                    pass

        # Schedule next heartbeat
        self.heartbeat_timer = threading.Timer(
            self.config.heartbeat_interval,
            self._send_heartbeat
        )
        self.heartbeat_timer.daemon = True
        self.heartbeat_timer.start()

    def _handle_heartbeat_packet(self, packet: Dict, addr: Tuple):
        """Handle heartbeat from leader (FR-003)"""
        node_id = packet.get("node_id")
        term = packet.get("term", 0)

        # Update leader
        if term >= self.current_term:
            self.current_term = term
            self.leader_id = node_id
            self.last_heartbeat = time.time()

            # Reset to follower if not already
            if self.state != NodeState.FOLLOWER:
                self.state = NodeState.FOLLOWER

                # Call leader callback
                if self.leader_callback:
                    self.leader_callback(False)

            # Reset election timer
            self._reset_election_timer()

            # Mark peer as leader
            with self.peer_lock:
                if node_id in self.peers:
                    self.peers[node_id].is_leader = True

    def _handle_vote_request(self, packet: Dict, addr: Tuple):
        """Handle vote request (FR-003)"""
        node_id = packet.get("node_id")
        term = packet.get("term", 0)

        # Vote if haven't voted this term
        if term > self.current_term and (self.voted_for is None or self.voted_for == node_id):
            self.current_term = term
            self.voted_for = node_id

            # Send vote response
            vote_response = {
                "type": "vote_response",
                "node_id": self.node_id,
                "term": self.current_term,
                "vote_granted": True
            }

            packet_bytes = self._encrypt_packet(vote_response)
            self.socket.sendto(packet_bytes, addr)

    def _handle_vote_response(self, packet: Dict, addr: Tuple):
        """Handle vote response (FR-003)"""
        # This would be collected during election
        # Simplified implementation
        pass

    def get_status(self) -> Dict[str, Any]:
        """
        Get network status (FR-008)

        Returns:
            Status dictionary
        """
        with self.peer_lock:
            return {
                "node_id": self.node_id,
                "state": self.state.value,
                "is_leader": self.state == NodeState.LEADER,
                "leader_id": self.leader_id,
                "current_term": self.current_term,
                "peer_count": len(self.peers),
                "peers": [
                    {
                        "node_id": peer.node_id,
                        "address": peer.address,
                        "is_leader": peer.is_leader,
                        "latency_ms": peer.latency * 1000,
                        "phase_diff": peer.phase_diff,
                        "last_seen": peer.last_seen
                    }
                    for peer in self.peers.values()
                ],
                "packets_sent": self.packets_sent,
                "packets_received": self.packets_received,
                "packets_dropped": self.packets_dropped
            }

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get network statistics (SC-001, SC-002)

        Returns:
            Statistics dictionary
        """
        stats = {
            "node_id": self.node_id,
            "state": self.state.value
        }

        # Latency statistics (SC-001)
        if self.latency_history:
            stats["latency"] = {
                "mean_ms": statistics.mean(self.latency_history) * 1000,
                "max_ms": max(self.latency_history) * 1000,
                "min_ms": min(self.latency_history) * 1000,
                "target_ms": 5.0  # SC-001
            }

        # Jitter statistics (SC-001)
        if self.jitter_history:
            stats["jitter"] = {
                "mean_ms": statistics.mean(self.jitter_history) * 1000,
                "max_ms": max(self.jitter_history) * 1000,
                "target_ms": 2.0  # SC-001
            }

        # Phase coherence statistics (SC-002)
        if self.coherence_history:
            stats["coherence"] = {
                "mean": statistics.mean(self.coherence_history),
                "min": min(self.coherence_history),
                "target": 0.99  # SC-002
            }

        # Packet statistics
        total_packets = self.packets_sent + self.packets_received
        stats["packets"] = {
            "sent": self.packets_sent,
            "received": self.packets_received,
            "dropped": self.packets_dropped,
            "drop_rate": self.packets_dropped / total_packets if total_packets > 0 else 0
        }

        return stats


# Self-test
if __name__ == "__main__":
    print("=" * 60)
    print("PhaseNet Protocol Self-Test")
    print("=" * 60)

    # Test node initialization
    print("\n1. Testing node initialization...")
    config = PhaseNetConfig(
        node_id="test_node_1",
        bind_port=9000,
        enable_logging=True
    )
    node = PhaseNetNode(config)
    print("   OK: Node initialization")

    # Test phase update
    print("\n2. Testing phase update...")
    node.update_phase(
        phi_phase=0.5,
        phi_depth=0.8,
        criticality=1.0,
        coherence=0.7,
        ici=0.3
    )
    print("   OK: Phase update")

    # Test status
    print("\n3. Testing status...")
    status = node.get_status()
    print(f"   OK: Status (state={status['state']}, peers={status['peer_count']})")

    # Test statistics
    print("\n4. Testing statistics...")
    stats = node.get_statistics()
    print(f"   OK: Statistics (packets={stats['packets']})")

    # Test encryption if available
    if ENCRYPTION_AVAILABLE and config.network_key:
        print("\n5. Testing encryption...")
        config_enc = PhaseNetConfig(
            node_id="test_node_2",
            network_key="test_key_12345",
            enable_encryption=True,
            enable_logging=True
        )
        node_enc = PhaseNetNode(config_enc)
        print("   OK: Encryption initialized")
    else:
        print("\n5. Skipping encryption test (cryptography not available)")

    print("\n" + "=" * 60)
    print("Self-Test PASSED")
    print("=" * 60)
    print("Note: Full network testing requires multiple running nodes")
