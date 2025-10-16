# Soundlab Modular Diagnostics

## 1. UI Element Audit
### Interactive inventory
| Element | Location | Bound handler | Notes |
| --- | --- | --- | --- |
| `#startBtn` | Transport controls partial | `initAudio()` click listener enables graph bootstrap and status messaging.ã€F:partials/transport-controls.htmlâ€ L3-L60ã€‘ã€F:js/soundlab-events.jsâ€ L69-L75ã€‘ | Correctly disables itself after initialization and enables downstream actions.ã€F:js/soundlab-audio-core.jsâ€ L248-L259ã€‘ |
| `#generateBtn` | Transport controls partial | `generateTone()` click listener starts sine source and enables stop control.ã€F:partials/transport-controls.htmlâ€ L11-L27ã€‘ã€F:js/soundlab-events.jsâ€ L69-L75ã€‘ã€F:js/soundlab-audio-core.jsâ€ L262-L289ã€‘ | Disabled until audio engine starts, preventing orphan presses.ã€F:js/soundlab-audio-core.jsâ€ L248-L257ã€‘ |
| `#stopBtn` | Transport controls partial | Composite click handler stops tone/file/Î¦/image playback.ã€F:partials/transport-controls.htmlâ€ L28-L47ã€‘ã€F:js/soundlab-events.jsâ€ L71-L75ã€‘ | Re-disabled after `stopAudio()`, but not after Î¦ auto-complete (see Â§3).ã€F:js/soundlab-audio-core.jsâ€ L338-L358ã€‘ã€F:js/soundlab-phi.jsâ€ L258-L285ã€‘ |
| `#loadBtn` / `#fileInput` | Transport controls partial | Button triggers hidden file input; `change` wired to `loadAudioFile()` with audio-context guard.ã€F:partials/transport-controls.htmlâ€ L48-L69ã€‘ã€F:js/soundlab-events.jsâ€ L76-L80ã€‘ã€F:js/soundlab-audio-core.jsâ€ L291-L336ã€‘ | Status messaging steers users back to Start Audio if context missing.ã€F:js/soundlab-audio-core.jsâ€ L295-L305ã€‘ |
| `#loadImageBtn` / `#imageInput` | Transport controls partial | Loads image into canvas, reveals panel, primes status.ã€F:partials/transport-controls.htmlâ€ L70-L99ã€‘ã€F:js/soundlab-events.jsâ€ L80-L84ã€‘ã€F:js/soundlab-image.jsâ€ L9-L62ã€‘ | Leaves Play button enabled even when audio context absent; playback simply no-ops (see Â§4). |
| `#playImageBtn` | Transport controls partial | Toggles between `startImagePlayback()` and `stopImagePlayback()` with status copy.ã€F:partials/transport-controls.htmlâ€ L88-L99ã€‘ã€F:js/soundlab-events.jsâ€ L83-L84ã€‘ã€F:js/soundlab-image.jsâ€ L64-L115ã€‘ | Button label swaps on toggle; disabled until image present.ã€F:js/soundlab-image.jsâ€ L46-L55ã€‘ |
| Î¦ controls (`#phiMode`, `#baseFreq`, `#duration`, `#driveCurve`, `#frequencyRange`, `#runPhiBtn`, `#restoreParamsBtn`, `#diagnosticBtn`) | Î¦ panel partial | Mode runner reads values via `getParams()`; restore & diagnostic buttons wired to recovery/log routines.ã€F:partials/transport-controls.htmlâ€ L101-L176ã€‘ã€F:js/soundlab-events.jsâ€ L84-L90ã€‘ã€F:js/soundlab-phi.jsâ€ L71-L337ã€‘ã€F:js/soundlab-utils.jsâ€ L39-L59ã€‘ | `#restoreParamsBtn` remains disabled until a Î¦ run captures state.ã€F:js/soundlab-phi.jsâ€ L266-L275ã€‘ |
| EQ & saturation knobs (`.knob`) | EQ/saturation partials | Mouse, keyboard, and focus handlers sync UI, logs, and audio params with readiness checks.ã€F:partials/eq-panel.htmlâ€ L4-L16ã€‘ã€F:partials/saturation-panel.htmlâ€ L4-L16ã€‘ã€F:js/soundlab-events.jsâ€ L110-L238ã€‘ | Prevents edits before engine start via `isEqReady()` messaging.ã€F:js/soundlab-audio-core.jsâ€ L205-L214ã€‘ |
| Image sonification controls (`#sonifyMode`, `#scanSpeed`, `#freqMin`, `#freqMax`) | Image panel partial | Slider updates live label; values consumed during playback per mode.ã€F:partials/image-sonification.htmlâ€ L1-L36ã€‘ã€F:js/soundlab-events.jsâ€ L97-L101ã€‘ã€F:js/soundlab-image.jsâ€ L117-L330ã€‘ | Panel stays hidden until image loads, preserving layout integrity.ã€F:js/soundlab-image.jsâ€ L42-L55ã€‘ |
| Logging controls (`#clearLogBtn`, `#exportLogBtn`, `#exportJsonBtn`) | Log partial | Click handlers reset log or export CSV/JSON via Blob download.ã€F:partials/log-and-matrix.htmlâ€ L3-L33ã€‘ã€F:js/soundlab-events.jsâ€ L103-L105ã€‘ã€F:js/soundlab-logging.jsâ€ L18-L144ã€‘ | Shortcut legend auto-populates from `data-shortcut` attributes.ã€F:js/soundlab-logging.jsâ€ L146-L164ã€‘ |
| Config dropdown `#configSelect` | Config loader partial | `change` handler fetches JSON, normalizes, and applies to UI/matrix.ã€F:partials/config-loader.htmlâ€ L1-L8ã€‘ã€F:js/soundlab-events.jsâ€ L92-L95ã€‘ã€F:js/soundlab-config.jsâ€ L4-L142ã€‘ |
| Status displays (`#status`, `#statusTip`, `#shortcutLegend`, log counters) | Transport & log partials | Updated across modules to reflect lifecycle state.ã€F:partials/transport-controls.htmlâ€ L101-L176ã€‘ã€F:partials/log-and-matrix.htmlâ€ L3-L33ã€‘ã€F:js/soundlab-audio-core.jsâ€ L248-L359ã€‘ã€F:js/soundlab-logging.jsâ€ L48-L164ã€‘ | Provide user feedback for readiness, diagnostics, and logging. |

