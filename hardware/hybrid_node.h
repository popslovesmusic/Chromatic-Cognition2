/**
 * Hybrid Analog-DSP Node - Feature 024
 * Hardware bridge for analog front-end + digital signal processing
 *
 * Platform: Raspberry Pi 4/5, Teensy 4.x, or compatible ARM Cortex-A/M7
 * Dependencies: I²S/SPI ADC/DAC drivers, DSP library (CMSIS-DSP or KissFFT)
 *
 * Integrates:
 * - Analog signal acquisition via ADC (I²S or SPI)
 * - Real-time DSP: FFT, ICI, coherence analysis
 * - Analog modulation via DAC control voltage
 * - Safety monitoring: voltage clamp, thermal shutdown
 * - Calibration routines for gain/offset/latency
 *
 * Requirements:
 * - FR-001: ADC/DAC management with DMA streaming
 * - FR-002: Analog preamp + filter (120 Hz–8 kHz)
 * - FR-003: Real-time FFT, ICI, coherence calculations
 * - FR-004: Control loop for analog VCA modulation
 * - FR-007: Safety monitoring (voltage clamp, thermal)
 * - FR-008: Calibration routine (gain, offset, latency)
 *
 * Success Criteria:
 * - SC-001: ADC→DSP→DAC loop latency ≤2 ms
 * - SC-002: Analog modulation fidelity >95%
 * - SC-003: Stable operation 1 h, drift <0.5%
 */

#ifndef HYBRID_NODE_H
#define HYBRID_NODE_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

// Configuration constants
#define HYBRID_SAMPLE_RATE      48000       // Audio sample rate (Hz)
#define HYBRID_BUFFER_SIZE      512         // DMA buffer size in samples
#define HYBRID_FFT_SIZE         1024        // FFT analysis window
#define HYBRID_ADC_CHANNELS     2           // Stereo input
#define HYBRID_DAC_CHANNELS     4           // 2 audio + 2 control voltage

// Analog filter parameters (FR-002)
#define ANALOG_HPF_CUTOFF       120.0f      // High-pass cutoff (Hz)
#define ANALOG_LPF_CUTOFF       8000.0f     // Low-pass cutoff (Hz)
#define ANALOG_PREAMP_GAIN_MIN  1.0f        // Minimum gain (0 dB)
#define ANALOG_PREAMP_GAIN_MAX  40.0f       // Maximum gain (32 dB)

// Safety thresholds (FR-007)
#define SAFETY_VOLTAGE_MAX      5.0f        // Maximum DAC voltage
#define SAFETY_VOLTAGE_MIN      0.0f        // Minimum DAC voltage
#define SAFETY_TEMP_WARNING     70.0f       // Temperature warning (°C)
#define SAFETY_TEMP_CRITICAL    85.0f       // Temperature critical (°C)
#define SAFETY_OVERLOAD_THRESH  0.95f       // ADC overload threshold (95% of max)

// Calibration constants (FR-008)
#define CAL_TONE_FREQ           1000.0f     // Calibration tone (Hz)
#define CAL_SAMPLES             10          // Calibration sample count

// ADC/DAC interface type (FR-001)
typedef enum {
    HYBRID_INTERFACE_I2S = 0,     // I²S audio interface
    HYBRID_INTERFACE_SPI = 1,     // SPI ADC/DAC (e.g., MCP3208/MCP4822)
    HYBRID_INTERFACE_USB = 2      // USB audio class device
} HybridInterfaceType;

// Node operational mode
typedef enum {
    HYBRID_MODE_ANALOG_ONLY = 0,   // Analog passthrough (no DSP)
    HYBRID_MODE_DSP_ONLY = 1,      // Digital-only processing
    HYBRID_MODE_HYBRID = 2,        // Full analog+digital hybrid
    HYBRID_MODE_CALIBRATION = 3    // Calibration mode
} HybridNodeMode;

// Safety status (FR-007)
typedef enum {
    HYBRID_SAFETY_OK = 0,
    HYBRID_SAFETY_VOLTAGE_CLAMP = 1,
    HYBRID_SAFETY_TEMP_WARNING = 2,
    HYBRID_SAFETY_TEMP_CRITICAL = 3,
    HYBRID_SAFETY_ADC_OVERLOAD = 4,
    HYBRID_SAFETY_FAULT = 5
} HybridSafetyStatus;

