"""Single entry point for portable conformance runs and reference capture."""
import argparse
from datetime import datetime, timezone
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys


def catalog():
    from .cases.cli import cli_cases
    from .cases.algorithms import algorithm_cases
    from .cases.devices import device_cases
    from .cases.interface import interface_cases
    from .cases.interface_settings import settings_cases
    return [*cli_cases(), *algorithm_cases(), *device_cases(), *interface_cases(), *settings_cases()]


def _parser():
    parser = argparse.ArgumentParser(prog="stack-conformance", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("list", "run"):
        command = commands.add_parser(name)
        command.add_argument("--suite", action="append", help="Select suites in execution order; repeat to include several")
        command.add_argument("--case", action="append", help="Select case ID glob; repeat to include several")
        if name == "list":
            command.add_argument("--json", action="store_true")
        else:
            command.add_argument("--target", type=Path, default=Path(__file__).resolve().parents[2] / "targets/chimpstackr.toml")
            command.add_argument("--output", type=Path)
            command.add_argument("--coverage", action=argparse.BooleanOptionalAction, default=None)
            command.add_argument("--min-line-coverage", type=float, default=0)
            command.add_argument("--min-branch-coverage", type=float, default=0)
            command.add_argument("--cli-command", help="JSON argv override, never executed through shell")
            command.add_argument("--gui-command", help="JSON argv override")
            baseline = command.add_mutually_exclusive_group()
            baseline.add_argument("--baseline", type=Path, help="Compare against immutable reference")
            baseline.add_argument("--record-baseline", type=Path, help="Capture new reference; refuses overwrite")
    return parser


def _provenance(target, cases):
    def git(args, cwd):
        result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else None
    project = Path(__file__).resolve().parents[2]
    lock = project / "uv.lock"
    sources = sorted((project / "src/stack_conformance").rglob("*.py")) + sorted((project / "src/stack_conformance").rglob("*.swift"))
    suite_hash = hashlib.sha256()
    for path in sources:
        suite_hash.update(str(path.relative_to(project)).encode() + b"\0" + path.read_bytes())
    return {"target": target.name, "target_root": str(target.root),
            "target_commit": git(["rev-parse", "HEAD"], target.root),
            "target_dirty": git(["status", "--porcelain"], target.root),
            "suite_commit": git(["rev-parse", "HEAD"], project),
            "suite_dirty": git(["status", "--porcelain"], project),
            "suite_source_sha256": suite_hash.hexdigest(),
            "target_descriptor_sha256": hashlib.sha256(target.descriptor.read_bytes()).hexdigest() if target.descriptor else None,
            "cli_command": target.command("cli"), "gui_command": target.command("gui") if target.gui else None,
            "python": sys.version, "platform": platform.platform(),
            "uv_lock_sha256": hashlib.sha256(lock.read_bytes()).hexdigest() if lock.exists() else None,
            "cases": [c.id for c in cases]}


def main(argv=None):
    if not __debug__:
        print("stack-conformance: Python optimization disables conformance assertions; use Python without -O", file=sys.stderr)
        return 2
    args = _parser().parse_args(argv)
    try:
        if args.command == "run":
            if not all(0 <= value <= 100 for value in (args.min_line_coverage, args.min_branch_coverage)):
                raise ValueError("coverage thresholds must be between 0 and 100")
            if args.coverage is False and (args.min_line_coverage or args.min_branch_coverage):
                raise ValueError("coverage thresholds require coverage collection")
        all_cases = catalog()
        unknown_suites = set(args.suite or ()) - {case.suite for case in all_cases}
        if unknown_suites:
            raise ValueError(f"unknown suite: {', '.join(sorted(unknown_suites))}")
        cases = [c for c in all_cases
                 if (not args.suite or c.suite in args.suite)
                 and (not args.case or any(fnmatch.fnmatchcase(c.id, p) for p in args.case))]
        if args.suite:
            order = {name: index for index, name in enumerate(dict.fromkeys(args.suite))}
            cases.sort(key=lambda case: order[case.suite])
        if not cases:
            raise ValueError("no cases match selection")
        if args.command == "list":
            records = [{"id": c.id, "suite": c.suite, "description": c.description} for c in cases]
            if args.json:
                print(json.dumps(records, indent=2))
            else:
                for record in records:
                    print(f"{record['id']:<65} {record['description']}")
                print(f"{len(records)} cases")
            return 0
        from .baseline import Baseline
        from .runner import run_cases, record_coverage
        from .target import TargetSpec
        target = TargetSpec.load(args.target)
        if args.cli_command or args.gui_command:
            overrides = {k: json.loads(v) for k, v in (("cli", args.cli_command), ("gui", args.gui_command)) if v}
            if not all(isinstance(v, list) and v and all(isinstance(x, str) for x in v) for v in overrides.values()):
                raise ValueError("command overrides must be nonempty JSON string arrays")
            target = target.with_commands(**overrides)
        output = (args.output or Path("artifacts") / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")).resolve()
        if output.exists() and any(output.iterdir()):
            raise ValueError(f"run output must be new or empty: {output}")
        output.mkdir(parents=True, exist_ok=True)
        baseline = Baseline(args.record_baseline, record=True) if args.record_baseline else Baseline(args.baseline) if args.baseline else None
        if baseline:
            baseline.validate_selection(cases, suites=args.suite, patterns=args.case)
        environment = dict(os.environ)
        coverage = None
        if args.coverage is True or (args.coverage is None and target.adapter == "chimpstackr-python"):
            if target.adapter != "chimpstackr-python":
                raise ValueError("coverage requires a target-specific coverage adapter")
            from .coverage import CoverageSession
            coverage = CoverageSession(target.root / "src", output / "coverage")
            environment = coverage.environment(environment)
        provenance = _provenance(target, cases)
        (output / "provenance.json").write_text(json.dumps(provenance, indent=2))
        print(f"Target: {target.name} | {len(cases)} cases | {output}", flush=True)
        def progress(index, total, result):
            print(f"[{index}/{total}] {result.status.upper():6} {result.id} ({result.duration:.2f}s)", flush=True)
            if result.suite == "interface" and not any(case.suite == "interface" for case in cases[index:]):
                print("Desktop phase finished; keyboard and pointer are free.", flush=True)
        results = run_cases(cases, target=target, output=output, environment=environment,
                            progress=progress, baseline=baseline)
        failed = sum(r.status == "failed" for r in results)
        if coverage:
            summary = coverage.finalize()
            print(f"Coverage: lines {summary['line_percent']:.2f}% ({summary['line_covered']}/{summary['line_total']}), "
                  f"branches {summary['branch_percent']:.2f}% ({summary['branch_covered']}/{summary['branch_total']})")
            if not record_coverage(output, summary, line_minimum=args.min_line_coverage,
                                   branch_minimum=args.min_branch_coverage):
                print("Coverage threshold failed", file=sys.stderr)
                failed += 1
        elif args.min_line_coverage or args.min_branch_coverage:
            raise ValueError("coverage thresholds require coverage collection")
        if baseline and baseline.record and not failed:
            baseline.save(provenance)
        print(f"Passed: {len(results) - sum(r.status == 'failed' for r in results)}; failed: {failed}")
        return 1 if failed else 0
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"stack-conformance: {exc}", file=sys.stderr)
        return 2
