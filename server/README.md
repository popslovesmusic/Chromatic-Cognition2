# Soundlab Server

Real-time audio processing server with Φ-modulation, consciousness metrics, and latency compensation.

## Features

### Core Audio Processing
- **48kHz @ 512 samples** real-time audio pipeline
- **<10ms end-to-end latency** target
- **D-ASE ChromaticFieldProcessor** - 8-channel analog cellular engine with AVX2 optimization
- **8-channel → Stereo downmix** with multiple strategies (spatial, energy, linear, phi)

### Φ-Modulation (Golden Ratio)
- **Multi-source architecture**: Manual, Audio envelope, MIDI CC1, Sensor (HR/GSR/accel), Internal oscillator
- **100ms smooth crossfading** between sources
- **Envelope follower** with configurable attack/release (10-500ms)

### Consciousness Metrics Streaming
- **Real-time telemetry at ≥30Hz** via WebSocket
- Metrics: ICI, Phase Coherence, Spectral Centroid, Criticality, Consciousness Level
- **State classification**: AWAKE, DREAMING, DEEP_SLEEP, REM, CRITICAL, IDLE, TRANSITION
- Multi-client support (≥5 concurrent WebSocket connections)

### Latency Compensation
- **Impulse response calibration** with sounddevice.playrec
- **Continuous drift monitoring** and auto-correction (<2ms per 10min)
- **Synchronized timestamping** across audio, Φ, and metrics
- Real-time diagnostics via WebSocket (10 Hz)

### Preset System
- **Versioned JSON schema (v1)** with validation
- **A/B snapshot comparison** with <30ms glitch-free toggle
- **Collision resolution**: prompt, overwrite, new_copy, merge
- **Import/Export** with dry-run validation
- Comprehensive audit logging

### Logging & Telemetry
- **Dual-format logging**: CSV + JSONL with gzip compression
- **Session-based organization** with gap detection
- Logs: `/logs/audio_engine/`, `/logs/phi_modulator/`, `/logs/metrics/`, `/logs/presets/`, `/logs/latency/`

---

## Installation

### Prerequisites

- **Python 3.8+**
- **Audio I/O device** (microphone + speakers/headphones)
- **(Optional) Audio loopback** for latency calibration (cable or virtual device like VB-Audio Cable, BlackHole, etc.)

### Install Dependencies

```bash
cd server
pip install -r requirements.txt
```

### Build D-ASE Engine (C++ with Python bindings)

```bash
cd ../sase\ amp\ fixed
python setup.py build_ext --inplace
```

This compiles the AVX2-optimized C++ audio engine with pybind11 bindings.

---

## Quick Start

### 1. List Available Audio Devices

```bash
python main.py --list-devices
```

Example output:
```
Available Audio Devices
============================================================
  0 Built-in Microphone (input)
  1 Built-in Output (output)
  2 BlackHole 2ch (input/output)
  ...
```

### 2. Start Server (Manual Audio Control)

```bash
python main.py
```

Then use the API to start audio:
```bash
curl -X POST http://localhost:8000/api/audio/start
```

### 3. Start Server (Auto-Start Audio)

```bash
python main.py --auto-start-audio
```

### 4. Start with Latency Calibration

**IMPORTANT**: Connect audio loopback (output → input) before running!

```bash
python main.py --auto-start-audio --calibrate
```

### 5. Specify Audio Devices

```bash
python main.py --input-device 0 --output-device 1 --auto-start-audio
```

### 6. Custom Host/Port

```bash
python main.py --host 127.0.0.1 --port 9000
```

---

## API Reference

### Server Status

#### GET `/api/status`
Get server status and statistics.

**Response:**
```json
{
  "audio_running": true,
  "sample_rate": 48000,
  "buffer_size": 512,
  "callback_count": 12543,
  "latency_calibrated": true,
  "preset_loaded": true,
  "metrics_clients": 2,
  "latency_clients": 1
}
```

### Audio Control

#### POST `/api/audio/start?calibrate={bool}`
Start audio processing.

**Query Parameters:**
- `calibrate` (optional): Run latency calibration before starting

#### POST `/api/audio/stop`
Stop audio processing.

#### GET `/api/audio/performance`
Get real-time performance metrics (CPU load, processing time).

**Response:**
```json
{
  "callback_count": 12543,
  "buffer_duration_ms": 10.67,
  "processing_time_ms": {
    "current": 3.2,
    "average": 3.1,
    "min": 2.8,
    "max": 4.5,
    "std": 0.3
  },
  "cpu_load": {
    "current": 0.30,
    "average": 0.29,
    "peak": 0.42
  }
}
```

### Preset Management

#### GET `/api/presets?query={str}&tag={str}&limit={int}`
List presets with optional filtering.

#### GET `/api/presets/{id}`
Get full preset by ID.

#### POST `/api/presets`
Create/save preset.

