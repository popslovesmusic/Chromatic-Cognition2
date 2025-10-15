/**
 * Feature 010: Preset Browser UI
 *
 * Browser-based preset manager for saving, loading, and managing
 * complete Soundlab parameter states.
 *
 * Features:
 * - FR-001: Preset list UI and file storage
 * - FR-002: JSON map of all parameters (Feature 007)
 * - FR-003: localStorage + file export/import
 * - FR-004: Sync via /ws/ui ("apply_preset" type)
 * - FR-005: Refresh, delete, export-all actions
 * - FR-006: Versioned format (version: 1.0)
 *
 * Success Criteria:
 * - SC-001: No desync or data loss
 * - SC-002: Full restoration < 200ms
 * - SC-003: Export/import preserves values
 * - SC-004: Persistent across reloads
 */

export class PresetBrowser {
  constructor(containerId, websocketURL, options = {}) {
    this.containerId = containerId;
    this.websocketURL = websocketURL;
    this.options = {
      enablePersistence: true,
      persistenceKey: 'soundlab_presets',
      autoConnect: true,
      ...options
    };

    // WebSocket connection
    this.ws = null;
    this.connected = false;
    this.reconnectTimeout = null;
    this.reconnectDelay = 2000;

    // Preset storage
    this.presets = {};
    this.currentPresetName = null;

    // Default parameter structure (from Feature 007)
    this.defaultParameters = this.getDefaultParameters();

    // Load presets from localStorage (FR-003)
    if (this.options.enablePersistence) {
      this.loadPresetsFromStorage();
    }

    // Initialize UI
    this.initializeUI();

    // Connect to WebSocket (FR-004)
    if (this.options.autoConnect) {
      this.connect();
    }

    console.log('[PresetBrowser] Initialized');
  }

  /**
   * Get default parameter structure (Feature 007)
   */
  getDefaultParameters() {
    const params = {
      version: '1.0',  // FR-006: Version field
      timestamp: Date.now(),
      channels: {},
      global: {},
      phi: {}
    };

    // Channel parameters (0-7)
    for (let i = 0; i < 8; i++) {
      params.channels[i] = {
        frequency: 440.0,
        amplitude: 0.5,
        enabled: true
      };
    }

    // Global parameters
    params.global = {
      coupling_strength: 1.0,
      gain: 1.0
    };

    // Phi parameters
    params.phi = {
      phase: 0.5,
      depth: 0.5
    };

    return params;
  }

  /**
   * Initialize UI elements
   */
  initializeUI() {
    const container = document.getElementById(this.containerId);
    if (!container) {
      console.error('[PresetBrowser] Container not found:', this.containerId);
      return;
    }

    container.innerHTML = `
      <div class="preset-browser">
        <div class="preset-browser-header">
          <h3>Preset Browser</h3>
          <div class="preset-browser-status">
            <span id="presetBrowserStatus">🔴 Disconnected</span>
          </div>
        </div>

        <div class="preset-browser-actions">
          <button id="presetSaveBtn" class="btn btn-primary">💾 Save</button>
          <button id="presetRefreshBtn" class="btn btn-secondary">🔄 Refresh</button>
          <button id="presetExportBtn" class="btn btn-secondary">📤 Export All</button>
          <button id="presetImportBtn" class="btn btn-secondary">📥 Import</button>
          <input type="file" id="presetImportFile" accept=".json" style="display: none;">
        </div>

        <div class="preset-browser-list">
          <div id="presetListContainer">
            <p class="preset-empty">No presets saved</p>
          </div>
        </div>

        <div class="preset-browser-info">
          <p>Presets: <span id="presetCount">0</span></p>
          <p>Current: <span id="presetCurrent">None</span></p>
        </div>
      </div>
    `;

    // Attach event listeners
    this.attachEventListeners();

    // Render preset list
    this.renderPresetList();
  }

