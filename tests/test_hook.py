import tomlkit
from mxdev_uv_pyproject_updater.hook import UvPyprojectUpdater
from pathlib import Path


# Mocking the mxdev State and Configuration classes
class MockConfig:
    def __init__(self, packages, hooks=None):
        self.packages = packages
        self.hooks = hooks or {}


class MockState:
    def __init__(self, config):
        self.configuration = config


def test_update_pyproject_empty():
    hook = UvPyprojectUpdater()
    doc = tomlkit.document()

    state = MockState(MockConfig(packages={}))

    hook._update_pyproject(doc, state)

    assert doc == tomlkit.document()


def test_update_pyproject_creates_tool_uv_sources():
    hook = UvPyprojectUpdater()
    doc = tomlkit.document()

    packages = {"pkg1": {"target": "sources", "install-mode": "editable"}}
    state = MockState(MockConfig(packages=packages))

    hook._update_pyproject(doc, state)

    assert "tool" in doc
    assert "uv" in doc["tool"]
    assert "sources" in doc["tool"]["uv"]

    sources = doc["tool"]["uv"]["sources"]
    assert "pkg1" in sources
    assert sources["pkg1"]["path"] == "sources/pkg1"
    assert sources["pkg1"]["editable"] is True


def test_update_pyproject_with_subdirectory():
    hook = UvPyprojectUpdater()
    doc = tomlkit.document()

    packages = {
        "pkg-with-sub": {
            "target": "sources",
            "subdirectory": "backend",
            "install-mode": "editable",
        }
    }
    state = MockState(MockConfig(packages=packages))

    hook._update_pyproject(doc, state)

    sources = doc["tool"]["uv"]["sources"]
    assert "pkg-with-sub" in sources
    assert sources["pkg-with-sub"]["path"] == "sources/pkg-with-sub/backend"


def test_update_pyproject_respects_install_modes():
    hook = UvPyprojectUpdater()
    doc = tomlkit.document()

    packages = {
        "editable-pkg": {"target": "sources", "install-mode": "editable"},
        "fixed-pkg": {"target": "sources", "install-mode": "fixed"},
        "skip-pkg": {"target": "sources", "install-mode": "skip"},
    }
    state = MockState(MockConfig(packages=packages))

    hook._update_pyproject(doc, state)

    sources = doc["tool"]["uv"]["sources"]

    assert "editable-pkg" in sources
    assert sources["editable-pkg"]["path"] == "sources/editable-pkg"
    assert sources["editable-pkg"]["editable"] is True

    assert "fixed-pkg" in sources
    assert sources["fixed-pkg"]["path"] == "sources/fixed-pkg"
    assert sources["fixed-pkg"]["editable"] is False

    assert "skip-pkg" not in sources


def test_update_pyproject_preserves_existing_sources():
    hook = UvPyprojectUpdater()

    initial_toml = """
[tool.uv.sources]
existing-pkg = { path = "sources/existing-pkg", editable = true }
"""
    doc = tomlkit.parse(initial_toml)

    packages = {"new-pkg": {"target": "sources", "install-mode": "editable"}}
    state = MockState(MockConfig(packages=packages))

    hook._update_pyproject(doc, state)

    sources = doc["tool"]["uv"]["sources"]
    assert "existing-pkg" in sources
    assert "new-pkg" in sources

    assert sources["existing-pkg"]["path"] == "sources/existing-pkg"
    assert sources["new-pkg"]["path"] == "sources/new-pkg"


def test_update_pyproject_adds_dependencies():
    hook = UvPyprojectUpdater()
    doc = tomlkit.document()

    packages = {
        "pkg1": {"target": "sources", "install-mode": "editable"},
        "pkg2": {"target": "sources", "install-mode": "fixed"},
    }
    state = MockState(MockConfig(packages=packages))

    hook._update_pyproject(doc, state)

    deps = doc["project"]["dependencies"]
    assert len(deps) == 2
    assert "pkg1" in deps
    assert "pkg2" in deps


def test_update_pyproject_preserves_existing_dependencies():
    hook = UvPyprojectUpdater()

    initial_toml = """
[project]
dependencies = [
    "existing-pkg>=1.0.0",
    "pkg1[extra]==2.0.0"
]
"""
    doc = tomlkit.parse(initial_toml)

    packages = {
        "pkg1": {"target": "sources", "install-mode": "editable"},
        "new-pkg": {"target": "sources", "install-mode": "editable"},
    }
    state = MockState(MockConfig(packages=packages))

    hook._update_pyproject(doc, state)

    deps = doc["project"]["dependencies"]
    assert len(deps) == 3
    assert deps[0] == "existing-pkg>=1.0.0"
    assert deps[1] == "pkg1[extra]==2.0.0"
    assert deps[2] == "new-pkg"


def test_update_pyproject_pep503_normalization():
    hook = UvPyprojectUpdater()
    
    initial_toml = """
[project]
dependencies = [
    "plone.app_discussion",
    "Some.Package"
]
"""
    doc = tomlkit.parse(initial_toml)
    
    packages = {
        # 'plone-app-discussion' is the PEP 503 normalized equivalent of 'plone.app_discussion'
        "plone-app-discussion": {"target": "sources", "install-mode": "editable"},
        # 'some-package' is equivalent to 'Some.Package'
        "some-package": {"target": "sources", "install-mode": "editable"},
        # A truly new package
        "new-package": {"target": "sources", "install-mode": "editable"}
    }
    state = MockState(MockConfig(packages=packages))
    
    hook._update_pyproject(doc, state)
    
    deps = doc["project"]["dependencies"]
    
    assert len(deps) == 3
    assert deps[0] == "plone.app_discussion"
    assert deps[1] == "Some.Package"
    assert deps[2] == "new-package"
    hook = UvPyprojectUpdater()

    initial_toml = """
[project]
dependencies = [
    "My_Package>=1.0.0"
]
"""
    doc = tomlkit.parse(initial_toml)

    packages = {
        "my-package": {"target": "sources", "install-mode": "editable"},
        "new_package": {"target": "sources", "install-mode": "editable"},
    }
    state = MockState(MockConfig(packages=packages))

    hook._update_pyproject(doc, state)

    deps = doc["project"]["dependencies"]
    assert len(deps) == 2
    assert deps[0] == "My_Package>=1.0.0"
    assert deps[1] == "new_package"
