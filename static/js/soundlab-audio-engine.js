export class SoundlabAudioEngine {
  constructor() {
    this.audioContext = null;
    this.inputGain = null;
    this.filterLow = null;
    this.filterMid = null;
    this.filterHigh = null;
    this.saturationNode = null;
    this.saturationGain = null;
    this.dryGain = null;
    this.wetGain = null;
    this.outputGain = null;
    this.compressor = null;
    this.isPlaying = false;
    this.parameters = {
      mix: 0.0
    };
  }

  async ensureContext() {
    if (this.audioContext) {
      return;
    }

    const ContextCtor = window.AudioContext || window.webkitAudioContext;
    if (!ContextCtor) {
      throw new Error('Web Audio API is not supported in this browser.');
    }

    this.audioContext = new ContextCtor();
    await this.audioContext.resume();

    this._initializeGraph();
  }

  _initializeGraph() {
    this.inputGain = this.audioContext.createGain();
    this.inputGain.gain.value = 1.0;

    this.filterLow = this.audioContext.createBiquadFilter();
    this.filterLow.type = 'lowshelf';
    this.filterLow.frequency.value = 120;

    this.filterMid = this.audioContext.createBiquadFilter();
    this.filterMid.type = 'peaking';
    this.filterMid.frequency.value = 1000;
    this.filterMid.Q.value = 1.25;

    this.filterHigh = this.audioContext.createBiquadFilter();
    this.filterHigh.type = 'highshelf';
    this.filterHigh.frequency.value = 6000;

    this.saturationNode = this.audioContext.createWaveShaper();
    this.saturationGain = this.audioContext.createGain();
    this.saturationGain.gain.value = 1.0;

    this.compressor = this.audioContext.createDynamicsCompressor();
    this.compressor.attack.value = 0.003;
    this.compressor.release.value = 0.25;

    this.outputGain = this.audioContext.createGain();
    this.outputGain.gain.value = 0.9;

    this.inputGain.connect(this.filterLow);
    this.filterLow.connect(this.filterMid);
    this.filterMid.connect(this.filterHigh);

    // Fix 1: true dry/wet crossfade bus
    this.dryGain = this.audioContext.createGain();
    this.wetGain = this.audioContext.createGain();
    this.dryGain.gain.value = 1.0;
    this.wetGain.gain.value = 0.0;

    this.filterHigh.connect(this.dryGain);
    this.filterHigh.connect(this.saturationNode);
    this.saturationNode.connect(this.saturationGain);
    this.saturationGain.connect(this.wetGain);

    const dryWetMerger = this.audioContext.createGain();
    this.dryGain.connect(dryWetMerger);
    this.wetGain.connect(dryWetMerger);
    dryWetMerger.connect(this.compressor);

    this.compressor.connect(this.outputGain);
    this.outputGain.connect(this.audioContext.destination);

    this.updateMix = value => {
      const now = this.audioContext.currentTime;
      const dry = 1.0 - value;
      const wet = value;
      this.dryGain.gain.setTargetAtTime(dry, now, 0.05);
      this.wetGain.gain.setTargetAtTime(wet, now, 0.05);
      this.parameters.mix = value;
    };
  }

  connectSource(node) {
    if (!this.inputGain) {
      throw new Error('Audio graph has not been initialized. Call ensureContext() first.');
    }
    node.connect(this.inputGain);
  }

  disconnectSource(node) {
    try {
      node.disconnect(this.inputGain);
    } catch (error) {
      console.warn('Attempted to disconnect an unknown source node.', error);
    }
  }

  async startAudio() {
    await this.ensureContext();

    window.soundlabTransport = window.soundlabTransport || {
      playing: false,
      phiMode: false,
      lastStop: null
    };
    window.soundlabTransport.playing = true;

    this.isPlaying = true;

    this.schedulePhiModulation().then(() => {
      window.soundlabTransport.playing = false;
      window.soundlabTransport.phiMode = false;
      this.isPlaying = false;
      const stopControl =
        document.querySelector('#stopButton') || document.querySelector('#stopBtn');
      if (stopControl) {
        stopControl.disabled = true;
      }
    });
    console.log('Audio started');
    const stopControl = document.querySelector('#stopButton') || document.querySelector('#stopBtn');
    if (stopControl) {
      stopControl.disabled = false;
    }
  }

  async stopAudio() {
    if (!this.audioContext) {
      return;
    }

    try {
      await this.audioContext.close();
    } finally {
      this.audioContext = null;
      this.inputGain = null;
      this.filterLow = null;
      this.filterMid = null;
      this.filterHigh = null;
      this.saturationNode = null;
      this.saturationGain = null;
      this.dryGain = null;
      this.wetGain = null;
      this.outputGain = null;
      this.compressor = null;
    }

    window.soundlabTransport = {
      playing: false,
      phiMode: false,
      lastStop: performance.now()
    };
    this.isPlaying = false;
    console.log('Audio stopped');

    const stopControl = document.querySelector('#stopButton') || document.querySelector('#stopBtn');
    if (stopControl) {
      stopControl.disabled = true;
    }
  }

  async schedulePhiModulation() {
    // Placeholder implementation. Real modulation sequencing should be provided
    // by higher-level Î¦ mode modules. Returning a resolved promise keeps the
    // lifecycle contract intact without blocking.
    return Promise.resolve();
  }
}

export default new SoundlabAudioEngine(); 
