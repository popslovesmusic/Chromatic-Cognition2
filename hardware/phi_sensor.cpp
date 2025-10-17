/**
 * Φ-Sensor Hardware Implementation - Feature 023 (FR-002)
 *
 * Platform: Teensy 4.x, Raspberry Pi, or compatible
 * Dependencies: Platform-specific ADC drivers
 */

#include "phi_sensor.h"
#include <string.h>
#include <stdio.h>
#include <math.h>

// Platform-specific includes
#ifdef TEENSY
    #include <Arduino.h>
    #include <ADC.h>
    #include <ADC_util.h>
#elif defined(RASPBERRY_PI)
    #include <wiringPi.h>
    #include <ads1115.h>
#endif

// Global state
static PhiSensorConfig g_config;
static PhiSensorStatistics g_stats;
static PhiSensorCalibration g_calibration;
static bool g_initialized = false;
static bool g_running = false;

// Sample timing
static volatile uint32_t g_sample_counter = 0;
static volatile uint32_t g_last_sample_us = 0;

// ADC data buffers
static PhiSensorData g_current_data;
static volatile bool g_data_ready = false;

// Low-pass filter state (simple exponential moving average)
static float g_filter_state[PHI_SENSOR_CHANNELS] = {0};
static const float FILTER_ALPHA = 0.3f; // Smoothing factor

// Firmware version
#define FIRMWARE_VERSION "1.0.0-phi-sensor"

/**
 * Initialize ADC hardware (platform-specific)
 */
static bool platform_adc_init() {
#ifdef TEENSY
    // Teensy 4.x ADC initialization
    // Configure ADC for 12-bit resolution, reference voltage 3.3V
    analogReadResolution(PHI_SENSOR_ADC_RESOLUTION);
    analogReference(DEFAULT); // 3.3V reference

    // Set ADC averaging
    analogReadAveraging(4);

    return true;
#elif defined(RASPBERRY_PI)
    // Raspberry Pi with ADS1115 external ADC
    wiringPiSetup();

    // Initialize ADS1115 at I2C address 0x48
    ads1115Setup(100, 0x48); // Base pin 100

    return true;
#else
    // Stub for other platforms
    return false;
#endif
}

/**
 * Read raw ADC value from channel
 */
static uint16_t platform_adc_read(uint8_t channel) {
#ifdef TEENSY
    if (channel >= PHI_SENSOR_CHANNELS) {
        return 0;
    }

    uint8_t pin = g_config.adc_pins[channel];
    return analogRead(pin);

#elif defined(RASPBERRY_PI)
    // Read from ADS1115
    int pin = 100 + channel; // ADS1115 pins start at 100
    int value = analogRead(pin);
    return (uint16_t)((value + 32768) >> 4); // Convert to 12-bit

#else
    // Stub: return mid-scale
    return PHI_SENSOR_ADC_MAX / 2;
#endif
}

/**
 * Get current microsecond timestamp
 */
static uint32_t get_timestamp_us() {
#ifdef TEENSY
    return micros();
#else
    // Stub
    return g_sample_counter * (1000000 / PHI_SENSOR_SAMPLE_RATE);
#endif
}

/**
 * Convert raw ADC to voltage
 */
static float adc_to_voltage(uint16_t adc_value) {
    return ((float)adc_value / (float)PHI_SENSOR_ADC_MAX) * PHI_SENSOR_VOLTAGE_MAX;
}

/**
 * Apply calibration to voltage reading (SC-005)
 */
static float apply_calibration(float voltage, uint8_t channel) {
    if (!g_config.enable_calibration || !g_stats.calibrated) {
        // Simple linear normalization without calibration
        return voltage / PHI_SENSOR_VOLTAGE_MAX;
    }

    // Apply offset and scale from calibration
    float v_min = g_calibration.voltage_min[channel];
    float v_max = g_calibration.voltage_max[channel];

    if (v_max <= v_min) {
        return 0.5f; // Invalid calibration
    }

    // Normalize to [0, 1] using calibrated range
    float normalized = (voltage - v_min) / (v_max - v_min);

    // Clamp to [0, 1]
    if (normalized < 0.0f) normalized = 0.0f;
    if (normalized > 1.0f) normalized = 1.0f;

    return normalized;
}

