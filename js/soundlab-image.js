import { getAudioContext, getGainNode } from './soundlab-audio-core.js';

let imageData = null;
let imageScanPosition = 0;
let imagePlaying = false;
let imageOscillators = [];
let imageScanInterval = null;

export function loadImage(e) {
  const file = e.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = function (event) {
    const img = new Image();
    img.onload = function () {
      const canvas = document.getElementById('imageCanvas');
      const ctx = canvas.getContext('2d');

      const maxSize = 512;
      let width = img.width;
      let height = img.height;

      if (width > height) {
        if (width > maxSize) {
          height = (height / width) * maxSize;
          width = maxSize;
        }
      } else {
        if (height > maxSize) {
          width = (width / height) * maxSize;
          height = maxSize;
        }
      }

      canvas.width = width;
      canvas.height = height;

      ctx.drawImage(img, 0, 0, width, height);
      imageData = ctx.getImageData(0, 0, width, height);

      const panel = document.getElementById('imagePanel');
      if (panel) {
        panel.classList.remove('is-hidden');
      }
      const playButton = document.getElementById('playImageBtn');
      if (playButton) playButton.disabled = false;
      const info = document.getElementById('imageInfo');
      if (info) info.textContent = `${width}x${height} pixels loaded`;

      if (!getAudioContext()) {
        alert('Please click START AUDIO first!');
        return;
      }

      const status = document.getElementById('status');
      if (status) status.textContent = 'Image loaded | Ready to sonify';
    };
    img.src = event.target.result;
  };
  reader.readAsDataURL(file);
}

export function toggleImagePlayback() {
  if (imagePlaying) {
    stopImagePlayback();
  } else {
    startImagePlayback();
  }
}

function startImagePlayback() {
  const audioContext = getAudioContext();
  if (!imageData || !audioContext) return;

  imagePlaying = true;
  imageScanPosition = 0;
  const playButton = document.getElementById('playImageBtn');
  if (playButton) playButton.textContent = 'Stop Image';
  const status = document.getElementById('status');
  if (status) status.textContent = 'Sonifying image...';

  const mode = document.getElementById('sonifyMode').value;

  if (mode === 'spectral') {
    playSpectralMode();
  } else if (mode === 'harmonic') {
    playHarmonicMode();
  } else if (mode === 'fm') {
    playFMMode();
  } else if (mode === 'additive') {
    playAdditiveMode();
  }
}

export function stopImagePlayback() {
  imagePlaying = false;
  const playButton = document.getElementById('playImageBtn');
  if (playButton) playButton.textContent = 'Play Image';
  const status = document.getElementById('status');
  if (status) status.textContent = 'Image playback stopped';

  if (imageScanInterval) {
    clearInterval(imageScanInterval);
    imageScanInterval = null;
  }

  imageOscillators.forEach(osc => {
    try {
      osc.stop();
      osc.disconnect();
    } catch (e) {}
  });
  imageOscillators = [];
}

function playSpectralMode() {
  const audioContext = getAudioContext();
  const gainNode = getGainNode();
  if (!audioContext || !gainNode || !imageData) return;

  const width = imageData.width;
  const height = imageData.height;
  const freqMin = parseFloat(document.getElementById('freqMin').value);
  const freqMax = parseFloat(document.getElementById('freqMax').value);
  const scanSpeed = parseFloat(document.getElementById('scanSpeed').value);

  const numBands = Math.min(height, 32);
  const oscillators = [];
  const gains = [];

  for (let i = 0; i < numBands; i++) {
    const osc = audioContext.createOscillator();
    const gain = audioContext.createGain();

    const freq = freqMin * Math.pow(freqMax / freqMin, i / numBands);
    osc.frequency.value = freq;
    osc.type = 'sine';

    gain.gain.value = 0;

    osc.connect(gain);
    gain.connect(gainNode);
    osc.start();

    oscillators.push(osc);
    gains.push(gain);
  }

  imageOscillators = oscillators;

  const msPerColumn = 50 / scanSpeed;
  imageScanInterval = setInterval(() => {
    if (imageScanPosition >= width) {
      stopImagePlayback();
      return;
    }

    for (let band = 0; band < numBands; band++) {
      const row = Math.floor((band / numBands) * height);
      const idx = (row * width + imageScanPosition) * 4;

      const r = imageData.data[idx];
      const g = imageData.data[idx + 1];
      const b = imageData.data[idx + 2];
      const brightness = (r + g + b) / 3 / 255;

      gains[band].gain.linearRampToValueAtTime(brightness * 0.3, audioContext.currentTime + 0.05);
    }

    drawScanIndicator(width, height);
    imageScanPosition++;
  }, msPerColumn);
}

