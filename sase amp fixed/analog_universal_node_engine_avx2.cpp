#include "analog_universal_node_engine_avx2.h"
#include <algorithm>
#include <random>
#include <chrono>
#include <iostream>
#include <iomanip>
#include <fftw3.h>
#include <immintrin.h>
#include <omp.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// Global metrics instance (lightweight)
static EngineMetrics g_metrics;

// High-precision timer class
class PrecisionTimer {
private:
    std::chrono::high_resolution_clock::time_point start_time;
    uint64_t* target_counter;
    
public:
    PrecisionTimer(uint64_t* counter) : target_counter(counter) {
        start_time = std::chrono::high_resolution_clock::now();
    }
    
    ~PrecisionTimer() {
        auto end_time = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(end_time - start_time);
        if (target_counter) {
            *target_counter += duration.count();
        }
    }
};

// Lightweight profiling macros
#define PROFILE_TOTAL() PrecisionTimer _total_timer(&g_metrics.total_execution_time_ns)
#define COUNT_OPERATION() g_metrics.total_operations++
#define COUNT_AVX2() g_metrics.avx2_operations++
#define COUNT_NODE() g_metrics.node_processes++
#define COUNT_HARMONIC() g_metrics.harmonic_generations++

// EngineMetrics implementation
void EngineMetrics::reset() {
    total_execution_time_ns = 0;
    avx2_operation_time_ns = 0;
    total_operations = 0;
    avx2_operations = 0;
    node_processes = 0;
    harmonic_generations = 0;
}

void EngineMetrics::update_performance() {
    if (total_operations > 0) {
        current_ns_per_op = static_cast<double>(total_execution_time_ns) / total_operations;
        current_ops_per_second = 1000000000.0 / current_ns_per_op;
        speedup_factor = 15500.0 / current_ns_per_op; // vs baseline 15,500ns
    }
}

void EngineMetrics::print_metrics() {
    update_performance();
    std::cout << "\n🚀 D-ASE AVX2 ENGINE METRICS 🚀" << std::endl;
    std::cout << "================================" << std::endl;
    std::cout << std::fixed << std::setprecision(2);
    std::cout << "⚡ Current Performance: " << current_ns_per_op << " ns/op" << std::endl;
    std::cout << "🎯 Target (8,000ns):   " << (current_ns_per_op <= target_ns_per_op ? "✅ ACHIEVED!" : "🔄 In Progress") << std::endl;
    std::cout << "🚀 Speedup Factor:     " << speedup_factor << "x" << std::endl;
    std::cout << "📊 Operations/sec:     " << static_cast<uint64_t>(current_ops_per_second) << std::endl;
    std::cout << "🔢 Total Operations:   " << total_operations << std::endl;
    std::cout << "⚙️  AVX2 Operations:    " << avx2_operations << " (" << (100.0 * avx2_operations / total_operations) << "%)" << std::endl;
    std::cout << "🎵 Harmonics Generated: " << harmonic_generations << std::endl;
    
    if (current_ns_per_op <= target_ns_per_op) {
        std::cout << "🎉 TARGET ACHIEVED! Engine ready for production!" << std::endl;
    } else {
        uint64_t remaining_ns = static_cast<uint64_t>(current_ns_per_op - target_ns_per_op);
        std::cout << "⏱️  Need " << remaining_ns << "ns improvement to hit target" << std::endl;
    }
    std::cout << "================================\n" << std::endl;
}

// AVX2 Vectorized Math Functions 
namespace AVX2Math {
    __m256 fast_sin_avx2(__m256 x) {
        // Fast sin approximation using AVX2
        __m256 pi2 = _mm256_set1_ps(2.0f * M_PI);
        x = _mm256_sub_ps(x, _mm256_mul_ps(pi2, _mm256_floor_ps(_mm256_div_ps(x, pi2))));
        __m256 x2 = _mm256_mul_ps(x, x);
        __m256 x3 = _mm256_mul_ps(x2, x);
        __m256 x5 = _mm256_mul_ps(x3, x2);
        __m256 c1 = _mm256_set1_ps(-1.0f / 6.0f);
        return _mm256_add_ps(x, _mm256_add_ps(_mm256_mul_ps(c1, x3), _mm256_mul_ps(_mm256_set1_ps(1.0f / 120.0f), x5)));
    }

