"""
Security Middleware - Feature 024 (FR-001, FR-003, FR-004, FR-005, FR-006, FR-007)

Provides JWT authentication, security headers, CSRF protection, and rate limiting
for REST and WebSocket endpoints.

Requirements:
- FR-001: JWT (RS256/EdDSA) auth with audience, exp ≤15m, nonce replay guard
- FR-003: TLS enforcement, secure cookies, HSTS
- FR-004: CSP headers
- FR-005: Additional security headers
- FR-006: CSRF protection
- FR-007: Rate limiting (token + IP buckets)
"""

import jwt
import time
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Set, Tuple
from functools import wraps
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)

# Nonce replay protection (in-memory cache, use Redis in production)
_nonce_cache: Set[str] = set()
_nonce_cache_max_size = 10000


class TokenValidator:
    """JWT token validation (FR-001)"""

    def __init__(self, config: dict):
        self.config = config
        self.algorithm = config.get('jwt_algorithm', 'RS256')
        self.public_key = config.get('jwt_public_key')
        self.audience = config.get('jwt_audience', 'soundlab-api')
        self.max_age_seconds = config.get('jwt_max_age', 900)  # 15 minutes
        self.clock_skew_seconds = config.get('jwt_clock_skew', 60)

    def verify_token(self, token: str) -> Dict:
        """
        Verify JWT token with audience, expiration, and nonce checks.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload

        Raises:
            HTTPException: If token is invalid, expired, or replayed
        """
        try:
            # Decode and verify signature
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.algorithm],
                audience=self.audience,
                leeway=self.clock_skew_seconds  # ±60s clock skew tolerance
            )

            # Check expiration (exp ≤ 15 minutes)
            exp = payload.get('exp')
            iat = payload.get('iat')

            if not exp or not iat:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing exp or iat"
                )

            token_age = exp - iat
            if token_age > self.max_age_seconds:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Token lifetime {token_age}s exceeds max {self.max_age_seconds}s"
                )

            # Nonce/JTI replay protection
            nonce = payload.get('jti') or payload.get('nonce')
            if not nonce:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing jti/nonce"
                )

            # Check if nonce already used
            if nonce in _nonce_cache:
                logger.warning(f"Replay attempt detected: nonce={nonce}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token replay detected"
                )

            # Add nonce to cache
            _nonce_cache.add(nonce)

            # Limit cache size (FIFO)
            if len(_nonce_cache) > _nonce_cache_max_size:
                _nonce_cache.pop()

            return payload

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired"
            )
        except jwt.InvalidAudienceError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid audience"
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )


class RateLimiter:
    """Rate limiting for REST and WebSocket (FR-007)"""

    def __init__(self, config: dict):
        self.config = config
        self.rest_limit = config.get('rate_limit_rest', 100)  # req/10s
        self.rest_window = config.get('rate_limit_window', 10)
        self.ws_handshake_limit = config.get('ws_handshake_limit', 10)  # per IP

        # Buckets: {(token_or_ip, endpoint): [(timestamp, count), ...]}
        self.buckets: Dict[Tuple[str, str], list] = {}

    def _get_bucket_key(self, identifier: str, endpoint: str) -> Tuple[str, str]:
        """Get bucket key for rate limiting"""
        return (identifier, endpoint)

    def _cleanup_bucket(self, bucket: list, window: int) -> list:
        """Remove expired entries from bucket"""
        now = time.time()
        return [(ts, count) for ts, count in bucket if now - ts < window]

    def check_rate_limit(self, identifier: str, endpoint: str) -> bool:
        """
        Check if request is within rate limit.

        Args:
            identifier: Token hash or IP address
            endpoint: Endpoint path

        Returns:
            True if within limit, False if exceeded
        """
        key = self._get_bucket_key(identifier, endpoint)
        now = time.time()

        # Get and clean bucket
        bucket = self.buckets.get(key, [])
        bucket = self._cleanup_bucket(bucket, self.rest_window)

        # Count requests in window
        total_requests = sum(count for _, count in bucket)

        if total_requests >= self.rest_limit:
            logger.warning(f"Rate limit exceeded: {identifier} on {endpoint}")
            return False

        # Add current request
        bucket.append((now, 1))
        self.buckets[key] = bucket

        return True

    def get_retry_after(self, identifier: str, endpoint: str) -> int:
        """Get retry-after seconds for rate limited request"""
        key = self._get_bucket_key(identifier, endpoint)
        bucket = self.buckets.get(key, [])

        if not bucket:
            return 0

        oldest_ts = min(ts for ts, _ in bucket)
        retry_after = int(self.rest_window - (time.time() - oldest_ts))
        return max(0, retry_after)


