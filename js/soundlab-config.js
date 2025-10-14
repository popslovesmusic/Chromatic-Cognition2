import { adaptIncomingConfig, parseFreqRange } from './soundlab-utils.js';
import { updateMatrix } from './soundlab-audio-core.js';

export function handleConfigSelection(event) {
  const value = event.target.value;
  const preview = document.getElementById('preview');

  if (!value) {
    updateMatrix();
    if (preview) {
      preview.textContent = 'No config loaded.';
    }
    return;
  }

  fetch(value)
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      return response.json();
    })
    .then(config => {
      const normalized = adaptIncomingConfig(config);
      applyConfig(normalized);
    })
    .catch(error => {
      if (preview) {
        preview.textContent = 'Error loading config: ' + error.message;
      }
      console.error('Config load failed', error);
    });
}

export function applyConfig(config) {
  const preview = document.getElementById('preview');

  if (!config) {
    if (preview) {
      preview.textContent = 'Invalid config data.';
    }
    return;
  }

  try {
    const matrix = config.matrix || [];
    const matrixGrid = document.getElementById('matrixGrid');
    if (matrixGrid && Array.isArray(matrix) && matrix.length > 0) {
      matrixGrid.innerHTML = '';
      matrix.forEach(row => {
        row.forEach(cellValue => {
          const cell = document.createElement('div');
          cell.className = 'matrix-cell';
          cell.innerHTML = `<strong>${cellValue.param}</strong><br>${cellValue.target}<br>${Math.round(cellValue.weight * 100)}%`;
          if (cellValue.weight > 0.66) {
            cell.classList.add('active');
          }
          matrixGrid.appendChild(cell);
        });
      });
    } else {
      updateMatrix();
    }

    const input = config.input || {};
    const frequencyRangeSource = config.frequencyRange || input.frequencyRange || config.freq_range;
    const parsedRange = parseFreqRange(frequencyRangeSource || '');
    const scanSpeedField = document.getElementById('scanSpeed');
    const scanSpeedLabel = document.getElementById('scanSpeedValue');
    const scanSpeedValue = Number(input.scanSpeed || config.scanSpeed || input.scan_speed || config.scan_speed);
    const baseConfigValue = Number(config.baseFreq || input.baseFreq || config.base_frequency);
    const durationValue = Number(input.duration || config.duration);

    if (document.getElementById('phiMode') && config.mode) {
      document.getElementById('phiMode').value = config.mode;
    }

    const baseField = document.getElementById('baseFreq');
    if (baseField && Number.isFinite(baseConfigValue)) {
      baseField.value = baseConfigValue;
    }

    const durationField = document.getElementById('duration') || document.getElementById('phiDuration');
    if (durationField && Number.isFinite(durationValue)) {
      durationField.value = durationValue;
    }

    const driveCurveField = document.getElementById('driveCurve');
    if (driveCurveField && config.driveCurve) {
      driveCurveField.value = config.driveCurve;
    }

    if (scanSpeedField && Number.isFinite(scanSpeedValue)) {
      scanSpeedField.value = scanSpeedValue;
      if (scanSpeedLabel) {
        const formatted = Number(scanSpeedValue).toFixed(2).replace(/\.00$/, '');
        scanSpeedLabel.textContent = `${formatted}x`;
      }
    }

    if (document.getElementById('sonifyMode') && input.scan_mode) {
      document.getElementById('sonifyMode').value = input.scan_mode;
    }

    if (document.getElementById('freqMin') && parsedRange && parsedRange.length === 2) {
      document.getElementById('freqMin').value = parsedRange[0];
    }

    if (document.getElementById('freqMax') && parsedRange && parsedRange.length === 2) {
      document.getElementById('freqMax').value = parsedRange[1];
    }

    const previewLines = [
      `Run ID        : ${config.run_id || 'N/A'}`,
      `Image File    : ${input.image_file || 'N/A'}`,
      `Scan Mode     : ${input.scan_mode || 'N/A'}`,
      `Scan Speed    : ${Number.isFinite(scanSpeedValue) ? scanSpeedValue : 'N/A'}`,
      `Freq Range    : ${parsedRange && parsedRange.length === 2 ? `${parsedRange[0]}-${parsedRange[1]}` : frequencyRangeSource || 'N/A'}`,
      `Duration (s)  : ${Number.isFinite(durationValue) ? durationValue : 'N/A'}`
    ];

    if (preview) {
      preview.textContent = previewLines.join('\n');
    }

    window.currentConfig = {
      ...config,
      frequencyRange: parsedRange ? [...parsedRange] : config.frequencyRange,
      scanSpeed: Number.isFinite(scanSpeedValue) ? scanSpeedValue : config.scanSpeed,
      baseFreq: Number.isFinite(baseConfigValue)
        ? baseConfigValue
        : parsedRange && parsedRange.length === 2
        ? parsedRange[0]
        : config.baseFreq
    };
  } catch (error) {
    if (preview) {
      preview.textContent = 'Error loading config: ' + error;
    }
    console.error('Failed to load config', error);
  }
}
