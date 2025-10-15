/**
 * Feature 008: Metrics Dashboard - Consciousness HUD
 *
 * Displays real-time consciousness metrics:
 * - ICI (Inter-Channel Interference)
 * - Phase Coherence
 * - Spectral Centroid
 * - Criticality
 * - Consciousness Level
 * - State classification (AWAKE, DREAMING, etc.)
 *
 * Updates via WebSocket at 30 Hz
 */

export class MetricsDashboard {
  constructor(containerId, websocketURL) {
    this.container = document.getElementById(containerId);
    if (!this.container) {
      throw new Error(`Container ${containerId} not found`);
    }

    this.websocketURL = websocketURL;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 2000;

    // State
    this.metrics = {
      ici: 0,
      phase_coherence: 0,
      spectral_centroid: 0,
      criticality: 0,
      consciousness_level: 0,
      state: 'IDLE',
      phi_phase: 0,
      phi_depth: 0,
      phi_mode: 'internal'
    };

    // Performance tracking
    this.lastUpdateTime = 0;
    this.updateCount = 0;
    this.fps = 0;

    this.build();
    this.connect();

    console.log('[MetricsDashboard] Initialized, connecting to', websocketURL);
  }

  /**
   * Build the HTML structure
   */
  build() {
    this.container.innerHTML = '';
    this.container.style.cssText = `
      padding: 15px;
      background: rgba(0, 0, 0, 0.9);
      border: 2px solid #0f0;
      border-radius: 8px;
      font-family: monospace;
    `;

    // Title
    const title = document.createElement('div');
    title.textContent = 'CONSCIOUSNESS METRICS';
    title.style.cssText = `
      font-weight: bold;
      color: #0f0;
      margin-bottom: 15px;
      text-align: center;
      font-size: 16px;
      letter-spacing: 3px;
    `;
    this.container.appendChild(title);

    // Connection status
    const statusDiv = document.createElement('div');
    statusDiv.id = 'metricsConnectionStatus';
    statusDiv.textContent = '● Connecting...';
    statusDiv.style.cssText = `
      text-align: center;
      color: #ff0;
      font-size: 12px;
      margin-bottom: 10px;
    `;
    this.container.appendChild(statusDiv);

    // Main metrics grid
    const metricsGrid = document.createElement('div');
    metricsGrid.style.cssText = `
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-bottom: 15px;
    `;

    // Create metric gauges
    const metricNames = [
      { key: 'ici', label: 'ICI', color: '#ff6b6b' },
      { key: 'phase_coherence', label: 'Phase Coherence', color: '#4ecdc4' },
      { key: 'spectral_centroid', label: 'Spectral Centroid', color: '#ffe66d' },
      { key: 'criticality', label: 'Criticality', color: '#ff006e' }
    ];

    metricNames.forEach(metric => {
      const gauge = this.createGauge(metric.key, metric.label, metric.color);
      metricsGrid.appendChild(gauge);
    });

    this.container.appendChild(metricsGrid);

    // Consciousness Level (large display)
    const consciousnessPanel = document.createElement('div');
    consciousnessPanel.style.cssText = `
      padding: 15px;
      background: rgba(0, 255, 0, 0.05);
      border: 2px solid #0f0;
      border-radius: 6px;
      text-align: center;
      margin-bottom: 15px;
    `;

    const consciousnessLabel = document.createElement('div');
    consciousnessLabel.textContent = 'CONSCIOUSNESS LEVEL';
    consciousnessLabel.style.cssText = `
      font-size: 12px;
      color: #888;
      margin-bottom: 5px;
    `;
    consciousnessPanel.appendChild(consciousnessLabel);

    const consciousnessValue = document.createElement('div');
    consciousnessValue.id = 'consciousnessLevelValue';
    consciousnessValue.textContent = '0.000';
    consciousnessValue.style.cssText = `
      font-size: 36px;
      font-weight: bold;
      color: #0f0;
      text-shadow: 0 0 10px #0f0;
    `;
    consciousnessPanel.appendChild(consciousnessValue);

    const consciousnessBar = document.createElement('div');
    consciousnessBar.style.cssText = `
      width: 100%;
      height: 20px;
      background: rgba(0, 0, 0, 0.5);
      border-radius: 10px;
      overflow: hidden;
      margin-top: 10px;
    `;

    const consciousnessBarFill = document.createElement('div');
    consciousnessBarFill.id = 'consciousnessBarFill';
    consciousnessBarFill.style.cssText = `
      height: 100%;
      width: 0%;
      background: linear-gradient(to right, #0f0, #0ff);
      transition: width 0.2s;
    `;
    consciousnessBar.appendChild(consciousnessBarFill);
    consciousnessPanel.appendChild(consciousnessBar);

    this.container.appendChild(consciousnessPanel);

    // State display
    const statePanel = document.createElement('div');
    statePanel.style.cssText = `
      padding: 10px;
      background: rgba(0, 0, 0, 0.7);
      border: 1px solid #333;
      border-radius: 4px;
      text-align: center;
    `;

    const stateLabel = document.createElement('div');
    stateLabel.textContent = 'STATE';
    stateLabel.style.cssText = `
      font-size: 11px;
      color: #888;
      margin-bottom: 5px;
    `;
    statePanel.appendChild(stateLabel);

    const stateValue = document.createElement('div');
    stateValue.id = 'metricsStateValue';
    stateValue.textContent = 'IDLE';
    stateValue.style.cssText = `
      font-size: 24px;
      font-weight: bold;
      color: #0f0;
      letter-spacing: 2px;
    `;
    statePanel.appendChild(stateValue);

    this.container.appendChild(statePanel);

    // Performance info
    const perfInfo = document.createElement('div');
    perfInfo.id = 'metricsPerfInfo';
    perfInfo.style.cssText = `
      margin-top: 10px;
      padding: 8px;
      background: rgba(0, 0, 0, 0.5);
      border-radius: 4px;
      font-size: 10px;
      color: #666;
      text-align: center;
    `;
    perfInfo.textContent = 'FPS: 0 | Updates: 0';
    this.container.appendChild(perfInfo);
  }

