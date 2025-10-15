/**
 * Feature 009: MIDI and Keyboard Integration (Enhanced)
 *
 * Real-time control of Soundlab parameters via:
 * - MIDI CC and Note messages
 * - Keyboard shortcuts
 * - Integration with /ws/ui WebSocket (FR-004)
 * - localStorage persistence for mappings (FR-005)
 * - Rate limiting <10 Hz (FR-006)
 * - Hot-plug detection (SC-003)
 *
 * Success Criteria:
 * - SC-001: MIDI latency <10ms, UI latency <100ms
 * - SC-002: Keyboard control within 150ms
 * - SC-003: Device hot-plug reliable
 * - SC-004: Mappings persist and reload
 */

export class MIDIController {
  constructor(websocketURL, options = {}) {
    this.websocketURL = websocketURL;
    this.options = {
      enablePersistence: true,
      persistenceKey: 'soundlab_midi_mappings',
      rateLimitHz: 10,  // FR-006: <10 Hz
      ...options
    };

    // WebSocket connection
    this.ws = null;
    this.connected = false;
    this.reconnectTimeout = null;
    this.reconnectDelay = 2000;

    // Rate limiting (FR-006)
    this.lastUpdateTime = {};
    this.minUpdateInterval = 1000 / this.options.rateLimitHz; // ms

    // Keyboard state
    this.keysPressed = new Set();
    this.keyBindings = this.initializeKeyBindings();

    // MIDI state
    this.midiAccess = null;
    this.midiEnabled = false;
    this.midiMappings = this.initializeMIDIMappings();
    this.customMappings = {};
    this.lastMIDIValues = new Map();

    // Load persisted mappings (FR-005)
    if (this.options.enablePersistence) {
      this.loadMappings();
    }

    // Initialize
    this.attachKeyboardListeners();
    this.initializeMIDI();
    this.connect();

    console.log('[MIDIController] Initialized with WebSocket integration');
  }

  /**
   * Initialize default key bindings (FR-003)
   */
  initializeKeyBindings() {
    return {
      // Φ-Modulation controls
      'ArrowUp': {
        description: 'Increase Φ-depth',
        action: () => this.adjustParameter('phi', null, 'depth', 0.05, true)
      },
      'ArrowDown': {
        description: 'Decrease Φ-depth',
        action: () => this.adjustParameter('phi', null, 'depth', -0.05, true)
      },
      'ArrowLeft': {
        description: 'Decrease Φ-phase',
        action: () => this.adjustParameter('phi', null, 'phase', -0.1, true)
      },
      'ArrowRight': {
        description: 'Increase Φ-phase',
        action: () => this.adjustParameter('phi', null, 'phase', 0.1, true)
      },

      // Transport controls
      ' ': {
        description: 'Toggle audio start/stop',
        action: () => this.toggleAudio()
      },

      // Preset recall (1-9)
      ...Object.fromEntries(
        ['1', '2', '3', '4', '5', '6', '7', '8', '9'].map(key => [
          key,
          {
            description: `Recall preset ${key}`,
            action: () => this.recallPreset(parseInt(key))
          }
        ])
      ),

      // Help
      '?': {
        description: 'Show keyboard shortcuts',
        action: () => this.showHelp()
      },

      // Edit mode (for custom bindings)
      'e': {
        description: 'Edit MIDI mappings',
        action: () => this.editMappings()
      }
    };
  }

