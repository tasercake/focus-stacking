"""Collect native coverage only from a genuine passing case with a clean exit."""
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
from subprocess import check_output, run
import sys
from tempfile import TemporaryDirectory

root = Path.cwd().resolve()
workspace = root / "pancake"
case = "interface.recovery.close-unsaved"
descriptor = root / "pancake-conformance/src/pancake_conformance/adapters/pancake/pancake.toml"
revision = check_output(["git", "rev-parse", "HEAD"], text=True).strip()
assert revision == sys.argv[1], revision
artifact = root / "artifacts/pancake-assurance" / f"native-profile-{revision[:7]}"
assert not check_output(["git", "status", "--porcelain"], text=True).strip()
artifact.mkdir()
raw_dir = artifact / "raw"
raw_dir.mkdir()
coverage_target = workspace / "target/llvm-cov-target/debug"
application = coverage_target / "pancake-gui"
commands = (
    "uv", "run", "--project", "pancake-conformance", "--frozen", "pancake-conformance", "run",
    "--target", str(descriptor), "--case", case, "--no-coverage", "--output", str(artifact / "case"),
)
binaries = {}
env = dict(os.environ)
for name in ("DISPLAY", "WAYLAND_DISPLAY", "DBUS_SESSION_BUS_ADDRESS", "AT_SPI_BUS_ADDRESS"):
    env.pop(name, None)
env["LLVM_PROFILE_FILE"] = str(raw_dir / "pancake-%p-%m.profraw")
env["VK_DRIVER_FILES"] = "/usr/share/vulkan/icd.d/nvidia_icd.json"

with TemporaryDirectory(prefix="restore-launch-paths.", dir=artifact) as temporary, ExitStack() as cleanup:
    backup = Path(temporary)
    for name in ("pancake-cli", "pancake-gui"):
        binary = coverage_target / name
        assert binary.is_file(), binary
        with binary.open("rb") as contents:
            binaries[name] = hashlib.file_digest(contents, "sha256").hexdigest()
        launch_path = workspace / "target/release" / name
        if launch_path.exists() or launch_path.is_symlink():
            previous = backup / name
            launch_path.replace(previous)
            cleanup.callback(previous.replace, launch_path)
        launch_path.symlink_to(binary)
        cleanup.callback(launch_path.unlink)
    with (artifact / "conformance.log").open("w") as output:
        process = run(commands, env=env, stdout=output, stderr=output, check=False)
assert process.returncode == 0, process.returncode
conformance = artifact / "case"
report = json.loads((conformance / "report.json").read_text())
assert report["complete"] and report["selected_count"] == report["completed_count"] == 1, report
record, = report["cases"]
assert record["id"] == case and record["status"] == "passed", record
shutdowns = sorted((conformance / "cases" / case).glob("call-*/shutdown.json"))
assert shutdowns, "The native runner did not report a launched application."
sessions = []
stacks = []
profiles = []
for result_file in shutdowns:
    result = json.loads(result_file.read_text())
    assert result["status"] == "clean" and result["returncode"] == 0 and not result["forced"], result
    candidates = sorted(raw_dir.glob(f"pancake-{result['pid']}-*.profraw"))
    assert candidates and all(item.stat().st_size > 0 for item in candidates), result
    profiles.extend(candidates)
    sessions.append(result)
    events = [
        json.loads(line)
        for line in result_file.with_name("events.jsonl").read_text().splitlines()
    ]
    stacks.extend(event for event in events if event["event"] == "stack_complete")
assert stacks and all(
    stack["completed"] and stack["actual_backend"] == "cpu" and stack["runtime"] == "cpu"
    for stack in stacks
), stacks

toolchain = Path(check_output(["rustc", "--print", "sysroot"], cwd=workspace, text=True).strip())
llvm = toolchain / "lib/rustlib/x86_64-unknown-linux-gnu/bin"
profile = artifact / "native.profdata"
run([llvm / "llvm-profdata", "merge", "-sparse", "-o", profile, *profiles], check=True)
coverage = artifact / "gui-coverage.json"
with coverage.open("wb") as output:
    run([llvm / "llvm-cov", "export", "-instr-profile", profile, application], stdout=output, check=True)
report = json.loads(coverage.read_text())["data"][0]
gui_dir = workspace / "crates/pancake-gui/src"
gui = [row for row in report["files"] if Path(row["filename"]).is_relative_to(gui_dir)]
contributions = {
    str(Path(row["filename"]).relative_to(workspace)): row["summary"]["lines"]
    for row in gui
}
assert sum(row["covered"] for row in contributions.values()) > 0, contributions
receipt = {
    "revision": revision,
    "command": commands,
    "compiled_profile": "dev, Rust LLVM -C instrument-coverage",
    "descriptor_sha256": hashlib.sha256(descriptor.read_bytes()).hexdigest(),
    "binaries": binaries,
    "sessions": sessions,
    "stack_completion_events": stacks,
    "only_pid_matched_raw": {
        item.name: {"sha256": hashlib.sha256(item.read_bytes()).hexdigest(), "size": item.stat().st_size}
        for item in profiles
    },
    "gui_line_contributions": contributions,
}
(artifact / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print("Passed native case with clean shutdown and an LLVM-readable PID-matched profile.")
