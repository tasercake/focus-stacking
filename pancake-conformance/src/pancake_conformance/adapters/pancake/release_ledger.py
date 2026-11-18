"""Capture and verify release conformance from the unchanged external runner."""

import argparse
from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

from pancake_conformance import CONTRACT_VERSION
from pancake_conformance.cli import catalog
from pancake_conformance.model import Case
from pancake_conformance.source_files import source_files
from pancake_conformance.target import TargetSpec


class Lane(StrEnum):
    """The disjoint native Linux conformance selections."""

    HOST = "host"
    ISOLATED_GUI = "isolated-gui"
    PHYSICAL_GPU_GUI = "physical-gpu-gui"


GPU_CASE = "interface.compute.gpu"
CASE_COUNTS = {Lane.HOST: 341, Lane.ISOLATED_GUI: 34, Lane.PHYSICAL_GPU_GUI: 1}
CATALOG_COUNTS = {"cli": 46, "algorithms": 223, "devices": 72, "interface": 35}
REPORT_FILES = ("report.json", "provenance.json", "junit.xml")
CONTRACT_SUFFIXES = {".py", ".swift", ".toml", ".lock", ".md", ".json"}
ADAPTER = Path(__file__).resolve().parent
PROJECT = ADAPTER.parents[3]


@dataclass(frozen=True)
class ReleaseContract:
    """Exact current catalog and runtime inputs for the release descriptor."""

    target: TargetSpec
    cases: tuple[Case, ...]
    snapshot_hash: str
    descriptor_hash: str
    suite_source_hash: str
    uv_lock_hash: str

    def select(self, lane):
        """Keep frozen execution order while assigning each ID to one lane."""
        if lane is Lane.HOST:
            return tuple(case for case in self.cases if case.suite in {"cli", "algorithms", "devices"})
        if lane is Lane.ISOLATED_GUI:
            return tuple(case for case in self.cases if case.suite == "interface" and case.id != GPU_CASE)
        return tuple(case for case in self.cases if case.id == GPU_CASE)


def _require(condition, message):
    """Fail closed with a diagnostic available to the command line."""
    if not condition:
        raise ValueError(message)


def _object(path):
    """Read a report object and reject ambiguous repeated fields."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            _require(key not in result, f"{path}: duplicate JSON key {key}")
            result[key] = value
        return result

    with path.open(encoding="utf-8") as stream:
        result = json.load(stream, object_pairs_hook=unique)
    _require(isinstance(result, dict), f"{path}: expected a JSON object")
    return result


def digest(path):
    """Return a streaming SHA-256 digest of an artifact."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _tree_digest(paths):
    """Use the runner's path, NUL and bytes encoding in lexical order."""
    result = hashlib.sha256()
    for path in sorted(paths):
        result.update(path.relative_to(PROJECT).as_posix().encode() + b"\0" + path.read_bytes())
    return result.hexdigest()


def _metadata(case):
    """Return the case fields pinned by the reviewed snapshot."""
    return {"id": case.id, "suite": case.suite, "description": case.description,
            "required_capabilities": list(case.required_capabilities)}


def load_contract():
    """Verify the reviewed non-adapter file universe and current 376 case catalog."""
    snapshot = _object(ADAPTER / "contract-current.json")
    roadmap = _object(ADAPTER / "case-roadmap.json")
    _require(snapshot["contract_version"] == roadmap["contract_version"] == CONTRACT_VERSION == 2,
             "Unexpected contract version")
    files = list(source_files(PROJECT))
    frozen = {path.relative_to(PROJECT).as_posix(): path for path in files
              if path.suffix in CONTRACT_SUFFIXES and "adapters" not in path.relative_to(PROJECT).parts}
    _require(frozen.keys() == snapshot["files"].keys(), "Reviewed frozen contract file inventory has changed")
    for name, path in frozen.items():
        _require(digest(path) == snapshot["files"][name], f"Reviewed contract file changed: {name}")
    snapshot_hash = _tree_digest(frozen.values())
    _require(snapshot_hash == snapshot["combined_sha256"], "Reviewed contract digest differs")
    cases = tuple(catalog())
    metadata = [_metadata(case) for case in cases]
    projected = [{key: record[key] for key in ("id", "suite", "description", "required_capabilities")}
                 for record in roadmap["cases"]]
    _require(len({case.id for case in cases}) == len(cases) == 376
             and Counter(case.suite for case in cases) == CATALOG_COUNTS
             and metadata == snapshot["catalog"]["cases"] == projected, "Frozen catalog metadata differs")
    descriptor = ADAPTER / "pancake.toml"
    target = TargetSpec.load(descriptor)
    _require(target.name == "pancake-rust" and not target.adapter, "Release requires the direct Pancake descriptor")
    suite_root = PROJECT / "src" / "pancake_conformance"
    sources = [path for path in files if path.is_relative_to(suite_root) and path.suffix in {".py", ".swift"}]
    contract = ReleaseContract(target, cases, snapshot_hash, digest(descriptor), _tree_digest(sources),
                               digest(PROJECT / "uv.lock"))
    _require(all(len(contract.select(lane)) == CASE_COUNTS[lane] for lane in Lane),
             "Unexpected release lane sizes")
    return contract