// Configuration structure
typedef struct {
    // Interface configuration (FR-001)
    HybridInterfaceType interface_type;
    uint32_t sample_rate;
    uint16_t buffer_size;
    uint8_t adc_channels;
    uint8_t dac_channels;

    // Analog section (FR-002)
    float preamp_gain;              // Preamp gain (linear)
    float hpf_cutoff;               // High-pass filter cutoff (Hz)
    float lpf_cutoff;               // Low-pass filter cutoff (Hz)
    bool enable_analog_filter;      // Enable analog filtering

    // DSP configuration (FR-003)
    uint16_t fft_size;              // FFT analysis window
    bool enable_dsp;                // Enable DSP analysis
    bool enable_coherence;          // Enable coherence calculation
    bool enable_ici;                // Enable ICI calculation

    // Control loop (FR-004)
    bool enable_modulation;         // Enable analog modulation
    float modulation_depth;         // Modulation depth [0, 1]
    float control_loop_rate;        // Control update rate (Hz)

    // Safety configuration (FR-007)
    bool enable_voltage_clamp;      // Enable voltage limiting
    bool enable_thermal_monitor;    // Enable thermal monitoring
    float voltage_max;              // Maximum output voltage
    uint8_t thermal_gpio_pin;       // GPIO pin for thermal sensor

    // Operation mode
    HybridNodeMode mode;
    bool enable_logging;            // Enable diagnostic logging
} HybridNodeConfig;

// Analog signal metrics (FR-002)
typedef struct {
    float rms_level;                // RMS signal level
    float peak_level;               // Peak signal level
    float dc_offset;                // DC offset measurement
    float thd;                      // Total harmonic distortion (%)
    float snr_db;                   // Signal-to-noise ratio (dB)
    bool is_overloaded;             // ADC overload flag
} AnalogMetrics;

// DSP analysis results (FR-003)
typedef struct {
    float ici;                      // Inter-Criticality Interval (ms)
    float coherence;                // Phase coherence [0, 1]
    float criticality;              // Criticality metric
    float spectral_centroid;        // Spectral centroid (Hz)
    float spectral_flux;            // Spectral flux
    float zero_crossing_rate;       // Zero-crossing rate
    uint32_t timestamp_us;          // Microsecond timestamp
} DSPMetrics;

// Control voltage output (FR-004)
typedef struct {
    float cv1;                      // Control voltage 1 (0-5V) - VCA depth
    float cv2;                      // Control voltage 2 (0-5V) - VCA rate
    float phi_phase;                // Φ-phase modulation [0, 2π]
    float phi_depth;                // Φ-depth modulation [0, 1]
} ControlVoltage;

// Safety telemetry (FR-007)
typedef struct {
    HybridSafetyStatus status;      // Overall safety status
    float temperature;              // Temperature (°C)
    float voltage_out[HYBRID_DAC_CHANNELS]; // Output voltages
    uint32_t overload_count;        // ADC overload event count
    uint32_t clamp_count;           // Voltage clamp event count
    bool thermal_warning;           // Thermal warning flag
} SafetyTelemetry;

// Calibration data (FR-008)
typedef struct {
    // ADC calibration
    float adc_gain[HYBRID_ADC_CHANNELS];      // ADC gain correction
    float adc_offset[HYBRID_ADC_CHANNELS];    // ADC offset correction

    // DAC calibration
    float dac_gain[HYBRID_DAC_CHANNELS];      // DAC gain correction
    float dac_offset[HYBRID_DAC_CHANNELS];    // DAC offset correction

    // Latency calibration (SC-001)
    uint32_t adc_latency_us;        // ADC latency (µs)
    uint32_t dsp_latency_us;        // DSP processing latency (µs)
    uint32_t dac_latency_us;        // DAC latency (µs)
    uint32_t total_latency_us;      // Total loop latency (µs)

    // Calibration metadata
    uint32_t calibration_timestamp; // Unix timestamp of last calibration
    bool is_calibrated;             // Calibration valid flag
} CalibrationData;

// Node statistics (SC-003)
typedef struct {
    uint64_t frames_processed;      // Total frames processed
    uint64_t frames_dropped;        // Dropped frames
    float cpu_load;                 // CPU load (%)
    float buffer_utilization;       // DMA buffer utilization (%)
    uint32_t uptime_ms;             // Uptime (milliseconds)
    float drift_ppm;                // Clock drift (parts per million)
    float modulation_fidelity;      // Modulation fidelity (%) (SC-002)
} NodeStatistics;

