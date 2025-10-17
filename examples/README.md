# Soundlab SDK Examples

This directory contains example scripts demonstrating how to use the Soundlab Φ-Matrix API and SDK.

## Prerequisites

```bash
pip install requests websockets asyncio
```

## Quick Start

1. **Start the server**: `cd server && python main.py`
2. **Run an example**: `python examples/01_basic_client.py`

## Examples

### 01_basic_client.py
Basic REST API client demonstrating:
- Health checks
- Version info
- Metrics endpoint
- Dashboard state

**Run**: `python examples/01_basic_client.py`

### 02_preset_management.py
Complete preset management:
- List/search presets
- Create/update/delete presets
- Import/export bundles
- A/B comparison

**Run**: `python examples/02_preset_management.py`

### 03_websocket_streaming.py
Real-time metrics streaming via WebSocket:
- Connect to metrics stream
- Process real-time metrics (30 Hz)
- Monitor Φ-depth, criticality, ICI
- Handle state changes

**Run**: `python examples/03_websocket_streaming.py`

### 04_session_recording.py
Session recording and playback:
- Start/stop recording
- Save session data
- Replay sessions
- Export metrics

**Run**: `python examples/04_session_recording.py`

### 05_performance_monitoring.py
Performance monitoring and diagnostics:
- Monitor FPS and latency
- Track CPU/memory usage
- Analyze performance metrics
- Generate reports

**Run**: `python examples/05_performance_monitoring.py`

## Environment Variables

```bash
# Server URL (default: http://localhost:8000)
export SOUNDLAB_API_URL=http://localhost:8000

# WebSocket URL (default: ws://localhost:8000)
export SOUNDLAB_WS_URL=ws://localhost:8000

# Enable debug logging
export SOUNDLAB_DEBUG=1
```

## Common Patterns

### Synchronous REST API Calls

```python
import requests

response = requests.get('http://localhost:8000/healthz')
print(response.json())
```

### Asynchronous WebSocket Streaming

```python
import asyncio
import websockets

async def stream_metrics():
    async with websockets.connect('ws://localhost:8000/ws/metrics') as ws:
        while True:
            data = await ws.recv()
            print(data)

asyncio.run(stream_metrics())
```

### Error Handling

```python
import requests

try:
    response = requests.get('http://localhost:8000/api/presets/123')
    response.raise_for_status()
    preset = response.json()
except requests.HTTPError as e:
    if e.response.status_code == 404:
        print("Preset not found")
    else:
        print(f"Error: {e}")
```

## API Reference

Full API documentation: `docs/api_reference/`

Interactive API docs: http://localhost:8000/docs

## Troubleshooting

### Connection Refused

Server not running. Start with: `cd server && python main.py`

### WebSocket Connection Failed

Check firewall settings and ensure port 8000 is accessible.

### Import Errors

Install dependencies: `pip install -r server/requirements.txt`

## Next Steps

- Read the full API reference: `docs/api_reference/`
- Check the architecture guide: `docs/ARCHITECTURE.md`
- Explore advanced features in the dashboard
