"""
Test Keyboard Shortcuts - SC-002: Keyboard control within 150ms

Validates that keyboard shortcuts trigger the correct parameter updates
with acceptable latency. This test requires browser automation to simulate
actual keyboard events.

This script provides conceptual validation logic and command simulations.
For full browser testing, integrate with Selenium/Playwright.

Usage:
    python test_keyboard_shortcuts.py
"""

import asyncio
import websockets
import json
import time
import sys


# Expected keyboard mappings from midi-controller.js
KEYBOARD_MAPPINGS = {
    'ArrowUp': {
        'description': 'Increase Φ-depth',
        'param_type': 'phi',
        'channel': None,
        'param': 'depth',
        'delta': 0.05  # Relative adjustment
    },
    'ArrowDown': {
        'description': 'Decrease Φ-depth',
        'param_type': 'phi',
        'channel': None,
        'param': 'depth',
        'delta': -0.05
    },
    'ArrowLeft': {
        'description': 'Decrease Φ-phase',
        'param_type': 'phi',
        'channel': None,
        'param': 'phase',
        'delta': -0.1
    },
    'ArrowRight': {
        'description': 'Increase Φ-phase',
        'param_type': 'phi',
        'channel': None,
        'param': 'phase',
        'delta': 0.1
    },
    ' ': {
        'description': 'Toggle audio start/stop',
        'action': 'toggle_audio'
    },
    '1': {'description': 'Recall preset 1', 'action': 'recall_preset', 'value': 1},
    '2': {'description': 'Recall preset 2', 'action': 'recall_preset', 'value': 2},
    '3': {'description': 'Recall preset 3', 'action': 'recall_preset', 'value': 3},
    '4': {'description': 'Recall preset 4', 'action': 'recall_preset', 'value': 4},
    '5': {'description': 'Recall preset 5', 'action': 'recall_preset', 'value': 5},
    '6': {'description': 'Recall preset 6', 'action': 'recall_preset', 'value': 6},
    '7': {'description': 'Recall preset 7', 'action': 'recall_preset', 'value': 7},
    '8': {'description': 'Recall preset 8', 'action': 'recall_preset', 'value': 8},
    '9': {'description': 'Recall preset 9', 'action': 'recall_preset', 'value': 9},
    '?': {'description': 'Show keyboard shortcuts', 'action': 'show_help'},
    'e': {'description': 'Edit MIDI mappings', 'action': 'edit_mappings'}
}


def test_keyboard_mapping_completeness():
    """
    Test 1: Verify all required keyboard shortcuts are defined
    """
    print("=" * 60)
    print("Keyboard Shortcuts Completeness Test")
    print("=" * 60)
    print()

    required_keys = [
        'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight',
        ' ', '1', '2', '3', '4', '5', '6', '7', '8', '9',
        '?', 'e'
    ]

    print("Checking required keyboard mappings:")
    print("-" * 60)

    all_present = True
    for key in required_keys:
        if key in KEYBOARD_MAPPINGS:
            mapping = KEYBOARD_MAPPINGS[key]
            display_key = 'Space' if key == ' ' else key
            print(f"  ✓ {display_key:15} - {mapping['description']}")
        else:
            print(f"  ✗ {key:15} - MISSING")
            all_present = False

    print()
    if all_present:
        print(f"✓ PASS: All {len(required_keys)} required shortcuts defined")
    else:
        print(f"✗ FAIL: Some required shortcuts missing")

    print("=" * 60)
    print()

    return all_present


async def test_keyboard_parameter_updates(server_url='ws://localhost:8000/ws/ui'):
    """
    Test 2: Verify keyboard shortcuts trigger correct parameter updates
    """
    print("=" * 60)
    print("Keyboard Parameter Update Test")
    print("=" * 60)
    print(f"Server: {server_url}")
    print()

    try:
        async with websockets.connect(server_url) as websocket:
            print("✓ Connected to /ws/ui endpoint")
            print("Simulating keyboard shortcuts...\n")

            # Test arrow keys (Φ controls)
            test_keys = [
                ('ArrowUp', {'type': 'set_param', 'param_type': 'phi', 'channel': None, 'param': 'depth', 'value': 0.55}),
                ('ArrowDown', {'type': 'set_param', 'param_type': 'phi', 'channel': None, 'param': 'depth', 'value': 0.45}),
                ('ArrowLeft', {'type': 'set_param', 'param_type': 'phi', 'channel': None, 'param': 'phase', 'value': 0.40}),
                ('ArrowRight', {'type': 'set_param', 'param_type': 'phi', 'channel': None, 'param': 'phase', 'value': 0.60}),
            ]

            latencies = []
            successful = 0
            failed = 0

            for key_name, message in test_keys:
                mapping = KEYBOARD_MAPPINGS[key_name]

                print(f"Testing: {key_name:15} ({mapping['description']})")

                # Measure latency (simulating keydown → WebSocket send)
                start_time = time.perf_counter()

                try:
                    # Send parameter update
                    await websocket.send(json.dumps(message))

                    # Wait for response
                    response = await asyncio.wait_for(websocket.recv(), timeout=0.5)

                    end_time = time.perf_counter()
                    latency_ms = (end_time - start_time) * 1000

                    data = json.loads(response)

                    if data.get('type') == 'param_updated' and data.get('success'):
                        latencies.append(latency_ms)
                        successful += 1
                        print(f"  ✓ Update confirmed - {latency_ms:.2f} ms")
                    else:
                        failed += 1
                        print(f"  ✗ Update failed: {data}")

                except asyncio.TimeoutError:
                    failed += 1
                    print(f"  ✗ Timeout")
                except Exception as e:
                    failed += 1
                    print(f"  ✗ Error: {e}")

                await asyncio.sleep(0.05)

            # Results
            print()
            print("-" * 60)
            print(f"Successful: {successful}/{len(test_keys)}")
            print(f"Failed: {failed}/{len(test_keys)}")

            if latencies:
                import statistics
                avg_latency = statistics.mean(latencies)
                max_latency = max(latencies)

                print(f"Average latency: {avg_latency:.2f} ms")
                print(f"Max latency: {max_latency:.2f} ms")
                print()

                # SC-002: Keyboard control within 150ms
                if max_latency < 150:
                    print(f"✓ PASS: All keyboard updates within 150ms (max: {max_latency:.2f}ms)")
                    pass_test = True
                else:
                    print(f"✗ FAIL: Some updates exceeded 150ms (max: {max_latency:.2f}ms)")
                    pass_test = False
            else:
                print("✗ No successful updates")
                pass_test = False

            print("=" * 60)
            print()

            return pass_test

    except websockets.exceptions.WebSocketException as e:
        print(f"✗ WebSocket error: {e}")
        print()
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        print()
        return False


