/**
 * I²S Bridge - Feature 023
 * Hardware synchronization bridge for Soundlab/PhaseNet
 *
 * Provides real-time audio and consciousness metrics exchange via I²S protocol
 * with GPIO sync pulses for drift recalibration.
 *
 * Requirements:
 * - FR-001: I²S bridge interface
 * - FR-002: Master/slave mode selection
 * - FR-003: Φ-phase and coherence encoding (32-bit float)
 * - FR-004: 8-channel 48kHz 24-bit format with DMA
 * - FR-005: GPIO 1 kHz sync pulse
 * - FR-006: Serial diagnostic interface
 * - FR-010: Loopback self-test
 *
 * Success Criteria:
 * - SC-001: Round-trip latency ≤40 µs; jitter ≤5 µs
 * - SC-002: Metrics loss <0.1% over 1h
 * - SC-003: Failover recovery <1s
 */

#ifndef I2S_BRIDGE_H
#define I2S_BRIDGE_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

// Configuration constants (FR-004)
#define I2S_SAMPLE_RATE     48000
#define I2S_BIT_DEPTH       24
#define I2S_CHANNELS        8
#define I2S_BUFFER_SIZE     512
#define GPIO_SYNC_FREQ_HZ   1000

// Mode selection (FR-002)
typedef enum {
    I2S_MODE_MASTER = 0,
    I2S_MODE_SLAVE = 1
} I2SMode;

// Link status
typedef enum {
    I2S_LINK_DISCONNECTED = 0,
    I2S_LINK_SYNCING = 1,
    I2S_LINK_STABLE = 2,
    I2S_LINK_DEGRADED = 3,
    I2S_LINK_ERROR = 4
} I2SLinkStatus;

// Configuration structure
typedef struct {
    I2SMode mode;                    // Master or slave mode
    uint32_t sample_rate;            // Audio sample rate (Hz)
    uint8_t bit_depth;               // Bits per sample (16, 24, 32)
    uint8_t channels;                // Number of audio channels
    uint16_t buffer_size;            // DMA buffer size in samples
    bool enable_gpio_sync;           // Enable GPIO sync pulse (FR-005)
    bool enable_diagnostics;         // Enable serial diagnostics (FR-006)
    uint8_t gpio_sync_pin;           // GPIO pin for sync pulse
} I2SBridgeConfig;

// Consciousness metrics structure (FR-003)
typedef struct {
    float phi_phase;                 // Φ-phase [0, 2π]
    float phi_depth;                 // Φ-depth [0, 1]
    float coherence;                 // Phase coherence [0, 1]
    float criticality;               // Criticality metric [0, ∞]
    float ici;                       // Inter-Criticality Interval (ms)
    uint32_t timestamp_us;           // Microsecond timestamp
    uint32_t sequence;               // Sequence number
} ConsciousnessMetrics;

// Statistics structure
typedef struct {
    uint64_t frames_transmitted;     // Total frames sent
    uint64_t frames_received;        // Total frames received
    uint64_t frames_dropped;         // Dropped frames
    uint32_t latency_us;             // Round-trip latency (µs) (SC-001)
    uint32_t jitter_us;              // Latency jitter (µs) (SC-001)
    float clock_drift_ppm;           // Clock drift (parts per million)
    I2SLinkStatus link_status;       // Current link status
    uint32_t uptime_ms;              // Uptime since last reset
} I2SStatistics;

// Function prototypes

/**
 * Initialize I²S bridge with configuration (FR-001, FR-002)
 *
 * @param config Configuration structure
 * @return true if initialization successful, false otherwise
 */
bool i2s_bridge_init(const I2SBridgeConfig *config);

/**
 * Start I²S communication and DMA transfers (FR-004)
 *
 * @return true if started successfully, false otherwise
 */
bool i2s_bridge_start(void);

/**
 * Stop I²S communication
 *
 * @return true if stopped successfully, false otherwise
 */
bool i2s_bridge_stop(void);

/**
 * Transmit audio frame with interleaved consciousness metrics (FR-003, FR-004)
 *
 * @param audio_data Pointer to audio samples (int32_t array, channels * buffer_size)
 * @param metrics Consciousness metrics to encode
 * @return true if transmission queued successfully, false otherwise
 */
bool i2s_bridge_transmit(const int32_t *audio_data, const ConsciousnessMetrics *metrics);

/**
 * Receive audio frame with interleaved consciousness metrics (FR-003, FR-004)
 *
 * @param audio_data Buffer to store received audio samples
 * @param metrics Buffer to store decoded consciousness metrics
 * @return true if data available and decoded, false otherwise
 */
bool i2s_bridge_receive(int32_t *audio_data, ConsciousnessMetrics *metrics);

/**
 * Enable/disable GPIO sync pulse (FR-005)
 *
 * @param enable true to enable sync pulse, false to disable
 * @return true if successful, false otherwise
 */
bool i2s_bridge_set_gpio_sync(bool enable);

/**
 * Get current statistics (SC-001, SC-002)
 *
 * @param stats Pointer to statistics structure to fill
 * @return true if statistics retrieved, false otherwise
 */
bool i2s_bridge_get_statistics(I2SStatistics *stats);

/**
 * Reset statistics counters
 *
 * @return true if reset successful, false otherwise
 */
bool i2s_bridge_reset_statistics(void);

/**
 * Get current link status
 *
 * @return Current link status
 */
I2SLinkStatus i2s_bridge_get_link_status(void);

/**
 * Perform loopback self-test (FR-010, SC-001)
 *
 * Transmits test pattern and measures round-trip latency
 *
 * @param latency_us Pointer to store measured latency (µs)
 * @param jitter_us Pointer to store measured jitter (µs)
 * @return true if test passed, false otherwise
 */
bool i2s_bridge_self_test(uint32_t *latency_us, uint32_t *jitter_us);

/**
 * Send diagnostic message over serial (FR-006)
 *
 * @param message Null-terminated diagnostic string
 * @return true if sent successfully, false otherwise
 */
bool i2s_bridge_send_diagnostic(const char *message);

/**
 * Check if diagnostic data available
 *
 * @return true if diagnostic data available, false otherwise
 */
bool i2s_bridge_diagnostic_available(void);

/**
 * Read diagnostic message from serial (FR-006)
 *
 * @param buffer Buffer to store received message
 * @param max_len Maximum buffer length
 * @return Number of bytes read, or -1 on error
 */
int i2s_bridge_read_diagnostic(char *buffer, size_t max_len);

/**
 * Calibrate clock drift (FR-005)
 *
 * Uses GPIO sync pulse to measure and compensate for clock drift
 *
 * @return Measured drift in parts per million (ppm)
 */
float i2s_bridge_calibrate_drift(void);

/**
 * Get firmware version string
 *
 * @return Firmware version string
 */
const char* i2s_bridge_get_version(void);

#ifdef __cplusplus
}
#endif

#endif // I2S_BRIDGE_H
