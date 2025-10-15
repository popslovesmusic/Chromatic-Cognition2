/**
 * Feature 009: Keyboard + MIDI Control
 *
 * Provides:
 * - Keyboard hotkeys for common operations
 * - MIDI CC control mapping
 * - Live performance controls
 * - Preset recall shortcuts
 */

export class KeyboardMIDIControl {
  constructor(callbacks = {}) {
    this.callbacks = {
      onPhiDepthChange: callbacks.onPhiDepthChange || (() => {}),
      onPhiPhaseChange: callbacks.onPhiPhaseChange || (() => {}),
      onPresetRecall: callbacks.onPresetRecall || (() => {}),
      onAudioToggle: callbacks.onAudioToggle || (() => {}),
      onRecordingToggle: callbacks.onRecordingToggle || (() => {}),
      onABToggle: callbacks.onABToggle || (() => {}),
      onParameterChange: callbacks.onParameterChange || (() => {})
    };

    // Keyboard state
    this.keysPressed = new Set();
    this.keyBindings = this.initializeKeyBindings();

    // MIDI state
    this.midiAccess = null;
    this.midiEnabled = false;
    this.midiMappings = this.initializeMIDIMappings();
    this.lastMIDIValues = new Map();

    this.attachKeyboardListeners();
    this.initializeMIDI();

    console.log('[KeyboardMIDIControl] Initialized');
  }

  /**
   * Initialize keyboard bindings
   * @returns {object} Key bindings map
   */
  initializeKeyBindings() {
    return {
      // Φ-Modulation controls
      'ArrowUp': {
        description: 'Increase Φ-depth',
        action: () => this.adjustPhiDepth(0.05)
      },
      'ArrowDown': {
        description: 'Decrease Φ-depth',
        action: () => this.adjustPhiDepth(-0.05)
      },
      'ArrowLeft': {
        description: 'Decrease Φ-phase',
        action: () => this.adjustPhiPhase(-0.1)
      },
      'ArrowRight': {
        description: 'Increase Φ-phase',
        action: () => this.adjustPhiPhase(0.1)
      },

      // Preset recall (1-9)
      ...Object.fromEntries(
        ['1', '2', '3', '4', '5', '6', '7', '8', '9'].map(key => [
          key,
          {
            description: `Recall preset ${key}`,
            action: () => this.callbacks.onPresetRecall(parseInt(key))
          }
        ])
      ),

      // Transport controls
      ' ': { // Spacebar
        description: 'Toggle audio processing',
        action: () => this.callbacks.onAudioToggle()
      },
      'r': {
        description: 'Toggle recording',
        action: () => this.callbacks.onRecordingToggle()
      },

      // A/B comparison
      'a': {
        description: 'Store state A',
        action: () => this.callbacks.onABToggle('store_a')
      },
      'b': {
        description: 'Store state B',
        action: () => this.callbacks.onABToggle('store_b')
      },
      't': {
        description: 'Toggle A/B',
        action: () => this.callbacks.onABToggle('toggle')
      },

      // Help
      '?': {
        description: 'Show keyboard shortcuts',
        action: () => this.showHelp()
      }
    };
  }

  /**
   * Initialize MIDI CC mappings
   * @returns {object} MIDI CC mappings
   */
  initializeMIDIMappings() {
    return {
      1: { // Mod Wheel (CC1)
        name: 'Φ-Depth',
        min: 0,
        max: 1.618,
        handler: (value) => this.callbacks.onPhiDepthChange(value)
      },
      2: { // Breath Controller (CC2)
        name: 'Φ-Phase',
        min: -Math.PI,
        max: Math.PI,
        handler: (value) => this.callbacks.onPhiPhaseChange(value)
      },
      7: { // Volume (CC7)
        name: 'Master Volume',
        min: 0,
        max: 1,
        handler: (value) => this.callbacks.onParameterChange('volume', value)
      },
      10: { // Pan (CC10)
        name: 'Coupling Strength',
        min: 0,
        max: 2,
        handler: (value) => this.callbacks.onParameterChange('coupling_strength', value)
      },
      // Add more mappings as needed
      16: { // General Purpose 1 (CC16)
        name: 'Channel 1 Amplitude',
        min: 0,
        max: 1,
        handler: (value) => this.callbacks.onParameterChange('amplitude', { channel: 0, value })
      },
      17: {
        name: 'Channel 2 Amplitude',
        min: 0,
        max: 1,
        handler: (value) => this.callbacks.onParameterChange('amplitude', { channel: 1, value })
      },
      18: {
        name: 'Channel 3 Amplitude',
        min: 0,
        max: 1,
        handler: (value) => this.callbacks.onParameterChange('amplitude', { channel: 2, value })
      },
      19: {
        name: 'Channel 4 Amplitude',
        min: 0,
        max: 1,
        handler: (value) => this.callbacks.onParameterChange('amplitude', { channel: 3, value })
      }
    };
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
   * @param {KeyboardEvent} e - Keyboard event
   */
  handleKeyDown(e) {
    // Ignore if typing in input field
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
      return;
    }

    const key = e.key;

    // Check if already pressed (prevent repeat)
    if (this.keysPressed.has(key)) {
      return;
    }

    this.keysPressed.add(key);

    // Check for binding
    const binding = this.keyBindings[key];
    if (binding) {
      e.preventDefault();
      binding.action();
      console.log(`[KeyboardMIDIControl] Hotkey: ${key} - ${binding.description}`);
    }
  }

  /**
   * Handle key up
   * @param {KeyboardEvent} e - Keyboard event
   */
  handleKeyUp(e) {
    this.keysPressed.delete(e.key);
  }

  /**
   * Adjust Φ-depth
   * @param {number} delta - Change amount
   */
  adjustPhiDepth(delta) {
    // Would need current value from external state
    this.callbacks.onPhiDepthChange(delta, true); // true = relative change
  }

