# Technical Specification: Audio Engine Integration (Feature 001)

**Version:** 1.0
**Created:** 2025-10-14
**Status:** Implementation Ready
**Branch:** 001-audio-engine-integration

---

## 1. System Architecture

### 1.1 Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                 Browser (Soundlab Frontend)                  │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│ │ Web Audio API│  │ UI Controls  │  │ Visualizations   │   │
│ │ - Input Cap. │  │ - Φ-phase    │  │ - Metrics Feed   │   │
│ │ - Monitoring │  │ - Φ-depth    │  │ - Real-time      │   │
│ └──────┬───────┘  └──────┬───────┘  └────────▲─────────┘   │
└────────┼──────────────────┼───────────────────┼──────────────┘
         │                  │                   │
         │ Audio (WebRTC)  │ Controls (WS)     │ Metrics (WS)
         ▼                  ▼                   │
┌─────────────────────────────────────────────────────────────┐
│              Python Server (FastAPI + WebSocket)             │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│ │ sounddevice  │  │ PhiModulator │  │ MetricsStreamer  │   │
│ │ - 48kHz I/O  │  │ - Golden Φ   │  │ - 30+ Hz         │   │
│ │ - 512 blocks │  │ - Modulation │  │ - JSON stream    │   │
│ └──────┬───────┘  └──────┬───────┘  └────────▲─────────┘   │
│        │                  │                   │              │
│        ▼                  ▼                   │              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │       ChromaticFieldProcessor (Python Wrapper)          │ │
│ │ ┌─────────────────────────────────────────────────────┐ │ │
│ │ │  AnalogCellularEngineAVX2 (C++/pybind11)           │ │ │
│ │ │  - 64 oscillators (8×8 channels)                   │ │ │
│ │ │  - AVX2 + OpenMP                                   │ │ │
│ │ │  - processBlock(float32[512])                      │ │ │
│ │ └─────────────────────────────────────────────────────┘ │ │
│ └───────────────────────────────────┬─────────────────────┘ │
│                                     │ Metrics Calculation   │
│                                     └───────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Component Specifications

### 2.1 ChromaticFieldProcessor (Python Wrapper)

**Purpose:** Bridge between audio I/O and C++ engine with Φ-modulation

**Module:** `server/chromatic_field_processor.py`

**Class Definition:**
```python
class ChromaticFieldProcessor:
    def __init__(self, num_channels=8, sample_rate=48000, block_size=512):
        """
        Initialize processor with 8×8 channel configuration

        Args:
            num_channels: Number of channels per dimension (8 = 64 total)
            sample_rate: Audio sample rate (48kHz)
            block_size: Processing block size (512 samples)
        """

    def processBlock(self, input_block: np.ndarray,
                     phi_phase: float,
                     phi_depth: float) -> np.ndarray:
        """
        Process single audio block through D-ASE engine

        Args:
            input_block: float32[512] mono input
            phi_phase: Φ-phase offset [0.0, 2π]
            phi_depth: Φ-modulation depth [0.0, 1.0]

        Returns:
            float32[8, 512] multi-channel output
        """

    def getMetrics(self) -> dict:
        """
        Calculate and return current metrics

        Returns:
            {
                'ici': float,              # Inter-Channel Interference
                'phase_coherence': float,  # Phase alignment across channels
                'spectral_centroid': float,# Center of spectral mass (Hz)
                'consciousness_level': float # Composite metric [0-1]
            }
        """

    def reset(self):
        """Reset all internal state and integrators"""
```

**Metrics Calculation Algorithms:**

- **ICI (Inter-Channel Interference):**
  ```python
  ici = np.mean([
      np.corrcoef(output[i], output[j])[0,1]
      for i in range(8) for j in range(i+1, 8)
  ])
  ```

- **Phase Coherence:**
  ```python
  phases = np.angle(scipy.signal.hilbert(output, axis=1))
  phase_coherence = 1.0 - np.std(phases) / np.pi
  ```

- **Spectral Centroid:**
  ```python
  spectrum = np.abs(np.fft.rfft(output, axis=1))
  freqs = np.fft.rfftfreq(block_size, 1/sample_rate)
  centroid = np.sum(spectrum * freqs) / np.sum(spectrum)
  ```

