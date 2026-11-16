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
    from .cases.interface_portability import portability_cases
    from .cases.coverage_algorithms import coverage_algorithm_cases
    from .cases.coverage_cli import coverage_cli_cases
    from .cases.coverage_interface import coverage_interface_cases
    from .cases.coverage_sprint import sprint_cases
    from .cases.recovery import recovery_cases
    cases = [*cli_cases(), *coverage_cli_cases(), *algorithm_cases(), *coverage_algorithm_cases(), *device_cases(),
            *interface_cases(), *settings_cases(), *portability_cases(), *coverage_interface_cases(), *sprint_cases(), *recovery_cases()]
    from dataclasses import replace
    optional = {
        "interface.layout.panels": "layout_panels",
        "interface.controls.advanced-visibility": "advanced_controls",
        "interface.settings.persistence": "preferences",
        "interface.import.recent-folders": "recent_folders",
        "interface.export.batch": "batch_export",
        "interface.recovery.batch-export": "batch_export",
        "interface.sprint.frame-context": "source_context",
        "interface.sprint.viewport-export": "viewport_export",
        "interface.portability.retained-results": "retained_results",
        "interface.result.manual-crop": "manual_crop",
        "interface.lifecycle.pause-cancel": "pause_resume",
        "interface.recovery.device-request": "gpu_preference",
    }
    return [replace(case, required_capabilities=tuple(dict.fromkeys(
        (*case.required_capabilities, *(('native_gui',) if case.suite == 'interface' else ()),
         *((optional[case.id],) if case.id in optional else ()))))) for case in cases]



