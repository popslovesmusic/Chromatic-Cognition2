export const PHI = (1 + Math.sqrt(5)) / 2;

export function parseFreqRange(value) {
  if (typeof value !== 'string') {
    return null;
  }

  const cleaned = value.replace(/[^0-9,\-]/g, '').trim();
  if (!cleaned) {
    return null;
  }

  const parts = cleaned.includes('-') ? cleaned.split('-') : cleaned.split(',');

  if (parts.length !== 2) return null;

  const min = Number(parts[0]);
  const max = Number(parts[1]);

  if (Number.isNaN(min) || Number.isNaN(max)) {
    return null;
  }

  return [min, max];
}

export function mapDriveCurve(curve, t) {
  const clamped = Math.min(Math.max(t, 0), 1);
  switch ((curve || 'linear').toLowerCase()) {
    case 'log':
      return clamped * clamped;
    case 'exp':
      return Math.sqrt(clamped);
    default:
      return clamped;
  }
}

export function getParams() {
  const baseFreqEl = document.getElementById('baseFreq');
  const durationEl = document.getElementById('duration') || document.getElementById('phiDuration');
  const driveCurveEl = document.getElementById('driveCurve');
  const freqRangeEl = document.getElementById('frequencyRange') || document.getElementById('freqRange');

  const baseFreq = baseFreqEl ? parseFloat(baseFreqEl.value) : 0;
  const duration = durationEl ? parseFloat(durationEl.value) : 0;
  const driveCurve = driveCurveEl ? driveCurveEl.value : 'linear';
  let freqRange = freqRangeEl ? parseFreqRange(freqRangeEl.value) : null;

  if (!freqRange && baseFreq) {
    freqRange = [baseFreq, baseFreq];
  }

  return {
    baseFreq: Number.isFinite(baseFreq) ? baseFreq : 0,
    duration: Number.isFinite(duration) ? duration : 0,
    driveCurve,
    freqRange
  };
}

export function adaptIncomingConfig(cfg) {
  if (!cfg || typeof cfg !== 'object') return cfg;

  const normalized = JSON.parse(JSON.stringify(cfg));

  if ('freq_range' in normalized && !('frequencyRange' in normalized)) {
    normalized.frequencyRange = normalized.freq_range;
  }

  if (normalized.input && 'freq_range' in normalized.input && !('frequencyRange' in normalized)) {
    normalized.frequencyRange = normalized.input.freq_range;
  }

  if ('phiDuration' in normalized && !('duration' in normalized)) {
    normalized.duration = normalized.phiDuration;
  }

  if (normalized.input && 'phiDuration' in normalized.input && !('duration' in normalized.input)) {
    normalized.input.duration = normalized.input.phiDuration;
  }

  const hasScanSpeed = !!document.getElementById('scanSpeed');
  if (hasScanSpeed) {
    if ('scan_speed' in normalized && !('scanSpeed' in normalized)) {
      normalized.scanSpeed = normalized.scan_speed;
    }

    if (normalized.input && 'scan_speed' in normalized.input && !('scanSpeed' in normalized)) {
      normalized.scanSpeed = normalized.input.scan_speed;
    }
  }

  return normalized;
}

export function pickFreqInRange(target, range) {
  if (!Array.isArray(range) || range.length !== 2) {
    return target;
  }

  const parsed = range.map(Number);
  if (parsed.some(value => !Number.isFinite(value))) {
    return target;
  }

  const min = Math.min(parsed[0], parsed[1]);
  const max = Math.max(parsed[0], parsed[1]);

  if (max <= 0) {
    return target;
  }

  if (min === max) {
    return min;
  }

  return Math.min(Math.max(target, min), max);
}

export function updateKnobRotation(knob, value, min, max) {
  const range = max - min;
  const normalized = (value - min) / range;
  const rotation = -135 + normalized * 270;
  const scale = knob.classList.contains('selected') ? 1.1 : 1;
  knob.style.transform = `rotate(${rotation}deg) scale(${scale})`;
}
