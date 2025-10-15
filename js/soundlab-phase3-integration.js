/**
 * Soundlab Phase 3 Integration Module
 *
 * Integrates all Phase 3 features (006-010):
 * - Φ-Matrix Visualizer
 * - Control Matrix Panel
 * - Metrics Dashboard
 * - Keyboard/MIDI Control
 * - Preset Browser UI
 *
 * Provides unified initialization and communication with backend server
 */

import { createPhiMatrixVisualizer } from './phi-matrix-visualizer.js';
import { createControlMatrixPanel } from './control-matrix-panel.js';
import { createMetricsDashboard } from './metrics-dashboard.js';
import { createKeyboardMIDIControl } from './keyboard-midi-control.js';
import { createPresetBrowserUI } from './preset-browser-ui.js';

export class SoundlabPhase3 {
  constructor(config = {}) {
    // Configuration
    this.serverURL = config.serverURL || 'http://localhost:8000';
    this.metricsWS = config.metricsWS || 'ws://localhost:8000/ws/metrics';
    this.latencyWS = config.latencyWS || 'ws://localhost:8000/ws/latency';

    // Component instances
    this.phiVisualizer = null;
    this.controlMatrix = null;
    this.metricsDashboard = null;
    this.keyboardMIDI = null;
    this.presetBrowser = null;

    // State
    this.initialized = false;
    this.audioRunning = false;

    // Animation loop
    this.animationFrameId = null;

    console.log('[SoundlabPhase3] Initializing with server:', this.serverURL);
  }

  /**
   * Initialize all Phase 3 components
   * @param {object} containerIds - Container element IDs
   * @returns {Promise<void>}
   */
  async initialize(containerIds = {}) {
    try {
      console.log('[SoundlabPhase3] Initializing components...');

      // Feature 006: Φ-Matrix Visualizer
      if (containerIds.phiMatrix) {
        this.phiVisualizer = createPhiMatrixVisualizer(containerIds.phiMatrix, {
          numChannels: 8,
          waveformLength: 512,
          showPhiEnvelope: true
        });
        console.log('[SoundlabPhase3] ✓ Φ-Matrix Visualizer initialized');
      }

      // Feature 007: Control Matrix Panel
      if (containerIds.controlMatrix) {
        this.controlMatrix = createControlMatrixPanel(
          containerIds.controlMatrix,
          (param, value) => this.handleParameterChange(param, value)
        );
        console.log('[SoundlabPhase3] ✓ Control Matrix Panel initialized');
      }

      // Feature 008: Metrics Dashboard
      if (containerIds.metricsDashboard) {
        this.metricsDashboard = createMetricsDashboard(
          containerIds.metricsDashboard,
          this.metricsWS
        );
        console.log('[SoundlabPhase3] ✓ Metrics Dashboard initialized');
      }

      // Feature 009: Keyboard + MIDI Control
      this.keyboardMIDI = createKeyboardMIDIControl({
        onPhiDepthChange: (value, relative) => this.handlePhiDepthChange(value, relative),
        onPhiPhaseChange: (value, relative) => this.handlePhiPhaseChange(value, relative),
        onPresetRecall: (index) => this.handlePresetRecall(index),
        onAudioToggle: () => this.handleAudioToggle(),
        onRecordingToggle: () => this.handleRecordingToggle(),
        onABToggle: (action) => this.handleABAction(action),
        onParameterChange: (param, value) => this.handleParameterChange(param, value)
      });
      console.log('[SoundlabPhase3] ✓ Keyboard/MIDI Control initialized');

      // Feature 010: Preset Browser UI
      if (containerIds.presetBrowser) {
        this.presetBrowser = createPresetBrowserUI(
          containerIds.presetBrowser,
          this.serverURL,
          {
            onPresetLoad: (preset) => this.handlePresetLoad(preset),
            onPresetSave: () => this.getCurrentState(),
            onABStore: (slot) => this.handleABStore(slot),
            onABToggle: () => this.handleABToggle()
          }
        );
        console.log('[SoundlabPhase3] ✓ Preset Browser UI initialized');
      }

      this.initialized = true;
      console.log('[SoundlabPhase3] ✓ All components initialized successfully');

      // Start animation loop
      this.startAnimationLoop();

      // Check server status
      await this.checkServerStatus();

    } catch (error) {
      console.error('[SoundlabPhase3] Initialization failed:', error);
      throw error;
    }
  }

