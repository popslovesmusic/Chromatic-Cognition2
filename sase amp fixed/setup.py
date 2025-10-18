"""
D-ASE Analog Engine Setup Script
Feature 020: Reproducible Build Environment + Dependency Bootstrap

Cross-platform build system for pybind11 C++ extension with AVX2 optimization.

Requirements (FR-008):
- gcc/g++ ≥ 10 (Linux)
- clang ≥ 12 (macOS)
- MSVC ≥ 19.30 (Windows)
- CMake ≥ 3.18 (optional)
- pybind11 ≥ 2.12

Build:
    python setup.py build_ext --inplace
    python setup.py install

Test:
    python -c "import dase_engine; print(dase_engine.__version__)"
    python -c "import dase_engine; dase_engine.print_cpu_capabilities()"
"""

from setuptools import setup, Extension
import sys
import platform
import os

try:
    import pybind11
except ImportError:
    print("ERROR: pybind11 not found. Install with: pip install pybind11>=2.12.0")
    sys.exit(1)

# Detect platform
is_windows = sys.platform == 'win32'
is_linux = sys.platform.startswith('linux')
is_macos = sys.platform == 'darwin'

# Base configuration
sources = [
    'analog_universal_node_engine_avx2.cpp',
    'python_bindings.cpp'
]

include_dirs = [
    pybind11.get_include(),
    '.'  # Current directory for headers
]

library_dirs = ['.']
libraries = []

# Platform-specific compiler flags (FR-003)
if is_windows:
    # MSVC compiler flags
    extra_compile_args = [
        '/EHsc',        # Exception handling model
        '/bigobj',      # Large object files
        '/std:c++17',   # C++17 standard
        '/O2',          # Optimize for speed
        '/arch:AVX2',   # Enable AVX2 instructions
        '/fp:fast',     # Fast floating point
        '/DNOMINMAX',   # Disable min/max macros
    ]
    extra_link_args = []
    libraries = ['libfftw3-3']

    print("Building for Windows (MSVC) with AVX2 optimization")

elif is_linux:
    # GCC/Clang compiler flags for Linux
    extra_compile_args = [
        '-std=c++17',       # C++17 standard
        '-O3',              # Maximum optimization
        '-march=native',    # Optimize for current CPU
        '-mavx2',           # Enable AVX2 instructions
        '-msse4.2',         # Enable SSE 4.2
        '-mfma',            # Enable FMA instructions
        '-ffast-math',      # Fast math optimizations
        '-fPIC',            # Position independent code
        '-Wall',            # Enable warnings
        '-Wno-unused-result',
    ]

    # Check for OpenMP support
    if os.path.exists('/usr/lib/gcc') or os.path.exists('/usr/lib/x86_64-linux-gnu/'):
        extra_compile_args.append('-fopenmp')
        extra_link_args = ['-fopenmp']
    else:
        extra_link_args = []

    # FFTW3 library
    libraries = ['fftw3']

    print("Building for Linux (GCC/Clang) with AVX2 optimization")

elif is_macos:
    # Clang compiler flags for macOS
    extra_compile_args = [
        '-std=c++17',       # C++17 standard
        '-O3',              # Maximum optimization
        '-march=native',    # Optimize for current CPU
        '-mavx2',           # Enable AVX2 instructions
        '-msse4.2',         # Enable SSE 4.2
        '-mfma',            # Enable FMA instructions
        '-ffast-math',      # Fast math optimizations
        '-fPIC',            # Position independent code
        '-Wall',            # Enable warnings
        '-Wno-unused-result',
    ]
    extra_link_args = []

    # FFTW3 via homebrew
    if os.path.exists('/opt/homebrew/lib'):
        library_dirs.append('/opt/homebrew/lib')
        include_dirs.append('/opt/homebrew/include')
    elif os.path.exists('/usr/local/lib'):
        library_dirs.append('/usr/local/lib')
        include_dirs.append('/usr/local/include')

    libraries = ['fftw3']

    print("Building for macOS (Clang) with AVX2 optimization")

else:
    print(f"WARNING: Unsupported platform: {sys.platform}")
    print("Using default compiler flags")
    extra_compile_args = ['-std=c++17', '-O2']
    extra_link_args = []

# CPU feature detection
print(f"Python version: {sys.version}")
print(f"Platform: {platform.platform()}")
print(f"Architecture: {platform.machine()}")
print(f"Compiler flags: {' '.join(extra_compile_args)}")

# Define extension module
ext_modules = [
    Extension(
        'dase_engine',
        sources=sources,
        include_dirs=include_dirs,
        library_dirs=library_dirs,
        libraries=libraries,
        language='c++',
        extra_compile_args=extra_compile_args,
        extra_link_args=extra_link_args,
    ),
]

# Setup configuration
setup(
    name='dase_engine',
    version='1.0.0',
    author='Soundlab Team',
    author_email='noreply@soundlab.io',
    description='D-ASE Analog Engine - High-performance analog signal processing with AVX2 optimization',
    long_description=__doc__,
    long_description_content_type='text/plain',
    ext_modules=ext_modules,
    install_requires=[
        'pybind11>=2.12.0',
        'numpy>=1.24.0',
    ],
    python_requires='>=3.9',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: C++',
        'Topic :: Multimedia :: Sound/Audio',
    ],
    zip_safe=False,
)

# Post-build verification
if __name__ == '__main__':
    print("\n" + "="*70)
    print("Build Configuration Summary")
    print("="*70)
    print(f"Extension: dase_engine")
    print(f"Sources: {', '.join(sources)}")
    print(f"Platform: {sys.platform}")
    print(f"Optimization: AVX2 + SSE4.2")
    print("="*70)
    print("\nTo verify build:")
    print("  python -c \"import dase_engine; print(dase_engine.__version__)\"")
    print("  python -c \"import dase_engine; dase_engine.print_cpu_capabilities()\"")
    print("="*70)