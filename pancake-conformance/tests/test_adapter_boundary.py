"""Adapter hooks and instrumentation must work for any declared target."""
import json
import sys

import pytest

from pancake_conformance.cli import _parser, main
from pancake_conformance.context import CaseContext
from pancake_conformance.target import TargetSpec


def test_run_requires_explicit_target():
    with pytest.raises(SystemExit):
        _parser().parse_args(["run"])


def test_declared_module_supplies_environment_and_runtime(tmp_path, monkeypatch):
    from pancake_conformance.cli import _provenance
    plugin = tmp_path / "fixture_adapter.py"
    plugin.write_text('def environment(target, base, events_path):\n'
                      '    return dict(base, FIXTURE_ROOT=str(target.root), FIXTURE_EVENTS=str(events_path))\n'
                      'def runtime_info():\n    return {"engine": "fixture"}\n')
    monkeypatch.syspath_prepend(str(tmp_path))
    target = TargetSpec("fixture", tmp_path, ("unused",), adapter="fixture_adapter")
    context = CaseContext(target, tmp_path / "case", environment={"KEEP": "yes"})
    events = tmp_path / "case/call/events.jsonl"
    environment = context.environment(events.parent)
    assert environment["FIXTURE_ROOT"] == str(tmp_path)
    assert environment["FIXTURE_EVENTS"] == str(events)
    assert environment["KEEP"] == "yes"
    assert _provenance(target, [])["reference_runtime"] == {"engine": "fixture"}


def test_unknown_adapter_cannot_silently_disable_instrumentation(tmp_path):
    target = TargetSpec("fixture", tmp_path, ("unused",), adapter="missing_fixture_adapter")
    with pytest.raises(RuntimeError, match="adapter"):
        CaseContext(target, tmp_path / "case").environment(tmp_path / "call")


def test_python_target_collects_coverage_from_declared_source_without_adapter(tmp_path):
    source = tmp_path / "engine"
    source.mkdir()
    (source / "cli.py").write_text('import sys\nif "--help" in sys.argv:\n    print("--input --output --method")\n')
    descriptor = tmp_path / "target.toml"
    descriptor.write_text('schema_version=1\nname="fixture"\nroot="."\n'
                          f'cli=[{json.dumps(sys.executable)}, "engine/cli.py"]\n'
                          '[instrumentation]\nsource="engine"\n')
    output = tmp_path / "run"
    assert main(["run", "--target", str(descriptor), "--case", "cli.help", "--output", str(output)]) == 0
    summary = json.loads((output / "coverage/summary.json").read_text())
    assert summary["execution_present"] is True
    assert summary["branch_total"] == 2
    assert summary["source_file_count"] == 1


def test_explicit_coverage_requires_declared_source(tmp_path, capsys):
    descriptor = tmp_path / "target.toml"
    descriptor.write_text('schema_version=1\nname="fixture"\nroot="."\ncli=["unused"]\n')
    assert main(["run", "--target", str(descriptor), "--coverage", "--case", "cli.help",
                 "--output", str(tmp_path / "run")]) == 2
    assert "instrumentation.source" in capsys.readouterr().err


def test_descriptor_resolves_runtime_and_instrumentation(tmp_path):
    (tmp_path / "engine").mkdir()
    (tmp_path / "runtime").mkdir()
    descriptor = tmp_path / "target.toml"
    descriptor.write_text('schema_version=1\nname="fixture"\nroot="."\ncli=["unused"]\n'
                          '[instrumentation]\nsource="engine"\n[runtime]\nproject="runtime"\n')
    target = TargetSpec.load(descriptor)
    assert target.coverage_source == tmp_path / "engine"
    assert target.runtime_project == tmp_path / "runtime"


def test_provenance_ignores_nested_runtime_environments(tmp_path, monkeypatch):
    from pancake_conformance import cli
    source = tmp_path / "src/pancake_conformance"
    source.mkdir(parents=True)
    entrypoint = source / "cli.py"
    entrypoint.write_text("# frozen suite\n")
    monkeypatch.setattr(cli, "__file__", str(entrypoint))
    target = TargetSpec("fixture", tmp_path, ("unused",))
    before = cli._provenance(target, [])["suite_source_sha256"]
    runtime = source / "adapters/runtime/.venv/lib"
    runtime.mkdir(parents=True)
    (runtime / "installed.py").write_text("# installed dependency\n")
    after = cli._provenance(target, [])["suite_source_sha256"]
    assert before == after
