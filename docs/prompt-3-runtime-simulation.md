# PROMPT 3: Runtime Behavior Simulation

## Initialization Sequence Analysis

### 1. Page Load (t=0ms)
```
Browser loads soundlab_v2.html
├─ Parses HTML structure
├─ Loads CSS files (parallel):
│  ├─ css/soundlab-theme.css
│  ├─ css/soundlab-controls.css
│  └─ css/soundlab-visuals.css
└─ Encounters <script type="module" src="js/soundlab-main.js">
    └─ Defers execution until DOM ready
```

### 2. DOMContentLoaded Event (t=~50-100ms)
```javascript
// soundlab-main.js lines 366-370
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeSoundlab, { once: true });
} else {
  initializeSoundlab();
}
```

**Execution Path:**
1. `initializeSoundlab()` called (line 359)
2. `await loadPartials()` - Sequential loading of 7 HTML partials
3. `updateMatrix()` - Generates parameter coupling matrix
4. `initLogging()` - Sets up keyboard shortcut legend
5. `initializeEventHandlers()` - Wires all event listeners

---

## 3. Partial Loading Sequence (t=~100-300ms)

### loadPartials() - soundlab-main.js:352-357
```javascript
async function loadPartials() {
  const includeElements = Array.from(document.querySelectorAll('[data-include]'));
  for (const element of includeElements) {
    await loadPartial(element);  // Sequential, not parallel
  }
}
```

**Order of Loading:**
1. `partials/config-loader.html` → #configSelect, #preview
2. `partials/transport-controls.html` → 9 buttons + status displays
3. `partials/eq-panel.html` → 3 EQ knobs
4. `partials/saturation-panel.html` → 3 saturation knobs
5. `partials/image-sonification.html` → #imagePanel (hidden initially)
6. `partials/visualizers.html` → 2 canvases
7. `partials/log-and-matrix.html` → Log + matrix displays

**Fallback Mechanism:**
- If `fetch()` fails (CORS, 404, etc.), uses `FALLBACK_PARTIALS` from lines 5-333
- Ensures app functions even without server or missing files
- Console logs error but doesn't break initialization

---

## 4. Matrix Initialization (t=~300ms)

### updateMatrix() - soundlab-audio-core.js:361-386
```javascript
// Generates 6×6 parameter coupling matrix
parameters = ['Low', 'Mid', 'High', 'Drive', 'Curve', 'Mix']
// Creates 36 cells showing parameter interactions
```

**Visual Output:**
- Self-influence cells marked as "active"
- Cross-coupling calculated via `Math.sin()` formula
- Displays percentage values (0-100%)

---

## 5. Logging System Init (t=~310ms)

### initLogging() - soundlab-logging.js:117-142
```javascript
// Builds keyboard shortcut legend dynamically
// Scans all buttons with data-shortcut attributes
// Displays: "Ctrl+Shift+S Start audio | Ctrl+Shift+G Generate tone | ..."
```

**DOM Update:**
- Populates `#shortcutLegend` with `<kbd>` elements
- Updates `#statusTip` visibility

---

## 6. Event Handler Registration (t=~320ms)

### initializeEventHandlers() - soundlab-events.js:66-108

**Global Listeners (3):**
1. `document.addEventListener('keydown', handleGlobalShortcuts)` - All keyboard shortcuts
2. Document-level knob interaction listeners (mousemove, mouseup, click, keyup)
3. Window beforeunload (cleanup)

**Button Listeners (12):**
- #startBtn → `initAudio()`
- #generateBtn → `generateTone()`
- #stopBtn → `stopAudio()` + `stopPhiSynthesis()` + `stopImagePlayback()`
- #loadBtn → triggers #fileInput click
- #fileInput → `loadAudioFile()`
- #loadImageBtn → triggers #imageInput click
- #imageInput → `loadImage()`
- #playImageBtn → `toggleImagePlayback()`
- #runPhiBtn → `runPhiMode(mode)`
- #restoreParamsBtn → `restoreLastParams()`
- #diagnosticBtn → `diagnosticParamsLog()`
- #configSelect → `handleConfigSelection()`

