/**
 * Feature 006: Φ-Matrix Dashboard - Real-Time 8-Channel Visualizer
 *
 * Displays:
 * - 8 independent channel waveforms
 * - Φ-modulation envelope overlay
 * - Color-coded by frequency band (chromatic identity)
 * - Real-time amplitude and phase visualization
 *
 * Visual latency target: <50ms
 */

export class PhiMatrixVisualizer {
  constructor(canvasId, options = {}) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) {
      throw new Error(`Canvas ${canvasId} not found`);
    }

    this.ctx = this.canvas.getContext('2d');
    this.width = this.canvas.width;
    this.height = this.canvas.height;

    // Configuration
    this.numChannels = options.numChannels || 8;
    this.waveformLength = options.waveformLength || 512;
    this.showPhiEnvelope = options.showPhiEnvelope !== false;
    this.showFrequencyLabels = options.showFrequencyLabels !== false;

    // Chromatic color palette (fixed hue per channel)
    this.channelColors = [
      'hsl(0, 100%, 50%)',     // Red - Low
      'hsl(30, 100%, 50%)',    // Orange
      'hsl(60, 100%, 50%)',    // Yellow
      'hsl(120, 100%, 50%)',   // Green
      'hsl(180, 100%, 50%)',   // Cyan
      'hsl(240, 100%, 50%)',   // Blue
      'hsl(280, 100%, 50%)',   // Purple
      'hsl(320, 100%, 50%)'    // Magenta - High
    ];

    // State
    this.channelData = Array.from({ length: this.numChannels }, () =>
      new Float32Array(this.waveformLength).fill(0)
    );
    this.phiPhase = 0;
    this.phiDepth = 0.618;
    this.phiMode = 'internal';
    this.frequencies = [0.5, 0.81, 1.31, 2.12, 3.43, 5.55, 8.97, 14.52]; // Default
    this.amplitudes = [0.6, 0.55, 0.5, 0.45, 0.4, 0.35, 0.3, 0.25]; // Default

    // Performance
    this.lastDrawTime = 0;
    this.targetFPS = 60;
    this.frameInterval = 1000 / this.targetFPS;

    console.log('[PhiMatrixVisualizer] Initialized with', this.numChannels, 'channels');
  }

  /**
   * Update channel data from audio stream
   * @param {Float32Array[]} channelWaveforms - Array of 8 waveform buffers
   */
  updateChannels(channelWaveforms) {
    if (channelWaveforms.length !== this.numChannels) {
      console.warn('[PhiMatrixVisualizer] Expected', this.numChannels, 'channels, got', channelWaveforms.length);
      return;
    }

    for (let i = 0; i < this.numChannels; i++) {
      this.channelData[i] = channelWaveforms[i];
    }
  }

  /**
   * Update Φ-modulation parameters
   * @param {number} phase - Φ phase (radians)
   * @param {number} depth - Φ depth [0, 1.618]
   * @param {string} mode - Φ mode (manual/audio/midi/sensor/internal)
   */
  updatePhi(phase, depth, mode) {
    this.phiPhase = phase;
    this.phiDepth = depth;
    this.phiMode = mode;
  }

  /**
   * Update frequency and amplitude parameters
   * @param {number[]} frequencies - Channel frequencies
   * @param {number[]} amplitudes - Channel amplitudes
   */
  updateParameters(frequencies, amplitudes) {
    if (frequencies) this.frequencies = frequencies;
    if (amplitudes) this.amplitudes = amplitudes;
  }

  /**
   * Draw the visualization (call from animation loop)
   */
  draw() {
    const now = performance.now();
    const elapsed = now - this.lastDrawTime;

    // Frame rate limiting
    if (elapsed < this.frameInterval) {
      return false; // Skip this frame
    }

    this.lastDrawTime = now - (elapsed % this.frameInterval);

    // Clear canvas
    this.ctx.fillStyle = '#000';
    this.ctx.fillRect(0, 0, this.width, this.height);

    // Draw grid
    this.drawGrid();

    // Draw each channel
    const channelHeight = this.height / this.numChannels;

    for (let ch = 0; ch < this.numChannels; ch++) {
      const y = ch * channelHeight;
      this.drawChannel(ch, y, this.width, channelHeight);
    }

    // Draw Φ-modulation overlay
    if (this.showPhiEnvelope) {
      this.drawPhiEnvelope();
    }

    // Draw info panel
    this.drawInfoPanel();

    return true; // Frame was drawn
  }

  /**
   * Draw background grid
   */
  drawGrid() {
    this.ctx.strokeStyle = 'rgba(0, 255, 0, 0.1)';
    this.ctx.lineWidth = 1;

    // Horizontal lines (channel separators)
    const channelHeight = this.height / this.numChannels;
    for (let i = 0; i <= this.numChannels; i++) {
      const y = i * channelHeight;
      this.ctx.beginPath();
      this.ctx.moveTo(0, y);
      this.ctx.lineTo(this.width, y);
      this.ctx.stroke();
    }

    // Vertical lines (time grid)
    const gridSpacing = this.width / 8;
    for (let i = 0; i <= 8; i++) {
      const x = i * gridSpacing;
      this.ctx.beginPath();
      this.ctx.moveTo(x, 0);
      this.ctx.lineTo(x, this.height);
      this.ctx.stroke();
    }

    // Center line
    this.ctx.strokeStyle = 'rgba(0, 255, 0, 0.2)';
    this.ctx.beginPath();
    this.ctx.moveTo(0, this.height / 2);
    this.ctx.lineTo(this.width, this.height / 2);
    this.ctx.stroke();
  }

  /**
   * Draw a single channel waveform
   * @param {number} channelIndex - Channel index (0-7)
   * @param {number} y - Top Y position
   * @param {number} w - Width
   * @param {number} h - Height
   */
  drawChannel(channelIndex, y, w, h) {
    const waveform = this.channelData[channelIndex];
    const centerY = y + h / 2;
    const amplitude = this.amplitudes[channelIndex] || 0.5;
    const frequency = this.frequencies[channelIndex] || 1.0;

    // Draw waveform
    this.ctx.strokeStyle = this.channelColors[channelIndex];
    this.ctx.lineWidth = 2;
    this.ctx.beginPath();

    for (let i = 0; i < waveform.length; i++) {
      const x = (i / waveform.length) * w;
      const sample = waveform[i];
      const waveY = centerY + (sample * amplitude * h * 0.4); // 40% of channel height

      if (i === 0) {
        this.ctx.moveTo(x, waveY);
      } else {
        this.ctx.lineTo(x, waveY);
      }
    }

    this.ctx.stroke();

    // Draw channel label
    if (this.showFrequencyLabels) {
      this.ctx.fillStyle = this.channelColors[channelIndex];
      this.ctx.font = '10px monospace';
      this.ctx.fillText(`CH${channelIndex + 1} ${frequency.toFixed(2)}Hz`, 5, y + 12);

      // Draw amplitude bar
      const barWidth = 30;
      const barX = this.width - 40;
      const barY = y + 5;
      const barHeight = h - 10;

      // Background
      this.ctx.strokeStyle = 'rgba(0, 255, 0, 0.2)';
      this.ctx.strokeRect(barX, barY, barWidth, barHeight);

      // Fill
      const fillHeight = amplitude * barHeight;
      this.ctx.fillStyle = this.channelColors[channelIndex];
      this.ctx.fillRect(barX, barY + barHeight - fillHeight, barWidth, fillHeight);
    }
  }

  /**
   * Draw Φ-modulation envelope overlay
   */
  drawPhiEnvelope() {
    const PHI = 1.618033988749895;

    // Draw Φ envelope curve
    this.ctx.strokeStyle = 'rgba(255, 215, 0, 0.8)'; // Gold
    this.ctx.lineWidth = 3;
    this.ctx.beginPath();

    for (let x = 0; x < this.width; x++) {
      const t = (x / this.width) * Math.PI * 2;
      const phiValue = 1.0 + this.phiDepth * Math.sin(t + this.phiPhase);
      const y = this.height * (1.0 - (phiValue / (1 + PHI)));

      if (x === 0) {
        this.ctx.moveTo(x, y);
      } else {
        this.ctx.lineTo(x, y);
      }
    }

    this.ctx.stroke();

    // Draw Φ phase indicator
    const phaseX = ((this.phiPhase % (Math.PI * 2)) / (Math.PI * 2)) * this.width;
    const phaseValue = 1.0 + this.phiDepth * Math.sin(this.phiPhase);
    const phaseY = this.height * (1.0 - (phaseValue / (1 + PHI)));

    this.ctx.fillStyle = 'rgba(255, 215, 0, 0.9)';
    this.ctx.beginPath();
    this.ctx.arc(phaseX, phaseY, 5, 0, Math.PI * 2);
    this.ctx.fill();
  }

  /**
   * Draw info panel with Φ parameters
   */
  drawInfoPanel() {
    const padding = 10;
    const panelX = this.width / 2 - 120;
    const panelY = 10;
    const panelW = 240;
    const panelH = 50;

    // Semi-transparent background
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
    this.ctx.fillRect(panelX, panelY, panelW, panelH);

    // Border
    this.ctx.strokeStyle = 'rgba(255, 215, 0, 0.5)';
    this.ctx.lineWidth = 1;
    this.ctx.strokeRect(panelX, panelY, panelW, panelH);

    // Text
    this.ctx.fillStyle = '#ffd700';
    this.ctx.font = 'bold 14px monospace';
    this.ctx.fillText('Φ-MODULATION', panelX + padding, panelY + 18);

    this.ctx.font = '11px monospace';
    this.ctx.fillStyle = '#0f0';

    const phaseDisplay = (this.phiPhase * (180 / Math.PI)).toFixed(1);
    this.ctx.fillText(`Phase: ${phaseDisplay}°`, panelX + padding, panelY + 35);

    this.ctx.fillText(`Depth: ${this.phiDepth.toFixed(3)}`, panelX + 100, panelY + 35);

    this.ctx.fillText(`Mode: ${this.phiMode.toUpperCase()}`, panelX + 180, panelY + 35);
  }

  /**
   * Resize canvas (call when window resizes)
   * @param {number} width - New width
   * @param {number} height - New height
   */
  resize(width, height) {
    this.canvas.width = width;
    this.canvas.height = height;
    this.width = width;
    this.height = height;
  }

  /**
   * Toggle Φ-envelope display
   * @param {boolean} show - Show/hide Φ envelope
   */
  togglePhiEnvelope(show) {
    this.showPhiEnvelope = show;
  }

  /**
   * Toggle frequency labels
   * @param {boolean} show - Show/hide labels
   */
  toggleFrequencyLabels(show) {
    this.showFrequencyLabels = show;
  }

  /**
   * Get performance stats
   * @returns {object} Performance statistics
   */
  getStats() {
    const actualFPS = 1000 / this.frameInterval;
    return {
      targetFPS: this.targetFPS,
      actualFPS: actualFPS,
      numChannels: this.numChannels,
      waveformLength: this.waveformLength
    };
  }
}

/**
 * Create and initialize Φ-Matrix visualizer
 * @param {string} canvasId - Canvas element ID
 * @param {object} options - Configuration options
 * @returns {PhiMatrixVisualizer} Visualizer instance
 */
export function createPhiMatrixVisualizer(canvasId, options = {}) {
  return new PhiMatrixVisualizer(canvasId, options);
}
