# Soundlab API Reference

Complete API reference for the Soundlab Φ-Matrix system.

## API Overview

The Soundlab API provides comprehensive control over the audio synthesis system through REST and WebSocket interfaces.

**Base URL**: `http://localhost:8000`

**WebSocket URL**: `ws://localhost:8000`

## API Documentation

- [**REST API**](rest_api.md) - HTTP endpoints for system control
- [**Preset API**](preset_api.md) - Preset management and A/B comparison
- [**Session API**](session_api.md) - Recording and playback
- [**WebSocket API**](websocket_api.md) - Real-time streaming

## Quick Reference

### Health & Status

```http
GET /healthz          # Health check
GET /readyz           # Readiness check
GET /version          # Version info
GET /metrics          # Current metrics snapshot
GET /api/status       # Server status
```

### Presets

```http
GET    /api/presets           # List presets
POST   /api/presets           # Create preset
GET    /api/presets/{id}      # Get preset
PUT    /api/presets/{id}      # Update preset
DELETE /api/presets/{id}      # Delete preset
```

### Session Recording

```http
POST   /api/session/start     # Start recording
POST   /api/session/stop      # Stop recording
GET    /api/session/list      # List sessions
GET    /api/session/{id}      # Get session
DELETE /api/session/{id}      # Delete session
```

### WebSocket Streams

```
ws://localhost:8000/ws/metrics     # Metrics stream (30 Hz)
ws://localhost:8000/ws/latency     # Latency stream (10 Hz)
```

## Authentication

Currently, the API does not require authentication. This may change in production deployments.

## Rate Limiting

No rate limiting is currently enforced. Clients should self-regulate to avoid overwhelming the server.

## Error Handling

All API endpoints return standard HTTP status codes:

- `200 OK` - Success
- `201 Created` - Resource created
- `400 Bad Request` - Invalid request
- `404 Not Found` - Resource not found
- `409 Conflict` - Resource conflict
- `500 Internal Server Error` - Server error

Error responses include a JSON body:

```json
{
  "detail": "Error message describing what went wrong"
}
```

## Data Formats

### Metrics Frame

```json
{
  "frame": 12345,
  "timestamp": 1234567890.123,
  "ici": 0.654,
  "criticality": 1.234,
  "phase_coherence": 0.876,
  "spectral_centroid": 1234.5,
  "phi_depth": 0.618,
  "phi_phase": 3.14,
  "active_channels": 4
}
```

### Preset

```json
{
  "id": "abc123...",
  "name": "My Preset",
  "schema_version": "1.0.0",
  "created_at": "2025-10-17T10:30:00Z",
  "modified_at": "2025-10-17T10:30:00Z",
  "notes": "Description of preset",
  "tags": ["ambient", "experimental"],
  "channels": [...]
}
```

### Session

```json
{
  "id": "session123...",
  "name": "Recording 2025-10-17",
  "created_at": "2025-10-17T10:30:00Z",
  "duration": 123.45,
  "frame_count": 3704,
  "sample_rate": 30
}
```

## SDKs and Examples

- **Python Examples**: `examples/` directory
- **Interactive Docs**: http://localhost:8000/docs

## Versioning

API Version: **1.0.0**

The API follows semantic versioning. Breaking changes will increment the major version.

## Support

- **Issues**: GitHub Issues
- **Documentation**: `docs/` directory
- **Examples**: `examples/` directory