def _git_output(root, *arguments):
    """Read Git state without modifying the worktree."""
    result = subprocess.run(["git", "-C", str(root), *arguments], capture_output=True, check=True, text=True)
    return result.stdout.strip()


def _source_identity(contract):
    """Bind a clean committed application and suite to the actual lock bytes."""
    root = contract.target.root.parent
    dirty = _git_output(root, "status", "--porcelain=v1", "--untracked-files=all", "--",
                        contract.target.root.name, PROJECT.name)
    _require(not dirty, f"Commit application and suite changes before release capture:\n{dirty}")
    return {
        "target_commit": _git_output(root, "rev-parse", "HEAD"),
        "pancake_tree": _git_output(root, "rev-parse", f"HEAD:{contract.target.root.name}"),
        "cargo_lock_sha256": digest(contract.target.root / "Cargo.lock"),
        "contract_sha256": contract.snapshot_hash,
        "descriptor_sha256": contract.descriptor_hash,
        "suite_source_sha256": contract.suite_source_hash,
        "uv_lock_sha256": contract.uv_lock_hash,
    }


def _executables(target):
    """Hash the direct launch executables used by the descriptor."""
    artifacts = {}
    for kind in ("cli", "gui"):
        token = target.command(kind)[0]
        _require("/" in token, f"Release {kind} command must identify a direct executable path")
        path = (target.root / token).resolve(strict=True)
        _require(path.is_file() and os.access(path, os.X_OK), f"Missing release executable: {path}")
        artifacts[kind] = {"sha256": digest(path), "bytes": path.stat().st_size}
    return artifacts


def _nvidia_inventory():
    """Observe physical devices and drivers independently of application events."""
    query = ["nvidia-smi", "--query-gpu=uuid,name,pci.bus_id,driver_version", "--format=csv,noheader"]
    return subprocess.run(query, text=True, check=True, capture_output=True, timeout=10).stdout.strip()


def _write_new(path, value):
    """Retain evidence without overwriting a previous run."""
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def capture_lane(output, lane, contract):
    """Run one real release selection and retain before/after provenance."""
    _require(sys.platform == "linux" and platform.machine() == "x86_64",
             "This capture command covers Linux x86-64 release conformance")
    _require("PANCAKE_CONFORMANCE_VM_GUEST" not in os.environ, "Use the native Linux runner for these lanes")
    identity = _source_identity(contract)
    executables = _executables(contract.target)
    inventory = _nvidia_inventory()
    output = output.resolve()
    output.mkdir(parents=True)
    run = output / "run"
    command = [sys.executable, "-m", "pancake_conformance", "run", "--no-coverage",
               "--target", str(contract.target.descriptor), "--output", str(run)]
    cases = contract.select(lane)
    for case in cases:
        command.extend(("--case", case.id))
    with (output / "run.log").open("x", encoding="utf-8") as log:
        process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, cwd=contract.target.root.parent)
    _require(identity == _source_identity(load_contract()), "Conformance inputs changed during execution")
    _require(executables == _executables(contract.target), "A release executable changed during execution")
    _require(inventory == _nvidia_inventory(), "Physical GPU inventory changed during execution")
    _write_new(output / "release-receipt.json", {
        "schema_version": 1,
        "lane": lane.value,
        "returncode": process.returncode,
        "command": command,
        "identity": identity,
        "executables": executables,
        "nvidia_inventory": inventory,
        "platform": {"system": platform.system(), "machine": platform.machine(), "kernel": platform.release(),
                     "processor": platform.processor(), "os": platform.platform()},
        "files": {name: digest(run / name) for name in REPORT_FILES if (run / name).is_file()},
    })
    return verify_lane(output, lane, contract)


def _verify_physical_gpu(case_dir, execution, inventory):
    """Require the native driver's original stack completion and physical identity."""
    names = [line.split(",")[1].strip() for line in inventory.splitlines() if line.count(",") == 3
             and line.startswith("GPU-")]
    _require(isinstance(execution, dict) and execution.get("event") == "stack_complete"
             and execution.get("completed") is True and execution.get("actual_backend") == "gpu"
             and execution.get("runtime") in {"wgpu-vulkan", "cuda"}
             and execution.get("physical_gpu") is True and execution.get("device") in names,
             "GPU GUI completion lacks matching physical NVIDIA device evidence")
    completions = []
    for path in sorted(case_dir.glob("call-*/events.jsonl")):
        events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        completions.extend(event for event in events if event.get("event") == "stack_complete")
    _require(bool(completions) and completions[-1] == execution, "Missing matching raw job completion event")