  /**
   * Start animation loop for visualizers
   */
  startAnimationLoop() {
    const animate = () => {
      // Update Φ-Matrix visualizer
      if (this.phiVisualizer) {
        this.phiVisualizer.draw();
      }

      this.animationFrameId = requestAnimationFrame(animate);
    };

    animate();
    console.log('[SoundlabPhase3] Animation loop started');
  }

  /**
   * Stop animation loop
   */
  stopAnimationLoop() {
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
      console.log('[SoundlabPhase3] Animation loop stopped');
    }
  }

  /**
   * Check server status
   * @returns {Promise<object>} Server status
   */
  async checkServerStatus() {
    try {
      const response = await fetch(`${this.serverURL}/api/status`);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const status = await response.json();
      this.audioRunning = status.audio_running;

      console.log('[SoundlabPhase3] Server status:', status);

      return status;

    } catch (error) {
      console.error('[SoundlabPhase3] Failed to check server status:', error);
      throw error;
    }
  }

  /**
   * Start audio processing on server
   * @param {boolean} calibrate - Run latency calibration
   * @returns {Promise<void>}
   */
  async startAudio(calibrate = false) {
    try {
      const response = await fetch(`${this.serverURL}/api/audio/start?calibrate=${calibrate}`, {
        method: 'POST'
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();

      if (result.ok) {
        this.audioRunning = true;
        console.log('[SoundlabPhase3] Audio started');
      } else {
        throw new Error(result.message);
      }

    } catch (error) {
      console.error('[SoundlabPhase3] Failed to start audio:', error);
      throw error;
    }
  }

  /**
   * Stop audio processing on server
   * @returns {Promise<void>}
   */
  async stopAudio() {
    try {
      const response = await fetch(`${this.serverURL}/api/audio/stop`, {
        method: 'POST'
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();

      if (result.ok) {
        this.audioRunning = false;
        console.log('[SoundlabPhase3] Audio stopped');
      }

    } catch (error) {
      console.error('[SoundlabPhase3] Failed to stop audio:', error);
      throw error;
    }
  }

  /**
   * Handle parameter change (from Control Matrix or MIDI)
   * @param {string} param - Parameter name
   * @param {any} value - Parameter value
   */
  async handleParameterChange(param, value) {
    console.log('[SoundlabPhase3] Parameter change:', param, value);

    // Update control matrix if needed
    if (this.controlMatrix && param !== 'amplitude') {
      // Would update control matrix visual state
    }

    // Send to server (would need API endpoint)
    // For now, just log it
  }

  /**
   * Handle Φ-depth change
   * @param {number} value - New depth value or delta
   * @param {boolean} relative - If true, value is a delta
   */
  handlePhiDepthChange(value, relative) {
    console.log('[SoundlabPhase3] Φ-depth change:', value, relative ? '(relative)' : '');

    // Would send to server via API
  }

  /**
   * Handle Φ-phase change
   * @param {number} value - New phase value or delta
   * @param {boolean} relative - If true, value is a delta
   */
  handlePhiPhaseChange(value, relative) {
    console.log('[SoundlabPhase3] Φ-phase change:', value, relative ? '(relative)' : '');

    // Would send to server via API
  }

  /**
   * Handle preset recall (from keyboard)
   * @param {number} index - Preset index (1-9)
   */
  handlePresetRecall(index) {
    console.log('[SoundlabPhase3] Preset recall:', index);

    // Would load preset from server
  }

  /**
   * Handle audio toggle
   */
  handleAudioToggle() {
    if (this.audioRunning) {
      this.stopAudio();
    } else {
      this.startAudio();
    }
  }

  /**
   * Handle recording toggle
   */
  handleRecordingToggle() {
    console.log('[SoundlabPhase3] Recording toggle');

    // Would trigger recording on server
  }

  /**
   * Handle A/B action
   * @param {string} action - Action ('store_a', 'store_b', or 'toggle')
   */
  handleABAction(action) {
    if (this.presetBrowser) {
      if (action === 'store_a') {
        this.presetBrowser.storeAB('A');
      } else if (action === 'store_b') {
        this.presetBrowser.storeAB('B');
      } else if (action === 'toggle') {
        this.presetBrowser.toggleAB();
      }
    }
  }

  /**
   * Handle preset load
   * @param {object} preset - Preset data
   */
  handlePresetLoad(preset) {
    console.log('[SoundlabPhase3] Preset loaded:', preset.name);

    // Update control matrix
    if (this.controlMatrix && preset.engine) {
      this.controlMatrix.updateParameters({
        frequencies: preset.engine.frequencies,
        amplitudes: preset.engine.amplitudes,
        coupling_strength: preset.engine.coupling_strength
      });
    }

    // Apply preset to server
    this.applyPreset(preset);
  }

  /**
   * Apply preset to server
   * @param {object} preset - Preset data
   * @returns {Promise<void>}
   */
  async applyPreset(preset) {
    try {
      const response = await fetch(`${this.serverURL}/api/preset/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(preset)
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      console.log('[SoundlabPhase3] Preset applied to server');

    } catch (error) {
      console.error('[SoundlabPhase3] Failed to apply preset:', error);
    }
  }

  /**
   * Get current state (for saving preset)
   * @returns {object} Current state
   */
  getCurrentState() {
    const state = {};

    // Get parameters from control matrix
    if (this.controlMatrix) {
      const params = this.controlMatrix.getParameters();
      state.engine = {
        frequencies: params.frequencies,
        amplitudes: params.amplitudes,
        coupling_strength: params.coupling_strength
      };
    }

    // Get Φ parameters from metrics
    if (this.metricsDashboard) {
      const metrics = this.metricsDashboard.getMetrics();
      state.phi = {
        mode: metrics.phi_mode,
        depth: metrics.phi_depth,
        phase: metrics.phi_phase
      };
    }

    return state;
  }

  /**
   * Update visualizer with 8-channel audio data
   * @param {Float32Array[]} channelData - Array of 8 waveform buffers
   */
  updateChannelData(channelData) {
    if (this.phiVisualizer) {
      this.phiVisualizer.updateChannels(channelData);
    }
  }

  /**
   * Update Φ-parameters in visualizer
   * @param {number} phase - Φ phase
   * @param {number} depth - Φ depth
   * @param {string} mode - Φ mode
   */
  updatePhiParameters(phase, depth, mode) {
    if (this.phiVisualizer) {
      this.phiVisualizer.updatePhi(phase, depth, mode);
    }
  }

  /**
   * Get MIDI status
   * @returns {object} MIDI status
   */
  getMIDIStatus() {
    return this.keyboardMIDI ? this.keyboardMIDI.getMIDIStatus() : { enabled: false };
  }

  /**
   * Get metrics dashboard stats
   * @returns {object} Metrics stats
   */
  getMetricsStats() {
    return this.metricsDashboard ? this.metricsDashboard.getStats() : null;
  }

  /**
   * Cleanup all components
   */
  destroy() {
    console.log('[SoundlabPhase3] Destroying components...');

    this.stopAnimationLoop();

    if (this.metricsDashboard) {
      this.metricsDashboard.disconnect();
    }

    if (this.keyboardMIDI) {
      this.keyboardMIDI.destroy();
    }

    this.initialized = false;

    console.log('[SoundlabPhase3] Cleanup complete');
  }
}

/**
 * Create and initialize Phase 3 integration
 * @param {object} config - Configuration
 * @param {object} containerIds - Container element IDs
 * @returns {Promise<SoundlabPhase3>} Phase 3 instance
 */
export async function initializePhase3(config = {}, containerIds = {}) {
  const phase3 = new SoundlabPhase3(config);
  await phase3.initialize(containerIds);
  return phase3;
}

// Export for global access
window.SoundlabPhase3 = SoundlabPhase3;
window.initializePhase3 = initializePhase3;
