/**
 * Phi-Matrix Dashboard - Feature 017
 *
 * Unified dashboard integrating all Soundlab visualization and control components.
 *
 * Features:
 * - FR-001: Integrate all dashboard modules
 * - FR-002: Synchronized clock across components
 * - FR-003: Bidirectional WebSocket < 50ms
 * - FR-004: Layout persistence to localStorage
 * - SC-001: <= 100ms latency
 * - SC-002: >= 30fps sustained
 * - SC-003: <= 50ms interaction delay
 * - SC-004: No desync > 0.1s for 60s+
 */

// ============================================================================
// CONSTANTS AND CONFIGURATION
// ============================================================================

const GOLDEN_ANGLE = 137.5077640500378;
const MIN_FREQUENCY = 20;
const MAX_FREQUENCY = 2000;
const AMPLITUDE_GAMMA = 2.2;
const PHI_BREATHING_FREQUENCY = 1.5; // Hz

const CONFIG = {
    websocketUrl: `ws://${window.location.host}/ws/dashboard`,
    reconnectDelay: 2000,
    latencyThreshold: 50, // ms (FR-003)
    desyncThreshold: 100, // ms (SC-004)
    targetFps: 60,
    storageKeys: {
        layout: 'phi_matrix_layout',
        theme: 'phi_matrix_theme'
    }
};

// ============================================================================
// STATE MANAGEMENT
// ============================================================================

const state = {
    // Connection
    websocket: null,
    connected: false,
    reconnecting: false,

    // Synchronized state from server
    masterTime: 0,
    isPaused: false,

    // Metrics
    ici: 0.5,
    coherence: 0.5,
    criticality: 1.0,
    phiPhase: 0,
    phiDepth: 1.0,
    phiBreathing: 0.5,

    // Chromatic state
    channels: [],
    coherenceLinks: [],

    // Visualization
    visualizerMode: 'spectral', // 'spectral', 'breathing', 'topology'
    canvas: null,
    ctx: null,

    // Performance tracking
    frameCount: 0,
    lastFpsUpdate: Date.now(),
    currentFps: 0,
    latencies: [],
    lastSyncTime: Date.now(),
    desyncEvents: [],

    // Session state
    isRecording: false,
    isPlaying: false,
    clusterNodesCount: 0,

    // Layout
    layout: null
};

// ============================================================================
// WEBSOCKET CONNECTION
// ============================================================================

function connectWebSocket() {
    try {
        console.log('[Dashboard] Connecting to WebSocket:', CONFIG.websocketUrl);
        state.websocket = new WebSocket(CONFIG.websocketUrl);

        state.websocket.onopen = handleWebSocketOpen;
        state.websocket.onmessage = handleWebSocketMessage;
        state.websocket.onclose = handleWebSocketClose;
        state.websocket.onerror = handleWebSocketError;

    } catch (error) {
        console.error('[Dashboard] WebSocket connection error:', error);
        scheduleReconnect();
    }
}

function handleWebSocketOpen(event) {
    console.log('[Dashboard] WebSocket connected');
    state.connected = true;
    state.reconnecting = false;

    updateConnectionStatus();

    // Request initial state
    sendWebSocketMessage({
        type: 'get_state',
        client_time: Date.now()
    });
}

function handleWebSocketMessage(event) {
    const receiveTime = Date.now();

    try {
        const message = JSON.parse(event.data);
        const messageType = message.type;

        // Track latency (FR-003)
        if (message.server_time) {
            const latency = receiveTime - message.server_time;
            state.latencies.push(latency);
            if (state.latencies.length > 100) {
                state.latencies.shift();
            }
        }

        // Handle message types
        switch (messageType) {
            case 'state_sync':
                handleStateSync(message.data);
                break;

            case 'pong':
                handlePong(message);
                break;

            case 'pause_ack':
                state.isPaused = true;
                state.masterTime = message.master_time;
                updateMasterTimeDisplay();
                break;

            case 'resume_ack':
                state.isPaused = false;
                state.masterTime = message.master_time;
                updateMasterTimeDisplay();
                break;

            case 'state_response':
                handleStateSync(message.data);
                break;

            case 'error':
                console.error('[Dashboard] Server error:', message.message);
                break;

            default:
                console.warn('[Dashboard] Unknown message type:', messageType);
        }

    } catch (error) {
        console.error('[Dashboard] Error handling WebSocket message:', error);
    }
}

