/**
 * Feature 007: Control Matrix Panel - Unified 8×8 Interactive Matrix
 *
 * Provides:
 * - 8×8 grid controlling channel parameters
 * - Real-time amplitude, frequency, and coupling adjustments
 * - Click/drag interaction
 * - Color-coded by channel (chromatic identity)
 * - Visual feedback with <50ms latency
 */

export class ControlMatrixPanel {
  constructor(containerId, onParameterChange) {
    this.container = document.getElementById(containerId);
    if (!this.container) {
      throw new Error(`Container ${containerId} not found`);
    }

    this.onParameterChange = onParameterChange || (() => {});

    // Configuration
    this.numChannels = 8;
    this.cellSize = 60;
    this.gap = 2;

    // Channel colors (matching visualizer)
    this.channelColors = [
      'hsl(0, 100%, 50%)',
      'hsl(30, 100%, 50%)',
      'hsl(60, 100%, 50%)',
      'hsl(120, 100%, 50%)',
      'hsl(180, 100%, 50%)',
      'hsl(240, 100%, 50%)',
      'hsl(280, 100%, 50%)',
      'hsl(320, 100%, 50%)'
    ];

    // State
    this.amplitudes = [0.6, 0.55, 0.5, 0.45, 0.4, 0.35, 0.3, 0.25];
    this.frequencies = [0.5, 0.81, 1.31, 2.12, 3.43, 5.55, 8.97, 14.52];
    this.couplingStrength = 1.0;
    this.selectedCell = null;

    // Interaction state
    this.isDragging = false;
    this.dragStartValue = 0;
    this.dragStartY = 0;

    this.build();
    this.attachEventListeners();

    console.log('[ControlMatrixPanel] Initialized with', this.numChannels, '×', this.numChannels, 'matrix');
  }

  /**
   * Build the HTML structure
   */
  build() {
    this.container.innerHTML = '';
    this.container.style.cssText = `
      display: inline-block;
      padding: 15px;
      background: rgba(0, 0, 0, 0.8);
      border: 2px solid var(--color-primary, #0f0);
      border-radius: 8px;
      user-select: none;
    `;

    // Title
    const title = document.createElement('div');
    title.textContent = 'CONTROL MATRIX (8×8)';
    title.style.cssText = `
      font-weight: bold;
      color: #0f0;
      margin-bottom: 10px;
      text-align: center;
      font-size: 14px;
      letter-spacing: 2px;
    `;
    this.container.appendChild(title);

    // Matrix container
    const matrixContainer = document.createElement('div');
    matrixContainer.id = 'controlMatrixGrid';
    matrixContainer.style.cssText = `
      display: grid;
      grid-template-columns: repeat(${this.numChannels}, ${this.cellSize}px);
      grid-gap: ${this.gap}px;
      margin-bottom: 10px;
    `;
    this.container.appendChild(matrixContainer);

    // Create cells
    for (let row = 0; row < this.numChannels; row++) {
      for (let col = 0; col < this.numChannels; col++) {
        const cell = this.createCell(row, col);
        matrixContainer.appendChild(cell);
      }
    }

    // Control panel
    const controlPanel = document.createElement('div');
    controlPanel.style.cssText = `
      margin-top: 10px;
      padding: 10px;
      background: rgba(0, 255, 0, 0.05);
      border-radius: 4px;
    `;

    // Coupling strength control
    const couplingLabel = document.createElement('div');
    couplingLabel.textContent = `Coupling Strength: ${this.couplingStrength.toFixed(2)}`;
    couplingLabel.id = 'couplingLabel';
    couplingLabel.style.cssText = `
      color: #0f0;
      font-size: 12px;
      margin-bottom: 5px;
      font-family: monospace;
    `;
    controlPanel.appendChild(couplingLabel);

    const couplingSlider = document.createElement('input');
    couplingSlider.type = 'range';
    couplingSlider.min = '0';
    couplingSlider.max = '2';
    couplingSlider.step = '0.01';
    couplingSlider.value = this.couplingStrength;
    couplingSlider.id = 'couplingSlider';
    couplingSlider.style.cssText = 'width: 100%;';
    couplingSlider.addEventListener('input', (e) => {
      this.couplingStrength = parseFloat(e.target.value);
      couplingLabel.textContent = `Coupling Strength: ${this.couplingStrength.toFixed(2)}`;
      this.onParameterChange('coupling_strength', this.couplingStrength);
    });
    controlPanel.appendChild(couplingSlider);

    this.container.appendChild(controlPanel);

    // Info panel
    const infoPanel = document.createElement('div');
    infoPanel.id = 'matrixInfoPanel';
    infoPanel.style.cssText = `
      margin-top: 10px;
      padding: 8px;
      background: rgba(0, 0, 0, 0.5);
      border: 1px solid #333;
      border-radius: 4px;
      font-family: monospace;
      font-size: 11px;
      color: #888;
      min-height: 40px;
    `;
    infoPanel.textContent = 'Click cells to adjust amplitude • Drag vertically to modify • Columns control frequency';
    this.container.appendChild(infoPanel);
  }

