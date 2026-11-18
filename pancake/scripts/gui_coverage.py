#!/usr/bin/env python3
"""Add authenticated native-desktop counters to an unchanged CPU coverage map."""

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
import sys


KINDS = ("lines", "functions", "regions", "branches")
DESCRIPTOR = "pancake-conformance/src/pancake_conformance/adapters/pancake/pancake.toml"


def read_json(path):
    """Read an evidence document without transforming the runner's format."""
    return json.loads(path.read_text())


def digest(path):
    """Hash a binary or profile without loading it into memory."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def check_report(report, cases):
    """Require the exact selected native case set to complete successfully."""
    delivered = report["cases"]
    if (report["complete"] is not True or report["completed_count"] != len(cases)
            or report["selected_count"] != len(cases)):
        raise ValueError("incomplete conformance report")
    if Counter(row["id"] for row in delivered) != Counter(cases):
        raise ValueError("conformance selection differs from the requested case IDs")
    failures = [f'{row["id"]} ({row["status"]})' for row in delivered if row["status"] != "passed"]
    if failures:
        raise ValueError(f"case did not pass: {', '.join(failures)}")


def collect_profiles(report_dir, raw, cases, gui_build_id, cli_build_id=None):
    """Bind each selected native process to one PID-matched CPU-only profile."""
    accepted = {}
    for case in cases:
        shutdowns = sorted((report_dir / "cases" / case).glob("call-*/shutdown.json"))
        if not shutdowns:
            raise ValueError(f"no native process was recorded for {case}")
        for shutdown_path in shutdowns:
            shutdown = read_json(shutdown_path)
            pid = shutdown["pid"]
            status = shutdown["status"]
            clean = status == "clean" and shutdown["returncode"] == 0 and shutdown["forced"] is False
            forced = (status == "forced" and shutdown["forced"] is True
                      and shutdown["returncode"] in (-signal.SIGTERM, -signal.SIGKILL))
            if type(pid) is not int or pid < 1 or not (clean or forced):
                raise ValueError(f"failed shutdown in {shutdown_path}: {shutdown}")
            events = shutdown_path.with_name("events.jsonl")
            cpu_completions = 0
            if events.exists():
                for line in events.read_text().splitlines():
                    event = json.loads(line)
                    if event.get("actual_backend", "cpu") != "cpu":
                        raise ValueError(f"non-CPU backend in {events}")
                    if event.get("event") == "stack_complete":
                        if (event.get("actual_backend") != "cpu" or event.get("runtime") != "cpu"
                                or event.get("completed") is not True):
                            raise ValueError(f"incomplete CPU stack evidence in {events}")
                        cpu_completions += 1
            profile = raw / f"pancake-{pid}-{gui_build_id}.profraw"
            if not profile.is_file() or profile.is_symlink() or profile.stat().st_size == 0:
                raise ValueError(f"missing or empty profile for {case} process {pid}")
            if profile in accepted:
                raise ValueError(f"profile PID {pid} appears in multiple native calls")
            accepted[profile] = {
                "case": case,
                "call": str(shutdown_path.parent.relative_to(report_dir)),
                "shutdown": shutdown,
                "cpu_completions": cpu_completions,
                "events_sha256": digest(events) if events.exists() else None,
                "profile": profile.name,
                "bytes": profile.stat().st_size,
                "sha256": digest(profile),
            }
    for profile in raw.iterdir():
        cli_profile = cli_build_id and re.fullmatch(rf"pancake-[1-9][0-9]*-{cli_build_id}\.profraw", profile.name)
        if profile not in accepted and not cli_profile:
            raise ValueError(f"unattributed raw profile: {profile}")
    return list(accepted.values())


def coverage_metrics(entry):
    """Extract the checked denominator and covered count for each metric."""
    return {kind: (entry[kind]["count"], entry[kind]["covered"]) for kind in KINDS}


def numeric_mappings(data):
    """Normalize LLVM source/function identities while excluding counter values."""
    regions, branches, functions = Counter(), Counter(), Counter()
    covered_regions, covered_branches = set(), set()
    for function in data["functions"]:
        identity = (function["name"], tuple(function["filenames"]))
        functions[identity] += 1
        for region in function["regions"]:
            key = (*identity, *region[:4], *region[5:])
            regions[key] += 1
            if region[4] > 0:
                covered_regions.add(key)
        for branch in function["branches"]:
            key = (*identity, *branch[:4], *branch[6:])
            branches[key] += 1
            covered_branches.update((key, outcome) for outcome in (4, 5) if branch[outcome] > 0)
    return (functions, regions, branches), covered_regions, covered_branches


def source_locations(entries):
    """Use exact source coordinates independent of generic symbol instantiation."""
    return {(entry[1][entry[6]], *entry[2:6], entry[8]) for entry in entries}


def compare_mapping(standard, merged, *, adding_mapping=False):
    """Reject altered source universes and loss of previously covered regions."""
    before, = standard["data"]
    after, = merged["data"]
    if not before["files"] or not before["functions"]:
        raise ValueError("no source mapping in the CPU report")
    left, line_regions, line_branches = numeric_mappings(before)
    right, joined_regions, joined_branches = numeric_mappings(after)
    if adding_mapping:
        removed = any(before_entries - after_entries for before_entries, after_entries in zip(left, right, strict=True))
        different_locations = any(source_locations(old) != source_locations(new)
                                  for old, new in zip(left[1:], right[1:], strict=True))
        if removed or different_locations:
            raise ValueError("source mapping changed when the native object was added")
    elif left != right:
        raise ValueError("source mapping changed")
    if line_regions - joined_regions or line_branches - joined_branches:
        raise ValueError("previously covered region or branch was lost")
    left_files = {row["filename"]: coverage_metrics(row["summary"]) for row in before["files"]}
    right_files = {row["filename"]: coverage_metrics(row["summary"]) for row in after["files"]}
    if left_files.keys() != right_files.keys():
        raise ValueError("source mapping file inventory changed")
    for left_metrics, right_metrics in [
        (coverage_metrics(before["totals"]), coverage_metrics(after["totals"])),
        *((left_files[name], right_files[name]) for name in left_files),
    ]:
        for kind, (count, covered) in left_metrics.items():
            merged_count, merged_covered = right_metrics[kind]
            if count != merged_count or covered > merged_covered or (adding_mapping and covered != merged_covered):
                raise ValueError(f"source mapping changed the {kind} denominator or control counts")


def output(command, cwd):
    """Run pinned tools with argument vectors and return their output."""
    return subprocess.check_output(command, cwd=cwd, text=True).strip()


def llvm_tool(workspace, name):
    """Resolve LLVM tooling from the active Rust toolchain's host directory."""
    target_lib = output(["rustc", "--print", "target-libdir"], workspace)
    return (Path(target_lib).parent / "bin" / name).resolve(strict=True)


