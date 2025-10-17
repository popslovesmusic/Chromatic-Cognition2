"""
Mock Modules for Testing
Feature 020: Reproducible Build Environment + Dependency Bootstrap

Provides simulation/stub implementations for hardware-dependent components,
enabling headless testing in CI environments without audio devices or sensors.
"""

__all__ = ['mock_sounddevice', 'mock_hybrid_node', 'mock_dase_engine']