def _parser():
    parser = argparse.ArgumentParser(prog="pancake-conformance", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("list", "run"):
        command = commands.add_parser(name)
        command.add_argument("--suite", action="append", help="Select suites in execution order; repeat to include several")
        command.add_argument("--case", action="append", help="Select case ID glob; repeat to include several")
        if name == "list":
            command.add_argument("--json", action="store_true")
        else:
            command.add_argument("--target", type=Path, required=True, help="Target descriptor; no application is selected by default")
            command.add_argument("--output", type=Path)
            command.add_argument("--fail-fast", action="store_true", help="Stop after first failed case; reports remain explicitly incomplete")
            command.add_argument("--gui-vm", action=argparse.BooleanOptionalAction, default=False,
                                 help="Run interface cases in configured Tart macOS VM; no host GUI fallback")
            command.add_argument("--gui-vm-visible", action="store_true", help="Show window when starting VM (default: headless)")
            command.add_argument("--gui-vm-persist", action="store_true", help="Leave dedicated VM running after tests (default: stop)")
            command.add_argument("--coverage", action=argparse.BooleanOptionalAction, default=None)
            command.add_argument("--raw-coverage", action="store_true", help="Use raw coverage denominator instead of configured reviewed scope")
            command.add_argument("--min-line-coverage", type=float, default=0)
            command.add_argument("--min-branch-coverage", type=float, default=0)
            command.add_argument("--cli-command", help="JSON argv override, never executed through shell")
            command.add_argument("--gui-command", help="JSON argv override")
            baseline = command.add_mutually_exclusive_group()
            baseline.add_argument("--baseline", type=Path, help="Compare against immutable reference")
            baseline.add_argument("--record-baseline", type=Path, help="Capture new reference; refuses overwrite")
    return parser


def _provenance(target, cases):
    from .source_files import source_files
    def git(args, cwd):
        result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else None
    project = Path(__file__).resolve().parents[2]
    lock = project / "uv.lock"
    sources = sorted(path for path in source_files(project / "src/pancake_conformance") if path.suffix in (".py", ".swift"))
    suite_hash = hashlib.sha256()
    for path in sources:
        suite_hash.update(str(path.relative_to(project)).encode() + b"\0" + path.read_bytes())
    from . import CONTRACT_VERSION
    record = {"contract_version": CONTRACT_VERSION, "target": target.name, "target_root": str(target.root),
            "target_commit": git(["rev-parse", "HEAD"], target.root),
            "target_dirty": git(["status", "--porcelain"], target.root),
            "suite_commit": git(["rev-parse", "HEAD"], project),
            "suite_dirty": git(["status", "--porcelain"], project),
            "suite_source_sha256": suite_hash.hexdigest(),
            "target_descriptor_sha256": hashlib.sha256(target.descriptor.read_bytes()).hexdigest() if target.descriptor else None,
            "coverage_scope_sha256": hashlib.sha256(target.coverage_scope.read_bytes()).hexdigest() if target.coverage_scope else None,
            "cli_command": target.command("cli"), "gui_command": target.command("gui") if target.gui else None,
            "python": sys.version, "platform": platform.platform(),
            "uv_lock_sha256": hashlib.sha256(lock.read_bytes()).hexdigest() if lock.exists() else None,
            "cases": [c.id for c in cases]}
    hooks = target.adapter_hooks()
    if hooks is not None and hasattr(hooks, "runtime_info"):
        record["reference_runtime"] = hooks.runtime_info()
    return record


def main(argv=None):
    if not __debug__:
        print("pancake-conformance: Python optimization disables conformance assertions; use Python without -O", file=sys.stderr)
        return 2
    args = _parser().parse_args(argv)
    try:
        if args.command == "run":
            if (args.gui_vm_visible or args.gui_vm_persist) and not args.gui_vm:
                raise ValueError("--gui-vm-visible and --gui-vm-persist require --gui-vm")
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
        if args.gui_vm and not args.suite:
            # The catalog interleaves feature groups; VM transport needs one GUI batch.
            order = {suite: i for i, suite in enumerate(dict.fromkeys(case.suite for case in cases))}
            cases.sort(key=lambda case: order[case.suite])
        from .baseline import Baseline
        from .runner import run_cases, run_vm_cases, record_coverage
        from .target import TargetSpec
        target = TargetSpec.load(args.target)
        overrides = {}
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
        scope_profile = None
        if args.coverage is True or (args.coverage is None and target.coverage_source is not None):
            if target.coverage_source is None:
                raise ValueError("coverage requires instrumentation.source in the target descriptor")
            from .coverage import CoverageSession
            coverage = CoverageSession(target.coverage_source, output / "coverage")
            environment = coverage.environment(environment)
            if target.coverage_scope and not args.raw_coverage:
                content = target.coverage_scope.read_bytes()
                scope_profile = json.loads(content)
                if scope_profile.get("source_sha256") != coverage.provenance["source_sha256"]:
                    raise ValueError("coverage scope source fingerprint changed; review exclusions")
                (output / "coverage/scope-profile.json").write_bytes(content)
        provenance = _provenance(target, cases)
        (output / "provenance.json").write_text(json.dumps(provenance, indent=2))
        print(f"Target: {target.name} | {len(cases)} cases | {output}", flush=True)
        def progress(index, total, result):
            print(f"[{index}/{total}] {result.status.upper():6} {result.id} ({result.duration:.2f}s)", flush=True)
            if not args.gui_vm and result.suite == "interface" and not any(case.suite == "interface" for case in cases[index:]):
                print("Desktop phase finished; keyboard and pointer are free.", flush=True)
        common = dict(target=target, output=output, environment=environment, progress=progress,
                      baseline=baseline, fail_fast=args.fail_fast)
        if args.gui_vm:
            project = Path(__file__).resolve().parents[2]
            workspace = next((parent for parent in project.parents if (parent / "submodules").is_dir()), project)
            results = run_vm_cases(cases, **common, workspace=workspace, project=project,
                                   visible=args.gui_vm_visible, persist=args.gui_vm_persist,
                                   coverage=coverage, provenance=provenance,
                                   cli_command=overrides.get("cli"), gui_command=overrides.get("gui"))
        else:
            if sys.platform == "linux" and any(case.suite == "interface" for case in cases):
                from .linux_ui import isolated_desktop
                with isolated_desktop(output / "linux-desktop", environment) as desktop_env:
                    results = run_cases(cases, **{**common, "environment": desktop_env})
            else:
                results = run_cases(cases, **common)
        failed = sum(r.status == "failed" for r in results)
        if coverage:
            summary = coverage.finalize(allow_empty=bool(results) and all(result.status == "unsupported" for result in results))
            if scope_profile is not None:
                from .coverage_scope import scoped_summary
                summary["scope"] = scoped_summary(json.loads((output / "coverage/coverage.json").read_text()),
                                                   target.coverage_source, scope_profile)
                (output / "coverage/scoped.json").write_text(json.dumps(summary["scope"], indent=2) + "\n")
                (output / "coverage/summary.json").write_text(json.dumps(summary, indent=2) + "\n")
            print(f"Coverage: lines {summary['line_percent']:.2f}% ({summary['line_covered']}/{summary['line_total']}), "
                  f"branches {summary['branch_percent']:.2f}% ({summary['branch_covered']}/{summary['branch_total']})")
            if scope := summary.get("scope"):
                print(f"Scoped coverage ({scope['name']}): lines {scope['line_percent']:.2f}% "
                      f"({scope['line_covered']}/{scope['line_total']}), branches {scope['branch_percent']:.2f}% "
                      f"({scope['branch_covered']}/{scope['branch_total']}); "
                      f"excluded {scope['excluded_lines']} lines, {scope['excluded_branches']} branch exits")
            if not record_coverage(output, summary, line_minimum=args.min_line_coverage,
                                   branch_minimum=args.min_branch_coverage):
                print("Coverage threshold failed", file=sys.stderr)
                failed += 1
        elif args.min_line_coverage or args.min_branch_coverage:
            raise ValueError("coverage thresholds require coverage collection")
        pending = sum(result.status == "pending" for result in results)
        if baseline and baseline.record and not failed and not pending:
            baseline.save(provenance)
        unsupported = [r for r in results if r.status == "unsupported"]
        for result in unsupported:
            print(f"Unsupported: {result.id}: {result.reason}")
        print(f"Passed: {sum(r.status == 'passed' for r in results)}; failed: {failed}; unsupported: {len(unsupported)}")
        if pending:
            print(f"Pending host CLI verification: {pending}")
            if os.environ.get("PANCAKE_CONFORMANCE_VM_GUEST") != "1":
                print("pancake-conformance: host CLI verification did not complete", file=sys.stderr)
                return 2
        return 1 if failed else 0
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"pancake-conformance: {exc}", file=sys.stderr)
        return 2
