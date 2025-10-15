/**
 * Feature 007: Control Matrix - Unified Parameter Hub
 *
 * Complete control interface for real-time D-ASE parameter adjustment:
 * - Per-channel controls (frequency, amplitude, enable toggle)
 * - Global controls (coupling strength, phi-phase, phi-depth, gain)
 * - WebSocket communication with /ws/ui
 * - localStorage persistence
 * - Preset integration
 * - Rate limiting (<10 Hz per control)
 *
 * Message format:
 * {
 *   "type": "set_param",
 *   "param_type": "channel" | "global" | "phi",
 *   "channel": 0-7 (for channel params) | null (for global/phi),
 *   "param": "frequency" | "amplitude" | "enabled" | "coupling_strength" | "gain" | "phase" | "depth",
 *   "value": number
 * }
 */

export class ControlMatrix {
  constructor(containerId, serverURL = 'ws://localhost:8000/ws/ui', options = {}) {
    this.container = document.getElementById(containerId);
    if (!this.container) {
      throw new Error(`Container ${containerId} not found`);
    }

    this.serverURL = serverURL;
    this.options = {
      numChannels: 8,
      enablePersistence: true,
      persistenceKey: 'soundlab_control_matrix_state',
      ...options
    };

    // WebSocket connection
    this.ws = null;
    this.connected = false;
    this.reconnectInterval = null;
    this.reconnectDelay = 2000;

    // Rate limiting (10 Hz = 100ms min interval)
    this.lastUpdateTime = {};
    this.minUpdateInterval = 100; // ms

    // Parameter state
    this.state = {
      channels: Array(this.options.numChannels).fill(0).map((_, i) => ({
        index: i,
        frequency: 0.5 + i * 0.3,
        amplitude: 0.5,
        enabled: true
      })),
      global: {
        coupling_strength: 1.0,
        gain: 1.0
      },
      phi: {
        phase: 0.0,
        depth: 0.618,
        mode: 'manual'
      }
    };

    // Load persisted state
    if (this.options.enablePersistence) {
      this.loadState();
    }

    this.build();
    this.connect();

    console.log('[ControlMatrix] Initialized');
  }

  /**
   * Build the HTML structure
   */
  build() {
    this.container.innerHTML = '';
    this.container.style.cssText = `
      display: block;
      padding: 20px;
      background: rgba(0, 0, 0, 0.9);
      border: 2px solid #0f0;
      border-radius: 8px;
      font-family: monospace;
      color: #0f0;
    `;

    // Title
    const title = document.createElement('div');
    title.textContent = 'CONTROL MATRIX - UNIFIED PARAMETER HUB';
    title.style.cssText = `
      font-weight: bold;
      font-size: 16px;
      margin-bottom: 15px;
      text-align: center;
      letter-spacing: 2px;
      color: #0f0;
    `;
    this.container.appendChild(title);

    // Connection status
    const status = document.createElement('div');
    status.id = 'controlMatrixStatus';
    status.textContent = '⚫ Disconnected';
    status.style.cssText = `
      font-size: 12px;
      margin-bottom: 15px;
      text-align: center;
      color: #f00;
    `;
    this.container.appendChild(status);

    // Create layout: channels on left, global controls on right
    const layout = document.createElement('div');
    layout.style.cssText = `
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 20px;
    `;
    this.container.appendChild(layout);

    // Left column: Channel controls
    const channelsContainer = document.createElement('div');
    channelsContainer.id = 'channelControls';
    layout.appendChild(channelsContainer);

    this.buildChannelControls(channelsContainer);

    // Right column: Global controls
    const globalContainer = document.createElement('div');
    globalContainer.id = 'globalControls';
    layout.appendChild(globalContainer);

    this.buildGlobalControls(globalContainer);

    // Bottom: Preset controls
    const presetContainer = document.createElement('div');
    presetContainer.id = 'presetControls';
    presetContainer.style.cssText = 'margin-top: 20px;';
    this.container.appendChild(presetContainer);

    this.buildPresetControls(presetContainer);
  }

