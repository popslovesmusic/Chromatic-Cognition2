"""
WebSocket Gatekeeper - Feature 024 (FR-002)

Enforces WebSocket origin checks, protocol validation, and token binding
for secure WebSocket connections.

Requirements:
- FR-002: Enforce Origin/Sec-WebSocket-Protocol and host allowlist
- Token binding for authenticated WS sessions
- Connection caps per IP to prevent handshake floods
"""

import logging
from typing import Optional, Dict, Set
from urllib.parse import urlparse
from fastapi import WebSocket, WebSocketDisconnect, status
from starlette.websockets import WebSocketState
import time

logger = logging.getLogger(__name__)


class WebSocketGatekeeper:
    """WebSocket security gatekeeper (FR-002)"""

    def __init__(self, config: dict):
        self.config = config
        self.allowed_origins = set(config.get('allowed_origins', ['http://localhost:3000']))
        self.allowed_protocols = set(config.get('allowed_protocols', ['soundlab-v1']))
        self.require_auth = config.get('ws_require_auth', True)
        self.max_connections_per_ip = config.get('ws_max_connections_per_ip', 10)

        # Track connections per IP
        self.connections_by_ip: Dict[str, int] = {}

        # Active authenticated connections
        self.authenticated_connections: Set[WebSocket] = set()

    def check_origin(self, origin: Optional[str]) -> bool:
        """
        Verify Origin header against allowlist (FR-002).

        Args:
            origin: Origin header value

        Returns:
            True if origin is allowed, False otherwise
        """
        if not origin:
            logger.warning("WebSocket connection without Origin header")
            return False

        # Parse and normalize origin
        parsed = urlparse(origin)
        normalized_origin = f"{parsed.scheme}://{parsed.netloc}"

        # Check against allowlist
        if normalized_origin not in self.allowed_origins:
            logger.warning(f"WebSocket origin not allowed: {origin}")
            return False

        return True

    def check_protocol(self, protocol: Optional[str]) -> bool:
        """
        Verify Sec-WebSocket-Protocol header (FR-002).

        Args:
            protocol: WebSocket protocol value

        Returns:
            True if protocol is allowed, False otherwise
        """
        if not protocol:
            logger.warning("WebSocket connection without protocol")
            return False

        if protocol not in self.allowed_protocols:
            logger.warning(f"WebSocket protocol not allowed: {protocol}")
            return False

        return True

    def check_connection_limit(self, client_ip: str) -> bool:
        """
        Check connection limit per IP to prevent handshake floods.

        Args:
            client_ip: Client IP address

        Returns:
            True if within limit, False otherwise
        """
        current_connections = self.connections_by_ip.get(client_ip, 0)

        if current_connections >= self.max_connections_per_ip:
            logger.warning(
                f"Connection limit exceeded for IP {client_ip}: "
                f"{current_connections}/{self.max_connections_per_ip}"
            )
            return False

        return True

    def register_connection(self, client_ip: str, websocket: WebSocket):
        """Register new connection"""
        self.connections_by_ip[client_ip] = \
            self.connections_by_ip.get(client_ip, 0) + 1

        logger.info(
            f"WebSocket connection registered: {client_ip} "
            f"({self.connections_by_ip[client_ip]} total)"
        )

    def unregister_connection(self, client_ip: str, websocket: WebSocket):
        """Unregister closed connection"""
        if client_ip in self.connections_by_ip:
            self.connections_by_ip[client_ip] -= 1

            if self.connections_by_ip[client_ip] <= 0:
                del self.connections_by_ip[client_ip]

        self.authenticated_connections.discard(websocket)

        logger.info(
            f"WebSocket connection unregistered: {client_ip} "
            f"({self.connections_by_ip.get(client_ip, 0)} remaining)"
        )

    async def authenticate_websocket(
        self,
        websocket: WebSocket,
        token_validator
    ) -> Optional[dict]:
        """
        Authenticate WebSocket connection via token.

        Args:
            websocket: WebSocket connection
            token_validator: TokenValidator instance

        Returns:
            Decoded token payload if valid, None otherwise
        """
        # Expect first message to be auth token
        try:
            # Wait for auth message with timeout
            message = await websocket.receive_json()

            if message.get('type') != 'auth':
                logger.warning("First WS message not auth type")
                await websocket.close(code=4401, reason="Authentication required")
                return None

            token = message.get('token')
            if not token:
                logger.warning("Auth message missing token")
                await websocket.close(code=4401, reason="Token required")
                return None

            # Verify token
            try:
                payload = token_validator.verify_token(token)

                # Mark connection as authenticated
                self.authenticated_connections.add(websocket)

                logger.info(f"WebSocket authenticated: user={payload.get('sub')}")
                return payload

            except Exception as e:
                logger.warning(f"WebSocket auth failed: {e}")
                await websocket.close(code=4401, reason="Invalid token")
                return None

        except WebSocketDisconnect:
            logger.info("WebSocket disconnected during auth")
            return None
        except Exception as e:
            logger.error(f"WebSocket auth error: {e}")
            await websocket.close(code=4500, reason="Internal error")
            return None

    async def accept_connection(
        self,
        websocket: WebSocket,
        token_validator=None
    ) -> Optional[dict]:
        """
        Accept and validate WebSocket connection.

        Args:
            websocket: WebSocket connection
            token_validator: Optional TokenValidator for auth

        Returns:
            User payload if authenticated, None otherwise
        """
        # Get client info
        client_ip = websocket.client.host
        origin = websocket.headers.get('origin')
        protocol = websocket.headers.get('sec-websocket-protocol')

        # Check origin (FR-002)
        if not self.check_origin(origin):
            await websocket.close(code=4403, reason="Origin not allowed")
            return None

        # Check protocol (FR-002)
        if not self.check_protocol(protocol):
            await websocket.close(code=4400, reason="Protocol not supported")
            return None

        # Check connection limit (handshake flood protection)
        if not self.check_connection_limit(client_ip):
            await websocket.close(code=4429, reason="Too many connections")
            return None

        # Accept connection
        await websocket.accept(subprotocol=protocol)

        # Register connection
        self.register_connection(client_ip, websocket)

        # Authenticate if required
        user_payload = None
        if self.require_auth and token_validator:
            user_payload = await self.authenticate_websocket(
                websocket,
                token_validator
            )

            if not user_payload:
                self.unregister_connection(client_ip, websocket)
                return None

        return user_payload

    async def close_connection(self, websocket: WebSocket):
        """Safely close WebSocket connection"""
        client_ip = websocket.client.host

        try:
            if websocket.client_state != WebSocketState.DISCONNECTED:
                await websocket.close()
        except Exception as e:
            logger.error(f"Error closing WebSocket: {e}")

        self.unregister_connection(client_ip, websocket)

    def get_stats(self) -> dict:
        """Get gatekeeper statistics"""
        return {
            'total_connections': sum(self.connections_by_ip.values()),
            'authenticated_connections': len(self.authenticated_connections),
            'connections_by_ip': dict(self.connections_by_ip),
            'config': {
                'allowed_origins': list(self.allowed_origins),
                'allowed_protocols': list(self.allowed_protocols),
                'max_per_ip': self.max_connections_per_ip
            }
        }