- **Consciousness Level:**
  ```python
  # Composite: balance of coherence, diversity, and centroid position
  consciousness = (
      0.4 * phase_coherence +
      0.3 * (1.0 - ici) +
      0.3 * (centroid / (sample_rate/2))
  )
  ```

---

### 2.2 PhiModulator (Φ-Modulation System)

**Purpose:** Generate golden-ratio modulation signals

**Module:** `server/phi_modulator.py`

**Class Definition:**
```python
class PhiModulator:
    PHI = 1.618033988749895  # Golden ratio
    PHI_INV = 0.618033988749895  # 1/Φ

    def __init__(self, sample_rate=48000):
        """
        Initialize Φ-modulator

        Args:
            sample_rate: Audio sample rate for time-based calculations
        """
        self.sample_rate = sample_rate
        self.phase_accumulator = 0.0

    def generateModulation(self, phi_phase: float, phi_depth: float,
                          num_samples: int) -> np.ndarray:
        """
        Generate Φ-modulated control signal

        Args:
            phi_phase: Phase offset [0, 2π]
            phi_depth: Modulation depth [0, 1]
            num_samples: Number of samples to generate

        Returns:
            float32[num_samples] modulation envelope

        Algorithm:
            modulation[n] = depth * sin(2π * Φ^-1 * n/SR + phase)
        """

    def applyModulation(self, signal: np.ndarray,
                       modulation: np.ndarray) -> np.ndarray:
        """
        Apply modulation to multi-channel signal

        Each channel gets Φ-rotated phase:
            channel[i] = signal[i] * modulation[n + i*PHI]
        """
```

**Modulation Characteristics:**
- Frequency: `f_mod = sample_rate / Φ ≈ 29,665 Hz` (for 48kHz)
- Depth range: 0 (no modulation) to 1 (full amplitude modulation)
- Phase offset: allows synchronized control across multiple processors

---

### 2.3 Audio Server (sounddevice Integration)

**Purpose:** Real-time audio I/O with low-latency processing

**Module:** `server/audio_server.py`

**Class Definition:**
```python
class AudioServer:
    def __init__(self, device_id=None, sample_rate=48000, block_size=512):
        """
        Initialize audio I/O system

        Args:
            device_id: Audio device ID (None = default)
            sample_rate: 48kHz (spec requirement)
            block_size: 512 samples (spec requirement)
        """

    def audioCallback(self, indata, outdata, frames, time, status):
        """
        Real-time audio callback (CRITICAL PATH)

        Processing order:
            1. Read input block (frames must == 512)
            2. Apply Φ-modulation via PhiModulator
            3. Process through ChromaticFieldProcessor
            4. Downmix 8 channels → stereo
            5. Write to outdata
            6. Queue metrics for WebSocket stream

        Latency target: < 10ms total
        """

    def start(self):
        """Start audio stream"""

    def stop(self):
        """Stop and cleanup audio stream"""

    def getDeviceList(self) -> list:
        """Return list of available audio devices"""
```

**Buffer Management:**
```python
class AdaptiveBuffer:
    """Double-buffer queue with dynamic sizing"""
    def __init__(self, initial_size=512, max_size=2048):
        self.buffer_a = np.zeros(initial_size, dtype=np.float32)
        self.buffer_b = np.zeros(initial_size, dtype=np.float32)
        self.current = 'a'
        self.underrun_count = 0
        self.overrun_count = 0

    def adapt(self):
        """Adjust buffer size based on underrun/overrun statistics"""
        if self.underrun_count > 10:
            self.increase_size()
        elif self.overrun_count > 10:
            self.decrease_size()
```

---

### 2.4 WebSocket Server (FastAPI)

**Purpose:** Bi-directional communication for control and metrics

**Module:** `server/websocket_server.py`

**Endpoints:**

**1. Control Endpoint:** `/ws/control`
```json
// Client → Server (Parameter Updates)
{
    "type": "param_update",
    "phi_phase": 1.57,      // radians [0, 2π]
    "phi_depth": 0.75,      // normalized [0, 1]
    "timestamp": 1697234567890
}

// Server → Client (Acknowledgment)
{
    "type": "param_ack",
    "phi_phase": 1.57,
    "phi_depth": 0.75,
    "latency_ms": 2.3
}
```

