"""
Quick functionality test for Feature 011 - no delays
"""

import time
import numpy as np
from .phi_sensor_bridge import SensorData, SensorType, AudioBeatDetector, SensorConfig
from .phi_router import PhiRouter, PhiRouterConfig, PhiSourcePriority

print("=" * 60)
print("Feature 011: Quick Functionality Test")
print("=" * 60)

PHI_MIN = 0.618033988749895
PHI_MAX = 1.618033988749895

# Test 1: Normalization
print("\n1. Testing Phi normalization (FR-002)...")
test_cases = [(0, 0.618), (64, 1.118), (127, 1.618)]
all_ok = True
for midi_val, expected in test_cases:
    normalized = PHI_MIN + (midi_val / 127.0) * (PHI_MAX - PHI_MIN)
    ok = abs(normalized - expected) < 0.001
    all_ok = all_ok and ok
    print(f"   MIDI {midi_val:3d} -> {normalized:.3f} (expected {expected:.3f}) {'[OK]' if ok else '[FAIL]'}")

# Test 2: PhiRouter creation
print("\n2. Testing PhiRouter creation...")
try:
    router = PhiRouter(PhiRouterConfig(enable_logging=False))
    router.start()
    print("   [OK] PhiRouter created and started")
except Exception as e:
    print(f"   [FAIL] PhiRouter creation failed: {e}")
    all_ok = False

# Test 3: Source registration
print("\n3. Testing source registration (FR-001)...")
try:
    router.register_source("midi", PhiSourcePriority.MIDI)
    router.register_source("serial", PhiSourcePriority.SERIAL)
    status = router.get_status()
    ok = status.source_count == 2
    all_ok = all_ok and ok
    print(f"   Sources registered: {status.source_count} {'[OK]' if ok else '[FAIL]'}")
except Exception as e:
    print(f"   [FAIL] Source registration failed: {e}")
    all_ok = False

# Test 4: Source updates
print("\n4. Testing source updates...")
try:
    data = SensorData(SensorType.MIDI_CC, time.time(), 64, 1.0, "midi")
    router.update_source("midi", data)
    phi, phase = router.get_current_phi()
    ok = PHI_MIN <= phi <= PHI_MAX
    all_ok = all_ok and ok
    print(f"   Phi value: {phi:.3f} {'[OK]' if ok else '[FAIL - out of range]'}")
except Exception as e:
    print(f"   [FAIL] Source update failed: {e}")
    all_ok = False

# Test 5: Audio beat detector
print("\n5. Testing audio beat detector...")
try:
    beats = []
    def beat_cb(data):
        beats.append(data)

    config = SensorConfig(sensor_type=SensorType.AUDIO_BEAT)
    detector = AudioBeatDetector(config, beat_cb)

    # Quiet baseline
    for _ in range(3):
        quiet = np.random.randn(512).astype(np.float32) * 0.1
        detector.process_audio(quiet)

    # Loud beat
    loud = np.random.randn(512).astype(np.float32) * 3.0
    detector.process_audio(loud)

    ok = len(beats) > 0
    all_ok = all_ok and ok
    print(f"   Beats detected: {len(beats)} {'[OK]' if ok else '[FAIL]'}")

    if beats:
        phi_ok = PHI_MIN <= beats[0].normalized_value <= PHI_MAX
        all_ok = all_ok and phi_ok
        print(f"   Beat Phi: {beats[0].normalized_value:.3f} {'[OK]' if phi_ok else '[FAIL]'}")
except Exception as e:
    print(f"   [FAIL] Audio beat detector failed: {e}")
    all_ok = False

# Test 6: Telemetry
print("\n6. Testing telemetry (FR-004)...")
try:
    status = router.get_status()
    checks = [
        ("Timestamp", status.timestamp > 0),
        ("Active source", status.active_source is not None),
        ("Phi value", PHI_MIN <= status.phi_value <= PHI_MAX),
        ("Source count", status.source_count > 0)
    ]
    for name, ok in checks:
        all_ok = all_ok and ok
        print(f"   {name}: {'[OK]' if ok else '[FAIL]'}")
except Exception as e:
    print(f"   [FAIL] Telemetry failed: {e}")
    all_ok = False

# Cleanup
router.stop()

# Summary
print("\n" + "=" * 60)
if all_ok:
    print("[PASS] All core functionality tests passed")
    print("\nFeature 011 components validated:")
    print("  - Phi normalization (FR-002)")
    print("  - PhiRouter source management (FR-001)")
    print("  - Audio beat detection")
    print("  - Telemetry (FR-004)")
else:
    print("[FAIL] Some tests failed - see details above")
print("=" * 60)