function handleWebSocketClose(event) {
    console.log('[Dashboard] WebSocket disconnected');
    state.connected = false;
    updateConnectionStatus();
    scheduleReconnect();
}

function handleWebSocketError(error) {
    console.error('[Dashboard] WebSocket error:', error);
}

function scheduleReconnect() {
    if (state.reconnecting) return;

    state.reconnecting = true;
    console.log(`[Dashboard] Reconnecting in ${CONFIG.reconnectDelay}ms...`);

    setTimeout(() => {
        connectWebSocket();
    }, CONFIG.reconnectDelay);
}

function sendWebSocketMessage(message) {
    if (state.websocket && state.websocket.readyState === WebSocket.OPEN) {
        state.websocket.send(JSON.stringify(message));
    } else {
        console.warn('[Dashboard] Cannot send message - WebSocket not connected');
    }
}

// ============================================================================
// STATE SYNCHRONIZATION
// ============================================================================

function handleStateSync(data) {
    if (!data) return;

    const syncTime = Date.now();

    // Update synchronized state
    state.masterTime = data.timestamp || 0;
    state.ici = data.ici || 0.5;
    state.coherence = data.coherence || 0.5;
    state.criticality = data.criticality || 1.0;
    state.phiPhase = data.phi_phase || 0;
    state.phiDepth = data.phi_depth || 1.0;
    state.phiBreathing = data.phi_breathing || 0.5;
    state.isRecording = data.is_recording || false;
    state.isPlaying = data.is_playing || false;
    state.clusterNodesCount = data.cluster_nodes_count || 0;

    // Check for desync (SC-004)
    const timeSinceLastSync = syncTime - state.lastSyncTime;
    if (timeSinceLastSync > CONFIG.desyncThreshold) {
        state.desyncEvents.push({
            timestamp: syncTime,
            desync_ms: timeSinceLastSync
        });

        // Keep only recent events (last 60 seconds)
        state.desyncEvents = state.desyncEvents.filter(
            e => (syncTime - e.timestamp) < 60000
        );
    }

    state.lastSyncTime = syncTime;

    // Update displays
    updateMetricsDisplay();
    updateMasterTimeDisplay();
    updateControlsFromState();
}

// ============================================================================
// CHROMATIC VISUALIZER
// ============================================================================

function frequencyToHue(frequency) {
    const freq = Math.max(MIN_FREQUENCY, Math.min(MAX_FREQUENCY, frequency));
    const logFreq = Math.log10(freq);
    const logMin = Math.log10(MIN_FREQUENCY);
    const logMax = Math.log10(MAX_FREQUENCY);
    const normalized = (logFreq - logMin) / (logMax - logMin);
    return normalized * 360;
}

function amplitudeToLightness(amplitude) {
    const amp = Math.max(0, Math.min(1, amplitude));
    return Math.pow(amp, 1.0 / AMPLITUDE_GAMMA);
}

function applyPhiRotation(baseHue, phiPhase) {
    const rotation = (phiPhase / (2 * Math.PI)) * GOLDEN_ANGLE;
    return (baseHue + rotation) % 360;
}

function hslToRgb(h, s, l) {
    const c = (1 - Math.abs(2 * l - 1)) * s;
    const x = c * (1 - Math.abs((h / 60) % 2 - 1));
    const m = l - c / 2;

    let r, g, b;

    if (h < 60) {
        [r, g, b] = [c, x, 0];
    } else if (h < 120) {
        [r, g, b] = [x, c, 0];
    } else if (h < 180) {
        [r, g, b] = [0, c, x];
    } else if (h < 240) {
        [r, g, b] = [0, x, c];
    } else if (h < 300) {
        [r, g, b] = [x, 0, c];
    } else {
        [r, g, b] = [c, 0, x];
    }

    return {
        r: Math.round((r + m) * 255),
        g: Math.round((g + m) * 255),
        b: Math.round((b + m) * 255)
    };
}