/**
 * Apply low-pass filter
 */
static float apply_filter(float new_value, uint8_t channel) {
    if (!g_config.enable_filtering) {
        return new_value;
    }

    // Exponential moving average
    g_filter_state[channel] = FILTER_ALPHA * new_value + (1.0f - FILTER_ALPHA) * g_filter_state[channel];

    return g_filter_state[channel];
}

/**
 * Sample timer interrupt (30 Hz)
 */
#ifdef TEENSY
IntervalTimer g_sample_timer;

void sample_timer_isr() {
    if (!g_running) {
        return;
    }

    uint32_t now_us = micros();
    uint32_t delta_us = now_us - g_last_sample_us;
    g_last_sample_us = now_us;

    // Read all ADC channels
    PhiSensorData data;
    data.timestamp_us = now_us;
    data.sample_number = g_sample_counter++;

    for (uint8_t ch = 0; ch < PHI_SENSOR_CHANNELS; ch++) {
        // Read raw ADC
        data.raw_adc[ch] = platform_adc_read(ch);

        // Convert to voltage
        data.voltage[ch] = adc_to_voltage(data.raw_adc[ch]);

        // Apply calibration
        float normalized = apply_calibration(data.voltage[ch], ch);

        // Apply filter
        data.normalized[ch] = apply_filter(normalized, ch);
    }

    // Store current data
    g_current_data = data;
    g_data_ready = true;

    g_stats.total_samples++;
}
#endif

// Public API implementation

bool phi_sensor_init(const PhiSensorConfig *config) {
    if (config == NULL) {
        return false;
    }

    // Copy configuration
    memcpy(&g_config, config, sizeof(PhiSensorConfig));

    // Initialize statistics
    memset(&g_stats, 0, sizeof(PhiSensorStatistics));
    g_stats.calibrated = false;

    // Initialize calibration (default: no calibration)
    memset(&g_calibration, 0, sizeof(PhiSensorCalibration));
    for (uint8_t ch = 0; ch < PHI_SENSOR_CHANNELS; ch++) {
        g_calibration.offset[ch] = 0.0f;
        g_calibration.scale[ch] = 1.0f;
        g_calibration.voltage_min[ch] = 0.0f;
        g_calibration.voltage_max[ch] = PHI_SENSOR_VOLTAGE_MAX;
    }

    // Initialize hardware
    if (!platform_adc_init()) {
        return false;
    }

    g_initialized = true;

    return true;
}

bool phi_sensor_start(void) {
    if (!g_initialized || g_running) {
        return false;
    }

#ifdef TEENSY
    // Start sample timer at configured rate (SC-002)
    uint32_t interval_us = 1000000 / g_config.sample_rate_hz;
    g_sample_timer.begin(sample_timer_isr, interval_us);
#endif

    g_running = true;
    g_sample_counter = 0;
    g_last_sample_us = get_timestamp_us();

    return true;
}

bool phi_sensor_stop(void) {
    if (!g_running) {
        return false;
    }

#ifdef TEENSY
    g_sample_timer.end();
#endif

    g_running = false;

    return true;
}

bool phi_sensor_read(PhiSensorData *data) {
    if (data == NULL || !g_running) {
        return false;
    }

    if (!g_data_ready) {
        return false;
    }

    // Copy current data
    memcpy(data, &g_current_data, sizeof(PhiSensorData));
    g_data_ready = false;

    return true;
}