  /**
   * Initialize default MIDI CC mappings (FR-002)
   */
  initializeMIDIMappings() {
    const mappings = {
      1: { // Mod Wheel
        name: 'Φ-Depth',
        param_type: 'phi',
        channel: null,
        param: 'depth',
        min: 0,
        max: 1
      },
      2: { // Breath Controller
        name: 'Φ-Phase',
        param_type: 'phi',
        channel: null,
        param: 'phase',
        min: 0,
        max: 1
      },
      7: { // Volume
        name: 'Master Gain',
        param_type: 'global',
        channel: null,
        param: 'gain',
        min: 0,
        max: 2
      },
      10: { // Pan
        name: 'Coupling Strength',
        param_type: 'global',
        channel: null,
        param: 'coupling_strength',
        min: 0,
        max: 2
      }
    };

    // Add CC16-23 for channel amplitudes (channels 1-8)
    for (let i = 0; i < 8; i++) {
      mappings[16 + i] = {
        name: `Channel ${i + 1} Amplitude`,
        param_type: 'channel',
        channel: i,
        param: 'amplitude',
        min: 0,
        max: 1
      };
    }

    return mappings;
  }

  /**
   * Connect to WebSocket (FR-004)
   */
  connect() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      this.ws = new WebSocket(this.websocketURL);

      this.ws.onopen = () => {
        console.log('[MIDIController] WebSocket connected');
        this.connected = true;

        if (this.reconnectTimeout) {
          clearTimeout(this.reconnectTimeout);
          this.reconnectTimeout = null;
        }
      };

      this.ws.onmessage = (event) => {
        // Handle responses if needed
        const data = JSON.parse(event.data);
        if (data.type === 'param_updated') {
          console.log('[MIDIController] Parameter confirmed:', data.param);
        }
      };

      this.ws.onclose = () => {
        console.log('[MIDIController] WebSocket closed');
        this.connected = false;
        this.attemptReconnect();
      };

