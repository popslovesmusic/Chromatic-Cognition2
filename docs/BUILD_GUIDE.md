# Soundlab Φ-Matrix - Build Guide

Feature 020: Reproducible Build Environment + Dependency Bootstrap

This guide provides complete instructions for building the Soundlab Φ-Matrix system, including the D-ASE Analog Engine C++ extension.

## Table of Contents

- [System Requirements](#system-requirements)
- [Toolchain Requirements](#toolchain-requirements)
- [Quick Start](#quick-start)
- [Platform-Specific Instructions](#platform-specific-instructions)
- [Building the C++ Extension](#building-the-c-extension)
- [Running Tests](#running-tests)
- [Troubleshooting](#troubleshooting)

## System Requirements

### Minimum Requirements

- **CPU**: x86-64 with AVX2 support (Intel Haswell+ or AMD Excavator+)
- **RAM**: 4 GB minimum, 8 GB recommended
- **Disk**: 2 GB free space
- **OS**:
  - Linux (Ubuntu 20.04+, Debian 11+, Fedora 35+)
  - macOS 11+ (Big Sur or later)
  - Windows 10/11 (64-bit)

### Checking CPU Support

```bash
# Linux
cat /proc/cpuinfo | grep avx2

# macOS
sysctl -a | grep machdep.cpu.features | grep AVX2

# Windows (PowerShell)
Get-CimInstance Win32_Processor | Select-Object -ExpandProperty Description
```

## Toolchain Requirements

### Python

- **Version**: Python 3.9 or later (3.11 recommended)
- **pip**: 21.0 or later

Check your Python version:
```bash
python --version  # or python3 --version
pip --version     # or pip3 --version
```

### C++ Compiler

#### Linux

- **GCC**: 10.0 or later (recommended)
- **Clang**: 12.0 or later

Install on Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install build-essential gcc g++ make cmake
```

Install on Fedora/RHEL:
```bash
sudo dnf groupinstall "Development Tools"
sudo dnf install gcc gcc-c++ make cmake
```

Verify installation:
```bash
gcc --version      # Should be >= 10.0
g++ --version      # Should be >= 10.0
make --version     # Should be >= 4.2
cmake --version    # Should be >= 3.18
```

#### macOS

- **Clang**: 12.0 or later (included with Xcode Command Line Tools)

Install Xcode Command Line Tools:
```bash
xcode-select --install
```

Install Homebrew (if not already installed):
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Install additional tools:
```bash
brew install cmake
```

Verify installation:
```bash
clang --version    # Should be >= 12.0
cmake --version    # Should be >= 3.18
```

#### Windows

- **MSVC**: Visual Studio 2019 (16.11+) or later
- **Build Tools**: Visual Studio Build Tools 2019+

Install Visual Studio:
1. Download [Visual Studio Community 2022](https://visualstudio.microsoft.com/downloads/)
2. During installation, select:
   - "Desktop development with C++"
   - "Python development" (optional but recommended)
3. Install CMake from https://cmake.org/download/ or via Visual Studio Installer

Verify installation (in Developer Command Prompt):
```cmd
cl         # Should show MSVC compiler version >= 19.30
cmake --version    # Should be >= 3.18
```

### System Libraries

#### Linux

Install FFTW3, PortAudio, and ALSA:

Ubuntu/Debian:
```bash
sudo apt-get install \
    libfftw3-dev \
    libfftw3-3 \
    portaudio19-dev \
    libasound2-dev
```

Fedora/RHEL:
```bash
sudo dnf install \
    fftw-devel \
    fftw \
    portaudio-devel \
    alsa-lib-devel
```

#### macOS

Install FFTW3 and PortAudio via Homebrew:
```bash
brew install fftw portaudio
```

#### Windows

- **FFTW3**: Pre-compiled DLL included in `sase amp fixed/` directory
- **PortAudio**: Bundled with sounddevice pip package

## Quick Start

### One-Command Setup

The easiest way to get started:

```bash
make setup
```

This command will:
1. Install all Python dependencies
2. Build the C++ extension (D-ASE engine)
3. Verify the build
4. Run post-install checks

Expected output:
```
========================================
Feature 020: Environment Bootstrap
========================================

[1/4] Installing Python dependencies...
✓ Python dependencies installed

[2/4] Building C++ extension (D-ASE)...
✓ C++ extension built: dase_engine.so/.pyd

[3/4] Verifying build...
D-ASE version: 1.0.0
CPU Capabilities: AVX2, FMA

[4/4] Running post-install checks...
Python 3.11.x
fastapi==0.111.x
pybind11==2.12.x
numpy==1.24.x
sounddevice==0.4.6

========================================
✓ Setup complete! Environment ready.
========================================
```

### Manual Setup

If you prefer step-by-step installation:

1. **Create virtual environment** (recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   .venv\Scripts\activate     # Windows
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r server/requirements.txt
   ```

3. **Build C++ extension**:
   ```bash
   cd "sase amp fixed"
   python setup.py build_ext --inplace
   cd ..
   ```

4. **Verify installation**:
   ```bash
   python -c "import dase_engine; print(dase_engine.__version__)"
   python -c "import dase_engine; dase_engine.CPUFeatures.print_capabilities()"
   ```

## Platform-Specific Instructions

### Linux Build

```bash
# 1. Install system dependencies
sudo apt-get install build-essential libfftw3-dev portaudio19-dev libasound2-dev

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies and build
pip install --upgrade pip setuptools wheel
pip install -r server/requirements.txt
cd "sase amp fixed"
python setup.py build_ext --inplace

# 4. Verify
python -c "import dase_engine; dase_engine.CPUFeatures.print_capabilities()"
```

Expected compiler flags:
```
-std=c++17 -O3 -march=native -mavx2 -msse4.2 -mfma
```

### macOS Build

```bash
# 1. Install dependencies via Homebrew
brew install fftw portaudio

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies and build
pip install --upgrade pip setuptools wheel
pip install -r server/requirements.txt
cd "sase amp fixed"
python setup.py build_ext --inplace

# 4. Verify
python -c "import dase_engine; dase_engine.CPUFeatures.print_capabilities()"
```

Expected compiler flags:
```
-std=c++17 -O3 -march=native -mavx2 -msse4.2 -mfma
```

### Windows Build

Open **Developer Command Prompt for VS 2022**:

```cmd
REM 1. Create virtual environment
python -m venv .venv
.venv\Scripts\activate

REM 2. Install dependencies and build
python -m pip install --upgrade pip setuptools wheel
pip install -r server\requirements.txt
cd "sase amp fixed"
python setup.py build_ext --inplace

REM 3. Verify
python -c "import dase_engine; dase_engine.CPUFeatures.print_capabilities()"
```

Expected compiler flags:
```
/EHsc /bigobj /std:c++17 /O2 /arch:AVX2 /fp:fast
```

## Building the C++ Extension

### Understanding the Build Process

The D-ASE Analog Engine (`dase_engine`) is a pybind11-based C++ extension that provides high-performance analog signal processing with AVX2 optimization.

Build files:
- `sase amp fixed/setup.py` - Build script (cross-platform)
- `sase amp fixed/analog_universal_node_engine_avx2.cpp` - Engine implementation
- `sase amp fixed/python_bindings.cpp` - Python bindings

### Build Commands

```bash
# Standard build (in-place)
cd "sase amp fixed"
python setup.py build_ext --inplace

# Clean build
python setup.py clean --all
python setup.py build_ext --inplace

# Install to site-packages
python setup.py install

# Development mode (editable install)
pip install -e "sase amp fixed"
```

### Makefile Targets

The Makefile provides convenient build targets:

```bash
# Build C++ extension only
make build-ext

# Clean C++ build artifacts
make build-ext-clean

# Full setup (dependencies + build)
make setup
```

### Verify Build Success

After building, verify the extension:

```bash
# Check module can be imported
python -c "import dase_engine; print('✓ Import successful')"

# Check version
python -c "import dase_engine; print(f'Version: {dase_engine.__version__}')"

# Check CPU capabilities
python -c "import dase_engine; dase_engine.CPUFeatures.print_capabilities()"

# Check AVX2 support
python -c "import dase_engine; print(f'AVX2 enabled: {dase_engine.avx2_enabled}')"

# Run quick benchmark
python -c "
import dase_engine
engine = dase_engine.AnalogCellularEngine(8)
result = engine.run_builtin_benchmark(100)
print(f'Benchmark: {result}')
"
```

## Running Tests

### Unit Tests

```bash
# All tests
make test

# Unit tests only
make test-unit

# With coverage
make test-cov

# Verbose output
make test-verbose
```

### Integration Tests

```bash
# Integration tests
make test-integration

# Validation scripts
make validate
```

### Simulation Mode (No Hardware)

Run tests without audio hardware:

```bash
# Headless/CI mode
make test-simulate

# Or manually
export SOUNDLAB_SIMULATE=1  # Linux/Mac
set SOUNDLAB_SIMULATE=1     # Windows
pytest tests/
```

## Troubleshooting

### Common Issues

#### 1. "ImportError: No module named 'pybind11'"

**Solution**:
```bash
pip install pybind11>=2.12.0
```

#### 2. "error: Microsoft Visual C++ 14.0 or greater is required"

**Solution**: Install Visual Studio Build Tools 2019+
- Download from https://visualstudio.microsoft.com/downloads/
- Select "Desktop development with C++"

#### 3. "fatal error: fftw3.h: No such file or directory"

**Solution**:

Linux:
```bash
sudo apt-get install libfftw3-dev
```

macOS:
```bash
brew install fftw
```

Windows: FFTW3 DLL should be in `sase amp fixed/` directory

#### 4. "AVX2 not supported on this CPU"

**Check CPU support**:
```bash
# Linux
grep avx2 /proc/cpuinfo

# If no AVX2, modify setup.py to remove AVX2 flags:
# Change: '/arch:AVX2' to '/arch:SSE2' (Windows)
# Or: '-mavx2' to '-msse2' (Linux/Mac)
```

#### 5. "dase_engine.so: cannot open shared object file"

**Solution** (Linux):
```bash
# Add current directory to library path
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$(pwd)/sase amp fixed"

# Or copy .so file to site-packages
cp "sase amp fixed/dase_engine.so" $(python -c "import site; print(site.getsitepackages()[0])")
```

#### 6. "error: command 'gcc' failed with exit status 1"

**Check compiler version**:
```bash
gcc --version  # Should be >= 10.0
```

**Update compiler** (Ubuntu):
```bash
sudo apt-get install gcc-10 g++-10
sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-10 100
```

### Build Logs

Enable verbose build output:

```bash
# Verbose setup.py
python setup.py build_ext --inplace --verbose

# Verbose make
make setup V=1
```

### Clean Build

If build fails, try a clean build:

```bash
# Clean Python cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete

# Clean C++ build artifacts
make build-ext-clean

# Clean all
make clean

# Rebuild
make setup
```

## Docker Build

For a completely reproducible environment, use Docker:

```bash
# Build development image
docker build -f Dockerfile.dev -t soundlab/phi-matrix:dev .

# Run interactive shell
docker run -it --rm \
    -v $(pwd):/workspace \
    soundlab/phi-matrix:dev \
    bash

# Inside container
make setup
make test
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Build and Test

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install system dependencies
      run: |
        sudo apt-get update
        sudo apt-get install -y libfftw3-dev portaudio19-dev

    - name: Setup environment
      run: make setup

    - name: Run tests
      run: make test-simulate

    - name: Run validation
      run: make validate
```

## Next Steps

After successful build:

1. **Run validation**: `make validate-020`
2. **Start server**: `cd server && python main.py`
3. **Run smoke tests**: `make smoke`
4. **Read operations guide**: `docs/OPERATIONS.md`

## Support

- **Documentation**: `docs/`
- **Issues**: https://github.com/soundlab/phi-matrix/issues
- **Troubleshooting**: `docs/TROUBLESHOOTING.md`
