# PROMPT 1: HTML Elements with Functional Roles

## Main Entry Point
**File:** `soundlab_v2.html`
- Entry script: `js/soundlab-main.js` (type="module")
- CSS: `soundlab-theme.css`, `soundlab-controls.css`, `soundlab-visuals.css`
- 7 partial includes via `data-include` attributes

---

## Functional Element Inventory

### 1. Transport Controls (`partials/transport-controls.html`)

#### Buttons (7)
- `#startBtn` - Initialize audio engine (Ctrl+Shift+S)
- `#generateBtn` - Generate reference tone (Ctrl+Shift+G) [disabled initially]
- `#stopBtn` - Stop audio (Ctrl+Shift+X) [disabled initially]
- `#loadBtn` - Load audio file (Ctrl+Shift+L) [disabled initially]
- `#loadImageBtn` - Load image (Ctrl+Shift+I)
- `#playImageBtn` - Play/stop image (Ctrl+Shift+P) [disabled initially]
- `#runPhiBtn` - Run Φ mode (Ctrl+Shift+M)
- `#restoreParamsBtn` - Restore Φ params (Ctrl+Shift+R) [disabled initially]
- `#diagnosticBtn` - Run diagnostic (Ctrl+Shift+D)

#### File Inputs (2)
- `#fileInput` - Audio file input (hidden, accept="audio/*")
- `#imageInput` - Image file input (hidden, accept="image/*")

#### Status Displays (2)
- `#status` - Main status text (role="status", aria-live="polite")
- `#statusTip` - Keyboard shortcut hints
- `#shortcutLegend` - Dynamic shortcut display (aria-live="polite")

#### Φ Mode Panel (`#phiPanel`)
- `#phiMode` - Mode selector (5 options)
- `#baseFreq` - Base frequency input (20-20000 Hz)
- `#duration` - Duration input (min 0.1s)
- `#driveCurve` - Curve selector (linear/log/exp)
- `#frequencyRange` - Text input for range (e.g., "200-2000")

---

### 2. Config Loader (`partials/config-loader.html`)
- `#configSelect` - Config file dropdown
- `#preview` - Config preview display (`<pre>` element)

---

### 3. EQ Panel (`partials/eq-panel.html`)

#### Interactive Knobs (3)
- `#lowKnob` - Low freq (100Hz) [data-param="low", data-value="0", tabindex="0"]
- `#midKnob` - Mid freq (1kHz) [data-param="mid", data-value="0", tabindex="0"]
- `#highKnob` - High freq (8kHz) [data-param="high", data-value="0", tabindex="0"]

#### Value Displays (3)
- `#lowValue` - Shows "0 dB"
- `#midValue` - Shows "0 dB"
- `#highValue` - Shows "0 dB"

---

### 4. Saturation Panel (`partials/saturation-panel.html`)

#### Interactive Knobs (3)
- `#driveKnob` - Drive amount [data-param="drive", data-value="1", tabindex="0"]
- `#curveKnob` - Curve shape [data-param="curve", data-value="1", tabindex="0"]
- `#mixKnob` - Wet/dry mix [data-param="mix", data-value="0", tabindex="0"]

#### Value Displays (3)
- `#driveValue` - Shows "1.0x"
- `#curveValue` - Shows "1.0"
- `#mixValue` - Shows "0%"

---

### 5. Image Sonification (`partials/image-sonification.html`)

#### Container
- `#imagePanel` - Main panel (class="is-hidden" initially)

#### Canvas & Info
- `#imageCanvas` - Image display canvas
- `#imageInfo` - Image metadata display

#### Controls
- `#sonifyMode` - Sonification algorithm selector (4 modes)
  - spectral, harmonic, fm, additive
- `#scanSpeed` - Scan speed slider (0.1-5, step 0.1)
- `#scanSpeedValue` - Speed display
- `#freqMin` - Min frequency input (default 100)
- `#freqMax` - Max frequency input (default 8000)

---

### 6. Visualizers (`partials/visualizers.html`)
- `#spectrumCanvas` - Frequency spectrum display (600x300)
- `#waveformCanvas` - Time-domain waveform (600x300)

---

### 7. Logging & Matrix (`partials/log-and-matrix.html`)

#### Log Controls
- `#clearLogBtn` - Clear log (Ctrl+Shift+C)
- `#exportLogBtn` - Export CSV (Ctrl+Shift+E)
- `#exportJsonBtn` - Export JSON (Ctrl+Shift+J)

#### Log Display
- `#logDisplay` - Log container (role="log", aria-live="polite")
- `#logCount` - Event counter
- `#workOutput` - Total work calculation

#### Matrix
- `#matrixGrid` - Parameter coupling matrix display

---

## Data Attributes & Accessibility Features

### Keyboard Shortcuts (all buttons with `data-shortcut` and `data-shortcut-label`)
- Ctrl+Shift+S → Start audio
- Ctrl+Shift+G → Generate tone
- Ctrl+Shift+X → Stop
- Ctrl+Shift+L → Load audio
- Ctrl+Shift+I → Load image
- Ctrl+Shift+P → Play image
- Ctrl+Shift+M → Run Φ mode
- Ctrl+Shift+R → Restore params
- Ctrl+Shift+D → Diagnostic
- Ctrl+Shift+C → Clear log
- Ctrl+Shift+E → Export CSV
- Ctrl+Shift+J → Export JSON

### Knob Interaction Pattern
All knobs have:
- `data-param` - Parameter name
- `data-value` - Current value
- `tabindex="0"` - Keyboard focusable
- Click to select → ↑↓ arrows to adjust
- Shift = fine control, Ctrl = coarse control

### ARIA Attributes
- `role="group"`, `role="status"`, `role="log"`
- `aria-label`, `aria-keyshortcuts`, `aria-controls`
- `aria-live="polite"`, `aria-atomic="false"`
- `aria-hidden="true"` for hidden file inputs

---

## Total Element Count
- **Buttons:** 12
- **File Inputs:** 2
- **Knobs:** 6 (interactive rotary controls)
- **Selects:** 4
- **Text/Number Inputs:** 5
- **Sliders:** 1
- **Canvases:** 3
- **Status/Display Elements:** 8
- **Config/Data Elements:** 2

**Grand Total:** 43 interactive or display elements

---

## External Resource Dependencies
1. `css/soundlab-theme.css`
2. `css/soundlab-controls.css`
3. `css/soundlab-visuals.css`
4. `js/soundlab-main.js` (module entry point)
5. 7 HTML partials loaded via `data-include`
6. Config JSON files (e.g., `phi_tone_run_01_with_history.json`)