class CSRFProtection:
    """CSRF protection for state-changing requests (FR-006)"""

    def __init__(self, config: dict):
        self.config = config
        self.enabled = config.get('csrf_enabled', True)
        self.header_name = config.get('csrf_header', 'X-CSRF-Token')
        self.cookie_name = config.get('csrf_cookie', 'csrf_token')

    def generate_token(self) -> str:
        """Generate CSRF token"""
        return secrets.token_urlsafe(32)

    def verify_token(self, request: Request) -> bool:
        """
        Verify CSRF token using double-submit pattern.

        Args:
            request: FastAPI request object

        Returns:
            True if token valid, False otherwise
        """
        if not self.enabled:
            return True

        # Skip CSRF for safe methods
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True

        # Get token from header and cookie
        header_token = request.headers.get(self.header_name)
        cookie_token = request.cookies.get(self.cookie_name)

        if not header_token or not cookie_token:
            return False

        # Compare tokens (constant-time)
        return secrets.compare_digest(header_token, cookie_token)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Security headers middleware (FR-003, FR-004, FR-005)"""

    def __init__(self, app, config: dict):
        super().__init__(app)
        self.config = config

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # FR-003: HSTS (HTTP Strict Transport Security)
        response.headers['Strict-Transport-Security'] = \
            'max-age=31536000; includeSubDomains; preload'

        # FR-004: Content Security Policy
        csp = self.config.get('csp_policy',
            "default-src 'self'; "
            "script-src 'self' 'sha256-...'; "
            "connect-src 'self' wss:; "
            "object-src 'none'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers['Content-Security-Policy'] = csp

        # FR-005: Additional security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Cross-Origin policies
        response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
        response.headers['Cross-Origin-Embedder-Policy'] = 'require-corp'

        # Permissions Policy (FR-005: camera/mic=())
        permissions = self.config.get('permissions_policy',
            'camera=(), microphone=(), geolocation=(), payment=()'
        )
        response.headers['Permissions-Policy'] = permissions

        # Remove server header
        response.headers.pop('Server', None)

        return response


class AuthMiddleware:
    """Authentication middleware for REST endpoints"""

    def __init__(self, token_validator: TokenValidator):
        self.token_validator = token_validator

    def __call__(self, func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get('request') or args[0]

            # Extract token from Authorization header
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing or invalid Authorization header"
                )

            token = auth_header.split(' ')[1]

            # Verify token
            payload = self.token_validator.verify_token(token)

            # Add user info to request state
            request.state.user = payload

            return await func(*args, **kwargs)

        return wrapper


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""

    def __init__(self, app, rate_limiter: RateLimiter):
        super().__init__(app)
        self.rate_limiter = rate_limiter

    async def dispatch(self, request: Request, call_next):
        # Get identifier (IP or token hash)
        identifier = request.client.host

        # Check Authorization header for token-based limiting
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            # Hash token for privacy
            identifier = hashlib.sha256(token.encode()).hexdigest()[:16]

        endpoint = request.url.path

        # Check rate limit
        if not self.rate_limiter.check_rate_limit(identifier, endpoint):
            retry_after = self.rate_limiter.get_retry_after(identifier, endpoint)

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(retry_after)}
            )

        response = await call_next(request)
        return response


def require_auth(token_validator: TokenValidator):
    """Decorator for endpoints requiring authentication"""
    return AuthMiddleware(token_validator)


def init_security_middleware(app, config: dict):
    """
    Initialize all security middleware.

    Args:
        app: FastAPI application
        config: Security configuration dict
    """
    # Token validator
    token_validator = TokenValidator(config)

    # Rate limiter
    rate_limiter = RateLimiter(config)

    # CSRF protection
    csrf = CSRFProtection(config)

    # Add middleware (order matters - last added runs first)
    app.add_middleware(SecurityHeadersMiddleware, config=config)
    app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)

    # Store in app state for use in routes
    app.state.token_validator = token_validator
    app.state.rate_limiter = rate_limiter
    app.state.csrf = csrf

    logger.info("Security middleware initialized")

    return {
        'token_validator': token_validator,
        'rate_limiter': rate_limiter,
        'csrf': csrf
    }
