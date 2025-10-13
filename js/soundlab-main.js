import { initLogging } from './soundlab-logging.js';
import { updateMatrix } from './soundlab-audio-core.js';
import { initializeEventHandlers } from './soundlab-events.js';

const FALLBACK_PARTIALS = {
  'partials/config-loader.html': `
<div class="dropdown-container">
  <label for="configSelect">Select Config:</label>
  <select id="configSelect" class="form-field__control">
    <option value="">-- Choose a Config --</option>
    <option value="phi_tone_run_01_with_history.json">phi_tone_run_01</option>
  </select>
  <pre id="preview" class="config-preview">No config loaded.</pre>
</div>
`,
  'partials/transport-controls.html': `
<div class="controls" role="group" aria-label="Primary transport and utility controls">
  <button
    id="startBtn"
    type="button"
    aria-label="Start audio engine (Control+Shift+S)"
    aria-keyshortcuts="Control+Shift+S"
    data-shortcut="Ctrl+Shift+S"
    data-shortcut-label="Start audio"
  >
    Start Audio
  </button>
  <button
    id="generateBtn"
    type="button"
    disabled
    aria-label="Generate reference tone (Control+Shift+G)"
    aria-keyshortcuts="Control+Shift+G"
    data-shortcut="Ctrl+Shift+G"
    data-shortcut-label="Generate tone"
  >
    Generate Tone
  </button>
  <button
    id="stopBtn"
    type="button"
    disabled
    aria-label="Stop audio playback (Control+Shift+X)"
    aria-keyshortcuts="Control+Shift+X"
    data-shortcut="Ctrl+Shift+X"
    data-shortcut-label="Stop audio"
  >
    Stop
  </button>
  <input
    type="file"
    id="fileInput"
    class="input-hidden"
    accept="audio/*"
    aria-hidden="true"
    tabindex="-1"
  />
  <button
    id="loadBtn"
    type="button"
    disabled
    aria-label="Load audio file (Control+Shift+L)"
    aria-keyshortcuts="Control+Shift+L"
    aria-controls="fileInput"
    data-shortcut="Ctrl+Shift+L"
    data-shortcut-label="Load audio file"
  >
    Load Audio File
  </button>
  <input
    type="file"
    id="imageInput"
    class="input-hidden"
    accept="image/*"
    aria-hidden="true"
    tabindex="-1"
  />
  <button
    id="loadImageBtn"
    type="button"
    aria-label="Load image for sonification (Control+Shift+I)"
    aria-keyshortcuts="Control+Shift+I"
    aria-controls="imageInput"
    data-shortcut="Ctrl+Shift+I"
    data-shortcut-label="Load image"
  >
    Load Image → Sound
  </button>
  <button
    id="playImageBtn"
    type="button"
    disabled
    aria-label="Play or stop image sonification (Control+Shift+P)"
    aria-keyshortcuts="Control+Shift+P"
    data-shortcut="Ctrl+Shift+P"
    data-shortcut-label="Play image"
  >
    Play Image
  </button>
</div>

<div class="status" id="status" role="status" aria-live="polite">
  System Ready | Click START AUDIO to initialize
</div>
<div class="status-tip" id="statusTip">
  <span>💡 Tip: Click knob to select (cyan glow), then use ↑↓ arrows | Hold Shift for fine control, Ctrl for coarse</span>
  <span class="status-tip__shortcuts" id="shortcutLegend" aria-live="polite"></span>
</div>

<div class="panel panel--spaced" id="phiPanel">
  <h2>Φ Mode Generator</h2>
  <div class="phi-grid">
    <div class="phi-field">
      <label for="phiMode">Mode</label>
      <select id="phiMode">
        <option value="phi_tone">Pure Φ Tone</option>
        <option value="phi_AM">Φ AM Modulation</option>
        <option value="phi_FM">Φ FM Modulation</option>
        <option value="phi_interval">Φ Interval Stack</option>
        <option value="phi_harmonic">Φ Harmonic Series</option>
      </select>
    </div>
    <div class="phi-field">
      <label for="baseFreq">Base Frequency (Hz)</label>
      <input type="number" id="baseFreq" min="20" max="20000" step="1" value="220" />
    </div>
    <div class="phi-field">
      <label for="duration">Duration (s)</label>
      <input type="number" id="duration" min="0.1" step="0.1" value="3" />
    </div>
    <div class="phi-field">
      <label for="driveCurve">Drive Curve</label>
      <select id="driveCurve">
        <option value="linear">Linear</option>
        <option value="log">Log</option>
        <option value="exp">Exp</option>
      </select>
    </div>
    <div class="phi-field">
      <label for="frequencyRange">Frequency Range</label>
      <input type="text" id="frequencyRange" value="200-2000" placeholder="200-2000" />
    </div>
  </div>
  <div class="phi-actions" id="phiActions">
    <button
      id="runPhiBtn"
      type="button"
      aria-label="Run Φ mode selection (Control+Shift+M)"
      aria-keyshortcuts="Control+Shift+M"
      data-shortcut="Ctrl+Shift+M"
      data-shortcut-label="Run Φ mode"
    >
      Run Φ Mode
    </button>
    <button
      id="restoreParamsBtn"
      type="button"
      disabled
      aria-label="Restore previous Φ parameters (Control+Shift+R)"
      aria-keyshortcuts="Control+Shift+R"
      data-shortcut="Ctrl+Shift+R"
      data-shortcut-label="Restore Φ params"
    >
      Restore Previous
    </button>
    <button
      id="diagnosticBtn"
      type="button"
      aria-label="Run diagnostic output (Control+Shift+D)"
      aria-keyshortcuts="Control+Shift+D"
      data-shortcut="Ctrl+Shift+D"
      data-shortcut-label="Run diagnostic"
    >
      Run Diagnostic
    </button>
  </div>
</div>
`,
  'partials/eq-panel.html': `
<div class="panel">
  <h2>⚙ Spectral Control (EQ) ⚙</h2>
  <div class="knob-row">
    <div class="knob-container">
      <div class="knob-label">Low (100Hz)</div>
      <div class="knob" id="lowKnob" data-param="low" data-value="0" tabindex="0"></div>
      <div class="knob-value" id="lowValue">0 dB</div>
    </div>
    <div class="knob-container">
      <div class="knob-label">Mid (1kHz)</div>
      <div class="knob" id="midKnob" data-param="mid" data-value="0" tabindex="0"></div>
      <div class="knob-value" id="midValue">0 dB</div>
    </div>
    <div class="knob-container">
      <div class="knob-label">High (8kHz)</div>
      <div class="knob" id="highKnob" data-param="high" data-value="0" tabindex="0"></div>
      <div class="knob-value" id="highValue">0 dB</div>
    </div>
  </div>
</div>
`,
  'partials/saturation-panel.html': `
<div class="panel">
  <h2>⚡ Temporal Control (Saturation) ⚡</h2>
  <div class="knob-row">
    <div class="knob-container">
      <div class="knob-label">Drive</div>
      <div class="knob" id="driveKnob" data-param="drive" data-value="1" tabindex="0"></div>
      <div class="knob-value" id="driveValue">1.0x</div>
    </div>
    <div class="knob-container">
      <div class="knob-label">Curve</div>
      <div class="knob" id="curveKnob" data-param="curve" data-value="1" tabindex="0"></div>
      <div class="knob-value" id="curveValue">1.0</div>
    </div>
    <div class="knob-container">
      <div class="knob-label">Mix</div>
      <div class="knob" id="mixKnob" data-param="mix" data-value="0" tabindex="0"></div>
      <div class="knob-value" id="mixValue">0%</div>
    </div>
  </div>
</div>
`,
  'partials/image-sonification.html': `
<div class="panel panel--spaced panel--margin-bottom is-hidden" id="imagePanel">
  <h2>🖼️ Image Sonification Engine 🖼️</h2>
  <div class="image-layout">
    <div class="image-layout__pane">
      <canvas id="imageCanvas" class="image-canvas"></canvas>
      <div class="image-meta">
        <span id="imageInfo">No image loaded</span>
      </div>
    </div>
    <div class="image-layout__pane">
      <div class="form-field">
        <label class="form-field__label" for="sonifyMode">Sonification Mode:</label>
        <select id="sonifyMode" class="form-field__control">
          <option value="spectral">Spectral (Rows = Frequencies)</option>
          <option value="harmonic">Harmonic (Brightness = Harmonics)</option>
          <option value="fm">FM Synthesis (R→Freq, G→Mod, B→Index)</option>
          <option value="additive">Additive (Each pixel = Oscillator)</option>
        </select>
      </div>
      <div class="form-field">
        <label class="form-field__label" for="scanSpeed">Scan Speed:</label>
        <input type="range" id="scanSpeed" min="0.1" max="5" step="0.1" value="1" class="form-field__control" />
        <div class="image-meta" id="scanSpeedValue">1.0x</div>
      </div>
      <div class="form-field">
        <label class="form-field__label" for="freqMin">Frequency Range:</label>
        <div class="form-field--inline">
          <input type="number" id="freqMin" value="100" />
          <input type="number" id="freqMax" value="8000" />
        </div>
      </div>
      <div class="form-hint">
        <strong>How it works:</strong><br />
        • Image pixels → audio parameters<br />
        • Left to right = time progression<br />
        • Top to bottom = frequency spectrum<br />
        • Brightness controls amplitude or modulation depth
      </div>
    </div>
  </div>
</div>
`,
  'partials/visualizers.html': `
<div class="visualizer-grid">
  <div class="visualizer">
    <h3>Spectral Energy Distribution</h3>
    <canvas id="spectrumCanvas" width="600" height="300"></canvas>
  </div>
  <div class="visualizer">
    <h3>Temporal Waveform</h3>
    <canvas id="waveformCanvas" width="600" height="300"></canvas>
  </div>
</div>
`,
  'partials/log-and-matrix.html': `
<div class="matrix-display panel--spaced">
  <h3>CPWP Parameter Work Log</h3>
  <div class="log-actions">
    <button
      id="clearLogBtn"
      type="button"
      aria-label="Clear CPWP log entries (Control+Shift+C)"
      aria-keyshortcuts="Control+Shift+C"
      data-shortcut="Ctrl+Shift+C"
      data-shortcut-label="Clear log"
    >
      Clear Log
    </button>
    <button
      id="exportLogBtn"
      type="button"
      aria-label="Export log as CSV (Control+Shift+E)"
      aria-keyshortcuts="Control+Shift+E"
      data-shortcut="Ctrl+Shift+E"
      data-shortcut-label="Export CSV"
    >
      Export CSV
    </button>
    <button
      id="exportJsonBtn"
      type="button"
      aria-label="Export log as JSON (Control+Shift+J)"
      aria-keyshortcuts="Control+Shift+J"
      data-shortcut="Ctrl+Shift+J"
      data-shortcut-label="Export JSON"
    >
      Export JSON
    </button>
  </div>
  <div
    id="logDisplay"
    class="log-display"
    role="log"
    aria-live="polite"
    aria-atomic="false"
  >
    <div class="log-placeholder">Waiting for parameter changes...</div>
  </div>
  <div class="log-summary">
    <span id="logCount">0 events logged</span>
    <span id="workOutput">Total Work: 0.00</span>
  </div>
</div>

<div class="matrix-display panel--spaced">
  <h3>Parameter Coupling Matrix</h3>
  <div class="matrix" id="matrixGrid"></div>
</div>
`
};

async function loadPartial(element) {
  const url = element.getAttribute('data-include');
  if (!url) return;

  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to load ${url}: ${response.status}`);
    }
    const html = await response.text();
    element.innerHTML = html;
  } catch (error) {
    console.error(error);
    element.innerHTML = FALLBACK_PARTIALS[url] || `<div class="panel">Failed to load ${url}</div>`;
  }
}

async function loadPartials() {
  const includeElements = Array.from(document.querySelectorAll('[data-include]'));
  for (const element of includeElements) {
    await loadPartial(element);
  }
}

async function initializeSoundlab() {
  await loadPartials();
  updateMatrix();
  initLogging();
  initializeEventHandlers();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeSoundlab, { once: true });
} else {
  initializeSoundlab();
}
