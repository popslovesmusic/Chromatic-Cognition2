# Soundlab Φ-Matrix - Quickstart Guide

**Get up and running with the Φ-Matrix audio synthesis system in under 10 minutes**

Feature 022: Developer SDK & Documentation

## Overview

The Soundlab Φ-Matrix is a real-time audio synthesis system that uses Φ (golden ratio) based adaptive modulation with a high-performance D-ASE analog engine. This guide will get you from zero to running tests in minutes.

## Prerequisites

- **Python**: 3.9+ (3.11 recommended)
- **OS**: Windows 10+, Linux (Ubuntu 20.04+), or macOS 11+
- **CPU**: x86-64 with AVX2 support
- **Memory**: 4 GB minimum, 8 GB recommended
- **Disk**: 2 GB free space

### Quick Check
```bash
python --version   # Should be 3.9+
git --version      # Should be 2.0+
make --version     # Should be 4.0+ (optional but recommended)
```

## Step 1: Clone Repository

```bash
git clone https://github.com/soundlab/phi-matrix.git
cd phi-matrix
```

**Time: ~30 seconds**

## Step 2: Environment Setup

### One-Command Setup (Recommended)

```bash
make setup
```

This command:
1. Installs all Python dependencies
2. Builds the D-ASE C++ extension (optional)
3. Verifies the installation
4. Runs post-install checks

**Time: 3-5 minutes**

### Manual Setup (Alternative)

If you don't have `make` or prefer manual control:

```bash
# 1. Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# OR
.venv\Scripts\activate     # Windows

# 2. Install dependencies
pip install -r server/requirements.txt

# 3. Build C++ extension (optional, for D-ASE engine)
cd "sase amp fixed"
python setup.py build_ext --inplace
cd ..
```

**Time: 3-5 minutes**

## Step 3: Verify Installation

```bash
# Check Python packages
python -c "import fastapi, numpy, sounddevice; print('✓ Core packages installed')"

# Check D-ASE engine (optional)
python -c "import dase_engine; print(f'D-ASE version: {dase_engine.__version__}')" 2>/dev/null || echo "D-ASE not built (optional)"

# Run validation
cd server && python validate_feature_020.py
```

**Time: ~30 seconds**

## Step 4: Start the Server

### With Audio Hardware

```bash
cd server
python main.py
```

### Without Audio Hardware (Simulation Mode)

```bash
cd server
export SOUNDLAB_SIMULATE=1  # Linux/Mac
# OR
set SOUNDLAB_SIMULATE=1     # Windows

python main.py
```

The server will start on `http://localhost:8000`

**Time: ~10 seconds**

## Step 5: Verify Server is Running

Open a new terminal:

```bash
# Check health
curl http://localhost:8000/healthz

# Check metrics
curl http://localhost:8000/metrics

# Check version
curl http://localhost:8000/version
```

Expected output:
```json
{
  "status": "healthy",
  "service": "soundlab-phi-matrix",
  "version": "0.9.0-rc1"
}
```

**Time: ~10 seconds**

## Step 6: Open Dashboard

Open your web browser and navigate to:

- **Main Dashboard**: http://localhost:8000/static/phi-matrix-dashboard.html
- **Chromatic Visualizer**: http://localhost:8000/static/chromatic-visualizer.html
- **API Documentation**: http://localhost:8000/docs

**Time: ~10 seconds**

## Step 7: Run Tests

```bash
# Quick unit tests
make test-fast

# Or full test suite (simulation mode)
make test-simulate
```

**Time: 1-2 minutes**

## Quick Reference

### Common Commands

```bash
# Setup
make setup              # Initial setup (one time)
make install            # Install dependencies only

# Running
cd server && python main.py                    # Start server
SOUNDLAB_SIMULATE=1 cd server && python main.py  # Start in simulation mode

# Testing
make test               # Run all tests
make test-fast          # Run unit tests only
make test-perf          # Run performance benchmarks
make test-simulate      # Run tests without hardware

# Building
make build-ext          # Build C++ extension
make build-ext-clean    # Clean C++ build
make docker-build       # Build Docker image

# Validation
make validate           # Run all validation scripts
make validate-020       # Validate build environment
make validate-021       # Validate test framework

# Documentation
make docs               # Generate documentation
make help               # Show all available targets
```

### Configuration Files

