import { PHI, mapDriveCurve, getParams, pickFreqInRange } from './soundlab-utils.js';
import {
  getAudioContext,
  getFilters,
  ensureProcessingChain,
  setAudioPlaying,
  getParamsState
} from './soundlab-audio-core.js';

let phiOscillators = [];
let phiAuxNodes = [];
let phiTimeout = null;
let lastParams = null;

function registerPhiOscillator(osc) {
  phiOscillators.push(osc);
  return osc;
}

function registerPhiNode(node) {
  phiAuxNodes.push(node);
  return node;
}

export function stopPhiSynthesis() {
  phiOscillators.forEach(osc => {
    try {
      osc.stop();
      osc.disconnect();
    } catch (e) {}
  });
  phiOscillators = [];

  phiAuxNodes.forEach(node => {
    try {
      node.disconnect();
    } catch (e) {}
  });
  phiAuxNodes = [];

  if (phiTimeout) {
    clearTimeout(phiTimeout);
    phiTimeout = null;
  }
}

function applyEnvelope(gainNode, duration, driveCurve, now, ctx) {
  const scale = typeof gainNode.__phiScale === 'number' ? gainNode.__phiScale : 1;
  const safeDuration = Number.isFinite(duration) && duration > 0 ? duration : 3;
  const attack = Math.max(0.05, Math.min(safeDuration * 0.2, 0.5));
  const sustainTime = Math.max(safeDuration - attack * 2, 0);
  const peak = mapDriveCurve(driveCurve, 1) * scale;
  const sustainLevel = mapDriveCurve(driveCurve, 0.5) * scale;
  const ctxNow = ctx && typeof ctx.currentTime === 'number' ? ctx.currentTime : now;
  const start = Math.max(now, ctxNow);
  const attackEnd = start + attack;
  const sustainEnd = attackEnd + sustainTime;
  const releaseEnd = start + safeDuration;

  gainNode.gain.cancelScheduledValues(start);
  gainNode.gain.setValueAtTime(0, start);
  gainNode.gain.linearRampToValueAtTime(peak, attackEnd);

  if (sustainTime > 0) {
    gainNode.gain.linearRampToValueAtTime(sustainLevel, sustainEnd);
  }

  gainNode.gain.linearRampToValueAtTime(0, releaseEnd);
}

