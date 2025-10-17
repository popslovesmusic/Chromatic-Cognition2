/**
 * Φ-Sensor Hardware Interface - Feature 023 (FR-002)
 *
 * Analog sensor acquisition for Φ-matrix consciousness metrics
 * Reads analog signals from hardware Φ-sensors via ADC and normalizes to [0, 1]
 *
 * Requirements:
 * - FR-002: Φ-sensor ADC acquisition with normalization
 * - SC-002: 30 Hz sample rate (±2 Hz tolerance)
 * - SC-005: Calibration residual error < 2%
 *
 * Hardware:
 * - ADC input range: 0-3.3V
 * - Resolution: 12-bit (4096 levels)
 * - Channels: 4 (phi_depth, phi_phase, coherence, criticality)
 */

#ifndef PHI_SENSOR_H
#define PHI_SENSOR_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

// Configuration constants
#define PHI_SENSOR_CHANNELS     4
#define PHI_SENSOR_SAMPLE_RATE  30  // Hz (SC-002)
#define PHI_SENSOR_ADC_RESOLUTION 12 // bits
#define PHI_SENSOR_ADC_MAX      4095 // 2^12 - 1
#define PHI_SENSOR_VOLTAGE_MAX  3.3f // Volts

// ADC channel assignments
typedef enum {
    PHI_CHANNEL_DEPTH = 0,       // Φ-depth sensor
    PHI_CHANNEL_PHASE = 1,       // Φ-phase sensor
    PHI_CHANNEL_COHERENCE = 2,   // Phase coherence sensor
    PHI_CHANNEL_CRITICALITY = 3  // Criticality sensor
} PhiSensorChannel;

// Sensor configuration
typedef struct {
    uint8_t adc_pins[PHI_SENSOR_CHANNELS];  // ADC pin assignments
    uint32_t sample_rate_hz;                 // Target sample rate (Hz)
    bool enable_filtering;                   // Enable low-pass filtering
    float filter_cutoff_hz;                  // Low-pass filter cutoff (Hz)
    bool enable_calibration;                 // Use calibration offsets
} PhiSensorConfig;

// Calibration data (SC-005)
typedef struct {
    float offset[PHI_SENSOR_CHANNELS];       // Zero offsets [0, 1]
    float scale[PHI_SENSOR_CHANNELS];        // Scale factors [0, 1]
    float voltage_min[PHI_SENSOR_CHANNELS];  // Minimum voltage (V)
    float voltage_max[PHI_SENSOR_CHANNELS];  // Maximum voltage (V)
    uint32_t calibration_samples;            // Number of samples used
    float residual_error;                    // Residual error (%) (SC-005)
} PhiSensorCalibration;

// Raw sensor readings
typedef struct {
    uint16_t raw_adc[PHI_SENSOR_CHANNELS];   // Raw ADC values [0, 4095]
    float voltage[PHI_SENSOR_CHANNELS];      // Voltage values [0, 3.3V]
    float normalized[PHI_SENSOR_CHANNELS];   // Normalized values [0, 1]
    uint32_t timestamp_us;                   // Microsecond timestamp
    uint32_t sample_number;                  // Sequential sample number
} PhiSensorData;

// Sensor statistics
typedef struct {
    uint64_t total_samples;                  // Total samples acquired
    uint32_t sample_rate_actual;             // Measured sample rate (Hz)
    float sample_rate_jitter;                // Sample rate jitter (Hz)
    uint32_t dropped_samples;                // Dropped/missed samples
    float signal_quality[PHI_SENSOR_CHANNELS]; // Signal quality [0, 1]
    bool calibrated;                         // Calibration active
} PhiSensorStatistics;

// Function prototypes

/**
 * Initialize Φ-sensor ADC system (FR-002)
 *
 * @param config Sensor configuration
 * @return true if initialization successful, false otherwise
 */
bool phi_sensor_init(const PhiSensorConfig *config);

/**
 * Start sensor acquisition at configured sample rate (SC-002)
 *
 * @return true if started successfully, false otherwise
 */
bool phi_sensor_start(void);

/**
 * Stop sensor acquisition
 *
 * @return true if stopped successfully, false otherwise
 */
bool phi_sensor_stop(void);

/**
 * Read current sensor data
 *
 * Provides raw ADC, voltage, and normalized [0,1] values
 *
 * @param data Pointer to data structure to fill
 * @return true if data available, false otherwise
 */
bool phi_sensor_read(PhiSensorData *data);

/**
 * Perform sensor calibration routine (FR-007, SC-005)
 *
 * Acquires calibration samples and computes offset/scale factors
 *
 * @param duration_ms Calibration duration in milliseconds
 * @param calibration Pointer to store calibration results
 * @return true if calibration successful, false otherwise
 */
bool phi_sensor_calibrate(uint32_t duration_ms, PhiSensorCalibration *calibration);

/**
 * Load calibration data from memory
 *
 * @param calibration Calibration data to apply
 * @return true if loaded successfully, false otherwise
 */
bool phi_sensor_load_calibration(const PhiSensorCalibration *calibration);

/**
 * Get calibration data
 *
 * @param calibration Pointer to store calibration data
 * @return true if calibration data available, false otherwise
 */
bool phi_sensor_get_calibration(PhiSensorCalibration *calibration);

/**
 * Get sensor statistics (SC-002)
 *
 * @param stats Pointer to statistics structure to fill
 * @return true if statistics retrieved, false otherwise
 */
bool phi_sensor_get_statistics(PhiSensorStatistics *stats);

/**
 * Reset statistics counters
 *
 * @return true if reset successful, false otherwise
 */
bool phi_sensor_reset_statistics(void);

/**
 * Check if new data is available
 *
 * @return true if new data ready, false otherwise
 */
bool phi_sensor_data_available(void);

/**
 * Get current sample rate (measured)
 *
 * @return Actual sample rate in Hz
 */
float phi_sensor_get_sample_rate(void);

/**
 * Set sample rate
 *
 * @param rate_hz Desired sample rate (Hz)
 * @return true if set successfully, false otherwise
 */
bool phi_sensor_set_sample_rate(uint32_t rate_hz);

/**
 * Enable/disable signal filtering
 *
 * @param enable true to enable filtering, false to disable
 * @return true if successful, false otherwise
 */
bool phi_sensor_set_filtering(bool enable);

/**
 * Get firmware version string
 *
 * @return Firmware version string
 */
const char* phi_sensor_get_version(void);

/**
 * Self-test routine
 *
 * Verifies ADC operation and signal integrity
 *
 * @return true if self-test passed, false otherwise
 */
bool phi_sensor_self_test(void);

#ifdef __cplusplus
}
#endif

#endif // PHI_SENSOR_H
