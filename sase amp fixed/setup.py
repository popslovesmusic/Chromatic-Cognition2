from setuptools import setup, Extension
import pybind11

# Define compiler arguments for MSVC (Windows)
extra_compile_args = ['/EHsc', '/bigobj', '/std:c++17', '/O2', '/arch:AVX2', '/DNOMINMAX']

ext_modules = [
    Extension(
        'dase_engine',
        ['analog_universal_node_engine_avx2.cpp', 'python_bindings.cpp'],
        include_dirs=[
            pybind11.get_include(),
            '.'  # Include current directory for header files
        ],
        language='c++',
        extra_compile_args=extra_compile_args,
        library_dirs=['.'],  # <-- ADD THIS LINE
        libraries=['libfftw3-3']
    ),
]

setup(
    name='dase_engine',
    version='1.0',
    description='D-ASE Analog Engine C++ extension compiled with pybind11',
    ext_modules=ext_modules,
)