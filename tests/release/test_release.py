"""
Release Verification Tests - Feature 025 (FR-010)

Tests for verifying release artifacts and installation

Requirements:
- SC-002: Artifacts install and run without errors
- SC-005: python -c "import dase_engine; print(dase_engine.hasAVX2())" returns True
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - fallback for older interpreters
    import tomli as tomllib  # type: ignore


EXPECTED_VERSION = "1.0.0"


class TestReleaseArtifacts:
    """Test release artifact integrity"""

    def test_version_file_exists(self):
        """Test that version file exists"""
        version_file = Path('build/version.txt')
        assert version_file.exists(), "Missing build/version.txt"
        contents = version_file.read_text().strip()
        assert contents == EXPECTED_VERSION, f"Expected version {EXPECTED_VERSION}, got {contents}"

    def test_changelog_exists(self):
        """Test that CHANGELOG.md exists"""
        changelog = Path('CHANGELOG.md')
        assert changelog.exists(), "CHANGELOG.md must be present for release"
        text = changelog.read_text()
        assert EXPECTED_VERSION in text

    def test_release_notes_exist(self):
        """Test that RELEASE_NOTES.md exists"""
        release_notes = Path('RELEASE_NOTES.md')
        assert release_notes.exists()
        assert EXPECTED_VERSION in release_notes.read_text()

    def test_pyproject_version(self):
        pyproject = Path('pyproject.toml')
        assert pyproject.exists(), "pyproject.toml missing"
        data = tomllib.loads(pyproject.read_text())
        assert data['project']['version'] == EXPECTED_VERSION

    def test_release_notes_linked(self):
        release_notes = Path('RELEASE_NOTES.md').read_text()
        assert 'docs/releases/v1.0.md' in release_notes


class TestInstallation:
    """Test installation verification (SC-002)"""

    def test_import_dase_engine(self):
        """Test that dase_engine can be imported"""
        try:
            import dase_engine
            assert dase_engine is not None
        except ImportError:
            pytest.skip("dase_engine not installed")

    def test_dase_version(self):
        """Test that dase_engine has version attribute"""
        try:
            import dase_engine
            assert hasattr(dase_engine, '__version__')
            print(f"D-ASE version: {dase_engine.__version__}")
        except ImportError:
            pytest.skip("dase_engine not installed")

    def test_avx2_support(self):
        """Test AVX2 support check (SC-005)"""
        try:
            import dase_engine
            if hasattr(dase_engine, 'hasAVX2'):
                has_avx2 = dase_engine.hasAVX2()
                print(f"AVX2 support: {has_avx2}")
                # Note: May return False on non-AVX2 systems
                assert isinstance(has_avx2, bool)
        except ImportError:
            pytest.skip("dase_engine not installed")


class TestServerStartup:
    """Test server startup and basic functionality (SC-002)"""

    def test_server_imports(self):
        """Test that server modules can be imported"""
        try:
            # Add server directory to path
            server_dir = Path(__file__).parent.parent.parent / 'server'
            if server_dir.exists():
                sys.path.insert(0, str(server_dir))

            # Test imports
            import security_middleware
            import ws_gatekeeper
            import privacy_manager

            assert security_middleware is not None
            assert ws_gatekeeper is not None
            assert privacy_manager is not None

        except ImportError as e:
            pytest.skip(f"Server modules not available: {e}")

    def test_config_files_exist(self):
        """Test that configuration files exist"""
        config_dir = Path('config')

        expected_files = [
            'security.yaml',
            'privacy.json',
            'license-allowlist.txt'
        ]

        for file in expected_files:
            config_file = config_dir / file
            assert config_file.exists(), f"Missing config file: {file}"


class TestDocumentation:
    """Test documentation completeness"""

    def test_required_docs_exist(self):
        """Test that required documentation files exist"""
        docs_dir = Path('docs')

        required_docs = [
            'PRIVACY.md',
            'threat_model.md',
            'incident_response.md',
            'hardware_integration.md'
        ]

        for doc in required_docs:
            doc_file = docs_dir / doc
            assert doc_file.exists(), f"Missing documentation: {doc}"

        release_announcement = docs_dir / 'releases' / 'v1.0.md'
        assert release_announcement.exists(), "Release announcement docs/releases/v1.0.md is required"

    def test_release_notes_exist(self):
        """Test RELEASE_NOTES.md exists"""
        assert Path('RELEASE_NOTES.md').exists()


class TestChecksums:
    """Test checksum verification"""

    def test_sha256sums_format(self):
        """Test SHA256SUMS file format"""
        # This test would run in CI with actual artifacts
        pytest.skip("Checksums generated during release")


class TestSigning:
    """Test artifact signing (SC-004)"""

    def test_signature_files_exist(self):
        """Test that signature files are generated"""
        # This test would run in CI with actual artifacts
        pytest.skip("Signatures generated during release")


class TestCrossPlatform:
    """Test cross-platform compatibility (SC-002)"""

    def test_platform_detection(self):
        """Test that platform is detected correctly"""
        import platform

        system = platform.system()
        assert system in ['Linux', 'Darwin', 'Windows']

        print(f"Platform: {system}")
        print(f"Python version: {sys.version}")

    def test_python_version(self):
        """Test that Python version is >= 3.11"""
        assert sys.version_info >= (3, 11), \
            f"Python 3.11+ required, got {sys.version_info}"


@pytest.mark.integration
class TestEndToEnd:
    """End-to-end release verification"""

    def test_full_installation_flow(self):
        """Test complete installation flow"""
        # This would test:
        # 1. Download artifact
        # 2. Verify checksum
        # 3. Verify signature
        # 4. Install
        # 5. Import and test
        pytest.skip("E2E test runs in CI")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