function updateChromaticState(channelFrequencies, channelAmplitudes) {
    state.channels = [];

    for (let i = 0; i < Math.min(8, channelFrequencies.length); i++) {
        const freq = channelFrequencies[i];
        const amp = channelAmplitudes[i];

        const baseHue = frequencyToHue(freq);
        const hue = applyPhiRotation(baseHue, state.phiPhase);
        let lightness = amplitudeToLightness(amp);

        // Apply Phi breathing modulation
        lightness = lightness * (0.5 + 0.5 * state.phiBreathing);

        const rgb = hslToRgb(hue, 1.0, lightness);

        state.channels.push({
            index: i,
            frequency: freq,
            amplitude: amp,
            hue: hue,
            lightness: lightness,
            r: rgb.r,
            g: rgb.g,
            b: rgb.b
        });
    }
}

function renderVisualizerSpectral() {
    const canvas = state.canvas;
    const ctx = state.ctx;

    if (!canvas || !ctx) return;

    // Clear canvas
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // 4x2 grid layout
    const cols = 4;
    const rows = 2;
    const cellWidth = canvas.width / cols;
    const cellHeight = canvas.height / rows;
    const padding = 4;

    for (let i = 0; i < state.channels.length; i++) {
        const ch = state.channels[i];
        const col = i % cols;
        const row = Math.floor(i / cols);

        const x = col * cellWidth + padding;
        const y = row * cellHeight + padding;
        const w = cellWidth - 2 * padding;
        const h = cellHeight - 2 * padding;

        // Fill with channel color
        ctx.fillStyle = `rgb(${ch.r}, ${ch.g}, ${ch.b})`;
        ctx.fillRect(x, y, w, h);

        // Draw channel label
        ctx.fillStyle = '#ffffff';
        ctx.font = '14px monospace';
        ctx.textAlign = 'left';
        ctx.textBaseline = 'top';
        ctx.fillText(`CH${i}`, x + 8, y + 8);

        // Draw frequency
        ctx.font = '12px monospace';
        ctx.fillText(`${Math.round(ch.frequency)} Hz`, x + 8, y + 28);
    }
}

function renderVisualizerBreathing() {
    const canvas = state.canvas;
    const ctx = state.ctx;

    if (!canvas || !ctx) return;

    // Clear canvas
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const maxRadius = Math.min(centerX, centerY) * 0.9;

    // Create radial gradient with Phi breathing
    const breathingRadius = maxRadius * (0.5 + 0.5 * state.phiBreathing);

    for (let i = state.channels.length - 1; i >= 0; i--) {
        const ch = state.channels[i];
        const radius = breathingRadius * ((i + 1) / state.channels.length);

        const gradient = ctx.createRadialGradient(
            centerX, centerY, 0,
            centerX, centerY, radius
        );

        gradient.addColorStop(0, `rgba(${ch.r}, ${ch.g}, ${ch.b}, ${ch.lightness})`);
        gradient.addColorStop(1, `rgba(${ch.r}, ${ch.g}, ${ch.b}, 0)`);

        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
        ctx.fill();
    }

    // Draw center Phi symbol
    ctx.fillStyle = '#ffffff';
    ctx.font = '32px monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('Phi', centerX, centerY);
}