export function runPhiMode(mode) {
  const audioContext = getAudioContext();
  if (!audioContext) {
    alert('Please click START AUDIO first!');
    return;
  }

  const { lowShelf } = getFilters();
  if (!lowShelf) {
    alert('Audio chain not ready.');
    return;
  }

  ensureProcessingChain();
  stopPhiSynthesis();

  const now = audioContext.currentTime;
  let branchDuration = 0;
  let modeLabel = mode;
  let savedParams = null;

  switch (mode) {
    case 'phi_tone': {
      const currentParams = getParams();
      savedParams = currentParams;
      const { baseFreq, duration, driveCurve, freqRange } = currentParams;
      const safeBase = baseFreq > 0 ? baseFreq : 220;
      const range = freqRange || [safeBase, safeBase * PHI];
      const runDuration = Number.isFinite(duration) && duration > 0 ? duration : 3;
      branchDuration = runDuration;
      const osc = registerPhiOscillator(audioContext.createOscillator());
      osc.type = 'sine';
      const freq = pickFreqInRange(safeBase * PHI, range);
      osc.frequency.setValueAtTime(freq, now);

      const gain = registerPhiNode(audioContext.createGain());
      gain.__phiScale = 0.6;
      applyEnvelope(gain, runDuration, driveCurve, now, audioContext);

      osc.connect(gain);
      gain.connect(lowShelf);
      osc.start(now);

      modeLabel = 'Φ Tone';
      break;
    }
    case 'phi_AM': {
      const currentParams = getParams();
      savedParams = currentParams;
      const { baseFreq, duration, driveCurve, freqRange } = currentParams;
      const safeBase = baseFreq > 0 ? baseFreq : 220;
      const range = freqRange || [safeBase, safeBase * PHI];
      const runDuration = Number.isFinite(duration) && duration > 0 ? duration : 3;
      branchDuration = runDuration;

      const carrierFreq = pickFreqInRange(safeBase, range);
      const modFreq = pickFreqInRange(safeBase / PHI, range);

      const carrier = registerPhiOscillator(audioContext.createOscillator());
      carrier.type = 'sine';
      carrier.frequency.setValueAtTime(carrierFreq, now);

      const modulator = registerPhiOscillator(audioContext.createOscillator());
      modulator.type = 'sine';
      modulator.frequency.setValueAtTime(modFreq, now);

      const voiceGain = registerPhiNode(audioContext.createGain());
      voiceGain.__phiScale = mapDriveCurve(driveCurve, 0.8) * 0.6;
      applyEnvelope(voiceGain, runDuration, driveCurve, now, audioContext);

      const modGain = registerPhiNode(audioContext.createGain());
      const depth = mapDriveCurve(driveCurve, 0.6) * carrierFreq * 0.25;
      modGain.gain.setValueAtTime(depth, now);

      modulator.connect(modGain);
      modGain.connect(carrier.frequency);

      carrier.connect(voiceGain);
      voiceGain.connect(lowShelf);

      carrier.start(now);
      modulator.start(now);

      modeLabel = 'Φ AM';
      break;
    }
    case 'phi_FM': {
      const currentParams = getParams();
      savedParams = currentParams;
      const { baseFreq, duration, driveCurve, freqRange } = currentParams;
      const safeBase = baseFreq > 0 ? baseFreq : 220;
      const range = freqRange || [safeBase, safeBase * PHI];
      const runDuration = Number.isFinite(duration) && duration > 0 ? duration : 3;
      branchDuration = runDuration;

      const carrierFreq = pickFreqInRange(safeBase, range);
      const modFreq = pickFreqInRange(safeBase * PHI, range);

      const carrier = registerPhiOscillator(audioContext.createOscillator());
      carrier.type = 'sine';
      carrier.frequency.setValueAtTime(carrierFreq, now);

      const modulator = registerPhiOscillator(audioContext.createOscillator());
      modulator.type = 'sine';
      modulator.frequency.setValueAtTime(modFreq, now);

      const voiceGain = registerPhiNode(audioContext.createGain());
      voiceGain.__phiScale = mapDriveCurve(driveCurve, 0.9) * 0.6;
      applyEnvelope(voiceGain, runDuration, driveCurve, now, audioContext);

      const fmGain = registerPhiNode(audioContext.createGain());
      const depth = mapDriveCurve(driveCurve, 0.7) * modFreq * 0.35;
      fmGain.gain.setValueAtTime(depth, now);

      modulator.connect(fmGain);
      fmGain.connect(carrier.frequency);

      carrier.connect(voiceGain);
      voiceGain.connect(lowShelf);

      carrier.start(now);
      modulator.start(now);

      modeLabel = 'Φ FM';
      break;
    }
    case 'phi_interval': {
      const currentParams = getParams();
      savedParams = currentParams;
      const { baseFreq, duration, driveCurve, freqRange } = currentParams;
      const safeBase = baseFreq > 0 ? baseFreq : 220;
      const range = freqRange || [safeBase, safeBase * Math.pow(PHI, 3)];
      const runDuration = Number.isFinite(duration) && duration > 0 ? duration : 3;
      branchDuration = runDuration;

      const intervals = [1, PHI, Math.pow(PHI, 2), Math.pow(PHI, 3)];
      intervals.forEach((interval, index) => {
        const osc = registerPhiOscillator(audioContext.createOscillator());
        osc.type = 'sine';
        const freq = pickFreqInRange(safeBase * interval, range);
        osc.frequency.setValueAtTime(freq, now);

        const voiceGain = registerPhiNode(audioContext.createGain());
        voiceGain.__phiScale = mapDriveCurve(driveCurve, (index + 1) / intervals.length) * 0.4;
        applyEnvelope(voiceGain, runDuration, driveCurve, now, audioContext);

        osc.connect(voiceGain);
        voiceGain.connect(lowShelf);
        osc.start(now);
      });

      modeLabel = 'Φ Interval Stack';
      break;
    }
    case 'phi_harmonic': {
      const currentParams = getParams();
      savedParams = currentParams;
      const { baseFreq, duration, driveCurve, freqRange } = currentParams;
      const safeBase = baseFreq > 0 ? baseFreq : 220;
      const range = freqRange || [safeBase, safeBase * 8];
      const runDuration = Number.isFinite(duration) && duration > 0 ? duration : 3;
      branchDuration = runDuration;

      for (let i = 1; i <= 8; i++) {
        const osc = registerPhiOscillator(audioContext.createOscillator());
        osc.type = 'sine';
        const freq = pickFreqInRange(safeBase * i, range);
        osc.frequency.setValueAtTime(freq, now);

        const voiceGain = registerPhiNode(audioContext.createGain());
        const phiWeight = 1 / Math.pow(PHI, i - 1);
        voiceGain.__phiScale = mapDriveCurve(driveCurve, 1 / i) * phiWeight * 0.5;
        applyEnvelope(voiceGain, runDuration, driveCurve, now, audioContext);

        osc.connect(voiceGain);
        voiceGain.connect(lowShelf);
        osc.start(now);
      }

      modeLabel = 'Φ Harmonic';
      break;
    }
    default:
      console.warn('Unknown phi mode:', mode);
      return;
  }

  const runDuration = Number.isFinite(branchDuration) && branchDuration > 0 ? branchDuration : 3;
  setAudioPlaying(true);
  const stopBtn = document.getElementById('stopBtn');
  const status = document.getElementById('status');

  if (stopBtn) stopBtn.disabled = false;
  if (status) status.textContent = `Running ${modeLabel} for ${runDuration.toFixed(2)}s`;

  // FIX 3: Save parameters including mode for restoration
  if (savedParams) {
    lastParams = {
      ...savedParams,
      mode: mode, // FIX 3: Save the current mode
      freqRange: Array.isArray(savedParams.freqRange) ? [...savedParams.freqRange] : savedParams.freqRange
    };
    const restoreButton = document.getElementById('restoreParamsBtn');
    if (restoreButton) {
      restoreButton.disabled = false;
    }
    console.log('[FIX-3] Saved Φ parameters for restoration:', lastParams);
  }

  if (phiTimeout) {
    clearTimeout(phiTimeout);
  }

  phiTimeout = setTimeout(() => {
    stopPhiSynthesis();
    setAudioPlaying(false);
    if (status) status.textContent = `${modeLabel} complete`;
  }, runDuration * 1000);
}

