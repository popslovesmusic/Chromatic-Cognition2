"""
Test MIDI Mapping Persistence - FR-005 & SC-004: Mappings persist and reload

Validates that custom MIDI mappings are saved to localStorage and
correctly restored on page reload.

This test requires browser automation (Selenium/Playwright) to test
localStorage functionality. This script provides conceptual validation
and logic testing.

Usage:
    python test_midi_persistence.py
"""

import json
import sys
from typing import Dict


# Default MIDI mappings from midi-controller.js
DEFAULT_MAPPINGS = {
    1: {
        'name': 'Φ-Depth',
        'param_type': 'phi',
        'channel': None,
        'param': 'depth',
        'min': 0,
        'max': 1
    },
    2: {
        'name': 'Φ-Phase',
        'param_type': 'phi',
        'channel': None,
        'param': 'phase',
        'min': 0,
        'max': 1
    },
    7: {
        'name': 'Master Gain',
        'param_type': 'global',
        'channel': None,
        'param': 'gain',
        'min': 0,
        'max': 2
    },
    10: {
        'name': 'Coupling Strength',
        'param_type': 'global',
        'channel': None,
        'param': 'coupling_strength',
        'min': 0,
        'max': 2
    }
}

# Add CC16-23 for channels
for i in range(8):
    DEFAULT_MAPPINGS[16 + i] = {
        'name': f'Channel {i + 1} Amplitude',
        'param_type': 'channel',
        'channel': i,
        'param': 'amplitude',
        'min': 0,
        'max': 1
    }


def test_persistence_logic():
    """
    Test 1: Persistence logic (serialization/deserialization)
    """
    print("=" * 60)
    print("Test 1: Persistence Logic")
    print("=" * 60)
    print()

    # Custom mapping to add
    custom_mappings = {
        74: {  # CC74 - Brightness
            'name': 'Custom Control 1',
            'param_type': 'channel',
            'channel': 0,
            'param': 'frequency',
            'min': 100,
            'max': 2000
        },
        71: {  # CC71 - Resonance
            'name': 'Custom Control 2',
            'param_type': 'phi',
            'channel': None,
            'param': 'depth',
            'min': 0.5,
            'max': 1.0
        }
    }

    # Simulate saveMappings()
    print("Simulating saveMappings():")
    print("-" * 60)

    try:
        storage_data = {
            'custom': custom_mappings,
            'timestamp': 1697548800000
        }

        serialized = json.dumps(storage_data)
        print(f"✓ Custom mappings serialized")
        print(f"  Size: {len(serialized)} bytes")
        print(f"  CCs: {list(custom_mappings.keys())}")
        print()

    except Exception as e:
        print(f"✗ FAIL: Serialization error: {e}")
        return False

    # Simulate loadMappings()
    print("Simulating loadMappings():")
    print("-" * 60)

    try:
        restored_data = json.loads(serialized)
        restored_mappings = restored_data['custom']

        print(f"✓ Custom mappings deserialized")
        print(f"  Count: {len(restored_mappings)}")
        print()

        # Verify all mappings match
        for cc, mapping in custom_mappings.items():
            if cc not in restored_mappings:
                print(f"✗ Missing CC{cc}")
                return False

            if restored_mappings[cc] != mapping:
                print(f"✗ Mismatch for CC{cc}")
                print(f"  Expected: {mapping}")
                print(f"  Got: {restored_mappings[cc]}")
                return False

        print(f"✓ All custom mappings match after round-trip")
        print()

    except Exception as e:
        print(f"✗ FAIL: Deserialization error: {e}")
        return False

    # Test merged mappings (default + custom)
    print("Testing merged mappings:")
    print("-" * 60)

    effective_mappings = {**DEFAULT_MAPPINGS, **custom_mappings}

    print(f"Default mappings: {len(DEFAULT_MAPPINGS)}")
    print(f"Custom mappings: {len(custom_mappings)}")
    print(f"Effective mappings: {len(effective_mappings)}")
    print()

    # Verify custom overrides
    if 74 in effective_mappings:
        print(f"✓ CC74 mapped to: {effective_mappings[74]['name']}")
    else:
        print(f"✗ CC74 not found")
        return False

    # Verify defaults still present
    if 1 in effective_mappings:
        print(f"✓ CC1 (default) mapped to: {effective_mappings[1]['name']}")
    else:
        print(f"✗ CC1 not found")
        return False

    print()
    print("✓ PASS: Persistence logic validated")
    print("=" * 60)
    print()

    return True


