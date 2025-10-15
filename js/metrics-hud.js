/**
 * Feature 008: Metrics HUD and State Indicator (Enhanced)
 *
 * Real-time consciousness metrics display with:
 * - Exponential moving average (EMA) smoothing (FR-003)
 * - Global metrics cache exposure (FR-004)
 * - localStorage persistence for reload recovery (FR-005)
 * - Sub-100ms latency (SC-001)
 * - Continuous 10-minute operation without drift (SC-002)
 * - State color mapping per spec #001 (SC-003)
 * - Auto-reconnect without UI stall (SC-004)
 */

export class MetricsHUD {
  constructor(containerId, websocketURL, options = {}) {
    this.container = document.getElementById(containerId);
    if (!this.container) {
      throw new Error(`Container ${containerId} not found`);
    }

    this.websocketURL = websocketURL;
    this.options = {
      emaAlpha: 0.3,           // EMA smoothing factor (FR-003)
      enablePersistence: true,  // localStorage persistence (FR-005)
      persistenceKey: 'soundlab_metrics_last_known',
      maxReconnectAttempts: Infinity,  // Never stop trying
      reconnectDelay: 2000,
      ...options
    };

    // WebSocket
    this.ws = null;
    this.reconnectAttempts = 0;
    this.reconnectTimeout = null;

    // Metrics state (raw and smoothed)
    this.rawMetrics = {
      ici: 0,
      phase_coherence: 0,
      spectral_centroid: 0,
      criticality: 0,
      consciousness_level: 0,
      state: 'IDLE',
      phi_phase: 0,
      phi_depth: 0,
      phi_mode: 'manual',
      timestamp: 0
    };

    this.smoothedMetrics = { ...this.rawMetrics };

    // Performance tracking
    this.lastUpdateTime = 0;
    this.frameCount = 0;
    this.fps = 0;
    this.latencyMs = 0;

    // Load persisted metrics
    if (this.options.enablePersistence) {
      this.loadPersistedMetrics();
    }

    // Expose to global cache (FR-004)
    if (!window.metricsCache) {
      window.metricsCache = {};
    }
    window.metricsCache = this.smoothedMetrics;

    this.build();
    this.connect();

    console.log('[MetricsHUD] Initialized with EMA smoothing and persistence');
  }

  /**
   * Build the HTML structure
   */
  build() {
    this.container.innerHTML = '';
    this.container.style.cssText = `
      padding: 15px;
      background: rgba(0, 0, 0, 0.95);
      border: 2px solid #0f0;
      border-radius: 8px;
      font-family: 'Courier New', monospace;
    `;

    // Title
    const title = document.createElement('div');
    title.textContent = 'CONSCIOUSNESS METRICS HUD';
    title.style.cssText = `
      font-weight: bold;
      color: #0f0;
      margin-bottom: 12px;
      text-align: center;
      font-size: 14px;
      letter-spacing: 2px;
    `;
    this.container.appendChild(title);

    // Connection status
    const statusDiv = document.createElement('div');
    statusDiv.id = 'metricsHudStatus';
    statusDiv.textContent = '⚫ Connecting...';
    statusDiv.style.cssText = `
      text-align: center;
      color: #ff0;
      font-size: 11px;
      margin-bottom: 10px;
    `;
    this.container.appendChild(statusDiv);

    // Large state indicator (SC-003)
    const statePanel = document.createElement('div');
    statePanel.id = 'metricsHudStatePanel';
    statePanel.style.cssText = `
      padding: 20px;
      background: rgba(0, 0, 0, 0.8);
      border: 3px solid #0f0;
      border-radius: 8px;
      text-align: center;
      margin-bottom: 15px;
    `;

    const stateLabel = document.createElement('div');
    stateLabel.textContent = 'CONSCIOUSNESS STATE';
    stateLabel.style.cssText = `
      font-size: 10px;
      color: #666;
      margin-bottom: 8px;
      letter-spacing: 1px;
    `;
    statePanel.appendChild(stateLabel);

    const stateValue = document.createElement('div');
    stateValue.id = 'metricsHudStateValue';
    stateValue.textContent = 'IDLE';
    stateValue.style.cssText = `
      font-size: 32px;
      font-weight: bold;
      color: #0f0;
      letter-spacing: 3px;
      text-shadow: 0 0 20px currentColor;
      transition: color 0.3s;
    `;
    statePanel.appendChild(stateValue);

    this.container.appendChild(statePanel);

    // Numeric metrics grid
    const metricsGrid = document.createElement('div');
    metricsGrid.style.cssText = `
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-bottom: 12px;
    `;

    const metricDefs = [
      { key: 'ici', label: 'ICI', unit: '', color: '#ff6b6b' },
      { key: 'phase_coherence', label: 'Phase Coherence', unit: '', color: '#4ecdc4' },
      { key: 'spectral_centroid', label: 'Spectral Centroid', unit: ' Hz', color: '#ffe66d' },
      { key: 'criticality', label: 'Criticality', unit: '', color: '#ff006e' },
      { key: 'consciousness_level', label: 'Consciousness', unit: '', color: '#00ff00', large: true }
    ];

    metricDefs.forEach(metric => {
      const el = this.createMetricDisplay(metric);
      if (metric.large) {
        el.style.gridColumn = '1 / -1';
      }
      metricsGrid.appendChild(el);
    });

    this.container.appendChild(metricsGrid);

    // Performance info
    const perfDiv = document.createElement('div');
    perfDiv.id = 'metricsHudPerf';
    perfDiv.style.cssText = `
      margin-top: 10px;
      padding: 6px;
      background: rgba(0, 0, 0, 0.5);
      border-radius: 4px;
      font-size: 9px;
      color: #555;
      text-align: center;
    `;
    perfDiv.textContent = 'FPS: 0 | Latency: 0ms';
    this.container.appendChild(perfDiv);
  }