function renderVisualizerTopology() {
    const canvas = state.canvas;
    const ctx = state.ctx;

    if (!canvas || !ctx) return;

    // Clear canvas
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const radius = Math.min(centerX, centerY) * 0.7;

    // Calculate node positions in circle
    const nodePositions = [];
    for (let i = 0; i < state.channels.length; i++) {
        const angle = (i / state.channels.length) * 2 * Math.PI - Math.PI / 2;
        nodePositions.push({
            x: centerX + radius * Math.cos(angle),
            y: centerY + radius * Math.sin(angle)
        });
    }

    // Draw coherence links (if available)
    if (state.coherenceLinks && state.coherenceLinks.length > 0) {
        for (const link of state.coherenceLinks) {
            const fromPos = nodePositions[link.from];
            const toPos = nodePositions[link.to];

            if (fromPos && toPos) {
                const alpha = link.strength * 0.8;
                ctx.strokeStyle = `rgba(0, 255, 200, ${alpha})`;
                ctx.lineWidth = link.width * 3;
                ctx.beginPath();
                ctx.moveTo(fromPos.x, fromPos.y);
                ctx.lineTo(toPos.x, toPos.y);
                ctx.stroke();
            }
        }
    }

    // Draw nodes
    for (let i = 0; i < state.channels.length; i++) {
        const ch = state.channels[i];
        const pos = nodePositions[i];

        // Node circle
        const nodeRadius = 30;
        ctx.fillStyle = `rgb(${ch.r}, ${ch.g}, ${ch.b})`;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, nodeRadius, 0, 2 * Math.PI);
        ctx.fill();

        // Node outline
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.stroke();

        // Node label
        ctx.fillStyle = '#ffffff';
        ctx.font = '14px monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(`${i}`, pos.x, pos.y);
    }
}

function renderVisualizer() {
    // Update frame count for FPS tracking
    state.frameCount++;

    const now = Date.now();
    const elapsed = now - state.lastFpsUpdate;

    if (elapsed >= 1000) {
        state.currentFps = Math.round((state.frameCount / elapsed) * 1000);
        state.frameCount = 0;
        state.lastFpsUpdate = now;
        updatePerformanceDisplay();
    }

    // Render based on mode
    switch (state.visualizerMode) {
        case 'spectral':
            renderVisualizerSpectral();
            break;
        case 'breathing':
            renderVisualizerBreathing();
            break;
        case 'topology':
            renderVisualizerTopology();
            break;
    }
}

// ============================================================================
// CONTROL HANDLERS
// ============================================================================

function handlePhiDepthChange(value) {
    state.phiDepth = parseFloat(value);
    document.getElementById('phi-depth-value').textContent = value;

    // Send update to server (SC-003: <= 50ms interaction delay)
    const sendTime = Date.now();
    sendWebSocketMessage({
        type: 'control_update',
        control: 'phi_depth',
        value: state.phiDepth,
        client_time: sendTime
    });
}

function handlePhiPhaseChange(value) {
    state.phiPhase = parseFloat(value);
    document.getElementById('phi-phase-value').textContent = value;

    const sendTime = Date.now();
    sendWebSocketMessage({
        type: 'control_update',
        control: 'phi_phase',
        value: state.phiPhase,
        client_time: sendTime
    });
}

function handlePauseResume() {
    if (state.isPaused) {
        sendWebSocketMessage({ type: 'resume', client_time: Date.now() });
    } else {
        sendWebSocketMessage({ type: 'pause', client_time: Date.now() });
    }
}

function handleRecordToggle() {
    const newState = !state.isRecording;
    sendWebSocketMessage({
        type: 'control_update',
        control: 'recording',
        value: newState,
        client_time: Date.now()
    });
}

function handlePresetLoad(presetName) {
    sendWebSocketMessage({
        type: 'load_preset',
        preset: presetName,
        client_time: Date.now()
    });
}

function handleChannelMuteToggle(channelIndex) {
    sendWebSocketMessage({
        type: 'control_update',
        control: 'channel_mute',
        channel: channelIndex,
        client_time: Date.now()
    });
}

function handleChannelAmplitudeChange(channelIndex, value) {
    sendWebSocketMessage({
        type: 'control_update',
        control: 'channel_amplitude',
        channel: channelIndex,
        value: parseFloat(value),
        client_time: Date.now()
    });
}

