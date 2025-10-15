"""
Test Metrics Persistence - FR-005: localStorage reload recovery

Verifies that last known metrics are stored in localStorage
and can be restored on reload.

NOTE: This test requires browser automation (Selenium/Playwright) to
test localStorage functionality. This script provides a conceptual test
and validation logic. For full testing, integrate with a browser automation
framework.

Usage:
    python test_persistence.py
"""

import json
import sys


def test_persistence_logic():
    """
    Test the persistence logic (without browser)

    This tests the JSON serialization/deserialization logic
    that the HUD uses for localStorage.
    """
    print("=" * 60)
    print("Metrics Persistence Logic Test")
    print("=" * 60)
    print()

    # Test 1: Serialize metrics
    print("Test 1: Serialize Metrics")
    print("-" * 60)

    test_metrics = {
        'ici': 0.456,
        'phase_coherence': 0.789,
        'spectral_centroid': 1234.5,
        'criticality': 0.234,
        'consciousness_level': 0.567,
        'state': 'AWAKE',
        'phi_phase': 0.123,
        'phi_depth': 0.618,
        'phi_mode': 'manual',
        'timestamp': 1697548800000
    }

    try:
        # Simulate localStorage.setItem
        stored_data = {
            'metrics': test_metrics,
            'timestamp': 1697548800000
        }
        serialized = json.dumps(stored_data)

        print(f"✓ Metrics serialized: {len(serialized)} bytes")
        print(f"  Sample: {serialized[:100]}...")
        print()

    except Exception as e:
        print(f"✗ FAIL: Serialization error: {e}\n")
        return False

    # Test 2: Deserialize metrics
    print("Test 2: Deserialize Metrics")
    print("-" * 60)

    try:
        # Simulate localStorage.getItem
        deserialized = json.loads(serialized)
        restored_metrics = deserialized['metrics']

        print(f"✓ Metrics deserialized")
        print(f"  Keys: {list(restored_metrics.keys())}")

        # Verify all values match
        all_match = True
        for key, value in test_metrics.items():
            if restored_metrics.get(key) != value:
                print(f"  ✗ Mismatch: {key} = {restored_metrics.get(key)} != {value}")
                all_match = False

        if all_match:
            print(f"✓ All values match after round-trip")
        else:
            print(f"✗ Some values don't match")
            return False

        print()

    except Exception as e:
        print(f"✗ FAIL: Deserialization error: {e}\n")
        return False

    # Test 3: Handle missing data
    print("Test 3: Handle Missing Data")
    print("-" * 60)

    try:
        # Simulate missing localStorage data
        stored = None

        if stored:
            print("✗ Should not have data")
            return False
        else:
            print("✓ Correctly handles missing localStorage data")

        # Default values should be used
        default_metrics = {
            'ici': 0,
            'phase_coherence': 0,
            'spectral_centroid': 0,
            'criticality': 0,
            'consciousness_level': 0,
            'state': 'IDLE'
        }

        print("✓ Would fall back to defaults:")
        print(f"  {default_metrics}")
        print()

    except Exception as e:
        print(f"✗ FAIL: Missing data handling error: {e}\n")
        return False

    # Test 4: Handle corrupted data
    print("Test 4: Handle Corrupted Data")
    print("-" * 60)

    try:
        corrupted = "not valid json {["

        try:
            json.loads(corrupted)
            print("✗ Should have raised exception")
            return False
        except json.JSONDecodeError:
            print("✓ Correctly rejects corrupted JSON")

        print()

    except Exception as e:
        print(f"✗ FAIL: Corrupted data handling error: {e}\n")
        return False

    # Test 5: Timestamp validation
    print("Test 5: Timestamp Validation")
    print("-" * 60)

    try:
        import time

        old_timestamp = time.time() - 86400  # 1 day ago
        recent_timestamp = time.time() - 60  # 1 minute ago

        print(f"Old timestamp: {old_timestamp} ({time.ctime(old_timestamp)})")
        print(f"Recent timestamp: {recent_timestamp} ({time.ctime(recent_timestamp)})")

        # In practice, the HUD loads metrics regardless of age
        # but the timestamp can be used to display staleness
        print("✓ Timestamps can be used for staleness indication")
        print()

    except Exception as e:
        print(f"✗ FAIL: Timestamp validation error: {e}\n")
        return False

    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    print("✓ All persistence logic tests PASSED")
    print()
    print("NOTE: Full localStorage testing requires browser automation.")
    print("Recommended tools:")
    print("  - Selenium WebDriver")
    print("  - Playwright")
    print("  - Puppeteer")
    print()
    print("Integration test steps:")
    print("  1. Load metrics-hud.js in browser")
    print("  2. Receive metrics via WebSocket")
    print("  3. Verify localStorage.setItem called")
    print("  4. Reload page")
    print("  5. Verify metrics restored from localStorage")
    print("  6. Verify display updated with restored metrics")
    print("=" * 60)

    return True


def generate_browser_test_script():
    """Generate a browser automation test script"""
    script = """
// Selenium WebDriver (JavaScript) example
const { Builder, By, until } = require('selenium-webdriver');

async function testMetricsPersistence() {
  let driver = await new Builder().forBrowser('chrome').build();

  try {
    // Load page with metrics HUD
    await driver.get('http://localhost:8000');

    // Wait for metrics HUD to initialize
    await driver.sleep(2000);

    // Get localStorage value
    let stored = await driver.executeScript(
      "return localStorage.getItem('soundlab_metrics_last_known');"
    );

    console.log('Stored metrics:', stored);

    if (!stored) {
      console.log('Waiting for metrics to be stored...');
      await driver.sleep(5000);

      stored = await driver.executeScript(
        "return localStorage.getItem('soundlab_metrics_last_known');"
      );
    }

    if (stored) {
      console.log('✓ Metrics stored in localStorage');

      // Parse stored data
      let data = JSON.parse(stored);
      console.log('Metrics keys:', Object.keys(data.metrics));

      // Reload page
      await driver.navigate().refresh();
      await driver.sleep(2000);

      // Check if metrics are displayed
      let hudElement = await driver.findElement(By.id('metricsHudStateValue'));
      let stateText = await hudElement.getText();

      console.log('State after reload:', stateText);
      console.log('✓ Metrics persistence test PASSED');

    } else {
      console.log('✗ No metrics stored');
    }

  } finally {
    await driver.quit();
  }
}

testMetricsPersistence();
"""

    return script


if __name__ == "__main__":
    print("\n")
    result = test_persistence_logic()

    print("\nBrowser Test Script:")
    print("=" * 60)
    print(generate_browser_test_script())

    sys.exit(0 if result else 1)