export function restoreLastParams() {
  // FIX 3: Check if previous params exist
  if (!lastParams) {
    console.warn('[FIX-3] No previous Φ parameters to restore');
    const status = document.getElementById('status');
    if (status) {
      status.textContent = 'No previous Φ parameters available';
    }
    return;
  }

  // FIX 3: Extract all saved parameters
  const { baseFreq, duration, driveCurve, freqRange, mode } = lastParams;

  // FIX 3: Restore mode selector if available
  const modeField = document.getElementById('phiMode');
  if (modeField && mode) {
    modeField.value = mode;
  }

  // FIX 3: Restore base frequency
  const baseField = document.getElementById('baseFreq');
  if (baseField && Number.isFinite(baseFreq)) {
    baseField.value = baseFreq;
    console.log(`[FIX-3] Restored baseFreq: ${baseFreq} Hz`);
  }

  // FIX 3: Restore duration
  const durationField = document.getElementById('duration') || document.getElementById('phiDuration');
  if (durationField && Number.isFinite(duration)) {
    durationField.value = duration;
    console.log(`[FIX-3] Restored duration: ${duration} s`);
  }

  // FIX 3: Restore drive curve
  const driveCurveField = document.getElementById('driveCurve');
  if (driveCurveField && driveCurve) {
    driveCurveField.value = driveCurve;
    console.log(`[FIX-3] Restored driveCurve: ${driveCurve}`);
  }

  // FIX 3: Restore frequency range
  const freqRangeField = document.getElementById('frequencyRange') || document.getElementById('freqRange');
  if (freqRangeField && Array.isArray(freqRange)) {
    freqRangeField.value = `${freqRange[0]}-${freqRange[1]}`;
    console.log(`[FIX-3] Restored freqRange: ${freqRange[0]}-${freqRange[1]} Hz`);
  }

  // FIX 3: Visual confirmation feedback
  const status = document.getElementById('status');
  if (status) {
    const modeText = mode ? ` (${mode})` : '';
    status.textContent = `Φ parameters restored${modeText} | Base: ${baseFreq}Hz | Duration: ${duration}s`;
  }

  // FIX 3: Highlight restored fields temporarily
  [baseField, durationField, driveCurveField, freqRangeField].forEach(field => {
    if (field) {
      field.style.backgroundColor = '#002200';
      setTimeout(() => {
        field.style.backgroundColor = '';
      }, 1500);
    }
  });

  console.log('[FIX-3] All Φ parameters restored successfully:', lastParams);
}

