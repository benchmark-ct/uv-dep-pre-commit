"""Tests for check_sources module."""

import subprocess
import tempfile
from pathlib import Path

import pytest

from uv_pre_commit.check_sources import (
    check_source_changes,
    get_uv_sources,
    parse_toml,
)


def test_parse_toml():
    """Test TOML parsing."""
    content = """
[tool.uv.sources]
package1 = { git = "https://github.com/example/package1" }
package2 = { path = "../package2" }
"""
    data = parse_toml(content)
    assert "tool" in data
    assert "uv" in data["tool"]
    assert "sources" in data["tool"]["uv"]


def test_get_uv_sources():
    """Test extracting UV sources."""
    data = {
        "tool": {
            "uv": {
                "sources": {
                    "package1": {"git": "https://github.com/example/package1"},
                    "package2": {"path": "../package2"},
                }
            }
        }
    }
    sources = get_uv_sources(data)
    assert len(sources) == 2
    assert "package1" in sources
    assert "package2" in sources


def test_get_uv_sources_missing():
    """Test extracting UV sources when section is missing."""
    data = {"tool": {}}
    sources = get_uv_sources(data)
    assert sources == {}


def test_check_source_changes_no_violations():
    """Test check when no sources changed from git."""
    git_sources = {
        "package1": {"git": "https://github.com/example/package1", "tag": "v1.0.0"},
        "package2": {"path": "../package2"},
    }
    current_sources = {
        "package1": {"git": "https://github.com/example/package1", "tag": "v2.0.0"},
        "package2": {"path": "../package2"},
    }
    violations = check_source_changes(current_sources, git_sources)
    assert len(violations) == 0


def test_check_source_changes_with_violation():
    """Test check when git source changed to path."""
    git_sources = {
        "package1": {"git": "https://github.com/example/package1", "tag": "v1.0.0"},
        "package2": {"git": "https://github.com/example/package2", "tag": "v1.0.0"},
    }
    current_sources = {
        "package1": {"git": "https://github.com/example/package1", "tag": "v2.0.0"},
        "package2": {"path": "../package2", "editable": True},
    }
    violations = check_source_changes(current_sources, git_sources)
    assert len(violations) == 1
    assert violations[0] == ("package2", "git", "path")


def test_check_source_changes_package_removed():
    """Test check when package is removed entirely."""
    git_sources = {
        "package1": {"git": "https://github.com/example/package1", "tag": "v1.0.0"},
        "package2": {"git": "https://github.com/example/package2", "tag": "v1.0.0"},
    }
    current_sources = {
        "package1": {"git": "https://github.com/example/package1", "tag": "v1.0.0"},
    }
    violations = check_source_changes(current_sources, git_sources)
    assert len(violations) == 0


def test_check_source_changes_new_path_source():
    """Test check when new path source is added (no git source before)."""
    git_sources = {
        "package1": {"git": "https://github.com/example/package1", "tag": "v1.0.0"},
    }
    current_sources = {
        "package1": {"git": "https://github.com/example/package1", "tag": "v1.0.0"},
        "package2": {"path": "../package2"},
    }
    violations = check_source_changes(current_sources, git_sources)
    assert len(violations) == 0


def test_integration_with_git(tmp_path):
    """Integration test with actual git repository."""
    # Create a temporary git repo
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )

    # Create initial pyproject.toml with git source
    pyproject = repo_dir / "pyproject.toml"
    pyproject.write_text("""[tool.uv.sources]
package1 = { git = "https://github.com/example/package1", tag = "v1.0.0" }
""")

    # Commit it
    subprocess.run(["git", "add", "pyproject.toml"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )

    # Now modify to use path
    pyproject.write_text("""[tool.uv.sources]
package1 = { path = "../package1", editable = true }
""")

    # Run check - should fail
    from uv_pre_commit.check_sources import check_file

    result = check_file(pyproject)
    assert result == 1  # Should detect violation
