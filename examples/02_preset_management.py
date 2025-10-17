#!/usr/bin/env python3
"""
Example 02: Preset Management

Demonstrates preset CRUD operations:
- List/search presets
- Create/update/delete presets
- Import/export bundles
- A/B comparison

Usage:
    python examples/02_preset_management.py
"""

import requests
import json
import os
from typing import Dict, Any, List, Optional


class PresetClient:
    """Client for preset management API"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()

    def list_presets(self, query: Optional[str] = None,
                     tag: Optional[str] = None,
                     limit: int = 50) -> List[Dict[str, Any]]:
        """List presets with optional filtering"""
        params = {'limit': limit}
        if query:
            params['query'] = query
        if tag:
            params['tag'] = tag

        response = self.session.get(f"{self.base_url}/api/presets", params=params)
        response.raise_for_status()
        return response.json()

    def get_preset(self, preset_id: str) -> Dict[str, Any]:
        """Get preset by ID"""
        response = self.session.get(f"{self.base_url}/api/presets/{preset_id}")
        response.raise_for_status()
        return response.json()

    def create_preset(self, preset_data: Dict[str, Any],
                      collision: str = "prompt") -> Dict[str, Any]:
        """Create a new preset"""
        params = {'collision': collision}
        response = self.session.post(
            f"{self.base_url}/api/presets",
            json=preset_data,
            params=params
        )
        response.raise_for_status()
        return response.json()

    def update_preset(self, preset_id: str, preset_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing preset"""
        response = self.session.put(
            f"{self.base_url}/api/presets/{preset_id}",
            json=preset_data
        )
        response.raise_for_status()
        return response.json()

    def delete_preset(self, preset_id: str) -> Dict[str, Any]:
        """Delete preset by ID"""
        response = self.session.delete(f"{self.base_url}/api/presets/{preset_id}")
        response.raise_for_status()
        return response.json()

    def export_presets(self, filename: str = "presets_export.json"):
        """Export all presets to file"""
        response = self.session.post(f"{self.base_url}/api/presets/export")
        response.raise_for_status()

        with open(filename, 'wb') as f:
            f.write(response.content)

        return filename

    def import_presets(self, filename: str, dry_run: bool = False,
                       collision: str = "prompt") -> Dict[str, Any]:
        """Import presets from file"""
        params = {'dry_run': dry_run, 'collision': collision}

        with open(filename, 'rb') as f:
            files = {'file': (filename, f, 'application/json')}
            response = self.session.post(
                f"{self.base_url}/api/presets/import",
                files=files,
                params=params
            )

        response.raise_for_status()
        return response.json()

    def store_ab_snapshot(self, slot: str, preset_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store preset in A or B slot"""
        response = self.session.post(
            f"{self.base_url}/api/presets/ab/store/{slot}",
            json=preset_data
        )
        response.raise_for_status()
        return response.json()

    def get_ab_snapshot(self, slot: str) -> Dict[str, Any]:
        """Get preset from A or B slot"""
        response = self.session.get(f"{self.base_url}/api/presets/ab/get/{slot}")
        response.raise_for_status()
        return response.json()

    def toggle_ab(self) -> Dict[str, Any]:
        """Toggle between A and B presets"""
        response = self.session.post(f"{self.base_url}/api/presets/ab/toggle")
        response.raise_for_status()
        return response.json()

    def get_ab_diff(self) -> Dict[str, Any]:
        """Get differences between A and B"""
        response = self.session.get(f"{self.base_url}/api/presets/ab/diff")
        response.raise_for_status()
        return response.json()

    def get_statistics(self) -> Dict[str, Any]:
        """Get preset store statistics"""
        response = self.session.get(f"{self.base_url}/api/presets/stats")
        response.raise_for_status()
        return response.json()


def main():
    """Main example"""
    print("=" * 70)
    print("Soundlab Preset Management Example")
    print("=" * 70)

    # Get server URL from environment or use default
    server_url = os.getenv('SOUNDLAB_API_URL', 'http://localhost:8000')
    print(f"\nConnecting to: {server_url}")

    # Create client
    client = PresetClient(server_url)

    try:
        # 1. List presets
        print("\n1. List All Presets")
        print("-" * 70)
        presets = client.list_presets(limit=10)
        print(f"Found {len(presets)} presets")
        for preset in presets[:5]:  # Show first 5
            print(f"  - {preset.get('name', 'Untitled')} (ID: {preset.get('id', 'N/A')[:8]}...)")

        # 2. Create a new preset
        print("\n2. Create New Preset")
        print("-" * 70)
        new_preset = {
            'name': 'Example Preset',
            'notes': 'Created by SDK example',
            'tags': ['example', 'sdk']
        }
        result = client.create_preset(new_preset, collision='new_copy')
        preset_id = result['id']
        print(f"Created preset: {result['name']} (ID: {preset_id[:8]}...)")

        # 3. Get the preset
        print("\n3. Get Preset Details")
        print("-" * 70)
        preset = client.get_preset(preset_id)
        print(f"Name: {preset.get('name')}")
        print(f"Created: {preset.get('created_at')}")
        print(f"Tags: {', '.join(preset.get('tags', []))}")

        # 4. Update the preset
        print("\n4. Update Preset")
        print("-" * 70)
        preset['notes'] = 'Updated via SDK'
        preset['tags'].append('updated')
        client.update_preset(preset_id, preset)
        print("✓ Preset updated")

        # 5. Statistics
        print("\n5. Preset Statistics")
        print("-" * 70)
        stats = client.get_statistics()
        print(f"Total presets: {stats.get('total_presets', 0)}")
        print(f"Total tags: {stats.get('total_tags', 0)}")
        print(f"Disk usage: {stats.get('disk_usage_bytes', 0)} bytes")

        # 6. A/B Comparison
        print("\n6. A/B Comparison")
        print("-" * 70)
        if len(presets) >= 2:
            # Store two presets in A and B slots
            preset_a = client.get_preset(presets[0]['id'])
            preset_b = client.get_preset(presets[1]['id'])

            client.store_ab_snapshot('A', preset_a)
            print(f"✓ Stored '{preset_a['name']}' in slot A")

            client.store_ab_snapshot('B', preset_b)
            print(f"✓ Stored '{preset_b['name']}' in slot B")

            # Get diff
            diff = client.get_ab_diff()
            print(f"\nDifferences: {len(diff.get('differences', []))} parameters changed")
        else:
            print("Need at least 2 presets for A/B comparison")

        # 7. Delete the example preset
        print("\n7. Cleanup: Delete Example Preset")
        print("-" * 70)
        client.delete_preset(preset_id)
        print(f"✓ Deleted preset {preset_id[:8]}...")

        print("\n" + "=" * 70)
        print("✓ All preset operations completed!")
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