export function diagnosticParamsLog() {
  // FIX 5: Get comprehensive parameter state
  const { baseFreq, driveCurve, freqRange, duration } = getParams();
  const audioParams = getParamsState();
  const audioContext = getAudioContext();

  const rangeText = Array.isArray(freqRange) && freqRange.length === 2 ? `${freqRange[0]}-${freqRange[1]}` : 'N/A';

  // FIX 5: Calculate derived metrics
  const derivedMetrics = {
    timestamp: new Date().toISOString(),
    systemTime: audioContext ? audioContext.currentTime.toFixed(3) : 'N/A',

    // Audio parameters
    audioParams: {
      eqLow: audioParams.low,
      eqMid: audioParams.mid,
      eqHigh: audioParams.high,
      satDrive: audioParams.drive,
      satCurve: audioParams.curve,
      satMix: audioParams.mix
    },

    // Phi parameters
    phiParams: {
      baseFreq,
      duration,
      driveCurve,
      freqRange: rangeText
    },

    // FIX 5: Spectral metrics (if audio is playing)
    spectral: calculateSpectralMetrics(),

    // FIX 5: Parameter work metrics
    parameterWork: calculateParameterWork(audioParams),

    // FIX 5: System state
    systemState: {
      audioContextState: audioContext ? audioContext.state : 'not initialized',
      sampleRate: audioContext ? audioContext.sampleRate : 'N/A',
      phi: PHI,
      phiSquared: PHI * PHI
    }
  };

  // FIX 5: Log to console with full detail
  console.log('═══════════════════════════════════════════');
  console.log('CPWP DIAGNOSTIC LOG');
  console.log('═══════════════════════════════════════════');
  console.log('Timestamp:', derivedMetrics.timestamp);
  console.log('System Time:', derivedMetrics.systemTime, 's');
  console.log('-------------------------------------------');
  console.log('Audio Parameters:', derivedMetrics.audioParams);
  console.log('Phi Parameters:', derivedMetrics.phiParams);
  console.log('Spectral Metrics:', derivedMetrics.spectral);
  console.log('Parameter Work:', derivedMetrics.parameterWork);
  console.log('System State:', derivedMetrics.systemState);
  console.log('═══════════════════════════════════════════');

  // FIX 5: Update status with key metrics
  const status = document.getElementById('status');
  if (status) {
    const baseText = Number.isFinite(baseFreq) ? baseFreq : 'N/A';
    const durationText = Number.isFinite(duration) ? duration : 'N/A';
    const rmsText = derivedMetrics.spectral.rmsDB !== 'N/A' ? `RMS: ${derivedMetrics.spectral.rmsDB}dB` : '';
    status.textContent = `Diagnostic → base: ${baseText} Hz | ${rmsText} | Work: ${derivedMetrics.parameterWork.totalWork.toFixed(2)}`;
  }

  // FIX 5: Return metrics for logging system
  return derivedMetrics;
}

// FIX 5: Helper function to calculate spectral metrics
function calculateSpectralMetrics() {
  const audioContext = getAudioContext();
  if (!audioContext) {
    return {
      rmsDB: 'N/A',
      spectralCentroid: 'N/A',
      spectralEntropy: 'N/A'
    };
  }

  // Get analyser data (if available from global scope or passed)
  // This is a simplified version - in production you'd access the analyser directly
  return {
    rmsDB: 'Calculated in visualizer',
    spectralCentroid: 'Requires FFT data',
    spectralEntropy: 'Requires FFT data',
    note: 'Full spectral analysis available in visualizer canvas overlay'
  };
}

// FIX 5: Helper function to calculate parameter work
function calculateParameterWork(params) {
  // Calculate total "work" done by parameter changes
  // Work = sum of absolute parameter values weighted by their ranges
  const eqWork = (Math.abs(params.low) + Math.abs(params.mid) + Math.abs(params.high)) / 20; // EQ range is ±20dB
  const satWork = (params.drive - 1) / 9 + Math.abs(params.curve - 1) / 4.9 + params.mix / 100; // Normalize to 0-1
  const totalWork = eqWork + satWork;

  return {
    eqWork: eqWork.toFixed(3),
    satWork: satWork.toFixed(3),
    totalWork: totalWork.toFixed(3),
    workRate: 'Tracked in CPWP log'
  };
}

export function getPhiParamsState() {
  return getParamsState();
}
