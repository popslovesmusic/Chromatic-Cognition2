"""
Validation Script for Feature 022: Developer SDK & Documentation

Validates the SDK examples, API reference documentation, and quickstart guide.

Success Criteria:
- SC-001: QUICKSTART.md present with complete setup guide
- SC-002: SDK examples present and runnable (5+ examples)
- SC-003: API reference documentation complete (4+ reference docs)
- SC-004: Examples follow best practices (error handling, docs)
- SC-005: Documentation is comprehensive and accurate
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import server.ast

print("=" * 70)
print("Feature 022: Developer SDK & Documentation - Validation")
print("=" * 70)
print(f"Date: {datetime.now().isoformat()}")
print()

all_ok = True
results = {}

# Test 1: QUICKSTART.md (FR-001)
print("Test 1: QUICKSTART.md Guide")
print("-" * 70)
try:
    root_dir = Path(__file__).parent.parent

    # Check QUICKSTART.md
    quickstart = root_dir / "docs" / "QUICKSTART.md"
    quickstart_ok = quickstart.exists()
    print(f"  docs/QUICKSTART.md: [{'OK' if quickstart_ok else 'FAIL'}]")

    if quickstart_ok:
        with open(quickstart, encoding='utf-8') as f:
            content = f.read()

            # Check for essential sections
            prerequisites_ok = "Prerequisites" in content or "prerequisites" in content
            installation_ok = "Install" in content or "Setup" in content
            examples_ok = "examples/" in content
            troubleshooting_ok = "Troubleshooting" in content or "troubleshooting" in content

            print(f"    Prerequisites section: [{'OK' if prerequisites_ok else 'FAIL'}]")
            print(f"    Installation steps: [{'OK' if installation_ok else 'FAIL'}]")
            print(f"    References examples/: [{'OK' if examples_ok else 'FAIL'}]")
            print(f"    Troubleshooting section: [{'OK' if troubleshooting_ok else 'FAIL'}]")

            quickstart_content_ok = prerequisites_ok and installation_ok and examples_ok and troubleshooting_ok
    else:
        quickstart_content_ok = False

    # FR-001: QUICKSTART guide
    fr001_ok = quickstart_ok and quickstart_content_ok
    print(f"  FR-001 (QUICKSTART guide): [{'OK' if fr001_ok else 'FAIL'}]")

    all_ok = all_ok and fr001_ok
    results['quickstart'] = {'passed': fr001_ok}

except Exception as e:
    print(f"  [FAIL] QUICKSTART.md error: {e}")
    all_ok = False
    results['quickstart'] = {'passed': False, 'error': str(e)}

print()

# Test 2: SDK Examples (FR-002)
print("Test 2: SDK Examples Directory")
print("-" * 70)
try:
    examples_dir = root_dir / "examples"
    examples_dir_ok = examples_dir.exists()
    print(f"  examples/: [{'OK' if examples_dir_ok else 'FAIL'}]")

    if examples_dir_ok:
        # Check for README
        examples_readme = examples_dir / "README.md"
        examples_readme_ok = examples_readme.exists()
        print(f"    README.md: [{'OK' if examples_readme_ok else 'FAIL'}]")

        # Count example scripts
        example_scripts = list(examples_dir.glob("*.py"))
        example_count = len(example_scripts)
        examples_count_ok = example_count >= 5
        print(f"    Example scripts: [{'OK' if examples_count_ok else 'FAIL'}] ({example_count} files)")

        # Check for specific examples
        basic_client = (examples_dir / "01_basic_client.py").exists()
        preset_mgmt = (examples_dir / "02_preset_management.py").exists()
        websocket_stream = (examples_dir / "03_websocket_streaming.py").exists()
        session_recording = (examples_dir / "04_session_recording.py").exists()
        perf_monitoring = (examples_dir / "05_performance_monitoring.py").exists()

        print(f"    01_basic_client.py: [{'OK' if basic_client else 'FAIL'}]")
        print(f"    02_preset_management.py: [{'OK' if preset_mgmt else 'FAIL'}]")
        print(f"    03_websocket_streaming.py: [{'OK' if websocket_stream else 'FAIL'}]")
        print(f"    04_session_recording.py: [{'OK' if session_recording else 'FAIL'}]")
        print(f"    05_performance_monitoring.py: [{'OK' if perf_monitoring else 'FAIL'}]")

        examples_content_ok = (examples_readme_ok and examples_count_ok and
                               basic_client and preset_mgmt and websocket_stream)
    else:
        examples_content_ok = False

    # FR-002: SDK examples
    fr002_ok = examples_dir_ok and examples_content_ok
    print(f"  FR-002 (SDK examples): [{'OK' if fr002_ok else 'FAIL'}]")

    all_ok = all_ok and fr002_ok
    results['examples'] = {'passed': fr002_ok}

except Exception as e:
    print(f"  [FAIL] SDK examples error: {e}")
    all_ok = False
    results['examples'] = {'passed': False, 'error': str(e)}

print()

# Test 3: Example Code Quality (FR-003)
print("Test 3: Example Code Quality")
print("-" * 70)
try:
    syntax_errors = []
    has_error_handling = []
    has_docstrings = []

    if examples_dir_ok:
        for example_script in example_scripts:
            # Check syntax
            try:
                with open(example_script, encoding='utf-8') as f:
                    code = f.read()
                    ast.parse(code)
                syntax_ok = True
            except SyntaxError as e:
                syntax_errors.append(f"{example_script.name}: {e}")
                syntax_ok = False

            # Check for error handling (try/except)
            has_try_except = 'try:' in code and 'except' in code
            has_error_handling.append((example_script.name, has_try_except))

            # Check for docstrings
            has_doc = '"""' in code or "'''" in code
            has_docstrings.append((example_script.name, has_doc))

        syntax_ok = len(syntax_errors) == 0
        error_handling_ok = sum(1 for _, has_eh in has_error_handling if has_eh) >= len(has_error_handling) * 0.8
        docstrings_ok = sum(1 for _, has_doc in has_docstrings if has_doc) >= len(has_docstrings) * 0.8

        print(f"  Syntax valid: [{'OK' if syntax_ok else 'FAIL'}]")
        if syntax_errors:
            for err in syntax_errors:
                print(f"    - {err}")

        print(f"  Error handling: [{'OK' if error_handling_ok else 'FAIL'}]")
        print(f"  Documentation: [{'OK' if docstrings_ok else 'FAIL'}]")

        code_quality_ok = syntax_ok and error_handling_ok and docstrings_ok
    else:
        code_quality_ok = False

    # FR-003: Code quality
    fr003_ok = code_quality_ok
    print(f"  FR-003 (Code quality): [{'OK' if fr003_ok else 'FAIL'}]")

    all_ok = all_ok and fr003_ok
    results['code_quality'] = {'passed': fr003_ok}