### Findings
* All declared interactive elements are wired to handlers after partial loading; no orphaned IDs detected because `loadPartials()` awaits each include before binding events.ã€F:js/soundlab-main.jsâ€ L335-L364ã€‘ã€F:js/soundlab-events.jsâ€ L66-L107ã€‘
* Shortcut legend covers every control exposing a `data-shortcut`, ensuring accessibility parity between mouse and keyboard workflows.ã€F:js/soundlab-logging.jsâ€ L146-L164ã€‘
* Event registration assumes partial markup availability; if a new include fails without a fallback snippet, `document.getElementById(...).addEventListener` would throw. Consider null-guards or `querySelector` option chaining for future extensibility.ã€F:js/soundlab-events.jsâ€ L69-L107ã€‘ã€F:js/soundlab-main.jsâ€ L335-L349ã€‘

## 2. Audio Graph Validation
### Observations
* `initAudio()` constructs a linear chain (source â†’ EQ filters â†’ waveshaper â†’ gain â†’ analyser â†’ destination), seeds analyser buffers, and primes UI state.ã€F:js/soundlab-audio-core.jsâ€ L216-L260ã€‘
* `generateTone()`/`loadAudioFile()` rebuild upstream sources while reusing the shared processing chain via `ensureProcessingChain()`.ã€F:js/soundlab-audio-core.jsâ€ L262-L333ã€‘
* `stopAudio()` tears down active oscillator/buffer sources and restores transport controls, but leaves the processing chain hot for subsequent playback.ã€F:js/soundlab-audio-core.jsâ€ L338-L359ã€‘

### Issues & recommendations
| Severity | Issue | Evidence | Recommendation |
| --- | --- | --- | --- |
| **High** | Saturation mix removes the dry signal entirely: the waveshaper curve is scaled by `params.mix/100`, so the default mix of `0` silences all audio traversing the chain.ã€F:js/soundlab-audio-core.jsâ€ L19-L106ã€‘ | Implement a parallel dry path or compute a crossfaded output (e.g., mix = 0 routes dry signal, mix = 100 fully wet). At minimum, default mix should be 100% until blending is supported. |
| Medium | `ensureProcessingChain()` repeatedly disconnects nodes on each call; while safe, it risks transient pops under load and omits context resume for suspended states.ã€F:js/soundlab-audio-core.jsâ€ L56-L92ã€‘ | Cache a flag to skip redundant disconnect/reconnect cycles and call `audioContext.resume()` inside `initAudio()` for Safari/Chrome autoplay policies. |
| Medium | `stopAudio()` does not call `setAudioPlaying(false)`, while Î¦ mode uses that flag. Divergent state tracking can desynchronize shared status helpers.ã€F:js/soundlab-audio-core.jsâ€ L338-L359ã€‘ã€F:js/soundlab-phi.jsâ€ L258-L285ã€‘ | Normalize on the exported setter when toggling playback so UI components share the same state source. |