function handleVisualizerModeChange(mode) {
    state.visualizerMode = mode;

    // Update tab active state
    document.querySelectorAll('.viz-tab').forEach(tab => {
        tab.classList.remove('active');
        if (tab.dataset.mode === mode) {
            tab.classList.add('active');
        }
    });

    // Save to localStorage
    saveLayout();
}

// ============================================================================
// UI UPDATES
// ============================================================================

function updateConnectionStatus() {
    const statusEl = document.getElementById('connection-status');
    if (state.connected) {
        statusEl.textContent = 'CONNECTED';
        statusEl.style.color = '#00ff00';
    } else {
        statusEl.textContent = 'DISCONNECTED';
        statusEl.style.color = '#ff0000';
    }
}

function updateMasterTimeDisplay() {
    const timeEl = document.getElementById('master-time');
    if (timeEl) {
        timeEl.textContent = state.masterTime.toFixed(3) + 's';
    }

    const pauseBtn = document.getElementById('pause-btn');
    if (pauseBtn) {
        pauseBtn.textContent = state.isPaused ? 'RESUME' : 'PAUSE';
    }
}

function updateMetricsDisplay() {
    const metricsEl = document.getElementById('metrics-display');
    if (!metricsEl) return;

    metricsEl.innerHTML = `
        <div class="metric-row">
            <span class="metric-label">ICI:</span>
            <span class="metric-value">${state.ici.toFixed(3)}</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Coherence:</span>
            <span class="metric-value">${state.coherence.toFixed(3)}</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Criticality:</span>
            <span class="metric-value">${state.criticality.toFixed(3)}</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Phi Phase:</span>
            <span class="metric-value">${state.phiPhase.toFixed(3)} rad</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Phi Depth:</span>
            <span class="metric-value">${state.phiDepth.toFixed(3)}</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Phi Breathing:</span>
            <span class="metric-value">${state.phiBreathing.toFixed(3)}</span>
        </div>
    `;
}

function updatePerformanceDisplay() {
    const perfEl = document.getElementById('performance-display');
    if (!perfEl) return;

    // Calculate average latency
    const avgLatency = state.latencies.length > 0
        ? state.latencies.reduce((a, b) => a + b, 0) / state.latencies.length
        : 0;

    const maxLatency = state.latencies.length > 0
        ? Math.max(...state.latencies)
        : 0;

    // Check success criteria
    const meetsSC001 = maxLatency <= 100; // SC-001: <= 100ms latency
    const meetsSC002 = state.currentFps >= 30; // SC-002: >= 30fps
    const meetsFR003 = avgLatency <= 50; // FR-003: < 50ms average

    const recentDesyncs = state.desyncEvents.filter(
        e => (Date.now() - e.timestamp) < 60000
    ).length;

    perfEl.innerHTML = `
        <div class="metric-row">
            <span class="metric-label">FPS:</span>
            <span class="metric-value" style="color: ${meetsSC002 ? '#00ff00' : '#ff6b6b'}">${state.currentFps}</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Avg Latency:</span>
            <span class="metric-value" style="color: ${meetsFR003 ? '#00ff00' : '#ff6b6b'}">${avgLatency.toFixed(1)} ms</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Max Latency:</span>
            <span class="metric-value" style="color: ${meetsSC001 ? '#00ff00' : '#ff6b6b'}">${maxLatency.toFixed(1)} ms</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Desyncs (60s):</span>
            <span class="metric-value">${recentDesyncs}</span>
        </div>
    `;

    // Update FPS counter in header
    const fpsEl = document.getElementById('fps-counter');
    if (fpsEl) {
        fpsEl.textContent = `${state.currentFps} FPS`;
        fpsEl.style.color = meetsSC002 ? '#00ff00' : '#ff6b6b';
    }

    // Update sync indicator
    updateSyncIndicator(avgLatency, recentDesyncs);
}

function updateSyncIndicator(latency, desyncs) {
    const indicatorEl = document.getElementById('sync-indicator');
    if (!indicatorEl) return;

    const synced = latency <= 50 && desyncs === 0;

    indicatorEl.innerHTML = `
        <div style="color: ${synced ? '#00ff00' : '#ff6b6b'}">
            ${synced ? 'SYNCED' : 'DEGRADED'}
        </div>
        <div style="font-size: 11px; opacity: 0.7;">
            ${latency.toFixed(1)}ms
        </div>
    `;
}