  /**
   * Create a metric gauge
   * @param {string} key - Metric key
   * @param {string} label - Display label
   * @param {string} color - Gauge color
   * @returns {HTMLElement} Gauge element
   */
  createGauge(key, label, color) {
    const gauge = document.createElement('div');
    gauge.style.cssText = `
      padding: 10px;
      background: rgba(0, 0, 0, 0.6);
      border: 1px solid ${color}40;
      border-radius: 4px;
    `;

    const gaugeLabel = document.createElement('div');
    gaugeLabel.textContent = label;
    gaugeLabel.style.cssText = `
      font-size: 11px;
      color: ${color};
      margin-bottom: 5px;
      font-weight: bold;
    `;
    gauge.appendChild(gaugeLabel);

    const gaugeValue = document.createElement('div');
    gaugeValue.id = `metric_${key}_value`;
    gaugeValue.textContent = '0.000';
    gaugeValue.style.cssText = `
      font-size: 20px;
      color: #0f0;
      margin-bottom: 5px;
    `;
    gauge.appendChild(gaugeValue);

    const gaugeBar = document.createElement('div');
    gaugeBar.style.cssText = `
      width: 100%;
      height: 8px;
      background: rgba(0, 0, 0, 0.5);
      border-radius: 4px;
      overflow: hidden;
    `;

    const gaugeBarFill = document.createElement('div');
    gaugeBarFill.id = `metric_${key}_bar`;
    gaugeBarFill.style.cssText = `
      height: 100%;
      width: 0%;
      background: ${color};
      transition: width 0.1s;
    `;
    gaugeBar.appendChild(gaugeBarFill);
    gauge.appendChild(gaugeBar);

    return gauge;
  }

