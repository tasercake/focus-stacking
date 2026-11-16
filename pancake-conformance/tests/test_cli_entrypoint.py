import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from pancake_conformance import main


@pytest.mark.parametrize("project_path", [".", "pancake-conformance", "nested/pancake-conformance"])
def test_vm_dispatch_preserves_workspace_for_nested_suite(tmp_path, monkeypatch, project_path):
    from pancake_conformance import cli

    workspace = tmp_path / "workspace"
    project = workspace / project_path
    (workspace / "submodules/ExampleStacker").mkdir(parents=True)
    (project / "src/pancake_conformance").mkdir(parents=True)
    descriptor = project / "target.toml"
    descriptor.write_text('schema_version=1\nname="example"\nroot="."\ncli=["unused"]\n')
    monkeypatch.setattr(cli, "__file__", str(project / "src/pancake_conformance/cli.py"))
    monkeypatch.setattr(cli, "_provenance", lambda *args: {})
    dispatched = {}

    def run_vm_cases(cases, **kwargs):
        dispatched.update(kwargs)
        return []

    monkeypatch.setattr("pancake_conformance.runner.run_vm_cases", run_vm_cases)
    assert main(["run", "--target", str(descriptor), "--output", str(tmp_path / "run"),
                 "--no-coverage", "--gui-vm", "--case", "interface.compute.gpu"]) == 0
    assert Path(dispatched["project"]) == project.resolve()
    assert Path(dispatched["workspace"]) == workspace


def test_single_entrypoint_lists_machine_readable_cases(capsys):
    assert main(["list", "--json"]) == 0
    records = json.loads(capsys.readouterr().out)
    assert records
    assert len({x["id"] for x in records}) == len(records)
    assert all(set(x) == {"id", "suite", "description"} for x in records)


def test_entrypoint_rejects_empty_selection(tmp_path, capsys):
    assert main(["run", "--target", "unused.toml", "--case", "does-not-exist", "--output", str(tmp_path / "run")]) == 2
    assert "no cases" in capsys.readouterr().err


def test_entrypoint_has_exact_suite_selection(capsys):
    assert main(["list", "--suite", "cli", "--json"]) == 0
    assert all(x["suite"] == "cli" for x in json.loads(capsys.readouterr().out))


def test_optimized_execution_cannot_disable_conformance_checks():
    result = subprocess.run([sys.executable, "-O", "-m", "pancake_conformance", "list", "--json"],
                            capture_output=True, text=True, env=dict(os.environ), check=False)
    assert result.returncode != 0
    assert "optimization" in result.stderr.lower()


def test_coverage_threshold_validation_precedes_target_execution(capsys):
    assert main(["run", "--min-line-coverage", "101", "--target", "/missing-target.toml"]) == 2
    assert "coverage thresholds" in capsys.readouterr().err


def test_explicit_suite_order_can_put_desktop_work_first(capsys):
    assert main(["list", "--suite", "interface", "--suite", "cli", "--json"]) == 0
    records = json.loads(capsys.readouterr().out)
    suites = [record["suite"] for record in records]
    assert suites == sorted(suites, key={"interface": 0, "cli": 1}.get)


def test_typo_in_one_requested_suite_cannot_silently_drop_it(capsys):
    assert main(["list", "--suite", "cli", "--suite", "algorihms", "--json"]) == 2
    assert "unknown suite" in capsys.readouterr().err


def test_full_vm_run_groups_interleaved_gui_cases(tmp_path, monkeypatch):
    from pancake_conformance import cli
    from pancake_conformance.model import Case
    cases = [Case('cli.first', 'cli', None), Case('interface.first', 'interface', None),
             Case('cli.second', 'cli', None), Case('interface.second', 'interface', None)]
    descriptor = tmp_path / 'target.toml'
    descriptor.write_text('schema_version=1\nname="example"\nroot="."\ncli=["unused"]\n')
    seen = []
    monkeypatch.setattr(cli, 'catalog', lambda: cases)
    def run(cases, **kwargs):
        seen.extend(case.id for case in cases)
        return []
    monkeypatch.setattr('pancake_conformance.runner.run_vm_cases', run)
    assert main(['run', '--target', str(descriptor), '--gui-vm', '--output', str(tmp_path / 'run')]) == 0
    assert seen == ['cli.first', 'cli.second', 'interface.first', 'interface.second']
