#!/usr/bin/env python3
"""
Retention Purge Utility - Feature 024 (FR-010)

Purges expired data based on retention policy defined in config/privacy.json

Usage:
    python scripts/purge_retention.py --dry-run
    python scripts/purge_retention.py --data-type logs
    python scripts/purge_retention.py --force

Requirements:
- FR-010: Retention policy enforcement and purge CLI
- SC-005: Purge reduces on-disk artifacts by ≥95% for expired set
"""

import sys
import argparse
from pathlib import Path

# Add server directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'server'))

from privacy_manager import PrivacyManager


def main():
    parser = argparse.ArgumentParser(
        description='Purge expired data based on retention policy'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Report what would be deleted without actually deleting'
    )

    parser.add_argument(
        '--data-type',
        type=str,
        choices=['logs', 'session_metrics', 'temp_files', 'recordings', 'all'],
        default='all',
        help='Type of data to purge (default: all)'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Force purge without confirmation'
    )

    parser.add_argument(
        '--config',
        type=str,
        default='config/privacy.json',
        help='Path to privacy config (default: config/privacy.json)'
    )

    args = parser.parse_args()

    print("=" * 70)
    print("Soundlab Data Retention Purge Utility")
    print("Feature 024 - Security & Privacy Audit")
    print("=" * 70)
    print()

    # Initialize privacy manager
    privacy = PrivacyManager(args.config)

    # Show retention policy
    print("Retention Policy:")
    print("-" * 70)
    for data_type, days in privacy.retention.config['retention_periods'].items():
        print(f"  {data_type:20s}: {days} days")
    print()

    # Confirm if not dry-run and not forced
    if not args.dry_run and not args.force:
        response = input("Proceed with purge? [y/N]: ")
        if response.lower() not in ['y', 'yes']:
            print("Purge cancelled")
            return

    # Run purge
    if args.data_type == 'all':
        print("Purging all expired data...")
        print("-" * 70)
        stats = privacy.purge_all_expired(dry_run=args.dry_run)
    else:
        print(f"Purging expired {args.data_type}...")
        print("-" * 70)

        patterns = {
            'logs': 'logs/**/*.log',
            'session_metrics': 'logs/**/*_metrics.csv',
            'temp_files': 'temp/**/*',
            'recordings': 'recordings/**/*.wav'
        }

        stats = privacy.purge_expired_data(
            args.data_type,
            patterns[args.data_type],
            dry_run=args.dry_run
        )

        # Wrap single result in expected format
        stats = {
            'timestamp': stats.get('timestamp', ''),
            'dry_run': args.dry_run,
            'total_files_deleted': stats.get('files_deleted', 0),
            'total_bytes_freed': stats.get('bytes_freed', 0),
            'results': [stats]
        }

    # Display results
    print()
    print("Purge Results:")
    print("-" * 70)

    if args.dry_run:
        print("  [DRY RUN] No files were actually deleted")
        print()

    print(f"  Files deleted: {stats['total_files_deleted']}")
    print(f"  Bytes freed: {stats['total_bytes_freed']:,} bytes "
          f"({stats['total_bytes_freed'] / 1024 / 1024:.2f} MB)")
    print()

    # Detail by data type
    for result in stats.get('results', []):
        if result.get('files_found', 0) > 0:
            print(f"  {result['data_type']}:")
            print(f"    Files: {result['files_found']} found, "
                  f"{result['files_deleted']} deleted")
            print(f"    Space: {result['bytes_freed']:,} bytes")

    print()

    # Calculate purge effectiveness (SC-005: ≥95%)
    if stats['total_files_deleted'] > 0:
        # For this metric, we assume all found files were expired
        total_found = sum(r.get('files_found', 0) for r in stats.get('results', []))
        purge_rate = (stats['total_files_deleted'] / total_found * 100) if total_found > 0 else 0

        print(f"Purge effectiveness: {purge_rate:.1f}% "
              f"({'PASS' if purge_rate >= 95 else 'FAIL'} SC-005)")
        print()

    # Audit log
    if not args.dry_run:
        privacy.audit_log_purge(stats)
        print("✓ Purge action logged to audit log")
    else:
        print("  [DRY RUN] No audit log created")

    print()
    print("=" * 70)
    print("Purge complete")
    print("=" * 70)


if __name__ == '__main__':
    main()
