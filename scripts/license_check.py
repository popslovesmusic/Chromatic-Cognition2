#!/usr/bin/env python3
"""
License Compliance Checker - Feature 024 (FR-013)

Checks dependencies against license allowlist

Usage:
    python scripts/license_check.py \\
        --licenses licenses.json \\
        --allowlist config/license-allowlist.txt \\
        --report license-compliance.json
"""

import json
import argparse
import sys
from pathlib import Path
from typing import Set, List, Dict


# Known problematic licenses
FORBIDDEN_LICENSES = {
    'GPL-3.0',
    'AGPL-3.0',
    'SSPL',  # Server Side Public License
    'BUSL',  # Business Source License
}

# Default allowed licenses
DEFAULT_ALLOWED = {
    'MIT',
    'Apache-2.0',
    'BSD-2-Clause',
    'BSD-3-Clause',
    'ISC',
    'Python-2.0',
    'PSF',
    'Unlicense',
    'CC0-1.0',
    'MPL-2.0',
}


def load_allowlist(allowlist_path: str) -> Set[str]:
    """Load license allowlist from file"""
    if not Path(allowlist_path).exists():
        print(f"Warning: Allowlist not found: {allowlist_path}")
        return DEFAULT_ALLOWED

    with open(allowlist_path) as f:
        return {line.strip() for line in f if line.strip() and not line.startswith('#')}


def check_licenses(licenses_data: Dict, allowlist: Set[str]) -> Dict:
    """Check licenses against allowlist"""

    violations = []
    warnings = []
    approved = []

    for package in licenses_data:
        name = package.get('Name', 'Unknown')
        version = package.get('Version', '')
        license_name = package.get('License', 'Unknown')

        # Normalize license name
        license_normalized = license_name.replace(' ', '-').upper()

        # Check if forbidden
        if any(forbidden in license_normalized for forbidden in FORBIDDEN_LICENSES):
            violations.append({
                'package': name,
                'version': version,
                'license': license_name,
                'severity': 'critical',
                'reason': 'Forbidden license'
            })
        # Check if not in allowlist
        elif license_name not in allowlist and license_normalized not in {l.upper() for l in allowlist}:
            warnings.append({
                'package': name,
                'version': version,
                'license': license_name,
                'severity': 'warning',
                'reason': 'License not in allowlist'
            })
        else:
            approved.append({
                'package': name,
                'version': version,
                'license': license_name
            })

    return {
        'total_packages': len(licenses_data),
        'approved': len(approved),
        'warnings': len(warnings),
        'violations': len(violations),
        'approved_packages': approved,
        'warning_packages': warnings,
        'violation_packages': violations,
        'passed': len(violations) == 0
    }


def main():
    parser = argparse.ArgumentParser(
        description='Check license compliance against allowlist'
    )

    parser.add_argument(
        '--licenses',
        required=True,
        help='Path to licenses JSON file'
    )

    parser.add_argument(
        '--allowlist',
        required=True,
        help='Path to license allowlist file'
    )

    parser.add_argument(
        '--report',
        default='license-compliance.json',
        help='Output report path'
    )

    args = parser.parse_args()

    # Load licenses
    with open(args.licenses) as f:
        licenses_data = json.load(f)

    # Load allowlist
    allowlist = load_allowlist(args.allowlist)

    # Check compliance
    result = check_licenses(licenses_data, allowlist)

    # Write report
    with open(args.report, 'w') as f:
        json.dump(result, f, indent=2)

    # Print summary
    print("=" * 70)
    print("License Compliance Report")
    print("=" * 70)
    print()
    print(f"Total packages: {result['total_packages']}")
    print(f"Approved: {result['approved']}")
    print(f"Warnings: {result['warnings']}")
    print(f"Violations: {result['violations']}")
    print()

    if result['violations'] > 0:
        print("VIOLATIONS:")
        for v in result['violation_packages']:
            print(f"  ❌ {v['package']} ({v['version']}) - {v['license']}")
        print()

    if result['warnings'] > 0:
        print("WARNINGS:")
        for w in result['warning_packages']:
            print(f"  ⚠️  {w['package']} ({w['version']}) - {w['license']}")
        print()

    print("=" * 70)
    print(f"Status: {'✅ PASSED' if result['passed'] else '❌ FAILED'}")
    print("=" * 70)

    # Exit with error if violations found
    sys.exit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
