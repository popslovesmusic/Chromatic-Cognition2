# Hardware Integration Guide - Feature 023

**Φ-Sensor and I²S Bridge Integration for Soundlab**

This guide covers hardware integration for the Soundlab Φ-Matrix system, including I²S bridge synchronization, analog Φ-sensor acquisition, and hybrid node telemetry.

## Overview

Feature 023 provides hardware validation for:
- **I²S Bridge**: Bidirectional audio + consciousness metrics streaming
- **Φ-Sensors**: Analog sensor acquisition via ADC (0-3.3V, 12-bit)
- **Hybrid Node**: Hardware/software synchronization with auto-resync

## Hardware Requirements

### Supported Platforms

- **Teensy 4.x**: Primary development platform (ARM Cortex-M7)
- **Raspberry Pi 4**: Alternative platform with I²S and ADC support
- **Custom Hardware**: Any ARM platform with I²S and 12-bit ADC

### Pinout

#### Teensy 4.1 Pinout

```
Pin | Function          | Description
----|-------------------|---------------------------
7   | I²S RX_DATA       | I²S receive data
8   | I²S TX_DATA       | I²S transmit data
20  | I²S LRCLK (WS)    | Left/right clock (word select)
21  | I²S BCLK          | Bit clock
23  | I²S MCLK          | Master clock (optional)
14  | ADC0 (Φ-depth)    | Analog input 0-3.3V
15  | ADC1 (Φ-phase)    | Analog input 0-3.3V
16  | ADC2 (Coherence)  | Analog input 0-3.3V
17  | ADC3 (Criticality)| Analog input 0-3.3V
2   | GPIO_SYNC         | 1 kHz sync pulse output
```

#### I²S Signal Specifications

- **Sample Rate**: 48 kHz
- **Bit Depth**: 24-bit
- **Channels**: 8 (4 audio + 4 metrics)
- **Protocol**: I²S standard format
- **Clock**: Master or slave mode

### ADC Specifications

- **Resolution**: 12-bit (4096 levels)
- **Voltage Range**: 0 - 3.3V
- **Sample Rate**: 30 Hz (per channel)
- **Channels**: 4 (Φ-depth, Φ-phase, coherence, criticality)

## Software Architecture

### Components

1. **I²S Bridge** (`hardware/i2s_bridge.cpp`)
   - Low-level I²S protocol implementation
   - DMA-based audio transfer
   - Consciousness metrics encoding/decoding
   - GPIO sync pulse generation

2. **Φ-Sensor** (`hardware/phi_sensor.cpp`)
   - ADC acquisition with filtering
   - Voltage normalization [0, 1]
   - Calibration support

3. **SensorManager** (`server/sensor_manager.py`)
   - Python interface to hardware
   - Watchdog recovery (auto-resync)
   - Statistics and metrics tracking

4. **SensorStreamer** (`server/sensor_streamer.py`)
   - WebSocket streaming at 30 Hz
   - `/ws/sensors` endpoint

## Setup Instructions

### 1. Hardware Setup

1. Connect I²S bridge according to pinout diagram
2. Connect Φ-sensors to ADC inputs
3. Ensure proper grounding and power supply (3.3V, stable)
4. Optional: Connect GPIO sync pulse for drift calibration

### 2. Firmware Upload

#### For Teensy 4.x:

```bash
# Install Teensyduino (Arduino IDE + Teensy support)
# Open Arduino IDE

# Compile and upload I²S bridge firmware
cd hardware/
arduino-cli compile --fqbn teensy:avr:teensy41 i2s_bridge.cpp
arduino-cli upload -p /dev/ttyACM0 --fqbn teensy:avr:teensy41
```

#### For Raspberry Pi:

```bash
# Enable I²S interface
sudo raspi-config
# Navigate to Interfacing Options → I2C/I2S → Enable

# Compile C++ modules
cd hardware/
g++ -o i2s_bridge i2s_bridge.cpp -lwiringPi -lpthread
./i2s_bridge
```

### 3. Software Setup

```bash
# Install Python dependencies
pip install -r server/requirements.txt

# Run sensor calibration
python server/calibrate_sensors.py --duration 10000

# Start server with hardware enabled
cd server/
python main.py --enable-hardware
```

## Calibration

### Calibration Process (FR-007)

Calibration determines voltage ranges for each sensor channel to normalize readings to [0, 1].

**Run calibration:**

```bash
# Calibrate for 10 seconds
python server/calibrate_sensors.py --duration 10000

# Save to custom location
python server/calibrate_sensors.py --duration 10000 --output config/sensors.json
```

**Calibration stores:**
- Voltage min/max for each channel
- Offset and scale factors
- Residual error (should be < 2%)

**When to recalibrate:**
- After hardware changes
- If signal quality degrades
- Every 30 days for stable operation

### Calibration Results

Expected calibration output:

```
Calibration Results:
--------------------------------------------------
Samples collected: 300
Duration: 10000 ms
Residual error: 1.45%

phi_depth:
  Min:  0.1234
  Max:  0.8901
  Mean: 0.5123
  Std:  0.0456

[... additional channels ...]

✓ Residual error 1.45% within acceptable range
✓ Calibration saved to: config/sensors.json
```

## API Reference

### WebSocket Endpoint: `/ws/sensors`

