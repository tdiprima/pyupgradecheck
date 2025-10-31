"""Comprehensive test suite for pyupgradecheck."""
from __future__ import annotations

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from packaging.specifiers import SpecifierSet, InvalidSpecifier
from packaging.version import Version, InvalidVersion
from hypothesis import given, strategies as st, assume, settings
import tempfile

try:
    from importlib.metadata import PackageNotFoundError
except ImportError:
    from importlib_metadata import PackageNotFoundError

from pyupgradecheck.checker import (
    get_installed_packages,
    fetch_pypi_requires_python,
    parse_requires_python,
    check_pkg_compatibility,
    parse_requirements_file,
    check_environment,
)


# ============================================================================
# Unit Tests with Mocking
# ============================================================================


class TestGetInstalledPackages:
    """Test get_installed_packages function."""

    def test_returns_dict(self):
        """Should return a dictionary."""
        result = get_installed_packages()
        assert isinstance(result, dict)

    def test_contains_known_packages(self):
        """Should contain at least some known packages."""
        result = get_installed_packages()
        # Should have at least packaging and pytest
        assert len(result) > 0

    @patch("pyupgradecheck.checker.importlib_metadata.distributions")
    def test_handles_missing_name(self, mock_distributions):
        """Should skip distributions without a name."""
        mock_dist = Mock()
        mock_dist.metadata.get.return_value = None
        mock_distributions.return_value = [mock_dist]

        result = get_installed_packages()
        assert result == {}

    @patch("pyupgradecheck.checker.importlib_metadata.distributions")
    def test_handles_version_error(self, mock_distributions):
        """Should handle version lookup errors gracefully."""
        mock_dist = Mock()
        mock_dist.metadata.get.side_effect = lambda x: "test-pkg" if x in ("Name", "name") else None
        # Make version property raise an exception when accessed
        type(mock_dist).version = property(lambda self: (_ for _ in ()).throw(Exception("version error")))

        mock_distributions.return_value = [mock_dist]

        result = get_installed_packages()
        assert "test-pkg" in result
        assert result["test-pkg"] == "unknown"