def _verify_case(case, record, run, inventory):
    """Match each report row to the frozen case and retained raw result."""
    ident = case.id
    _require(record.get("suite") == case.suite and record.get("execution_environment") == "host",
             f"{ident}: wrong lane")
    status = record.get("status")
    _require(status == "passed", f"{ident}: {status} is not a passing verdict")
    duration = record.get("duration")
    _require(type(duration) in {int, float} and math.isfinite(duration) and duration >= 0,
             f"{ident}: invalid duration")
    notes, outputs = record.get("notes"), record.get("outputs")
    _require(isinstance(notes, dict) and isinstance(outputs, dict)
             and not (record.get("error") or record.get("reason") or notes.get("host_verification_pending")
                      or notes.get("unsupported_capabilities")), f"{ident}: inconsistent passing record")
    case_dir = run / "cases" / ident
    _require(case_dir.resolve().is_relative_to(run), f"{ident}: case directory escapes run")
    _require(record == _object(case_dir / "result.json"), f"{ident}: raw case result differs")
    for value in outputs.values():
        _require(isinstance(value, str), f"{ident}: invalid output entry")
        relative = Path(value)
        artifact = (case_dir / relative).resolve()
        _require(not relative.is_absolute() and artifact.is_relative_to(case_dir.resolve()) and artifact.is_file(),
                 f"{ident}: invalid or missing output {relative}")
    if ident == GPU_CASE:
        _verify_physical_gpu(case_dir, notes.get("execution"), inventory)


def verify_lane(output, lane, contract):
    """Accept only the complete native report, with matching executable provenance."""
    output = output.resolve()
    run = output / "run"
    receipt = _object(output / "release-receipt.json")
    _require(receipt.get("schema_version") == 1 and receipt.get("lane") == lane.value,
             f"{output}: receipt does not describe {lane.value}")
    for name in REPORT_FILES:
        _require(receipt["files"].get(name) == digest(run / name), f"{name}: digest differs from capture receipt")
    identity = receipt["identity"]
    expected = {"contract_sha256": contract.snapshot_hash, "descriptor_sha256": contract.descriptor_hash,
                "suite_source_sha256": contract.suite_source_hash, "uv_lock_sha256": contract.uv_lock_hash}
    for field, value in expected.items():
        _require(identity.get(field) == value, f"Receipt {field} differs from the current release inputs")
    for field in ("target_commit", "pancake_tree", "cargo_lock_sha256"):
        pattern = r"[0-9a-f]{64}" if field == "cargo_lock_sha256" else r"[0-9a-f]{40}"
        _require(re.fullmatch(pattern, identity.get(field, "")), f"Missing a valid {field}")
    for kind in ("cli", "gui"):
        artifact = receipt["executables"][kind]
        _require(re.fullmatch(r"[0-9a-f]{64}", artifact.get("sha256", ""))
                 and type(artifact.get("bytes")) is int and artifact["bytes"] > 0, f"Missing {kind} binary evidence")
    machine = receipt["platform"]
    _require(machine.get("system") == "Linux" and machine.get("machine") == "x86_64",
             f"{lane.value}: requires the Linux x86-64 execution receipt")
    inventory = receipt["nvidia_inventory"]
    _require(isinstance(inventory, str) and bool(inventory.strip()), "Missing physical NVIDIA inventory")
    provenance = _object(run / "provenance.json")
    matched = {
        "contract_version": CONTRACT_VERSION, "target": contract.target.name,
        "suite_commit": identity["target_commit"], "target_commit": identity["target_commit"],
        "target_descriptor_sha256": identity["descriptor_sha256"],
        "suite_source_sha256": identity["suite_source_sha256"], "uv_lock_sha256": identity["uv_lock_sha256"],
        "cli_command": contract.target.command("cli"), "gui_command": contract.target.command("gui"),
    }
    for key, expected in matched.items():
        _require(provenance.get(key) == expected, f"Run provenance {key} differs from capture identity")
    _require(provenance.get("platform", "").startswith("Linux") and not provenance.get("guest"),
             "Provenance is from the wrong execution environment")
    if lane is not Lane.HOST:
        _require((run / "linux-desktop" / "desktop.log").is_file(), "Missing private Linux desktop evidence")
    cases = contract.select(lane)
    identifiers = [case.id for case in cases]
    _require(provenance.get("cases") == identifiers, f"{lane.value}: incorrect case selection in provenance")
    report = _object(run / "report.json")
    count = len(cases)
    _require(report.get("schema_version") == 1 and report.get("target") == contract.target.name,
             "Wrong conformance report identity")
    _require(report.get("complete") is True and report.get("selected_count") == count
             and report.get("completed_count") == count, "Run did not complete the selected cases")
    records = report["cases"]
    _require([record.get("id") for record in records] == identifiers,
             f"{lane.value}: incorrect case inventory in report")
    for case, record in zip(cases, records, strict=True):
        _verify_case(case, record, run, inventory)
    _require(report.get("counts") == {"passed": count, "failed": 0, "unsupported": 0}, "Incorrect report counts")
    _require(report.get("status") == "passed" and receipt.get("returncode") == 0, "Run did not pass")
    return {"cases": identifiers, "identity": identity, "executables": receipt["executables"],
            "platform": machine, "nvidia_inventory": inventory, "receipt_sha256": digest(output / "release-receipt.json"),
            "report_sha256": receipt["files"]["report.json"], "artifact_directory": str(output)}


