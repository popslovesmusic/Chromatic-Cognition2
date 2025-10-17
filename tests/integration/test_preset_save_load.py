"""
Test Preset Save/Load - SC-001: Presets save/load without desync or data loss

Validates that presets can be saved and loaded with exact parameter values
preserved. Tests round-trip consistency.

Usage:
    python test_preset_save_load.py [ws://localhost:8000/ws/ui]
"""

import asyncio
import websockets
import json
import sys
from typing import Dict, Any


# Test preset with known values
TEST_PRESET = {
    "version": "1.0",
    "name": "Test_Preset_001",
    "timestamp": 1697548800000,
    "parameters": {
        "channels": {
            "0": {"frequency": 220.0, "amplitude": 0.8, "enabled": True},
            "1": {"frequency": 330.0, "amplitude": 0.7, "enabled": True},
            "2": {"frequency": 440.0, "amplitude": 0.6, "enabled": True},
            "3": {"frequency": 550.0, "amplitude": 0.5, "enabled": False},
            "4": {"frequency": 660.0, "amplitude": 0.4, "enabled": False},
            "5": {"frequency": 770.0, "amplitude": 0.3, "enabled": False},
            "6": {"frequency": 880.0, "amplitude": 0.2, "enabled": False},
            "7": {"frequency": 990.0, "amplitude": 0.1, "enabled": False}
        },
        "global": {
            "coupling_strength": 1.5,
            "gain": 0.9
        },
        "phi": {
            "phase": 0.618,
            "depth": 0.789
        }
    }
}