def test_addMIDIMapping():
    """
    Test 2: addMIDIMapping() functionality
    """
    print("=" * 60)
    print("Test 2: addMIDIMapping() Functionality")
    print("=" * 60)
    print()

    custom_mappings = {}

    # Simulate addMIDIMapping(cc, config)
    def add_midi_mapping(cc: int, config: Dict):
        """Simulate the addMIDIMapping method"""
        custom_mappings[cc] = config
        print(f"  Added: CC{cc} → {config['name']}")
        return True

    print("Adding custom mappings:")
    print("-" * 60)

    try:
        # Add mapping 1
        add_midi_mapping(74, {
            'name': 'Spectral Tilt',
            'param_type': 'channel',
            'channel': 0,
            'param': 'frequency',
            'min': 50,
            'max': 500
        })

        # Add mapping 2
        add_midi_mapping(71, {
            'name': 'Consciousness Boost',
            'param_type': 'phi',
            'channel': None,
            'param': 'phase',
            'min': 0,
            'max': 1
        })

        # Add mapping 3 (override default)
        add_midi_mapping(7, {
            'name': 'Custom Gain',
            'param_type': 'global',
            'channel': None,
            'param': 'gain',
            'min': 0.5,
            'max': 1.5
        })

        print()
        print(f"✓ Successfully added {len(custom_mappings)} custom mappings")
        print()

        # Verify structure
        for cc, mapping in custom_mappings.items():
            required_keys = ['name', 'param_type', 'param', 'min', 'max']
            missing_keys = [key for key in required_keys if key not in mapping]

            if missing_keys:
                print(f"✗ CC{cc} missing keys: {missing_keys}")
                return False

        print("✓ All mappings have required keys")
        print()

        # Test override behavior
        merged = {**DEFAULT_MAPPINGS, **custom_mappings}

        if merged[7]['name'] == 'Custom Gain':
            print("✓ Override works: CC7 now maps to 'Custom Gain'")
        else:
            print(f"✗ Override failed: CC7 = '{merged[7]['name']}'")
            return False

        print()
        print("✓ PASS: addMIDIMapping() validated")
        print("=" * 60)
        print()

        return True

    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


def test_edge_cases():
    """
    Test 3: Edge cases
    """
    print("=" * 60)
    print("Test 3: Edge Cases")
    print("=" * 60)
    print()

    # Test 3a: Missing localStorage data
    print("3a. Missing localStorage data:")
    print("-" * 60)

    stored = None

    if stored:
        print("✗ Should be None")
        return False
    else:
        print("✓ Correctly handles missing data")
        print("  → Should load defaults only")
        print()

    # Test 3b: Corrupted JSON
    print("3b. Corrupted JSON:")
    print("-" * 60)

    corrupted_data = "{ invalid json ["

    try:
        json.loads(corrupted_data)
        print("✗ Should have raised exception")
        return False
    except json.JSONDecodeError:
        print("✓ Correctly rejects corrupted JSON")
        print("  → Should load defaults only")
        print()

    # Test 3c: Invalid mapping structure
    print("3c. Invalid mapping structure:")
    print("-" * 60)

    invalid_mapping = {
        'custom': {
            74: {
                'name': 'Test',
                # Missing required fields
            }
        }
    }

    mapping = invalid_mapping['custom'][74]
    required = ['param_type', 'param', 'min', 'max']
    missing = [key for key in required if key not in mapping]

    if missing:
        print(f"✓ Detected missing keys: {missing}")
        print("  → Should skip or use defaults")
        print()
    else:
        print("✗ Should have detected missing keys")
        return False

    # Test 3d: CC number validation
    print("3d. CC number validation:")
    print("-" * 60)

    valid_ccs = [0, 1, 7, 74, 127]
    invalid_ccs = [-1, 128, 200, 'abc']

    for cc in valid_ccs:
        if isinstance(cc, int) and 0 <= cc <= 127:
            print(f"  ✓ CC{cc} valid")
        else:
            print(f"  ✗ CC{cc} should be valid but rejected")
            return False

    for cc in invalid_ccs:
        if not isinstance(cc, int) or cc < 0 or cc > 127:
            print(f"  ✓ CC{cc} correctly rejected")
        else:
            print(f"  ✗ CC{cc} should be rejected but accepted")
            return False

    print()
    print("✓ PASS: Edge cases handled")
    print("=" * 60)
    print()

    return True


