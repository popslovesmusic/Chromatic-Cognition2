#!/usr/bin/env python3
"""
Example 04: Session Recording and Playback

Demonstrates session recording features:
- Start/stop recording
- Save session data
- Replay sessions
- Export metrics

Usage:
    python examples/04_session_recording.py
"""

import requests
import json
import os
import time
from typing import Dict, Any, List


class SessionClient:
    """Client for session recording and playback API"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()

    def start_recording(self, session_name: str = None) -> Dict[str, Any]:
        """Start a new recording session"""
        data = {}
        if session_name:
            data['name'] = session_name

        response = self.session.post(
            f"{self.base_url}/api/session/start",
            json=data
        )
        response.raise_for_status()
        return response.json()

    def stop_recording(self) -> Dict[str, Any]:
        """Stop current recording session"""
        response = self.session.post(f"{self.base_url}/api/session/stop")
        response.raise_for_status()
        return response.json()

    def get_recording_status(self) -> Dict[str, Any]:
        """Get current recording status"""
        response = self.session.get(f"{self.base_url}/api/session/status")
        response.raise_for_status()
        return response.json()

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all recorded sessions"""
        response = self.session.get(f"{self.base_url}/api/session/list")
        response.raise_for_status()
        return response.json()

    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get session details"""
        response = self.session.get(f"{self.base_url}/api/session/{session_id}")
        response.raise_for_status()
        return response.json()

    def delete_session(self, session_id: str) -> Dict[str, Any]:
        """Delete a recorded session"""
        response = self.session.delete(f"{self.base_url}/api/session/{session_id}")
        response.raise_for_status()
        return response.json()

    def export_session(self, session_id: str, filename: str,
                       format: str = "json") -> str:
        """Export session data to file"""
        params = {'format': format}
        response = self.session.get(
            f"{self.base_url}/api/session/{session_id}/export",
            params=params
        )
        response.raise_for_status()

        with open(filename, 'wb') as f:
            f.write(response.content)

        return filename

    def get_session_statistics(self, session_id: str) -> Dict[str, Any]:
        """Get session statistics"""
        response = self.session.get(
            f"{self.base_url}/api/session/{session_id}/stats"
        )
        response.raise_for_status()
        return response.json()


def main():
    """Main example"""
    print("=" * 70)
    print("Soundlab Session Recording Example")
    print("=" * 70)

    # Get server URL from environment or use default
    server_url = os.getenv('SOUNDLAB_API_URL', 'http://localhost:8000')
    print(f"\nConnecting to: {server_url}")

    # Create client
    client = SessionClient(server_url)

    try:
        # 1. Check initial status
        print("\n1. Check Recording Status")
        print("-" * 70)
        status = client.get_recording_status()
        print(f"Recording: {status.get('is_recording', False)}")

        # 2. Start recording
        print("\n2. Start New Recording")
        print("-" * 70)
        session_name = f"Example Session {int(time.time())}"
        result = client.start_recording(session_name)
        session_id = result.get('session_id')
        print(f"✓ Started recording: {session_name}")
        print(f"  Session ID: {session_id[:16]}...")

        # 3. Record for a few seconds
        print("\n3. Recording...")
        print("-" * 70)
        for i in range(5):
            time.sleep(1)
            status = client.get_recording_status()
            frames = status.get('frames_recorded', 0)
            duration = status.get('duration', 0)
            print(f"  {i+1}s | Frames: {frames:4d} | Duration: {duration:.2f}s")

        # 4. Stop recording
        print("\n4. Stop Recording")
        print("-" * 70)
        result = client.stop_recording()
        print(f"✓ Recording stopped")
        print(f"  Total frames: {result.get('total_frames', 0)}")
        print(f"  Duration: {result.get('duration', 0):.2f}s")

        # 5. Get session details
        print("\n5. Session Details")
        print("-" * 70)
        session = client.get_session(session_id)
        print(f"Name: {session.get('name')}")
        print(f"Created: {session.get('created_at')}")
        print(f"Frames: {session.get('frame_count', 0)}")
        print(f"Duration: {session.get('duration', 0):.2f}s")

        # 6. Get session statistics
        print("\n6. Session Statistics")
        print("-" * 70)
        stats = client.get_session_statistics(session_id)
        print(f"Average ICI: {stats.get('avg_ici', 0):.3f}")
        print(f"Average Criticality: {stats.get('avg_criticality', 0):.3f}")
        print(f"Average Coherence: {stats.get('avg_coherence', 0):.3f}")
        print(f"Peak Criticality: {stats.get('peak_criticality', 0):.3f}")
        print(f"Critical Events: {stats.get('critical_events', 0)}")

        # 7. List all sessions
        print("\n7. All Recorded Sessions")
        print("-" * 70)
        sessions = client.list_sessions()
        print(f"Total sessions: {len(sessions)}")
        for sess in sessions[-5:]:  # Show last 5
            print(f"  - {sess.get('name')} ({sess.get('duration', 0):.1f}s)")

        # 8. Export session
        print("\n8. Export Session Data")
        print("-" * 70)
        export_file = f"session_{session_id[:8]}.json"
        client.export_session(session_id, export_file, format="json")
        print(f"✓ Exported to: {export_file}")

        # 9. Cleanup: Delete example session
        print("\n9. Cleanup: Delete Example Session")
        print("-" * 70)
        client.delete_session(session_id)
        print(f"✓ Deleted session {session_id[:16]}...")

        print("\n" + "=" * 70)
        print("✓ All session operations completed!")
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