## 3. Î¦ Mode Dispatch and Recovery
### Observations
* `runPhiMode()` validates the audio graph, stops prior Î¦ synthesis, then branches across tone/AM/FM/interval/harmonic implementations that share envelope helpers and parameter sampling from `getParams()`.ã€F:js/soundlab-phi.jsâ€ L71-L256ã€‘ã€F:js/soundlab-utils.jsâ€ L39-L59ã€‘
* On completion, last-run parameters are cached and the restore button is enabled; `restoreLastParams()` hydrates form inputs and announces status.ã€F:js/soundlab-phi.jsâ€ L258-L313ã€‘
* `diagnosticParamsLog()` prints structured details to the console and echoes a concise summary in the status banner.ã€F:js/soundlab-phi.jsâ€ L316-L333ã€‘

### Issues & recommendations
| Severity | Issue | Evidence | Recommendation |
| --- | --- | --- | --- |
| Medium | When a Î¦ run times out naturally, the stop button remains enabled even though synthesis is halted, inviting redundant presses.ã€F:js/soundlab-phi.jsâ€ L258-L285ã€‘ | Disable `#stopBtn` inside the timeout callback (and re-enable Generate) to keep transport UI truthful without relying on manual stop. |
| Medium | Parameter recovery is session-bound only; reloading the page clears `lastParams`, reducing Î¦ workflow continuity.ã€F:js/soundlab-phi.jsâ€ L10-L44ã€‘ã€F:js/soundlab-phi.jsâ€ L266-L275ã€‘ | Persist the last Î¦ payload into `localStorage` (with timestamp) and hydrate during initialization to survive reloads. |
| Low | `diagnosticParamsLog()` relies on the console for detail, offering no in-app history beyond transient status text.ã€F:js/soundlab-phi.jsâ€ L316-L333ã€‘ | Pipe diagnostic output into the existing logging panel or a dedicated diagnostics feed for traceability. |

## 4. Image Sonification Workflow
### Observations
* Image loading scales artwork to â‰¤512 px, reveals the sonification panel, and populates metadata before asserting audio readiness.ã€F:js/soundlab-image.jsâ€ L9-L58ã€‘
* Playback toggles update button text and status messaging while dispatching to spectral, harmonic, FM, or additive renderers that interpret pixel data differently.ã€F:js/soundlab-image.jsâ€ L64-L330ã€‘
* Each renderer advances a column counter, calls `drawScanIndicator()`, and halts automatically at image bounds.ã€F:js/soundlab-image.jsâ€ L152-L343ã€‘

### Issues & recommendations
| Severity | Issue | Evidence | Recommendation |
| --- | --- | --- | --- |
| Medium | Loading an image before the audio engine is started leaves `#playImageBtn` enabled, yet subsequent playback simply returns without user feedback when `audioContext` is null.ã€F:js/soundlab-image.jsâ€ L46-L75ã€‘ | Either defer enabling Play until `getAudioContext()` succeeds or display a status prompt when `startImagePlayback()` aborts due to a missing context. |
| Medium | FM mode allocates a persistent `GainNode` (`modGain`) that is never stored in `imageOscillators`, so `stopImagePlayback()` cannot disconnect it explicitly.ã€F:js/soundlab-image.jsâ€ L222-L277ã€‘ | Track auxiliary nodes alongside oscillators or add a dedicated cleanup routine to prevent stray graph attachments during repeated toggles. |
| Medium | Harmonic and additive modes spawn numerous short-lived oscillators without tracking references, so stopping playback midway cannot immediately halt grains in flight.ã€F:js/soundlab-image.jsâ€ L187-L330ã€‘ | Maintain a pool of active grains (oscillators & gains) to allow forced teardown when the user presses Stop. |
| Low | `freqMin`/`freqMax` inputs accept any numeric values without validation, which can lead to silent or aliasing-prone spectra.ã€F:js/soundlab-image.jsâ€ L122-L330ã€‘ | Clamp ranges inside playback routines and surface validation errors near the form fields. |