| File | Purpose |
|------|---------|
| `server/requirements.txt` | Python dependencies |
| `pyproject.toml` | Build system configuration |
| `pytest.ini` | Test configuration |
| `Makefile` | Build automation |
| `server/config/performance_profile.json` | Performance tuning |
| `.env` | Environment variables (create if needed) |

### Key Directories

| Directory | Contents |
|-----------|----------|
| `server/` | Main Python server code |
| `static/` | Web dashboard and visualizers |
| `tests/` | Unit, integration, and performance tests |
| `docs/` | Documentation |
| `examples/` | SDK usage examples |
| `smoke/` | Smoke tests |
| `scripts/` | Utility scripts |
| `sase amp fixed/` | D-ASE C++ engine |

## Troubleshooting

### Port 8000 Already in Use

```bash
# Find process using port
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# Use different port
uvicorn main:app --port 8001
```

### Audio Device Not Found

Use simulation mode:
```bash
export SOUNDLAB_SIMULATE=1  # Linux/Mac
set SOUNDLAB_SIMULATE=1     # Windows
```

### C++ Extension Build Fails

The D-ASE engine is optional. The system works without it using Python fallbacks.

To build manually:
```bash
cd "sase amp fixed"
python setup.py build_ext --inplace --verbose
```

See `docs/BUILD_GUIDE.md` for detailed troubleshooting.

### Dependencies Installation Issues

```bash
# Upgrade pip first
pip install --upgrade pip setuptools wheel

# Reinstall dependencies
pip install --force-reinstall -r server/requirements.txt
```

### Tests Failing

```bash
# Run in simulation mode
make test-simulate

# Check server is not running
curl http://localhost:8000/healthz || echo "Server not running (OK for tests)"
```

## Next Steps

Now that you're up and running:

1. **Explore the API**: http://localhost:8000/docs
2. **Read Architecture**: `docs/ARCHITECTURE.md`
3. **Try Examples**: `examples/` directory
4. **Read API Reference**: `docs/api_reference/`
5. **Contribute**: See `docs/CONTRIBUTING.md`

### Learn More

- **Architecture Overview**: `docs/ARCHITECTURE.md`
- **Build Guide**: `docs/BUILD_GUIDE.md`
- **Operations Guide**: `docs/OPERATIONS.md`
- **Troubleshooting**: `docs/TROUBLESHOOTING.md`
- **Contributing**: `docs/CONTRIBUTING.md`
- **API Reference**: `docs/api_reference/`

## Performance Tuning

Edit `server/config/performance_profile.json`:

```json
{
  "target_fps": 30,          // Target frame rate
  "audio_buffer_ms": 10,      // Audio buffer size
  "visual_complexity_level": 5, // Visual detail level
  "enable_phi_breathing": true, // Φ breathing effect
  "enable_topology_links": true  // Network visualization
}
```

## Environment Variables

Create `.env` file in project root:

```bash
# Server
SOUNDLAB_ENV=development
SOUNDLAB_PORT=8000
SOUNDLAB_LOG_LEVEL=info

# Audio
SOUNDLAB_SAMPLE_RATE=48000
SOUNDLAB_BUFFER_SIZE=512

# Features
SOUNDLAB_ENABLE_CORS=true
SOUNDLAB_ENABLE_ADAPTIVE_SCALING=true
SOUNDLAB_SIMULATE=0  # Set to 1 for simulation mode

# Performance
SOUNDLAB_MAX_CONNECTIONS=100
SOUNDLAB_TARGET_FPS=30
```

## Docker Quickstart

```bash
# Build image
make docker-build

# Run container
docker run -p 8000:8000 soundlab/phi-matrix:0.9.0-rc1

# Or use docker-compose
docker-compose -f docker-compose.staging.yml up
```

## Getting Help

- **Issues**: https://github.com/soundlab/phi-matrix/issues
- **Discussions**: https://github.com/soundlab/phi-matrix/discussions
- **Documentation**: `docs/` directory
- **Troubleshooting**: `docs/TROUBLESHOOTING.md`

## Summary

You should now have:
- ✅ Environment set up
- ✅ Dependencies installed
- ✅ Server running
- ✅ Tests passing
- ✅ Dashboard accessible

**Total time: ~10 minutes**

Ready to explore! Check out `examples/` for SDK usage samples.
