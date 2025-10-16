"""
Hybrid Analog-DSP Node Bridge - Feature 024
Python interface for hybrid analog/digital processing node

Communicates with hybrid node hardware via PySerial for:
- ADC/DAC configuration and control
- Real-time DSP metrics (ICI, coherence, spectral analysis)
- Analog modulation control (VCA, control voltages)
- Safety monitoring (voltage clamp, thermal)
- Calibration routines

Requirements:
- FR-005: Interface via PySerial or PyUSB
- FR-006: Integrate with metrics bus /ws/metrics
- FR-007: Safety monitoring and emergency shutdown
- FR-008: Calibration routine
- FR-009: Cluster Monitor integration

Success Criteria:
- SC-001: Total loop latency ≤2 ms
- SC-002: Modulation fidelity >95%
- SC-003: Stable operation 1 h, drift <0.5%
"""

import serial
import serial.tools.list_ports
import struct
import time
import threading
import json
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict
from enum import Enum


class HybridInterfaceType(Enum):
    """ADC/DAC interface type"""
    I2S = 0
    SPI = 1
    USB = 2


class HybridNodeMode(Enum):
    """Node operational mode"""
    ANALOG_ONLY = 0
    DSP_ONLY = 1
    HYBRID = 2
    CALIBRATION = 3


class HybridSafetyStatus(Enum):
    """Safety status"""
    OK = 0
    VOLTAGE_CLAMP = 1
    TEMP_WARNING = 2
    TEMP_CRITICAL = 3
    ADC_OVERLOAD = 4
    FAULT = 5


@dataclass
class AnalogMetrics:
    """Analog signal metrics (FR-002)"""
    rms_level: float          # RMS signal level
    peak_level: float         # Peak signal level
    dc_offset: float          # DC offset
    thd: float                # Total harmonic distortion (%)
    snr_db: float             # Signal-to-noise ratio (dB)
    is_overloaded: bool       # Overload flag


@dataclass
class DSPMetrics:
    """DSP analysis results (FR-003)"""
    ici: float                # Inter-Criticality Interval (ms)
    coherence: float          # Phase coherence [0, 1]
    criticality: float        # Criticality metric
    spectral_centroid: float  # Spectral centroid (Hz)
    spectral_flux: float      # Spectral flux
    zero_crossing_rate: float # Zero-crossing rate
    timestamp_us: int         # Microsecond timestamp


@dataclass
class ControlVoltage:
    """Control voltage output (FR-004)"""
    cv1: float                # Control voltage 1 (0-5V) - VCA depth
    cv2: float                # Control voltage 2 (0-5V) - VCA rate
    phi_phase: float          # Φ-phase modulation [0, 2π]
    phi_depth: float          # Φ-depth modulation [0, 1]


@dataclass
class SafetyTelemetry:
    """Safety monitoring telemetry (FR-007)"""
    status: str               # Safety status
    temperature: float        # Temperature (°C)
    voltage_out: List[float]  # Output voltages
    overload_count: int       # Overload event count
    clamp_count: int          # Voltage clamp count
    thermal_warning: bool     # Thermal warning flag


@dataclass
class CalibrationData:
    """Calibration data (FR-008)"""
    adc_gain: List[float]     # ADC gain correction per channel
    adc_offset: List[float]   # ADC offset correction per channel
    dac_gain: List[float]     # DAC gain correction per channel
    dac_offset: List[float]   # DAC offset correction per channel
    adc_latency_us: int       # ADC latency (µs)
    dsp_latency_us: int       # DSP latency (µs)
    dac_latency_us: int       # DAC latency (µs)
    total_latency_us: int     # Total loop latency (µs) (SC-001)
    calibration_timestamp: int # Calibration timestamp
    is_calibrated: bool       # Calibration valid


@dataclass
class NodeStatistics:
    """Node statistics (SC-003)"""
    frames_processed: int     # Total frames processed
    frames_dropped: int       # Dropped frames
    cpu_load: float           # CPU load (%)
    buffer_utilization: float # Buffer utilization (%)
    uptime_ms: int            # Uptime (ms)
    drift_ppm: float          # Clock drift (ppm)
    modulation_fidelity: float # Modulation fidelity (%) (SC-002)