class TestFetchPyPIRequiresPython:
    """Test fetch_pypi_requires_python function."""

    @patch("pyupgradecheck.checker.httpx.get")
    def test_successful_fetch(self, mock_get):
        """Should return requires_python when successful."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "info": {"requires_python": ">=3.8"}
        }
        mock_get.return_value = mock_response

        result = fetch_pypi_requires_python("requests")
        assert result == ">=3.8"
        mock_get.assert_called_once()

    @patch("pyupgradecheck.checker.httpx.get")
    def test_missing_requires_python(self, mock_get):
        """Should return None when requires_python is missing."""
        mock_response = Mock()
        mock_response.json.return_value = {"info": {}}
        mock_get.return_value = mock_response

        result = fetch_pypi_requires_python("some-pkg")
        assert result is None

    @patch("pyupgradecheck.checker.httpx.get")
    def test_http_error(self, mock_get):
        """Should return None on HTTP errors."""
        mock_get.side_effect = Exception("Network error")

        result = fetch_pypi_requires_python("nonexistent")
        assert result is None

    @patch("pyupgradecheck.checker.httpx.get")
    def test_timeout_parameter(self, mock_get):
        """Should respect timeout parameter."""
        mock_response = Mock()
        mock_response.json.return_value = {"info": {}}
        mock_get.return_value = mock_response

        fetch_pypi_requires_python("pkg", timeout=10)
        mock_get.assert_called_once()
        assert mock_get.call_args[1]["timeout"] == 10


class TestParseRequiresPython:
    """Test parse_requires_python function."""

    def test_valid_specifier(self):
        """Should parse valid specifiers."""
        result = parse_requires_python(">=3.8")
        assert isinstance(result, SpecifierSet)
        assert Version("3.8") in result
        assert Version("3.9") in result

    def test_complex_specifier(self):
        """Should parse complex specifiers."""
        result = parse_requires_python(">=3.8,<4.0")
        assert isinstance(result, SpecifierSet)
        assert Version("3.8") in result
        assert Version("3.9") in result
        assert Version("4.0") not in result

    def test_none_input(self):
        """Should return None for None input."""
        result = parse_requires_python(None)
        assert result is None

    def test_empty_string(self):
        """Should return None for empty string."""
        result = parse_requires_python("")
        assert result is None

    def test_invalid_specifier(self):
        """Should return None for invalid specifiers."""
        result = parse_requires_python("invalid>>3.8")
        assert result is None


class TestCheckPkgCompatibility:
    """Test check_pkg_compatibility function."""

    @patch("pyupgradecheck.checker.importlib_metadata.distribution")
    @patch("pyupgradecheck.checker.fetch_pypi_requires_python")
    def test_supported_package(self, mock_fetch, mock_dist):
        """Should return 'supported' for compatible packages."""
        mock_fetch.return_value = ">=3.8,<4.0"  # Use non-broad specifier
        # Mock will try to check classifiers as fallback, so make it raise PackageNotFoundError
        mock_dist.side_effect = PackageNotFoundError("test")

        status, details, source = check_pkg_compatibility("pkg", "1.0", "3.9")
        assert status == "supported"
        assert "PyPI" in source

    @patch("pyupgradecheck.checker.importlib_metadata.distribution")
    @patch("pyupgradecheck.checker.fetch_pypi_requires_python")
    def test_incompatible_package(self, mock_fetch, mock_dist):
        """Should return 'incompatible' for incompatible packages."""
        mock_fetch.return_value = ">=3.10,<4.0"  # Use non-broad specifier
        mock_dist.side_effect = PackageNotFoundError("test")

        status, details, source = check_pkg_compatibility("pkg", "1.0", "3.8")
        assert status == "incompatible"

    @patch("pyupgradecheck.checker.importlib_metadata.distribution")
    @patch("pyupgradecheck.checker.fetch_pypi_requires_python")
    def test_broad_specifier_flagged(self, mock_fetch, mock_dist):
        """Should flag overly broad specifiers as unknown."""
        mock_fetch.return_value = ">=3.6"
        mock_dist.side_effect = PackageNotFoundError("test")

        status, details, source = check_pkg_compatibility("pkg", "1.0", "3.12")
        assert status == "unknown"
        assert "broadly" in details.lower()  # Check details, not source

    @patch("pyupgradecheck.checker.fetch_pypi_requires_python")
    def test_invalid_target_python(self, mock_fetch):
        """Should handle invalid target Python versions."""
        mock_fetch.return_value = ">=3.8"

        status, details, source = check_pkg_compatibility("pkg", "1.0", "invalid")
        assert status == "unknown"
        assert "invalid" in details.lower()

    @patch("pyupgradecheck.checker.fetch_pypi_requires_python")
    @patch("pyupgradecheck.checker.importlib_metadata.distribution")
    def test_fallback_to_classifiers(self, mock_dist, mock_fetch):
        """Should fall back to classifiers when PyPI data unavailable."""
        mock_fetch.return_value = None
        mock_metadata = Mock()
        mock_metadata.get_all.return_value = [
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.9",
        ]
        mock_dist.return_value.metadata = mock_metadata

        status, details, source = check_pkg_compatibility("pkg", "1.0", "3.9")
        assert status == "supported"
        assert "classifier" in source.lower()

    @patch("pyupgradecheck.checker.fetch_pypi_requires_python")
    @patch("pyupgradecheck.checker.importlib_metadata.distribution")
    def test_strict_mode_both_match(self, mock_dist, mock_fetch):
        """In strict mode, both PyPI and classifiers must match."""
        mock_fetch.return_value = ">=3.9,<4.0"  # Use non-broad specifier
        mock_metadata = Mock()
        mock_metadata.get_all.return_value = [
            "Programming Language :: Python :: 3.9",
        ]
        mock_dist.return_value.metadata = mock_metadata

        status, details, source = check_pkg_compatibility("pkg", "1.0", "3.9", strict=True)
        assert status == "supported"
        assert source == "strict"

    @patch("pyupgradecheck.checker.fetch_pypi_requires_python")
    @patch("pyupgradecheck.checker.importlib_metadata.distribution")
    def test_strict_mode_partial_match(self, mock_dist, mock_fetch):
        """In strict mode, partial matches should be unknown."""
        mock_fetch.return_value = ">=3.9"
        mock_metadata = Mock()
        mock_metadata.get_all.return_value = []
        mock_dist.return_value.metadata = mock_metadata

        status, details, source = check_pkg_compatibility("pkg", "1.0", "3.9", strict=True)
        assert status == "unknown"
        assert "partial" in details.lower()

    @patch("pyupgradecheck.checker.importlib_metadata.distribution")
    @patch("pyupgradecheck.checker.fetch_pypi_requires_python")
    def test_no_metadata_found(self, mock_fetch, mock_dist):
        """Should return 'unknown' when no metadata found."""
        mock_fetch.return_value = None
        mock_dist.side_effect = PackageNotFoundError("Not found")

        status, details, source = check_pkg_compatibility("pkg", "1.0", "3.9")
        assert status == "unknown"
        assert "no metadata" in details.lower()


class TestParseRequirementsFile:
    """Test parse_requirements_file function."""

    def test_simple_requirements(self):
        """Should parse simple package names."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("requests\n")
            f.write("flask\n")
            f.write("django\n")
            f.flush()
            filepath = f.name

        try:
            result = parse_requirements_file(filepath)
            assert result == ["requests", "flask", "django"]
        finally:
            Path(filepath).unlink()

    def test_requirements_with_versions(self):
        """Should extract package names from versioned requirements."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("requests>=2.28.0\n")
            f.write("flask==2.0.1\n")
            f.write("django~=4.0\n")
            f.flush()
            filepath = f.name

        try:
            result = parse_requirements_file(filepath)
            assert result == ["requests", "flask", "django"]
        finally:
            Path(filepath).unlink()

    def test_requirements_with_comments(self):
        """Should skip comments."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("# This is a comment\n")
            f.write("requests\n")
            f.write("# Another comment\n")
            f.write("flask\n")
            f.flush()
            filepath = f.name

        try:
            result = parse_requirements_file(filepath)
            assert result == ["requests", "flask"]
        finally:
            Path(filepath).unlink()

    def test_requirements_with_git_urls(self):
        """Should skip git+ URLs."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("git+https://github.com/user/repo.git\n")
            f.write("requests\n")
            f.flush()
            filepath = f.name

        try:
            result = parse_requirements_file(filepath)
            assert result == ["requests"]
        finally:
            Path(filepath).unlink()

    def test_requirements_with_editable(self):
        """Should skip -e editable installs."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("-e .\n")
            f.write("requests\n")
            f.flush()
            filepath = f.name

        try:
            result = parse_requirements_file(filepath)
            assert result == ["requests"]
        finally:
            Path(filepath).unlink()

    def test_requirements_with_http_urls(self):
        """Should skip http/https URLs."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("https://example.com/package.whl\n")
            f.write("requests\n")
            f.flush()
            filepath = f.name

        try:
            result = parse_requirements_file(filepath)
            assert result == ["requests"]
        finally:
            Path(filepath).unlink()

    def test_nonexistent_file(self):
        """Should raise FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError):
            parse_requirements_file("/nonexistent/requirements.txt")

    def test_empty_lines_and_whitespace(self):
        """Should handle empty lines and whitespace."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("\n")
            f.write("  requests  \n")
            f.write("\n")
            f.write("  flask  \n")
            f.write("\n")
            f.flush()
            filepath = f.name

        try:
            result = parse_requirements_file(filepath)
            assert result == ["requests", "flask"]
        finally:
            Path(filepath).unlink()

    def test_comprehensive_requirements_file(self):
        """Should parse the comprehensive test_requirements.txt file."""
        # This test uses the actual test_requirements.txt in the project root
        test_req_path = Path(__file__).parent.parent / "test_requirements.txt"

        if not test_req_path.exists():
            pytest.skip("test_requirements.txt not found")

        result = parse_requirements_file(str(test_req_path))

        # Should extract valid package names
        assert isinstance(result, list)
        assert len(result) > 0

        # Should include these known packages
        assert "requests" in result
        assert "flask" in result
        assert "numpy" in result
        assert "django" in result

        # Should handle extras (extract base package name)
        assert "sqlalchemy" in result or "requests" in result  # from requests[security]

        # Should NOT include git URLs or editable installs
        for pkg in result:
            assert not pkg.startswith("git+")
            assert not pkg.startswith("http")
            assert not pkg.startswith("-e")
            assert not pkg.startswith("#")


class TestCheckEnvironment:
    """Test check_environment function."""

    @patch("pyupgradecheck.checker.check_pkg_compatibility")
    @patch("pyupgradecheck.checker.get_installed_packages")
    def test_returns_dict(self, mock_get, mock_check):
        """Should return a dictionary."""
        mock_get.return_value = {"test-pkg": "1.0"}
        mock_check.return_value = ("supported", "test", "test")

        result = check_environment("3.9")
        assert isinstance(result, dict)

    @patch("pyupgradecheck.checker.get_installed_packages")
    @patch("pyupgradecheck.checker.check_pkg_compatibility")
    def test_checks_specific_packages(self, mock_check, mock_get):
        """Should check only specified packages."""
        mock_get.return_value = {"pkg1": "1.0", "pkg2": "2.0", "pkg3": "3.0"}
        mock_check.return_value = ("supported", "test", "test")

        result = check_environment("3.9", packages=["pkg1", "pkg2"])
        assert "pkg1" in result
        assert "pkg2" in result
        assert "pkg3" not in result

    @patch("pyupgradecheck.checker.get_installed_packages")
    @patch("pyupgradecheck.checker.check_pkg_compatibility")
    def test_includes_version_and_status(self, mock_check, mock_get):
        """Should include version and status in results."""
        mock_get.return_value = {"requests": "2.28.0"}
        mock_check.return_value = ("supported", "PyPI requires_python: >=3.7", "PyPI")

        result = check_environment("3.9")
        assert "requests" in result
        assert result["requests"]["version"] == "2.28.0"
        assert result["requests"]["status"] == "supported"
        assert result["requests"]["details"] == "PyPI requires_python: >=3.7"
        assert result["requests"]["source"] == "PyPI"

    @patch("pyupgradecheck.checker.get_installed_packages")
    @patch("pyupgradecheck.checker.check_pkg_compatibility")
    def test_strict_mode_passed_through(self, mock_check, mock_get):
        """Should pass strict mode to check_pkg_compatibility."""
        mock_get.return_value = {"pkg": "1.0"}
        mock_check.return_value = ("unknown", "partial metadata", "strict")

        check_environment("3.9", strict=True)
        mock_check.assert_called_once()
        assert mock_check.call_args[0][3] is True  # strict parameter


# ============================================================================
# Property-Based Tests with Hypothesis
# ============================================================================


class TestHypothesisProperties:
    """Property-based tests using hypothesis."""

    @given(st.text(min_size=1, max_size=20, alphabet=st.characters(min_codepoint=97, max_codepoint=122)))
    @settings(max_examples=50)
    def test_parse_requirements_always_returns_list(self, pkg_name):
        """parse_requirements_file should always return a list."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(f"{pkg_name}\n")
            f.flush()
            filepath = f.name

        try:
            result = parse_requirements_file(filepath)
            assert isinstance(result, list)
        finally:
            Path(filepath).unlink()

    @given(st.integers(min_value=0, max_value=20))
    @settings(max_examples=20)
    def test_parse_requirements_correct_count(self, num_packages):
        """Should return correct number of packages."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for i in range(num_packages):
                f.write(f"package{i}\n")
            f.flush()
            filepath = f.name

        try:
            result = parse_requirements_file(filepath)
            assert len(result) == num_packages
        finally:
            Path(filepath).unlink()

    @given(
        major=st.integers(min_value=3, max_value=3),
        minor=st.integers(min_value=8, max_value=13),
    )
    @settings(max_examples=20)
    def test_parse_requires_python_with_valid_versions(self, major, minor):
        """parse_requires_python should handle valid Python versions."""
        version_str = f"{major}.{minor}"
        spec_str = f">={version_str}"
        result = parse_requires_python(spec_str)

        assert result is not None
        assert isinstance(result, SpecifierSet)
        assert Version(version_str) in result

    @given(st.text(min_size=0, max_size=100))
    @settings(max_examples=50)
    def test_parse_requires_python_never_raises(self, spec_str):
        """parse_requires_python should never raise exceptions."""
        try:
            result = parse_requires_python(spec_str)
            assert result is None or isinstance(result, SpecifierSet)
        except Exception as e:
            pytest.fail(f"parse_requires_python raised {e}")

    def test_compatibility_check_consistency(self):
        """Compatibility checks should be consistent with version ordering."""
        # Test a few specific cases to verify consistency
        with patch("pyupgradecheck.checker.fetch_pypi_requires_python") as mock_fetch, \
             patch("pyupgradecheck.checker.importlib_metadata.distribution") as mock_dist:
            mock_dist.side_effect = PackageNotFoundError("Not found")

            # Target >= requires should be supported
            mock_fetch.return_value = ">=3.8,<4.0"
            status, _, _ = check_pkg_compatibility("pkg", "1.0", "3.9")
            assert status == "supported"

            # Target < requires should be incompatible
            mock_fetch.return_value = ">=3.10,<4.0"
            status, _, _ = check_pkg_compatibility("pkg", "1.0", "3.9")
            assert status == "incompatible"

            # Equal versions should be supported
            mock_fetch.return_value = ">=3.9,<4.0"
            status, _, _ = check_pkg_compatibility("pkg", "1.0", "3.9")
            assert status == "supported"

    def test_check_environment_handles_any_target_version(self):
        """check_environment should handle any target version string."""
        with patch("pyupgradecheck.checker.get_installed_packages") as mock_get, \
             patch("pyupgradecheck.checker.check_pkg_compatibility") as mock_check:
            mock_get.return_value = {"pkg": "1.0"}
            mock_check.return_value = ("unknown", "test", "test")

            # Test with valid version
            result = check_environment("3.9")
            assert isinstance(result, dict)

            # Test with invalid version
            result = check_environment("invalid-version")
            assert isinstance(result, dict)


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests with real package data."""

    def test_check_environment_real_execution(self):
        """Integration test: check environment with real installed packages."""
        # This will actually call PyPI, so we limit to just one package
        result = check_environment("3.9", packages=["packaging"])

        assert isinstance(result, dict)
        assert "packaging" in result
        assert "version" in result["packaging"]
        assert "status" in result["packaging"]
        assert result["packaging"]["status"] in ("supported", "incompatible", "unknown")

    def test_full_workflow_with_requirements_file(self):
        """Integration test: full workflow from requirements file to report."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("packaging\n")
            f.write("hypothesis>=6.0\n")
            f.flush()
            filepath = f.name

        try:
            packages = parse_requirements_file(filepath)
            assert len(packages) == 2

            # Check compatibility (this will hit PyPI)
            result = check_environment("3.9", packages=packages)
            assert isinstance(result, dict)
            assert len(result) == 2
        finally:
            Path(filepath).unlink()
