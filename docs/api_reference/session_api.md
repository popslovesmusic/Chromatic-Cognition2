# Session API Reference

Complete reference for session recording and playback endpoints.

## Base URL

```
http://localhost:8000/api/session
```

## Session Recording Operations

### POST /api/session/start

Start a new recording session.

**Request Body** (optional):
```json
{
  "name": "My Recording Session",
  "notes": "Session description",
  "tags": ["tag1", "tag2"]
}
```

**Response**:
```json
{
  "ok": true,
  "session_id": "session-uuid-123",
  "name": "My Recording Session",
  "started_at": "2025-10-17T10:30:00Z"
}
```

**Status Codes**:
- `200 OK` - Recording started
- `400 Bad Request` - Already recording

---

### POST /api/session/stop

Stop current recording session.

**Response**:
```json
{
  "ok": true,
  "session_id": "session-uuid-123",
  "total_frames": 3704,
  "duration": 123.45,
  "stopped_at": "2025-10-17T10:32:03Z"
}
```

**Status Codes**:
- `200 OK` - Recording stopped
- `400 Bad Request` - No active recording

---

### GET /api/session/status

Get current recording status.

**Response** (when recording):
```json
{
  "is_recording": true,
  "session_id": "session-uuid-123",
  "name": "My Recording Session",
  "started_at": "2025-10-17T10:30:00Z",
  "duration": 45.67,
  "frames_recorded": 1370
}
```

**Response** (when not recording):
```json
{
  "is_recording": false
}
```

**Status Codes**:
- `200 OK` - Success

---

## Session Management

### GET /api/session/list

List all recorded sessions.

**Query Parameters**:
- `limit` (integer, optional, default: 50) - Maximum results
- `offset` (integer, optional, default: 0) - Skip N results
- `sort` (string, optional, default: "created_at") - Sort field
- `order` (string, optional, default: "desc") - Sort order: `asc` or `desc`

**Example Request**:
```http
GET /api/session/list?limit=10&sort=duration&order=desc
```

**Response**:
```json
{
  "total": 42,
  "offset": 0,
  "limit": 10,
  "sessions": [
    {
      "id": "session-uuid-123",
      "name": "My Recording Session",
      "created_at": "2025-10-17T10:30:00Z",
      "duration": 123.45,
      "frame_count": 3704,
      "sample_rate": 30,
      "size_bytes": 456789,
      "tags": ["tag1", "tag2"]
    },
    ...
  ]
}
```

**Status Codes**:
- `200 OK` - Success

---

### GET /api/session/{id}

Get session details.

**Path Parameters**:
- `id` (string, required) - Session ID

**Response**:
```json
{
  "id": "session-uuid-123",
  "name": "My Recording Session",
  "notes": "Session description",
  "created_at": "2025-10-17T10:30:00Z",
  "duration": 123.45,
  "frame_count": 3704,
  "sample_rate": 30,
  "size_bytes": 456789,
  "tags": ["tag1", "tag2"],
  "metadata": {
    "preset_id": "preset-uuid-456",
    "preset_name": "Ambient Preset",
    "software_version": "0.9.0-rc1"
  }
}
```

**Status Codes**:
- `200 OK` - Success
- `404 Not Found` - Session not found

---

### PUT /api/session/{id}

Update session metadata.

**Path Parameters**:
- `id` (string, required) - Session ID

**Request Body**:
```json
{
  "name": "Updated Name",
  "notes": "Updated description",
  "tags": ["new", "tags"]
}
```

**Response**:
```json
{
  "ok": true,
  "id": "session-uuid-123"
}
```

**Status Codes**:
- `200 OK` - Session updated
- `404 Not Found` - Session not found

---

### DELETE /api/session/{id}

Delete a recorded session.

**Path Parameters**:
- `id` (string, required) - Session ID

**Response**:
```json
{
  "ok": true
}
```

**Status Codes**:
- `200 OK` - Session deleted
- `404 Not Found` - Session not found

---

## Session Data Access

### GET /api/session/{id}/data

Get session frame data.

**Path Parameters**:
- `id` (string, required) - Session ID

**Query Parameters**:
- `offset` (integer, optional, default: 0) - Frame offset
- `limit` (integer, optional, default: 1000) - Max frames to return

**Example Request**:
```http
GET /api/session/session-uuid-123/data?offset=0&limit=100
```

**Response**:
```json
{
  "session_id": "session-uuid-123",
  "offset": 0,
  "count": 100,
  "frames": [
    {
      "frame": 0,
      "timestamp": 0.0,
      "ici": 0.654,
      "criticality": 1.234,
      "phase_coherence": 0.876,
      "phi_depth": 0.618,
      "phi_phase": 3.14
    },
    ...
  ]
}
```

**Status Codes**:
- `200 OK` - Success
- `404 Not Found` - Session not found

---

### GET /api/session/{id}/export

Export session data.

**Path Parameters**:
- `id` (string, required) - Session ID

**Query Parameters**:
- `format` (string, optional, default: "json") - Export format: `json`, `csv`, `hdf5`