async def websocket_endpoint_with_auth(
    websocket: WebSocket,
    gatekeeper: WebSocketGatekeeper,
    token_validator,
    handler
):
    """
    WebSocket endpoint wrapper with authentication and security checks.

    Usage:
        @app.websocket("/ws/dashboard")
        async def dashboard_ws(websocket: WebSocket):
            await websocket_endpoint_with_auth(
                websocket,
                app.state.gatekeeper,
                app.state.token_validator,
                handle_dashboard_messages
            )

    Args:
        websocket: WebSocket connection
        gatekeeper: WebSocketGatekeeper instance
        token_validator: TokenValidator instance
        handler: Async function to handle messages
    """
    client_ip = websocket.client.host

    try:
        # Accept and authenticate connection
        user_payload = await gatekeeper.accept_connection(
            websocket,
            token_validator
        )

        if not user_payload:
            logger.warning(f"WebSocket auth failed: {client_ip}")
            return

        # Connection accepted and authenticated
        logger.info(f"WebSocket ready: {client_ip}, user={user_payload.get('sub')}")

        # Send auth success
        await websocket.send_json({
            'type': 'auth_success',
            'user': user_payload.get('sub')
        })

        # Handle messages
        await handler(websocket, user_payload)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {client_ip}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await gatekeeper.close_connection(websocket)
