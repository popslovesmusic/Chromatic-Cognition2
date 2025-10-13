import {
  initAudio,
  generateTone,
  stopAudio,
  loadAudioFile,
  isEqReady,
  notifyEqNotReady,
  getMinValue,
  getMaxValue,
  updateSaturation,
  getParamsState,
  getFilters
} from './soundlab-audio-core.js';
import { logParameterChange, clearLog, exportLogCSV, exportLogJSON } from './soundlab-logging.js';
import { runPhiMode, restoreLastParams, diagnosticParamsLog, stopPhiSynthesis } from './soundlab-phi.js';
import { loadImage, toggleImagePlayback, stopImagePlayback } from './soundlab-image.js';
import { handleConfigSelection } from './soundlab-config.js';
import { updateKnobRotation } from './soundlab-utils.js';

function getShortcutBindings() {
  return [
    { code: 'KeyS', elementId: 'startBtn' },
    { code: 'KeyG', elementId: 'generateBtn' },
    { code: 'KeyX', elementId: 'stopBtn' },
    { code: 'KeyL', elementId: 'loadBtn' },
    { code: 'KeyI', elementId: 'loadImageBtn' },
    { code: 'KeyP', elementId: 'playImageBtn' },
    { code: 'KeyM', elementId: 'runPhiBtn' },
    { code: 'KeyR', elementId: 'restoreParamsBtn' },
    { code: 'KeyD', elementId: 'diagnosticBtn' },
    { code: 'KeyC', elementId: 'clearLogBtn' },
    { code: 'KeyE', elementId: 'exportLogBtn' },
    { code: 'KeyJ', elementId: 'exportJsonBtn' }
  ];
}

function handleGlobalShortcuts(event) {
  const usesPrimaryModifier = event.ctrlKey || event.metaKey;
  if (!usesPrimaryModifier || !event.shiftKey) {
    return;
  }

  const tag = event.target && event.target.tagName;
  if (tag && ['INPUT', 'SELECT', 'TEXTAREA'].includes(tag)) {
    return;
  }
  if (event.target && event.target.isContentEditable) {
    return;
  }

  const binding = getShortcutBindings().find(entry => entry.code === event.code);
  if (!binding) {
    return;
  }

  const element = document.getElementById(binding.elementId);
  if (!element || element.disabled) {
    return;
  }

  event.preventDefault();
  element.focus({ preventScroll: true });
  element.click();
}

export function initializeEventHandlers() {
  document.addEventListener('keydown', handleGlobalShortcuts);

  document.getElementById('startBtn').addEventListener('click', initAudio);
  document.getElementById('generateBtn').addEventListener('click', generateTone);
  document.getElementById('stopBtn').addEventListener('click', () => {
    stopAudio();
    stopPhiSynthesis();
    stopImagePlayback();
  });
  document.getElementById('loadBtn').addEventListener('click', () => {
    document.getElementById('fileInput').click();
  });
  document.getElementById('fileInput').addEventListener('change', loadAudioFile);
  document.getElementById('loadImageBtn').addEventListener('click', () => {
    document.getElementById('imageInput').click();
  });
  document.getElementById('imageInput').addEventListener('change', loadImage);
  document.getElementById('playImageBtn').addEventListener('click', toggleImagePlayback);
  document.getElementById('runPhiBtn').addEventListener('click', () => {
    const mode = document.getElementById('phiMode').value;
    runPhiMode(mode);
  });
  document.getElementById('restoreParamsBtn').addEventListener('click', restoreLastParams);
  document.getElementById('diagnosticBtn').addEventListener('click', diagnosticParamsLog);

  const configSelect = document.getElementById('configSelect');
  if (configSelect) {
    configSelect.addEventListener('change', handleConfigSelection);
  }

  document.getElementById('scanSpeed').addEventListener('input', e => {
    const value = Number(e.target.value);
    const formatted = value.toFixed(2).replace(/\.00$/, '');
    document.getElementById('scanSpeedValue').textContent = `${formatted}x`;
  });

  document.getElementById('clearLogBtn').addEventListener('click', clearLog);
  document.getElementById('exportLogBtn').addEventListener('click', exportLogCSV);
  document.getElementById('exportJsonBtn').addEventListener('click', exportLogJSON);

  setupKnobInteractions();
}

