import { updateKnobRotation } from './soundlab-utils.js';

let audioContext;
let analyser;
let source;
let oscillator;
let gainNode;
let isPlaying = false;

let lowShelf;
let midPeak;
let highShelf;
let waveshaper;

let dataArray;
let bufferLength;
let frequencyData;

const params = {
  low: 0,
  mid: 0,
  high: 0,
  drive: 1,
  curve: 1,
  mix: 0
};

export function getParamsState() {
  return params;
}

export function getAudioContext() {
  return audioContext;
}

export function getAnalyser() {
  return analyser;
}

export function getGainNode() {
  return gainNode;
}

export function getFilters() {
  return { lowShelf, midPeak, highShelf, waveshaper };
}

export function isAudioPlaying() {
  return isPlaying;
}

export function setAudioPlaying(value) {
  isPlaying = value;
}

export function ensureProcessingChain() {
  if (!audioContext || !lowShelf || !midPeak || !highShelf || !waveshaper || !gainNode || !analyser) {
    return;
  }

  if (gainNode.numberOfOutputs > 0) {
    try {
      gainNode.disconnect();
    } catch (e) {}
  }

  try {
    lowShelf.disconnect();
  } catch (e) {}
  try {
    midPeak.disconnect();
  } catch (e) {}
  try {
    highShelf.disconnect();
  } catch (e) {}
  try {
    waveshaper.disconnect();
  } catch (e) {}
  try {
    gainNode.disconnect();
  } catch (e) {}
  try {
    analyser.disconnect();
  } catch (e) {}

  lowShelf.connect(midPeak);
  midPeak.connect(highShelf);
  highShelf.connect(waveshaper);
  waveshaper.connect(gainNode);
  gainNode.connect(analyser);
  analyser.connect(audioContext.destination);
}

export function updateSaturation() {
  if (!waveshaper) return;

  const curveAmount = params.drive * params.curve;
  const curveLength = 2048;
  const curve = new Float32Array(curveLength);

  for (let i = 0; i < curveLength; i++) {
    const x = (i * 2) / curveLength - 1;
    curve[i] = Math.tanh(curveAmount * x) * (params.mix / 100);
  }

  waveshaper.curve = curve;
}

function draw() {
  if (!audioContext || !analyser || !dataArray || !frequencyData) {
    requestAnimationFrame(draw);
    return;
  }

  analyser.getByteTimeDomainData(dataArray);
  analyser.getByteFrequencyData(frequencyData);

  const spectrumCanvas = document.getElementById('spectrumCanvas');
  const waveformCanvas = document.getElementById('waveformCanvas');
  if (!spectrumCanvas || !waveformCanvas) {
    requestAnimationFrame(draw);
    return;
  }

  const spectrumCtx = spectrumCanvas.getContext('2d');
  const waveformCtx = waveformCanvas.getContext('2d');

  spectrumCtx.fillStyle = '#000';
  spectrumCtx.fillRect(0, 0, spectrumCanvas.width, spectrumCanvas.height);
  spectrumCtx.lineWidth = 2;
  spectrumCtx.strokeStyle = '#00ff66';
  spectrumCtx.beginPath();

  const sliceWidth = (spectrumCanvas.width * 1.0) / bufferLength;
  let x = 0;

  for (let i = 0; i < bufferLength; i++) {
    const v = frequencyData[i] / 255;
    const y = spectrumCanvas.height - v * spectrumCanvas.height;
    if (i === 0) {
      spectrumCtx.moveTo(x, y);
    } else {
      spectrumCtx.lineTo(x, y);
    }
    x += sliceWidth;
  }

  spectrumCtx.stroke();

  waveformCtx.fillStyle = '#000';
  waveformCtx.fillRect(0, 0, waveformCanvas.width, waveformCanvas.height);
  waveformCtx.lineWidth = 2;
  waveformCtx.strokeStyle = '#00ffff';
  waveformCtx.beginPath();

  const waveformSliceWidth = (waveformCanvas.width * 1.0) / bufferLength;
  let waveformX = 0;

  for (let i = 0; i < bufferLength; i++) {
    const v = dataArray[i] / 128.0;
    const y = (v * waveformCanvas.height) / 2;
    if (i === 0) {
      waveformCtx.moveTo(waveformX, y);
    } else {
      waveformCtx.lineTo(waveformX, y);
    }
    waveformX += waveformSliceWidth;
  }

  waveformCtx.lineTo(waveformCanvas.width, waveformCanvas.height / 2);
  waveformCtx.stroke();

  requestAnimationFrame(draw);
}

export function setKnobValue(knobId, value, labelId, formatFn) {
  const knob = document.getElementById(knobId);
  const label = document.getElementById(labelId);
  if (!knob || !label) return;

  const min = getMinValue(knob.dataset.param);
  const max = getMaxValue(knob.dataset.param);
  params[knob.dataset.param] = value;
  knob.dataset.value = value;
  updateKnobRotation(knob, value, min, max);
  label.textContent = formatFn(value);
}

export function getMinValue(param) {
  if (param === 'low' || param === 'mid' || param === 'high') return -20;
  if (param === 'drive') return 1;
  if (param === 'curve') return 0.1;
  if (param === 'mix') return 0;
  return 0;
}

export function getMaxValue(param) {
  if (param === 'low' || param === 'mid' || param === 'high') return 20;
  if (param === 'drive') return 10;
  if (param === 'curve') return 5;
  if (param === 'mix') return 100;
  return 1;
}

