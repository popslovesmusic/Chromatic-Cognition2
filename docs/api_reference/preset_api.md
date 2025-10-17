# Preset API Reference

Complete reference for preset management endpoints.

## Base URL

```
http://localhost:8000/api/presets
```

## Preset CRUD Operations

### GET /api/presets

List presets with optional filtering.

**Query Parameters**:
- `query` (string, optional) - Search query for name/notes
- `tag` (string, optional) - Filter by tag
- `limit` (integer, optional, default: 50) - Maximum results (1-200)

**Example Request**:
```http
GET /api/presets?query=ambient&tag=experimental&limit=10
```

**Response**:
```json
[
  {
    "id": "abc123...",
    "name": "Ambient Preset 1",
    "created_at": "2025-10-17T10:30:00Z",
    "modified_at": "2025-10-17T10:30:00Z",
    "tags": ["ambient", "experimental"],
    "notes": "Warm ambient sound"
  },
  ...
]
```

**Status Codes**:
- `200 OK` - Success
- `500 Internal Server Error` - Server error

---

### GET /api/presets/{id}

Get full preset by ID.

**Path Parameters**:
- `id` (string, required) - Preset ID

**Example Request**:
```http
GET /api/presets/abc123def456
```

**Response**:
```json
{
  "id": "abc123def456",
  "name": "My Preset",
  "schema_version": "1.0.0",
  "created_at": "2025-10-17T10:30:00Z",
  "modified_at": "2025-10-17T10:30:00Z",
  "notes": "Detailed description",
  "tags": ["ambient", "experimental"],
  "channels": [
    {
      "id": 0,
      "enabled": true,
      "frequency": 440.0,
      "amplitude": 0.5,
      "phase": 0.0,
      "waveform": "sine"
    }
  ],
  "global": {
    "phi_depth": 0.618,
    "phi_phase": 3.14
  }
}
```

**Status Codes**:
- `200 OK` - Success
- `404 Not Found` - Preset not found

---

### POST /api/presets

Create a new preset.

**Query Parameters**:
- `collision` (string, optional, default: "prompt") - Collision policy: `prompt`, `overwrite`, `new_copy`, `merge`

**Request Body**:
```json
{
  "name": "New Preset",
  "notes": "Description",
  "tags": ["tag1", "tag2"],
  "channels": [...],
  "global": {...}
}
```

**Response**:
```json
{
  "id": "abc123...",
  "created": true,
  "name": "New Preset"
}
```

**Status Codes**:
- `201 Created` - Preset created
- `200 OK` - Preset already existed (depending on collision policy)
- `400 Bad Request` - Validation error
- `409 Conflict` - Preset already exists (collision=prompt)

---

### PUT /api/presets/{id}

Update existing preset.

**Path Parameters**:
- `id` (string, required) - Preset ID

**Request Body**:
```json
{
  "id": "abc123...",
  "name": "Updated Preset",
  "notes": "Updated description",
  "tags": ["updated"],
  "channels": [...],
  "global": {...}
}
```

**Response**:
```json
{
  "ok": true,
  "id": "abc123..."
}
```

**Status Codes**:
- `200 OK` - Preset updated
- `400 Bad Request` - Validation error
- `404 Not Found` - Preset not found

---

### DELETE /api/presets/{id}

Delete preset by ID.

**Path Parameters**:
- `id` (string, required) - Preset ID

**Response**:
```json
{
  "ok": true
}
```

**Status Codes**:
- `200 OK` - Preset deleted
- `404 Not Found` - Preset not found

---

## Import/Export Operations

### POST /api/presets/export

Export all presets as JSON bundle.

**Response**:
- Content-Type: `application/json`
- Content-Disposition: `attachment; filename=soundlab_presets_export.json`

Returns file download containing:
```json
{
  "version": "1.0.0",
  "exported_at": "2025-10-17T10:30:00Z",
  "count": 42,
  "presets": [...]
}
```

**Status Codes**:
- `200 OK` - Export successful
- `500 Internal Server Error` - Export failed

---

### POST /api/presets/import

Import preset bundle from JSON file.

**Query Parameters**:
- `dry_run` (boolean, optional, default: false) - Validate only, don't save
- `collision` (string, optional, default: "prompt") - Collision policy

**Request Body**:
- Multipart form data with file upload

**Example Request**:
```http
POST /api/presets/import?dry_run=false&collision=new_copy
Content-Type: multipart/form-data; boundary=...

--boundary
Content-Disposition: form-data; name="file"; filename="presets.json"
Content-Type: application/json

{...}
--boundary--
```

