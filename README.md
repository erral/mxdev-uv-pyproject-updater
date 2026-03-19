# mxdev-uv-pyproject-updater

An [mxdev](https://github.com/mxstack/mxdev/) extension hook that automatically updates `pyproject.toml` during the mxdev write phase to support [uv](https://github.com/astral-sh/uv) workflows.

## Installation

You must install this package in the same environment as `mxdev`.

If you are using `uv` to run `mxdev` globally, you can install the hook via `uv tool install`:

```bash
uv tool install mxdev --with mxdev-uv-pyproject-updater
```

Or if you are running `mxdev` via a local virtual environment:

```bash
uv pip install mxdev mxdev-uv-pyproject-updater
```

You can also run it directly using `uvx` as follows:

```bash
uvx --with="mxdev-uv-pyproject-updater" mxdev -c mx.ini
```

## Usage

Because it registers an `mxdev` entry point, this hook runs automatically whenever you run `mxdev`. It will automatically detect packages defined in your `mx.ini` file and write the corresponding configuration to your `pyproject.toml` file.

### Features

1. **Automatic `uv` Source Mapping**
   It natively configures the `[tool.uv.sources]` table in your `pyproject.toml`. It handles `mxdev`'s absolute vs relative directories and automatically respects the `install-mode` setting (`editable`, `fixed`, or `skip`). It perfectly supports `mxdev` `subdirectory` parameters too.

   ```toml
   [tool.uv.sources]
   "plone.app.discussion" = {path = "sources/plone.app.discussion", editable = true}
   ```

2. **Smart Dependency Injection**
   The hook safely inserts your checked-out packages directly into your `[project]` `dependencies` array.

   It implements strict **PEP 503 normalization** (converting `-`, `_`, and `.` equivalently) to intelligently ensure packages aren't duplicated, even if the dependency is already specified in your `pyproject.toml` with version specifiers or extras.

   ```toml
   [project]
   dependencies = [
       "plone.app.discussion"
   ]
   ```

3. **Format Preservation**
   Built on `tomlkit`, it safely updates `pyproject.toml` while perfectly preserving all your existing user formatting, arrays, spacing, and comments.