// Comprehensive node status (FR-009)
typedef struct {
    HybridNodeMode mode;
    bool is_running;
    bool is_calibrated;
    AnalogMetrics analog;
    DSPMetrics dsp;
    ControlVoltage control;
    SafetyTelemetry safety;
    CalibrationData calibration;
    NodeStatistics stats;
} HybridNodeStatus;

// Function prototypes

/**
 * Initialize hybrid node (FR-001)
 *
 * @param config Configuration structure
 * @return true if initialization successful, false otherwise
 */
bool hybrid_node_init(const HybridNodeConfig *config);

/**
 * Start hybrid node processing (FR-001)
 *
 * Begins DMA streaming and processing loop.
 *
 * @return true if started successfully, false otherwise
 */
bool hybrid_node_start(void);

/**
 * Stop hybrid node processing
 *
 * @return true if stopped successfully, false otherwise
 */
bool hybrid_node_stop(void);

/**
 * Process audio buffer (called from DMA callback)
 *
 * Main processing loop: ADC→DSP→DAC
 *
 * @param input ADC input buffer
 * @param output DAC output buffer
 * @param frames Number of frames to process
 * @return true if processed successfully, false otherwise
 */
bool hybrid_node_process(const float *input, float *output, size_t frames);

/**
 * Set analog preamp gain (FR-002)
 *
 * @param gain Gain factor (linear, 1.0 = 0dB)
 * @return true if set successfully, false otherwise
 */
bool hybrid_node_set_preamp_gain(float gain);

/**
 * Set control voltage output (FR-004)
 *
 * @param cv Control voltage structure
 * @return true if set successfully, false otherwise
 */
bool hybrid_node_set_control_voltage(const ControlVoltage *cv);

/**
 * Get current node status (FR-009)
 *
 * @param status Pointer to status structure to fill
 * @return true if status retrieved, false otherwise
 */
bool hybrid_node_get_status(HybridNodeStatus *status);

/**
 * Get DSP metrics (FR-003)
 *
 * @param metrics Pointer to DSP metrics structure to fill
 * @return true if metrics retrieved, false otherwise
 */
bool hybrid_node_get_dsp_metrics(DSPMetrics *metrics);

/**
 * Get safety telemetry (FR-007)
 *
 * @param telemetry Pointer to safety telemetry structure to fill
 * @return true if telemetry retrieved, false otherwise
 */
bool hybrid_node_get_safety(SafetyTelemetry *telemetry);

/**
 * Run calibration routine (FR-008)
 *
 * Performs automatic calibration of ADC, DAC, and latency.
 * Node must be stopped before running calibration.
 *
 * @param calibration Pointer to calibration data structure to fill
 * @return true if calibration successful, false otherwise
 */
bool hybrid_node_calibrate(CalibrationData *calibration);

/**
 * Load calibration data (FR-008)
 *
 * @param calibration Calibration data to load
 * @return true if loaded successfully, false otherwise
 */
bool hybrid_node_load_calibration(const CalibrationData *calibration);

/**
 * Save calibration data to file (FR-008)
 *
 * @param filename Path to calibration file
 * @return true if saved successfully, false otherwise
 */
bool hybrid_node_save_calibration(const char *filename);

/**
 * Load calibration data from file (FR-008)
 *
 * @param filename Path to calibration file
 * @return true if loaded successfully, false otherwise
 */
bool hybrid_node_load_calibration_file(const char *filename);

/**
 * Reset node statistics
 *
 * @return true if reset successful, false otherwise
 */
bool hybrid_node_reset_statistics(void);

/**
 * Set operational mode
 *
 * @param mode Operational mode
 * @return true if set successfully, false otherwise
 */
bool hybrid_node_set_mode(HybridNodeMode mode);

/**
 * Emergency shutdown (FR-007)
 *
 * Immediately stops all processing and clamps outputs to safe levels.
 *
 * @param reason Reason for shutdown
 * @return true if shutdown successful, false otherwise
 */
bool hybrid_node_emergency_shutdown(const char *reason);

/**
 * Get firmware version
 *
 * @return Firmware version string
 */
const char* hybrid_node_get_version(void);

#ifdef __cplusplus
}
#endif

#endif // HYBRID_NODE_H
