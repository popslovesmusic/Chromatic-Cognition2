"""
Smoke Test: Health Endpoints
Feature 019: Release Readiness Validation

Tests health and readiness endpoints.

Success Criteria:
- /healthz returns 200
- /readyz returns 200 when ready
- /version returns version info
- /metrics returns Prometheus metrics
"""

import requests
import time
import os
import sys

# Configuration
SOUNDLAB_URL = os.getenv('SOUNDLAB_URL', 'http://localhost:8000')
TIMEOUT_SECONDS = 10


def test_healthz():
    """Test health check endpoint"""
    print("=" * 70)
    print("Smoke Test: Health Check (/healthz)")
    print("=" * 70)
    print(f"Target: {SOUNDLAB_URL}/healthz")
    print()

    try:
        response = requests.get(
            f"{SOUNDLAB_URL}/healthz",
            timeout=TIMEOUT_SECONDS
        )

        print(f"Status code: {response.status_code}")
        print(f"Response: {response.json()}")
        print()

        if response.status_code != 200:
            print(f"✗ FAIL: Expected 200, got {response.status_code}")
            return False

        data = response.json()
        if data.get('status') != 'healthy':
            print(f"✗ FAIL: Expected status 'healthy', got '{data.get('status')}'")
            return False

        print("✓ PASS: Health check successful")
        return True

    except requests.exceptions.RequestException as e:
        print(f"✗ FAIL: Request error: {e}")
        return False


def test_readyz():
    """Test readiness check endpoint"""
    print("=" * 70)
    print("Smoke Test: Readiness Check (/readyz)")
    print("=" * 70)
    print(f"Target: {SOUNDLAB_URL}/readyz")
    print()

    try:
        response = requests.get(
            f"{SOUNDLAB_URL}/readyz",
            timeout=TIMEOUT_SECONDS
        )

        print(f"Status code: {response.status_code}")
        print(f"Response: {response.json()}")
        print()

        # Accept both 200 (ready) and 503 (not ready) as valid responses
        if response.status_code not in [200, 503]:
            print(f"✗ FAIL: Expected 200 or 503, got {response.status_code}")
            return False

        data = response.json()
        status = data.get('status')

        if response.status_code == 200:
            if status != 'ready':
                print(f"⚠ WARNING: Status is '{status}' but code is 200")

            # Check readiness checks
            checks = data.get('checks', {})
            print(f"Readiness checks: {checks}")

            failing_checks = [k for k, v in checks.items() if not v]
            if failing_checks:
                print(f"⚠ WARNING: Some checks failing: {failing_checks}")

            print("✓ PASS: Readiness check successful (ready)")

        else:  # 503
            print(f"⚠ INFO: Service not ready yet (status: {status})")
            print("✓ PASS: Readiness check endpoint working (not ready)")

        return True

    except requests.exceptions.RequestException as e:
        print(f"✗ FAIL: Request error: {e}")
        return False


def test_version():
    """Test version endpoint"""
    print("=" * 70)
    print("Smoke Test: Version Info (/version)")
    print("=" * 70)
    print(f"Target: {SOUNDLAB_URL}/version")
    print()

    try:
        response = requests.get(
            f"{SOUNDLAB_URL}/version",
            timeout=TIMEOUT_SECONDS
        )

        print(f"Status code: {response.status_code}")
        data = response.json()
        print(f"Response: {data}")
        print()

        if response.status_code != 200:
            print(f"✗ FAIL: Expected 200, got {response.status_code}")
            return False

        # Check for version fields
        expected_fields = ['version']
        missing_fields = [f for f in expected_fields if f not in data]

        if missing_fields:
            print(f"✗ FAIL: Missing fields: {missing_fields}")
            return False

        print(f"Version: {data.get('version')}")
        print(f"Commit: {data.get('commit', 'N/A')}")
        print(f"Build Date: {data.get('build_date', 'N/A')}")
        print()

        print("✓ PASS: Version endpoint successful")
        return True

    except requests.exceptions.RequestException as e:
        print(f"✗ FAIL: Request error: {e}")
        return False