**Body:**
```json
{
  "name": "My Preset",
  "tags": ["experimental", "spatial"],
  "engine": {
    "coupling_strength": 1.5,
    "frequencies": [0.5, 0.81, 1.31, 2.12, 3.43, 5.55, 8.97, 14.52],
    "amplitudes": [0.6, 0.55, 0.5, 0.45, 0.4, 0.35, 0.3, 0.25]
  },
  "phi": {
    "mode": "audio",
    "depth": 0.618
  },
  "downmix": {
    "strategy": "spatial"
  }
}
```

#### PUT `/api/presets/{id}`
Update existing preset.

#### DELETE `/api/presets/{id}`
Delete preset.

#### POST `/api/presets/export`
Export all presets as JSON bundle (downloadable file).

#### POST `/api/presets/import?dry_run={bool}&collision={policy}`
Import preset bundle from file.

**Query Parameters:**
- `dry_run`: Validate only, don't save
- `collision`: `prompt` | `overwrite` | `new_copy` | `merge`

### A/B Comparison

#### POST `/api/presets/ab/store/{slot}`
Store current preset in A or B slot.

**Path Parameters:**
- `slot`: `A` or `B`

#### GET `/api/presets/ab/get/{slot}`
Get preset from A or B slot.

#### POST `/api/presets/ab/toggle`
Toggle between A and B (glitch-free, <30ms guard time).

#### GET `/api/presets/ab/status`
Get A/B comparison status.

#### GET `/api/presets/ab/diff`
Get differences between A and B.

#### DELETE `/api/presets/ab/clear/{slot}`
Clear A, B, or both slots.

**Path Parameters:**
- `slot`: `A` | `B` | `all`

### Latency Compensation

#### GET `/api/latency/current`
Get current latency frame.

#### GET `/api/latency/stats`
Get comprehensive latency statistics.

#### POST `/api/latency/calibrate`
Trigger impulse response calibration (requires audio loopback).

#### POST `/api/latency/compensation/set?offset_ms={float}`
Manually set compensation offset (0-200 ms).

#### POST `/api/latency/compensation/adjust?delta_ms={float}`
Adjust compensation by delta (-50 to +50 ms).

#### POST `/api/latency/compensation/manual?offset_ms={float}`
Set manual user offset (-50 to +50 ms).

#### GET `/api/latency/drift`
Get drift monitoring statistics.

#### POST `/api/latency/drift/reset`
Reset drift monitor (clear history).

#### GET `/api/latency/aligned?tolerance_ms={float}`
Check if system is aligned within tolerance (default: 5.0 ms).

### WebSocket Streams

#### WS `/ws/metrics`
Real-time metrics stream at 30 Hz.

**Message Format:**
```json
{
  "timestamp": 1234567890.123,
  "ici": 0.45,
  "phase_coherence": 0.78,
  "spectral_centroid": 2500.0,
  "criticality": 0.62,
  "consciousness_level": 0.71,
  "state": "AWAKE",
  "phi_phase": 1.57,
  "phi_depth": 0.618,
  "phi_mode": "audio"
}
```

#### WS `/ws/latency`
Real-time latency telemetry at 10 Hz.

**Message Format:**
```json
{
  "timestamp": 1234567890.123,
  "hw_input_latency_ms": 5.2,
  "hw_output_latency_ms": 5.1,
  "engine_latency_ms": 10.7,
  "os_latency_ms": 1.5,
  "total_measured_ms": 22.5,
  "compensation_offset_ms": 22.5,
  "effective_latency_ms": 0.0,
  "drift_ms": 0.05,
  "drift_rate_ms_per_sec": 0.001,
  "calibrated": true,
  "calibration_quality": 0.95,
  "aligned_5ms": true
}
```

---

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Main Server (main.py)                  │
│                                                             │
│  ┌─────────────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │  AudioServer    │  │ PresetStore  │  │  FastAPI App  │ │
│  │                 │  │              │  │               │ │
│  │  ┌───────────┐  │  │  ┌────────┐  │  │  REST APIs    │ │
│  │  │ sounddev  │  │  │  │  JSON  │  │  │  WebSockets   │ │
│  │  │  Input    │  │  │  │  Files │  │  │  CORS         │ │
│  │  └─────┬─────┘  │  │  └────────┘  │  └───────────────┘ │
│  │        │        │  │              │                     │
│  │        v        │  │  ┌────────┐  │  ┌───────────────┐ │
│  │  ┌───────────┐  │  │  │   AB   │  │  │ MetricsStream │ │
│  │  │  D-ASE    │  │  │  │Snapshot│  │  │  (30 Hz)      │ │
│  │  │ Processor │  │  │  └────────┘  │  └───────────────┘ │
│  │  │(8-channel)│  │  │              │                     │
│  │  └─────┬─────┘  │  │              │  ┌───────────────┐ │
│  │        │        │  │              │  │LatencyStream  │ │
│  │        v        │  │              │  │  (10 Hz)      │ │
│  │  ┌───────────┐  │  │              │  └───────────────┘ │
│  │  │ Downmix   │  │  │              │                     │
│  │  │ (Stereo)  │  │  │              │                     │
│  │  └─────┬─────┘  │  │              │                     │
│  │        │        │  │              │                     │
│  │        v        │  │              │                     │
│  │  ┌───────────┐  │  │              │                     │
│  │  │ Latency   │  │  │              │                     │
│  │  │Compensate │  │  │              │                     │
│  │  └─────┬─────┘  │  │              │                     │
│  │        │        │  │              │                     │
│  │        v        │  │              │                     │
│  │  ┌───────────┐  │  │              │                     │
│  │  │ sounddev  │  │  │              │                     │
│  │  │  Output   │  │  │              │                     │
│  │  └───────────┘  │  │              │                     │
│  └─────────────────┘  └──────────────┘                     │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Logging (CSV + JSONL)                  │   │
│  │  /logs/metrics/  /logs/latency/  /logs/presets/    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### File Structure