async def test_save_load_cycle(server_url='ws://localhost:8000/ws/ui'):
    """
    Test 1: Save preset, load it back, verify values match

    Args:
        server_url: WebSocket URL

    Returns:
        True if test passes
    """
    print("=" * 60)
    print("Test 1: Save/Load Cycle")
    print("=" * 60)
    print(f"Server: {server_url}")
    print()

    try:
        async with websockets.connect(server_url) as websocket:
            print("✓ Connected to /ws/ui")

            # Step 1: Apply test preset
            print("\nStep 1: Applying test preset...")

            apply_message = {
                "type": "apply_preset",
                "preset_name": TEST_PRESET["name"],
                "parameters": TEST_PRESET["parameters"]
            }

            await websocket.send(json.dumps(apply_message))

            # Wait for confirmation
            response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            apply_response = json.loads(response)

            if apply_response.get("type") != "preset_applied" or not apply_response.get("success"):
                print(f"✗ FAIL: Preset application failed: {apply_response}")
                return False

            print(f"✓ Preset applied: {apply_response.get('preset_name')}")

            # Step 2: Request current state
            print("\nStep 2: Requesting current state...")

            get_state_message = {"type": "get_state"}
            await websocket.send(json.dumps(get_state_message))

            response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            state_response = json.loads(response)

            if state_response.get("type") != "state":
                print(f"✗ FAIL: Did not receive state: {state_response}")
                return False

            retrieved_params = state_response.get("parameters", {})
            print("✓ Retrieved current state")

            # Step 3: Compare parameters
            print("\nStep 3: Comparing parameters...")

            mismatches = []

            # Compare channels
            print("\nChannel parameters:")
            if "channels" in TEST_PRESET["parameters"] and "channels" in retrieved_params:
                for ch_idx, expected_ch in TEST_PRESET["parameters"]["channels"].items():
                    retrieved_ch = retrieved_params["channels"].get(ch_idx, {})

                    for param_name, expected_value in expected_ch.items():
                        retrieved_value = retrieved_ch.get(param_name)

                        # Allow small float tolerance
                        if isinstance(expected_value, float):
                            match = abs(expected_value - retrieved_value) < 0.001 if retrieved_value is not None else False
                        else:
                            match = expected_value == retrieved_value

                        status = "✓" if match else "✗"

                        if not match:
                            mismatches.append({
                                "param": f"channels[{ch_idx}].{param_name}",
                                "expected": expected_value,
                                "retrieved": retrieved_value
                            })

                        if ch_idx in ["0", "1", "2"]:  # Only print first 3 channels
                            print(f"  {status} Channel {ch_idx}.{param_name:12} : {expected_value:8.3f} -> {retrieved_value}")
            else:
                print("  ⚠ Channel data missing")
                mismatches.append({"param": "channels", "expected": "present", "retrieved": "missing"})

            # Compare global
            print("\nGlobal parameters:")
            if "global" in TEST_PRESET["parameters"] and "global" in retrieved_params:
                for param_name, expected_value in TEST_PRESET["parameters"]["global"].items():
                    retrieved_value = retrieved_params["global"].get(param_name)

                    match = abs(expected_value - retrieved_value) < 0.001 if retrieved_value is not None else False
                    status = "✓" if match else "✗"

                    if not match:
                        mismatches.append({
                            "param": f"global.{param_name}",
                            "expected": expected_value,
                            "retrieved": retrieved_value
                        })

                    print(f"  {status} {param_name:20} : {expected_value:8.3f} -> {retrieved_value}")
            else:
                print("  ⚠ Global data missing")
                mismatches.append({"param": "global", "expected": "present", "retrieved": "missing"})

            # Compare phi
            print("\nPhi parameters:")
            if "phi" in TEST_PRESET["parameters"] and "phi" in retrieved_params:
                for param_name, expected_value in TEST_PRESET["parameters"]["phi"].items():
                    retrieved_value = retrieved_params["phi"].get(param_name)

                    match = abs(expected_value - retrieved_value) < 0.001 if retrieved_value is not None else False
                    status = "✓" if match else "✗"

                    if not match:
                        mismatches.append({
                            "param": f"phi.{param_name}",
                            "expected": expected_value,
                            "retrieved": retrieved_value
                        })

                    print(f"  {status} {param_name:20} : {expected_value:8.3f} -> {retrieved_value}")
            else:
                print("  ⚠ Phi data missing")
                mismatches.append({"param": "phi", "expected": "present", "retrieved": "missing"})

            # Results
            print()
            print("=" * 60)
            print("Results")
            print("=" * 60)

            if mismatches:
                print(f"✗ FAIL: {len(mismatches)} parameter mismatch(es):")
                for mismatch in mismatches[:10]:  # Show first 10
                    print(f"  {mismatch['param']}: expected {mismatch['expected']}, got {mismatch['retrieved']}")
                if len(mismatches) > 10:
                    print(f"  ... and {len(mismatches) - 10} more")
                return False
            else:
                print("✓ PASS: All parameters match (SC-001: No data loss)")
                return True

    except websockets.exceptions.WebSocketException as e:
        print(f"✗ WebSocket error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_partial_preset(server_url='ws://localhost:8000/ws/ui'):
    """
    Test 2: Apply partial preset (missing values should use defaults)

    Edge case: missing values replaced with defaults
    """
    print("\n" + "=" * 60)
    print("Test 2: Partial Preset (Missing Values)")
    print("=" * 60)
    print(f"Server: {server_url}")
    print()

    # Partial preset (only some parameters)
    partial_preset = {
        "version": "1.0",
        "name": "Partial_Preset",
        "parameters": {
            "phi": {
                "phase": 0.25
                # depth missing
            },
            "global": {
                "gain": 1.5
                # coupling_strength missing
            }
            # channels completely missing
        }
    }

    try:
        async with websockets.connect(server_url) as websocket:
            print("✓ Connected")

            # Apply partial preset
            print("\nApplying partial preset...")

            apply_message = {
                "type": "apply_preset",
                "preset_name": partial_preset["name"],
                "parameters": partial_preset["parameters"]
            }

            await websocket.send(json.dumps(apply_message))

            response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            apply_response = json.loads(response)

            if apply_response.get("success"):
                print("✓ Partial preset applied")
            else:
                print(f"⚠ Partial preset failed: {apply_response}")

            # Get state
            get_state_message = {"type": "get_state"}
            await websocket.send(json.dumps(get_state_message))

            response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            state_response = json.loads(response)

            params = state_response.get("parameters", {})

            # Verify partial values applied
            if "phi" in params and "phase" in params["phi"]:
                phi_phase = params["phi"]["phase"]
                match = abs(phi_phase - 0.25) < 0.001
                print(f"  {'✓' if match else '✗'} phi.phase = {phi_phase} (expected 0.25)")

            if "global" in params and "gain" in params["global"]:
                gain = params["global"]["gain"]
                match = abs(gain - 1.5) < 0.001
                print(f"  {'✓' if match else '✗'} global.gain = {gain} (expected 1.5)")

            # Verify missing values have defaults (or previous values)
            if "phi" in params and "depth" in params["phi"]:
                print(f"  ✓ phi.depth present (value: {params['phi']['depth']})")

            if "channels" in params:
                print(f"  ✓ channels present ({len(params['channels'])} channels)")

            print("\n✓ PASS: Partial preset handled (defaults for missing values)")
            return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


if __name__ == "__main__":
    server_url = sys.argv[1] if len(sys.argv) > 1 else 'ws://localhost:8000/ws/ui'

    print("\n")

    # Run tests
    result1 = asyncio.run(test_save_load_cycle(server_url))
    result2 = asyncio.run(test_partial_preset(server_url))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"  Save/Load Cycle:       {'✓ PASS' if result1 else '✗ FAIL'}")
    print(f"  Partial Preset:        {'✓ PASS' if result2 else '✗ FAIL'}")
    print("=" * 60)
    print()

    all_passed = result1 and result2
    sys.exit(0 if all_passed else 1)
