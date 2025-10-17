# REST API Reference

Complete reference for the Soundlab REST API endpoints.

## Base URL

```
http://localhost:8000
```

## Health & Status Endpoints

### GET /healthz

Health check endpoint.

**Response**:
```json
{
  "status": "healthy",
  "service": "soundlab-phi-matrix",
  "version": "0.9.0-rc1"
}
```

**Status Codes**:
- `200 OK` - Service is healthy

---

### GET /readyz

Readiness check endpoint. Returns 200 when service is ready to accept requests.

**Response**:
```json
{
  "status": "ready",
  "audio_engine": "initialized",
  "components": {
    "audio_server": true,
    "metrics_streamer": true,
    "preset_store": true
  }
}
```

**Status Codes**:
- `200 OK` - Service is ready
- `503 Service Unavailable` - Service is not ready

---

### GET /version

Get service version information.

**Response**:
```json
{
  "version": "0.9.0-rc1",
  "api_version": "1.0.0",
  "build_date": "2025-10-17",
  "commit": "abc123def456",
  "features": [
    "auto-phi",
    "criticality-balancer",
    "session-recording",
    "cluster-sync"
  ]
}
```

**Status Codes**:
- `200 OK` - Success

---

### GET /metrics

Get current metrics snapshot.

**Response**:
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
  "phi_breathing_active": true,
  "active_channels": 4,
  "channel_metrics": [
    {
      "channel": 0,
      "frequency": 440.0,
      "amplitude": 0.5,
      "phase": 0.0
    }
  ]
}
```

**Status Codes**:
- `200 OK` - Success

---

### GET /api/status

Get detailed server status.

**Response**:
```json
{
  "uptime": 1234.56,
  "total_frames": 37035,
  "fps": 30.0,
  "cpu_usage": 23.4,
  "memory_mb": 128.5,
  "audio": {
    "sample_rate": 48000,
    "buffer_size": 512,
    "input_device": 0,
    "output_device": 0
  },
  "features": {
    "auto_phi": true,
    "criticality_balancer": false,
    "session_recording": true
  }
}
```

**Status Codes**:
- `200 OK` - Success

---

### GET /api/dashboard/state

Get complete dashboard state including all metrics and component states.

**Response**:
```json
{
  "metrics": { ... },
  "auto_phi": {
    "enabled": true,
    "phi_depth": 0.618,
    "phi_phase": 3.14,
    "learning_rate": 0.01
  },
  "criticality_balancer": {
    "enabled": false,
    "target_criticality": 1.5
  },
  "session": {
    "recording": false,
    "current_session": null
  },
  "channels": [...]
}
```

**Status Codes**:
- `200 OK` - Success

---

## Configuration Endpoints

### POST /api/config/audio

Update audio configuration.

**Request Body**:
```json
{
  "sample_rate": 48000,
  "buffer_size": 512,
  "input_device": 0,
  "output_device": 0
}
```

**Response**:
```json
{
  "ok": true,
  "config": { ... }
}
```

**Status Codes**:
- `200 OK` - Configuration updated
- `400 Bad Request` - Invalid configuration

---

### GET /api/config/performance

Get performance configuration.

**Response**:
```json
{
  "target_fps": 30,
  "audio_buffer_ms": 10,
  "visual_complexity_level": 5,
  "enable_phi_breathing": true,
  "enable_topology_links": true
}
```

**Status Codes**:
- `200 OK` - Success

---

### POST /api/config/performance

Update performance configuration.

**Request Body**:
```json
{
  "target_fps": 30,
  "audio_buffer_ms": 10,
  "visual_complexity_level": 5
}
```

**Response**:
```json
{
  "ok": true,
  "config": { ... }
}
```

**Status Codes**:
- `200 OK` - Configuration updated
- `400 Bad Request` - Invalid configuration

---

## Auto-Phi Endpoints

### GET /api/auto-phi/state

Get Auto-Phi learner state.

**Response**:
```json
{
  "enabled": true,
  "phi_depth": 0.618,
  "phi_phase": 3.14,
  "learning_rate": 0.01,
  "momentum": 0.02,
  "criticality_target": 1.5,
  "adaptation_count": 1234
}
```

**Status Codes**:
- `200 OK` - Success

---

### POST /api/auto-phi/enable

Enable Auto-Phi learning.

**Response**:
```json
{
  "ok": true,
  "enabled": true
}
```

**Status Codes**:
- `200 OK` - Auto-Phi enabled

---

### POST /api/auto-phi/disable

Disable Auto-Phi learning.

**Response**:
```json
{
  "ok": true,
  "enabled": false
}
```

**Status Codes**:
- `200 OK` - Auto-Phi disabled

---

### POST /api/auto-phi/reset

Reset Auto-Phi learner to initial state.

**Response**:
```json
{
  "ok": true,
  "state": { ... }
}
```

**Status Codes**:
- `200 OK` - Auto-Phi reset

---

## Criticality Balancer Endpoints

### GET /api/criticality/state

Get criticality balancer state.

**Response**:
```json
{
  "enabled": false,
  "target_criticality": 1.5,
  "current_criticality": 1.234,
  "active_adjustments": 2,
  "total_adjustments": 567
}
```

**Status Codes**:
- `200 OK` - Success

---

### POST /api/criticality/enable

Enable criticality balancer.

**Request Body** (optional):
```json
{
  "target_criticality": 1.5
}
```

**Response**:
```json
{
  "ok": true,
  "enabled": true
}
```

**Status Codes**:
- `200 OK` - Criticality balancer enabled

---

### POST /api/criticality/disable

Disable criticality balancer.

**Response**:
```json
{
  "ok": true,
  "enabled": false
}
```

**Status Codes**:
- `200 OK` - Criticality balancer disabled

---

## Latency Endpoints

### GET /api/latency/metrics

Get latency diagnostics.

**Response**:
```json
{
  "total_latency_ms": 45.2,
  "hardware_latency_ms": 21.3,
  "software_latency_ms": 23.9,
  "buffer_latency_ms": 10.7,
  "calibrated": true,
  "compensation_ms": 15.0
}
```

**Status Codes**:
- `200 OK` - Success

---

### POST /api/latency/calibrate

Run latency calibration.

**Response**:
```json
{
  "ok": true,
  "latency_ms": 45.2,
  "confidence": 0.95,
  "samples": 100
}
```

**Status Codes**:
- `200 OK` - Calibration complete
- `500 Internal Server Error` - Calibration failed

---

## Error Responses

All endpoints may return error responses:

```json
{
  "detail": "Error message"
}
```

Common error status codes:
- `400 Bad Request` - Invalid request parameters
- `404 Not Found` - Resource not found
- `409 Conflict` - Resource conflict
- `500 Internal Server Error` - Server error