class HybridBridge:
    """
    Hybrid Analog-DSP Node Bridge

    Provides Python API for communicating with hybrid processing nodes
    via serial/USB connection.
    """

    # Protocol commands
    CMD_INIT = 0x10
    CMD_START = 0x11
    CMD_STOP = 0x12
    CMD_GET_STATUS = 0x13
    CMD_GET_DSP_METRICS = 0x14
    CMD_GET_SAFETY = 0x15
    CMD_SET_PREAMP_GAIN = 0x16
    CMD_SET_CONTROL_VOLTAGE = 0x17
    CMD_CALIBRATE = 0x18
    CMD_LOAD_CALIBRATION = 0x19
    CMD_SAVE_CALIBRATION = 0x1A
    CMD_RESET_STATS = 0x1B
    CMD_SET_MODE = 0x1C
    CMD_EMERGENCY_SHUTDOWN = 0x1D
    CMD_GET_VERSION = 0x1E

    RESP_OK = 0x00
    RESP_ERROR = 0xFF

    def __init__(self, port: Optional[str] = None, baudrate: int = 115200, enable_logging: bool = True):
        """
        Initialize hybrid bridge

        Args:
            port: Serial port path (auto-detect if None)
            baudrate: Serial baud rate
            enable_logging: Enable diagnostic logging
        """
        self.port = port
        self.baudrate = baudrate
        self.enable_logging = enable_logging

        self.serial: Optional[serial.Serial] = None
        self.is_connected = False
        self.is_running = False

        # Background thread for metrics streaming
        self.metrics_thread: Optional[threading.Thread] = None
        self.metrics_lock = threading.Lock()
        self.metrics_callback = None

        # Current state
        self.current_mode = HybridNodeMode.HYBRID
        self.analog_metrics = None
        self.dsp_metrics = None
        self.safety_telemetry = None
        self.calibration = None
        self.statistics = None

        if self.enable_logging:
            print("[HybridBridge] Initialized")

    def list_devices(self) -> List[Dict]:
        """
        List available serial devices

        Returns:
            List of device info dictionaries
        """
        ports = serial.tools.list_ports.comports()
        devices = []

        for port in ports:
            devices.append({
                "port": port.device,
                "description": port.description,
                "hwid": port.hwid,
                "vid": port.vid,
                "pid": port.pid
            })

        return devices

    def connect(self) -> bool:
        """
        Connect to hybrid node device (FR-005)

        Returns:
            True if connected successfully
        """
        if self.is_connected:
            return True

        try:
            # Auto-detect port if not specified
            if self.port is None:
                devices = self.list_devices()

                # Look for Teensy, Arduino, or Raspberry Pi devices
                for device in devices:
                    desc = device['description'].lower()
                    if 'teensy' in desc or 'arduino' in desc or 'raspberry' in desc:
                        self.port = device['port']
                        if self.enable_logging:
                            print(f"[HybridBridge] Auto-detected: {device['description']} on {self.port}")
                        break

                if self.port is None:
                    if self.enable_logging:
                        print("[HybridBridge] No compatible device found")
                    return False

            # Open serial connection
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1.0,
                write_timeout=1.0
            )

            time.sleep(2.0)  # Wait for device reset

            self.is_connected = True

            if self.enable_logging:
                print(f"[HybridBridge] Connected to {self.port} @ {self.baudrate} baud")

            return True

        except Exception as e:
            if self.enable_logging:
                print(f"[HybridBridge] Connection error: {e}")
            return False

    def disconnect(self):
        """Disconnect from hybrid node"""
        if not self.is_connected:
            return

        self.stop()

        if self.serial:
            self.serial.close()
            self.serial = None

        self.is_connected = False

        if self.enable_logging:
            print("[HybridBridge] Disconnected")

    def start(self) -> bool:
        """
        Start hybrid node processing

        Returns:
            True if started successfully
        """
        if not self.is_connected or self.is_running:
            return False

        try:
            self._send_command(self.CMD_START)
            response = self._receive_response()

            if response == self.RESP_OK:
                self.is_running = True

                # Start metrics streaming thread
                self.metrics_thread = threading.Thread(target=self._metrics_loop, daemon=True)
                self.metrics_thread.start()

                if self.enable_logging:
                    print("[HybridBridge] Node started")
                return True
            else:
                if self.enable_logging:
                    print("[HybridBridge] Start command failed")
                return False

        except Exception as e:
            if self.enable_logging:
                print(f"[HybridBridge] Start error: {e}")
            return False

    def stop(self) -> bool:
        """
        Stop hybrid node processing

        Returns:
            True if stopped successfully
        """
        if not self.is_running:
            return False

        try:
            self._send_command(self.CMD_STOP)
            response = self._receive_response()

            self.is_running = False

            # Wait for metrics thread to finish
            if self.metrics_thread:
                self.metrics_thread.join(timeout=2.0)
                self.metrics_thread = None

            if self.enable_logging:
                print("[HybridBridge] Node stopped")

            return (response == self.RESP_OK)

        except Exception as e:
            if self.enable_logging:
                print(f"[HybridBridge] Stop error: {e}")
            return False

    def get_dsp_metrics(self) -> Dict:
        """
        Get DSP metrics (FR-003)

        Returns:
            DSP metrics dictionary
        """
        if not self.is_connected:
            return {}

        try:
            self._send_command(self.CMD_GET_DSP_METRICS)
            response = self._receive_response()

            if response == self.RESP_OK:
                # Receive DSP metrics packet (36 bytes)
                # Format: 6 floats + 1 uint32
                data = self.serial.read(28)
                if len(data) == 28:
                    unpacked = struct.unpack('<ffffffI', data)

                    self.dsp_metrics = DSPMetrics(
                        ici=unpacked[0],
                        coherence=unpacked[1],
                        criticality=unpacked[2],
                        spectral_centroid=unpacked[3],
                        spectral_flux=unpacked[4],
                        zero_crossing_rate=unpacked[5],
                        timestamp_us=unpacked[6]
                    )

                    return asdict(self.dsp_metrics)

            return {}

        except Exception as e:
            if self.enable_logging:
                print(f"[HybridBridge] Get DSP metrics error: {e}")
            return {}

    def get_safety(self) -> Dict:
        """
        Get safety telemetry (FR-007)

        Returns:
            Safety telemetry dictionary
        """
        if not self.is_connected:
            return {}

        try:
            self._send_command(self.CMD_GET_SAFETY)
            response = self._receive_response()

            if response == self.RESP_OK:
                # Receive safety telemetry (26 bytes)
                # Format: 1 uint8 + 1 float + 4 floats + 2 uint32 + 1 bool
                data = self.serial.read(26)
                if len(data) == 26:
                    unpacked = struct.unpack('<BfffffIIB', data)

                    self.safety_telemetry = SafetyTelemetry(
                        status=HybridSafetyStatus(unpacked[0]).name,
                        temperature=unpacked[1],
                        voltage_out=[unpacked[2], unpacked[3], unpacked[4], unpacked[5]],
                        overload_count=unpacked[6],
                        clamp_count=unpacked[7],
                        thermal_warning=bool(unpacked[8])
                    )

                    return asdict(self.safety_telemetry)

            return {}

        except Exception as e:
            if self.enable_logging:
                print(f"[HybridBridge] Get safety error: {e}")
            return {}

    def set_preamp_gain(self, gain: float) -> bool:
        """
        Set analog preamp gain (FR-002)

        Args:
            gain: Gain factor (linear, 1.0 = 0dB)

        Returns:
            True if set successfully
        """
        if not self.is_connected:
            return False

        try:
            # Pack gain as float
            packed = struct.pack('<f', gain)
            self._send_command(self.CMD_SET_PREAMP_GAIN, packed)
            response = self._receive_response()

            return (response == self.RESP_OK)

        except Exception as e:
            if self.enable_logging:
                print(f"[HybridBridge] Set preamp gain error: {e}")
            return False

    def set_control_voltage(self, cv: ControlVoltage) -> bool:
        """
        Set control voltage output (FR-004)

        Args:
            cv: Control voltage structure

        Returns:
            True if set successfully
        """
        if not self.is_connected:
            return False

        try:
            # Pack control voltage (4 floats)
            packed = struct.pack('<ffff', cv.cv1, cv.cv2, cv.phi_phase, cv.phi_depth)
            self._send_command(self.CMD_SET_CONTROL_VOLTAGE, packed)
            response = self._receive_response()

            return (response == self.RESP_OK)

        except Exception as e:
            if self.enable_logging:
                print(f"[HybridBridge] Set control voltage error: {e}")
            return False

    def calibrate(self) -> Optional[Dict]:
        """
        Run calibration routine (FR-008, SC-001)

        Returns:
            Calibration data dictionary if successful, None otherwise
        """
        if not self.is_connected:
            return None

        try:
            if self.enable_logging:
                print("[HybridBridge] Starting calibration (this may take 10-20 seconds)...")

            self._send_command(self.CMD_CALIBRATE)
            response = self._receive_response()

            if response == self.RESP_OK:
                # Receive calibration data (large packet)
                # Wait longer for calibration to complete
                time.sleep(5.0)

                # Read calibration data
                # This is a simplified version; actual implementation would
                # receive the full CalibrationData structure
                data = self.serial.read(64)  # Approximate size
                if len(data) >= 16:
                    # Parse basic calibration info
                    total_latency_us = struct.unpack('<I', data[0:4])[0]
                    is_calibrated = struct.unpack('<B', data[4:5])[0]

                    self.calibration = CalibrationData(
                        adc_gain=[1.0, 1.0],
                        adc_offset=[0.0, 0.0],
                        dac_gain=[1.0, 1.0, 1.0, 1.0],
                        dac_offset=[0.0, 0.0, 0.0, 0.0],
                        adc_latency_us=total_latency_us // 3,
                        dsp_latency_us=total_latency_us // 3,
                        dac_latency_us=total_latency_us // 3,
                        total_latency_us=total_latency_us,
                        calibration_timestamp=int(time.time()),
                        is_calibrated=bool(is_calibrated)
                    )

                    if self.enable_logging:
                        print(f"[HybridBridge] Calibration complete")
                        print(f"  Total latency: {total_latency_us} µs")
                        print(f"  SC-001 (≤2000 µs): {'PASS' if total_latency_us <= 2000 else 'FAIL'}")

                    return asdict(self.calibration)

            return None

        except Exception as e:
            if self.enable_logging:
                print(f"[HybridBridge] Calibration error: {e}")
            return None

    def get_statistics(self) -> Dict:
        """
        Get node statistics (SC-003)

        Returns:
            Statistics dictionary
        """
        if not self.is_connected:
            return {}

        try:
            self._send_command(self.CMD_GET_STATUS)
            response = self._receive_response()

            if response == self.RESP_OK:
                # Receive statistics (28 bytes)
                data = self.serial.read(28)
                if len(data) == 28:
                    unpacked = struct.unpack('<QQffffI', data)

                    self.statistics = NodeStatistics(
                        frames_processed=unpacked[0],
                        frames_dropped=unpacked[1],
                        cpu_load=unpacked[2],
                        buffer_utilization=unpacked[3],
                        uptime_ms=unpacked[6],
                        drift_ppm=unpacked[4],
                        modulation_fidelity=unpacked[5]
                    )

                    return asdict(self.statistics)

            return {}

        except Exception as e:
            if self.enable_logging:
                print(f"[HybridBridge] Get statistics error: {e}")
            return {}

    def reset_statistics(self) -> bool:
        """Reset statistics counters"""
        if not self.is_connected:
            return False

        try:
            self._send_command(self.CMD_RESET_STATS)
            response = self._receive_response()
            return (response == self.RESP_OK)

        except Exception as e:
            if self.enable_logging:
                print(f"[HybridBridge] Reset statistics error: {e}")
            return False

    def set_mode(self, mode: HybridNodeMode) -> bool:
        """Set operational mode"""
        if not self.is_connected:
            return False

        try:
            packed = struct.pack('<B', mode.value)
            self._send_command(self.CMD_SET_MODE, packed)
            response = self._receive_response()

            if response == self.RESP_OK:
                self.current_mode = mode
                return True

            return False

        except Exception as e:
            if self.enable_logging:
                print(f"[HybridBridge] Set mode error: {e}")
            return False

    def emergency_shutdown(self, reason: str) -> bool:
        """
        Emergency shutdown (FR-007)

        Args:
            reason: Reason for shutdown

        Returns:
            True if shutdown successful
        """
        if not self.is_connected:
            return False

        try:
            if self.enable_logging:
                print(f"[HybridBridge] EMERGENCY SHUTDOWN: {reason}")

            self._send_command(self.CMD_EMERGENCY_SHUTDOWN)
            response = self._receive_response()

            self.is_running = False

            return (response == self.RESP_OK)

        except Exception as e:
            if self.enable_logging:
                print(f"[HybridBridge] Emergency shutdown error: {e}")
            return False

    def get_version(self) -> str:
        """Get firmware version"""
        if not self.is_connected:
            return "Unknown"

        try:
            self._send_command(self.CMD_GET_VERSION)
            response = self._receive_response()

            if response == self.RESP_OK:
                version = self.serial.read_until(b'\x00', 32).decode('utf-8').strip('\x00')
                return version

            return "Unknown"

        except Exception as e:
            if self.enable_logging:
                print(f"[HybridBridge] Get version error: {e}")
            return "Unknown"

    def _send_command(self, cmd: int, data: bytes = b''):
        """Send command to hybrid node"""
        if not self.serial:
            raise RuntimeError("Serial not connected")

        # Command format: [0xAA] [CMD] [LEN_L] [LEN_H] [DATA...] [CHECKSUM]
        length = len(data)
        packet = bytes([0xAA, cmd, length & 0xFF, (length >> 8) & 0xFF]) + data

        # Calculate checksum (XOR)
        checksum = 0
        for b in packet:
            checksum ^= b

        packet += bytes([checksum])

        self.serial.write(packet)
        self.serial.flush()

    def _receive_response(self, timeout: float = 1.0) -> int:
        """Receive response from hybrid node"""
        if not self.serial:
            raise RuntimeError("Serial not connected")

        start_time = time.time()

        while (time.time() - start_time) < timeout:
            if self.serial.in_waiting >= 1:
                return ord(self.serial.read(1))

        return self.RESP_ERROR

    def _metrics_loop(self):
        """Background thread for metrics streaming (FR-006)"""
        while self.is_running:
            try:
                # Poll DSP metrics
                metrics = self.get_dsp_metrics()

                if metrics and self.metrics_callback:
                    self.metrics_callback(metrics)

                time.sleep(0.033)  # ~30 Hz update rate

            except Exception as e:
                if self.enable_logging:
                    print(f"[HybridBridge] Metrics loop error: {e}")
                time.sleep(0.1)


# Self-test
if __name__ == "__main__":
    print("=" * 60)
    print("Hybrid Analog-DSP Node Bridge Self-Test")
    print("=" * 60)

    # List available devices
    bridge = HybridBridge()
    devices = bridge.list_devices()

    print(f"\nAvailable devices: {len(devices)}")
    for i, device in enumerate(devices):
        print(f"  [{i}] {device['port']}: {device['description']}")

    if not devices:
        print("  No devices found")
        print("\nSkipping connection test (no hardware detected)")
    else:
        # Try to connect
        print(f"\nAttempting connection to {devices[0]['port']}...")
        if bridge.connect():
            print("  OK: Connected")

            # Get version
            version = bridge.get_version()
            print(f"  Firmware version: {version}")

            # Get statistics
            stats = bridge.get_statistics()
            print(f"  Statistics: {stats}")

            # Disconnect
            bridge.disconnect()
            print("  OK: Disconnected")
        else:
            print("  FAILED: Could not connect")

    print("\n" + "=" * 60)
    print("Self-Test Complete")
    print("=" * 60)