function setupKnobInteractions() {
  const params = getParamsState();
  let activeKnob = null;
  let selectedKnob = null;
  let startY = 0;
  let startValue = 0;

  document.querySelectorAll('.knob').forEach(knob => {
    knob.addEventListener('click', e => {
      document.querySelectorAll('.knob').forEach(k => {
        if (k.classList.contains('selected')) {
          k.classList.remove('selected');
          const currentTransform = k.style.transform || 'rotate(-135deg) scale(1)';
          k.style.transform = currentTransform.replace('scale(1.1)', 'scale(1)');
        }
      });

      knob.classList.add('selected');
      selectedKnob = knob;
      const currentTransform = knob.style.transform || 'rotate(-135deg) scale(1)';
      knob.style.transform = currentTransform.replace('scale(1)', 'scale(1.1)');
      e.stopPropagation();
    });

    knob.addEventListener('mousedown', e => {
      if (!isEqReady()) {
        notifyEqNotReady();
        e.preventDefault();
        return;
      }
      activeKnob = knob;
      startY = e.clientY;
      startValue = parseFloat(knob.dataset.value);
      document.body.style.cursor = 'ns-resize';
      e.preventDefault();
    });

    knob.addEventListener('focus', () => {
      document.querySelectorAll('.knob').forEach(k => {
        if (k !== knob) {
          k.classList.remove('selected');
          const currentTransform = k.style.transform || 'rotate(-135deg) scale(1)';
          k.style.transform = currentTransform.replace('scale(1.1)', 'scale(1)');
        }
      });
      knob.classList.add('selected');
      selectedKnob = knob;
      const currentTransform = knob.style.transform || 'rotate(-135deg) scale(1)';
      knob.style.transform = currentTransform.includes('scale(1.1)') ? currentTransform : `${currentTransform} scale(1.1)`;
    });
  });

  document.addEventListener('click', e => {
    if (!e.target.closest('.knob') && selectedKnob) {
      selectedKnob.classList.remove('selected');
      const currentTransform = selectedKnob.style.transform || 'rotate(-135deg) scale(1)';
      selectedKnob.style.transform = currentTransform.replace('scale(1.1)', 'scale(1)');
      selectedKnob = null;
    }
  });

  document.addEventListener('keydown', e => {
    if (!selectedKnob) return;

    if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
      e.preventDefault();

      if (!isEqReady()) {
        notifyEqNotReady();
        return;
      }

      const param = selectedKnob.dataset.param;
      let currentValue = parseFloat(selectedKnob.dataset.value);

      let step = 0.1;
      if (param === 'mix') step = 1;
      if (param === 'drive') step = 0.1;
      if (param === 'curve') step = 0.05;

      if (e.key === 'ArrowUp') {
        currentValue += step;
      } else {
        currentValue -= step;
      }

      const min = getMinValue(param);
      const max = getMaxValue(param);
      const oldValue = parseFloat(selectedKnob.dataset.value);
      currentValue = Math.max(min, Math.min(max, currentValue));

      selectedKnob.dataset.value = currentValue;
      params[param] = currentValue;

      logParameterChange(param, oldValue, currentValue);
      updateKnobLabel(param, currentValue);
      updateKnobRotation(selectedKnob, currentValue, min, max);
      applyParamToAudio(param, currentValue);
    }
  });

  document.addEventListener('mousemove', e => {
    if (!activeKnob) return;

    if (!isEqReady()) {
      notifyEqNotReady();
      return;
    }

    const param = activeKnob.dataset.param;
    let delta = (startY - e.clientY) * 0.02;

    if (e.shiftKey) delta *= 0.1;
    if (e.ctrlKey || e.metaKey) delta *= 5;

    let newValue = startValue + delta;
    const min = getMinValue(param);
    const max = getMaxValue(param);
    newValue = Math.max(min, Math.min(max, newValue));

    const oldValue = parseFloat(activeKnob.dataset.value);
    activeKnob.dataset.value = newValue;
    params[param] = newValue;

    logParameterChange(param, oldValue, newValue);
    updateKnobLabel(param, newValue);
    updateKnobRotation(activeKnob, newValue, min, max);
    applyParamToAudio(param, newValue);
  });

  document.addEventListener('mouseup', () => {
    if (activeKnob) {
      activeKnob = null;
      document.body.style.cursor = 'default';
    }
  });

  document.addEventListener('mouseleave', () => {
    if (activeKnob) {
      activeKnob = null;
      document.body.style.cursor = 'default';
    }
  });

  document.addEventListener('keyup', e => {
    if (e.key === 'Shift' || e.key === 'Control' || e.key === 'Meta') {
      startValue = parseFloat(selectedKnob ? selectedKnob.dataset.value : 0);
    }
  });
}

function updateKnobLabel(param, value) {
  if (param === 'low' || param === 'mid' || param === 'high') {
    document.getElementById(`${param}Value`).textContent = `${value.toFixed(1)} dB`;
  } else if (param === 'mix') {
    document.getElementById(`${param}Value`).textContent = `${Math.round(value)}%`;
  } else if (param === 'drive') {
    document.getElementById(`${param}Value`).textContent = `${value.toFixed(1)}x`;
  } else if (param === 'curve') {
    document.getElementById(`${param}Value`).textContent = `${value.toFixed(2)}`;
  }
}

function applyParamToAudio(param, value) {
  const { lowShelf, midPeak, highShelf, waveshaper } = getFilters();
  const context = lowShelf?.context || midPeak?.context || highShelf?.context;
  const currentTime = context ? context.currentTime : undefined;

  if (param === 'low' && lowShelf && currentTime !== undefined) {
    lowShelf.gain.setValueAtTime(value, currentTime);
  } else if (param === 'mid' && midPeak && currentTime !== undefined) {
    midPeak.gain.setValueAtTime(value, currentTime);
  } else if (param === 'high' && highShelf && currentTime !== undefined) {
    highShelf.gain.setValueAtTime(value, currentTime);
  } else if ((param === 'drive' || param === 'curve' || param === 'mix') && waveshaper) {
    updateSaturation();
  }
}