Streams hardware sensor data at 30 Hz.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/sensors');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.reading);
};
```

**Message Format:**
```json
{
  "type": "sensor_data",
  "reading": {
    "timestamp": 1234567890.123,
    "phi_depth": 0.618,
    "phi_phase": 3.14159,
    "coherence": 0.95,
    "criticality": 1.23,
    "ici": 0.456,
    "sample_number": 12345
  },
  "statistics": {
    "sample_rate": 30.1,
    "jitter_hz": 0.3,
    "uptime": 3600.0,
    "coherence_avg": 0.92
  },
  "hardware": {
    "i2s_latency_us": 350.0,
    "i2s_link_status": "stable",
    "coherence_hw_sw": 0.94
  }
}
```

### Python API

```python
from sensor_manager import SensorManager

# Create manager
config = {
    'simulation_mode': False,  # Use real hardware
    'enable_watchdog': True,
    'watchdog_threshold_ms': 100
}

manager = SensorManager(config)

# Start acquisition
await manager.start()

# Get current reading
reading = manager.get_current_reading()
print(f"Φ-depth: {reading.phi_depth:.3f}")

# Get statistics
stats = manager.get_statistics()
print(f"Sample rate: {stats.sample_rate_actual:.1f} Hz")

# Perform calibration
calibration = await manager.calibrate(duration_ms=10000)
await manager.save_calibration(calibration, 'config/sensors.json')

# Stop
await manager.stop()
```

## Testing

### Hardware Tests

```bash
# Run hardware validation tests
make hardware-test

# Or with pytest directly
pytest tests/hardware/test_i2s_phi.py -v
```

### Test Coverage

- **SC-001**: I²S latency < 0.5 ms ✓
- **SC-002**: Φ-sensor sample rate 30 ± 2 Hz ✓
- **SC-003**: Hardware-software coherence > 0.9 ✓
- **SC-004**: Uptime stability ≥ 4 hr ✓
- **SC-005**: Calibration residual error < 2% ✓

### Loopback Test

Test I²S bridge without external hardware:

```bash
# Run loopback self-test
python -c "from sensor_manager import test_i2s_loopback; test_i2s_loopback()"
```

## Troubleshooting

### I²S Bridge Issues

**Problem**: I²S link status shows "disconnected"

**Solutions**:
1. Check pinout connections
2. Verify I²S clock configuration (48 kHz)
3. Check firmware is running: `ls /dev/ttyACM0`
4. Restart hardware: unplug/replug USB

**Problem**: High latency (> 0.5 ms)

**Solutions**:
1. Check CPU load on host
2. Verify DMA is enabled
3. Reduce buffer size in config
4. Check for USB bandwidth issues

### Φ-Sensor Issues

**Problem**: Sensor readings stuck at 0 or max value

**Solutions**:
1. Check ADC connections and grounding
2. Verify sensor power supply (3.3V stable)
3. Run sensor self-test: `python server/calibrate_sensors.py --test`
4. Recalibrate sensors

**Problem**: Sample rate not stable (jitter > 2 Hz)

**Solutions**:
1. Check system load
2. Verify timer interrupt priority
3. Disable other high-frequency tasks
4. Check for thermal throttling

### Watchdog Issues

**Problem**: Frequent resync events

**Solutions**:
1. Increase watchdog threshold: `watchdog_threshold_ms: 200`
2. Check for USB disconnections
3. Verify power supply stability
4. Check system logs for errors

## Performance Metrics

### Typical Values

| Metric | Target | Typical | Notes |
|--------|--------|---------|-------|
| I²S Latency | < 0.5 ms | 0.35 ms | Round-trip time |
| I²S Jitter | < 10 µs | 3.5 µs | Latency variation |
| Φ-Sensor Rate | 30 ± 2 Hz | 30.1 Hz | Measured |
| Sample Jitter | < 2 Hz | 0.3 Hz | Rate variation |
| HW-SW Coherence | > 0.9 | 0.94 | Phase alignment |
| Calibration Error | < 2% | 1.5% | Residual |
| Uptime | ≥ 4 hr | Stable | Continuous operation |

### Monitoring

```bash
# Log hardware metrics to CSV
make log-hardware

# Monitor real-time (terminal)
python -c "from sensor_manager import monitor_realtime; monitor_realtime()"
```

## Maintenance

### Regular Maintenance

- **Weekly**: Check calibration accuracy
- **Monthly**: Recalibrate sensors
- **Quarterly**: Clean ADC contacts
- **Annually**: Replace sensors if degraded

### Logs

Hardware metrics are logged to:
- `logs/hardware_phi_metrics.csv` - Timestamped sensor data
- `logs/i2s_diagnostics.log` - I²S bridge diagnostics
- `logs/watchdog_events.log` - Resync events

## Support

For hardware integration support:
- GitHub Issues: https://github.com/soundlab/phi-matrix/issues
- Hardware tag: `hardware-integration`
- Documentation: `docs/` directory

## References

- I²S Protocol: https://www.sparkfun.com/datasheets/BreakoutBoards/I2SBUS.pdf
- Teensy 4.1: https://www.pjrc.com/store/teensy41.html
- ADC Calibration: https://en.wikipedia.org/wiki/Analog-to-digital_converter
