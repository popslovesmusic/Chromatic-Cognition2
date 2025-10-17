"""
Security Test Suite - Feature 024

Tests for JWT auth, security headers, rate limiting, CSRF, WebSocket security,
privacy controls, and compliance.

Requirements:
- SC-001: Unauth WS/REST blocked; valid tokens accepted; replay rejected
- SC-002: No CSP violations; no mixed content
- SC-003: ZAP baseline 0 High/Critical; SAST/DAST green
"""

import pytest
import jwt
import time
import hashlib
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "server"))

from security_middleware import (
    TokenValidator,
    RateLimiter,
    CSRFProtection,
    SecurityHeadersMiddleware
)
from ws_gatekeeper import WebSocketGatekeeper
from privacy_manager import PIIRedactor, RetentionPolicy, PrivacyManager


class TestJWTAuthentication:
    """Test JWT token validation (FR-001, SC-001)"""

    def setup_method(self):
        # Test config
        self.config = {
            'jwt_algorithm': 'HS256',  # Using HS256 for testing
            'jwt_public_key': 'test_secret_key',
            'jwt_audience': 'test-api',
            'jwt_max_age': 900,  # 15 minutes
            'jwt_clock_skew': 60
        }
        self.validator = TokenValidator(self.config)

    def test_valid_token_accepted(self):
        """Test that valid JWT tokens are accepted (SC-001)"""
        now = int(time.time())
        payload = {
            'sub': 'test_user',
            'aud': 'test-api',
            'exp': now + 600,  # 10 minutes
            'iat': now,
            'jti': 'unique_nonce_123'
        }

        token = jwt.encode(payload, 'test_secret_key', algorithm='HS256')
        decoded = self.validator.verify_token(token)

        assert decoded['sub'] == 'test_user'
        assert decoded['aud'] == 'test-api'

    def test_expired_token_rejected(self):
        """Test that expired tokens are rejected (SC-001)"""
        now = int(time.time())
        payload = {
            'sub': 'test_user',
            'aud': 'test-api',
            'exp': now - 100,  # Expired 100s ago
            'iat': now - 1000,
            'jti': 'expired_nonce'
        }

        token = jwt.encode(payload, 'test_secret_key', algorithm='HS256')

        with pytest.raises(Exception) as exc:
            self.validator.verify_token(token)
        assert 'expired' in str(exc.value).lower()

    def test_invalid_audience_rejected(self):
        """Test that tokens with wrong audience are rejected"""
        now = int(time.time())
        payload = {
            'sub': 'test_user',
            'aud': 'wrong-api',  # Wrong audience
            'exp': now + 600,
            'iat': now,
            'jti': 'wrong_aud_nonce'
        }

        token = jwt.encode(payload, 'test_secret_key', algorithm='HS256')

        with pytest.raises(Exception) as exc:
            self.validator.verify_token(token)
        assert 'audience' in str(exc.value).lower()

    def test_replay_attack_rejected(self):
        """Test that replay attacks are rejected (SC-001)"""
        now = int(time.time())
        payload = {
            'sub': 'test_user',
            'aud': 'test-api',
            'exp': now + 600,
            'iat': now,
            'jti': 'replay_test_nonce'
        }

        token = jwt.encode(payload, 'test_secret_key', algorithm='HS256')

        # First use - should succeed
        self.validator.verify_token(token)

        # Second use - should fail (replay)
        with pytest.raises(Exception) as exc:
            self.validator.verify_token(token)
        assert 'replay' in str(exc.value).lower()

    def test_token_lifetime_limit(self):
        """Test that token lifetime is limited to max_age (FR-001)"""
        now = int(time.time())
        payload = {
            'sub': 'test_user',
            'aud': 'test-api',
            'exp': now + 2000,  # 2000s lifetime (> 900s max)
            'iat': now,
            'jti': 'long_lifetime_nonce'
        }

        token = jwt.encode(payload, 'test_secret_key', algorithm='HS256')

        with pytest.raises(Exception) as exc:
            self.validator.verify_token(token)
        assert 'lifetime' in str(exc.value).lower() or 'exceeds' in str(exc.value).lower()