def test_metrics():
    """Test Prometheus metrics endpoint"""
    print("=" * 70)
    print("Smoke Test: Prometheus Metrics (/metrics)")
    print("=" * 70)
    print(f"Target: {SOUNDLAB_URL}/metrics")
    print()

    try:
        response = requests.get(
            f"{SOUNDLAB_URL}/metrics",
            timeout=TIMEOUT_SECONDS
        )

        print(f"Status code: {response.status_code}")
        print()

        if response.status_code != 200:
            print(f"✗ FAIL: Expected 200, got {response.status_code}")
            return False

        # Check content type
        content_type = response.headers.get('Content-Type', '')
        if 'text/plain' not in content_type:
            print(f"⚠ WARNING: Expected text/plain, got {content_type}")

        # Parse metrics
        metrics_text = response.text
        metrics_lines = [line for line in metrics_text.split('\n') if line and not line.startswith('#')]

        print(f"Metrics found: {len(metrics_lines)}")

        # Show sample metrics
        if metrics_lines:
            print("Sample metrics:")
            for line in metrics_lines[:5]:
                print(f"  {line}")
            print()

        # Check for expected metrics
        expected_metrics = ['soundlab_audio_running', 'soundlab_cpu_percent']
        found_metrics = [m for m in expected_metrics if any(m in line for line in metrics_lines)]

        print(f"Expected metrics found: {len(found_metrics)}/{len(expected_metrics)}")
        print()

        if len(found_metrics) < len(expected_metrics):
            missing = set(expected_metrics) - set(found_metrics)
            print(f"⚠ WARNING: Missing metrics: {missing}")

        print("✓ PASS: Metrics endpoint successful")
        return True

    except requests.exceptions.RequestException as e:
        print(f"✗ FAIL: Request error: {e}")
        return False


def test_status_api():
    """Test status API endpoint"""
    print("=" * 70)
    print("Smoke Test: Status API (/api/status)")
    print("=" * 70)
    print(f"Target: {SOUNDLAB_URL}/api/status")
    print()

    try:
        response = requests.get(
            f"{SOUNDLAB_URL}/api/status",
            timeout=TIMEOUT_SECONDS
        )

        print(f"Status code: {response.status_code}")
        data = response.json()
        print(f"Response keys: {list(data.keys())}")
        print()

        if response.status_code != 200:
            print(f"✗ FAIL: Expected 200, got {response.status_code}")
            return False

        # Check for expected fields
        expected_fields = ['audio_running', 'sample_rate', 'buffer_size']
        missing_fields = [f for f in expected_fields if f not in data]

        if missing_fields:
            print(f"⚠ WARNING: Missing fields: {missing_fields}")

        print(f"Audio running: {data.get('audio_running')}")
        print(f"Sample rate: {data.get('sample_rate')}")
        print(f"Buffer size: {data.get('buffer_size')}")
        print()

        print("✓ PASS: Status API successful")
        return True

    except requests.exceptions.RequestException as e:
        print(f"✗ FAIL: Request error: {e}")
        return False


def main():
    """Run all health smoke tests"""
    print()
    print("Running Health Endpoint Smoke Tests...")
    print()

    results = []

    # Test 1: Health check
    result1 = test_healthz()
    results.append(result1)
    print()

    # Test 2: Readiness check
    result2 = test_readyz()
    results.append(result2)
    print()

    # Test 3: Version
    result3 = test_version()
    results.append(result3)
    print()

    # Test 4: Metrics
    result4 = test_metrics()
    results.append(result4)
    print()

    # Test 5: Status API
    result5 = test_status_api()
    results.append(result5)
    print()

    # Summary
    print("=" * 70)
    print("Health Endpoints Smoke Test Summary")
    print("=" * 70)
    passed = sum(results)
    total = len(results)

    print(f"Passed: {passed}/{total}")
    print()

    if all(results):
        print("✓ ALL HEALTH ENDPOINT SMOKE TESTS PASSED")
        sys.exit(0)
    else:
        print("✗ SOME HEALTH ENDPOINT SMOKE TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