  /**
   * Create a single matrix cell
   * @param {number} row - Row index (amplitude control)
   * @param {number} col - Column index (frequency/channel)
   * @returns {HTMLElement} Cell element
   */
  createCell(row, col) {
    const cell = document.createElement('div');
    cell.className = 'matrix-cell';
    cell.dataset.row = row;
    cell.dataset.col = col;

    const channelIndex = col;
    const intensity = this.amplitudes[channelIndex] || 0.5;
    const isActive = row < Math.floor(intensity * this.numChannels);

    cell.style.cssText = `
      width: ${this.cellSize}px;
      height: ${this.cellSize}px;
      background: ${isActive ? this.channelColors[channelIndex] : 'rgba(0, 255, 0, 0.1)'};
      border: 1px solid ${isActive ? this.channelColors[channelIndex] : 'rgba(0, 255, 0, 0.2)'};
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.1s;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 10px;
      color: ${isActive ? '#000' : '#666'};
      font-weight: bold;
    `;

    // Label (show frequency on top row)
    if (row === 0) {
      const freq = this.frequencies[channelIndex];
      cell.textContent = freq ? freq.toFixed(2) : '';
    }

    // Hover effect
    cell.addEventListener('mouseenter', () => {
      if (!this.isDragging) {
        cell.style.transform = 'scale(1.1)';
        cell.style.boxShadow = `0 0 10px ${this.channelColors[channelIndex]}`;
        this.showCellInfo(row, col);
      }
    });

    cell.addEventListener('mouseleave', () => {
      if (!this.isDragging) {
        cell.style.transform = 'scale(1)';
        cell.style.boxShadow = 'none';
      }
    });

    return cell;
  }

  /**
   * Attach event listeners for interaction
   */
  attachEventListeners() {
    const matrixGrid = document.getElementById('controlMatrixGrid');
    if (!matrixGrid) return;

    matrixGrid.addEventListener('mousedown', (e) => {
      if (e.target.classList.contains('matrix-cell')) {
        this.handleCellMouseDown(e);
      }
    });

    document.addEventListener('mousemove', (e) => {
      if (this.isDragging) {
        this.handleDrag(e);
      }
    });

    document.addEventListener('mouseup', () => {
      if (this.isDragging) {
        this.handleDragEnd();
      }
    });
  }

  /**
   * Handle cell mouse down (start drag)
   * @param {MouseEvent} e - Mouse event
   */
  handleCellMouseDown(e) {
    const cell = e.target;
    const col = parseInt(cell.dataset.col);
    const row = parseInt(cell.dataset.row);

    this.isDragging = true;
    this.selectedCell = { row, col };
    this.dragStartValue = this.amplitudes[col];
    this.dragStartY = e.clientY;

    e.preventDefault();
  }

  /**
   * Handle drag (adjust amplitude)
   * @param {MouseEvent} e - Mouse event
   */
  handleDrag(e) {
    if (!this.isDragging || !this.selectedCell) return;

    const deltaY = this.dragStartY - e.clientY; // Inverted: up = increase
    const sensitivity = 0.005;
    const newValue = Math.max(0, Math.min(1, this.dragStartValue + deltaY * sensitivity));

    const col = this.selectedCell.col;
    this.amplitudes[col] = newValue;

    // Update visual
    this.updateColumn(col);

    // Notify change
    this.onParameterChange('amplitude', { channel: col, value: newValue });
  }

