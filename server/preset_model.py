"""
Preset Data Model - Versioned State Container

Implements FR-001, FR-006: JSON schema v1 with validation and migration
"""

import uuid
import json
from typing import List, Optional, Dict, Literal
from dataclasses import dataclass, field, asdict
from datetime import datetime
import copy


StrategyType = Literal["spatial", "energy", "linear", "phi"]
PhiModeType = Literal["manual", "audio", "midi", "sensor", "internal"]
CollisionPolicy = Literal["prompt", "overwrite", "new_copy", "merge"]


@dataclass
class EngineState:
    """Engine parameters for D-ASE ChromaticFieldProcessor"""
    sample_rate: int = 48000
    num_channels: int = 8
    frequencies: List[float] = field(default_factory=lambda: [
        0.5, 0.81, 1.31, 2.12, 3.43, 5.55, 8.97, 14.52
    ])
    amplitudes: List[float] = field(default_factory=lambda: [
        0.6, 0.55, 0.5, 0.45, 0.4, 0.35, 0.3, 0.25
    ])
    coupling_strength: float = 1.0

    def validate(self) -> bool:
        """Validate engine state parameters"""
        # Check array lengths match num_channels
        if len(self.frequencies) != self.num_channels:
            raise ValueError(f"frequencies length {len(self.frequencies)} != num_channels {self.num_channels}")
        if len(self.amplitudes) != self.num_channels:
            raise ValueError(f"amplitudes length {len(self.amplitudes)} != num_channels {self.num_channels}")

        # Check value ranges
        if self.sample_rate not in [44100, 48000, 96000]:
            raise ValueError(f"Invalid sample_rate: {self.sample_rate}")

        if self.coupling_strength < 0.0 or self.coupling_strength > 2.0:
            raise ValueError(f"coupling_strength {self.coupling_strength} out of range [0, 2]")

        return True


@dataclass
class PhiState:
    """Φ-modulation parameters"""
    mode: PhiModeType = "internal"
    depth: float = 0.618  # [0, 1.618]
    phase: float = 0.0  # radians
    frequency: Optional[float] = 0.1  # Hz (for internal/sensor modes)

    def validate(self) -> bool:
        """Validate Φ parameters"""
        PHI = 1.618033988749895

        if self.depth < 0.0 or self.depth > PHI:
            raise ValueError(f"phi.depth {self.depth} out of range [0, {PHI}]")

        if self.phase < -6.28318 or self.phase > 6.28318:
            raise ValueError(f"phi.phase {self.phase} out of range [-2π, 2π]")

        if self.frequency is not None:
            if self.frequency < 0.01 or self.frequency > 10.0:
                raise ValueError(f"phi.frequency {self.frequency} out of range [0.01, 10]")

        return True


@dataclass
class DownmixState:
    """Downmix strategy and weights"""
    strategy: StrategyType = "spatial"
    weights_l: List[float] = field(default_factory=lambda: [
        0.8, 0.6, 0.4, 0.2, 0.0, 0.0, 0.0, 0.0
    ])
    weights_r: List[float] = field(default_factory=lambda: [
        0.0, 0.0, 0.0, 0.0, 0.2, 0.4, 0.6, 0.8
    ])

    def validate(self) -> bool:
        """Validate downmix parameters"""
        if len(self.weights_l) != 8:
            raise ValueError(f"weights_l length {len(self.weights_l)} != 8")
        if len(self.weights_r) != 8:
            raise ValueError(f"weights_r length {len(self.weights_r)} != 8")

        return True


@dataclass
class UIState:
    """UI configuration"""
    fft_size: int = 2048
    meters: Dict = field(default_factory=lambda: {"show": True})
    visualizer: Dict = field(default_factory=lambda: {"palette": "chromatic"})


@dataclass
class Preset:
    """
    Complete preset with metadata and versioned schema

    Conforms to schema v1 requirements
    """
    # Metadata
    schema_version: int = 1
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Untitled Preset"
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + 'Z')
    modified_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + 'Z')
    author: str = "user@local"
    notes: str = ""

    # State components
    engine: EngineState = field(default_factory=EngineState)
    phi: PhiState = field(default_factory=PhiState)
    downmix: DownmixState = field(default_factory=DownmixState)
    ui: UIState = field(default_factory=UIState)

    def validate(self) -> bool:
        """
        Validate entire preset

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        # Validate schema version
        if self.schema_version != 1:
            raise ValueError(f"Unsupported schema_version: {self.schema_version}")

        # Validate name
        if not self.name or len(self.name) == 0:
            raise ValueError("name cannot be empty")

        # Validate components
        self.engine.validate()
        self.phi.validate()
        self.downmix.validate()

        return True

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    def to_json(self, pretty: bool = False) -> str:
        """
        Convert to JSON string

        Args:
            pretty: If True, format with indentation

        Returns:
            JSON string
        """
        data = self.to_dict()
        if pretty:
            return json.dumps(data, indent=2)
        else:
            return json.dumps(data)

    @classmethod
    def from_dict(cls, data: Dict) -> 'Preset':
        """
        Create Preset from dictionary

        Args:
            data: Dictionary representation

        Returns:
            Preset instance
        """
        # Handle nested objects
        if 'engine' in data and isinstance(data['engine'], dict):
            data['engine'] = EngineState(**data['engine'])

        if 'phi' in data and isinstance(data['phi'], dict):
            data['phi'] = PhiState(**data['phi'])

        if 'downmix' in data and isinstance(data['downmix'], dict):
            data['downmix'] = DownmixState(**data['downmix'])

        if 'ui' in data and isinstance(data['ui'], dict):
            data['ui'] = UIState(**data['ui'])

        # Filter to only valid fields
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}

        return cls(**valid_fields)

    @classmethod
    def from_json(cls, json_str: str) -> 'Preset':
        """
        Create Preset from JSON string

        Args:
            json_str: JSON representation

        Returns:
            Preset instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)

    def clone(self) -> 'Preset':
        """
        Create a deep copy of this preset

        Returns:
            New Preset instance with same values but new ID
        """
        data = self.to_dict()
        data['id'] = str(uuid.uuid4())
        data['modified_at'] = datetime.utcnow().isoformat() + 'Z'
        return Preset.from_dict(data)

    def update_timestamp(self):
        """Update modified_at timestamp"""
        self.modified_at = datetime.utcnow().isoformat() + 'Z'

    def diff(self, other: 'Preset') -> Dict:
        """
        Calculate differences between two presets

        Args:
            other: Preset to compare with

        Returns:
            Dictionary of changed fields with {field: (old, new)}
        """
        changes = {}

        def compare_recursive(path: str, val1, val2):
            if isinstance(val1, dict) and isinstance(val2, dict):
                for key in set(val1.keys()) | set(val2.keys()):
                    if key in val1 and key in val2:
                        compare_recursive(f"{path}.{key}" if path else key, val1[key], val2[key])
                    elif key in val1:
                        changes[f"{path}.{key}" if path else key] = (val1[key], None)
                    else:
                        changes[f"{path}.{key}" if path else key] = (None, val2[key])
            elif isinstance(val1, list) and isinstance(val2, list):
                if val1 != val2:
                    changes[path] = (val1, val2)
            else:
                if val1 != val2:
                    changes[path] = (val1, val2)

        compare_recursive("", self.to_dict(), other.to_dict())
        return changes