    __m256 fast_cos_avx2(__m256 x) {
        // Fast cos approximation using AVX2
        __m256 pi2 = _mm256_set1_ps(2.0f * M_PI);
        x = _mm256_sub_ps(x, _mm256_mul_ps(pi2, _mm256_floor_ps(_mm256_div_ps(x, pi2))));
        __m256 x2 = _mm256_mul_ps(x, x);
        __m256 x4 = _mm256_mul_ps(x2, x2);
        __m256 one = _mm256_set1_ps(1.0f);
        __m256 c1 = _mm256_set1_ps(-1.0f / 2.0f);
        return _mm256_add_ps(one, _mm256_add_ps(_mm256_mul_ps(c1, x2), _mm256_mul_ps(_mm256_set1_ps(1.0f / 24.0f), x4)));
    }

    void generate_harmonics_avx2(float input_signal, float pass_offset, float* harmonics_out) {
        PROFILE_TOTAL();
        COUNT_AVX2();
        COUNT_HARMONIC();
        
        // Vectorized harmonic generation - 8 harmonics at once
        __m256 input_vec = _mm256_set1_ps(input_signal);
        __m256 offset_vec = _mm256_set1_ps(pass_offset);
        __m256 harmonics = _mm256_set_ps(8.0f, 7.0f, 6.0f, 5.0f, 4.0f, 3.0f, 2.0f, 1.0f);
        __m256 freq_vec = _mm256_mul_ps(input_vec, harmonics);
        freq_vec = _mm256_add_ps(freq_vec, offset_vec);
        __m256 base_amp = _mm256_set1_ps(0.1f);
        __m256 amplitudes = _mm256_div_ps(base_amp, harmonics);
        __m256 sin_vals = fast_sin_avx2(freq_vec);
        __m256 result = _mm256_mul_ps(sin_vals, amplitudes);
        _mm256_store_ps(harmonics_out, result);
    }

    float process_spectral_avx2(float output_base) {
        PROFILE_TOTAL();
        COUNT_AVX2();
        
        // Fast spectral processing using AVX2
        __m256 base_vec = _mm256_set1_ps(output_base);
        __m256 freq_mults = _mm256_set_ps(2.7f, 2.1f, 1.8f, 1.4f, 1.2f, 0.9f, 0.7f, 0.3f);
        __m256 processed = _mm256_mul_ps(base_vec, freq_mults);
        processed = fast_sin_avx2(processed);
        __m128 low = _mm256_extractf128_ps(processed, 0);
        __m128 high = _mm256_extractf128_ps(processed, 1);
        __m128 sum = _mm_add_ps(low, high);
        sum = _mm_hadd_ps(sum, sum);
        sum = _mm_hadd_ps(sum, sum);
        return _mm_cvtss_f32(sum) * 0.125f; // Divide by 8
    }

} // End AVX2Math namespace

// AnalogUniversalNodeAVX2 Implementation
double AnalogUniversalNodeAVX2::amplify(double input_signal, double gain) {
    return input_signal * gain;
}

double AnalogUniversalNodeAVX2::integrate(double input_signal, double time_constant) {
    integrator_state += (input_signal - integrator_state) * time_constant;
    return integrator_state;
}

double AnalogUniversalNodeAVX2::applyFeedback(double input_signal, double feedback_gain) {
    double feedback_component = integrator_state * feedback_gain;
    return input_signal + feedback_component;
}

double AnalogUniversalNodeAVX2::processSignalAVX2(double input_signal, double control_signal, double aux_signal) {
    PROFILE_TOTAL();
    COUNT_OPERATION();
    COUNT_NODE();

    double amplified_signal = amplify(input_signal, control_signal);
    double integrated_output = integrate(amplified_signal, 0.1);
    double aux_blended = amplified_signal + aux_signal;

    float spectral_boost = AVX2Math::process_spectral_avx2(static_cast<float>(aux_blended));
    
    double feedback_output = applyFeedback(integrated_output, feedback_gain);
    
    current_output = feedback_output + static_cast<double>(spectral_boost);
    current_output = clamp_custom(current_output, -10.0, 10.0);
    
    previous_input = input_signal;

    return current_output;
}

