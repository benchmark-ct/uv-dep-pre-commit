"""Check that git sources in tool.uv.sources remain git sources."""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # type: ignore


def parse_toml(content: str) -> Dict[str, Any]:
    """Parse TOML content."""
    return tomllib.loads(content)


def get_git_version(file_path: Path) -> Optional[str]:
    """Get the version of the file from git HEAD.

    Returns None if the file is not in git or is new.
    """
    try:
        # Get the git repository root
        git_root_result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=file_path.parent,
            capture_output=True,
            text=True,
            check=True,
        )
        git_root = Path(git_root_result.stdout.strip())

        # Convert to relative path from git root
        relative_path = file_path.resolve().relative_to(git_root)

        result = subprocess.run(
            ["git", "show", f"HEAD:{relative_path}"],
            cwd=git_root,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError:
        # File doesn't exist in HEAD (new file) or not in a git repo
        return None
    except ValueError:
        # File is not within the git repository
        return None


def get_uv_sources(toml_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Extract tool.uv.sources from TOML data.

    Returns an empty dict if the section doesn't exist.
    """
    try:
        return toml_data.get("tool", {}).get("uv", {}).get("sources", {})
    except (KeyError, AttributeError):
        return {}


def check_source_changes(
    current_sources: Dict[str, Dict[str, Any]],
    git_sources: Dict[str, Dict[str, Any]],
) -> list[tuple[str, str, str]]:
    """Check for sources that changed from git to non-git types.

    Returns a list of (package_name, old_type, new_type) tuples for violations.
    """
    violations = []

    for package_name, git_config in git_sources.items():
        if package_name not in current_sources:
            # Package removed entirely - not our concern
            continue

        current_config = current_sources[package_name]

        # Check if it was a git source
        if "git" not in git_config:
            # Wasn't a git source before, so changes are allowed
            continue

        # It was a git source - check if it still is
        if "git" not in current_config:
            # Changed from git to something else (likely path)
            old_type = "git"
            new_type = "path" if "path" in current_config else "unknown"
            violations.append((package_name, old_type, new_type))

    return violations


def check_file(file_path: Path) -> int:
    """Check a single pyproject.toml file.

    Returns 0 if check passes, 1 if violations found, 2 for errors.
    """
    if not file_path.exists():
        print(f"Error: {file_path} does not exist", file=sys.stderr)
        return 2

    # Read current file
    try:
        with open(file_path, "rb") as f:
            current_data = tomllib.load(f)
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return 2

    # Get git version
    git_content = get_git_version(file_path)
    if git_content is None:
        # File is new or not in git - nothing to compare against
        print(f"File {file_path} is not in git or is new - skipping check")
        return 0

    # Parse git version
    try:
        git_data = parse_toml(git_content)
    except Exception as e:
        print(f"Error parsing git version of {file_path}: {e}", file=sys.stderr)
        return 2

    # Extract sources
    current_sources = get_uv_sources(current_data)
    git_sources = get_uv_sources(git_data)

    if not git_sources:
        # No sources in git version - nothing to enforce
        return 0

    # Check for violations
    violations = check_source_changes(current_sources, git_sources)

    if violations:
        print("ERROR: Git sources were changed to non-git sources!", file=sys.stderr)
        print(file=sys.stderr)
        print(
            "The following packages were git sources but are no longer:",
            file=sys.stderr,
        )
        for package_name, old_type, new_type in violations:
            print(f"  - {package_name}: {old_type} -> {new_type}", file=sys.stderr)
        print(file=sys.stderr)
        print(
            "This likely means you have local development changes that shouldn't be committed.",
            file=sys.stderr,
        )
        print(
            "Please revert these sources back to their git configurations.",
            file=sys.stderr,
        )
        return 1

    return 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check that git sources in tool.uv.sources remain git sources"
    )
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        default=[Path("pyproject.toml")],
        help="pyproject.toml files to check (default: pyproject.toml)",
    )

    args = parser.parse_args()

    exit_code = 0
    for file_path in args.files:
        result = check_file(file_path)
        if result != 0:
            exit_code = result

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
