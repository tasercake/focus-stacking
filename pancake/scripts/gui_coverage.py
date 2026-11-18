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
            if events.exists():
                for line in events.read_text().splitlines():
                    event = json.loads(line)
                    if event.get("actual_backend", "cpu") != "cpu":
                        raise ValueError(f"non-CPU backend in {events}")
            profile = raw / f"pancake-{pid}-{gui_build_id}.profraw"
            if not profile.is_file() or profile.is_symlink() or profile.stat().st_size == 0:
                raise ValueError(f"missing or empty profile for {case} process {pid}")
            if profile in accepted:
                raise ValueError(f"profile PID {pid} appears in multiple native calls")
            accepted[profile] = {
                "case": case,
                "call": str(shutdown_path.parent.relative_to(report_dir)),
                "shutdown": shutdown,
                "profile": profile.name,
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


def compare_mapping(standard, merged):
    """Reject altered source universes and loss of previously covered regions."""
    before, = standard["data"]
    after, = merged["data"]
    if not before["files"] or not before["functions"]:
        raise ValueError("no source mapping in the CPU report")
    left, line_regions, line_branches = numeric_mappings(before)
    right, joined_regions, joined_branches = numeric_mappings(after)
    if left != right:
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
            if count != merged_count or covered > merged_covered:
                raise ValueError(f"source mapping lost coverage or changed the {kind} denominator")


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
    if counts == [] or int(counts[0]) == 0 or not summary.endswith(f"Binary IDs: \n{build_id}"):
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


def main():
    """Expose explicit capture with a distinct status for invalid evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", action="append", required=True)
    parser.add_argument("--cli", required=True, type=lambda path: Path(path).resolve(strict=True))
    parser.add_argument("--gui", required=True, type=lambda path: Path(path).resolve(strict=True))
    parser.add_argument("--output", required=True, type=lambda path: Path(path).resolve())
    args = parser.parse_args()
    try:
        capture(args, Path(__file__).resolve().parents[2])
    except subprocess.CalledProcessError as error:
        print(f"GUI coverage: subprocess ended with status {error.returncode}", file=sys.stderr)
        return error.returncode if error.returncode >= 0 else 128 - error.returncode
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"GUI coverage: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
