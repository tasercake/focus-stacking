"""The suite must run from its own project without the parent repository."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib


def project_root():
    return Path(__file__).resolve().parents[1]


def test_cli_lists_cases_without_parent_repository(tmp_path):
    project = project_root()
    assert (project / "pyproject.toml").is_file(), "pancake-conformance must own its project metadata"
    checkout = tmp_path / "pancake-conformance"
    shutil.copytree(project, checkout, ignore=shutil.ignore_patterns(
        ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "artifacts", "dist", "build"))
    environment = dict(os.environ, PYTHONPATH=str(checkout / "src"))
    result = subprocess.run([sys.executable, "-m", "pancake_conformance", "list", "--json"],
                            cwd=tmp_path, env=environment, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    cases = json.loads(result.stdout)
    assert len(cases) >= 316
    assert len({case["id"] for case in cases}) == len(cases)
    assert len({case["id"] for case in cases}) == len(cases)


def test_core_project_has_no_application_dependencies():
    metadata = tomllib.loads((project_root() / "pyproject.toml").read_text())
    assert metadata["project"]["name"] == "pancake-conformance"
    assert metadata["project"]["scripts"] == {"pancake-conformance": "pancake_conformance:main"}
    assert "workspace" not in metadata["tool"]["uv"]
    assert not metadata["tool"]["uv"].get("sources")
    assert not metadata["project"].get("optional-dependencies")


def test_application_names_stay_inside_adapter_directory():
    """Derive application names from isolated adapter dependency manifests."""
    project = project_root()
    adapters = project / "src/pancake_conformance/adapters"
    names = set()
    for manifest in adapters.glob("*/pyproject.toml"):
        metadata = tomllib.loads(manifest.read_text())
        names.update(name.casefold() for name in metadata.get("tool", {}).get("uv", {}).get("sources", {})
                     if name != "pancake-conformance")
    assert names, "No adapter application dependency was checked"
    ignored = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "artifacts", "dist", "build"}
    violations = []
    for directory, children, files in os.walk(project):
        children[:] = [name for name in children if name not in ignored and Path(directory) / name != adapters]
        for filename in files:
            path = Path(directory) / filename
            relative = path.relative_to(project)
            content = path.read_bytes().decode("utf-8", errors="ignore").casefold()
            if any(name in relative.as_posix().casefold() or name in content for name in names):
                violations.append(str(relative))
    assert not violations, "Application references outside adapters: " + ", ".join(sorted(violations))
