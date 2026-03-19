import logging
import re
from pathlib import Path
from typing import Any

import tomlkit
from mxdev.state import State
from mxdev.hooks import Hook

logger = logging.getLogger("mxdev")

def normalize_name(name: str) -> str:
    """PEP 503 normalization: lowercased, runs of -, _, . become single -"""
    return re.sub(r"[-_.]+", "-", name).lower()

class UvPyprojectUpdater(Hook):
    """
    An mxdev hook that updates pyproject.toml during the write phase.
    """

    namespace = "mxdev-uv-pyproject-updater"

    def read(self, state: State) -> None:
        """Called after mxdev's read phase completes."""
        pass

    def write(self, state: State) -> None:
        """Called after mxdev's write phase completes."""
        logger.info("[%s] Updating pyproject.toml...", self.namespace)

        pyproject_path = Path("pyproject.toml")
        if not pyproject_path.exists():
            logger.warning(
                "[%s] pyproject.toml not found, skipping update.", self.namespace
            )
            return

        # 3. Read the pyproject.toml using tomlkit to preserve formatting
        try:
            with pyproject_path.open("r", encoding="utf-8") as f:
                doc = tomlkit.load(f)
        except Exception as e:
            logger.error("[%s] Failed to read pyproject.toml: %s", self.namespace, e)
            return

        # 4. Modify the document
        self._update_pyproject(doc, state)

        # 5. Write it back preserving formatting
        try:
            with pyproject_path.open("w", encoding="utf-8") as f:
                tomlkit.dump(doc, f)
            logger.info("[%s] Successfully updated pyproject.toml", self.namespace)
        except Exception as e:
            logger.error("[%s] Failed to write pyproject.toml: %s", self.namespace, e)

    def _update_pyproject(self, doc: tomlkit.TOMLDocument, state: State) -> None:
        """
        Modify the pyproject.toml document based on mxdev state.
        Injects packages into [tool.uv.sources] based on install-mode.
        """
        if not state.configuration.packages:
            return

        # 1. Update [tool.uv.sources]
        if "tool" not in doc:
            doc.add("tool", tomlkit.table())
        if "uv" not in doc["tool"]:
            doc["tool"]["uv"] = tomlkit.table()
        if "sources" not in doc["tool"]["uv"]:
            doc["tool"]["uv"]["sources"] = tomlkit.table()

        uv_sources = doc["tool"]["uv"]["sources"]

        for pkg_name, pkg_data in state.configuration.packages.items():
            install_mode = pkg_data.get("install-mode", "editable")
            
            if install_mode == "skip":
                continue

            target_dir = Path(pkg_data.get("target", "sources"))
            
            # The actual path to the package is target_dir / pkg_name
            # If a subdirectory is specified, we append it
            package_path = target_dir / pkg_name
            subdirectory = pkg_data.get("subdirectory", "")
            if subdirectory:
                package_path = package_path / subdirectory
                
            try:
                # If target_dir is absolute and inside cwd, relative_to works
                # If target_dir is already relative, relative_to will fail, so we just use it directly
                if package_path.is_absolute():
                    rel_path = package_path.relative_to(Path.cwd()).as_posix()
                else:
                    rel_path = package_path.as_posix()
            except ValueError:
                # Fallback for absolute paths outside cwd
                rel_path = package_path.as_posix()

            source_table = tomlkit.inline_table()
            source_table.append("path", rel_path)
            
            if install_mode in ("editable", "direct"):
                source_table.append("editable", True)
            elif install_mode == "fixed":
                source_table.append("editable", False)

            uv_sources[pkg_name] = source_table

        # 2. Add packages to project.dependencies if not present
        if "project" not in doc:
            doc.add("project", tomlkit.table())
            
        if "dependencies" not in doc["project"]:
            doc["project"]["dependencies"] = tomlkit.array()
            
        dependencies = doc["project"]["dependencies"]
        
        # PEP 508 package names can contain letters, numbers, hyphens, underscores, and dots.
        pkg_name_pattern = re.compile(r"^([a-zA-Z0-9_\-\.]+)")
        
        existing_pkg_names = set()
        for dep in dependencies:
            match = pkg_name_pattern.match(str(dep).strip())
            if match:
                existing_pkg_names.add(normalize_name(match.group(1)))
                
        for pkg_name, pkg_data in state.configuration.packages.items():
            install_mode = pkg_data.get("install-mode", "editable")
            if install_mode == "skip":
                continue
                
            normalized_name = normalize_name(pkg_name)
            if normalized_name not in existing_pkg_names:
                dependencies.append(pkg_name)