**Example Request**:
```http
GET /api/session/session-uuid-123/export?format=csv
```

**Response**:
- Content-Type: Varies by format
- Content-Disposition: `attachment; filename=session_123.{format}`

**JSON Format**:
```json
{
  "session": {...},
  "frames": [...]
}
```

**CSV Format**:
```csv
frame,timestamp,ici,criticality,phase_coherence,phi_depth,phi_phase
0,0.0,0.654,1.234,0.876,0.618,3.14
1,0.033,0.652,1.235,0.875,0.619,3.15
...
```

**Status Codes**:
- `200 OK` - Export successful
- `404 Not Found` - Session not found
- `400 Bad Request` - Invalid format

---

## Session Statistics

### GET /api/session/{id}/stats

Get session statistics.

**Path Parameters**:
- `id` (string, required) - Session ID

**Response**:
```json
{
  "session_id": "session-uuid-123",
  "duration": 123.45,
  "frame_count": 3704,
  "sample_rate": 30.0,
  "metrics": {
    "ici": {
      "mean": 0.654,
      "min": 0.123,
      "max": 0.987,
      "stdev": 0.123
    },
    "criticality": {
      "mean": 1.234,
      "min": 0.567,
      "max": 2.891,
      "stdev": 0.456
    },
    "phase_coherence": {
      "mean": 0.876,
      "min": 0.234,
      "max": 0.999,
      "stdev": 0.123
    },
    "phi_depth": {
      "mean": 0.618,
      "min": 0.500,
      "max": 0.750,
      "stdev": 0.050
    }
  },
  "events": {
    "critical_events": 12,
    "state_changes": 5,
    "peak_criticality": 2.891,
    "peak_criticality_time": 45.67
  }
}
```

**Status Codes**:
- `200 OK` - Success
- `404 Not Found` - Session not found

---

## Session Playback

### POST /api/session/{id}/play

Start playing back a recorded session.

**Path Parameters**:
- `id` (string, required) - Session ID

**Request Body** (optional):
```json
{
  "speed": 1.0,
  "loop": false,
  "start_frame": 0
}
```

**Response**:
```json
{
  "ok": true,
  "session_id": "session-uuid-123",
  "playback_id": "playback-uuid-789",
  "started_at": "2025-10-17T11:00:00Z"
}
```

**Status Codes**:
- `200 OK` - Playback started
- `404 Not Found` - Session not found
- `400 Bad Request` - Invalid playback parameters

---

### POST /api/session/playback/stop

Stop current playback.

**Response**:
```json
{
  "ok": true,
  "playback_id": "playback-uuid-789",
  "frames_played": 1234
}
```

**Status Codes**:
- `200 OK` - Playback stopped
- `400 Bad Request` - No active playback

---

### GET /api/session/playback/status

Get playback status.

**Response** (when playing):
```json
{
  "is_playing": true,
  "session_id": "session-uuid-123",
  "playback_id": "playback-uuid-789",
  "current_frame": 1234,
  "total_frames": 3704,
  "progress": 0.333,
  "speed": 1.0,
  "loop": false
}
```

**Response** (when not playing):
```json
{
  "is_playing": false
}
```

**Status Codes**:
- `200 OK` - Success

---

## Session Comparison

### POST /api/session/compare

Compare two sessions.

**Request Body**:
```json
{
  "session_a_id": "session-uuid-123",
  "session_b_id": "session-uuid-456",
  "metrics": ["ici", "criticality", "phase_coherence"]
}
```

**Response**:
```json
{
  "session_a": {...},
  "session_b": {...},
  "comparison": {
    "ici": {
      "mean_a": 0.654,
      "mean_b": 0.543,
      "difference": 0.111,
      "correlation": 0.789
    },
    "criticality": {
      "mean_a": 1.234,
      "mean_b": 1.456,
      "difference": -0.222,
      "correlation": 0.654
    }
  },
  "overall_similarity": 0.723
}
```

**Status Codes**:
- `200 OK` - Comparison complete
- `404 Not Found` - One or both sessions not found
- `400 Bad Request` - Invalid comparison parameters

---

## Session Schema

### Full Session Object

```json
{
  "id": "session-uuid-123",
  "name": "Recording Session",
  "notes": "Description",
  "tags": ["tag1", "tag2"],
  "created_at": "2025-10-17T10:30:00Z",
  "duration": 123.45,
  "frame_count": 3704,
  "sample_rate": 30,
  "size_bytes": 456789,
  "metadata": {
    "preset_id": "preset-uuid-456",
    "preset_name": "Ambient Preset",
    "software_version": "0.9.0-rc1",
    "user": "user@example.com"
  }
}
```

### Frame Data Schema

```json
{
  "frame": 0,
  "timestamp": 0.0,
  "ici": 0.654,
  "criticality": 1.234,
  "phase_coherence": 0.876,
  "spectral_centroid": 1234.5,
  "phi_depth": 0.618,
  "phi_phase": 3.14,
  "active_channels": 4,
  "channel_metrics": [...]
}
```