def verify_profile(path, build_id, profdata):
    """Require a valid producer identity inside the raw LLVM counters."""
    summary = output([profdata, "show", "--binary-ids", path], path.parent)
    counts = re.findall(r"^Total count: ([0-9]+)$", summary, re.MULTILINE)
    if not counts or int(counts[0]) == 0 or not summary.endswith(f"Binary IDs: \n{build_id}"):
        raise ValueError(f"invalid counters or internal build ID mismatch: {path}")


def native_identity(path):
    """Record the executable SHA-256 and standard GNU ELF build ID."""
    notes = output(["readelf", "--notes", path], path.parent)
    ids = re.findall(r"Build ID: ([0-9a-f]+)", notes)
    if len(ids) != 1:
        raise ValueError(f"expected one ELF build ID in {path}")
    return {"path": str(path), "sha256": digest(path), "build_id": ids[0]}


def run_native(repo, evidence, cases, cli, gui, env):
    """Use the frozen runner's real isolated desktop and command substitutions."""
    command = [
        "uv", "run", "--project", str(repo / "pancake-conformance"), "--frozen",
        "pancake-conformance", "run", "--target", str(repo / DESCRIPTOR),
        "--output", str(evidence / "conformance"), "--no-coverage",
        "--cli-command", json.dumps([str(cli)]), "--gui-command", json.dumps([str(gui)]),
    ]
    for case in cases:
        command.extend(("--case", case))
    with (evidence / "conformance.log").open("w") as log:
        process = subprocess.run(command, cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT, check=False)
    (evidence / "conformance.status").write_text(f"{process.returncode}\n")
    process.check_returncode()
    return command


