"""Release accounting checks against the frozen runner's report format."""

from dataclasses import asdict
import json
from pathlib import Path

import pytest

from pancake_conformance.model import CaseResult
from pancake_conformance.runner import write_reports

from pancake_conformance.adapters.pancake.release_ledger import (
    Lane,
    ReleaseContract,
    digest,
    load_contract,
    verify_lane,
    verify_package,
    verify_release,
)


@pytest.fixture
def contract():
    return load_contract()


def test_release_partition_matches_current_catalog(contract):
    chosen = [case.id for lane in Lane for case in contract.select(lane)]
    assert len(chosen) == len(set(chosen)) == 376
    assert [len(contract.select(lane)) for lane in Lane] == [341, 34, 1]
    assert contract.select(Lane.PHYSICAL_GPU_GUI)[0].id == "interface.compute.gpu"


def _write_json(path, record):
    path.write_text(json.dumps(record), encoding="utf-8")


def _lane_evidence(root: Path, contract: ReleaseContract, lane: Lane, change=lambda _report, _provenance: None):
    """Exercise the verifier independently of application execution."""
    output = root / lane.value
    run = output / "run"
    run.mkdir(parents=True)
    cases = contract.select(lane)
    results = [CaseResult(case.id, case.suite, "passed", 0.1) for case in cases]
    completion = {
        "event": "stack_complete",
        "actual_backend": "gpu",
        "completed": True,
        "runtime": "wgpu-vulkan",
        "device": "NVIDIA GeForce RTX 3090",
        "physical_gpu": True,
    }
    if lane is Lane.PHYSICAL_GPU_GUI:
        results[0].notes["execution"] = completion
    for result in results:
        directory = run / "cases" / result.id
        directory.mkdir(parents=True)
        _write_json(directory / "result.json", asdict(result))
        if lane is Lane.PHYSICAL_GPU_GUI:
            gui = directory / "call-01"
            gui.mkdir()
            _write_json(gui / "events.jsonl", completion)
    if lane is not Lane.HOST:
        desktop = run / "linux-desktop"
        desktop.mkdir()
        (desktop / "desktop.log").write_text("", encoding="utf-8")
    write_reports(results, run, target=contract.target)
    report = json.loads((run / "report.json").read_text())
    provenance = {
        "contract_version": 2,
        "target": contract.target.name,
        "target_commit": "a" * 40,
        "suite_commit": "a" * 40,
        "target_descriptor_sha256": contract.descriptor_hash,
        "suite_source_sha256": contract.suite_source_hash,
        "uv_lock_sha256": contract.uv_lock_hash,
        "cli_command": contract.target.command("cli"),
        "gui_command": contract.target.command("gui"),
        "cases": [case.id for case in cases],
        "platform": "Linux-test-x86_64",
    }
    change(report, provenance)
    _write_json(run / "report.json", report)
    _write_json(run / "provenance.json", provenance)
    binary = {"sha256": "a" * 64, "bytes": 700}
    _write_json(output / "release-receipt.json", {
        "schema_version": 1,
        "lane": lane.value,
        "returncode": 0,
        "identity": {
            "target_commit": "a" * 40,
            "pancake_tree": "b" * 40,
            "cargo_lock_sha256": "c" * 64,
            "contract_sha256": contract.snapshot_hash,
            "descriptor_sha256": contract.descriptor_hash,
            "suite_source_sha256": contract.suite_source_hash,
            "uv_lock_sha256": contract.uv_lock_hash,
        },
        "platform": {"system": "Linux", "machine": "x86_64", "kernel": "test"},
        "executables": {"cli": binary, "gui": binary},
        "nvidia_inventory": "GPU-test, NVIDIA GeForce RTX 3090, 0000:01:00.0, 580.178.04",
        "files": {name: digest(run / name) for name in ("report.json", "provenance.json", "junit.xml")},
    })
    return output


def test_physical_gpu_lane_checks_original_result_and_event(tmp_path, contract):
    output = _lane_evidence(tmp_path, contract, Lane.PHYSICAL_GPU_GUI)
    ledger = verify_lane(output, Lane.PHYSICAL_GPU_GUI, contract)
    assert ledger["cases"] == ["interface.compute.gpu"]
    (output / "run/cases/interface.compute.gpu/call-01/events.jsonl").unlink()
    with pytest.raises(ValueError, match="raw job completion"):
        verify_lane(output, Lane.PHYSICAL_GPU_GUI, contract)