function updateControlsFromState() {
    // Update sliders to match server state
    const phiDepthSlider = document.getElementById('phi-depth');
    if (phiDepthSlider && Math.abs(parseFloat(phiDepthSlider.value) - state.phiDepth) > 0.001) {
        phiDepthSlider.value = state.phiDepth;
        document.getElementById('phi-depth-value').textContent = state.phiDepth.toFixed(3);
    }

    const phiPhaseSlider = document.getElementById('phi-phase');
    if (phiPhaseSlider && Math.abs(parseFloat(phiPhaseSlider.value) - state.phiPhase) > 0.01) {
        phiPhaseSlider.value = state.phiPhase;
        document.getElementById('phi-phase-value').textContent = state.phiPhase.toFixed(2);
    }

    // Update recording button
    const recordBtn = document.getElementById('record-btn');
    if (recordBtn) {
        recordBtn.textContent = state.isRecording ? 'STOP REC' : 'START REC';
        recordBtn.style.background = state.isRecording ? '#ff4444' : '#4a5568';
    }
}

// ============================================================================
// LOCALSTORAGE PERSISTENCE (FR-004, SC-005)
// ============================================================================

function saveLayout() {
    const layout = {
        visualizerMode: state.visualizerMode,
        timestamp: Date.now()
    };

    try {
        localStorage.setItem(CONFIG.storageKeys.layout, JSON.stringify(layout));
        console.log('[Dashboard] Layout saved to localStorage');
    } catch (error) {
        console.error('[Dashboard] Error saving layout:', error);
    }
}

function loadLayout() {
    try {
        const layoutJson = localStorage.getItem(CONFIG.storageKeys.layout);
        if (layoutJson) {
            const layout = JSON.parse(layoutJson);
            state.layout = layout;

            // Restore visualizer mode
            if (layout.visualizerMode) {
                handleVisualizerModeChange(layout.visualizerMode);
            }

            console.log('[Dashboard] Layout loaded from localStorage');
            return true;
        }
    } catch (error) {
        console.error('[Dashboard] Error loading layout:', error);
    }

    return false;
}

function saveTheme(themeName) {
    try {
        localStorage.setItem(CONFIG.storageKeys.theme, themeName);
        console.log('[Dashboard] Theme saved:', themeName);
    } catch (error) {
        console.error('[Dashboard] Error saving theme:', error);
    }
}

function loadTheme() {
    try {
        const theme = localStorage.getItem(CONFIG.storageKeys.theme);
        if (theme) {
            // Apply theme (extend as needed)
            console.log('[Dashboard] Theme loaded:', theme);
            return theme;
        }
    } catch (error) {
        console.error('[Dashboard] Error loading theme:', error);
    }

    return 'default';
}

// ============================================================================
// CHANNEL CONTROLS GENERATION
// ============================================================================

function generateChannelControls() {
    const container = document.getElementById('channel-controls');
    if (!container) return;

    container.innerHTML = '';

    for (let i = 0; i < 8; i++) {
        const channelDiv = document.createElement('div');
        channelDiv.className = 'channel-control';
        channelDiv.innerHTML = `
            <div class="channel-header">
                <span>CH${i}</span>
                <button class="channel-mute-btn" data-channel="${i}">M</button>
            </div>
            <input type="range"
                   class="channel-amplitude"
                   data-channel="${i}"
                   min="0"
                   max="1"
                   step="0.01"
                   value="1.0">
        `;

        container.appendChild(channelDiv);
    }

    // Add event listeners
    container.querySelectorAll('.channel-mute-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const channel = parseInt(e.target.dataset.channel);
            handleChannelMuteToggle(channel);
            e.target.classList.toggle('active');
        });
    });

    container.querySelectorAll('.channel-amplitude').forEach(slider => {
        slider.addEventListener('input', (e) => {
            const channel = parseInt(e.target.dataset.channel);
            handleChannelAmplitudeChange(channel, e.target.value);
        });
    });
}