  /**
   * Build channel-specific controls
   */
  buildChannelControls(container) {
    const title = document.createElement('div');
    title.textContent = 'CHANNEL PARAMETERS (1-8)';
    title.style.cssText = `
      font-weight: bold;
      margin-bottom: 10px;
      padding-bottom: 5px;
      border-bottom: 1px solid #0f0;
    `;
    container.appendChild(title);

    // Channel grid
    const grid = document.createElement('div');
    grid.style.cssText = `
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 10px;
      max-height: 500px;
      overflow-y: auto;
    `;
    container.appendChild(grid);

    for (let i = 0; i < this.options.numChannels; i++) {
      const channelControl = this.createChannelControl(i);
      grid.appendChild(channelControl);
    }
  }

  /**
   * Create control panel for a single channel
   */
  createChannelControl(index) {
    const channel = this.state.channels[index];
    const colors = [
      '#ff0000', '#ff8800', '#ffff00', '#00ff00',
      '#00ffff', '#0000ff', '#8800ff', '#ff00ff'
    ];

    const panel = document.createElement('div');
    panel.style.cssText = `
      padding: 10px;
      background: rgba(0, 0, 0, 0.5);
      border: 1px solid ${colors[index]};
      border-radius: 4px;
    `;

    // Header with enable toggle
    const header = document.createElement('div');
    header.style.cssText = `
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
    `;

    const label = document.createElement('div');
    label.textContent = `Ch ${index + 1}`;
    label.style.cssText = `
      font-weight: bold;
      color: ${colors[index]};
    `;
    header.appendChild(label);

    const toggle = document.createElement('input');
    toggle.type = 'checkbox';
    toggle.checked = channel.enabled;
    toggle.id = `ch${index}_enabled`;
    toggle.addEventListener('change', () => {
      this.updateParameter('channel', index, 'enabled', toggle.checked ? 1 : 0);
    });
    header.appendChild(toggle);

    panel.appendChild(header);

    // Frequency control
    panel.appendChild(this.createSlider(
      'Freq',
      `ch${index}_freq`,
      channel.frequency,
      0.1,
      20.0,
      0.1,
      (value) => this.updateParameter('channel', index, 'frequency', parseFloat(value)),
      'Hz'
    ));

    // Amplitude control
    panel.appendChild(this.createSlider(
      'Amp',
      `ch${index}_amp`,
      channel.amplitude,
      0,
      1,
      0.01,
      (value) => this.updateParameter('channel', index, 'amplitude', parseFloat(value)),
      ''
    ));

    return panel;
  }

  /**
   * Build global control panel
   */
  buildGlobalControls(container) {
    const title = document.createElement('div');
    title.textContent = 'GLOBAL PARAMETERS';
    title.style.cssText = `
      font-weight: bold;
      margin-bottom: 10px;
      padding-bottom: 5px;
      border-bottom: 1px solid #0f0;
    `;
    container.appendChild(title);

    const panel = document.createElement('div');
    panel.style.cssText = `
      padding: 10px;
      background: rgba(0, 0, 0, 0.5);
      border: 1px solid #0f0;
      border-radius: 4px;
    `;
    container.appendChild(panel);

    // Coupling strength
    panel.appendChild(this.createSlider(
      'Coupling',
      'coupling_strength',
      this.state.global.coupling_strength,
      0,
      2,
      0.01,
      (value) => this.updateParameter('global', null, 'coupling_strength', parseFloat(value)),
      ''
    ));

    // Overall gain
    panel.appendChild(this.createSlider(
      'Gain',
      'gain',
      this.state.global.gain,
      0,
      2,
      0.01,
      (value) => this.updateParameter('global', null, 'gain', parseFloat(value)),
      ''
    ));

    // Phi controls section
    const phiTitle = document.createElement('div');
    phiTitle.textContent = 'Φ-MODULATION';
    phiTitle.style.cssText = `
      font-weight: bold;
      margin: 15px 0 10px 0;
      padding-bottom: 5px;
      border-bottom: 1px solid #ffa500;
      color: #ffa500;
    `;
    container.appendChild(phiTitle);

    const phiPanel = document.createElement('div');
    phiPanel.style.cssText = `
      padding: 10px;
      background: rgba(0, 0, 0, 0.5);
      border: 1px solid #ffa500;
      border-radius: 4px;
    `;
    container.appendChild(phiPanel);

    // Phi phase
    phiPanel.appendChild(this.createSlider(
      'Phase',
      'phi_phase',
      this.state.phi.phase,
      0,
      1,
      0.01,
      (value) => this.updateParameter('phi', null, 'phase', parseFloat(value)),
      ''
    ));

    // Phi depth
    phiPanel.appendChild(this.createSlider(
      'Depth',
      'phi_depth',
      this.state.phi.depth,
      0,
      1,
      0.01,
      (value) => this.updateParameter('phi', null, 'depth', parseFloat(value)),
      ''
    ));
  }

