"""
ABSnapshot - Memory-Resident A/B Comparison Manager

Implements FR-008: In-memory A/B snapshots with instant toggle and glitch-free switching
"""

from typing import Optional, Literal
import copy
import time

from .preset_model import Preset, create_default_preset


ABSlot = Literal["A", "B"]


class ABSnapshot:
    """
    A/B comparison snapshot manager

    Features:
    - Memory-resident snapshots (not auto-saved to disk)
    - Instant toggle between A and B states
    - Glitch-free switching with crossfade guard
    - State preservation across preset loads
    """

    CROSSFADE_GUARD_MS = 30  # Minimum time for smooth transition

    def __init__(self):
        """Initialize A/B snapshot manager"""
        self.snapshot_a: Optional[Preset] = None
        self.snapshot_b: Optional[Preset] = None
        self.current_slot: Optional[ABSlot] = None
        self.last_toggle_time = 0.0

        print("[ABSnapshot] Initialized")

    def store_a(self, preset: Preset):
        """
        Store current state as snapshot A

        Args:
            preset: Preset to store in slot A
        """
        # Deep copy to prevent external modifications
        self.snapshot_a = copy.deepcopy(preset)
        self.current_slot = "A"

        print(f"[ABSnapshot] Stored A: {preset.name}")

    def store_b(self, preset: Preset):
        """
        Store current state as snapshot B

        Args:
            preset: Preset to store in slot B
        """
        # Deep copy to prevent external modifications
        self.snapshot_b = copy.deepcopy(preset)
        self.current_slot = "B"

        print(f"[ABSnapshot] Stored B: {preset.name}")

    def get_a(self) -> Optional[Preset]:
        """
        Get snapshot A

        Returns:
            Deep copy of snapshot A or None
        """
        if self.snapshot_a:
            return copy.deepcopy(self.snapshot_a)
        return None

    def get_b(self) -> Optional[Preset]:
        """
        Get snapshot B

        Returns:
            Deep copy of snapshot B or None
        """
        if self.snapshot_b:
            return copy.deepcopy(self.snapshot_b)
        return None

    def toggle(self) -> Optional[Preset]:
        """
        Toggle between A and B snapshots

        Implements FR-008 requirement for glitch-free switching

        Returns:
            Preset to apply or None if toggle not possible

        Raises:
            ValueError: If both snapshots are empty
        """
        if self.snapshot_a is None and self.snapshot_b is None:
            raise ValueError("Cannot toggle: Both A and B snapshots are empty")

        # Enforce crossfade guard time
        current_time = time.time()
        time_since_last_toggle = (current_time - self.last_toggle_time) * 1000  # ms

        if time_since_last_toggle < self.CROSSFADE_GUARD_MS:
            print(f"[ABSnapshot] Toggle too fast ({time_since_last_toggle:.1f}ms < {self.CROSSFADE_GUARD_MS}ms)")
            return None

        # Determine target slot
        if self.current_slot == "A":
            if self.snapshot_b is None:
                raise ValueError("Cannot toggle to B: Snapshot B is empty")
            target_slot = "B"
            target_preset = self.get_b()
        elif self.current_slot == "B":
            if self.snapshot_a is None:
                raise ValueError("Cannot toggle to A: Snapshot A is empty")
            target_slot = "A"
            target_preset = self.get_a()
        else:
            # No current slot - default to A
            if self.snapshot_a:
                target_slot = "A"
                target_preset = self.get_a()
            elif self.snapshot_b:
                target_slot = "B"
                target_preset = self.get_b()
            else:
                return None

        # Update state
        self.current_slot = target_slot
        self.last_toggle_time = current_time

        print(f"[ABSnapshot] Toggled to {target_slot}: {target_preset.name if target_preset else 'None'}")

        return target_preset

    def get_current_slot(self) -> Optional[ABSlot]:
        """
        Get currently active slot

        Returns:
            'A', 'B', or None
        """
        return self.current_slot

    def is_slot_occupied(self, slot: ABSlot) -> bool:
        """
        Check if a slot has a snapshot stored

        Args:
            slot: 'A' or 'B'

        Returns:
            True if slot has a snapshot
        """
        if slot == "A":
            return self.snapshot_a is not None
        else:
            return self.snapshot_b is not None

    def get_diff(self) -> Optional[dict]:
        """
        Get differences between A and B snapshots

        Returns:
            Dictionary of changes or None if comparison not possible
        """
        if self.snapshot_a is None or self.snapshot_b is None:
            return None

        return self.snapshot_a.diff(self.snapshot_b)

    def clear_a(self):
        """Clear snapshot A"""
        self.snapshot_a = None
        if self.current_slot == "A":
            self.current_slot = None
        print("[ABSnapshot] Cleared A")

    def clear_b(self):
        """Clear snapshot B"""
        self.snapshot_b = None
        if self.current_slot == "B":
            self.current_slot = None
        print("[ABSnapshot] Cleared B")

    def clear_all(self):
        """Clear both snapshots"""
        self.snapshot_a = None
        self.snapshot_b = None
        self.current_slot = None
        print("[ABSnapshot] Cleared A and B")

    def get_status(self) -> dict:
        """
        Get A/B status information

        Returns:
            Dictionary with current state
        """
        return {
            'slot_a_occupied': self.is_slot_occupied("A"),
            'slot_b_occupied': self.is_slot_occupied("B"),
            'current_slot': self.current_slot,
            'slot_a_name': self.snapshot_a.name if self.snapshot_a else None,
            'slot_b_name': self.snapshot_b.name if self.snapshot_b else None,
            'time_since_last_toggle_ms': (time.time() - self.last_toggle_time) * 1000 if self.last_toggle_time > 0 else None
        }