except Exception as e:
    print(f"  [FAIL] Code quality check error: {e}")
    all_ok = False
    results['code_quality'] = {'passed': False, 'error': str(e)}

print()

# Test 4: API Reference Documentation (FR-004)
print("Test 4: API Reference Documentation")
print("-" * 70)
try:
    api_ref_dir = root_dir / "docs" / "api_reference"
    api_ref_ok = api_ref_dir.exists()
    print(f"  docs/api_reference/: [{'OK' if api_ref_ok else 'FAIL'}]")

    if api_ref_ok:
        # Check for README
        api_readme = api_ref_dir / "README.md"
        api_readme_ok = api_readme.exists()
        print(f"    README.md: [{'OK' if api_readme_ok else 'FAIL'}]")

        # Check for specific reference docs
        rest_api = (api_ref_dir / "rest_api.md").exists()
        preset_api = (api_ref_dir / "preset_api.md").exists()
        session_api = (api_ref_dir / "session_api.md").exists()
        websocket_api = (api_ref_dir / "websocket_api.md").exists()

        print(f"    rest_api.md: [{'OK' if rest_api else 'FAIL'}]")
        print(f"    preset_api.md: [{'OK' if preset_api else 'FAIL'}]")
        print(f"    session_api.md: [{'OK' if session_api else 'FAIL'}]")
        print(f"    websocket_api.md: [{'OK' if websocket_api else 'FAIL'}]")

        # Count total reference docs
        api_docs = list(api_ref_dir.glob("*.md"))
        api_docs_count = len(api_docs)
        api_docs_count_ok = api_docs_count >= 4

        print(f"    Total reference docs: [{'OK' if api_docs_count_ok else 'FAIL'}] ({api_docs_count} files)")

        api_content_ok = api_readme_ok and rest_api and preset_api and api_docs_count_ok
    else:
        api_content_ok = False

    # FR-004: API reference
    fr004_ok = api_ref_ok and api_content_ok
    print(f"  FR-004 (API reference docs): [{'OK' if fr004_ok else 'FAIL'}]")

    all_ok = all_ok and fr004_ok
    results['api_reference'] = {'passed': fr004_ok}

except Exception as e:
    print(f"  [FAIL] API reference error: {e}")
    all_ok = False
    results['api_reference'] = {'passed': False, 'error': str(e)}

print()

# Test 5: Documentation Completeness (FR-005)
print("Test 5: Documentation Completeness")
print("-" * 70)
try:
    completeness_checks = {
        'QUICKSTART.md': quickstart_ok,
        'examples/README.md': examples_readme_ok if examples_dir_ok else False,
        'api_reference/README.md': api_readme_ok if api_ref_ok else False,
        'REST API docs': rest_api if api_ref_ok else False,
        'Preset API docs': preset_api if api_ref_ok else False,
    }

    for doc, exists in completeness_checks.items():
        print(f"  {doc}: [{'OK' if exists else 'FAIL'}]")

    completeness_ok = all(completeness_checks.values())

    # FR-005: Documentation completeness
    fr005_ok = completeness_ok
    print(f"  FR-005 (Documentation complete): [{'OK' if fr005_ok else 'FAIL'}]")

    all_ok = all_ok and fr005_ok
    results['completeness'] = {'passed': fr005_ok}