  /**
   * Create a metric display element
   */
  createMetricDisplay(metric) {
    const container = document.createElement('div');
    container.style.cssText = `
      padding: 8px;
      background: rgba(0, 0, 0, 0.6);
      border: 1px solid ${metric.color}40;
      border-radius: 4px;
    `;

    const label = document.createElement('div');
    label.textContent = metric.label;
    label.style.cssText = `
      font-size: 9px;
      color: ${metric.color};
      margin-bottom: 4px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    `;
    container.appendChild(label);

    const value = document.createElement('div');
    value.id = `metricsHud_${metric.key}`;
    value.textContent = `0.000${metric.unit}`;
    value.style.cssText = `
      font-size: ${metric.large ? '28px' : '18px'};
      color: #0f0;
      font-weight: bold;
    `;
    container.appendChild(value);

    // Bar indicator
    const bar = document.createElement('div');
    bar.style.cssText = `
      width: 100%;
      height: 4px;
      background: rgba(0, 0, 0, 0.5);
      border-radius: 2px;
      overflow: hidden;
      margin-top: 4px;
    `;

    const barFill = document.createElement('div');
    barFill.id = `metricsHudBar_${metric.key}`;
    barFill.style.cssText = `
      height: 100%;
      width: 0%;
      background: ${metric.color};
      transition: width 0.15s;
    `;
    bar.appendChild(barFill);
    container.appendChild(bar);

    return container;
  }