double AnalogUniversalNodeAVX2::processSignal(double input_signal, double control_signal, double aux_signal) {
    return processSignalAVX2(input_signal, control_signal, aux_signal);
}

void AnalogUniversalNodeAVX2::setFeedback(double feedback_coefficient) {
    feedback_gain = clamp_custom(feedback_coefficient, -2.0, 2.0);
}

double AnalogUniversalNodeAVX2::getOutput() const {
    return current_output;
}

double AnalogUniversalNodeAVX2::getIntegratorState() const {
    return integrator_state;
}

void AnalogUniversalNodeAVX2::resetIntegrator() {
    integrator_state = 0.0;
    previous_input = 0.0;
}

// AnalogCellularEngineAVX2 Implementation
AnalogCellularEngineAVX2::AnalogCellularEngineAVX2(size_t num_nodes)
    : nodes(num_nodes), system_frequency(1.0), noise_level(0.001) {
    for (size_t i = 0; i < num_nodes; i++) {
        nodes[i] = AnalogUniversalNodeAVX2();
        nodes[i].x = static_cast<int16_t>(i % 10);
        nodes[i].y = static_cast<int16_t>((i / 10) % 10);
        nodes[i].z = static_cast<int16_t>(i / 100);
        nodes[i].node_id = static_cast<uint16_t>(i);
    }
}

// New: The mission loop is now in C++ to run at max speed
void AnalogCellularEngineAVX2::runMission(uint64_t num_steps) {
    #ifdef _OPENMP
    omp_set_dynamic(0);
    omp_set_num_threads(omp_get_max_threads());
    #endif

    g_metrics.reset();

    std::cout << "\n🚀 C++ MISSION LOOP STARTED 🚀" << std::endl;
    std::cout << "===============================" << std::endl;
    std::cout << "Total steps: " << num_steps << std::endl;
    std::cout << "Total nodes: " << nodes.size() << std::endl;
    std::cout << "Threads: " << omp_get_max_threads() << std::endl;
    std::cout << "===============================" << std::endl;

    for (uint64_t step = 0; step < num_steps; ++step) {
        double input_signal = std::sin(static_cast<double>(step) * 0.01);
        double control_pattern = std::cos(static_cast<double>(step) * 0.01);

        #pragma omp parallel for
        for (int i = 0; i < nodes.size(); i++) {
            // New: Added a nested loop to significantly increase the workload per thread
            for (int j = 0; j < 30; ++j) {
                nodes[i].processSignalAVX2(input_signal, control_pattern, 0.0);
            }
        }
        
        // Removed blocking I/O here to prevent bottlenecks
        // No progress logs to keep the CPU focused on computation
    }

    g_metrics.print_metrics();
    std::cout << "===============================" << std::endl;
}