export function isEqReady() {
  return !!(audioContext && lowShelf && midPeak && highShelf);
}

export function notifyEqNotReady() {
  const statusEl = document.getElementById('status');
  if (statusEl) {
    statusEl.textContent = 'Start the audio engine before adjusting EQ controls.';
  }
}

export function initAudio() {
  if (!audioContext) {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
  }

  analyser = audioContext.createAnalyser();
  analyser.fftSize = 2048;
  bufferLength = analyser.frequencyBinCount;
  dataArray = new Uint8Array(bufferLength);
  frequencyData = new Uint8Array(bufferLength);

  lowShelf = audioContext.createBiquadFilter();
  lowShelf.type = 'lowshelf';
  lowShelf.frequency.value = 100;

  midPeak = audioContext.createBiquadFilter();
  midPeak.type = 'peaking';
  midPeak.frequency.value = 1000;
  midPeak.Q.value = 1;

  highShelf = audioContext.createBiquadFilter();
  highShelf.type = 'highshelf';
  highShelf.frequency.value = 8000;

  waveshaper = audioContext.createWaveShaper();
  updateSaturation();

  gainNode = audioContext.createGain();
  gainNode.gain.value = 0.5;

  ensureProcessingChain();

  const startBtn = document.getElementById('startBtn');
  const generateBtn = document.getElementById('generateBtn');
  const loadBtn = document.getElementById('loadBtn');
  const status = document.getElementById('status');

  if (startBtn) startBtn.disabled = true;
  if (generateBtn) generateBtn.disabled = false;
  if (loadBtn) loadBtn.disabled = false;
  if (status) status.textContent = 'Audio System Active | Ready for Input';

  updateMatrix();
  draw();
}

export function generateTone() {
  if (!audioContext) {
    initAudio();
  }

  if (oscillator) {
    oscillator.stop();
    oscillator.disconnect();
  }

  oscillator = audioContext.createOscillator();
  oscillator.type = 'sine';
  oscillator.frequency.value = 440;

  ensureProcessingChain();
  oscillator.connect(lowShelf);

  oscillator.start();
  isPlaying = true;

  const generateBtn = document.getElementById('generateBtn');
  const stopBtn = document.getElementById('stopBtn');
  const status = document.getElementById('status');

  if (generateBtn) generateBtn.disabled = true;
  if (stopBtn) stopBtn.disabled = false;
  if (status) status.textContent = 'Generating 440Hz Tone | Processing Active';
}

export function loadAudioFile(e) {
  const file = e.target.files[0];
  if (!file) return;

  if (!audioContext) {
    const statusEl = document.getElementById('status');
    if (statusEl) {
      statusEl.textContent = 'Start the audio engine before loading a file.';
    }
    e.target.value = '';
    const startButton = document.getElementById('startBtn');
    if (startButton) {
      startButton.focus({ preventScroll: true });
    }
    return;
  }

  const reader = new FileReader();
  reader.onload = function (event) {
    audioContext.decodeAudioData(event.target.result, function (buffer) {
      if (source) {
        source.stop();
        source.disconnect();
      }

      source = audioContext.createBufferSource();
      source.buffer = buffer;
      source.loop = true;

      ensureProcessingChain();
      source.connect(lowShelf);

      source.start();
      isPlaying = true;

      const generateBtn = document.getElementById('generateBtn');
      const stopBtn = document.getElementById('stopBtn');
      const status = document.getElementById('status');

      if (generateBtn) generateBtn.disabled = true;
      if (stopBtn) stopBtn.disabled = false;
      if (status) status.textContent = 'Playing Audio File | Processing Active';
    });
  };
  reader.readAsArrayBuffer(file);
}

export function stopAudio() {
  if (oscillator) {
    oscillator.stop();
    oscillator.disconnect();
    oscillator = null;
  }
  if (source) {
    source.stop();
    source.disconnect();
    source = null;
  }

  isPlaying = false;

  const generateBtn = document.getElementById('generateBtn');
  const stopBtn = document.getElementById('stopBtn');
  const status = document.getElementById('status');

  if (generateBtn) generateBtn.disabled = false;
  if (stopBtn) stopBtn.disabled = true;
  if (status) status.textContent = 'Audio Stopped | Ready for Input';
}

export function updateMatrix() {
  const matrixGrid = document.getElementById('matrixGrid');
  if (!matrixGrid) return;

  const parameters = ['Low', 'Mid', 'High', 'Drive', 'Curve', 'Mix'];
  matrixGrid.innerHTML = '';

  parameters.forEach((rowParam, rowIndex) => {
    parameters.forEach((colParam, colIndex) => {
      const cell = document.createElement('div');
      cell.className = 'matrix-cell';
      cell.innerHTML = `<strong>${rowParam}</strong><br>${colParam}`;

      if (rowIndex === colIndex) {
        cell.classList.add('active');
        cell.innerHTML += '<br>Self Influence';
      } else {
        const coupling = (Math.sin((rowIndex + 1) * (colIndex + 2)) + 1) / 2;
        const intensity = Math.round(coupling * 100);
        cell.innerHTML += `<br>${intensity}%`;
      }

      matrixGrid.appendChild(cell);
    });
  });
}

window.addEventListener('beforeunload', () => {
  if (audioContext) {
    audioContext.close();
  }
});
