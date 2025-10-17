"""
Integration Tests for API Endpoints
Feature 021: Automated Validation & Regression Testing

Tests that require the server to be running - can use simulation mode.
"""

import pytest
import server.requests
import time
import os


# Check if running in simulation mode
SIMULATE = os.getenv('SOUNDLAB_SIMULATE', '0') == '1'
BASE_URL = os.getenv('SOUNDLAB_URL', 'http://localhost:8000')


@pytest.mark.integration
class TestHealthEndpoints:
    """Test health check endpoints"""

    def test_healthz_endpoint(self):
        """Test liveness check"""
        response = requests.get(f"{BASE_URL}/healthz", timeout=5)
        assert response.status_code == 200

        data = response.json()
        assert data['status'] == 'healthy'
        assert 'service' in data
        assert 'version' in data

    def test_readyz_endpoint(self):
        """Test readiness check"""
        response = requests.get(f"{BASE_URL}/readyz", timeout=5)
        assert response.status_code in [200, 503]  # May not be ready yet

        data = response.json()
        assert 'status' in data
        assert 'checks' in data

    def test_metrics_endpoint(self):
        """Test Prometheus metrics endpoint"""
        response = requests.get(f"{BASE_URL}/metrics", timeout=5)
        assert response.status_code == 200
        assert response.headers['content-type'] == 'text/plain; charset=utf-8'

        metrics_text = response.text
        # Check for expected metrics
        assert 'soundlab_audio_running' in metrics_text or SIMULATE
        assert 'soundlab_cpu_percent' in metrics_text

    def test_version_endpoint(self):
        """Test version information endpoint"""
        response = requests.get(f"{BASE_URL}/version", timeout=5)
        assert response.status_code == 200

        data = response.json()
        assert 'version' in data


@pytest.mark.integration
class TestStatusEndpoints:
    """Test status and state endpoints"""

    def test_api_status(self):
        """Test /api/status endpoint"""
        response = requests.get(f"{BASE_URL}/api/status", timeout=5)
        assert response.status_code == 200

        data = response.json()
        # Check for expected fields
        assert isinstance(data, dict)

    def test_dashboard_state(self):
        """Test dashboard state endpoint"""
        response = requests.get(f"{BASE_URL}/api/dashboard/state", timeout=5)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, dict)
        # State should include phi_depth and phi_phase
        if 'phi_depth' in data:
            assert isinstance(data['phi_depth'], (int, float))
        if 'phi_phase' in data:
            assert isinstance(data['phi_phase'], (int, float))


@pytest.mark.integration
@pytest.mark.slow
class TestWebSocketConnection:
    """Test WebSocket connectivity"""

    def test_websocket_endpoint_exists(self):
        """Test that WebSocket upgrade endpoint exists"""
        # HTTP request to WS endpoint should return 426 Upgrade Required
        # or similar error, not 404
        try:
            response = requests.get(f"{BASE_URL}/ws/metrics", timeout=2)
            # Should get 426, 400, or 403 (not 404)
            assert response.status_code != 404
        except requests.exceptions.ConnectionError:
            # WebSocket endpoints may not respond to HTTP GET
            pytest.skip("WebSocket endpoint requires WebSocket client")


@pytest.mark.integration
class TestAPIValidation:
    """Test API input validation"""

    def test_invalid_endpoint_404(self):
        """Test that invalid endpoints return 404"""
        response = requests.get(f"{BASE_URL}/api/nonexistent", timeout=5)
        assert response.status_code == 404

    def test_cors_headers(self):
        """Test CORS headers if enabled"""
        response = requests.options(f"{BASE_URL}/api/status", timeout=5)
        # Should return 200 or 405 (method not allowed), but not crash
        assert response.status_code in [200, 405]


@pytest.mark.integration
@pytest.mark.skipif(not SIMULATE, reason="Requires simulation mode or server restart")
class TestSimulationMode:
    """Test simulation mode functionality"""

    def test_simulation_mode_active(self):
        """Test that simulation mode is active when SOUNDLAB_SIMULATE=1"""
        if SIMULATE:
            # In simulation mode, server should still respond
            response = requests.get(f"{BASE_URL}/healthz", timeout=5)
            assert response.status_code == 200


# Fixture for server availability
@pytest.fixture(scope="module", autouse=True)
def check_server_available():
    """Check if server is available before running tests"""
    max_retries = 10
    retry_delay = 1

    for attempt in range(max_retries):
        try:
            response = requests.get(f"{BASE_URL}/healthz", timeout=2)
            if response.status_code == 200:
                print(f"\nServer is available at {BASE_URL}")
                return
        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)

    pytest.skip(f"Server not available at {BASE_URL}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-m', 'integration'])
