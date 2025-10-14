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

  // FIX 6: Add session metadata header
  const sessionMeta = [
    `# CPWP Audio Parameter Control System - Session Export`,
    `# Export Date: ${new Date().toISOString()}`,
    `# Session Duration: ${((Date.now() - startTime) / 1000).toFixed(2)} seconds`,
    `# Total Events: ${analysisLog.length}`,
    `# Total Work: ${totalWork.toFixed(3)}`,
    `# User Agent: ${navigator.userAgent}`,
    `# Format: CSV (Comma-Separated Values)`,
    `# Reproducibility: Import this file to replay parameter changes`,
    ``
  ].join('\n');

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

  const csvContent = sessionMeta + [header, ...rows]
    .map(row => row.map(value => `"${value}"`).join(','))
    .join('\n');

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  const filename = `cpwp_log_${new Date().toISOString().replace(/[:.]/g, '-').substring(0, 19)}.csv`;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);

  console.log(`[FIX-6] CSV exported: ${filename} (${analysisLog.length} entries, ${(csvContent.length / 1024).toFixed(2)} KB)`);
}

export function exportLogJSON() {
  if (analysisLog.length === 0) {
    alert('No log data to export.');
    return;
  }

  // FIX 6: Create comprehensive exportable session object
  const sessionData = {
    metadata: {
      version: '2.0',
      exportDate: new Date().toISOString(),
      systemName: 'CPWP Audio Parameter Control System',
      sessionStartTime: new Date(startTime).toISOString(),
      sessionDuration: ((Date.now() - startTime) / 1000).toFixed(2),
      totalEvents: analysisLog.length,
      totalWork: totalWork.toFixed(3),
      userAgent: navigator.userAgent,
      platform: navigator.platform,
      language: navigator.language,
      screenResolution: `${window.screen.width}x${window.screen.height}`,
      reproducible: true,
      format: 'JSON'
    },

    // FIX 6: Include final parameter state for reproducibility
    finalState: getFinalParameterState(),

    // FIX 6: Include statistical summary
    statistics: calculateSessionStatistics(),

    // FIX 6: Include all log entries
    events: analysisLog,

    // FIX 6: Include re-import instructions
    instructions: {
      reimport: 'Load this file via Config Loader to restore parameter state',
      replay: 'Events can be replayed sequentially using timestamp data',
      analysis: 'Compatible with R, Python pandas, MATLAB for scientific analysis'
    }
  };

  const jsonString = JSON.stringify(sessionData, null, 2);
  const blob = new Blob([jsonString], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  const filename = `cpwp_session_${new Date().toISOString().replace(/[:.]/g, '-').substring(0, 19)}.json`;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);

  console.log(`[FIX-6] JSON exported: ${filename} (${analysisLog.length} entries, ${(jsonString.length / 1024).toFixed(2)} KB)`);
  console.log('[FIX-6] Session statistics:', sessionData.statistics);
}

// FIX 6: Helper function to get final parameter state
function getFinalParameterState() {
  // Build final state from log entries
  const finalParams = {
    low: 0,
    mid: 0,
    high: 0,
    drive: 1,
    curve: 1,
    mix: 0
  };

  analysisLog.forEach(entry => {
    finalParams[entry.parameter] = parseFloat(entry.newValue);
  });

  return finalParams;
}

// FIX 6: Helper function to calculate session statistics
function calculateSessionStatistics() {
  if (analysisLog.length === 0) {
    return {
      message: 'No events to analyze'
    };
  }

  const paramCounts = {};
  const paramWork = {};
  let maxForce = 0;
  let maxWork = 0;

  analysisLog.forEach(entry => {
    const param = entry.parameter;
    paramCounts[param] = (paramCounts[param] || 0) + 1;
    paramWork[param] = (paramWork[param] || 0) + parseFloat(entry.work);
    maxForce = Math.max(maxForce, parseFloat(entry.force));
    maxWork = Math.max(maxWork, parseFloat(entry.work));
  });

  return {
    totalEvents: analysisLog.length,
    totalWork: totalWork.toFixed(3),
    sessionDuration: ((Date.now() - startTime) / 1000).toFixed(2),
    averageWorkPerEvent: (totalWork / analysisLog.length).toFixed(3),
    eventRate: (analysisLog.length / ((Date.now() - startTime) / 1000)).toFixed(2) + ' events/sec',
    maxForce: maxForce.toFixed(3),
    maxWork: maxWork.toFixed(3),
    parameterCounts: paramCounts,
    parameterWork: Object.fromEntries(
      Object.entries(paramWork).map(([k, v]) => [k, v.toFixed(3)])
    ),
    mostActiveParameter: Object.entries(paramCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || 'none'
  };
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
