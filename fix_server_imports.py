#!/usr/bin/env python3
"""
Fix imports in server/ directory files
Updates imports from server modules to use relative imports (with dot prefix)
"""

import re
from pathlib import Path

# Standard library modules that should NOT be prefixed
STDLIB_MODULES = {
    'sys', 'os', 'time', 'json', 'asyncio', 'argparse', 'math', 'copy',
    'collections', 'datetime', 'pathlib', 'typing', 'statistics', 'threading',
    'unittest', 'pytest', 'numpy', 'scipy', 'websockets', 'fastapi', 're',
    'traceback', 'queue', 'dataclasses', 'enum', 'abc', 'functools', 'itertools'
}

def is_server_module_import(module_name: str, all_server_modules: set) -> bool:
    """Check if module_name is a server module"""
    return module_name in all_server_modules


def fix_imports_in_file(filepath: Path, all_server_modules: set) -> int:
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

            # Check if it's a server module (not stdlib)
            if module_name not in STDLIB_MODULES and is_server_module_import(module_name, all_server_modules):
                # Add relative import prefix
                new_line = line.replace(f'from {module_name} import',
                                       f'from .{module_name} import')
                new_lines.append(new_line)
                changes += 1
                continue

        # Match: import module_name
        match = re.match(r'^import\s+([a-z_][a-z0-9_]*)\s*$', line)

        if match:
            module_name = match.group(1)

            # Check if it's a server module (not stdlib)
            if module_name not in STDLIB_MODULES and is_server_module_import(module_name, all_server_modules):
                # Add relative import
                new_line = line.replace(f'import {module_name}',
                                       f'from . import {module_name}')
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
            return changes
        except Exception as e:
            print(f"  ERROR writing {filepath}: {e}")
            return 0

    return changes


def main():
    """Process all server files"""
    print("=" * 60)
    print("Fixing Server Module Imports")
    print("=" * 60)

    repo_root = Path(__file__).parent
    server_dir = repo_root / "server"

    if not server_dir.exists():
        print(f"ERROR: {server_dir} not found")
        return 1

    # Get all server module names (without .py extension)
    all_py_files = list(server_dir.glob('*.py'))
    all_server_modules = {f.stem for f in all_py_files if f.stem != '__init__'}

    print(f"\nFound {len(all_server_modules)} server modules")
    print(f"Processing {len(all_py_files)} Python files...\n")

    total_files = 0
    total_changes = 0

    for py_file in all_py_files:
        if py_file.name == '__init__.py':
            continue

        changes = fix_imports_in_file(py_file, all_server_modules)
        if changes > 0:
            print(f"  {py_file.name}: {changes} imports fixed")
            total_files += 1
            total_changes += changes

    print("\n" + "=" * 60)
    print(f"Summary: {total_changes} imports fixed in {total_files} files")
    print("=" * 60)

    return 0


if __name__ == '__main__':
    exit(main())