  /**
   * Build preset control panel
   */
  buildPresetControls(container) {
    const panel = document.createElement('div');
    panel.style.cssText = `
      display: flex;
      gap: 10px;
      justify-content: center;
      padding: 10px;
      background: rgba(0, 0, 0, 0.5);
      border: 1px solid #0f0;
      border-radius: 4px;
    `;
    container.appendChild(panel);

    const saveBtn = document.createElement('button');
    saveBtn.textContent = '💾 Save State';
    saveBtn.style.cssText = `
      padding: 8px 16px;
      background: #00ff00;
      color: #000;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-weight: bold;
      font-family: monospace;
    `;
    saveBtn.addEventListener('click', () => this.saveState());
    panel.appendChild(saveBtn);

    const loadBtn = document.createElement('button');
    loadBtn.textContent = '📂 Load State';
    loadBtn.style.cssText = `
      padding: 8px 16px;
      background: #00ff00;
      color: #000;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-weight: bold;
      font-family: monospace;
    `;
    loadBtn.addEventListener('click', () => this.loadState(true));
    panel.appendChild(loadBtn);

    const resetBtn = document.createElement('button');
    resetBtn.textContent = '🔄 Reset';
    resetBtn.style.cssText = `
      padding: 8px 16px;
      background: #ff8800;
      color: #000;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-weight: bold;
      font-family: monospace;
    `;
    resetBtn.addEventListener('click', () => this.reset());
    panel.appendChild(resetBtn);
  }

  /**
   * Create a slider control
   */
  createSlider(label, id, value, min, max, step, onChange, unit = '') {
    const container = document.createElement('div');
    container.style.cssText = 'margin-bottom: 8px;';

    const labelDiv = document.createElement('div');
    labelDiv.style.cssText = `
      display: flex;
      justify-content: space-between;
      font-size: 11px;
      margin-bottom: 2px;
    `;

    const labelText = document.createElement('span');
    labelText.textContent = label;
    labelDiv.appendChild(labelText);

    const valueDisplay = document.createElement('span');
    valueDisplay.id = `${id}_value`;
    valueDisplay.textContent = `${value.toFixed(2)}${unit}`;
    valueDisplay.style.cssText = 'color: #fff;';
    labelDiv.appendChild(valueDisplay);

    container.appendChild(labelDiv);

    const slider = document.createElement('input');
    slider.type = 'range';
    slider.id = id;
    slider.min = min;
    slider.max = max;
    slider.step = step;
    slider.value = value;
    slider.style.cssText = 'width: 100%;';

    slider.addEventListener('input', (e) => {
      const val = parseFloat(e.target.value);
      valueDisplay.textContent = `${val.toFixed(2)}${unit}`;
      onChange(val);
    });

    container.appendChild(slider);

    return container;
  }

