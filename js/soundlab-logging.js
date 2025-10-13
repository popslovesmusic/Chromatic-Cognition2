const analysisLog = [];
let totalWork = 0;
let startTime = Date.now();

const logDisplay = () => document.getElementById('logDisplay');
const logCountLabel = () => document.getElementById('logCount');
const workOutputLabel = () => document.getElementById('workOutput');

function flashLogDisplay() {
  const logDiv = logDisplay();
  if (!logDiv) return;
  logDiv.classList.add('log-display--flash');
  setTimeout(() => {
    logDiv.classList.remove('log-display--flash');
  }, 250);
}

export function logParameterChange(param, oldValue, newValue) {
  const now = Date.now();
  const elapsedSeconds = (now - startTime) / 1000;
  const timestamp = new Date(now).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });

  const force = Math.abs(newValue - oldValue);
  const work = force * 0.1;
  totalWork += work;

  const logEntry = {
    time: elapsedSeconds.toFixed(3),
    timestamp,
    parameter: param,
    oldValue: oldValue.toFixed(3),
    newValue: newValue.toFixed(3),
    delta: (newValue - oldValue).toFixed(3),
    force: force.toFixed(3),
    work: work.toFixed(3),
    totalWork: totalWork.toFixed(3)
  };

  analysisLog.push(logEntry);
  flashLogDisplay();
  updateLogDisplay();
}

export function updateLogDisplay() {
  const logDiv = logDisplay();
  if (!logDiv) return;

  const maxDisplay = 20;
  const recentLogs = analysisLog.slice(-maxDisplay);

  if (recentLogs.length === 0) {
    logDiv.innerHTML = '<div class="log-placeholder">Waiting for parameter changes...</div>';
    const countLabel = logCountLabel();
    const workLabel = workOutputLabel();
    if (countLabel) {
      countLabel.textContent = '0 events logged';
    }
    if (workLabel) {
      workLabel.textContent = 'Total Work: 0.00';
    }
    logDiv.scrollTop = 0;
    return;
  }

  const logHtml = recentLogs
    .map(entry => {
      const isHighForce = parseFloat(entry.force) > 1;
      const entryClass = isHighForce ? 'log-entry log-entry--high' : 'log-entry log-entry--medium';
      return `<div class="${entryClass}">[${entry.timestamp} | +${entry.time}s] ${entry.parameter.toUpperCase()}: ${entry.oldValue} → ${entry.newValue} (Δ=${entry.delta}, F=${entry.force}, W=${entry.work})</div>`;
    })
    .join('');

  logDiv.innerHTML = logHtml;
  requestAnimationFrame(() => {
    logDiv.scrollTop = logDiv.scrollHeight;
  });

  const countLabel = logCountLabel();
  const workLabel = workOutputLabel();
  if (countLabel) {
    countLabel.textContent = `${analysisLog.length} events logged`;
  }
  if (workLabel) {
    workLabel.textContent = `Total Work: ${totalWork.toFixed(2)}`;
  }
}

export function clearLog() {
  analysisLog.length = 0;
  totalWork = 0;
  startTime = Date.now();
  updateLogDisplay();
}

export function exportLogCSV() {
  if (analysisLog.length === 0) {
    alert('No log data to export.');
    return;
  }

  const header = ['Timestamp', 'ElapsedSeconds', 'Parameter', 'OldValue', 'NewValue', 'Delta', 'Force', 'Work', 'TotalWork'];
  const rows = analysisLog.map(entry => [
    entry.timestamp,
    entry.time,
    entry.parameter,
    entry.oldValue,
    entry.newValue,
    entry.delta,
    entry.force,
    entry.work,
    entry.totalWork
  ]);

  const csvContent = [header, ...rows]
    .map(row => row.map(value => `"${value}"`).join(','))
    .join('\n');

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'cpwp_log.csv';
  link.click();
  URL.revokeObjectURL(url);
}

export function exportLogJSON() {
  if (analysisLog.length === 0) {
    alert('No log data to export.');
    return;
  }

  const blob = new Blob([JSON.stringify(analysisLog, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'cpwp_log.json';
  link.click();
  URL.revokeObjectURL(url);
}

export function ensureShortcutLegend() {
  const legend = document.getElementById('shortcutLegend');
  if (!legend) return;

  const shortcuts = Array.from(document.querySelectorAll('[data-shortcut]'))
    .filter(btn => btn.dataset.shortcutLabel !== 'skip')
    .map(btn => {
      const combo = btn.dataset.shortcut;
      const label = btn.dataset.shortcutLabel || btn.textContent.trim();
      return `<span><kbd>${combo}</kbd>${label ? ` ${label}` : ''}</span>`;
    });

  legend.innerHTML = shortcuts.join('');
}

export function initLogging() {
  updateLogDisplay();
  ensureShortcutLegend();
}