  /**
   * Handle drag end
   */
  handleDragEnd() {
    this.isDragging = false;
    this.selectedCell = null;
    this.dragStartValue = 0;
    this.dragStartY = 0;
  }

  /**
   * Update visual appearance of a column
   * @param {number} col - Column index
   */
  updateColumn(col) {
    const matrixGrid = document.getElementById('controlMatrixGrid');
    if (!matrixGrid) return;

    const intensity = this.amplitudes[col];
    const activeRows = Math.floor(intensity * this.numChannels);

    for (let row = 0; row < this.numChannels; row++) {
      const cellIndex = row * this.numChannels + col;
      const cell = matrixGrid.children[cellIndex];

      if (cell) {
        const isActive = (this.numChannels - row - 1) < activeRows; // Inverted rows

        cell.style.background = isActive ? this.channelColors[col] : 'rgba(0, 255, 0, 0.1)';
        cell.style.borderColor = isActive ? this.channelColors[col] : 'rgba(0, 255, 0, 0.2)';
        cell.style.color = isActive ? '#000' : '#666';
      }
    }
  }

  /**
   * Show info about a cell
   * @param {number} row - Row index
   * @param {number} col - Column index
   */
  showCellInfo(row, col) {
    const infoPanel = document.getElementById('matrixInfoPanel');
    if (!infoPanel) return;

    const channelIndex = col;
    const amp = this.amplitudes[channelIndex];
    const freq = this.frequencies[channelIndex];

    infoPanel.innerHTML = `
      <strong>Channel ${channelIndex + 1}</strong> |
      Frequency: <span style="color: ${this.channelColors[channelIndex]}">${freq.toFixed(2)} Hz</span> |
      Amplitude: <span style="color: ${this.channelColors[channelIndex]}">${(amp * 100).toFixed(1)}%</span> |
      Row: ${row} Col: ${col}
    `;
  }

  /**
   * Update parameters from external source
   * @param {object} params - Parameter object with frequencies, amplitudes, coupling
   */
  updateParameters(params) {
    if (params.frequencies) {
      this.frequencies = params.frequencies;
    }

    if (params.amplitudes) {
      this.amplitudes = params.amplitudes;

      // Update all columns
      for (let col = 0; col < this.numChannels; col++) {
        this.updateColumn(col);
      }
    }

    if (params.coupling_strength !== undefined) {
      this.couplingStrength = params.coupling_strength;

      const slider = document.getElementById('couplingSlider');
      const label = document.getElementById('couplingLabel');

      if (slider) slider.value = this.couplingStrength;
      if (label) label.textContent = `Coupling Strength: ${this.couplingStrength.toFixed(2)}`;
    }
  }

  /**
   * Get current parameters
   * @returns {object} Current parameter values
   */
  getParameters() {
    return {
      frequencies: [...this.frequencies],
      amplitudes: [...this.amplitudes],
      coupling_strength: this.couplingStrength
    };
  }

  /**
   * Reset to default values
   */
  reset() {
    this.amplitudes = [0.6, 0.55, 0.5, 0.45, 0.4, 0.35, 0.3, 0.25];
    this.frequencies = [0.5, 0.81, 1.31, 2.12, 3.43, 5.55, 8.97, 14.52];
    this.couplingStrength = 1.0;

    this.updateParameters({
      frequencies: this.frequencies,
      amplitudes: this.amplitudes,
      coupling_strength: this.couplingStrength
    });
  }
}

/**
 * Create and initialize Control Matrix Panel
 * @param {string} containerId - Container element ID
 * @param {function} onParameterChange - Callback for parameter changes
 * @returns {ControlMatrixPanel} Panel instance
 */
export function createControlMatrixPanel(containerId, onParameterChange) {
  return new ControlMatrixPanel(containerId, onParameterChange);
}
