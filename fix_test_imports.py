#!/usr/bin/env python3
"""
Fix imports in moved test files
Updates imports from server modules to use 'server.' prefix
"""

import re
from pathlib import Path

# Standard library modules that should NOT be prefixed
STDLIB_MODULES = {
    'sys', 'os', 'time', 'json', 'asyncio', 'argparse', 'math',
    'collections', 'datetime', 'pathlib', 'typing', 'statistics',
    'unittest', 'pytest', 'numpy', 'scipy', 'websockets', 'fastapi'
}

# Directories to process
TEST_DIRS = [
    'tests/unit',
    'tests/integration',
    'tests/hardware',
    'tests/perf',
    'tests/validation'
]

def fix_imports_in_file(filepath: Path) -> int:
    """
    Fix imports in a single file

    Returns:
        Number of lines changed
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"  ERROR reading {filepath}: {e}")
        return 0

    new_lines = []
    changes = 0

    for line in lines:
        # Match: from module_name import ...
        match = re.match(r'^from\s+([a-z_][a-z0-9_]*)\s+import\s+', line)

        if match:
            module_name = match.group(1)

            # Check if it's NOT a standard library module
            if module_name not in STDLIB_MODULES:
                # Add 'server.' prefix
                new_line = line.replace(f'from {module_name} import',
                                       f'from server.{module_name} import')
                new_lines.append(new_line)
                changes += 1
                continue

        # Match: import module_name
        match = re.match(r'^import\s+([a-z_][a-z0-9_]*)\s*$', line)

        if match:
            module_name = match.group(1)

            # Check if it's NOT a standard library module
            if module_name not in STDLIB_MODULES:
                # Add 'server.' prefix
                new_line = line.replace(f'import {module_name}',
                                       f'import server.{module_name}')
                new_lines.append(new_line)
                changes += 1
                continue

        # No change needed
        new_lines.append(line)

    if changes > 0:
        # Write back
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            print(f"  ✓ {filepath.name}: {changes} imports fixed")
        except Exception as e:
            print(f"  ERROR writing {filepath}: {e}")
            return 0

    return changes


def main():
    """Process all test files"""
    print("=" * 60)
    print("Fixing Test File Imports")
    print("=" * 60)

    total_files = 0
    total_changes = 0

    repo_root = Path(__file__).parent

    for test_dir in TEST_DIRS:
        dir_path = repo_root / test_dir

        if not dir_path.exists():
            print(f"\n⚠️  Directory not found: {test_dir}")
            continue

        print(f"\n{test_dir}/:")

        # Process all .py files except __init__.py
        py_files = [f for f in dir_path.glob('*.py') if f.name != '__init__.py']

        if not py_files:
            print("  (no test files)")
            continue

        for py_file in py_files:
            changes = fix_imports_in_file(py_file)
            if changes > 0:
                total_files += 1
                total_changes += changes

    print("\n" + "=" * 60)
    print(f"Summary: {total_changes} imports fixed in {total_files} files")
    print("=" * 60)


if __name__ == '__main__':
    main()