# Self-test function
def _self_test():
    """Test ABSnapshot functionality"""
    print("=" * 60)
    print("ABSnapshot Self-Test")
    print("=" * 60)

    try:
        # Initialize manager
        print("\n1. Initializing AB manager...")
        ab = ABSnapshot()
        print("   ✓ Initialized")

        # Create test presets
        print("\n2. Creating test presets...")
        preset_a = Preset(name="Preset A", tags=["test"])
        preset_a.engine.coupling_strength = 0.5

        preset_b = Preset(name="Preset B", tags=["test"])
        preset_b.engine.coupling_strength = 1.5

        print("   ✓ Presets created")

        # Store snapshots
        print("\n3. Storing snapshots...")
        ab.store_a(preset_a)
        ab.store_b(preset_b)

        status = ab.get_status()
        print(f"   Slot A: {status['slot_a_name']} (occupied={status['slot_a_occupied']})")
        print(f"   Slot B: {status['slot_b_name']} (occupied={status['slot_b_occupied']})")
        print(f"   Current: {status['current_slot']}")
        assert status['slot_a_occupied']
        assert status['slot_b_occupied']
        print("   ✓ Snapshots stored")

        # Test toggle
        print("\n4. Testing toggle...")
        assert ab.get_current_slot() == "B"  # Last store was B

        toggled = ab.toggle()
        assert toggled is not None
        assert ab.get_current_slot() == "A"
        print(f"   Toggled to: {ab.get_current_slot()}")

        time.sleep(0.05)  # Wait for crossfade guard

        toggled = ab.toggle()
        assert toggled is not None
        assert ab.get_current_slot() == "B"
        print(f"   Toggled to: {ab.get_current_slot()}")

        print("   ✓ Toggle OK")

        # Test crossfade guard
        print("\n5. Testing crossfade guard...")
        time.sleep(0.05)
        ab.toggle()  # Should work (enough time passed)
        toggled = ab.toggle()  # Should return None (too fast)
        assert toggled is None
        print("   ✓ Crossfade guard working")

        # Test diff
        print("\n6. Testing diff...")
        diff = ab.get_diff()
        assert diff is not None
        print(f"   Found {len(diff)} differences")
        if 'engine.coupling_strength' in diff:
            print(f"     coupling_strength: {diff['engine.coupling_strength']}")
        print("   ✓ Diff OK")

        # Test clear
        print("\n7. Testing clear...")
        ab.clear_a()
        assert not ab.is_slot_occupied("A")
        assert ab.is_slot_occupied("B")

        ab.clear_all()
        assert not ab.is_slot_occupied("A")
        assert not ab.is_slot_occupied("B")
        print("   ✓ Clear OK")

        # Test empty toggle error
        print("\n8. Testing empty toggle error...")
        try:
            ab.toggle()
            assert False, "Should have raised ValueError"
        except ValueError as e:
            print(f"   Caught expected error: {e}")
            print("   ✓ Error handling OK")

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
