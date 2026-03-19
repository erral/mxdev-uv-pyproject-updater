# AGENTS.md

This document serves as an architectural record and instruction manual for future AI agents, developers, and maintainers working on `mxdev-uv-pyproject-updater`.

## Project Context and Purpose
The goal of this project is to create an extension hook for `mxdev` that automatically modifies `pyproject.toml` during the "Write Phase" of `mxdev`. It specifically configures `pyproject.toml` for `uv` workflows by injecting checked-out packages into `[tool.uv.sources]` and the `[project.dependencies]` array.

## Core Architectural Decisions

### 1. Standalone Plugin Architecture
**Decision**: Create a standalone package (`mxdev-uv-pyproject-updater`) instead of modifying `mxdev` core.
**Reasoning**: `mxdev` has a strict architectural constraint defined in its `CLAUDE.md`: "Minimal dependencies: Only `packaging` at runtime". Modifying `pyproject.toml` requires a robust TOML parsing library. By creating a standalone `mxdev` hook package, we can freely depend on `tomlkit` without violating `mxdev`'s core principles.
**Implementation**: We use standard Python entry points (`[project.entry-points.mxdev]`) to automatically hook into `mxdev`'s execution flow.

### 2. Formatting Preservation
**Decision**: Use `tomlkit` instead of the standard library `tomllib`.
**Reasoning**: `tomllib` (Python 3.11+) only supports reading TOML, not writing it. Other libraries like `tomli-w` write TOML but destroy user comments and formatting. `tomlkit` is specifically designed to parse, modify, and rewrite TOML files while perfectly preserving existing comments, spacing, and array structures.

### 3. Path Resolution strategy
**Decision**: Dynamically construct paths using `pathlib.Path` and resolve relative paths against the current working directory.
**Reasoning**: `mxdev` provides a `target` directory (e.g., `sources`) and a package name. To support `uv`, the path in `[tool.uv.sources]` must point directly to the package folder (e.g., `sources/my-package`). We construct `target / name` and, if a `subdirectory` is defined in `mx.ini`, append it (`target / name / subdirectory`). If the resulting path is absolute and inside the project, we convert it to a relative path to keep `pyproject.toml` portable.

### 4. Dependency Deduplication (PEP 503)
**Decision**: Implement strict PEP 503 normalization when checking for existing dependencies.
**Reasoning**: Package names can be written with hyphens, underscores, or dots (e.g., `plone.app.discussion`, `plone_app_discussion`, `plone-app-discussion`). Without normalization, the hook would incorrectly identify these as missing and inject duplicates.
**Implementation**: We use the regex `re.sub(r"[-_.]+", "-", name).lower()` to normalize all existing and incoming dependencies before appending them to the `[project.dependencies]` array. We also strip version specifiers (like `>=1.0.0`) and extras (`[test]`) using `r"^([a-zA-Z0-9_\-\.]+)"` before normalization.

## Code Structure

- `pyproject.toml`: Defines dependencies (`mxdev`, `tomlkit`) and the `mxdev` entry point.
- `src/mxdev_uv_pyproject_updater/hook.py`: Contains the `UvPyprojectUpdater` class extending `mxdev.Hook`.
  - `write()`: Entry point called by `mxdev`. Opens the file safely.
  - `_update_pyproject()`: The core business logic for TOML manipulation.
  - `normalize_name()`: PEP 503 string normalization utility.
- `tests/test_hook.py`: Comprehensive test suite using mocked `mxdev.State` objects.

## Testing Instructions

Tests are written using `pytest`. They use mocked representations of `mxdev`'s `State` and `Configuration` objects to simulate the "Write Phase" without needing actual git checkouts.

### Running the Tests

To run the tests locally, you should use `uv`:

```bash
# Run tests using uv
uv run --with pytest pytest tests/test_hook.py

# Run tests with verbose output
uv run --with pytest pytest -v tests/test_hook.py
```

### Test Coverage Areas
The `test_hook.py` file covers the following critical areas:
- `test_update_pyproject_creates_tool_uv_sources`: Creation of the `[tool.uv.sources]` table from scratch.
- `test_update_pyproject_with_subdirectory`: Correct path concatenation for packages using the `subdirectory` parameter.
- `test_update_pyproject_respects_install_modes`: Correct mapping of `editable`, `fixed` (editable=false), and `skip` (ignored).
- `test_update_pyproject_preserves_existing_sources`: Ensuring user-defined sources aren't overwritten.
- `test_update_pyproject_adds_dependencies`: Injection into `[project.dependencies]`.
- `test_update_pyproject_preserves_existing_dependencies`: Safe regex parsing of existing dependencies with versions/extras.
- `test_update_pyproject_pep503_normalization`: Verification that dots, underscores, and hyphens are treated equivalently to prevent duplication.
