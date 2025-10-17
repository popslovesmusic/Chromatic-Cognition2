# Performance Benchmarks

Feature 026 (FR-006): Performance tracking and regression detection

## Overview

This directory contains performance benchmarks and tracking data for Soundlab + D-ASE. Benchmarks measure latency, throughput, and resource usage across different scenarios.

## Files

- **latency_v1.1.json**: Target and current performance metrics for v1.1
- **README.md**: This file

## Benchmark Metrics

### Latency Metrics (lower is better)
- **phi_matrix_latency_ms**: Time to compute Φ-matrix analysis
- **dase_latency_ms**: D-ASE engine processing time
- **i2s_latency_ms**: I²S hardware bridge latency
- **total_pipeline_latency_ms**: End-to-end processing latency

### Throughput Metrics (higher is better)
- **websocket_update_rate_hz**: WebSocket metric update frequency
- **throughput_streams_per_core**: Concurrent streams per CPU core
- **cpu_usage_percent**: CPU utilization per stream

## Running Benchmarks

### Compare against baseline:
```bash
python scripts/check_benchmarks.py
```

### Run with make:
```bash
make benchmarks
```

### Run full benchmark suite:
```bash
pytest benchmarks/test_performance.py -v
```

## Targets for v1.1

| Metric | v1.0 Baseline | v1.1 Target | Improvement |
|--------|---------------|-------------|-------------|
| Φ-matrix latency | 8.2ms | 5.0ms | -39% |
| D-ASE latency | 3.1ms | 2.5ms | -19% |
| I²S latency | 0.35ms | 0.30ms | -14% |
| Throughput | 3.2 streams/core | 4.2 streams/core | +31% |

## Optimization Roadmap

### Phase 2 Optimizations (A-001, A-002)
- **AVX-512 support**: 25% improvement expected
- **Latency reduction**: 40% improvement expected
- **WebSocket compression**: 15% bandwidth improvement

See [docs/roadmap_v1.1.md](../docs/roadmap_v1.1.md) for details.

## Regression Tolerance

Performance variance thresholds (SC-003):
- **Latency**: ±5%
- **Throughput**: ±5%
- **CPU usage**: ±10%

Exceeding these thresholds triggers a regression warning.

## Test Scenarios

### 1. Single Stream (48kHz)
Standard single-stream processing at 48kHz, 512 block size.
**Target:** < 5ms latency

### 2. Multi-Stream (4×)
Four concurrent streams to test scalability.
**Target:** < 60% CPU usage

### 3. High Sample Rate (96kHz)
Processing at 96kHz for high-fidelity audio.
**Target:** < 8ms latency

### 4. Multi-Channel (8ch)
8-channel processing for surround sound.
**Target:** < 12ms latency

## System Requirements

Benchmarks assume:
- Modern CPU with AVX2 support (AVX-512 for v1.1 targets)
- 16GB+ RAM
- Quiet system (minimal background processes)
- Python 3.11+

## References

- [Regression Tests](../tests/regression/README.md)
- [Roadmap v1.1](../docs/roadmap_v1.1.md)
- [Performance Baseline v1.0](../tests/regression/baselines/performance_latency_v1.0.json)