  /**
   * Connect to WebSocket server
   */
  connect() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log('[ControlMatrix] Already connected');
      return;
    }

    console.log('[ControlMatrix] Connecting to', this.serverURL);

    try {
      this.ws = new WebSocket(this.serverURL);

      this.ws.onopen = () => {
        console.log('[ControlMatrix] Connected');
        this.connected = true;
        this.updateConnectionStatus(true);

        // Stop reconnect attempts
        if (this.reconnectInterval) {
          clearInterval(this.reconnectInterval);
          this.reconnectInterval = null;
        }
      };

      this.ws.onmessage = (event) => {
        this.handleMessage(JSON.parse(event.data));
      };

      this.ws.onclose = () => {
        console.log('[ControlMatrix] Disconnected');
        this.connected = false;
        this.updateConnectionStatus(false);

        // Start reconnect attempts
        if (!this.reconnectInterval) {
          this.reconnectInterval = setInterval(() => {
            console.log('[ControlMatrix] Attempting reconnect...');
            this.connect();
          }, this.reconnectDelay);
        }
      };

      this.ws.onerror = (error) => {
        console.error('[ControlMatrix] WebSocket error:', error);
      };

    } catch (error) {
      console.error('[ControlMatrix] Connection error:', error);
      this.connected = false;
      this.updateConnectionStatus(false);
    }
  }

  /**
   * Handle incoming WebSocket message
   */
  handleMessage(data) {
    if (data.type === 'state') {
      // Update state from server
      this.state = data.data;
      this.refreshUI();
      console.log('[ControlMatrix] State received from server');
    } else if (data.type === 'param_updated') {
      console.log('[ControlMatrix] Parameter updated:', data.param, '=', data.value);
    } else if (data.type === 'pong') {
      // Handle ping response
    }
  }

  /**
   * Update connection status display
   */
  updateConnectionStatus(connected) {
    const status = document.getElementById('controlMatrixStatus');
    if (status) {
      if (connected) {
        status.textContent = '🟢 Connected';
        status.style.color = '#0f0';
      } else {
        status.textContent = '🔴 Disconnected';
        status.style.color = '#f00';
      }
    }
  }

  /**
   * Update a parameter and send to server
   */
  updateParameter(paramType, channel, param, value) {
    // Rate limiting
    const key = `${paramType}_${channel}_${param}`;
    const now = Date.now();

    if (this.lastUpdateTime[key] && (now - this.lastUpdateTime[key]) < this.minUpdateInterval) {
      // Too soon, skip this update
      return;
    }

    this.lastUpdateTime[key] = now;

    // Update local state
    if (paramType === 'channel' && channel !== null) {
      this.state.channels[channel][param] = value;
    } else if (paramType === 'global') {
      this.state.global[param] = value;
    } else if (paramType === 'phi') {
      this.state.phi[param] = value;
    }

    // Send to server
    if (this.connected && this.ws) {
      const message = {
        type: 'set_param',
        param_type: paramType,
        channel: channel,
        param: param,
        value: value
      };

      try {
        this.ws.send(JSON.stringify(message));
      } catch (error) {
        console.error('[ControlMatrix] Error sending parameter update:', error);
      }
    }

    // Persist state
    if (this.options.enablePersistence) {
      this.saveState();
    }
  }

  /**
   * Refresh UI from current state
   */
  refreshUI() {
    // Update channel controls
    for (let i = 0; i < this.options.numChannels; i++) {
      const channel = this.state.channels[i];

      const freqSlider = document.getElementById(`ch${i}_freq`);
      const ampSlider = document.getElementById(`ch${i}_amp`);
      const enabledToggle = document.getElementById(`ch${i}_enabled`);

      if (freqSlider) {
        freqSlider.value = channel.frequency;
        document.getElementById(`ch${i}_freq_value`).textContent = `${channel.frequency.toFixed(2)}Hz`;
      }

      if (ampSlider) {
        ampSlider.value = channel.amplitude;
        document.getElementById(`ch${i}_amp_value`).textContent = channel.amplitude.toFixed(2);
      }

      if (enabledToggle) {
        enabledToggle.checked = channel.enabled;
      }
    }

    // Update global controls
    const couplingSlider = document.getElementById('coupling_strength');
    if (couplingSlider) {
      couplingSlider.value = this.state.global.coupling_strength;
      document.getElementById('coupling_strength_value').textContent =
        this.state.global.coupling_strength.toFixed(2);
    }

    const gainSlider = document.getElementById('gain');
    if (gainSlider) {
      gainSlider.value = this.state.global.gain;
      document.getElementById('gain_value').textContent =
        this.state.global.gain.toFixed(2);
    }

    // Update phi controls
    const phaseSlider = document.getElementById('phi_phase');
    if (phaseSlider) {
      phaseSlider.value = this.state.phi.phase;
      document.getElementById('phi_phase_value').textContent =
        this.state.phi.phase.toFixed(2);
    }

    const depthSlider = document.getElementById('phi_depth');
    if (depthSlider) {
      depthSlider.value = this.state.phi.depth;
      document.getElementById('phi_depth_value').textContent =
        this.state.phi.depth.toFixed(2);
    }
  }

  /**
   * Save current state to localStorage
   */
  saveState() {
    if (this.options.enablePersistence) {
      try {
        localStorage.setItem(this.options.persistenceKey, JSON.stringify(this.state));
        console.log('[ControlMatrix] State saved to localStorage');
      } catch (error) {
        console.error('[ControlMatrix] Error saving state:', error);
      }
    }
  }

  /**
   * Load state from localStorage
   */
  loadState(forceApply = false) {
    if (this.options.enablePersistence) {
      try {
        const saved = localStorage.getItem(this.options.persistenceKey);
        if (saved) {
          this.state = JSON.parse(saved);
          this.refreshUI();
          console.log('[ControlMatrix] State loaded from localStorage');

          // Optionally apply all parameters to server
          if (forceApply && this.connected) {
            this.applyAllParameters();
          }
        }
      } catch (error) {
        console.error('[ControlMatrix] Error loading state:', error);
      }
    }
  }

  /**
   * Apply all current parameters to server
   */
  applyAllParameters() {
    console.log('[ControlMatrix] Applying all parameters to server');

    // Apply channel parameters
    for (let i = 0; i < this.options.numChannels; i++) {
      const ch = this.state.channels[i];
      this.updateParameter('channel', i, 'frequency', ch.frequency);
      this.updateParameter('channel', i, 'amplitude', ch.amplitude);
      this.updateParameter('channel', i, 'enabled', ch.enabled ? 1 : 0);
    }

    // Apply global parameters
    this.updateParameter('global', null, 'coupling_strength', this.state.global.coupling_strength);
    this.updateParameter('global', null, 'gain', this.state.global.gain);

    // Apply phi parameters
    this.updateParameter('phi', null, 'phase', this.state.phi.phase);
    this.updateParameter('phi', null, 'depth', this.state.phi.depth);
  }

  /**
   * Reset to default values
   */
  reset() {
    this.state = {
      channels: Array(this.options.numChannels).fill(0).map((_, i) => ({
        index: i,
        frequency: 0.5 + i * 0.3,
        amplitude: 0.5,
        enabled: true
      })),
      global: {
        coupling_strength: 1.0,
        gain: 1.0
      },
      phi: {
        phase: 0.0,
        depth: 0.618,
        mode: 'manual'
      }
    };

    this.refreshUI();
    this.applyAllParameters();
    this.saveState();

    console.log('[ControlMatrix] Reset to defaults');
  }

  /**
   * Get current state
   */
  getState() {
    return JSON.parse(JSON.stringify(this.state));
  }

  /**
   * Set state from preset
   */
  setState(newState) {
    this.state = JSON.parse(JSON.stringify(newState));
    this.refreshUI();
    this.applyAllParameters();
    this.saveState();
  }

  /**
   * Disconnect and cleanup
   */
  disconnect() {
    if (this.reconnectInterval) {
      clearInterval(this.reconnectInterval);
      this.reconnectInterval = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.connected = false;
    console.log('[ControlMatrix] Disconnected');
  }
}

/**
 * Create and initialize Control Matrix
 */
export function createControlMatrix(containerId, serverURL, options) {
  return new ControlMatrix(containerId, serverURL, options);
}