def capture(args, repo):
    """Collect raw profiles for a complete run of explicitly named CPU cases."""
    if sys.platform != "linux":
        raise ValueError("native continuous profiles are qualified on Linux only")
    if (len(set(args.case)) != len(args.case)
            or any(not re.fullmatch(r"interface\.[A-Za-z0-9_.-]+", case) for case in args.case)):
        raise ValueError("provide distinct exact native interface case IDs")
    descriptor = repo / DESCRIPTOR
    if output(["git", "status", "--porcelain"], repo):
        raise ValueError("native profile capture requires a clean revision")
    revision = output(["git", "rev-parse", "HEAD"], repo)
    binary = {kind: native_identity(getattr(args, kind)) for kind in ("gui", "cli")}
    evidence = args.output
    evidence.mkdir(parents=True)
    raw = evidence / "raw"
    raw.mkdir()
    env = dict(os.environ)
    for key in ("DISPLAY", "WAYLAND_DISPLAY", "DBUS_SESSION_BUS_ADDRESS", "AT_SPI_BUS_ADDRESS"):
        env.pop(key, None)
    env["LLVM_PROFILE_FILE"] = str(raw / "pancake-%p-%b%c.profraw")
    command = run_native(repo, evidence, args.case, args.cli, args.gui, env)
    report_dir = evidence / "conformance"
    check_report(read_json(report_dir / "report.json"), args.case)
    provenance = read_json(report_dir / "provenance.json")
    if (provenance["target_commit"] != revision or provenance["suite_commit"] != revision
            or provenance["target_dirty"] or provenance["suite_dirty"]
            or provenance["target_descriptor_sha256"] != digest(descriptor)
            or provenance["gui_command"] != [str(args.gui)]
            or provenance["cli_command"] != [str(args.cli)]):
        raise ValueError("conformance source or executable provenance does not match")
    for kind, identity in binary.items():
        if digest(getattr(args, kind)) != identity["sha256"]:
            raise ValueError(f"{kind} executable changed during conformance")
    sessions = collect_profiles(report_dir, raw, args.case, binary["gui"]["build_id"], binary["cli"]["build_id"])
    profdata = llvm_tool(repo / "pancake", "llvm-profdata")
    for session in sessions:
        verify_profile(raw / session["profile"], binary["gui"]["build_id"], profdata)
    result = {
        "revision": revision, "toolchain": output(["rustc", "-Vv"], repo / "pancake"),
        "lock_sha256": digest(repo / "pancake/Cargo.lock"),
        "suite_source_sha256": provenance["suite_source_sha256"],
        "descriptor_sha256": provenance["target_descriptor_sha256"],
        "command": command, "binary": binary, "sessions": sessions,
    }
    (evidence / "capture.json").write_text(json.dumps(result, indent=2) + "\n")
    print(f"Native CPU coverage: {len(args.case)} passed cases, {len(sessions)} matched GUI profiles.")


def export_arguments(log, workspace, llvm_cov):
    """Reuse exactly the objects and source filter selected by pinned cargo-llvm-cov."""
    prefix = "     Running `"
    exports = [
        shlex.split(line.removeprefix(prefix).removesuffix("`"))
        for line in log.read_text().splitlines()
        if line.startswith(prefix) and "/llvm-cov export " in line
    ]
    if len(exports) != 1:
        raise ValueError("expected one cargo-llvm-cov export command")
    tool, operation, format_flag, profile_flag, *mapping = exports[0]
    if (Path(tool).resolve() != llvm_cov or operation != "export" or format_flag != "-format=text"
            or not profile_flag.startswith("-instr-profile=")):
        raise ValueError("unexpected cargo-llvm-cov export arguments")
    pairs = list(zip(mapping[::2], mapping[1::2], strict=True))
    if len(pairs) < 2 or pairs[-1][0] != "-ignore-filename-regex":
        raise ValueError("missing standard coverage objects or filename filter")
    profile = Path(profile_flag.split("=", 1)[1]).resolve(strict=True)
    if profile.name != "pancake.profdata":
        raise ValueError("unexpected standard coverage profile")
    for flag, value in pairs[:-1]:
        if flag != "-object" or not (workspace / value).resolve(strict=True).is_relative_to(profile.parent):
            raise ValueError("unexpected object in the standard coverage report")
    return profile, mapping


def logged(command, destination, *, cwd, env=None):
    """Preserve command output and propagate actual failures."""
    with destination.open("w") as log:
        process = subprocess.run(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, check=False)
    return process.returncode


def combine(workspace, evidence, baseline, reexport_log):
    """Add GUI counters and prove that the standard denominator and scope survive."""
    capture_dir = evidence / "native"
    record = read_json(capture_dir / "capture.json")
    llvm_cov = llvm_tool(workspace, "llvm-cov")
    profdata = llvm_tool(workspace, "llvm-profdata")
    cpu_profile, mapping = export_arguments(reexport_log, workspace, llvm_cov)
    gui = Path(record["binary"]["gui"]["path"])
    if record["binary"]["gui"] != native_identity(gui):
        raise ValueError("native GUI executable changed before coverage merge")
    raw = []
    for session in record["sessions"]:
        profile = capture_dir / "raw" / session["profile"]
        if digest(profile) != session["sha256"]:
            raise ValueError(f"native profile changed before coverage merge: {profile}")
        raw.append(profile)
    records = {}
    for label, extra in (("control", ()), ("combined", raw)):
        profile = evidence / f"{label}.profdata"
        subprocess.run([profdata, "merge", "-sparse", "-o", profile, cpu_profile, *extra], check=True)
        export = [llvm_cov, "export", "-format=text", f"-instr-profile={profile}", *mapping, "-object", gui]
        with (evidence / f"{label}.json").open("w") as report:
            subprocess.run(export, cwd=workspace, stdout=report, check=True)
        records[label] = read_json(evidence / f"{label}.json")
    compare_mapping(baseline, records["control"], adding_mapping=True)
    compare_mapping(records["control"], records["combined"])
    print("Native CPU coverage: standard source mapping and thresholds retained.")