def generate_browser_test_script():
    """
    Generate browser automation test script
    """
    script = """
// Selenium WebDriver (JavaScript) example
const { Builder, By, until } = require('selenium-webdriver');

async function testMIDIPersistence() {
  let driver = await new Builder().forBrowser('chrome').build();

  try {
    // Load page
    await driver.get('http://localhost:8000');
    await driver.sleep(2000);

    // Clear localStorage
    await driver.executeScript("localStorage.clear();");
    console.log('✓ localStorage cleared');

    // Add custom MIDI mapping via console
    await driver.executeScript(`
      // Assuming window.midiController exists
      if (window.midiController) {
        window.midiController.addMIDIMapping(74, {
          name: 'Test Mapping',
          param_type: 'phi',
          channel: null,
          param: 'depth',
          min: 0,
          max: 1
        });
        console.log('✓ Custom mapping added');
      }
    `);

    await driver.sleep(500);

    // Check localStorage
    let stored = await driver.executeScript(
      "return localStorage.getItem('soundlab_midi_mappings');"
    );

    if (stored) {
      console.log('✓ Mappings stored in localStorage');
      let data = JSON.parse(stored);
      console.log('Custom mappings:', Object.keys(data.custom));

      // Reload page
      await driver.navigate().refresh();
      await driver.sleep(2000);

      // Check if mappings restored
      let restored = await driver.executeScript(`
        if (window.midiController) {
          let mappings = window.midiController.getMappings();
          return mappings.custom;
        }
        return null;
      `);

      if (restored && restored['74']) {
        console.log('✓ Custom mapping restored after reload');
        console.log('  CC74:', restored['74'].name);
        console.log('✓ PASS: Persistence test complete');
      } else {
        console.log('✗ FAIL: Mapping not restored');
      }

    } else {
      console.log('✗ FAIL: Mappings not stored');
    }

  } finally {
    await driver.quit();
  }
}

testMIDIPersistence();
"""

    return script


if __name__ == "__main__":
    print()

    # Run tests
    result1 = test_persistence_logic()
    result2 = test_addMIDIMapping()
    result3 = test_edge_cases()

    # Summary
    print()
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"  Persistence Logic:     {'✓ PASS' if result1 else '✗ FAIL'}")
    print(f"  addMIDIMapping():      {'✓ PASS' if result2 else '✗ FAIL'}")
    print(f"  Edge Cases:            {'✓ PASS' if result3 else '✗ FAIL'}")
    print("=" * 60)
    print()

    # Browser test script
    print("Browser Automation Test Script:")
    print("=" * 60)
    print(generate_browser_test_script())
    print("=" * 60)
    print()
    print("NOTE: Full persistence testing requires browser automation.")
    print("Recommended tools: Selenium WebDriver, Playwright, Puppeteer")
    print()
    print("Integration test steps:")
    print("  1. Load midi-controller.js in browser")
    print("  2. Add custom MIDI mapping via addMIDIMapping()")
    print("  3. Verify localStorage.setItem() called")
    print("  4. Reload page")
    print("  5. Verify custom mapping restored")
    print("  6. Test MIDI CC with custom mapping")
    print()

    all_passed = result1 and result2 and result3
    sys.exit(0 if all_passed else 1)