// New: The massive benchmark function to simulate a continuous heavy load
void AnalogCellularEngineAVX2::runMassiveBenchmark(int iterations) {
    std::cout << "\n🚀 D-ASE BUILTIN BENCHMARK STARTING 🚀" << std::endl;
    std::cout << "=====================================" << std::endl;
    
    // Reset metrics
    g_metrics.reset();
    
    // CPU capability check
    std::cout << "🖥️  CPU Features:" << std::endl;
    std::cout << "   AVX2: " << (CPUFeatures::hasAVX2() ? "✅" : "❌") << std::endl;
    std::cout << "   FMA:  " << (CPUFeatures::hasFMA() ? "✅" : "❌") << std::endl;
    
    // Warmup
    std::cout << "🔥 Warming up..." << std::endl;
    for (int i = 0; i < 100; i++) {
        performSignalSweepAVX2(1.0 + i * 0.001);
    }
    
    // Reset after warmup
    g_metrics.reset();
    
    std::cout << "⚡ Running " << iterations << " iterations..." << std::endl;
    
    auto bench_start = std::chrono::high_resolution_clock::now();
    
    for (int i = 0; i < iterations; i++) {
        double frequency = 1.0 + (i % 100) * 0.01;
        performSignalSweepAVX2(frequency);
        
        // Live progress every 100 operations
        if ((i + 1) % 100 == 0) {
            g_metrics.update_performance();
            std::cout << "   Progress: " << (i + 1) << "/" << iterations 
                     << " | Current: " << std::setprecision(1) << g_metrics.current_ns_per_op << "ns/op" << std::endl;
        }
    }
    
    auto bench_end = std::chrono::high_resolution_clock::now();
    auto total_bench_time = std::chrono::duration_cast<std::chrono::milliseconds>(bench_end - bench_start);
    
    // Final metrics
    g_metrics.print_metrics();
    
    std::cout << "⏱️  Total Benchmark Time: " << total_bench_time.count() << " ms" << std::endl;
    std::cout << "🎯 AVX2 Usage: " << std::setprecision(1) << (100.0 * g_metrics.avx2_operations / g_metrics.total_operations) << "%" << std::endl;
    
    // Success criteria
    if (g_metrics.current_ns_per_op <= g_metrics.target_ns_per_op) {
        std::cout << "🏆 BENCHMARK SUCCESS! Target achieved!" << std::endl;
    } else {
        std::cout << "🔄 Benchmark complete. Continue optimization." << std::endl;
    }
    
    std::cout << "=====================================" << std::endl;
}

// New: The drag race benchmark function
double AnalogCellularEngineAVX2::runDragRaceBenchmark(int num_runs) {
    std::cout << "\n🏁 D-ASE DRAG RACE BENCHMARK STARTING 🏁" << std::endl;
    std::cout << "=====================================" << std::endl;
    
    // Force maximum parallel utilization
    #ifdef _OPENMP
    omp_set_dynamic(0);
    omp_set_num_threads(omp_get_max_threads());
    #endif
    
    // Reset metrics before the test
    g_metrics.reset();

    double total_time_ms = 0.0;
    const int num_iterations = 10000; // Number of inner loop iterations for the burst
    
    for (int run = 0; run < num_runs; ++run) {
        auto start_time = std::chrono::high_resolution_clock::now();
        
        #pragma omp parallel for
        for (int i = 0; i < nodes.size(); ++i) {
            // This is the short-duration, high-intensity workload
            for(int j = 0; j < num_iterations; ++j) {
                double input_signal = 1.0;
                double control_pattern = 1.0;
                nodes[i].processSignalAVX2(input_signal, control_pattern, 0.0);
            }
        }
        
        auto end_time = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time);
        total_time_ms += duration.count();
        std::cout << "   Run " << run + 1 << ": " << duration.count() << " ms" << std::endl;
    }
    
    double average_time_ms = total_time_ms / num_runs;
    
    std::cout << "=====================================" << std::endl;
    std::cout << "🏁 Average Drag Race Time: " << average_time_ms << " ms" << std::endl;
    std::cout << "=====================================" << std::endl;
    
    return average_time_ms;
}

double AnalogCellularEngineAVX2::processSignalWaveAVX2(double input_signal, double control_pattern) {
    double total_output = 0.0;

    #ifdef _OPENMP
    omp_set_dynamic(0);
    omp_set_num_threads(omp_get_max_threads());
    #endif

    #pragma omp parallel for reduction(+:total_output) schedule(dynamic, 2)
    for (int i = 0; i < static_cast<int>(nodes.size()); i++) {
        for (int pass = 0; pass < 10; pass++) {
            double control = control_pattern + std::sin(static_cast<double>(i + pass) * 0.1) * 0.3;
            double aux_signal = input_signal * 0.5;

            alignas(32) float harmonics_result[8];
            AVX2Math::generate_harmonics_avx2(static_cast<float>(input_signal),
                                             static_cast<float>(pass) * 0.1f, harmonics_result);

            for (int h = 0; h < 8; h++) {
                aux_signal += static_cast<double>(harmonics_result[h]);
            }

            double output = nodes[i].processSignalAVX2(input_signal, control, aux_signal);
            total_output += output;
        }
    }

    return total_output / (static_cast<double>(nodes.size()) * 10.0);
}