**Knob Listeners (6 knobs):**
- Click → select/deselect + scale animation
- Mousedown → drag mode + cursor change
- Focus → keyboard selection
- Arrow keys → increment/decrement (Shift=fine, Ctrl=coarse)

**Slider Listeners (1):**
- #scanSpeed → updates #scanSpeedValue display

**Log Listeners (3):**
- #clearLogBtn → `clearLog()`
- #exportLogBtn → `exportLogCSV()`
- #exportJsonBtn → `exportLogJSON()`

---

## 7. Initial UI State (t=~350ms)

### Button States:
```
✅ Enabled:
  - #startBtn (primary action)
  - #loadImageBtn
  - #runPhiBtn
  - #diagnosticBtn
  - #clearLogBtn (no-op if empty)
  - #exportLogBtn (no-op if empty)
  - #exportJsonBtn (no-op if empty)

🔒 Disabled:
  - #generateBtn (requires audio context)
  - #stopBtn (nothing playing)
  - #loadBtn (requires audio context)
  - #playImageBtn (no image loaded)
  - #restoreParamsBtn (no previous params)
```

### Status Display:
```
#status: "System Ready | Click START AUDIO to initialize"
#statusTip: Shows keyboard shortcuts
#shortcutLegend: Populated with all shortcuts
```

### Knob Values:
```
EQ:
  - Low: 0 dB (neutral)
  - Mid: 0 dB (neutral)
  - High: 0 dB (neutral)

Saturation:
  - Drive: 1.0x (no gain)
  - Curve: 1.0 (linear)
  - Mix: 0% (fully dry)
```

### Visualizers:
- Both canvases exist but show black (no audio data yet)
- Animation loop not started until audio initialized

---

## Typical User Interaction Flows

### Flow A: Generate Reference Tone
```
User clicks "Start Audio" (#startBtn)
  ↓
initAudio() called (soundlab-audio-core.js:216)
  ├─ Creates AudioContext
  ├─ Creates analyser (FFT size 2048)
  ├─ Creates 3 BiquadFilters (lowShelf, midPeak, highShelf)
  ├─ Creates WaveShaper node
  ├─ Creates GainNode (0.5 gain)
  ├─ Connects processing chain
  ├─ Disables #startBtn
  ├─ Enables #generateBtn, #loadBtn
  ├─ Updates status: "Audio System Active | Ready for Input"
  ├─ Calls updateMatrix()
  └─ Starts draw() animation loop
  ↓
User clicks "Generate Tone" (#generateBtn)
  ↓
generateTone() called (soundlab-audio-core.js:262)
  ├─ Creates OscillatorNode (440Hz sine)
  ├─ Connects: oscillator → lowShelf → midPeak → highShelf → waveshaper → gain → analyser → destination
  ├─ Starts oscillator
  ├─ Disables #generateBtn
  ├─ Enables #stopBtn
  └─ Updates status: "Generating 440Hz Tone | Processing Active"
  ↓
User clicks knob (e.g., #lowKnob)
  ↓
Knob selected (cyan glow + scale 1.1)
  ↓
User presses ↑ arrow
  ↓
  ├─ Value increments by 0.1 dB
  ├─ Clamps to range [-20, 20]
  ├─ Logs change to CPWP log
  ├─ Updates #lowValue display
  ├─ Rotates knob visual
  └─ Applies: lowShelf.gain.setValueAtTime(value, currentTime)
  ↓
**Result:** User hears tonal change in real-time
```

---

### Flow B: Load Audio File
```
User clicks "Start Audio" → (same as Flow A)
  ↓
User clicks "Load Audio File" (#loadBtn)
  ↓
Triggers hidden #fileInput.click()
  ↓
File dialog opens
  ↓
User selects MP3/WAV file
  ↓
loadAudioFile() called (soundlab-audio-core.js:291)
  ├─ Validates audioContext exists
  ├─ Reads file as ArrayBuffer
  ├─ Decodes audio data
  ├─ Creates BufferSource (loop enabled)
  ├─ Connects: source → lowShelf → ... → destination
  ├─ Starts playback
  ├─ Disables #generateBtn
  ├─ Enables #stopBtn
  └─ Updates status: "Playing Audio File | Processing Active"
  ↓
**Result:** File plays with real-time EQ/saturation processing
```

