# uv-pre-commit

A pre-commit hook to prevent accidentally committing local path sources instead of git sources in `pyproject.toml` files.

## Problem

When working with `uv` and managing dependencies via `tool.uv.sources`, developers often temporarily change git sources to local path sources for development:

```toml
[tool.uv.sources]
# Development: using local path
materials = { path = "../materials", editable = true }

# Should be committed as:
# materials = { git = "ssh://git@github.com/org/materials", tag = "v1.0.0" }
```

This hook prevents such changes from being accidentally committed to the repository.

## Installation

Add this hook to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/yourusername/uv-pre-commit
    rev: v0.1.0  # Use the latest version
    hooks:
      - id: check-uv-sources
```

Then install the pre-commit hook:

```bash
pre-commit install
```

## How It Works

The hook:

1. Reads your `pyproject.toml` file
2. Compares the current `[tool.uv.sources]` section with the version in git HEAD
3. Checks if any sources that were `git` sources in the committed version have been changed to `path` sources
4. Fails the commit if such changes are detected, with a clear error message

## Example

Given this committed version in git:

```toml
[tool.uv.sources]
bb_transforms = { git = "ssh://git@github.com/bb-takeoffs/bb_transforms", tag = "v1.0.0" }
materials = { git = "ssh://git@github.com/bb-takeoffs/materials", tag = "v1.0.0" }
utils = { git = "ssh://git@github.com/bb-takeoffs/utils", tag = "v1.0.0" }
```

If you try to commit this change:

```toml
[tool.uv.sources]
bb_transforms = { git = "ssh://git@github.com/bb-takeoffs/bb_transforms", tag = "v1.0.0" }
materials = { path = "../materials", editable = true }  # ❌ Changed to path!
utils = { git = "ssh://git@github.com/bb-takeoffs/utils", tag = "v1.0.0" }
```

The hook will fail with:

```
ERROR: Git sources were changed to non-git sources!

The following packages were git sources but are no longer:
  - materials: git -> path

This likely means you have local development changes that shouldn't be committed.
Please revert these sources back to their git configurations.
```

## What's Allowed

The hook only prevents changing existing git sources to non-git sources. These changes are all allowed:

- ✅ Adding new path sources (that weren't git sources before)
- ✅ Removing sources entirely
- ✅ Changing git tags/branches/revisions (still git sources)
- ✅ Adding new packages with any source type
- ✅ Changing path sources to other path sources
- ✅ Changing non-git sources to git sources

## Running Manually

You can run the check manually:

```bash
# Check pyproject.toml (default)
check-uv-sources

# Check specific file(s)
check-uv-sources path/to/pyproject.toml

# Check multiple files
check-uv-sources project1/pyproject.toml project2/pyproject.toml
```

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/uv-pre-commit
cd uv-pre-commit

# Install in development mode with test dependencies
pip install -e ".[test]"
```

### Running Tests

```bash
pytest
```

### Testing the Hook Locally

You can test the hook in a local repository:

```bash
# In your test repository
pip install -e /path/to/uv-pre-commit

# Add to .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: check-uv-sources
        name: Check UV Sources
        entry: check-uv-sources
        language: system
        files: pyproject\.toml$
        pass_filenames: true
```

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