**Response**:
```json
{
  "imported": 10,
  "updated": 2,
  "skipped": 1,
  "errors": [
    "Preset 'X' failed validation: ..."
  ]
}
```

**Status Codes**:
- `200 OK` - Import complete (check response for details)
- `400 Bad Request` - Invalid JSON or file format

---

## A/B Snapshot Operations

### POST /api/presets/ab/store/{slot}

Store preset in A or B slot for comparison.

**Path Parameters**:
- `slot` (string, required) - `A` or `B`

**Request Body**:
```json
{
  "id": "abc123...",
  "name": "Preset A",
  "channels": [...],
  ...
}
```

**Response**:
```json
{
  "ok": true,
  "slot": "A",
  "status": {
    "slot_a_filled": true,
    "slot_b_filled": false,
    "current_slot": "A"
  }
}
```

**Status Codes**:
- `200 OK` - Snapshot stored
- `400 Bad Request` - Invalid slot or preset data

---

### GET /api/presets/ab/get/{slot}

Get snapshot from A or B slot.

**Path Parameters**:
- `slot` (string, required) - `A` or `B`

**Response**:
```json
{
  "id": "abc123...",
  "name": "Preset A",
  "channels": [...],
  ...
}
```

**Status Codes**:
- `200 OK` - Success
- `404 Not Found` - Slot is empty

---

### POST /api/presets/ab/toggle

Toggle between A and B snapshots.

**Response**:
```json
{
  "ok": true,
  "current_slot": "B",
  "preset": {
    "id": "def456...",
    "name": "Preset B",
    ...
  }
}
```

**Status Codes**:
- `200 OK` - Toggled successfully
- `400 Bad Request` - Cannot toggle (A or B empty)
- `429 Too Many Requests` - Toggle too fast (guard time not elapsed)

---

### GET /api/presets/ab/status

Get A/B comparison status.

**Response**:
```json
{
  "slot_a_filled": true,
  "slot_b_filled": true,
  "current_slot": "A",
  "can_toggle": true,
  "guard_time_ms": 500
}
```

**Status Codes**:
- `200 OK` - Success

---

### GET /api/presets/ab/diff

Get differences between A and B.

**Response**:
```json
{
  "differences": [
    {
      "path": "channels[0].frequency",
      "value_a": 440.0,
      "value_b": 880.0
    },
    {
      "path": "global.phi_depth",
      "value_a": 0.618,
      "value_b": 0.500
    }
  ],
  "total_differences": 2
}
```

**Status Codes**:
- `200 OK` - Success
- `400 Bad Request` - Cannot compare (A or B is empty)

---

### DELETE /api/presets/ab/clear/{slot}

Clear A, B, or both slots.

**Path Parameters**:
- `slot` (string, required) - `A`, `B`, or `all`

**Response**:
```json
{
  "ok": true
}
```

**Status Codes**:
- `200 OK` - Slot(s) cleared
- `400 Bad Request` - Invalid slot

---

## Statistics

### GET /api/presets/stats

Get preset store statistics.

**Response**:
```json
{
  "total_presets": 42,
  "total_tags": 15,
  "disk_usage_bytes": 123456,
  "most_used_tags": [
    {"tag": "ambient", "count": 12},
    {"tag": "experimental", "count": 8}
  ]
}
```

**Status Codes**:
- `200 OK` - Success

---

## Collision Policies

When creating presets, collision policies determine what happens if a preset with the same name exists:

- **`prompt`** (default) - Return 409 error, let client decide
- **`overwrite`** - Replace existing preset
- **`new_copy`** - Create new preset with unique ID
- **`merge`** - Merge changes into existing preset

## Preset Schema

### Full Preset Object

```json
{
  "id": "unique-uuid",
  "name": "Preset Name",
  "schema_version": "1.0.0",
  "created_at": "2025-10-17T10:30:00Z",
  "modified_at": "2025-10-17T10:30:00Z",
  "notes": "Description",
  "tags": ["tag1", "tag2"],
  "channels": [
    {
      "id": 0,
      "enabled": true,
      "frequency": 440.0,
      "amplitude": 0.5,
      "phase": 0.0,
      "waveform": "sine",
      "modulation": {...}
    }
  ],
  "global": {
    "phi_depth": 0.618,
    "phi_phase": 3.14,
    "master_volume": 0.8
  }
}
```

### Validation Rules

- `name` - Required, 1-100 characters
- `schema_version` - Must be "1.0.0"
- `tags` - Optional array of strings
- `channels` - Optional array, max 16 channels
- `channels[].frequency` - 20.0 to 20000.0 Hz
- `channels[].amplitude` - 0.0 to 1.0
- `global.phi_depth` - 0.0 to 1.0
