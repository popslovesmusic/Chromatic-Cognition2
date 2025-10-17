"""
Enhanced PhiModulator Controller - Multi-Source Φ Modulation Manager

Manages multiple Φ-modulation sources with smooth crossfading and mode switching.
Integrates Manual, Audio, MIDI, Sensor, and Internal sources.
"""

import numpy as np
from typing import Optional, Dict, Literal
import time
import os
from datetime import datetime

from .phi_sources import (
    PhiSource, PhiState,
    ManualSource, AudioEnvelopeSource, InternalOscillatorSource,
    MIDISource, SensorSource
)


PhiMode = Literal["manual", "audio", "midi", "sensor", "internal"]


class PhiModulatorController:
    """
    Enhanced Φ-Modulation Controller

    Features:
    - Multi-source management (5 modes)
    - Smooth crossfading between sources (<100ms)
    - Automatic fallback to internal oscillator
    - Logging and state monitoring
    - WebSocket-ready state export
    """

    CROSSFADE_TIME = 0.1  # 100ms crossfade

    def __init__(self,
                 sample_rate: int = 48000,
                 block_size: int = 512,
                 log_dir: Optional[str] = None):
        """
        Initialize PhiModulator controller

        Args:
            sample_rate: Audio sample rate (48000 Hz)
            block_size: Audio block size (512 samples)
            log_dir: Directory for logging (None = logs/phi_modulator/)
        """
        self.sample_rate = sample_rate
        self.block_size = block_size

        # Initialize all sources
        self.sources: Dict[PhiMode, PhiSource] = {
            "manual": ManualSource(sample_rate),
            "audio": AudioEnvelopeSource(sample_rate, attack_ms=20, release_ms=100),
            "midi": MIDISource(sample_rate),
            "sensor": SensorSource(sample_rate),
            "internal": InternalOscillatorSource(sample_rate, frequency=0.1)
        }

        # Active mode and crossfading
        self.current_mode: PhiMode = "internal"
        self.previous_mode: Optional[PhiMode] = None
        self.crossfade_progress = 1.0  # 0.0 = prev, 1.0 = current
        self.crossfade_start_time = 0.0

        # Activate internal source by default
        self.sources["internal"].activate()

        # State tracking
        self.current_state = PhiState(source="internal")
        self.state_history = []
        self.max_history = 1000

        # Logging
        if log_dir is None:
            log_dir = os.path.join(os.path.dirname(__file__), "..", "logs", "phi_modulator")
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)

        self.log_file = None
        self._init_logging()

        print(f"[PhiModulatorController] Initialized @ {sample_rate}Hz, block={block_size}")
        print(f"[PhiModulatorController] Default mode: {self.current_mode}")

    def _init_logging(self):
        """Initialize logging to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = os.path.join(self.log_dir, f"phi_session_{timestamp}.log")

        try:
            self.log_file = open(log_path, 'w')
            self.log_file.write(f"# Φ-Modulator Session Log\n")
            self.log_file.write(f"# Started: {datetime.now().isoformat()}\n")
            self.log_file.write(f"# Sample Rate: {self.sample_rate} Hz\n")
            self.log_file.write(f"# Block Size: {self.block_size} samples\n")
            self.log_file.write("timestamp,mode,phase,depth,frequency\n")
            self.log_file.flush()
            print(f"[PhiModulatorController] Logging to {log_path}")
        except Exception as e:
            print(f"[PhiModulatorController] Warning: Could not init logging: {e}")
            self.log_file = None

    def _log_state(self, state: PhiState):
        """Log current state to file"""
        if self.log_file and not self.log_file.closed:
            try:
                self.log_file.write(
                    f"{state.timestamp:.3f},{state.source},"
                    f"{state.phase:.4f},{state.depth:.4f},{state.frequency:.4f}\n"
                )
            except Exception as e:
                print(f"[PhiModulatorController] Warning: Logging failed: {e}")

    def set_mode(self, mode: PhiMode):
        """
        Switch to a new Φ-modulation mode

        Initiates crossfade from current to new mode

        Args:
            mode: New mode ('manual', 'audio', 'midi', 'sensor', 'internal')
        """
        if mode not in self.sources:
            raise ValueError(f"Invalid mode: {mode}. Must be one of {list(self.sources.keys())}")

        if mode == self.current_mode:
            return  # Already in this mode

        print(f"[PhiModulatorController] Switching mode: {self.current_mode} → {mode}")

        # Start crossfade
        self.previous_mode = self.current_mode
        self.current_mode = mode
        self.crossfade_progress = 0.0
        self.crossfade_start_time = time.time()

        # Deactivate previous, activate new
        if self.previous_mode:
            self.sources[self.previous_mode].deactivate()
        self.sources[self.current_mode].activate()

        # Log mode change
        self._log_state(PhiState(source=f"MODE_CHANGE_{mode}"))

    def update(self, audio_block: Optional[np.ndarray] = None, **kwargs) -> PhiState:
        """
        Update Φ-modulation state

        This is called at audio block rate (typically every 512 samples @ 48kHz)

        Args:
            audio_block: Audio input (for audio-driven mode)
            **kwargs: Additional parameters for specific sources

        Returns:
            Current PhiState (potentially crossfaded between sources)
        """
        current_time = time.time()

        # Update crossfade progress
        if self.crossfade_progress < 1.0:
            elapsed = current_time - self.crossfade_start_time
            self.crossfade_progress = min(1.0, elapsed / self.CROSSFADE_TIME)

        # Update current source
        current_source = self.sources[self.current_mode]

        # Pass appropriate data to source
        if self.current_mode == "audio" and audio_block is not None:
            current_state = current_source.update(audio_block=audio_block, **kwargs)
        else:
            current_state = current_source.update(**kwargs)

        # If crossfading, blend with previous source
        if self.crossfade_progress < 1.0 and self.previous_mode:
            prev_source = self.sources[self.previous_mode]
            prev_state = prev_source.get_state()

            # Blend phase and depth
            alpha = self.crossfade_progress  # 0 = prev, 1 = current

            # Use smooth crossfade (equal power)
            alpha_smooth = 0.5 * (1.0 - np.cos(alpha * np.pi))

            blended_phase = (
                (1.0 - alpha_smooth) * prev_state.phase +
                alpha_smooth * current_state.phase
            )
            blended_depth = (
                (1.0 - alpha_smooth) * prev_state.depth +
                alpha_smooth * current_state.depth
            )

            self.current_state = PhiState(
                phase=blended_phase,
                depth=blended_depth,
                source=f"{self.previous_mode}→{self.current_mode}",
                frequency=current_state.frequency
            )
        else:
            self.current_state = current_state

        # Store in history
        self.state_history.append(self.current_state)
        if len(self.state_history) > self.max_history:
            self.state_history.pop(0)

        # Log periodically (every 100 updates to avoid overhead)
        if len(self.state_history) % 100 == 0:
            self._log_state(self.current_state)

        return self.current_state

    def get_state(self) -> PhiState:
        """Get current Φ state without updating"""
        return self.current_state

    def get_state_dict(self) -> Dict:
        """Get state as dictionary for JSON serialization"""
        state_dict = self.current_state.to_dict()
        state_dict['crossfade_progress'] = float(self.crossfade_progress)
        state_dict['available_modes'] = list(self.sources.keys())
        return state_dict

    def get_mode(self) -> PhiMode:
        """Get current active mode"""
        return self.current_mode

    # Convenience methods for mode-specific controls

    def set_manual_params(self, phase: Optional[float] = None, depth: Optional[float] = None):
        """Set manual mode parameters"""
        manual = self.sources["manual"]
        if phase is not None:
            manual.set_phase(phase)
        if depth is not None:
            manual.set_depth(depth)

    def set_audio_envelope_params(self, attack_ms: Optional[float] = None, release_ms: Optional[float] = None):
        """Configure audio envelope follower"""
        audio = self.sources["audio"]
        if attack_ms is not None:
            audio.set_attack(attack_ms)
        if release_ms is not None:
            audio.set_release(release_ms)

    def set_internal_frequency(self, frequency: float):
        """Set internal oscillator frequency [0.01, 10 Hz]"""
        internal = self.sources["internal"]
        internal.set_frequency(frequency)

    def set_midi_cc1(self, value: int):
        """Set MIDI CC1 value [0, 127]"""
        midi = self.sources["midi"]
        midi.set_cc1(value)

    def set_sensor_data(self,
                       heart_rate: Optional[float] = None,
                       gsr: Optional[float] = None,
                       accel: Optional[tuple] = None):
        """Update sensor data"""
        sensor = self.sources["sensor"]
        sensor.update(heart_rate=heart_rate, gsr=gsr, accel=accel)

    def detect_midi_ports(self) -> list:
        """Detect available MIDI input ports"""
        midi = self.sources["midi"]
        return midi.detect_ports()

    def connect_midi(self, port_name: Optional[str] = None):
        """Connect to MIDI input port"""
        midi = self.sources["midi"]
        midi.connect(port_name)

    def get_metrics(self) -> Dict:
        """
        Get comprehensive metrics for monitoring

        Returns:
            Dictionary with:
                - current_state: Current Φ state
                - mode: Active mode
                - crossfade_progress: Crossfade progress [0, 1]
                - history_size: Number of states in history
                - uptime_seconds: Time since initialization
        """
        return {
            'current_state': self.current_state.to_dict(),
            'mode': self.current_mode,
            'crossfade_progress': float(self.crossfade_progress),
            'history_size': len(self.state_history),
            'source_states': {
                mode: source.get_state().to_dict()
                for mode, source in self.sources.items()
            }
        }

    def reset(self):
        """Reset all sources and state"""
        print("[PhiModulatorController] Resetting all sources")

        for source in self.sources.values():
            source.reset()

        self.current_mode = "internal"
        self.previous_mode = None
        self.crossfade_progress = 1.0
        self.current_state = PhiState(source="internal")
        self.state_history.clear()

        self.sources["internal"].activate()

    def close(self):
        """Cleanup and close resources"""
        print("[PhiModulatorController] Shutting down")

        if self.log_file and not self.log_file.closed:
            self.log_file.write(f"# Session ended: {datetime.now().isoformat()}\n")
            self.log_file.close()

    def __del__(self):
        """Ensure cleanup on destruction"""
        self.close()


# Self-test function
def _self_test():
    """Test PhiModulatorController"""
    print("=" * 60)
    print("PhiModulatorController Self-Test")
    print("=" * 60)

    try:
        # Initialize controller
        print("\n1. Initializing controller...")
        controller = PhiModulatorController(sample_rate=48000, block_size=512)
        print(f"   ✓ Controller initialized in mode: {controller.get_mode()}")

        # Test internal oscillator (default)
        print("\n2. Testing internal oscillator...")
        for i in range(5):
            state = controller.update()
            print(f"   Update {i+1}: {state}")
            time.sleep(0.05)
        print("   ✓ Internal oscillator working")

        # Switch to manual mode
        print("\n3. Switching to manual mode...")
        controller.set_mode("manual")
        controller.set_manual_params(phase=np.pi/4, depth=0.8)
        time.sleep(0.15)  # Wait for crossfade
        state = controller.update()
        print(f"   Manual state: {state}")
        assert abs(state.depth - 0.8) < 0.1, f"Expected depth ≈0.8, got {state.depth}"
        print("   ✓ Manual mode working")

        # Switch to audio mode
        print("\n4. Switching to audio mode...")
        controller.set_mode("audio")
        test_audio = np.random.randn(512).astype(np.float32) * 0.5
        time.sleep(0.15)  # Wait for crossfade
        for i in range(3):
            state = controller.update(audio_block=test_audio)
            print(f"   Audio update {i+1}: depth={state.depth:.3f}")
        print("   ✓ Audio mode working")

        # Test MIDI port detection
        print("\n5. Testing MIDI detection...")
        ports = controller.detect_midi_ports()
        print(f"   Available MIDI ports: {ports if ports else 'None'}")
        print("   ✓ MIDI detection OK (even if no ports)")

        # Test metrics
        print("\n6. Testing metrics...")
        metrics = controller.get_metrics()
        print(f"   Mode: {metrics['mode']}")
        print(f"   Crossfade: {metrics['crossfade_progress']:.2f}")
        print(f"   History size: {metrics['history_size']}")
        print("   ✓ Metrics working")

        # Test state export
        print("\n7. Testing state export...")
        state_dict = controller.get_state_dict()
        print(f"   State dict keys: {list(state_dict.keys())}")
        assert 'phase' in state_dict
        assert 'depth' in state_dict
        print("   ✓ State export working")

        # Cleanup
        print("\n8. Cleanup...")
        controller.close()
        print("   ✓ Cleanup complete")

        print("\n" + "=" * 60)
        print("Self-Test PASSED ✓")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n✗ Self-Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    _self_test()