      this.ws.onerror = (error) => {
        console.error('[MIDIController] WebSocket error:', error);
      };

    } catch (e) {
      console.error('[MIDIController] Connection failed:', e);
      this.attemptReconnect();
    }
  }

  /**
   * Attempt reconnect
   */
  attemptReconnect() {
    if (this.reconnectTimeout) return;

    this.reconnectTimeout = setTimeout(() => {
      console.log('[MIDIController] Reconnecting...');
      this.connect();
    }, this.reconnectDelay);
  }

  /**
   * Send parameter update via WebSocket (FR-004)
   */
  sendParameterUpdate(paramType, channel, param, value) {
    // Rate limiting (FR-006)
    const key = `${paramType}_${channel}_${param}`;
    const now = Date.now();

    if (this.lastUpdateTime[key] && (now - this.lastUpdateTime[key]) < this.minUpdateInterval) {
      return; // Too soon, skip
    }

    this.lastUpdateTime[key] = now;

    if (!this.connected || !this.ws) {
      console.warn('[MIDIController] Not connected, cannot send update');
      return;
    }

    const message = {
      type: 'set_param',
      param_type: paramType,
      channel: channel,
      param: param,
      value: value
    };

    try {
      this.ws.send(JSON.stringify(message));
      console.log(`[MIDIController] Sent: ${paramType}.${param} = ${value.toFixed(3)}`);
    } catch (e) {
      console.error('[MIDIController] Send error:', e);
    }
  }

  /**
   * Adjust parameter (absolute or relative)
   */
  adjustParameter(paramType, channel, param, value, relative = false) {
    if (relative) {
      // For relative adjustments, we'd need to query current value
      // For now, send the delta as-is
      console.log(`[MIDIController] Relative adjustment: ${paramType}.${param} ${value > 0 ? '+' : ''}${value}`);
    }

    this.sendParameterUpdate(paramType, channel, param, value);
  }

  /**
   * Attach keyboard event listeners
   */
  attachKeyboardListeners() {
    document.addEventListener('keydown', (e) => this.handleKeyDown(e));
    document.addEventListener('keyup', (e) => this.handleKeyUp(e));
  }

  /**
   * Handle key down
   */
  handleKeyDown(e) {
    // Ignore if typing in input field
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
      return;
    }

    const key = e.key;

    // Prevent repeat
    if (this.keysPressed.has(key)) {
      return;
    }

    this.keysPressed.add(key);

    // Check binding
    const binding = this.keyBindings[key];
    if (binding) {
      e.preventDefault();

      const startTime = performance.now();
      binding.action();
      const latency = performance.now() - startTime;

      console.log(`[MIDIController] Key: ${key} - ${binding.description} (${latency.toFixed(2)}ms)`);
    }
  }

  /**
   * Handle key up
   */
  handleKeyUp(e) {
    this.keysPressed.delete(e.key);
  }

  /**
   * Initialize MIDI (FR-001)
   */
  async initializeMIDI() {
    if (!navigator.requestMIDIAccess) {
      console.warn('[MIDIController] Web MIDI API not supported');
      return;
    }

    try {
      this.midiAccess = await navigator.requestMIDIAccess();
      console.log('[MIDIController] MIDI access granted');

      // Hot-plug detection (SC-003)
      this.midiAccess.onstatechange = (e) => this.handleMIDIStateChange(e);

      // Connect to all inputs
      for (const input of this.midiAccess.inputs.values()) {
        this.connectMIDIInput(input);
      }

      this.midiEnabled = true;

      console.log(`[MIDIController] Connected to ${this.midiAccess.inputs.size} MIDI devices`);

    } catch (e) {
      console.error('[MIDIController] MIDI initialization failed:', e);
    }
  }

  /**
   * Handle MIDI state change (SC-003: hot-plug)
   */
  handleMIDIStateChange(e) {
    const port = e.port;

    if (port.type === 'input') {
      if (port.state === 'connected') {
        console.log('[MIDIController] ✓ Device connected:', port.name);
        this.connectMIDIInput(port);
      } else if (port.state === 'disconnected') {
        console.log('[MIDIController] ✗ Device disconnected:', port.name);
      }
    }
  }

  /**
   * Connect MIDI input device
   */
  connectMIDIInput(input) {
    input.onmidimessage = (message) => {
      const startTime = performance.now();
      this.handleMIDIMessage(message);
      const latency = performance.now() - startTime;

      // Track latency (SC-001: <10ms for MIDI processing)
      if (latency > 10) {
        console.warn(`[MIDIController] High MIDI latency: ${latency.toFixed(2)}ms`);
      }
    };
  }

  /**
   * Handle MIDI message
   */
  handleMIDIMessage(message) {
    const [status, data1, data2] = message.data;

    const messageType = status & 0xf0;
    const channel = status & 0x0f;

    // Control Change (CC)
    if (messageType === 0xb0) {
      const cc = data1;
      const value = data2 / 127; // Normalize to 0-1

      this.handleMIDICC(cc, value, channel);
    }

    // Note On (could trigger presets)
    else if (messageType === 0x90 && data2 > 0) {
      console.log(`[MIDIController] Note On: ${data1}, Velocity: ${data2}`);
      // Could map notes to preset recall
    }
  }

  /**
   * Handle MIDI CC message
   */
  handleMIDICC(cc, value, midiChannel) {
    // Check custom mappings first (FR-005)
    let mapping = this.customMappings[cc] || this.midiMappings[cc];

    if (!mapping) {
      // Unmapped CC ignored safely (edge case)
      return;
    }

    // Scale to parameter range
    const scaledValue = mapping.min + value * (mapping.max - mapping.min);

    // Throttle small changes
    const lastValue = this.lastMIDIValues.get(cc);
    if (lastValue !== undefined && Math.abs(scaledValue - lastValue) < 0.01) {
      return;
    }

    this.lastMIDIValues.set(cc, scaledValue);

    // Send via WebSocket (FR-004)
    this.sendParameterUpdate(
      mapping.param_type,
      mapping.channel,
      mapping.param,
      scaledValue
    );

    console.log(`[MIDIController] CC${cc} (${mapping.name}): ${scaledValue.toFixed(3)}`);
  }

  /**
   * Save mappings to localStorage (FR-005)
   */
  saveMappings() {
    if (!this.options.enablePersistence) return;

    try {
      const data = {
        custom: this.customMappings,
        timestamp: Date.now()
      };

      localStorage.setItem(this.options.persistenceKey, JSON.stringify(data));
      console.log('[MIDIController] Mappings saved');
    } catch (e) {
      console.error('[MIDIController] Failed to save mappings:', e);
    }
  }

  /**
   * Load mappings from localStorage (FR-005, SC-004)
   */
  loadMappings() {
    if (!this.options.enablePersistence) return;

    try {
      const stored = localStorage.getItem(this.options.persistenceKey);
      if (stored) {
        const data = JSON.parse(stored);
        this.customMappings = data.custom || {};

        console.log('[MIDIController] Loaded custom mappings:', Object.keys(this.customMappings));
      }
    } catch (e) {
      console.error('[MIDIController] Failed to load mappings:', e);
    }
  }

  /**
   * Add custom MIDI mapping
   */
  addMIDIMapping(cc, config) {
    this.customMappings[cc] = config;
    this.saveMappings();

    console.log(`[MIDIController] Added mapping: CC${cc} → ${config.name}`);
  }

  /**
   * Add custom key binding
   */
  addKeyBinding(key, description, action) {
    this.keyBindings[key] = { description, action };
    console.log(`[MIDIController] Added key binding: ${key} - ${description}`);
  }

  /**
   * Toggle audio (example action)
   */
  toggleAudio() {
    // Would call via REST API
    console.log('[MIDIController] Toggle audio (would call /api/audio/start or /stop)');
  }

  /**
   * Recall preset (example action)
   */
  recallPreset(index) {
    console.log(`[MIDIController] Recall preset ${index} (would call /api/presets/{id})`);
  }

  /**
   * Show keyboard shortcuts help
   */
  showHelp() {
    const helpText = Object.entries(this.keyBindings)
      .map(([key, binding]) => `${key.padEnd(15)} - ${binding.description}`)
      .join('\n');

    alert(`KEYBOARD SHORTCUTS:\n\n${helpText}\n\nMIDI: ${this.midiEnabled ? this.midiAccess.inputs.size + ' devices connected' : 'Not available'}`);
  }

  /**
   * Edit mappings (placeholder)
   */
  editMappings() {
    const current = Object.entries(this.customMappings).length;
    const defaults = Object.entries(this.midiMappings).length;

    alert(`MIDI MAPPINGS:\n\nDefault: ${defaults}\nCustom: ${current}\n\nUse addMIDIMapping() to customize.`);
  }

  /**
   * Get MIDI status
   */
  getMIDIStatus() {
    if (!this.midiEnabled) {
      return { enabled: false, inputs: 0 };
    }

    const inputs = Array.from(this.midiAccess.inputs.values());

    return {
      enabled: true,
      inputs: inputs.length,
      devices: inputs.map(input => ({
        id: input.id,
        name: input.name,
        manufacturer: input.manufacturer,
        state: input.state
      }))
    };
  }

  /**
   * Get active mappings
   */
  getMappings() {
    return {
      default: this.midiMappings,
      custom: this.customMappings,
      effective: { ...this.midiMappings, ...this.customMappings }
    };
  }

  /**
   * Get key bindings
   */
  getKeyBindings() {
    return Object.entries(this.keyBindings).map(([key, binding]) => ({
      key,
      description: binding.description
    }));
  }

  /**
   * Disconnect and cleanup
   */
  disconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    if (this.midiAccess) {
      for (const input of this.midiAccess.inputs.values()) {
        input.onmidimessage = null;
      }
    }

    document.removeEventListener('keydown', this.handleKeyDown);
    document.removeEventListener('keyup', this.handleKeyUp);

    console.log('[MIDIController] Disconnected');
  }
}

/**
 * Create and initialize MIDI Controller
 */
export function createMIDIController(websocketURL, options) {
  return new MIDIController(websocketURL, options);
}
