#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include "analog_universal_node_engine_avx2.h"

namespace py = pybind11;

PYBIND11_MODULE(dase_engine, m) {
    m.doc() = "DASE Analog Engine - High-performance analog signal processing with AVX2 optimization";

    // EngineMetrics struct
    py::class_<EngineMetrics>(m, "EngineMetrics")
        .def(py::init<>())
        .def_readwrite("total_execution_time_ns", &EngineMetrics::total_execution_time_ns)
        .def_readwrite("avx2_operation_time_ns", &EngineMetrics::avx2_operation_time_ns)
        .def_readwrite("total_operations", &EngineMetrics::total_operations)
        .def_readwrite("avx2_operations", &EngineMetrics::avx2_operations)
        .def_readwrite("node_processes", &EngineMetrics::node_processes)
        .def_readwrite("harmonic_generations", &EngineMetrics::harmonic_generations)
        .def_readonly("current_ns_per_op", &EngineMetrics::current_ns_per_op)
        .def_readonly("current_ops_per_second", &EngineMetrics::current_ops_per_second)
        .def_readonly("speedup_factor", &EngineMetrics::speedup_factor)
        .def_readonly("target_ns_per_op", &EngineMetrics::target_ns_per_op)
        .def("reset", &EngineMetrics::reset)
        .def("update_performance", &EngineMetrics::update_performance)
        .def("print_metrics", &EngineMetrics::print_metrics);

    // AnalogUniversalNodeAVX2 class  
    py::class_<AnalogUniversalNodeAVX2>(m, "AnalogUniversalNode")
        .def(py::init<>())
        .def_readwrite("x", &AnalogUniversalNodeAVX2::x)
        .def_readwrite("y", &AnalogUniversalNodeAVX2::y) 
        .def_readwrite("z", &AnalogUniversalNodeAVX2::z)
        .def_readwrite("node_id", &AnalogUniversalNodeAVX2::node_id)
        .def("process_signal", &AnalogUniversalNodeAVX2::processSignal,
             "Process analog signal through the node",
             py::arg("input_signal"), py::arg("control_signal"), py::arg("aux_signal"))
        .def("process_signal_avx2", &AnalogUniversalNodeAVX2::processSignalAVX2,
             "Process analog signal with AVX2 optimization",
             py::arg("input_signal"), py::arg("control_signal"), py::arg("aux_signal"))
        .def("set_feedback", &AnalogUniversalNodeAVX2::setFeedback,
             "Set feedback coefficient",
             py::arg("feedback_coefficient"))
        .def("get_output", &AnalogUniversalNodeAVX2::getOutput,
             "Get current output value")
        .def("get_integrator_state", &AnalogUniversalNodeAVX2::getIntegratorState,
             "Get current integrator state")
        .def("reset_integrator", &AnalogUniversalNodeAVX2::resetIntegrator,
             "Reset integrator state to zero")
        // Add the separated functions if they exist
        .def("amplify", &AnalogUniversalNodeAVX2::amplify,
             "Simple amplification",
             py::arg("input_signal"), py::arg("gain"))
        .def("integrate", &AnalogUniversalNodeAVX2::integrate,
             "Integration with time constant",
             py::arg("input_signal"), py::arg("time_constant"))
        .def("apply_feedback", &AnalogUniversalNodeAVX2::applyFeedback,
             "Apply feedback to signal",
             py::arg("input_signal"), py::arg("feedback_gain"));

    // AnalogCellularEngineAVX2 class
    py::class_<AnalogCellularEngineAVX2>(m, "AnalogCellularEngine")
        .def(py::init<size_t>(), "Initialize engine with specified number of nodes",
             py::arg("num_nodes"))
        .def("process_signal_wave", &AnalogCellularEngineAVX2::processSignalWaveAVX2,
             "Process signal wave through cellular array",
             py::arg("input_signal"), py::arg("control_pattern"))
        .def("perform_signal_sweep", &AnalogCellularEngineAVX2::performSignalSweepAVX2,
             "Perform frequency sweep operation",
             py::arg("frequency"))
        .def("run_builtin_benchmark", &AnalogCellularEngineAVX2::runBuiltinBenchmark,
             "Run performance benchmark",
             py::arg("iterations") = 1000)
        .def("run_massive_benchmark", &AnalogCellularEngineAVX2::runMassiveBenchmark,
             "Run massive performance benchmark",
             py::arg("iterations") = 10000)
        .def("run_drag_race_benchmark", &AnalogCellularEngineAVX2::runDragRaceBenchmark,
             "Run drag race benchmark",
             py::arg("num_runs") = 5)
        .def("run_mission", &AnalogCellularEngineAVX2::runMission,
             "Run mission loop",
             py::arg("num_steps"))
        .def("process_block_frequency_domain", &AnalogCellularEngineAVX2::processBlockFrequencyDomain,
             "Process signal block in frequency domain",
             py::arg("signal_block"))
        .def("get_metrics", &AnalogCellularEngineAVX2::getMetrics,
             "Get current performance metrics")
        .def("print_live_metrics", &AnalogCellularEngineAVX2::printLiveMetrics,
             "Print current performance metrics")
        .def("reset_metrics", &AnalogCellularEngineAVX2::resetMetrics,
             "Reset performance counters")
        .def("generate_noise_signal", &AnalogCellularEngineAVX2::generateNoiseSignal,
             "Generate random noise signal")
        .def("calculate_inter_node_coupling", &AnalogCellularEngineAVX2::calculateInterNodeCoupling,
             "Calculate coupling between nodes",
             py::arg("node_index"));

    // CPUFeatures utility class - THIS WAS MISSING
    py::class_<CPUFeatures>(m, "CPUFeatures")
        .def_static("has_avx2", &CPUFeatures::hasAVX2,
                   "Check if CPU supports AVX2 instructions")
        .def_static("has_fma", &CPUFeatures::hasFMA,
                   "Check if CPU supports FMA instructions")
        .def_static("print_capabilities", &CPUFeatures::printCapabilities,
                   "Print detected CPU capabilities");

    // Version info
    m.attr("__version__") = "1.0.0";
    m.attr("avx2_enabled") = true;
    
    #ifdef _OPENMP
    m.attr("openmp_enabled") = true;
    #else
    m.attr("openmp_enabled") = false;
    #endif
}