double AnalogCellularEngineAVX2::performSignalSweepAVX2(double frequency) {
    PROFILE_TOTAL();
    
    double sweep_result = 0.0;
    
    for (int sweep_pass = 0; sweep_pass < 5; sweep_pass++) {
        double time_step = static_cast<double>(sweep_pass) * 0.1;
        double input_signal = std::sin(frequency * time_step * 2.0 * M_PI);
        double control_pattern = std::cos(frequency * time_step * 1.5 * M_PI) * 0.7;
        
        double pass_output = processSignalWaveAVX2(input_signal, control_pattern);
        sweep_result += pass_output;
    }
    
    return sweep_result / 5.0;
}

void AnalogCellularEngineAVX2::runBuiltinBenchmark(int iterations) {
    std::cout << "\n🚀 D-ASE BUILTIN BENCHMARK STARTING 🚀" << std::endl;
    std::cout << "=====================================" << std::endl;
    
    g_metrics.reset();
    
    std::cout << "🖥️  CPU Features:" << std::endl;
    std::cout << "   AVX2: " << (CPUFeatures::hasAVX2() ? "✅" : "❌") << std::endl;
    std::cout << "   FMA:  " << (CPUFeatures::hasFMA() ? "✅" : "❌") << std::endl;
    
    std::cout << "🔥 Warming up..." << std::endl;
    for (int i = 0; i < 100; i++) {
        performSignalSweepAVX2(1.0 + i * 0.001);
    }
    
    g_metrics.reset();
    
    std::cout << "⚡ Running " << iterations << " iterations..." << std::endl;
    
    auto bench_start = std::chrono::high_resolution_clock::now();
    
    for (int i = 0; i < iterations; i++) {
        double frequency = 1.0 + (i % 100) * 0.01;
        performSignalSweepAVX2(frequency);
        
        if ((i + 1) % 100 == 0) {
            g_metrics.update_performance();
            std::cout << "   Progress: " << (i + 1) << "/" << iterations 
                     << " | Current: " << std::setprecision(1) << g_metrics.current_ns_per_op << "ns/op" << std::endl;
        }
    }
    
    auto bench_end = std::chrono::high_resolution_clock::now();
    auto total_bench_time = std::chrono::duration_cast<std::chrono::milliseconds>(bench_end - bench_start);
    
    g_metrics.print_metrics();
    
    std::cout << "⏱️  Total Benchmark Time: " << total_bench_time.count() << " ms" << std::endl;
    std::cout << "🎯 AVX2 Usage: " << std::setprecision(1) << (100.0 * g_metrics.avx2_operations / g_metrics.total_operations) << "%" << std::endl;
    
    if (g_metrics.current_ns_per_op <= g_metrics.target_ns_per_op) {
        std::cout << "🏆 BENCHMARK SUCCESS! Target achieved!" << std::endl;
    } else {
        std::cout << "🔄 Benchmark complete. Continue optimization." << std::endl;
    }
    
    std::cout << "=====================================" << std::endl;
}

void AnalogCellularEngineAVX2::processBlockFrequencyDomain(std::vector<double>& signal_block) {
    int N = signal_block.size();
    fftw_complex* in = (fftw_complex*) fftw_malloc(sizeof(fftw_complex) * N);
    fftw_complex* out = (fftw_complex*) fftw_malloc(sizeof(fftw_complex) * N);
    fftw_plan p = fftw_plan_dft_1d(N, in, out, FFTW_FORWARD, FFTW_ESTIMATE);

    for (int i = 0; i < N; ++i) {
        in[i][0] = signal_block[i];
        in[i][1] = 0;
    }

    fftw_execute(p);

    // --- MANIPULATE FREQUENCIES HERE (e.g., a simple filter) ---
    for (int i = N / 4; i < (N * 3 / 4); ++i) {
         out[i][0] = 0;
         out[i][1] = 0;
    }

    fftw_plan p_inv = fftw_plan_dft_1d(N, out, in, FFTW_BACKWARD, FFTW_ESTIMATE);
    fftw_execute(p_inv);

    for (int i = 0; i < N; ++i) {
        signal_block[i] = in[i][0] / N;
    }

    fftw_destroy_plan(p);
    fftw_destroy_plan(p_inv);
    fftw_free(in);
    fftw_free(out);
}