// ============================================================================
// ANIMATION LOOP
// ============================================================================

function animate() {
    // Render visualizer
    renderVisualizer();

    // Continue animation loop
    requestAnimationFrame(animate);
}

// ============================================================================
// INITIALIZATION
// ============================================================================

function initialize() {
    console.log('[Dashboard] Initializing Phi-Matrix Dashboard...');

    // Hide loading overlay
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
        setTimeout(() => {
            loadingOverlay.style.display = 'none';
        }, 1000);
    }

    // Get canvas
    state.canvas = document.getElementById('visualizer-canvas');
    if (state.canvas) {
        state.ctx = state.canvas.getContext('2d');

        // Set canvas size
        const resizeCanvas = () => {
            const container = state.canvas.parentElement;
            state.canvas.width = container.clientWidth;
            state.canvas.height = container.clientHeight;
        };

        resizeCanvas();
        window.addEventListener('resize', resizeCanvas);
    }

    // Load layout and theme from localStorage (FR-004)
    loadLayout();
    loadTheme();

    // Generate channel controls
    generateChannelControls();

    // Setup event listeners
    const phiDepthSlider = document.getElementById('phi-depth');
    if (phiDepthSlider) {
        phiDepthSlider.addEventListener('input', (e) => handlePhiDepthChange(e.target.value));
    }

    const phiPhaseSlider = document.getElementById('phi-phase');
    if (phiPhaseSlider) {
        phiPhaseSlider.addEventListener('input', (e) => handlePhiPhaseChange(e.target.value));
    }

    const pauseBtn = document.getElementById('pause-btn');
    if (pauseBtn) {
        pauseBtn.addEventListener('click', handlePauseResume);
    }

    const recordBtn = document.getElementById('record-btn');
    if (recordBtn) {
        recordBtn.addEventListener('click', handleRecordToggle);
    }

    // Visualizer mode tabs
    document.querySelectorAll('.viz-tab').forEach(tab => {
        tab.addEventListener('click', (e) => {
            const mode = e.target.dataset.mode;
            handleVisualizerModeChange(mode);
        });
    });

    // Preset buttons
    document.querySelectorAll('.preset-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const preset = e.target.dataset.preset;
            handlePresetLoad(preset);
        });
    });

    // Connect WebSocket
    connectWebSocket();

    // Start animation loop
    animate();

    // Mock data for testing without server connection
    // (Remove this in production)
    if (!state.connected) {
        startMockDataGenerator();
    }

    console.log('[Dashboard] Initialization complete');
}

// ============================================================================
// MOCK DATA GENERATOR (for testing without server)
// ============================================================================

function startMockDataGenerator() {
    console.log('[Dashboard] Starting mock data generator...');

    setInterval(() => {
        // Generate mock chromatic state
        const mockFrequencies = [100, 200, 300, 400, 500, 600, 700, 800];
        const mockAmplitudes = Array.from({length: 8}, (_, i) =>
            0.5 + 0.3 * Math.sin(Date.now() / 1000 + i)
        );

        // Update state
        state.phiBreathing = 0.5 + 0.5 * Math.sin(Date.now() / 1000 * PHI_BREATHING_FREQUENCY * 2 * Math.PI);
        state.ici = 0.5 + 0.1 * Math.sin(Date.now() / 2000);
        state.coherence = 0.8 + 0.1 * Math.cos(Date.now() / 3000);
        state.criticality = 1.0 + 0.2 * Math.sin(Date.now() / 4000);
        state.masterTime = (Date.now() - state.lastFpsUpdate) / 1000;

        updateChromaticState(mockFrequencies, mockAmplitudes);
        updateMetricsDisplay();
        updateMasterTimeDisplay();

    }, 33); // ~30 Hz
}

// ============================================================================
// START
// ============================================================================

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize);
} else {
    initialize();
}