def verify_release(directories, contract):
    """Require disjoint lane passes from a single source, lock and binary set."""
    lanes = {lane: verify_lane(directories[lane], lane, contract) for lane in Lane}
    host = lanes[Lane.HOST]
    for lane, record in lanes.items():
        for field in ("identity", "executables", "nvidia_inventory", "platform"):
            _require(record[field] == host[field], f"{lane.value}: {field} differs from host receipt")
    identifiers = [ident for record in lanes.values() for ident in record["cases"]]
    _require(len(identifiers) == len(set(identifiers)) == 376, "Incomplete or conflicting 376-case ledger")
    # Review the claimed source objects even after an evidence-only follow-up commit.
    identity = host["identity"]
    root = contract.target.root.parent
    spec = f"{identity['target_commit']}:{contract.target.root.name}"
    _require(_git_output(root, "rev-parse", spec) == identity["pancake_tree"], "Application Git tree differs")
    git_lock = subprocess.run(["git", "-C", str(root), "show", f"{spec}/Cargo.lock"],
                              capture_output=True, check=True).stdout
    _require(hashlib.sha256(git_lock).hexdigest() == identity["cargo_lock_sha256"], "Cargo.lock differs from tested revision")
    return {"schema_version": 1, "target": contract.target.name, "passed": 376,
            "required_apple_runtime_evidence": "separate", "lanes": lanes}


def verify_package(directory, host):
    """Bind the native package receipt to the conformance executables."""
    path = directory / "package-receipt.json"
    package = _object(path)
    identity = host["identity"]
    _require(package.get("schema_version") == 1 and package.get("source_commit") == identity["target_commit"]
             and package.get("cargo_lock_sha256") == identity["cargo_lock_sha256"],
             "Package source or lock differs from the tested release")
    for kind, binary in host["executables"].items():
        packaged = package["binaries"][f"pancake-{kind}"]
        _require(all(packaged.get(key) == value for key, value in binary.items()),
                 f"Packaged {kind} binary differs from the tested release")
    artifact = package["archive"]
    filename = artifact["file"]
    _require(re.fullmatch(r"pancake_[0-9A-Za-z.+~\-]+_amd64\.deb", filename), "Invalid Linux package filename")
    archive = directory / filename
    _require(archive.stat().st_size == artifact.get("bytes") and digest(archive) == artifact.get("sha256"),
             "Linux package differs from its capture receipt")
    return {"file": str(archive.resolve()), "artifact_sha256": artifact["sha256"], "receipt_sha256": digest(path)}


def main(argv=None):
    """Expose collection and strict verification as separate commands."""
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="command", required=True)
    capture = modes.add_parser("capture", help="Run a native Linux lane")
    capture.add_argument("lane", type=Lane, choices=tuple(Lane))
    capture.add_argument("output", type=Path)
    verify = modes.add_parser("verify", help="Verify the 376-case Linux receipts")
    for lane in Lane:
        verify.add_argument(f"--{lane.value}", dest=lane.name, type=Path, required=True)
    verify.add_argument("--package", type=Path, required=True)
    verify.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        contract = load_contract()
        if args.command == "capture":
            record = capture_lane(args.output, args.lane, contract)
            print(f"{args.lane.value}: {len(record['cases'])} cases passed")
        else:
            result = verify_release({lane: getattr(args, lane.name) for lane in Lane}, contract)
            result["linux_package"] = verify_package(args.package, result["lanes"][Lane.HOST])
            _write_new(args.output, result)
            print(f"{result['passed']}/376 Pancake cases passed on the matched Linux lanes")
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(f"release ledger: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