---

### Flow C: Image Sonification
```
User clicks "Load Image → Sound" (#loadImageBtn)
  ↓
loadImage() called (soundlab-image.js:177)
  ├─ Triggers #imageInput.click()
  ├─ User selects image file (PNG/JPG)
  ├─ Reads file as data URL
  ├─ Loads into Image object
  ├─ Draws to #imageCanvas (max 200×150)
  ├─ Extracts pixel data
  ├─ Shows #imagePanel (removes .is-hidden)
  ├─ Enables #playImageBtn
  └─ Updates #imageInfo with dimensions
  ↓
User clicks "Play Image" (#playImageBtn)
  ↓
toggleImagePlayback() called (soundlab-image.js:219)
  ├─ If not playing:
  │  ├─ Ensures audio context initialized
  │  ├─ Gets sonification mode (#sonifyMode)
  │  ├─ Starts playback based on mode:
  │  │  ├─ spectral: playSpectral()
  │  │  ├─ harmonic: playHarmonic()
  │  │  ├─ fm: playFM()
  │  │  └─ additive: playAdditive()
  │  ├─ Updates button: "Stop Image"
  │  └─ Updates status
  └─ If playing:
     ├─ Calls stopImagePlayback()
     └─ Updates button: "Play Image"
  ↓
**Result:** Image pixels converted to evolving audio texture
```

---

### Flow D: Phi Mode Synthesis
```
User configures Phi panel:
  - Mode: "Φ FM Modulation"
  - Base Freq: 432 Hz
  - Duration: 5s
  - Drive Curve: Log
  - Frequency Range: 100-3000
  ↓
User clicks "Run Φ Mode" (#runPhiBtn)
  ↓
runPhiMode('phi_FM') called (soundlab-phi.js:250)
  ├─ Validates audio context
  ├─ Parses config values
  ├─ Stops existing synthesis
  ├─ Calls phi_FM(baseFreq=432, duration=5)
  ├─ Creates carrier oscillator (432 Hz)
  ├─ Creates modulator oscillator (432 * φ Hz)
  ├─ Ramps modulation depth using log curve
  ├─ Connects: osc → gain → lowShelf → ... → destination
  ├─ Schedules stop after 5s
  ├─ Stores params for restore
  ├─ Enables #restoreParamsBtn
  ├─ Disables #generateBtn, enables #stopBtn
  └─ Updates status
  ↓
**Result:** Golden ratio-based FM synthesis plays for 5 seconds
```

---

### Flow E: Config Loading
```
User selects "phi_tone_run_01" from #configSelect
  ↓
handleConfigSelection() called (soundlab-config.js:50)
  ├─ Fetches phi_tone_run_01_with_history.json
  ├─ Parses JSON
  ├─ Displays formatted JSON in #preview
  ├─ Extracts config object (if present)
  ├─ Calls applyConfig(configObj)
  ├─ Populates Phi panel inputs:
  │  ├─ #phiMode = config.mode
  │  ├─ #baseFreq = config.baseFreq
  │  ├─ #duration = config.duration
  │  └─ etc.
  ├─ Applies EQ/saturation values:
  │  ├─ setKnobValue('lowKnob', config.low, ...)
  │  ├─ Updates audio filters if active
  │  └─ Logs parameter changes
  └─ Shows confirmation message
  ↓
**Result:** All UI controls populated from saved config
```

---

## Error Handling & Edge Cases

### Scenario 1: User Adjusts Knob Before Starting Audio
```
User clicks #lowKnob (no audio context exists)
  ↓
isEqReady() returns false
  ↓
notifyEqNotReady() called
  ↓
#status displays: "Start the audio engine before adjusting EQ controls."
  ↓
**Result:** Graceful failure, user guided to correct action
```

### Scenario 2: Partial Loading Fails (CORS, 404)
```
fetch('partials/eq-panel.html') fails
  ↓
loadPartial() catch block executes
  ↓
console.error(error) logs the issue
  ↓
element.innerHTML = FALLBACK_PARTIALS[url]
  ↓
**Result:** Fallback HTML injected, app continues functioning
```