@pytest.mark.parametrize(
    ("change", "error"),
    [
        (lambda r, _: r.update(complete=False), "did not complete"),
        (lambda r, _: r["cases"].pop(), "case inventory"),
        (lambda r, _: r["cases"].__setitem__(0, r["cases"][1]), "case inventory"),
        (lambda r, _: r["cases"][0].update(status="unsupported"), "unsupported"),
        (lambda r, _: r["cases"][0].update(status="failed"), "failed"),
        (lambda r, _: r["cases"][0].update(status="pending"), "pending"),
        (lambda r, _: r["cases"][0].update(suite="devices"), "wrong lane"),
        (lambda r, _: r["counts"].update(passed=0), "counts"),
        (lambda _, p: p.update(uv_lock_sha256="d" * 64), "uv_lock_sha256"),
        (lambda _, p: p.update(target_commit="b" * 40), "target_commit"),
        (lambda _, p: p["cases"].reverse(), "case selection"),
        (lambda _, p: p.update(cli_command=["another-program"]), "cli_command"),
    ],
)
def test_lane_rejects_nonmatching_evidence(tmp_path, contract, change, error):
    output = _lane_evidence(tmp_path, contract, Lane.ISOLATED_GUI, change)
    with pytest.raises(ValueError, match=error):
        verify_lane(output, Lane.ISOLATED_GUI, contract)


def test_lane_rejects_post_receipt_report_edit(tmp_path, contract):
    output = _lane_evidence(tmp_path, contract, Lane.PHYSICAL_GPU_GUI)
    report = output / "run" / "report.json"
    report.write_text(report.read_text() + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="report.json.*digest"):
        verify_lane(output, Lane.PHYSICAL_GPU_GUI, contract)


def test_release_rejects_cases_from_different_binary_sets(tmp_path, contract):
    evidence = {lane: _lane_evidence(tmp_path, contract, lane) for lane in Lane}
    receipt_path = evidence[Lane.ISOLATED_GUI] / "release-receipt.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["executables"]["cli"]["sha256"] = "b" * 64
    _write_json(receipt_path, receipt)
    with pytest.raises(ValueError, match="executables differs from host receipt"):
        verify_release(evidence, contract)


def test_gpu_software_adapter_report_is_rejected(tmp_path, contract):
    output = _lane_evidence(tmp_path, contract, Lane.PHYSICAL_GPU_GUI)
    run = output / "run"
    report_path = run / "report.json"
    report = json.loads(report_path.read_text())
    result = report["cases"][0]
    result["notes"]["execution"]["physical_gpu"] = False
    _write_json(report_path, report)
    _write_json(run / "cases/interface.compute.gpu/result.json", result)
    receipt_path = output / "release-receipt.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["files"]["report.json"] = digest(report_path)
    _write_json(receipt_path, receipt)
    with pytest.raises(ValueError, match="physical NVIDIA"):
        verify_lane(output, Lane.PHYSICAL_GPU_GUI, contract)


def test_package_must_contain_the_tested_binaries(tmp_path):
    archive = tmp_path / "pancake_0.1.0_amd64.deb"
    archive.write_bytes(b"package receipt fixture")
    binary = {"sha256": "b" * 64, "bytes": 500}
    host = {
        "identity": {"target_commit": "a" * 40, "cargo_lock_sha256": "c" * 64},
        "executables": {"cli": binary, "gui": binary},
    }
    package = {
        "schema_version": 1,
        "source_commit": "a" * 40,
        "cargo_lock_sha256": "c" * 64,
        "binaries": {"pancake-cli": binary, "pancake-gui": binary},
        "archive": {"file": archive.name, "sha256": digest(archive), "bytes": archive.stat().st_size},
    }
    receipt = tmp_path / "package-receipt.json"
    _write_json(receipt, package)
    assert verify_package(tmp_path, host)["artifact_sha256"] == digest(archive)

    package["binaries"]["pancake-gui"] = {"sha256": "e" * 64, "bytes": 500}
    _write_json(receipt, package)
    with pytest.raises(ValueError, match="Packaged gui binary"):
        verify_package(tmp_path, host)