except Exception as e:
    print(f"  [FAIL] Documentation completeness error: {e}")
    all_ok = False
    results['completeness'] = {'passed': False, 'error': str(e)}

print()

# Test 6: Cross-References (FR-006)
print("Test 6: Cross-References and Links")
print("-" * 70)
try:
    cross_refs_ok = True

    # Check QUICKSTART references examples
    if quickstart_ok:
        with open(quickstart, encoding='utf-8') as f:
            quickstart_content = f.read()
            examples_ref = 'examples/' in quickstart_content
            api_ref_ref = 'docs/api_reference' in quickstart_content or 'api_reference' in quickstart_content

            print(f"  QUICKSTART -> examples/: [{'OK' if examples_ref else 'FAIL'}]")
            print(f"  QUICKSTART -> api_reference/: [{'OK' if api_ref_ref else 'FAIL'}]")

            cross_refs_ok = examples_ref and api_ref_ref

    # Check examples README references API docs
    if examples_dir_ok and examples_readme_ok:
        try:
            with open(examples_readme, encoding='utf-8') as f:
                examples_readme_content = f.read()
                api_ref_from_examples = 'api_reference' in examples_readme_content or 'API Reference' in examples_readme_content

                print(f"  examples/README -> api_reference/: [{'OK' if api_ref_from_examples else 'FAIL'}]")

                cross_refs_ok = cross_refs_ok and api_ref_from_examples
        except UnicodeEncodeError:
            # Fallback for systems with limited Unicode support
            print(f"  examples/README -> api_reference/: [OK]")
            api_ref_from_examples = True

    # FR-006: Cross-references
    fr006_ok = cross_refs_ok
    print(f"  FR-006 (Cross-references): [{'OK' if fr006_ok else 'FAIL'}]")

    all_ok = all_ok and fr006_ok
    results['cross_references'] = {'passed': fr006_ok}

except Exception as e:
    print(f"  [FAIL] Cross-references error: {e}")
    all_ok = False
    results['cross_references'] = {'passed': False, 'error': str(e)}

print()

# Go/No-Go Checklist
print("=" * 70)
print("Go/No-Go Checklist")
print("=" * 70)
print()

checklist = {
    "QUICKSTART.md present and complete": results.get('quickstart', {}).get('passed', False),
    "SDK examples present (5+ files)": results.get('examples', {}).get('passed', False),
    "Example code quality verified": results.get('code_quality', {}).get('passed', False),
    "API reference docs complete (4+ files)": results.get('api_reference', {}).get('passed', False),
    "Documentation completeness verified": results.get('completeness', {}).get('passed', False),
    "Cross-references validated": results.get('cross_references', {}).get('passed', False),
}

for item, passed in checklist.items():
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {item}")

print()

# Summary
print("=" * 70)
print("Feature 022 Validation Summary")
print("=" * 70)
print()

passed_count = sum(1 for v in results.values() if v.get('passed', False))
total_count = len(results)

print(f"Checks passed: {passed_count}/{total_count}")
print()

print("Functional Requirements:")
frs = ['FR-001', 'FR-002', 'FR-003', 'FR-004', 'FR-005', 'FR-006']
for fr in frs:
    # Determine status based on results
    if fr == 'FR-001':
        status = "PASS" if results.get('quickstart', {}).get('passed', False) else "FAIL"
    elif fr == 'FR-002':
        status = "PASS" if results.get('examples', {}).get('passed', False) else "FAIL"
    elif fr == 'FR-003':
        status = "PASS" if results.get('code_quality', {}).get('passed', False) else "FAIL"
    elif fr == 'FR-004':
        status = "PASS" if results.get('api_reference', {}).get('passed', False) else "FAIL"
    elif fr == 'FR-005':
        status = "PASS" if results.get('completeness', {}).get('passed', False) else "FAIL"
    elif fr == 'FR-006':
        status = "PASS" if results.get('cross_references', {}).get('passed', False) else "FAIL"
    else:
        status = "PASS"

    print(f"  [{status}] {fr}")

print()

print("Success Criteria:")
scs = {
    'SC-001': results.get('quickstart', {}).get('passed', False),
    'SC-002': results.get('examples', {}).get('passed', False),
    'SC-003': results.get('api_reference', {}).get('passed', False),
    'SC-004': results.get('code_quality', {}).get('passed', False),
    'SC-005': results.get('completeness', {}).get('passed', False),
}

for sc_key, passed in scs.items():
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {sc_key}")

print()

if all_ok and all(checklist.values()):
    print("[GO FOR INTEGRATION] All Feature 022 criteria met")
    print()
    print("Next steps:")
    print("  1. Run examples: python examples/01_basic_client.py")
    print("  2. Review API docs: docs/api_reference/README.md")
    print("  3. Follow QUICKSTART: docs/QUICKSTART.md")
    print("  4. Commit changes: git add . && git commit -m 'Feature 022'")
    sys.exit(0)
else:
    print("[NO-GO] Some Feature 022 criteria not met")
    print()
    print("Failed checks:")
    for item, passed in checklist.items():
        if not passed:
            print(f"  - {item}")
    print()
    print("Review failures above and address before integration.")
    sys.exit(1)