function playHarmonicMode() {
  const audioContext = getAudioContext();
  const gainNode = getGainNode();
  if (!audioContext || !gainNode || !imageData) return;

  const width = imageData.width;
  const height = imageData.height;
  const freqMin = parseFloat(document.getElementById('freqMin').value);
  const freqMax = parseFloat(document.getElementById('freqMax').value);
  const scanSpeed = parseFloat(document.getElementById('scanSpeed').value);

  const msPerColumn = 60 / scanSpeed;
  imageScanInterval = setInterval(() => {
    if (imageScanPosition >= width) {
      stopImagePlayback();
      return;
    }

    for (let y = 0; y < height; y++) {
      const idx = (y * width + imageScanPosition) * 4;
      const brightness = (imageData.data[idx] + imageData.data[idx + 1] + imageData.data[idx + 2]) / 3 / 255;
      if (brightness > 0.1) {
        const freq = freqMin * Math.pow(freqMax / freqMin, y / height);
        const osc = audioContext.createOscillator();
        const gain = audioContext.createGain();
        const now = audioContext.currentTime;

        osc.frequency.value = freq;
        osc.type = 'sine';

        gain.gain.setValueAtTime(0, now);
        gain.gain.linearRampToValueAtTime(brightness * 0.2, now + 0.05);
        gain.gain.linearRampToValueAtTime(0, now + 0.3);

        osc.connect(gain);
        gain.connect(gainNode);
        osc.start(now);
        osc.stop(now + 0.3);
      }
    }

    drawScanIndicator(width, height);
    imageScanPosition++;
  }, msPerColumn);
}

function playFMMode() {
  const audioContext = getAudioContext();
  const gainNode = getGainNode();
  if (!audioContext || !gainNode || !imageData) return;

  const width = imageData.width;
  const height = imageData.height;
  const scanSpeed = parseFloat(document.getElementById('scanSpeed').value);

  const carrier = audioContext.createOscillator();
  const modulator = audioContext.createOscillator();
  const modGain = audioContext.createGain();

  carrier.type = 'sine';
  modulator.type = 'sine';

  modulator.connect(modGain);
  modGain.connect(carrier.frequency);
  carrier.connect(gainNode);

  carrier.start();
  modulator.start();

  imageOscillators = [carrier, modulator];

  const msPerColumn = 100 / scanSpeed;
  imageScanInterval = setInterval(() => {
    if (imageScanPosition >= width) {
      stopImagePlayback();
      return;
    }

    let avgR = 0;
    let avgG = 0;
    let avgB = 0;
    for (let y = 0; y < height; y++) {
      const idx = (y * width + imageScanPosition) * 4;
      avgR += imageData.data[idx];
      avgG += imageData.data[idx + 1];
      avgB += imageData.data[idx + 2];
    }
    avgR /= height;
    avgG /= height;
    avgB /= height;

    const carrierFreq = 200 + (avgR / 255) * 1800;
    const modFreq = 50 + (avgG / 255) * 950;
    const modIndex = (avgB / 255) * 500;

    carrier.frequency.linearRampToValueAtTime(carrierFreq, audioContext.currentTime + 0.1);
    modulator.frequency.linearRampToValueAtTime(modFreq, audioContext.currentTime + 0.1);
    modGain.gain.linearRampToValueAtTime(modIndex, audioContext.currentTime + 0.1);

    drawScanIndicator(width, height);
    imageScanPosition++;
  }, msPerColumn);
}

function playAdditiveMode() {
  const audioContext = getAudioContext();
  const gainNode = getGainNode();
  if (!audioContext || !gainNode || !imageData) return;

  const width = imageData.width;
  const height = imageData.height;
  const scanSpeed = parseFloat(document.getElementById('scanSpeed').value);
  const freqMin = parseFloat(document.getElementById('freqMin').value);
  const freqMax = parseFloat(document.getElementById('freqMax').value);

  const msPerColumn = 30 / scanSpeed;
  imageScanInterval = setInterval(() => {
    if (imageScanPosition >= width) {
      stopImagePlayback();
      return;
    }

    const grainDuration = 0.05;

    for (let y = 0; y < height; y += Math.ceil(height / 16)) {
      const idx = (y * width + imageScanPosition) * 4;

      const r = imageData.data[idx];
      const g = imageData.data[idx + 1];
      const b = imageData.data[idx + 2];
      const brightness = (r + g + b) / 3 / 255;

      if (brightness > 0.1) {
        const freq = freqMin * Math.pow(freqMax / freqMin, y / height);
        const osc = audioContext.createOscillator();
        const gain = audioContext.createGain();
        const now = audioContext.currentTime;

        osc.frequency.value = freq;
        osc.type = 'sine';

        gain.gain.setValueAtTime(0, now);
        gain.gain.linearRampToValueAtTime(brightness * 0.3, now + grainDuration * 0.1);
        gain.gain.linearRampToValueAtTime(0, now + grainDuration);

        osc.connect(gain);
        gain.connect(gainNode);
        osc.start(now);
        osc.stop(now + grainDuration);
      }
    }

    drawScanIndicator(width, height);
    imageScanPosition++;
  }, msPerColumn);
}

function drawScanIndicator(width, height) {
  const canvas = document.getElementById('imageCanvas');
  const ctx = canvas.getContext('2d');
  ctx.putImageData(imageData, 0, 0);
  ctx.strokeStyle = '#00ff00';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(imageScanPosition, 0);
  ctx.lineTo(imageScanPosition, height);
  ctx.stroke();
}
