# WebSocket API Reference

Complete reference for WebSocket streaming endpoints.

## Base URL

```
ws://localhost:8000
```

## WebSocket Endpoints

### ws://localhost:8000/ws/metrics

Real-time metrics streaming at 30 Hz.

**Protocol**: WebSocket

**Connection**:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/metrics');
```

**Message Format**:
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
      "phase": 0.0,
      "active": true
    }
  ]
}
```

**Message Rate**: ~30 messages per second (30 Hz)

**Python Example**:
```python
import asyncio
import websockets
import json

async def stream_metrics():
    async with websockets.connect('ws://localhost:8000/ws/metrics') as ws:
        while True:
            message = await ws.recv()
            data = json.loads(message)
            print(f"Frame {data['frame']}: ICI={data['ici']:.3f}")

asyncio.run(stream_metrics())
```

**JavaScript Example**:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/metrics');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`Frame ${data.frame}: ICI=${data.ici.toFixed(3)}`);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};
```

---

### ws://localhost:8000/ws/latency

Real-time latency diagnostics at 10 Hz.

**Protocol**: WebSocket

**Connection**:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/latency');
```

**Message Format**:
```json
{
  "timestamp": 1234567890.123,
  "total_latency_ms": 45.2,
  "hardware_latency_ms": 21.3,
  "software_latency_ms": 23.9,
  "buffer_latency_ms": 10.7,
  "jitter_ms": 2.3,
  "calibrated": true,
  "compensation_ms": 15.0
}
```

**Message Rate**: ~10 messages per second (10 Hz)

**Python Example**:
```python
import asyncio
import websockets
import json

async def stream_latency():
    async with websockets.connect('ws://localhost:8000/ws/latency') as ws:
        while True:
            message = await ws.recv()
            data = json.loads(message)
            print(f"Latency: {data['total_latency_ms']:.1f}ms")

asyncio.run(stream_latency())
```

---

### ws://localhost:8000/ws/events

Real-time event stream (state changes, critical events, etc).

**Protocol**: WebSocket

**Connection**:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/events');
```

**Message Format**:

**State Change Event**:
```json
{
  "type": "state_change",
  "timestamp": 1234567890.123,
  "from_state": "ambient",
  "to_state": "critical",
  "trigger": "ici_threshold",
  "confidence": 0.95
}
```

**Critical Event**:
```json
{
  "type": "critical_event",
  "timestamp": 1234567890.123,
  "criticality": 2.891,
  "duration_ms": 156.7,
  "peak_ici": 0.987
}
```

**Auto-Phi Adaptation**:
```json
{
  "type": "phi_adaptation",
  "timestamp": 1234567890.123,
  "old_depth": 0.618,
  "new_depth": 0.625,
  "old_phase": 3.14,
  "new_phase": 3.16,
  "reason": "criticality_optimization"
}
```

**Message Rate**: Variable (event-driven)

---

## Connection Lifecycle

### Connection Establishment

1. Client initiates WebSocket connection
2. Server accepts connection
3. Server immediately starts sending messages
4. No authentication required (currently)

### Connection Maintenance

- Server sends periodic messages (heartbeat not required)
- Client should handle reconnection on disconnect
- No explicit ping/pong required (handled by WebSocket protocol)

### Connection Termination

- Client closes connection: Server cleans up resources
- Server closes connection: Client should attempt reconnection

---

## Error Handling

### Connection Errors

If connection fails:
- Check server is running
- Verify WebSocket URL is correct
- Check firewall/proxy settings

### Message Parsing Errors

All messages are valid JSON. If parsing fails:
- Log the raw message
- Continue processing subsequent messages

### Reconnection Strategy

Recommended exponential backoff:

```python
import asyncio
import websockets

async def connect_with_retry(url, max_retries=5):
    retry_delay = 1.0

    for attempt in range(max_retries):
        try:
            async with websockets.connect(url) as ws:
                # Connection successful
                retry_delay = 1.0

                while True:
                    message = await ws.recv()
                    # Process message

        except websockets.exceptions.WebSocketException as e:
            print(f"Connection failed (attempt {attempt + 1}): {e}")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 30.0)