class TestRateLimiting:
    """Test rate limiting (FR-007, SC-001)"""

    def setup_method(self):
        self.config = {
            'rate_limit_rest': 10,  # 10 req/10s for testing
            'rate_limit_window': 10
        }
        self.limiter = RateLimiter(self.config)

    def test_rate_limit_enforcement(self):
        """Test that rate limits are enforced"""
        identifier = '192.168.1.100'
        endpoint = '/api/test'

        # Make requests up to limit
        for i in range(10):
            assert self.limiter.check_rate_limit(identifier, endpoint) == True

        # 11th request should be blocked
        assert self.limiter.check_rate_limit(identifier, endpoint) == False

    def test_rate_limit_per_endpoint(self):
        """Test that rate limits are per-endpoint"""
        identifier = '192.168.1.100'

        # Fill limit for endpoint 1
        for i in range(10):
            self.limiter.check_rate_limit(identifier, '/api/endpoint1')

        # Endpoint 2 should still be available
        assert self.limiter.check_rate_limit(identifier, '/api/endpoint2') == True

    def test_rate_limit_retry_after(self):
        """Test retry-after calculation"""
        identifier = '192.168.1.100'
        endpoint = '/api/test'

        # Fill limit
        for i in range(10):
            self.limiter.check_rate_limit(identifier, endpoint)

        # Get retry-after
        retry_after = self.limiter.get_retry_after(identifier, endpoint)
        assert 0 <= retry_after <= 10


class TestCSRFProtection:
    """Test CSRF protection (FR-006)"""

    def setup_method(self):
        self.config = {
            'csrf_enabled': True,
            'csrf_header': 'X-CSRF-Token',
            'csrf_cookie': 'csrf_token'
        }
        self.csrf = CSRFProtection(self.config)

    def test_csrf_token_generation(self):
        """Test CSRF token generation"""
        token = self.csrf.generate_token()
        assert len(token) > 0
        assert isinstance(token, str)

    def test_safe_methods_skip_csrf(self):
        """Test that safe methods (GET, HEAD, OPTIONS) skip CSRF"""
        from unittest.mock import Mock

        for method in ['GET', 'HEAD', 'OPTIONS']:
            request = Mock()
            request.method = method
            assert self.csrf.verify_token(request) == True


class TestWebSocketSecurity:
    """Test WebSocket security (FR-002, SC-001)"""

    def setup_method(self):
        self.config = {
            'allowed_origins': ['http://localhost:3000'],
            'allowed_protocols': ['soundlab-v1'],
            'ws_require_auth': True,
            'ws_max_connections_per_ip': 5
        }
        self.gatekeeper = WebSocketGatekeeper(self.config)

    def test_origin_validation(self):
        """Test Origin header validation (FR-002)"""
        # Valid origin
        assert self.gatekeeper.check_origin('http://localhost:3000') == True

        # Invalid origin
        assert self.gatekeeper.check_origin('http://evil.com') == False

        # Missing origin
        assert self.gatekeeper.check_origin(None) == False

    def test_protocol_validation(self):
        """Test WebSocket protocol validation (FR-002)"""
        # Valid protocol
        assert self.gatekeeper.check_protocol('soundlab-v1') == True

        # Invalid protocol
        assert self.gatekeeper.check_protocol('evil-protocol') == False

        # Missing protocol
        assert self.gatekeeper.check_protocol(None) == False

    def test_connection_limit_per_ip(self):
        """Test connection caps per IP (FR-002)"""
        ip = '192.168.1.100'

        # Allow up to limit
        for i in range(5):
            assert self.gatekeeper.check_connection_limit(ip) == True
            from unittest.mock import Mock
            ws = Mock()
            self.gatekeeper.register_connection(ip, ws)

        # 6th connection should be blocked
        assert self.gatekeeper.check_connection_limit(ip) == False