  /**
   * Adjust Φ-phase
   * @param {number} delta - Change amount (radians)
   */
  adjustPhiPhase(delta) {
    this.callbacks.onPhiPhaseChange(delta, true); // true = relative change
  }

  /**
   * Initialize MIDI
   */
  async initializeMIDI() {
    if (!navigator.requestMIDIAccess) {
      console.warn('[KeyboardMIDIControl] Web MIDI API not supported');
      return;
    }

    try {
      this.midiAccess = await navigator.requestMIDIAccess();
      console.log('[KeyboardMIDIControl] MIDI access granted');

      this.midiAccess.onstatechange = (e) => this.handleMIDIStateChange(e);

      // Connect to all inputs
      for (const input of this.midiAccess.inputs.values()) {
        this.connectMIDIInput(input);
      }

      this.midiEnabled = true;

    } catch (e) {
      console.error('[KeyboardMIDIControl] MIDI initialization failed:', e);
    }
  }

  /**
   * Handle MIDI state change (device connect/disconnect)
   * @param {MIDIConnectionEvent} e - Connection event
   */
  handleMIDIStateChange(e) {
    console.log('[KeyboardMIDIControl] MIDI state change:', e.port.name, e.port.state);

    if (e.port.type === 'input') {
      if (e.port.state === 'connected') {
        this.connectMIDIInput(e.port);
      }
    }
  }

  /**
   * Connect MIDI input device
   * @param {MIDIInput} input - MIDI input port
   */
  connectMIDIInput(input) {
    console.log('[KeyboardMIDIControl] Connecting MIDI input:', input.name);

    input.onmidimessage = (message) => this.handleMIDIMessage(message);
  }

  /**
   * Handle MIDI message
   * @param {MIDIMessageEvent} message - MIDI message
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

    // Note On (could be used for triggers)
    else if (messageType === 0x90 && data2 > 0) {
      console.log(`[KeyboardMIDIControl] Note On: ${data1}, Velocity: ${data2}`);
      // Could trigger preset recall, etc.
    }

    // Note Off
    else if (messageType === 0x80 || (messageType === 0x90 && data2 === 0)) {
      console.log(`[KeyboardMIDIControl] Note Off: ${data1}`);
    }
  }

  /**
   * Handle MIDI CC message
   * @param {number} cc - CC number
   * @param {number} value - Normalized value (0-1)
   * @param {number} channel - MIDI channel
   */
  handleMIDICC(cc, value, channel) {
    const mapping = this.midiMappings[cc];

    if (mapping) {
      // Scale to parameter range
      const scaledValue = mapping.min + value * (mapping.max - mapping.min);

      // Throttle updates (only if value changed significantly)
      const lastValue = this.lastMIDIValues.get(cc);
      if (lastValue !== undefined && Math.abs(scaledValue - lastValue) < 0.01) {
        return; // Skip small changes
      }

      this.lastMIDIValues.set(cc, scaledValue);

      // Call handler
      mapping.handler(scaledValue);

      console.log(`[KeyboardMIDIControl] MIDI CC${cc} (${mapping.name}): ${scaledValue.toFixed(3)}`);
    }
  }

  /**
   * Show keyboard shortcuts help
   */
  showHelp() {
    const helpText = Object.entries(this.keyBindings)
      .map(([key, binding]) => `${key.padEnd(15)} - ${binding.description}`)
      .join('\n');

    alert(`KEYBOARD SHORTCUTS:\n\n${helpText}`);
  }

  /**
   * Add custom key binding
   * @param {string} key - Key identifier
   * @param {string} description - Action description
   * @param {function} action - Action callback
   */
  addKeyBinding(key, description, action) {
    this.keyBindings[key] = { description, action };
    console.log(`[KeyboardMIDIControl] Added key binding: ${key} - ${description}`);
  }

  /**
   * Add custom MIDI CC mapping
   * @param {number} cc - CC number
   * @param {string} name - Parameter name
   * @param {number} min - Minimum value
   * @param {number} max - Maximum value
   * @param {function} handler - Value change handler
   */
  addMIDIMapping(cc, name, min, max, handler) {
    this.midiMappings[cc] = { name, min, max, handler };
    console.log(`[KeyboardMIDIControl] Added MIDI mapping: CC${cc} - ${name}`);
  }

  /**
   * Get MIDI status
   * @returns {object} MIDI status
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
        name: input.name,
        manufacturer: input.manufacturer,
        state: input.state
      }))
    };
  }

  /**
   * Get active key bindings
   * @returns {object} Key bindings
   */
  getKeyBindings() {
    return Object.entries(this.keyBindings).map(([key, binding]) => ({
      key,
      description: binding.description
    }));
  }

  /**
   * Get MIDI CC mappings
   * @returns {object} MIDI mappings
   */
  getMIDIMappings() {
    return Object.entries(this.midiMappings).map(([cc, mapping]) => ({
      cc: parseInt(cc),
      name: mapping.name,
      min: mapping.min,
      max: mapping.max
    }));
  }

  /**
   * Cleanup
   */
  destroy() {
    document.removeEventListener('keydown', this.handleKeyDown);
    document.removeEventListener('keyup', this.handleKeyUp);

    if (this.midiAccess) {
      for (const input of this.midiAccess.inputs.values()) {
        input.onmidimessage = null;
      }
    }

    console.log('[KeyboardMIDIControl] Destroyed');
  }
}

/**
 * Create and initialize Keyboard/MIDI Control
 * @param {object} callbacks - Event callbacks
 * @returns {KeyboardMIDIControl} Control instance
 */
export function createKeyboardMIDIControl(callbacks) {
  return new KeyboardMIDIControl(callbacks);
}