```

---

## Performance Considerations

### Message Rate

- **Metrics stream**: 30 Hz (30 messages/second)
- **Latency stream**: 10 Hz (10 messages/second)
- **Events stream**: Variable (event-driven)

### Bandwidth

- **Metrics**: ~30 KB/s (compressed)
- **Latency**: ~5 KB/s (compressed)
- **Events**: ~1 KB/s (average)

### Processing

- Process messages asynchronously
- Avoid blocking the message loop
- Use queues for heavy processing

**Python Example**:
```python
import asyncio
from queue import Queue
from threading import Thread

message_queue = Queue()

def process_messages():
    while True:
        message = message_queue.get()
        # Heavy processing here
        message_queue.task_done()

# Start processing thread
Thread(target=process_messages, daemon=True).start()

async def stream_metrics():
    async with websockets.connect('ws://localhost:8000/ws/metrics') as ws:
        while True:
            message = await ws.recv()
            # Quick enqueue
            message_queue.put(message)
```

---

## Client Libraries

### Python

**Required Package**:
```bash
pip install websockets
```

**Basic Client**:
```python
import asyncio
import websockets
import json

async def main():
    async with websockets.connect('ws://localhost:8000/ws/metrics') as ws:
        async for message in ws:
            data = json.loads(message)
            print(data)

asyncio.run(main())
```

### JavaScript (Browser)

**Native WebSocket API**:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/metrics');

ws.onopen = () => {
  console.log('Connected');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Disconnected');
};
```

### JavaScript (Node.js)

**Required Package**:
```bash
npm install ws
```

**Basic Client**:
```javascript
const WebSocket = require('ws');

const ws = new WebSocket('ws://localhost:8000/ws/metrics');

ws.on('open', () => {
  console.log('Connected');
});

ws.on('message', (data) => {
  const message = JSON.parse(data);
  console.log(message);
});

ws.on('error', (error) => {
  console.error('WebSocket error:', error);
});

ws.on('close', () => {
  console.log('Disconnected');
});
```

---

## Subscription Management

### Multiple Streams

You can connect to multiple streams simultaneously:

```python
import asyncio
import websockets

async def stream_metrics():
    async with websockets.connect('ws://localhost:8000/ws/metrics') as ws:
        async for message in ws:
            print(f"Metrics: {message}")

async def stream_latency():
    async with websockets.connect('ws://localhost:8000/ws/latency') as ws:
        async for message in ws:
            print(f"Latency: {message}")

async def main():
    await asyncio.gather(
        stream_metrics(),
        stream_latency()
    )

asyncio.run(main())
```

### Selective Filtering

Filter messages client-side:

```python
async def stream_critical_events():
    async with websockets.connect('ws://localhost:8000/ws/metrics') as ws:
        async for message in ws:
            data = json.loads(message)

            # Only process high criticality
            if data.get('criticality', 0) > 2.0:
                print(f"Critical event: {data}")
```

---

## Security Considerations

### Current State (Development)

- No authentication required
- No encryption (ws:// protocol)
- Intended for local/development use

### Production Recommendations

- Use WSS (WebSocket Secure) with TLS
- Implement token-based authentication
- Add rate limiting
- Use firewall rules to restrict access

---

## Debugging

### Connection Issues

Check connection with curl:
```bash
# Won't work directly, but use websocat:
websocat ws://localhost:8000/ws/metrics
```

### Message Inspection

Log all messages:
```python
async with websockets.connect('ws://localhost:8000/ws/metrics') as ws:
    async for message in ws:
        print(f"Raw message: {message}")
        data = json.loads(message)
        # Process...
```

### Performance Monitoring

Track message rate:
```python
import time

message_count = 0
start_time = time.time()

async with websockets.connect('ws://localhost:8000/ws/metrics') as ws:
    async for message in ws:
        message_count += 1

        if message_count % 100 == 0:
            elapsed = time.time() - start_time
            rate = message_count / elapsed
            print(f"Rate: {rate:.1f} messages/second")
```

---

## Best Practices

1. **Handle Disconnections**: Always implement reconnection logic
2. **Process Asynchronously**: Don't block the message loop
3. **Buffer Management**: Use queues for heavy processing
4. **Error Recovery**: Catch and log all exceptions
5. **Resource Cleanup**: Close connections properly
6. **Message Validation**: Validate all incoming data
7. **Rate Monitoring**: Track actual vs expected message rates