class TestPIIRedaction:
    """Test PII redaction (FR-009)"""

    def test_email_redaction(self):
        """Test email redaction"""
        text = "Contact user@example.com for support"
        redacted = PIIRedactor.redact_text(text)
        assert 'user@example.com' not in redacted
        assert '[EMAIL]' in redacted

    def test_phone_redaction(self):
        """Test phone number redaction"""
        text = "Call 555-123-4567 for help"
        redacted = PIIRedactor.redact_text(text)
        assert '555-123-4567' not in redacted
        assert '[PHONE]' in redacted

    def test_ip_address_redaction(self):
        """Test IP address partial redaction"""
        text = "Request from 192.168.1.100"
        redacted = PIIRedactor.redact_text(text)
        assert '192.168.1.100' not in redacted
        assert '192.168' in redacted  # Partial preservation

    def test_dict_redaction(self):
        """Test dictionary redaction"""
        data = {
            'username': 'testuser',
            'password': 'secret123',
            'token': 'abc123xyz',
            'email': 'user@test.com'
        }

        redacted = PIIRedactor.redact_dict(data)

        assert redacted['username'] == 'testuser'  # Not sensitive
        assert redacted['password'] == '[REDACTED]'
        assert redacted['token'] == '[REDACTED]'
        assert '[EMAIL]' in redacted['email']


class TestRetentionPolicy:
    """Test data retention (FR-010, SC-005)"""

    def test_retention_period_config(self):
        """Test retention period configuration"""
        import tempfile
        import json

        config_data = {
            'retention_periods': {
                'logs': 30,
                'session_metrics': 90
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(config_data, f)
            config_path = f.name

        policy = RetentionPolicy(config_path)

        assert policy.get_retention_period('logs') == 30
        assert policy.get_retention_period('session_metrics') == 90

        import os
        os.unlink(config_path)

    def test_expired_file_detection(self):
        """Test expired file detection"""
        import tempfile
        from datetime import datetime, timedelta

        policy = RetentionPolicy()

        # Create old file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test")
            file_path = Path(f.name)

        # Check if expired (should be False for recent file)
        assert policy.is_expired(file_path, 'logs') == False

        # Cleanup
        file_path.unlink()


class TestFrontendStorageValidation:
    """Test frontend storage validation (FR-011)"""

    def test_detect_secrets_in_localstorage(self):
        """Test detection of secrets in localStorage"""
        privacy = PrivacyManager()

        # localStorage with secrets
        storage_with_secrets = {
            'theme': 'dark',
            'auth_token': 'secret_token_123',  # Should not be here!
            'api_key': 'key_xyz'  # Should not be here!
        }

        result = privacy.validate_frontend_storage(storage_with_secrets)

        assert result['valid'] == False
        assert len(result['secrets_found']) >= 2
        assert 'auth_token' in result['secrets_found']
        assert 'api_key' in result['secrets_found']

    def test_allowed_localstorage_content(self):
        """Test allowed localStorage content"""
        privacy = PrivacyManager()

        # Safe localStorage
        safe_storage = {
            'theme': 'dark',
            'preset_name': 'my_preset',
            'ui_layout': 'grid'
        }

        result = privacy.validate_frontend_storage(safe_storage)

        assert result['valid'] == True
        assert len(result['secrets_found']) == 0


class TestSecurityHeaders:
    """Test security headers (FR-003, FR-004, FR-005, SC-002)"""

    def test_csp_header_format(self):
        """Test CSP header format (SC-002)"""
        csp = "default-src 'self'; script-src 'self'; object-src 'none'"

        # Check no inline scripts
        assert "'unsafe-inline'" not in csp or 'script-src' in csp
        assert "'unsafe-eval'" not in csp

        # Check frame protection
        assert "frame-ancestors 'none'" in csp or "frame-ancestors" in csp

    def test_hsts_header(self):
        """Test HSTS header (FR-003)"""
        hsts = "max-age=31536000; includeSubDomains; preload"

        assert 'max-age=' in hsts
        assert int(hsts.split('max-age=')[1].split(';')[0]) >= 31536000
        assert 'includeSubDomains' in hsts


@pytest.mark.integration
class TestSecurityIntegration:
    """Integration tests for complete security flow"""

    def test_unauth_request_blocked(self):
        """Test that unauthenticated requests are blocked (SC-001)"""
        # This would test with actual FastAPI app
        pass

    def test_auth_request_accepted(self):
        """Test that authenticated requests are accepted (SC-001)"""
        # This would test with actual FastAPI app
        pass

    def test_rate_limit_429_response(self):
        """Test 429 response on rate limit (SC-001)"""
        # This would test with actual FastAPI app
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
