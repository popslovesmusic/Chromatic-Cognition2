#!/usr/bin/env python3
"""
Example 01: Basic REST API Client

Demonstrates basic REST API usage:
- Health checks
- Version info
- Metrics endpoint
- Dashboard state

Usage:
    python examples/01_basic_client.py
"""

import requests
import json
import os
from typing import Dict, Any


class SoundlabClient:
    """Simple REST API client for Soundlab"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()

    def health_check(self) -> Dict[str, Any]:
        """Check if server is healthy"""
        response = self.session.get(f"{self.base_url}/healthz")
        response.raise_for_status()
        return response.json()

    def readiness_check(self) -> Dict[str, Any]:
        """Check if server is ready to accept requests"""
        response = self.session.get(f"{self.base_url}/readyz")
        response.raise_for_status()
        return response.json()

    def get_version(self) -> Dict[str, Any]:
        """Get server version info"""
        response = self.session.get(f"{self.base_url}/version")
        response.raise_for_status()
        return response.json()

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics snapshot"""
        response = self.session.get(f"{self.base_url}/metrics")
        response.raise_for_status()
        return response.json()

    def get_dashboard_state(self) -> Dict[str, Any]:
        """Get full dashboard state"""
        response = self.session.get(f"{self.base_url}/api/dashboard/state")
        response.raise_for_status()
        return response.json()

    def get_status(self) -> Dict[str, Any]:
        """Get server status"""
        response = self.session.get(f"{self.base_url}/api/status")
        response.raise_for_status()
        return response.json()


def main():
    """Main example"""
    print("=" * 70)
    print("Soundlab Basic Client Example")
    print("=" * 70)

    # Get server URL from environment or use default
    server_url = os.getenv('SOUNDLAB_API_URL', 'http://localhost:8000')
    print(f"\nConnecting to: {server_url}")

    # Create client
    client = SoundlabClient(server_url)

    try:
        # Health check
        print("\n1. Health Check")
        print("-" * 70)
        health = client.health_check()
        print(json.dumps(health, indent=2))

        # Readiness check
        print("\n2. Readiness Check")
        print("-" * 70)
        readiness = client.readiness_check()
        print(json.dumps(readiness, indent=2))

        # Version info
        print("\n3. Version Info")
        print("-" * 70)
        version = client.get_version()
        print(json.dumps(version, indent=2))

        # Current metrics
        print("\n4. Current Metrics Snapshot")
        print("-" * 70)
        metrics = client.get_metrics()
        print(f"Frame: {metrics.get('frame', 'N/A')}")
        print(f"ICI: {metrics.get('ici', 0):.3f}")
        print(f"Criticality: {metrics.get('criticality', 0):.3f}")
        print(f"Coherence: {metrics.get('phase_coherence', 0):.3f}")
        print(f"Φ Depth: {metrics.get('phi_depth', 0):.3f}")
        print(f"Φ Phase: {metrics.get('phi_phase', 0):.3f}")

        # Dashboard state
        print("\n5. Dashboard State")
        print("-" * 70)
        state = client.get_dashboard_state()
        print(f"Active Channels: {state.get('active_channels', 0)}")
        print(f"Auto-Φ Enabled: {state.get('auto_phi_enabled', False)}")
        print(f"Criticality Balancer: {state.get('criticality_balancer_enabled', False)}")

        # Status
        print("\n6. Server Status")
        print("-" * 70)
        status = client.get_status()
        print(f"Uptime: {status.get('uptime', 0):.1f}s")
        print(f"Total Frames: {status.get('total_frames', 0)}")
        print(f"FPS: {status.get('fps', 0):.1f}")

        print("\n" + "=" * 70)
        print("✓ All checks passed!")
        print("=" * 70)

    except requests.ConnectionError:
        print(f"\n✗ Error: Could not connect to {server_url}")
        print("Make sure the server is running: cd server && python main.py")
    except requests.HTTPError as e:
        print(f"\n✗ HTTP Error: {e}")
        print(f"Response: {e.response.text}")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")


if __name__ == "__main__":
    main()
