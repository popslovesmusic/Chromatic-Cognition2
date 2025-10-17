# Versioning Policy

**Document Version:** 1.0
**Last Updated:** 2025-10-17
**Status:** Active

---

## Overview

This document defines the versioning policy for Soundlab + D-ASE, including version number semantics, release cadence, deprecation policy, and long-term support (LTS) strategy.

## Semantic Versioning

Soundlab + D-ASE follows [Semantic Versioning 2.0.0](https://semver.org/) (SemVer):

```
MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
```

### Version Number Components

#### MAJOR Version (X.0.0)

Incremented when making **incompatible API changes**:

- Breaking changes to public APIs
- Removal of deprecated features
- Fundamental architecture changes
- Changes that require user code modifications

**Examples:**
- `1.0.0` → `2.0.0`: Removed deprecated WebSocket endpoints
- `2.0.0` → `3.0.0`: Changed Φ-matrix computation algorithm (breaking output format)

**Release Frequency:** Once per year (with LTS support)

#### MINOR Version (X.Y.0)

Incremented when adding **backward-compatible functionality**:

- New features
- New APIs
- Performance improvements (non-breaking)
- Deprecated features (marked but not removed)

**Examples:**
- `1.0.0` → `1.1.0`: Added plugin system
- `1.1.0` → `1.2.0`: Added multi-channel audio support

**Release Frequency:** Every 3-4 months

#### PATCH Version (X.Y.Z)

Incremented for **backward-compatible bug fixes**:

- Bug fixes
- Security patches
- Documentation updates
- Minor performance improvements

**Examples:**
- `1.1.0` → `1.1.1`: Fixed memory leak in WebSocket handler
- `1.1.1` → `1.1.2`: Patched security vulnerability CVE-2025-XXXXX

**Release Frequency:** As needed (typically monthly or for critical fixes)

### Pre-release Versions

Pre-release versions are denoted by appending a hyphen and identifiers:

- **Alpha** (`-alpha.N`): Early development, unstable
- **Beta** (`-beta.N`): Feature complete, testing phase
- **Release Candidate** (`-rc.N`): Final testing before release

**Examples:**
- `1.1.0-alpha.1`: First alpha of v1.1
- `1.1.0-beta.2`: Second beta of v1.1
- `1.1.0-rc.1`: First release candidate

### Build Metadata

Build metadata may be appended with a plus sign:

```
1.1.0+20251017.abc1234
```

Build metadata **does not affect** version precedence.

---

## Release Cadence

### Regular Release Schedule

| Release Type | Frequency | Typical Month | Support Duration |
|--------------|-----------|---------------|------------------|
| Major (X.0.0) | Yearly | January | 3 years (LTS) |
| Minor (X.Y.0) | Quarterly | Jan, Apr, Jul, Oct | 6 months |
| Patch (X.Y.Z) | As needed | Any | Until next minor |

### Release Timeline Example

```
2025-01  v1.0.0    Major release (LTS)
2025-04  v1.1.0    Minor release (plugin system)
2025-05  v1.1.1    Patch (bug fixes)
2025-07  v1.2.0    Minor release (multi-channel)
2025-08  v1.2.1    Patch (security fix)
2025-10  v1.3.0    Minor release (performance)
2026-01  v2.0.0    Major release (breaking changes, LTS)
```

---

## Long-Term Support (LTS)

### LTS Policy

- **LTS versions** are designated major releases (X.0.0)
- **Support duration**: 3 years from release date
- **Maintenance**: Security patches and critical bug fixes only

### Current LTS Versions

| Version | Release Date | End of Support | Status |
|---------|-------------|----------------|--------|
| v1.0.0 | 2025-10-17 | 2028-10-17 | Active |

### LTS Support Levels

#### Full Support (First 12 months)
- Security patches
- Critical bug fixes
- Performance regression fixes
- Documentation updates

#### Maintenance Support (Months 13-24)
- Security patches
- Critical bug fixes only

#### Extended Support (Months 25-36)
- Security patches only (CVE fixes)

---

## Deprecation Policy

### Deprecation Process

When deprecating features or APIs:

1. **Announcement**: Deprecation announced in release notes
2. **Warning Period**: Feature marked as deprecated (minimum 1 minor version)
3. **Removal**: Feature removed in next major version

### Deprecation Timeline

```
v1.0.0: Feature introduced
v1.2.0: Feature deprecated (warnings issued)
v1.3.0: Deprecation warnings continue
v2.0.0: Feature removed
```

### Marking Deprecations

Use the deprecation decorator:

```python
from server.deprecation import deprecated

@deprecated(
    deprecated_in="1.2.0",
    remove_in="2.0.0",
    reason="Replaced by optimized implementation",
    alternative="new_feature()"
)
def old_feature():
    pass
```

### Deprecation Warnings

- **Console warnings**: Issued at runtime
- **Documentation**: Marked in API docs
- **CHANGELOG**: Listed in deprecation section
- **Migration guide**: Provided for replacements

---

## Compatibility Guarantees

### Backward Compatibility

- **PATCH versions**: 100% backward compatible
- **MINOR versions**: 100% backward compatible
- **MAJOR versions**: May break compatibility

### Forward Compatibility

- **Not guaranteed**: Older versions may not work with data from newer versions
- **Best effort**: Format versioning where possible

### API Stability

#### Stable APIs

APIs marked as stable will:
- Not change behavior in minor/patch versions
- Follow deprecation policy for removal
- Maintain signature compatibility

#### Experimental APIs

APIs marked as experimental:
- May change without deprecation warnings
- Not subject to SemVer guarantees
- Clearly marked in documentation

**Marking experimental APIs:**

```python
def experimental_feature():
    """
    Experimental feature - may change in future versions.

    .. warning::
       This is an experimental API and may change without notice.
    """
    pass
```

---

## Version Support Matrix

### Python Version Support

| Soundlab Version | Python 3.9 | Python 3.10 | Python 3.11 | Python 3.12 |
|------------------|------------|-------------|-------------|-------------|
| v1.0.x | ✓ | ✓ | ✓ | ✓ |
| v1.1.x | ✓ | ✓ | ✓ | ✓ |
| v2.0.x (planned) | ✗ | ✓ | ✓ | ✓ |

### Dependency Support

- **FFTW3**: 3.3.8+
- **NumPy**: 1.24+
- **FastAPI**: 0.100+
- **Pybind11**: 2.11+

Dependencies updated conservatively, following their own stability policies.

---

## Breaking Change Policy

### What Constitutes a Breaking Change

- Removing a public API or function
- Changing function signatures (parameters, return types)
- Changing default behavior that affects outputs
- Removing or renaming configuration options
- Changes to data formats (breaking deserialization)

### What is NOT a Breaking Change

- Adding new optional parameters (with defaults)
- Adding new APIs or functions
- Deprecating features (as long as they still work)
- Internal implementation changes
- Performance improvements
- Bug fixes (even if behavior changes)

### Announcing Breaking Changes

Breaking changes must be:

1. **Documented** in CHANGELOG with `BREAKING:` prefix
2. **Announced** in release notes prominently
3. **Included** in migration guide
4. **Discussed** in community forums before major release

---

## Release Process

### Release Checklist

- [ ] All tests pass (100% pass rate)
- [ ] Regression tests pass (< 5% performance variance)
- [ ] Documentation updated
- [ ] CHANGELOG updated
- [ ] Version numbers incremented
- [ ] Git tag created
- [ ] Artifacts signed
- [ ] GitHub release created
- [ ] PyPI package published
- [ ] Docker images pushed

### Version Tagging

Git tags follow the format: `vMAJOR.MINOR.PATCH`

```bash
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin v1.1.0
```

---

## Version Detection

### Runtime Version Query

```python
import dase_engine

print(dase_engine.__version__)  # "1.0.0"
```

### Programmatic Checks

```python
from packaging import version

if version.parse(dase_engine.__version__) >= version.parse("1.1.0"):
    # Use new feature
    use_new_api()
else:
    # Use old feature
    use_old_api()
```

---

## Examples

### Scenario 1: Adding a New Feature

**Before:** v1.0.0
**Change:** Add plugin system
**After:** v1.1.0 (MINOR bump)

**Rationale:** New functionality, backward compatible

### Scenario 2: Bug Fix

**Before:** v1.1.0
**Change:** Fix memory leak
**After:** v1.1.1 (PATCH bump)

**Rationale:** Bug fix, no API changes

### Scenario 3: Breaking Change

**Before:** v1.3.0
**Change:** Remove deprecated WebSocket API
**After:** v2.0.0 (MAJOR bump)

**Rationale:** Incompatible change, requires user code updates

### Scenario 4: Security Patch

**Before:** v1.1.2
**Change:** Fix CVE-2025-XXXXX
**After:** v1.1.3 (PATCH bump)
**Also:** v1.0.5 (backport to LTS)

**Rationale:** Critical security fix, backported to LTS

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-10-17 | Initial versioning policy for Feature 026 |

---

## References

- [Semantic Versioning 2.0.0](https://semver.org/)
- [Roadmap v1.1](roadmap_v1.1.md)
- [Contributing Guide](../CONTRIBUTING.md)
- [Deprecation System](../server/deprecation.py)

---

## Questions?

For questions about this policy:
- Open an issue on GitHub
- Discuss in GitHub Discussions
- Contact maintainers

This policy may be updated over time. Check the revision history for changes.