def workflow(args, repo):
    """Run the standard CPU gate and add real GUI counters through a separate check."""
    workspace = repo / "pancake"
    evidence = args.output
    evidence.mkdir(parents=True)
    revision = output(["git", "rev-parse", "HEAD"], repo)
    if output(["git", "status", "--porcelain"], repo):
        raise ValueError("native CPU coverage requires a clean revision")
    # A failing stand-alone test does not produce a fresh report. The standard
    # gate's uncovered-source failure is recorded independently of the union.
    baseline_command = ["bash", "scripts/check.sh", "coverage-cpu"]
    baseline_log = evidence / "coverage-cpu.log"
    report_path = workspace / "target/assurance/coverage-cpu.json"
    report_path.unlink(missing_ok=True)
    status = logged(baseline_command, baseline_log, cwd=workspace)
    (evidence / "coverage-cpu.status").write_text(f"{status}\n")
    uncovered = any(re.fullmatch(r"CPU assurance: uncovered CPU (lines|functions|regions|branches)", line)
                    for line in baseline_log.read_text().splitlines())
    if (not report_path.is_file() or status not in (0, 1) or (status == 1 and not uncovered)):
        raise subprocess.CalledProcessError(status or 2, baseline_command)
    baseline = read_json(report_path)
    (evidence / "coverage-cpu.json").write_bytes(report_path.read_bytes())
    reexport = evidence / "coverage-cpu-reexport.json"
    reexport_log = evidence / "coverage-cpu-reexport.log"
    report_command = ["cargo", "llvm-cov", "report", "--workspace", "--include-build-script",
                      "--json", "-v", "--output-path", reexport]
    status = logged(report_command, reexport_log, cwd=workspace)
    if status != 0:
        raise subprocess.CalledProcessError(status, report_command)
    fresh = read_json(reexport)
    compare_mapping(baseline, fresh)
    compare_mapping(fresh, baseline)

    native_target = workspace / "target/native-profile-target"
    env = dict(os.environ, CARGO_TARGET_DIR=str(native_target))
    flags = env.get("CARGO_ENCODED_RUSTFLAGS")
    if flags is None:
        flags = "\x1f".join(shlex.split(env.get("RUSTFLAGS", "")))
    env["CARGO_ENCODED_RUSTFLAGS"] = "\x1f".join(filter(None, (
        flags, "-C", "llvm-args=-runtime-counter-relocation",
    )))
    build_command = ["bash", "-e", "-c", "source <(cargo llvm-cov show-env --sh)\n"
                     "cargo build --locked --workspace --all-features --bins"]
    status = logged(build_command, evidence / "native-build.log", cwd=workspace, env=env)
    if status != 0:
        raise subprocess.CalledProcessError(status, build_command)
    if output(["git", "rev-parse", "HEAD"], repo) != revision:
        raise ValueError("source revision changed during coverage build")
    args.cli = native_target / "debug/pancake-cli"
    args.gui = native_target / "debug/pancake-gui"
    args.output = evidence / "native"
    capture(args, repo)
    combine(workspace, evidence, baseline, reexport_log)
    combined = evidence / "combined.json"
    return subprocess.run([sys.executable, "scripts/compare_assurance_coverage.py", workspace,
                           combined, combined], cwd=workspace, check=False).returncode


def main():
    """Expose explicit collection and a strict isolated CPU plus GUI check."""
    parser = argparse.ArgumentParser(description=__doc__)
    operations = parser.add_subparsers(dest="operation", required=True)
    for name in ("capture", "workflow"):
        command = operations.add_parser(name)
        command.add_argument("--case", action="append", required=True)
        command.add_argument("--output", required=True, type=lambda path: Path(path).resolve())
    capture_options = operations.choices["capture"]
    for kind in ("cli", "gui"):
        capture_options.add_argument(f"--{kind}", required=True, type=lambda path: Path(path).resolve(strict=True))
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    try:
        if args.operation == "workflow":
            return workflow(args, repo)
        capture(args, repo)
    except subprocess.CalledProcessError as error:
        print(f"GUI coverage: subprocess ended with status {error.returncode}", file=sys.stderr)
        return error.returncode if error.returncode >= 0 else 128 - error.returncode
    except (ValueError, OSError, KeyError, TypeError, IndexError) as error:
        print(f"GUI coverage: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
