# Contributing to Soundlab + D-ASE

Thank you for your interest in contributing to Soundlab + D-ASE! This document provides guidelines and workflows for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Submitting Changes](#submitting-changes)
- [Coding Standards](#coding-standards)
- [Testing Requirements](#testing-requirements)
- [Documentation](#documentation)
- [Community](#community)

---

## Code of Conduct

We are committed to providing a welcoming and inclusive environment. All contributors are expected to:

- Be respectful and considerate
- Welcome newcomers and help them get started
- Focus on what is best for the community
- Show empathy towards other community members

## Getting Started

### Prerequisites

- Python 3.9+ (3.11+ recommended)
- Git
- FFTW3 library (for D-ASE engine)
- C++ compiler with AVX2 support (recommended)

### Setting Up Your Development Environment

1. **Fork the repository** on GitHub

2. **Clone your fork:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/soundlab.git
   cd soundlab
   ```

3. **Add upstream remote:**
   ```bash
   git remote add upstream https://github.com/soundlab/phi-matrix.git
   ```

4. **Create a virtual environment:**
   ```bash
   make venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

5. **Install dependencies:**
   ```bash
   make install-dev
   ```

6. **Build the C++ extension:**
   ```bash
   make build-ext
   ```

7. **Run tests to verify setup:**
   ```bash
   make test
   ```

---

## Development Workflow

### Branching Strategy

We use a feature branch workflow:

- **`master`**: Stable release branch
- **`develop`**: Active development (not currently used, we work directly on master)
- **`feature/XXX-description`**: New features (e.g., `feature/026-postrelease-maintenance`)
- **`fix/issue-number-description`**: Bug fixes (e.g., `fix/123-latency-regression`)
- **`docs/description`**: Documentation updates

### Creating a Feature Branch

```bash
# Update your local repository
git fetch upstream
git checkout master
git merge upstream/master

# Create a feature branch
git checkout -b feature/027-my-feature
```

### Making Changes

1. **Make your changes** in your feature branch

2. **Follow coding standards** (see below)

3. **Add tests** for new functionality

4. **Run tests locally:**
   ```bash
   make test
   make regression  # Check for regressions
   ```

5. **Run code quality checks:**
   ```bash
   make quality     # Linting, formatting, type checking
   ```

6. **Update documentation** as needed

### Keeping Your Branch Up to Date

```bash
# Fetch and merge upstream changes
git fetch upstream
git checkout your-feature-branch
git merge upstream/master

# Or rebase (if you prefer)
git rebase upstream/master
```

---

## Submitting Changes

### Commit Message Guidelines

We follow the Conventional Commits specification:

**Format:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(phi-matrix): add AVX-512 optimization for Φ-depth calculation

Implement AVX-512 SIMD instructions to accelerate Φ-matrix computation.
Results in 25% latency reduction on supported CPUs.

Closes #42
```

```
fix(api): correct websocket disconnect handling

Previously, disconnects caused memory leaks. Now properly cleanup
resources on disconnect.

Fixes #123
```

### Sign-Off Requirement

All commits must include a "Signed-off-by" line to certify that you have the right to submit the contribution under the project's license (Developer Certificate of Origin).

**Add sign-off automatically:**
```bash
git commit -s -m "feat: add new feature"
```

**Manual sign-off:**
```
feat: add new feature

Signed-off-by: Your Name <your.email@example.com>
```

### Creating a Pull Request

1. **Push your branch:**
   ```bash
   git push origin feature/027-my-feature
   ```

2. **Open a Pull Request** on GitHub

3. **Fill out the PR template** with:
   - Description of changes
   - Related issue numbers
   - Testing performed
   - Screenshots (if UI changes)

4. **Ensure CI passes:**
   - All tests pass
   - Code quality checks pass
   - No regressions detected

5. **Request review** from maintainers

### Pull Request Review Process

1. **Automated checks** run (CI, tests, linting)
2. **Code review** by at least one maintainer
3. **Address feedback** by pushing additional commits
4. **Approval** by maintainer
5. **Merge** (usually squash and merge)

---

## Coding Standards

### Python Style Guide

- **PEP 8** compliance (enforced by `flake8`)
- **Black** code formatting (line length: 120)
- **Type hints** for function signatures
- **Docstrings** for all public APIs (Google style)

**Example:**
```python
def compute_phi_depth(
    signal: np.ndarray,
    sample_rate: int = 48000,
    threshold: float = 0.3
) -> float:
    """
    Compute the Φ-depth metric for an audio signal.

    Args:
        signal: Input audio signal as numpy array
        sample_rate: Sample rate in Hz (default: 48000)
        threshold: Detection threshold (default: 0.3)

    Returns:
        Φ-depth value between 0.0 and 1.0

    Raises:
        ValueError: If signal is empty or sample_rate is invalid
    """
    # Implementation...
    pass
```

### Code Quality Tools

Run before submitting:

```bash
make format       # Auto-format with Black
make lint         # Check with flake8
make typecheck    # Check types with mypy
make quality      # Run all quality checks
```

### C++ Style Guide (D-ASE Engine)

- Follow **Google C++ Style Guide**
- Use **modern C++17** features
- **SIMD optimizations** for performance-critical code
- **Comments** for complex algorithms

---

## Testing Requirements

### Test Coverage

- **Minimum 80% code coverage** for new code
- **100% coverage** for critical paths (Φ-matrix, D-ASE engine)
- **Regression tests** for bug fixes

### Writing Tests

Use `pytest` for all tests:

```python
import pytest
from phi_matrix import compute_phi_depth

def test_phi_depth_basic():
    """Test Φ-depth computation with basic signal."""
    signal = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 48000))
    result = compute_phi_depth(signal)
    assert 0.0 <= result <= 1.0

def test_phi_depth_empty_signal():
    """Test Φ-depth with empty signal raises error."""
    with pytest.raises(ValueError):
        compute_phi_depth(np.array([]))
```

### Running Tests

```bash
# All tests
make test

# Unit tests only
make test-unit

# Integration tests
make test-integration

# With coverage
make test-cov

# Regression tests
make regression
```

### Performance Tests

For performance-critical changes:

```bash
make test-perf      # Run performance benchmarks
make benchmarks     # Compare against baseline
```

---

## Documentation

### Documentation Requirements

- **Docstrings** for all public APIs
- **README updates** for new features
- **CHANGELOG entries** for all changes
- **Architecture docs** for significant changes

### Documentation Style

- Use **Markdown** for all docs
- Include **code examples** where appropriate
- Add **diagrams** for complex concepts (use Mermaid or ASCII art)
- Link to **related issues** and **pull requests**

### Building Documentation

```bash
make docs           # Generate documentation
```

### Updating the Roadmap

When adding features related to the roadmap:

1. Check [docs/roadmap_v1.1.md](docs/roadmap_v1.1.md)
2. Update status and link your PR
3. Add completion notes

---

## Applying Patches and Diffs

### Using Patch Files

We support patch/diff-based contributions:

```bash
# Apply a patch
make apply-patch diff=path/to/feature.patch

# Apply with custom strip level
make apply-patch diff=feature.patch strip=0

# Dry run (test without applying)
make apply-patch diff=feature.patch dry_run=1

# Reverse a patch
make apply-patch diff=feature.patch reverse=1
```

### Creating Patches

```bash
# Create a patch from uncommitted changes
git diff > my-changes.patch

# Create a patch from commits
git format-patch HEAD~3  # Last 3 commits

# Create a patch for a specific branch
git diff master..feature/my-feature > feature.patch
```

---

## Deprecation Policy

When deprecating APIs:

1. **Use the deprecation decorator:**
   ```python
   from server.deprecation import deprecated

   @deprecated(
       deprecated_in="1.1.0",
       remove_in="2.0.0",
       reason="Replaced by new_function",
       alternative="new_function()"
   )
   def old_function():
       pass
   ```

2. **Update documentation** with deprecation notice

3. **Add to deprecation report:**
   ```bash
   make deprecation-report
   ```

4. **Follow semantic versioning:**
   - Deprecate in minor version (e.g., 1.1.0)
   - Remove in next major version (e.g., 2.0.0)

---

## Community

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and community discussion
- **Pull Requests**: Code contributions

### Getting Help

- Check the [documentation](docs/)
- Search [existing issues](https://github.com/soundlab/phi-matrix/issues)
- Ask in [GitHub Discussions](https://github.com/soundlab/phi-matrix/discussions)
- Review the [roadmap](docs/roadmap_v1.1.md)

### Office Hours

We hold community office hours:
- **When**: Bi-weekly (schedule in Discussions)
- **Where**: GitHub Discussions or video call
- **What**: Q&A, pair programming, feature planning

---

## Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):
- **MAJOR**: Incompatible API changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

See [docs/versioning_policy.md](docs/versioning_policy.md) for details.

### Release Cycle

- **Minor releases** (1.x.0): Every 3-4 months
- **Patch releases** (1.1.x): As needed for critical fixes
- **Major releases** (x.0.0): Once per year (with LTS support)

---

## License

By contributing to Soundlab + D-ASE, you agree that your contributions will be licensed under the MIT License.

---

## Thank You!

Your contributions make Soundlab + D-ASE better for everyone. We appreciate your time and effort!

For questions or clarifications, don't hesitate to:
- Open an issue
- Start a discussion
- Contact the maintainers

Happy coding! 🎵