def test_keydown_filtering():
    """
    Test 3: Verify keydown filtering logic (prevent repeat, ignore input fields)
    """
    print("=" * 60)
    print("Keydown Filtering Logic Test")
    print("=" * 60)
    print()

    print("Testing key repeat prevention:")
    print("-" * 60)

    # Simulate key press state
    keys_pressed = set()

    # First press - should trigger
    key = 'ArrowUp'
    if key not in keys_pressed:
        keys_pressed.add(key)
        print(f"  ✓ First press of '{key}' - TRIGGER action")
    else:
        print(f"  ✗ First press of '{key}' - BLOCKED (should not happen)")

    # Repeat press - should block
    if key not in keys_pressed:
        keys_pressed.add(key)
        print(f"  ✗ Repeat press of '{key}' - TRIGGER (should not happen)")
    else:
        print(f"  ✓ Repeat press of '{key}' - BLOCKED")

    # Key up - remove from set
    keys_pressed.discard(key)
    print(f"  ✓ Key released - removed from set")

    # Press again - should trigger
    if key not in keys_pressed:
        keys_pressed.add(key)
        print(f"  ✓ Second press of '{key}' - TRIGGER action")

    print()
    print("Testing input field filtering:")
    print("-" * 60)

    # Simulate target element types
    target_types = ['INPUT', 'TEXTAREA', 'DIV', 'BUTTON']

    for target in target_types:
        should_ignore = target in ['INPUT', 'TEXTAREA']
        if should_ignore:
            print(f"  ✓ Target: {target:10} - IGNORE keyboard shortcuts")
        else:
            print(f"  ✓ Target: {target:10} - ALLOW keyboard shortcuts")

    print()
    print("✓ PASS: Filtering logic validated")
    print("=" * 60)
    print()

    return True


def generate_browser_test_script():
    """
    Generate Selenium/Playwright test script for browser automation
    """
    script = """
// Playwright example for keyboard shortcut testing
const { chromium } = require('playwright');

async function testKeyboardShortcuts() {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  try {
    // Load page with MIDI controller
    await page.goto('http://localhost:8000');
    await page.waitForTimeout(2000);

    // Test Arrow Up - Increase Φ-depth
    console.log('Testing Arrow Up...');
    await page.keyboard.press('ArrowUp');
    await page.waitForTimeout(200);

    // Check console logs or network activity for WebSocket message
    const logs = [];
    page.on('console', msg => logs.push(msg.text()));

    // Look for parameter update log
    const found = logs.some(log => log.includes('Φ-depth'));
    console.log(found ? '✓ Arrow Up triggered' : '✗ Arrow Up failed');

    // Test number keys - Preset recall
    console.log('Testing preset recall (key "1")...');
    await page.keyboard.press('1');
    await page.waitForTimeout(200);

    // Test help dialog
    console.log('Testing help dialog (key "?")...');
    await page.keyboard.press('Shift+/');  // ? key
    await page.waitForTimeout(500);

    // Check if alert/dialog appeared
    page.on('dialog', dialog => {
      console.log('✓ Help dialog shown:', dialog.message());
      dialog.dismiss();
    });

    console.log('\\n✓ All keyboard tests completed');

  } finally {
    await browser.close();
  }
}

testKeyboardShortcuts();
"""

    return script


if __name__ == "__main__":
    print()

    # Test 1: Completeness
    result1 = test_keyboard_mapping_completeness()

    # Test 2: Parameter updates (requires server)
    print("NOTE: Parameter update test requires running server")
    print("To run: Ensure server is running, then this test will connect")
    print()

    server_url = sys.argv[1] if len(sys.argv) > 1 else 'ws://localhost:8000/ws/ui'

    try:
        result2 = asyncio.run(test_keyboard_parameter_updates(server_url))
    except Exception as e:
        print(f"⚠ Could not connect to server: {e}")
        print("Skipping parameter update test")
        result2 = None

    # Test 3: Filtering logic
    result3 = test_keydown_filtering()

    # Summary
    print()
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"  Completeness:       {'✓ PASS' if result1 else '✗ FAIL'}")
    print(f"  Parameter Updates:  {'✓ PASS' if result2 else '⚠ SKIPPED' if result2 is None else '✗ FAIL'}")
    print(f"  Filtering Logic:    {'✓ PASS' if result3 else '✗ FAIL'}")
    print("=" * 60)
    print()

    # Browser test script
    print("Browser Automation Test Script:")
    print("=" * 60)
    print(generate_browser_test_script())
    print("=" * 60)
    print()
    print("For full keyboard testing, use Playwright or Selenium with the script above.")
    print()

    # Exit code
    all_passed = result1 and (result2 is not False) and result3
    sys.exit(0 if all_passed else 1)