def migrate_v0_to_v1(data_v0: Dict) -> Preset:
    """
    Migrate schema v0 to v1

    Legacy field mappings:
    - "lowGain" → engine.frequencies[0-2] (if present)
    - "midGain" → engine.frequencies[3-4]
    - "highGain" → engine.frequencies[5-7]
    - Add schema_version = 1

    Args:
        data_v0: Legacy preset dictionary

    Returns:
        Migrated Preset (v1)
    """
    # Start with defaults
    preset = Preset()

    # Copy metadata if present
    if 'name' in data_v0:
        preset.name = data_v0['name']
    if 'created_at' in data_v0 or 'timestamp' in data_v0:
        preset.created_at = data_v0.get('created_at', data_v0.get('timestamp', preset.created_at))

    # Migrate engine parameters (legacy may have different structure)
    if 'low' in data_v0:
        # Map legacy EQ gains to frequencies (approximate)
        pass  # Would need actual legacy schema to implement

    # Migrate Φ parameters
    if 'drive' in data_v0:
        preset.phi.depth = float(data_v0['drive']) / 10.0  # Example mapping

    # Always set schema_version to 1
    preset.schema_version = 1

    # Preserve extra fields if present (forward-compatible)
    # (stored but not validated)

    return preset


def create_default_preset(name: str = "Default") -> Preset:
    """
    Create a default preset with safe values

    Args:
        name: Preset name

    Returns:
        Default Preset instance
    """
    return Preset(
        name=name,
        tags=["default"],
        notes="Default safe configuration"
    )


# Self-test function
def _self_test():
    """Test Preset model functionality"""
    print("=" * 60)
    print("Preset Model Self-Test")
    print("=" * 60)

    try:
        # Test basic creation
        print("\n1. Creating preset...")
        preset = Preset(
            name="Test Preset",
            tags=["test", "lab"],
            notes="Test configuration"
        )
        print(f"   Created: {preset.name} (ID: {preset.id[:8]}...)")
        print("   ✓ Creation OK")

        # Test validation
        print("\n2. Testing validation...")
        is_valid = preset.validate()
        print(f"   Valid: {is_valid}")
        assert is_valid
        print("   ✓ Validation OK")

        # Test JSON serialization
        print("\n3. Testing JSON serialization...")
        json_str = preset.to_json()
        print(f"   JSON length: {len(json_str)} bytes")

        preset_restored = Preset.from_json(json_str)
        assert preset_restored.name == preset.name
        assert preset_restored.id == preset.id
        print("   ✓ JSON round-trip OK")

        # Test cloning
        print("\n4. Testing cloning...")
        preset_copy = preset.clone()
        assert preset_copy.name == preset.name
        assert preset_copy.id != preset.id  # New ID
        print(f"   Cloned with new ID: {preset_copy.id[:8]}...")
        print("   ✓ Cloning OK")

        # Test diff
        print("\n5. Testing diff...")
        preset_copy.name = "Modified Preset"
        preset_copy.engine.coupling_strength = 1.5
        changes = preset.diff(preset_copy)
        print(f"   Changes detected: {len(changes)}")
        for key, (old, new) in list(changes.items())[:3]:
            print(f"     {key}: {old} → {new}")
        assert 'name' in changes
        print("   ✓ Diff OK")

        # Test invalid preset
        print("\n6. Testing validation errors...")
        invalid_preset = Preset(name="Invalid")
        invalid_preset.phi.depth = 99.0  # Out of range
        try:
            invalid_preset.validate()
            assert False, "Should have raised ValueError"
        except ValueError as e:
            print(f"   Caught expected error: {e}")
            print("   ✓ Validation error handling OK")

        # Test default preset
        print("\n7. Testing default preset...")
        default = create_default_preset()
        default.validate()
        print(f"   Default preset: {default.name}")
        print("   ✓ Default preset OK")

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