  /**
   * Connect to WebSocket
   */
  connect() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log('[MetricsHUD] Already connected');
      return;
    }

    try {
      this.ws = new WebSocket(this.websocketURL);

      this.ws.onopen = () => {
        console.log('[MetricsHUD] WebSocket connected');
        this.reconnectAttempts = 0;
        this.updateStatus('🟢 Connected', '#0f0');
      };

      this.ws.onmessage = (event) => {
        const receiveTime = performance.now();
        try {
          const data = JSON.parse(event.data);
          this.handleMetricsUpdate(data, receiveTime);
        } catch (e) {
          console.error('[MetricsHUD] Parse error:', e);
        }
      };

      this.ws.onerror = (error) => {
        console.error('[MetricsHUD] WebSocket error:', error);
        this.updateStatus('🔴 Error', '#f00');
      };

      this.ws.onclose = () => {
        console.log('[MetricsHUD] WebSocket closed');
        this.updateStatus('🔴 Disconnected', '#f00');
        this.attemptReconnect();
      };

    } catch (e) {
      console.error('[MetricsHUD] Connection failed:', e);
      this.updateStatus('🔴 Failed', '#f00');
      this.attemptReconnect();
    }
  }

  /**
   * Attempt to reconnect
   */
  attemptReconnect() {
    // Clear any existing reconnect timeout
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }

    this.reconnectAttempts++;
    this.updateStatus(`🟡 Reconnecting... (${this.reconnectAttempts})`, '#ff0');

    this.reconnectTimeout = setTimeout(() => {
      console.log('[MetricsHUD] Reconnecting...');
      this.connect();
    }, this.reconnectDelay);
  }

  /**
   * Handle metrics update from WebSocket
   */
  handleMetricsUpdate(data, receiveTime) {
    // Calculate latency (SC-001: <100ms)
    const updateStartTime = performance.now();

    // Update raw metrics
    this.rawMetrics = {
      ...this.rawMetrics,
      ...data,
      timestamp: Date.now()
    };

    // Apply EMA smoothing (FR-003)
    const alpha = this.options.emaAlpha;
    Object.keys(data).forEach(key => {
      if (typeof data[key] === 'number') {
        this.smoothedMetrics[key] =
          alpha * data[key] + (1 - alpha) * (this.smoothedMetrics[key] || 0);
      } else {
        // Non-numeric values (like state) - no smoothing
        this.smoothedMetrics[key] = data[key];
      }
    });

    // Clamp values to 0-1 range (edge case)
    ['ici', 'phase_coherence', 'criticality', 'consciousness_level'].forEach(key => {
      if (this.smoothedMetrics[key] !== undefined) {
        this.smoothedMetrics[key] = Math.max(0, Math.min(1, this.smoothedMetrics[key]));
      }
    });

    // Update global cache (FR-004)
    window.metricsCache = { ...this.smoothedMetrics };

    // Persist to localStorage (FR-005)
    if (this.options.enablePersistence) {
      this.persistMetrics();
    }

    // Update UI
    this.updateDisplay();

    // Calculate and track latency
    const updateEndTime = performance.now();
    this.latencyMs = updateEndTime - updateStartTime;

    // Update performance counters
    this.frameCount++;
    const now = performance.now();
    if (now - this.lastUpdateTime >= 1000) {
      this.fps = this.frameCount;
      this.frameCount = 0;
      this.lastUpdateTime = now;

      this.updatePerformanceDisplay();
    }
  }

  /**
   * Update the visual display
   */
  updateDisplay() {
    const m = this.smoothedMetrics;

    // Update numeric values
    ['ici', 'phase_coherence', 'criticality', 'consciousness_level'].forEach(key => {
      const el = document.getElementById(`metricsHud_${key}`);
      if (el) {
        el.textContent = (m[key] || 0).toFixed(3);
      }

      const bar = document.getElementById(`metricsHudBar_${key}`);
      if (bar) {
        bar.style.width = ((m[key] || 0) * 100) + '%';
      }
    });

    // Spectral centroid (special handling)
    const centroidEl = document.getElementById('metricsHud_spectral_centroid');
    if (centroidEl) {
      centroidEl.textContent = Math.round(m.spectral_centroid || 0) + ' Hz';
    }

    const centroidBar = document.getElementById('metricsHudBar_spectral_centroid');
    if (centroidBar) {
      // Normalize to 0-8000 Hz range
      centroidBar.style.width = ((m.spectral_centroid || 0) / 8000 * 100) + '%';
    }

    // Update state display with color mapping (SC-003)
    const stateEl = document.getElementById('metricsHudStateValue');
    const statePanel = document.getElementById('metricsHudStatePanel');
    if (stateEl && statePanel) {
      const state = m.state || 'IDLE';
      stateEl.textContent = state;

      // State color map per spec #001
      const stateColors = {
        'IDLE': { text: '#666', border: '#333' },
        'AWAKE': { text: '#0ff', border: '#0ff' },
        'DREAMING': { text: '#f0f', border: '#f0f' },
        'DEEP_SLEEP': { text: '#00f', border: '#00f' },
        'REM': { text: '#ff0', border: '#ff0' },
        'CRITICAL': { text: '#f00', border: '#f00' },
        'TRANSITION': { text: '#fa0', border: '#fa0' }
      };

      const colors = stateColors[state] || stateColors['IDLE'];
      stateEl.style.color = colors.text;
      statePanel.style.borderColor = colors.border;
    }
  }

  /**
   * Update performance display
   */
  updatePerformanceDisplay() {
    const perfDiv = document.getElementById('metricsHudPerf');
    if (perfDiv) {
      perfDiv.textContent = `FPS: ${this.fps} | Latency: ${this.latencyMs.toFixed(1)}ms`;
    }
  }

  /**
   * Update connection status
   */
  updateStatus(text, color) {
    const statusDiv = document.getElementById('metricsHudStatus');
    if (statusDiv) {
      statusDiv.textContent = text;
      statusDiv.style.color = color;
    }
  }

  /**
   * Persist metrics to localStorage (FR-005)
   */
  persistMetrics() {
    try {
      localStorage.setItem(this.options.persistenceKey, JSON.stringify({
        metrics: this.smoothedMetrics,
        timestamp: Date.now()
      }));
    } catch (e) {
      console.error('[MetricsHUD] Failed to persist metrics:', e);
    }
  }

  /**
   * Load persisted metrics from localStorage (FR-005)
   */
  loadPersistedMetrics() {
    try {
      const stored = localStorage.getItem(this.options.persistenceKey);
      if (stored) {
        const data = JSON.parse(stored);
        this.smoothedMetrics = data.metrics || this.smoothedMetrics;
        console.log('[MetricsHUD] Loaded persisted metrics from', new Date(data.timestamp));

        // Display persisted metrics immediately
        this.updateDisplay();
      }
    } catch (e) {
      console.error('[MetricsHUD] Failed to load persisted metrics:', e);
    }
  }

  /**
   * Get current metrics
   */
  getMetrics() {
    return {
      raw: { ...this.rawMetrics },
      smoothed: { ...this.smoothedMetrics }
    };
  }

  /**
   * Get performance stats
   */
  getStats() {
    return {
      fps: this.fps,
      latencyMs: this.latencyMs,
      connected: this.ws && this.ws.readyState === WebSocket.OPEN,
      reconnectAttempts: this.reconnectAttempts
    };
  }

  /**
   * Disconnect WebSocket
   */
  disconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
      console.log('[MetricsHUD] Disconnected');
    }
  }
}

/**
 * Create and initialize Metrics HUD
 */
export function createMetricsHUD(containerId, websocketURL, options) {
  return new MetricsHUD(containerId, websocketURL, options);
}