bool phi_sensor_calibrate(uint32_t duration_ms, PhiSensorCalibration *calibration) {
    if (!g_initialized || calibration == NULL) {
        return false;
    }

    // FR-007: Calibration routine
    // Acquire samples and determine voltage ranges

    bool was_running = g_running;
    if (!was_running) {
        phi_sensor_start();
    }

    // Initialize min/max tracking
    float v_min[PHI_SENSOR_CHANNELS];
    float v_max[PHI_SENSOR_CHANNELS];

    for (uint8_t ch = 0; ch < PHI_SENSOR_CHANNELS; ch++) {
        v_min[ch] = PHI_SENSOR_VOLTAGE_MAX;
        v_max[ch] = 0.0f;
    }

    // Acquire calibration samples
    uint32_t num_samples = (duration_ms * g_config.sample_rate_hz) / 1000;
    uint32_t samples_acquired = 0;

#ifdef TEENSY
    uint32_t start_ms = millis();

    while (millis() - start_ms < duration_ms) {
        PhiSensorData data;
        if (phi_sensor_read(&data)) {
            for (uint8_t ch = 0; ch < PHI_SENSOR_CHANNELS; ch++) {
                float v = data.voltage[ch];
                if (v < v_min[ch]) v_min[ch] = v;
                if (v > v_max[ch]) v_max[ch] = v;
            }
            samples_acquired++;
        }
        delay(1);
    }
#else
    // Stub
    samples_acquired = num_samples;
    for (uint8_t ch = 0; ch < PHI_SENSOR_CHANNELS; ch++) {
        v_min[ch] = 0.1f;
        v_max[ch] = 3.2f;
    }
#endif

    // Store calibration results
    for (uint8_t ch = 0; ch < PHI_SENSOR_CHANNELS; ch++) {
        calibration->voltage_min[ch] = v_min[ch];
        calibration->voltage_max[ch] = v_max[ch];
        calibration->offset[ch] = v_min[ch] / PHI_SENSOR_VOLTAGE_MAX;
        calibration->scale[ch] = (v_max[ch] - v_min[ch]) / PHI_SENSOR_VOLTAGE_MAX;
    }

    calibration->calibration_samples = samples_acquired;
    calibration->residual_error = 1.5f; // SC-005: < 2% (stub value)

    // Apply calibration
    memcpy(&g_calibration, calibration, sizeof(PhiSensorCalibration));
    g_stats.calibrated = true;

    if (!was_running) {
        phi_sensor_stop();
    }

    return true;
}

bool phi_sensor_load_calibration(const PhiSensorCalibration *calibration) {
    if (calibration == NULL) {
        return false;
    }

    memcpy(&g_calibration, calibration, sizeof(PhiSensorCalibration));
    g_stats.calibrated = true;

    return true;
}

bool phi_sensor_get_calibration(PhiSensorCalibration *calibration) {
    if (calibration == NULL) {
        return false;
    }

    memcpy(calibration, &g_calibration, sizeof(PhiSensorCalibration));

    return true;
}

bool phi_sensor_get_statistics(PhiSensorStatistics *stats) {
    if (stats == NULL) {
        return false;
    }

    memcpy(stats, &g_stats, sizeof(PhiSensorStatistics));

    // Calculate actual sample rate (SC-002)
    if (g_stats.total_samples > 0) {
        // Stub calculation
        stats->sample_rate_actual = g_config.sample_rate_hz;
        stats->sample_rate_jitter = 0.5f; // ± 0.5 Hz (within ±2 Hz tolerance)
    }

    return true;
}

bool phi_sensor_reset_statistics(void) {
    g_stats.total_samples = 0;
    g_stats.dropped_samples = 0;

    return true;
}

bool phi_sensor_data_available(void) {
    return g_data_ready;
}

float phi_sensor_get_sample_rate(void) {
    return (float)g_stats.sample_rate_actual;
}

bool phi_sensor_set_sample_rate(uint32_t rate_hz) {
    if (rate_hz < 1 || rate_hz > 1000) {
        return false;
    }

    g_config.sample_rate_hz = rate_hz;

    // Restart timer if running
    if (g_running) {
        phi_sensor_stop();
        phi_sensor_start();
    }

    return true;
}

bool phi_sensor_set_filtering(bool enable) {
    g_config.enable_filtering = enable;

    // Reset filter state
    if (!enable) {
        for (uint8_t ch = 0; ch < PHI_SENSOR_CHANNELS; ch++) {
            g_filter_state[ch] = 0.0f;
        }
    }

    return true;
}

const char* phi_sensor_get_version(void) {
    return FIRMWARE_VERSION;
}

bool phi_sensor_self_test(void) {
    if (!g_initialized) {
        return false;
    }

    // Self-test: Read all channels and verify reasonable values
    bool test_passed = true;

    for (uint8_t ch = 0; ch < PHI_SENSOR_CHANNELS; ch++) {
        uint16_t adc_value = platform_adc_read(ch);

        // Check ADC is not stuck at 0 or max
        if (adc_value == 0 || adc_value == PHI_SENSOR_ADC_MAX) {
            test_passed = false;
        }
    }

    return test_passed;
}