  /**
   * Attach event listeners
   */
  attachEventListeners() {
    // Save button
    const saveBtn = document.getElementById('presetSaveBtn');
    if (saveBtn) {
      saveBtn.addEventListener('click', () => this.showSaveDialog());
    }

    // Refresh button
    const refreshBtn = document.getElementById('presetRefreshBtn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.refreshPresetList());
    }

    // Export button
    const exportBtn = document.getElementById('presetExportBtn');
    if (exportBtn) {
      exportBtn.addEventListener('click', () => this.exportAllPresets());
    }

    // Import button
    const importBtn = document.getElementById('presetImportBtn');
    if (importBtn) {
      importBtn.addEventListener('click', () => {
        const fileInput = document.getElementById('presetImportFile');
        if (fileInput) fileInput.click();
      });
    }

    // Import file input
    const fileInput = document.getElementById('presetImportFile');
    if (fileInput) {
      fileInput.addEventListener('change', (e) => this.handleImportFile(e));
    }
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
        console.log('[PresetBrowser] WebSocket connected');
        this.connected = true;
        this.updateStatus('🟢 Connected');

        if (this.reconnectTimeout) {
          clearTimeout(this.reconnectTimeout);
          this.reconnectTimeout = null;
        }
      };

      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        this.handleWebSocketMessage(data);
      };

      this.ws.onclose = () => {
        console.log('[PresetBrowser] WebSocket closed');
        this.connected = false;
        this.updateStatus('🔴 Disconnected');
        this.attemptReconnect();
      };

      this.ws.onerror = (error) => {
        console.error('[PresetBrowser] WebSocket error:', error);
      };

    } catch (e) {
      console.error('[PresetBrowser] Connection failed:', e);
      this.attemptReconnect();
    }
  }

  /**
   * Attempt reconnect
   */
  attemptReconnect() {
    if (this.reconnectTimeout) return;

    this.reconnectTimeout = setTimeout(() => {
      console.log('[PresetBrowser] Reconnecting...');
      this.connect();
    }, this.reconnectDelay);
  }

  /**
   * Handle WebSocket message
   */
  handleWebSocketMessage(data) {
    if (data.type === 'state') {
      // Current state received
      console.log('[PresetBrowser] Received current state');
    } else if (data.type === 'preset_applied') {
      // Preset applied confirmation
      console.log('[PresetBrowser] Preset applied:', data.success);
      if (data.success) {
        this.currentPresetName = data.preset_name || null;
        this.updateCurrentPreset();
      }
    }
  }

  /**
   * Update status display
   */
  updateStatus(status) {
    const statusEl = document.getElementById('presetBrowserStatus');
    if (statusEl) {
      statusEl.textContent = status;
    }
  }

  /**
   * Get current parameters from server
   */
  async getCurrentParameters() {
    return new Promise((resolve, reject) => {
      if (!this.connected || !this.ws) {
        reject(new Error('Not connected'));
        return;
      }

      // Request current state
      const message = { type: 'get_state' };

      // Set up one-time listener for response
      const onMessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'state') {
          this.ws.removeEventListener('message', onMessage);
          resolve(data.parameters || this.defaultParameters);
        }
      };

      this.ws.addEventListener('message', onMessage);
      this.ws.send(JSON.stringify(message));

      // Timeout after 1 second
      setTimeout(() => {
        this.ws.removeEventListener('message', onMessage);
        reject(new Error('Timeout getting parameters'));
      }, 1000);
    });
  }

  /**
   * Show save dialog
   */
  showSaveDialog() {
    const name = prompt('Enter preset name:');
    if (!name) return;

    // Check for duplicate (Edge case: overwrite confirmation)
    if (this.presets[name]) {
      const confirmed = confirm(`Preset "${name}" already exists. Overwrite?`);
      if (!confirmed) return;
    }

    this.savePreset(name);
  }

  /**
   * Save current parameters as preset (FR-001, FR-002)
   */
  async savePreset(name) {
    try {
      // Get current parameters from server
      let parameters;
      try {
        parameters = await this.getCurrentParameters();
      } catch (e) {
        console.warn('[PresetBrowser] Could not get server state, using defaults');
        parameters = { ...this.defaultParameters };
      }

      // Create preset object (FR-006: versioned)
      const preset = {
        version: '1.0',
        name: name,
        timestamp: Date.now(),
        parameters: parameters
      };

      // Store preset
      this.presets[name] = preset;

      // Persist to localStorage (FR-003)
      if (this.options.enablePersistence) {
        this.savePresetsToStorage();
      }

      // Update UI
      this.renderPresetList();
      this.currentPresetName = name;
      this.updateCurrentPreset();

      console.log(`[PresetBrowser] Saved preset: ${name}`);

    } catch (e) {
      console.error('[PresetBrowser] Failed to save preset:', e);
      alert('Failed to save preset: ' + e.message);
    }
  }

  /**
   * Load preset and apply to engine (FR-004)
   */
  loadPreset(name) {
    const preset = this.presets[name];
    if (!preset) {
      console.error('[PresetBrowser] Preset not found:', name);
      return;
    }

    const startTime = performance.now();

    try {
      // Apply preset via WebSocket (SC-002: < 200ms)
      this.applyPreset(preset);

      const latency = performance.now() - startTime;
      console.log(`[PresetBrowser] Loaded preset: ${name} (${latency.toFixed(2)}ms)`);

      this.currentPresetName = name;
      this.updateCurrentPreset();

    } catch (e) {
      console.error('[PresetBrowser] Failed to load preset:', e);
      alert('Failed to load preset: ' + e.message);
    }
  }

  /**
   * Apply preset to engine via WebSocket (FR-004)
   */
  applyPreset(preset) {
    if (!this.connected || !this.ws) {
      throw new Error('Not connected to server');
    }

    // Validate preset structure (Edge case: missing values)
    const parameters = this.validateParameters(preset.parameters);

    // Send apply_preset message
    const message = {
      type: 'apply_preset',
      preset_name: preset.name,
      parameters: parameters
    };

    this.ws.send(JSON.stringify(message));
  }

  /**
   * Validate parameters and fill missing with defaults
   * Edge case: missing values replaced with defaults
   */
  validateParameters(parameters) {
    const validated = JSON.parse(JSON.stringify(this.defaultParameters));

    if (!parameters) return validated;

    // Merge channels
    if (parameters.channels) {
      for (let i = 0; i < 8; i++) {
        if (parameters.channels[i]) {
          validated.channels[i] = {
            ...validated.channels[i],
            ...parameters.channels[i]
          };
        }
      }
    }

    // Merge global
    if (parameters.global) {
      validated.global = {
        ...validated.global,
        ...parameters.global
      };
    }

    // Merge phi
    if (parameters.phi) {
      validated.phi = {
        ...validated.phi,
        ...parameters.phi
      };
    }

    return validated;
  }

  /**
   * Delete preset
   */
  deletePreset(name) {
    const confirmed = confirm(`Delete preset "${name}"?`);
    if (!confirmed) return;

    delete this.presets[name];

    // Persist to localStorage
    if (this.options.enablePersistence) {
      this.savePresetsToStorage();
    }

    // Clear current if deleted
    if (this.currentPresetName === name) {
      this.currentPresetName = null;
      this.updateCurrentPreset();
    }

    // Update UI
    this.renderPresetList();

    console.log(`[PresetBrowser] Deleted preset: ${name}`);
  }

  /**
   * Export all presets to JSON file (FR-003, FR-005)
   */
  exportAllPresets() {
    if (Object.keys(this.presets).length === 0) {
      alert('No presets to export');
      return;
    }

    const exportData = {
      version: '1.0',  // FR-006: Version field
      exported: Date.now(),
      presets: this.presets
    };

    const json = JSON.stringify(exportData, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `soundlab-presets-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    console.log('[PresetBrowser] Exported all presets');
  }

  /**
   * Export single preset
   */
  exportPreset(name) {
    const preset = this.presets[name];
    if (!preset) return;

    const json = JSON.stringify(preset, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `soundlab-preset-${name}-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    console.log(`[PresetBrowser] Exported preset: ${name}`);
  }

  /**
   * Handle import file selection
   */
  handleImportFile(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();

    reader.onload = (e) => {
      try {
        const json = e.target.result;
        this.importPresets(json);
      } catch (err) {
        console.error('[PresetBrowser] Import error:', err);
        alert('Failed to import presets: ' + err.message);
      }
    };

    reader.readAsText(file);

    // Reset file input
    event.target.value = '';
  }

  /**
   * Import presets from JSON (FR-003)
   * Edge case: Invalid JSON ignored with message
   */
  importPresets(json) {
    try {
      const data = JSON.parse(json);

      // Validate format
      if (!data.version) {
        throw new Error('Invalid preset format: missing version');
      }

      // Import individual preset or collection
      let imported = 0;

      if (data.presets) {
        // Collection of presets
        for (const [name, preset] of Object.entries(data.presets)) {
          if (this.validatePresetStructure(preset)) {
            // Check for duplicate (overwrite confirmation)
            if (this.presets[name]) {
              const confirmed = confirm(`Preset "${name}" already exists. Overwrite?`);
              if (!confirmed) continue;
            }

            this.presets[name] = preset;
            imported++;
          }
        }
      } else if (data.name && data.parameters) {
        // Single preset
        if (this.validatePresetStructure(data)) {
          if (this.presets[data.name]) {
            const confirmed = confirm(`Preset "${data.name}" already exists. Overwrite?`);
            if (!confirmed) return;
          }

          this.presets[data.name] = data;
          imported++;
        }
      } else {
        throw new Error('Invalid preset format: missing name or parameters');
      }

      // Persist to localStorage
      if (this.options.enablePersistence) {
        this.savePresetsToStorage();
      }

      // Update UI
      this.renderPresetList();

      console.log(`[PresetBrowser] Imported ${imported} preset(s)`);
      alert(`Successfully imported ${imported} preset(s)`);

    } catch (e) {
      console.error('[PresetBrowser] Invalid JSON:', e);
      alert('Invalid preset file: ' + e.message);
    }
  }

  /**
   * Validate preset structure
   */
  validatePresetStructure(preset) {
    if (!preset.version) return false;
    if (!preset.name) return false;
    if (!preset.parameters) return false;

    return true;
  }

  /**
   * Refresh preset list (FR-005)
   */
  refreshPresetList() {
    if (this.options.enablePersistence) {
      this.loadPresetsFromStorage();
    }

    this.renderPresetList();

    console.log('[PresetBrowser] Refreshed preset list');
  }

  /**
   * Render preset list
   */
  renderPresetList() {
    const container = document.getElementById('presetListContainer');
    if (!container) return;

    const presetNames = Object.keys(this.presets).sort();

    if (presetNames.length === 0) {
      container.innerHTML = '<p class="preset-empty">No presets saved</p>';
    } else {
      container.innerHTML = presetNames.map(name => {
        const preset = this.presets[name];
        const date = new Date(preset.timestamp).toLocaleString();
        const isCurrent = this.currentPresetName === name;

        return `
          <div class="preset-item ${isCurrent ? 'preset-current' : ''}">
            <div class="preset-info">
              <strong>${name}</strong>
              <small>${date}</small>
            </div>
            <div class="preset-actions">
              <button class="btn-small" onclick="window.presetBrowser.loadPreset('${name}')">Load</button>
              <button class="btn-small" onclick="window.presetBrowser.exportPreset('${name}')">Export</button>
              <button class="btn-small btn-danger" onclick="window.presetBrowser.deletePreset('${name}')">Delete</button>
            </div>
          </div>
        `;
      }).join('');
    }

    // Update count
    const countEl = document.getElementById('presetCount');
    if (countEl) {
      countEl.textContent = presetNames.length;
    }
  }

  /**
   * Update current preset display
   */
  updateCurrentPreset() {
    const currentEl = document.getElementById('presetCurrent');
    if (currentEl) {
      currentEl.textContent = this.currentPresetName || 'None';
    }

    // Update UI highlighting
    this.renderPresetList();
  }

  /**
   * Save presets to localStorage (FR-003)
   */
  savePresetsToStorage() {
    if (!this.options.enablePersistence) return;

    try {
      const data = {
        version: '1.0',
        timestamp: Date.now(),
        presets: this.presets
      };

      localStorage.setItem(this.options.persistenceKey, JSON.stringify(data));
      console.log('[PresetBrowser] Saved to localStorage');
    } catch (e) {
      console.error('[PresetBrowser] Failed to save to localStorage:', e);
    }
  }

  /**
   * Load presets from localStorage (FR-003, SC-004)
   */
  loadPresetsFromStorage() {
    if (!this.options.enablePersistence) return;

    try {
      const stored = localStorage.getItem(this.options.persistenceKey);
      if (stored) {
        const data = JSON.parse(stored);

        if (data.version && data.presets) {
          this.presets = data.presets;
          console.log('[PresetBrowser] Loaded from localStorage:', Object.keys(this.presets).length, 'presets');
        }
      }
    } catch (e) {
      console.error('[PresetBrowser] Failed to load from localStorage:', e);
    }
  }

  /**
   * Get all presets
   */
  getPresets() {
    return this.presets;
  }

  /**
   * Get preset by name
   */
  getPreset(name) {
    return this.presets[name] || null;
  }

  /**
   * Clear all presets
   */
  clearAllPresets() {
    const confirmed = confirm('Delete ALL presets? This cannot be undone.');
    if (!confirmed) return;

    this.presets = {};
    this.currentPresetName = null;

    if (this.options.enablePersistence) {
      this.savePresetsToStorage();
    }

    this.renderPresetList();
    this.updateCurrentPreset();

    console.log('[PresetBrowser] Cleared all presets');
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

    console.log('[PresetBrowser] Disconnected');
  }
}

/**
 * Create and initialize Preset Browser
 */
export function createPresetBrowser(containerId, websocketURL, options) {
  const browser = new PresetBrowser(containerId, websocketURL, options);

  // Expose globally for onclick handlers
  window.presetBrowser = browser;

  return browser;
}
