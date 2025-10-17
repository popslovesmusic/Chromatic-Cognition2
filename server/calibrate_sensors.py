#!/usr/bin/env python3
"""
Sensor Calibration Utility - Feature 023 (FR-007)

Calibrates Φ-sensors and stores calibration data to config/sensors.json

Usage:
    python calibrate_sensors.py --duration 10000

Requirements:
- FR-007: Calibration routine stores offsets in /config/sensors.json
- SC-005: Calibration residual error < 2%
"""

import asyncio
import argparse
import json
import logging
from pathlib import Path
from datetime import datetime
from sensor_manager import SensorManager


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def calibrate_sensors(duration_ms: int = 10000, config_path: str = "config/sensors.json"):
    """
    Perform sensor calibration and save results

    Args:
        duration_ms: Calibration duration in milliseconds
        config_path: Path to save calibration config
    """
    print("=" * 70)
    print("Soundlab Φ-Sensor Calibration Utility")
    print("Feature 023 - Hardware Validation")
    print("=" * 70)
    print()

    # Create sensor manager
    config = {
        'simulation_mode': True,  # Set to False for real hardware
        'enable_watchdog': False,  # Disable watchdog during calibration
    }

    logger.info("Initializing sensor manager...")
    manager = SensorManager(config)

    # Start acquisition
    logger.info("Starting sensor acquisition...")
    await manager.start()

    # Wait for sensors to stabilize
    logger.info("Stabilizing sensors (2 seconds)...")
    await asyncio.sleep(2.0)

    # Perform calibration
    logger.info("Performing calibration (%d ms)...", duration_ms)
    print(f"\n{'='*70}")
    print(f"Calibration in progress: {duration_ms} ms")
    print(f"{'='*70}")

    calibration = await manager.calibrate(duration_ms=duration_ms)

    print("\nCalibration Results:")
    print("-" * 70)
    print(f"Samples collected: {calibration['samples']}")
    print(f"Duration: {calibration['duration_ms']} ms")
    print(f"Residual error: {calibration['residual_error']:.2f}%")
    print()

    # Show channel ranges
    for channel in ['phi_depth', 'phi_phase', 'coherence', 'criticality']:
        if channel in calibration:
            data = calibration[channel]
            print(f"{channel}:")
            print(f"  Min:  {data['min']:.4f}")
            print(f"  Max:  {data['max']:.4f}")
            print(f"  Mean: {data['mean']:.4f}")
            print(f"  Std:  {data['std']:.4f}")
            print()

    # Check residual error (SC-005)
    if calibration['residual_error'] >= 2.0:
        print(f"⚠ WARNING: Residual error {calibration['residual_error']:.2f}% exceeds 2% threshold")
        print("  Calibration may be inaccurate. Consider recalibrating.")
    else:
        print(f"✓ Residual error {calibration['residual_error']:.2f}% within acceptable range")

    # Save calibration
    config_file = Path(config_path)
    config_file.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Saving calibration to %s...", config_path)
    await manager.save_calibration(calibration, str(config_file))

    print()
    print("=" * 70)
    print(f"✓ Calibration saved to: {config_path}")
    print("=" * 70)

    # Stop acquisition
    await manager.stop()

    return calibration


def main():
    parser = argparse.ArgumentParser(
        description="Calibrate Φ-sensors and save calibration data"
    )

    parser.add_argument(
        '--duration',
        type=int,
        default=10000,
        help='Calibration duration in milliseconds (default: 10000)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='config/sensors.json',
        help='Output path for calibration data (default: config/sensors.json)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Run calibration
    asyncio.run(calibrate_sensors(
        duration_ms=args.duration,
        config_path=args.output
    ))


if __name__ == "__main__":
    main()