  /**
   * Connect to WebSocket
   */
  connect() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log('[MetricsDashboard] Already connected');
      return;
    }

    try {
      this.ws = new WebSocket(this.websocketURL);

      this.ws.onopen = () => {
        console.log('[MetricsDashboard] WebSocket connected');
        this.reconnectAttempts = 0;
        this.updateConnectionStatus('● Connected', '#0f0');
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.updateMetrics(data);
        } catch (e) {
          console.error('[MetricsDashboard] Failed to parse message:', e);
        }
      };

      this.ws.onerror = (error) => {
        console.error('[MetricsDashboard] WebSocket error:', error);
        this.updateConnectionStatus('● Error', '#f00');
      };

      this.ws.onclose = () => {
        console.log('[MetricsDashboard] WebSocket closed');
        this.updateConnectionStatus('● Disconnected', '#f00');
        this.attemptReconnect();
      };

    } catch (e) {
      console.error('[MetricsDashboard] Failed to connect:', e);
      this.updateConnectionStatus('● Failed to connect', '#f00');
      this.attemptReconnect();
    }
  }

  /**
   * Attempt to reconnect
   */
  attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[MetricsDashboard] Max reconnect attempts reached');
      this.updateConnectionStatus('● Connection failed', '#f00');
      return;
    }

    this.reconnectAttempts++;
    this.updateConnectionStatus(`● Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`, '#ff0');

    setTimeout(() => {
      console.log('[MetricsDashboard] Reconnecting...');
      this.connect();
    }, this.reconnectDelay);
  }

  /**
   * Update connection status display
   * @param {string} text - Status text
   * @param {string} color - Status color
   */
  updateConnectionStatus(text, color) {
    const statusDiv = document.getElementById('metricsConnectionStatus');
    if (statusDiv) {
      statusDiv.textContent = text;
      statusDiv.style.color = color;
    }
  }

  /**
   * Update metrics from WebSocket data
   * @param {object} data - Metrics data frame
   */
  updateMetrics(data) {
    // Update internal state
    this.metrics = { ...this.metrics, ...data };

    // Update gauges
    const metricKeys = ['ici', 'phase_coherence', 'spectral_centroid', 'criticality'];

    metricKeys.forEach(key => {
      const value = this.metrics[key] || 0;
      const valueEl = document.getElementById(`metric_${key}_value`);
      const barEl = document.getElementById(`metric_${key}_bar`);

      if (valueEl) {
        if (key === 'spectral_centroid') {
          valueEl.textContent = value.toFixed(0) + ' Hz';
        } else {
          valueEl.textContent = value.toFixed(3);
        }
      }

      if (barEl) {
        // Normalize spectral centroid to 0-1 range (assume max 8000 Hz)
        const normalizedValue = key === 'spectral_centroid' ? value / 8000 : value;
        barEl.style.width = (normalizedValue * 100) + '%';
      }
    });

    // Update consciousness level
    const consciousnessValue = document.getElementById('consciousnessLevelValue');
    const consciousnessBar = document.getElementById('consciousnessBarFill');

    if (consciousnessValue) {
      consciousnessValue.textContent = this.metrics.consciousness_level.toFixed(3);
    }

    if (consciousnessBar) {
      consciousnessBar.style.width = (this.metrics.consciousness_level * 100) + '%';
    }

    // Update state
    const stateValue = document.getElementById('metricsStateValue');
    if (stateValue) {
      stateValue.textContent = this.metrics.state || 'IDLE';

      // Color-code by state
      const stateColors = {
        'AWAKE': '#0ff',
        'DREAMING': '#f0f',
        'DEEP_SLEEP': '#00f',
        'REM': '#ff0',
        'CRITICAL': '#f00',
        'IDLE': '#666',
        'TRANSITION': '#fa0'
      };

      stateValue.style.color = stateColors[this.metrics.state] || '#0f0';
    }

    // Update performance info
    const now = performance.now();
    this.updateCount++;

    if (now - this.lastUpdateTime >= 1000) {
      this.fps = this.updateCount;
      this.updateCount = 0;
      this.lastUpdateTime = now;

      const perfInfo = document.getElementById('metricsPerfInfo');
      if (perfInfo) {
        perfInfo.textContent = `FPS: ${this.fps} | Φ: ${this.metrics.phi_mode.toUpperCase()}`;
      }
    }
  }

  /**
   * Disconnect WebSocket
   */
  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
      console.log('[MetricsDashboard] Disconnected');
    }
  }

  /**
   * Get current metrics
   * @returns {object} Current metrics
   */
  getMetrics() {
    return { ...this.metrics };
  }

  /**
   * Get performance stats
   * @returns {object} Performance stats
   */
  getStats() {
    return {
      fps: this.fps,
      updateCount: this.updateCount,
      connected: this.ws && this.ws.readyState === WebSocket.OPEN
    };
  }
}

/**
 * Create and initialize Metrics Dashboard
 * @param {string} containerId - Container element ID
 * @param {string} websocketURL - WebSocket URL for metrics stream
 * @returns {MetricsDashboard} Dashboard instance
 */
export function createMetricsDashboard(containerId, websocketURL) {
  return new MetricsDashboard(containerId, websocketURL);
}
