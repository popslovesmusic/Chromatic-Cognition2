# Regression Test Suite

Feature 026 (FR-005): Regression testing against v1.0 baseline

## Overview

This directory contains regression tests that ensure new development (v1.1+) does not break existing functionality from v1.0.0. Tests compare current behavior against golden baselines captured from the v1.0.0 release.

## Structure

```
regression/
├── README.md                    # This file
├── test_v1_0_baseline.py       # Main regression test suite
├── baselines/                   # Golden baseline data
│   ├── metadata.json           # Baseline version metadata
│   ├── performance_latency_v1.0.json
│   ├── api_healthz_v1.0.json
│   ├── config_defaults_v1.0.json
│   └── ...                     # Other baseline files
└── scripts/
    └── capture_baseline.py      # Script to capture new baselines
```

## Running Regression Tests

### Run all regression tests:
```bash
pytest tests/regression/ -v
```

### Run with baseline comparison:
```bash
make regression
```

### Run specific test class:
```bash
pytest tests/regression/test_v1_0_baseline.py::TestPhiMatrixRegression -v
```

## Tolerance Thresholds

- **Performance metrics**: ±5% variance allowed (SC-003)
- **Functional outputs**: Exact match required
- **API structure**: All required keys must be present

## Baseline Files

Baseline files are JSON documents that capture expected behavior from v1.0.0:

- **performance_latency_v1.0.json**: Latency measurements for Φ-matrix, D-ASE, I²S
- **api_healthz_v1.0.json**: Expected structure of /healthz endpoint
- **api_metrics_v1.0.json**: Expected structure of /api/metrics endpoint
- **config_defaults_v1.0.json**: Default configuration values
- **phi_depth_v1.0.json**: Expected Φ-depth calculation results
- **coherence_v1.0.json**: Expected coherence metric results
- **dase_fft_v1.0.json**: D-ASE FFT processing expectations
- **dase_dissipation_v1.0.json**: Dissipation computation expectations

## Capturing New Baselines

When releasing a new major version (e.g., v2.0.0), capture new baselines:

```bash
# Capture all baselines from current state
python tests/regression/scripts/capture_baseline.py --version 1.1.0

# Capture specific baseline
python tests/regression/scripts/capture_baseline.py --version 1.1.0 --only performance_latency
```

## Interpreting Failures

### Performance Regression
If performance tests fail:
1. Check if the variance exceeds 5% threshold
2. Review recent commits for performance-impacting changes
3. Run benchmarks to confirm the regression
4. Consider if the change is intentional (e.g., trading latency for accuracy)

### Functional Regression
If functional tests fail:
1. Verify the API structure change is intentional
2. Update API version if breaking change is required
3. Provide migration guide for users
4. Update baselines only after confirming the change is correct

### API Structure Regression
If API structure tests fail:
1. Ensure all required keys from v1.0 are still present
2. New keys can be added without breaking compatibility
3. Removing keys requires a major version bump

## Integration with CI

Regression tests run automatically:
- **On pull requests**: Ensures PRs don't introduce regressions
- **Weekly maintenance**: Catches drift over time
- **Before releases**: Part of the Go/No-Go checklist

See `.github/workflows/maintenance.yml` for CI configuration.

## Success Criteria (SC-003)

✅ All regression tests pass
✅ Performance variance < 5%
✅ No functional behavior changes without explicit approval
✅ API structure maintains backward compatibility

## References

- [Roadmap v1.1](../../docs/roadmap_v1.1.md)
- [Versioning Policy](../../docs/versioning_policy.md)
- [Maintenance Workflow](../../.github/workflows/maintenance.yml)
