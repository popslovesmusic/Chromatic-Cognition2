"""
PresetStore - Filesystem-backed Preset Management

Implements FR-001, FR-002, FR-005, FR-007, FR-009:
- CRUD operations on ./presets/
- Search and filtering
- Collision resolution
- Audit logging
- Import/Export with dry-run validation
"""

import os
import json
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from datetime import datetime
import logging

from .preset_model import Preset, CollisionPolicy, create_default_preset


class PresetStore:
    """
    Filesystem-backed preset storage and management

    Features:
    - CRUD operations (Create, Read, Update, Delete)
    - Search by name/tags
    - Collision resolution strategies
    - Audit logging
    - Import/Export with validation
    """

    def __init__(self,
                 presets_dir: Optional[str] = None,
                 log_dir: Optional[str] = None):
        """
        Initialize preset store

        Args:
            presets_dir: Directory for preset files (None = ./presets/)
            log_dir: Directory for audit logs (None = ./logs/presets/)
        """
        # Setup directories
        if presets_dir is None:
            presets_dir = os.path.join(os.path.dirname(__file__), "..", "presets")
        if log_dir is None:
            log_dir = os.path.join(os.path.dirname(__file__), "..", "logs", "presets")

        self.presets_dir = Path(presets_dir)
        self.log_dir = Path(log_dir)

        # Create directories if they don't exist
        self.presets_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Audit logging
        self.audit_log = None
        self._init_audit_log()

        # Statistics
        self.stats = {
            'created': 0,
            'updated': 0,
            'deleted': 0,
            'loaded': 0,
            'errors': 0
        }

        print(f"[PresetStore] Initialized")
        print(f"[PresetStore] Presets: {self.presets_dir}")
        print(f"[PresetStore] Logs: {self.log_dir}")

    def _init_audit_log(self):
        """Initialize audit log file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = self.log_dir / f"audit_{timestamp}.log"

        try:
            self.audit_log = open(log_path, 'a')
            self._log_audit("SYSTEM", "INIT", "PresetStore initialized")
        except Exception as e:
            print(f"[PresetStore] WARNING: Could not init audit log: {e}")
            self.audit_log = None

    def _log_audit(self, action: str, target: str, result: str, details: str = ""):
        """
        Log audit entry (FR-007)

        Args:
            action: Action performed (SAVE, LOAD, DELETE, etc.)
            target: Target preset ID or name
            result: SUCCESS or FAILURE
            details: Additional details
        """
        if self.audit_log and not self.audit_log.closed:
            timestamp = datetime.now().isoformat()
            entry = f"{timestamp} | {action:10} | {target:30} | {result:10} | {details}\n"
            try:
                self.audit_log.write(entry)
                self.audit_log.flush()
            except:
                pass

    def _get_preset_path(self, preset_id: str) -> Path:
        """Get filepath for preset ID"""
        # Sanitize ID to prevent directory traversal
        safe_id = "".join(c for c in preset_id if c.isalnum() or c in ('-', '_'))
        return self.presets_dir / f"{safe_id}.json"

    def create(self, preset: Preset, collision: CollisionPolicy = "prompt") -> Tuple[str, bool]:
        """
        Create/save a new preset (FR-002: POST /api/presets)

        Args:
            preset: Preset to save
            collision: Collision resolution strategy

        Returns:
            Tuple of (preset_id, was_created)
                was_created = False if existing preset was updated

        Raises:
            FileExistsError: If collision="prompt" and preset exists
            ValueError: If preset validation fails
        """
        # Validate preset
        try:
            preset.validate()
        except ValueError as e:
            self._log_audit("CREATE", preset.name, "FAILURE", f"Validation error: {e}")
            self.stats['errors'] += 1
            raise

        preset_path = self._get_preset_path(preset.id)
        existed = preset_path.exists()

        # Handle collision
        if existed:
            if collision == "prompt":
                self._log_audit("CREATE", preset.name, "FAILURE", "Preset exists, prompt required")
                raise FileExistsError(f"Preset {preset.id} already exists")

            elif collision == "new_copy":
                # Create new ID for copy
                preset = preset.clone()
                preset.name = f"{preset.name} (Copy)"
                preset_path = self._get_preset_path(preset.id)
                existed = False

            elif collision == "merge":
                # Load existing and merge (keep newer values)
                existing = self.load(preset.id)
                if existing:
                    # Simple merge: take non-default values from preset
                    # (Full merge logic would be more complex)
                    pass

            # collision == "overwrite": just continue and overwrite

        # Save preset
        try:
            preset.update_timestamp()
            with open(preset_path, 'w') as f:
                f.write(preset.to_json(pretty=True))

            if existed:
                self._log_audit("UPDATE", preset.name, "SUCCESS", f"ID: {preset.id}")
                self.stats['updated'] += 1
            else:
                self._log_audit("CREATE", preset.name, "SUCCESS", f"ID: {preset.id}")
                self.stats['created'] += 1

            return preset.id, not existed

        except Exception as e:
            self._log_audit("CREATE", preset.name, "FAILURE", str(e))
            self.stats['errors'] += 1
            raise

    def load(self, preset_id: str) -> Optional[Preset]:
        """
        Load preset by ID (FR-002: GET /api/presets/{id})

        Args:
            preset_id: Preset identifier

        Returns:
            Preset instance or None if not found
        """
        preset_path = self._get_preset_path(preset_id)

        if not preset_path.exists():
            self._log_audit("LOAD", preset_id, "FAILURE", "Not found")
            return None

        try:
            with open(preset_path, 'r') as f:
                data = json.load(f)

            preset = Preset.from_dict(data)

            # Validate loaded preset
            preset.validate()

            self._log_audit("LOAD", preset.name, "SUCCESS", f"ID: {preset_id}")
            self.stats['loaded'] += 1

            return preset

        except json.JSONDecodeError as e:
            self._log_audit("LOAD", preset_id, "FAILURE", f"JSON error: {e}")
            self.stats['errors'] += 1
            return None

        except ValueError as e:
            self._log_audit("LOAD", preset_id, "FAILURE", f"Validation error: {e}")
            self.stats['errors'] += 1
            return None

        except Exception as e:
            self._log_audit("LOAD", preset_id, "FAILURE", str(e))
            self.stats['errors'] += 1
            return None

    def update(self, preset: Preset) -> bool:
        """
        Update existing preset (FR-002: PUT /api/presets/{id})

        Args:
            preset: Preset with updated values

        Returns:
            True if updated successfully
        """
        preset_path = self._get_preset_path(preset.id)

        if not preset_path.exists():
            self._log_audit("UPDATE", preset.id, "FAILURE", "Not found")
            return False

        try:
            preset.validate()
            preset.update_timestamp()

            with open(preset_path, 'w') as f:
                f.write(preset.to_json(pretty=True))

            self._log_audit("UPDATE", preset.name, "SUCCESS", f"ID: {preset.id}")
            self.stats['updated'] += 1
            return True

        except Exception as e:
            self._log_audit("UPDATE", preset.name, "FAILURE", str(e))
            self.stats['errors'] += 1
            return False

    def delete(self, preset_id: str) -> bool:
        """
        Delete preset by ID (FR-002: DELETE /api/presets/{id})

        Args:
            preset_id: Preset identifier

        Returns:
            True if deleted successfully
        """
        preset_path = self._get_preset_path(preset_id)

        if not preset_path.exists():
            self._log_audit("DELETE", preset_id, "FAILURE", "Not found")
            return False

        try:
            # Load name before deleting for audit log
            preset = self.load(preset_id)
            name = preset.name if preset else preset_id

            preset_path.unlink()

            self._log_audit("DELETE", name, "SUCCESS", f"ID: {preset_id}")
            self.stats['deleted'] += 1
            return True

        except Exception as e:
            self._log_audit("DELETE", preset_id, "FAILURE", str(e))
            self.stats['errors'] += 1
            return False

    def list(self,
             query: Optional[str] = None,
             tag: Optional[str] = None,
             limit: int = 50) -> List[Dict]:
        """
        List presets with optional filtering (FR-002: GET /api/presets)

        Args:
            query: Search query (matches name or notes)
            tag: Filter by tag
            limit: Maximum results

        Returns:
            List of preset metadata dictionaries
        """
        results = []

        for preset_path in self.presets_dir.glob("*.json"):
            try:
                with open(preset_path, 'r') as f:
                    data = json.load(f)

                # Apply filters
                if query:
                    name_match = query.lower() in data.get('name', '').lower()
                    notes_match = query.lower() in data.get('notes', '').lower()
                    if not (name_match or notes_match):
                        continue

                if tag:
                    if tag not in data.get('tags', []):
                        continue

                # Extract metadata
                metadata = {
                    'id': data.get('id'),
                    'name': data.get('name'),
                    'tags': data.get('tags', []),
                    'modified_at': data.get('modified_at'),
                    'author': data.get('author'),
                    'notes': data.get('notes', '')[:100]  # Truncate notes
                }

                results.append(metadata)

                if len(results) >= limit:
                    break

            except:
                continue  # Skip corrupted files

        # Sort by modified_at (most recent first)
        results.sort(key=lambda x: x['modified_at'], reverse=True)

        return results

    def export_all(self) -> Dict:
        """
        Export all presets as a single bundle (FR-009)

        Returns:
            Dictionary with schema version and presets array
        """
        bundle = {
            "schema_version": 1,
            "export_date": datetime.utcnow().isoformat() + 'Z',
            "presets": []
        }

        for preset_path in self.presets_dir.glob("*.json"):
            try:
                with open(preset_path, 'r') as f:
                    data = json.load(f)
                bundle["presets"].append(data)
            except:
                continue

        self._log_audit("EXPORT", "ALL", "SUCCESS", f"{len(bundle['presets'])} presets")

        return bundle

    def import_bundle(self,
                     bundle: Dict,
                     collision: CollisionPolicy = "prompt",
                     dry_run: bool = False) -> Dict:
        """
        Import preset bundle (FR-009)

        Args:
            bundle: Export bundle dictionary
            collision: Collision resolution strategy
            dry_run: If True, validate only, don't save

        Returns:
            Dictionary with import results:
                {
                    'imported': int,
                    'updated': int,
                    'skipped': int,
                    'errors': List[str]
                }
        """
        results = {
            'imported': 0,
            'updated': 0,
            'skipped': 0,
            'errors': []
        }

        # Validate bundle schema
        if 'presets' not in bundle:
            results['errors'].append("Invalid bundle: missing 'presets' array")
            return results

        for preset_data in bundle['presets']:
            try:
                # Create Preset from data
                preset = Preset.from_dict(preset_data)

                # Validate
                preset.validate()

                if dry_run:
                    results['imported'] += 1
                    continue

                # Save with collision handling
                preset_id, was_created = self.create(preset, collision=collision)

                if was_created:
                    results['imported'] += 1
                else:
                    results['updated'] += 1

            except FileExistsError:
                results['skipped'] += 1
            except ValueError as e:
                results['errors'].append(f"Preset '{preset_data.get('name')}': {e}")
            except Exception as e:
                results['errors'].append(f"Preset '{preset_data.get('name')}': {e}")

        mode = "DRY_RUN" if dry_run else "IMPORT"
        self._log_audit(mode, "BUNDLE", "SUCCESS",
                       f"imported={results['imported']}, updated={results['updated']}, errors={len(results['errors'])}")

        return results

    def get_statistics(self) -> Dict:
        """Get store statistics"""
        total_presets = len(list(self.presets_dir.glob("*.json")))

        return {
            **self.stats,
            'total_presets': total_presets
        }

    def close(self):
        """Close audit log and cleanup"""
        if self.audit_log and not self.audit_log.closed:
            self._log_audit("SYSTEM", "SHUTDOWN", "PresetStore closing")
            self.audit_log.close()

        print("[PresetStore] Closed")

    def __del__(self):
        """Ensure cleanup"""
        self.close()


# Self-test function
def _self_test():
    """Test PresetStore functionality"""
    print("=" * 60)
    print("PresetStore Self-Test")
    print("=" * 60)

    try:
        import tempfile
        from preset_model import Preset

        # Create temporary directory for testing
        temp_dir = tempfile.mkdtemp()
        print(f"\n1. Using temp directory: {temp_dir}")

        # Initialize store
        print("\n2. Initializing store...")
        store = PresetStore(presets_dir=temp_dir)
        print("   ✓ Store initialized")

        # Create test preset
        print("\n3. Creating preset...")
        preset = Preset(
            name="Test Preset",
            tags=["test", "lab"],
            notes="Test configuration"
        )
        preset_id, was_created = store.create(preset, collision="overwrite")
        print(f"   ✓ Created: {preset_id[:8]}... (was_created={was_created})")

        # Load preset
        print("\n4. Loading preset...")
        loaded = store.load(preset_id)
        assert loaded is not None
        assert loaded.name == preset.name
        print(f"   ✓ Loaded: {loaded.name}")

        # List presets
        print("\n5. Listing presets...")
        presets = store.list()
        print(f"   Found {len(presets)} presets")
        assert len(presets) == 1
        print("   ✓ List OK")

        # Update preset
        print("\n6. Updating preset...")
        loaded.name = "Modified Preset"
        success = store.update(loaded)
        assert success
        print("   ✓ Update OK")

        # Search
        print("\n7. Searching...")
        results = store.list(query="modified")
        print(f"   Found {len(results)} matches")
        assert len(results) == 1
        print("   ✓ Search OK")

        # Export all
        print("\n8. Exporting all...")
        bundle = store.export_all()
        print(f"   Exported {len(bundle['presets'])} presets")
        assert len(bundle['presets']) == 1
        print("   ✓ Export OK")

        # Delete preset
        print("\n9. Deleting preset...")
        success = store.delete(preset_id)
        assert success
        presets_after = store.list()
        assert len(presets_after) == 0
        print("   ✓ Delete OK")

        # Import bundle
        print("\n10. Importing bundle...")
        results = store.import_bundle(bundle, collision="overwrite")
        print(f"   Imported: {results['imported']}, Errors: {len(results['errors'])}")
        assert results['imported'] == 1
        print("   ✓ Import OK")

        # Statistics
        print("\n11. Getting statistics...")
        stats = store.get_statistics()
        print(f"   Stats: {stats}")
        print("   ✓ Statistics OK")

        # Cleanup
        print("\n12. Cleanup...")
        store.close()
        shutil.rmtree(temp_dir)
        print("   ✓ Cleanup complete")

        print("\n" + "=" * 60)
        print("Self-Test PASSED ✓")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n✗ Self-Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    _self_test()
