"""VM dispatch stays outside portable conformance cases."""
from dataclasses import asdict
import json
from types import SimpleNamespace

import pytest

from pancake_conformance.model import Case, CaseResult
from pancake_conformance.target import TargetSpec


def test_vm_dispatch_never_calls_host_gui_and_marks_missing_capability(tmp_path):
    from pancake_conformance.coverage import source_provenance
    from pancake_conformance.runner import run_vm_cases
    source = tmp_path / "target" / "src"
    source.mkdir(parents=True)
    (source / "app.py").write_text("value = 1\n")
    descriptor = tmp_path / "target.toml"
    descriptor.write_text("")
    target = TargetSpec("example", source.parent, ("app",), ("app-gui",), descriptor=descriptor,
                        gui_vm={"name": "test"})
    calls = []
    def forbid_gui(ctx):
        raise AssertionError("GUI ran on host")
    cases = [Case("host.before", "cli", lambda ctx: calls.append("host.before")),
             Case("gui", "interface", forbid_gui),
             Case("gui.gpu", "interface", forbid_gui, required_capabilities=("physical_gpu",)),
             Case("host.after", "algorithms", lambda ctx: calls.append("host.after"))]
    class FakeVM:
        def __init__(self, config, workspace, output, *, visible, persist):
            assert visible is False and persist is True
        def prepare(self):
            calls.append("prepare")
        def run_cases(self, ids, **kwargs):
            assert ids == ["gui"]
            calls.append("guest.gui")
            artifacts = tmp_path / "download"
            artifacts.mkdir()
            return SimpleNamespace(report={"complete": True, "cases": [asdict(CaseResult("gui", "interface", "passed", 1))]},
                                   artifacts=artifacts, returncode=0, guest_source_root="/guest/src",
                                   source_provenance=source_provenance(source))
        def close(self):
            calls.append("close")
    results = run_vm_cases(cases, target=target, output=tmp_path / "run", workspace=tmp_path,
                           persist=True, vm_factory=FakeVM)
    assert calls == ["prepare", "host.before", "guest.gui", "host.after", "close"]
    assert [r.status for r in results] == ["passed", "passed", "unsupported", "passed"]
    assert [r.execution_environment for r in results] == ["host", "vm", "vm", "host"]
    assert results[0].notes["artifact_directory"] == str((tmp_path / "run/host-before/cases/host.before").resolve())
    assert results[1].notes["artifact_directory"] == str((tmp_path / "download/cases/gui").resolve())
    report = json.loads((tmp_path / "run/report.json").read_text())
    assert report["counts"] == {"passed": 3, "failed": 0, "unsupported": 1}
    assert report["complete"] is True and report["status"] == "partial"


def test_missing_vm_fails_before_any_host_case(tmp_path):
    from pancake_conformance.runner import run_vm_cases
    executed = []
    class Missing:
        def __init__(self, *args, **kwargs):
            pass
        def prepare(self):
            raise RuntimeError("configured VM unavailable")
        def close(self):
            pass
    target = TargetSpec("example", tmp_path, ("app",), gui_vm={"name": "missing"})
    with pytest.raises(RuntimeError, match="unavailable"):
        run_vm_cases([Case("host", "cli", lambda ctx: executed.append(True)),
                      Case("gui", "interface", lambda ctx: executed.append(True))],
                     target=target, output=tmp_path, workspace=tmp_path, vm_factory=Missing)
    assert not executed
    assert json.loads((tmp_path / "report.json").read_text())["complete"] is False


def test_gui_vm_flags_have_safe_defaults():
    from pancake_conformance.cli import _parser
    args = _parser().parse_args(["run", "--target", "target.toml", "--gui-vm"])
    assert args.gui_vm is True and args.gui_vm_visible is False and args.gui_vm_persist is False
    assert _parser().parse_args(["run", "--target", "target.toml", "--no-gui-vm"]).gui_vm is False


