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
    assert len(cases) == 316
    assert len({case["id"] for case in cases}) == len(cases)


def test_chimpstackr_is_an_optional_external_reference():
    project = project_root()
    assert (project / "pyproject.toml").is_file(), "pancake-conformance must own its project metadata"
    metadata = tomllib.loads((project / "pyproject.toml").read_text())
    assert metadata["project"]["name"] == "pancake-conformance"
    assert metadata["project"]["scripts"] == {"pancake-conformance": "pancake_conformance:main"}
    assert "workspace" not in metadata["tool"]["uv"]
    source = metadata["tool"]["uv"]["sources"]["chimpstackr"]
    assert (project / source["path"]).resolve() == project.parent / "submodules/ChimpStackr"
    assert "chimpstackr" in metadata["project"]["optional-dependencies"]
