# Soundlab Functional Element Map

This inventory consolidates the interactive elements, supporting scripts, and resource links for `soundlab_v1.html` after modularization. It is used for dependency verification in Step 4 of the SAFE modularization pass.

## Transport, Status, and Φ Controls
- Buttons: `startBtn`, `generateBtn`, `stopBtn`, `loadBtn`, `loadImageBtn`, `playImageBtn`, `runPhiBtn`, `restoreParamsBtn`, `diagnosticBtn`
- Hidden file inputs: `fileInput`, `imageInput`
- Status/legend containers: `status`, `statusTip`, `shortcutLegend`
- Φ parameter fields: `phiMode`, `baseFreq`, `duration`, `driveCurve`, `frequencyRange`
- Action container: `phiActions`

## EQ and Saturation Panels
- Knobs (with `.knob` class and `data-param` attributes): `lowKnob`, `midKnob`, `highKnob`, `driveKnob`, `curveKnob`, `mixKnob`
- Value readouts: `lowValue`, `midValue`, `highValue`, `driveValue`, `curveValue`, `mixValue`

## Image Sonification Workspace
- Panel wrapper: `imagePanel`
- Canvas + metadata: `imageCanvas`, `imageInfo`
- Controls: `sonifyMode`, `scanSpeed`, `scanSpeedValue`, `freqMin`, `freqMax`

## Visualizers and Analytics
- Canvas visualizers: `spectrumCanvas`, `waveformCanvas`
- Log controls: `clearLogBtn`, `exportLogBtn`, `exportJsonBtn`
- Log output: `logDisplay`, `logCount`, `workOutput`
- Parameter matrix: `matrixGrid`

## Linked Resources
- Stylesheets: `css/soundlab-theme.css`, `css/soundlab-controls.css`, `css/soundlab-visuals.css`
- HTML partials (loaded via `data-include`): config loader, transport controls, EQ panel, saturation panel, image sonification, visualizers, log and matrix
- JavaScript modules: `soundlab-utils.js`, `soundlab-logging.js`, `soundlab-config.js`, `soundlab-audio-core.js`, `soundlab-phi.js`, `soundlab-image.js`, `soundlab-events.js`, `soundlab-main.js`

## JavaScript Function Coverage
- Initialization: `initializeSoundlab()` chains `loadPartials()`, `updateMatrix()`, `initLogging()`, `initializeEventHandlers()`.
- Audio core exports consumed: `initAudio`, `generateTone`, `stopAudio`, `loadAudioFile`, `isEqReady`, `notifyEqNotReady`, `getMinValue`, `getMaxValue`, `updateSaturation`, `getParamsState`, `getFilters`.
- Logging: `logParameterChange`, `clearLog`, `exportLogCSV`, `exportLogJSON`.
- Φ synthesis: `runPhiMode`, `restoreLastParams`, `diagnosticParamsLog`, `stopPhiSynthesis`.
- Image sonification: `loadImage`, `toggleImagePlayback`, `stopImagePlayback`.
- Config selection: `handleConfigSelection`.

All referenced DOM IDs/classes exist in the loaded partials, and each module function listed above is defined in its respective file. No orphaned listeners or missing imports were detected during this audit.
