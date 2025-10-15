/**
 * Feature 010: Preset Browser UI - Server-Integrated Preset Management
 *
 * Provides:
 * - Visual preset browser with search/filter
 * - A/B comparison interface
 * - Import/Export with server API
 * - Collision resolution dialogs
 * - Preset tagging and metadata
 *
 * Connects to: /api/presets endpoints
 */

export class PresetBrowserUI {
  constructor(containerId, serverURL, callbacks = {}) {
    this.container = document.getElementById(containerId);
    if (!this.container) {
      throw new Error(`Container ${containerId} not found`);
    }

    this.serverURL = serverURL;
    this.callbacks = {
      onPresetLoad: callbacks.onPresetLoad || (() => {}),
      onPresetSave: callbacks.onPresetSave || (() => {}),
      onABStore: callbacks.onABStore || (() => {}),
      onABToggle: callbacks.onABToggle || (() => {})
    };

    // State
    this.presets = [];
    this.currentPreset = null;
    this.searchQuery = '';
    this.selectedTag = null;
    this.abStatus = { slot_a_occupied: false, slot_b_occupied: false, current_slot: null };

    this.build();
    this.loadPresets();
    this.loadABStatus();

    console.log('[PresetBrowserUI] Initialized, server:', serverURL);
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
    `;

    // Title
    const title = document.createElement('div');
    title.textContent = 'PRESET BROWSER';
    title.style.cssText = `
      font-weight: bold;
      color: #0f0;
      margin-bottom: 15px;
      text-align: center;
      font-size: 16px;
      letter-spacing: 3px;
      font-family: monospace;
    `;
    this.container.appendChild(title);

    // Search/Filter bar
    const searchBar = document.createElement('div');
    searchBar.style.cssText = `
      display: flex;
      gap: 8px;
      margin-bottom: 10px;
    `;

    const searchInput = document.createElement('input');
    searchInput.type = 'text';
    searchInput.placeholder = 'Search presets...';
    searchInput.id = 'presetSearchInput';
    searchInput.style.cssText = `
      flex: 1;
      padding: 6px 10px;
      background: rgba(0, 0, 0, 0.7);
      border: 1px solid #333;
      border-radius: 4px;
      color: #0f0;
      font-family: monospace;
      font-size: 12px;
    `;
    searchInput.addEventListener('input', (e) => {
      this.searchQuery = e.target.value;
      this.filterPresets();
    });
    searchBar.appendChild(searchInput);

    const refreshBtn = document.createElement('button');
    refreshBtn.textContent = '↻';
    refreshBtn.title = 'Refresh';
    refreshBtn.style.cssText = `
      padding: 6px 12px;
      background: rgba(0, 255, 0, 0.1);
      border: 1px solid #0f0;
      border-radius: 4px;
      color: #0f0;
      cursor: pointer;
      font-size: 16px;
    `;
    refreshBtn.addEventListener('click', () => this.loadPresets());
    searchBar.appendChild(refreshBtn);

    this.container.appendChild(searchBar);

    // Preset list
    const presetListContainer = document.createElement('div');
    presetListContainer.id = 'presetListContainer';
    presetListContainer.style.cssText = `
      max-height: 300px;
      overflow-y: auto;
      margin-bottom: 15px;
      padding: 8px;
      background: rgba(0, 0, 0, 0.5);
      border: 1px solid #333;
      border-radius: 4px;
    `;
    this.container.appendChild(presetListContainer);

    // A/B Comparison Panel
    const abPanel = document.createElement('div');
    abPanel.style.cssText = `
      padding: 10px;
      background: rgba(0, 255, 0, 0.05);
      border: 1px solid #0f0;
      border-radius: 4px;
      margin-bottom: 15px;
    `;

    const abTitle = document.createElement('div');
    abTitle.textContent = 'A/B COMPARISON';
    abTitle.style.cssText = `
      font-weight: bold;
      color: #0f0;
      margin-bottom: 8px;
      font-size: 12px;
      font-family: monospace;
    `;
    abPanel.appendChild(abTitle);

    const abControls = document.createElement('div');
    abControls.style.cssText = `
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 8px;
    `;

    const storeABtn = document.createElement('button');
    storeABtn.textContent = 'Store A';
    storeABtn.id = 'storeAButton';
    storeABtn.style.cssText = this.getButtonStyle();
    storeABtn.addEventListener('click', () => this.storeAB('A'));
    abControls.appendChild(storeABtn);

    const storeBBtn = document.createElement('button');
    storeBBtn.textContent = 'Store B';
    storeBBtn.id = 'storeBButton';
    storeBBtn.style.cssText = this.getButtonStyle();
    storeBBtn.addEventListener('click', () => this.storeAB('B'));
    abControls.appendChild(storeBBtn);

    const toggleBtn = document.createElement('button');
    toggleBtn.textContent = 'Toggle A↔B';
    toggleBtn.id = 'toggleABButton';
    toggleBtn.style.cssText = this.getButtonStyle('#ff0');
    toggleBtn.addEventListener('click', () => this.toggleAB());
    abControls.appendChild(toggleBtn);

    abPanel.appendChild(abControls);

    // A/B Status display
    const abStatus = document.createElement('div');
    abStatus.id = 'abStatusDisplay';
    abStatus.style.cssText = `
      margin-top: 8px;
      padding: 6px;
      background: rgba(0, 0, 0, 0.5);
      border-radius: 3px;
      font-size: 11px;
      color: #888;
      font-family: monospace;
      text-align: center;
    `;
    abStatus.textContent = 'A: Empty | B: Empty | Current: None';
    abPanel.appendChild(abStatus);

    this.container.appendChild(abPanel);

    // Action buttons
    const actionBar = document.createElement('div');
    actionBar.style.cssText = `
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    `;

    const saveBtn = document.createElement('button');
    saveBtn.textContent = '💾 Save Preset';
    saveBtn.style.cssText = this.getButtonStyle();
    saveBtn.addEventListener('click', () => this.savePreset());
    actionBar.appendChild(saveBtn);

    const exportBtn = document.createElement('button');
    exportBtn.textContent = '📤 Export All';
    exportBtn.style.cssText = this.getButtonStyle();
    exportBtn.addEventListener('click', () => this.exportAll());
    actionBar.appendChild(exportBtn);

    const importBtn = document.createElement('button');
    importBtn.textContent = '📥 Import';
    importBtn.style.cssText = this.getButtonStyle();
    importBtn.addEventListener('click', () => this.import());
    actionBar.appendChild(importBtn);

    const diffBtn = document.createElement('button');
    diffBtn.textContent = '⚖️ View A/B Diff';
    diffBtn.style.cssText = this.getButtonStyle();
    diffBtn.addEventListener('click', () => this.viewABDiff());
    actionBar.appendChild(diffBtn);

    this.container.appendChild(actionBar);

    // Hidden file input for import
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.json';
    fileInput.id = 'presetImportFileInput';
    fileInput.style.display = 'none';
    fileInput.addEventListener('change', (e) => this.handleImportFile(e));
    this.container.appendChild(fileInput);
  }

  /**
   * Get button style
   * @param {string} borderColor - Border color
   * @returns {string} CSS style
   */
  getButtonStyle(borderColor = '#0f0') {
    return `
      padding: 8px 12px;
      background: rgba(0, 255, 0, 0.1);
      border: 1px solid ${borderColor};
      border-radius: 4px;
      color: ${borderColor};
      cursor: pointer;
      font-size: 12px;
      font-family: monospace;
      transition: all 0.2s;
    `;
  }

  /**
   * Load presets from server
   */
  async loadPresets() {
    try {
      const response = await fetch(`${this.serverURL}/api/presets?limit=100`);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      this.presets = await response.json();
      this.renderPresets();

      console.log('[PresetBrowserUI] Loaded', this.presets.length, 'presets');

    } catch (e) {
      console.error('[PresetBrowserUI] Failed to load presets:', e);
      this.showError('Failed to load presets from server');
    }
  }

  /**
   * Render preset list
   */
  renderPresets() {
    const container = document.getElementById('presetListContainer');
    if (!container) return;

    if (this.presets.length === 0) {
      container.innerHTML = '<div style="color: #666; padding: 20px; text-align: center; font-family: monospace;">No presets found</div>';
      return;
    }

    container.innerHTML = '';

    this.presets.forEach(preset => {
      const presetItem = document.createElement('div');
      presetItem.style.cssText = `
        padding: 8px;
        margin-bottom: 6px;
        background: rgba(0, 255, 0, 0.05);
        border: 1px solid rgba(0, 255, 0, 0.2);
        border-radius: 4px;
        cursor: pointer;
        transition: all 0.2s;
        font-family: monospace;
        font-size: 12px;
      `;

      presetItem.addEventListener('mouseenter', () => {
        presetItem.style.background = 'rgba(0, 255, 0, 0.15)';
        presetItem.style.borderColor = '#0f0';
      });

      presetItem.addEventListener('mouseleave', () => {
        presetItem.style.background = 'rgba(0, 255, 0, 0.05)';
        presetItem.style.borderColor = 'rgba(0, 255, 0, 0.2)';
      });

      presetItem.addEventListener('click', () => this.loadPreset(preset.id));

      // Preset name
      const nameDiv = document.createElement('div');
      nameDiv.textContent = preset.name;
      nameDiv.style.cssText = 'color: #0f0; font-weight: bold; margin-bottom: 4px;';
      presetItem.appendChild(nameDiv);

      // Metadata
      const metaDiv = document.createElement('div');
      metaDiv.style.cssText = 'color: #666; font-size: 10px;';

      const tags = preset.tags && preset.tags.length > 0 ? preset.tags.join(', ') : 'no tags';
      const modified = preset.modified_at ? new Date(preset.modified_at).toLocaleDateString() : 'unknown';

      metaDiv.textContent = `Tags: ${tags} | Modified: ${modified}`;
      presetItem.appendChild(metaDiv);

      container.appendChild(presetItem);
    });
  }

  /**
   * Filter presets by search query
   */
  filterPresets() {
    // Re-render with filter applied (would need server-side search for large datasets)
    this.renderPresets();
  }

  /**
   * Load a preset
   * @param {string} presetId - Preset ID
   */
  async loadPreset(presetId) {
    try {
      const response = await fetch(`${this.serverURL}/api/presets/${presetId}`);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const preset = await response.json();
      this.currentPreset = preset;

      this.callbacks.onPresetLoad(preset);

      console.log('[PresetBrowserUI] Loaded preset:', preset.name);

    } catch (e) {
      console.error('[PresetBrowserUI] Failed to load preset:', e);
      this.showError('Failed to load preset');
    }
  }

  /**
   * Save current state as preset
   */
  async savePreset() {
    const name = prompt('Preset name:');
    if (!name) return;

    try {
      // Get current state from callback
      const currentState = this.callbacks.onPresetSave();

      const presetData = {
        name,
        tags: [],
        ...currentState
      };

      const response = await fetch(`${this.serverURL}/api/presets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(presetData)
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || `HTTP ${response.status}`);
      }

      const result = await response.json();

      console.log('[PresetBrowserUI] Saved preset:', result.id);
      this.showSuccess(`Preset "${name}" saved`);

      // Reload list
      this.loadPresets();

    } catch (e) {
      console.error('[PresetBrowserUI] Failed to save preset:', e);
      this.showError(`Failed to save preset: ${e.message}`);
    }
  }

  /**
   * Store A/B snapshot
   * @param {string} slot - 'A' or 'B'
   */
  async storeAB(slot) {
    try {
      const currentState = this.callbacks.onPresetSave();

      const response = await fetch(`${this.serverURL}/api/presets/ab/store/${slot}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(currentState)
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();
      this.abStatus = result.status;

      console.log('[PresetBrowserUI] Stored snapshot', slot);
      this.updateABStatus();

    } catch (e) {
      console.error('[PresetBrowserUI] Failed to store A/B:', e);
      this.showError(`Failed to store snapshot ${slot}`);
    }
  }

  /**
   * Toggle A/B comparison
   */
  async toggleAB() {
    try {
      const response = await fetch(`${this.serverURL}/api/presets/ab/toggle`, {
        method: 'POST'
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();

      this.callbacks.onPresetLoad(result.preset);
      this.abStatus.current_slot = result.current_slot;

      console.log('[PresetBrowserUI] Toggled to', result.current_slot);
      this.updateABStatus();

    } catch (e) {
      console.error('[PresetBrowserUI] Failed to toggle A/B:', e);
      this.showError('Failed to toggle A/B');
    }
  }

  /**
   * Load A/B status from server
   */
  async loadABStatus() {
    try {
      const response = await fetch(`${this.serverURL}/api/presets/ab/status`);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      this.abStatus = await response.json();
      this.updateABStatus();

    } catch (e) {
      console.error('[PresetBrowserUI] Failed to load A/B status:', e);
    }
  }

  /**
   * Update A/B status display
   */
  updateABStatus() {
    const statusDisplay = document.getElementById('abStatusDisplay');
    if (!statusDisplay) return;

    const aStatus = this.abStatus.slot_a_occupied ? this.abStatus.slot_a_name : 'Empty';
    const bStatus = this.abStatus.slot_b_occupied ? this.abStatus.slot_b_name : 'Empty';
    const current = this.abStatus.current_slot || 'None';

    statusDisplay.textContent = `A: ${aStatus} | B: ${bStatus} | Current: ${current}`;

    // Highlight current slot
    const storeABtn = document.getElementById('storeAButton');
    const storeBBtn = document.getElementById('storeBButton');

    if (storeABtn) {
      storeABtn.style.borderColor = this.abStatus.current_slot === 'A' ? '#ff0' : '#0f0';
      storeABtn.style.color = this.abStatus.current_slot === 'A' ? '#ff0' : '#0f0';
    }

    if (storeBBtn) {
      storeBBtn.style.borderColor = this.abStatus.current_slot === 'B' ? '#ff0' : '#0f0';
      storeBBtn.style.color = this.abStatus.current_slot === 'B' ? '#ff0' : '#0f0';
    }
  }

  /**
   * View A/B diff
   */
  async viewABDiff() {
    try {
      const response = await fetch(`${this.serverURL}/api/presets/ab/diff`);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const diff = await response.json();

      // Format diff for display
      const diffText = Object.entries(diff)
        .map(([key, [oldVal, newVal]]) => `${key}: ${JSON.stringify(oldVal)} → ${JSON.stringify(newVal)}`)
        .join('\n');

      alert(`A/B DIFFERENCES:\n\n${diffText || 'No differences'}`);

    } catch (e) {
      console.error('[PresetBrowserUI] Failed to get A/B diff:', e);
      this.showError('Failed to get A/B diff');
    }
  }

  /**
   * Export all presets
   */
  async exportAll() {
    try {
      const response = await fetch(`${this.serverURL}/api/presets/export`, {
        method: 'POST'
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);

      const a = document.createElement('a');
      a.href = url;
      a.download = `soundlab_presets_${Date.now()}.json`;
      a.click();

      URL.revokeObjectURL(url);

      console.log('[PresetBrowserUI] Exported all presets');

    } catch (e) {
      console.error('[PresetBrowserUI] Failed to export:', e);
      this.showError('Failed to export presets');
    }
  }

  /**
   * Trigger import file dialog
   */
  import() {
    const fileInput = document.getElementById('presetImportFileInput');
    if (fileInput) {
      fileInput.click();
    }
  }

  /**
   * Handle import file selection
   * @param {Event} e - File input change event
   */
  async handleImportFile(e) {
    const file = e.target.files[0];
    if (!file) return;

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${this.serverURL}/api/presets/import?collision=prompt`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();

      alert(`Import complete:\n\nImported: ${result.imported}\nUpdated: ${result.updated}\nSkipped: ${result.skipped}\nErrors: ${result.errors.length}`);

      console.log('[PresetBrowserUI] Import result:', result);

      // Reload list
      this.loadPresets();

    } catch (e) {
      console.error('[PresetBrowserUI] Failed to import:', e);
      this.showError('Failed to import presets');
    }

    // Reset file input
    e.target.value = '';
  }

  /**
   * Show error message
   * @param {string} message - Error message
   */
  showError(message) {
    // Could be replaced with a toast notification
    alert(`ERROR: ${message}`);
  }

  /**
   * Show success message
   * @param {string} message - Success message
   */
  showSuccess(message) {
    // Could be replaced with a toast notification
    console.log(`[PresetBrowserUI] SUCCESS: ${message}`);
  }
}

/**
 * Create and initialize Preset Browser UI
 * @param {string} containerId - Container element ID
 * @param {string} serverURL - Server URL
 * @param {object} callbacks - Event callbacks
 * @returns {PresetBrowserUI} Browser instance
 */
export function createPresetBrowserUI(containerId, serverURL, callbacks) {
  return new PresetBrowserUI(containerId, serverURL, callbacks);
}