**2. Metrics Endpoint:** `/ws/metrics`
```json
// Server → Client (Streaming at 30+ Hz)
{
    "type": "metrics_update",
    "timestamp": 1697234567890,
    "metrics": {
        "ici": 0.234,
        "phase_coherence": 0.876,
        "spectral_centroid": 2345.67,
        "consciousness_level": 0.723
    },
    "performance": {
        "latency_ms": 8.2,
        "cpu_usage": 0.47,
        "buffer_underruns": 0
    }
}
```

**Server Class:**
```python
class WebSocketServer:
    def __init__(self, host="0.0.0.0", port=8765):
        """Initialize FastAPI WebSocket server"""

    async def handleControl(self, websocket: WebSocket):
        """Handle /ws/control connection"""

    async def handleMetrics(self, websocket: WebSocket):
        """Handle /ws/metrics connection (streaming)"""

    async def metricsStreamLoop(self):
        """Background task: stream metrics at 30Hz"""
        while True:
            metrics = processor.getMetrics()
            await self.broadcast(metrics)
            await asyncio.sleep(1/30)  # 30 Hz
```

---

### 2.5 Multi-Channel Downmix

**Purpose:** Convert 8-channel D-ASE output to stereo for browser

**Module:** `server/downmix.py`

**Algorithm:**
```python
def downmix_8ch_to_stereo(multi_channel: np.ndarray) -> np.ndarray:
    """
    Downmix 8 channels to stereo with spatial panning

    Args:
        multi_channel: float32[8, 512] input

    Returns:
        float32[2, 512] stereo output

    Channel mapping (based on spatial positions):
        L: 0.8*ch0 + 0.6*ch1 + 0.4*ch2 + 0.2*ch3
        R: 0.2*ch4 + 0.4*ch5 + 0.6*ch6 + 0.8*ch7

    Normalization: divide by 2.0 to prevent clipping
    """
    left = (0.8*multi_channel[0] + 0.6*multi_channel[1] +
            0.4*multi_channel[2] + 0.2*multi_channel[3]) / 2.0
    right = (0.2*multi_channel[4] + 0.4*multi_channel[5] +
             0.6*multi_channel[6] + 0.8*multi_channel[7]) / 2.0
    return np.vstack([left, right])
```

---

## 3. Frontend Integration

### 3.1 UI Controls (soundlab_v2.html)

**New Panel:** "Φ-Modulation Control"

```html
<div class="phi-control-panel">
  <h3>⚡ Φ-Modulation (Golden Ratio Processing)</h3>

  <div class="control-group">
    <label>Φ-Phase</label>
    <div class="knob" data-param="phi_phase" data-min="0" data-max="6.28318"></div>
    <span id="phiPhaseValue">0.00 rad</span>
  </div>

  <div class="control-group">
    <label>Φ-Depth</label>
    <div class="knob" data-param="phi_depth" data-min="0" data-max="1"></div>
    <span id="phiDepthValue">0.00</span>
  </div>

  <div class="connection-status">
    <span id="daseStatus">⚪ Disconnected</span>
    <span id="latencyDisplay">-- ms</span>
  </div>
</div>
```

### 3.2 Metrics Visualization

**New Canvas:** Real-time metrics display

```html
<canvas id="metricsCanvas" width="800" height="300"></canvas>
```

**Display Layout:**
```
┌────────────────────────────────────────────┐
│  ICI: 0.234          [████░░░░░░] 23.4%   │
│  Coherence: 0.876    [████████░░] 87.6%   │
│  Centroid: 2.3kHz    [████░░░░░░] 2300Hz  │
│  Consciousness: 0.72 [███████░░░] 72.0%   │
│                                            │
│  ┌──────────────────────────────────────┐ │
│  │  [Time-series graph of metrics]      │ │
│  │  Last 10 seconds @ 30 Hz             │ │
│  └──────────────────────────────────────┘ │
└────────────────────────────────────────────┘
```