```
server/
├── main.py                        # Main server entry point
├── audio_server.py                # Real-time audio pipeline
├── chromatic_field_processor.py   # D-ASE engine wrapper
├── phi_modulator.py               # Basic Φ-modulation
├── phi_sources.py                 # Multi-source Φ architecture
├── phi_modulator_controller.py    # Φ-source manager
├── downmix.py                     # 8-channel → stereo
├── latency_manager.py             # Calibration & compensation
├── latency_frame.py               # Latency data structure
├── latency_logger.py              # Latency logging
├── latency_api.py                 # Latency REST/WebSocket API
├── metrics_frame.py               # Metrics data structure
├── metrics_logger.py              # Metrics logging
├── metrics_streamer.py            # Metrics WebSocket broadcaster
├── preset_model.py                # Preset data model (schema v1)
├── preset_store.py                # Preset filesystem storage
├── ab_snapshot.py                 # A/B comparison manager
├── preset_api.py                  # Preset REST API
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

---

## Testing

### Component Self-Tests

Each module includes a self-test function. Run individually:

```bash
# Test latency frame
python latency_frame.py

# Test latency manager
python latency_manager.py

# Test audio server
python audio_server.py

# Test preset model
python preset_model.py

# Test preset store
python preset_store.py

# ... etc.
```

### Interactive Audio Test

```bash
python audio_server.py
```

Follow prompts to test:
1. Audio initialization
2. Real-time processing
3. Latency calibration (if loopback available)

---

## Troubleshooting

### Audio Device Issues

**Problem:** "Failed to start audio stream"

**Solutions:**
1. List devices: `python main.py --list-devices`
2. Specify devices explicitly: `--input-device 0 --output-device 1`
3. Check device availability (close other audio apps)
4. Try different buffer sizes (modify `BUFFER_SIZE` in `audio_server.py`)

### Latency Calibration Fails

**Problem:** "Invalid latency measurement" or "Low calibration quality"

**Solutions:**
1. Ensure audio loopback is properly connected:
   - **Cable**: Output jack → Input jack
   - **Virtual**: Install VB-Audio Cable (Windows), BlackHole (macOS), or equivalent
2. Check loopback volume (not muted, not too loud)
3. Reduce background noise
4. Try calibration multiple times

### High CPU Load

**Problem:** "WARNING: High CPU load"

**Solutions:**
1. Increase buffer size (trade-off: higher latency)
2. Reduce sample rate (48kHz → 44.1kHz)
3. Disable logging: `--no-logging`
4. Check D-ASE engine compilation (ensure AVX2 is enabled)

### WebSocket Connection Issues

**Problem:** "WebSocket connection failed"

**Solutions:**
1. Check CORS settings in `main.py`
2. Ensure server is running: `curl http://localhost:8000/api/status`
3. Check firewall settings
4. Use correct WebSocket URL: `ws://localhost:8000/ws/metrics`

---

## Performance Targets

| Metric | Target | Typical |
|--------|--------|---------|
| End-to-end latency | <10 ms | 5-8 ms |
| Processing time | <80% buffer | 25-35% |
| Metrics rate | ≥30 Hz | 30 Hz |
| Latency telemetry | ≥10 Hz | 10 Hz |
| Drift per 10 min | <2 ms | <1 ms |
| Alignment tolerance | ±5 ms | ±2 ms |

---

## Development

### Adding New Features

1. Create component module (e.g., `new_feature.py`)
2. Add self-test function
3. Integrate into `audio_server.py` or `main.py`
4. Add REST/WebSocket endpoints if needed
5. Update this README

### Logging

All components log to `../logs/`:
- `audio_engine/` - Audio processing events
- `phi_modulator/` - Φ-source switching, crossfades
- `metrics/` - Real-time metrics (CSV + JSONL)
- `latency/` - Latency telemetry and calibration
- `presets/` - Audit trail (CRUD operations)

Files are automatically compressed (gzip) on session close.

---

## License

(Add your license here)

---

## Support

For issues, questions, or contributions, please refer to the project repository.