### Scenario 3: Invalid Config JSON
```
User selects config with malformed JSON
  ↓
JSON.parse() throws SyntaxError
  ↓
handleConfigSelection() catch block executes
  ↓
#preview displays: "Failed to load config: [error message]"
  ↓
**Result:** Error shown, app state unchanged
```

### Scenario 4: Multiple Simultaneous Audio Sources
```
User generates tone, then loads audio file without stopping
  ↓
loadAudioFile() checks if source exists
  ↓
Stops and disconnects previous source
  ↓
Creates new source
  ↓
**Result:** Clean transition, no audio leaks
```

### Scenario 5: Browser Autoplay Policy Blocks Audio
```
User clicks "Start Audio" immediately after page load
  ↓
AudioContext may be in "suspended" state
  ↓
audioContext.resume() called (implicit in Web Audio API)
  ↓
OR: User interaction already present (button click)
  ↓
**Result:** Should work; button click counts as user gesture
```

---

## Performance Characteristics

### Memory Usage:
- **AudioContext:** ~10-20 MB (browser-managed)
- **Audio Buffers:** Variable (file size dependent)
- **FFT Analysis:** 2048 samples × 2 arrays = ~4 KB
- **Image Data:** Max 200×150×4 = 120 KB
- **Total:** ~30-50 MB typical

### CPU Usage:
- **Idle (no audio):** <1% CPU
- **Playing tone:** ~2-5% CPU (visualizers running)
- **Playing file:** ~3-7% CPU
- **Image sonification:** ~5-15% CPU (complex modes like additive)

### Animation Loop:
- **requestAnimationFrame:** ~60 FPS
- **draw() function:** Runs continuously after audio init
- **Canvas updates:** Double-buffered (no flicker)

---

## State Transitions

```
[UNINITIALIZED]
  ↓ Click "Start Audio"
[AUDIO_READY]
  ↓ Click "Generate Tone" or "Load File"
[AUDIO_PLAYING]
  ↓ Click "Stop"
[AUDIO_READY]
  ↓ (can loop between READY ↔ PLAYING)
```

**Substates:**
- Image loaded/not loaded
- Config loaded/not loaded
- Previous Phi params available/not available
- Selected knob active/none selected

---

## Console Output (Expected)

### Normal Operation:
```
(no console output if all loads succeed)
```

### With Missing Partials (expected if not on server):
```
Failed to load partials/config-loader.html: 404
Failed to load partials/transport-controls.html: 404
... (falls back silently to embedded HTML)
```

### With Diagnostic Logging:
```javascript
// When user clicks "Run Diagnostic"
diagnosticParamsLog() outputs:
{
  timestamp: "2025-10-13T03:30:45.123Z",
  params: { low: 5.2, mid: -2.1, high: 3.5, drive: 2.0, curve: 1.5, mix: 50 },
  phiConfig: { mode: "phi_FM", baseFreq: 432, duration: 5 }
}
```

---

## Accessibility Features in Action

### Keyboard Navigation:
1. **Tab key:** Cycles through all focusable elements
2. **Enter/Space:** Activates focused button
3. **Arrow keys:** Adjusts selected knob
4. **Ctrl+Shift+[Key]:** Global shortcuts (even when focus elsewhere)

### Screen Reader Announcements:
- **#status (aria-live="polite"):** Status changes announced
- **#logDisplay (role="log"):** New log entries announced
- **Buttons (aria-label):** Clear purpose stated

### Visual Feedback:
- **Knob selection:** Cyan glow + scale increase
- **Button states:** Disabled appearance + cursor change
- **Status updates:** Real-time text changes

---

## Summary: Initialization is Robust ✅

**Strengths:**
- Sequential, predictable initialization
- Fallback mechanisms for network failures
- No race conditions (await pattern)
- Graceful error handling
- Clean state management
- Proper resource cleanup

**Potential Improvements:**
- Could parallelize partial loading (Promise.all)
- Could add loading indicator during init
- Could cache compiled audio buffers
- Could add service worker for offline support

**Overall:** The initialization sequence is production-ready and handles edge cases well.