### 3.3 WebSocket Client (JavaScript)

**Module:** `js/soundlab-dase-client.js`

```javascript
class DASEClient {
  constructor() {
    this.controlWS = null;
    this.metricsWS = null;
    this.connected = false;
  }

  connect(serverURL = 'ws://localhost:8765') {
    // Connect to /ws/control
    this.controlWS = new WebSocket(`${serverURL}/ws/control`);

    // Connect to /ws/metrics
    this.metricsWS = new WebSocket(`${serverURL}/ws/metrics`);
    this.metricsWS.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.updateMetricsDisplay(data.metrics);
    };
  }

  sendParameters(phiPhase, phiDepth) {
    if (!this.controlWS) return;
    this.controlWS.send(JSON.stringify({
      type: 'param_update',
      phi_phase: phiPhase,
      phi_depth: phiDepth,
      timestamp: Date.now()
    }));
  }

  updateMetricsDisplay(metrics) {
    document.getElementById('iciValue').textContent =
      metrics.ici.toFixed(3);
    document.getElementById('coherenceValue').textContent =
      metrics.phase_coherence.toFixed(3);
    // ... update visualization
  }
}
```

---

## 4. Performance Requirements

### 4.1 Latency Budget (Total: < 10ms)

| Component | Target | Max |
|-----------|--------|-----|
| sounddevice input buffer | 2ms | 3ms |
| Φ-modulation calculation | 0.5ms | 1ms |
| ChromaticFieldProcessor.processBlock() | 4ms | 6ms |
| Downmix to stereo | 0.5ms | 1ms |
| sounddevice output buffer | 2ms | 3ms |
| **Total** | **9ms** | **14ms** |

### 4.2 CPU Usage Targets

- **Idle:** < 5%
- **Processing:** < 50% (8 cores assumed)
- **Peak (parameter change):** < 70%

### 4.3 Memory Usage

- **Base (engine init):** ~100 MB
- **Processing buffers:** ~10 MB
- **Metrics history (10s @ 30Hz):** ~1 MB
- **Total:** ~120 MB

---

## 5. Testing Strategy

### 5.1 Unit Tests

**File:** `tests/test_chromatic_field_processor.py`
```python
def test_process_block_latency():
    """Verify processBlock() completes in < 6ms"""
    processor = ChromaticFieldProcessor()
    input_block = np.random.randn(512).astype(np.float32)

    start = time.perf_counter()
    output = processor.processBlock(input_block, 0.0, 0.5)
    elapsed = time.perf_counter() - start

    assert elapsed < 0.006, f"Latency {elapsed*1000:.1f}ms exceeds 6ms"
    assert output.shape == (8, 512)
```

### 5.2 Integration Tests

**File:** `tests/test_audio_pipeline.py`
```python
def test_end_to_end_latency():
    """Measure total pipeline latency"""
    # Simulate audio callback with timing
    # Verify < 10ms total

def test_metrics_stream_rate():
    """Verify metrics stream at ≥30 Hz"""
    # Connect to /ws/metrics
    # Count messages over 10 seconds
    # Assert count >= 300
```

### 5.3 Acceptance Tests (User Stories)

**User Story 1:** Real-time audio processing
```python
def test_continuous_audio_flow():
    """Run for 60 seconds, verify no dropouts"""
    server = AudioServer()
    server.start()
    time.sleep(60)
    assert server.underrun_count == 0
    assert server.overrun_count == 0
```

**User Story 2:** Φ-modulation control
```python
def test_phi_parameter_response():
    """Verify parameter changes within 100ms"""
    client = DASEClient()
    client.connect()

    start = time.time()
    client.sendParameters(phi_phase=1.57, phi_depth=0.8)
    # Wait for acknowledgment
    ack = client.waitForAck(timeout=0.2)
    elapsed = time.time() - start

    assert elapsed < 0.1, "Response too slow"
    assert ack['phi_phase'] == 1.57
```

**User Story 3:** Metrics feedback
```python
def test_metrics_streaming():
    """Verify continuous metrics at 30+ Hz"""
    client = DASEClient()
    client.connect()

    metrics_received = []
    def collect(msg):
        metrics_received.append(msg)

    client.on_metrics = collect
    time.sleep(1.0)

    assert len(metrics_received) >= 30, "Insufficient update rate"
```