def test_unsupported_only_cli_reports_zero_coverage_without_running_target(tmp_path, monkeypatch):
    from pancake_conformance.cli import main
    (tmp_path / "src").mkdir()
    (tmp_path / "src/app.py").write_text("value = 1\n")
    descriptor = tmp_path / "target.toml"
    descriptor.write_text('schema_version=1\nname="example"\nroot="."\ncli=["unused"]\n'
                          'gui=["unused"]\n[instrumentation]\nsource="src"\n[gui_vm]\nname="test"\n')
    class VM:
        def __init__(self, *args, **kwargs):
            pass
        def prepare(self):
            pass
        def run_cases(self, *args, **kwargs):
            pytest.fail("Unsupported case executed")
        def close(self):
            pass
    monkeypatch.setattr("pancake_conformance.gui_vm.TartGuiVM", VM)
    output = tmp_path / "run"
    assert main(["run", "--target", str(descriptor), "--output", str(output),
                 "--gui-vm", "--gui-vm-persist", "--case", "interface.compute.gpu"]) == 0
    report = json.loads((output / "report.json").read_text())
    assert report["status"] == "partial" and report["counts"]["passed"] == 0
    assert report["coverage"]["line_covered"] == report["coverage"]["branch_covered"] == 0
    assert report["coverage"]["execution_present"] is False


def test_vm_partition_rejects_duplicate_ids_before_vm_work(tmp_path):
    from pancake_conformance.runner import run_vm_cases
    cases = [Case("same", "cli", lambda ctx: None), Case("same", "interface", lambda ctx: None)]
    with pytest.raises(ValueError, match="duplicate"):
        run_vm_cases(cases, target=None, output=tmp_path, workspace=tmp_path,
                     vm_factory=lambda *args, **kwargs: pytest.fail("VM work before inventory validation"))


def test_pending_verdict_cannot_exit_success_outside_guest_worker(tmp_path, monkeypatch):
    from pancake_conformance.cli import main
    monkeypatch.delenv("PANCAKE_CONFORMANCE_VM_GUEST", raising=False)
    monkeypatch.setattr("pancake_conformance.cli.catalog", lambda: [
        Case("pending", "cli", lambda ctx: ctx.note("host_verification_pending", True))])
    descriptor = tmp_path / "target.toml"
    descriptor.write_text('schema_version=1\nname="example"\nroot="."\ncli=["unused"]\n')
    assert main(["run", "--gui-vm", "--gui-vm-persist", "--no-coverage",
                 "--target", str(descriptor), "--output", str(tmp_path / "run")]) != 0


@pytest.mark.parametrize("field", ["suite_source_sha256", "target_descriptor_sha256", "target_commit"])
def test_guest_must_run_same_suite_descriptor_and_target(field):
    from pancake_conformance.runner import validate_execution_provenance
    expected = {"suite_source_sha256": "suite", "target_descriptor_sha256": "descriptor", "target_commit": "commit"}
    validate_execution_provenance(expected, expected)
    with pytest.raises(ValueError, match=field):
        validate_execution_provenance(expected, {**expected, field: "different"})


def test_vm_fail_fast_stops_host_parity_comparisons(tmp_path, monkeypatch):
    from pancake_conformance.runner import run_vm_cases
    checked = []
    def verify(result, **kwargs):
        checked.append(result.id)
        result.status = "failed"
        result.error = "wrong pixels"
        result.notes["host_verification_pending"] = False
    monkeypatch.setattr("pancake_conformance.runner.verify_guest_parity", verify)
    class VM:
        def __init__(self, *args, **kwargs):
            pass
        def prepare(self):
            pass
        def close(self):
            pass
        def run_cases(self, ids, **kwargs):
            records = [asdict(CaseResult(ident, "interface", "pending", 0,
                        notes={"host_verification_pending": True, "host_parity_requests": [{}]})) for ident in ids]
            return SimpleNamespace(report={"complete": True, "cases": records}, artifacts=tmp_path,
                                   source_provenance={}, returncode=0)
    results = run_vm_cases([Case(ident, "interface", lambda ctx: pytest.fail("host GUI")) for ident in ("first", "second")],
        target=TargetSpec("example", tmp_path, ("unused",)), output=tmp_path, workspace=tmp_path,
        vm_factory=VM, fail_fast=True)
    assert checked == ["first"]
    assert len(results) == 1 and results[0].status == "failed"