## 5. Logging and Export Hooks
### Observations
* Parameter deltas, derived â€œforce/work,â€ and running totals populate both the DOM log and downloadable CSV/JSON exports.ã€F:js/soundlab-logging.jsâ€ L18-L144ã€‘
* Clearing the log resets counters and redraws the placeholder; shortcut legend generation keeps keyboard hints in sync with UI changes.ã€F:js/soundlab-logging.jsâ€ L92-L164ã€‘

### Issues & recommendations
| Severity | Issue | Evidence | Recommendation |
| --- | --- | --- | --- |
| Medium | Only knob interactions trigger logging; Î¦ mode actions, image scans, and transport events leave no audit trail.ã€F:js/soundlab-events.jsâ€ L110-L287ã€‘ã€F:js/soundlab-phi.jsâ€ L71-L333ã€‘ã€F:js/soundlab-image.jsâ€ L64-L330ã€‘ | Extend `logParameterChange()` usage (or introduce event-level logging) for Î¦ dispatch, image playback toggles, and transport state changes to achieve complete workflow coverage. |
| Low | CSV/JSON exports assume synchronous Blob support and do not report success/failure in the UI.ã€F:js/soundlab-logging.jsâ€ L99-L144ã€‘ | Update status text on export completion (or failure) so users receive inline confirmation without relying on browser download UI. |

## 6. Modularization Integrity Check
### Observations
* `loadPartials()` fetches each include sequentially, falling back to baked-in HTML snippets when a request fails, guaranteeing required IDs exist before handler registration.ã€F:js/soundlab-main.jsâ€ L5-L369ã€‘
* Initialization orderâ€”partials, matrix seed, logging, then eventsâ€”keeps dependencies satisfied (matrix grid exists before `updateMatrix()`, log elements exist before `initLogging()`, etc.).ã€F:js/soundlab-main.jsâ€ L352-L364ã€‘
* Audio state is centralized in `soundlab-audio-core.js`, and shared getters ensure other modules read from the same context instance.ã€F:js/soundlab-audio-core.jsâ€ L32-L55ã€‘

### Issues & recommendations
| Severity | Issue | Evidence | Recommendation |
| --- | --- | --- | --- |
| Medium | Sequential partial loading can delay first paint and input readiness if any include stalls.ã€F:js/soundlab-main.jsâ€ L352-L356ã€‘ | Load partials in parallel (`Promise.all`) while preserving post-load initialization sequencing to reduce perceived startup latency. |
| Low | Event binding assumes fallback HTML parity; if a future partial omits an ID, initialization will throw and halt setup.ã€F:js/soundlab-events.jsâ€ L69-L107ã€‘ | Wrap each `getElementById` call with optional chaining or guard clauses to improve resilience during iterative modular refactors. |

## 7. Summary Report
| Area | Issues Found | Severity | Impact | Suggested Fixes | Missing Tests | Confidence |
| --- | --- | --- | --- | --- | --- | --- |
| Audio core | Dry/wet mix bug; redundant reconnects; inconsistent playback state flag | High / Medium | Silence by default, potential pops, state drift | Introduce proper mix bus; memoize connections; standardize `setAudioPlaying` usage | No automated Web Audio regression suite | Medium |
| Î¦ mode | Stop button state drift; session-only recovery; diagnostic visibility | Medium / Low | Confusing transport UI; lost presets across reloads; limited traceability | Disable stop post-timeout; persist last params; surface diagnostics in UI | No preset dispatch tests | Medium |
| Image sonification | Audio-context gating; FM cleanup gap; granular teardown; input validation | Medium / Low | User confusion, lingering nodes, noisy stoppage, invalid spectra | Gate Play button via context; track auxiliary nodes; maintain grain pool; clamp frequency inputs | No mode-by-mode playback tests | Low |
| Logging | Coverage gaps; export feedback | Medium / Low | Incomplete audit trail; unclear export results | Log Î¦/image/transport actions; update status after exports | No log export unit tests | Medium |
| Modularization | Sequential include loading; rigid binding assumptions | Medium / Low | Slower initial render; brittle future changes | Parallelize fetches; add binding guards | No integration smoke tests | Medium |

**Overall:** The system is structurally sound, but the high-severity saturation mix defect and several medium-level lifecycle gaps merit prioritization. Confidence is medium because review relied on static analysis; targeted runtime tests (especially across browsers for Web Audio) are still required.