---

## 6. File Structure

```
soundlab/
├── server/
│   ├── __init__.py
│   ├── chromatic_field_processor.py  # NEW: Wrapper around dase_engine
│   ├── phi_modulator.py              # NEW: Φ-modulation generator
│   ├── audio_server.py               # NEW: sounddevice integration
│   ├── websocket_server.py           # NEW: FastAPI WebSocket server
│   ├── downmix.py                    # NEW: 8ch → stereo
│   ├── metrics_calculator.py         # NEW: ICI, coherence, etc.
│   ├── main.py                       # NEW: Server entry point
│   └── requirements.txt              # NEW: Dependencies
│
├── sase amp fixed/                   # EXISTING: D-ASE C++ engine
│   ├── analog_universal_node_engine_avx2.cpp
│   ├── analog_universal_node_engine_avx2.h
│   ├── python_bindings.cpp
│   ├── setup.py
│   └── dase_engine.pyd              # Compiled module
│
├── js/
│   ├── soundlab-main.js             # EXISTING
│   ├── soundlab-audio-core.js       # EXISTING
│   ├── soundlab-dase-client.js      # NEW: WebSocket client
│   └── soundlab-metrics-viz.js      # NEW: Metrics visualization
│
├── partials/
│   └── phi-controls.html            # NEW: Φ-modulation UI panel
│
├── tests/
│   ├── test_chromatic_field_processor.py  # NEW
│   ├── test_phi_modulator.py              # NEW
│   ├── test_audio_server.py               # NEW
│   ├── test_websocket_server.py           # NEW
│   └── test_integration.py                # NEW
│
├── logs/
│   └── audio_engine/                # NEW: Session logs
│       ├── session_20251014_120000.log
│       └── metrics_20251014_120000.csv
│
└── docs/
    ├── technical-spec-001-audio-engine-integration.md  # THIS FILE
    └── api-reference.md             # NEW: API documentation
```

---

## 7. Dependencies

**Python Requirements (server/requirements.txt):**
```
fastapi==0.104.1
uvicorn==0.24.0
websockets==12.0
sounddevice==0.4.6
numpy==1.24.3
scipy==1.11.3
pybind11==2.11.1
```

**System Requirements:**
- Python 3.9+
- C++ compiler with AVX2 support
- FFTW3 library
- PortAudio (for sounddevice)

---

## 8. Success Criteria Verification

| ID | Criterion | Verification Method |
|----|-----------|---------------------|
| SC-001 | Audio routing at 48kHz, <10ms latency | `test_end_to_end_latency()` |
| SC-002 | Φ-controls respond within 100ms | `test_phi_parameter_response()` |
| SC-003 | Metrics stream at ≥30 fps for 60s | `test_metrics_streaming()` |
| SC-004 | 8×8 channels (64 oscillators) at <50% CPU | Manual profiling with `htop` |
| SC-005 | No audio artifacts during start/stop | `test_graceful_shutdown()` |
| SC-006 | All tests pass via pytest | `pytest tests/ -v` |

---

## 9. Implementation Checklist

**Phase 1: Core Audio Pipeline**
- [ ] Create ChromaticFieldProcessor wrapper
- [ ] Implement PhiModulator class
- [ ] Build AudioServer with sounddevice
- [ ] Test audio callback latency

**Phase 2: WebSocket Bridge**
- [ ] Implement FastAPI WebSocket server
- [ ] Add /ws/control endpoint
- [ ] Add /ws/metrics endpoint
- [ ] Implement downmix function

**Phase 3: Frontend Integration**
- [ ] Add Φ-phase/Φ-depth UI controls
- [ ] Create WebSocket client (JS)
- [ ] Build metrics visualization
- [ ] Add device selection dropdown

**Phase 4: Testing & Polish**
- [ ] Write unit tests (pytest)
- [ ] Write integration tests
- [ ] Measure and optimize latency
- [ ] Add session logging
- [ ] Create API documentation

---

**End of Technical Specification**
