#pragma once

#include <vector>
#include <cstdint>
#include <cmath>
#include <omp.h> // Include OpenMP for parallel processing

// Forward declaration for CPU feature detection
namespace CPUFeatures {
    bool hasAVX2();
    bool hasFMA();
    void printCapabilities();
    bool checkCPUID(int function, int subfunction, int reg, int bit);
}

// Lightweight metrics system
struct EngineMetrics {
    uint64_t total_execution_time_ns;
    uint64_t avx2_operation_time_ns;
    uint64_t total_operations;
    uint64_t avx2_operations;
    uint64_t node_processes;
    uint64_t harmonic_generations;
    double current_ns_per_op;
    double current_ops_per_second;
    double speedup_factor;
    const double target_ns_per_op = 8000.0;

    void reset();
    void update_performance();
    void print_metrics();
};

// Generic clamp function
inline double clamp_custom(double value, double min, double max) {
    return (value > max) ? max : (value < min) ? min : value;
}

// AnalogUniversalNodeAVX2 Definition
class AnalogUniversalNodeAVX2 {
public:
    AnalogUniversalNodeAVX2() : integrator_state(0.0), feedback_gain(0.0), current_output(0.0), previous_input(0.0), operation_count(0) {}

    // Main processing function - now acts as a pipeline
    double processSignalAVX2(double input_signal, double control_signal, double aux_signal);
    double processSignal(double input_signal, double control_signal, double aux_signal);

    // Getters and setters
    void setFeedback(double feedback_coefficient);
    double getOutput() const;
    double getIntegratorState() const;
    void resetIntegrator();
    
    // Core analog functions
    double amplify(double input_signal, double gain);
    double integrate(double input_signal, double time_constant);
    double applyFeedback(double input_signal, double feedback_gain);
    
    // Public member variables for cellular grid placement
    int16_t x, y, z;
    uint16_t node_id;

private:
    // Internal state variables
    double integrator_state;
    double feedback_gain;
    double current_output;
    double previous_input;
    uint64_t operation_count;
};

// AnalogCellularEngineAVX2 Definition
class AnalogCellularEngineAVX2 {
public:
    AnalogCellularEngineAVX2(size_t num_nodes);
    double processSignalWaveAVX2(double input_signal, double control_pattern);
    double performSignalSweepAVX2(double frequency);
    void runBuiltinBenchmark(int iterations);
    void runMassiveBenchmark(int iterations);
    void runMission(uint64_t num_steps);
    // New: The drag race benchmark function
    double runDragRaceBenchmark(int num_runs);
    void processBlockFrequencyDomain(std::vector<double>& signal_block);
    
    // Metrics
    EngineMetrics getMetrics() const;
    void printLiveMetrics();
    void resetMetrics();

    // Helper functions
    double generateNoiseSignal();
    double calculateInterNodeCoupling(size_t node_index);
    
    std::vector<AnalogUniversalNodeAVX2> nodes;
    double system_frequency;
    double noise_level;
};