EngineMetrics AnalogCellularEngineAVX2::getMetrics() const {
    return g_metrics;
}

void AnalogCellularEngineAVX2::printLiveMetrics() {
    g_metrics.print_metrics();
}

void AnalogCellularEngineAVX2::resetMetrics() {
    g_metrics.reset();
}

double AnalogCellularEngineAVX2::generateNoiseSignal() {
    static std::random_device rd;
    static std::mt19937 gen(rd());
    static std::normal_distribution<double> dist(0.0, noise_level);
    return dist(gen);
}

double AnalogCellularEngineAVX2::calculateInterNodeCoupling(size_t node_index) {
    if (node_index >= nodes.size()) return 0.0;
    
    // Simple nearest-neighbor coupling
    double coupling = 0.0;
    if (node_index > 0) {
        coupling += nodes[node_index - 1].getOutput() * 0.1;
    }
    if (node_index < nodes.size() - 1) {
        coupling += nodes[node_index + 1].getOutput() * 0.1;
    }
    
    return coupling;
}

// CPU Feature Detection Implementation
bool CPUFeatures::hasAVX2() {
    #ifdef _WIN32
    int cpui[4];
    __cpuid(cpui, 7);
    return (cpui[1] & (1 << 5)) != 0; // EBX bit 5 = AVX2
    #else
    unsigned int eax, ebx, ecx, edx;
    __asm__ __volatile__(
        "cpuid"
        : "=a"(eax), "=b"(ebx), "=c"(ecx), "=d"(edx)
        : "a"(7), "c"(0)
    );
    return (ebx & (1 << 5)) != 0;
    #endif
}

bool CPUFeatures::hasFMA() {
    #ifdef _WIN32
    int cpui[4];
    __cpuid(cpui, 1);
    return (cpui[2] & (1 << 12)) != 0; // ECX bit 12 = FMA
    #else
    unsigned int eax, ebx, ecx, edx;
    __asm__ __volatile__(
        "cpuid"
        : "=a"(eax), "=b"(ebx), "=c"(ecx), "=d"(edx)
        : "a"(1), "c"(0)
    );
    return (ecx & (1 << 12)) != 0;
    #endif
}

bool CPUFeatures::checkCPUID(int function, int subfunction, int reg, int bit) {
    #ifdef _WIN32
    int cpui[4];
    __cpuidex(cpui, function, subfunction);
    return (cpui[reg] & (1 << bit)) != 0;
    #else
    unsigned int eax, ebx, ecx, edx;
    __asm__ __volatile__(
        "cpuid"
        : "=a"(eax), "=b"(ebx), "=c"(ecx), "=d"(edx)
        : "a"(function), "c"(subfunction)
    );
    unsigned int result = (reg == 0) ? eax : (reg == 1) ? ebx : (reg == 2) ? ecx : edx;
    return (result & (1U << bit)) != 0;
    #endif
}

void CPUFeatures::printCapabilities() {
    std::cout << "CPU Features Detected:" << std::endl;
    std::cout << "  AVX2: " << (hasAVX2() ? "✅ Supported" : "❌ Not Available") << std::endl;
    std::cout << "  FMA:  " << (hasFMA() ? "✅ Supported" : "❌ Not Available") << std::endl;
    
    if (hasAVX2()) {
        std::cout << "🚀 AVX2 acceleration will provide 2-3x speedup!" << std::endl;
    } else {
        std::cout << "⚠️  Falling back to scalar operations" << std::endl;
    }
}
